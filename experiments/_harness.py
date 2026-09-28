"""实验脚手架：跑一轮快环，把它身上的量收成数字。

设计上有三条刻意的选择：

**一、量从 trace、累计计数器与审计日志取，不从环形缓冲取。**
``Environment.event_log()`` / ``event_notes()`` 是 16 槽环形缓冲（12 §6 债务 10），
"跑完再遍历事件流"会**静默漏掉早期事件**——本次核对时它真的咬过一次：
「跑完统计 ``ENERGY_GAINED``」得到 0 次，而逐帧追踪显示第 10 帧确实
``grasp: +0.356 energy``。所以本模块的累计量逐帧现加，
或者读 ``StructureStore.audit_log()``（append-only，不丢），
或者读 ``Environment.event_counts()``（**只增不减、不截断**，2026-09-27 加入，
正是为了补这个洞）。

但注意 ``event_counts()`` 与逐帧求和**不是一回事**，两者不可互换：

- 它按**事件类型**分解，所以回答得了"这轮 grasp 成功了几次"；
  但它**没有 source_id 维度**，所以回答不了"接触了几次危险源"——
  ``OBJECT_FOUND`` 对资源与危险源一视同仁。
- 它数的是**事件**，不是**能量**：一次抓取会发 ``ENERGY_GAINED``，
  但同一帧的 ``Feedback.energy_change`` 完全可能是负的（还扣着基础代谢
  与动作消耗），而 ``push`` / ``pull`` / 基础代谢的耗能**根本不发事件**。
  要能量收支就用 trace 上的 ``Feedback``。

**一之二、能量口径：三条约定写死在这里，别在各脚本里各定一套。**

1. **分母是 RUN 帧数**，不是 ``len(trace)``。睡眠帧每帧**涨** 0.01 能量
   （``environment.py`` 的 ``rest``），WAKE 帧经 ``_empty_feedback()`` 塞一个
   **合成 0**。用总帧数归一化会让"睡得多的回合"显得**更省**——
   和上面 ``action_legality_rate`` 同一个陷阱。
2. **``energy_spent`` 是毛支出**（负增量取绝对值求和），睡眠期的恢复**不抵消**它。
   净额另给（``net_energy_change``）。两者差别很大：睡眠占寿命一大半。
3. **取的是夹取后的"实现增量"，不是"请求增量"。** ``Feedback.energy_change``
   是 ``round(self.energy - energy_before, 6)``，即夹取之后的差。能量满 1.0 时
   抓资源，它是 0.0——这是**对的**：上限 1.0 是刻意强加的策略压力
   （"吃饱了就不能再存"），用资源标称价值求和会把这份浪费藏起来。

   由此有一条**已知偏低、不是 bug**：能量 6 处 ``max(0.0, ...)`` 与 damage 的
   ``min(max_damage, ...)`` 都在**丢弃超调**，而死亡帧恰恰是消耗峰值帧。
   报告里要注明，不要当成测量误差去"修"。

**一之三、求和要有容差。** ``round(..., 6)`` 累积几百帧后与
``final − initial`` 差约 1e-4，"精确守恒"这个断言拿不到，用 ``pytest.approx``。

**一之四、两个曾经只有名字的算式，定义在这里。**

12 §4.2 与 14 §5.2 的表格里有两个指标名长期**只有名字**——没有公式、
没有分母、没有窗口（14 §6.3.4）。定义补在这里，各自只有一个实现：

- **危险回避率**（实验 2）= ``EpisodeResult.hazard_avoidance_rate``。
  分母是**视野内存在危险源的 RUN 帧数**（该帧 ``observation`` 里有
  ``threat_level > 0`` 的对象），分子是其中**真的受了危险源损伤**的帧数
  （该帧 ``Feedback.damage_change > 0``；``environment.py`` 里
  ``self.damage`` 只在 ``_apply_hazard_contact`` 一处增加，所以这个等价是准的）。

  两条刻意的选择：

  1. **分母为 0 时返回 ``None``，不返回 1.0。** "0/0 写成 100%" 是这个项目
     反复出现的失败形状（实验 6/7 的四个 ``1.0000`` 里有两个分母来自注入样本，
     自然运行下分母是 0）。**造分母是实验脚本的责任**，不是这个属性的。
  2. **不从事件流数分子。** ``DAMAGE_RECEIVED`` 在 16 槽环形缓冲里会静默漏
     （债务 10），而漏的方向偏向零——正好把"躲开了"读成"没躲开"。
     ``source_id`` 只作交叉校验用。

  副指标 ``mean_nearest_hazard_distance`` 是**连续量**，比二值率灵敏：
  分母同样是"危险源可见的 RUN 帧"。

- **能量消耗变化**（实验 3）= 两个 :func:`energy_by_version_window` 窗口的
  ``energy_spent_per_run_frame`` 之差（固化后 − 固化前）。
  它**不是一个新算式**，就是那个已有函数在版本窗口上的差分——
  所以这里不给它第二个实现，只给用法：``energy_change_between_windows()``。
  不切版本的话，固化**前**的消耗会永远留在分子里，"固化有没有降低消耗"
  这个问题会被历史数据稀释掉（理由与 ``_current_window`` 相同）。

**二、每个数字都必须能被人复跑。**
``run_episode`` 的种子与帧数是显式参数，且 ``torch.manual_seed`` 在
**构造任何对象之前**调用——记忆门控与操纵门控的开启与否由随机初始化决定
（12 §4.3），种子的位置换一下就是另一场抽奖。

**三、脚本输出是给人看的。**
不打印 tensor，不打印中间态，只打印能写进 12 §4.2 表格的那几行。
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import torch

from SSEA.environment import Environment
from SSEA.experience_compiler import make_slow_loop_hook
from SSEA.fast_loop import STATE_RUN, STATE_SLEEP, STATE_WAKE, FastLoop, FastLoopConfig
from SSEA.plasticity import LocalPlasticity
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate

#: 实验默认用的随机种子集。八个足够看出「一半 seed 门不开」这类双峰现象。
DEFAULT_SEEDS: tuple[int, ...] = tuple(range(8))

#: 实验默认**上限**帧数。够跑到默认世界里的自然死亡（60–90 帧），留一倍余量。
#:
#: ⚠️ **它是上限，不是分母。** 2026-09-29 实测：8/8 个 seed 全部在 **66–182** 帧死亡，
#: **0/8** 活到 200；真实分母是**死亡帧**。所有派生量的分母都取自 ``len(trace)``，
#: 但这个上限**从未被任何一张表印出来**——于是「× 200 帧上限」会被读成「跑了 200 帧」。
#: 报告层因此补了 :func:`survival_summary`（见 docs/06 §4 债务 31）。
DEFAULT_FRAMES = 200


@dataclass(frozen=True)
class FrameAction:
    """一帧**解码后**动作的最小指纹——够算两臂的逐帧差，又不留整条 trace。

    只留 ``locomotion`` 三个数。记忆的作用路径是
    ``m_t → StateCore 隐状态 → ActionDecoder``，落点就在这三个数上。

    **刻意不留 ``executed_action``**：那一层还叠了技能重放与约束执行点，
    是实验 3 的主题。混进来会把两条机制的作用搅在一起，而实验 2 的
    自变量只有记忆（见 ``exp2_memory_recall`` 的模块 docstring）。

    方向向量的维数**不写死**：协议里 ``Locomotion.direction`` 是
    ``tuple[float, ...]``，最小动作那条用的是 2 维。
    """

    direction: tuple[float, ...]
    speed: float
    duration: float

    @classmethod
    def of(cls, action: Any) -> "FrameAction":
        loco = action.locomotion
        return cls(
            direction=tuple(float(x) for x in loco.direction),
            speed=float(loco.speed),
            duration=float(loco.duration),
        )


@dataclass
class EpisodeResult:
    """一轮 episode 的原始量。派生指标做成属性，避免两处各算一遍。"""

    seed: int
    frames: int
    alive: bool
    run_frames: int
    sleep_frames: int
    wake_frames: int
    constraint_rejected: int
    internal_errors: int
    max_consecutive_run: int
    language_crossings: int
    observation_leaks: int
    proposals: int
    applied: int
    rejected: int
    #: 睡眠**段数**（极大连续 SLEEP 段），不是睡眠帧数。
    #: 实验 7 的「慢环触发成功率」分母是它：一次睡眠应当正好触发一次慢环。
    sleep_episodes: int = 0
    #: 慢环钩子被真正调用的次数。与 ``sleep_episodes`` 之差就是漏触发。
    slow_loop_calls: int = 0
    rejected_kinds: tuple[str, ...] = ()
    version_bumps: int = 0
    audited_bumps: int = 0
    #: 逐帧 ``Feedback.energy_change`` 的**正部**之和（夹取后的实现增量）。
    energy_gained: float = 0.0
    #: 逐帧 ``Feedback.energy_change`` 的**负部绝对值**之和——毛支出，睡眠恢复不抵消。
    energy_spent: float = 0.0
    #: 逐帧 ``Feedback.damage_change`` 的正部之和。
    damage_taken: float = 0.0
    #: 环境的按类型累计计数快照（``Environment.event_counts()``）。
    #: **只在尾部取一次**——它本身不截断，所以不需要逐帧加。
    event_totals: dict[str, int] = field(default_factory=dict)
    # ---- 危险暴露的三个原始计数（危险回避率的分母/分子/副指标，见 docstring 一之四）----
    #: 视野内存在危险源（``threat_level > 0``）的 RUN 帧数。**这就是分母。**
    hazard_visible_frames: int = 0
    #: 上述帧中 ``Feedback.damage_change > 0`` 的帧数。**这就是分子。**
    hazard_contact_frames: int = 0
    #: 危险源可见帧上「最近危险源距离」之和（除以 ``hazard_visible_frames`` 得副指标）。
    nearest_hazard_distance_sum: float = 0.0
    # ---- 资源侧（与危险侧对称）——
    #: 视野内存在资源（``resource_value > 0``）的 RUN 帧数。
    resource_visible_frames: int = 0
    #: 资源可见帧上「最近资源距离」之和。**「趋近」这个动作就是靠它看出来的**：
    #: ``ENERGY_GAINED`` 为 0 既可能是"没靠近"，也可能是"靠近了但抓取链没通"，
    #: 只有这条连续量能分开这两种完全不同的结论。
    nearest_resource_distance_sum: float = 0.0
    # ---- ② 的验收判据（不是存活帧数）----
    #: 最长的一段连续「直接成功」帧（判据见 ``success_run_lengths``）。
    #: 编译器要 ``min_frames=3``，所以这个数 < 3 就意味着**一条技能也编译不出来**。
    max_success_run: int = 0
    #: ``compile_skills(trace)`` 的产出条数——用真编译器量的可编译段数。
    compileable_segments: int = 0
    # ---- 记忆侧（实验 2）----
    #: 模型**请求**写入记忆的帧数（``Environment.memory_requests``）。
    #: 它是「记忆门开了几次」，与「写进去了几条」是两件事（见下表）。
    memory_write_requests: int = 0
    #: ``MemorySystem.stats.as_dict()`` 的快照。**没有仪器的检索器
    #: （``ZeroMemoryRetriever``）留空字典**——空字典不等于「全是 0」，
    #: 这正是两条通路要分开的地方，见 :attr:`memory_instrumented`。
    memory_stats: dict[str, int] = field(default_factory=dict)
    # ---- 技能侧（实验 3）----
    #: 模型**请求**调用技能的帧数（``decoded_action.skill is not None``）。
    #: 「没调用过」与「调用了但全失败」在成功率上都是 0，靠它分开。
    skill_calls: int = 0
    #: 技能运行器报出的 ``SKILL_SUCCESS`` / ``SKILL_FAILURE`` 次数。
    #:
    #: **取自 ``StepRecord.skill_event``，不是 ``Environment.event_counts()``。**
    #: 后者对这两个类型**恒为 0**——它们在 ``EVENT_TYPES`` 里，但**没有生产者**
    #: （``tests/test_environment.py::test_event_counts_name_the_producerless_types``
    #: 钉着这一条）。``SkillRunner.report()`` 返回的正是这两个字符串，所以
    #: 从事件计数器读会得到"一次都没调用过"，而真相可能在调用（还会失败）。
    skill_successes: int = 0
    skill_failures: int = 0
    # ---- 动作侧的分母（债务 30 的兄弟；2026-09-29 补）----
    #: RUN 帧里动作成功 / 失败的帧数。**「动作全失败」这一档需要它才可归因**：
    #: 只看 `ACTION_FAILED` 计数看不出它占 RUN 帧的多大比例。
    #: 实测 3/8 个 seed 的 RUN 成功率是 **0**——它们靠睡眠活着。
    run_success_frames: int = 0
    run_failed_frames: int = 0
    #: **被真正调用过**至少一次的技能 id（去重、排序）。
    #:
    #: 它是技能固化漏斗第三档 ``reused`` 的分子：**不同技能的个数**，不是调用
    #: 次数。调用次数已经在 ``skill_calls`` / ``skill_events`` 上；把两者混起来，
    #: 正是「0/33」会同时被读成「没有技能被复用」与「调用全部失败」的原因。
    #: 取自 ``SkillRunner.invoked_skill_ids()``——只有 ``submit`` 不算，
    #: precondition 可能在 submit 时就把它挡回去，那是「想调用」不是「调用到」。
    invoked_skills: tuple[str, ...] = ()
    #: 版本窗口的段数（``energy_by_version_window``）。它是
    #: :attr:`energy_change` 的分母来源——少于 2 段就没有第二个观测点。
    energy_windows: int = 0
    #: **实验 3 的「能量消耗变化」**：末窗口 − 首窗口的每 RUN 帧支出。
    #: ``None`` = trace 里没发生过版本切换。
    energy_change: float | None = None
    #: 逐帧**解码后**动作指纹。它是实验 2 **第三档**判据的分母来源
    #: （:func:`action_divergence`）——比 ``coarse_signature`` 的 5 个整数
    #: 灵敏得多，理由见那个函数。
    #:
    #: **取自主环 trace，所以 Gate 沙箱的重放天然不在里面。**
    #: 2026-09-28 的探针把 ``FastLoop.step`` 打在类上，沙箱环混了进来、
    #: 两个列表还错位了；在这里量在构造上就没有这个洞。
    action_trace: tuple[FrameAction, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    # ---- 派生指标（12 §4.2 表格里的那几列）----

    @property
    def run_action_success_rate(self) -> float | None:
        """RUN 帧的动作成功率。**分母为 0 → `None`，不是 `0.0`。**

        「一帧 RUN 都没跑过」与「跑了但一次没成功」是两件事，在 `0.0` 上长得一样。
        2026-09-29 实测：8 个 seed 里有 **3 个**是 0——它们靠睡眠活着。
        """

        total = self.run_success_frames + self.run_failed_frames
        if total == 0:
            return None
        return self.run_success_frames / total

    @property
    def action_legality_rate(self) -> float:
        """动作合法率 = 1 − 被约束执行点拒掉的帧数 / RUN 帧数。

        注意分母是 RUN 帧：睡眠帧不产生动作，把它算进分母会凭空拉高合法率。
        """
        if self.run_frames == 0:
            return 0.0
        return 1.0 - self.constraint_rejected / self.run_frames

    @property
    def interface_error_rate(self) -> float:
        """接口异常率 = 触发内部兜底的帧数 / 总帧数。

        这一列**应当恒为 0**——环境把任何未预期异常转成
        ``action_success=False`` + ACTION_FAILED，不崩溃（08 §2.6.2）。
        """
        if self.frames == 0:
            return 0.0
        return self.internal_errors / self.frames

    @property
    def sleep_entry(self) -> bool:
        return self.sleep_frames > 0

    @property
    def audit_completeness(self) -> float:
        """版本切换审计记录完整率 = 有审计记录的升版次数 / 总升版次数。"""
        if self.version_bumps == 0:
            return 1.0  # 没升过版，"每次都记了"空真
        return self.audited_bumps / self.version_bumps

    @property
    def net_energy_change(self) -> float:
        """净能量变化 = 正部 − 负部。

        与 ``energy_gained - energy_spent`` 恒等（就这么定义的），
        单独给个名字是为了让"用净额还是毛额"在调用处**看得见**——
        睡眠期的恢复会抵消运行期的消耗，两个数差别很大。
        """
        return self.energy_gained - self.energy_spent

    @property
    def energy_spent_per_run_frame(self) -> float:
        """每 RUN 帧的能量支出。**实验 3 的「能量消耗变化」应当用这个口径。**

        分母是 RUN 帧数而非 ``len(trace)``：睡眠帧每帧涨 0.01 能量，
        用它当分母会让睡得多的回合显得更省。理由见模块 docstring 一之二。
        """
        if self.run_frames == 0:
            return 0.0
        return self.energy_spent / self.run_frames

    @property
    def hazard_avoidance_rate(self) -> float | None:
        """危险回避率 = 1 − 受危险源损伤的帧数 / 危险源可见的帧数。

        **分母为 0 时返回 ``None``，不返回 1.0。** 没有危险源可见的那些回合
        不是"完美回避"，是**没东西可回避**——把它算成 1.0 会让
        "世界里没有危险源"伪装成"躲得极好"。这是实验 6/7 已经咬过一次的形状
        （``1.0000`` 的分母来自注入样本）。理由与分子口径见 docstring 一之四。
        """
        if self.hazard_visible_frames == 0:
            return None
        return 1.0 - self.hazard_contact_frames / self.hazard_visible_frames

    @property
    def mean_nearest_hazard_distance(self) -> float | None:
        """危险源可见帧上「最近危险源距离」的均值。分母同上，无可见帧时为 ``None``。

        比二值率灵敏：回避率只能在"接触/不接触"上动，距离能看出**趋势**。
        """
        if self.hazard_visible_frames == 0:
            return None
        return self.nearest_hazard_distance_sum / self.hazard_visible_frames

    @property
    def mean_nearest_resource_distance(self) -> float | None:
        """资源可见帧上的最近资源距离均值。**「趋近」的直接读数。**

        无定义时返回 ``None``（一帧都没看见资源）——理由同
        ``hazard_avoidance_rate``：0/0 写成 0.0 会被读成"贴着资源"。
        """
        if self.resource_visible_frames == 0:
            return None
        return self.nearest_resource_distance_sum / self.resource_visible_frames

    # ---- 记忆侧（实验 2）----

    @property
    def memory_instrumented(self) -> bool:
        """这一轮挂的是**有仪器的**检索器吗（``MemorySystem`` 而非零检索器）。

        判据是 ``memory_stats`` 非空，不是"写入数为 0"。``MemorySystem`` 的
        ``as_dict()`` 恒有十个键（哪怕是全 0），零检索器没有 ``stats`` 属性。
        **这个区分是实验 2 的全部要害**：一行 ``writes = 0`` 在两个来源下
        长得一模一样，而它们指向完全相反的结论——
        「记忆关着」（对照组）与「记忆开着但一次都没触发」。
        """
        return bool(self.memory_stats)

    @property
    def memory_writes(self) -> int | None:
        """真的落库的记忆条数。没有仪器时为 ``None``。"""
        if not self.memory_instrumented:
            return None
        return int(self.memory_stats.get("writes", 0))

    @property
    def memory_write_success_rate(self) -> float | None:
        """记忆写入成功率 = 落库条数 / 模型请求写入的帧数。

        **分母是"请求数"不是"帧数"。** 用帧数当分母会把这个指标变成
        "模型有多爱记东西"，而它要回答的是"想记的东西记下来了没有"。
        ``environment.memory_requests`` 是全量 append 的列表（不是 16 槽
        环形缓冲），所以这个分母不会静默漏。

        分母为 0 → ``None``：一次都没请求过时，成功率无定义。
        **这一条尤其要紧**——记忆门控是未训练的（12 §6 债务 5），
        所以"一次都没请求"完全可能发生，而 0/0 写成 1.0 会把它读成
        "写入机制很可靠"。
        """
        if not self.memory_instrumented or self.memory_write_requests == 0:
            return None
        writes = self.memory_writes or 0
        return writes / self.memory_write_requests

    @property
    def memory_hit_rate(self) -> float | None:
        """记忆检索命中率 = 有命中的检索次数 / 真的做了检索的次数。

        分母不是 ``frames``：``retrieve()`` 受检索策略的 ``stride`` 过滤，
        低频检索时两者差很远（``MemoryStats.frames`` vs ``.retrievals``
        就是为这个分开放的）。分母为 0 → ``None``。
        """
        if not self.memory_instrumented:
            return None
        retrievals = int(self.memory_stats.get("retrievals", 0))
        if retrievals == 0:
            return None
        return int(self.memory_stats.get("hits", 0)) / retrievals

    # ---- 技能侧（实验 3）----

    @property
    def skill_events(self) -> int:
        """技能运行器报出的事件总数——**调用成功率的分母**。"""
        return self.skill_successes + self.skill_failures

    @property
    def skill_call_success_rate(self) -> float | None:
        """技能调用成功率 = 成功次数 / (成功 + 失败)。

        分母是**运行器报出的事件数**，不是"调用了的帧数"：一次调用可以跨
        好几帧，按帧算会把长技能的成功率稀释掉。

        分母为 0 → ``None``，并且要**分清是哪一种 0**：
        ``skill_calls == 0`` 是"模型从没请求过"（技能库可能是空的，也可能是
        有技能但门不开）；``skill_calls > 0`` 而事件为 0 是"请求了但运行器
        一个事件都没报"——后者是缺陷，不是结论。
        """
        events = self.skill_events
        if events == 0:
            return None
        return self.skill_successes / events


@dataclass(frozen=True)
class SurvivalSummary:
    """存活读数的**唯一一份口径**（docs/06 §4 债务 31）。

    **为什么它是一等公民**：C9 把「淘汰」判给环境，而「活了多少帧」就是**淘汰函数的
    直接输出**——它因此是本项目**唯一一条模型碰不到的读数**。

    而 2026-09-29 实测：8/8 个 seed 全部在 **66–182** 帧死亡（中位 122.5），**0/8**
    活到 200 帧上限。可七条实验都在报机制计数，**没有任何一张表把「死亡」印出来**。

    **为什么要有它、而不是各实验各写一遍**：措辞会漂；漂了之后「上限 200」与
    「实测存活 122.5」就会再次被读成同一件事——那正是它要防的误读。
    """

    n: int
    died: int
    median_frames: float | None
    low: int | None
    high: int | None
    at_cap: int

    def headline(self, cap: int) -> str:
        """一行话，**把上限与实测分开放**——它们不是一回事。"""

        if self.median_frames is None:
            return f"帧上限 {cap}（一轮都没跑起来）"
        return (
            f"帧上限 {cap}，实测存活 {self.low}–{self.high}"
            f"（中位 {self.median_frames:g}），{self.n - self.at_cap}/{self.n} 未活到上限"
        )

    def rows(self) -> tuple[tuple[str, object], ...]:
        """放进验收指标表**最前面**——它是环境那一侧的判据。"""

        if self.median_frames is None:
            return (("存活帧（淘汰函数输出；模型不可见）", "无"),)
        return (
            (
                "存活帧（淘汰函数输出；模型不可见）",
                f"中位 {self.median_frames:g} · 范围 {self.low}–{self.high} · n={self.n}",
            ),
            ("死亡 / 活到上限的 seed 数", f"{self.died}/{self.n} · {self.at_cap}/{self.n}"),
        )


def survival_summary(
    results: Sequence[EpisodeResult], cap: int
) -> SurvivalSummary:
    """逐 seed 的**实际**存活帧（``r.frames`` = ``len(trace)``），**不是**那个上限。

    ``cap`` 只用来算「有几个活到了上限」；它**不参与任何分母**。
    """

    frames = [r.frames for r in results]
    if not frames:
        return SurvivalSummary(0, 0, None, None, None, 0)
    return SurvivalSummary(
        n=len(results),
        died=sum(1 for r in results if not r.alive),
        median_frames=statistics.median(frames),
        low=min(frames),
        high=max(frames),
        at_cap=sum(1 for r in results if r.frames >= cap),
    )


def build_slow_loop(
    store: StructureStore,
    *,
    env_frames: int = 8,
    plasticity: bool = True,
) -> Callable[[Sequence[Any]], Any]:
    """标准的慢环钩子：ExperienceCompiler → VerificationGate → StructureStore。"""
    return make_slow_loop_hook(
        store,
        VerificationGate(GateConfig(env_frames=env_frames)),
        plasticity=LocalPlasticity() if plasticity else None,
    )


class BudgetMatchedRetriever:
    """**预算匹配臂**：记忆系统照跑，但注入的向量被抹掉。

    `HarnessEval`（arXiv:2607.12227）的「预算匹配基线」在 SSEA 的对应物。
    处理臂相对对照臂**多花的那部分算力**必须被单独控制住，否则「增益」可能
    只是「多跑了一件事」。这里多跑的正是「记忆系统走一遍」：写入、检索、
    命中计数、`last_retrieved` 回写**全部照旧发生**，只有 `m_t` 换成零向量。

    于是两臂的差别**只剩「记忆有没有影响决策」**。

    包装的是 `FastLoop` **已经构造好的那个实例**（`run_episode` 在构造之后替换
    `loop.memory`），所以「默认到底长什么样」仍然只有一处定义——实验里另写
    一份构造就是分叉，而分叉的表现是「两臂在默认值上不一致」，读数里看不见。
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner

    @property
    def dim(self) -> int:
        return int(getattr(self.inner, "dim", 16))

    @property
    def stats(self) -> dict:
        """**保留**：记忆系统确实跑过，所以这一臂**有仪器**。

        把它抹成空字典会让人把「预算匹配臂」读成「记忆关臂」，而两者要问的
        是完全不同的问题。
        """

        return getattr(self.inner, "stats", {})

    def retrieve(self, perception: Any, now: float | None = None) -> Any:
        self.inner.retrieve(perception, now)  # 真算：检索、命中计数、回写
        return torch.zeros(self.dim, dtype=torch.float32)

    def write(self, request: Any, query: Any, observation: Any, feedback: Any) -> Any:
        return self.inner.write(request, query, observation, feedback)

    def use_context(self, context: Any) -> None:
        return self.inner.use_context(context)

    def __len__(self) -> int:
        return len(self.inner)


