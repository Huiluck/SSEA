"""8.5 Action —— 混合结构化动作对象。

**修订依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.4
（移除 latent_action）。

07 §8.5 原文含：

    "latent_action": {"vector": list[float]},

已删除。v0.3.1 全文没有任何模块或环境消费该字段——它是一个永远为空的死字段。

修订后新增一条明文约束：

    **动作必须可执行。协议中不允许存在无消费者的通道。**

这条约束的落地方式：Action 的六个通道各有明确消费者，
``Action.is_executable()`` 强制至少一个通道非空。

    通道              消费者
    ───────────────  ──────────────────────────
    locomotion       Environment（物理后果）
    manipulation     Environment（物理后果）
    communication    CommunicationSignal 路径（第一阶段只预留）
    memory           Memory System
    skill            Skill Runner
    self_modification  Experience Compiler → Verification Gate

潜空间职责的归属调整：

    - State Core 输出的 ``intent_vector`` 承担模型内部潜表示，**不进入协议**
    - 对外的潜空间通道仅保留 ``CommunicationSignal.signal``，
      对应 doc 01「模型之间以二进制或其它方式交流形成模型自身的语言」的雏形
    - 第一阶段只预留接口，不实现语言演化（与 07 §8.8 一致）
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Locomotion:
    """连续通道：移动。

    ``direction`` 为方向向量，``speed`` 为速率，``duration`` 为持续时间。
    speed = 0 是合法的"本帧原地不动"。
    """

    direction: tuple[float, ...]
    speed: float
    duration: float


@dataclass(frozen=True)
class Manipulation:
    """离散 + 参数化 + 连续混合通道：操作。

    ``operation`` 取值见 action_space.OPERATIONS；``"none"`` 合法。
    ``target_id`` 为空字符串表示无目标。
    """

    target_id: str
    operation: str
    force: float
    duration: float


@dataclass(frozen=True)
class Communication:
    """潜空间通信通道（第一阶段只预留，不实现语言演化）。

    对应 07 §8.8 CommunicationSignal 的发送侧。
    """

    target_id: str
    signal: tuple[float, ...]


@dataclass(frozen=True)
class MemoryWrite:
    """记忆写入请求。``store=False`` 表示本帧不写入。

    ``importance`` 由模型给出，是 HeritableFilter 的输入之一（08 §3.3）。
    """

    store: bool
    content: tuple[float, ...]
    importance: float


@dataclass(frozen=True)
class SkillCall:
    """技能调用请求。非空时由 Skill Runner 查表展开为逐帧子动作（08 §2.3）。

    ``skill_id`` 为空字符串表示本帧不调用技能。
    """

    skill_id: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SelfModification:
    """自我修改请求。产物是 SelfModificationProposal，不直接改任何结构。"""

    proposal_type: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Action:
    """混合结构化动作。

    六个通道全部可选（默认 None），但**至少一个必须非空**——
    这就是「动作必须可执行」的协议级强制。

    无 ``latent_action`` 字段（08 §2.4）。
    """

    locomotion: Locomotion | None = None
    manipulation: Manipulation | None = None
    communication: Communication | None = None
    memory: MemoryWrite | None = None
    skill: SkillCall | None = None
    self_modification: SelfModification | None = None

    #: 六个通道名，顺序即协议定义的通道顺序。
    #: 刻意不加类型标注：加了标注它就会变成 dataclass 字段，而它是协议元数据。
    CHANNELS = (
        "locomotion",
        "manipulation",
        "communication",
        "memory",
        "skill",
        "self_modification",
    )

    def __post_init__(self) -> None:
        unknown = set(self.__dataclass_fields__) - set(self.CHANNELS)
        if unknown:
            # 防御：若将来有人给 Action 加字段而忘了登记消费者，
            # 这里立刻失败，而不是让新通道悄悄变成无消费者的死字段。
            raise TypeError(
                f"Action 出现未登记通道 {sorted(unknown)}；"
                f"新通道必须同时在 CHANNELS 登记并指定消费者"
            )

    def active_channels(self) -> tuple[str, ...]:
        """返回本动作实际启用的通道名。"""
        return tuple(name for name in self.CHANNELS if getattr(self, name) is not None)

    def is_executable(self) -> bool:
        """动作是否可执行：至少一个通道非空。

        这是 08 §2.4 新增明文约束的协议级执行。全空动作不是"安全的默认值"，
        它是协议违背——调用方必须明确表达"本帧不动"（如 locomotion.speed=0）。
        """
        return bool(self.active_channels())

    def calls_skill(self) -> bool:
        """是否请求了技能调用。Skill Runner 的入口判据。"""
        return self.skill is not None and bool(self.skill.skill_id)


def idle_action() -> Action:
    """明确表达"本帧原地不动"的动作。

    用于对照实验与调试。注意它是**可执行的**（locomotion 通道非空），
    与全空的非法 Action 不同。
    """
    return Action(
        locomotion=Locomotion(direction=(0.0, 0.0), speed=0.0, duration=0.0)
    )
