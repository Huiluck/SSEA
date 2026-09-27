"""Skill Runner 测试 —— 逐帧展开 + 三条中止条件（08 §2.3）。"""

from __future__ import annotations

import pytest

from SSEA.skill_runner import (
    ABORT_ENERGY,
    ABORT_ENV,
    ABORT_PRECONDITION,
    SkillRunner,
    SkillRun,
    SkillStats,
)
from SSEA.sse_protocols import (
    Action,
    BodyState,
    EnvironmentSummary,
    Locomotion,
    Observation,
    Skill,
    SkillCall,
    default_constraints,
)
from tests.conftest import make_context


def body(energy: float = 1.0) -> BodyState:
    return BodyState(
        energy=energy,
        damage=0.0,
        fatigue=0.0,
        position=(0.0, 0.0),
        orientation=(1.0, 0.0),
        action_constraints=default_constraints(),
        internal_state=(),
    )


def observation(time: float = 1.0, energy: float = 1.0) -> Observation:
    return Observation(
        time=time,
        body=body(energy),
        environment=EnvironmentSummary(
            light_level=1.0,
            temperature=0.5,
            danger_level=0.0,
            resource_density=0.0,
            time_phase="day",
        ),
        objects=(),
        events=(),
        social_signals=(),
    )


def sub(speed: float = 0.5) -> Action:
    return Action(locomotion=Locomotion((1.0, 0.0), speed, 1.0))


def call(skill_id: str) -> Action:
    return Action(skill=SkillCall(skill_id=skill_id, params={}))


def skill(
    skill_id: str = "s1",
    n_steps: int = 3,
    *,
    precondition: dict | None = None,
    energy_cost: float = 0.0,
) -> Skill:
    return Skill(
        skill_id=skill_id,
        name=f"技能 {skill_id}",
        precondition=precondition if precondition is not None else {},
        action_sequence=tuple(sub() for _ in range(n_steps)),
        expected_outcome={},
        success_count=0,
        failure_count=0,
        energy_cost=energy_cost,
        created_from="test",
        last_used=0.0,
    )


def drive(
    runner: SkillRunner, skill_id: str, frames: int, *, success: bool = True
) -> list[str | None]:
    """按帧驱动 submit → current_action → report，收集事件。"""

    events: list[str | None] = []
    for t in range(1, frames + 1):
        runner.submit(call(skill_id), body(), observation(time=float(t)))
        executed = runner.current_action(sub())
        assert executed.is_executable()
        events.append(
            runner.report(success, body(), observation(time=float(t)))
        )
    return events


