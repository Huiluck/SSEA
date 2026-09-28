"""技能固化漏斗测试 —— docs/03 §11.8。

本文件的重心是两件事：

1. **诊断顺序不可颠倒**：`reused == 0` 在 `windows == 0` 时是**必然**的。
   若把它报成「调用面有问题」，人会去改 precondition，而真正的问题在切段
   ——这正是只看 0/33 会犯的错。
2. **四种病必须能被分开**：实测（2026-09-29，8 seed × 200 帧）证明「0/33」
   里同时住着四种不同的病，其中 **6/8 个 seed 连候选都没产出**。

轨迹夹具从 `tests.test_skill_library` 导入而**不另写一份**：
夹具写两份必然漂移，而漂移的表现是「同一个轨迹在两处编出不同的技能」。
"""

from __future__ import annotations

import pytest

from SSEA.skill_library import SkillLibrary, candidate_counts
from SSEA.skill_runner import SkillRunner
from SSEA.sse_protocols.induction_funnel import (
    ALL_DUPLICATE,
    EMPTY_TRACE,
    NEVER_INVOKED,
    NO_POSITIVE_SEGMENT,
    NO_WINDOW,
    OPEN,
    REJECTED_BY_GATE,
    InductionFunnel,
    diagnose,
)
from tests.test_skill_library import consistent_run, successful_run


def _funnel(
    frames: int = 100,
    windows: int = 10,
    positive: int = 5,
    new_candidates: int = 5,
    committed: int = 3,
    reused: int = 2,
) -> InductionFunnel:
    """造一个**合法**漏斗。

    把某一段置 0 时，**下游自动归零**——这不是为了让测试好写而放宽检查，
    而是把「上游为 0 则下游必为 0」这条事实编码进夹具。手写 `windows=0`
    而 `positive=5` 会被 `InductionFunnel` 直接拒收（那正是它的职责），
    夹具必须表达真实形状而不是随手改一个数。
    """

    vals = [frames, windows, positive, new_candidates, committed]
    for i in range(1, len(vals)):
        vals[i] = 0 if vals[i - 1] == 0 else min(vals[i], vals[i - 1])
    if vals[-1] == 0:
        reused = 0
    else:
        reused = min(reused, vals[-1])
    return InductionFunnel(
        frames=vals[0],
        windows=vals[1],
        positive=vals[2],
        new_candidates=vals[3],
        committed=vals[4],
        reused=reused,
    )


class TestFunnelShape:
    def test_monotone_violation_is_rejected(self) -> None:
        """漏斗只能单调不增。违反它说明计数来自**不同来源**，那比计数为 0 更难发现。"""

        with pytest.raises(ValueError, match='不单调'):
            InductionFunnel(frames=10, windows=20)

    def test_committed_greater_than_new_candidates_is_rejected(self) -> None:
        # 直接构造，不走 `_funnel`——那个夹具会**夹住**非法形状（上游为 0 则下游归零），
        # 所以它造不出违反单调的例子。要测守卫就得正面撞它。
        with pytest.raises(ValueError, match='不单调'):
            InductionFunnel(frames=100, windows=10, positive=5, new_candidates=2, committed=4)

    def test_negative_count_is_rejected(self) -> None:
        with pytest.raises(ValueError, match='不得为负'):
            InductionFunnel(frames=-1)

    def test_attempted_and_passed_are_aliases_of_the_right_stages(self) -> None:
        """ASI 的 attempted 是**候选数**，不是切窗数——差一格就是两种病。"""

        f = _funnel(windows=10, positive=4)
        assert f.attempted == 4
        assert f.passed == f.committed

    def test_losses_are_per_stage(self) -> None:
        f = _funnel(frames=100, windows=10, positive=6, new_candidates=6, committed=3)
        assert f.losses == (('帧', '窗', 90), ('窗', '候选', 4), ('候选', '去重', 0), ('去重', '入库', 3))

    def test_first_empty_stage_walks_front_to_back(self) -> None:
        assert _funnel(windows=0).first_empty_stage == 'windows'
        assert _funnel(positive=0).first_empty_stage == 'positive'
        assert _funnel(reused=0).first_empty_stage == 'reused'
        assert _funnel().first_empty_stage is None


