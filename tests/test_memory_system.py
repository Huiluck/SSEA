"""Memory System 测试 —— 07 §6.4 五项要求 + 08 §3.3 / §4.1。

07 §6.4 的第一阶段五条（写入 / 向量检索 / 重要度排序 / 容量限制 / 记忆合并）
是验收骨架；本文件把它们逐条钉住，并额外覆盖三处 SSEA 特有的不变量：

1. ``m_t`` 恒为 ``memory_dim``，与库内条数无关（08 §4.1 的低带宽约束）；
2. 无命中时是**诚实的空**——与 ``ZeroMemoryRetriever`` 数值上不可区分；
3. 检索键是世界（perception），不是模型私有状态（08 §4.1 的一处已记录偏差，
   理由见 memory_system.py 模块 docstring 第 3 条）。

关于检索键的取法
--------------
测试里的上下文向量一律用 ``ctx(deg)`` 生成：与 ``(1,0)`` 成 ``deg`` 度的
单位向量。**不用共线向量**（如 ``(1,0)`` / ``(2,0)``）——它们的余弦相似度是
1.0，会被合并阈值静默并成一条，于是"插了两条"的断言莫名失败。
角度间隔取 20° 以上，保证两两相似度 < 0.95（默认合并阈值）。
"""

from __future__ import annotations

import math

import pytest
import torch

from SSEA.action_decoder import ActionDecoderConfig
from SSEA.memory_system import (
    DEFAULT_RETRIEVAL_POLICY,
    MERGE_IMPORTANCE_BOOST,
    MemoryConfig,
    MemoryItem,
    MemorySystem,
    validate_retrieval_policy,
)
from SSEA.sse_protocols import (
    ActionConstraints,
    BodyState,
    EnvironmentSummary,
    Feedback,
    MemoryWrite,
    Observation,
    default_constraints,
)
from SSEA.state_core import StateCoreConfig
from tests.conftest import make_context


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def fb(
    *,
    energy: float = 0.0,
    damage: float = 0.0,
    fatigue: float = 0.0,
) -> Feedback:
    """一条最小反馈。energy 用于 outcome 标记，damage/fatigue 用于分类。"""

    return Feedback(
        energy_change=energy,
        damage_change=damage,
        fatigue_change=fatigue,
        prediction_error=0.0,
        action_success=True,
        survived=True,
    )


def write_request(content: tuple[float, ...], importance: float) -> MemoryWrite:
    return MemoryWrite(store=True, content=content, importance=importance)


def ctx(deg: float) -> tuple[float, ...]:
    """与 ``(1,0)`` 成 ``deg`` 度的单位向量，取正 y 分支。"""

    a = math.radians(deg)
    return (round(math.cos(a), 6), round(math.sin(a), 6))


def vec(*values: float) -> torch.Tensor:
    return torch.tensor(values, dtype=torch.float32)


def item(
    *,
    memory_id: str,
    context: tuple[float, ...],
    memory_type: str = "EVENT",
    importance: float = 0.5,
    retrieval_count: int = 0,
    content: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0),
    timestamp: float = 0.0,
    last_retrieved: float = 0.0,
) -> MemoryItem:
    """绕过 write() 直接造一条记忆——测试要精确控制相似度与类型。"""

    return MemoryItem(
        id=memory_id,
        timestamp=timestamp,
        type=memory_type,
        context_vector=context,
        content_vector=content,
        outcome="neutral",
        importance=importance,
        retrieval_count=retrieval_count,
        last_retrieved=last_retrieved,
    )


def mem(**policy: object) -> MemorySystem:
    """一个带指定策略、其余取默认值的记忆系统。"""

    return MemorySystem(MemoryConfig(memory_dim=16), make_context(retrieval=policy or None))


def slots_used(m_t: torch.Tensor, top_k: int) -> int:
    """m_t 里被写进内容的槽位数。

    直接数下标会踩坑：槽宽是 ``memory_dim / top_k``，``top_k`` 一变，
    "第几条"的下标也跟着变。按 top_k 切段再数非零段才是稳定的判据。
    """

    width = m_t.numel() // top_k
    return sum(
        1
        for i in range(top_k)
        if float(m_t[i * width : (i + 1) * width].abs().sum()) > 0.0
    )


