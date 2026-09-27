"""Perception Encoder 测试 —— C4「低带宽」在观测侧的落地（07 §6.1）。"""

from __future__ import annotations

import pytest
import torch

from SSEA.perception_encoder import (
    ENV_DIM,
    EVENT_EMBED_DIM,
    PER_EVENT_DIM,
    PER_OBJECT_DIM,
    TIME_PHASES,
    PerceptionConfig,
    PerceptionEncoder,
)
from SSEA.sse_protocols import (
    EVENT_TYPES,
    BodyState,
    CommunicationSignal,
    EnvironmentSummary,
    EventVector,
    ObjectVector,
    Observation,
    default_constraints,
)


def make_body(energy: float = 0.8) -> BodyState:
    return BodyState(
        energy=energy,
        damage=0.1,
        fatigue=0.2,
        position=(1.0, 2.0),
        orientation=(0.0, 1.0),
        action_constraints=default_constraints(),
        internal_state=(0.1, 0.2, 0.3, 0.4),
    )


def make_env(phase: str = "day") -> EnvironmentSummary:
    return EnvironmentSummary(
        light_level=0.9,
        temperature=0.5,
        danger_level=0.2,
        resource_density=0.5,
        time_phase=phase,
    )


def make_object(object_id: str = "o1", distance: float = 2.0) -> ObjectVector:
    return ObjectVector(
        object_id=object_id,
        category_id=1,
        distance=distance,
        direction=(1.0, 0.0),
        velocity=(0.0, 0.0),
        resource_value=0.7,
        threat_level=0.1,
        affordance=(1.0, 0.0, 0.0, 0.0),
    )


def make_observation(
    n_objects: int = 3,
    n_events: int = 2,
    n_signals: int = 1,
    phase: str = "day",
) -> Observation:
    return Observation(
        time=10.0,
        body=make_body(),
        environment=make_env(phase),
        objects=tuple(make_object(f"o{i}", float(i + 1)) for i in range(n_objects)),
        events=tuple(
            EventVector(
                event_id=f"e{i}",
                timestamp=float(i),
                event_type="OBJECT_FOUND",
                source_id=f"o{i}",
                context_vector=(0.1, 0.2, 0.3, 0.4),
                importance=0.5,
            )
            for i in range(n_events)
        ),
        social_signals=tuple(
            CommunicationSignal(
                sender_id="a",
                receiver_id="b",
                signal=(0.1, 0.2, 0.3, 0.4),
                timestamp=1.0,
                priority=0,
            )
            for _ in range(n_signals)
        ),
    )


class TestFeaturePacking:
    """特征打包段无参数——这让「感知编码器贡献了多少」可被单独消融。"""

    def test_raw_dim_matches_features(self, encoder: PerceptionEncoder) -> None:
        """``raw_dim`` 属性与 ``features()`` 实际输出长度必须一致。

        这条测试守着一条容易腐烂的不变量：两者若漂移，Linear 层会在运行时
        才报维度错误，而那时的栈顶离病因很远。
        """

        cfg = encoder.config
        expected = (
            3  # body
            + 2 * 2  # position + orientation
            + 4  # internal_state
            + ENV_DIM
            + len(TIME_PHASES)
            + cfg.max_objects * (PER_OBJECT_DIM + 1)  # +1 = 存在掩码
            + cfg.max_events * PER_EVENT_DIM
            + cfg.social_dim
        )
        assert cfg.raw_dim == expected
        feats = encoder.features(make_observation())
        assert feats.numel() == cfg.raw_dim

    def test_features_are_finite(self, encoder: PerceptionEncoder) -> None:
        feats = encoder.features(make_observation())
        assert torch.isfinite(feats).all()

    def test_object_count_does_not_change_length(
        self, encoder: PerceptionEncoder
    ) -> None:
        """对象数量可变，输出维度不可变——这是低带宽的必要条件。"""

        lengths = {
            encoder.features(make_observation(n_objects=n)).numel()
            for n in (0, 1, 5, 20)
        }
        assert lengths == {encoder.config.raw_dim}

    def test_event_count_does_not_change_length(
        self, encoder: PerceptionEncoder
    ) -> None:
        lengths = {
            encoder.features(make_observation(n_events=n)).numel()
            for n in (0, 1, 9)
        }
        assert lengths == {encoder.config.raw_dim}


class TestObjectSelection:
    """只编码最近的 K 个对象。"""

    def test_takes_nearest_objects(self, encoder: PerceptionEncoder) -> None:
        """只取距离最近的 K 个；槽位 0 是最近的那个。"""

        obs = Observation(
            time=0.0,
            body=make_body(),
            environment=make_env(),
            # 距离从 20 递减到 9，最近的是最后一个
            objects=tuple(make_object(f"o{i}", float(20 - i)) for i in range(12)),
        )
        feats = encoder.features(obs)
        offset = _object_block_offset(encoder.config)
        block = PER_OBJECT_DIM + 1

        masks = [
            float(feats[offset + block * i + PER_OBJECT_DIM])
            for i in range(encoder.config.max_objects)
        ]
        assert masks == [1.0] * encoder.config.max_objects

        # 槽位 0 的距离字段应是最小距离 9.0，不是列表顺序里的 20.0
        assert float(feats[offset]) == pytest.approx(9.0)

    def test_short_objects_are_zero_padded(self, encoder: PerceptionEncoder) -> None:
        obs = make_observation(n_objects=1)
        feats = encoder.features(obs)
        offset = _object_block_offset(encoder.config)
        block = PER_OBJECT_DIM + 1
        # 第 2 个对象槽位应全零
        second = feats[offset + block : offset + 2 * block]
        assert torch.count_nonzero(second) == 0


