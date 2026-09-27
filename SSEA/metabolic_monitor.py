"""Metabolic Monitor —— 代谢监控器。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.5
（internal_drive 接线）、§2.2（慢环触发器与睡眠期）、§3.6（死亡判定权归属）。

07 §6.10 说代谢监控器输出"内部需求信号、生存压力信号、动作预算约束"三个信号，
但这三个信号**没接回任何公式**——模块定义了，线没接。本模块把线接上：

    ┌──────────────────────────────────────────────────────────┐
    │ Metabolic Monitor                                        │
    │  ├── internal_drive_vector  → State Core / Action Decoder │
    │  ├── SurpriseEstimator      → Feedback.prediction_error   │
    │  ├── sleep_judgement()      → 慢环 SLEEP 触发器            │
    │  └── （不拥有死亡判定，见下）                              │
    └──────────────────────────────────────────────────────────┘

**死亡判定权归环境**（08 §3.6）：环境在 ``energy ≤ 0`` 或 ``damage ≥ max``
时判定死亡。本模块是模型侧的**预测与预算镜像**，不拥有判定权。

这使安全约束"模型不可修改淘汰函数"天然成立——淘汰函数在模型之外，
模型物理上碰不到它，不需要靠权限系统阻止。也符合 C9：淘汰是环境对模型的
筛选，不是模型对自己的评分。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .sse_protocols import BodyState, Observation
from .surprise_estimator import SurpriseEstimator

#: internal_drive_vector 的维度。由 08 §2.5 固定，不可配置。
DRIVE_DIM = 4

#: internal_drive_vector 各分量的语义索引。
IDX_ENERGY_DEFICIT = 0
IDX_SURPRISE_EMA = 1
IDX_DAMAGE_URGENCY = 2
IDX_FATIGUE = 3


@dataclass
class MetabolicMonitor:
    """代谢监控器：产出 internal_drive_vector，兼睡眠判定。

    第一阶段实现 ``energy_deficit`` 与 ``surprise_ema`` 两项，
    ``damage_urgency`` 与 ``fatigue`` **置 0 预留**（08 §2.5）：

        > ``energy_deficit`` 与 ``surprise_ema`` 第一阶段实现，其余置 0 预留
        > （符合 C8：给结构先验，不给满能力）。

    注意这与"BodyState 有 fatigue 字段"不矛盾——BodyState.fatigue 是环境
    提供的真实身体状态，睡眠判定会读它；此处置 0 是指它**不进入
    internal_drive_vector**，即不作为模型的第 3 / 4 号内在驱动力。
    """

    surprise: SurpriseEstimator = field(default_factory=SurpriseEstimator)

    #: 睡眠判定阈值。位于 behavior_policy 可经 UPDATE_THRESHOLD 提案修改，
    #: 故此处是默认值而非常量。
    sleep_energy_threshold: float = 0.7
    sleep_threat_threshold: float = 0.05
    sleep_fatigue_threshold: float = 0.6

    def observe(self, observation: Observation) -> float:
        """消费一步 Observation，更新惊奇估计并返回本帧 prediction_error。

        这是 ``Feedback.prediction_error`` 的唯一生产者（08 §2.6.1）。
        """

        body = observation.body
        return self.surprise.update(
            energy=body.energy,
            damage=body.damage,
            nearest_resource_dist=observation.nearest_resource_distance(),
        )

    def drive_vector(self, body: BodyState) -> tuple[float, ...]:
        """internal_drive_vector。对应 08 §2.5 的四分量定义。

        两个消费点：

        1. State Core 的 ``internal_drive`` 输入
        2. Action Decoder 的能量预算约束来源（与 ``b_t.action_constraints`` 合并）
        """

        return (
            self._energy_deficit(body),
            self.surprise.ema,
            0.0,  # damage_urgency —— 第一阶段置 0 预留
            0.0,  # fatigue —— 第一阶段置 0 预留
        )

    @staticmethod
    def _energy_deficit(body: BodyState) -> float:
        """能量缺口，归一化到 [0,1]。1 = 完全枯竭。"""
        return max(0.0, min(1.0, 1.0 - body.energy))

    # ------------------------------------------------------------------
    #  睡眠判定（08 §2.2）
    # ------------------------------------------------------------------

    def wants_sleep(self, body: BodyState, observation: Observation) -> bool:
        """慢环 SLEEP 触发器的判据：能量充足 + 无迫近威胁 + 疲劳累积。

        三条同时满足才进入睡眠期。刻意不用 OR——睡眠期是一等公民状态，
        入口必须窄，否则模型会靠反复睡眠逃避生存压力。
        """

        return (
            body.energy >= self.sleep_energy_threshold
            and observation.max_threat_level() <= self.sleep_threat_threshold
            and body.fatigue >= self.sleep_fatigue_threshold
        )

    def sleep_blockers(
        self, body: BodyState, observation: Observation
    ) -> tuple[str, ...]:
        """返回未满足的睡眠条件名。空元组表示可以睡。

        用于调试与观察员输出——"为什么还不睡"应当是可回答的。
        """

        blockers: list[str] = []
        if body.energy < self.sleep_energy_threshold:
            blockers.append("energy_below_threshold")
        if observation.max_threat_level() > self.sleep_threat_threshold:
            blockers.append("threat_imminent")
        if body.fatigue < self.sleep_fatigue_threshold:
            blockers.append("fatigue_insufficient")
        return tuple(blockers)

    def reset(self) -> None:
        """清空惊奇基线。用于基因恢复 / 新 episode 起始。"""
        self.surprise.reset()
