"""8.8 CommunicationSignal —— 通信信号（第一阶段只预留接口）。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.4。

移除 Action.latent_action 后，``signal`` 成为协议中**唯一**的对外潜空间通道。
它对应 doc 01 的原始构想：

    「能否直接让模型之间以二进制或其它方式交流形成模型自身的语言」

第一阶段只预留结构，不实现编解码、不实现语言演化
（docs/11-phase1-not-doing-list.md 第 16 项：语言演化 / 同族语言 → v0.4+）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationSignal:
    """一条潜空间通信信号。字段对应 07 §8.8 原文，未增删。

    ``signal`` 的语义由模型自行演化（v0.4+），协议不解释其内容——
    这正是"模型自身语言"与"人类语言"的分界。
    """

    sender_id: str
    receiver_id: str
    signal: tuple[float, ...]
    timestamp: float
    priority: int