class TestEventEmbedding:
    def test_event_type_is_embedded_not_one_hot(
        self, encoder: PerceptionEncoder
    ) -> None:
        """事件类型走 nn.Embedding，不是 one-hot——类型之间有可学相似度。"""

        assert encoder.event_embed.num_embeddings == len(EVENT_TYPES)
        assert encoder.event_embed.embedding_dim == EVENT_EMBED_DIM

    def test_padding_event_has_zero_importance(
        self, encoder: PerceptionEncoder
    ) -> None:
        """无事件时 importance=0，使 padding 不产生梯度贡献。"""

        obs = make_observation(n_events=0)
        feats = encoder.features(obs)
        offset = _event_block_offset(encoder.config)
        for i in range(encoder.config.max_events):
            assert float(feats[offset + i * PER_EVENT_DIM]) == 0.0


class TestTimePhase:
    def test_time_phase_is_one_hot(self, encoder: PerceptionEncoder) -> None:
        offsets = _time_phase_offset(encoder.config)
        for phase in TIME_PHASES:
            feats = encoder.features(make_observation(phase=phase))
            block = feats[offsets : offsets + len(TIME_PHASES)]
            assert float(block.sum()) == 1.0
            assert float(block[TIME_PHASES.index(phase)]) == 1.0


class TestForward:
    def test_output_shape(self, encoder: PerceptionEncoder) -> None:
        out = encoder(make_observation())
        assert out.shape == (encoder.config.perception_dim,)

    def test_output_is_finite_and_bounded(self, encoder: PerceptionEncoder) -> None:
        out = encoder(make_observation())
        assert torch.isfinite(out).all()
        # 投影尾部是 Linear→LayerNorm→GELU，故输出不保证零均值；
        # 可保证的是 LayerNorm 那一段是归一化的（见下条）。
        assert out.abs().max() < 10.0

    def test_layernorm_segment_is_normalized(
        self, encoder: PerceptionEncoder
    ) -> None:
        """Linear→LayerNorm→GELU 的中间段必须归一化。

        GELU 在 LayerNorm **之后**，所以最终输出没有零均值性质。
        直接测中间段才对——这条测试原来的写法断言最终输出零均值，
        是把网络结构记反了。
        """

        feats = encoder.features(make_observation())
        projected = encoder.projection[0](feats)  # Linear
        normalized = encoder.projection[1](projected)  # LayerNorm
        assert abs(float(normalized.mean())) < 1e-4
        assert abs(float(normalized.std(unbiased=False)) - 1.0) < 1e-4

    def test_different_observations_give_different_vectors(
        self, encoder: PerceptionEncoder
    ) -> None:
        a = encoder(make_observation(phase="day"))
        b = encoder(make_observation(phase="night"))
        assert not torch.allclose(a, b)

    def test_gradients_flow(self, encoder: PerceptionEncoder) -> None:
        out = encoder(make_observation())
        out.sum().backward()
        grads = [p.grad for p in encoder.parameters() if p.grad is not None]
        assert grads, "没有任何参数收到梯度"
        assert all(torch.isfinite(g).all() for g in grads)


class TestConfigValidation:
    def test_custom_dims_change_raw_dim(self) -> None:
        cfg = PerceptionConfig(perception_dim=32, max_objects=4, max_events=2)
        assert cfg.max_objects == 4
        encoder = PerceptionEncoder(cfg)
        assert encoder.config.raw_dim == cfg.raw_dim
        assert encoder(make_observation()).shape == (32,)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"perception_dim": 0},
            {"max_objects": 0},
            {"max_events": 0},
            {"social_dim": -1},
        ],
    )
    def test_degenerate_config_is_rejected(self, kwargs: dict) -> None:
        """退化配置必须立刻失败，不能让对象段 / 事件段悄悄消失。"""

        with pytest.raises(ValueError):
            PerceptionConfig(**kwargs)


# ----------------------------------------------------------------------
#  偏移量计算（与 features() 的拼装顺序一一对应）
# ----------------------------------------------------------------------


def _object_block_offset(cfg: PerceptionConfig) -> int:
    return 3 + 2 * 2 + 4 + ENV_DIM + len(TIME_PHASES)


def _event_block_offset(cfg: PerceptionConfig) -> int:
    return _object_block_offset(cfg) + cfg.max_objects * (PER_OBJECT_DIM + 1) + cfg.social_dim


def _time_phase_offset(cfg: PerceptionConfig) -> int:
    return 3 + 2 * 2 + 4 + ENV_DIM
