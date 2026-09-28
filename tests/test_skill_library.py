"""Skill Library 测试 —— 07 §6.5 + 08 §2.1 / §2.3 / §3.4。

四条验收里「模型可以保存技能」由本文件钉住（「模型可以调用技能」是
Milestone 2 的 Skill Runner，见 test_fast_loop.py::TestSkillIntegration）。

本文件重点覆盖三件事：

1. **编译判据**：只从"模型自己做对了"的连续轨迹里切，技能执行中的子动作
   不参与（抄一条已有技能的动作序列得到一条新技能，是复制不是学习）；
2. **无直接改技能的路径**：一切写入走提案 → Gate → Store → 新快照。
   Gate 不通过则版本号不切换，旧快照继续有效——不存在"回滚"操作；
3. **编译产物真的能跑**：保存后的新快照交给快环，技能能被调用并展开成子动作。
"""

from __future__ import annotations

import pytest
import torch

from SSEA.environment import Environment
from SSEA.fast_loop import STATE_RUN, STATE_SLEEP, STATE_WAKE, FastLoop, FastLoopConfig
from SSEA.skill_library import (
    SOURCE_COMPILED,
    SOURCE_INHERITED,
    SkillLibrary,
    SkillLibraryConfig,
)
from SSEA.sse_protocols import (
    Action,
    Feedback,
    GateResult,
    Locomotion,
    Skill,
    StructureStore,
)
from tests.conftest import make_context


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def move(speed: float = 0.5) -> Action:
    """一个朝 +x 移动的动作。``speed`` 进签名，改它就换一条技能。"""

    return Action(locomotion=Locomotion((1.0, 0.0), speed, 1.0))


def fb(
    energy: float = 0.0,
    damage: float = 0.0,
    success: bool = True,
    survived: bool = True,
) -> Feedback:
    return Feedback(
        energy_change=energy,
        damage_change=damage,
        fatigue_change=0.0,
        prediction_error=0.0,
        action_success=success,
        survived=survived,
    )


def record(
    *,
    frame: int = 0,
    action: Action | None = None,
    energy: float = 0.1,
    state: str = STATE_RUN,
    body_energy: float = 1.0,
    success: bool = True,
    survived: bool = True,
    damage: float = 0.0,
):
    """一条最小 StepRecord。

    ``executed_action is decoded_action`` 表示"执行的就是解码出来的那个"；
    技能执行中的子动作两者不是同一个对象（见 ``sub_action_record``）。
    """

    from SSEA.fast_loop import StepRecord

    decoded = action if action is not None else move()
    return StepRecord(
        frame=frame,
        state=state,
        observation=_obs(body_energy),
        feedback=fb(energy, damage=damage, success=success, survived=survived),
        decoded_action=decoded,
        executed_action=decoded,
        skill_event=None,
        context_fingerprint=(),
        intent=None,
    )


def sub_action_record(frame: int = 0, energy: float = 0.1) -> object:
    """一条技能执行中的帧：executed 与 decoded 不是同一个对象。"""

    from SSEA.fast_loop import StepRecord

    decoded = Action(
        skill=None,
        locomotion=Locomotion((1.0, 0.0), 0.5, 1.0),
    )
    return StepRecord(
        frame=frame,
        state=STATE_RUN,
        observation=_obs(1.0),
        feedback=fb(energy),
        decoded_action=decoded,
        executed_action=move(1.0),
        skill_event="SKILL_RUNNING",
        context_fingerprint=(),
        intent=None,
    )