def build_budget_matched_slow_loop(
    *,
    throwaway: StructureStore,
    **kwargs: Any,
) -> Callable[[Sequence[Any]], Any]:
    """预算匹配臂的慢环：**照跑**，但产物不发布。

    区分两件事：

    - 「**结构进入快环**」有没有用（处理臂 vs 本臂）；
    - 「**慢环跑过一遍**」有没有用（本臂 vs 对照臂）。

    只做「机制开 / 机制关」的消融时这两件事被绑在一起，读数分不开。

    ⚠️ **发布通道是返回值，不是 store。** 第一版实现只是把真正的慢环绑到另一个
    store（弃置场）上就交了差，实测发现它**什么都没改变**——`FastLoop._step_wake`
    在慢环返回非 None 时会把**返回值**当成新快照换进去
    （`self.context = self._pending_context`，并顺手重建 `skill_runner`）。
    于是弃置场那一版跑出了与处理臂**逐位相同**的 33 次调用与同一个能量值，
    看上去像一条重大发现，实际是这一臂根本没被改动。

    正确做法是**照跑但返回 None**：编译、门控、提交到弃置场全都发生，
    而快环拿不到新快照，结构永远进不去。

    这是一条通用教训：**「把某个东西换掉」不等于「切断它」**——
    切断要看清楚它实际是从哪条路过去的。
    """

    inner = build_slow_loop(throwaway, **kwargs)

    def budget_matched(trace: Sequence[Any]) -> None:
        inner(trace)  # 照跑：编译 · 门控 · 提交到弃置场
        return None  # **不发布**：返回 None，快环保持旧快照

    return budget_matched


