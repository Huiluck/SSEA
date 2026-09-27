"""Verification Gate —— 验证门。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.8 +
docs/08-dual-loop-interface-and-gap-closure.md §2.1（四级检查）。

职责：对一条自我修改提案给出二值结论——**能不能安全应用**。

    result = gate.check(proposal, store.snapshot())
    record = store.commit(proposal, result, timestamp)   # 内部自己分流

``commit()`` 不抛异常、不要求调用方先判断 ``passed``，所以慢环可以写成
一条直线，不需要 try/except 包住拒绝路径。

四级检查（顺序不可换）
------------------
::

    格式 → 沙盒 → 回归 → 小范围环境测试

任一级失败即停，``stage_failed`` 记下失败的那一级。顺序不可换是因为它
对应代价递增：格式错是纸面错误，沙盒错会污染结构，回归错会弄坏别的类别，
环境错要跑闭环。先做便宜的。

Gate 刻意不做什么
----------------
**不评估提案好不好，只评估能不能安全应用。**

SSEA 没有评分函数，只有淘汰函数（C9）。Gate 一旦开始给提案打分、按分数
排序、只放高分的过，它就变成了一个评分函数——而那正是 SSEA 立场要拒绝的
东西。Gate 的回答是二值的：合法 / 不合法。

推论：**两个提案一个让存活帧数翻倍、一个让存活帧数减半，只要两者都合法，
Gate 对它们一视同仁。** 选择权不在 Gate，在淘汰函数——活下来的那个自然被
保留，死掉的自然被淘汰。这是 07 §4.6「自我修改必须经过验证」与 C9 的接缝。

**不执行任意代码。** 08 §3.1 已把 ΔC 折叠进 ΔS，第一阶段没有代码执行。
所以「沙盒」不是代码沙盒，是**结构副本上的不变量检查**。

**不碰权重。** ``UPDATE_ADAPTER`` 改的是快照里的 adapter 配置，不是 torch
参数。参数更新走 LocalPlasticity，那条路有 07 §6.7 的不可更新对象清单管着。

**不做回滚。** ``StructureStore`` 上没有 rollback 方法——被拒的提案从未被
应用，没有东西需要回滚。Gate 的拒绝只是让 ``commit()`` 记一条
``applied=False``。

这条纪律由 ``tests/test_verification_gate.py::TestNoScoring`` 守着：
断言 ``GateResult`` 的字段集合恰为三件套，且 Gate 上没有排序 / 打分 API。
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, Mapping

from .sse_protocols import (
    FastLoopContext,
    Skill,
    SelfModificationProposal,
)
from .sse_protocols.structure_store import (
    PROPOSAL_KIND_MAP,
    GateResult,
    StructureStore,
)

#: 四级检查的名字。``GateResult.stage_failed`` 只能取这四个值。
STAGES: tuple[str, ...] = ("format", "sandbox", "regression", "env_test")

#: 每种提案类型要求 payload 里出现的键。
_REQUIRED_PAYLOAD_KEY: dict[str, str] = {
    "ADD_SKILL": "skill",
    "UPDATE_SKILL": "skill",
    "ADD_RULE": "rule",
    "UPDATE_RULE": "rule",
    "UPDATE_THRESHOLD": "value",
    "UPDATE_RETRIEVAL_POLICY": "policy",
    "UPDATE_ADAPTER": "adapter",
}

#: 全部结构类别。回归级要逐个复查。
_ALL_KINDS: tuple[str, ...] = (
    "skills",
    "rules",
    "adapters",
    "thresholds",
    "retrieval",
)

#: 新增类提案——target 必须尚不存在。
_ADD_TYPES = frozenset({"ADD_SKILL", "ADD_RULE"})

#: 移除类提案——target 必须已存在，且不需要 payload。
_REMOVE_TYPES = frozenset({"DISABLE_SKILL"})

#: 「UPDATE 即创建」类提案——target **不判存在性**。
#:
#: ``adapters`` 与 ``retrieval`` / ``thresholds`` 曾经是**同一个洞**：
#: ``UPDATE_*`` 只改已有的键，而没有任何提案能建第一个键，于是类别
#: **永远无法被初始化**。那两类当时被发现了（MemorySystem 与 ActionDecoder
#: 都要用），``adapters`` 没有——**因为当时没有任何代码读过 ``adapters``**，
#: 也就没人试过往里放第一个键。② 给它补上读取接口之后，这个洞当场暴露：
#: 一份合法的趋近先验被门拒掉，理由却是"目标 'approach' 不存在"。
#:
#: 与那两类不同的是，这里**不做合法键名检查**——因为不存在合法名清单：
#: ``instinct.decode_instinct_set`` 把所有 adapter 的偏置**全部相加**，
#: 名字纯粹是审计与遗传用的标签，不参与解码。编一份名清单等于编一份假护栏。
#:
#: 真正管住它的是**内容**而非名字：``_check_adapters`` 要求 blob 必须被
#: **真实解码器**解得开。这比名字检查强——名字检查管拼写，内容检查管
#: "下游读不读得懂"，而后者才是 13 §4.6 那个洞的成因。
#:
#: 副作用要写明：``UPDATE_ADAPTER`` 因此是 **create-or-replace**。这与另两类
#: UPDATE 的实际行为一致——``_apply_to_copy`` 与 ``StructureStore._apply``
#: 本来就是 ``current[target] = ...``，建键是它们的固有语义，此前只是被
#: 这道存在性检查挡在门外。
_CREATE_OR_UPDATE_TYPES = frozenset({"UPDATE_ADAPTER"})


@dataclass(frozen=True)
class GateConfig:
    """Verification Gate 配置。"""

    #: 环境级检查跑多少帧。要够长到能暴露崩溃，又要短到 gate 可频繁调用。
    env_frames: int = 20

    #: 环境级检查里，多少帧内死亡算「立即死亡」。
    #: 淘汰本身不是提案的错（世界可能是难的），但**装配即崩**一定是。
    env_sudden_death_frames: int = 3

    #: 环境级检查用的世界 seed。固定它是为了让 gate 的结论可复现——
    # 同一个提案在同一个结构上必须得到同一个答案。
    env_seed: int = 0

    #: 环境级检查用的解码器初始化 seed。理由同上。
    decoder_seed: int = 0


class VerificationGate:
    """对提案做四级检查，产出 ``GateResult``。

    本类**不持有结构状态**。结构由调用方以快照形式传入，Gate 只在副本上
    试算。这让 Gate 可被单独测试，也让它不可能意外改动物理结构。
    """

    def __init__(self, config: GateConfig | None = None) -> None:
        self.config = config or GateConfig()

    # ------------------------------------------------------------------
    #  主入口
    # ------------------------------------------------------------------

    def check(
        self,
        proposal: SelfModificationProposal,
        structure: FastLoopContext,
    ) -> GateResult:
        """四级检查，任一级失败即停。"""

        for stage, runner in (
            ("format", self._check_format),
            ("sandbox", self._check_sandbox),
            ("regression", self._check_regression),
            ("env_test", self._check_env),
        ):
            ok, reason = runner(proposal, structure)
            if not ok:
                return GateResult(passed=False, reason=reason, stage_failed=stage)
        return GateResult(passed=True, reason="四级检查全部通过")

    # ------------------------------------------------------------------
    #  第一级：格式
    # ------------------------------------------------------------------

    def _check_format(
        self, proposal: SelfModificationProposal, structure: FastLoopContext
    ) -> tuple[bool, str]:
        """纸面合法性。不碰结构，只看提案自己说得通。"""

        ptype = proposal.proposal_type
        kind = PROPOSAL_KIND_MAP.get(ptype)
        if kind is None:
            return False, f"提案类型 {ptype!r} 无对应结构类别"

        if not proposal.target:
            return False, "提案 target 不能为空"

        if not proposal.proposal_id:
            return False, "提案 proposal_id 不能为空（审计需要）"

        current = self._current(structure, kind)

        if ptype in _ADD_TYPES and proposal.target in current:
            return False, f"{ptype} 的目标 {proposal.target!r} 已存在"
        if ptype in _REMOVE_TYPES and proposal.target not in current:
            return False, f"{ptype} 的目标 {proposal.target!r} 不存在"
        # ``retrieval`` 与 ``thresholds`` 都是**一份扁平策略**（键即策略字段名），
        # 所以这两类提案的 target 不该按「当前存在哪些键」判——Store 刚建起来时
        # 两个类别都是空的，而 MemorySystem 会退回 DEFAULT_RETRIEVAL_POLICY、
        # ActionDecoder 会退回 config.gate_threshold。按「已存在」判会让这两个
        # 类别**永远无法被初始化**：UPDATE_* 只能改已有的键，而没有任何提案能
        # 建第一个键。
        #
        # 这里判的是「target 是不是一个合法的策略键名」，那才是这两类提案
        # 真正可能出错的地方。合法键名从各自语义的所有者取（memory_system /
        # action_decoder），不在 Gate 里另列一份——两份清单必然漂移。
        if ptype in ("UPDATE_RETRIEVAL_POLICY", "UPDATE_THRESHOLD"):
            legal = (
                _policy_keys() if ptype == "UPDATE_RETRIEVAL_POLICY"
                else _threshold_keys()
            )
            if proposal.target not in legal:
                label = "策略" if ptype == "UPDATE_RETRIEVAL_POLICY" else "阈值"
                return False, (
                    f"{ptype} 的目标 {proposal.target!r} 不是合法的{label}键；"
                    f"合法键见 {'memory_system.DEFAULT_RETRIEVAL_POLICY' if ptype == 'UPDATE_RETRIEVAL_POLICY' else 'action_decoder.GATE_THRESHOLD_KEYS'}"
                )
        elif ptype not in _ADD_TYPES | _REMOVE_TYPES | _CREATE_OR_UPDATE_TYPES and proposal.target not in current:
            return False, f"{ptype} 的目标 {proposal.target!r} 不存在"

        if ptype in _REMOVE_TYPES:
            return True, ""

        key = _REQUIRED_PAYLOAD_KEY.get(ptype)
        if key is None:  # pragma: no cover - 两表由同一处维护
            return False, f"提案类型 {ptype!r} 未登记 payload 键"
        if key not in proposal.payload:
            return False, f"payload 缺少必需键 {key!r}"
        value = proposal.payload[key]
        if value is None:
            return False, f"payload[{key!r}] 不能为 None"

        if ptype in ("ADD_SKILL", "UPDATE_SKILL"):
            if not isinstance(value, Skill):
                return False, f"payload['skill'] 必须是 Skill，实为 {type(value).__name__}"
            if value.skill_id != proposal.target:
                return False, (
                    f"技能 id 与 target 不一致: "
                    f"{value.skill_id!r} != {proposal.target!r}"
                )

        if ptype == "UPDATE_THRESHOLD" and not isinstance(value, (int, float)):
            return False, f"payload['value'] 必须是数值，实为 {type(value).__name__}"

        return True, ""

    # ------------------------------------------------------------------
    #  第二级：沙盒
    # ------------------------------------------------------------------

    def _check_sandbox(
        self, proposal: SelfModificationProposal, structure: FastLoopContext
    ) -> tuple[bool, str]:
        """把提案应用到结构**副本**上，副本仍满足该类别的不变量。

        沙盒与回归的分工：沙盒查**这一个提案引入的**问题，回归查**它有没有
        弄坏别的**。前者是「新东西合法吗」，后者是「旧东西还活着吗」。
        """

        kind = PROPOSAL_KIND_MAP[proposal.proposal_type]
        candidate = self._apply_to_copy(structure, kind, proposal)
        return self._invariants_for(kind, candidate, proposal)

    # ------------------------------------------------------------------
    #  第三级：回归
    # ------------------------------------------------------------------

    def _check_regression(
        self, proposal: SelfModificationProposal, structure: FastLoopContext
    ) -> tuple[bool, str]:
        """候选结构仍通过**全部类别**的不变量，不只是被改的那一个。

        一个 ``UPDATE_THRESHOLD`` 提案理论上不该弄坏技能库，但「理论上」
        不是保证。逐个类别复查的代价是 O(类别数)，可以忽略。
        """

        kind = PROPOSAL_KIND_MAP[proposal.proposal_type]
        candidate = self._apply_to_copy(structure, kind, proposal)
        for other in _ALL_KINDS:
            ok, reason = self._invariants_for(other, candidate, proposal)
            if not ok:
                return False, f"回归: {reason}"
        return True, ""

    # ------------------------------------------------------------------
    #  第四级：小范围环境测试
    # ------------------------------------------------------------------

    def _check_env(
        self, proposal: SelfModificationProposal, structure: FastLoopContext
    ) -> tuple[bool, str]:
        """用候选结构装配快环跑一小段。不崩溃、不立即死亡。

        只查**装配与运行**是否成立，不查跑得好不好——后者是淘汰函数的职权
        （C9）。所以这里没有分数、没有「比原来更好」的比较。
        """

        from .environment import Environment
        from .fast_loop import FastLoop, FastLoopConfig

        kind = PROPOSAL_KIND_MAP[proposal.proposal_type]
        candidate = self._apply_to_copy(structure, kind, proposal)

        try:
            env = Environment(seed=self.config.env_seed)
            loop = FastLoop(
                env,
                candidate,
                config=FastLoopConfig(
                    max_frames=self.config.env_frames,
                    min_sleep_frames=1,
                ),
            )
            loop.run(self.config.env_frames)
        except Exception as exc:  # noqa: BLE001 - 崩溃即拒绝，不向外传
            return False, f"候选结构下闭环异常: {type(exc).__name__}: {exc}"

        if not env.alive and len(loop.trace()) <= self.config.env_sudden_death_frames:
            return False, (
                f"候选结构下 {len(loop.trace())} 帧内死亡——"
                f"装配即崩，不是世界太难"
            )
        return True, ""

    # ------------------------------------------------------------------
    #  内部
    # ------------------------------------------------------------------

    @staticmethod
    def _current(structure: FastLoopContext, kind: str) -> Mapping[str, Any]:
        return {
            "skills": structure.skills,
            "rules": structure.rules,
            "adapters": structure.adapters,
            "thresholds": structure.thresholds,
            "retrieval": structure.retrieval,
        }[kind]

    @staticmethod
    def _apply_to_copy(
        structure: FastLoopContext,
        kind: str,
        proposal: SelfModificationProposal,
    ) -> FastLoopContext:
        """在结构的副本上应用提案，返回**新**的 FastLoopContext。

        复制而非原地改，是为了保证传入的 ``structure`` 永不被 Gate 修改——
        调用方传的是快照，快照的不可变性是「快环零改动」的前提，Gate 没有
        特权破例。
        """

        target = proposal.target
        ptype = proposal.proposal_type
        current = dict(
            {
                "skills": structure.skills,
                "rules": structure.rules,
                "adapters": structure.adapters,
                "thresholds": structure.thresholds,
                "retrieval": structure.retrieval,
            }[kind]
        )

        if ptype == "DISABLE_SKILL":
            current.pop(target, None)
        elif ptype in ("ADD_SKILL", "UPDATE_SKILL"):
            current[target] = proposal.payload["skill"]
        elif ptype in ("ADD_RULE", "UPDATE_RULE"):
            current[target] = proposal.payload["rule"]
        elif ptype == "UPDATE_THRESHOLD":
            current[target] = float(proposal.payload["value"])
        elif ptype == "UPDATE_RETRIEVAL_POLICY":
            # 与 StructureStore._apply 同形：target 是策略键名，policy 是它的新值。
            # 这里不能写 current[target] = dict(policy)——那会把一份整策略塞进一个
            # 键里，产出的 retrieval 过不了 _check_retrieval，也会让 MemorySystem 崩。
            current[target] = proposal.payload["policy"]
        elif ptype == "UPDATE_ADAPTER":
            current[target] = proposal.payload["adapter"]

        return _replace_kind(structure, kind, current)

    def _invariants_for(
        self,
        kind: str,
        candidate: FastLoopContext,
        proposal: SelfModificationProposal,
    ) -> tuple[bool, str]:
        """某个类别的不变量。返回 ``(是否满足, 不满足的原因)``。"""

        if kind == "skills":
            return _check_skills(candidate.skills)
        if kind == "thresholds":
            return _check_thresholds(candidate.thresholds)
        if kind == "retrieval":
            return _check_retrieval(candidate.retrieval)
        if kind == "adapters":
            return _check_adapters(candidate.adapters)
        if kind == "rules":
            return True, ""
        return True, ""  # pragma: no cover - _ALL_KINDS 是闭集


def _replace_kind(
    structure: FastLoopContext, kind: str, value: Mapping[str, Any]
) -> FastLoopContext:
    """返回一个只替换了某个类别的新 FastLoopContext。"""

    from dataclasses import replace

    return replace(structure, **{kind: dict(value)})


# ----------------------------------------------------------------------
#  各类别的不变量
# ----------------------------------------------------------------------


def _check_skills(skills: Mapping[str, Any]) -> tuple[bool, str]:
    """技能库不变量：值都是 Skill、id 唯一、id 与键一致、序列非空。"""

    seen: set[str] = set()
    for key, value in skills.items():
        if not isinstance(value, Skill):
            return False, f"技能 {key!r} 的值不是 Skill，实为 {type(value).__name__}"
        if value.skill_id != key:
            return False, (
                f"技能键与 id 不一致: {key!r} != {value.skill_id!r}"
            )
        if value.skill_id in seen:
            return False, f"技能 id 重复: {value.skill_id!r}"
        seen.add(value.skill_id)
        if not value.action_sequence:
            return False, f"技能 {key!r} 的 action_sequence 为空"
    return True, ""


def _check_thresholds(thresholds: Mapping[str, Any]) -> tuple[bool, str]:
    """阈值不变量：值都是有限实数。"""

    import math

    for key, value in thresholds.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, f"阈值 {key!r} 不是数值，实为 {type(value).__name__}"
        if not math.isfinite(float(value)):
            return False, f"阈值 {key!r} 不是有限值: {value!r}"
    return True, ""


def _check_adapters(adapters: Mapping[str, Any]) -> tuple[bool, str]:
    """adapter 不变量：值都是 bytes、非空，**且真的解得开**。

    第一阶段的 adapter 是**权重片段**而非配置 dict——这是 08 §2.1 注入物
    五类里唯一直接携带参数的一类，所以它的形状必须被管住。

    「非空 bytes」这一条**不够**，而补上的这一条是 13 §4.6 的教训的直接应用：
    **Store 只管版本号与审计，不保证下游读得懂。** 一份长度不对、版本不认识、
    形状是 3×7 的 blob 完全可以是"非空 bytes"，一路过门、升版本、进快照，
    然后在快环的**下一帧**上被静默丢弃——行为毫无变化，而审计里写着"已应用"。
    这与 ``UPDATE_RETRIEVAL_POLICY`` 当年写出下游读不懂的形状是同一个洞
    （债务 7），只是那次快环崩了所以被发现，这次不会崩，只会安静地少一个行为。

    **校验调用真实的解码器，不另写一份格式检查。** 两份格式知识必然漂移，
    而漂移的方向是固定的：门这边更宽松，于是门放行了一份快环用不了的东西。
    """

    from .instinct import decode_instinct

    for key, value in adapters.items():
        if not isinstance(value, (bytes, bytearray)):
            return False, (
                f"adapter {key!r} 必须是 bytes，实为 {type(value).__name__}"
            )
        if not value:
            return False, f"adapter {key!r} 为空"
        if decode_instinct(value) is None:
            return False, (
                f"adapter {key!r} 不是可解码的本能 blob（长度 {len(value)}）——"
                "提交后快环会静默丢弃它，行为不会有任何变化"
            )
    return True, ""


def _check_retrieval(retrieval: Mapping[str, Any]) -> tuple[bool, str]:
    """检索策略不变量：整份扁平策略能通过 MemorySystem 的校验。

    **校验的是整份映射，不是逐个值。** 这不是风格选择：``MemorySystem`` 把
    ``context.retrieval`` 整个交给 ``validate_retrieval_policy``，所以能进快环的
    形状只有「一份扁平策略」。逐值校验会放过 ``{"top_k": 2, "stride": "x"}``
    之外的任何畸形——包括把一个整策略塞进某个键里。

    复用 ``validate_retrieval_policy`` 而不是在 Gate 里另写一份规则——
    两份规则必然漂移，而漂移的校验比没有校验更糟。
    """

    from .memory_system import validate_retrieval_policy

    try:
        validate_retrieval_policy(retrieval, memory_dim=_memory_dim())
    except Exception as exc:  # noqa: BLE001 - 校验失败即拒绝
        return False, f"检索策略不合法: {exc}"
    return True, ""


def _policy_keys() -> frozenset[str]:
    """合法的检索策略键名。

    从 ``DEFAULT_RETRIEVAL_POLICY`` 取而不是另列一份——两份清单必然漂移，
    而漂移会让一个拼错的键名通过格式级、在运行时才炸。
    """

    from .memory_system import DEFAULT_RETRIEVAL_POLICY

    return frozenset(DEFAULT_RETRIEVAL_POLICY)


def _threshold_keys() -> frozenset[str]:
    """合法的行为阈值键名。

    从 ``action_decoder.GATE_THRESHOLD_KEYS`` 取：那是这些阈值的**语义所有者**，
    它说"这个键控制哪个通道的门控"。Gate 不另列一份，理由同 ``_policy_keys``。
    """

    from .action_decoder import GATE_THRESHOLD_KEYS

    return frozenset(GATE_THRESHOLD_KEYS.values())


def _memory_dim() -> int:
    """State Core 期望的 ``m_t`` 维度。

    Gate 需要一个具体的维度才能校验 ``top_k`` 与 ``memory_dim`` 的整除关系。
    取 StateCoreConfig 的默认值——它与 MemorySystem 的默认策略是同一条约定。
    """

    from .state_core import StateCoreConfig

    return StateCoreConfig().memory_dim


__all__ = [
    "STAGES",
    "GateConfig",
    "VerificationGate",
]


# 让 ``GateResult`` 的字段集合可被测试断言（TestNoScoring 守「没有分数字段」）。
GATE_RESULT_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(GateResult))
