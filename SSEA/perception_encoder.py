"""Perception Encoder —— 感知编码器。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.1。

职责：将环境观测压缩为低维内部感知向量 ``perception_vector``。

第一阶段要求（07 §6.1 原文）：

    - 不使用高分辨率图像。
    - 不使用自然语言描述作为主输入。
    - 使用稀疏对象向量和事件向量。

本模块是 C4「低带宽」在观测侧的落地：输入是若干对象的标量摘要，
不是图像；输出是固定维向量，与视野内对象数量无关。

对象数量可变如何处理
--------------------
观测中 ``objects`` 是变长列表。编码器取**距离最近的 K 个**，不足则补零掩码。
这是"稀疏对象向量 → 定维向量"的标准做法，也是低带宽的必要条件——
若让向量长度随对象数变化，后续所有层的维度都不确定了。

可学习容量集中在唯一一个线性层里，特征打包部分无参数——这让
「感知编码器贡献了多少」可以被单独消融（对应 docs/09 §4 的检验思路）。
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

from .sse_protocols import EVENT_TYPES, Observation

#: 单个对象的标量摘要维度：distance, resource_value, threat_level,
#: direction(2), velocity(2)。对应 ObjectVector 去掉 id / category / affordance。
PER_OBJECT_DIM = 7

#: 身体状态摘要维度：energy, damage, fatigue。
BODY_DIM = 3

#: 位置 / 朝向各取前 N 维（第一阶段 2D 世界）。
POSE_DIM = 2

#: 身体 internal_state 取前 N 维。
INTERNAL_STATE_DIM = 4

#: 环境摘要维度：light, temperature, danger, resource_density。
ENV_DIM = 4

#: time_phase 的 one-hot 维度。
TIME_PHASES: tuple[str, ...] = ("dawn", "day", "dusk", "night")
TIME_PHASE_DIM = len(TIME_PHASES)

#: 通信信号 pooling 维度。
SOCIAL_DIM = 4

#: event_type 嵌入维度。
EVENT_EMBED_DIM = 8

#: 单事件特征维度 = importance(1) + embedding。
PER_EVENT_DIM = 1 + EVENT_EMBED_DIM


@dataclass(frozen=True)
class PerceptionConfig:
    """感知编码器配置。"""

    #: 输出 perception_vector 维度。
    perception_dim: int = 64

    #: 参与编码的最近对象数上限。
    max_objects: int = 8

    #: 参与编码的最近事件数上限。
    max_events: int = 4

    #: 通信信号 pooling 维度。
    social_dim: int = SOCIAL_DIM

    def __post_init__(self) -> None:
        if self.perception_dim <= 0:
            raise ValueError("perception_dim 必须为正")
        if self.max_objects < 1:
            # 0 会让对象段整体消失——那不是"不感知对象"，是配置写错了。
            raise ValueError("max_objects 至少为 1")
        if self.max_events < 1:
            raise ValueError("max_events 至少为 1")
        if self.social_dim < 0:
            raise ValueError("social_dim 不能为负")

    @property
    def raw_dim(self) -> int:
        """手工特征打包后的原始维度（含事件嵌入部分）。

        由 ``features()`` 的输出长度反推校验，两者必须一致——
        ``test_perception_encoder.py::test_raw_dim_matches_features`` 守着这条。
        """

        return (
            BODY_DIM
            + POSE_DIM * 2
            + INTERNAL_STATE_DIM
            + ENV_DIM
            + TIME_PHASE_DIM
            + self.max_objects * (PER_OBJECT_DIM + 1)  # +1 = 存在掩码
            + self.max_events * PER_EVENT_DIM
            + self.social_dim
        )


class PerceptionEncoder(nn.Module):
    """Observation → perception_vector。

    结构：手工特征打包 → 线性投影 → LayerNorm → GELU。
    """

    def __init__(self, config: PerceptionConfig | None = None) -> None:
        super().__init__()
        self.config = config or PerceptionConfig()
        self.event_embed = nn.Embedding(len(EVENT_TYPES), EVENT_EMBED_DIM)
        self.projection = nn.Sequential(
            nn.Linear(self.config.raw_dim, self.config.perception_dim),
            nn.LayerNorm(self.config.perception_dim),
            nn.GELU(),
        )

    # ------------------------------------------------------------------
    #  特征打包（无参数）
    # ------------------------------------------------------------------

    def features(self, observation: Observation) -> torch.Tensor:
        """Observation → 1D 原始特征张量。

        分两段：标量段直接拼装；事件段需过嵌入表，最后cat。
        """

        cfg = self.config
        parts: list[float] = []

        body = observation.body
        parts += [body.energy, body.damage, body.fatigue]
        parts += _pad(body.position, POSE_DIM)
        parts += _pad(body.orientation, POSE_DIM)
        parts += _pad(body.internal_state, INTERNAL_STATE_DIM)

        env = observation.environment
        parts += [
            env.light_level,
            env.temperature,
            env.danger_level,
            env.resource_density,
        ]
        parts += _one_hot(env.time_phase, TIME_PHASES)

        # 对象：按距离升序取前 K 个
        objects = sorted(observation.objects, key=lambda o: o.distance)
        for i in range(cfg.max_objects):
            if i < len(objects):
                obj = objects[i]
                parts += [
                    obj.distance,
                    obj.resource_value,
                    obj.threat_level,
                    *_pad(obj.direction, 2),
                    *_pad(obj.velocity, 2),
                    1.0,  # 存在掩码
                ]
            else:
                parts += [0.0] * (PER_OBJECT_DIM + 1)

        # 通信信号：pooling 前 social_dim 维
        if observation.social_signals:
            pooled = [0.0] * cfg.social_dim
            for sig in observation.social_signals:
                for j in range(min(cfg.social_dim, len(sig.signal))):
                    pooled[j] += sig.signal[j]
            n = len(observation.social_signals)
            parts += [v / n for v in pooled]
        else:
            parts += [0.0] * cfg.social_dim

        scalar = torch.tensor(parts, dtype=torch.float32)

        # 事件：按 timestamp 降序取前 M 个
        events = sorted(observation.events, key=lambda e: e.timestamp, reverse=True)
        event_ids: list[int] = []
        event_imp: list[float] = []
        for i in range(cfg.max_events):
            if i < len(events):
                ev = events[i]
                event_ids.append(EVENT_TYPES.index(ev.event_type))
                event_imp.append(ev.importance)
            else:
                event_ids.append(0)  # padding id；importance=0 使其不产生影响
                event_imp.append(0.0)

        emb = self.event_embed(torch.tensor(event_ids, dtype=torch.long))
        imp = torch.tensor(event_imp, dtype=torch.float32).unsqueeze(1)
        event_feat = torch.cat([imp, emb], dim=1).flatten()

        return torch.cat([scalar, event_feat])

    # ------------------------------------------------------------------
    #  前向
    # ------------------------------------------------------------------

    def forward(self, observation: Observation) -> torch.Tensor:
        """Observation → perception_vector（形状 ``[perception_dim]``）。"""

        return self.projection(self.features(observation))


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def _pad(values: tuple[float, ...], size: int) -> list[float]:
    """补齐 / 截断到定长。"""
    out = list(values[:size])
    out += [0.0] * (size - len(out))
    return out


def _one_hot(value: str, vocab: tuple[str, ...]) -> list[float]:
    return [1.0 if value == v else 0.0 for v in vocab]
