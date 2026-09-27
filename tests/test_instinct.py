"""Instinct —— 本能先验：编解码、特征、以及「没有本能时逐位不变」。

对应 [docs/14](../docs/14-overview-and-roadmap.md) §6.3.2 的推论：

    真约束不是「解码器不记得抓」，是**它不会转向**。
    而趋近行为落在 C8「给基因先验，不给知识语料」这个位置上——它是本能，
    不是知识。所以最符合 SSEA 的形态是把它做成 ``instinct_adapters`` 的
    第一个消费者，而不是手工调一个更好的默认解码器。

本文件的重心是 **``TestControlArmFidelity``**：没有本能时必须与改动前
**逐位相同**。这是整套对照组的地基——如果"本能关闭"这一臂走的不是同一段
代码，那两臂之差就不是本能造成的。写成"近似相同"或"数值接近"都不够：
只要那一项存在，它就在改数值。

v2 之后有两个作用点（locomotion / manipulation），于是"没有本能"这句话
要拆成**三**种情形分别钉住：没有 adapter、特征全零、**投影恰好为零**。
第三种最阴——它长得像"装了本能但没效果"，真相是那个加法根本不该发生。
"""

from __future__ import annotations

import math
import struct
from dataclasses import replace

import pytest
import torch

from SSEA.action_decoder import DEFAULT_GATE_THRESHOLD, ActionDecoder, DecodeCandidates
from SSEA.environment import Environment
from SSEA.fast_loop import FastLoop, FastLoopConfig
from SSEA.instinct import (
    DIRECTION_DIM,
    FORMAT_VERSION,
    INSTINCT_PRESETS,
    LOCOMOTION_FEATURES_DIM,
    MAGIC,
    MANIP_GRASP_ROW,
    MANIP_GATE_ROW,
    MANIPULATION_FEATURES_DIM,
    MANIPULATION_ROWS,
    TARGET_LOCOMOTION,
    TARGET_MANIPULATION,
    Instinct,
    decode_instinct,
    decode_instinct_set,
    encode_instinct,
    locomotion_bias,
    locomotion_features,
    manipulation_bias,
    manipulation_features,
    preset_blob,
)
from SSEA.sse_protocols import OPERATIONS, BodyState, default_constraints
from SSEA.sse_protocols.object_vector import ObjectVector
from SSEA.sse_protocols.observation import Observation
from tests.conftest import make_context

LOCO_WEIGHTS = torch.tensor([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])
MANIP_WEIGHTS = torch.tensor([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])

#: 头部字节数：``version:u8 | target:u8 | rows:u16 | cols:u16``。
HEADER_TAIL = struct.calcsize("<BBHH")


def seeded(name: str) -> tuple:
    """``preset_blob`` → ``decode_instinct_set`` 的返回形状（一个元组）。"""
    return decode_instinct_set({"w": preset_blob(name)})


def projected_bias(preset: str, features: torch.Tensor | None = None) -> torch.Tensor:
    """一份 locomotion 先验投影到方向空间后的偏置，形状 ``(DIRECTION_DIM,)``。

    这正是 ``ActionDecoder.forward`` 的 ``loco_instinct`` 参数**要的东西**
    ——它收的是投影结果，不是原始权重矩阵。测试走真实投影路径而不是手搓一个
    形状对的张量：手搓的那一份与生产路径会漂移，而漂移的表现是
    "测试过了、快环没转"。
    """

    f = torch.tensor([1.0, 0.0, 0.0, 0.0]) if features is None else features
    bias = locomotion_bias(seeded(preset), f)
    assert bias is not None
    return bias


def two_candidates() -> DecodeCandidates:
    """两个候选：o0 危险且近、o1 是资源且远。给操纵链的测试当固定输入。"""

    return DecodeCandidates(
        object_ids=("o0", "o1"),
        object_features=((0.0, 0.9, 0.1), (0.8, 0.0, 0.5)),
    )


def obj(
    object_id: str,
    *,
    distance: float = 1.0,
    direction: tuple[float, ...] = (1.0, 0.0),
    value: float = 0.0,
    threat: float = 0.0,
) -> ObjectVector:
    return ObjectVector(
        object_id=object_id,
        category_id=1,
        distance=distance,
        direction=direction,
        velocity=(0.0, 0.0),
        resource_value=value,
        threat_level=threat,
        affordance=(),
    )


