"""Metabolic Monitor —— 代谢监控器。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.5
（internal_drive 接线）、§2.2（慢环触发器与睡眠期）、§3.6（死亡判定权归属）。

**2026-09-27 对 08 §2.2 的一处修订**：睡眠判据从三条减为两条，移除
``energy ≥ 0.7``。那一条与 ``fatigue ≥ 0.6`` 在默认代谢参数下算术互斥，
使慢环的唯一常规入口永不可达——不是「难触发」，是**恒不触发**。
推导与实测见 :meth:`MetabolicMonitor.wants_sleep`。

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
    #:
    #: **只有两条**——08 §2.2 原本写的是三条（还有 ``energy ≥ 0.7``），
    #: 那一条是错的，2026-09-27 移除。理由见 :meth:`wants_sleep`。
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
        """慢环 SLEEP 触发器的判据：无迫近威胁 + 疲劳累积。

        两条同时满足才进入睡眠期。刻意不用 OR——睡眠期是一等公民状态，
        入口必须窄，否则模型会靠反复睡眠逃避生存压力。

        **能量不参与判定**（2026-09-27 修订，移除 08 §2.2 原列的第三条
        ``energy ≥ 0.7``）。理由有两条，各自独立成立。

        **一、合取取到的是空集，不是窄入口。** 能量单调降、疲劳单调升：

            fatigue ≥ 0.6   fatigue_rate = 0.02  → 最早第 30 帧成立
            energy ≥ 0.7    base_drain  = 0.01   → 最晚第 30 帧跌破
                                                 （含移动则第 20–25 帧）

        要求「能量充裕」**且**「已经累了」，等于要求这两条反向曲线在时间上
        相交。它们只在第 30 帧附近擦肩，一旦有移动就彻底错开。实测 8 个
        seed（200 帧、接真慢环钩子）：**0/8 进入过睡眠**，唤醒 0、提案 0，
        均寿命 67.0 帧。慢环的**唯一常规入口**不是「难触发」，是恒不触发。

        **二、更根本的是，能量作为入口条件会自我复制。** 把能量单独拿出来当
        条件（``safe ∧ energy ≥ 0.7``）实测是**双峰退化**：

            4/8 seed  锁进「睡-醒-睡」循环，**65%–72% 的寿命在睡眠中度过**，
                      26–28 次唤醒，却只产出 0–1 条提案——RUN 帧被切成
                      1 帧碎片，慢环无事可做。**模型学会了不行动。**
            4/8 seed  能量在威胁解除前就跌破 0.7，**从不睡眠**，67–70 帧死。

        原因是结构性的：``Environment.rest()`` 不扣基础代谢、反而每帧
        ``+0.01`` 能量（见其 docstring——「若睡眠也耗能，模型就没有理由进入
        睡眠期，慢环的唯一常规入口会被生存压力挤掉」）。于是「能量充裕」
        是睡眠自己生产出来的前提，构成正反馈，不动就是最优策略。
        **拿「余粮」当门槛，筛出来的是不行动。**

        疲劳判据没有这个问题，因为它是自限的：睡眠期每帧恢复 0.15，醒来即
        归零，要再攒约 30 帧才够，天然存在不应期。实测 ``safe ∧ F ≥ 0.6``
        下睡眠只占寿命的 6%–12%，RUN 帧 66–74 帧，足以让慢环编译。

        08 §2.2 的原话是「在**安全**时允许无损整理经验」，正确的读法是：
        **安全是本质条件，疲劳是自然的进入理由，能量不参与判定。**
        「入口必须窄」这个顾虑由疲劳单独承担——它量的是需要，不是富余。

        .. note::
           上面的数字是 2026-09-27 在本项目实测的（8 seed × 200 帧、
           ``min_sleep_frames = 5``、接 ``make_slow_loop_hook``）。
           早先记录的「8/8 可达」未能复现，已按实测改为 7/8——唯一未睡的
           seed 0 是**安全条件在正确拒绝**（``threat`` 恒 0.929，
           附近有危险源而它无法转向），不是判据缺陷。
        """

        return (
            observation.max_threat_level() <= self.sleep_threat_threshold
            and body.fatigue >= self.sleep_fatigue_threshold
        )

    def sleep_blockers(
        self, body: BodyState, observation: Observation
    ) -> tuple[str, ...]:
        """返回未满足的睡眠条件名。空元组表示可以睡。

        用于调试与观察员输出——"为什么还不睡"应当是可回答的。

        只报**判据**里真实存在的条件。能量不参与判定，所以即使能量很低
        这里也不报 ``energy_below_threshold``——一个永远不影响结论的
        blocker 会让「为什么还不睡」的答案变成假话。
        """

        blockers: list[str] = []
        if observation.max_threat_level() > self.sleep_threat_threshold:
            blockers.append("threat_imminent")
        if body.fatigue < self.sleep_fatigue_threshold:
            blockers.append("fatigue_insufficient")
        return tuple(blockers)

    def reset(self) -> None:
        """清空惊奇基线。用于基因恢复 / 新 episode 起始。"""
        self.surprise.reset()