def run_episode(
    seed: int,
    *,
    frames: int = DEFAULT_FRAMES,
    min_sleep_frames: int = 5,
    monitor: Any | None = None,
    store: StructureStore | None = None,
    slow_loop: Callable[[Sequence[Any]], Any] | None = None,
    watch_language: bool = False,
    memory_retriever: Any | None = None,
    memory_budget_matched: bool = False,
) -> EpisodeResult:
    """跑一轮，把量收齐。

    ``watch_language=True`` 时逐帧检查有无 ``str`` 值跨越控制边界。
    这是实验 1 的第四个指标，也是**唯一一个只能运行时测的**——
    静态字段检查已由 ``tests/test_protocol_consistency.py`` 守着，
    但"字段里没有 str"不等于"运行时没有 str 流过去"。

    ``memory_retriever=None`` 用 ``FastLoop`` 的默认值（``MemorySystem``）。
    传 ``ZeroMemoryRetriever()`` 就是实验 2 的对照组。**这个参数不设默认值
    之外的任何开关语义**——"记忆关掉"不是本模块的一个布尔量，是一个显式的
    检索器实现，理由见 ``fast_loop.ZeroMemoryRetriever`` 的 docstring。
    """

    # 必须在构造任何对象之前——门控开不开由这里的种子决定（12 §4.3）。
    torch.manual_seed(seed)

    store = store if store is not None else StructureStore()
    if slow_loop is None:
        slow_loop = build_slow_loop(store)

    # 包一层数调用次数。快环在睡眠末尾调它一次，所以"调用次数"就是
    # 「慢环真的被触发了几次」——比从版本号倒推可靠：慢环被触发但
    # 一条提案都没提时，版本号不动。
    calls = 0

    def counted_slow_loop(trace):
        nonlocal calls
        calls += 1
        return slow_loop(trace)

    loop = FastLoop(
        Environment(seed=seed),
        _context(store),
        metabolic_monitor=monitor,
        memory_retriever=memory_retriever,
        config=FastLoopConfig(max_frames=frames, min_sleep_frames=min_sleep_frames),
        slow_loop=counted_slow_loop,
    )

    # 预算匹配：在构造**之后**替换，包的是 FastLoop 自己造的那个实例。
    # 这样「默认记忆系统长什么样」仍然只有一处定义（非分叉），而多花的算力
    # 被单独控制住。放在这里而不是构造参数里，是因为构造参数会逼实验自己
    # 新建一个「默认」，那正是分叉。
    if memory_budget_matched:
        loop.memory = BudgetMatchedRetriever(loop.memory)

    rejected_total = 0
    internal_total = 0
    language_crossings = 0
    observation_leaks = 0
    run_success_frames = 0
    run_failed_frames = 0
    energy_gained = 0.0
    energy_spent = 0.0
    damage_taken = 0.0

    while loop.alive and len(loop.trace()) < frames:
        if watch_language:
            # 决策边界：进入解码器之前的隐藏状态。
            language_crossings += count_strs_deep(loop.hidden)
        loop.step()
        record = loop.trace()[-1]

        if record.feedback is not None:
            if record.state == STATE_RUN:
                if record.feedback.action_success:
                    run_success_frames += 1
                else:
                    run_failed_frames += 1
            rejected_total += record.feedback.notes.count("constraint_rejected:")
            internal_total += record.feedback.notes.count("internal_error:")
            # 逐帧现加，不从事件流取——口径见模块 docstring 一之一。
            change = record.feedback.energy_change
            energy_gained += max(0.0, change)
            energy_spent += max(0.0, -change)
            damage_taken += max(0.0, record.feedback.damage_change)

        if watch_language:
            # 发出边界：这一帧真正送进环境的动作。
            language_crossings += count_strs_deep(record.executed_action)
            # 感知边界：这一帧落到模型眼前的观测。
            observation_leaks += observation_str_leaks(record.observation)

    trace = loop.trace()
    # 危险暴露走 hazard_frames() 这个**唯一实现**（测试也调它），不在这里再写一遍。
    # 它读的是逐帧 observation，不经事件流，所以没有环形缓冲那个洞。
    hazard_visible, hazard_contact, hazard_distance_sum = hazard_frames(trace)
    # 资源侧同一条纪律：走 resource_frames()，不在这里另写一份。
    resource_visible, resource_distance_sum = resource_frames(trace)
    success_lengths = success_run_lengths(trace)
    audit = store.audit_log()
    applied = [a for a in audit if a.applied]
    rejected = [a for a in audit if not a.applied]

    return EpisodeResult(
        seed=seed,
        frames=len(trace),
        alive=loop.alive,
        run_frames=sum(1 for r in trace if r.state == STATE_RUN),
        run_success_frames=run_success_frames,
        run_failed_frames=run_failed_frames,
        sleep_frames=sum(1 for r in trace if r.state == STATE_SLEEP),
        wake_frames=sum(1 for r in trace if r.state == STATE_WAKE),
        constraint_rejected=rejected_total,
        internal_errors=internal_total,
        max_consecutive_run=max_consecutive_clean_run(trace),
        language_crossings=language_crossings,
        observation_leaks=observation_leaks,
        proposals=len(audit),
        applied=len(applied),
        rejected=len(rejected),
        sleep_episodes=count_sleep_episodes(trace),
        slow_loop_calls=calls,
        rejected_kinds=tuple(sorted({a.kind for a in rejected})),
        # 审计完整性：每次升版都该有一条 from→to 连续的 applied 记录。
        version_bumps=sum(1 for a in applied if a.to_version == a.from_version + 1),
        audited_bumps=len(applied),
        energy_gained=energy_gained,
        energy_spent=energy_spent,
        damage_taken=damage_taken,
        hazard_visible_frames=hazard_visible,
        hazard_contact_frames=hazard_contact,
        nearest_hazard_distance_sum=hazard_distance_sum,
        resource_visible_frames=resource_visible,
        nearest_resource_distance_sum=resource_distance_sum,
        max_success_run=success_lengths[0] if success_lengths else 0,
        compileable_segments=compileable_segments(trace),
        invoked_skills=tuple(loop.skill_runner.invoked_skill_ids()),
        # 尾部取一次即可：计数器只增不减、不截断，不需要逐帧加。
        event_totals=loop.environment.event_counts(),
        # 记忆请求是**全量 append 的列表**（不是 16 槽环形缓冲），所以这个
        # 分母不会静默漏——理由与"量不从环形缓冲取"那条纪律相同。
        memory_write_requests=len(loop.environment.memory_requests),
        # 有仪器才取；零检索器没有 `stats` 属性，取到空字典正是要的
        # （见 EpisodeResult.memory_instrumented）。
        memory_stats=_memory_stats(loop.memory),
        # 技能事件取自 trace 上运行器的报告，**不是** event_counts()——那两个
        # 事件类型没有生产者，从计数器读恒得 0（见 EpisodeResult 的字段注释）。
        skill_calls=sum(1 for r in trace if r.decoded_action.skill is not None),
        skill_successes=sum(1 for r in trace if r.skill_event == "SKILL_SUCCESS"),
        skill_failures=sum(1 for r in trace if r.skill_event == "SKILL_FAILURE"),
        energy_windows=len(energy_by_version_window(trace)),
        energy_change=energy_change_between_windows(trace),
        # 解码后的动作指纹，逐帧。见 EpisodeResult.action_trace 的字段注释：
        # 取自 trace，所以 Gate 沙箱那 8 帧不会混进来。
        action_trace=tuple(FrameAction.of(r.decoded_action) for r in trace),
    )