def observation(*objects: ObjectVector) -> Observation:
    from SSEA.sse_protocols import EnvironmentSummary

    return Observation(
        time=0.0,
        body=BodyState(
            energy=1.0,
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
        objects=objects,
    )


# ----------------------------------------------------------------------
#  编解码
# ----------------------------------------------------------------------


class TestCodec:
    def test_roundtrip_is_exact(self):
        blob = encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION)
        back = decode_instinct(blob)
        assert back is not None
        assert back.target == TARGET_LOCOMOTION
        assert torch.equal(back.weights, LOCO_WEIGHTS.to(torch.float32))

    def test_roundtrip_carries_the_manipulation_target(self):
        """作用点是**内容**的一部分：同一张矩阵，声明不同就是不同的本能。"""

        blob = encode_instinct(MANIP_WEIGHTS, target=TARGET_MANIPULATION)
        back = decode_instinct(blob)
        assert back is not None
        assert back.target == TARGET_MANIPULATION
        assert torch.equal(back.weights, MANIP_WEIGHTS.to(torch.float32))

    def test_header_layout(self):
        """头部 ``MAGIC | version:u8 | target:u8 | rows:u16 | cols:u16``，小端。"""

        blob = encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION)
        assert blob[: len(MAGIC)] == MAGIC
        version, target, rows, cols = struct.unpack(
            "<BBHH", blob[len(MAGIC) : len(MAGIC) + HEADER_TAIL]
        )
        assert (version, target, rows, cols) == (
            FORMAT_VERSION,
            TARGET_LOCOMOTION,
            DIRECTION_DIM,
            LOCOMOTION_FEATURES_DIM,
        )
        assert len(blob) == len(MAGIC) + HEADER_TAIL + DIRECTION_DIM * 4 * 4

    def test_target_is_required(self):
        """**没有默认作用点**——默认为 locomotion 会让操纵先验被当成方向偏置。

        那种错不报错：形状合法、数值无害，只是语义全错，现象是"本能没效果"。
        """

        with pytest.raises(TypeError):
            encode_instinct(LOCO_WEIGHTS)  # type: ignore[call-arg]

    def test_unknown_target_is_rejected_at_encode_time(self):
        with pytest.raises(ValueError, match="未知的本能作用点"):
            encode_instinct(LOCO_WEIGHTS, target=77)

    def test_non_2d_is_rejected_at_encode_time(self):
        """编码侧可以抛——它不在快环的每帧路径上。解码侧不行。"""

        with pytest.raises(ValueError, match="二维"):
            encode_instinct(torch.zeros(4), target=TARGET_LOCOMOTION)

    def test_shape_must_match_the_declared_target(self):
        """形状对不上就在编码时拒——别指望解码侧兜住。"""

        with pytest.raises(ValueError, match="必须是 2×4"):
            encode_instinct(torch.zeros(3, 7), target=TARGET_LOCOMOTION)

    def test_gain_scales_the_weights(self):
        plain = decode_instinct(preset_blob("approach", gain=1.0))
        doubled = decode_instinct(preset_blob("approach", gain=2.0))
        assert plain is not None and doubled is not None
        assert torch.allclose(doubled.weights, plain.weights * 2.0)

    def test_preset_is_approach_toward_first_feature(self):
        """``approach`` 的语义就是「沿资源方向推」——它的第一行取 x 分量，第二行取 y。"""

        preset = INSTINCT_PRESETS["approach"]
        assert preset.target == TARGET_LOCOMOTION
        assert torch.equal(
            torch.tensor(preset.weights), torch.tensor([[1.0, 0, 0, 0], [0, 1.0, 0, 0]])
        )

    def test_forage_adds_avoidance_on_the_negated_hazard_slots(self):
        preset = INSTINCT_PRESETS["forage"]
        assert preset.target == TARGET_LOCOMOTION
        assert torch.equal(
            torch.tensor(preset.weights),
            torch.tensor([[1.0, 0, 1.0, 0], [0, 1.0, 0, 1.0]]),
        )

    def test_grasp_preset_pushes_gate_and_op_with_no_hazard_terms(self):
        """``grasp_in_reach`` 两行都只吃资源两列，危险两列的系数是 **0**。

        那个 0 是一个**选择**，不是遗漏：现有测量只说明「卡在操纵链」，
        没有说明危险该不该压低抓取意愿。这条测试把"我们决定不编那个权重"
        钉成明文，免得日后有人把它当成没写完。
        """

        preset = INSTINCT_PRESETS["grasp_in_reach"]
        assert preset.target == TARGET_MANIPULATION
        assert torch.equal(
            torch.tensor(preset.weights),
            torch.tensor([[1.0, 1.0, 0.0, 0.0], [1.0, 1.0, 0.0, 0.0]]),
        )

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="未知的本能先验"):
            preset_blob("nope")


