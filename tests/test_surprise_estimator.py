"""SurpriseEstimator 测试 —— Feedback.prediction_error 的唯一生产者（08 §2.6.1）。"""

from __future__ import annotations

import pytest

from SSEA.surprise_estimator import DEFAULT_SCALES, SurpriseEstimator


class TestPersistencePrediction:
    """一阶持久化预测：预测下一帧 = 当前帧。"""

    def test_first_frame_has_no_error(self) -> None:
        """第一帧只建立基线，无预测可犯。"""
        est = SurpriseEstimator()
        assert est.update(energy=1.0, damage=0.0, nearest_resource_dist=3.0) == 0.0
        assert est.frames_seen == 1

    def test_perfectly_stable_stream_has_zero_error(self) -> None:
        est = SurpriseEstimator()
        est.update(0.8, 0.1, 4.0)
        for _ in range(5):
            assert est.update(0.8, 0.1, 4.0) == pytest.approx(0.0)

    def test_energy_drop_is_the_error(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 5.0)
        # energy 掉 0.2（scale 1.0），其余不变 → 均值 = 0.2 / 3
        err = est.update(0.8, 0.0, 5.0)
        assert err == pytest.approx(0.2 / 3)

    def test_distance_error_is_scaled(self) -> None:
        """distance 无上界，必须按尺度归一化，否则它会压过其它两类流。"""
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 2.0)
        err = est.update(1.0, 0.0, 4.0)
        assert err == pytest.approx(2.0 / DEFAULT_SCALES["nearest_resource_dist"] / 3)

    def test_all_three_streams_contribute_equally(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 5.0)
        # 三条各变 0.1 / 0.1 / 1.0（后者按 scale 10 → 0.1）
        err = est.update(0.9, 0.1, 6.0)
        assert err == pytest.approx(0.1)

    def test_is_deterministic(self) -> None:
        """无权重、无随机——同输入序列必得同输出。"""
        seq = [(1.0, 0.0, 3.0), (0.9, 0.0, 2.5), (0.7, 0.2, 2.0)]
        a = [SurpriseEstimator().update(*s) for s in seq]
        b = [SurpriseEstimator().update(*s) for s in seq]
        assert a == b


class TestMissingStream:
    """资源消失 / 出现是最该被注意的事件，不能因缺值被静默跳过。"""

    def test_absent_both_frames_is_ignored(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, None)
        assert est.update(1.0, 0.0, None) == pytest.approx(0.0)

    def test_appearance_counts_as_full_scale_surprise(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, None)
        err = est.update(1.0, 0.0, 3.0)
        # 该流记 1.0，另两条记 0 → 均值 1/3
        assert err == pytest.approx(1.0 / 3)

    def test_disappearance_counts_as_full_scale_surprise(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 3.0)
        err = est.update(1.0, 0.0, None)
        assert err == pytest.approx(1.0 / 3)


class TestEma:
    """EMA 进入 internal_drive_vector.surprise_ema（08 §2.5）。"""

    def test_ema_starts_at_first_real_error(self) -> None:
        est = SurpriseEstimator(ema_alpha=0.5)
        est.update(1.0, 0.0, 5.0)
        assert est.ema == 0.0
        est.update(0.5, 0.0, 5.0)
        assert est.ema == pytest.approx(est.last_error)

    def test_ema_smooths_spike(self) -> None:
        est = SurpriseEstimator(ema_alpha=0.1)
        est.update(1.0, 0.0, 5.0)          # 基线
        est.update(0.5, 0.0, 5.0)          # 突变，ema 被拉到突变值
        spike_ema = est.ema
        est.update(0.5, 0.0, 5.0)          # 之后完全稳定，原始误差归零
        # 原始误差已经归零，EMA 还在缓慢下落——这就是"平滑"
        assert est.last_error == pytest.approx(0.0)
        assert est.ema == pytest.approx(spike_ema * 0.9)
        assert est.ema > 0.0

    def test_ema_lags_raw_error_after_warmup(self) -> None:
        est = SurpriseEstimator(ema_alpha=0.1)
        est.update(1.0, 0.0, 5.0)          # 基线
        est.update(0.9, 0.0, 5.0)          # 第 2 帧：ema 初值 = raw
        est.update(0.9, 0.0, 5.0)          # 第 3 帧：误差归零，ema 开始衰减
        assert est.last_error == pytest.approx(0.0)
        assert est.ema > 0.0
        est.update(0.5, 0.0, 5.0)          # 第 4 帧：raw 跳升，ema 跟不上
        assert est.last_error > est.ema

    def test_last_error_is_raw_not_smoothed(self) -> None:
        est = SurpriseEstimator(ema_alpha=0.1)
        est.update(1.0, 0.0, 5.0)
        est.update(0.9, 0.0, 5.0)
        raw = est.update(0.5, 0.0, 5.0)
        assert est.last_error == pytest.approx(raw)
        assert est.ema != pytest.approx(raw)


class TestReset:
    def test_reset_clears_baseline(self) -> None:
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 5.0)
        est.update(0.5, 0.0, 4.0)
        est.reset()
        assert est.frames_seen == 0
        assert est.ema == 0.0
        assert est.last_error == 0.0
        # 重置后第一帧又是基线帧
        assert est.update(1.0, 0.0, 5.0) == 0.0

    def test_reset_reinitializes_ema(self) -> None:
        """reset 后 EMA 重新从首个真实误差起算，而不是续用旧值。"""
        est = SurpriseEstimator(ema_alpha=0.1)
        est.update(1.0, 0.0, 5.0)
        est.update(0.5, 0.0, 5.0)
        old = est.ema
        est.reset()
        est.update(1.0, 0.0, 5.0)
        est.update(0.9, 0.0, 5.0)
        assert est.ema == pytest.approx(est.last_error)
        assert est.ema != pytest.approx(old)


class TestNeverNegative:
    def test_errors_are_absolutes(self) -> None:
        """Feedback 拒绝负 prediction_error，估计器必须先保证非负。"""
        est = SurpriseEstimator()
        est.update(1.0, 0.0, 5.0)
        for energy in (1.5, 0.2, 0.0, 3.0):
            assert est.update(energy, 0.0, 5.0) >= 0.0
