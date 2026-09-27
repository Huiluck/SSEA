"""EnvironmentSummary —— 环境摘要。

定义来源：docs/05-ssea-v0.3-charter.md §7.3（07 §8.1 引用但未重载）。

第一阶段保持极简，不实现四季与灾害
（docs/11-phase1-not-doing-list.md 第 1、2 项）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentSummary:
    """环境级标量摘要，与对象级 ObjectVector 互补。

    字段对应 05 §7.3 原文，未增删。
    """

    light_level: float
    temperature: float
    danger_level: float
    resource_density: float
    time_phase: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.danger_level <= 1.0:
            raise ValueError(f"danger_level 应在 [0,1]: {self.danger_level}")
