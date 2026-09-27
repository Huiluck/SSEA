"""Skill Runner —— 技能执行器（第 11 个模块）。

**新增依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.3。

症状：07 §8.11 定义了 ``Skill.action_sequence: list[Action]``，但快环公式
每步只产出一个动作，十个模块里**没有一个**负责把序列逐帧执行——技能被定义了，
却无法运行。

置于 **Action Decoder 之后、Environment 之前**：

    State Core → intent_vector
                      ↓
              Action Decoder → Action
                      ↓
              Skill Runner ← 若 skill 通道非空：查 Skill Library，
              │               取 action_sequence，按 params 实例化，
              │               逐帧吐出子动作（每步一个）
              ↓
              Environment.step(sub_action)

中止条件（任一命中即中断并回报 SKILL_FAILURE，08 §2.3）
------------------------------------------------------
1. 前置条件 ``precondition`` 不再满足
2. 能量低于该技能 ``energy_cost`` 的剩余需求
3. 环境变化使后续子动作非法（由 Environment 第二执行点检出）

SSEA 意义
--------
技能是压缩的行为先验，**查表比每步重新推理更省算力**。这是 C4「低算力」
真正的落地机制，也解释了为什么技能库增长不会导致算力爆炸——技能是查表，
不是搜索。

使用统计的归属
------------
``Skill`` 是 frozen dataclass 且住在不可变快照里，Runner 不能就地改它。
故 Runner 只维护外部统计，经 ``updated_skill()`` 产出一个带新统计的
Skill 副本——由慢环（Milestone 4）以 ``UPDATE_SKILL`` 提案提交回
Structure Store。这与"所有自我修改必须过验证门"一致：Runner 改不了技能，
只能提案。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .sse_protocols import (
    Action,
    BodyState,
    FastLoopContext,
    Observation,
    Skill,
)


#: 中止原因。
ABORT_PRECONDITION = "precondition_failed"
ABORT_ENERGY = "energy_insufficient"
ABORT_ENV = "environment_rejected"


@dataclass
class SkillStats:
    """单个技能的运行统计。由 Runner 维护，不写回快照。"""

    success_count: int = 0
    failure_count: int = 0
    executed_frames: int = 0
    last_used: float = 0.0


@dataclass
class SkillRun:
    """一次正在执行的技能实例。"""

    skill: Skill
    #: 下一个待执行子动作的索引。
    cursor: int = 0
    #: 已执行帧数（本技能生命周期内累计，含本次）。
    frames_done: int = 0
    aborted: bool = False
    abort_reason: str | None = None

    @property
    def is_finished(self) -> bool:
        return self.cursor >= len(self.skill.action_sequence)


class SkillRunner:
    """逐帧展开 ``Action.skill`` 为子动作。

    用法::

        runner = SkillRunner(context)
        runner.submit(action, body, observation)   # 每帧调用
        sub = runner.current_action()              # 本帧真正执行的动作
        runner.report(feedback, observation)       # 每帧调用，推进游标

    ``submit`` 与 ``report`` 分开是有意的：环境在 ``step()`` 之前需要知道
    要执行哪个动作，在 ``step()`` 之后才能给出反馈。
    """

    def __init__(self, context: FastLoopContext) -> None:
        self.context = context
        self.stats: dict[str, SkillStats] = {}
        self._run: SkillRun | None = None

    # ------------------------------------------------------------------
    #  提交
    # ------------------------------------------------------------------

    def submit(
        self,
        action: Action,
        body: BodyState,
        observation: Observation,
    ) -> None:
        """接收本帧 Action。若带技能调用则开始 / 继续一次技能执行。"""

        if action.calls_skill():
            assert action.skill is not None
            skill = self.context.get_skill(action.skill.skill_id)
            if skill is None:
                # 技能不存在：不启动执行，退回普通动作路径。
                # 这里不抛异常——技能库可能刚被 DISABLE_SKILL 改过，
                # 而快环持有的快照是旧的。
                self._run = None
                return
            if self._run is None or self._run.skill.skill_id != skill.skill_id:
                self._run = SkillRun(skill=skill)
            return

        # 无技能调用：若正在执行技能，视为中断（模型主动放弃）
        if self._run is not None:
            self._abort(self._run, ABORT_ENV, observation.time)
            self._run = None

    # ------------------------------------------------------------------
    #  取本帧动作
    # ------------------------------------------------------------------

    def current_action(self, fallback: Action) -> Action:
        """返回本帧应执行的动作。

        有技能在执行 → 当前子动作；否则 → ``fallback``（Action Decoder 的原产物）。
        """

        if self._run is None:
            return fallback
        return self._run.skill.action_sequence[self._run.cursor]

    @property
    def running_skill_id(self) -> str | None:
        return self._run.skill.skill_id if self._run is not None else None

    # ------------------------------------------------------------------
    #  反馈
    # ------------------------------------------------------------------

    def report(
        self,
        feedback_success: bool,
        body: BodyState,
        observation: Observation,
    ) -> str | None:
        """消费本帧环境反馈，推进技能游标。

        返回本次产生的事件类型（``SKILL_SUCCESS`` / ``SKILL_FAILURE``），
        无事件则返回 None。
        """

        if self._run is None:
            return None

        run = self._run
        skill = run.skill
        stats = self.stats.setdefault(skill.skill_id, SkillStats())
        stats.last_used = observation.time

        # 中止条件 1：前置条件不再满足
        if not _precondition_holds(skill, body):
            return self._abort(run, ABORT_PRECONDITION, observation.time)

        # 中止条件 2：能量不足以支撑该技能的剩余成本
        # ``- 1``：本帧的子动作已经执行完、成本已经付掉了。``cursor`` 指向
        # 的是**下一个**待执行项，故真正未付费的是 ``len - cursor - 1`` 帧。
        # 少了这个 -1 会多算一步：3 步、每步 0.1 的技能在能量 0.25 时会被
        # 判为差 0.3，于是第一帧就中止——而它本可以跑完前两步。
        remaining = max(0, len(skill.action_sequence) - run.cursor - 1)
        if remaining > 0 and body.energy < skill.energy_cost * remaining:
            return self._abort(run, ABORT_ENERGY, observation.time)

        # 中止条件 3：环境判定本子动作非法
        if not feedback_success:
            return self._abort(run, ABORT_ENV, observation.time)

        run.cursor += 1
        run.frames_done += 1
        stats.executed_frames += 1

        if run.is_finished:
            stats.success_count += 1
            self._run = None
            return "SKILL_SUCCESS"
        return None

    # ------------------------------------------------------------------
    #  统计与回写
    # ------------------------------------------------------------------

    def _abort(self, run: SkillRun, reason: str, timestamp: float) -> str:
        run.aborted = True
        run.abort_reason = reason
        stats = self.stats.setdefault(run.skill.skill_id, SkillStats())
        stats.failure_count += 1
        stats.last_used = timestamp
        self._run = None
        return "SKILL_FAILURE"

    def stats_for(self, skill_id: str) -> SkillStats:
        return self.stats.setdefault(skill_id, SkillStats())

    def updated_skill(self, skill_id: str) -> Skill | None:
        """产出带最新统计的 Skill 副本，供慢环提案使用。

        快照中没有该技能时返回 None。
        """

        skill = self.context.get_skill(skill_id)
        if skill is None:
            return None
        stats = self.stats_for(skill_id)
        return replace(
            skill,
            success_count=stats.success_count,
            failure_count=stats.failure_count,
            last_used=stats.last_used,
            metadata={**skill.metadata, "executed_frames": stats.executed_frames},
        )

    def consolidatable_skills(
        self, min_success_count: int = 3, min_executed_frames: int = 30
    ) -> tuple[str, ...]:
        """满足本能内化条件的技能 id（08 §3.4）。

        由 Experience Compiler（Milestone 4）消费。
        """

        out: list[str] = []
        for skill_id in self.context.skills:
            updated = self.updated_skill(skill_id)
            if updated is None:
                continue
            if updated.is_consolidatable(min_success_count, min_executed_frames):
                out.append(skill_id)
        return tuple(out)


# ----------------------------------------------------------------------
#  前置条件检查
# ----------------------------------------------------------------------


def _precondition_holds(skill: Skill, body: BodyState) -> bool:
    """检查 Skill.precondition。**检查方是 Skill Runner**（08 §2.3）。

    第一阶段只支持 ``min_energy`` 一个键——协议里 ``precondition`` 是自由
    dict，加键需同步扩展此处，并由测试固定行为。
    """

    pre = skill.precondition
    if "min_energy" in pre:
        if body.energy < float(pre["min_energy"]):
            return False
    return True
