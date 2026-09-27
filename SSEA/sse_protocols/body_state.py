"""8.2 BodyState —— 身体状态。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.5。

07 §8.2 已移除 ``available_actions``（动作不是字符串菜单）。
本模块另按 08 §2.5 明确 ``action_constraints`` 的**强制执行语义**——
约束由 ActionConstraints.violations() 定义规则，Action Decoder 与
Environment 两个执行点共用，见 action_constraints.py。

``internal_state`` 是模型侧内部状态的对外镜像（如 State Core 的
hidden_state 摘要），不参与决策，仅供观察员与审计。
"""

from __future__ import annotations

from dataclasses import dataclass

from .action_constraints import ActionConstraints


@dataclass(frozen=True)
class BodyState:
    """身体状态。字段对应 07 §8.2 修订后原文，未增删。

    注意：身体状态由环境提供，是**镜像**而非模型自有属性——
    模型侧只读，不修改（见 10-boundary-definition-table.md 代谢条目：
    环境真实扣减能量与损伤，模型侧只有镜像）。
    """

    energy: float
    damage: float
    fatigue: float
    position: tuple[float, ...]
    orientation: tuple[float, ...]
    action_constraints: ActionConstraints
    internal_state: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.energy < 0:
            raise ValueError(f"energy 不能为负: {self.energy}")
        if self.damage < 0:
            raise ValueError(f"damage 不能为负: {self.damage}")
        if not 0.0 <= self.fatigue <= 1.0:
            raise ValueError(f"fatigue 应在 [0,1]: {self.fatigue}")

    def is_starving(self, threshold: float = 0.0) -> bool:
        """能量是否已低于阈值。睡眠判定的输入之一（08 §2.2）。"""
        return self.energy <= threshold
