"""8.1 Observation —— 观测。

07 §8.1 原文的字段结构，未修订。全部子协议见各自模块。

对应 07 §7.1 环境接口强制规则的另一半：

    env.step(action: Action) -> tuple[Observation, Feedback]

Observation 中**不含自然语言描述**。控制闭环不使用 tokenizer、
不使用 language head（07 §7.2）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .body_state import BodyState
from .communication_signal import CommunicationSignal
from .environment_summary import EnvironmentSummary
from .event_vector import EventVector
from .object_vector import ObjectVector


@dataclass(frozen=True)
class Observation:
    """一步观测。字段对应 07 §8.1 原文，未增删。

    ``objects`` 与 ``events`` 是稀疏列表——第一阶段环境只需返回视野内的
    对象与近期事件，不需要全量世界状态（C4 低带宽）。
    """

    time: float
    body: BodyState
    environment: EnvironmentSummary
    objects: tuple[ObjectVector, ...] = ()
    events: tuple[EventVector, ...] = ()
    social_signals: tuple[CommunicationSignal, ...] = ()

    def nearest_resource_distance(self) -> float | None:
        """最近资源对象的距离；无资源对象时返回 None。

        SurpriseEstimator 的三类标量流之一（08 §2.6.1）。
        """

        best: float | None = None
        for obj in self.objects:
            if obj.resource_value <= 0:
                continue
            if best is None or obj.distance < best:
                best = obj.distance
        return best

    def max_threat_level(self) -> float:
        """视野内最高威胁等级；无威胁对象时为 0。

        睡眠判定「无迫近威胁」的输入之一（08 §2.2）。
        """

        return max((obj.threat_level for obj in self.objects), default=0.0)