class TestDecodeIsFailClosedAndNeverRaises:
    """解码在快环每帧路径上：**崩溃 = episode 中断 = 真实死亡**，代价不对等。

    所以下面每一条都必须返回 ``None`` 而不是抛。写成
    ``pytest.raises`` 是**错的**——那等于承认它会抛。
    """

    LOCO = MAGIC + struct.pack(
        "<BBHH", FORMAT_VERSION, TARGET_LOCOMOTION, DIRECTION_DIM, LOCOMOTION_FEATURES_DIM
    )
    MANIP = MAGIC + struct.pack(
        "<BBHH",
        FORMAT_VERSION,
        TARGET_MANIPULATION,
        MANIPULATION_ROWS,
        MANIPULATION_FEATURES_DIM,
    )

    @pytest.mark.parametrize(
        "blob",
        [
            None,
            b"",
            b"x",
            "not-bytes",
            12345,
            b"NOTMAGIC" + b"\x00" * 20,
            MAGIC,  # 只有魔数，没有头
            LOCO,  # 有头没体
            LOCO + b"\x00" * 5,  # 体太短
            LOCO + b"\x00" * 40,  # 体太长
            MAGIC + struct.pack("<BBHH", 99, TARGET_LOCOMOTION, 2, 4) + b"\x00" * 32,
            # 版本不认识 ↑
            MAGIC + struct.pack("<BBHH", FORMAT_VERSION, 77, 2, 4) + b"\x00" * 32,
            # 作用点不认识 ↑
            MAGIC + struct.pack("<BBHH", FORMAT_VERSION, TARGET_LOCOMOTION, 3, 7)
            + b"\x00" * 84,
            # 形状与**所声明的作用点**对不上 ↑
            MAGIC + struct.pack("<BBHH", FORMAT_VERSION, TARGET_MANIPULATION, 3, 7)
            + b"\x00" * 84,
            # 换个作用点，同一个错形状仍然要被拒 ↑
        ],
    )
    def test_returns_none_for_every_bad_input(self, blob):
        assert decode_instinct(blob) is None

    @pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
    def test_non_finite_weights_are_not_decodable(self, bad):
        """含 ``inf`` / ``nan`` 的权重按"读不懂"处理——它不是另一份合法先验。

        后果不是"效果差一点"，是**先验顶掉约束**：操纵链按约束把越界的 op
        屏蔽成 ``-inf``，而 ``-inf + inf = nan``，``nan`` 在比较里胜过 ``-inf``
        ——于是 ``argmax`` 可能落在那个本该被屏蔽的 op 上。

        编码侧拒不了它（``inf`` 是个合法的 float32，原样写得进字节），所以
        这道检查只能在解码侧，而门调的正是这个解码器。
        """

        body = struct.pack(
            "<8f", 1.0, 1.0, 0.0, 0.0, bad, 1.0, 0.0, 0.0
        )
        blob = (
            MAGIC
            + struct.pack(
                "<BBHH",
                FORMAT_VERSION,
                TARGET_MANIPULATION,
                MANIPULATION_ROWS,
                MANIPULATION_FEATURES_DIM,
            )
            + body
        )
        assert decode_instinct(blob) is None

    def test_a_bad_blob_does_not_take_down_the_good_ones(self):
        """一份坏的被丢弃，其余照常可用。``adapters`` 是个映射，不是单值。"""

        good = encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION)
        decoded = decode_instinct_set({"good": good, "bad": b"garbage"})
        assert len(decoded) == 1
        assert torch.equal(decoded[0].weights, LOCO_WEIGHTS.to(torch.float32))

    def test_names_do_not_appear_in_the_result(self):
        """键名不进入返回值——名字是标签，解码只看内容。

        带出来就会诱导下游按名字分支，而"名字选作用点"正是 v2 要杜绝的事
        （见 ``SSEA/instinct.py`` 的模块 docstring）。
        """

        blob = preset_blob("grasp_in_reach")
        assert decode_instinct_set({"totally-made-up-name": blob})[0].target == (
            TARGET_MANIPULATION
        )

    def test_empty_and_none_maps(self):
        assert decode_instinct_set({}) == ()
        assert decode_instinct_set(None) == ()


# ----------------------------------------------------------------------
#  特征
# ----------------------------------------------------------------------


class TestLocomotionFeatures:
    def test_nearest_resource_goes_in_the_first_slots(self):
        f = locomotion_features(
            observation(
                obj("res_far", distance=5.0, direction=(1.0, 0.0), value=0.5),
                obj("res_near", distance=1.2, direction=(0.0, -1.0), value=0.5),
            )
        )
        assert torch.allclose(f[:2], torch.tensor([0.0, -1.0]))

    def test_worst_threat_goes_in_the_last_slots_negated(self):
        """取**威胁最高**的那个，方向**取负**——负号就是「回避」的全部语义。"""

        f = locomotion_features(
            observation(
                obj("haz_mild", distance=1.0, direction=(1.0, 0.0), threat=0.3),
                obj("haz_worst", distance=3.0, direction=(0.6, 0.8), threat=0.95),
            )
        )
        assert torch.allclose(f[2:], torch.tensor([-0.6, -0.8]))

    def test_missing_side_is_zero(self):
        only_resource = locomotion_features(
            observation(obj("res", distance=1.0, direction=(1.0, 0.0), value=0.5))
        )
        assert torch.allclose(only_resource, torch.tensor([1.0, 0.0, 0.0, 0.0]))

        only_hazard = locomotion_features(
            observation(obj("haz", distance=1.0, direction=(0.0, 1.0), threat=0.9))
        )
        assert torch.allclose(only_hazard, torch.tensor([0.0, 0.0, 0.0, -1.0]))

    def test_nothing_visible_is_all_zero(self):
        """全零特征 → 偏置恒为 0 → 行为与没有本能时相同。这是"诚实的空"。"""

        f = locomotion_features(observation(obj("prop", distance=1.0)))
        assert float(f.abs().sum()) == 0.0

    def test_direction_shorter_than_world_is_zero_padded(self):
        """``direction`` 是变长的（协议不绑定维度），短了就补零，不炸。"""

        f = locomotion_features(
            observation(obj("res", distance=1.0, direction=(1.0,), value=0.5))
        )
        assert torch.allclose(f[:2], torch.tensor([1.0, 0.0]))

    def test_direction_longer_than_world_is_truncated(self):
        f = locomotion_features(
            observation(obj("res", distance=1.0, direction=(1.0, 0.0, 9.0), value=0.5))
        )
        assert torch.allclose(f[:2], torch.tensor([1.0, 0.0]))


