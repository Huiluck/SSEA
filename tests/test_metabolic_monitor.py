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
    """08 §2.2：三条同时满足才睡。刻意不用 OR——入口必须窄。"""

    def test_sleeps_when_all_three_hold(self, monitor: MetabolicMonitor) -> None:
        body = make_body(energy=0.9, fatigue=0.8)
        obs = make_observation(energy=0.9, fatigue=0.8, threat=0.0)
        assert monitor.wants_sleep(body, obs)

    def test_blocked_by_low_energy(self, monitor: MetabolicMonitor) -> None:
        body = make_body(energy=0.5, fatigue=0.8)
        obs = make_observation(energy=0.5, fatigue=0.8)
        assert not monitor.wants_sleep(body, obs)
        assert monitor.sleep_blockers(body, obs) == ("energy_below_threshold",)

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
        """三条全不满足时，三个 blocker 都必须报出来。"""

        body = make_body(energy=0.1, fatigue=0.1)
        obs = make_observation(energy=0.1, fatigue=0.1, threat=0.9)
        assert set(monitor.sleep_blockers(body, obs)) == {
            "energy_below_threshold",
            "threat_imminent",
            "fatigue_insufficient",
        }


class TestThresholdsAreConfigurable:
    """阈值在 behavior_policy 里，可经 UPDATE_THRESHOLD 提案修改（08 §3.1）。"""

    def test_thresholds_are_fields_not_constants(self) -> None:
        m = MetabolicMonitor(
            sleep_energy_threshold=0.5,
            sleep_threat_threshold=0.5,
            sleep_fatigue_threshold=0.5,
        )
        assert m.sleep_energy_threshold == 0.5
        assert m.sleep_threat_threshold == 0.5
        assert m.sleep_fatigue_threshold == 0.5

    def test_loosened_thresholds_change_behaviour(self) -> None:
        strict = MetabolicMonitor()
        loose = MetabolicMonitor(
            sleep_energy_threshold=0.3, sleep_fatigue_threshold=0.1
        )
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
