"""8.12 SelfModificationProposal —— 自我修改提案。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §3.1
（ΔC 折叠进 ΔS）与 §3.4（origin 语义）。

07 §8.12 的 ``proposal_type`` 列表无 CODE 类型，而慢环公式却有
``ΔC = CodeProposal(trace, f_t)``——产物是孤儿。修订后：

    - 第一阶段**不开放任意代码执行**
    - ΔC 折叠进 ΔS：代码仅作为 ``Skill.action_sequence`` 内的代码段存在，
      归入 ``ADD_SKILL`` / ``UPDATE_SKILL`` 两类提案，从而自动经过
      Verification Gate

理由：C6 要求可自主修改自身代码，但 07 第 16 节要求所有自我修改必须可回滚。
开放任意执行违背此条（docs/11 第 13 项）。
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: 允许的 proposal_type。对应 07 §8.12 原文，未增删。
#: 第一阶段代码只能以技能代码段形式存在，故无独立 CODE 类型（08 §3.1）。
ALLOWED_PROPOSAL_TYPES: tuple[str, ...] = (
    "UPDATE_SKILL",
    "ADD_SKILL",
    "DISABLE_SKILL",
    "UPDATE_RULE",
    "ADD_RULE",
    "UPDATE_THRESHOLD",
    "UPDATE_RETRIEVAL_POLICY",
    "UPDATE_ADAPTER",
)

#: 第一阶段明确不允许的 proposal_type。对应 07 §8.12 原文。
FORBIDDEN_PROPOSAL_TYPES: tuple[str, ...] = (
    "UPDATE_CORE_OS",
    "UPDATE_VERIFICATION_GATE",
    "UPDATE_ENV_INTERFACE",
    "UPDATE_GENE_PERMISSION",
    "UPDATE_OBSERVER_INTERFACE",
)

#: origin 前缀。对应 08 §3.4：本能 = 被反复验证后压缩成权重形式的行为先验。
ORIGIN_CONSOLIDATED_PREFIX = "consolidated_from:"


@dataclass(frozen=True)
class SelfModificationProposal:
    """一条自我修改提案。字段对应 07 §8.12 原文 + 08 §3.4 新增 ``origin``。

    提案**不直接修改任何结构**。它经 Verification Gate 通过后由
    Structure Store 提升版本号，快环读取新快照（08 §2.1）。
    """

    proposal_id: str
    proposal_type: str
    target: str
    payload: dict = field(default_factory=dict)
    reason: str = ""
    expected_effect: dict = field(default_factory=dict)
    risk_level: str = "medium"
    origin: str | None = None

    def __post_init__(self) -> None:
        if self.proposal_type not in ALLOWED_PROPOSAL_TYPES:
            if self.proposal_type in FORBIDDEN_PROPOSAL_TYPES:
                raise ValueError(
                    f"提案类型 {self.proposal_type!r} 在第一阶段明确不允许；"
                    f"见 FORBIDDEN_PROPOSAL_TYPES"
                )
            raise ValueError(
                f"未定义的提案类型 {self.proposal_type!r}；"
                f"合法值见 ALLOWED_PROPOSAL_TYPES"
            )
        if self.risk_level not in ("low", "medium", "high"):
            raise ValueError(
                f"risk_level 必须是 low / medium / high: {self.risk_level!r}"
            )

    @property
    def is_skill_code_carrier(self) -> bool:
        """该提案是否携带代码段。第一阶段代码只走这条路（08 §3.1）。"""
        return self.proposal_type in ("ADD_SKILL", "UPDATE_SKILL")

    @classmethod
    def consolidated_from(cls, skill_id: str, **kwargs: object) -> SelfModificationProposal:
        """构造一条本能内化提案。对应 08 §3.4。

        产物写入 ``instinct_adapters``，可遗传。这是 doc 01「内化成类似
        本能传递到下一代」的第一阶段最小实现。
        """

        kwargs.setdefault("proposal_type", "UPDATE_ADAPTER")
        kwargs.setdefault("target", "instinct_adapters")
        kwargs.setdefault("reason", f"技能 {skill_id} 满足内化条件")
        return cls(origin=f"{ORIGIN_CONSOLIDATED_PREFIX}{skill_id}", **kwargs)  # type: ignore[arg-type]
