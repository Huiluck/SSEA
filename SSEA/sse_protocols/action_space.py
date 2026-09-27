"""8.4 ActionSpace —— 动作空间声明。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.4
（移除 latent 块）。

07 §8.4 原文含 ``latent`` 子块：

    "latent": {"latent_action_vector": "R^d"}

已删除。理由见 action.py 的同名修订说明：**协议中不允许存在无消费者的通道**。

ActionSpace 是**声明**，不是菜单。它声明模型可以产出哪几类结构化控制量，
与 07 §8.2 移除 ``available_actions`` 是同一条立场的两面——动作空间由架构定义，
不由环境罗列。

混合动作空间（连续 + 离散 + 参数化 + 技能）本身不是新东西；SSEA 的新意在
**动作必须可执行**这条硬约束，见 action.py。
"""

from __future__ import annotations

from dataclasses import dataclass


#: 离散操作全集。对应 07 §8.4 ``discrete.manipulation.operation``。
#: 注意 "none" 是合法操作——"本帧什么都不做"是可执行动作，不是空动作。
OPERATIONS: tuple[str, ...] = (
    "none",
    "grasp",
    "push",
    "pull",
    "use_tool",
    "release",
)


@dataclass(frozen=True)
class ActionSpace:
    """动作空间声明。

    第一阶段只记录维度和取值范围，不持有可学习参数——ActionSpace 是接口约定，
    不是模型组件。Action Decoder（Milestone 2）是它的消费者。
    """

    #: 连续通道： locomotion.direction / locomotion.speed /
    #: manipulation.force / manipulation.duration
    continuous_dims: dict[str, int]

    #: 离散通道取值集合。
    discrete_values: dict[str, tuple[str, ...]]

    #: 参数化通道是否启用（target_id / skill.params）。
    parametric_enabled: bool = True

    #: 技能通道是否启用。关闭时 Action.skill 必须为空。
    skill_enabled: bool = True

    def __post_init__(self) -> None:
        for name, dim in self.continuous_dims.items():
            if dim <= 0:
                raise ValueError(f"连续通道 {name!r} 维度必须为正: {dim}")
        for name, values in self.discrete_values.items():
            if not values:
                raise ValueError(f"离散通道 {name!r} 不能为空")

    def is_valid_operation(self, operation: str) -> bool:
        return operation in OPERATIONS


def default_action_space() -> ActionSpace:
    """第一阶段最小动作空间：2D 世界，无 z 轴。

    刻意不给"全维度"默认空间——空间维度必须由环境声明，否则协议层就在替
    环境做决定。
    """
    return ActionSpace(
        continuous_dims={
            "locomotion.direction": 2,
            "locomotion.speed": 1,
            "manipulation.force": 1,
            "manipulation.duration": 1,
        },
        discrete_values={
            "manipulation.operation": OPERATIONS,
        },
    )
