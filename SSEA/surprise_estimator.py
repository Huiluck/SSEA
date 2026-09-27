"""SurpriseEstimator —— 惊奇估计器。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.6.1。

定位为 **Metabolic Monitor 的子组件**，不单列为第 12 个模块——它零权重、
无梯度、纯统计（08 §2.6.1）。

对三类标量流做**一阶持久化预测**：

    标量流                    预测假设        来源
    ───────────────────────  ─────────────  ─────────────────
    energy                   下一帧 = 当前帧  BodyState
    damage                   下一帧 = 当前帧  BodyState
    nearest_resource_dist    下一帧 = 当前帧  Observation

    prediction_error_t = mean(|实际_t − 预测_t|)     # 三类归一化后取均值

**为什么不引入 World Model**：07 第 13.2 节明确不推荐重模块。一阶持久化预测
只需几行代码就能让慢环有触发器，完整状态转移模型留到 v0.4+
（docs/11 第 15 项：完整世界模型 / 梦境推演 → v0.4+）。

**为什么第一阶段必须实现**：预测误差是 SSEA 替代评分函数的核心学习信号
（doc 03：「没有显式评分函数，但有：预测误差、生存误差、能量消耗、死亡」）。
置空会让 Milestone 4 的规则生成失去触发器——重复因果关系正是从预测误差中
提炼的。
"""

from __future__ import annotations

from dataclasses import dataclass, field


#: 三类标量流的归一化尺度。distance 无上界，需显式给出观测尺度。
DEFAULT_SCALES: dict[str, float] = {
    "energy": 1.0,
    "damage": 1.0,
    "nearest_resource_dist": 10.0,
}


@dataclass
class SurpriseEstimator:
    """一阶持久化预测 + 误差 EMA。

    无权重、无梯度、无随机性——给定同样的输入序列，输出完全确定。
    这让「惊奇」成为可复现的实验指标，而不是又一个需要调参的模块。
    """

    scales: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SCALES))
    ema_alpha: float = 0.1

    #: 上一帧的各标量流实测值。缺失的流（如无资源对象时）不出现。
    _prev: dict[str, float] = field(default_factory=dict, init=False)

    #: prediction_error 的指数滑动平均，进入 internal_drive_vector。
    ema: float = field(default=0.0, init=False)

    #: EMA 是否已初始化。用显式标志而不是 ``ema == 0.0`` 判断——
    #: 长时段无误差后 EMA 会浮点衰减到恰好 0.0，那时下一个真实误差
    #: 会被误当成"第一次"而直接覆盖，而不是与历史混合。
    _ema_started: bool = field(default=False, init=False)

    #: 原始（未 EMA）的最近一次误差。
    last_error: float = field(default=0.0, init=False)

    #: 已处理的帧数。前几帧无预测基准，误差记为 0。
    frames_seen: int = field(default=0, init=False)

    def update(
        self,
        energy: float,
        damage: float,
        nearest_resource_dist: float | None,
    ) -> float:
        """喂入本帧实测值，返回本帧 prediction_error。

        ``nearest_resource_dist`` 为 None 表示视野内无资源对象。此时若上一帧
        也无资源，该流不参与均值；若上一帧有而本帧没有（或相反），视为一次
        突变——用尺度上限作为该流的误差，避免"资源消失"这种最该被注意的事件
        因缺值而被静默跳过。
        """

        observed: dict[str, float | None] = {
            "energy": energy,
            "damage": damage,
            "nearest_resource_dist": nearest_resource_dist,
        }

        if self.frames_seen == 0:
            # 第一帧：建立基线，无预测可犯。
            self._prev = {k: v for k, v in observed.items() if v is not None}
            self.frames_seen = 1
            self.last_error = 0.0
            self.ema = 0.0
            return 0.0

        errors: list[float] = []
        for name, value in observed.items():
            scale = self.scales.get(name, 1.0) or 1.0
            prev = self._prev.get(name)

            if value is None and prev is None:
                continue  # 该流本帧与上帧都不可观测
            if value is None or prev is None:
                # 出现 / 消失：按满尺度计一次突变
                errors.append(1.0)
                continue

            errors.append(abs(value - prev) / scale)

        error = sum(errors) / len(errors) if errors else 0.0

        self._prev = {k: v for k, v in observed.items() if v is not None}
        self.frames_seen += 1
        self.last_error = error
        # 首个真实误差作为 EMA 初值：若从 0 起算，surprise_ema 会在前几帧
        # 系统性低估惊奇，而那几帧恰恰是模型最需要被推一把的时候。
        if not self._ema_started:
            self.ema = error
            self._ema_started = True
        else:
            self.ema = self.ema + self.ema_alpha * (error - self.ema)
        return error

    def reset(self) -> None:
        """清空预测基线。用于基因恢复 / 新 episode 起始。"""
        self._prev.clear()
        self.ema = 0.0
        self.last_error = 0.0
        self.frames_seen = 0
        self._ema_started = False
