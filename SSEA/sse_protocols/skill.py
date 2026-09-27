"""8.11 Skill —— 可执行技能。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.3
（Skill Runner）与 §3.4（instinct adapter 内化规则）。

07 §8.11 定义了 ``action_sequence: list[Action]``，但十个模块里**没有一个**
负责把序列逐帧执行——技能被定义了，却无法运行。08 §2.3 新增 Skill Runner
（第 11 模块）补上这个执行方。

本协议的修订：``precondition`` 的**检查方**明确为 Skill Runner。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .action import Action


@dataclass(frozen=True)
class Skill:
    """一条技能：多步动作序列 + 前置条件 + 预期结果 + 使用统计。

    字段对应 07 §8.11 原文，未增删。

    ``precondition`` 由 **Skill Runner** 在逐帧执行前后检查（08 §2.3）：
    前置条件不再满足即中断并回报 ``SKILL_FAILURE``。

    ``success_count`` / ``failure_count`` / ``last_used`` 由 Skill Runner
    累计，同时是 instinct adapter 内化判定的输入（见 ``is_consolidatable``）。
    """

    skill_id: str
    name: str
    precondition: dict
    action_sequence: tuple[Action, ...]
    expected_outcome: dict
    success_count: int
    failure_count: int
    energy_cost: float
    created_from: str
    last_used: float

    #: 附加元数据，不参与协议字段比较。
    #: 用于 08 §3.4 的 ``origin`` 标记（如 "consolidated_from:<skill_id>"）。
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action_sequence:
            raise ValueError(
                f"技能 {self.skill_id!r} 的 action_sequence 不能为空"
            )
        if self.energy_cost < 0:
            raise ValueError(f"energy_cost 不能为负: {self.energy_cost}")
        for i, sub in enumerate(self.action_sequence):
            if not sub.is_executable():
                raise ValueError(
                    f"技能 {self.skill_id!r} 第 {i} 个子动作不可执行"
                )

    @property
    def origin(self) -> str | None:
        """技能或 adapter 的来源标记。对应 08 §3.4 的 origin 语义。"""
        return self.metadata.get("origin")

    def total_frames(self) -> int:
        """该技能执行完需多少帧。Skill Runner 的帧预算依据。"""
        return len(self.action_sequence)

    def is_consolidatable(
        self,
        min_success_count: int = 3,
        min_executed_frames: int = 30,
    ) -> bool:
        """是否满足本能内化条件。对应 08 §3.4 的两条：

            - 该技能 ``success_count ≥ K``
            - 且被 Skill Runner 累计执行的帧数 ≥ F

        帧数由 Skill Runner 在运行时累计并写入 ``metadata`` 的
        ``executed_frames``；协议只定义判据，不持有运行时状态。

        满足条件时由 Experience Compiler 提议固化为 instinct adapter，
        标记 ``origin: "consolidated_from:<skill_id>"``，进入基因包可遗传。
        """

        executed = int(self.metadata.get("executed_frames", 0))
        return (
            self.success_count >= min_success_count
            and executed >= min_executed_frames
        )
