"""Memory System —— 记忆系统。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.4 +
docs/08-dual-loop-interface-and-gap-closure.md §3.3（可继承性筛选）、
§4.1（检索受 retrieval_policy 约束）。

职责（07 §6.4 原文）：存储、检索、更新和遗忘经验。

第一阶段五条要求与本文实现的对应：

    支持写入        → write() / write_item()
    支持向量检索    → retrieve() / recall()，余弦相似度
    支持重要度排序  → items() / most_important()，淘汰与排序共用同一把尺
    支持容量限制    → capacity，写满先淘汰再插入
    支持记忆合并    → merge_threshold，情境相同则合并而非新增

三条 SSEA 立场的落地
-------------------
**1. 记忆是模型侧状态，不进结构快照。**
``FastLoopContext`` 的五类注入物（skills / rules / adapters / thresholds /
retrieval）里**没有记忆本体**，只有 ``retrieval`` 这一个*策略*。记忆住在
MemorySystem 里，随 agent 生命周期存在，换结构版本不影响它。
这与 C3「权重 / 记忆 / 技能三分离」直接对应：若记忆进快照，一次版本切换
就会重置记忆，"精准回忆历史"（C5）便无从谈起。

**2. m_t 恒为 memory_dim，与记忆条数无关。**
08 §4.1 标注 ``retrieve`` "受 retrieval_policy 约束，非每步全量检索"。
实现是两件事合起来：

    - ``top_k``：一次最多带回几条（不是全量）
    - ``stride``：每几帧才真的检索一次（不是每步）

布局按**槽位**铺开：``m_t`` 切成 ``top_k`` 段，第 i 段放第 i 相关的记忆，
按相似度加权。空槽补零。于是"没有命中"与 Milestone 2 的
``ZeroMemoryRetriever`` 输出**不可区分**——这是刻意的：占位实现是诚实的空，
真实实现在无命中时必须也是诚实的空，否则"有记忆"与"没记忆"在数值上无法分辨。

**3. 记忆的键是世界，不是模型私有状态。**
08 §4.1 的公式写 ``MemorySystem.retrieve(p_t, h_{t-1})``。实现**收窄为
``retrieve(p_t)``，``h_{t-1}`` 不进检索键。理由是可继承性（C7）：

    可继承记忆（RULE / SKILL）要复制进子代，而子代的 hidden 分布与父代不同
    ——用 hidden 做键，继承来的记忆永远命中不了，等于把一个永远为空的死字段
    传给了下一代。这正是 08 §2.4 从 Action 里删掉 latent_action 的同一条理由。

``h_{t-1}`` 仍然进入 State Core，只是不经记忆系统。这是本模块与 08 §4.1
的一处**已记录偏差**，见 SSEA/README.md 的差异清单。

使用统计的归属
------------
``MemoryItem`` 是 frozen dataclass。检索命中后要更新 ``retrieval_count``
与 ``last_retrieved``，故本系统以 ``replace()`` 产副本换掉旧项——
**不就地改协议对象**。这与 Skill Runner 改不了快照里的 Skill 是同一条纪律。

``retrieval_count`` 的语义被放宽为"这条记忆被再次经历或检索到的次数"：
合并（同一情境再次出现）与检索命中都递增它。协议没有 metadata 字段可放
单独的"重现次数"，而 08 §3.3 的可遗传筛选恰好需要这个量——重复出现的情境
正是该被继承的那一类。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

import torch

from .sse_protocols import (
    MEMORY_TYPES,
    Feedback,
    FastLoopContext,
    MemoryItem,
    MemoryWrite,
    Observation,
)
from .tensorize import as_vector

#: 合并时的重要度提升。重复经历同一情境应提升它的排序位置。
MERGE_IMPORTANCE_BOOST = 0.05

#: 默认记忆检索策略。快照里 ``retrieval`` 为空时用它；
#: 快照里给了部分键时，**逐键覆盖**默认值（见 validate_retrieval_policy）。
DEFAULT_RETRIEVAL_POLICY: dict[str, Any] = {
    # 一次检索最多带回几条。同时决定 m_t 的分槽布局。
    "top_k": 4,
    # 相似度低于此值不算命中。必须 > 0，否则"无命中"与"命中但相似度为 0"
    # 在 m_t 上不可区分。
    "min_similarity": 0.1,
    # 每几帧真的做一次检索。> 1 时其余帧沿用上一次的 m_t（低频检索）。
    "stride": 1,
    # 重要度低于此值的记忆不参与检索。
    "importance_floor": 0.0,
    # 参与每步 m_t 的记忆类型。RULE / SKILL 是编译产物，走 recall()，
    # 不进 m_t——它们不是"当前情境"，是跨情境的结论。
    "types": ("EVENT", "BODY_EXPERIENCE"),
    # 情境相似度达到此值即合并而非新增。0 = 关闭合并。
    "merge_threshold": 0.95,
    # False = 拒绝一切写入。约束第二执行点（见类 docstring）。
    "writable": True,
    # 可继承筛选的两条阈值（08 §3.3）。
    "heritable_importance": 0.5,
    "heritable_min_retrievals": 1,
}

#: 策略合法键。未知键立即报错——拼错的键会静默关掉一个机制，
#: 而这类失效在任何运行时报错里都看不见。
_POLICY_KEYS = frozenset(DEFAULT_RETRIEVAL_POLICY)


def validate_retrieval_policy(
    policy: Mapping[str, Any] | None,
    *,
    memory_dim: int,
) -> dict[str, Any]:
    """把（可能为部分的）策略合并到默认值上并校验。

    返回**新 dict**，不修改入参。合并而非替换是有意的：
    ``UPDATE_RETRIEVAL_POLICY`` 提案只应改动它想改的那个键，
    而 Structure Store 的 ``_apply`` 是整体替换 ``retrieval[target]``，
    故"改一个键"的语义由本函数在读取侧保证。
    """

    merged: dict[str, Any] = dict(DEFAULT_RETRIEVAL_POLICY)
    if policy:
        unknown = sorted(set(policy) - _POLICY_KEYS)
        if unknown:
            raise ValueError(
                f"检索策略含未知键 {unknown}；合法键见 DEFAULT_RETRIEVAL_POLICY"
            )
        merged.update(dict(policy))

    def _int(name: str, low: int) -> int:
        v = merged[name]
        # bool 是 int 的子类：JSON 里的 true 会静默变成 1，必须先挡掉。
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError(f"检索策略 {name!r} 必须是整数: {v!r}")
        if v < low:
            raise ValueError(f"检索策略 {name!r} 必须 ≥ {low}: {v}")
        return v

    def _float(name: str, low: float, high: float, strict_low: bool = False) -> float:
        v = merged[name]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"检索策略 {name!r} 必须是数: {v!r}")
        v = float(v)
        bad = v <= low if strict_low else v < low
        if bad or v > high:
            op = ">" if strict_low else "≥"
            raise ValueError(
                f"检索策略 {name!r} 必须满足 {op}{low} 且 ≤{high}: {v}"
            )
        return v

    top_k = _int("top_k", 1)
    if memory_dim % top_k:
        raise ValueError(
            f"memory_dim={memory_dim} 不能被 top_k={top_k} 整除——"
            f"m_t 的分槽布局要求两者严格对齐，否则最后一段会短一截"
        )
    _float("min_similarity", 0.0, 1.0, strict_low=True)
    _int("stride", 1)
    _float("importance_floor", 0.0, 1.0)

    types = merged["types"]
    if isinstance(types, str) or not isinstance(types, (list, tuple, set, frozenset)):
        raise ValueError(f"检索策略 'types' 必须是类型名序列: {types!r}")
    bad = sorted(set(types) - set(MEMORY_TYPES))
    if bad:
        raise ValueError(
            f"检索策略 'types' 含未定义类型 {bad}；合法值见 MEMORY_TYPES"
        )
    if not types:
        # 空白名单会让 m_t 恒为零——那不是"关掉类型过滤"，是关掉检索本身。
        # 要限定范围就列出想要的类型；要全都要就列全四个。
        raise ValueError(
            "检索策略 'types' 不能为空：空名单会让 m_t 恒为零，"
            "而那不是本策略想表达的意思"
        )
    merged["types"] = tuple(types)

    _float("merge_threshold", 0.0, 1.0)
    if not isinstance(merged["writable"], bool):
        raise ValueError(f"检索策略 'writable' 必须是布尔: {merged['writable']!r}")
    _float("heritable_importance", 0.0, 1.0)
    _int("heritable_min_retrievals", 0)
    return merged


@dataclass(frozen=True)
class MemoryConfig:
    """Memory System 配置。"""

    #: ``m_t`` 维度。必须与 StateCoreConfig.memory_dim 一致。
    memory_dim: int = 16

    #: 记忆条数上限。写满时先淘汰再插入（07 §6.4「支持容量限制」）。
    capacity: int = 256

    def __post_init__(self) -> None:
        if self.memory_dim <= 0:
            raise ValueError("memory_dim 必须为正")
        if self.capacity < 1:
            # 0 会让"容量限制"退化成"禁止记忆"，那是配置写错了。
            raise ValueError("capacity 至少为 1")


@dataclass
class MemoryStats:
    """记忆系统运行计数。慢环与实验的观测面。"""

    #: ``retrieve()`` 被调用次数（≈ 快环 RUN 帧数）。
    frames: int = 0
    #: 真的做了检索的次数（stride 过滤之后）。
    retrievals: int = 0
    #: 检索有命中 / 无命中的次数。
    hits: int = 0
    misses: int = 0
    #: 写入条数（含被合并后未新增的那些不计入）。
    writes: int = 0
    #: 因情境相同而被合并的次数。
    merged: int = 0
    #: 因容量上限被淘汰的条数。
    evicted: int = 0
    #: 因 ``writable=False`` 被拒绝的写入次数。
    refused: int = 0
    #: 因上下文向量维度不匹配而被拒绝的条数。
    incompatible: int = 0
    #: 内容向量长于槽位被截断的次数。
    truncated: int = 0

    def as_dict(self) -> dict[str, int]:
        return dict(self.__dict__)


class MemorySystem:
    """外部记忆：写入、检索、淘汰、合并、可继承筛选。

    用法::

        mem = MemorySystem()
        m_t = mem.retrieve(perception, now=obs.time)
        mem.write(action.memory, perception, obs, feedback)

    **无参数。** 记忆系统的容量是数据，不是权重（C3 三分离）——
    做成 ``nn.Module`` 会暗示它有可训练参数，而它没有。

    约束第二执行点
    -------------
    ``writable=False`` 时 ``write()`` 拒绝一切写入并计入 ``stats.refused``。
    第一执行点是 Action Decoder（读 ``ActionConstraints.can_store_memory``）。
    两处分立与 08 §2.6.2 的物理动作双执行点同构：模型侧的裁剪负责"生成本就不
    越界"，记忆系统这边的拒绝负责兜住漏网的。
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        context: FastLoopContext | None = None,
    ) -> None:
        self.config = config or MemoryConfig()
        self.stats = MemoryStats()
        self._items: dict[str, MemoryItem] = {}
        self._seq = 0
        self._policy = validate_retrieval_policy(
            context.retrieval if context is not None else None,
            memory_dim=self.config.memory_dim,
        )
        self._context_fingerprint = (
            context.fingerprint() if context is not None else None
        )
        # 上一次检索的 m_t。stride > 1 时被复用——低频检索的落点。
        self._last_m: torch.Tensor | None = None
        # 上下文向量的既定维度。由第一次成功写入/检索钉住，
        # 之后维度不符的项一律拒绝（否则它们永远命中不了，是死数据）。
        self._dim: int | None = None
        # 向量索引缓存。只有插入 / 合并 / 淘汰才失效；
        # 检索命中只改计数，不改向量，故不触发重建。
        self._index_ids: tuple[str, ...] = ()
        self._index_matrix: torch.Tensor | None = None
        self._index_dim: int | None = None
        self._index_dirty = True

    # ------------------------------------------------------------------
    #  策略
    # ------------------------------------------------------------------

    @property
    def policy(self) -> dict[str, Any]:
        """当前生效的检索策略（已合并默认值）。"""
        return self._policy

    def use_context(self, context: FastLoopContext) -> None:
        """换快照后重新读取检索策略。

        快环在 ``WAKE`` 时调用。**记忆本体不在这里**——它不随版本切换重置
        （见模块 docstring 第 1 条）。这里只换策略。
        """

        self._policy = validate_retrieval_policy(
            context.retrieval, memory_dim=self.config.memory_dim
        )
        self._context_fingerprint = context.fingerprint()

    @property
    def context_fingerprint(self) -> tuple[tuple[str, int], ...] | None:
        """策略来源快照的指纹。审计用。"""
        return self._context_fingerprint

    # ------------------------------------------------------------------
    #  检索（快环入口）
    # ------------------------------------------------------------------

    def retrieve(
        self,
        perception: torch.Tensor,
        now: float | None = None,
    ) -> torch.Tensor:
        """``p_t`` → ``m_t``。对应 08 §4.1 的 ``MemorySystem.retrieve``。

        **不收 ``h_{t-1}``**：检索键必须是世界（perception），不能是模型私有
        状态，否则可继承记忆到了子代永远命中不了。理由见模块 docstring 第 3 条。

        无命中时返回零向量——与 ``ZeroMemoryRetriever`` 的输出不可区分。
        这不是偷懒，是"诚实的空"在真实实现上的对应物。
        """

        policy = self._policy
        self.stats.frames += 1

        stride = int(policy["stride"])
        if stride > 1 and self.stats.frames % stride != 1:
            # 低频检索：沿用上一次的 m_t。首帧还没检索过时是诚实的空。
            if self._last_m is None:
                return torch.zeros(self.config.memory_dim, dtype=torch.float32)
            return self._last_m.clone()

        top_k = int(policy["top_k"])
        hits = self._search(perception, policy=policy, top_k=top_k)
        self.stats.retrievals += 1

        if not hits:
            self.stats.misses += 1
            self._last_m = None
            return torch.zeros(self.config.memory_dim, dtype=torch.float32)

        self.stats.hits += 1
        width = self.config.memory_dim // top_k
        out = torch.zeros(self.config.memory_dim, dtype=torch.float32)
        for i, (item, sim) in enumerate(hits):
            if len(item.content_vector) > width:
                self.stats.truncated += 1
            out[i * width : (i + 1) * width] = _slot_vector(
                item.content_vector, width
            ) * sim
            if now is not None:
                self._touch(item, now)

        self._last_m = out
        return out.clone()

    def recall(
        self,
        perception: torch.Tensor,
        *,
        types: Iterable[str] | None = None,
        top_k: int | None = None,
        now: float | None = None,
    ) -> tuple[MemoryItem, ...]:
        """显式召回记忆项本身。慢环与观察员的入口。

        与 ``retrieve()`` 的分工：``retrieve()`` 受策略的 ``types`` / ``top_k``
        约束，产出固定维的 ``m_t``，是快环的低带宽入口；``recall()`` 由调用方
        指定范围，返回记忆项，是慢环 RuleCompiler 与实验指标的入口。

        ``min_similarity`` / ``importance_floor`` 仍取策略值——它们是"什么算
        一次命中"的定义，不该由调用方每次重定。
        """

        if types is not None:
            policy = dict(self._policy)
            policy["types"] = tuple(types)
        else:
            policy = self._policy
        n = int(policy["top_k"]) if top_k is None else int(top_k)
        hits = self._search(perception, policy=policy, top_k=n)
        if now is not None:
            for item, _ in hits:
                self._touch(item, now)
        return tuple(item for item, _ in hits)

    # ------------------------------------------------------------------
    #  写入
    # ------------------------------------------------------------------

    def write(
        self,
        request: MemoryWrite | None,
        query: torch.Tensor,
        observation: Observation,
        feedback: Feedback,
    ) -> MemoryItem | None:
        """把 ``Action.memory`` 通道的请求落成一条记忆。

        ``request is None`` 或 ``store=False`` 都表示本帧不写入——前者是通道
        门控没开，后者是门控开了但模型选择不存。两者都不是失败。

        ``query`` 是**本帧的 perception_vector**：它将成为这条记忆的检索键。
        """

        if request is None or not request.store:
            return None
        if not self._policy["writable"]:
            self.stats.refused += 1
            return None

        item = MemoryItem(
            id=self._next_id("mem"),
            timestamp=observation.time,
            type=_classify(feedback),
            context_vector=_as_protocol_vector(query),
            content_vector=tuple(request.content),
            outcome=_outcome_marker(feedback),
            importance=float(request.importance),
            retrieval_count=0,
            last_retrieved=observation.time,
        )
        survivor = self.write_item(item)
        if survivor is None:
            return None
        self.stats.writes += 1
        return survivor

    def write_item(self, item: MemoryItem) -> MemoryItem | None:
        """低阶插入：先尝试合并，再容量淘汰，最后入库。

        返回最终留在库里的那条（合并时是**旧的那条**，不是新传入的），
        被拒时返回 None。合并时返回旧项是有意的：记忆的身份是它第一次被记下的
        时刻，重复经历只更新它。
        """

        if self._dim is not None and len(item.context_vector) != self._dim:
            # 维度不符的上下文向量永远命中不了——它是死数据，不是记忆。
            self.stats.incompatible += 1
            return None

        merged = self._try_merge(item)
        if merged is not None:
            return merged

        while len(self._items) >= self.config.capacity:
            if self._evict_one() is None:
                break
        self._items[item.id] = item
        self._dim = self._dim or len(item.context_vector)
        self._index_dirty = True
        return item

    def load_heritable(self, items: Iterable[MemoryItem]) -> int:
        """载入可继承记忆。基因继承的消费端（08 §3.3）。

        瞬时记忆（EVENT / BODY_EXPERIENCE）在此被丢弃——子代只加载
        RULE / SKILL。这是 07 风险 5「记忆无限膨胀」的缓解措施：
        记忆规模不随世代累积。
        """

        loaded = 0
        for item in items:
            if item.is_transient:
                continue
            if self.write_item(item) is not None:
                loaded += 1
        return loaded

    # ------------------------------------------------------------------
    #  查询 / 排序 / 可继承
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._items)

    def get(self, memory_id: str) -> MemoryItem | None:
        return self._items.get(memory_id)

    def items(self) -> tuple[MemoryItem, ...]:
        """全部记忆，按重要度降序（同重要度按检索次数、时间、id）。

        重要度排序不是展示用的：淘汰与"最相关"用的是同一把尺，
        只是方向相反。
        """

        return tuple(
            sorted(
                self._items.values(),
                key=lambda m: (-m.importance, -m.retrieval_count, -m.last_retrieved, m.id),
            )
        )

    def most_important(self, k: int) -> tuple[MemoryItem, ...]:
        """重要度最高的前 k 条。"""
        return self.items()[: max(0, int(k))]

    def heritable(self) -> tuple[MemoryItem, ...]:
        """可继承记忆。对应 08 §4.2 的 ``ΔM_h = HeritableFilter(ΔM)``。

        阈值来自检索策略而不是写死在代码里——它们属于 behavior_policy，
        可经 UPDATE_THRESHOLD / UPDATE_RETRIEVAL_POLICY 提案修改。
        """

        policy = self._policy
        return tuple(
            m
            for m in self.items()
            if m.is_heritable(
                float(policy["heritable_importance"]),
                int(policy["heritable_min_retrievals"]),
            )
        )

    # ------------------------------------------------------------------
    #  内部：检索
    # ------------------------------------------------------------------

    def _search(
        self,
        perception: torch.Tensor,
        *,
        policy: Mapping[str, Any],
        top_k: int,
    ) -> tuple[tuple[MemoryItem, float], ...]:
        """相似度检索。返回 [(记忆, 相似度)]，按相似度降序，最多 top_k 条。"""

        if not self._items:
            return ()
        query = as_vector(perception, name="perception_vector")
        if float(query.abs().sum()) == 0.0:
            return ()

        ids, matrix = self._ensure_index(query.numel())
        if matrix is None:
            return ()

        unit_q = query / query.norm()
        sims = matrix @ unit_q

        min_sim = float(policy["min_similarity"])
        floor = float(policy["importance_floor"])
        allowed = policy["types"]

        scored: list[tuple[float, MemoryItem]] = []
        for idx, mid in enumerate(ids):
            item = self._items[mid]
            if item.importance < floor:
                continue
            # 白名单语义：不在名单里就不参与。空名单 = 谁都不参与，
            # 与 allowed_operations 同构；策略层已禁止空名单（见校验），
            # 这里是 recall(types=()) 这类显式空范围的落点。
            if item.type not in allowed:
                continue
            sim = float(sims[idx])
            if sim < min_sim:
                continue
            scored.append((sim, item))

        # 相似度优先；同相似度时重要度高者优先；再同则按 id 保证确定性。
        scored.sort(key=lambda pair: (-pair[0], -pair[1].importance, pair[1].id))
        return tuple((item, sim) for sim, item in scored[: max(0, top_k)])

    def _ensure_index(
        self, dim: int
    ) -> tuple[tuple[str, ...], torch.Tensor | None]:
        """（惰性）重建 L2 归一化的上下文向量矩阵。"""

        if not self._index_dirty and self._index_dim == dim:
            return self._index_ids, self._index_matrix

        ids: list[str] = []
        rows: list[torch.Tensor] = []
        for mid, item in self._items.items():
            if len(item.context_vector) != dim:
                continue
            row = as_vector(item.context_vector, expected=dim, name=mid)
            norm = float(row.norm())
            if norm == 0.0:
                continue
            ids.append(mid)
            rows.append(row / norm)

        self._index_ids = tuple(ids)
        self._index_matrix = torch.stack(rows) if rows else None
        self._index_dim = dim
        self._index_dirty = False
        return self._index_ids, self._index_matrix

    def _touch(self, item: MemoryItem, now: float) -> None:
        """命中后更新检索计数。产副本换旧项，不就地改 frozen 协议对象。"""

        self._items[item.id] = replace(
            item,
            retrieval_count=item.retrieval_count + 1,
            last_retrieved=now,
        )

    # ------------------------------------------------------------------
    #  内部：合并与淘汰
    # ------------------------------------------------------------------

    def _try_merge(self, item: MemoryItem) -> MemoryItem | None:
        """情境相同则合并，返回合并后的旧项；否则 None。

        只合**同类型**的记忆——把一条 EVENT 并进一条 BODY_EXPERIENCE 会
        让类型的语义变浑，而类型是可遗传性的判据（08 §3.3）。
        """

        threshold = float(self._policy["merge_threshold"])
        if threshold <= 0.0:
            return None
        ids, matrix = self._ensure_index(len(item.context_vector))
        if matrix is None:
            return None

        query = as_vector(item.context_vector, name="context_vector")
        norm = float(query.norm())
        if norm == 0.0:
            return None
        sims = matrix @ (query / norm)
        best = int(torch.argmax(sims).item()) if sims.numel() else -1
        if best < 0:
            return None

        survivor = self._items[ids[best]]
        if survivor.type != item.type:
            return None
        if float(sims[best]) < threshold:
            return None

        # 重要度取高者并提升：重复经历的情境更值得留下。
        importance = min(
            1.0,
            max(survivor.importance, item.importance) + MERGE_IMPORTANCE_BOOST,
        )
        merged = replace(
            survivor,
            timestamp=item.timestamp,
            last_retrieved=item.timestamp,
            # 同一情境再次出现即计一次——这是可遗传筛选需要的量。
            retrieval_count=survivor.retrieval_count + 1,
            importance=importance,
            outcome=item.outcome,
            content_vector=(
                survivor.content_vector
                if survivor.importance >= item.importance
                else item.content_vector
            ),
        )
        self._items[survivor.id] = merged
        self.stats.merged += 1
        return merged

    def _evict_one(self) -> MemoryItem | None:
        """淘汰最该忘的一条：重要度最低 → 检索最少 → 最久未用 → id 最小。

        顺序即 ``items()`` 的逆序。两条路径共用一把尺，避免"排序说它重要、
        淘汰说它该走"。
        """

        if not self._items:
            return None
        victim = min(
            self._items.values(),
            key=lambda m: (m.importance, m.retrieval_count, m.last_retrieved, m.id),
        )
        del self._items[victim.id]
        self.stats.evicted += 1
        self._index_dirty = True
        return victim

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}_{self._seq:06d}"


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def _classify(feedback: Feedback) -> str:
    """反馈 → 记忆类型。

    身体受了伤或累了 → 身体经验记忆；其余 → 事件记忆。
    RULE / SKILL 不由本函数产出——它们是编译产物（慢环），
    经 ``write_item()`` 直接入库。
    """

    if feedback.damage_change > 0.0 or feedback.fatigue_change > 0.0:
        return "BODY_EXPERIENCE"
    return "EVENT"