class TestReuseRateNeverFillsAnEmptyDenominator:
    def test_zero_committed_yields_none_not_zero(self) -> None:
        """`committed == 0` 时复用率是 `None`。

        填 0.0 会让「没有技能可复用」读成「技能都没被复用」——两句结论指向
        完全不同的下一步，而它们在 0.0 上长得一样。
        """

        assert _funnel(committed=0, new_candidates=0, reused=0).reuse_rate is None

    def test_real_rate(self) -> None:
        assert _funnel(committed=4, reused=1).reuse_rate == pytest.approx(0.25)


class TestDiagnosisOrderCannotBeReversed:
    def test_zero_windows_wins_over_zero_reuse(self) -> None:
        """**本文件最重要的一条。** 全 0 的漏斗必须报最上游的那一段。"""

        f = InductionFunnel(frames=100, windows=0)
        d = diagnose(f)
        assert d.code == NO_WINDOW
        assert d.code != NEVER_INVOKED

    def test_empty_trace_wins_over_everything(self) -> None:
        assert diagnose(InductionFunnel()).code == EMPTY_TRACE

    def test_each_code_is_reachable(self) -> None:
        assert diagnose(_funnel(frames=0)).code == EMPTY_TRACE
        assert diagnose(_funnel(windows=0)).code == NO_WINDOW
        assert diagnose(_funnel(positive=0)).code == NO_POSITIVE_SEGMENT
        assert diagnose(_funnel(positive=3, new_candidates=0, committed=0, reused=0)).code == ALL_DUPLICATE
        assert diagnose(_funnel(committed=0, reused=0)).code == REJECTED_BY_GATE
        assert diagnose(_funnel(reused=0)).code == NEVER_INVOKED
        assert diagnose(_funnel()).code == OPEN

    def test_every_diagnosis_carries_a_stage_and_a_next_action(self) -> None:
        """诊断必须带**一个**下一步；只说「失败了」等于没说。

        并且：不同的病必须给出**不同**的下一步——若四种病给出同一句话，
        三档分母就白拆了。
        """

        funnels = (
            _funnel(frames=0),
            _funnel(windows=0),
            _funnel(positive=0),
            _funnel(positive=3, new_candidates=0, committed=0, reused=0),
            _funnel(committed=0, reused=0),
            _funnel(reused=0),
            _funnel(),
        )
        diagnoses = [diagnose(f) for f in funnels]
        assert [d.code for d in diagnoses] == [
            EMPTY_TRACE, NO_WINDOW, NO_POSITIVE_SEGMENT, ALL_DUPLICATE,
            REJECTED_BY_GATE, NEVER_INVOKED, OPEN,
        ]
        for d in diagnoses:
            assert d.stage
            assert d.next_action
        actions = {d.next_action for d in diagnoses}
        assert len(actions) == len(diagnoses), '不同的病给出了相同的下一步'

    def test_is_open_only_when_every_stage_is_non_zero(self) -> None:
        assert _funnel().is_open is True
        assert _funnel(reused=0).is_open is False