class TestManipulationFeatures:
    """操纵特征回答的不是「往哪走」，是「现在该不该动手」——所以是标量不是方向。"""

    def test_layout_is_closeness_then_value(self):
        f = manipulation_features(
            observation(
                obj("res", distance=1.0, value=0.8),
                obj("haz", distance=3.0, threat=0.5),
            )
        )
        assert f[0] == pytest.approx(1.0 / 2.0)  # 1/(1+1)
        assert f[1] == pytest.approx(0.8)
        assert f[2] == pytest.approx(-1.0 / 4.0)  # 1/(1+3)，取负
        assert f[3] == pytest.approx(-0.5)

    def test_closeness_is_monotone_and_bounded(self):
        """贴近度**不含任何需要编出来的尺度**：没有 reach 阈值，只有 1/(1+d)。

        d=0 → 1；d=1（``reach``）→ 0.5；d=6（``perception_radius``）→ 1/7。
        边界由行为自己长出来，不由一个没人测量过的旋钮定。
        """

        far = manipulation_features(observation(obj("res", distance=6.0, value=0.5)))
        near = manipulation_features(observation(obj("res", distance=1.0, value=0.5)))
        closest = manipulation_features(observation(obj("res", distance=0.0, value=0.5)))
        assert 0.0 < float(far[0]) < float(near[0]) < float(closest[0]) == 1.0

    def test_negative_distance_does_not_blow_up(self):
        """``_closeness`` 自己兜住负距离：返回 inf 会一路污染到 logit 上，且不报错。

        直接测这个辅助函数而不是构造一个负距离的 ``ObjectVector``——后者在
        ``ObjectVector.__post_init__`` 就被拒了（协议层已经守住了）。
        这条测的是**第二道防线**：本模块对观测一律用 ``getattr`` 取值
        （``direction`` 截断补零、字段缺失补 0），所以它面对的未必是真正的
        ``ObjectVector``，而 1/(1+(-1)) 是个除以零。
        """

        from SSEA.instinct import _closeness

        assert math.isfinite(_closeness(-1.0))
        assert _closeness(-5.0) == 1.0

    def test_missing_side_is_zero(self):
        only_hazard = manipulation_features(
            observation(obj("haz", distance=1.0, threat=0.9))
        )
        assert torch.allclose(only_hazard, torch.tensor([0.0, 0.0, -0.5, -0.9]))

        nothing = manipulation_features(observation(obj("prop", distance=1.0)))
        assert float(nothing.abs().sum()) == 0.0

    def test_it_is_a_different_vector_from_locomotion(self):
        """同一个观测，两个作用点的特征**不是**同一个东西。

        若哪天有人"顺手合并"这两个函数，这条会红——而合并的代价是其中一边
        拿到自己用不上的字段（方向 vs 条件），并且它以"简化"的名义发生。
        """

        obs = observation(
            obj("res", distance=2.0, direction=(0.0, 1.0), value=0.7),
            obj("haz", distance=1.0, direction=(1.0, 0.0), threat=0.4),
        )
        loco = locomotion_features(obs)
        manip = manipulation_features(obs)
        assert loco.shape == manip.shape  # 今天恰好同维
        assert not torch.allclose(loco, manip)