def _memory_stats(retriever: Any) -> dict[str, int]:
    """有 ``stats`` 就抄一份，没有就返回空字典。

    **不写 ``getattr(retriever, "stats", MemoryStats())``**：那会让零检索器
    也长出一份全 0 的统计，于是"记忆关着"与"记忆开着但什么都没发生"
    在输出里**长得一模一样**——而这两个结论相反。空字典是"没有仪器"的
    信号，全 0 字典是"有仪器、读数为 0"的信号。
    """

    stats = getattr(retriever, "stats", None)
    if stats is None or not hasattr(stats, "as_dict"):
        return {}
    return dict(stats.as_dict())


def _context(store: StructureStore | None = None):
    """快环的**初始**上下文。

    有 store 时取它的快照。这一条曾经是错的：``run_episode(store=...)`` 把
    store 交给了慢环，初始上下文却仍从 ``make_context()`` 现造一份**空结构**。
    于是预置在 store 里的东西（技能、本能）进不了快环，除非慢环**恰好应用了
    一条提案**——而 ``run_slow_loop`` 只在 ``applied`` 时回传
    ``store.snapshot()``，慢环要应用提案又得先有可编译段。闭环咬住了自己：
    **预置结构被静默忽略，测出来的"没效果"其实是"没装上"。**

    无 store 时仍走 ``make_context()``（它与 ``StructureStore().snapshot()``
    等价），保留"与测试同一个构造点"这条。
    """

    if store is not None:
        return store.snapshot()

    from tests.conftest import make_context

    return make_context()