def _obs(time: float) -> Observation:
    """最小 Observation。``write()`` 只读 ``time``，其余字段给占位值。"""

    return Observation(
        time=time,
        body=BodyState(
            energy=1.0,
            damage=0.0,
            fatigue=0.0,
            position=(0.0, 0.0),
            orientation=(1.0, 0.0),
            action_constraints=default_constraints(),
            internal_state=(),
        ),
        environment=EnvironmentSummary(
            light_level=1.0,
            temperature=0.5,
            danger_level=0.0,
            resource_density=0.0,
            time_phase="day",
        ),
    )


# ----------------------------------------------------------------------
#  策略校验
# ----------------------------------------------------------------------


class TestPolicyValidation:
    """策略是快照给的，写错必须立刻炸——拼错的键会静默关掉一个机制。"""

    def test_defaults_are_used_when_snapshot_is_empty(self) -> None:
        m = MemorySystem()
        for k, v in DEFAULT_RETRIEVAL_POLICY.items():
            assert m.policy[k] == v

    def test_partial_policy_merges_key_by_key(self) -> None:
        """改一个键不能把其余九个重置掉。"""

        m = mem(top_k=2)
        assert m.policy["top_k"] == 2
        assert m.policy["min_similarity"] == DEFAULT_RETRIEVAL_POLICY["min_similarity"]

    def test_unknown_key_raises(self) -> None:
        with pytest.raises(ValueError, match="未知键"):
            mem(top_k=4, topK=2)

    def test_top_k_must_divide_memory_dim(self) -> None:
        """分槽布局要求整除；不整除时最后一段会短一截，m_t 的语义就废了。"""

        with pytest.raises(ValueError, match="整除"):
            validate_retrieval_policy({"top_k": 3}, memory_dim=16)

    def test_top_k_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="≥ 1"):
            mem(top_k=0)

    def test_min_similarity_must_be_positive(self) -> None:
        """0 会让"无命中"与"命中但相似度为 0"在 m_t 上不可区分。"""

        with pytest.raises(ValueError, match=">"):
            mem(min_similarity=0.0)

    def test_bool_is_not_an_int(self) -> None:
        """JSON 的 true 会静默变成 1，必须先挡掉。"""

        with pytest.raises(ValueError, match="整数"):
            mem(top_k=True)

    def test_unknown_memory_type_raises(self) -> None:
        with pytest.raises(ValueError, match="未定义类型"):
            mem(types=("EVENT", "TELEPATHY"))

    def test_types_string_is_rejected(self) -> None:
        """单个字符串会被 iterable 成字符，那是无声的错。"""

        with pytest.raises(ValueError, match="序列"):
            mem(types="EVENT")

    def test_empty_types_is_rejected(self) -> None:
        """空白名单会让 m_t 恒为零——那不是"关掉类型过滤"，是关掉检索本身。"""

        with pytest.raises(ValueError, match="不能为空"):
            mem(types=())

    def test_types_are_normalized_to_tuple(self) -> None:
        m = mem(types=["EVENT", "RULE"])
        assert m.policy["types"] == ("EVENT", "RULE")

    def test_merge_threshold_zero_disables_merging(self) -> None:
        m = mem(merge_threshold=0.0)
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.write_item(item(memory_id="b", context=ctx(0)))
        assert len(m) == 2
        assert m.stats.merged == 0

    def test_writable_must_be_bool(self) -> None:
        with pytest.raises(ValueError, match="布尔"):
            mem(writable=1)

    def test_input_policy_is_not_mutated(self) -> None:
        policy = {"top_k": 2}
        validate_retrieval_policy(policy, memory_dim=16)
        assert policy == {"top_k": 2}

    def test_stride_below_one_raises(self) -> None:
        with pytest.raises(ValueError, match="≥ 1"):
            mem(stride=0)


# ----------------------------------------------------------------------
#  写入
# ----------------------------------------------------------------------


