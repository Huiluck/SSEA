"""FastLoopContext —— 不可变结构快照。

**新增依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.1。

快环（FSL）与慢环（SEL）之间**不直接通信**。慢环只发布结构的新版本，
快环只读当前版本——本组件就是那个"当前版本"的物化。

设计要点
--------
**不可变**。快照一经交出，不随后续 commit 变化。这不是性能优化，是安全性质：
它让「Gate 不通过则版本号不切换，快照继续用旧版」成为结构事实，
而不依赖调用方记得回滚。

**快环零改动**。快环代码只读本对象，不知道慢环存在；换版本 = 换句柄。
慢环无论改什么，快环的读取接口都不变。

**可遗传**。本对象的 ``skills`` / ``adapters`` / ``thresholds`` 就是
GenePackage 的 ``skill_library`` / ``instinct_adapters`` / ``behavior_policy``
的直接来源（08 §2.1）。注入面是遗传面的子集，两套机制共用一份结构定义。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .skill import Skill


@dataclass(frozen=True)
class FastLoopContext:
    """快环可见的结构快照。

    五个字段对应 08 §2.1 的五类注入物；``versions`` 记录各类别版本号，
    用于审计与「这次行为改变来自哪个版本」的归因。

    全部字段只读。若需修改，应由慢环产出提案 → 过门 → Structure Store
    提升版本 → 重新取快照，而不是就地改这个对象。
    """

    skills: Mapping[str, Skill]
    rules: Mapping[str, Any]
    adapters: Mapping[str, bytes]
    thresholds: Mapping[str, float]
    retrieval: Mapping[str, Any]
    versions: Mapping[str, int]

    def __post_init__(self) -> None:
        for name in ("skills", "rules", "adapters", "thresholds", "retrieval"):
            if getattr(self, name) is None:
                raise ValueError(f"{name} 不能为 None；空结构用空 Mapping")

    # ------------------------------------------------------------------
    # 快环读取接口
    # ------------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Skill | None:
        """按 id 取技能。Skill Runner 的查表入口（08 §2.3）。

        技能是**查表**，不是搜索——这是 C4「低算力」真正的落地机制，
        也解释了为什么技能库增长不会导致算力爆炸。
        """

        return self.skills.get(skill_id)

    def get_threshold(self, name: str, default: float = 0.0) -> float:
        """取行为策略阈值。Action Decoder 的决策阈值来源。"""
        return float(self.thresholds.get(name, default))

    def get_retrieval_policy(self) -> dict[str, Any]:
        """取记忆检索策略。Memory System 的检索参数来源。

        注意 08 §4.1 的公式标注：``m_t = MemorySystem.retrieve(...)``
        **受 retrieval_policy 约束，非每步全量检索**。

        返回深拷贝：策略是嵌套 dict，浅拷贝会让调用方的修改污染快照本身。
        """

        return deepcopy(dict(self.retrieval))

    def version_of(self, kind: str) -> int:
        """某类结构的版本号。"""
        try:
            return int(self.versions[kind])
        except KeyError:
            raise KeyError(f"未知的结构类别 {kind!r}") from None

    def fingerprint(self) -> tuple[tuple[str, int], ...]:
        """快照指纹：各类别 + 版本号。

        用于实验记录中标注「这一步用的是哪一版结构」，是可追踪性的最小充分量。
        """

        return tuple(sorted((k, int(v)) for k, v in self.versions.items()))
