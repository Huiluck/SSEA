"""8.3 ActionConstraints —— 动作约束协议。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.6.2
（约束强制执行双点）。

ActionConstraints 是**约束**，不是动作。它描述模型这一步被允许做什么的边界，
本身不产生任何动作。

双点强制执行（08 §2.6.2）
-------------------------
    ┌─────────────────┐        ┌──────────────┐
    │  Action Decoder │ ──裁剪──►│  Environment │
    │  （第一执行点）  │        │ （第二执行点）│
    └─────────────────┘        └──────────────┘
    主路径：输出前即裁剪/否决     防御性复核：不崩溃，记 ACTION_FAILED

两个执行点共用本模块的 ``ActionConstraints.violations()``——规则只有一份，
放在协议里，避免两处漂移。

第二点为何必要：Skill Runner 吐出的子动作序列跨越多个步长，期间约束可能变化
（如 energy_budget 下降），Environment 必须能兜住（08 §2.6.2）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionConstraints:
    """动作约束。第一阶段全部字段必填，无默认值——约束缺失即协议违背。

    字段对应 07 §8.3 原文，未增删。
    """

    max_speed: float
    max_force: float
    max_duration: float
    allowed_operations: tuple[str, ...]
    forbidden_targets: tuple[str, ...]
    energy_budget: float
    can_communicate: bool
    can_store_memory: bool
    can_call_skill: bool
    can_self_modify: bool

    def __post_init__(self) -> None:
        if self.max_speed < 0:
            raise ValueError(f"max_speed 不能为负: {self.max_speed}")
        if self.max_force < 0:
            raise ValueError(f"max_force 不能为负: {self.max_force}")
        if self.max_duration <= 0:
            raise ValueError(f"max_duration 必须为正: {self.max_duration}")
        if self.energy_budget < 0:
            raise ValueError(f"energy_budget 不能为负: {self.energy_budget}")

    # ------------------------------------------------------------------
    # 强制执行规则（第一 / 第二执行点共用）
    # ------------------------------------------------------------------

    def violations(self, action: object) -> list[str]:
        """返回 action 违反的约束列表；空列表表示合法。

        只做**可判定**的约束检查。数值型裁剪（如 speed > max_speed 时截断）
        属于 Action Decoder 的策略，不属于协议的合法性判定——协议回答
        "这个动作是否被允许"，不回答"这个动作该被怎么改"。
        """
        out: list[str] = []
        loco = getattr(action, "locomotion", None)
        if loco is not None:
            if loco.speed > self.max_speed:
                out.append(
                    f"locomotion.speed={loco.speed} 超过 max_speed={self.max_speed}"
                )
            if loco.duration > self.max_duration:
                out.append(
                    f"locomotion.duration={loco.duration} 超过 "
                    f"max_duration={self.max_duration}"
                )

        manip = getattr(action, "manipulation", None)
        if manip is not None:
            if manip.force > self.max_force:
                out.append(
                    f"manipulation.force={manip.force} 超过 max_force={self.max_force}"
                )
            if manip.duration > self.max_duration:
                out.append(
                    f"manipulation.duration={manip.duration} 超过 "
                    f"max_duration={self.max_duration}"
                )
            if manip.operation not in self.allowed_operations:
                out.append(
                    f"manipulation.operation={manip.operation!r} 不在 "
                    f"allowed_operations={list(self.allowed_operations)}"
                )
            if manip.target_id and manip.target_id in self.forbidden_targets:
                out.append(
                    f"manipulation.target_id={manip.target_id!r} 在 "
                    f"forbidden_targets 中"
                )

        comm = getattr(action, "communication", None)
        if comm is not None and not self.can_communicate:
            out.append("communication 通道被 can_communicate=False 禁止")

        mem = getattr(action, "memory", None)
        if mem is not None and mem.store and not self.can_store_memory:
            out.append("memory.store 被 can_store_memory=False 禁止")

        skill = getattr(action, "skill", None)
        if skill is not None and not self.can_call_skill:
            out.append("skill 通道被 can_call_skill=False 禁止")

        selfmod = getattr(action, "self_modification", None)
        if selfmod is not None and not self.can_self_modify:
            out.append("self_modification 通道被 can_self_modify=False 禁止")

        return out

    def permits(self, action: object) -> bool:
        """action 是否满足全部约束。violations() 的布尔形式。"""
        return not self.violations(action)


def default_constraints() -> ActionConstraints:
    """构造一份宽松约束，供测试与调试使用。

    刻意**不**作为 ActionConstraints 的字段默认值：约束缺失即协议违背，
    给一个"看起来能用"的默认值会让缺失在测试中静默通过。
    """
    return ActionConstraints(
        max_speed=1.0,
        max_force=1.0,
        max_duration=1.0,
        allowed_operations=(
            "none",
            "grasp",
            "push",
            "pull",
            "use_tool",
            "release",
        ),
        forbidden_targets=(),
        energy_budget=1.0,
        can_communicate=True,
        can_store_memory=True,
        can_call_skill=True,
        can_self_modify=True,
    )
