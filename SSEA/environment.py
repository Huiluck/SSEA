"""Environment —— 第一阶段最小 2D 世界。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.7 +
docs/08-dual-loop-interface-and-gap-closure.md §2.6.2（约束第二执行点）、
§3.6（死亡判定权归属）。

职责（07 §6.7 原文）：环境模拟、对象交互、约束强制执行、事件生成、
淘汰函数。

本模块**不是**一个通用物理引擎，也不是一个游戏。它是 SSEA 立场的物化：

    ┌────────────────────────────────────────────────────────┐
    │ Environment                                            │
    │  ├── step(action) → (Observation, Feedback)            │
    │  ├── 第二约束执行点：非法动作记 ACTION_FAILED，不崩溃     │
    │  ├── 淘汰函数：energy ≤ 0 或 damage ≥ max_damage        │
    │  └── 事件流：不是奖励，是"刚刚发生了什么"的客观记录        │
    └────────────────────────────────────────────────────────┘

为什么淘汰函数必须在环境里
------------------------
08 §3.6 明确了死亡判定权归属。若判定权在模型侧，模型就可以通过修改自身
参数来避免死亡——那 SSEA 的"生存压力"就退化成一个可被 hack 的评分函数。
放在环境里之后，安全约束「模型不可修改淘汰函数」**天然成立**：它在模型
之外，模型物理上碰不到它。这也符合 C9——淘汰是环境对模型的筛选，不是
模型对自己的评分。

为什么第二执行点必须存在
----------------------
Skill Runner 吐出的子动作序列跨越多个步长，期间 ``action_constraints``
可能变化（如 ``energy_budget`` 随能量下降而收缩）。第一执行点（Action
Decoder）裁剪的是**它当时看到的**约束。故 Environment 必须能兜住漏网的，
且兜住的方式是记事件而非抛异常——崩溃会让 episode 中断，而 episode 中断
在生存式架构里等于一次真实的死亡，代价不对等。

第一阶段刻意不做的事（docs/11-phase1-not-doing-list.md）
------------------------------------------------------
不实现四季 / 灾害 / 多智能体 / 高分辨率视觉 / 语言指令 / 奖励函数。
``EnvironmentSummary.time_phase`` 只有四个相位，且**不产生生存后果**——
它只是让感知编码器的 one-hot 段有非零输入，使「时间进入感知」这条通路
可被端到端验证。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .sse_protocols import (
    EVENT_TYPES,
    Action,
    ActionConstraints,
    BodyState,
    Communication,
    CommunicationSignal,
    EnvironmentSummary,
    EventVector,
    Feedback,
    Locomotion,
    Manipulation,
    MemoryWrite,
    ObjectVector,
    Observation,
    SelfModification,
    SelfModificationProposal,
)

#: 一天的帧数。只驱动 time_phase 与 light_level，不驱动生存后果。
DAY_LENGTH = 100.0

#: time_phase → light_level。四相位对应 07 §8.1 的枚举。
LIGHT_BY_PHASE: dict[str, float] = {
    "dawn": 0.4,
    "day": 1.0,
    "dusk": 0.3,
    "night": 0.05,
}

#: 对象类别。resource 可被 grasp 换取能量；hazard 造成损伤；prop 无生存后果，
#: 存在的意义是让 Action Decoder 的离散目标选择有非资源候选可挑。
KIND_RESOURCE = "resource"
KIND_HAZARD = "hazard"
KIND_PROP = "prop"

#: 环境支持的离散操作。与 action_space.OPERATIONS 一致——规则只有一份，
#: 环境是它的第二执行点，不另立一套。
ENV_OPERATIONS: tuple[str, ...] = (
    "none",
    "grasp",
    "push",
    "pull",
    "use_tool",
    "release",
)

#: 通信信号回环保留条数。
MAX_ECHOED_SIGNALS = 4


@dataclass(frozen=True)
class EnvironmentConfig:
    """环境配置。全部数值集中在此，便于实验扫描与复现。"""

    # ---- 世界几何 ----
    #: 世界半径（2D 圆形世界，agent 位置被约束在其中）。
    world_radius: float = 20.0
    #: 感知半径。超出即不可见——这是 C4「低带宽」在观测侧的硬边界。
    perception_radius: float = 6.0
    #: 操作可达距离。
    reach: float = 1.0
    #: 危险源接触半径。
    contact_radius: float = 0.6

    # ---- 代谢 ----
    #: 每帧基础代谢消耗（不动也耗）。
    base_drain: float = 0.01
    #: 每单位移动距离的能量成本系数。
    move_cost_factor: float = 0.02
    #: 每次离散操作的固定能量成本。
    act_cost: float = 0.01
    #: 单位 resource_value 换来的能量。
    resource_gain: float = 0.6
    #: 接触危险源时每单位时间的损伤。
    hazard_damage_rate: float = 0.2
    #: 损伤上限 = 淘汰阈值。
    max_damage: float = 1.0

    # ---- 疲劳与睡眠 ----
    #: 每帧疲劳累积。
    fatigue_rate: float = 0.02
    #: 睡眠期每帧疲劳恢复。
    sleep_fatigue_recovery: float = 0.15
    #: 睡眠期每帧能量恢复（少量；睡眠不是进食）。
    sleep_energy_recovery: float = 0.01

    # ---- 动作约束上限（由环境声明，不由协议层默认值决定）----
    max_speed: float = 1.0
    max_force: float = 1.0
    max_duration: float = 1.0

    #: 是否允许 self_modification 通道。第一阶段默认 False：
    #: 自我修改只应经慢环提案 → 验证门（07 §16），快环不直接改结构。
    allow_self_modify: bool = False

    #: 禁止操作的对象 id。由环境声明，供约束第二执行点使用。
    forbidden_targets: tuple[str, ...] = ()

    #: 是否把本帧通信信号回环进 Observation.social_signals。
    #: 第一阶段单智能体，没有接收方；回环是为了让这条潜空间通道可被
    #: 端到端验证（否则感知编码器的 social 段永远是零，通道虽存在却
    #: 不可观测）。多智能体在 Milestone 3+。
    echo_communication: bool = True

    # ---- 世界生成 ----
    n_resources: int = 6
    n_hazards: int = 3
    n_props: int = 3
    #: 保证落在感知半径内的资源数。
    #: 若开局全盲，Action Decoder 的离散目标选择前几帧无候选，
    #: manipulation 通道恒空——闭环虽可运行，但"移动→接近→抓取"这条
    #: 因果链要等很久才第一次被走到，实验效率极低。
    spawn_near_count: int = 2
    #: 上述资源的落点半径上限。
    spawn_near_radius: float = 4.0
    #: 事件历史保留条数。
    max_events: int = 16

    def __post_init__(self) -> None:
        if self.world_radius <= 0:
            raise ValueError("world_radius 必须为正")
        if self.perception_radius <= 0:
            raise ValueError("perception_radius 必须为正")
        if self.max_damage <= 0:
            raise ValueError("max_damage 必须为正")
        if self.reach > self.perception_radius:
            raise ValueError(
                "reach 大于 perception_radius：可达但不可见的目标"
                "会让 Action Decoder 无从选择"
            )
        # max_events=0 会让 ``del self._events[: -0]`` 退化成 ``del lst[:0]``，
        # 一条都不删——缓冲静默变成无界。这是"看起来生效了，其实没有"的
        # 同一形状（12 §6 债务 1），所以在这里炸掉而不是等它悄悄长大。
        if self.max_events < 1:
            raise ValueError(f"max_events 至少为 1，否则缓冲不截断: {self.max_events}")


@dataclass
class _WorldObject:
    """环境内部对象。与协议层的 ObjectVector 刻意分离。

    内部对象持有绝对位置与速度；``ObjectVector`` 是**相对于 agent** 的
    摘要。协议层不出现绝对坐标之外的内部量，环境也不向协议泄漏可变句柄。
    """

    object_id: str
    category_id: int
    kind: str
    position: list[float]
    velocity: tuple[float, float]
    resource_value: float
    threat_level: float
    affordance: tuple[float, ...]


class Environment:
    """第一阶段最小 2D 世界。

    用法::

        env = Environment(seed=0)
        obs, fb = env.step(action)
        ...
        obs, fb = env.rest()      # 睡眠期一步
        env.reset()               # 新 episode
    """

    def __init__(
        self, config: EnvironmentConfig | None = None, seed: int | None = None
    ) -> None:
        self.config = config or EnvironmentConfig()
        self._seed = seed
        self._rng = random.Random(seed)
        self._event_seq = 0
        self._proposal_seq = 0

        self.time = 0.0
        self.energy = 1.0
        self.damage = 0.0
        self.fatigue = 0.0
        self.position: list[float] = [0.0, 0.0]
        self.orientation: list[float] = [1.0, 0.0]
        self.alive = True

        # 模型侧内部状态的对外镜像。由 FastLoop 每帧回填——环境不生产它，
        # 只是把它带进 Observation（07 §8.2）。
        self.internal_state: tuple[float, ...] = ()

        self.objects: list[_WorldObject] = []
        self._events: list[EventVector] = []
        self._echoed: list[CommunicationSignal] = []
        self._event_notes: list[tuple[float, str, str, str]] = []
        self._visible_ids: frozenset[str] = frozenset()
        self._reset_event_counts()

        # 通道副产物：本阶段只记录，不消费。真正的消费者在 Milestone 3/4。
        self.proposals: list[SelfModificationProposal] = []
        self.memory_requests: list[tuple[float, MemoryWrite]] = []

        self._spawn_world()
        self._diff_visibility()

    # ------------------------------------------------------------------
    #  生命周期
    # ------------------------------------------------------------------

    def reset(self, seed: int | None = None) -> Observation:
        """重置到初始状态并返回首个观测。"""

        if seed is not None:
            self._seed = seed
        self._rng = random.Random(self._seed)
        self.time = 0.0
        self.energy = 1.0
        self.damage = 0.0
        self.fatigue = 0.0
        self.position = [0.0, 0.0]
        self.orientation = [1.0, 0.0]
        self.alive = True
        self.internal_state = ()
        self.objects = []
        self._events = []
        self._echoed = []
        self._event_notes = []
        self._event_seq = 0
        self._proposal_seq = 0
        self._visible_ids = frozenset()
        self.proposals = []
        self.memory_requests = []
        self._reset_event_counts()
        self._spawn_world()
        self._diff_visibility()
        return self._observe()

    def _reset_event_counts(self) -> None:
        """把按类型的事件累计重置为全零。

        键集**动态取自** ``EVENT_TYPES``，不是写死的 14 个名字——这样往词表里
        增删类型时不需要记得来这里改第二处（两处各写一遍，迟早漂移）。

        ``__init__`` 与 ``reset()`` 都调它，因为它们做的是同一件事：
        ``_events`` / ``_event_notes`` / ``_event_seq`` 一起归零。计数器与它们
        同生命周期，理由见 ``event_counts()``。
        """

        self._event_counts: dict[str, int] = {t: 0 for t in EVENT_TYPES}

    def _spawn_world(self) -> None:
        """生成资源 / 危险源 / 道具。

        用 ``random.Random(seed)`` 而非全局 ``random``——全局态会让两次
        同 seed 的运行结果依赖于此前的调用历史，实验不可复现。
        """

        cfg = self.config
        idx = 0

        def place(min_r: float, max_r: float) -> list[float]:
            angle = self._rng.uniform(0.0, 2.0 * math.pi)
            radius = self._rng.uniform(min_r, max_r)
            return [radius * math.cos(angle), radius * math.sin(angle)]

        for i in range(cfg.n_resources):
            near = i < cfg.spawn_near_count
            self.objects.append(
                _WorldObject(
                    object_id=f"res_{idx}",
                    category_id=1,
                    kind=KIND_RESOURCE,
                    position=place(
                        1.5,
                        min(cfg.spawn_near_radius, cfg.world_radius)
                        if near
                        else cfg.world_radius,
                    ),
                    velocity=(0.0, 0.0),
                    resource_value=round(self._rng.uniform(0.3, 1.0), 3),
                    threat_level=0.0,
                    affordance=(1.0, 0.0, 0.0, 0.0),
                )
            )
            idx += 1

        for _ in range(cfg.n_hazards):
            self.objects.append(
                _WorldObject(
                    object_id=f"haz_{idx}",
                    category_id=2,
                    kind=KIND_HAZARD,
                    position=place(2.0, cfg.world_radius * 0.8),
                    velocity=(
                        round(self._rng.uniform(-0.1, 0.1), 3),
                        round(self._rng.uniform(-0.1, 0.1), 3),
                    ),
                    resource_value=0.0,
                    threat_level=round(self._rng.uniform(0.3, 1.0), 3),
                    affordance=(0.0, 1.0, 0.0, 0.0),
                )
            )
            idx += 1

        for _ in range(cfg.n_props):
            self.objects.append(
                _WorldObject(
                    object_id=f"prop_{idx}",
                    category_id=3,
                    kind=KIND_PROP,
                    position=place(1.0, cfg.world_radius),
                    velocity=(0.0, 0.0),
                    resource_value=0.0,
                    threat_level=0.0,
                    affordance=(0.0, 0.0, 1.0, 0.0),
                )
            )
            idx += 1

    # ------------------------------------------------------------------
    #  主接口
    # ------------------------------------------------------------------

    def step(
        self, action: Action, prediction_error: float = 0.0
    ) -> tuple[Observation, Feedback]:
        """推进一步。返回 ``(Observation, Feedback)``（07 §7.1）。

        参数
        ----
        action:
            本帧动作。由 Skill Runner 吐出的子动作，或 Action Decoder 的原产物。
        prediction_error:
            **本字段不是环境生产的**。生产者是 Metabolic Monitor 的
            SurpriseEstimator（08 §2.6.1）。这里只是入口，让调用方不必
            对 frozen 的 Feedback 做 ``replace``；默认 0.0 表示未提供。

        返回的 Feedback 恒不抛异常。任何非法输入都被转化为
        ``action_success=False`` + ACTION_FAILED 事件（08 §2.6.2）。
        """

        if not self.alive:
            raise RuntimeError(
                "环境已终结（survived=False）。淘汰是终态，不可撤销；"
                "开始新 episode 请调用 reset()。"
            )

        energy_before = self.energy
        damage_before = self.damage
        fatigue_before = self.fatigue
        self.time += 1.0

        constraints = self.constraints()
        notes: list[str] = []

        # ---- 约束第二执行点 ----
        violations = constraints.violations(action)
        if not action.is_executable():
            violations.append("动作不可执行：六个通道全空")
        if violations:
            reason = "; ".join(violations)
            self._emit_event(
                "ACTION_FAILED", source_id="environment", importance=0.6, extra=reason
            )
            notes.append(f"constraint_rejected: {reason}")
            # 拒绝只跳过动作后果，不跳过基础代谢——身体不动也在耗能。
            self.energy = max(0.0, self.energy - self.config.base_drain)
            return self._finish_step(
                energy_before,
                damage_before,
                fatigue_before,
                action_success=False,
                success_event=False,
                prediction_error=prediction_error,
                notes="; ".join(notes),
            )

        # ---- 动作后果 ----
        # 防御性兜底：任何未预期异常都转化为 ACTION_FAILED 而非崩溃。
        try:
            ok = self._apply(action, notes)
        except Exception as exc:  # pragma: no cover - 防御路径
            self._emit_event(
                "ACTION_FAILED",
                source_id="environment",
                importance=0.6,
                extra=f"internal: {exc}",
            )
            notes.append(f"internal_error: {exc}")
            self.energy = max(0.0, self.energy - self.config.base_drain)
            return self._finish_step(
                energy_before,
                damage_before,
                fatigue_before,
                action_success=False,
                success_event=False,
                prediction_error=prediction_error,
                notes="; ".join(notes),
            )

        # ---- 环境自身演化 ----
        self._drift_hazards()
        self._apply_hazard_contact(notes)
        self.energy = max(0.0, self.energy - self.config.base_drain)
        self.fatigue = min(1.0, self.fatigue + self.config.fatigue_rate)

        return self._finish_step(
            energy_before,
            damage_before,
            fatigue_before,
            action_success=ok,
            success_event=True,
            prediction_error=prediction_error,
            notes="; ".join(notes),
        )

    def rest(self, prediction_error: float = 0.0) -> tuple[Observation, Feedback]:
        """睡眠期一步。**不消耗动作**，只恢复疲劳与少量能量。

        这是 08 §2.2 睡眠期在环境侧的落地：睡眠期是一等公民状态，
        入口由 Metabolic Monitor 判定，环境负责"睡的时候身体发生什么"。

        刻意**不**扣基础代谢——"在安全时允许无损整理经验"里的"无损"指的
        就是这个。若睡眠也耗能，模型就没有理由进入睡眠期，慢环的唯一常规
        入口会被生存压力挤掉。
        """

        if not self.alive:
            raise RuntimeError("环境已终结；调用 reset() 开始新 episode。")

        energy_before = self.energy
        damage_before = self.damage
        fatigue_before = self.fatigue
        self.time += 1.0
        self.fatigue = max(0.0, self.fatigue - self.config.sleep_fatigue_recovery)
        self.energy = min(1.0, self.energy + self.config.sleep_energy_recovery)

        return self._finish_step(
            energy_before,
            damage_before,
            fatigue_before,
            action_success=True,
            success_event=False,
            prediction_error=prediction_error,
            notes="sleep",
        )

    # ------------------------------------------------------------------
    #  约束（第二执行点与 Observation 共用一份）
    # ------------------------------------------------------------------

    def constraints(self) -> ActionConstraints:
        """本帧的动作约束。随身体状态变化，尤其是 ``energy_budget``。

        ``energy_budget`` 取当前剩余能量：能量即动作预算，这是代谢监控器
        「动作预算约束」信号与约束体系的接合点。
        """

        cfg = self.config
        return ActionConstraints(
            max_speed=cfg.max_speed,
            max_force=cfg.max_force,
            max_duration=cfg.max_duration,
            allowed_operations=ENV_OPERATIONS,
            forbidden_targets=cfg.forbidden_targets,
            energy_budget=round(self.energy, 6),
            can_communicate=True,
            can_store_memory=True,
            can_call_skill=self.energy > 0.0,
            can_self_modify=cfg.allow_self_modify,
        )

    # ------------------------------------------------------------------
    #  观测构造
    # ------------------------------------------------------------------

    def set_internal_state(self, state: tuple[float, ...]) -> None:
        """回填模型侧内部状态镜像。由 FastLoop 在 step 之前调用。"""

        self.internal_state = tuple(state)

    def visible_objects(self) -> list[tuple[_WorldObject, float]]:
        """视野内对象及其距离，按距离升序。"""

        out: list[tuple[_WorldObject, float]] = []
        for obj in self.objects:
            d = _distance(obj.position, self.position)
            if d <= self.config.perception_radius:
                out.append((obj, d))
        out.sort(key=lambda pair: pair[1])
        return out

    def _observe(self) -> Observation:
        objects = tuple(
            _to_object_vector(obj, self.position) for obj, _ in self.visible_objects()
        )
        return Observation(
            time=self.time,
            body=BodyState(
                energy=round(self.energy, 6),
                damage=round(self.damage, 6),
                fatigue=round(self.fatigue, 6),
                position=tuple(round(v, 6) for v in self.position),
                orientation=tuple(round(v, 6) for v in self.orientation),
                action_constraints=self.constraints(),
                internal_state=self.internal_state,
            ),
            environment=self._summary(objects),
            objects=objects,
            events=tuple(self._events[-self.config.max_events :]),
            social_signals=tuple(self._echoed[-MAX_ECHOED_SIGNALS:]),
        )

    def _summary(self, objects: tuple[ObjectVector, ...]) -> EnvironmentSummary:
        phase = self._time_phase()
        if objects:
            danger = max(obj.threat_level for obj in objects)
            density = sum(1 for obj in objects if obj.resource_value > 0) / len(objects)
        else:
            danger = 0.0
            density = 0.0
        return EnvironmentSummary(
            light_level=LIGHT_BY_PHASE[phase],
            temperature=0.5,
            danger_level=round(min(1.0, max(0.0, danger)), 6),
            resource_density=round(density, 6),
            time_phase=phase,
        )

    def _time_phase(self) -> str:
        phase = (self.time % DAY_LENGTH) / DAY_LENGTH
        if phase < 0.15:
            return "dawn"
        if phase < 0.55:
            return "day"
        if phase < 0.70:
            return "dusk"
        return "night"

    # ------------------------------------------------------------------
    #  动作应用
    # ------------------------------------------------------------------

    def _apply(self, action: Action, notes: list[str]) -> bool:
        """应用动作后果。返回本帧动作是否真的生效。

        返回值必须与 ACTION_FAILED 事件一致——``Feedback.action_success``
        是 Skill Runner 的中止判据（``ABORT_ENV``），事件流是慢环的检索
        依据。两者若各说各话，一个技能会在"明明抓空了"的情况下继续跑完
        整个 action_sequence，且没有任何运行时会报错。
        """

        ok = True
        if action.locomotion is not None:
            # bool(...) 是必须的：某个 _apply_* 漏写 return 时会返回 None，
            # None 是 falsy 但不是 False，会原样流进 Feedback.action_success。
            # 那种字段类型错误不会在任何地方报错，只会让 Skill Runner
            # 的中止判据变成"不确定"。
            ok = bool(self._apply_locomotion(action.locomotion, notes)) and ok
        if action.manipulation is not None:
            ok = bool(self._apply_manipulation(action.manipulation, notes)) and ok
        if action.communication is not None:
            self._apply_communication(action.communication)
        if action.memory is not None:
            self._apply_memory(action.memory)
        if action.self_modification is not None:
            self._apply_self_modification(action.self_modification)
        return ok

    def _apply_locomotion(self, loco: Locomotion, notes: list[str]) -> bool:
        unit = _unit(loco.direction)
        if unit is None or loco.speed <= 0.0:
            notes.append("locomotion: idle")
            return True  # 原地不动是合法动作，不是失败
        dist = loco.speed * loco.duration
        self.position = [
            self.position[i] + unit[i] * dist for i in range(min(2, len(unit)))
        ]
        # 世界边界：径向投影回圆内。撞墙不是死亡，只是走不动。
        r = math.hypot(*self.position)
        if r > self.config.world_radius:
            scale = self.config.world_radius / r
            self.position = [v * scale for v in self.position]
        if len(unit) >= 2:
            self.orientation = list(unit[:2])
        cost = dist * self.config.move_cost_factor
        self.energy = max(0.0, self.energy - cost)
        notes.append(f"locomotion: dist={dist:.3f} cost={cost:.3f}")
        return True

    def _apply_manipulation(self, manip: Manipulation, notes: list[str]) -> bool:
        cfg = self.config
        if manip.operation == "none":
            notes.append("manipulation: none")
            return True
        if not manip.target_id:
            self._emit_event(
                "ACTION_FAILED",
                source_id="environment",
                importance=0.5,
                extra="manipulation 无 target_id",
            )
            notes.append("manipulation: no target")
            return False

        target = self._find(manip.target_id)
        if target is None:
            self._emit_event(
                "ACTION_FAILED",
                source_id="environment",
                importance=0.5,
                extra=f"target={manip.target_id} 不存在",
            )
            notes.append(f"manipulation: missing {manip.target_id}")
            return False

        dist = _distance(target.position, self.position)
        if dist > cfg.reach:
            self._emit_event(
                "ACTION_FAILED",
                source_id="environment",
                importance=0.5,
                extra=f"target={manip.target_id} 距离 {dist:.3f} 超出 reach",
            )
            notes.append(f"manipulation: unreachable {manip.target_id}")
            return False

        self.energy = max(0.0, self.energy - cfg.act_cost)

        if manip.operation == "grasp":
            if target.kind != KIND_RESOURCE:
                self._emit_event(
                    "ACTION_FAILED",
                    source_id=target.object_id,
                    importance=0.5,
                    extra=f"{target.kind} 不可 grasp",
                )
                notes.append(f"manipulation: {target.kind} not graspable")
                return False
            gain = target.resource_value * cfg.resource_gain
            # 按身份移除，不用 list.remove——_WorldObject 按值比较，
            # 两个字段全同的对象会让 remove 删错那个。
            self.objects = [o for o in self.objects if o is not target]
            # 上限 1.0：吃饱了就不能再存。这意味着"能量满时抓资源是浪费"，
            # 是环境强加的策略压力，不是数值意外。
            self.energy = min(1.0, self.energy + gain)
            self._emit_event(
                "ENERGY_GAINED",
                source_id=target.object_id,
                importance=0.8,
                extra=f"gain={gain:.3f}",
            )
            notes.append(f"grasp: +{gain:.3f} energy")
            return True

        if manip.operation in ("push", "pull"):
            # 方向由 agent→target 推导：push 沿此方向推开，pull 反向拉回。
            # Manipulation 协议里没有 direction 字段——推拉的方向是几何
            # 后果，不是模型的自由参数。
            delta = [target.position[i] - self.position[i] for i in range(2)]
            unit = _unit(delta)
            if unit is None:
                notes.append(f"{manip.operation}: coincident, no-op")
                return True
            sign = 1.0 if manip.operation == "push" else -1.0
            target.position = [
                target.position[i] + unit[i] * manip.force * sign for i in range(2)
            ]
            self.energy = max(0.0, self.energy - manip.force * cfg.move_cost_factor)
            notes.append(f"{manip.operation}: force={manip.force:.3f}")
            return True

        if manip.operation == "use_tool":
            if target.kind != KIND_HAZARD:
                self._emit_event(
                    "ACTION_FAILED",
                    source_id=target.object_id,
                    importance=0.5,
                    extra=f"{target.kind} 不是危险源",
                )
                notes.append(f"use_tool: {target.kind} not a hazard")
                return False
            before = target.threat_level
            target.threat_level = max(0.0, before - manip.force * 0.5)
            notes.append(f"use_tool: threat {before:.3f}->{target.threat_level:.3f}")
            return True

        # release：本阶段无持物状态，明确记为无操作而非失败。
        notes.append("release: no-op")
        return True

    def _apply_communication(self, comm: Communication) -> None:
        if not self.config.echo_communication:
            # 关掉回环时仍记事件——通道被走过，只是没有接收方。
            self._emit_event(
                "ACTION_SUCCESS", source_id="self", importance=0.1, extra="comm: 无接收方"
            )
            return
        self._echoed.append(
            CommunicationSignal(
                sender_id="self",
                receiver_id=comm.target_id,
                signal=tuple(comm.signal),
                timestamp=self.time,
                priority=0,
            )
        )
        del self._echoed[:-MAX_ECHOED_SIGNALS]

    def _apply_memory(self, mem: MemoryWrite) -> None:
        if not mem.store:
            return
        self.memory_requests.append((self.time, mem))
        self._emit_event(
            "MEMORY_STORED",
            source_id="self",
            importance=mem.importance,
            extra=f"importance={mem.importance:.3f}",
        )

    def _apply_self_modification(self, selfmod: SelfModification) -> None:
        """记录提案，**不应用**。

        环境是自我修改的观察方，不是执行方。执行方是 Structure Store，
        且必须过 Verification Gate（08 §2.1）。环境这里只做一件事：把
        请求变成一条可审计的 SelfModificationProposal 并发出事件。
        """

        self._proposal_seq += 1
        proposal = SelfModificationProposal(
            proposal_id=f"p_{self._proposal_seq}",
            proposal_type=selfmod.proposal_type,
            target=str(selfmod.payload.get("target", "")),
            payload=dict(selfmod.payload),
            reason="来自 Action.self_modification 通道",
            risk_level="medium",
        )
        self.proposals.append(proposal)
        self._emit_event(
            "SELF_MOD_PROPOSED",
            source_id=proposal.proposal_id,
            importance=0.7,
            extra=proposal.proposal_type,
        )

    # ------------------------------------------------------------------
    #  环境演化
    # ------------------------------------------------------------------

    def _drift_hazards(self) -> None:
        for obj in self.objects:
            if obj.kind != KIND_HAZARD or obj.velocity == (0.0, 0.0):
                continue
            obj.position = [
                obj.position[i] + obj.velocity[i] for i in range(min(2, len(obj.position)))
            ]

    def _apply_hazard_contact(self, notes: list[str]) -> None:
        cfg = self.config
        for obj in list(self.objects):
            if obj.kind != KIND_HAZARD:
                continue
            dist = _distance(obj.position, self.position)
            if dist > cfg.contact_radius:
                continue
            dmg = obj.threat_level * cfg.hazard_damage_rate
            self.damage = min(cfg.max_damage, self.damage + dmg)
            self._emit_event(
                "DAMAGE_RECEIVED",
                source_id=obj.object_id,
                importance=0.9,
                extra=f"damage={dmg:.3f}",
            )
            notes.append(f"hazard contact: +{dmg:.3f} damage")

    # ------------------------------------------------------------------
    #  收尾
    # ------------------------------------------------------------------

    def _finish_step(
        self,
        energy_before: float,
        damage_before: float,
        fatigue_before: float,
        *,
        action_success: bool,
        success_event: bool,
        prediction_error: float,
        notes: str,
    ) -> tuple[Observation, Feedback]:
        if success_event:
            self._emit_event("ACTION_SUCCESS", source_id="self", importance=0.2)
        self._diff_visibility()

        # ---- 淘汰函数（08 §3.6：判定权归环境）----
        survived = not (self.energy <= 0.0 or self.damage >= self.config.max_damage)
        if not survived:
            self.alive = False
            notes = f"{notes}; eliminated" if notes else "eliminated"

        observation = self._observe()
        feedback = Feedback(
            energy_change=round(self.energy - energy_before, 6),
            damage_change=round(self.damage - damage_before, 6),
            fatigue_change=round(self.fatigue - fatigue_before, 6),
            prediction_error=max(0.0, prediction_error),
            action_success=action_success,
            survived=survived,
            notes=notes,
        )
        return observation, feedback

    def _diff_visibility(self) -> None:
        """视野进出事件（OBJECT_FOUND / OBJECT_LOST）。

        稀疏观测下"某个对象消失了"本身就是信息——它意味着资源被耗尽，
        或对象离开了感知半径。这条事件让慢环的 RuleCompiler 有据可查。
        """

        now = frozenset(obj.object_id for obj, _ in self.visible_objects())
        for object_id in sorted(now - self._visible_ids):
            self._emit_event("OBJECT_FOUND", source_id=object_id, importance=0.3)
        for object_id in sorted(self._visible_ids - now):
            self._emit_event("OBJECT_LOST", source_id=object_id, importance=0.3)
        self._visible_ids = now

    def observe_model_event(
        self,
        event_type: str,
        importance: float,
        extra: str = "",
    ) -> None:
        """记录一条**模型侧**事件。由快环在 step 之后调用。

        为什么环境要记录模型内部发生的事：``EVENT_TYPES`` 里
        MEMORY_STORED 与 MEMORY_RETRIEVED 描述的都是记忆系统的行为，
        而记忆系统不是环境、也发不出事件。若不从这里补，这两个类型在第一阶段
        就没有生产者——正是 08 §2.4 从 Action 里删掉 latent_action 的那种缺陷。

        环境**只是记录方**：它不知道模型为什么检索、检索到了什么，
        也不据此改变世界。事件进观测流，供观察员与慢环检索。
        07 §7.2 的两份清单正是这个位置：自然语言可用于"人类观察员日志 /
        事后解释 / 慢环规划候选 / 调试输出"，**不能直接参与**"感知输入 /
        动作输出 / 身体控制 / 实时闭环"。
        """

        self._emit_event(event_type, source_id="self", importance=importance, extra=extra)

    # ------------------------------------------------------------------
    #  事件
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        event_type: str,
        *,
        source_id: str,
        importance: float,
        extra: str = "",
    ) -> None:
        self._event_seq += 1
        self._events.append(
            EventVector(
                event_id=f"e_{self._event_seq}",
                timestamp=self.time,
                event_type=event_type,
                source_id=source_id,
                # 四维固定长度：变长上下文会让 PerceptionEncoder 的
                # raw_dim 不确定。
                context_vector=(
                    round(self.energy, 6),
                    round(self.damage, 6),
                    round(self.fatigue, 6),
                    0.0,
                ),
                importance=min(1.0, max(0.0, importance)),
            )
        )
        # 累计计数**写在构造之后**，不是与 ``_event_seq += 1`` 并排。
        # 顺序有讲究：``_apply`` 被 step() 的兜底 except 包着，越界的事件类型
        # 会先在这里被 EventVector 拒掉（抛 ValueError），若那时计数器已经加过，
        # 闭词表的 dict 里就会多出一个外来键——而"模糊的事件类型比没有更糟"。
        # 放在构造之后，dict 保持干净，代价只是 ``_event_seq`` 永久领先 1，
        # 而它只用来生成 event_id，编号有空洞无害。
        self._event_counts[event_type] += 1
        del self._events[: -self.config.max_events]
        if extra:
            # 事件向量没有自由文本字段（07 §8.7 刻意如此），但"为什么失败"
            # 必须可回答。故另存一份可读说明，只供观察员，不进控制闭环。
            self._event_notes.append((self.time, event_type, source_id, extra))
            del self._event_notes[: -self.config.max_events]

    def _find(self, object_id: str) -> _WorldObject | None:
        for obj in self.objects:
            if obj.object_id == object_id:
                return obj
        return None

    # ------------------------------------------------------------------
    #  观察员接口
    # ------------------------------------------------------------------

    def event_log(self) -> tuple[EventVector, ...]:
        """近期事件流。供观察员与慢环检索，不进控制闭环。"""

        return tuple(self._events)

    def event_counts(self) -> dict[str, int]:
        """按类型累计的事件计数，**自构造或上次 reset() 以来**。

        观察员用，不是奖励信号。

        为什么需要它：``event_log()`` 是 16 槽环形缓冲（``max_events``），
        跑完一轮再统计会**静默丢掉早期事件**，而且错的方向偏向零——正好会把
        有效果的实验读成没效果。本计数器只增不减、不截断，与 ``_event_seq``
        互为校验（``sum(event_counts().values()) == env._event_seq``）。

        为什么口径是"自构造或上次 ``reset()`` 以来"而不是"整轮"：
        ``FastLoop.__init__`` 会调 ``reset()``，而 ``reset()`` 归零。环境不该持有
        比一个 episode 更长的记忆；跨 episode 的累计是**调用方**的职责。

        **返回全部 ``EVENT_TYPES`` 键、含 0 值。** 稀疏 dict 会把"0 次"与
        "没测"混成同一个样子，而这两者必须可区分。但键全了之后 ``0`` 本身
        有三义，dict 分不出来，只能靠这段话：

        1. **有机会、确实没发生。**
        2. **没有生产者**——当前是这 5 个：``ENERGY_LOST`` /
           ``SKILL_SUCCESS`` / ``SKILL_FAILURE`` / ``SELF_MOD_APPLIED`` /
           ``SELF_MOD_ROLLBACK``。它们恒为 0，**这是缺口不是成绩**。
           （``ENERGY_LOST``：能量一直在掉却一条事件都不发；``SKILL_*``：只进
           ``StepRecord.skill_event``，从不进事件流；``SELF_MOD_*``：应用方是
           StructureStore，它没有环境引用，属 Milestone 5 的接线。）
        3. **这段没跑到**（比如从未睡眠）。

        **不要拿 ``ACTION_FAILED`` 反推动作合法率。** 这一个桶混了三类：
        约束拒绝、动作级失败（无 target / 超距 / 不可抓）、以及被兜底 except
        吞掉的内部异常。运行指标里的合法率是从 ``feedback.notes`` 数
        ``constraint_rejected:`` 得来的，口径不同，混用会让归档数字悄悄改义。

        同理 ``ENERGY_GAINED`` **不是**"拿到了多少能量"：抓取是先夹到上限
        1.0 再发事件，事件里记的是**意图值**，而同一帧的
        ``Feedback.energy_change`` 可能**是负的**（还在扣基础代谢与动作消耗）。
        要能量收支就用 ``Feedback``，别用事件计数。

        合法性：这是**症状计数**，不是质量评分（C9 只淘汰、不评分）。
        ``11-phase1-not-doing-list.md`` 给 C9 开的唯一豁免口是
        "观察员评分系统 / 奖励函数……生态级永不；**调试指标除外**"。
        但它没有物理屏障——``FastLoop`` 手里就握着 ``environment``，
        所以"不进控制闭环"是**约定 + 测试**守着的，不是架构保证的。
        """

        return dict(self._event_counts)

    def event_notes(self) -> tuple[tuple[float, str, str, str], ...]:
        """近期事件的可读说明：``(time, event_type, source_id, extra)``。

        回答"这个 ACTION_FAILED 到底为什么失败"。EventVector 没有自由
        文本字段（07 §8.7 刻意如此），但调试不能没有它。
        """

        return tuple(self._event_notes)

    def stats(self) -> dict[str, float]:
        """世界统计。观察员用，不是奖励信号。"""

        return {
            "time": self.time,
            "energy": self.energy,
            "damage": self.damage,
            "fatigue": self.fatigue,
            "alive": float(self.alive),
            "n_objects": float(len(self.objects)),
            "n_resources": float(
                sum(1 for o in self.objects if o.kind == KIND_RESOURCE)
            ),
        }


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def _distance(
    a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]
) -> float:
    n = min(len(a), len(b))
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(n)))


def _unit(vec: tuple[float, ...] | list[float]) -> tuple[float, ...] | None:
    """单位化；零向量返回 None（"方向未指定"，不是"方向为零"）。"""

    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return None
    return tuple(v / norm for v in vec)


def _pad(values: tuple[float, ...] | list[float], size: int) -> list[float]:
    out = list(values[:size])
    out += [0.0] * (size - len(out))
    return out


def _to_object_vector(obj: _WorldObject, agent_pos: list[float]) -> ObjectVector:
    delta = [obj.position[i] - agent_pos[i] for i in range(min(2, len(obj.position)))]
    dist = math.sqrt(sum(v * v for v in delta))
    direction = _unit(delta) if dist > 1e-12 else (0.0, 0.0)
    return ObjectVector(
        object_id=obj.object_id,
        category_id=obj.category_id,
        distance=round(dist, 6),
        direction=tuple(round(v, 6) for v in _pad(direction, 2)),
        velocity=tuple(round(v, 6) for v in _pad(obj.velocity, 2)),
        resource_value=round(obj.resource_value, 6),
        threat_level=round(obj.threat_level, 6),
        affordance=obj.affordance,
    )
