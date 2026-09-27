"""Metabolic Monitor 测试 —— internal_drive 接线 + 睡眠判定（08 §2.5 / §2.2）。"""

from __future__ import annotations

import pytest

from SSEA.metabolic_monitor import (
    DRIVE_DIM,
    IDX_DAMAGE_URGENCY,
    IDX_ENERGY_DEFICIT,
    IDX_FATIGUE,
    IDX_SURPRISE_EMA,
    MetabolicMonitor,
)
from SSEA.sse_protocols import (
    BodyState,
    EnvironmentSummary,
    ObjectVector,
    Observation,
    default_constraints,
)


def make_body(
    energy: float = 0.8, damage: float = 0.1, fatigue: float = 0.2
) -> BodyState:
    return BodyState(
        energy=energy,
        damage=damage,
        fatigue=fatigue,
        position=(0.0, 0.0),
        orientation=(1.0, 0.0),
        action_constraints=default_constraints(),
        internal_state=(),
    )


def make_observation(
    energy: float = 0.8, fatigue: float = 0.2, threat: float = 0.0
) -> Observation:
    return Observation(
        time=1.0,
        body=make_body(energy=energy, fatigue=fatigue),
        environment=EnvironmentSummary(
            light_level=1.0,
            temperature=0.5,
            danger_level=threat,
            resource_density=0.5,
            time_phase="day",
        ),
        objects=(
            ObjectVector(
                object_id="h1",
                category_id=2,
                distance=3.0,
                direction=(1.0, 0.0),
                velocity=(0.0, 0.0),
                resource_value=0.0,
                threat_level=threat,
                affordance=(0.0,),
            ),
        )
        if threat > 0
        else (),
    )


class TestDriveVector:
    """08 §2.5：internal_drive_vector 四分量，第一阶段实现前两项。"""

    def test_shape_is_four(self, monitor: MetabolicMonitor) -> None:
        d = monitor.drive_vector(make_body())
        assert len(d) == DRIVE_DIM

    def test_energy_deficit_is_first(self, monitor: MetabolicMonitor) -> None:
        assert monitor.drive_vector(make_body(energy=0.75))[IDX_ENERGY_DEFICIT] == (
            pytest.approx(0.25)
        )
        assert monitor.drive_vector(make_body(energy=1.0))[IDX_ENERGY_DEFICIT] == (
            pytest.approx(0.0)
        )
        assert monitor.drive_vector(make_body(energy=0.0))[IDX_ENERGY_DEFICIT] == (
            pytest.approx(1.0)
        )

    def test_deficit_never_negative(self, monitor: MetabolicMonitor) -> None:
        """BodyState 已禁止负能量，但驱动向量仍应自行兜住。"""

        assert monitor.drive_vector(make_body(energy=0.0))[IDX_ENERGY_DEFICIT] >= 0.0

    def test_reserved_components_are_zero(self, monitor: MetabolicMonitor) -> None:
        """C8：给结构先验，不给满能力。后两项置 0 预留。"""

        d = monitor.drive_vector(make_body(damage=0.9, fatigue=0.9))
        assert d[IDX_DAMAGE_URGENCY] == 0.0
        assert d[IDX_FATIGUE] == 0.0

    def test_surprise_ema_is_second(self, monitor: MetabolicMonitor) -> None:
        assert monitor.drive_vector(make_body())[IDX_SURPRISE_EMA] == 0.0
        monitor.observe(make_observation(energy=0.8))
        monitor.observe(make_observation(energy=0.5))
        assert monitor.drive_vector(make_body())[IDX_SURPRISE_EMA] > 0.0


class TestObserve:
    """Feedback.prediction_error 的唯一生产者（08 §2.6.1）。"""

    def test_first_observation_gives_zero(self, monitor: MetabolicMonitor) -> None:
        assert monitor.observe(make_observation()) == 0.0

    def test_feeds_three_scalar_streams(self, monitor: MetabolicMonitor) -> None:
        """energy / damage / nearest_resource_dist 三类。"""

        monitor.observe(make_observation(energy=1.0))
        err = monitor.observe(make_observation(energy=0.5))
        assert err > 0.0

    def test_resources_are_seen_by_the_estimator(
        self, monitor: MetabolicMonitor
    ) -> None:
        obs = Observation(
            time=1.0,
            body=make_body(),
            environment=make_observation().environment,
            objects=(
                ObjectVector(
                    object_id="r1",
                    category_id=1,
                    distance=4.0,
                    direction=(1.0, 0.0),
                    velocity=(0.0, 0.0),
                    resource_value=0.8,
                    threat_level=0.0,
                    affordance=(1.0,),
                ),
            ),
        )
        assert obs.nearest_resource_distance() == pytest.approx(4.0)
        monitor.observe(obs)
        # 距离变了 → 有误差
        obs2 = Observation(
            time=2.0,
            body=make_body(),
            environment=obs.environment,
            objects=(
                ObjectVector(
                    object_id="r1",
                    category_id=1,
                    distance=1.0,
                    direction=(1.0, 0.0),
                    velocity=(0.0, 0.0),
                    resource_value=0.8,
                    threat_level=0.0,
                    affordance=(1.0,),
                ),
            ),
        )
        assert monitor.observe(obs2) > 0.0