class TestWrite:
    """07 §6.4「支持写入」。"""

    def test_store_true_inserts(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        out = m.write(
            write_request((1.0, 2.0, 3.0, 4.0), 0.7), ctx(0) and vec(*ctx(0)), _obs(1.0), fb()
        )
        assert out is not None
        assert len(m) == 1
        assert m.stats.writes == 1
        assert out.type == "EVENT"
        assert out.importance == 0.7
        assert out.context_vector == ctx(0)
        assert out.timestamp == 1.0

    def test_none_request_is_not_a_write(self) -> None:
        """通道门控没开——不是失败，不计 refused。"""

        m = MemorySystem()
        assert m.write(None, vec(1.0), _obs(0.0), fb()) is None
        assert m.stats.writes == 0
        assert m.stats.refused == 0

    def test_store_false_is_not_a_write(self) -> None:
        m = MemorySystem()
        req = MemoryWrite(store=False, content=(1.0,), importance=0.5)
        assert m.write(req, vec(1.0), _obs(0.0), fb()) is None
        assert len(m) == 0

    def test_context_vector_is_the_retrieval_key(self) -> None:
        """键必须是世界（perception）——这条是可继承性的前提。"""

        m = MemorySystem()
        out = m.write(write_request((1.0,), 0.5), vec(0.5, 0.5), _obs(0.0), fb())
        assert out is not None
        assert out.context_vector == (0.5, 0.5)

    def test_content_is_stored_verbatim(self) -> None:
        m = MemorySystem()
        out = m.write(write_request((0.25, -1.5, 9.0), 0.5), vec(1.0), _obs(0.0), fb())
        assert out is not None
        assert out.content_vector == (0.25, -1.5, 9.0)

    def test_outcome_marker_from_feedback(self) -> None:
        m = MemorySystem()
        gain = m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb(energy=0.4))
        loss = m.write(write_request((1.0,), 0.5), vec(*ctx(40)), _obs(0.0), fb(energy=-0.4))
        assert gain is not None and gain.outcome == "energy_gain"
        assert loss is not None and loss.outcome == "energy_loss"

    def test_damage_outranks_energy(self) -> None:
        """同帧既掉血又回能时，结果标记必须说受伤——那是更严重的后果。"""

        m = MemorySystem()
        out = m.write(
            write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb(energy=0.4, damage=0.2)
        )
        assert out is not None
        assert out.outcome == "damaged"
        assert out.type == "BODY_EXPERIENCE"

    def test_type_is_classified_from_feedback(self) -> None:
        m = MemorySystem()
        m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb())
        m.write(write_request((1.0,), 0.5), vec(*ctx(30)), _obs(0.0), fb(fatigue=0.3))
        m.write(write_request((1.0,), 0.5), vec(*ctx(60)), _obs(0.0), fb(damage=0.3))
        assert m.get("mem_000001").type == "EVENT"
        assert m.get("mem_000002").type == "BODY_EXPERIENCE"
        assert m.get("mem_000003").type == "BODY_EXPERIENCE"

    def test_ids_are_sequential_and_unique(self) -> None:
        m = MemorySystem()
        m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb())
        m.write(write_request((1.0,), 0.5), vec(*ctx(30)), _obs(0.0), fb())
        assert m.get("mem_000001") is not None
        assert m.get("mem_000002") is not None

    def test_writable_false_refuses_and_counts(self) -> None:
        """约束第二执行点：模型漏过的写入由这里兜住。"""

        m = mem(writable=False)
        out = m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb())
        assert out is None
        assert len(m) == 0
        assert m.stats.refused == 1
        assert m.stats.writes == 0

    def test_write_item_rejects_incompatible_dimension(self) -> None:
        """维度不符的上下文永远命中不了——它是死数据，不是记忆。"""

        m = MemorySystem()
        m.write_item(item(memory_id="a", context=(1.0, 0.0)))
        m.write_item(item(memory_id="b", context=(1.0, 0.0, 0.0)))
        assert len(m) == 1
        assert m.stats.incompatible == 1

    def test_merged_write_is_counted_once(self) -> None:
        """合并不新增条数，但算一次写入——记忆确实被记录了。"""

        m = MemorySystem()
        m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(0.0), fb())
        m.write(write_request((1.0,), 0.5), vec(*ctx(0)), _obs(1.0), fb())
        assert len(m) == 1
        assert m.stats.writes == 2
        assert m.stats.merged == 1


# ----------------------------------------------------------------------
#  检索
# ----------------------------------------------------------------------


