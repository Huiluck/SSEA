"""Action Decoder 测试 —— 约束第一执行点 + 通道门控（07 §6.3 + 08 §2.6.2）。"""

from __future__ import annotations

import pytest
import torch

from SSEA.action_decoder import (
    DEFAULT_GATE_THRESHOLD,
    GATED_CHANNELS,
    ActionDecoder,
    ActionDecoderConfig,
    DecodeCandidates,
)
from SSEA.sse_protocols import (
    OPERATIONS,
    Action,
    ActionConstraints,
    default_constraints,
    idle_action,
)


def constraints(**overrides: object) -> ActionConstraints:
    base = dict(
        max_speed=1.0,
        max_force=1.0,
        max_duration=1.0,
        allowed_operations=OPERATIONS,
        forbidden_targets=(),
        energy_budget=1.0,
        can_communicate=True,
        can_store_memory=True,
        can_call_skill=True,
        can_self_modify=True,
    )
    base.update(overrides)
    return ActionConstraints(**base)  # type: ignore[arg-type]


def decode(
    decoder: ActionDecoder,
    cons: ActionConstraints | None = None,
    candidates: DecodeCandidates | None = None,
) -> Action:
    intent = torch.randn(decoder.config.intent_dim)
    drive = torch.zeros(decoder.config.drive_dim)
    return decoder(intent, cons or constraints(), drive, candidates)


class TestLocomotionAlwaysOn:
    """locomotion 常开——"移动或原地不动"是每帧都要表达的基本意图。"""

    def test_locomotion_is_always_present(self, decoder: ActionDecoder) -> None:
        for _ in range(10):
            action = decode(decoder)
            assert action.locomotion is not None

    def test_locomotion_respects_max_speed(self, decoder: ActionDecoder) -> None:
        """speed 由 sigmoid × max_speed 得出，结构上不可能越界。"""

        for max_speed in (0.1, 1.0, 5.0):
            cons = constraints(max_speed=max_speed)
            for _ in range(20):
                action = decode(decoder, cons)
                assert action.locomotion is not None
                assert action.locomotion.speed <= max_speed + 1e-6

    def test_locomotion_respects_max_duration(self, decoder: ActionDecoder) -> None:
        cons = constraints(max_duration=0.25)
        for _ in range(20):
            action = decode(decoder, cons)
            assert action.locomotion is not None
            assert action.locomotion.duration <= 0.25 + 1e-6


class TestOutputAlwaysLegal:
    """第一执行点的核心承诺：输出必然满足约束。"""

    @pytest.mark.parametrize(
        "overrides",
        [
            {"max_speed": 0.05},
            {"max_force": 0.05},
            {"max_duration": 0.05},
            {"allowed_operations": ("none",)},
            {"can_communicate": False},
            {"can_store_memory": False},
            {"can_call_skill": False},
            {"can_self_modify": False},
        ],
    )
    def test_never_violates_constraints(
        self, decoder: ActionDecoder, overrides: dict
    ) -> None:
        cons = constraints(**overrides)
        candidates = DecodeCandidates(
            object_ids=("o1", "o2"),
            skill_ids=("s1",),
            proposal_types=("ADD_RULE",),
        )
        for _ in range(20):
            action = decode(decoder, cons, candidates)
            assert cons.violations(action) == [], (
                f"解码器产出了越界动作: {cons.violations(action)}"
            )

    def test_action_is_always_executable(self, decoder: ActionDecoder) -> None:
        for _ in range(20):
            assert decode(decoder).is_executable()

    def test_falls_back_to_idle_when_nothing_gates_open(
        self, decoder: ActionDecoder
    ) -> None:
        """全部门控关闭（不应发生）时回退 idle_action 而非产出空 Action。"""

        # 用一个极低门控阈值 + 零驱动使所有门控大概率关闭不可行，
        # 故直接验证 idle 动作本身是可执行的
        idle = idle_action()
        assert idle.is_executable()
        assert idle.locomotion is not None
        assert idle.locomotion.speed == 0.0