class TestBias:
    def test_no_instinct_is_none(self):
        assert locomotion_bias((), torch.ones(LOCOMOTION_FEATURES_DIM)) is None
        assert manipulation_bias((), torch.ones(MANIPULATION_FEATURES_DIM)) is None

    def test_zero_features_is_none_not_zero(self):
        """特征全零时返回 ``None``——"本能无从施加"与"施加了零"不是一回事。

        数值上两者相同，但 ``None`` 让调用方**走原路径**（根本没有那一项），
        而不是做一个加法。这是对照组逐位保真的实现方式。
        """

        assert (
            locomotion_bias(seeded("approach"), torch.zeros(LOCOMOTION_FEATURES_DIM))
            is None
        )

    def test_a_zero_projection_is_none_too(self):
        """**投影恰好为零**也返回 ``None``——这是 v2 新增的第三种情形。

        ``x + 0.0`` 对 ``x = -0.0`` 并不逐位相同（结果是 ``+0.0``）。
        内置 ``grasp_in_reach`` 给危险两列的系数是 0，所以"只看见危险源"
        时投影正好是一行 0；留着那一项就等于在对照组里留了一个改数值的加法。
        """

        instincts = seeded("grasp_in_reach")
        f = manipulation_features(observation(obj("haz", distance=1.0, threat=0.9)))
        assert float(f.abs().sum()) > 0.0, "特征本身不是全零，否则测不到这一条"
        assert manipulation_bias(instincts, f) is None

    def test_multiple_instincts_add(self):
        f = torch.tensor([1.0, 0.0, 0.0, 0.0])
        bone = decode_instinct(encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION))
        assert bone is not None
        one = locomotion_bias((bone,), f)
        two = locomotion_bias((bone, bone), f)
        assert one is not None and two is not None
        assert torch.allclose(two, one * 2)

    def test_instincts_of_the_other_target_are_ignored(self):
        """locomotion 的投影拿不到 manipulation 的本能，反之亦然。

        这是 v2 的**核心断言**：作用点写进 blob 里，于是"投错地方"在结构上
        不可能——两份本能在同一个元组里，各自只被自己那一侧看见。
        """

        loco = decode_instinct(encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION))
        manip = decode_instinct(
            encode_instinct(MANIP_WEIGHTS, target=TARGET_MANIPULATION)
        )
        assert loco is not None and manip is not None
        f = torch.tensor([1.0, 0.0, 0.0, 0.0])
        assert torch.allclose(locomotion_bias((loco, manip), f), torch.tensor([1.0, 0.0]))
        assert torch.allclose(
            manipulation_bias((loco, manip), f), torch.tensor([1.0, 0.0])
        )
        assert locomotion_bias((manip,), f) is None

    def test_wrong_shape_is_skipped_not_fatal(self):
        """形状对不上：单份坏的被跳过，不拖垮其余的。解码已按作用点保证过形状，
        这里是防御——本模块的纪律是"读不懂就当没有"，不是"抛"。"""

        good = decode_instinct(encode_instinct(LOCO_WEIGHTS, target=TARGET_LOCOMOTION))
        assert good is not None
        broken = Instinct(target=TARGET_LOCOMOTION, weights=torch.zeros(3, 7))
        f = torch.tensor([1.0, 0.0, 0.0, 0.0])
        assert torch.allclose(
            locomotion_bias((broken, good), f), torch.tensor([1.0, 0.0])
        )


# ----------------------------------------------------------------------
#  对照组保真 —— 本文件的重心
# ----------------------------------------------------------------------


def _directions(context) -> list[object]:
    """跑一条 40 帧的 episode，收集每帧解出来的方向。"""

    torch.manual_seed(11)
    loop = FastLoop(
        Environment(seed=11),
        context,
        config=FastLoopConfig(max_frames=40, min_sleep_frames=4),
    )
    while loop.alive and len(loop.trace()) < 40:
        loop.step()
    return [r.executed_action.locomotion.direction for r in loop.trace()]


class TestControlArmFidelity:
    def test_loco_instinct_none_reproduces_the_original_expression_exactly(self):
        """``loco_instinct=None`` 时方向必须**逐位等于** ``tanh(loco_dir(h))``。

        这是"关本能"那一臂不是另一个实现的证明。断言用 ``==`` 不用
        ``approx``：只要本能项存在，它就在改数值，哪怕改得很小。
        """

        torch.manual_seed(3)
        model = ActionDecoder()
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        constraints = default_constraints()

        action = model(intent, constraints, drive, None, None, None)

        # 手工重算改动前的表达式：trunk → loco_dir → tanh。
        h = model.trunk(torch.cat([intent, drive]))
        expected = torch.tanh(model.loco_dir(h)).tolist()
        assert tuple(action.locomotion.direction) == tuple(expected)

    def test_manip_instinct_none_reproduces_the_original_gate_and_op(self):
        """``manip_instinct=None`` 时操纵门与 op 必须**逐位等于**改动前。

        与上一条对称。门这一侧尤其要钉：偏置是加在 logit 上的，若有人把
        它挪到 sigmoid 之后（或干脆改成乘法），``None`` 这一路看起来"没变"，
        而装上本能的那一路会静默失效。
        """

        torch.manual_seed(4)
        model = ActionDecoder()
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        constraints = default_constraints()
        candidates = two_candidates()

        action = model(intent, constraints, drive, candidates, None, None, None)

        # 手工重算改动前的表达式：sigmoid(门 logit) 与 argmax(op logit)。
        h = model.trunk(torch.cat([intent, drive]))
        gate = float(torch.sigmoid(model.gates["manipulation"](h)))
        expected_op = OPERATIONS[int(torch.argmax(model.manip_op(h)))]

        # 门开不开由随机初始化决定（约一半 seed 恒闭，见 12 §4.3），所以
        # 两条分支都要断言，而不是"假定它开着"——假定会让这条测试在
        # 换个 seed 之后从"通过"直接变成"报错说前提不成立"。
        if gate < DEFAULT_GATE_THRESHOLD:
            assert action.manipulation is None
        else:
            assert action.manipulation is not None
            assert action.manipulation.operation == expected_op

    def test_empty_adapters_make_the_loop_behave_identically(self):
        """快照里 ``adapters`` 为空时，整条 episode 与没有本能的世界逐位相同。"""

        assert _directions(make_context()) == _directions(make_context(adapters={}))

    def test_undecodable_adapter_is_silently_ignored(self):
        """一份读不懂的 adapter 不该改变行为，也不该让 episode 崩。

        它正常路径上进不了门（``_check_adapters`` 会拒），但**初始结构
        可以由调用方直接塞**，而"能进门"不该是快环不崩的前提——
        快环崩了就是真实死亡，而它面对的是一份静态字节。
        """

        baseline = _directions(make_context())
        garbage = _directions(make_context(adapters={"broken": b"not-a-blob"}))
        assert baseline == garbage
        assert len(baseline) > 0

    def test_a_blob_of_the_wrong_target_does_not_reach_the_direction(self):
        """把一份**操纵**本能塞进只该有方向本能的世界：方向那一侧收不到它。

        这是作用点写进 blob 之后最该钉的一条：若解码侧按形状或按名字猜
        作用点，这份 2×4 的矩阵会被当成方向偏置投影出一个 (2,) 的偏置，
        于是"塞错东西"变成一个静默的、看起来合理的转向。

        **测的是分配那一刻，不是整条 episode 的方向序列。** 操纵本能会让
        操纵门开得不一样，于是执行的动作不一样、世界跟着不一样——后面所有帧
        的方向本来就会分叉。拿整条序列做断言等于在断言"操纵本能对世界没有
        任何影响"，那既不真，也把真正要钉的东西（两个作用点在**入口**就分开）
        埋掉了。所以在快环分出两个偏置的那道缝上断言。
        """

        torch.manual_seed(41)
        loop = FastLoop(
            Environment(seed=41),
            make_context(adapters={"oops": preset_blob("grasp_in_reach")}),
            config=FastLoopConfig(max_frames=5, min_sleep_frames=2),
        )
        loco, manip = loop._instincts(loop.observation)
        assert loco is None, "操纵本能被投影进了方向路径——作用点没有隔离"
        assert manip is not None, "操纵本能本该作用在操纵链上，这条测试失去了前提"


