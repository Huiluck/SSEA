"""Action Decoder —— 动作解码器。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.3 +
docs/08-dual-loop-interface-and-gap-closure.md §2.6.2。

职责：将 intent_vector 解码为结构化 Action 对象。

**Action Decoder 不是自然语言解析器**（07 §6.3 原文）。它输出的是：
连续控制参数、离散操作选择、目标对象选择、技能调用参数、记忆写入指令、
通信向量、自我修改提案。

约束强制执行第一执行点（08 §2.6.2）
------------------------------------
本模块**本就接收** ``action_constraints`` 作为输入，因此是约束的第一执行点：
输出前即裁剪 / 否决。Environment 是第二执行点（防御性复核）。

两处共用同一份规则——``ActionConstraints.violations()`` 定义规则，
本模块负责在生成阶段就不越界，Environment 负责兜住漏网的。

通道门控
--------
六个通道各有独立的门控 logit。只有门控打开的通道才出现在 Action 里，
其余为 None。这让 ``Action.active_channels()`` 有实际意义——若每帧都把
六个通道全填上，"动作必须可执行"（08 §2.4）就退化成一个恒真断言。

``locomotion`` 例外：它常开，因为"移动或原地不动"是每帧都要表达的基本意图。
若全部门控关闭（不应发生），回退到 ``idle_action()`` 而非产出空 Action。

门控阈值住在结构里
----------------
门控阈值**不是**模型的私有参数，是 ``FastLoopContext.thresholds`` 里的一项
行为策略（键名见 ``GATE_THRESHOLD_KEYS``）。``forward`` 的 ``gate_thresholds``
参数就是那个映射；不给时退回 ``config.gate_threshold``。

为什么这样接：慢环要能改变门控，而 07 §16「模型不可绕过验证器应用修改」
禁止它直接写 torch 参数。把阈值放进结构快照，改它就必须走
「提案 → 验证门 → Structure Store → 换快照」——于是门控的每一次变动都是
可审计的一次版本切换，而不是一次无人知晓的原地赋值。

在此之前 ``thresholds`` 是个**没有消费者的类别**：改结构里的阈值对行为没有
任何影响，而提案、Gate、Store 一路都是绿的。本模块补上这个消费者
（Milestone 4 增量 3）。

> **注意补上的是类别，不是访问器。** 这里曾写成「``FastLoopContext.
> get_threshold()`` 是个没有消费者的声明……本模块补上这个消费者」，
> 2026-09-28 更正：本模块读的是 ``gate_thresholds`` **整个映射**（解码器要按
> 多个键取值，单键访问器不是它需要的形状），一次都没调用过那个方法。
> 那个方法已于 2026-09-28 删除——它的 ``default=0.0`` 与本模块的回落
> （``config.gate_threshold``）对不上，契约是猜的。**类别活着不等于名字
> 对应的接口活着**，见 14 §6.3.6 与 `tests/test_consumer_surface.py`
> 的 `DELETED_ACCESSORS`。

本能也住在结构里
----------------
同一个道理用在 ``FastLoopContext.adapters`` 上：``forward`` 的
``loco_instinct`` / ``manip_instinct`` 参数是从 ``adapters`` 里的 blob
解码出来的本能先验（见 ``forward`` 的 docstring 与 ``SSEA/instinct.py``）。
于是行为先验走的是完整的遗传路径——可保存、可变异、过验证门、进
GenePackage——而不是被塞进一个手工调好的权重初始化里。

在它之前，``adapters`` 是五类结构里**唯一连读取接口都没有**的一类：
提案能写、门会校验、Store 会升版本、审计会记一笔，只是没人读过。

**两个作用点，都不是「替换」。** 本能一律**加**在某个已经算出来的量上：

| 参数 | 加在哪 | 形状 |
|---|---|---|
| ``loco_instinct`` | ``loco_dir(h)`` 的输出，**tanh 之前** | ``(direction_dim,)`` |
| ``manip_instinct`` | 操纵门 logit 与 ``grasp`` op logit，**sigmoid / argmax 之前** | ``(MANIPULATION_ROWS,)`` |

加法而非替换，是为了让被推的那个头**留在计算图里**。替换会让
``loco_dir`` / ``gates["manipulation"]`` / ``manip_op`` 从图上掉出去，
于是 SSEA 少几个学习作用点——而那不会在任何运行时报错里显现。
``TestTrainability`` 与 ``test_instinct.py::TestInstinctActuallySteers``
各守一边。

推 **logit** 而不是概率：推概率要先过 sigmoid，而 sigmoid 的饱和区会把
一份强先验压成毫无差别的一坨——“加了偏置但什么也没发生”，且不报错。

为什么本模块的输出不可微
--------------------
两件事合起来的结果，不是疏漏：

1. **协议约定 2**：``Action`` 的向量是 ``tuple[float, ...]``，不是 torch
   张量——协议必须可序列化、可 diff、可跨进程。
2. **门控是硬阈值比较**（``sigmoid >= threshold``），不是可微稀疏化。

故 ``forward`` 返回的 Action 不携带计算图。这不是缺陷，是立场：
SSEA **不走"反向传播穿过动作"这条路**——那需要一个可微环境，而 SSEA 的
环境是淘汰函数，不是损失函数（C9）。学习发生在慢环的 LocalPlasticity
与基因变异上（08 §4.2 的 ``Δθ``）。

**内部头仍然可微**：``trunk`` / ``gates`` / 各通道头都是标准 nn.Module，
对它们做反向传播完全通畅。局部可塑性的作用点在这里，不在 Action 上。
把某个头改成纯 Python 运算会让 SSEA 失去学习作用点，且不会在任何
运行时报错里显现——``tests/test_action_decoder.py::TestTrainability``
守着这条。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import torch
import torch.nn as nn

from .instinct import MANIP_GRASP_ROW, MANIP_GATE_ROW, MANIPULATION_ROWS
from .sse_protocols import (
    OPERATIONS,
    Action,
    ActionConstraints,
    Communication,
    Locomotion,
    Manipulation,
    MemoryWrite,
    SelfModification,
    SkillCall,
    idle_action,
)
from .tensorize import as_vector

#: ``grasp`` 在 ``OPERATIONS`` 里的下标——manipulation 本能推的那个 logit。
#:
#: 模块级求值，取不到就在 import 时炸掉。写成函数里 ``try/except`` 会更"稳"，
#: 但那个稳是假的：闭词表被改了却不炸，结果就是**本能偏置悄悄推到一个
#: 错误的下标上**（甚至越界被 argmax 忽略），而现象只是"本能没效果"。
#: 闭词表由协议层守着（``test_protocol_consistency``），这里该做的是
#: 在它被破坏的那一刻就喊出来。
_GRASP_INDEX = OPERATIONS.index("grasp")

#: 参与门控的通道（locomotion 常开，不参与）。
GATED_CHANNELS = ("manipulation", "communication", "memory", "skill", "self_modification")

#: 通道门控的开启阈值。设为可配置而非 0.5，便于实验扫描。
DEFAULT_GATE_THRESHOLD = 0.5

#: 各通道门控阈值在 ``FastLoopContext.thresholds`` 里的键名。
#: 慢环的 Δθ（LocalPlasticity）只能通过改这些键来影响门控——参数侧更新
#: 在第一阶段没有可验证的落点，见 SSEA/plasticity.py 的 DEFERRED_SCOPES。
GATE_THRESHOLD_KEYS: dict[str, str] = {
    name: f"{name}_gate_threshold" for name in GATED_CHANNELS
}


@dataclass(frozen=True)
class ActionDecoderConfig:
    """Action Decoder 配置。"""

    #: intent_vector 维度。必须与 StateCoreConfig.intent_dim 一致。
    intent_dim: int = 32

    #: internal_drive_vector 维度（08 §2.5 固定为 4）。
    drive_dim: int = 4

    #: locomotion.direction 的维度（2D 世界）。
    direction_dim: int = 2

    #: 通信信号向量维度。
    comm_dim: int = 4

    #: 记忆内容向量维度。
    memory_content_dim: int = 4

    #: 通道门控阈值。
    gate_threshold: float = DEFAULT_GATE_THRESHOLD


#: 候选对象的特征维度：``(resource_value, threat_level, distance)``。
#:
#: 这三个字段是**环境自己标注的生存后果**，不是模型解释出来的语义：
#: ``resource_value`` 是这一抓能换多少能量，``threat_level`` 是接触的伤害率，
#: ``distance`` 够不够得着（``reach``）。判据刻意不看 ``category_id``——
#: 它的语义由 ``object_vector.py`` 明令「不由模型解释」。
#:
#: 它们同时是**目标打分的输入**：``manip_target`` 头从「常量分」改成
#: 「对这一组特征打分」之后，同一个头对不同候选才会给出不同的分，
#: ``argmax`` 才不会恒返回 0（债务 5）。
OBJECT_FEATURE_DIM = 3


@dataclass(frozen=True)
class DecodeCandidates:
    """解码时可选的离散目标。

    离散选择（目标对象 / 技能）必须从真实候选里取，不能让解码器自由生成
    字符串——否则它会产出环境中不存在的 object_id，而这类错误要到
    Environment 才被发现。
    """

    #: 视野内对象 id，按距离升序。
    object_ids: tuple[str, ...] = ()

    #: 与 ``object_ids`` **逐项对应**的对象特征，每项 ``OBJECT_FEATURE_DIM`` 维。
    #:
    #: 为什么必须有它：``manip_target`` 头原先只吃 ``h``，对每个候选算出的分
    #: **完全相同**（``expand`` 出来的等值张量），于是 ``argmax`` 恒为 0——
    #: 头本身有参数、有梯度、在 `nn.ModuleList` 里，**输出却被整个丢掉**。
    #: 打分要能区分候选，就必须有候选侧的特征进来。
    #:
    #: 允许留空（老调用点）：空时按全零特征处理，各候选得分相同，
    #: 行为退回「恒选第一个」——那是**退化情形**，不是另一条实现路径。
    object_features: tuple[tuple[float, ...], ...] = ()

    #: 当前可调用的技能 id。
    skill_ids: tuple[str, ...] = ()

    #: 可提案的自我修改类型。
    proposal_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.object_features:
            return
        if len(self.object_features) != len(self.object_ids):
            raise ValueError(
                f"object_features 与 object_ids 必须逐项对应: "
                f"{len(self.object_features)} != {len(self.object_ids)}"
            )
        for i, feats in enumerate(self.object_features):
            if len(feats) != OBJECT_FEATURE_DIM:
                raise ValueError(
                    f"第 {i} 个候选的特征是 {len(feats)} 维，"
                    f"应为 {OBJECT_FEATURE_DIM} 维（见 OBJECT_FEATURE_DIM）"
                )


class ActionDecoder(nn.Module):
    """intent_vector + constraints + drive → Action。

    输出层的构造使"合法"成为默认：连续量直接按约束上限缩放，
    离散量从候选集合里 argmax，布尔门控读约束的 can_* 标志。
    """

    def __init__(self, config: ActionDecoderConfig | None = None) -> None:
        super().__init__()
        self.config = config or ActionDecoderConfig()
        cfg = self.config
        in_dim = cfg.intent_dim + cfg.drive_dim

        # 共享主干
        self.trunk = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.GELU(),
        )

        # locomotion（常开）
        self.loco_dir = nn.Linear(64, cfg.direction_dim)
        self.loco_speed = nn.Linear(64, 1)
        self.loco_dur = nn.Linear(64, 1)

        # manipulation
        self.manip_op = nn.Linear(64, len(OPERATIONS))
        # 目标打分是**双线性**的：``score_i = <manip_target(h), feature_i>``。
        # 头从 h 产出 OBJECT_FEATURE_DIM 维的「我方权重」，与候选侧的
        # (resource_value, threat_level, distance) 点积。于是同一帧的不同候选
        # 得分不同，argmax 才有意义——原先输出是 (1,) 再 expand，分值全等。
        self.manip_target = nn.Linear(64, OBJECT_FEATURE_DIM)
        self.manip_force = nn.Linear(64, 1)
        self.manip_dur = nn.Linear(64, 1)

        # communication
        self.comm = nn.Linear(64, cfg.comm_dim)

        # memory
        self.mem_store = nn.Linear(64, 1)
        self.mem_content = nn.Linear(64, cfg.memory_content_dim)
        self.mem_importance = nn.Linear(64, 1)

        # skill
        self.skill = nn.Linear(64, 1)

        # self_modification
        self.selfmod = nn.Linear(64, 1)

        # 通道门控（不含 locomotion）
        self.gates = nn.ModuleDict({name: nn.Linear(64, 1) for name in GATED_CHANNELS})

    # ------------------------------------------------------------------
    #  前向
    # ------------------------------------------------------------------

    def forward(
        self,
        intent: torch.Tensor,
        constraints: ActionConstraints,
        internal_drive: torch.Tensor,
        candidates: DecodeCandidates | None = None,
        gate_thresholds: Mapping[str, float] | None = None,
        loco_instinct: torch.Tensor | None = None,
        manip_instinct: torch.Tensor | None = None,
    ) -> Action:
        """解码出一个满足约束的 Action。

        签名对应 08 §4.1 的 ``a_t = ActionDecoder(h_t, b_t.action_constraints, d_t)``
        ——**收 constraints 而不收 body**。BodyState 里除约束外没有本模块
        需要的东西（能量 / 损伤 / 疲劳已经进了 ``internal_drive``），收一个
        只为了取其字段的参数会让签名说谎。

        ``gate_thresholds`` 是**结构侧的行为策略**（``FastLoopContext.thresholds``）。
        它是慢环 Δθ 唯一的落点：门控阈值住在结构快照里，于是改它要走
        「提案 → 验证门 → Structure Store → 换快照」整条路，而不必让慢环
        直接写 torch 参数（07 §16：模型不可绕过验证器应用修改）。
        默认 None = 用 ``config.gate_threshold``，老调用点一行不用改。

        两个本能参数都是**已经投影好的偏置**，不是原始权重矩阵：

        - ``loco_instinct``：形状 ``(direction_dim,)``
        - ``manip_instinct``：形状 ``(MANIPULATION_ROWS,)``——第
          ``MANIP_GATE_ROW`` 项推操纵门，第 ``MANIP_GRASP_ROW`` 项推 ``grasp``

        投影（``W @ f``）在 ``SSEA/instinct.py`` 里做，因为那一步要读观测，
        而本模块刻意不收 Observation（见上：收一个只为取字段的参数会让签名说谎）。
        没有可施加的本能时两者都是 ``None``，各自**加**在对应的量上：

            direction      = tanh(loco_dir(h) + loco_bias)
            manip gate     = sigmoid(gates["manipulation"](h) + manip_bias[0])
            manip op       = argmax(manip_op(h) + manip_bias[1] @ grasp 那一项)

        加法是刻意的，有两个后果都是要的：

        1. **被推的头仍然可微、仍然可学。** 替换成 ``tanh(W @ f)`` 会让
           ``loco_dir`` 从计算图里掉出去，于是 SSEA 少一个学习作用点——
           而那不会在任何运行时报错里显现。``TestTrainability`` 守着这条。
        2. **``None`` 时与改动前逐位相同。** 不是"近似相同"：没有本能项
           就是没有那一项。对照组不是"另一个实现"，是同一段代码的本能项为 0。

        门与 op 的偏置都推在 **logit** 上（sigmoid / argmax 之前）：
        推概率要先过 sigmoid，而饱和区会把一份强先验压成毫无差别的一坨。
        """

        cfg = self.config
        candidates = candidates or DecodeCandidates()
        h = self.trunk(
            torch.cat(
                [
                    as_vector(intent, expected=cfg.intent_dim, name="intent_vector"),
                    as_vector(
                        internal_drive, expected=cfg.drive_dim, name="internal_drive"
                    ),
                ]
            )
        )

        # ---- locomotion（常开）----
        # 本能偏置：快照里没有可用 adapter 时 loco_instinct 为 None，
        # 这一行退回改动前的表达式（不是乘 0，是根本没有这一项）。
        loco_logits = self.loco_dir(h)
        if loco_instinct is not None:
            loco_logits = loco_logits + loco_instinct
        direction = torch.tanh(loco_logits).tolist()
        speed = float(torch.sigmoid(self.loco_speed(h))) * constraints.max_speed #UserWarning，张量转标量
        duration = float(torch.sigmoid(self.loco_dur(h))) * constraints.max_duration
        locomotion = Locomotion(
            direction=tuple(direction), speed=speed, duration=duration
        )

        action = Action(locomotion=locomotion)

        # ---- 门控通道 ----
        # 先算 logit 再 sigmoid，中间夹一层本能偏置。**顺序不能反**：
        # sigmoid 之后再加就不是"推 logit"了——那是推概率，而推概率在
        # 饱和区几乎没有效果，现象是"本能装上了但门还是不开"。
        gate_logits = {name: layer(h) for name, layer in self.gates.items()}
        if manip_instinct is not None:
            # 形状 (1,) + 0 维标量 → 广播回 (1,)，与不装本能时同一形状。
            gate_logits["manipulation"] = (
                gate_logits["manipulation"] + manip_instinct[MANIP_GATE_ROW]
            )
        gate_values = {
            name: float(torch.sigmoid(logit)) for name, logit in gate_logits.items()
        }

        def threshold_for(channel: str) -> float:
            """本通道的门控阈值：结构给了就用结构的，否则退回配置值。"""
            if gate_thresholds is None:
                return cfg.gate_threshold
            return float(
                gate_thresholds.get(GATE_THRESHOLD_KEYS[channel], cfg.gate_threshold)
            )

        # manipulation
        if (
            gate_values["manipulation"] >= threshold_for("manipulation")
            and candidates.object_ids
        ):
            action = self._add_manipulation(
                action, h, constraints, candidates, manip_instinct
            )

        # communication
        if (
            gate_values["communication"] >= threshold_for("communication")
            and constraints.can_communicate
        ):
            signal = tuple(torch.tanh(self.comm(h)).tolist())
            action = _replace_channel(
                action, "communication", Communication(target_id="", signal=signal)
            )

        # memory
        if (
            gate_values["memory"] >= threshold_for("memory")
            and constraints.can_store_memory
        ):
            store = bool(torch.sigmoid(self.mem_store(h)) >= cfg.gate_threshold)
            content = tuple(torch.tanh(self.mem_content(h)).tolist())
            importance = float(torch.sigmoid(self.mem_importance(h)))
            action = _replace_channel(
                action,
                "memory",
                MemoryWrite(store=store, content=content, importance=importance),
            )

        # skill
        if (
            gate_values["skill"] >= threshold_for("skill")
            and constraints.can_call_skill
            and candidates.skill_ids
        ):
            chosen = self._argmax_over(self.skill(h), len(candidates.skill_ids))
            action = _replace_channel(
                action,
                "skill",
                SkillCall(skill_id=candidates.skill_ids[chosen], params={}),
            )

        # self_modification
        if (
            gate_values["self_modification"] >= threshold_for("self_modification")
            and constraints.can_self_modify
            and candidates.proposal_types
        ):
            chosen = self._argmax_over(self.selfmod(h), len(candidates.proposal_types))
            action = _replace_channel(
                action,
                "self_modification",
                SelfModification(proposal_type=candidates.proposal_types[chosen]),
            )

        if not action.is_executable():  # 防御：不应发生
            return idle_action()
        return action

    # ------------------------------------------------------------------
    #  内部
    # ------------------------------------------------------------------

    def _add_manipulation(
        self,
        action: Action,
        h: torch.Tensor,
        constraints: ActionConstraints,
        candidates: DecodeCandidates,
        manip_instinct: torch.Tensor | None = None,
    ) -> Action:
        """从候选对象中选目标，并按约束裁剪操作与力。

        目标打分**逐候选**做（债务 5 的修正）：``manip_target(h)`` 产出的是
        「我方对各特征的偏好权重」（``OBJECT_FEATURE_DIM`` 维），与每个候选自己的
        ``(resource_value, threat_level, distance)`` 点积得到该候选的分。

        修正前是 ``self.manip_target(h).expand(n)``——一个等值张量，
        ``argmax`` 恒返回 0，于是**永远选「最近的可见对象」，不看它是什么**。
        头本身有参数、有梯度、挂在 ``nn.Module`` 上，**输出却被整个丢掉**：
        这类"参数在、梯度在、效果不在"的缺陷不会报错，只会让目标选择
        退化成「按距离取第一个」。

        候选不带特征时（``object_features`` 为空）各候选得分相同，
        行为退回「取第一个」——那是**退化情形**，不是另一条实现路径。
        """

        features = candidates.object_features
        if features:
            weights = self.manip_target(h)
            # 用张量乘法而不是把 weights 取成 Python 浮点再点积。注意这**不是**
            # 为了"保住梯度"：argmax 不可微、且分值算完即被丢掉（只留一个下标），
            # 所以 manip_target 本来就不在从 Action 出发的任何梯度路径上——
            # 与"本模块输出不可微"同一个理由（见模块 docstring）。
            # 用张量写法只因它少一层 Python 循环、且让这个头保持成一个
            # 普通的 nn.Module（参数进 state_dict，日后可被结构侧 Δθ 改）。
            feature_matrix = torch.tensor(features, dtype=weights.dtype)
            scores = feature_matrix @ weights
        else:
            scores = torch.zeros(len(candidates.object_ids))
        target_idx = int(torch.argmax(scores))

        op_logits = self.manip_op(h)
        if manip_instinct is not None:
            # 只在 grasp 那一格上加，其余格是 0——用一张零张量散射而不是
            # 就地改 op_logits：就地改会让这个头在反向时多一条没人想要的
            # 版本计数路径，而这里的输出本来就不参与梯度（argmax 不可微）。
            grasp_bias = torch.zeros_like(op_logits)
            grasp_bias[_GRASP_INDEX] = manip_instinct[MANIP_GRASP_ROW]
            op_logits = op_logits + grasp_bias
        # 推偏置在前、按约束屏蔽在后：**屏蔽恒为最后一步**，"抓不到的东西
        # 别去抓"这条边界不该被一份先验顶掉（先验是行为，约束是边界）。
        #
        # 但要诚实说清这个顺序**兜住了什么**：偏置有限时，两种顺序其实等价
        # ——``-inf + 有限数 = -inf``，屏蔽照样成立。它真正不同的是偏置为
        # ``inf`` 时：``-inf + inf = nan``，而 ``nan`` 在比较里胜过 ``-inf``，
        # 于是 ``argmax`` 可能落在一个本该被屏蔽的 op 上。
        #
        # 那一格已经由 ``instinct.decode_instinct`` 从源头堵死了（含 inf / nan
        # 的 blob 一律按"读不懂"拒绝，门也跟着拒）。所以这里是**第二道防线**，
        # 不是唯一那道——写成"这个顺序关掉了复活"会是假话，而假话会让后来者
        # 以为解码侧不需要那道检查。
        allowed = [
            i for i, op in enumerate(OPERATIONS) if op in constraints.allowed_operations
        ]
        if not allowed:
            op = "none"
        else:
            masked = torch.full_like(op_logits, float("-inf"))
            masked[allowed] = op_logits[allowed]
            op = OPERATIONS[int(torch.argmax(masked))]

        force = float(torch.sigmoid(self.manip_force(h))) * constraints.max_force
        duration = float(torch.sigmoid(self.manip_dur(h))) * constraints.max_duration

        return _replace_channel(
            action,
            "manipulation",
            Manipulation(
                target_id=candidates.object_ids[target_idx],
                operation=op,
                force=force,
                duration=duration,
            ),
        )

    @staticmethod
    def _argmax_over(score: torch.Tensor, n: int) -> int:
        """单标量打分 → 候选索引。第一阶段用确定性映射，无随机探索。"""
        if n <= 0:
            return 0
        return int(torch.argmax(score.expand(n)))


def _replace_channel(action: Action, channel: str, value: object) -> Action:
    """返回一个替换了某通道的新 Action（frozen dataclass）。"""
    from dataclasses import replace

    return replace(action, **{channel: value})
