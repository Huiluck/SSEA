"""State Core —— 状态核心。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.2 +
docs/08-dual-loop-interface-and-gap-closure.md §2.5。

职责：维护模型内部状态，形成行动意图。

输入（07 §6.2 + 08 §2.5 补 ``internal_drive``）：:

    perception_vector      # p_t
    memory_context         # m_t
    body_state             # b_t（紧凑编码）
    internal_drive         # d_t ← 08 §2.5 新增
    h_{t-1}                # 上一帧 hidden_state

输出：:

    hidden_state           # h_t
    intent_vector          # 行动意图

算子选型：**GRU**
--------------
07 §6.2 列出 GRU / Mamba / 小型 SSM / Liquid NN / Sparse Transformer / Small MoE
六个候选，未指定。第一阶段选 GRU，理由：

1. **它是 L1 算子层，可替换**。docs/09 §2 明确 SSEA 的创新在 L2/L3/L4，
   不在 L1。选最成熟的算子降低工程风险，把验证成本留给车架。
2. **单步推理无需额外内核**。``torch.nn.GRU`` 在 CPU 上逐步调用即可，
   不需要 CUDA graph 或自定义 scan——第一阶段要的是闭环跑通。
3. **状态即隐藏态，无额外缓存**。低带宽目标下，hidden_state 是唯一需要
   跨帧携带的东西。

选 GRU 不构成架构声明——它只是第一个被插进 State Core 接口的算子。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import torch
import torch.nn as nn

from .sse_protocols import BodyState
from .tensorize import as_vector

#: body_state 喂给 GRU 的紧凑编码维度：energy, damage, fatigue。
BODY_INPUT_DIM = 3

#: internal_drive_vector 维度。由 08 §2.5 固定为 4。
DRIVE_DIM = 4


@dataclass(frozen=True)
class StateCoreConfig:
    """State Core 配置。"""

    #: perception_vector 维度。必须与 PerceptionConfig.perception_dim 一致。
    perception_dim: int = 64

    #: memory_context 维度。Milestone 3 的 Memory System 产出同维向量。
    memory_dim: int = 16

    #: GRU 隐藏维度 = hidden_state 维度。
    hidden_dim: int = 64

    #: intent_vector 维度。
    intent_dim: int = 32

    def __post_init__(self) -> None:
        if self.hidden_dim <= 0 or self.intent_dim <= 0:
            raise ValueError("hidden_dim / intent_dim 必须为正")


class StateCore(nn.Module):
    """GRU 状态核心。

    ``forward`` 单步调用：输入本帧各向量与上一帧 hidden_state，
    输出新 hidden_state 与 intent_vector。

    **不含 batch 维**。第一阶段单智能体、单进程，逐帧推理；加 batch 会
    让所有调用点都多一层 unsqueeze，而收益要等到多模型阶段（v0.4+）。
    """

    def __init__(self, config: StateCoreConfig | None = None) -> None:
        super().__init__()
        self.config = config or StateCoreConfig()
        cfg = self.config

        self.gru = nn.GRU(
            input_size=cfg.perception_dim + cfg.memory_dim + BODY_INPUT_DIM + DRIVE_DIM,
            hidden_size=cfg.hidden_dim,
            num_layers=1,
            batch_first=True,
        )
        self.intent_head = nn.Sequential(
            nn.Linear(cfg.hidden_dim, cfg.intent_dim),
            nn.Tanh(),
        )

    def initial_hidden(self) -> torch.Tensor:
        """零初始 hidden_state，形状 ``[1, 1, hidden_dim]``（GRU 的 (h_0) 约定）。"""
        return torch.zeros(1, 1, self.config.hidden_dim)

    def encode_body(self, body: BodyState) -> torch.Tensor:
        """BodyState → GRU 的身体输入段。

        只取三个生存标量。位置 / 朝向已在 perception_vector 里，
        重复喂入会让 GRU 用两份编码学同一件事。
        """
        return torch.tensor(
            [body.energy, body.damage, body.fatigue], dtype=torch.float32
        )

    @staticmethod
    def encode_drive(
        internal_drive: Sequence[float] | torch.Tensor,
    ) -> torch.Tensor:
        """internal_drive_vector → 张量。

        协议层用 ``tuple[float, ...]``（sse_protocols 约定 2：向量不用
        torch，必须可序列化）。张量化发生在模型边界，见 tensorize.py。
        """

        return as_vector(internal_drive, expected=DRIVE_DIM, name="internal_drive")

    def forward(
        self,
        perception: torch.Tensor,
        memory_context: torch.Tensor,
        body: BodyState,
        internal_drive: Sequence[float] | torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """单步前向。

        参数
        ----
        perception:
            ``[perception_dim]``
        memory_context:
            ``[memory_dim]``。无记忆系统时传零向量。
        body:
            BodyState 协议对象。
        internal_drive:
            ``[DRIVE_DIM]``，来自 MetabolicMonitor.drive_vector()。
            协议原产物是 tuple，此处负责张量化。
        hidden:
            ``[1, 1, hidden_dim]``，上一帧 hidden_state。

        返回
        ----
        ``(hidden_state, intent_vector)``，形状分别为
        ``[1, 1, hidden_dim]`` 与 ``[intent_dim]``。
        """

        cfg = self.config
        parts = [
            perception.reshape(-1),
            memory_context.reshape(-1),
            self.encode_body(body),
            self.encode_drive(internal_drive),
        ]
        x = torch.cat(parts).reshape(1, 1, -1)
        if x.shape[-1] != (
            cfg.perception_dim + cfg.memory_dim + BODY_INPUT_DIM + DRIVE_DIM
        ):
            raise ValueError(
                f"输入维度不匹配：拼得 {x.shape[-1]}，"
                f"配置要求 {cfg.perception_dim}+{cfg.memory_dim}"
                f"+{BODY_INPUT_DIM}+{DRIVE_DIM}。"
                f"perception_dim 必须与 PerceptionConfig.perception_dim 一致。"
            )
        out, h_new = self.gru(x, hidden)
        intent = self.intent_head(out.reshape(-1))
        return h_new, intent

    def param_count(self) -> int:
        return sum(p.numel() for p in self.parameters())
