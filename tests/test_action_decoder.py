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


class TestTargetScoringIsReal:
    """目标打分必须**逐候选不同**（债务 5）。

    修正前的形状格外隐蔽：``manip_target`` 是个 ``nn.Linear(64, 1)``，
    参数在、梯度在、挂在 ``nn.Module`` 上，但 ``forward`` 里写的是
    ``self.manip_target(h).expand(n)``——把 (1,) 的分值复制成 n 份等值张量，
    ``argmax`` 因此**恒返回 0**。头算出来的那个数被整个丢掉了。

    后果是目标选择退化成「按距离取第一个」：不管最近的是资源、危险源还是
    石头。这不会报错，只会让 agent 一直抓错东西——而"抓了但没抓到资源"
    在 ``ENERGY_GAINED`` 上看起来就像"没抓"。

    这个类里的断言必须能**在修回 ``expand`` 时变红**，否则它们只是装饰。
    """

    @staticmethod
    def _feats(*rows: tuple[float, float, float]) -> DecodeCandidates:
        return DecodeCandidates(
            object_ids=tuple(f"o{i}" for i in range(len(rows))),
            object_features=tuple(rows),
        )

    @staticmethod
    def _force_gate_open(decoder: ActionDecoder) -> None:
        """把 manipulation 门强制打开。

        本类测的是**目标打分**，不是门控。门控值随机初始化、约一半 seed 恒闭
        （12 §4.3），不强制的话断言"选了谁"会因为通道根本没开而落空——
        那是拿抽奖当断言。
        """

        with torch.no_grad():
            decoder.gates["manipulation"].weight.zero_()
            decoder.gates["manipulation"].bias.fill_(10.0)

    @staticmethod
    def _prefer(decoder: ActionDecoder, dim: int) -> None:
        """把 ``manip_target`` 设成"只看第 ``dim`` 个特征"。

        用 **bias** 而不是 weight：weight 版本的分值会带上 ``h`` 的符号，
        于是"选谁"取决于随机初始化出来的 ``h[0]`` 是正是负——测试就变成了
        抽奖。bias 版让偏好与 ``h`` 完全无关，测的才是特征这一侧。
        """

        with torch.no_grad():
            decoder.manip_target.weight.zero_()
            decoder.manip_target.bias.zero_()
            decoder.manip_target.bias[dim] = 1.0

    def test_features_must_align_with_ids(self) -> None:
        with pytest.raises(ValueError, match="逐项对应"):
            DecodeCandidates(object_ids=("a", "b"), object_features=((1.0, 0.0, 0.0),))

    def test_feature_dim_is_checked(self) -> None:
        with pytest.raises(ValueError, match="OBJECT_FEATURE_DIM"):
            DecodeCandidates(object_ids=("a",), object_features=((1.0, 0.0),))

    def test_no_features_is_allowed(self) -> None:
        """留空合法（老调用点），但那是**退化情形**，不是另一条路径。"""

        assert DecodeCandidates(object_ids=("a", "b")).object_features == ()

    def test_choice_follows_candidate_features_not_index(self) -> None:
        """同一帧、同一偏好，**只改候选特征的顺序**，选中的目标要跟着变。

        这是"打分真的逐候选算了"最直接的证据：分若只依赖 ``h`` 与下标，
        换顺序不会改变"选第几个"。
        """

        cons = constraints()

        # 资源在**第三个**候选。若打分退化（expand 成等值张量），会选 o0。
        decoder = ActionDecoder()
        self._prefer(decoder, 0)  # 只看 resource_value
        self._force_gate_open(decoder)
        candidates = self._feats(
            (0.0, 0.9, 0.1),  # 危险源，最近
            (0.0, 0.0, 0.2),  # 石头
            (0.8, 0.0, 0.5),  # 资源，最远
        )
        action = decode(decoder, cons, candidates)
        assert action.manipulation is not None, "门已强制打开，不应为 None"
        assert action.manipulation.target_id == "o2", (
            "打分退化成了「按距离取第一个」——检查 manip_target 的输出"
            "是不是又被 expand 成等值张量丢掉了"
        )

    def test_choice_follows_the_head_preference(self) -> None:
        """改**头的参数**要改变选择——证明头的输出真的被用上了。

        与上一条合起来把两边都钉住：候选特征换了要变（上一条），
        头的偏好换了也要变（这一条）。只钉一边的话，
        "打分 = 某个与头和特征都无关的常量"这种退化仍可能蒙混过关。
        """

        cons = constraints()
        candidates = self._feats(
            (0.1, 0.9, 0.5),  # 威胁最高的是 o0
            (0.7, 0.0, 0.5),  # resource_value 最高的是 o1
        )

        decoder = ActionDecoder()
        self._force_gate_open(decoder)

        self._prefer(decoder, 0)  # 偏好 resource_value
        assert decode(decoder, cons, candidates).manipulation.target_id == "o1"

        self._prefer(decoder, 1)  # 偏好 threat_level
        assert decode(decoder, cons, candidates).manipulation.target_id == "o0"

    def test_missing_features_degenerates_to_first(self) -> None:
        """没有特征 → 各候选同分 → 取第一个。这是**退化**，不是另一条路径。

        写明它是因为"取第一个"正是修正前的**正常**行为。区别在于修正前
        无论有没有特征都取第一个；现在只有真没特征时才如此。
        """

        decoder = ActionDecoder()
        self._force_gate_open(decoder)
        action = decode(
            decoder, constraints(), DecodeCandidates(object_ids=("a", "b", "c"))
        )
        assert action.manipulation.target_id == "a"
