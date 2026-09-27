"""8.10 MemoryItem —— 记忆项。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §3.3
（memory_index 继承语义）。

07 §8.10 只定义了字段，未定义**哪些记忆可遗传**。修订后记忆分两类，
继承策略不同：

    ┌────────────┬──────────────────────┬─────────────────────────────────┐
    │ 类别        │ type                 │ 继承策略                         │
    ├────────────┼──────────────────────┼─────────────────────────────────┤
    │ 可继承记忆  │ RULE / SKILL         │ 复制进子代 heritable_memory      │
    │ 瞬时记忆    │ EVENT / BODY_EXPERIENCE │ 只留 memory_store_ref 引用，   │
    │            │                      │ 子代不加载，仅供审计              │
    └────────────┴──────────────────────┴─────────────────────────────────┘

筛选条件：``type ∈ {RULE, SKILL}`` 且 ``importance ≥ 阈值`` 且
``retrieval_count ≥ N``。

这同时落地了 07 风险 5 的缓解措施：子代不继承瞬时记忆，记忆规模不随世代累积
（docs/11-phase1-not-doing-list.md 第 17 项：跨代记忆累积 → **永不**，
这是设计，不是延期）。
"""

from __future__ import annotations

from dataclasses import dataclass


#: 记忆类型全集。对应 08 §3.3 的两类划分。
MEMORY_TYPES: tuple[str, ...] = (
    "RULE",
    "SKILL",
    "EVENT",
    "BODY_EXPERIENCE",
)

#: 可继承记忆的类型集合。其余类型为瞬时记忆，不进基因包。
HERITABLE_TYPES: frozenset[str] = frozenset({"RULE", "SKILL"})


@dataclass(frozen=True)
class MemoryItem:
    """一条记忆。字段对应 07 §8.10 原文，未增删。

    可继承性不是新字段，而是**从既有字段推导出的判定**——见
    ``is_heritable()``。协议不为它加一个布尔标记，因为那会让标记与
    字段值失去同步。
    """

    id: str
    timestamp: float
    type: str
    context_vector: tuple[float, ...]
    content_vector: tuple[float, ...]
    outcome: str
    importance: float
    retrieval_count: int
    last_retrieved: float

    def __post_init__(self) -> None:
        if self.type not in MEMORY_TYPES:
            raise ValueError(
                f"未定义的记忆类型 {self.type!r}；合法值见 MEMORY_TYPES"
            )
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance 应在 [0,1]: {self.importance}")
        if self.retrieval_count < 0:
            raise ValueError(
                f"retrieval_count 不能为负: {self.retrieval_count}"
            )

    def is_heritable(
        self,
        importance_threshold: float = 0.5,
        min_retrieval_count: int = 1,
    ) -> bool:
        """该记忆是否可继承。对应 08 §3.3 的三条筛选条件。

        阈值由调用方（HeritableFilter，Milestone 4）给出，不写死在协议里——
        阈值属于 ``behavior_policy``，可经 UPDATE_THRESHOLD 提案修改
        （docs/07 第 8.12 节）。
        """

        return (
            self.type in HERITABLE_TYPES
            and self.importance >= importance_threshold
            and self.retrieval_count >= min_retrieval_count
        )

    @property
    def is_transient(self) -> bool:
        """是否为瞬时记忆。瞬时记忆只留引用，不随基因传递。"""
        return self.type not in HERITABLE_TYPES
