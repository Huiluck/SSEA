"""判据健康度检查表测试 —— docs/03 §11。

本文件的重心不是「代码跑得通」，而是 **`TestTheGuardCanActuallyGoRed`**：
项目已经吃过三次同一个亏，判据在**不变红**时看起来完全正常
（危险回避率两臂均 0.9814、技能固化 0/33、记忆粗粒度签名 7/8 seed 相同）。
所以本协议必须先在**这三种已知病象**上给出指定的红，才有资格去体检别的判据。
"""

from __future__ import annotations

import pytest

from SSEA.sse_protocols.judgement_health import (
    BOUND_NONE,
    BOUND_UNIT,
    BOUND_ZERO,
    FAIL,
    PASS,
    UNKNOWN,
    WARN,
    EDGE_MASS_LIMIT,
    MARGIN_FLOOR,
    RESOLUTION_FLOOR,
    JudgementDeclaration,
    assess,
    v_tau,
)


def _healthy_declaration(name: str = '健全判据', bound: str = BOUND_UNIT) -> JudgementDeclaration:
    """一条**八条全声明齐**的判据，用来隔离出「只有数据在决定判定」。"""

    return JudgementDeclaration(
        name=name,
        bound=bound,
        matched_baseline='等预算多试 K 次',
        search_seeds=(0, 1, 2, 3),
        eval_seeds=(4, 5, 6, 7),
        reported_as='pass@1',
        can_go_red=True,
    )


class TestVtau:
    """`V_τ` 的两个零不是同一个零。"""

    def test_zero_denominator_is_none_not_zero(self) -> None:
        """没有样本 → **None**。这是「没有观测」，不是「观测到 0」。"""

        assert v_tau([]) is None
        assert v_tau([None, None]) is None

    def test_single_sample_is_a_real_zero(self) -> None:
        """一个样本 → **0.0**，这是真实的 0（单个观测没有离散度）。"""

        assert v_tau([0.9814]) == 0.0

    def test_matches_population_variance(self) -> None:
        # 总体方差（除以 n，不除以 n−1）
        assert v_tau([0.0, 1.0, 2.0]) == pytest.approx(2.0 / 3.0)

    def test_none_samples_are_dropped_not_zeroed(self) -> None:
        """`None` 被丢掉，**不被当成 0**——当成 0 会压低方差，把有差的情境读成没差。"""

        assert v_tau([1.0, None, 3.0]) == v_tau([1.0, 3.0]) == pytest.approx(1.0)


class TestDerivedQuantitiesNeverFillTheZeroDenominator:
    """分母为 0 时，所有派生量必须是 `None`，不得填 1.0 或 0.0。"""

    def test_all_none_yields_none_derivations(self) -> None:
        health = assess(
            _healthy_declaration(),
            (('A', (None, None)), ('B', (None, None))),
        )
        assert health.n_defined == 0
        assert health.minimum is None
        assert health.maximum is None
        assert health.median is None
        assert health.distinct_ratio is None
        assert health.edge_mass is None
        assert health.boundary_margin is None
        assert health.arm_gap is None

    def test_all_none_is_h1_red(self) -> None:
        health = assess(_healthy_declaration(), (('A', (None,)), ('B', (None,))))
        assert health.clause('H1') == FAIL
        assert 'H1' in health.failing


