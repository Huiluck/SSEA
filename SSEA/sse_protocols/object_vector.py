"""8.6 ObjectVector —— 感知对象向量。

稀疏对象向量，不是图像。这是 C4「低带宽」在观测侧的落地：
模型看到的是若干对象的标量摘要，而非高分辨率视觉输入
（docs/11-phase1-not-doing-list.md 第 6 项：高分辨率视觉 / 多模态不做）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ObjectVector:
    """单个感知对象的稀疏向量摘要。

    字段对应 07 §8.6 原文，未增删。

    ``category_id`` 是离散类别，不由模型解释语义；``affordance`` 是
    可供性向量，由环境标注该对象支持哪些操作。
    """

    object_id: str
    category_id: int
    distance: float
    direction: tuple[float, ...]
    velocity: tuple[float, ...]
    resource_value: float
    threat_level: float
    affordance: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.distance < 0:
            raise ValueError(f"distance 不能为负: {self.distance}")
        if not 0.0 <= self.threat_level <= 1.0:
            raise ValueError(f"threat_level 应在 [0,1]: {self.threat_level}")
