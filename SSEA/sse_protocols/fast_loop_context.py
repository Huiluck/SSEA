"""FastLoopContext —— 不可变结构快照。

**新增依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.1。

快环（FSL）与慢环（SEL）之间**不直接通信**。慢环只发布结构的新版本，
快环只读当前版本——本组件就是那个"当前版本"的物化。

设计要点
--------
**不可变**。快照一经交出，不随后续 commit 变化。这不是性能优化，是安全性质：
它让「Gate 不通过则版本号不切换，快照继续用旧版」成为结构事实，
而不依赖调用方记得回滚。

**「不可变」曾经只是约定，2026-09-28 起才是结构事实。** ``frozen=True`` 只挡
**重新绑定**（``ctx.thresholds = {}`` 抛异常），不挡**就地改**
（``ctx.thresholds["x"] = 1`` 静默成功）。而字段注解写的是 ``Mapping``——
一句只读承诺，配一个可变的 ``dict``。差别不是学术的：快照被快环**持有一整段
episode**，就地改它就是一次**绕过「提案 → 验证门 → Structure Store」的行为
变更**，直接违反 07 §16「模型不可绕过验证器应用修改」，且不留版本号、不进审计。
现在六个字段在 ``__post_init__`` 里包成 ``MappingProxyType``，写入抛
``TypeError``。**约定换成结构事实**，与 ``frozen=True`` 本身是同一个动作。

*边界要说清*：``MappingProxyType`` 只读**顶层**。值本身若可变
（如 ``Skill`` 对象、``retrieval`` 里嵌套的 dict）仍可被就地改。
这对 ``retrieval`` 不构成实际缺口——它的形状是**扁平策略**
（见 ``structure_store`` 的 ``_apply``），``validate_retrieval_policy``
会拒绝任何嵌套键；而 ``Skill`` 的可变性是更深一层的题目，尚未处理。
本模块只声称「顶层只读」，不声称「深度不可变」。

**快环零改动**。快环代码只读本对象，不知道慢环存在；换版本 = 换句柄。
慢环无论改什么，快环的读取接口都不变。

**可遗传**。本对象的 ``skills`` / ``adapters`` / ``thresholds`` 就是
GenePackage 的 ``skill_library`` / ``instinct_adapters`` / ``behavior_policy``
的直接来源（08 §2.1）。注入面是遗传面的子集，两套机制共用一份结构定义。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .skill import Skill

#: 六个只读字段。``versions`` 是元数据，只读的理由与五个类别相同。
_READONLY_FIELDS = (
    "skills",
    "rules",
    "adapters",
    "thresholds",
    "retrieval",
    "versions",
)


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
        for name in _READONLY_FIELDS:
            value = getattr(self, name)
            if value is None:
                raise ValueError(f"{name} 不能为 None；空结构用空 Mapping")
            # 注解是 Mapping（只读契约），传进来的却是可变 dict。
            # 见模块 docstring「不可变是结构事实，不是约定」。
            object.__setattr__(self, name, MappingProxyType(dict(value)))

    def __deepcopy__(self, memo: dict[int, Any]) -> "FastLoopContext":
        """显式深拷贝——**``deepcopy`` 一个 ``mappingproxy`` 会抛 ``TypeError``**。

        ``MappingProxyType`` 不可 pickle（``cannot pickle 'mappingproxy'
        object``），所以默认的深拷贝路径在本类上根本走不通。这里逐字段
        深拷贝后重新构造，只读外壳由 ``__post_init__`` 重新包上。
        """

        return FastLoopContext(
            **{
                name: deepcopy(dict(getattr(self, name)), memo)
                for name in _READONLY_FIELDS
            }
        )

    # ------------------------------------------------------------------
    # 快环读取接口
    #
    # 只有**有调用方**的访问器才留在这里。判定标准是 08 §2.4 那条约束
    # 「协议中不允许存在无消费者的通道」，在快照上加一层：**声明了没有
    # 消费者的接口就是本项目反复出现的病**——``get_threshold()`` 是第一次
    # （改结构阈值对行为毫无影响，而提案 / 门 / Store 一路全绿）。
    #
    # 这里曾另有 ``get_threshold()`` / ``get_adapter()`` /
    # ``get_retrieval_policy()`` / ``version_of()``，四个都已删（2026-09-28）：
    #   - ``get_threshold(name, default=0.0)``：**默认值是那个假的契约。**
    #     读 ``thresholds`` 的两个真消费者各自算各自的回落，**没有一个是 0.0**：
    #     解码器回落到 ``cfg.gate_threshold``（一个配置值），
    #     ``plasticity._current_value`` 回落到 ``DEFAULT_BOUNDS[target]`` 的**中点**，
    #     后者还专门写了一段理由说明为什么 0.0 是错的（「0 对阈值是恒开，
    #     对相似度是恒命中——两个都是机制被关掉」）。于是一个 ``default``
    #     参数无论取什么值都对不上任何一个真消费者：**它的契约是照着
    #     一个想象中的消费者猜的**，不是从消费者推出来的。
    #   - ``get_adapter``：消费者读的是 ``context.adapters`` **字段本身**
    #     （``decode_instinct_set`` 要整份集合按已知名字过滤，不是按名取一份）。
    #     方法是按「应该有个读取接口」的设想加的，加完没有消费者。
    #   - ``get_retrieval_policy()``：返回深拷贝，理由是「调用方改不动存在
    #     结构里的那份」。**它的理由是假的**：``retrieval`` 的形状是**扁平
    #     策略**（键就是策略字段名），``validate_retrieval_policy`` 拒绝任何
    #     嵌套键，所以顶层只读（``MappingProxyType``）就是全覆盖，深拷贝没有
    #     第二层要保护。留在那里等于为一个**系统不会产生的形状**留一个防御。
    #     真要一份可改的拷贝，调用点自己写 ``deepcopy(dict(ctx.retrieval))``，
    #     让这个需要**在看得见的地方**表达。
    #   - ``version_of``：被 ``fingerprint()`` 严格支配——审计要问的是
    #     「这一步用的是哪一版结构」，那是**全部类别的版本号**。三个生产
    #     调用点用的都是 ``fingerprint()``。它顺带做的类别名校验，
    #     ``structure_store.py`` 与 ``plasticity.py`` 各已有一份。
    #
    # **别再按「对称」「完整性」补回来。** 要加，先指出哪一行行为会因它改变。
    # ``tests/test_consumer_surface.py`` 的 ``DELETED_ACCESSORS`` 记着它们
    # 为什么删，`test_deleted_accessors_stay_deleted` 盯着它们不回来。
    # ------------------------------------------------------------------

    def get_skill(self, skill_id: str) -> Skill | None:
        """按 id 取技能。Skill Runner 的查表入口（08 §2.3）。

        技能是**查表**，不是搜索——这是 C4「低算力」真正的落地机制，
        也解释了为什么技能库增长不会导致算力爆炸。
        """

        return self.skills.get(skill_id)

    def fingerprint(self) -> tuple[tuple[str, int], ...]:
        """快照指纹：各类别 + 版本号。

        用于实验记录中标注「这一步用的是哪一版结构」，是可追踪性的最小充分量。
        """

        return tuple(sorted((k, int(v)) for k, v in self.versions.items()))