def count_sleep_episodes(trace: Sequence[Any]) -> int:
    """极大连续 SLEEP 段的段数——"睡着了几次"，不是"睡了几帧"。

    实验 7 的睡眠进入率若按帧数算，一次长睡会把比率抬得很高，
    掩盖"其实只睡过一次"。按段数算才对得上"慢环触发了几次"。
    """

    return sum(
        1
        for prev, cur in zip(trace, trace[1:])
        if cur.state == STATE_SLEEP and prev.state != STATE_SLEEP
    ) + (1 if trace and trace[0].state == STATE_SLEEP else 0)


def max_consecutive_clean_run(trace: Sequence[Any]) -> int:
    """最长的一段「RUN 且未触发约束拒绝/内部异常」的连续帧。

    拒绝打断的是**连续闭环**，不是存活——所以实验 1 数它，不数总帧数。
    """
    best = 0
    current = 0
    for record in trace:
        if record.state != STATE_RUN:
            current = 0
            continue
        notes = record.feedback.notes if record.feedback is not None else ""
        if "constraint_rejected:" in notes or "internal_error:" in notes:
            current = 0
            continue
        current += 1
        best = max(best, current)
    return best


# ----------------------------------------------------------------------
#  窗口内的量（实验 2 / 3 用；与 Environment 的全轮累计分工不同）
# ----------------------------------------------------------------------