# ----------------------------------------------------------------------
#  消费者真的接上了
# ----------------------------------------------------------------------


class TestInstinctActuallySteers:
    def test_direction_turns_toward_the_nearest_resource(self):
        """装上趋近本能后，方向与「指向最近资源」的夹角应当很小。

        这是 ② 的核心断言：``adapters`` 从"有完整写入路径但无人读"
        变成"有一个真的会改行为的消费者"。

        注意帧序：``StepRecord.observation`` 是**动作之后**的观测
        （``obs_next``），而这一帧的方向是拿**动作之前**的观测解出来的。
        所以要比的是 ``loop.observation``（步进前）而不是记录里的那一个——
        差一帧就是把两个时刻的东西对在一起，而它照样会"通过"。
        """

        ctx = make_context(adapters={"forage": preset_blob("approach")})
        torch.manual_seed(5)
        loop = FastLoop(
            Environment(seed=5),
            ctx,
            config=FastLoopConfig(max_frames=30, min_sleep_frames=4),
        )

        obs = loop.observation
        record = loop.step()

        resources = [o for o in obs.objects if o.resource_value > 0]
        assert resources, "这个 seed 的视野里应当有资源"
        nearest = min(resources, key=lambda o: o.distance)

        d = record.executed_action.locomotion.direction
        norm = math.hypot(*d)
        assert norm > 0, "方向不能是零向量"
        cos = (d[0] * nearest.direction[0] + d[1] * nearest.direction[1]) / norm
        assert cos > 0.9, f"方向没指向最近资源：cos={cos:.3f}"

    def test_without_instinct_the_direction_does_not_track_the_resource(self):
        """对照组：没有本能时方向**不**跟着资源走。

        只断言"本能臂指向资源"是不够的——得证明**对照臂不指向**，
        否则那个余弦值可能只是"随机方向本来就这样"。两个数都算出来，
        因为**一个没有对照的余弦值什么也说明不了**。
        """

        def mean_cos(context) -> float:
            values = []
            for seed in range(6):
                torch.manual_seed(seed)
                loop = FastLoop(
                    Environment(seed=seed),
                    context,
                    config=FastLoopConfig(max_frames=25, min_sleep_frames=4),
                )
                while loop.alive and len(loop.trace()) < 25:
                    obs = loop.observation  # 步进前——解出这一帧方向的那个观测
                    record = loop.step()
                    res = [o for o in obs.objects if o.resource_value > 0]
                    if not res:
                        continue
                    near = min(res, key=lambda o: o.distance)
                    d = record.executed_action.locomotion.direction
                    n = math.hypot(*d)
                    if n == 0:
                        continue
                    values.append(
                        (d[0] * near.direction[0] + d[1] * near.direction[1]) / n
                    )
            assert values, "一条样本都没有"
            return sum(values) / len(values)

        control = mean_cos(make_context())
        instinct = mean_cos(make_context(adapters={"forage": preset_blob("approach")}))

        assert instinct > control + 0.3, (
            f"本能没有把方向拉开：对照 {control:.3f} vs 本能 {instinct:.3f}"
        )

    def test_bias_is_added_before_tanh_not_substituted(self):
        """方向恰好等于 ``tanh(loco_dir(h) + bias)`` —— 加法、且在 tanh 之前。

        这是**结构性**断言，不是数值接近：它同时钉住"加不是替换"
        （否则 ``tanh(loco_dir(h))`` 会消失）与"在 tanh 之前"
        （``tanh(a) + b`` 是另一个函数）。两条里任何一条被改成别的写法，
        这个等式就不再成立。

        ``loco_dir`` 本身是否可微由 ``test_action_decoder.py::TestTrainability``
        守着——那是模块级性质，不需要在这里重测一遍；这里测的是**本能的接入
        方式没有破坏它**：加法让方向头留在同一个张量表达式里。
        """

        torch.manual_seed(23)
        model = ActionDecoder()
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        bias = projected_bias("approach")

        # 抓 loco_dir 的真实输出，再用它重算期望值。
        captured: list[torch.Tensor] = []
        handle = model.loco_dir.register_forward_hook(
            lambda mod, inp, out: captured.append(out.detach().clone())
        )
        action = model(intent, default_constraints(), drive, None, None, bias)
        handle.remove()

        assert len(captured) == 1
        expected = torch.tanh(captured[0] + bias).tolist()
        assert tuple(action.locomotion.direction) == tuple(expected)

    def test_the_bias_is_actually_applied(self):
        """方向确实被本能推开：同一份权重下，有无本能的方向不同。"""

        torch.manual_seed(17)
        model = ActionDecoder()
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        constraints = default_constraints()

        plain = model(intent, constraints, drive, None, None, None)
        biased = model(
            intent, constraints, drive, None, None, projected_bias("approach")
        )
        assert tuple(plain.locomotion.direction) != tuple(biased.locomotion.direction)


