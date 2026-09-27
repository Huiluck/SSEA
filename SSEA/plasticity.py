"""Plasticity Controller + LocalPlasticity —— 可塑性控制器与局部参数更新。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.7（Plasticity Controller）
+ docs/08-dual-loop-interface-and-gap-closure.md §4.2（慢环公式的 ``Δθ``）。

07 §6.7 原文只给了两张清单——可更新对象与不可更新对象——没有说"怎么更新、
更新到哪、谁来判定越界"。本模块把这两张清单变成**可执行的边界**：

    PlasticityController  持有 ``allowed_scope``，回答"这个能不能改"
    LocalPlasticity       吃 trace 与结构，产出 Δθ 提案

两者分工的理由与增量 1 / 2 相同：判定与生成是两件事。捏在一起，
「提了一个越界的更新」与「边界定错了」在日志里不可区分。

Δθ 在第一阶段是什么，以及它不是什么
--------------------------------
**是**：``thresholds`` 与 ``retrieval`` 两个结构类别里的若干键的行为阈值。
它们住在 ``FastLoopContext`` 里，于是改它们必须走
「提案 → 验证门 → Structure Store → 换快照」——每一次变动都是一次可审计的
版本切换。

**不是**：torch 参数。``ActionDecoder`` 的门控头（``gates.memory`` 等）确实
可微，但第一阶段**不动它**，理由见下面「参数侧为什么整个留给后续」。

参数侧为什么整个留给后续
----------------------
这不是排不下，是因为现在做会造出一个**假的安全保证**：

1. 07 §16「模型不可绕过验证器应用修改」。参数更新要么不过门（违背此条），
   要么过门。
2. 而过门这条路在第一阶段是**空的**：``VerificationGate`` 的四级检查全部
   在 ``FastLoopContext`` 上进行，第四级环境测试装配的是一个**全新的**
   ActionDecoder——一个权重增量递进去，环境测试看不见它，于是
   "四级检查全部通过"这句话在参数上什么也没检验。
3. 把权重增量塞进 ``UPDATE_ADAPTER`` 的 bytes 里能让它"看起来过了门"。
   ``_check_adapters`` 只查"是非空 bytes"。那比不过门更糟：它让文档可以
   写「自我修改经过验证门」，而实际上验证了什么并不知道。

所以本模块把参数侧整个声明为未实现（``DEFERRED_SCOPES``），
由 ``tests/test_plasticity.py::TestDeferredScopes`` 守着。真正的落地顺序是：
先让 ``adapters`` 有模型侧消费者（现在它是个写得进、过得门、传得下、
**却没有消费者**的类别），再让 Gate 的第四级能装上候选权重，
然后才谈参数侧 Δθ。三步都是可见的工程，不是"以后再说"。

Δθ 的判据是世界，不是偏好
----------------------
两条规则，各自对应一个**可观测的症状**，且都能沉默：

    症状 1  值得记的帧上门从没开过     → 降低 memory_gate_threshold
    症状 2  写进去了却从来读不回来     → 降低 min_similarity
    两者皆非                        → 不提案

"值得记的帧"由**惊奇**判定（``Feedback.prediction_error``，SurpriseEstimator
的产物，doc 03 点名的 SSEA 核心学习信号），不由任何内部偏好判定。
判据是**相对**的：惊奇度在 ``surprise_quantile`` 分位数**及以上**的帧算值得记
（``>=`` 而非 ``>``，理由见 ``PlasticityConfig.surprise_quantile`` 的注释）。
这与增量 2 的同一条纪律：编译器按世界计价物决定提不提，不按内部排序。

注意症状 1 的措辞是"门从没开过"，不是"门开得不够多"。
通道门开着而模型选择 ``store=False`` 是**一个决定**，不是缺失——
那个决定属于 ``mem_store`` 头，是参数侧的职权。第一阶段只修"连决定都没得做"。

证据只看当前版本
--------------
慢环拿到的 trace 是**整条 episode**，横跨多个结构版本。Δθ 的判定因此
只取末帧指纹那段（``_current_window``）——换版前那些帧上的"门没开"是
**旧策略的账**，算进新策略会让每条规则每次睡眠都再触发一次，一路推到
边界上才停。那不是收敛，是撞夹子。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .action_decoder import GATE_THRESHOLD_KEYS
from .fast_loop import STATE_RUN, StepRecord
from .sse_protocols import FastLoopContext, SelfModificationProposal
from .sse_protocols.structure_store import PROPOSAL_KIND_MAP

#: 07 §6.7 可更新对象 → 第一阶段的落地形态。
#: 前两项由本模块产出提案；后三项各有自己的生产者（ΔS / ΔR / ΔM），
#: 列在这里是为了让 ``allowed_scope`` 是一份**完整的**清单，
#: 而不是"本模块能改的那部分"——后者会让边界看起来比实际窄。
UPDATABLE_SCOPES: tuple[str, ...] = (
    "thresholds",  # 行为阈值 → UPDATE_THRESHOLD（本模块）
    "retrieval",  # 检索策略 → UPDATE_RETRIEVAL_POLICY（本模块）
    "adapters",  # 小型 adapter → UPDATE_ADAPTER（参数侧，见 DEFERRED_SCOPES）
    "skills",  # 技能 → ADD_SKILL / UPDATE_SKILL（ΔS，Experience Compiler）
    "rules",  # 规则 → ADD_RULE / UPDATE_RULE（ΔR，RuleCompiler）
    "memory",  # 记忆 → 记忆系统写入，不走提案（ΔM）
)

#: 07 §6.7 不可更新对象 + 08 §3.5 补的两项。
#: 这七项的共性是：改了它们，"验证"这件事本身就不再可信。
NON_UPDATABLE: tuple[str, ...] = (
    "core_safety",  # 核心安全机制
    "verification_gate",  # 验证门
    "environment_interface",  # 环境接口
    "gene_permissions",  # 基因管理器底层权限
    "observer_interface",  # 观察员接口
    "architecture",  # 08 §3.5：仅作配置记录与遗传
    "core_weights",  # 08 §3.5：mutation_rate 不作用于结构
)

#: 已实现的 Δθ 落点。见模块 docstring。
IMPLEMENTED_SCOPES: tuple[str, ...] = ("thresholds", "retrieval")

#: 未实现的落点 → 归属哪里、为什么现在不做。
#: 键集由 TestDeferredScopes 守着：落地时必须同步改这里。
DEFERRED_SCOPES: Mapping[str, str] = {
    "adapters": (
        "结构类别已通（Gate 的 _check_adapters + Store 的 UPDATE_ADAPTER），"
        "但 adapters 没有模型侧消费者——写得进、过得门、传得下，却没人读。"
        "先补消费者，再让 Gate 第四级能装候选权重"
    ),
    "policy_heads": (
        "ActionDecoder 的门控头可微，但参数更新无法被 Gate 检验："
        "第四级环境测试装配的是全新模型，权重增量递进去它看不见，"
        "于是「四级检查全部通过」在参数上一文不值。见模块 docstring 第 2 条"
    ),
}

#: 默认边界。键名即 ``FastLoopContext.thresholds`` / ``retrieval`` 的键。
#: **不在表里的键不可改**——白名单而非黑名单：一个忘了登记的键应当提不出提案，
#: 而不是悄悄改掉某个机制。
DEFAULT_BOUNDS: Mapping[str, tuple[float, float]] = {
    **{key: (0.15, 0.85) for key in GATE_THRESHOLD_KEYS.values()},
    # min_similarity 必须 > 0：等于 0 会让"无命中"与"命中但相似度为 0"
    # 在 m_t 上不可区分（memory_system.validate_retrieval_policy 的 strict_low）。
    "min_similarity": (0.01, 0.5),
}

#: 门控阈值下界不取 0 的理由与 min_similarity 同构：阈值为 0 时门控恒开，
#: 那不再是"倾向于开门"，是"门控不存在了"。


@dataclass(frozen=True)
class PlasticityConfig:
    """LocalPlasticity 配置。"""

    #: 记忆通道门控阈值在结构里的键。
    memory_gate_key: str = GATE_THRESHOLD_KEYS["memory"]

    #: 检索相似度阈值在结构里的键。
    similarity_key: str = "min_similarity"

    #: 判定"这一帧值得记住"的惊奇分位数。0.5 = **中位数及以上**算值得记。
    #: 取 ``>=`` 而不是 ``>``：全部帧的惊奇度相同时（``cut`` 落在众数上），
    #: 严格大于会让 ``surprising == 0``，于是症状 1 永远沉默——而"模型对世界
    #: 毫无预测能力"恰恰是最该记的时候。代价是 ``surprising`` 恒不少于半数帧，
    #: 所以它是**相对**判据（"比一半的帧更意外"），不是绝对判据。
    surprise_quantile: float = 0.5

    #: 症状 2（写进去了却读不回来）要求的最少 RUN 帧数。
    #: 两条症状对证据量的要求**刻意不同**：症状 1 是逐帧性质
    #: （"这一帧上门没开"在单帧上就是真的），症状 2 是**关系**断言
    #: （"写了却读不回"要写入与读取双方都有机会发生）。两帧既可能真的
    #: 读不回，也可能只是还没轮到读——前者该修，后者不该动。
    #: 不设这个下限的后果实测过：短窗口下规则每轮都触发，把 min_similarity
    #: 一路推到下界 0.01，而 0.01 意味着恒命中——机制被关掉而不是被调好。
    min_evidence_frames: int = 8

    #: 提案 id 前缀。审计日志里能看出这条提案是谁提的。
    proposal_prefix: str = "plasticity"

    def __post_init__(self) -> None:
        if not 0.0 <= self.surprise_quantile <= 1.0:
            raise ValueError("surprise_quantile 应在 [0,1]")
        if self.min_evidence_frames < 1:
            raise ValueError("min_evidence_frames 至少为 1")
        if self.memory_gate_key not in DEFAULT_BOUNDS:
            raise ValueError(
                f"memory_gate_key={self.memory_gate_key!r} 不在 DEFAULT_BOUNDS 里；"
                f"未登记边界的键不可改"
            )
        if self.similarity_key not in DEFAULT_BOUNDS:
            raise ValueError(
                f"similarity_key={self.similarity_key!r} 不在 DEFAULT_BOUNDS 里"
            )


@dataclass(frozen=True)
class PlasticityScope:
    """``allowed_scope`` —— 07 §6.7 两张清单的可执行形式。

    ``kinds`` 是可提案的结构类别（``STRUCTURE_KINDS`` 的子集）；
    ``bounds`` 是键名 → (下界, 上界) 的白名单。
    """

    #: 可提案的结构类别。
    kinds: tuple[str, ...] = IMPLEMENTED_SCOPES

    #: 键名 → 合法区间。**不在表里的键不可改。**
    bounds: Mapping[str, tuple[float, float]] = field(
        default_factory=lambda: dict(DEFAULT_BOUNDS)
    )

    #: 单次更新的最大绝对变化量。上限而非步长：实际走多少由症状决定。
    max_step: float = 0.1

    #: 小于这个量的更新不提提案——它只是噪声，却会占一条审计记录。
    min_step: float = 0.01

    def __post_init__(self) -> None:
        unknown = sorted(set(self.kinds) - set(PROPOSAL_KIND_MAP.values()))
        if unknown:
            raise ValueError(f"未知的结构类别: {unknown}")
        if self.max_step <= 0:
            raise ValueError("max_step 必须为正")
        if not 0 < self.min_step <= self.max_step:
            raise ValueError("min_step 必须落在 (0, max_step]")


@dataclass(frozen=True)
class PlasticityObservation:
    """一次 trace 的可观测症状。**纯读，不产生任何提案。**

    单独拿出来是为了让"为什么没提案"可回答：只有提案的话，
    一次沉默与"什么都没看到"在日志里不可区分（与增量 2 的
    ``CompileResult.skipped`` 同一条理由）。
    """

    #: RUN 帧数（**当前结构版本**产出的那一段，即本次判定实际使用的帧数）。
    #: SLEEP / WAKE 帧没有解码动作，不参与判定。
    run_frames: int = 0
    #: trace 里 RUN 帧的总数。与 ``run_frames`` 之差就是被版本切换切掉的
    #: 帧数——把这个差记下来，是因为"判定用了多少证据"必须可回答：
    #: 只有 run_frames 的话，一次基于 2 帧的判定与一次基于 60 帧的判定
    #: 在日志里长得一样。
    trace_frames: int = 0
    #: 记忆通道门没开的帧——模型连"记不记"都没被问。
    gate_closed: int = 0
    #: 门开了但模型选择 store=False 的帧。**这是一个决定，不是缺失。**
    declined: int = 0
    #: 模型请求了记忆写入、且请求到达了环境的次数。
    #: 是**请求级**不是入库级：Environment._apply_memory 在看到
    #: ``MemoryWrite.store=True`` 时发 MEMORY_STORED，容量淘汰 / 合并 /
    #: ``writable=False`` 都在那之后，由 ``memory.stats.writes`` 说。
    #: Δθ 关心的是模型的行为，不是记忆系统的收纳，故请求级正是要的量。
    store_requests: int = 0
    #: 真的命中了的检索次数（按 MEMORY_RETRIEVED 事件的去重 id 计）。
    retrieved: int = 0
    #: 惊奇分位数以上的帧数。
    surprising: int = 0
    #: 惊奇、且记忆门没开的帧数。**症状 1 的判据。**
    missed_surprise: int = 0

    @property
    def has_run(self) -> bool:
        return self.run_frames > 0


class PlasticityController:
    """07 §6.7 的判定方：这个更新在不在 ``allowed_scope`` 里。

    本类**不持有结构状态**，也不产出提案。它只回答两个问题：
    ``allows(kind, target)`` 与 ``clip(target, desired)``。
    """

    def __init__(self, scope: PlasticityScope | None = None) -> None:
        self.scope = scope or PlasticityScope()

    def allows(self, kind: str, target: str) -> tuple[bool, str]:
        """(kind, target) 是否在可更新范围内。

        先查 ``NON_UPDATABLE`` 再查 ``kinds`` / ``bounds``——顺序有意：
        一张显式的禁止清单应当**先于**白名单匹配，否则将来若有人把
        "verification_gate" 加进 kinds，禁止清单会被白名单悄悄盖掉。
        """

        if kind in NON_UPDATABLE or target in NON_UPDATABLE:
            return False, f"{kind}/{target!r} 在 07 §6.7 不可更新清单里"
        if kind not in self.scope.kinds:
            return False, (
                f"结构类别 {kind!r} 不在 allowed_scope.kinds="
                f"{list(self.scope.kinds)} 里"
            )
        if target not in self.scope.bounds:
            return False, (
                f"键 {target!r} 没有登记边界；未登记的键不可改"
                f"（白名单，不是黑名单）"
            )
        return True, ""

    def bounds_of(self, target: str) -> tuple[float, float]:
        """取某键的合法区间。未登记则 KeyError——调用方必须先 allows()。"""

        return self.scope.bounds[target]

    def clip(self, target: str, desired: float) -> float:
        """把期望值夹进合法区间。**不判断 min_step**——那是提案侧的职责。"""

        low, high = self.scope.bounds[target]
        return float(min(max(float(desired), low), high))

    def step_toward(
        self, target: str, current: float, direction: float
    ) -> float:
        """从 ``current`` 朝 ``direction`` 的方向走一步（不超过 max_step），
        再夹进合法区间。``direction`` 只取符号：-1 = 放宽，+1 = 收紧。
        """

        delta = self.scope.max_step if direction > 0 else -self.scope.max_step
        return self.clip(target, float(current) + delta)


class LocalPlasticity:
    """trace + 结构 → Δθ 提案（07 §6.7 + 08 §4.2）。

    用法::

        plasticity = LocalPlasticity()
        obs = plasticity.observe(trace)              # 诊断，纯读
        for p in plasticity.propose(trace, store.snapshot()):
            store.commit(p, gate.check(p, store.snapshot()), t)

    本类**不提交任何东西**。与增量 2 的同一条纪律：编译 / 验证 / 应用是三个
    问题。也不评估提案好不好——提案的生死由淘汰函数决定，不由本模块排序（C9）。
    """

    def __init__(
        self,
        config: PlasticityConfig | None = None,
        controller: PlasticityController | None = None,
    ) -> None:
        self.config = config or PlasticityConfig()
        self.controller = controller or PlasticityController()

    # ------------------------------------------------------------------
    #  观测（纯读）
    # ------------------------------------------------------------------

    def observe(self, trace: Sequence[StepRecord]) -> PlasticityObservation:
        """trace → 症状。**不产出提案**，可单独调用做诊断。

        只统计**当前结构版本**产出的那一段帧（见 ``_current_window``）。
        这不是省算力，是归因：换版之前那些帧上的"门没开"是旧策略的账，
        把它们算进新策略会得到一个只降不升的棘轮。
        """

        window = _current_window(trace)
        if not window:
            return PlasticityObservation()

        surprises = [float(r.feedback.prediction_error) for r in window]
        cut = _quantile(surprises, self.config.surprise_quantile)

        gate_closed = declined = surprising = missed = 0
        for record, error in zip(window, surprises):
            mem = record.decoded_action.memory
            if mem is None:
                gate_closed += 1
                recorded = False
            elif mem.store:
                recorded = True
            else:
                declined += 1
                recorded = True  # 门开了、模型决定了——不是缺失
            if error >= cut:
                surprising += 1
                if not recorded:
                    missed += 1

        return PlasticityObservation(
            run_frames=len(window),
            trace_frames=sum(1 for r in trace if r.state == STATE_RUN),
            gate_closed=gate_closed,
            declined=declined,
            store_requests=len(_event_ids(window, "MEMORY_STORED")),
            retrieved=len(_event_ids(window, "MEMORY_RETRIEVED")),
            surprising=surprising,
            missed_surprise=missed,
        )

    # ------------------------------------------------------------------
    #  提案
    # ------------------------------------------------------------------

    def propose(
        self,
        trace: Sequence[StepRecord],
        structure: FastLoopContext | None = None,
    ) -> tuple[SelfModificationProposal, ...]:
        """trace → Δθ 提案。**不提交、不过门。**"""

        obs = self.observe(trace)
        if not obs.has_run:
            return ()

        out: list[SelfModificationProposal] = []

        # 症状 1：值得记的帧上，门从没开过。
        if obs.missed_surprise > 0:
            proposal = self._propose(
                kind="thresholds",
                target=self.config.memory_gate_key,
                current=_current_value(structure, "thresholds", self.config.memory_gate_key),
                direction=-1.0,
                reason=(
                    f"{obs.missed_surprise}/{obs.surprising} 个惊奇帧上记忆门未开"
                    f"（run={obs.run_frames} gate_closed={obs.gate_closed}）"
                ),
                effect={"missed_surprise": obs.missed_surprise, "surprising": obs.surprising},
            )
            if proposal is not None:
                out.append(proposal)

        # 症状 2：写进去了，却从来读不回来。
        # 关系断言，要足够长的窗口才配叫"从来"（见 min_evidence_frames）。
        if (
            obs.store_requests > 0
            and obs.retrieved == 0
            and obs.run_frames >= self.config.min_evidence_frames
        ):
            proposal = self._propose(
                kind="retrieval",
                target=self.config.similarity_key,
                current=_current_value(
                    structure, "retrieval", self.config.similarity_key
                ),
                direction=-1.0,
                reason=(
                    f"请求写入 {obs.store_requests} 次但检索零命中"
                    f"（run={obs.run_frames}）"
                ),
                effect={
                    "store_requests": obs.store_requests,
                    "retrieved": obs.retrieved,
                },
            )
            if proposal is not None:
                out.append(proposal)

        return tuple(out)

    # ------------------------------------------------------------------
    #  内部
    # ------------------------------------------------------------------

    def _propose(
        self,
        *,
        kind: str,
        target: str,
        current: float,
        direction: float,
        reason: str,
        effect: Mapping[str, int],
    ) -> SelfModificationProposal | None:
        """造一条 UPDATE_THRESHOLD / UPDATE_RETRIEVAL_POLICY 提案。

        返回 None 表示**不该提**：越界，或这一步的变化量小于 min_step。
        """

        allowed, why = self.controller.allows(kind, target)
        if not allowed:
            return None

        desired = self.controller.step_toward(target, current, direction)
        delta = abs(desired - float(current))
        if delta < self.controller.scope.min_step:
            # 已经在边界上，再"放宽"也不会动。这条沉默是有信息的：
            # 它说明症状还在，但可调范围用完了。
            return None

        ptype = "UPDATE_THRESHOLD" if kind == "thresholds" else "UPDATE_RETRIEVAL_POLICY"
        return SelfModificationProposal(
            proposal_id=f"{self.config.proposal_prefix}-{target}",
            proposal_type=ptype,
            target=target,
            payload={"value" if kind == "thresholds" else "policy": desired},
            reason=reason,
            expected_effect=dict(effect),
            # 局部可塑性的作用半径就是这一个键，且方向被 allowed_scope 夹住。
            # 这不是乐观估计——是这一级改动的真实半径。
            risk_level="low",
        )


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def _current_window(trace: Sequence[StepRecord]) -> list[StepRecord]:
    """trace 里**当前结构版本**产出的那一段 RUN 帧。

    判据是 ``StepRecord.context_fingerprint``——那个字段的文档写的是
    "行为改变的归因依据（08 §2.1）"，这里就是它的第一个消费者。取最后一段
    与末帧同指纹的连续 RUN 帧。

    为什么必须切这一刀：慢环拿到的 trace 是**整条 episode**，而 Δθ 的规则
    是"症状还在就再走一步"。不切窗口的话，第一次换版之前那些"门没开"的帧
    会永远留在证据里，于是每条规则每次睡眠都再触发一次，一路推到边界上
    才停——那不是"收敛到合适的阈值"，是"撞到夹子"。实测（seed 2）：
    不切窗口时三轮睡眠把 memory_gate_threshold 从 0.5 推到 0.4 → 0.3 → 0.15
    （下界），而第二、三轮的触发证据全部来自第一轮之前。

    切了窗口之后，同一轨迹的行为是：第一轮提案，换版后新窗口里
    ``missed_surprise == 0``，于是**不再提案**——症状消失了，这是规则该有的
    样子。规则修的是"当前版本的问题"，不是"历史上的问题"。

    指纹为空（``versions={}``）时退化为整条 trace：没有版本信息就没有归因
    可言，此时的行为与不切窗口一致，而不是抛异常。
    """

    run = [r for r in trace if r.state == STATE_RUN]
    if not run:
        return []

    last = run[-1].context_fingerprint
    if not last:
        return run

    window: list[StepRecord] = []
    for record in reversed(run):
        if record.context_fingerprint != last:
            break
        window.append(record)
    window.reverse()
    return window


def _event_ids(trace: Iterable[StepRecord], event_type: str) -> set[str]:
    """trace 里某类事件的去重 id 集合。

    按 id 去重而不是按帧计数：环境的 ``events`` 是**滚动窗口**
    （``max_events=16``），同一事件会连续出现在十几帧的观测里，
    按帧数会把一次写入数成十几次。

    另外注意**有一帧滞后**：``observe_model_event`` 在 ``step()`` 返回观测
    之后才调用，所以帧 t 发出的事件出现在帧 t+1 的观测里。滞后一帧不影响
    计数，只影响"哪一帧"的归因。
    """

    out: set[str] = set()
    for record in trace:
        if record.state != STATE_RUN:
            continue
        for event in record.observation.events:
            if event.event_type == event_type:
                out.add(event.event_id)
    return out


def _quantile(values: Sequence[float], q: float) -> float:
    """分位数。空序列返回 0.0（调用方已保证非空，这里是防御）。"""

    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    frac = pos - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


def _current_value(
    structure: FastLoopContext | None, kind: str, target: str
) -> float:
    """结构里某键的当前值。快照没给（或键不存在）时用 DEFAULT_BOUNDS 的中点。

    取中点而不是 0：0 对阈值是"恒开"，对相似度是"恒命中"，两个都是
    机制被关掉而不是机制取默认值。中点是"没有信息时的中立位置"。
    """

    if structure is not None:
        table = getattr(structure, kind, None)
        if table and target in table:
            return float(table[target])
    low, high = DEFAULT_BOUNDS[target]
    return (low + high) / 2.0


__all__ = [
    "DEFAULT_BOUNDS",
    "DEFERRED_SCOPES",
    "IMPLEMENTED_SCOPES",
    "NON_UPDATABLE",
    "UPDATABLE_SCOPES",
    "LocalPlasticity",
    "PlasticityConfig",
    "PlasticityController",
    "PlasticityObservation",
    "PlasticityScope",
]