class TestSequentialExecution:
    """核心承诺：每帧吐一个子动作，序列按序推进。"""

    def test_first_frame_returns_first_subaction(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        assert runner.running_skill_id == "s1"
        assert runner.current_action(sub()) is not None

    def test_subactions_come_out_in_order(self) -> None:
        ctx = make_context(s1=skill())
        # 快照是深拷贝——比身份要比快照里那份，不是本地这份
        expected = ctx.skills["s1"].action_sequence
        runner = SkillRunner(ctx)
        taken: list[int] = []
        for t in range(1, 4):
            runner.submit(call("s1"), body(), observation(time=float(t)))
            taken.append(id(runner.current_action(sub())))
            runner.report(True, body(), observation(time=float(t)))
        # 三个不同身份 = 序列里的三个不同子动作，且顺序与 action_sequence 一致
        assert taken == [id(a) for a in expected]

    def test_cursor_advances_once_per_frame(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        assert runner._run is not None
        assert runner._run.cursor == 0
        runner.report(True, body(), observation())
        assert runner._run is not None and runner._run.cursor == 1
        runner.report(True, body(), observation())
        assert runner._run is not None and runner._run.cursor == 2

    def test_completion_emits_skill_success(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        events = drive(runner, "s1", 3)
        assert events == [None, None, "SKILL_SUCCESS"]

    def test_run_is_cleared_after_completion(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        drive(runner, "s1", 3)
        assert runner.running_skill_id is None

    def test_no_skill_means_fallback_passthrough(self) -> None:
        """没有技能在执行时，Action Decoder 的原产物必须原样通过。"""

        runner = SkillRunner(make_context(s1=skill()))
        fallback = sub(speed=0.9)
        runner.submit(fallback, body(), observation())
        assert runner.current_action(fallback) is fallback

    def test_repeated_calls_do_not_restart(self) -> None:
        """每帧都带同一个 skill_id 不应把游标重置回 0。

        用 5 步技能跑 3 帧——跑满 3 步的话技能已完成，测的是另一件事。
        """

        runner = SkillRunner(make_context(s1=skill(n_steps=5)))
        for t in range(1, 4):
            runner.submit(call("s1"), body(), observation(time=float(t)))
            runner.report(True, body(), observation(time=float(t)))
        assert runner._run is not None
        assert runner._run.frames_done == 3
        assert runner._run.cursor == 3

    def test_switching_skill_restarts(self) -> None:
        runner = SkillRunner(make_context(s1=skill(), s2=skill(skill_id="s2")))
        runner.submit(call("s1"), body(), observation())
        runner.report(True, body(), observation())
        runner.submit(call("s2"), body(), observation())
        assert runner.running_skill_id == "s2"
        assert runner._run is not None
        assert runner._run.cursor == 0

    def test_single_step_skill_completes_in_one_frame(self) -> None:
        runner = SkillRunner(make_context(s1=skill(n_steps=1)))
        assert drive(runner, "s1", 1) == ["SKILL_SUCCESS"]


class TestMissingSkill:
    def test_unknown_skill_falls_back(self) -> None:
        """技能库可能刚被 DISABLE_SKILL 改过，而快环快照是旧的——
        这时必须退回普通动作路径，而不是崩。"""

        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("ghost"), body(), observation())
        assert runner.running_skill_id is None
        fallback = sub(speed=0.3)
        assert runner.current_action(fallback) is fallback

    def test_unknown_skill_emits_no_event(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("ghost"), body(), observation())
        assert runner.report(True, body(), observation()) is None

    def test_empty_skill_id_is_not_a_call(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(
            Action(skill=SkillCall(skill_id="", params={})), body(), observation()
        )
        assert runner.running_skill_id is None


class TestPreconditionAbort:
    """中止条件 1：前置条件不再满足。"""

    def test_aborts_when_precondition_fails(self) -> None:
        runner = SkillRunner(
            make_context(s1=skill(precondition={"min_energy": 0.5}))
        )
        runner.submit(call("s1"), body(energy=1.0), observation())
        event = runner.report(True, body(energy=0.2), observation())
        assert event == "SKILL_FAILURE"
        assert runner.running_skill_id is None

    def test_holds_when_precondition_met(self) -> None:
        runner = SkillRunner(
            make_context(s1=skill(precondition={"min_energy": 0.5}))
        )
        runner.submit(call("s1"), body(energy=0.9), observation())
        assert runner.report(True, body(energy=0.9), observation()) is None

    def test_unknown_precondition_keys_are_ignored(self) -> None:
        """precondition 是自由 dict；只支持 min_energy，未知键不能当作失败。"""

        runner = SkillRunner(
            make_context(s1=skill(precondition={"near_fire": True}))
        )
        runner.submit(call("s1"), body(), observation())
        assert runner.report(True, body(), observation()) is None

    def test_boundary_is_inclusive(self) -> None:
        runner = SkillRunner(
            make_context(s1=skill(precondition={"min_energy": 0.5}))
        )
        runner.submit(call("s1"), body(energy=0.5), observation())
        assert runner.report(True, body(energy=0.5), observation()) is None

    def test_failure_is_counted(self) -> None:
        runner = SkillRunner(
            make_context(s1=skill(precondition={"min_energy": 0.5}))
        )
        runner.submit(call("s1"), body(energy=1.0), observation())
        runner.report(True, body(energy=0.2), observation())
        assert runner.stats_for("s1").failure_count == 1


class TestEnergyAbort:
    """中止条件 2：能量不足以支撑剩余成本。"""

    def test_aborts_when_energy_runs_out(self) -> None:
        runner = SkillRunner(make_context(s1=skill(energy_cost=0.5)))
        runner.submit(call("s1"), body(energy=1.0), observation())
        event = runner.report(True, body(energy=0.4), observation())
        assert event == "SKILL_FAILURE"

    def test_zero_cost_skill_never_aborts_on_energy(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        events = drive(runner, "s1", 3)
        assert "SKILL_FAILURE" not in events

    def test_remaining_cost_shrinks_as_skill_progresses(self) -> None:
        """第 3 帧已无可付，需求为 0——不能按全序列预算扣，也不能把
        本帧（已付过）再算一遍。"""

        runner = SkillRunner(
            make_context(s1=skill(n_steps=3, energy_cost=0.1))
        )
        event = None
        for t in (1, 2, 3):
            runner.submit(call("s1"), body(energy=0.25), observation(time=float(t)))
            event = runner.report(True, body(energy=0.25), observation(time=float(t)))
        # 0.25 ≥ 0.1 × 2（第 1 帧时还有 2 帧未付）→ 全程不中止，正常完成
        assert event == "SKILL_SUCCESS"
        assert runner.stats_for("s1").success_count == 1
        assert runner.stats_for("s1").failure_count == 0

    def test_already_paid_frame_is_not_double_charged(self) -> None:
        """直接钉住那个 off-by-one：0.25 能量跑 3 步 × 0.1 的技能。
        按全序列预算（0.3）会在第一帧就中止；正确行为是跑完。"""

        runner = SkillRunner(
            make_context(s1=skill(n_steps=3, energy_cost=0.1))
        )
        events = drive(runner, "s1", 3)
        assert "SKILL_FAILURE" not in events
        assert events[-1] == "SKILL_SUCCESS"

    def test_aborts_when_only_first_frame_is_affordable(self) -> None:
        """3 步 × 0.3：第 1 帧需预付后 2 帧（0.6），第 2 帧只需后 1 帧（0.3）。
        能量 0.65 → 0.2 正好落在"第 1 帧过、第 2 帧中止"的区间。"""

        runner = SkillRunner(
            make_context(s1=skill(n_steps=3, energy_cost=0.3))
        )
        runner.submit(call("s1"), body(energy=0.65), observation())
        assert runner.report(True, body(energy=0.65), observation()) is None
        event = runner.report(True, body(energy=0.2), observation())
        assert event == "SKILL_FAILURE"


class TestEnvironmentAbort:
    """中止条件 3：环境判定子动作非法。"""

    def test_aborts_when_environment_rejects(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        event = runner.report(False, body(), observation())
        assert event == "SKILL_FAILURE"
        assert runner.running_skill_id is None

    def test_failure_is_counted(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        runner.report(False, body(), observation())
        assert runner.stats_for("s1").failure_count == 1

    def test_voluntary_abandon_counts_as_failure(self) -> None:
        """模型主动换动作 = 放弃技能，记为失败——不是静默丢弃。"""

        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        runner.report(True, body(), observation())
        runner.submit(sub(), body(), observation())
        assert runner.running_skill_id is None
        assert runner.stats_for("s1").failure_count == 1


class TestStats:
    def test_success_and_failure_are_separate(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        drive(runner, "s1", 3)
        runner.submit(call("s1"), body(), observation())
        runner.report(False, body(), observation())
        stats = runner.stats_for("s1")
        assert stats.success_count == 1
        assert stats.failure_count == 1

    def test_executed_frames_counts_only_completed_frames(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation())
        runner.report(True, body(), observation())
        runner.report(True, body(), observation())
        assert runner.stats_for("s1").executed_frames == 2

    def test_last_used_tracks_time(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        runner.submit(call("s1"), body(), observation(time=7.0))
        runner.report(True, body(), observation(time=7.0))
        assert runner.stats_for("s1").last_used == 7.0

    def test_stats_are_per_skill(self) -> None:
        runner = SkillRunner(make_context(s1=skill(), s2=skill(skill_id="s2")))
        drive(runner, "s1", 3)
        assert runner.stats_for("s2").success_count == 0

    def test_stats_default_is_zeroed(self) -> None:
        stats = SkillStats()
        assert stats.success_count == 0
        assert stats.failure_count == 0
        assert stats.executed_frames == 0
        assert stats.last_used == 0.0


class TestUpdatedSkill:
    """Runner 改不了快照里的 Skill，只能产出副本供慢环提案。"""

    def test_original_skill_is_untouched(self) -> None:
        ctx = make_context(s1=skill())
        original = ctx.skills["s1"]
        runner = SkillRunner(ctx)
        drive(runner, "s1", 3)
        assert ctx.skills["s1"] is original
        assert original.success_count == 0

    def test_copy_carries_new_stats(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        drive(runner, "s1", 3)
        updated = runner.updated_skill("s1")
        assert updated is not None
        assert updated.success_count == 1
        assert updated.metadata["executed_frames"] == 3

    def test_copy_keeps_protocol_fields(self) -> None:
        ctx = make_context(s1=skill())
        original = ctx.skills["s1"]
        runner = SkillRunner(ctx)
        drive(runner, "s1", 3)
        updated = runner.updated_skill("s1")
        assert updated is not None
        assert updated.action_sequence == original.action_sequence
        assert updated.precondition == original.precondition
        assert updated.energy_cost == original.energy_cost

    def test_unknown_skill_returns_none(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        assert runner.updated_skill("ghost") is None


class TestConsolidation:
    """08 §3.4：本能内化的两条判据都由 Runner 的统计喂饱。"""

    def test_not_consolidatable_when_unused(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        assert runner.consolidatable_skills() == ()

    def test_below_frame_threshold_is_not_consolidatable(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        for _ in range(3):
            drive(runner, "s1", 3)
        # 3 次成功 × 3 帧 = 9 帧，仍低于默认的 30 帧
        assert runner.consolidatable_skills() == ()

    def test_consolidatable_with_relaxed_frame_threshold(self) -> None:
        runner = SkillRunner(make_context(s1=skill()))
        for _ in range(3):
            drive(runner, "s1", 3)
        assert runner.consolidatable_skills(
            min_success_count=3, min_executed_frames=9
        ) == ("s1",)

    def test_success_count_alone_is_not_enough(self) -> None:
        """帧数判据是独立的——只成功不够，还得真被跑过。"""

        runner = SkillRunner(make_context(s1=skill()))
        for _ in range(5):
            drive(runner, "s1", 3)
        assert runner.stats_for("s1").success_count == 5
        assert runner.consolidatable_skills() == ()


class TestSkillRun:
    def test_is_finished_at_end_of_sequence(self) -> None:
        run = SkillRun(skill=skill(n_steps=2))
        assert not run.is_finished
        run.cursor = 2
        assert run.is_finished

    def test_is_finished_at_zero_length_sequence(self) -> None:
        """空序列的技能不允许存在（Skill.__post_init__），但 SkillRun 自身
        的判据不该因越界游标而崩溃。"""

        run = SkillRun(skill=skill(n_steps=1))
        run.cursor = 99
        assert run.is_finished


class TestAbortReasonsAreDistinct:
    """三条中止条件必须可区分——慢环的 RuleCompiler 要靠原因归因。"""

    def test_three_distinct_constants(self) -> None:
        assert len({ABORT_PRECONDITION, ABORT_ENERGY, ABORT_ENV}) == 3

    def test_reasons_are_stable_strings(self) -> None:
        for reason in (ABORT_PRECONDITION, ABORT_ENERGY, ABORT_ENV):
            assert isinstance(reason, str)
            assert reason