def _outcome_marker(feedback: Feedback) -> str:
    """反馈 → 结果标记。

    是**标记**不是句子：``MemoryItem.outcome`` 是协议里唯一允许的 str 结果
    字段（见 tests/test_protocol_consistency.py::test_notes_is_the_only_free_text_field），
    不进控制闭环。
    """

    if feedback.damage_change > 0.0:
        return "damaged"
    if feedback.energy_change > 0.0:
        return "energy_gain"
    if feedback.energy_change < 0.0:
        return "energy_loss"
    return "neutral"


def _as_protocol_vector(query: torch.Tensor, digits: int = 6) -> tuple[float, ...]:
    """张量 → 协议向量。

    取六位小数：记忆要可序列化、可 diff、可跨进程（协议约定 2），
    而浮点末位差异会让"同一情境"在比较时显得不同。
    """

    return tuple(
        round(float(v), digits) for v in query.reshape(-1).tolist()
    )


def _slot_vector(content: Sequence[float], width: int) -> torch.Tensor:
    """内容向量 → 定长槽位段。短了补零，长了截断（截断计入 stats.truncated）。"""

    values = [float(v) for v in content[:width]]
    if len(values) < width:
        values += [0.0] * (width - len(values))
    return torch.tensor(values, dtype=torch.float32)
