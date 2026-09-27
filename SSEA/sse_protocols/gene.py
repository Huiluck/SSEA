"""8.13 GenePackage —— 基因包。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §3.2
（ΔM 补入 mutate）、§3.3（memory_index 继承语义）、§3.5（architecture
变异禁止）。

三处修订：

1. 新增 ``heritable_memory``：可继承记忆副本。原公式
   ``G' = GeneManager.mutate(G, ΔS, Δθ, ΔC)`` 漏了 ΔM，而 GenePackage
   又含 memory_index——记忆更新到不了基因，"继承"退化成"继承行为模板"。
   修订后 ``G' = GeneManager.mutate(G, ΔS, Δθ, ΔM_h)``（08 §3.2）。
2. ``memory_index`` 更名 ``memory_store_ref``，并注明**仅审计用**。
   子代拿到的是引用而非副本，且不加载（08 §3.3）。
3. ``mutation_rate`` 增补作用范围说明：只作用于 adapter / 阈值 / 技能参数，
   **不作用于网络结构**（08 §3.5）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .memory import MemoryItem
from .skill import Skill


#: mutation_rate 的作用范围。对应 08 §3.5。
MUTATION_SCOPES: tuple[str, ...] = (
    "instinct_adapters",
    "thresholds",
    "skill_params",
)

#: 明确不在作用范围内的项。
NON_MUTABLE: tuple[str, ...] = ("architecture", "core_weights")


@dataclass(frozen=True)
class GenePackage:
    """可保存 / 恢复 / 变异 / 继承的基因包。

    字段对应 07 §8.13 原文，按 08 §3.2 / §3.3 修订。

    ``core_weights`` 与 ``instinct_adapters`` 存 bytes，不绑定具体张量库——
    协议层不依赖 torch。序列化 / 反序列化由 Gene Manager（Milestone 4）负责。
    """

    agent_id: str
    created_at: float
    architecture: dict
    core_weights: bytes
    instinct_adapters: tuple[bytes, ...]
    skill_library: tuple[Skill, ...]
    heritable_memory: tuple[MemoryItem, ...]
    memory_store_ref: str
    behavior_policy: dict
    metabolic_policy: dict
    mutation_rate: float

    def __post_init__(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id 不能为空")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError(f"mutation_rate 应在 [0,1]: {self.mutation_rate}")
        for item in self.heritable_memory:
            if item.is_transient:
                raise ValueError(
                    f"heritable_memory 含瞬时记忆 {item.id!r}"
                    f"（type={item.type}）；瞬时记忆不继承（08 §3.3）"
                )

    def adapter_origins(self) -> tuple[str, ...]:
        """各 instinct adapter 的来源标记。审计用（08 §3.4）。"""
        return tuple(s.origin for s in self.skill_library if s.origin)
