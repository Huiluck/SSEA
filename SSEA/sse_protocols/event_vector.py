"""8.7 EventVector —— 事件向量。

事件是环境对"刚刚发生了什么"的客观记录，不是奖励。
SSEA 不设评分函数（C9），事件流与 Feedback 共同构成生存后果的来源。
"""

from __future__ import annotations

from dataclasses import dataclass


#: 事件类型全集。对应 07 §8.7 原文列举的 14 种。
EVENT_TYPES: tuple[str, ...] = (
    "OBJECT_FOUND",
    "OBJECT_LOST",
    "ENERGY_GAINED",
    "ENERGY_LOST",
    "DAMAGE_RECEIVED",
    "ACTION_FAILED",
    "ACTION_SUCCESS",
    "SKILL_SUCCESS",
    "SKILL_FAILURE",
    "MEMORY_STORED",
    "MEMORY_RETRIEVED",
    "SELF_MOD_PROPOSED",
    "SELF_MOD_APPLIED",
    "SELF_MOD_ROLLBACK",
)


@dataclass(frozen=True)
class EventVector:
    """单个事件的稀疏向量记录。字段对应 07 §8.7 原文，未增删。

    ``context_vector`` 是事件发生时的上下文摘要，供慢环的 SkillCompiler /
    RuleCompiler 检索（Milestone 4）。
    """

    event_id: str
    timestamp: float
    event_type: str
    source_id: str
    context_vector: tuple[float, ...]
    importance: float

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES:
            raise ValueError(
                f"未定义的事件类型 {self.event_type!r}；"
                f"合法值见 EVENT_TYPES"
            )
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance 应在 [0,1]: {self.importance}")