class TestTheGuardCanActuallyGoRed:
    """三种**已知病象**必须给出指定的红。这是本协议存在的全部理由。"""

    def test_disease_1_saturated_and_arms_identical(self) -> None:
        """病象一：危险回避率两臂均 0.9814。

        期望：H3（两臂分不开）与 H4（取值是常数）**判红**，H2（贴界）**警告**。
        H3 曾经是绿的——因为判「可分」时用了 `a <= b`，而两臂取值完全相同时
        它**恒真**，于是「分不开」被读成了「可分」。
        """

        health = assess(
            _healthy_declaration('危险回避率'),
            (('A', (0.9814,) * 8), ('B', (0.9814,) * 8)),
        )
        assert health.clause('H3') == FAIL, '两臂完全相同时必须判红'
        assert health.clause('H4') == FAIL, '常数取值必须判红'
        assert health.clause('H2') == WARN, '距 1.0 只剩 0.0186 余量，应警告'
        assert health.separable is False, '取值完全相同时不得报 separable'
        assert set(health.failing) == {'H3', 'H4'}

    def test_disease_2_zero_denominator_on_one_arm(self) -> None:
        """病象二：技能调用成功率 0/33——一边**根本没调用过**，另一边全失败。

        期望：H2 判红（唯一的样本贴在 0 边界上，可分辨空间为 0），
        H3 记 UNKNOWN（只有一臂有数据）。
        """

        health = assess(
            _healthy_declaration('技能调用成功率'),
            (('固化关', (None,) * 8), ('固化开', (0.0,) + (None,) * 7)),
        )
        assert health.clause('H2') == FAIL
        assert health.clause('H3') == UNKNOWN
        assert 'H2' in health.failing
        assert 'H3' not in health.failing, 'UNKNOWN 不得计入 failing（它不是红）'

    def test_disease_3_integer_quantisation(self) -> None:
        """病象三：记忆粗粒度签名的 5 个整数 7/8 seed 相同——分辨率不足。

        期望：H4 **警告**（取值数/样本数低于地板），因为 8 个样本只有 2 个取值。
        """

        # 16 个样本、3 个取值 → 0.1875 < 0.25。**8 个样本是量不出 WARN 的**：
        # distinct=1 且 n≥8 直接判红，distinct=2 恰好等于 1/4 不满足「小于」——
        # 这不是缺陷，是「分辨率不足」在 8 个样本上只有「常数」与「够用」两档。
        health = assess(
            _healthy_declaration('可编译段数', bound=BOUND_ZERO),
            (('A', (0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 2.0)), ('B', (0.0,) * 4 + (1.0,) * 4)),
        )
        assert health.clause('H4') == WARN
        assert health.distinct == 3
        assert health.distinct_ratio == pytest.approx(3 / 16)
        assert health.distinct_ratio < RESOLUTION_FLOOR

    def test_constant_at_eight_samples_is_red_not_warn(self) -> None:
        """8 个样本只有 1 个取值 → **红**（信息量为 0），不是警告。"""

        health = assess(
            _healthy_declaration('常量判据', bound=BOUND_NONE),
            (('A', (3.0,) * 4), ('B', (3.0,) * 4)),
        )
        assert health.clause('H4') == FAIL

    def test_few_samples_with_one_value_is_not_flagged(self) -> None:
        """样本少时「只有 1 个取值」是正常现象——**不得误报**。

        n=2 时取值数必然是 1 或 2；此时报「分辨率不足」是假阳性，而假阳性
        会让整套检查表被当成噪声忽略掉。所以下限是「n ≥ 8 且有 1 个取值 → 红」，
        而不是「取值数少就红」。
        """

        health = assess(
            _healthy_declaration('小样本', bound=BOUND_NONE),
            (('A', (2.0,)), ('B', (2.0,))),
        )
        assert health.clause('H4') == PASS
        assert health.distinct == 1
        assert health.n_defined == 2


class TestDeclarativeClauses:
    """H5–H8 靠声明；`None`（未声明）不等于通过。"""

    def test_matched_baseline_missing_is_unknown_not_fail(self) -> None:
        declaration = JudgementDeclaration(name='未登记', bound=BOUND_UNIT)
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H5') == UNKNOWN

    def test_matched_baseline_declared_as_none_is_red(self) -> None:
        declaration = JudgementDeclaration(name='无基线', bound=BOUND_UNIT, matched_baseline='')
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H5') == FAIL

    def test_overlapping_seeds_are_red(self) -> None:
        declaration = JudgementDeclaration(
            name='同集', bound=BOUND_UNIT, search_seeds=(0, 1, 2), eval_seeds=(2, 3)
        )
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H6') == FAIL

    def test_disjoint_seeds_pass(self) -> None:
        declaration = JudgementDeclaration(
            name='分离', bound=BOUND_UNIT, search_seeds=(0, 1), eval_seeds=(2, 3)
        )
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H6') == PASS

    def test_pass_at_k_only_is_red(self) -> None:
        declaration = JudgementDeclaration(name='best-of-k', bound=BOUND_UNIT, reported_as='pass@k')
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H7') == FAIL

    def test_cannot_go_red_is_red(self) -> None:
        declaration = JudgementDeclaration(name='拉不红', bound=BOUND_UNIT, can_go_red=False)
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.clause('H8') == FAIL

    def test_all_unknown_is_not_pass(self) -> None:
        """全未声明时必须**不是** PASS——否则「没登记」会被读成「没问题」。"""

        declaration = JudgementDeclaration(name='空白登记', bound=BOUND_UNIT)
        health = assess(declaration, (('A', (0.4,)), ('B', (0.6,))))
        assert health.verdict != PASS
        assert health.is_healthy is False
        assert len(health.unresolved) == 4

    def test_a_fully_healthy_judgement_passes(self) -> None:
        """八条齐备的一条判据必须**全绿**——否则本协议自己就是个假守卫。

        造一条真正有余量、两臂严格分开、分辨率充足的判据。
        """

        declaration = _healthy_declaration('健全')
        health = assess(
            declaration,
            (
                ('A', (0.10, 0.15, 0.12, 0.18)),
                ('B', (0.60, 0.65, 0.62, 0.68)),
            ),
        )
        assert health.failing == ()
        assert health.unresolved == ()
        assert health.verdict == PASS
        assert health.is_healthy is True


