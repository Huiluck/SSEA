"""Skill Library —— 技能库。

**任务书依据**：docs/07-ssea-v0.3.1-charter.md §6.5 +
docs/08-dual-loop-interface-and-gap-closure.md §2.1（注入面）、§3.4（内化）。

职责（07 §6.5 原文）：存储可复用的动作序列或可执行程序。

四个来源与第一阶段的落地：

    成功行为轨迹  → compile_from_trace()        ← 本模块实现
    模型生成代码  → Action.self_modification 的 ADD_SKILL 提案（Milestone 4 接线）
    慢环编译结果  → compile_from_trace() 的产物经 Gate 提交
    遗传继承      → adopt()（GenePackage.skill_library → 本库）

七项必备字段（前置条件 / 动作序列 / 预期结果 / 成功次数 / 失败次数 / 能量消耗 /
最后使用时间）**全部在 07 §8.11 的 Skill 协议里**，本模块不重复定义，
只负责产出与流转。

权威数据在 Structure Store，本类是可写门面
--------------------------------------
``StructureStore`` 是技能的唯一权威（08 §2.1）。本类不另存一份：
它向 Store 提案，过门后由 Store 提升版本号，再从 Store 取新快照。

    SkillLibrary.compile_from_trace(trace)
        → SelfModificationProposal(ADD_SKILL)
        → Verification Gate
        → StructureStore.commit → skills@v+1
        → FastLoopContext（新快照）→ 快环

**因此本类没有任何"直接改技能"的路径。** 这与 Skill Runner 改不了快照里的
Skill 是同一条纪律，也与 08 §2.1「失败天然回滚」同源：Gate 不通过则版本号
不切换，库里看到的还是旧版，不存在回滚操作。

编译出来的技能是开环动作程序
--------------------------
从轨迹里切出来的 ``action_sequence`` 是**当时有效的绝对动作**（世界坐标下的
方向与速率）。重放它只在情境相近时成立——这正是 ``precondition`` 与记忆系统
的情境匹配要负责的事。闭环技能组合（以感知为条件的子动作选择）留到 v0.4+，
见 docs/11。

``precondition`` 是 option 的 initiation set
--------------------------------------------
``Skill`` 在结构上就是一个 **option**（半 MDP，Sutton / Precup / Singh 1999）：

    precondition     ＝ initiation set —— 「在哪些状态下可以启动」，状态集合的谓词
    action_sequence  ＝ policy        —— 启动之后做什么

所以 ``precondition`` 记的必须是 **option 被观测到可以启动的那个状态**，即
**首帧动作前**的能量（``_pre_action_energy``），**不是**首帧动作后的能量。

这个区别不是精度问题，是**描述被当成了判据**：``StepRecord.observation`` 记的是
**动作后**的状态，拿它当门槛，等于要求「复现这条技能自己刚制造出来的峰值」——
最好情形也只剩零余量，于是技能出生之后闸 1 能过的帧往往只剩它出生的那一帧。
实测（2026-09-28，债务 26）：seed 0 编出的技能 ``min_energy = 0.99``，而能量
上限是 1.0；主环 33 次调用**全部**卡在 ``precondition_failed``。

闸在哪一侧：``SkillRunner.report`` 检查时拿到的是**本帧动作后**的身体状态，而
它恰好是**下一帧动作前**的状态——也就是「要不要继续这条 option」的那个决策点。
所以按 initiation set 的语义，检查点本身是对的；错的只是被拿来比较的那个**数**
取错了状态。``_pre_action_energy`` 把那个数取回它该在的状态。

``energy_cost`` 是**每帧毛**成本
---------------------------
Skill Runner 的中止判据是 ``body.energy < energy_cost × 剩余帧数``
（见 skill_runner.py），故 ``energy_cost`` 必须按帧计。编译时取该段轨迹的
**平均每帧能量损失**（净收益为正的帧计 0）。

刻意不取"净消耗"：编译只收净收益为正的段，取净会让每条技能的
``energy_cost`` 恒为 0——一个永远为 0 的字段就是死字段。取毛才有信息量：
"这条技能每帧烧多少"正是中止判据要用的量。

这个单位不在 07 §8.11 里写明，是消费方反推出来的约定——
由 ``tests/test_skill_library.py`` 钉住。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Iterable, Mapping, Sequence

# StepRecord 与 STATE_RUN 同住 fast_loop——技能库消费的就是快环产出的 trace。
# 依赖方向是 慢环组件 → 快环产物，fast_loop 不引用本模块，故不成环。
from .fast_loop import STATE_RUN, StepRecord
from .sse_protocols import (
    FastLoopContext,
    Feedback,
    GateResult,
    Skill,
    StructureStore,
)
from .sse_protocols.self_modification import SelfModificationProposal
from .sse_protocols.structure_store import AuditRecord

#: 编译来源标记。写进 ``Skill.created_from``，是标记不是描述。
SOURCE_COMPILED = "skill_compiler:trace"

#: 来源标记 → 技能来源。对应 07 §6.5 的四个来源，供观察员分流统计。
SOURCE_INHERITED = "gene:inherited"


@dataclass(frozen=True)
class SkillLibraryConfig:
    """技能库配置。"""

    #: 一段轨迹至少几帧才值得固化成技能。短于它的序列没有压缩价值。
    min_frames: int = 3

    #: 一段轨迹至多几帧。更长的按此长度切窗（见 ``_windows``）。
    max_frames: int = 12

    #: 调用次数达到此数后才允许因低成功率被淘汰。
    #: 没用过的技能不淘汰——没有证据说它坏。
    min_attempts: int = 3

    #: 成功率低于此值且调用次数足够 → 可淘汰。
    min_success_rate: float = 0.34

    #: 库内技能数上限。超出时最差的那些进入 ``prunable()``。
    max_skills: int = 64


class SkillLibrary:
    """技能的存储 / 编译 / 提案 / 淘汰。

    用法::

        lib = SkillLibrary()
        records = lib.compile_and_save(trace, GateResult(passed=True), t)
        ctx = lib.context            # 新快照，可直接交给快环

    本类**不持有** ``FastLoop``。快环只读快照，不知道慢环存在（08 §2.1）；
    让库去改一个正在跑的环会打破这条边界。
    """

    def __init__(
        self,
        store: StructureStore | None = None,
        config: SkillLibraryConfig | None = None,
    ) -> None:
        self.store = store if store is not None else StructureStore()
        self.config = config or SkillLibraryConfig()
        self._context: FastLoopContext = self.store.snapshot()
        self._seq = 0

    # ------------------------------------------------------------------
    #  读取
    # ------------------------------------------------------------------

    @property
    def context(self) -> FastLoopContext:
        """当前快照。每有一次提案被应用就刷新。"""
        return self._context

    @property
    def skills(self) -> Mapping[str, Skill]:
        return self._context.skills

    def get(self, skill_id: str) -> Skill | None:
        """按 id 取技能。查表，不是搜索（C4 低算力）。"""
        return self._context.get_skill(skill_id)

    def __len__(self) -> int:
        return len(self._context.skills)

    def sync(self) -> FastLoopContext:
        """从 Store 重新取快照。

        慢环可能通过别的路径提交了提案（如 Milestone 4 的 Experience
        Compiler 直接调 Store）。本类不假设自己是唯一写入方。
        """

        self._context = self.store.snapshot()
        return self._context

    # ------------------------------------------------------------------
    #  编译：成功行为轨迹 → 技能
    # ------------------------------------------------------------------

    def compile_from_trace(self, trace: Sequence[StepRecord]) -> tuple[Skill, ...]:
        """从快环 trace 里切出成功行为轨迹，固化为技能候选。

        "成功"的判据是**净能量收益**：``sum(energy_change) > 0``。
        不用奖励函数——SSEA 只有淘汰函数（C9），而能量是唯一的世界计价物。

        只编译**直接解码**出来的动作：``executed_action is decoded_action``。
        技能执行中的子动作不参与编译，否则会把已有技能抄一份。

        本方法委托给模块级 ``compile_skills``——Milestone 4 的 Experience
        Compiler 要用同一份切分规则，而不该为了复用它去持有一个 Store。
        """

        return compile_skills(trace, self.config)

    def new_skills(
        self, candidates: Iterable[Skill]
    ) -> tuple[Skill, ...]:
        """从候选里滤掉库里已有的（按 skill_id，即按轨迹签名）。"""

        return tuple(s for s in candidates if s.skill_id not in self.skills)

    def compile_and_save(
        self,
        trace: Sequence[StepRecord],
        gate: GateResult,
        timestamp: float,
    ) -> tuple[AuditRecord, ...]:
        """编译 + 保存。验收「模型可以保存技能」的单次调用路径。"""

        return tuple(
            self.save(skill, gate, timestamp)
            for skill in self.new_skills(self.compile_from_trace(trace))
        )

    # ------------------------------------------------------------------
    #  提案
    # ------------------------------------------------------------------

    def save(
        self, skill: Skill, gate: GateResult, timestamp: float
    ) -> AuditRecord:
        """保存一条新技能。产物是 ADD_SKILL 提案，必须过门。"""

        if skill.skill_id in self.skills:
            raise ValueError(
                f"技能 {skill.skill_id!r} 已在库中；更新请用 update()。"
                f"ADD_SKILL 与 UPDATE_SKILL 在 Store 里都是写入，"
                f"但审计日志必须能区分「新增」与「回写统计」。"
            )
        return self._commit(
            "ADD_SKILL",
            skill.skill_id,
            {"skill": skill},
            gate,
            timestamp,
            reason=(
                f"compiled frames={skill.total_frames()} "
                f"outcome={skill.expected_outcome.get('outcome', '?')}"
            ),
            expected_effect={
                "frames": skill.total_frames(),
                "energy_change": float(
                    skill.expected_outcome.get("energy_change", 0.0)
                ),
                "energy_cost_per_frame": skill.energy_cost,
            },
            risk_level="low",
        )

    def update(
        self, skill: Skill, gate: GateResult, timestamp: float
    ) -> AuditRecord:
        """回写一条已有技能的统计（Skill Runner 的 updated_skill() 产物）。"""

        if skill.skill_id not in self.skills:
            raise ValueError(
                f"技能 {skill.skill_id!r} 不在库中；新增请用 save()。"
            )
        return self._commit(
            "UPDATE_SKILL",
            skill.skill_id,
            {"skill": skill},
            gate,
            timestamp,
            reason=(
                f"stats success={skill.success_count} "
                f"failure={skill.failure_count}"
            ),
            expected_effect={
                "success_count": skill.success_count,
                "failure_count": skill.failure_count,
            },
            risk_level="low",
        )

    def disable(
        self, skill_id: str, gate: GateResult, timestamp: float
    ) -> AuditRecord:
        """下线一条技能。产物是 DISABLE_SKILL 提案。"""

        return self._commit(
            "DISABLE_SKILL",
            skill_id,
            {},
            gate,
            timestamp,
            reason="prunable",
            expected_effect={"removed": skill_id},
            risk_level="medium",
        )

    def adopt(
        self,
        skills: Iterable[Skill],
        gate: GateResult,
        timestamp: float,
    ) -> tuple[AuditRecord, ...]:
        """从基因包载入遗传技能。对应 07 §6.5 的来源「遗传继承」。

        同 id 已存在时走 ``update()``：子代继承的是父代的版本，
        覆盖是继承的语义，不是意外。
        """

        out: list[AuditRecord] = []
        for skill in skills:
            inherited = replace_created_from(skill, SOURCE_INHERITED)
            if inherited.skill_id in self.skills:
                out.append(self.update(inherited, gate, timestamp))
            else:
                out.append(self.save(inherited, gate, timestamp))
        return tuple(out)

    # ------------------------------------------------------------------
    #  淘汰建议
    # ------------------------------------------------------------------

    def prunable(self) -> tuple[str, ...]:
        """建议下线的技能 id。**只建议，不执行**——下线也要过 Gate。

        两类会进名单：

        1. 调用次数足够且成功率低于 ``min_success_rate``；
        2. 库内超容时，按成功率升序补足差额（从未调用的技能不参与——
           没有证据说它坏）。
        """

        cfg = self.config
        used: list[tuple[float, str]] = []
        low: set[str] = set()
        for skill_id, skill in self.skills.items():
            attempts = skill.success_count + skill.failure_count
            if attempts == 0:
                continue
            rate = skill.success_count / attempts
            used.append((rate, skill_id))
            if attempts >= cfg.min_attempts and rate < cfg.min_success_rate:
                low.add(skill_id)

        excess = len(self.skills) - cfg.max_skills
        if excess > 0:
            for _, skill_id in sorted(used)[:excess]:
                low.add(skill_id)
        return tuple(sorted(low))

    # ------------------------------------------------------------------
    #  内部
    # ------------------------------------------------------------------

    def _commit(
        self,
        proposal_type: str,
        target: str,
        payload: dict,
        gate: GateResult,
        timestamp: float,
        *,
        reason: str,
        expected_effect: dict,
        risk_level: str,
    ) -> AuditRecord:
        self._seq += 1
        proposal = SelfModificationProposal(
            proposal_id=f"skill-{self._seq:06d}",
            proposal_type=proposal_type,
            target=target,
            payload=payload,
            reason=reason,
            expected_effect=expected_effect,
            risk_level=risk_level,
        )
        record = self.store.commit(proposal, gate, timestamp)
        if record.applied:
            # 只在真的应用后刷新快照。被驳回时版本号没变，旧快照继续有效——
            # 这就是 08 §2.1 的"失败天然回滚"：没有东西被应用，故无需回滚。
            self._context = self.store.snapshot()
        return record

    def _skill_for(self, chunk: Sequence[StepRecord], total: float) -> Skill:
        """一段成功轨迹 → 一条技能。委托给模块级同名函数。"""

        return _skill_for(chunk, total)


def compile_skills(
    trace: Sequence[StepRecord], config: SkillLibraryConfig | None = None
) -> tuple[Skill, ...]:
    """轨迹 → 技能候选。**纯函数**：不碰 Store，不提提案。

    ``SkillLibrary.compile_from_trace`` 与 Milestone 4 的
    ``ExperienceCompiler`` 共用这一份实现。写成两份必然漂移，而漂移的表现是
    「同一条轨迹编译出两条不同的技能」——那种不一致在任何运行时报错里都看不见，
    只会在审计日志里表现为两条语义相同的提案。
    """

    cfg = config or SkillLibraryConfig()
    return tuple(_skill_for(chunk, total) for chunk, total in _segments(trace, cfg))


def _skill_for(chunk: Sequence[StepRecord], total: float) -> Skill:
    """一段成功轨迹 → 一条技能。

    ``precondition`` 取**首帧动作前**的能量，即这条 option 被观测到「可以在此
    启动」的那个状态——initiation set 上的一个样本。取动作后的能量会把它变成
    「复现这条技能自己刚制造的峰值」，见模块 docstring 与 ``_pre_action_energy``。
    """

    first, last = chunk[0], chunk[-1]
    sequence = tuple(rec.executed_action for rec in chunk)
    precondition = {"min_energy": round(_pre_action_energy(first), 6)}
    signature = _signature(sequence, precondition)
    outcome = _outcome_marker(last.feedback)
    return Skill(
        skill_id=f"sk_{signature[:10]}",
        name=f"seq:{len(sequence)}f:{outcome}",
        precondition=precondition,
        action_sequence=sequence,
        expected_outcome={
            "energy_change": round(total, 6),
            "frames": len(sequence),
            "outcome": outcome,
        },
        success_count=0,
        failure_count=0,
        # 每帧**毛**成本：各帧能量损失的均值（净收益为正的帧计 0）。
        # Skill Runner 的中止判据按"剩余帧数 × 每帧成本"算，要的是
        # 这条技能每帧烧多少，不是这段轨迹净赚多少。
        #
        # 刻意不用 ``max(0, -total) / n``：净收益为正的段会被它钳成 0，
        # 于是每条编译出来的技能 energy_cost 恒为 0——一个永远为 0 的
        # 字段就是死字段，而「协议不容无消费者的通道」这条纪律对字段
        # 同样成立（08 §2.4）。
        energy_cost=round(_gross_per_frame_cost(chunk), 6),
        created_from=SOURCE_COMPILED,
        # 从未作为技能被调用过。行为发生过，但那是轨迹，不是这次调用。
        last_used=0.0,
        metadata={"signature": signature},
    )


# ----------------------------------------------------------------------
#  轨迹切分
# ----------------------------------------------------------------------


def _gross_per_frame_cost(chunk: Sequence[StepRecord]) -> float:
    """一段轨迹的每帧**毛**能量成本。

    各帧能量损失的均值，净收益为正的帧计 0。之所以取毛而非净：编译只收
    净收益为正的段，取净会让每条技能的成本恒为 0（见 ``_skill_for`` 的注释）。
    """

    spent = sum(max(0.0, -rec.feedback.energy_change) for rec in chunk)
    return spent / len(chunk)


def _is_direct_success(rec: StepRecord) -> bool:
    """这一帧是否是"模型自己做对了一个动作"。

    四个条件都要：

    - ``state == RUN``：睡眠 / 唤醒帧没有动作，整理它们没有意义；
    - ``survived``：终帧之后没有未来；
    - ``action_success``：动作真的生效了（与 ACTION_FAILED 事件同一判断）；
    - ``executed_action is decoded_action``：**不是**技能展开出来的子动作。
      抄一条已有技能的动作序列得到一条新技能，是复制不是学习。
    """

    return (
        rec.state == STATE_RUN
        and rec.feedback.survived
        and rec.feedback.action_success
        and rec.executed_action is rec.decoded_action
    )


def _pre_action_energy(rec: StepRecord) -> float:
    """``rec`` 这一帧**动作前**的身体能量——option 的 initiation state。

    ``StepRecord.observation`` 是**动作后**的状态：``FastLoop._step_run`` 把它
    记在 ``Environment.step`` **之后**。而模型是拿着动作**前**的那份观测做决策的
    （``_step_run`` 开头的 ``obs = self.observation``），本函数要的是后者。

    两者之间隔着这一帧自己的动作后果，所以不能直接读 ``observation``。
    还原式是精确的，不是估计：``Environment._finish_step`` 把 ``energy_change``
    定义成 ``post - energy_before``，而 ``energy_before`` 取在 ``step()`` 的开口处
    ——即这一帧决策所用的那份观测里的能量。故 ``post - change`` 恒等于动作前能量。
    夹取（``max(0.0, ...)`` / ``min(1.0, ...)``）不破坏它：夹取已经体现在 ``post``
    与 ``change`` 里，两者相减把它抵消掉了。

    ⚠️ 这条恒等式是**跨模块假设**（环境定义、技能库消费），故由
    ``tests/test_skill_library.py`` 的 ``TestPreActionEnergyIsTheDecisionState``
    在真实快环 trace 上钉住——它不是纸面推导，是一条会红的断言。
    """

    return rec.observation.body.energy - rec.feedback.energy_change


def _segments(
    trace: Sequence[StepRecord], cfg: SkillLibraryConfig
) -> tuple[tuple[tuple[StepRecord, ...], float], ...]:
    """trace → [((帧...), 净能量变化)]，只留净收益为正的段。"""

    runs: list[list[StepRecord]] = []
    current: list[StepRecord] = []
    for rec in trace:
        if _is_direct_success(rec):
            current.append(rec)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)

    out: list[tuple[tuple[StepRecord, ...], float]] = []
    for run in runs:
        for chunk in _windows(run, cfg):
            total = sum(rec.feedback.energy_change for rec in chunk)
            if total > 0.0:
                out.append((tuple(chunk), total))
    return tuple(out)


def _windows(
    run: Sequence[StepRecord], cfg: SkillLibraryConfig
) -> list[tuple[StepRecord, ...]]:
    """把一段连续成功的轨迹切成可固化的窗口。

    短于 ``max_frames`` 的整段收下；更长的按 ``max_frames`` 切窗，
    末尾不足 ``min_frames`` 的余料丢弃。

    整段拒绝（而不是切窗）会让"活了很久且一直成功"的轨迹产出**零**条技能——
    那正好是最该被固化的一类。切窗是压缩，不是放任长度。
    """

    if len(run) <= cfg.max_frames:
        return [tuple(run)] if len(run) >= cfg.min_frames else []
    chunks: list[tuple[StepRecord, ...]] = []
    for start in range(0, len(run) - cfg.min_frames + 1, cfg.max_frames):
        chunk = tuple(run[start : start + cfg.max_frames])
        if len(chunk) >= cfg.min_frames:
            chunks.append(chunk)
    return chunks


# ----------------------------------------------------------------------
#  签名
# ----------------------------------------------------------------------


def _signature(sequence: Sequence[object], precondition: Mapping) -> str:
    """动作序列 + 前置条件 → 稳定摘要。

    用 sha1 而非内置 ``hash()``：后者每个进程都不同，同一份轨迹在两台机器上
    会编出不同的 skill_id，"这条技能是否已存在"就不可判定了。
    浮点先取四位小数，否则末位抖动会让同一段行为签出两个名。
    """

    payload = json.dumps(
        {
            "precondition": _rounded(dict(precondition)),
            "sequence": [_rounded(asdict(a)) for a in sequence],  # type: ignore[arg-type]
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _rounded(value: object, digits: int = 4) -> object:
    """递归地把所有浮点取到固定位数，其余原样返回。"""

    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, dict):
        return {k: _rounded(v, digits) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_rounded(v, digits) for v in value)
    return value


def _outcome_marker(feedback: Feedback) -> str:
    """与 memory_system._outcome_marker 同一套标记。

    刻意重复而不是 import：两个模块的标记若共用一处，将来给记忆加一种结果
    就会顺带改掉技能的 expected_outcome，而两者本就不该耦合。
    """

    if feedback.damage_change > 0.0:
        return "damaged"
    if feedback.energy_change > 0.0:
        return "energy_gain"
    if feedback.energy_change < 0.0:
        return "energy_loss"
    return "neutral"


def replace_created_from(skill: Skill, source: str) -> Skill:
    """返回一个改了 ``created_from`` 的技能副本。

    ``Skill`` 是 frozen dataclass，且住在不可变快照里；改写来源标记必须
    产副本，不能就地改。
    """

    return replace(skill, created_from=source)