def count_events(trace: Sequence[Any], event_type: str) -> int:
    """``trace`` 里某类事件的个数，**按 event_id 去重**。

    为什么要去重：观测里带的 ``events`` 是环境的**滚动窗口**，同一个事件会
    连续出现在十几帧的观测里，按帧数会把一次写入数成十几次。这个口径与
    ``SSEA.plasticity._event_ids`` 一致（那里也是这么写的，理由相同）。

    为什么不去重不行、不按窗口也不行——两者是**两件事**，别混：

    - 去重治的是**重复计数**（同一事件的多次出现）。
    - 本函数仍在 ``trace`` 这个**给定窗口**内计数，窗口外的事件它看不见。
      要"整轮一共几次"请用 ``Environment.event_counts()``，
      那个只增不减、不截断。

    注意 ``MEMORY_RETRIEVED`` **有一帧滞后**：``observe_model_event`` 在
    ``step()`` 返回观测**之后**才调用，所以帧 t 发出的事件出现在帧 t+1 的
    观测里。计数不受影响，只影响"算在哪一帧头上"（``plasticity`` 的
    docstring 也记了这一条）。
    """

    ids: set[str] = set()
    for record in trace:
        if record.state != STATE_RUN:
            continue
        for event in record.observation.events:
            if event.event_type == event_type:
                ids.add(event.event_id)
    return len(ids)


def energy_by_version_window(trace: Sequence[Any]) -> list[dict[str, Any]]:
    """按**结构版本窗口**切开的能量收支，从旧到新。

    **实验 3 的「能量消耗变化」必须用这个，不能用全轮累计。** 判据是
    ``StepRecord.context_fingerprint``——与 ``SSEA.plasticity._current_window``
    同一个切法，那是这个字段的第一个消费者。它 docstring 里记着不切窗口的实测
    代价：三轮睡眠把 ``memory_gate_threshold`` 从 0.5 一路推到下界 0.15，
    "不是『收敛到合适的阈值』，是『撞到夹子』"。**同一个错法在能量指标上会重演**：
    不切版本，固化**前**的消耗会永远留在分子里，于是"固化有没有降低消耗"
    这个问题被历史数据稀释掉。

    返回每段一个 dict，键为 ``fingerprint`` / ``run_frames`` /
    ``energy_gained`` / ``energy_spent`` / ``damage_taken`` /
    ``energy_spent_per_run_frame``。空 trace 返回空列表；
    指纹为空（``versions={}``，没有版本信息）时退化为**一段**——
    没有版本信息就没有归因可言，与 ``_current_window`` 的取舍一致。
    """

    windows: list[dict[str, Any]] = []
    current_fp: tuple[tuple[str, int], ...] | None = None
    acc: dict[str, Any] | None = None

    for record in trace:
        if record.state != STATE_RUN:
            continue
        fp = record.context_fingerprint
        if fp != current_fp:
            current_fp = fp
            acc = {
                "fingerprint": fp,
                "run_frames": 0,
                "energy_gained": 0.0,
                "energy_spent": 0.0,
                "damage_taken": 0.0,
            }
            windows.append(acc)
        assert acc is not None  # 由上面那个分支保证，仅给类型检查看
        acc["run_frames"] += 1
        if record.feedback is not None:
            change = record.feedback.energy_change
            acc["energy_gained"] += max(0.0, change)
            acc["energy_spent"] += max(0.0, -change)
            acc["damage_taken"] += max(0.0, record.feedback.damage_change)

    for acc in windows:
        n = acc["run_frames"]
        acc["energy_spent_per_run_frame"] = acc["energy_spent"] / n if n else 0.0
    return windows


def energy_change_between_windows(trace: Sequence[Any]) -> float | None:
    """**实验 3 的「能量消耗变化」**：最后一个窗口减第一个窗口，按每 RUN 帧口径。

    这不是新算式，是 :func:`energy_by_version_window` 的差分——
    被减数是"固化后"，减数是"固化前"。**必须有至少两个窗口**（即 trace 里
    真的发生过一次版本切换），否则返回 ``None``：只有一个窗口时
    "变化"没有第二个观测点，返回 0.0 会把"没发生过固化"读成"固化没有效果"。

    口径（分母 RUN 帧、毛支出）沿用模块 docstring 一之二，不在这里另定一套。
    """

    windows = energy_by_version_window(trace)
    if len(windows) < 2:
        return None
    return (
        windows[-1]["energy_spent_per_run_frame"]
        - windows[0]["energy_spent_per_run_frame"]
    )


def success_run_lengths(trace: Sequence[Any]) -> list[int]:
    """连续「直接成功」帧的**段长**，从长到短。

    「直接成功」的判据**不在这里定义**——直接用
    ``SSEA.skill_library._is_direct_success``。抄一份到本模块是错的：
    判据一旦有两份就会漂移，而漂移的表现是「本脚本说能编译、编译器说不能」。
    从包里 import 一个下划线名字是这里能接受的代价，因为另一条路更糟。

    这条指标是 ② 的**验收判据**，不是存活帧数。理由：编译器要的是
    连续成功段（``min_frames=3``），活得久但一路随机游走**产不出任何技能**。
    "存活帧数涨了"曾被误当成进展——实测里 8 seed 3 次抓取把均寿命
    从 67 抬到 72 帧，而可编译段仍然是 0。**活的久不等于学到了东西。**
    """

    from SSEA.skill_library import _is_direct_success

    lengths: list[int] = []
    current = 0
    for record in trace:
        if _is_direct_success(record):
            current += 1
        elif current:
            lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return sorted(lengths, reverse=True)


def compileable_segments(trace: Sequence[Any]) -> int:
    """这条 trace 能编译出几条技能——**用真的编译器量**，不用代理指标。

    调 ``compile_skills`` 而不是自己判断"段长 ≥ 3 且净收益为正"：
    判据有两份就会漂移，而这里漂移的后果格外难查——脚本说"有东西可编译"，
    慢环实际上一条都没提，于是实验读成"固化没效果"。
    """

    from SSEA.skill_library import compile_skills

    return len(compile_skills(trace))


def _pct(xs: Sequence[float], q: float) -> float:
    """线性插值分位数。空序列返回 0.0——调用方负责把「空」与「全零」分开。"""

    if not xs:
        return 0.0
    ordered = sorted(xs)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