def _obs(energy: float):
    from SSEA.sse_protocols import (
        ActionConstraints,
        BodyState,
        EnvironmentSummary,
        Observation,
        default_constraints,
    )

    return Observation(
        time=0.0,
        body=BodyState(
            energy=energy,
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


def successful_run(n: int, *, energy: float = 0.2) -> tuple:
    """一段连续成功的 RUN 轨迹。"""

    return tuple(record(frame=i, energy=energy) for i in range(n))


def consistent_run(before, changes) -> tuple:
    """一段**物理自洽**的轨迹：``before`` 是各帧动作前能量，``changes`` 是各帧增量。

    动作后能量由 ``before[i] + changes[i]`` 算出，不由调用方各写一个数。
    这是债务 26 的夹具纪律：旧夹具把 ``body_energy`` 写成恒定常数、而
    ``energy_change`` 每帧不为零，两者**互相矛盾**，于是「动作前 / 动作后」
    与「首帧 / 末帧」在那份夹具上不可区分——测试守不住它名字所指的东西。
    """

    return tuple(
        record(frame=i, body_energy=round(b + c, 6), energy=c)
        for i, (b, c) in enumerate(zip(before, changes))
    )


PASS = GateResult(passed=True)
FAIL = GateResult(passed=False, reason="回归未过", stage_failed="regression")


def lib(**cfg: object) -> SkillLibrary:
    return SkillLibrary(config=SkillLibraryConfig(**cfg))  # type: ignore[arg-type]


# ----------------------------------------------------------------------
#  编译判据
# ----------------------------------------------------------------------


class TestCompilationCriteria:
    """编译只从"模型自己做对了"的轨迹里切。"""

    def test_successful_run_yields_a_skill(self) -> None:
        out = lib().compile_from_trace(successful_run(5))
        assert len(out) == 1
        assert out[0].total_frames() == 5

    def test_short_run_is_not_worth_compressing(self) -> None:
        assert lib(min_frames=3).compile_from_trace(successful_run(2)) == ()

    def test_net_energy_loss_is_not_compiled(self) -> None:
        """没有净收益的行为不是成功行为——能量是唯一的世界计价物。"""

        assert lib().compile_from_trace(successful_run(5, energy=-0.1)) == ()

    def test_failed_action_is_not_compiled(self) -> None:
        trace = tuple(record(frame=i, success=False) for i in range(5))
        assert lib().compile_from_trace(trace) == ()

    def test_terminal_frame_ends_the_run(self) -> None:
        """终帧之后没有未来——不该被固化。"""

        trace = tuple(record(frame=i, survived=(i < 3)) for i in range(5))
        out = lib().compile_from_trace(trace)
        assert all(s.total_frames() <= 3 for s in out)

    def test_sleep_and_wake_frames_are_skipped(self) -> None:
        """那两帧没有动作，整理它们没有意义。"""

        trace = (
            record(frame=0),
            record(frame=1),
            record(frame=2),
            record(frame=3, state=STATE_SLEEP),
            record(frame=4, state=STATE_WAKE),
            record(frame=5),
            record(frame=6),
            record(frame=7),
        )
        out = lib().compile_from_trace(trace)
        assert len(out) == 2
        assert all(s.total_frames() == 3 for s in out), "睡眠 / 唤醒帧被算进了动作序列"

    def test_skill_sub_actions_are_not_compiled(self) -> None:
        """抄一条已有技能的动作序列得到一条新技能，是复制不是学习。"""

        trace = tuple(sub_action_record(frame=i) for i in range(5))
        assert lib().compile_from_trace(trace) == ()

    def test_mixed_trace_compiles_only_the_direct_success_runs(self) -> None:
        trace = (
            record(frame=0),
            record(frame=1),
            record(frame=2),
            sub_action_record(frame=3),
            record(frame=4),
            record(frame=5),
            record(frame=6),
        )
        out = lib().compile_from_trace(trace)
        assert len(out) == 2
        assert all(s.total_frames() == 3 for s in out)

    def test_long_run_is_windowed_not_rejected(self) -> None:
        """整段拒绝会让"活了很久且一直成功"的轨迹产出零条技能——
        那正好是最该被固化的一类。"""

        out = lib(max_frames=4).compile_from_trace(successful_run(10))
        assert len(out) == 2
        assert all(s.total_frames() == 4 for s in out)

    def test_window_remainder_below_min_is_dropped(self) -> None:
        out = lib(max_frames=4, min_frames=3).compile_from_trace(successful_run(6))
        assert len(out) == 1
        assert out[0].total_frames() == 4

    def test_zero_energy_run_is_not_compiled(self) -> None:
        """净收益必须严格为正——持平没有压缩价值。"""

        assert lib().compile_from_trace(successful_run(5, energy=0.0)) == ()


# ----------------------------------------------------------------------
#  编译产物
# ----------------------------------------------------------------------


class TestCompiledSkillFields:
    """技能字段：前置条件、每帧能量成本、来源标记。"""

    def test_precondition_records_starting_energy(self) -> None:
        """``min_energy`` 是首帧**动作前**的能量——option 的 initiation state。

        债务 26（2026-09-28 修）：旧版本取的是 ``observation.body.energy``，
        而 ``StepRecord.observation`` 是**动作后**的状态，于是判据变成
        「复现这条技能自己刚制造出来的峰值」。旧夹具把 ``body_energy`` 写成
        恒定常数、``energy_change`` 却每帧 +0.1，两者互相矛盾，所以它同时
        放过了「取动作后」与「取末帧」两个变异——名字对，守不住。
        """

        # 动作前能量 0.30 → 0.50 → 0.60；增量 +0.20 / +0.10 / -0.05（净 +0.25）
        trace = consistent_run((0.30, 0.50, 0.60), (0.20, 0.10, -0.05))
        out = lib().compile_from_trace(trace)

        assert len(out) == 1
        assert out[0].precondition == {"min_energy": pytest.approx(0.30)}
        # 不是首帧动作后（0.50），也不是末帧动作前（0.60）——两个变异各有断言守着，
        # 见下面两条。

    def test_precondition_is_not_the_post_action_energy(self) -> None:
        """点名债务 26 的那个具体错法：读 ``observation.body.energy``（动作后）。

        这条断言的存在理由只有一个：让「改回动作后能量」这个变异**有名字地红**。
        旧夹具做不到这件事（见上一条的 docstring），这正是它被记成假守卫的原因。
        """

        trace = consistent_run((0.30, 0.50, 0.60), (0.20, 0.10, -0.05))
        out = lib().compile_from_trace(trace)
        first = trace[0]

        assert out[0].precondition["min_energy"] != pytest.approx(
            first.observation.body.energy, abs=1e-9
        ), "min_energy 取的是动作后能量——债务 26 复发"
        assert out[0].precondition["min_energy"] == pytest.approx(
            first.observation.body.energy - first.feedback.energy_change
        )

    def test_precondition_comes_from_the_first_frame_not_the_last(self) -> None:
        """第二个变异：从末帧取能量。旧夹具里三帧 ``body_energy`` 全等，它看不见。"""

        trace = consistent_run((0.30, 0.50, 0.60), (0.20, 0.10, -0.05))
        out = lib().compile_from_trace(trace)
        last = trace[-1]

        assert out[0].precondition["min_energy"] == pytest.approx(0.30)
        assert out[0].precondition["min_energy"] != pytest.approx(
            last.observation.body.energy - last.feedback.energy_change
        ), "min_energy 取的不是首帧——initiation state 取错了位置"

    def test_action_sequence_is_the_executed_actions(self) -> None:
        trace = tuple(
            record(frame=i, action=move(0.1 * i)) for i in range(3)
        )
        out = lib().compile_from_trace(trace)
        assert [a.locomotion.speed for a in out[0].action_sequence] == [
            pytest.approx(0.0),
            pytest.approx(0.1),
            pytest.approx(0.2),
        ]

    def test_expected_outcome_records_net_energy(self) -> None:
        out = lib().compile_from_trace(successful_run(4, energy=0.2))
        assert out[0].expected_outcome["energy_change"] == pytest.approx(0.8)
        assert out[0].expected_outcome["frames"] == 4
        assert out[0].expected_outcome["outcome"] == "energy_gain"

    def test_outcome_marker_damaged(self) -> None:
        """标记取段末那一帧——它代表这段行为收场时的状态。"""

        trace = (
            record(frame=0, energy=0.3),
            record(frame=1, energy=0.3),
            record(frame=2, energy=0.3, damage=0.1),
        )
        out = lib().compile_from_trace(trace)
        assert out[0].expected_outcome["outcome"] == "damaged"

    def test_energy_cost_is_the_gross_per_frame_loss(self) -> None:
        """Skill Runner 的中止判据按"剩余帧数 × 每帧成本"算——
        要的是这条技能每帧烧多少，不是这段轨迹净赚多少。

        刻意不用净消耗：净收益为正的段会被钳成 0，于是每条编译出来的
        技能 energy_cost 恒为 0，那是个死字段。
        """

        out = lib().compile_from_trace(successful_run(4, energy=-0.1))
        # 每帧亏 0.1、共 4 帧 → 毛成本 0.1（净收益为负，编译不出来）
        assert out == ()

        mixed = lib().compile_from_trace(
            (
                record(frame=0, energy=-0.4),
                record(frame=1, energy=0.5),
                record(frame=2, energy=-0.2),
                record(frame=3, energy=0.5),
            )
        )
        assert len(mixed) == 1
        assert mixed[0].expected_outcome["energy_change"] == pytest.approx(0.4)
        assert mixed[0].energy_cost == pytest.approx(0.15), "应为 (0.4 + 0.2) / 4"

    def test_energy_cost_is_zero_when_no_frame_lost_energy(self) -> None:
        """帧帧都赚时每帧成本是 0，不能是负数。"""

        out = lib().compile_from_trace(successful_run(3, energy=0.5))
        assert out[0].energy_cost == 0.0

    def test_created_from_marks_the_compiler(self) -> None:
        out = lib().compile_from_trace(successful_run(3))
        assert out[0].created_from == SOURCE_COMPILED

    def test_counts_start_at_zero(self) -> None:
        """从未作为技能被调用过。行为发生过，但那是轨迹，不是这次调用。"""

        out = lib().compile_from_trace(successful_run(3))
        assert out[0].success_count == 0
        assert out[0].failure_count == 0
        assert out[0].last_used == 0.0

    def test_signature_is_deterministic(self) -> None:
        a = lib().compile_from_trace(successful_run(4))
        b = lib().compile_from_trace(successful_run(4))
        assert a[0].skill_id == b[0].skill_id

    def test_different_sequence_gives_different_id(self) -> None:
        a = lib().compile_from_trace(successful_run(3, energy=0.2))
        b = lib().compile_from_trace(
            tuple(record(frame=i, action=move(2.0), energy=0.2) for i in range(3))
        )
        assert a[0].skill_id != b[0].skill_id
        assert a[0].skill_id != b[0].skill_id, "同序列必须同名，异序列必须异名"

    def test_different_precondition_gives_different_id(self) -> None:
        """前置条件是技能身份的一部分——同样的动作在不同能量下不是同一条。"""

        a = lib().compile_from_trace(
            tuple(record(frame=i, body_energy=1.0) for i in range(3))
        )
        b = lib().compile_from_trace(
            tuple(record(frame=i, body_energy=0.5) for i in range(3))
        )
        assert a[0].skill_id != b[0].skill_id

    def test_id_is_stable_against_float_noise(self) -> None:
        """末位抖动不能让同一段行为签出两个名——否则"是否已存在"不可判定。"""

        base = lib().compile_from_trace(successful_run(4))
        noisy = lib().compile_from_trace(
            tuple(
                record(frame=i, body_energy=1.0 + 1e-9, energy=0.2 + 1e-9)
                for i in range(4)
            )
        )
        assert base[0].skill_id == noisy[0].skill_id


# ----------------------------------------------------------------------
#  initiation state 的还原式（跨模块恒等式）
# ----------------------------------------------------------------------


class TestPreActionEnergyIsTheDecisionState:
    """``_pre_action_energy`` 的还原式是一条**跨模块恒等式**，这里是它的钉子。

    它声称 ``observation.body.energy - feedback.energy_change`` 等于这一帧
    **动作前**的能量，即模型做这次决策时看到的那份观测里的能量。技能库把这个数
    写进 option 的 initiation set（债务 26），所以恒等式一旦不成立，编出来的
    ``precondition`` 就是另一个数——**而不会有任何东西报错**。

    这条恒等式两端分属两个模块：环境定义 ``energy_change = post - energy_before``，
    快环把 ``observation`` 记在动作**之后**。合流点就是下面这条断言。

    为什么不用 ``skill_library._pre_action_energy`` 自证：拿被测函数算期望值，
    它写错时两边一起错，断言照绿。所以这里用的是**独立的**算术。
    """

    def _trace(self, frames: int = 40) -> list:
        loop = FastLoop(
            Environment(seed=7),
            make_context(),
            config=FastLoopConfig(max_frames=frames, min_sleep_frames=3),
        )
        self.initial_energy = loop.observation.body.energy
        loop.run(frames)
        return list(loop.trace())

    def test_first_run_frame_is_measured_from_the_reset_observation(self) -> None:
        """第 0 帧没有"上一帧"，它的动作前状态是 ``reset()`` 的那份观测。"""

        trace = self._trace()
        first = trace[0]
        assert first.state == STATE_RUN
        assert first.observation.body.energy == pytest.approx(
            self.initial_energy + first.feedback.energy_change, abs=2e-6
        )

    def test_each_run_frame_is_measured_from_the_previous_state(self) -> None:
        """相邻两帧：本帧动作前能量 = 上一帧动作后能量。

        只比**相邻的 RUN 对**——中间隔着 SLEEP / WAKE 时环境自己动过能量
        （``rest()`` 会恢复），等式不该成立，也不该被拿来当成反例。
        """

        trace = self._trace()
        pairs = 0
        for prev, cur in zip(trace, trace[1:]):
            if prev.state != STATE_RUN or cur.state != STATE_RUN:
                continue
            assert cur.observation.body.energy == pytest.approx(
                prev.observation.body.energy + cur.feedback.energy_change,
                abs=2e-6,
            ), f"第 {cur.frame} 帧：能量账对不上，"\
               "``observation - energy_change`` 不再等于动作前状态"
            pairs += 1
        assert pairs >= 3, "RUN 帧太少，这条断言等于没跑"

    def test_the_identity_is_not_vacuous(self) -> None:
        """恒等式必须真的在区分：至少要有一帧的能量增量不为零。

        若所有帧的 ``energy_change`` 都是 0，那么"动作前 = 动作后"成立得毫无
        信息量，上面两条断言也会变成恒真——**这正是旧夹具的病**。
        """

        trace = self._trace()
        moved = [
            r for r in trace
            if r.state == STATE_RUN and abs(r.feedback.energy_change) > 1e-9
        ]
        assert moved, "整条轨迹能量零变化：还原式没有被检验到"


# ----------------------------------------------------------------------
#  保存 / 提案 / Gate
# ----------------------------------------------------------------------


class TestSave:
    """保存走提案 → Gate → Store，没有直接改技能的路径。"""

    def test_save_returns_an_applied_audit_record(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        rec = l.save(skill, PASS, 1.0)
        assert rec.applied
        assert rec.from_version == 0
        assert rec.to_version == 1
        assert rec.kind == "skills"

    def test_saved_skill_appears_in_the_snapshot(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        assert l.get(skill.skill_id) is not None
        assert len(l) == 1

    def test_duplicate_save_raises(self) -> None:
        """新增与回写统计必须能在审计日志里区分。"""

        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        with pytest.raises(ValueError, match="已在库中"):
            l.save(skill, PASS, 2.0)

    def test_gate_rejection_leaves_the_version_unchanged(self) -> None:
        """失败天然回滚：版本号没切换，快照就没变，不存在回滚操作。"""

        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        rec = l.save(skill, FAIL, 1.0)
        assert not rec.applied
        assert rec.from_version == rec.to_version == 0
        assert len(l) == 0
        assert l.get(skill.skill_id) is None

    def test_rejection_is_not_an_exception(self) -> None:
        """拒绝是正常路径，不是错误路径。"""

        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        assert l.save(skill, FAIL, 1.0).gate_result.startswith("reject:")

    def test_rejected_commit_does_not_refresh_the_snapshot(self) -> None:
        l = lib()
        before = l.context
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, FAIL, 1.0)
        assert l.context is before

    def test_snapshot_is_immutable_after_save(self) -> None:
        """已交出的快照不随后续 commit 变化——快环零改动的前提。"""

        l = lib()
        before = l.context
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        assert before.skills == {}
        assert l.context.skills != {}

    def test_version_increments_per_save(self) -> None:
        l = lib()
        for i, speed in enumerate((1.0, 2.0, 3.0)):
            skill = l.compile_from_trace(
                tuple(
                    record(frame=j, action=move(speed), energy=0.2)
                    for j in range(3)
                )
            )[0]
            l.save(skill, PASS, float(i))
        assert l.store.versions["skills"] == 3

    def test_audit_log_records_every_attempt(self) -> None:
        """通过与被拒都留痕——审计日志要能还原"提过什么"。"""

        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        other = l.compile_from_trace(
            tuple(record(frame=j, action=move(7.0)) for j in range(3))
        )[0]
        l.save(other, FAIL, 2.0)
        log = l.store.audit_log()
        assert len(log) == 2
        assert [r.applied for r in log] == [True, False]

    def test_compile_and_save_end_to_end(self) -> None:
        l = lib()
        trace = successful_run(5)
        recs = l.compile_and_save(trace, PASS, 1.0)
        assert len(recs) == 1
        assert recs[0].applied
        assert len(l) == 1

    def test_compile_and_save_dedups(self) -> None:
        """同一段轨迹保存两次只入库一次。"""

        l = lib()
        trace = successful_run(5)
        l.compile_and_save(trace, PASS, 1.0)
        second = l.compile_and_save(trace, PASS, 2.0)
        assert second == ()
        assert len(l) == 1

    def test_new_skills_filters_existing(self) -> None:
        l = lib()
        candidates = l.compile_from_trace(successful_run(5))
        assert l.new_skills(candidates) == candidates
        l.save(candidates[0], PASS, 1.0)
        assert l.new_skills(candidates) == ()


# ----------------------------------------------------------------------
#  更新 / 下线 / 淘汰建议
# ----------------------------------------------------------------------


class TestUpdateAndDisable:
    def test_update_writes_back_stats(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        used = Skill(**{**skill.__dict__, "success_count": 4, "failure_count": 1})
        rec = l.update(used, PASS, 2.0)
        assert rec.applied
        assert l.get(skill.skill_id).success_count == 4
        assert l.get(skill.skill_id).failure_count == 1

    def test_update_of_unknown_skill_raises(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        with pytest.raises(ValueError, match="不在库中"):
            l.update(skill, PASS, 1.0)

    def test_disable_removes_from_snapshot(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        rec = l.disable(skill.skill_id, PASS, 2.0)
        assert rec.applied
        assert len(l) == 0

    def test_disable_of_unknown_skill_is_a_no_op_commit(self) -> None:
        """下线不存在的技能不该炸——它可能已被别的路径下线。"""

        l = lib()
        rec = l.disable("nope", PASS, 1.0)
        assert rec.applied
        assert len(l) == 0

    def test_prunable_is_empty_for_unused_skills(self) -> None:
        """没用过的技能不淘汰——没有证据说它坏。"""

        l = lib()
        l.save(lib().compile_from_trace(successful_run(3))[0], PASS, 1.0)
        assert l.prunable() == ()

    def test_prunable_flags_low_success_rate(self) -> None:
        l = lib(min_attempts=3, min_success_rate=0.34)
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        bad = Skill(**{**skill.__dict__, "success_count": 1, "failure_count": 9})
        l.update(bad, PASS, 2.0)
        assert l.prunable() == (skill.skill_id,)

    def test_prunable_keeps_good_skills(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        good = Skill(**{**skill.__dict__, "success_count": 8, "failure_count": 1})
        l.update(good, PASS, 2.0)
        assert l.prunable() == ()

    def test_prunable_ignores_skills_below_min_attempts(self) -> None:
        l = lib(min_attempts=5)
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        bad = Skill(**{**skill.__dict__, "success_count": 0, "failure_count": 2})
        l.update(bad, PASS, 2.0)
        assert l.prunable() == ()

    def test_prunable_advises_but_never_acts(self) -> None:
        """只建议，不执行——下线也要过 Gate。"""

        l = lib(min_attempts=3)
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        bad = Skill(**{**skill.__dict__, "success_count": 0, "failure_count": 9})
        l.update(bad, PASS, 2.0)
        assert l.prunable() == (skill.skill_id,)
        assert len(l) == 1, "prunable() 直接下线了技能"

    def test_prunable_flags_excess_by_worst_rate(self) -> None:
        """超容时按成功率升序补足差额；从未调用的技能不参与——
        没有证据说它坏。"""

        l = lib(max_skills=2)
        good = l.compile_from_trace(successful_run(3, energy=0.9))[0]
        poor = l.compile_from_trace(
            tuple(record(frame=i, action=move(3.0), energy=0.2) for i in range(3))
        )[0]
        unused = l.compile_from_trace(
            tuple(record(frame=i, action=move(5.0), energy=0.2) for i in range(3))
        )[0]
        assert len({good.skill_id, poor.skill_id, unused.skill_id}) == 3
        for skill in (good, poor, unused):
            l.save(skill, PASS, 1.0)
        g = Skill(**{**good.__dict__, "success_count": 5, "failure_count": 0})
        p = Skill(**{**poor.__dict__, "success_count": 0, "failure_count": 5})
        l.update(g, PASS, 3.0)
        l.update(p, PASS, 4.0)
        assert l.prunable() == (poor.skill_id,), "unused 从未被调用，不该进名单"


# ----------------------------------------------------------------------
#  遗传继承
# ----------------------------------------------------------------------


class TestAdopt:
    """07 §6.5 的来源「遗传继承」。"""

    def test_adopt_saves_inherited_skill(self) -> None:
        l = lib()
        parent = lib().compile_from_trace(successful_run(3))[0]
        recs = l.adopt([parent], PASS, 1.0)
        assert len(recs) == 1
        assert recs[0].applied
        assert len(l) == 1

    def test_adopt_marks_the_source(self) -> None:
        l = lib()
        parent = lib().compile_from_trace(successful_run(3))[0]
        l.adopt([parent], PASS, 1.0)
        assert l.get(parent.skill_id).created_from == SOURCE_INHERITED

    def test_adopt_same_id_updates_rather_than_raises(self) -> None:
        """子代继承的是父代的版本，覆盖是继承的语义，不是意外。"""

        l = lib()
        parent = lib().compile_from_trace(successful_run(3))[0]
        l.adopt([parent], PASS, 1.0)
        recs = l.adopt([parent], PASS, 2.0)
        assert len(recs) == 1
        assert recs[0].applied
        assert len(l) == 1
        assert l.store.versions["skills"] == 2

    def test_adopted_skill_is_runnable(self) -> None:
        l = lib()
        parent = lib().compile_from_trace(successful_run(3))[0]
        l.adopt([parent], PASS, 1.0)
        got = l.get(parent.skill_id)
        assert got is not None
        assert got.total_frames() == 3


# ----------------------------------------------------------------------
#  与 Store 的关系
# ----------------------------------------------------------------------


class TestStoreRelationship:
    """权威数据在 Structure Store，本类是可写门面。"""

    def test_sync_picks_up_external_commits(self) -> None:
        """本类不假设自己是唯一写入方。"""

        store = StructureStore()
        l = SkillLibrary(store)
        skill = lib().compile_from_trace(successful_run(3))[0]
        other = SkillLibrary(store)
        other.save(skill, PASS, 1.0)
        assert len(l) == 0
        l.sync()
        assert len(l) == 1

    def test_context_tracks_the_store(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(3))[0]
        l.save(skill, PASS, 1.0)
        assert l.context is l.store.snapshot() or l.context.skills

    def test_two_libraries_sharing_a_store_agree(self) -> None:
        store = StructureStore()
        a, b = SkillLibrary(store), SkillLibrary(store)
        skill = lib().compile_from_trace(successful_run(3))[0]
        a.save(skill, PASS, 1.0)
        b.sync()
        assert b.get(skill.skill_id) is not None


# ----------------------------------------------------------------------
#  端到端：编译 → 保存 → 快环调用
# ----------------------------------------------------------------------


class TestEndToEnd:
    """「模型可以保存技能」的完整路径：轨迹进，新快照出，快环调用它。"""

    def test_compiled_skill_can_be_called_by_the_fast_loop(self) -> None:
        """这是本条验收的落点：保存后的技能必须真的能被跑起来。"""

        skill = lib().compile_from_trace(successful_run(4))[0]
        assert skill.total_frames() >= 3

        env = Environment(seed=5)
        loop = FastLoop(
            env,
            make_context(**{skill.skill_id: skill}),
            config=FastLoopConfig(max_frames=60, min_sleep_frames=3),
        )
        with torch.no_grad():
            loop.decoder.gates["skill"].bias.fill_(20.0)

        records = loop.run(10)
        called = [r for r in records if r.decoded_action.calls_skill()]
        assert called, "技能在快照里却从未被调用"
        assert any(
            r.executed_action is not r.decoded_action for r in called
        ), "技能从未被展开成子动作"

    def test_library_context_plugs_straight_into_a_loop(self) -> None:
        l = lib()
        skill = l.compile_from_trace(successful_run(4))[0]
        l.save(skill, PASS, 1.0)

        env = Environment(seed=5)
        loop = FastLoop(
            env,
            l.context,
            config=FastLoopConfig(max_frames=60, min_sleep_frames=3),
        )
        assert skill.skill_id in loop.context.skills
        assert loop.skill_runner is not None

    def test_compile_from_a_real_loop_trace(self) -> None:
        """从真的跑出来的 trace 编译，而不是从手搓的 record。"""

        env = Environment(seed=7)
        loop = FastLoop(
            env,
            make_context(),
            config=FastLoopConfig(max_frames=40, min_sleep_frames=3),
        )
        loop.run(40)
        l = lib()
        candidates = l.compile_from_trace(loop.trace())
        # 随机策略下不保证有正净收益的连续段——有就验字段，没有就验不崩。
        for skill in candidates:
            assert skill.total_frames() >= 3
            assert skill.expected_outcome["energy_change"] > 0.0
            assert skill.created_from == SOURCE_COMPILED

    def test_skill_from_trace_survives_a_save_and_reload(self) -> None:
        """序列要能被序列化进快照再取回——否则保存是假的。"""

        store = StructureStore()
        l = SkillLibrary(store)
        skill = l.compile_from_trace(successful_run(4))[0]
        l.save(skill, PASS, 1.0)

        fresh = SkillLibrary(StructureStore()).context
        assert skill.skill_id not in fresh.skills
        assert skill.skill_id in store.snapshot().skills

    def test_updated_stats_reach_the_next_snapshot(self) -> None:
        """Skill Runner 的回写要能进新快照，否则统计永远停在 0。"""

        l = lib()
        skill = l.compile_from_trace(successful_run(4))[0]
        l.save(skill, PASS, 1.0)
        used = Skill(**{**skill.__dict__, "success_count": 3, "last_used": 9.0})
        l.update(used, PASS, 2.0)
        assert l.context.skills[skill.skill_id].success_count == 3
        assert l.context.skills[skill.skill_id].last_used == 9.0