class TestSleepJudgement:
    """08 §2.2：安全 + 疲劳，两条同时满足才睡。刻意不用 OR——入口必须窄。

    08 §2.2 原文还有第三条 ``energy ≥ 0.7``，2026-09-27 移除：
    它与疲劳判据在默认代谢参数下算术互斥（能量单调降、疲劳单调升），
    交出的不是「收窄的入口」而是**空集**。见
    ``TestEnergyDoesNotGateSleep`` 与 ``SSEA.metabolic_monitor`` 的推导。
    """

    def test_sleeps_when_all_conditions_hold(self, monitor: MetabolicMonitor) -> None:
        body = make_body(energy=0.9, fatigue=0.8)
        obs = make_observation(energy=0.9, fatigue=0.8, threat=0.0)
        assert monitor.wants_sleep(body, obs)

    def test_blocked_by_threat(self, monitor: MetabolicMonitor) -> None:
        body = make_body(energy=0.9, fatigue=0.8)
        obs = make_observation(energy=0.9, fatigue=0.8, threat=0.5)
        assert not monitor.wants_sleep(body, obs)
        assert "threat_imminent" in monitor.sleep_blockers(body, obs)

    def test_blocked_by_low_fatigue(self, monitor: MetabolicMonitor) -> None:
        body = make_body(energy=0.9, fatigue=0.1)
        obs = make_observation(energy=0.9, fatigue=0.1)
        assert not monitor.wants_sleep(body, obs)
        assert monitor.sleep_blockers(body, obs) == ("fatigue_insufficient",)

    def test_blockers_are_empty_when_sleepable(
        self, monitor: MetabolicMonitor
    ) -> None:
        body = make_body(energy=0.9, fatigue=0.8)
        obs = make_observation(energy=0.9, fatigue=0.8)
        assert monitor.sleep_blockers(body, obs) == ()

    def test_blockers_cover_every_condition(
        self, monitor: MetabolicMonitor
    ) -> None:
        """判据里的每条都没满足时，每个 blocker 都必须报出来。"""

        body = make_body(energy=0.1, fatigue=0.1)
        obs = make_observation(energy=0.1, fatigue=0.1, threat=0.9)
        assert set(monitor.sleep_blockers(body, obs)) == {
            "threat_imminent",
            "fatigue_insufficient",
        }


class TestEnergyDoesNotGateSleep:
    """能量**不参与**睡眠判定（2026-09-27 修订 08 §2.2）。

    这一组守的是「移除 energy ≥ 0.7」这个决定本身：如果哪天有人把能量条件
    加回来，下面两条会红，而不是让睡眠重新变成不可达的空集。
    """

    def test_starving_but_safe_and_tired_still_sleeps(
        self, monitor: MetabolicMonitor
    ) -> None:
        body = make_body(energy=0.02, fatigue=0.9)
        obs = make_observation(energy=0.02, fatigue=0.9, threat=0.0)
        assert monitor.wants_sleep(body, obs)

    def test_low_energy_is_not_a_blocker(self, monitor: MetabolicMonitor) -> None:
        """能量低不构成 blocker——一个不影响结论的 blocker 会让
        「为什么还不睡」的答案变成假话。"""

        body = make_body(energy=0.01, fatigue=0.9)
        obs = make_observation(energy=0.01, fatigue=0.9, threat=0.0)
        assert monitor.sleep_blockers(body, obs) == ()

    def test_energy_threshold_is_gone_not_merely_ignored(self) -> None:
        """字段是**移除**，不是留着不读。

        留一个不参与判定的阈值旋钮，就是文档里那种「看起来完成了，
        其实没生效」的配置——有人会去调它，而调它什么也不会发生。
        """

        assert not hasattr(MetabolicMonitor(), "sleep_energy_threshold")


class TestThresholdsAreConfigurable:
    """阈值在 behavior_policy 里，可经 UPDATE_THRESHOLD 提案修改（08 §3.1）。"""

    def test_thresholds_are_fields_not_constants(self) -> None:
        m = MetabolicMonitor(
            sleep_threat_threshold=0.5,
            sleep_fatigue_threshold=0.5,
        )
        assert m.sleep_threat_threshold == 0.5
        assert m.sleep_fatigue_threshold == 0.5

    def test_loosened_thresholds_change_behaviour(self) -> None:
        strict = MetabolicMonitor()
        loose = MetabolicMonitor(sleep_fatigue_threshold=0.1)
        body = make_body(energy=0.4, fatigue=0.2)
        obs = make_observation(energy=0.4, fatigue=0.2)
        assert not strict.wants_sleep(body, obs)
        assert loose.wants_sleep(body, obs)


class TestReset:
    def test_reset_clears_surprise_baseline(
        self, monitor: MetabolicMonitor
    ) -> None:
        monitor.observe(make_observation(energy=1.0))
        monitor.observe(make_observation(energy=0.3))
        assert monitor.surprise.ema > 0.0
        monitor.reset()
        assert monitor.surprise.ema == 0.0
        assert monitor.surprise.frames_seen == 0