class TestBoundHandling:
    """三种边界的贴界语义不同，混用会误报。"""

    def test_unit_bound_flags_both_ends(self) -> None:
        health = assess(
            _healthy_declaration(bound=BOUND_UNIT),
            (('A', (0.0, 1.0)), ('B', (0.0, 1.0))),
        )
        assert health.edge_mass == 1.0
        assert health.clause('H2') == FAIL

    def test_zero_bound_only_flags_zero(self) -> None:
        health = assess(
            _healthy_declaration(bound=BOUND_ZERO),
            (('A', (0.0, 5.0)), ('B', (0.0, 7.0))),
        )
        assert health.edge_mass == pytest.approx(0.5)
        assert health.boundary_margin == 0.0

    def test_bound_none_does_not_crash_and_h2_is_na(self) -> None:
        """无自然边界的判据（如「能量消耗变化」可以为负）不得炸在格式化上。"""

        health = assess(
            _healthy_declaration(bound=BOUND_NONE),
            (('A', (-0.2, -0.1)), ('B', (0.3, 0.4))),
        )
        assert health.boundary_margin is None
        assert health.clause('H2') == PASS
        assert '不适用' in health.explain('H2')

    def test_margin_floor_is_what_it_says(self) -> None:
        """
        阈值是**严格小于**才警告：余量恰等于 0.05 → 绿；小一点点 → 警告。

        把边界本身算进警告会（在有噪声的数据上）让阈值的作用被放大一倍左右，
        而这类阈值本来就是一个粗刻度，不值得为它加一次额外误报。
        """

        at_floor = assess(
            _healthy_declaration(),
            (('A', (0.2, 0.3)), ('B', (MARGIN_FLOOR, 0.4))),
        )
        assert at_floor.clause('H2') == PASS

        just_below = assess(
            _healthy_declaration(),
            (('A', (0.2, 0.3)), ('B', (MARGIN_FLOOR - 0.001, 0.4))),
        )
        assert just_below.clause('H2') == WARN

    def test_edge_mass_limit_is_a_declared_constant(self) -> None:
        assert EDGE_MASS_LIMIT == 1.0


class TestDeclarationValidation:
    def test_unknown_bound_raises(self) -> None:
        with pytest.raises(ValueError):
            JudgementDeclaration(name='x', bound='percentage')

    def test_unknown_reported_as_raises(self) -> None:
        with pytest.raises(ValueError):
            JudgementDeclaration(name='x', bound=BOUND_UNIT, reported_as='pass@100')


class TestVtauByScenarioIsAligned:
    """`V_τ` 必须在**同一情境内跨臂**算，不能跨情境。"""

    def test_per_scenario_matches_alignment(self) -> None:
        health = assess(
            _healthy_declaration(),
            (('A', (0.0, 1.0, 0.5)), ('B', (1.0, 1.0, 0.5))),
        )
        assert len(health.v_tau_by_scenario) == 3
        assert health.v_tau_by_scenario[0] == pytest.approx(0.25)
        assert health.v_tau_by_scenario[1] == pytest.approx(0.0)
        assert health.v_tau_by_scenario[2] == pytest.approx(0.0)

    def test_unequal_lengths_use_the_shorter(self) -> None:
        """两臂长度不等时按较短的截断——不补齐（补齐就是注入样本）。"""

        health = assess(
            _healthy_declaration(),
            (('A', (0.0, 1.0, 0.5)), ('B', (1.0,))),
        )
        assert len(health.v_tau_by_scenario) == 1