class TestRetrieve:
    """07 §6.4「支持向量检索」+ 08 §4.1 的低带宽约束。"""

    def test_returns_memory_dim_vector(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        m.write(write_request((1.0, 2.0, 3.0, 4.0), 0.5), vec(*ctx(0)), _obs(0.0), fb())
        out = m.retrieve(vec(*ctx(0)))
        assert out.shape == (16,)

    def test_empty_memory_is_honest_zero(self) -> None:
        """与 ZeroMemoryRetriever 不可区分——诚实的空。"""

        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        out = m.retrieve(vec(*ctx(0)))
        assert out.shape == (16,)
        assert float(out.abs().sum()) == 0.0
        assert m.stats.misses == 1
        assert m.stats.hits == 0

    def test_no_hit_above_threshold_is_honest_zero(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0), importance=0.9))
        out = m.retrieve(vec(*ctx(90)))
        assert float(out.abs().sum()) == 0.0
        assert m.stats.misses == 1

    def test_hit_packs_content_into_slots(self) -> None:
        m = mem(top_k=4)
        m.write_item(
            item(memory_id="a", context=ctx(0), content=(1.0, 2.0, 3.0, 4.0))
        )
        out = m.retrieve(vec(*ctx(0)), now=1.0)
        assert float(out[0]) == pytest.approx(1.0)
        assert float(out[1]) == pytest.approx(2.0)
        assert float(out[2]) == pytest.approx(3.0)
        assert float(out[3]) == pytest.approx(4.0)
        # 槽位宽度 = memory_dim / top_k = 4
        assert float(out[4]) == 0.0
        assert m.stats.hits == 1

    def test_similarity_weights_the_slot(self) -> None:
        """45° 相似 → 内容按 cos45° 缩放。"""

        m = mem(top_k=4)
        m.write_item(item(memory_id="a", context=ctx(0), content=(2.0, 4.0)))
        out = m.retrieve(vec(*ctx(45)))
        assert float(out[0]) == pytest.approx(2.0 / math.sqrt(2.0), abs=1e-5)
        assert float(out[1]) == pytest.approx(4.0 / math.sqrt(2.0), abs=1e-5)

    def test_top_k_limits_slots_used(self) -> None:
        """三条都过阈值，但用上的槽位数不超过 top_k。"""

        m2 = mem(top_k=2, merge_threshold=0.0)
        m4 = mem(top_k=4, merge_threshold=0.0)
        for m in (m2, m4):
            for i, deg in enumerate((0.0, 20.0, 40.0)):
                m.write_item(item(memory_id=f"a{i}", context=ctx(deg), content=(1.0,)))
        q = vec(*ctx(0))
        assert slots_used(m4.retrieve(q), 4) == 3
        assert slots_used(m2.retrieve(q), 2) == 2, "第三条没有槽位可落"

    def test_slot_layout_is_stable_across_counts(self) -> None:
        """m_t 的形状不随库内条数变——这是低带宽约束的硬性部分。"""

        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        m.write_item(item(memory_id="a", context=ctx(0)))
        one = m.retrieve(vec(*ctx(0)))
        for i in range(1, 8):
            m.write_item(item(memory_id=f"a{i}", context=ctx(i * 20.0)))
        many = m.retrieve(vec(*ctx(0)))
        assert one.shape == many.shape == (16,)

    def test_min_similarity_filters(self) -> None:
        m = mem(min_similarity=0.9)
        m.write_item(item(memory_id="a", context=ctx(0)))
        out = m.retrieve(vec(*ctx(30)))
        assert float(out.abs().sum()) == 0.0

    def test_importance_floor_filters(self) -> None:
        m = mem(importance_floor=0.8)
        m.write_item(item(memory_id="low", context=ctx(0), importance=0.2))
        out = m.retrieve(vec(*ctx(0)))
        assert float(out.abs().sum()) == 0.0
        assert m.stats.misses == 1

    def test_type_filter_excludes_by_default(self) -> None:
        """RULE / SKILL 不进 m_t——它们是跨情境的结论，不是当前情境。"""

        m = MemorySystem()
        m.write_item(item(memory_id="r", context=ctx(0), memory_type="RULE"))
        out = m.retrieve(vec(*ctx(0)))
        assert float(out.abs().sum()) == 0.0

    def test_stride_caches_last_result(self) -> None:
        """低频检索：非检索帧沿用上一次的 m_t。"""

        m = mem(stride=3)
        m.write_item(item(memory_id="a", context=ctx(0), content=(1.0,)))
        first = m.retrieve(vec(*ctx(0)))
        assert m.stats.retrievals == 1
        second = m.retrieve(vec(*ctx(0)))
        assert m.stats.retrievals == 1
        assert torch.allclose(first, second)
        m.retrieve(vec(*ctx(0)))
        assert m.stats.retrievals == 1, "第 3 帧仍在跳过窗口内"
        fourth = m.retrieve(vec(*ctx(0)))
        assert m.stats.retrievals == 2
        assert torch.allclose(first, fourth)

    def test_cached_result_is_a_clone(self) -> None:
        """调用方改返回值不能污染缓存。"""

        m = mem(stride=2)
        m.write_item(item(memory_id="a", context=ctx(0), content=(1.0,)))
        first = m.retrieve(vec(*ctx(0)))
        first[0] = 999.0
        second = m.retrieve(vec(*ctx(0)))
        assert float(second[0]) != 999.0

    def test_zero_query_never_matches(self) -> None:
        """零向量没有方向——它不该与任何东西相似。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        out = m.retrieve(torch.zeros(2))
        assert float(out.abs().sum()) == 0.0

    def test_hit_updates_retrieval_count(self) -> None:
        """retrieval_count 是可遗传筛选的输入之一，必须真的在动。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.retrieve(vec(*ctx(0)), now=5.0)
        assert m.get("a").retrieval_count == 1
        assert m.get("a").last_retrieved == 5.0

    def test_frozen_items_are_replaced_not_mutated(self) -> None:
        """MemoryItem 是 frozen——更新计数必须产副本。"""

        m = mem()
        original = item(memory_id="a", context=ctx(0))
        m.write_item(original)
        m.retrieve(vec(*ctx(0)), now=1.0)
        assert original.retrieval_count == 0
        assert m.get("a") is not original

    def test_touch_does_not_invalidate_the_index(self) -> None:
        """命中只改计数不改向量——索引不该为此重建。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.retrieve(vec(*ctx(0)), now=1.0)
        assert not m._index_dirty

    def test_frame_count_increments_even_on_stride_skip(self) -> None:
        m = mem(stride=4)
        m.retrieve(vec(*ctx(0)))
        m.retrieve(vec(*ctx(0)))
        assert m.stats.frames == 2
        assert m.stats.retrievals == 1


# ----------------------------------------------------------------------
#  recall
# ----------------------------------------------------------------------


class TestRecall:
    """慢环与观察员的入口：返回记忆项本身，范围由调用方指定。"""

    def test_returns_items_not_vectors(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        out = m.recall(vec(*ctx(0)))
        assert len(out) == 1
        assert out[0].id == "a"

    def test_can_override_types(self) -> None:
        m = mem()
        m.write_item(item(memory_id="e", context=ctx(0)))
        m.write_item(item(memory_id="r", context=ctx(20), memory_type="RULE"))
        out = m.recall(vec(*ctx(0)), types=("RULE",))
        assert [i.id for i in out] == ["r"]

    def test_can_override_top_k(self) -> None:
        m = mem(top_k=1)
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.write_item(item(memory_id="b", context=ctx(20)))
        assert len(m.recall(vec(*ctx(0)))) == 1
        assert len(m.recall(vec(*ctx(0)), top_k=5)) == 2

    def test_empty_types_returns_nothing(self) -> None:
        """显式空范围 = 谁都不召回。白名单语义，与 allowed_operations 同构。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        assert m.recall(vec(*ctx(0)), types=()) == ()

    def test_min_similarity_still_applies(self) -> None:
        """"什么算命中"是策略的定义，不该由调用方每次重定。"""

        m = mem(min_similarity=0.95)
        m.write_item(item(memory_id="a", context=ctx(0)))
        assert m.recall(vec(0.3, 1.0)) == ()


