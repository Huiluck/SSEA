"""Experience Compiler —— 经验编译器（Milestone 4 增量 2）。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.6 + 模块 D1。

职责（07 §6.6 原文）：

    将原始行为轨迹编译为可复用结构。

输入：动作序列 / 观测序列 / 反馈序列 / 成功失败结果 / 能量变化。
输出：技能提案 / 规则提案 / 记忆摘要 / 局部参数更新提案。

这是 SSEA 慢环的核心模块，也是慢环公式（08 §4.2）里
``ExperienceCompiler(ΔM, ΔS, ΔR, Δθ)`` 的那一项。

本模块刻意不做的事
------------------

**不提交任何东西。** 编译、验证、应用是三个不同的问题：

    编译器决定「提什么」
    Gate  决定「能不能安全应用」      （增量 1，已完成）
    Store 决定「应用不应用」

把三者捏在一起，就没法单独回答「提得对不对」——而那正是慢环最该被测的
部分。所以 ``compile()`` 返回提案，提交是调用方的事（见 ``run_slow_loop``）。

**不评估提案好不好。** 与 Gate 同一条纪律（C9：只有淘汰函数，没有评分函数）。
编译器按**世界计价物**（能量）决定提不提，不按任何内部偏好排序。
07 §6.6 把「成功/失败结果」列为输入，而 SSEA 里成功的判据只有一个：
净能量收益为正。不用奖励函数。

**不自己发明 Δ。** ΔS 复用 ``skill_library.compile_skills`` 那份切分规则。
两份规则必然漂移，而漂移的表现是「同一条轨迹编译出两条语义相同的技能」——
那种不一致在运行时报错里看不见，只会在审计日志里表现为重复提案。

已实现与未实现的 Δ
----------------

**已实现**：ΔS（技能提案）。``SkillLibrary.compile_from_trace`` 自 Milestone 3
就存在但无触发器——编译器就是那个触发器。这是 07 §18 第 7 项
「模型可以将成功行为固化为技能」缺的那半条。

**未实现**：ΔR / ΔM。它们各有自己的增量，且都不是空壳能敷衍的：

    ΔR  RuleCompiler     增量 4。要从 trace 提规则，判据尚未设计。
    ΔM  记忆摘要         增量 5。可继承判据已实现但无消费者（HeritableFilter）。

**已实现但不归本模块**：Δθ。生产者是 ``plasticity.LocalPlasticity``（增量 3），
由 ``run_slow_loop`` 一并接进慢环。它记在 ``DELEGATED_DELTAS`` 而不是
``DEFERRED_DELTAS``——「有人管但不是我」与「没人管」是两件不同的事，
审计日志要能分辨。

这里**不写返回空 tuple 的占位方法**——一个永远为空的函数就是死代码，
而「协议不容无消费者的通道」这条纪律对函数同样成立（08 §2.4）。
未实现的 Δ 以 ``DEFERRED_DELTAS`` 常量声明，并由
``tests/test_experience_compiler.py::TestDeferredDeltas`` 守着：
增量落地时那条测试会失败，强迫文档同步更新。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .sse_protocols import (
    FastLoopContext,
    SelfModificationProposal,
    Skill,
)
from .sse_protocols.structure_store import (
    PROPOSAL_KIND_MAP,
    AuditRecord,
    StructureStore,
)
from .skill_library import SkillLibraryConfig, compile_skills

# ----------------------------------------------------------------------
#  导入 StepRecord 只为类型标注。它在 fast_loop 里定义，而 fast_loop 不 import
#  本模块——慢环钩子是调用方注入的，方向不能反。
# ----------------------------------------------------------------------
from .fast_loop import StepRecord  # noqa: TC001  (TYPE_CHECKING 之外的运行时需要)


#: 已实现的 Δ。见模块 docstring。
IMPLEMENTED_DELTAS: tuple[str, ...] = ("ΔS",)

#: 已实现、但**不由本模块**产出的 Δ → 生产者是谁。
#: 与 DEFERRED_DELTAS 分开：审计日志要能回答「这个 Δ 有人管吗」，
#: 而「有人管但不是我」与「没人管」是两件不同的事。
DELEGATED_DELTAS: Mapping[str, str] = {
    "Δθ": (
        "LocalPlasticity（plasticity.py，增量 3）。结构侧阈值与检索策略已通；"
        "参数侧见 plasticity.DEFERRED_SCOPES"
    ),
}

#: 未实现的 Δ → 归属哪个增量、为什么现在不做。
#: 键集由 TestDeferredDeltas 守着：增量落地必须同步改这里。
DEFERRED_DELTAS: Mapping[str, str] = {
    "ΔR": "RuleCompiler 是增量 4；从 trace 提规则的判据尚未设计",
    "ΔM": "记忆摘要归 HeritableFilter（增量 5）；is_heritable() 已实现但无消费者",
}


@dataclass(frozen=True)
class ExperienceConfig:
    """Experience Compiler 配置。"""

    #: 技能编译配置。与 SkillLibrary 共用同一份，避免两套切分规则漂移。
    skill: SkillLibraryConfig = field(default_factory=SkillLibraryConfig)

    #: 提案 id 前缀。审计日志里能看出这条提案是谁提的。
    proposal_prefix: str = "exp"

    #: 是否跳过**结构里已有**的技能。
    #: 默认 True：编译器该提「新东西」，重复提案只会污染 Gate 的通过率统计。
    #: 设 False 可观察「不过滤时 Gate 会拒掉多少重复项」。
    skip_existing: bool = True


@dataclass(frozen=True)
class CompileResult:
    """一次编译的产物。

    ``proposals`` 与 ``skipped`` 分开是有意的：审计日志要能回答「我们看到了
    一条可编译的成功轨迹，为什么没提案」。只有 proposals 的话，那次沉默
    与「什么都没看到」在日志里不可区分。
    """

    #: 要提交的提案，按编译顺序。
    proposals: tuple[SelfModificationProposal, ...]

    #: 编译出来了但没提案的，形如 ``(skill_id, 原因)``。
    skipped: tuple[tuple[str, str], ...] = ()

    @property
    def compiled(self) -> int:
        """看到了多少条可编译的成功轨迹（提案的 + 跳过的）。"""
        return len(self.proposals) + len(self.skipped)


class ExperienceCompiler:
    """把一条 trace 编译成一组自我修改提案（07 §6.6）。

    用法::

        compiler = ExperienceCompiler()
        result = compiler.compile(trace, structure=store.snapshot())
        for p in result.proposals:
            record = store.commit(p, gate.check(p, store.snapshot()), t)

    本类**不持有结构状态**，也不持有 Store。结构由调用方以快照形式传入，
    只用于「这个技能是不是已经有了」这一问。
    """

    def __init__(self, config: ExperienceConfig | None = None) -> None:
        self.config = config or ExperienceConfig()

    # ------------------------------------------------------------------
    #  主入口
    # ------------------------------------------------------------------

    def compile(
        self,
        trace: Sequence[StepRecord],
        structure: FastLoopContext | None = None,
    ) -> CompileResult:
        """trace → 提案。**不提交任何东西。**

        ``structure`` 给定时跳过已有技能；不给时全部提案（Gate 会在格式级
        拒掉重复项，但那会把审计日志填满噪音）。
        """

        candidates = compile_skills(trace, self.config.skill)

        proposals: list[SelfModificationProposal] = []
        skipped: list[tuple[str, str]] = []
        seen: set[str] = set()

        existing = set(structure.skills) if structure is not None else set()

        for skill in candidates:
            if skill.skill_id in seen:
                # 同一批里两条轨迹签名相同。提两条会让第二条被 Gate 以
                # 「目标已存在」拒掉——那是噪音，不是信息。
                skipped.append((skill.skill_id, "本批内已有同签名的技能"))
                continue
            seen.add(skill.skill_id)

            if self.config.skip_existing and skill.skill_id in existing:
                skipped.append((skill.skill_id, "结构里已有该技能"))
                continue

            proposals.append(self._propose_skill(skill))

        return CompileResult(proposals=tuple(proposals), skipped=tuple(skipped))

    # ------------------------------------------------------------------
    #  内部
    # ------------------------------------------------------------------

    def _propose_skill(self, skill: Skill) -> SelfModificationProposal:
        """一条编译出来的技能 → 一条 ADD_SKILL 提案。

        ``origin`` 留 None：这不是本能内化（08 §3.4 的
        ``consolidated_from:<skill_id>``），是首次固化。内化的条件是
        success_count ≥ K 且被执行帧数 ≥ F，那条路属于增量 3/4。

        ``proposal_id`` 由**提案内容**导出（``前缀-目标``），不由调用次数导出。
        计数器式的 id（``exp-000001``、``exp-000002``）会让同一条 trace 在两次
        编译下得到两个不同的 id，于是三个后果：

        - ``compile()`` 不是纯函数，「同样的输入同样的输出」无法断言，
          而这条性质正是「不恒真」的对偶——恒真编译器坏在输出与输入无关，
          计数器坏在输出与**调用历史**有关，两者都让提案不可复现；
        - 审计日志里同一条技能会出现两行不同 id 的记录，「这是重复提案」
          要一次集合运算才能回答；
        - Gate 的可复现性（见 ``GateConfig.env_seed`` 的注释）缺了上游一半。

        用目标做 id 还有一个好处：审计日志里一眼能看出这条提案是关于哪个
        技能的，不必去 payload 里翻。重复提案现在**看起来就是重复的**。
        """

        return SelfModificationProposal(
            proposal_id=f"{self.config.proposal_prefix}-{skill.skill_id}",
            proposal_type="ADD_SKILL",
            target=skill.skill_id,
            payload={"skill": skill},
            reason=(
                f"compiled frames={skill.total_frames()} "
                f"outcome={skill.expected_outcome.get('outcome', '?')}"
            ),
            expected_effect={
                "frames": skill.total_frames(),
                "energy_change": float(
                    skill.expected_outcome.get("energy_change", 0.0)
                ),
                "energy_cost_per_frame": skill.energy_cost,
            },
            # 新增一条技能不碰任何已有结构，失败天然回滚（版本号不切换）。
            # 这不是乐观估计——是这一级改动的真实半径。
            risk_level="low",
        )


# ----------------------------------------------------------------------
#  慢环一步：编译 → 过门 → 提交
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class SlowLoopOutcome:
    """慢环一步的结果。"""

    #: 每条提案的提交记录，含被拒的（``applied=False``）。
    records: tuple[AuditRecord, ...]

    #: 有提案被应用时的新快照；否则 None——**旧快照继续有效**，
    #: 这就是 08 §2.1 的「失败天然回滚」：没有东西被应用，故无需回滚。
    context: FastLoopContext | None

    @property
    def applied(self) -> int:
        return sum(1 for r in self.records if r.applied)

    @property
    def rejected(self) -> int:
        return sum(1 for r in self.records if not r.applied)


def run_slow_loop(
    trace: Sequence[StepRecord],
    store: StructureStore,
    gate,  # VerificationGate；不 import 以避免环依赖
    compiler: ExperienceCompiler | None = None,
    plasticity: "LocalPlasticity | None" = None,  # noqa: F821 - 见下方 import
    timestamp: float = 0.0,
) -> SlowLoopOutcome:
    """慢环公式（08 §4.2）的第一步可执行形式::

        for p in ExperienceCompiler(ΔM, ΔS, ΔR, Δθ):
            VerificationGate(p) → pass ? StructureStore.commit(p, v+1) : reject

    **不抛异常。** 拒绝是正常路径：``commit()`` 自己会记 ``applied=False``
    并保持版本号。调用方（快环的 SLEEP 钩子）因此不需要 try/except。

    Gate 每次检查都取**新快照**而不是复用一个。代价是每条提案一次深拷贝，
    收益是提案 2 看到提案 1 应用后的结构——否则「同批里两条提案互相冲突」
    这种情况会被静默放过。

    ΔS 与 Δθ 的顺序
    ---------------
    编译器在前、可塑性在后，**这个顺序不承载任何语义**：两者产出的提案
    落在互不相交的结构类别（skills vs thresholds/retrieval），谁也不读谁的
    快照。定一个顺序只是为了让它确定——审计日志必须可复现。
    """

    comp = compiler if compiler is not None else ExperienceCompiler()
    result = comp.compile(trace, structure=store.snapshot())

    proposals = list(result.proposals)
    if plasticity is not None:
        proposals.extend(plasticity.propose(trace, store.snapshot()))

    records: list[AuditRecord] = []
    for proposal in proposals:
        verdict = gate.check(proposal, store.snapshot())
        records.append(store.commit(proposal, verdict, timestamp))

    applied = any(r.applied for r in records)
    return SlowLoopOutcome(
        records=tuple(records),
        context=store.snapshot() if applied else None,
    )


def make_slow_loop_hook(
    store: StructureStore,
    gate,
    compiler: ExperienceCompiler | None = None,
    plasticity: "LocalPlasticity | None" = None,  # noqa: F821
):
    """造一个能直接传给 ``FastLoop(slow_loop=...)`` 的钩子。

    钩子类型是 ``Callable[[trace], FastLoopContext | None]``——返回 None 表示
    「这轮睡眠没有改变结构」，快环于是继续用旧快照。见
    ``fast_loop.py::SlowLoopHook``。

    ``plasticity`` 给了才接 Δθ：没给就只跑编译器。这条默认值的理由是
    「协议不容无消费者的通道」——把一个恒返回空提案的组件接进去，
    只会让审计日志多一类永远不出现的行。
    """

    def hook(trace: tuple[StepRecord, ...]) -> FastLoopContext | None:
        return run_slow_loop(trace, store, gate, compiler, plasticity).context

    return hook


__all__ = [
    "DELEGATED_DELTAS",
    "DEFERRED_DELTAS",
    "IMPLEMENTED_DELTAS",
    "CompileResult",
    "ExperienceCompiler",
    "ExperienceConfig",
    "SlowLoopOutcome",
    "make_slow_loop_hook",
    "run_slow_loop",
]
