"""8.9 Feedback —— 环境反馈。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.6.1
（补 prediction_error 的生产者）。

07 §8.9 原文含 ``prediction_error`` 字段，但 v0.3.1 的十个模块里
**没有 World Model、没有 Predictor**——字段无生产者。

修订后：

    生产者 = Metabolic Monitor 的 SurpriseEstimator 子组件（08 §2.6.1）
    算法   = 对 energy / damage / nearest_resource_dist 三类标量流
             做一阶持久化预测，取归一化绝对误差的均值

        prediction_error_t = mean(|实际_t − 预测_t|)

该值同时经 EMA 进入 ``internal_drive_vector.surprise_ema``（08 §2.5）。
第一阶段置空会让 Milestone 4 的规则生成失去触发器，故 Milestone 1
必须把生产者写进协议。

**Feedback 不是评分函数。** 它是环境对动作后果的客观反馈（07 §8.9 原文）。
SSEA 不设奖励函数，只有淘汰函数（C9）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feedback:
    """一步反馈。字段对应 07 §8.9 原文，未增删。

    ``survived`` 由环境判定。死亡判定权归环境，不归模型侧的任何模块
    （08 §3.6：淘汰函数在模型之外，模型物理上碰不到它）。
    """

    energy_change: float
    damage_change: float
    fatigue_change: float
    prediction_error: float
    action_success: bool
    survived: bool
    notes: str = ""

    def __post_init__(self) -> None:
        if self.prediction_error < 0:
            raise ValueError(
                f"prediction_error 不能为负: {self.prediction_error}"
            )