# ----------------------------------------------------------------------
#  容量与淘汰
# ----------------------------------------------------------------------


class TestCapacity:
    """07 §6.4「支持容量限制」。"""

    def test_evicts_when_full(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16, capacity=3), make_context())
        for i in range(5):
            m.write_item(item(memory_id=f"a{i}", context=ctx(i * 20.0)))
        assert len(m) == 3
        assert m.stats.evicted == 2

    def test_evicts_least_important_first(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16, capacity=2), make_context())
        m.write_item(item(memory_id="keep", context=ctx(0), importance=0.9))
        m.write_item(item(memory_id="drop", context=ctx(20), importance=0.1))
        m.write_item(item(memory_id="new", context=ctx(40), importance=0.5))
        assert m.get("drop") is None
        assert m.get("keep") is not None
        assert m.get("new") is not None

    def test_eviction_prefers_never_retrieved(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16, capacity=2), make_context())
        m.write_item(
            item(memory_id="used", context=ctx(0), importance=0.4, retrieval_count=5)
        )
        m.write_item(
            item(memory_id="fresh", context=ctx(20), importance=0.4, retrieval_count=0)
        )
        m.write_item(item(memory_id="new", context=ctx(40), importance=0.4))
        assert m.get("fresh") is None

    def test_eviction_order_matches_items_order(self) -> None:
        """排序与淘汰共用一把尺，只是方向相反。"""

        m = MemorySystem(MemoryConfig(memory_dim=16, capacity=2), make_context())
        m.write_item(item(memory_id="a", context=ctx(0), importance=0.9))
        m.write_item(item(memory_id="b", context=ctx(20), importance=0.5))
        m.write_item(item(memory_id="c", context=ctx(40), importance=0.7))
        assert [i.id for i in m.items()] == ["a", "c"]

    def test_capacity_one_still_works(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16, capacity=1), make_context())
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.write_item(item(memory_id="b", context=ctx(20)))
        assert len(m) == 1
        assert m.get("b") is not None

    def test_capacity_zero_is_a_config_error(self) -> None:
        """0 会让"容量限制"退化成"禁止记忆"。"""

        with pytest.raises(ValueError, match="至少为 1"):
            MemoryConfig(memory_dim=16, capacity=0)

    def test_memory_dim_zero_is_a_config_error(self) -> None:
        with pytest.raises(ValueError, match="为正"):
            MemoryConfig(memory_dim=0)