@dataclass(frozen=True)
class ActionDivergence:
    """两臂动作序列的逐帧差——实验 2 的**第三档**判据的载体。

    保留原始差分而不只留汇总：中位数会把**双峰分布**抹平，而这个项目
    反复咬到的正是双峰（约一半 seed 门恒闭，12 §4.3）。留原始值，
    调用方才能把 p90 / max 也打出来。
    """

    #: 两臂各自的帧数。**两者不等时**，``compared`` 之外的那些帧没有参与
    #: 比较——长度差本身也是行为差，所以要报出来而不是静默截断。
    frames: tuple[int, int]
    #: 实际参与比较的帧数 = ``min(frames)``。
    compared: int
    #: 方向向量**维数不一致**的帧数。它们不计入 ``direction_diffs``。
    dim_mismatches: int
    direction_diffs: tuple[float, ...]
    speed_diffs: tuple[float, ...]
    duration_diffs: tuple[float, ...]

    @property
    def differing_frames(self) -> int:
        """方向真的不同的帧数（严格 > 0）。"""

        return sum(1 for d in self.direction_diffs if d > 0.0)

    @property
    def differing_ratio(self) -> float:
        """``differing_frames / compared``。分母为 0 时返回 0.0。

        **0.0 不等于「两臂相同」**——没有帧可比时它什么都没说。
        调用方要自己看 ``compared``。
        """

        return self.differing_frames / self.compared if self.compared else 0.0

    @property
    def direction_median(self) -> float:
        return statistics.median(self.direction_diffs) if self.direction_diffs else 0.0

    @property
    def direction_p90(self) -> float:
        return _pct(self.direction_diffs, 0.9)

    @property
    def direction_max(self) -> float:
        return max(self.direction_diffs, default=0.0)

    @property
    def speed_max(self) -> float:
        return max(self.speed_diffs, default=0.0)

    @property
    def duration_max(self) -> float:
        return max(self.duration_diffs, default=0.0)

    @property
    def lengths_differ(self) -> bool:
        return self.frames[0] != self.frames[1]


def action_divergence(
    a: Sequence[FrameAction], b: Sequence[FrameAction]
) -> ActionDivergence:
    """两臂动作序列的逐帧差分布——实验 2 的**第三档**判据。

    为什么不复用 ``exp2_memory_recall.coarse_signature``：那 5 个整数是
    **阈值化之后的投影**（帧数 / RUN 帧 / 可编译段 / ``ENERGY_GAINED`` /
    危险接触帧），1e-3 量级的扰动投过去就没了。2026-09-28 逐帧实测：
    两臂的 5 个整数在 7/8 个 seed 上相同，**而动作在 5/8 个 seed 上不同**
    （中位幅度 ~1e-3）。**「整数指标相同」不等于「行为相同」**——
    这一档就是来补这个洞的（12 §6 债务 21）。

    ``direction_diffs`` 是逐帧欧氏范数（单位向量之差，量纲就是"方向"），
    ``speed_diffs`` / ``duration_diffs`` 是标量绝对差。

    **维数不一致的帧不计入方向统计**，只记进 ``dim_mismatches``：
    拿 ``zip`` 静默截断会把「3 维对 2 维」读成一个很小的差分，那是假数字。
    """

    n = min(len(a), len(b))
    dd: list[float] = []
    sd: list[float] = []
    td: list[float] = []
    dims = 0
    for i in range(n):
        x, y = a[i], b[i]
        if len(x.direction) != len(y.direction):
            dims += 1
            continue
        dd.append(math.dist(x.direction, y.direction))
        sd.append(abs(x.speed - y.speed))
        td.append(abs(x.duration - y.duration))
    return ActionDivergence(
        frames=(len(a), len(b)),
        compared=n,
        dim_mismatches=dims,
        direction_diffs=tuple(dd),
        speed_diffs=tuple(sd),
        duration_diffs=tuple(td),
    )


def pool_action_divergences(rows: Sequence[ActionDivergence]) -> ActionDivergence:
    """把多个 seed 的差分**合池**，而不是把各 seed 的中位数再平均。

    平均中位数会把「多数 seed 几乎无差、少数 seed 差很大」抹平——
    而那正是本项目反复咬到的双峰现象。合池之后中位数与 p90 才反映真实分布。
    """

    return ActionDivergence(
        frames=(sum(r.frames[0] for r in rows), sum(r.frames[1] for r in rows)),
        compared=sum(r.compared for r in rows),
        dim_mismatches=sum(r.dim_mismatches for r in rows),
        direction_diffs=tuple(d for r in rows for d in r.direction_diffs),
        speed_diffs=tuple(d for r in rows for d in r.speed_diffs),
        duration_diffs=tuple(d for r in rows for d in r.duration_diffs),
    )


def _visible_frames(
    trace: Sequence[Any], predicate: Any
) -> list[tuple[Any, float]]:
    """``[(记录, 最近目标距离)]``——只留 RUN 帧且视野内存在满足判据的对象。

    ``hazard_frames`` 与 ``resource_frames`` 共用这一段，但**判据不同**，
    所以判据作为参数传进来：危险源是 ``threat_level > 0``，资源是
    ``resource_value > 0``。两个判据都取自环境自己标注的生存后果，
    不依赖任何"类别号是几"的约定（``object_vector.py`` 刻意不让模型
    解释 ``category_id`` 的语义）。
    """

    out: list[tuple[Any, float]] = []
    for record in trace:
        if record.state != STATE_RUN:
            continue
        targets = [o for o in record.observation.objects if predicate(o)]
        if not targets:
            continue
        out.append((record, min(o.distance for o in targets)))
    return out


def hazard_frames(trace: Sequence[Any]) -> tuple[int, int, float]:
    """数出危险暴露的三个原始量：``(可见帧数, 接触帧数, 最近距离之和)``。

    **危险回避率的唯一实现**（公式与两条选择见模块 docstring 一之四；
    派生比率在 ``EpisodeResult.hazard_avoidance_rate`` 上）。
    只数 RUN 帧——睡眠帧不产生动作，也不接触危险源，把它算进分母是虚增暴露。

    危险源的判据是 ``threat_level > 0``，不是 ``category_id``：观测里
    只暴露 ``category_id`` 这个整数，而它的语义**刻意不由模型解释**
    （``object_vector.py`` 的 docstring）。``threat_level`` 是环境自己标注的
    生存后果，用它做判据不依赖任何"类别号是几"的约定。
    实测世界初始化里 hazard 的 ``threat_level ∈ [0.3, 1.0]``、resource 与 prop
    恒为 0.0（``environment.py`` 建对象处），所以这个判据是准的。
    """

    frames = _visible_frames(trace, lambda o: o.threat_level > 0)
    # 分子不看事件流：环形缓冲会静默漏，且漏的方向正好把"躲开了"读成"没躲开"。
    contact = sum(
        1
        for record, _ in frames
        if record.feedback is not None and record.feedback.damage_change > 0
    )
    return len(frames), contact, sum(d for _, d in frames)


def resource_frames(trace: Sequence[Any]) -> tuple[int, float]:
    """``(资源可见帧数, 最近资源距离之和)``——**「趋近」这个动作的度量**。

    ②.1 的验收要回答的是「本能有没有让它真的靠近资源」，而这个问题的
    反面（"没靠近"）与"本能没装上"在 ``ENERGY_GAINED`` 上**长得一模一样**：
    两者都是 0。所以必须有这条连续量，否则「趋近成功但抓取链没通」与
    「趋近根本没生效」无法区分——而这两种结论指向完全不同的下一步。

    与 ``hazard_frames`` 对称：只数 RUN 帧，判据取 ``resource_value > 0``
    （prop 恒为 0.0，见 ``environment.py`` 建对象处）。
    """

    frames = _visible_frames(trace, lambda o: o.resource_value > 0)
    return len(frames), sum(d for _, d in frames)


# ----------------------------------------------------------------------
#  自然语言越界检查（实验 1 的第四个指标）
# ----------------------------------------------------------------------

