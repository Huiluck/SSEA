"""实验脚手架：跑一轮快环，把它身上的量收成数字。

设计上有三条刻意的选择：

**一、量从 trace 与审计日志取，不从事件流取。**
``Environment._event_notes`` 是 16 槽环形缓冲（12 §6 债务 10），
"跑完再统计事件流"会**静默漏掉早期事件**——本次核对时它真的咬过一次：
「跑完统计 ``ENERGY_GAINED``」得到 0 次，而逐帧追踪显示第 10 帧确实
``grasp: +0.356 energy``。所以本模块的累计量一律逐帧现加，
或者直接读 ``StructureStore.audit_log()``（那是 append-only 的，不丢）。

**二、每个数字都必须能被人复跑。**
``run_episode`` 的种子与帧数是显式参数，且 ``torch.manual_seed`` 在
**构造任何对象之前**调用——记忆门控与操纵门控的开启与否由随机初始化决定
（12 §4.3），种子的位置换一下就是另一场抽奖。

**三、脚本输出是给人看的。**
不打印 tensor，不打印中间态，只打印能写进 12 §4.2 表格的那几行。
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import torch

from SSEA.environment import Environment
from SSEA.experience_compiler import make_slow_loop_hook
from SSEA.fast_loop import STATE_RUN, STATE_SLEEP, STATE_WAKE, FastLoop, FastLoopConfig
from SSEA.plasticity import LocalPlasticity
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate

#: 实验默认用的随机种子集。八个足够看出「一半 seed 门不开」这类双峰现象。
DEFAULT_SEEDS: tuple[int, ...] = tuple(range(8))

#: 实验默认帧数。够跑到默认世界里的自然死亡（60–90 帧），留一倍余量。
DEFAULT_FRAMES = 200


@dataclass
class EpisodeResult:
    """一轮 episode 的原始量。派生指标做成属性，避免两处各算一遍。"""

    seed: int
    frames: int
    alive: bool
    run_frames: int
    sleep_frames: int
    wake_frames: int
    constraint_rejected: int
    internal_errors: int
    max_consecutive_run: int
    language_crossings: int
    observation_leaks: int
    proposals: int
    applied: int
    rejected: int
    #: 睡眠**段数**（极大连续 SLEEP 段），不是睡眠帧数。
    #: 实验 7 的「慢环触发成功率」分母是它：一次睡眠应当正好触发一次慢环。
    sleep_episodes: int = 0
    #: 慢环钩子被真正调用的次数。与 ``sleep_episodes`` 之差就是漏触发。
    slow_loop_calls: int = 0
    rejected_kinds: tuple[str, ...] = ()
    version_bumps: int = 0
    audited_bumps: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    # ---- 派生指标（12 §4.2 表格里的那几列）----

    @property
    def action_legality_rate(self) -> float:
        """动作合法率 = 1 − 被约束执行点拒掉的帧数 / RUN 帧数。

        注意分母是 RUN 帧：睡眠帧不产生动作，把它算进分母会凭空拉高合法率。
        """
        if self.run_frames == 0:
            return 0.0
        return 1.0 - self.constraint_rejected / self.run_frames

    @property
    def interface_error_rate(self) -> float:
        """接口异常率 = 触发内部兜底的帧数 / 总帧数。

        这一列**应当恒为 0**——环境把任何未预期异常转成
        ``action_success=False`` + ACTION_FAILED，不崩溃（08 §2.6.2）。
        """
        if self.frames == 0:
            return 0.0
        return self.internal_errors / self.frames

    @property
    def sleep_entry(self) -> bool:
        return self.sleep_frames > 0

    @property
    def audit_completeness(self) -> float:
        """版本切换审计记录完整率 = 有审计记录的升版次数 / 总升版次数。"""
        if self.version_bumps == 0:
            return 1.0  # 没升过版，"每次都记了"空真
        return self.audited_bumps / self.version_bumps


def build_slow_loop(
    store: StructureStore,
    *,
    env_frames: int = 8,
    plasticity: bool = True,
) -> Callable[[Sequence[Any]], Any]:
    """标准的慢环钩子：ExperienceCompiler → VerificationGate → StructureStore。"""
    return make_slow_loop_hook(
        store,
        VerificationGate(GateConfig(env_frames=env_frames)),
        plasticity=LocalPlasticity() if plasticity else None,
    )


def run_episode(
    seed: int,
    *,
    frames: int = DEFAULT_FRAMES,
    min_sleep_frames: int = 5,
    monitor: Any | None = None,
    store: StructureStore | None = None,
    slow_loop: Callable[[Sequence[Any]], Any] | None = None,
    watch_language: bool = False,
) -> EpisodeResult:
    """跑一轮，把量收齐。

    ``watch_language=True`` 时逐帧检查有无 ``str`` 值跨越控制边界。
    这是实验 1 的第四个指标，也是**唯一一个只能运行时测的**——
    静态字段检查已由 ``tests/test_protocol_consistency.py`` 守着，
    但"字段里没有 str"不等于"运行时没有 str 流过去"。
    """

    # 必须在构造任何对象之前——门控开不开由这里的种子决定（12 §4.3）。
    torch.manual_seed(seed)

    store = store if store is not None else StructureStore()
    if slow_loop is None:
        slow_loop = build_slow_loop(store)

    # 包一层数调用次数。快环在睡眠末尾调它一次，所以"调用次数"就是
    # 「慢环真的被触发了几次」——比从版本号倒推可靠：慢环被触发但
    # 一条提案都没提时，版本号不动。
    calls = 0

    def counted_slow_loop(trace):
        nonlocal calls
        calls += 1
        return slow_loop(trace)

    loop = FastLoop(
        Environment(seed=seed),
        _context(),
        metabolic_monitor=monitor,
        config=FastLoopConfig(max_frames=frames, min_sleep_frames=min_sleep_frames),
        slow_loop=counted_slow_loop,
    )

    rejected_total = 0
    internal_total = 0
    language_crossings = 0
    observation_leaks = 0

    while loop.alive and len(loop.trace()) < frames:
        if watch_language:
            # 决策边界：进入解码器之前的隐藏状态。
            language_crossings += count_strs_deep(loop.hidden)
        loop.step()
        record = loop.trace()[-1]

        if record.feedback is not None:
            rejected_total += record.feedback.notes.count("constraint_rejected:")
            internal_total += record.feedback.notes.count("internal_error:")

        if watch_language:
            # 发出边界：这一帧真正送进环境的动作。
            language_crossings += count_strs_deep(record.executed_action)
            # 感知边界：这一帧落到模型眼前的观测。
            observation_leaks += observation_str_leaks(record.observation)

    trace = loop.trace()
    audit = store.audit_log()
    applied = [a for a in audit if a.applied]
    rejected = [a for a in audit if not a.applied]

    return EpisodeResult(
        seed=seed,
        frames=len(trace),
        alive=loop.alive,
        run_frames=sum(1 for r in trace if r.state == STATE_RUN),
        sleep_frames=sum(1 for r in trace if r.state == STATE_SLEEP),
        wake_frames=sum(1 for r in trace if r.state == STATE_WAKE),
        constraint_rejected=rejected_total,
        internal_errors=internal_total,
        max_consecutive_run=max_consecutive_clean_run(trace),
        language_crossings=language_crossings,
        observation_leaks=observation_leaks,
        proposals=len(audit),
        applied=len(applied),
        rejected=len(rejected),
        sleep_episodes=count_sleep_episodes(trace),
        slow_loop_calls=calls,
        rejected_kinds=tuple(sorted({a.kind for a in rejected})),
        # 审计完整性：每次升版都该有一条 from→to 连续的 applied 记录。
        version_bumps=sum(1 for a in applied if a.to_version == a.from_version + 1),
        audited_bumps=len(applied),
    )


def _context():
    """快环上下文。从 ``tests/conftest`` 取，与测试用同一个构造点。"""
    from tests.conftest import make_context

    return make_context()


def count_sleep_episodes(trace: Sequence[Any]) -> int:
    """极大连续 SLEEP 段的段数——"睡着了几次"，不是"睡了几帧"。

    实验 7 的睡眠进入率若按帧数算，一次长睡会把比率抬得很高，
    掩盖"其实只睡过一次"。按段数算才对得上"慢环触发了几次"。
    """

    return sum(
        1
        for prev, cur in zip(trace, trace[1:])
        if cur.state == STATE_SLEEP and prev.state != STATE_SLEEP
    ) + (1 if trace and trace[0].state == STATE_SLEEP else 0)


def max_consecutive_clean_run(trace: Sequence[Any]) -> int:
    """最长的一段「RUN 且未触发约束拒绝/内部异常」的连续帧。

    拒绝打断的是**连续闭环**，不是存活——所以实验 1 数它，不数总帧数。
    """
    best = 0
    current = 0
    for record in trace:
        if record.state != STATE_RUN:
            current = 0
            continue
        notes = record.feedback.notes if record.feedback is not None else ""
        if "constraint_rejected:" in notes or "internal_error:" in notes:
            current = 0
            continue
        current += 1
        best = max(best, current)
    return best


# ----------------------------------------------------------------------
#  自然语言越界检查（实验 1 的第四个指标）
# ----------------------------------------------------------------------

#: 这些字段装的是**名字**（id 与事件类型），不是被传递的正文。
#:
#: 它比 ``tests/test_protocol_consistency.py::TestNoNaturalLanguageInLoop``
#: 的白名单**多四个**，那四个是本次实验发现的守卫缺口：静态检查只扫了
#: ``Action`` 的顶层字段名（六个通道名），**没扫通道内部**——于是
#: ``Manipulation.target_id`` / ``operation``、``SkillCall.skill_id``、
#: ``SelfModification.proposal_type`` 这四个 str 字段从来没被检查过。
#: 它们确实都是名字（前两个是对象 id 与操作码，后两个是技能 id 与提案类型），
#: 所以不是违规；但"没人检查过"与"检查过没问题"是两件事。
#: 见本目录 ``README.md`` 的「本次实验发现的守卫缺口」。
IDENTIFIER_FIELDS = frozenset(
    {
        # Observation / Feedback / EventVector / MemoryItem（静态检查已覆盖）
        "object_id",
        "category_id",
        "event_id",
        "event_type",
        "source_id",
        "id",
        "type",
        "outcome",
        "notes",
        "time_phase",
        # Action 通道内部（静态检查**未**覆盖，本次补上）
        "target_id",
        "operation",
        "skill_id",
        "proposal_type",
    }
)

#: 操作码的**闭词表**。标识符允许出现，但必须取自一张封闭的表——
#: 否则 ``operation`` 就成了一个"可以往里写任何字符串"的字段，
#: 而"可以写任何字符串"正是正文的入口。名字与正文的分界就在这里：
#: 名字取自闭集，正文不是。
OPCODE_VOCABULARIES: dict[str, frozenset[str]] = {}


def _opcode_vocabularies() -> dict[str, frozenset[str]]:
    """惰性构造闭词表——避免在 import 期拉起整个协议包。"""
    if OPCODE_VOCABULARIES:
        return OPCODE_VOCABULARIES
    from SSEA.sse_protocols.action_space import OPERATIONS
    from SSEA.sse_protocols.self_modification import ALLOWED_PROPOSAL_TYPES

    OPCODE_VOCABULARIES.update(
        {
            "operation": frozenset(OPERATIONS),
            "proposal_type": frozenset(ALLOWED_PROPOSAL_TYPES),
        }
    )
    return OPCODE_VOCABULARIES


def observation_str_leaks(observation: Any) -> int:
    """``Observation`` 里出现了几个**非标识符**的 str 值。

    对象 id 与时间相位名是标识符（07 §8.1），允许；除此之外任何 str
    都意味着有正文从环境流进了感知输入。
    """
    leaks = 0
    for obj in observation.objects:
        if not isinstance(obj.object_id, str):
            leaks += 1
    environment = getattr(observation, "environment", None)
    if environment is not None and not isinstance(environment.time_phase, str):
        leaks += 1
    return leaks


def count_strs_deep(value: Any, _depth: int = 0) -> int:
    """数一数结构里有多少个 str **越界**。

    判据是**名字 vs 正文**，不是"有没有 str"：

    - 允许：标识符字段（:data:`IDENTIFIER_FIELDS`）里的 str。
    - 允许：取自**闭词表**的操作码（:func:`_opcode_vocabularies`）。
    - 越界：其余任何 str。

    闭词表那一层是必要的——只按字段名放行的话，``operation`` 就成了一个
    "可以往里写任何字符串"的字段，而"可以写任何字符串"正是正文的入口。
    名字取自闭集，正文不是，分界就在这里。

    走进 dict 时只看值不看键：键是字段名。再往深走，字段名信息就丢了，
    所以闭词表检查只在**具名**那一层生效——这也是 ``_depth`` 停在 6 的原因。
    """
    if _depth > 6:
        return 0
    if isinstance(value, str):
        return 1
    if isinstance(value, (tuple, list)):
        return sum(count_strs_deep(v, _depth + 1) for v in value)
    if isinstance(value, dict):
        return sum(count_strs_deep(v, _depth + 1) for v in value.values())

    names = getattr(value, "__dataclass_fields__", None)
    if not names:
        # torch.Tensor / float / None / int —— 都不是 str，贡献 0
        return 0

    vocabularies = _opcode_vocabularies()
    crossings = 0
    for name in names:
        if name in IDENTIFIER_FIELDS:
            continue
        field_value = getattr(value, name)
        vocabulary = vocabularies.get(name)
        if vocabulary is not None and isinstance(field_value, str):
            # 操作码：取自闭集才算名字。
            if field_value in vocabulary:
                continue
            crossings += 1
            continue
        crossings += count_strs_deep(field_value, _depth + 1)
    return crossings


# ----------------------------------------------------------------------
#  输出
# ----------------------------------------------------------------------


def summarize(results: Sequence[EpisodeResult]) -> dict[str, float]:
    """把一个 seed 集合收成一行数字。"""
    n = len(results)
    return {
        "seeds": float(n),
        "mean_frames": statistics.mean(r.frames for r in results),
        "mean_run_frames": statistics.mean(r.run_frames for r in results),
        "max_consecutive_run": float(max(r.max_consecutive_run for r in results)),
        "action_legality_rate": statistics.mean(
            r.action_legality_rate for r in results
        ),
        "interface_error_rate": statistics.mean(
            r.interface_error_rate for r in results
        ),
        "language_crossings": float(sum(r.language_crossings for r in results)),
        "observation_leaks": float(sum(r.observation_leaks for r in results)),
        "sleep_entry_rate": sum(1 for r in results if r.sleep_entry) / n,
        "wakes": float(sum(r.wake_frames for r in results)),
        "proposals": float(sum(r.proposals for r in results)),
        "applied": float(sum(r.applied for r in results)),
        "rejected": float(sum(r.rejected for r in results)),
        "audit_completeness": statistics.mean(
            r.audit_completeness for r in results
        ),
    }


def print_table(title: str, rows: Sequence[tuple[str, Any]]) -> None:
    """``(标签, 值)`` 序列打成长度对齐的两列表。"""
    width = max(len(label) for label, _ in rows)
    print(f"\n{title}")
    print("-" * (width + 22))
    for label, value in rows:
        shown = f"{value:.4f}" if isinstance(value, float) else str(value)
        print(f"{label:<{width}}  {shown}")


def print_matrix(
    results: Sequence[EpisodeResult], columns: Sequence[tuple[str, str]]
) -> None:
    """逐 seed 明细。``columns`` 是 ``(表头, EpisodeResult 属性名)`` 序列。"""
    width = max(10, *(len(h) for h, _ in columns))
    print("  " + " ".join(f"{h:>{width}}" for h, _ in columns))
    for r in results:
        cells = []
        for _, attr in columns:
            value = getattr(r, attr)
            shown = f"{value:.3f}" if isinstance(value, float) else str(value)
            cells.append(f"{shown:>{width}}")
        print("  " + " ".join(cells))