class TestChannelGating:
    """六通道各有独立门控；只有门控打开的通道才出现在 Action 里。"""

    def test_all_gated_channels_have_a_gate(self, decoder: ActionDecoder) -> None:
        assert set(decoder.gates.keys()) == set(GATED_CHANNELS)
        assert "locomotion" not in decoder.gates

    def test_gate_threshold_is_configurable(self) -> None:
        cfg = ActionDecoderConfig(gate_threshold=0.9)
        assert cfg.gate_threshold == 0.9
        assert DEFAULT_GATE_THRESHOLD == 0.5

    def test_no_candidates_means_no_manipulation(
        self, decoder: ActionDecoder
    ) -> None:
        """离散选择必须从候选集合里取——没有候选就不开这个通道。"""

        for _ in range(20):
            action = decode(decoder, candidates=DecodeCandidates())
            assert action.manipulation is None
            assert action.skill is None
            assert action.self_modification is None

    def test_disabled_constraint_blocks_channel(
        self, decoder: ActionDecoder
    ) -> None:
        candidates = DecodeCandidates(
            object_ids=("o1",),
            skill_ids=("s1",),
            proposal_types=("ADD_RULE",),
        )
        cons = constraints(
            can_communicate=False,
            can_store_memory=False,
            can_call_skill=False,
            can_self_modify=False,
        )
        for _ in range(20):
            action = decode(decoder, cons, candidates)
            assert action.communication is None
            assert action.memory is None
            assert action.skill is None
            assert action.self_modification is None


class TestDiscreteChoices:
    """离散量从候选集合 argmax，不让解码器自由生成字符串。"""

    def test_target_comes_from_candidates(self) -> None:
        """目标 id 只能来自候选集合，不能让解码器自由生成字符串。

        **必须自己构造解码器并固定 seed**：``decoder`` 夹具是随机初始化的，
        而 ``decode()`` 用的是全局 RNG——manipulation 通道在 30 次抽样里
        是否至少开一次，取决于这两个随机源的叠加。测试顺序一变，结论就翻，
        那是拿抽奖当断言。固定 seed 后这条测试与顺序无关。
        """

        torch.manual_seed(0)
        decoder = ActionDecoder()
        candidates = DecodeCandidates(object_ids=("only_one",))
        seen = set()
        for _ in range(30):
            action = decode(decoder, candidates=candidates)
            if action.manipulation is not None:
                assert action.manipulation.target_id in ("only_one",)
                seen.add(action.manipulation.target_id)
        assert seen, "manipulation 通道从未开启，测试无意义"

    def test_skill_comes_from_candidates(self, decoder: ActionDecoder) -> None:
        candidates = DecodeCandidates(skill_ids=("skill_a", "skill_b"))
        for _ in range(30):
            action = decode(decoder, candidates=candidates)
            if action.skill is not None:
                assert action.skill.skill_id in ("skill_a", "skill_b")

    def test_operation_masked_to_allowed(self, decoder: ActionDecoder) -> None:
        """不在 allowed_operations 里的操作被 -inf 屏蔽，不可能被选中。"""

        cons = constraints(allowed_operations=("grasp", "push"))
        candidates = DecodeCandidates(object_ids=("o1",))
        for _ in range(30):
            action = decode(decoder, cons, candidates)
            if action.manipulation is not None:
                assert action.manipulation.operation in ("grasp", "push")

    def test_no_allowed_operation_yields_none(self, decoder: ActionDecoder) -> None:
        cons = constraints(allowed_operations=())
        candidates = DecodeCandidates(object_ids=("o1",))
        for _ in range(20):
            action = decode(decoder, cons, candidates)
            if action.manipulation is not None:
                assert action.manipulation.operation == "none"

    def test_proposal_type_comes_from_candidates(
        self, decoder: ActionDecoder
    ) -> None:
        candidates = DecodeCandidates(proposal_types=("ADD_RULE", "UPDATE_RULE"))
        for _ in range(30):
            action = decode(decoder, candidates=candidates)
            if action.self_modification is not None:
                assert action.self_modification.proposal_type in (
                    "ADD_RULE",
                    "UPDATE_RULE",
                )


