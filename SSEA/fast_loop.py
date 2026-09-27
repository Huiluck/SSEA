"""Fast Loop —— 快环（FSL）闭环 + 睡眠期状态机。

**任务书依据**：docs/08-dual-loop-interface-and-gap-closure.md §4.1（快环公式）、
§4.3（睡眠期状态机）、§2.1（结构注入面）。

本模块是 Milestone 2 的**集成点**。它不做任何新算法，只把已实现的模块按
08 §4.1 的公式接线：

    p_t = PerceptionEncoder(o_t, b_t)
    m_t = MemorySystem.retrieve(p_t)               # Milestone 3 起为真实记忆
    d_t = MetabolicMonitor.drive_vector(b_t)
    h_t = StateCore(p_t, m_t, b_t, d_t, h_{t-1})
    a_t = ActionDecoder(h_t, b_t.action_constraints, d_t)
    u_t = SkillRunner(a_t, ctx.skills)
    o_{t+1}, f_t = Environment.step(u_t)
    f_t.prediction_error = SurpriseEstimator.update(o_t, o_{t+1})
    MemorySystem.write(a_t.memory, p_t, o_{t+1}, f_t)   # Milestone 3 新增

慢环在哪里
----------
**不在这里。** 本模块只提供 ``slow_loop`` 一个钩子，默认 None——快环不会
伪造一个慢环来"演示"双环。慢环（Milestone 4）实现这个钩子即可接入，
快环代码零改动。

这正是 08 §2.1「快环零改动」的落地：慢环无论改什么，本文件的读取接口都不变。

睡眠期为什么在快环里
------------------
状态机在快环里，因为**只有快环知道模型此刻是否处于安全状态**（代谢监控器
读的是本帧观测）。睡眠期是一等公民状态（08 §2.2），与 RUN 并列：

    RUN ──代谢判定──► SLEEP ──触发慢环──► WAKE ──换版快照──► RUN

``WAKE`` 单独作为一个状态是有意的：它让"换结构版本"成为一个**可观测的
时刻**，而不是混在某一帧的动作里。任何行为改变的归因都能对齐到这一次换版。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Protocol

import torch

from .action_decoder import ActionDecoder, DecodeCandidates
from .environment import Environment
from .memory_system import MemoryConfig, MemorySystem
from .metabolic_monitor import MetabolicMonitor
from .perception_encoder import PerceptionEncoder
from .skill_runner import SkillRunner
from .sse_protocols import (
    ALLOWED_PROPOSAL_TYPES,
    Action,
    FastLoopContext,
    Feedback,
    MemoryItem,
    MemoryWrite,
    Observation,
    idle_action,
)
from .state_core import StateCore

#: 睡眠期最少帧数。少于这个数就不值得触发慢环——整理经验有固定开销。
DEFAULT_MIN_SLEEP_FRAMES = 5

# ----------------------------------------------------------------------
#  状态
# ----------------------------------------------------------------------

STATE_RUN = "RUN"
STATE_SLEEP = "SLEEP"
STATE_WAKE = "WAKE"
STATE_DEAD = "DEAD"

#: 全部状态。供观察员与测试枚举。
STATES: tuple[str, ...] = (STATE_RUN, STATE_SLEEP, STATE_WAKE, STATE_DEAD)

#: 慢环钩子：吃整条 trace，产出一份新快照（或 None = 未提交新结构）。
SlowLoopHook = Callable[[tuple["StepRecord", ...]], FastLoopContext | None]

#: 死亡快照钩子：环境判定死亡时调用（08 §2.2 的 DEATH_SNAPSHOT 触发器）。
DeathHook = Callable[[tuple["StepRecord", ...], Observation], None]


# ----------------------------------------------------------------------
#  记忆检索接口
# ----------------------------------------------------------------------


class MemoryRetriever(Protocol):
    """记忆检索接口。对应 08 §4.1 的 ``MemorySystem.retrieve``。

    Milestone 3 起由 ``MemorySystem`` 实现。签名相对 08 §4.1 的公式
    ``retrieve(p_t, h_{t-1})`` **收窄了一个参数**：``h_{t-1}`` 不进检索键。

    理由是可继承性（C7）：记忆的键必须是世界（perception）。用 hidden 做键，
    子代的 hidden 分布与父代不同，继承来的 RULE / SKILL 记忆永远命中不了——
    那等于把 latent_action 那种"永远为空的死字段"传给了下一代。
    完整推导见 memory_system.py 模块 docstring 第 3 条。

    ``now`` 是观测时间，用于回写 ``MemoryItem.last_retrieved``。可省——
    省了就不更新计数，那会让可遗传筛选（08 §3.3 的 retrieval_count ≥ N）
    永远不满足。
    """

    def retrieve(
        self,
        perception: torch.Tensor,
        now: float | None = None,
    ) -> torch.Tensor:
        """perception_vector → memory_context。"""
        ...

    def write(
        self,
        request: MemoryWrite,
        query: torch.Tensor,
        observation: Observation,
        feedback: Feedback,
    ) -> MemoryItem | None:
        """写入一条记忆。返回落库的那条，被拒绝则 None。

        快环每帧都调它——**通道是否走过由模型决定，是否落库由记忆系统
        决定**。二者分离是有意的：通道门控是模型的意图，落库判据是记忆
        系统的策略（容量、合并、可写性），后者才是"记住了什么"的权威。
        """
        ...

    def use_context(self, context: FastLoopContext) -> None:
        """换快照后重读检索策略。无状态实现留空操作即可。"""
        ...


class ZeroMemoryRetriever:
    """无记忆检索器：恒返回零向量。**消融对照用**，不是默认值。

    Milestone 2 时它是默认值——那时记忆系统未实现，``m_t`` 必须是诚实的空，
    而不是一个看起来有内容的假值。Milestone 3 起默认值换成 MemorySystem，
    本类保留为对照组："把记忆关掉，行为差多少"是可消融检验的一格
    （docs/09 第 4 节）。

    做成显式类而不是 ``lambda: torch.zeros(16)``，是为了让"当前没有记忆"
    这件事在调用栈里可见——一个 lambda 会把边界藏起来。

    ``now`` 只为与 MemorySystem 同签名；零检索器没有时间概念。

    ``write`` 同样丢弃：这一侧关掉的是**整条记忆通路**，不只是读取。
    只关读取会留下"写了但读不到"的半残状态，那是另一个（更无聊的）对照。
    """

    def __init__(self, dim: int = 16) -> None:
        self.dim = dim

    def retrieve(
        self,
        perception: torch.Tensor,
        now: float | None = None,
    ) -> torch.Tensor:
        return torch.zeros(self.dim, dtype=torch.float32)

    def write(
        self,
        request: MemoryWrite,
        query: torch.Tensor,
        observation: Observation,
        feedback: Feedback,
    ) -> MemoryItem | None:
        """丢弃：无记忆检索器没有地方可写。"""
        return None

    def use_context(self, context: FastLoopContext) -> None:
        """空操作：零检索器没有策略可换。"""


# ----------------------------------------------------------------------
#  记录
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class StepRecord:
    """一帧的完整记录。慢环的输入（``trace``）就是它的列表。"""

    #: 快环自己的帧计数。与环境时间 ``observation.body`` 无关——
    #: 睡眠帧也计数，但不推进世界。
    frame: int
    state: str
    observation: Observation
    feedback: Feedback
    #: Action Decoder 的原产物。
    decoded_action: Action
    #: 本帧真正送进环境的动作（技能执行中为子动作）。
    executed_action: Action
    #: 本帧的技能事件；无则为 None。
    skill_event: str | None
    #: 本帧使用的结构快照指纹。行为改变的归因依据（08 §2.1）。
    context_fingerprint: tuple[tuple[str, int], ...]
    #: 睡眠 / 唤醒帧为 None——那两帧没有解码动作。
    intent: torch.Tensor | None = None

    @property
    def survived(self) -> bool:
        return self.feedback.survived


@dataclass
class FastLoopConfig:
    """快环配置。"""

    #: ``run()`` 的默认帧数上限。
    max_frames: int = 200
    #: 睡眠期最少帧数。
    min_sleep_frames: int = DEFAULT_MIN_SLEEP_FRAMES


# ----------------------------------------------------------------------
#  快环
# ----------------------------------------------------------------------


class FastLoop:
    """把各模块接成闭环，并驱动睡眠期状态机。

    用法::

        loop = FastLoop(env, context)
        for _ in range(100):
            rec = loop.step()
            if rec.state == STATE_DEAD:
                break
        trace = loop.trace()
    """

    def __init__(
        self,
        environment: Environment,
        context: FastLoopContext,
        perception_encoder: PerceptionEncoder | None = None,
        state_core: StateCore | None = None,
        skill_runner: SkillRunner | None = None,
        metabolic_monitor: MetabolicMonitor | None = None,
        memory_retriever: MemoryRetriever | None = None,
        action_decoder: ActionDecoder | None = None,
        config: FastLoopConfig | None = None,
        slow_loop: SlowLoopHook | None = None,
        on_death: DeathHook | None = None,
    ) -> None:
        self.config = config or FastLoopConfig()
        self.environment = environment
        self.context = context

        self.perception = perception_encoder or PerceptionEncoder()
        self.state_core = state_core or StateCore()
        self.metabolic = metabolic_monitor or MetabolicMonitor()
        self.skill_runner = skill_runner or SkillRunner(context)
        self.memory = memory_retriever or MemorySystem(
            MemoryConfig(memory_dim=self.state_core.config.memory_dim),
            context,
        )
        self.decoder = action_decoder or ActionDecoder()

        #: 慢环钩子。Milestone 2 无慢环，默认 None。
        self.slow_loop = slow_loop
        #: 死亡快照钩子（DEATH_SNAPSHOT）。
        self.on_death = on_death

        self.hidden: torch.Tensor = self.state_core.initial_hidden()
        self._state = STATE_RUN
        self._frame = 0
        self._sleep_frames_left = 0
        self._pending_context: FastLoopContext | None = None
        self._trace: list[StepRecord] = []

        self.observation: Observation = self.environment.reset()

    # ------------------------------------------------------------------
    #  状态
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def alive(self) -> bool:
        return self._state != STATE_DEAD

    def trace(self) -> tuple[StepRecord, ...]:
        """至今为止的全部帧记录。慢环的输入。"""

        return tuple(self._trace)

    # ------------------------------------------------------------------
    #  单帧
    # ------------------------------------------------------------------

    def step(self) -> StepRecord:
        """推进一帧，返回本帧记录。

        状态机在此推进：

        - ``RUN``：跑 08 §4.1 的公式，然后判睡眠
        - ``SLEEP``：调 ``environment.rest()``，最后一帧触发慢环
        - ``WAKE``：应用慢环产出的新快照，回 ``RUN``
        - ``DEAD``：抛异常（淘汰是终态）
        """

        if self._state == STATE_DEAD:
            raise RuntimeError(
                "快环已终结（环境判定死亡）。淘汰不可撤销；"
                "开始新 episode 请重新构造 FastLoop。"
            )
        if self._state == STATE_WAKE:
            return self._step_wake()
        if self._state == STATE_SLEEP:
            return self._step_sleep()
        return self._step_run()

    def run(self, n_frames: int | None = None) -> tuple[StepRecord, ...]:
        """连续跑若干帧，直到帧数用尽或死亡。返回本次新增的记录。"""

        n = self.config.max_frames if n_frames is None else n_frames
        start = len(self._trace)
        for _ in range(n):
            if self._state == STATE_DEAD:
                break
            self.step()
        return tuple(self._trace[start:])

    # ------------------------------------------------------------------
    #  RUN
    # ------------------------------------------------------------------

    def _step_run(self) -> StepRecord:
        obs = self.observation
        body = obs.body

        # ---- 08 §4.1 公式，逐行对应 ----
        p_t = self.perception(obs)
        m_t = self.memory.retrieve(p_t, now=obs.time)
        d_t = self.metabolic.drive_vector(body)

        hidden_new, intent = self.state_core(p_t, m_t, body, d_t, self.hidden)

        a_t = self.decoder(
            intent,
            body.action_constraints,
            d_t,
            self._candidates(obs),
            # 门控阈值来自结构快照。慢环改门控的唯一合法路径就是改这份快照
            # （提案 → 验证门 → Structure Store → WAKE 换版），参数侧没有
            # 可验证的落点，见 SSEA/plasticity.py 的 DEFERRED_SCOPES。
            dict(self.context.thresholds),
        )

        self.skill_runner.submit(a_t, body, obs)
        u_t = self.skill_runner.current_action(a_t)

        # 模型侧内部状态的对外镜像（07 §8.2）。必须在 step 之前回填，
        # 才会出现在本帧返回的 Observation 里。
        self.environment.set_internal_state(_summarize(hidden_new))

        obs_next, feedback = self.environment.step(u_t)

        # prediction_error 的生产者在这里，不在 Environment（08 §2.6.1）。
        # 必须在 step 之后——它比较的是上一帧留下的预测与本帧的实际。
        prediction_error = self.metabolic.observe(obs_next)
        feedback = replace(feedback, prediction_error=prediction_error)

        # 记忆写入：Action.memory 通道的消费者是 Memory System（action.py
        # 的通道表），不是 Environment。环境只把这次请求记进观测流
        # （memory_requests / MEMORY_STORED 事件），是否真的存入由
        # memory.stats.writes 与 memory.stats.refused 说话。
        #
        # 用 a_t 而非 u_t：技能执行中 u_t 是子动作，而"本帧想记一件事"是
        # 模型的意图，意图只存在于解码产物里。
        #
        # **不在这里补 MEMORY_STORED 事件**：Environment._apply_memory 已经
        # 发了。两个生产者发同一条事件类型、语义却不同（"请求已发出" vs
        # "已入库"）会让这条类型变含糊——而含糊的事件类型比没有更糟。
        # "真的写进去了几条"由 memory.stats.writes 说，不靠事件流。
        self.memory.write(a_t.memory, p_t, obs_next, feedback)

        # 检索命中同样留痕。判据是 m_t 非零——无命中时 retrieve() 返回零向量，
        # 与 ZeroMemoryRetriever 不可区分，"诚实的空"由此可检验。
        # 事件由环境记录但环境不据此改变世界：它是观察项，不是后果。
        if float(m_t.abs().sum()) > 0.0:
            self.environment.observe_model_event(
                "MEMORY_RETRIEVED", importance=0.3
            )

        skill_event = self.skill_runner.report(
            feedback.action_success, obs_next.body, obs_next
        )

        self.hidden = hidden_new
        self.observation = obs_next
        self._frame += 1

        record = self._record(
            STATE_RUN, obs_next, feedback, a_t, u_t, skill_event, intent
        )
        self._trace.append(record)

        if not feedback.survived:
            return self._enter_dead(record)

        # ---- 睡眠判定（08 §2.2）：入口必须窄，两条同时满足 ----
        # 08 §2.2 原本还有第三条 energy ≥ 0.7，2026-09-27 移除——它与疲劳判据
        # 算术互斥，使这里恒不成立。推导见 metabolic_monitor.wants_sleep。
        if self.metabolic.wants_sleep(obs_next.body, obs_next):
            self._state = STATE_SLEEP
            self._sleep_frames_left = max(1, self.config.min_sleep_frames)
        return record

    # ------------------------------------------------------------------
    #  SLEEP / WAKE
    # ------------------------------------------------------------------

    def _step_sleep(self) -> StepRecord:
        """睡眠期一帧：只恢复，不动作。

        最后一帧触发慢环（SLEEP→SEL）。调用点放在这里而不是 ``WAKE``，
        是为了让"睡"与"整理"在时间上分开：睡眠帧负责身体恢复，慢环负责
        结构更新，两者不互相等待。
        """

        obs_next, feedback = self.environment.rest(0.0)
        self.observation = obs_next
        self._frame += 1
        self._sleep_frames_left -= 1

        record = self._record(
            STATE_SLEEP,
            obs_next,
            feedback,
            idle_action(),
            idle_action(),
            None,
            None,
        )
        self._trace.append(record)

        if not feedback.survived:
            return self._enter_dead(record)

        if self._sleep_frames_left <= 0:
            if self.slow_loop is not None:
                self._pending_context = self.slow_loop(self.trace())
            self._state = STATE_WAKE
        return record

    def _step_wake(self) -> StepRecord:
        """应用慢环产出的新快照，回 RUN。

        慢环返回 None（未提交新结构）时保持旧快照——这正是 08 §2.1 的
        "失败天然回滚"：版本号没切换，快照就没变，不存在回滚操作。
        """

        if self._pending_context is not None:
            self.context = self._pending_context
            self.skill_runner = SkillRunner(self.context)
            # 记忆不随版本切换重置——它不在快照里（C3 三分离）。
            # 这里只把新快照的 retrieval 策略接过来。
            self.memory.use_context(self.context)
            self._pending_context = None

        self._state = STATE_RUN
        self._frame += 1
        record = self._record(
            STATE_WAKE,
            self.observation,
            _empty_feedback(),
            idle_action(),
            idle_action(),
            None,
            None,
        )
        self._trace.append(record)
        return record

    def _enter_dead(self, record: StepRecord) -> StepRecord:
        """标记终结帧并触发死亡快照钩子。

        记录的状态改成 ``STATE_DEAD``：trace 里必须能看出**哪一帧**是
        终帧，否则慢环做 DEATH_SNAPSHOT 时无从判断该编译到哪儿为止。
        """

        self._state = STATE_DEAD
        terminal = replace(record, state=STATE_DEAD)
        self._trace[-1] = terminal
        if self.on_death is not None:
            self.on_death(self.trace(), self.observation)
        return terminal

    # ------------------------------------------------------------------
    #  辅助
    # ------------------------------------------------------------------

    def _candidates(self, obs: Observation) -> DecodeCandidates:
        """离散候选集合。**从真实存在的东西里取**，不让解码器自由生成。

        对象 id 来自视野内对象；技能 id 来自当前快照；提案类型来自协议
        白名单。三者都是有限集合，解码器只能 argmax——否则它会产出环境中
        不存在的 object_id，而这类错误要到 Environment 才被发现。
        """

        return DecodeCandidates(
            object_ids=tuple(obj.object_id for obj in obs.objects),
            skill_ids=tuple(self.context.skills.keys()),
            proposal_types=ALLOWED_PROPOSAL_TYPES,
        )

    def _record(
        self,
        state: str,
        observation: Observation,
        feedback: Feedback,
        decoded_action: Action,
        executed_action: Action,
        skill_event: str | None,
        intent: torch.Tensor | None,
    ) -> StepRecord:
        return StepRecord(
            frame=self._frame,
            state=state,
            observation=observation,
            feedback=feedback,
            decoded_action=decoded_action,
            executed_action=executed_action,
            skill_event=skill_event,
            context_fingerprint=self.context.fingerprint(),
            intent=intent,
        )


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def _summarize(hidden: torch.Tensor, size: int = 4) -> tuple[float, ...]:
    """hidden_state → 定长摘要，作为 BodyState.internal_state 镜像。

    取前 ``size`` 维。刻意不取均值 / 范数——那些量丢失了"哪一维在动"的
    信息，而 internal_state 的用途正是让观察员判断"内部状态变了吗"。
    """

    flat = hidden.reshape(-1)
    return tuple(round(float(v), 6) for v in flat[:size])


def _empty_feedback() -> Feedback:
    """WAKE 帧没有环境交互，feedback 是全零占位。"""

    return Feedback(
        energy_change=0.0,
        damage_change=0.0,
        fatigue_change=0.0,
        prediction_error=0.0,
        action_success=True,
        survived=True,
        notes="wake",
    )