class TestManipulationInstinctActuallySteers:
    """操纵本能必须真的推得动**门**与**op**——两边各钉住。

    这一类的存在理由与 locomotion 那边同源，但要紧得多：门是硬阈值比较，
    ``sigmoid(logit + bias) >= 0.5``。偏置若被加在 sigmoid **之后**，
    它会先去和 ``>=`` 右边那个 0.5 比较，效果五花八门且不报错。
    所以下面两条都用"同一个解码器、同一帧，只换本能"的形式，
    逼出一个**方向明确**的翻转。
    """

    @staticmethod
    def _pin_gate(decoder: ActionDecoder, logit: float) -> None:
        """把操纵门的 logit 钉成一个已知常数（与 h 无关）。"""

        with torch.no_grad():
            decoder.gates["manipulation"].weight.zero_()
            decoder.gates["manipulation"].bias.fill_(logit)

    @staticmethod
    def _pin_op(decoder: ActionDecoder, op: str, strength: float) -> None:
        with torch.no_grad():
            decoder.manip_op.weight.zero_()
            decoder.manip_op.bias.zero_()
            decoder.manip_op.bias[OPERATIONS.index(op)] = strength

    @staticmethod
    def _bias(gate: float, grasp: float) -> torch.Tensor:
        from SSEA.instinct import MANIPULATION_ROWS

        row = torch.zeros(MANIPULATION_ROWS)
        row[MANIP_GATE_ROW] = gate
        row[MANIP_GRASP_ROW] = grasp
        return row

    def test_the_gate_bias_can_open_a_shut_gate(self):
        """门本来不开（logit = −0.6 → 0.354 < 0.5），本能把它推开。"""

        torch.manual_seed(31)
        model = ActionDecoder()
        self._pin_gate(model, -0.6)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = default_constraints()

        shut = model(intent, cons, drive, two_candidates(), None, None)
        assert shut.manipulation is None, "门本应关着，这条测试的前提不成立"

        opened = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(5.0, 0.0)
        )
        assert opened.manipulation is not None, (
            "本能没能把门推开——检查偏置是不是被加到了 sigmoid 之后"
        )

    def test_the_gate_bias_can_shut_an_open_gate(self):
        """反向也要成立：门本来开着（logit = +0.6），本能把它压回去。

        只测"推开"是不够的——一个恒为正的加法（比如写成 ``abs``）也能通过
        那条。两条合起来才说明它加的是**值**，不是**强度**。
        """

        torch.manual_seed(32)
        model = ActionDecoder()
        self._pin_gate(model, 0.6)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = default_constraints()

        opened = model(intent, cons, drive, two_candidates(), None, None)
        assert opened.manipulation is not None, "门本应开着，这条测试的前提不成立"

        shut = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(-5.0, 0.0)
        )
        assert shut.manipulation is None, "本能没能把门关上"

    def test_the_gate_bias_is_added_to_the_logit_not_the_probability(self):
        """**边界上**的断言——大的偏置区分不出这两种写法，小的可以。

        阈值的比较是 ``sigmoid(x) >= 0.5``，而它等价于 ``x >= 0``。所以：

        - 推 **logit**：``logit + bias >= 0``，即偏置的门槛是 ``−logit``
        - 推 **概率**：``sigmoid(logit) + bias >= 0.5``，门槛是 ``0.5 − sigmoid(logit)``

        固定 ``logit = +0.6``（``sigmoid = 0.6457``）时两者给出**不同**的答案，
        当 ``bias = −0.3``：前者 ``0.3 >= 0`` 开，后者 ``0.3457 < 0.5`` 关。

        **这一条是补出来的。** 原来那两条（推开 / 关合）用的偏置是 ±5.0，
        大到两种写法都会翻到同一侧——把偏置挪到 sigmoid 之后，它们照样全绿。
        「今天绿不算证明，能红才算」在这里真的咬到了：守卫写了，但它守不住
        它声称要守的那件事。
        """

        torch.manual_seed(36)
        model = ActionDecoder()
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = default_constraints()

        # logit = +0.6，bias = −0.3 → 推 logit 时开，推概率时关。
        self._pin_gate(model, 0.6)
        opened = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(-0.3, 0.0)
        )
        assert opened.manipulation is not None, (
            "边界行为不对：偏置被加到了 sigmoid 之后（那是推概率，不是推 logit）"
        )

        # logit = −0.6，bias = +0.3 → 推 logit 时关，推概率时开。
        self._pin_gate(model, -0.6)
        shut = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(0.3, 0.0)
        )
        assert shut.manipulation is None, (
            "边界行为不对：偏置被加到了 sigmoid 之后"
        )

    def test_the_op_bias_switches_the_chosen_operation(self):
        """op 头本来选 ``none``，本能把 ``grasp`` 推上去。"""

        torch.manual_seed(33)
        model = ActionDecoder()
        self._pin_gate(model, 5.0)  # 门先开着，否则看不到 op
        self._pin_op(model, "none", 5.0)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = default_constraints()

        plain = model(intent, cons, drive, two_candidates(), None, None)
        assert plain.manipulation is not None
        assert plain.manipulation.operation == "none"

        biased = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(0.0, 20.0)
        )
        assert biased.manipulation is not None
        assert biased.manipulation.operation == "grasp", (
            "本能没能把 grasp 推上去——检查偏置是不是加在了错的下标上"
        )

    def test_the_bias_cannot_resurrect_a_forbidden_operation(self):
        """``grasp`` 不在 ``allowed_operations`` 里时，本能**推不动**它。

        **这条测试能红的前提要说清楚**（它一开始没红）：偏置有限时，
        "先推后屏蔽"与"先屏蔽后推"**是等价的**——``-inf + 有限数 = -inf``，
        屏蔽照样成立。所以这条测不出那个顺序，它测的是"屏蔽确实发生在
        argmax 之前"（真把屏蔽漏掉，它会红）。

        顺序真正有别的那一格是偏置为 ``inf`` 时：``-inf + inf = nan``，
        而 ``nan`` 在比较里胜过 ``-inf``。那条路已经由
        ``test_a_hand_made_infinite_bias_cannot_hijack_the_op`` 单独守着。
        """

        torch.manual_seed(34)
        model = ActionDecoder()
        self._pin_gate(model, 5.0)
        self._pin_op(model, "none", 5.0)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = replace(default_constraints(), allowed_operations=("none", "push"))

        action = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(0.0, 20.0)
        )
        assert action.manipulation is not None
        assert action.manipulation.operation == "none", (
            "本能复活了一个被约束屏蔽掉的 op"
        )

    def test_a_hand_made_infinite_bias_cannot_hijack_the_op(self):
        """第二道防线：一份 ``inf`` 偏置**绕过解码器**直接送进来，也顶不掉约束。

        正常路径到不了这里——``decode_instinct`` 已经把含 ``inf`` / ``nan``
        的 blob 按"读不懂"拒了，门跟着拒，所以这份偏置进不了结构。这条测的
        是 ``_add_manipulation`` 里"先推偏置、后屏蔽"那个顺序本身。

        **它必须存在，因为那段注释声称它兜住了这一格。** 注释与守卫不匹配
        的代价不是"多写了一句废话"：后来者会据此以为解码侧那道检查可以省掉，
        于是唯一的防线变成零道。
        """

        torch.manual_seed(37)
        model = ActionDecoder()
        self._pin_gate(model, 5.0)
        self._pin_op(model, "none", 5.0)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        # 只允许 push：``grasp`` 与 ``none`` 都被屏蔽成 -inf。
        cons = replace(default_constraints(), allowed_operations=("push",))

        poisoned = torch.zeros(MANIPULATION_ROWS)
        poisoned[MANIP_GRASP_ROW] = float("inf")
        action = model(intent, cons, drive, two_candidates(), None, None, poisoned)
        assert action.manipulation is not None
        assert action.manipulation.operation == "push", (
            "被屏蔽的 op 被一份 inf 偏置复活了——屏蔽没兜住，"
            "而解码侧那道检查并不是唯一防线"
        )

    def test_a_manipulation_instinct_does_not_touch_the_direction(self):
        """作用点隔离：操纵本能不能改方向。

        它与上一条是同一枚硬币的两面——v2 把作用点写进 blob，图的就是
        "投错地方"在结构上不可能。
        """

        torch.manual_seed(35)
        model = ActionDecoder()
        self._pin_gate(model, 5.0)
        intent = torch.randn(model.config.intent_dim)
        drive = torch.randn(model.config.drive_dim)
        cons = default_constraints()

        plain = model(intent, cons, drive, two_candidates(), None, None)
        biased = model(
            intent, cons, drive, two_candidates(), None, None, self._bias(5.0, 5.0)
        )
        assert (
            plain.locomotion.direction == biased.locomotion.direction
        ), "操纵本能改到了方向——作用点隔离被破坏了"
