"""Plasticity Controller + LocalPlasticity 测试 —— 增量 3。

对应 [docs/13-milestone4-plan.md](../docs/13-milestone4-plan.md) §3 的验收：

> | 3 | **Plasticity Controller + LocalPlasticity** | 价值路径；解「门控不开」；
> | ``allowed_scope`` 划定更新边界 | 记忆门在训练后开启率显著高于随机初始化 | ⬜ |

本文件把这条验收拆成四组可判定的断言：

1. **边界**（``TestScopeBoundary``）—— 07 §6.7 的不可更新清单是**先于**白名单
   匹配的；未登记边界的键提不出提案。白名单而非黑名单：一个忘了登记的键
   应当沉默，而不是悄悄改掉某个机制。
2. **沉默**（``TestNotTautological``）—— 三条症状都不成立时**一条提案都没有**。
   这条比"症状成立时提了提案"更重要：一个永远提案的规则不需要证据，
   也就没有信息。门开着而模型选 ``store=False`` 是一个**决定**，不是缺失。
3. **收敛**（``TestConvergesOnce``）—— 换版之后不再提案。不收敛的规则会把
   阈值一路推到边界上，那是撞夹子不是调参（``_current_window`` 的回归钉子）。
4. **成效**（``TestAcceptance``）—— 记忆门开启率在训练后显著高于随机初始化，
   且**该沉默的种子保持沉默**。

第 4 条是本文件的落点，但前三条是它的前提：没有边界，成效来自乱改；
没有沉默，成效来自每次都改；不收敛，成效来自推到边界。
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest
import torch

from SSEA.action_decoder import GATE_THRESHOLD_KEYS
from SSEA.environment import Environment
from SSEA.fast_loop import STATE_RUN, FastLoop, FastLoopConfig
from SSEA.metabolic_monitor import MetabolicMonitor
from SSEA.plasticity import (
    DEFAULT_BOUNDS,
    DEFERRED_SCOPES,
    IMPLEMENTED_SCOPES,
    NON_UPDATABLE,
    UPDATABLE_SCOPES,
    LocalPlasticity,
    PlasticityConfig,
    PlasticityController,
    PlasticityObservation,
    PlasticityScope,
)
from SSEA.sse_protocols import (
    Action,
    Feedback,
    Locomotion,
    MemoryWrite,
)
from SSEA.sse_protocols.event_vector import EventVector
from SSEA.sse_protocols.structure_store import PROPOSAL_KIND_MAP, StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate
from tests.conftest import make_context
from tests.test_verification_gate import THRESHOLD_KEY

MEMORY_KEY = GATE_THRESHOLD_KEYS["memory"]
SIMILARITY_KEY = "min_similarity"


# ----------------------------------------------------------------------
#  助手：合成 trace
# ----------------------------------------------------------------------


def move() -> Action:
    return Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0))


def with_memory(store: bool = True, importance: float = 0.5) -> Action:
    """一条带着记忆写入请求的动作。``store`` 是模型的**决定**。"""

    return Action(
        locomotion=Locomotion((1.0, 0.0), 0.5, 1.0),
        memory=MemoryWrite(store=store, content=(0.1, 0.2), importance=importance),
    )


def event(event_id: str, event_type: str) -> EventVector:
    return EventVector(
        event_id=event_id,
        timestamp=0.0,
        event_type=event_type,
        source_id="test",
        context_vector=(),
        importance=0.5,
    )


def frame(
    n: int,
    *,
    action: Action = move(),
    error: float = 0.0,
    fingerprint: tuple[tuple[str, int], ...] = (("thresholds", 0),),
    events: tuple[EventVector, ...] = (),
    state: str = STATE_RUN,
) -> object:
    """一条 StepRecord。

    默认指纹 ``thresholds@0``：让 ``_current_window`` 有版本可切，
    也顺带证明空指纹会退化成整条 trace（见 ``test_empty_fingerprint_uses_all``）。
    """

    from SSEA.fast_loop import StepRecord

    return StepRecord(
        frame=n,
        state=state,
        observation=_observation(events),
        feedback=Feedback(
            energy_change=0.0,
            damage_change=0.0,
            fatigue_change=0.0,
            prediction_error=error,
            action_success=True,
            survived=True,
        ),
        decoded_action=action,
        executed_action=action,
        skill_event=None,
        context_fingerprint=fingerprint,
        intent=None,
    )


def _observation(events: tuple[EventVector, ...]) -> object:
    from SSEA.sse_protocols import (
        BodyState,
        EnvironmentSummary,
        Observation,
        default_constraints,
    )

    return Observation(
        time=0.0,
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
        events=events,
    )


def trace_of(*frames: object) -> tuple:
    return tuple(frames)


# ----------------------------------------------------------------------
#  边界（07 §6.7）
# ----------------------------------------------------------------------


class TestScopeBoundary:
    """``allowed_scope`` 是白名单；不可更新清单先于它匹配。"""

    def test_non_updatable_list_beats_the_whitelist(self) -> None:
        """禁止清单**先于**白名单。

        顺序是刻意的：若先查 kinds/bounds，将来有人把一个禁止项登记进
        白名单（``bounds={"core_weights": (0,1)}`` 这种），禁止清单会被
        白名单悄悄盖掉——而那正好是 07 §16 要防的事。
        """

        scope = PlasticityScope(
            kinds=("thresholds",), bounds={**DEFAULT_BOUNDS, "core_weights": (0.0, 1.0)}
        )
        allowed, why = PlasticityController(scope).allows("thresholds", "core_weights")
        assert not allowed
        assert "不可更新" in why

    def test_every_non_updatable_scope_is_refused(self) -> None:
        """07 §6.7 那七项，逐项拒绝。

        逐项而不是只测一两个：这张清单的共性是"改了它们，验证这件事本身
        就不再可信"，漏一项就漏一类。
        """

        controller = PlasticityController()
        for name in NON_UPDATABLE:
            allowed, why = controller.allows(name, MEMORY_KEY)
            assert not allowed, f"{name} 居然被允许更新"
            assert "不可更新" in why

    def test_unregistered_key_is_refused(self) -> None:
        """没登记边界的键不可改——白名单，不是黑名单。"""

        controller = PlasticityController()
        allowed, why = controller.allows("thresholds", "some_unlisted_key")
        assert not allowed
        assert "白名单" in why

    def test_kind_outside_allowed_scope_is_refused(self) -> None:
        controller = PlasticityController()
        allowed, why = controller.allows("rules", "whatever")
        assert not allowed
        assert "allowed_scope" in why

    def test_registered_key_and_kind_is_allowed(self) -> None:
        controller = PlasticityController()
        assert controller.allows("thresholds", MEMORY_KEY)[0]
        assert controller.allows("retrieval", SIMILARITY_KEY)[0]

    def test_scope_kinds_must_be_real_structure_kinds(self) -> None:
        """``kinds`` 只能是 PROPOSAL_KIND_MAP 里的类别——拼错的类别该在建表时炸。"""

        with pytest.raises(ValueError, match="未知的结构类别"):
            PlasticityScope(kinds=("thresolds",))

    def test_min_step_must_fit_inside_max_step(self) -> None:
        with pytest.raises(ValueError, match="min_step"):
            PlasticityScope(max_step=0.1, min_step=0.2)

    def test_the_two_lists_are_disjoint(self) -> None:
        """可更新与不可更新不能有交集。有交集意味着同一件事既允许又禁止。"""

        assert not (set(UPDATABLE_SCOPES) & set(NON_UPDATABLE))

    def test_implemented_is_a_subset_of_updatable(self) -> None:
        assert set(IMPLEMENTED_SCOPES) <= set(UPDATABLE_SCOPES)

    def test_deferred_scopes_are_declared_not_stubbed(self) -> None:
        """未实现的落点是**声明出来的常量**，不是返回空的方法。

        「协议不容无消费者的通道」（08 §2.4）对函数同样成立：一个恒返回
        空 tuple 的 ``propose_adapters()`` 会让文档可以写"已实现"。
        键集被这条测试守着：落地时必须同步改。
        """

        assert set(DEFERRED_SCOPES) == {"adapters", "policy_heads"}
        for why in DEFERRED_SCOPES.values():
            assert why  # 每一项都要说得出为什么现在不做


# ----------------------------------------------------------------------
#  观测（纯读）
# ----------------------------------------------------------------------


class TestObservation:
    """``observe`` 只读不写，且三种帧必须可区分。"""

    def test_three_frame_categories_are_distinguishable(self) -> None:
        """门没开 / 门开了但决定不记 / 记了——三件事不能混成一类。

        混成一类的后果是灾难性的：规则会把"模型决定不记"当成"门没开"，
        于是一次次降低阈值去修一个不是缺失的东西。

        惊奇度取 (1.0, 0.9, 0.5, 0.1, 0.0)，中位数切在 0.5：前三帧算"值得记"。
        那三帧分别是"门没开 / 门开了决定不记 / 门开了记了"——三类各一格。
        """

        trace = trace_of(
            frame(0, action=move(), error=1.0),                    # 门没开，且值得记
            frame(1, action=with_memory(store=False), error=0.9),  # 门开了，决定不记
            frame(2, action=with_memory(store=True), error=0.5),   # 门开了，记了
            frame(3, action=with_memory(store=True), error=0.1),
            frame(4, action=with_memory(store=True), error=0.0),
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.run_frames == 5
        assert obs.gate_closed == 1
        assert obs.declined == 1
        assert obs.surprising == 3
        # 三个"值得记"的帧里只有一个真的没被记——另两个是模型的**决定**与真的记了
        assert obs.missed_surprise == 1

    def test_declined_frames_do_not_count_as_missing(self) -> None:
        """门开着而 ``store=False`` 是**一个决定**，不是缺失。

        这是症状 1 措辞的落点："门从没开过"才修。按"开得不够多"修会去动
        ``mem_store`` 头的职权范围，而那是参数侧的 Δθ（见 DEFERRED_SCOPES）。
        """

        trace = trace_of(*[frame(i, action=with_memory(False), error=1.0) for i in range(5)])
        obs = LocalPlasticity().observe(trace)
        assert obs.gate_closed == 0 and obs.declined == 5
        assert obs.missed_surprise == 0
        assert LocalPlasticity().propose(trace) == ()

    def test_missed_surprise_counts_gate_closed_surprising_frames(self) -> None:
        trace = trace_of(
            frame(0, action=move(), error=1.0),
            frame(1, action=move(), error=0.0),
        )
        obs = LocalPlasticity().observe(trace)
        # 分位数切在 0.5 处：只有 error=1.0 那帧算"值得记"
        assert obs.surprising == 1
        assert obs.missed_surprise == 1

    def test_sleep_and_wake_frames_are_ignored(self) -> None:
        """SLEEP / WAKE 帧没有解码动作，参与判定会凭空造出"门没开"。"""

        trace = trace_of(
            frame(0, action=with_memory(True), error=1.0),
            frame(1, action=move(), error=0.0, state="SLEEP"),
            frame(2, action=move(), error=0.0, state="WAKE"),
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.run_frames == 1

    def test_events_are_deduped_by_id_not_counted_per_frame(self) -> None:
        """环境的 ``events`` 是滚动窗口，同一事件会连续出现在十几帧里。

        按帧数会把一次写入数成十几次，于是"读不回来"的症状被噪声淹没。
        """

        repeated = (event("e1", "MEMORY_STORED"),)
        trace = trace_of(
            *[frame(i, action=with_memory(True), events=repeated) for i in range(10)]
        )
        assert LocalPlasticity().observe(trace).store_requests == 1

    def test_event_types_are_not_confused(self) -> None:
        trace = trace_of(
            *[
                frame(
                    i,
                    action=with_memory(True),
                    events=(event(f"s{i}", "MEMORY_STORED"), event(f"r{i}", "MEMORY_RETRIEVED")),
                )
                for i in range(3)
            ]
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.store_requests == 3
        assert obs.retrieved == 3

    def test_observe_does_not_mutate_the_trace(self) -> None:
        trace = trace_of(*[frame(i, action=move(), error=float(i)) for i in range(5)])
        before = tuple(trace)
        LocalPlasticity().observe(trace)
        assert trace == before


# ----------------------------------------------------------------------
#  证据窗口（_current_window）
# ----------------------------------------------------------------------


class TestEvidenceWindow:
    """判定只看**当前结构版本**产出的那一段帧。"""

    def test_only_the_current_version_is_used(self) -> None:
        """换版之前的"门没开"是旧策略的账。

        不切这一刀的后果实测过（seed 2）：三轮睡眠把阈值从 0.5 推到
        0.4 → 0.3 → 0.15（下界），而第二、三轮的触发证据全部来自第一轮
        之前。那是撞夹子，不是调参。
        """

        trace = trace_of(
            *[frame(i, action=move(), error=1.0, fingerprint=(("thresholds", 0),)) for i in range(5)],
            *[frame(i, action=with_memory(True), error=1.0, fingerprint=(("thresholds", 1),)) for i in range(5, 8)],
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.run_frames == 3
        assert obs.trace_frames == 8
        assert obs.missed_surprise == 0

    def test_trace_frames_records_what_was_discarded(self) -> None:
        """"判定用了多少证据"必须可回答。

        只有 run_frames 的话，一次基于 2 帧的判定与一次基于 60 帧的判定
        在日志里长得一样。
        """

        trace = trace_of(
            *[frame(i, action=move(), error=1.0, fingerprint=(("thresholds", 0),)) for i in range(9)],
            frame(9, action=with_memory(True), error=1.0, fingerprint=(("thresholds", 1),)),
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.run_frames == 1 and obs.trace_frames == 10

    def test_empty_fingerprint_uses_the_whole_trace(self) -> None:
        """没有版本信息就没有归因可言——退化成整条 trace，而不是抛异常。"""

        trace = trace_of(*[frame(i, action=move(), error=1.0, fingerprint=()) for i in range(4)])
        obs = LocalPlasticity().observe(trace)
        assert obs.run_frames == 4 and obs.trace_frames == 4

    def test_switching_to_an_unrelated_kind_still_windows(self) -> None:
        """慢环同时改 skills 与 thresholds 时，指纹整体变化，窗口照样切得动。"""

        trace = trace_of(
            frame(0, action=move(), error=1.0, fingerprint=(("skills", 0), ("thresholds", 0))),
            frame(1, action=with_memory(True), error=1.0, fingerprint=(("skills", 1), ("thresholds", 0))),
        )
        assert LocalPlasticity().observe(trace).run_frames == 1


# ----------------------------------------------------------------------
#  沉默（规则不能恒真）
# ----------------------------------------------------------------------


class TestNotTautological:
    """症状不成立时**一条提案都没有**。"""

    def test_no_run_frames_means_silence(self) -> None:
        trace = trace_of(frame(0, action=move(), error=1.0, state="SLEEP"))
        assert LocalPlasticity().observe(trace) == PlasticityObservation()
        assert LocalPlasticity().propose(trace) == ()

    def test_empty_trace_means_silence(self) -> None:
        assert LocalPlasticity().propose(()) == ()

    def test_healthy_path_means_silence(self) -> None:
        """门开着、也真的读得回来——没有任何症状，一条提案都没有。"""

        trace = trace_of(
            *[
                frame(
                    i,
                    action=with_memory(True),
                    error=float(i % 3),
                    events=(event(f"s{i}", "MEMORY_STORED"), event(f"r{i}", "MEMORY_RETRIEVED")),
                )
                for i in range(10)
            ]
        )
        assert LocalPlasticity().propose(trace) == ()

    def test_already_at_the_bound_means_silence(self) -> None:
        """症状还在，但可调范围用完了。

        这条沉默是有信息的：它说明"放宽阈值"这条路走到头了，下一步该做的
        不是继续推，是去做 DEFERRED_SCOPES 里的参数侧。
        """

        structure = make_context()
        structure = replace(
            structure, thresholds={MEMORY_KEY: DEFAULT_BOUNDS[MEMORY_KEY][0]}
        )
        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        assert LocalPlasticity().propose(trace, structure) == ()

    def test_a_step_smaller_than_min_step_means_silence(self) -> None:
        """噪声级的改动不提提案——它只会占一条审计记录。"""

        structure = replace(
            make_context(),
            thresholds={MEMORY_KEY: DEFAULT_BOUNDS[MEMORY_KEY][0] + 0.001},
        )
        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        assert LocalPlasticity().propose(trace, structure) == ()

    def test_short_window_does_not_trigger_the_relational_symptom(self) -> None:
        """症状 2 是**关系**断言，两帧不配叫"从来读不回来"。

        两条症状对证据量的要求刻意不同：症状 1 是逐帧性质（单帧上就是真的），
        症状 2 要写入与读取双方都有机会发生。不设下限的后果实测过：短窗口下
        规则每轮都触发，把 min_similarity 一路推到下界 0.01——恒命中，
        机制被关掉而不是被调好。
        """

        trace = trace_of(
            *[frame(i, action=with_memory(True), events=(event(f"s{i}", "MEMORY_STORED"),)) for i in range(3)]
        )
        obs = LocalPlasticity().observe(trace)
        assert obs.store_requests == 3 and obs.retrieved == 0
        assert LocalPlasticity().propose(trace) == ()

    def test_but_a_long_window_does(self) -> None:
        trace = trace_of(
            *[frame(i, action=with_memory(True), events=(event(f"s{i}", "MEMORY_STORED"),)) for i in range(10)]
        )
        proposals = LocalPlasticity().propose(trace)
        assert [p.target for p in proposals] == [SIMILARITY_KEY]


# ----------------------------------------------------------------------
#  提案形状
# ----------------------------------------------------------------------


class TestProposalShape:
    """提案必须正好落在 Gate 认得的形状上——否则四级检查在第一级就拒。"""

    def test_payload_key_matches_what_the_gate_requires(self) -> None:
        """payload 的键名与 Gate 的 ``_REQUIRED_PAYLOAD_KEY`` 一致。

        两份清单必然漂移，而漂移的表现是"编译器提了、Gate 拒了、日志里
        看不出为什么"。所以这里**从 Gate 那张表取**，不另写一份。
        """

        from SSEA.verification_gate import _REQUIRED_PAYLOAD_KEY

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        (proposal,) = LocalPlasticity().propose(trace)
        required = _REQUIRED_PAYLOAD_KEY[proposal.proposal_type]
        assert required in proposal.payload

    def test_proposal_type_matches_the_kind(self) -> None:
        assert PROPOSAL_KIND_MAP["UPDATE_THRESHOLD"] == "thresholds"
        assert PROPOSAL_KIND_MAP["UPDATE_RETRIEVAL_POLICY"] == "retrieval"

    def test_proposal_id_is_content_derived(self) -> None:
        """id 由内容导出（``前缀-目标``），不由调用次数导出。

        计数器式 id 会让同一条 trace 在两次编译下得到两个 id，于是
        「这是重复提案」要一次集合运算才能回答（与增量 2 同一条理由）。
        """

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        first = LocalPlasticity().propose(trace)
        second = LocalPlasticity().propose(trace)
        assert [p.proposal_id for p in first] == [p.proposal_id for p in second]
        assert first[0].proposal_id == f"plasticity-{MEMORY_KEY}"

    def test_risk_level_is_low_and_says_why(self) -> None:
        """作用半径就是这一个键，且方向被 allowed_scope 夹住。

        这不是乐观估计——是这一级改动的真实半径。
        """

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        (proposal,) = LocalPlasticity().propose(trace)
        assert proposal.risk_level == "low"

    def test_reason_names_the_symptom_in_numbers(self) -> None:
        """reason 里要能看出"多少帧、错过了多少"——沉默与提案都要可归因。"""

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        (proposal,) = LocalPlasticity().propose(trace)
        assert str(5) in proposal.reason
        assert "惊奇" in proposal.reason

    def test_expected_effect_carries_the_evidence(self) -> None:
        """证据要跟着提案走：2 个值得记的帧里错过了几个，audit 里看得见。"""

        trace = trace_of(
            frame(0, action=move(), error=1.0),                   # 值得记，门没开
            frame(1, action=move(), error=0.9),                   # 值得记，门没开
            frame(2, action=with_memory(True), error=0.5),
            frame(3, action=with_memory(True), error=0.1),
            frame(4, action=with_memory(True), error=0.0),
        )
        (proposal,) = LocalPlasticity().propose(trace)
        assert proposal.expected_effect == {"missed_surprise": 2, "surprising": 3}

    def test_step_is_bounded_by_max_step(self) -> None:
        """单次改动不超过 max_step——局部可塑性，"局部"两个字由这里保证。"""

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        structure = replace(make_context(), thresholds={MEMORY_KEY: 0.8})
        (proposal,) = LocalPlasticity().propose(trace, structure)
        assert proposal.payload["value"] == pytest.approx(0.7)  # 0.8 - max_step

    def test_value_is_clipped_into_the_bounds(self) -> None:
        controller = PlasticityController()
        low, high = controller.bounds_of(MEMORY_KEY)
        assert controller.clip(MEMORY_KEY, -99.0) == low
        assert controller.clip(MEMORY_KEY, 99.0) == high

    def test_direction_only_supplies_the_sign(self) -> None:
        """``direction`` 只取符号：-1 = 放宽，+1 = 收紧。量由 max_step 决定。"""

        controller = PlasticityController()
        assert controller.step_toward(MEMORY_KEY, 0.5, -1.0) == pytest.approx(0.4)
        assert controller.step_toward(MEMORY_KEY, 0.5, +1.0) == pytest.approx(0.6)
        assert controller.step_toward(MEMORY_KEY, 0.5, -100.0) == pytest.approx(0.4)


# ----------------------------------------------------------------------
#  配置自校验
# ----------------------------------------------------------------------


class TestConfigValidation:
    """配置里的键必须在 DEFAULT_BOUNDS 里登记过。"""

    def test_unbounded_key_is_rejected_at_construction(self) -> None:
        """未登记边界的键不可改——这条在建配置时就该炸，而不是提提案时才炸。"""

        with pytest.raises(ValueError, match="DEFAULT_BOUNDS"):
            PlasticityConfig(memory_gate_key="not_registered")

    def test_similarity_key_must_be_registered(self) -> None:
        with pytest.raises(ValueError, match="DEFAULT_BOUNDS"):
            PlasticityConfig(similarity_key="not_registered")

    def test_quantile_must_be_a_probability(self) -> None:
        with pytest.raises(ValueError, match="surprise_quantile"):
            PlasticityConfig(surprise_quantile=1.5)

    def test_min_evidence_frames_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="min_evidence_frames"):
            PlasticityConfig(min_evidence_frames=0)


# ----------------------------------------------------------------------
#  收敛（_current_window 的行为后果）
# ----------------------------------------------------------------------


class TestConvergesOnce:
    """换版之后，症状消失 → 不再提案。"""

    def test_after_the_fix_the_same_trace_is_silent(self) -> None:
        """症状消失之后，**整条** trace 也提不出提案。

        ``propose`` 拿的是整条 trace，但窗口已经把旧证据切掉了：换版后那五帧
        门是开的，于是 ``missed_surprise == 0``。若这条红，说明窗口没生效——
        规则会把旧账反复算，一路把阈值推到下界。
        """

        before = [frame(i, action=move(), error=1.0, fingerprint=(("thresholds", 0),)) for i in range(5)]
        after = [
            frame(i, action=with_memory(True), error=1.0, fingerprint=(("thresholds", 1),))
            for i in range(5, 10)
        ]
        assert LocalPlasticity().propose(trace_of(*before))  # 旧窗口：症状成立
        assert LocalPlasticity().propose(trace_of(*(before + after))) == ()  # 新窗口：症状消失

    def test_repeated_propose_on_an_unchanged_trace_is_stable(self) -> None:
        """纯函数性：同样的输入同样的输出，与调用历史无关。"""

        trace = trace_of(*[frame(i, action=move(), error=1.0) for i in range(5)])
        plasticity = LocalPlasticity()
        first = plasticity.propose(trace)
        for _ in range(3):
            assert plasticity.propose(trace) == first


# ----------------------------------------------------------------------
#  成效（验收第 4 条）
# ----------------------------------------------------------------------


def _sleep_once_after(n: int) -> MetabolicMonitor:
    """一个只在第 n 次询问时同意睡眠的代谢监控器。

    真实监控器不会每帧都同意——那样睡眠就没有"安全窗口"的含义了。
    这里要的是一次**可定位**的睡眠：前 n 帧训练，睡一次，再看后 n 帧。
    """

    inner = MetabolicMonitor(
        sleep_threat_threshold=1.1, sleep_fatigue_threshold=0.0
    )
    fired = [False]
    asked = [0]

    class OnceAt:
        def drive_vector(self, body):
            return inner.drive_vector(body)

        def observe(self, obs):
            return inner.observe(obs)

        def wants_sleep(self, body, obs) -> bool:
            asked[0] += 1
            if fired[0]:
                return False
            if asked[0] >= n and inner.wants_sleep(body, obs):
                fired[0] = True
                return True
            return False

        def reset(self) -> None:
            inner.reset()

    return OnceAt()  # type: ignore[return-value]


@dataclass
class _Run:
    before: float
    after: float
    proposals: int
    threshold: float | None


def _train_then_measure(seed: int, frames: int = 25) -> _Run:
    """前 ``frames`` 帧 → 睡一次 → 再 ``frames`` 帧，比较换版前后的开门率。"""

    torch.manual_seed(seed)
    env = Environment(seed=seed)
    store = StructureStore()
    from SSEA.experience_compiler import make_slow_loop_hook

    hook = make_slow_loop_hook(
        store, VerificationGate(GateConfig(env_frames=8)), plasticity=LocalPlasticity()
    )
    loop = FastLoop(
        env,
        make_context(),
        metabolic_monitor=_sleep_once_after(frames),
        config=FastLoopConfig(max_frames=4 * frames, min_sleep_frames=3),
        slow_loop=hook,
    )

    loop.run(frames)
    pre = [r for r in loop.trace() if r.state == STATE_RUN]
    before = sum(1 for r in pre if r.decoded_action.memory is not None) / len(pre)

    # 睡完并唤醒（SLEEP 帧出现在末尾时继续走到回 RUN）
    while loop.alive and loop.state != STATE_RUN:
        loop.step()
    loop.run(frames)

    run = [r for r in loop.trace() if r.state == STATE_RUN]
    last = run[-1].context_fingerprint
    post = [r for r in run if r.context_fingerprint == last]
    after = sum(1 for r in post if r.decoded_action.memory is not None) / len(post)

    snap = store.snapshot()
    return _Run(
        before=before,
        after=after,
        proposals=len(store.audit_log()),
        threshold=snap.thresholds.get(MEMORY_KEY),
    )


class TestAcceptance:
    """验收原话：**记忆门在训练后开启率显著高于随机初始化**。"""

    SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)

    def test_open_rate_rises_after_plasticity(self) -> None:
        results = {s: _train_then_measure(s) for s in self.SEEDS}
        before = sum(r.before for r in results.values()) / len(results)
        after = sum(r.after for r in results.values()) / len(results)
        assert after > before, f"开启率没有上升: {before:.3f} -> {after:.3f}"

    def test_the_rise_is_large_not_marginal(self) -> None:
        """"显著"取一个可判定的下界：均值至少翻倍。

        这条断言会在机制失效时红。翻倍而不是 1.001 倍，是因为默认阈值 0.5
        几乎切在门控值的正中间，随机初始化下大约一半的种子门恒闭。
        """

        results = {s: _train_then_measure(s) for s in self.SEEDS}
        before = sum(r.before for r in results.values()) / len(results)
        after = sum(r.after for r in results.values()) / len(results)
        assert after >= 2 * before, f"提升不够显著: {before:.3f} -> {after:.3f}"

    def test_seeds_that_already_work_stay_silent(self) -> None:
        """门本来就能开的种子**不提案**。

        这条是"规则不是每次都改"的直接检验。若它红，说明规则恒真——
        那么上面的提升可能只是乱改撞对了。
        """

        results = {s: _train_then_measure(s) for s in self.SEEDS}
        working = {s: r for s, r in results.items() if r.before >= 0.9}
        assert working, "没有任何种子本来就能开门——样本失去对照意义"
        for seed, run in working.items():
            assert run.proposals == 0, f"seed {seed} 本来正常却被提案 {run.proposals} 次"

    def test_seeds_that_do_not_work_get_exactly_one_step(self) -> None:
        """门闭着的种子提一次提案，且只提一次（见 TestConvergesOnce）。"""

        results = {s: _train_then_measure(s) for s in self.SEEDS}
        broken = {s: r for s, r in results.items() if r.before < 0.9}
        assert broken, "没有种子本来门是闭的——样本失去对照意义"
        for seed, run in broken.items():
            assert run.proposals >= 1, f"seed {seed} 门闭着却没有提案"
            assert run.threshold is not None and run.threshold < 0.5, (
                f"seed {seed} 的阈值没有被降低: {run.threshold}"
            )

    def test_the_committed_value_is_actually_installed(self) -> None:
        """审计记录 applied 之后，新快照里必须看得见那个值。

        "提交成功"与"行为改变"之间隔着 WAKE 换版；这条断言盯的就是那一环。
        """

        results = {s: _train_then_measure(s) for s in self.SEEDS}
        changed = [r for r in results.values() if r.proposals]
        assert changed, "没有任何种子走完提案路径"
        for run in changed:
            assert run.threshold == pytest.approx(0.4)  # 0.5 - max_step


class TestThresholdIsObservable:
    """阈值改动必须**看得见**——否则 Δθ 提了也白提。"""

    def test_lowering_the_threshold_opens_the_gate(self) -> None:
        """同一个 hidden、同一个门控值：阈值从 0.5 降到刚好低于门控值，门从闭到开。

        这是 ``thresholds`` 那个**没有消费者的类别**的回归钉子：在
        ActionDecoder 接上 ``gate_thresholds`` 之前，改结构里的阈值对行为
        **没有任何影响**，而提案、Gate、Store 一路都是绿的。

        历史注：这个洞当年被记成「``get_threshold()`` 没有消费者」，两处
        差一层——补上的消费者读的是**整个映射**，那个访问器一次都没被调用过，
        已于 2026-09-28 删除。**类别活着不等于名字对应的接口活着。**
        """

        from SSEA.action_decoder import ActionDecoder, DecodeCandidates

        torch.manual_seed(0)
        decoder = ActionDecoder()
        intent = torch.randn(decoder.config.intent_dim)
        # 门控层吃的是 trunk 出来的 h，不是 intent 本身。
        h = decoder.trunk(
            torch.cat([intent, torch.zeros(decoder.config.drive_dim)])
        )
        gate_value = float(torch.sigmoid(decoder.gates["memory"](h)))

        def decode(thresholds: dict | None) -> object:
            return decoder(
                intent,
                _constraints(),
                _drive(),
                DecodeCandidates(object_ids=(), skill_ids=(), proposal_types=()),
                thresholds,
            )

        closed = decode({MEMORY_KEY: min(1.0, gate_value + 0.01)})
        opened = decode({MEMORY_KEY: max(0.0, gate_value - 0.01)})
        assert closed.memory is None
        assert opened.memory is not None

    def test_absent_key_falls_back_to_the_config_value(self) -> None:
        """结构没给这个键时退回配置值——不是崩，也不是恒开。"""

        from SSEA.action_decoder import ActionDecoder, DecodeCandidates

        torch.manual_seed(0)
        decoder = ActionDecoder()
        intent = torch.randn(decoder.config.intent_dim)

        def decode(thresholds: dict | None) -> object:
            return decoder(
                intent, _constraints(), _drive(), DecodeCandidates(), thresholds
            )

        fallback = {MEMORY_KEY: decoder.config.gate_threshold}
        assert decode(None).memory == decode({}).memory == decode(fallback).memory


def _constraints() -> object:
    from SSEA.sse_protocols import default_constraints

    return default_constraints()


def _drive() -> torch.Tensor:
    return torch.zeros(4)