class TestRealReadings20260929:
    """**实测锚点**：2026-09-29 的 8 seed × 200 帧读数。

    这一组数字把「0/33」拆成了四种病，而且其中 **6/8 个 seed 连候选都没产出**。
    把它钉成测试，是为了让「技能表示够不够」这个问题**不能在候选还不存在时**
    被提起。
    """

    #: (windows, positive, new_candidates, committed, reused)，逐 seed，顺序同 DEFAULT_SEEDS。
    READINGS = (
        (8, 2, 1, 1, 1),    # seed 0 → OPEN
        (12, 0, 0, 0, 0),   # seed 1 → NO_POSITIVE_SEGMENT
        (18, 0, 0, 0, 0),   # seed 2 → NO_POSITIVE_SEGMENT
        (0, 0, 0, 0, 0),    # seed 3 → NO_WINDOW
        (0, 0, 0, 0, 0),    # seed 4 → NO_WINDOW
        (10, 3, 1, 1, 0),   # seed 5 → NEVER_INVOKED
        (0, 0, 0, 0, 0),    # seed 6 → NO_WINDOW
        (13, 0, 0, 0, 0),   # seed 7 → NO_POSITIVE_SEGMENT
    )

    def _funnels(self) -> tuple[InductionFunnel, ...]:
        return tuple(
            InductionFunnel(
                frames=200, windows=w, positive=p, new_candidates=n, committed=c, reused=r
            )
            for w, p, n, c, r in self.READINGS
        )

    def test_four_diseases_not_one(self) -> None:
        codes = {diagnose(f).code for f in self._funnels()}
        assert codes == {OPEN, NO_POSITIVE_SEGMENT, NO_WINDOW, NEVER_INVOKED}

    def test_two_thirds_of_seeds_never_produce_a_candidate(self) -> None:
        """6/8 个 seed 的 attempted 是 0 ⇒ 在这些 seed 上「技能表示够不够」
        根本无法被提出——没有候选可谈。"""

        assert sum(1 for f in self._funnels() if f.attempted == 0) == 6

    def test_totals_match_the_reported_0_over_33(self) -> None:
        funnels = self._funnels()
        assert sum(f.passed for f in funnels) == 2
        assert sum(f.reused for f in funnels) == 1
        # 33 次调用全落在那一条被复用的技能上：0/33 不是「没有复用」。
        assert sum(f.reused for f in funnels) == 1


class TestCandidateCountsMatchesTheCompiler:
    """`candidate_counts` 与 `compile_from_trace` **必须走同一份切段规则**。

    写成两份必然漂移，漂移的表现是「漏斗说切了 12 窗、编译说产出 5 条」这种
    谁都对不上的数——而它不会报错。
    """

    def test_successful_run_yields_one_window_and_one_candidate(self) -> None:
        trace = successful_run(5)
        assert candidate_counts(trace) == (1, 1)

    def test_non_positive_energy_is_a_window_but_not_a_candidate(self) -> None:
        """窗口存在、能量判据把它丢掉 ⇒ (1, 0)。

        这正是实测里 3 个 seed 的病：**不是没切出来，是切出来了但净收益不为正**。
        """

        trace = consistent_run([0.5] * 5, [0.0] * 5)
        assert candidate_counts(trace) == (1, 0)

    def test_too_short_run_yields_no_window(self) -> None:
        assert candidate_counts(successful_run(2)) == (0, 0)

    def test_candidate_count_equals_compiled_length(self) -> None:
        """防漂移断言：候选数必须等于编译器实际产出的条数。"""

        for trace in (successful_run(5), consistent_run([0.5] * 5, [0.0] * 5), successful_run(9)):
            _windows, positive = candidate_counts(trace)
            assert positive == len(SkillLibrary().compile_from_trace(trace))

    def test_library_delegates_to_the_same_rule(self) -> None:
        trace = successful_run(5)
        assert SkillLibrary().funnel_counts(trace) == candidate_counts(trace)


class TestRunnerCountsOnlyRealInvocations:
    def test_no_invocation_before_any_run(self) -> None:
        runner = SkillRunner(SkillLibrary().context)
        assert runner.invoked_skill_ids() == ()
        assert runner.stats_for('sk_x').invocations == 0

    def test_an_aborted_run_counts_as_an_invocation(self) -> None:
        """中止也是调用——「调用过但失败」与「从没调用过」必须分得开。"""

        runner = SkillRunner(SkillLibrary().context)
        runner.stats_for('sk_x').failure_count += 1
        assert runner.invoked_skill_ids() == ('sk_x',)

    def test_ids_are_sorted_and_deduplicated(self) -> None:
        runner = SkillRunner(SkillLibrary().context)
        for sid in ('sk_b', 'sk_a', 'sk_b'):
            runner.stats_for(sid).success_count += 1
        assert runner.invoked_skill_ids() == ('sk_a', 'sk_b')
        assert runner.stats_for('sk_a').invocations == 1