#: 这些字段装的是**名字**（id 与事件类型），不是被传递的正文。
#:
#: 它比 ``tests/test_protocol_consistency.py::TestNoNaturalLanguageInLoop``
#: 的白名单**多四个**，那四个是本次实验发现的守卫缺口：静态检查只扫了
#: ``Action`` 的顶层字段名（六个通道名），**没扫通道内部**——于是
#: ``Manipulation.target_id`` / ``operation``、``SkillCall.skill_id``、
#: ``SelfModification.proposal_type`` 这四个 str 字段从来没被检查过。
#: 它们确实都是名字（前两个是对象 id 与操作码，后两个是技能 id 与提案类型），
#: 所以不是违规；但"没人检查过"与"检查过没问题"是两件事。
#: 见本目录 ``README.md`` 的「本次实验发现的守卫缺口」。
IDENTIFIER_FIELDS = frozenset(
    {
        # Observation / Feedback / EventVector / MemoryItem（静态检查已覆盖）
        "object_id",
        "category_id",
        "event_id",
        "event_type",
        "source_id",
        "id",
        "type",
        "outcome",
        "notes",
        "time_phase",
        # Action 通道内部（静态检查**未**覆盖，本次补上）
        "target_id",
        "operation",
        "skill_id",
        "proposal_type",
    }
)

#: 操作码的**闭词表**。标识符允许出现，但必须取自一张封闭的表——
#: 否则 ``operation`` 就成了一个"可以往里写任何字符串"的字段，
#: 而"可以写任何字符串"正是正文的入口。名字与正文的分界就在这里：
#: 名字取自闭集，正文不是。
OPCODE_VOCABULARIES: dict[str, frozenset[str]] = {}


def _opcode_vocabularies() -> dict[str, frozenset[str]]:
    """惰性构造闭词表——避免在 import 期拉起整个协议包。"""
    if OPCODE_VOCABULARIES:
        return OPCODE_VOCABULARIES
    from SSEA.sse_protocols.action_space import OPERATIONS
    from SSEA.sse_protocols.self_modification import ALLOWED_PROPOSAL_TYPES

    OPCODE_VOCABULARIES.update(
        {
            "operation": frozenset(OPERATIONS),
            "proposal_type": frozenset(ALLOWED_PROPOSAL_TYPES),
        }
    )
    return OPCODE_VOCABULARIES


def observation_str_leaks(observation: Any) -> int:
    """``Observation`` 里出现了几个**非标识符**的 str 值。

    对象 id 与时间相位名是标识符（07 §8.1），允许；除此之外任何 str
    都意味着有正文从环境流进了感知输入。
    """
    leaks = 0
    for obj in observation.objects:
        if not isinstance(obj.object_id, str):
            leaks += 1
    environment = getattr(observation, "environment", None)
    if environment is not None and not isinstance(environment.time_phase, str):
        leaks += 1
    return leaks


def count_strs_deep(value: Any, _depth: int = 0) -> int:
    """数一数结构里有多少个 str **越界**。

    判据是**名字 vs 正文**，不是"有没有 str"：

    - 允许：标识符字段（:data:`IDENTIFIER_FIELDS`）里的 str。
    - 允许：取自**闭词表**的操作码（:func:`_opcode_vocabularies`）。
    - 越界：其余任何 str。

    闭词表那一层是必要的——只按字段名放行的话，``operation`` 就成了一个
    "可以往里写任何字符串"的字段，而"可以写任何字符串"正是正文的入口。
    名字取自闭集，正文不是，分界就在这里。

    走进 dict 时只看值不看键：键是字段名。再往深走，字段名信息就丢了，
    所以闭词表检查只在**具名**那一层生效——这也是 ``_depth`` 停在 6 的原因。
    """
    if _depth > 6:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (tuple, list)):
        return sum(count_strs_deep(v, _depth + 1) for v in value)
    if isinstance(value, dict):
        return sum(count_strs_deep(v, _depth + 1) for v in value.values())

    names = getattr(value, "__dataclass_fields__", None)
    if not names:
        # torch.Tensor / float / None / int —— 都不是 str，贡献 0
        return 0

    vocabularies = _opcode_vocabularies()
    crossings = 0
    for name in names:
        if name in IDENTIFIER_FIELDS:
            continue
        field_value = getattr(value, name)
        vocabulary = vocabularies.get(name)
        if vocabulary is not None and isinstance(field_value, str):
            # 操作码：取自闭集才算名字。
            if field_value in vocabulary:
                continue
            crossings += 1
            continue
        crossings += count_strs_deep(field_value, _depth + 1)
    return crossings


# ----------------------------------------------------------------------
#  输出
# ----------------------------------------------------------------------


def summarize(results: Sequence[EpisodeResult]) -> dict[str, float]:
    """把一个 seed 集合收成一行数字。"""
    n = len(results)
    return {
        "seeds": float(n),
        "mean_frames": statistics.mean(r.frames for r in results),
        "mean_run_frames": statistics.mean(r.run_frames for r in results),
        "max_consecutive_run": float(max(r.max_consecutive_run for r in results)),
        "action_legality_rate": statistics.mean(
            r.action_legality_rate for r in results
        ),
        "interface_error_rate": statistics.mean(
            r.interface_error_rate for r in results
        ),
        "language_crossings": float(sum(r.language_crossings for r in results)),
        "observation_leaks": float(sum(r.observation_leaks for r in results)),
        "sleep_entry_rate": sum(1 for r in results if r.sleep_entry) / n,
        "wakes": float(sum(r.wake_frames for r in results)),
        "proposals": float(sum(r.proposals for r in results)),
        "applied": float(sum(r.applied for r in results)),
        "rejected": float(sum(r.rejected for r in results)),
        "audit_completeness": statistics.mean(
            r.audit_completeness for r in results
        ),
    }


def mean_defined(values: Sequence[float | None]) -> tuple[float | None, int]:
    """跨 seed 求均值，**跳过 ``None``**，并把「有几个 seed 真的有定义」一并返回。

    返回的第二个数是**分母**，必须打进实验输出里。理由是这一整套指标里
    ``None`` 不是缺数据，是"这个 seed 上没有可测的东西"（没有危险源可见、
    没有发生过版本切换）——把它当 0 平均进去，就正好复现了项目要治的那个错
    （14 §5.2：看数字先看分母）。全为 ``None`` 时返回 ``(None, 0)``。
    """

    defined = [v for v in values if v is not None]
    if not defined:
        return None, 0
    return statistics.mean(defined), len(defined)


def print_table(title: str, rows: Sequence[tuple[str, Any]]) -> None:
    """``(标签, 值)`` 序列打成长度对齐的两列表。"""
    width = max(len(label) for label, _ in rows)
    print(f"\n{title}")
    print("-" * (width + 22))
    for label, value in rows:
        shown = f"{value:.4f}" if isinstance(value, float) else str(value)
        print(f"{label:<{width}}  {shown}")


def print_matrix(
    results: Sequence[EpisodeResult], columns: Sequence[tuple[str, str]]
) -> None:
    """逐 seed 明细。``columns`` 是 ``(表头, EpisodeResult 属性名)`` 序列。"""
    width = max(10, *(len(h) for h, _ in columns))
    print("  " + " ".join(f"{h:>{width}}" for h, _ in columns))
    for r in results:
        cells = []
        for _, attr in columns:
            value = getattr(r, attr)
            shown = f"{value:.3f}" if isinstance(value, float) else str(value)
            cells.append(f"{shown:>{width}}")
        print("  " + " ".join(cells))