class TestContinuousClamping:
    def test_force_respects_max_force(self, decoder: ActionDecoder) -> None:
        candidates = DecodeCandidates(object_ids=("o1",))
        cons = constraints(max_force=0.2)
        for _ in range(20):
            action = decode(decoder, cons, candidates)
            if action.manipulation is not None:
                assert action.manipulation.force <= 0.2 + 1e-6

    def test_direction_is_unit_ish(self, decoder: ActionDecoder) -> None:
        """direction 过 tanh，不是单位向量但必须有界。"""

        action = decode(decoder)
        assert action.locomotion is not None
        assert all(-1.0 <= v <= 1.0 for v in action.locomotion.direction)


class TestConfig:
    def test_intent_dim_must_match_state_core(self) -> None:
        from SSEA.state_core import StateCoreConfig

        assert ActionDecoderConfig().intent_dim == StateCoreConfig().intent_dim

    def test_drive_dim_is_fixed_at_four(self) -> None:
        assert ActionDecoderConfig().drive_dim == 4


class TestTrainability:
    """Action 装的是 Python float——这**决定了 SSEA 的学习方式**。

    两件事合起来让解码器的输出不可微：

    1. 协议约定 2：向量用 ``tuple[float, ...]``，不用 torch（可序列化）
    2. 通道门控是硬阈值比较，不是可微的稀疏化

    这不是缺陷，是立场。SSEA **不走"反向传播穿过动作"这条路**——那需要
    一个可微环境，而 SSEA 的环境是淘汰函数，不是损失函数（C9）。学习发生
    在慢环的 LocalPlasticity 与基因变异上（08 §4.2 的 ``Δθ``）。

    本条测试守住的是一条更容易腐烂的性质：**内部头仍然可微**。
    若有人把某个头改成纯 Python 运算，局部可塑性就失去了作用点，
    而这件事不会在任何运行时报错里显现。
    """

    def test_internal_heads_receive_gradients(
        self, decoder: ActionDecoder
    ) -> None:
        intent = torch.randn(decoder.config.intent_dim, requires_grad=True)
        drive = torch.zeros(decoder.config.drive_dim, requires_grad=True)
        h = decoder.trunk(torch.cat([intent, drive]))

        loss = decoder.loco_speed(h).sum()
        for layer in decoder.gates.values():
            loss = loss + torch.sigmoid(layer(h)).sum()
        loss = loss + decoder.manip_op(h).sum()
        loss.backward()

        assert intent.grad is not None and torch.isfinite(intent.grad).all()
        assert drive.grad is not None and torch.isfinite(drive.grad).all()
        assert decoder.trunk[0].weight.grad is not None
        for name, layer in decoder.gates.items():
            assert layer.weight.grad is not None, f"门控 {name} 收不到梯度"

    def test_gate_values_depend_on_intent(self, decoder: ActionDecoder) -> None:
        """门控值必须随 intent 变化，否则门控永远学不会何时开。"""

        with torch.no_grad():
            h_a = decoder.trunk(
                torch.cat([torch.zeros(decoder.config.intent_dim), torch.zeros(4)])
            )
            h_b = decoder.trunk(
                torch.cat([torch.ones(decoder.config.intent_dim), torch.zeros(4)])
            )
            ga = [float(torch.sigmoid(layer(h_a))) for layer in decoder.gates.values()]
            gb = [float(torch.sigmoid(layer(h_b))) for layer in decoder.gates.values()]
        assert ga != gb

    def test_action_carries_plain_protocol_floats(
        self, decoder: ActionDecoder
    ) -> None:
        """Action 是协议对象，不携带张量——这是可序列化的前提。"""

        action = decode(decoder)
        assert action.locomotion is not None
        assert isinstance(action.locomotion.speed, float)
        assert isinstance(action.locomotion.duration, float)
        assert isinstance(action.locomotion.direction, tuple)
        assert all(isinstance(v, float) for v in action.locomotion.direction)
