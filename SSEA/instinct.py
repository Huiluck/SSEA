"""Instinct —— 本能先验的读写与特征提取。

**架构依据**：docs/07 §6 的「局部学习 / 小型 adapter」+
docs/08-dual-loop-interface-and-gap-closure.md §2.1 与 §3.4。

本能是什么，不是什么
--------------------
08 §3.4：**本能 = 被反复验证后压缩成权重形式的行为先验。** 它住在
``FastLoopContext.adapters`` 这个结构类别里，于是它**可遗传**
（``GenePackage.instinct_adapters``）、**可变异**（``MUTATION_SCOPES``）、
且**每一次改动都必须走验证门**。

这与「手工调一个更好的默认解码器」是两件不同的事，且这个区别是立场性的：
``action_decoder.loco_dir`` 的权重是**参数**——不可遗传、不受验证门管辖、
也不在 C8 的「给基因先验」范围里。往那里塞一个趋近行为，等于把先验藏进
一个模型物理上碰不到、遗传也带不走的角落。**先验必须住在结构侧。**

为什么 blob 格式定义在模型层而不是协议层
--------------------------------------
``sse_protocols`` **只依赖标准库**（不 import torch），而
``GenePackage.instinct_adapters`` 的类型是 ``tuple[bytes, ...]``——
协议层刻意不绑定具体张量库。所以格式由本模块定义，协议层只当它是一段字节。

作用点由 blob 自己声明，不由 adapter 的名字决定（v2）
---------------------------------------------------
一条 adapter 是一段权重，而**权重只有配上「作用在哪」才有意义**：同样是
2×4 的矩阵，加在 ``loco_dir`` 的输出上是方向偏置，加在操纵链上是门 / op 的
logit 偏置。所以 v2 的头部多了一个 ``target`` 字节。

**为什么不让 adapter 的名字来选作用点**（``"loco"`` / ``"grasp"`` 之类）：
``VerificationGate`` 那边写死了一条立场——「``decode_instinct_set`` 把所有
adapter 的偏置**全部相加**，名字纯粹是审计与遗传用的标签，**不参与解码**」。
名字一旦能选作用点，它就从标签变成了**接线**，而接线是行为的一部分：
改个键名就能让盲测的两臂行为不同，而审计日志上看不出任何结构变动。
更要紧的是，**名字无法被验证**——门只能看见 ``{str: bytes}``，一份叫
``"approach"`` 却写着操纵偏置的 blob 在名字侧完全合法。放进 blob 里则
``_check_adapters`` 那一关（它调用真实解码器）当场就能拒掉。

所以：**名字是标签，作用点是内容。** 两者不混。

失败必须闭，且**不许抛异常**
--------------------------
:func:`decode_instinct` 遇到任何不认识的东西一律返回 ``None``（= 无本能），
不抛。两条理由：

1. **崩溃的代价不对等。** 解码发生在快环的每帧路径上；快环里抛异常 =
   episode 中断 = **真实死亡**。一份坏结构不该杀死一个正在生存的个体。
2. **验证门管不了语义。** ``VerificationGate._check_adapters`` 只校验
   「值是 bytes 且非空」——它不知道里面装的是不是可解的权重
   （13 §4.6 的教训：Store 只管版本号与审计，**不保证下游读得懂**）。
   所以本模块自己保证「读不懂就当作没有」，而门那一侧补的是
   「提交前先真的解一次」（见 ``_check_adapters``）。

**编码侧相反：能抛就抛。** :func:`encode_instinct` 不在每帧路径上，
它只在提案成形时跑一次；在那里静默产出一份下游读不懂的 blob，正是
13 §4.6 那个洞的成因。

两个作用点的特征布局
-------------------

**locomotion（4 维）**：``[资源方向的 x, y, −危险源方向的 x, y]``

- 资源取**最近**的（``resource_value > 0`` 里 distance 最小）；
  方向是 agent → 对象的单位向量，环境已经算好（``ObjectVector.direction``），
  所以**本模块不需要扩协议**。
- 危险源取**威胁最高**的（``threat_level`` 最大），方向**取负**——
  负号就是「回避」这个语义的全部：本能项要往远离它的方向推。

**manipulation（4 维）**：``[资源贴近度, 资源价值, −危险贴近度, −危险威胁度]``

它回答的是与 locomotion **不同**的问题。趋近要的是「往哪个方向走」——一个
由 ``direction`` 直接给出的向量；操纵要的是「现在该不该动手」——一个**条件**，
而条件是标量。所以这里不能用方向，只能用「有多近、多值」这类可比较的量。

权重矩阵的行（``MANIPULATION_ROWS`` 行）就是要去推的那几个 logit：

- ``MANIP_GATE_ROW`` → ``gates["manipulation"]`` 的 logit
- ``MANIP_GRASP_ROW`` → ``manip_op`` 里 ``grasp`` 那一项的 logit

**推的是 logit 不是概率**，与 locomotion 推 ``loco_dir`` 输出同一个道理：
推概率要先过 sigmoid，而 sigmoid 的饱和区会把一份强先验压成毫无差别的一坨。

缺哪一边就填 0。两边都没有 → 全零特征 → 偏置恒为 0 →
**行为与改动前逐位相同**。这让「没有本能」与「没有可本能的对象」
在数值上不可区分，与 ``ZeroMemoryRetriever`` 的「诚实的空」同一条纪律。
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Mapping

import torch

#: blob 的魔数。8 字节，够短也够不可能撞上。
MAGIC = b"SSEAINST"

#: blob 格式版本。改布局必须同时改它，否则旧 blob 会被静默误读。
#:
#: v1 → v2：头部加了一个 ``target`` 字节（见模块 docstring）。
#: **不加兼容分支**：v1 的 blob 里没有作用点，只能被当成 locomotion——
#: 那是一个猜出来的语义，而 v1 的 blob 总数是 0（第一阶段尚未产出过
#: 任何一条被保存下来的 adapter），所以"兼容"没有要保护的对象。
FORMAT_VERSION = 2

#: locomotion 作用点：偏置加在 ``loco_dir`` 的输出上。
TARGET_LOCOMOTION = 0

#: manipulation 作用点：偏置加在操纵门与 ``grasp`` op 的 logit 上。
TARGET_MANIPULATION = 1

#: locomotion 特征维度（见模块 docstring 的布局）。
LOCOMOTION_FEATURES_DIM = 4

#: locomotion 方向维度（2D 世界）。
DIRECTION_DIM = 2

#: manipulation 特征维度（见模块 docstring 的布局）。
MANIPULATION_FEATURES_DIM = 4

#: manipulation 权重矩阵的行数——每行推一个 logit。
MANIPULATION_ROWS = 2

#: 作用点 → 权重矩阵必须的形状。
#:
#: 解码时按它查（形状对不上就当读不懂），编码时按它拒（形状对不上就抛）。
#: **格式知识只此一份**：门那一侧调的是本模块的解码器，不是另写一份检查。
#:
#: 注意今天两个作用点的形状**恰好都是 2×4**。别据此以为形状可以代替
#: ``target`` 字节——那是巧合，作用点是语义，不是尺寸。
TARGET_SHAPES: dict[int, tuple[int, int]] = {
    TARGET_LOCOMOTION: (DIRECTION_DIM, LOCOMOTION_FEATURES_DIM),
    TARGET_MANIPULATION: (MANIPULATION_ROWS, MANIPULATION_FEATURES_DIM),
}

#: 作用点 → 人读的名字。只用于错误信息与打印，**不参与任何判断**。
TARGET_NAMES: dict[int, str] = {
    TARGET_LOCOMOTION: "locomotion",
    TARGET_MANIPULATION: "manipulation",
}

#: manipulation 权重矩阵里推「操纵门 logit」的那一行。
MANIP_GATE_ROW = 0

#: manipulation 权重矩阵里推「``grasp`` op logit」的那一行。
MANIP_GRASP_ROW = 1

#: 本能偏置相对被推的那个量的幅度。
#:
#: 这个数不是随手取的：实测默认世界下 ``loco_dir(h)`` 的输出范数只有
#: **0.08–0.22**（4 个 seed，60 帧），tanh 在该区间内近乎线性，所以
#: 未经训练的方向头几乎是「一个固定的随机方向」——这正是「agent 近似直线
#: 行进、不会转向」的量化版本。1.5 的偏置在范数上高出它一个量级，
#: 于是本能**决定性**地接管方向，而加法结构让方向头仍然可微、仍可贡献。
#:
#: 门与 op 的 logit 也在这个量级上（``nn.Linear(64, 1)`` 吃 GELU 输出），
#: 所以同一个 gain 对两个作用点都成立——**一个先验要么强到能产生行为，
#: 要么就不该叫本能**。真正该由验证门管的是「这份先验合不合法」，
#: 不是「它有多强」。
DEFAULT_GAIN = 1.5


@dataclass(frozen=True)
class Instinct:
    """一份**已解码**的本能：作用点 + 权重矩阵。

    两者绑在一起返回，而不是返回一个裸张量：作用点决定这份权重怎么用，
    分开放就一定会出现「张量在手上、作用点丢了」的调用点——那时它只能
    凭形状猜（两个作用点今天都是 2×4，猜不出来），于是退化成一个默认值。
    """

    target: int
    weights: torch.Tensor


@dataclass(frozen=True)
class Preset:
    """一份内置先验：作用点 + 权重矩阵。"""

    target: int
    weights: tuple[tuple[float, ...], ...]


#: 内置的本能先验。
#:
#: - ``approach``（locomotion）：只趋近最近资源。用于「先趋近，量一次」
#:   那一步——它只含一个变量（趋近），所以测出来的差异只可能来自它。
#: - ``forage``（locomotion）：趋近资源 **且** 回避危险源（危险项取负方向，
#:   故系数为正）。两项**等权**。等权是个固定的选择，不是调出来的：自保
#:   该不该高于取食，第一阶段没有任何依据可依，而**编一个权重比承认它是
#:   任意的更糟**。记在这里，等有测量数据时再谈它配不配改。
#: - ``grasp_in_reach``（manipulation）：资源越近、越值钱，就越该开操纵门
#:   并选 ``grasp``。危险两列的系数是 **0**——这是一个**选择**，不是遗漏：
#:   现有测量（14 §6.3.5）只说明「卡在操纵链」，没有说明危险该不该压低
#:   抓取意愿。填一个负数就是编一个没人测量过的权重。
INSTINCT_PRESETS: dict[str, Preset] = {
    "approach": Preset(
        target=TARGET_LOCOMOTION,
        weights=(
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
        ),
    ),
    "forage": Preset(
        target=TARGET_LOCOMOTION,
        weights=(
            (1.0, 0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0, 1.0),
        ),
    ),
    "grasp_in_reach": Preset(
        target=TARGET_MANIPULATION,
        weights=(
            (1.0, 1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0, 0.0),
        ),
    ),
}


# ----------------------------------------------------------------------
#  编解码
# ----------------------------------------------------------------------


def encode_instinct(weights: torch.Tensor, *, target: int) -> bytes:
    """``TARGET_SHAPES[target]`` 形状的权重矩阵 → blob。

    布局：``MAGIC | version:u8 | target:u8 | rows:u16 | cols:u16 |
    float32 * rows*cols``，全部小端。用 float32 而不是 float64：这是权重
    片段，不是审计数字，而 C4 的「低带宽」在结构侧同样成立。

    ``target`` 是**必填的关键字参数**，没有默认值。给一个默认值
    （哪怕是 ``TARGET_LOCOMOTION``）会让「忘了声明作用点」这个错误
    静默变成「声明成了 locomotion」——于是操纵先验被当成方向偏置去投影，
    算出一个形状合法、数值无害、语义全错的偏置。这种错不报错，只会
    让本能悄悄不生效，正是本项目反复咬到的那一类。

    本函数**可以抛**：它不在快环的每帧路径上（对照 :func:`decode_instinct`）。
    """

    if target not in TARGET_SHAPES:
        raise ValueError(
            f"未知的本能作用点 {target!r}；可选 {sorted(TARGET_SHAPES)}"
        )
    w = torch.as_tensor(weights, dtype=torch.float32)
    if w.dim() != 2:
        raise ValueError(f"本能权重必须是二维矩阵，实为 {tuple(w.shape)}")
    rows, cols = int(w.shape[0]), int(w.shape[1])
    if not 0 < rows < 65536 or not 0 < cols < 65536:
        raise ValueError(f"本能权重维度超出 u16 范围: {rows}×{cols}")
    expected = TARGET_SHAPES[target]
    if (rows, cols) != expected:
        raise ValueError(
            f"作用点 {TARGET_NAMES[target]} 的权重必须是 "
            f"{expected[0]}×{expected[1]}，实为 {rows}×{cols}"
        )
    header = MAGIC + struct.pack("<BBHH", FORMAT_VERSION, target, rows, cols)
    return header + w.contiguous().numpy().tobytes()


def decode_instinct(blob: bytes | bytearray | None) -> Instinct | None:
    """blob → :class:`Instinct`；**读不懂就返回 ``None``**。

    **绝不抛异常。** 任何形状不对、版本不认识、作用点不认识、长度不匹配、
    根本不是 bytes 的输入都返回 ``None``——语义是「这份结构没有可用的本能」。
    理由见模块 docstring：快环每帧都调它，崩溃 = 真实死亡，代价不对等。

    形状按 blob **自己声明的作用点**查 :data:`TARGET_SHAPES`：一份格式合法
    但形状是 3×7 的权重，对任何作用点都不可用，与「读不懂」同等对待。
    """

    if not isinstance(blob, (bytes, bytearray)):
        return None
    blob = bytes(blob)
    header_size = len(MAGIC) + struct.calcsize("<BBHH")
    if len(blob) < header_size:
        return None
    if blob[: len(MAGIC)] != MAGIC:
        return None

    version, target, rows, cols = struct.unpack(
        "<BBHH", blob[len(MAGIC) : header_size]
    )
    if version != FORMAT_VERSION:
        return None
    shape = TARGET_SHAPES.get(target)
    if shape is None:
        return None
    if (rows, cols) != shape:
        return None

    body = blob[header_size:]
    expected = rows * cols * 4  # float32
    if len(body) != expected:
        return None
    flat = struct.unpack(f"<{rows * cols}f", body)
    weights = torch.tensor(flat, dtype=torch.float32).reshape(rows, cols)
    if not bool(torch.isfinite(weights).all()):
        # 含 inf / nan 的权重不是"另一份合法的先验"，是一份**会算出非有限数的**
        # 先验。后果不是"效果差一点"：偏置一旦是 nan / inf，``argmax`` 的行为就
        # 不再是"取最大的那个"——``nan`` 在比较里胜过 ``-inf``，而操纵链是按
        # 约束把越界的 op **屏蔽成 -inf** 的。两者相遇时，一份先验能让
        # ``argmax`` 落在一个本该被屏蔽的 op 上，于是**先验顶掉了约束**。
        # 那正是「行为不该改边界」这条立场最不想看到的事。
        #
        # 按"读不懂就当没有"处理，而不是抛：解码在快环每帧路径上（见模块
        # docstring）。门那一侧调的是同一个解码器，所以这份 blob 也进不了结构。
        return None
    return Instinct(target=target, weights=weights)


def preset_blob(name: str, *, gain: float = DEFAULT_GAIN) -> bytes:
    """内置先验 → blob。``name`` 取自 :data:`INSTINCT_PRESETS`。"""

    try:
        preset = INSTINCT_PRESETS[name]
    except KeyError:
        raise KeyError(
            f"未知的本能先验 {name!r}；可选 {sorted(INSTINCT_PRESETS)}"
        ) from None
    return encode_instinct(
        torch.tensor(preset.weights, dtype=torch.float32) * gain,
        target=preset.target,
    )


def decode_instinct_set(
    adapters: Mapping[str, Any] | None,
) -> tuple[Instinct, ...]:
    """快照的 ``adapters`` 映射 → 可用的本能。不可解的直接丢弃。

    返回而不就地写回：``FastLoopContext`` 是冻结的，而**丢弃本身是结论**——
    「这份结构提交了但读不懂」不该静默变成「这份结构没提交」，
    所以调用方拿到的只有能用的那些，而原始映射保持原样可供审计比对。

    **键名不进入返回值。** 名字是审计与遗传用的标签，解码只看内容
    （见模块 docstring）——把名字带出来只会诱导下游按名字分支，
    而那正是 v2 把作用点移进 blob 要杜绝的事。审计要看名字就直接读快照的
    ``adapters``，那里原样都在。
    """

    if not adapters:
        return ()
    decoded = (decode_instinct(blob) for blob in adapters.values())
    return tuple(inst for inst in decoded if inst is not None)


# ----------------------------------------------------------------------
#  特征
# ----------------------------------------------------------------------


def locomotion_features(observation: Any) -> torch.Tensor:
    """观测 → locomotion 特征向量（布局见模块 docstring）。

    只用 ``ObjectVector`` 已有的字段（``direction`` / ``distance`` /
    ``resource_value`` / ``threat_level``），**不需要扩协议**。
    ``direction`` 是变长的（协议不绑定维度），这里按 2 维世界截断/补零。
    """

    features = torch.zeros(LOCOMOTION_FEATURES_DIM, dtype=torch.float32)

    nearest_resource = _nearest_resource(observation)
    if nearest_resource is not None:
        features[0:DIRECTION_DIM] = _direction_of(nearest_resource, DIRECTION_DIM)

    worst_threat = _worst_threat(observation)
    if worst_threat is not None:
        # 取负 = 「回避」这个语义的全部。
        features[DIRECTION_DIM : 2 * DIRECTION_DIM] = -_direction_of(
            worst_threat, DIRECTION_DIM
        )

    return features


def manipulation_features(observation: Any) -> torch.Tensor:
    """观测 → manipulation 特征向量（布局见模块 docstring）。

    与 :func:`locomotion_features` **不共用实现**，因为两者要的不是同一种量：
    那边要方向（向量），这边要「该不该动手」的条件（标量）。硬凑成一个
    函数会让其中一边拿到自己用不上的字段。

    危险两列取负，与 locomotion 那边同一个约定：负号就是「回避」。
    今天内置的 ``grasp_in_reach`` 给这两列的系数是 0（见 :data:`INSTINCT_PRESETS`），
    所以负号暂时不产生行为——但**约定要先立好**，否则日后想加一条
    「危险附近少动手」的先验时，符号方向得靠猜。
    """

    features = torch.zeros(MANIPULATION_FEATURES_DIM, dtype=torch.float32)

    nearest_resource = _nearest_resource(observation)
    if nearest_resource is not None:
        features[0] = _closeness(float(nearest_resource.distance))
        features[1] = float(getattr(nearest_resource, "resource_value", 0.0))

    worst_threat = _worst_threat(observation)
    if worst_threat is not None:
        features[2] = -_closeness(float(worst_threat.distance))
        features[3] = -float(getattr(worst_threat, "threat_level", 0.0))

    return features


def _nearest_resource(observation: Any) -> Any | None:
    """``resource_value > 0`` 里 distance 最小的那个；没有则 ``None``。"""

    resources = [
        obj for obj in observation.objects if getattr(obj, "resource_value", 0.0) > 0
    ]
    return min(resources, key=lambda o: o.distance) if resources else None


def _worst_threat(observation: Any) -> Any | None:
    """``threat_level > 0`` 里威胁最高的那个；没有则 ``None``。"""

    threats = [
        obj for obj in observation.objects if getattr(obj, "threat_level", 0.0) > 0
    ]
    return max(threats, key=lambda o: o.threat_level) if threats else None


def _closeness(distance: float) -> float:
    """``1 / (1 + d)``：有界、单调、**不含任何需要编出来的尺度**。

    为什么不写成「在 ``reach`` 内为 1，否则为 0」：那要引入一个阈值，
    而阈值是一个**可调旋钮**——于是"本能"里就混进了一个没人测量过其取值的
    参数，还长得像环境常量。``1/(1+d)`` 在 d=0 取 1、d=1（``reach``）取 0.5、
    d=6（``perception_radius``）取 0.14：近处强、远处弱，边界由行为自己长出来。

    ``max(0.0, ...)`` 是防御：d = −1 会让分母为零。距离为负不该发生，
    但这里返回 inf 会一路污染到 logit 上，而它不会报错。
    """

    return 1.0 / (1.0 + max(0.0, distance))


def _direction_of(obj: Any, direction_dim: int) -> torch.Tensor:
    """对象的 ``direction`` 截断/补零到 ``direction_dim`` 维。"""

    raw = list(getattr(obj, "direction", ()) or ())
    values = [float(v) for v in raw[:direction_dim]]
    values += [0.0] * (direction_dim - len(values))
    return torch.tensor(values, dtype=torch.float32)


# ----------------------------------------------------------------------
#  投影
# ----------------------------------------------------------------------


def locomotion_bias(
    instincts: tuple[Instinct, ...],
    features: torch.Tensor,
) -> torch.Tensor | None:
    """locomotion 本能 → 要加到 ``loco_dir`` 输出上的偏置 ``(DIRECTION_DIM,)``。"""
    return _sum_bias(instincts, TARGET_LOCOMOTION, features)


def manipulation_bias(
    instincts: tuple[Instinct, ...],
    features: torch.Tensor,
) -> torch.Tensor | None:
    """manipulation 本能 → ``(MANIPULATION_ROWS,)`` 的 logit 偏置。

    第 ``MANIP_GATE_ROW`` 项推操纵门，第 ``MANIP_GRASP_ROW`` 项推
    ``grasp`` op。**调用方按行取**，别用字面下标。
    """
    return _sum_bias(instincts, TARGET_MANIPULATION, features)


def _sum_bias(
    instincts: tuple[Instinct, ...],
    target: int,
    features: torch.Tensor,
) -> torch.Tensor | None:
    """把 ``target`` 作用点上的全部本能投影到特征上，求和。

    **多份本能相加**，不是覆盖：``adapters`` 是个映射，键是名字。
    相加让「装着两份本能」有一个说得通的含义（各自推一把），
    而覆盖会让键的迭代顺序决定行为——那是个不该存在的隐式依赖。

    三种情形返回 ``None``，调用方据此走原路径，于是「没有本能」与改动前的
    行为**逐位相同**：

    1. 这个作用点上一份可用本能都没有；
    2. 特征全零（视野里既没有资源也没有危险源）——本能无从施加；
    3. **投影结果全零**——例如内置 ``grasp_in_reach`` 给危险两列的系数是 0，
       于是「只看见危险源」时算出来是一行 0。

    第 3 条不是优化而是**保真的必要条件**：``x + 0.0`` 对 ``x = -0.0``
    并不逐位相同（结果是 ``+0.0``）。留着那一项就等于在对照组里留了一个
    改数值的加法，而"对照组不是另一个实现"这条纪律要求它根本没有那一项。
    """

    if not instincts:
        return None
    if float(features.abs().sum()) == 0.0:
        return None

    bias: torch.Tensor | None = None
    for inst in instincts:
        if inst.target != target:
            continue
        if inst.weights.dim() != 2 or inst.weights.shape[1] != features.shape[0]:
            # 形状对不上：单份本能坏了不该拖垮其余的。解码已经按
            # TARGET_SHAPES 保证过形状，这里是防御——本模块的纪律是
            # "读不懂就当没有"，不是"抛"。
            continue
        term = inst.weights @ features
        bias = term if bias is None else bias + term

    if bias is None or float(bias.abs().sum()) == 0.0:
        return None
    return bias
