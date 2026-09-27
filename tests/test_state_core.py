"""State Core 测试 —— GRU 状态核心（07 §6.2 + 08 §2.5 补 d_t）。"""

from __future__ import annotations

import pytest
import torch

from SSEA.sse_protocols import BodyState, default_constraints
from SSEA.state_core import BODY_INPUT_DIM, DRIVE_DIM, StateCore, StateCoreConfig


def make_body(energy: float = 0.8) -> BodyState:
    return BodyState(
        energy=energy,
        damage=0.1,
        fatigue=0.2,
        position=(1.0, 2.0),
        orientation=(0.0, 1.0),
        action_constraints=default_constraints(),
        internal_state=(0.1, 0.2),
    )


def drive(deficit: float = 0.2) -> tuple[float, ...]:
    return (deficit, 0.1, 0.0, 0.0)


class TestShapes:
    def test_initial_hidden_shape(self, core: StateCore) -> None:
        h = core.initial_hidden()
        assert h.shape == (1, 1, core.config.hidden_dim)
        assert torch.count_nonzero(h) == 0

    def test_forward_shapes(self, core: StateCore) -> None:
        p = torch.zeros(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        h, intent = core(p, m, make_body(), drive(), core.initial_hidden())
        assert h.shape == (1, 1, core.config.hidden_dim)
        assert intent.shape == (core.config.intent_dim,)

    def test_intent_is_bounded(self, core: StateCore) -> None:
        """intent_head 结尾是 Tanh——intent_vector 必须落在 [-1,1]。"""

        p = torch.randn(core.config.perception_dim) * 10
        m = torch.randn(core.config.memory_dim) * 10
        _, intent = core(p, m, make_body(), drive(), core.initial_hidden())
        assert intent.abs().max() <= 1.0

    def test_encode_body_takes_three_survival_scalars(
        self, core: StateCore
    ) -> None:
        vec = core.encode_body(make_body(energy=0.42))
        assert vec.numel() == BODY_INPUT_DIM
        assert float(vec[0]) == pytest.approx(0.42)


class TestDriveInput:
    """08 §2.5：internal_drive 是新增输入，第一阶段实现前两项。"""

    def test_accepts_protocol_tuple(self, core: StateCore) -> None:
        """协议原产物是 tuple，模型边界负责张量化（见 tensorize.py）。"""

        p = torch.zeros(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        h, _ = core(p, m, make_body(), drive(), core.initial_hidden())
        assert torch.isfinite(h).all()

    def test_drive_changes_the_output(self, core: StateCore) -> None:
        p = torch.zeros(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        h0 = core.initial_hidden()
        _, a = core(p, m, make_body(), drive(0.0), h0)
        _, b = core(p, m, make_body(), drive(1.0), h0)
        assert not torch.allclose(a, b)

    def test_wrong_drive_dim_is_rejected(self, core: StateCore) -> None:
        """维度不符必须立刻报错，而不是让 GRU 内部给出难懂的报错。"""

        p = torch.zeros(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        with pytest.raises(ValueError, match="internal_drive 维度不符"):
            core(p, m, make_body(), (0.1, 0.2), core.initial_hidden())

    def test_wrong_perception_dim_is_rejected(self, core: StateCore) -> None:
        p = torch.zeros(3)
        m = torch.zeros(core.config.memory_dim)
        with pytest.raises(ValueError, match="输入维度不匹配"):
            core(p, m, make_body(), drive(), core.initial_hidden())


class TestRecurrence:
    """GRU 的全部意义：hidden_state 跨帧携带。"""

    def test_hidden_carries_across_frames(self, core: StateCore) -> None:
        h = core.initial_hidden()
        p = torch.randn(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)

        h1, _ = core(p, m, make_body(), drive(), h)
        h2_same, _ = core(p, m, make_body(), drive(), h)
        h2_carry, _ = core(p, m, make_body(), drive(), h1)

        # 同输入同 hidden → 同输出（无隐式随机性）
        assert torch.allclose(h1, h2_same)
        # 同输入不同 hidden → 不同输出（GRU 确实在递归）
        assert not torch.allclose(h1, h2_carry), (
            "hidden_state 未跨帧携带——GRU 退化成前馈网络"
        )

    def test_later_frames_depend_on_history(self, core: StateCore) -> None:
        h = core.initial_hidden()
        m = torch.zeros(core.config.memory_dim)
        p_a = torch.zeros(core.config.perception_dim)
        p_b = torch.ones(core.config.perception_dim)

        # 两条路径前两帧不同、第三帧相同
        ha = core(p_a, m, make_body(), drive(), h)[0]
        hb = core(p_b, m, make_body(), drive(), h)[0]
        _, final_a = core(p_a, m, make_body(), drive(), ha)
        _, final_b = core(p_b, m, make_body(), drive(), hb)
        assert not torch.allclose(final_a, final_b)

    def test_no_batch_dimension(self, core: StateCore) -> None:
        """第一阶段单智能体、逐帧推理，不加 batch 维。"""

        p = torch.zeros(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        h, intent = core(p, m, make_body(), drive(), core.initial_hidden())
        assert h.dim() == 3 and h.shape[0] == 1 and h.shape[1] == 1
        assert intent.dim() == 1


class TestConfig:
    def test_dims_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            StateCoreConfig(hidden_dim=0)
        with pytest.raises(ValueError):
            StateCoreConfig(intent_dim=-1)

    def test_perception_dim_must_match_encoder(self) -> None:
        """StateCore 与 PerceptionEncoder 的维度契约靠调用方保证，
        对不上时 StateCore 报错（见 test_wrong_perception_dim_is_rejected）。"""

        from SSEA.perception_encoder import PerceptionConfig

        assert StateCoreConfig().perception_dim == PerceptionConfig().perception_dim

    def test_param_count_is_reported(self, core: StateCore) -> None:
        n = core.param_count()
        assert n > 0
        assert n == sum(p.numel() for p in core.parameters())

    def test_param_count_scales_with_hidden_dim(self) -> None:
        small = StateCore(StateCoreConfig(hidden_dim=16)).param_count()
        large = StateCore(StateCoreConfig(hidden_dim=64)).param_count()
        assert large > small


class TestDeterminism:
    def test_eval_mode_is_deterministic(self, core: StateCore) -> None:
        core.eval()
        p = torch.randn(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        with torch.no_grad():
            _, a = core(p, m, make_body(), drive(), core.initial_hidden())
            _, b = core(p, m, make_body(), drive(), core.initial_hidden())
        assert torch.allclose(a, b)

    def test_gradients_reach_gru_and_head(self, core: StateCore) -> None:
        p = torch.randn(core.config.perception_dim)
        m = torch.zeros(core.config.memory_dim)
        _, intent = core(p, m, make_body(), drive(), core.initial_hidden())
        intent.sum().backward()
        assert core.gru.weight_ih_l0.grad is not None
        assert core.intent_head[0].weight.grad is not None
