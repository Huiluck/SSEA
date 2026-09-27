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

在此之前 ``FastLoopContext.get_threshold()`` 是个**没有消费者的声明**：
它写着"Action Decoder 的决策阈值来源"，而 Action Decoder 读的是自己的
config。本模块补上这个消费者（Milestone 4 增量 3）。

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


@dataclass(frozen=True)
class DecodeCandidates:
    """解码时可选的离散目标。

    离散选择（目标对象 / 技能）必须从真实候选里取，不能让解码器自由生成
    字符串——否则它会产出环境中不存在的 object_id，而这类错误要到
    Environment 才被发现。
    """

    #: 视野内对象 id，按距离升序。
    object_ids: tuple[str, ...] = ()

    #: 当前可调用的技能 id。
    skill_ids: tuple[str, ...] = ()

    #: 可提案的自我修改类型。
    proposal_types: tuple[str, ...] = ()


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
        self.manip_target = nn.Linear(64, 1)  # 对候选打分用
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
        direction = torch.tanh(self.loco_dir(h)).tolist()
        speed = float(torch.sigmoid(self.loco_speed(h))) * constraints.max_speed #UserWarning，张量转标量
        duration = float(torch.sigmoid(self.loco_dur(h))) * constraints.max_duration
        locomotion = Locomotion(
            direction=tuple(direction), speed=speed, duration=duration
        )

        action = Action(locomotion=locomotion)

        # ---- 门控通道 ----
        gate_values = {
            name: float(torch.sigmoid(layer(h)))
            for name, layer in self.gates.items()
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
            action = self._add_manipulation(action, h, constraints, candidates)

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
    ) -> Action:
        """从候选对象中选目标，并按约束裁剪操作与力。"""

        # 目标选择：用 manip_target 对每个候选打分。候选本身不带可学特征，
        # 故按索引顺序打分——第一阶段只验证"离散选择走候选集合"这条机制。
        # 目标语义注意力留到 Milestone 4：它要的是"哪个对象与当前记忆相关"，
        # 而记忆系统在 Milestone 3 才落地——在它之前做注意力，打分依据只能是
        # 一个还不存在的输入。
        scores = self.manip_target(h).expand(len(candidates.object_ids))
        target_idx = int(torch.argmax(scores))

        op_logits = self.manip_op(h)
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