# ----------------------------------------------------------------------
#  合并
# ----------------------------------------------------------------------


class TestMerge:
    """07 §6.4「支持记忆合并」。"""

    def test_identical_context_merges(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        out = m.write_item(item(memory_id="b", context=ctx(0)))
        assert out is not None
        assert out.id == "a", "合并后留下的是旧项——记忆的身份是它第一次被记下的时刻"
        assert len(m) == 1
        assert m.stats.merged == 1

    def test_merge_boosts_importance(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0), importance=0.5))
        out = m.write_item(item(memory_id="b", context=ctx(0), importance=0.4))
        assert out is not None
        assert out.importance == pytest.approx(0.5 + MERGE_IMPORTANCE_BOOST)

    def test_merge_importance_is_capped_at_one(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0), importance=0.98))
        out = m.write_item(item(memory_id="b", context=ctx(0), importance=0.98))
        assert out is not None
        assert out.importance == 1.0

    def test_merge_counts_as_a_retrieval(self) -> None:
        """重复经历同一情境即计一次——这是可遗传筛选需要的量。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.write_item(item(memory_id="b", context=ctx(0)))
        m.write_item(item(memory_id="c", context=ctx(0)))
        assert m.get("a").retrieval_count == 2

    def test_different_context_does_not_merge(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.write_item(item(memory_id="b", context=ctx(20)))
        assert len(m) == 2

    def test_cross_type_merge_is_refused(self) -> None:
        """类型是可遗传性的判据，不能合并成一笔糊涂账。"""

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0), memory_type="EVENT"))
        m.write_item(
            item(memory_id="b", context=ctx(0), memory_type="BODY_EXPERIENCE")
        )
        assert len(m) == 2
        assert m.stats.merged == 0

    def test_merge_takes_the_stronger_content(self) -> None:
        m = mem()
        m.write_item(
            item(memory_id="a", context=ctx(0), importance=0.2, content=(1.0,))
        )
        out = m.write_item(
            item(memory_id="b", context=ctx(0), importance=0.9, content=(9.0,))
        )
        assert out is not None
        assert out.content_vector == (9.0,)

    def test_merge_updates_timestamp_and_outcome(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0), timestamp=1.0))
        out = m.write_item(item(memory_id="b", context=ctx(0), timestamp=9.0))
        assert out is not None
        assert out.timestamp == 9.0

    def test_merge_keeps_the_index_valid(self) -> None:
        """合并后留下的是旧项，检索键没变——索引无需重建。

        真正让索引失效的是**插入**：新键要进矩阵。这一条把两者分开，
        否则"命中就重建索引"会让低频检索的收益被索引重建吃回去。
        """

        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.retrieve(vec(*ctx(0)))
        assert not m._index_dirty, "检索后索引应是干净的"
        m.write_item(item(memory_id="b", context=ctx(0)))
        assert not m._index_dirty, "合并没引入新键"
        m.write_item(item(memory_id="c", context=ctx(40)))
        assert m._index_dirty, "插入新键必须让索引失效"


# ----------------------------------------------------------------------
#  排序与可继承
# ----------------------------------------------------------------------


class TestOrdering:
    """07 §6.4「支持重要度排序」。"""

    def test_items_sorted_by_importance_desc(self) -> None:
        m = mem()
        m.write_item(item(memory_id="lo", context=ctx(0), importance=0.1))
        m.write_item(item(memory_id="hi", context=ctx(20), importance=0.9))
        m.write_item(item(memory_id="mid", context=ctx(40), importance=0.5))
        assert [i.id for i in m.items()] == ["hi", "mid", "lo"]

    def test_ties_broken_by_retrieval_count(self) -> None:
        m = mem()
        m.write_item(item(memory_id="cold", context=ctx(0), importance=0.5))
        m.write_item(
            item(memory_id="warm", context=ctx(20), importance=0.5, retrieval_count=3)
        )
        assert [i.id for i in m.items()] == ["warm", "cold"]

    def test_most_important_is_a_prefix(self) -> None:
        m = mem()
        for i in range(5):
            m.write_item(
                item(
                    memory_id=f"a{i}",
                    context=ctx(i * 20.0),
                    importance=i / 10.0,
                )
            )
        assert [i.id for i in m.most_important(2)] == ["a4", "a3"]

    def test_most_important_of_zero(self) -> None:
        assert mem().most_important(0) == ()

    def test_most_important_beyond_size(self) -> None:
        m = mem()
        m.write_item(item(memory_id="a", context=ctx(0)))
        assert len(m.most_important(99)) == 1


class TestHeritable:
    """08 §3.3 可继承筛选 + 07 风险 5 的记忆规模缓解。"""

    def test_transient_types_are_not_heritable(self) -> None:
        m = mem()
        m.write_item(
            item(memory_id="e", context=ctx(0), importance=1.0, retrieval_count=9)
        )
        assert m.heritable() == ()

    def test_rule_and_skill_are_heritable_when_thresholds_met(self) -> None:
        m = mem()
        m.write_item(
            item(
                memory_id="r",
                context=ctx(0),
                memory_type="RULE",
                importance=0.9,
                retrieval_count=2,
            )
        )
        m.write_item(
            item(
                memory_id="s",
                context=ctx(20),
                memory_type="SKILL",
                importance=0.9,
                retrieval_count=2,
            )
        )
        assert {i.id for i in m.heritable()} == {"r", "s"}

    def test_importance_threshold_comes_from_policy(self) -> None:
        m = mem(heritable_importance=0.9)
        m.write_item(
            item(
                memory_id="r",
                context=ctx(0),
                memory_type="RULE",
                importance=0.8,
                retrieval_count=5,
            )
        )
        assert m.heritable() == ()

    def test_retrieval_threshold_comes_from_policy(self) -> None:
        m = mem(heritable_min_retrievals=3)
        m.write_item(
            item(
                memory_id="r",
                context=ctx(0),
                memory_type="RULE",
                importance=0.9,
                retrieval_count=1,
            )
        )
        assert m.heritable() == ()

    def test_load_heritable_drops_transient(self) -> None:
        """子代不加载瞬时记忆——记忆规模不随世代累积。"""

        m = MemorySystem()
        loaded = m.load_heritable(
            [
                item(memory_id="e", context=ctx(0)),
                item(
                    memory_id="r",
                    context=ctx(20),
                    memory_type="RULE",
                    importance=0.9,
                ),
            ]
        )
        assert loaded == 1
        assert [i.id for i in m.items()] == ["r"]

    def test_load_heritable_keeps_ids(self) -> None:
        """继承的记忆保留父代的 id——子代要能追到它是哪一条。"""

        m = MemorySystem()
        m.load_heritable(
            [
                item(
                    memory_id="rule_from_parent",
                    context=ctx(0),
                    memory_type="RULE",
                    importance=0.9,
                )
            ]
        )
        assert m.get("rule_from_parent") is not None

    def test_load_heritable_counts_each_loaded_item(self) -> None:
        m = MemorySystem()
        loaded = m.load_heritable(
            [
                item(
                    memory_id="r1",
                    context=ctx(0),
                    memory_type="RULE",
                    importance=0.9,
                ),
                item(
                    memory_id="r2",
                    context=ctx(20),
                    memory_type="RULE",
                    importance=0.9,
                ),
            ]
        )
        assert loaded == 2
        assert len(m) == 2


# ----------------------------------------------------------------------
#  上下文切换
# ----------------------------------------------------------------------


class TestUseContext:
    """换结构版本：策略跟着换，记忆本体不动。"""

    def test_policy_is_reread(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        assert m.policy["top_k"] == 4
        m.use_context(make_context(retrieval={"top_k": 2}))
        assert m.policy["top_k"] == 2

    def test_memory_survives(self) -> None:
        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        m.write_item(item(memory_id="a", context=ctx(0)))
        m.use_context(make_context(retrieval={"top_k": 2}))
        assert len(m) == 1

    def test_fingerprint_tracks_the_source_snapshot(self) -> None:
        c = make_context(retrieval={"top_k": 2})
        m = MemorySystem(MemoryConfig(memory_dim=16), c)
        assert m.context_fingerprint == c.fingerprint()

    def test_no_context_leaves_fingerprint_none(self) -> None:
        assert MemorySystem().context_fingerprint is None

    def test_incompatible_new_policy_fails_loudly(self) -> None:
        """新快照的策略不能把 m_t 的分槽布局弄坏。"""

        m = MemorySystem(MemoryConfig(memory_dim=16), make_context())
        with pytest.raises(ValueError, match="整除"):
            m.use_context(make_context(retrieval={"top_k": 3}))


# ----------------------------------------------------------------------
#  跨模块一致性
# ----------------------------------------------------------------------


class TestCrossModuleContract:
    """m_t 的维度契约横跨三个模块，任一环改动都会打破它。"""

    def test_memory_dim_matches_state_core(self) -> None:
        assert MemoryConfig.memory_dim == StateCoreConfig().memory_dim

    def test_top_k_divides_state_core_memory_dim(self) -> None:
        dim = StateCoreConfig().memory_dim
        top_k = DEFAULT_RETRIEVAL_POLICY["top_k"]
        assert dim % top_k == 0

    def test_default_content_fits_the_default_slot(self) -> None:
        """ActionDecoder 产出的 content 长度必须放进一个槽位。"""

        dim = StateCoreConfig().memory_dim
        top_k = DEFAULT_RETRIEVAL_POLICY["top_k"]
        assert ActionDecoderConfig().memory_content_dim <= dim // top_k

    def test_content_longer_than_slot_is_truncated_and_counted(self) -> None:
        """截断是允许的，但必须计数——静默截断会让"存了什么"不可审计。"""

        m = mem(top_k=4)  # 槽位宽 4
        m.write_item(
            item(
                memory_id="a",
                context=ctx(0),
                content=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0),
            )
        )
        m.retrieve(vec(*ctx(0)))
        assert m.stats.truncated == 1
        assert float(m.retrieve(vec(*ctx(0)))[4]) == 0.0

    def test_content_shorter_than_slot_is_padded(self) -> None:
        m = mem(top_k=4)
        m.write_item(item(memory_id="a", context=ctx(0), content=(7.0,)))
        out = m.retrieve(vec(*ctx(0)))
        assert float(out[0]) == pytest.approx(7.0)
        assert float(out[1]) == 0.0
