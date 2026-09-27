"""实验脚手架：跑一轮快环，把它身上的量收成数字。

设计上有三条刻意的选择：

**一、量从 trace、累计计数器与审计日志取，不从环形缓冲取。**
``Environment.event_log()`` / ``event_notes()`` 是 16 槽环形缓冲（12 §6 债务 10），
"跑完再遍历事件流"会**静默漏掉早期事件**——本次核对时它真的咬过一次：
「跑完统计 ``ENERGY_GAINED``」得到 0 次，而逐帧追踪显示第 10 帧确实
``grasp: +0.356 energy``。所以本模块的累计量逐帧现加，
或者读 ``StructureStore.audit_log()``（append-only，不丢），
或者读 ``Environment.event_counts()``（**只增不减、不截断**，2026-09-27 加入，
正是为了补这个洞）。

但注意 ``event_counts()`` 与逐帧求和**不是一回事**，两者不可互换：

- 它按**事件类型**分解，所以回答得了"这轮 grasp 成功了几次"；
  但它**没有 source_id 维度**，所以回答不了"接触了几次危险源"——
  ``OBJECT_FOUND`` 对资源与危险源一视同仁。
- 它数的是**事件**，不是**能量**：一次抓取会发 ``ENERGY_GAINED``，
  但同一帧的 ``Feedback.energy_change`` 完全可能是负的（还扣着基础代谢
  与动作消耗），而 ``push`` / ``pull`` / 基础代谢的耗能**根本不发事件**。
  要能量收支就用 trace 上的 ``Feedback``。

**一之二、能量口径：三条约定写死在这里，别在各脚本里各定一套。**

1. **分母是 RUN 帧数**，不是 ``len(trace)``。睡眠帧每帧**涨** 0.01 能量
   （``environment.py`` 的 ``rest``），WAKE 帧经 ``_empty_feedback()`` 塞一个
   **合成 0**。用总帧数归一化会让"睡得多的回合"显得**更省**——
   和上面 ``action_legality_rate`` 同一个陷阱。
2. **``energy_spent`` 是毛支出**（负增量取绝对值求和），睡眠期的恢复**不抵消**它。
   净额另给（``net_energy_change``）。两者差别很大：睡眠占寿命一大半。
3. **取的是夹取后的"实现增量"，不是"请求增量"。** ``Feedback.energy_change``
   是 ``round(self.energy - energy_before, 6)``，即夹取之后的差。能量满 1.0 时
   抓资源，它是 0.0——这是**对的**：上限 1.0 是刻意强加的策略压力
   （"吃饱了就不能再存"），用资源标称价值求和会把这份浪费藏起来。

   由此有一条**已知偏低、不是 bug**：能量 6 处 ``max(0.0, ...)`` 与 damage 的
   ``min(max_damage, ...)`` 都在**丢弃超调**，而死亡帧恰恰是消耗峰值帧。
   报告里要注明，不要当成测量误差去"修"。

**一之三、求和要有容差。** ``round(..., 6)`` 累积几百帧后与
``final − initial`` 差约 1e-4，"精确守恒"这个断言拿不到，用 ``pytest.approx``。

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
    #: 逐帧 ``Feedback.energy_change`` 的**正部**之和（夹取后的实现增量）。
    energy_gained: float = 0.0
    #: 逐帧 ``Feedback.energy_change`` 的**负部绝对值**之和——毛支出，睡眠恢复不抵消。
    energy_spent: float = 0.0
    #: 逐帧 ``Feedback.damage_change`` 的正部之和。
    damage_taken: float = 0.0
    #: 环境的按类型累计计数快照（``Environment.event_counts()``）。
    #: **只在尾部取一次**——它本身不截断，所以不需要逐帧加。
    event_totals: dict[str, int] = field(default_factory=dict)
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

    @property
    def net_energy_change(self) -> float:
        """净能量变化 = 正部 − 负部。

        与 ``energy_gained - energy_spent`` 恒等（就这么定义的），
        单独给个名字是为了让"用净额还是毛额"在调用处**看得见**——
        睡眠期的恢复会抵消运行期的消耗，两个数差别很大。
        """
        return self.energy_gained - self.energy_spent

    @property
    def energy_spent_per_run_frame(self) -> float:
        """每 RUN 帧的能量支出。**实验 3 的「能量消耗变化」应当用这个口径。**

        分母是 RUN 帧数而非 ``len(trace)``：睡眠帧每帧涨 0.01 能量，
        用它当分母会让睡得多的回合显得更省。理由见模块 docstring 一之二。
        """
        if self.run_frames == 0:
            return 0.0
        return self.energy_spent / self.run_frames


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
    energy_gained = 0.0
    energy_spent = 0.0
    damage_taken = 0.0

    while loop.alive and len(loop.trace()) < frames:
        if watch_language:
            # 决策边界：进入解码器之前的隐藏状态。
            language_crossings += count_strs_deep(loop.hidden)
        loop.step()
        record = loop.trace()[-1]

        if record.feedback is not None:
            rejected_total += record.feedback.notes.count("constraint_rejected:")
            internal_total += record.feedback.notes.count("internal_error:")
            # 逐帧现加，不从事件流取——口径见模块 docstring 一之一。
            change = record.feedback.energy_change
            energy_gained += max(0.0, change)
            energy_spent += max(0.0, -change)
            damage_taken += max(0.0, record.feedback.damage_change)

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
        energy_gained=energy_gained,
        energy_spent=energy_spent,
        damage_taken=damage_taken,
        # 尾部取一次即可：计数器只增不减、不截断，不需要逐帧加。
        event_totals=loop.environment.event_counts(),
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
#  窗口内的量（实验 2 / 3 用；与 Environment 的全轮累计分工不同）
# ----------------------------------------------------------------------


def count_events(trace: Sequence[Any], event_type: str) -> int:
    """``trace`` 里某类事件的个数，**按 event_id 去重**。

    为什么要去重：观测里带的 ``events`` 是环境的**滚动窗口**，同一个事件会
    连续出现在十几帧的观测里，按帧数会把一次写入数成十几次。这个口径与
    ``SSEA.plasticity._event_ids`` 一致（那里也是这么写的，理由相同）。

    为什么不去重不行、不按窗口也不行——两者是**两件事**，别混：

    - 去重治的是**重复计数**（同一事件的多次出现）。
    - 本函数仍在 ``trace`` 这个**给定窗口**内计数，窗口外的事件它看不见。
      要"整轮一共几次"请用 ``Environment.event_counts()``，
      那个只增不减、不截断。

    注意 ``MEMORY_RETRIEVED`` **有一帧滞后**：``observe_model_event`` 在
    ``step()`` 返回观测**之后**才调用，所以帧 t 发出的事件出现在帧 t+1 的
    观测里。计数不受影响，只影响"算在哪一帧头上"（``plasticity`` 的
    docstring 也记了这一条）。
    """

    ids: set[str] = set()
    for record in trace:
        if record.state != STATE_RUN:
            continue
        for event in record.observation.events:
            if event.event_type == event_type:
                ids.add(event.event_id)
    return len(ids)


def energy_by_version_window(trace: Sequence[Any]) -> list[dict[str, Any]]:
    """按**结构版本窗口**切开的能量收支，从旧到新。

    **实验 3 的「能量消耗变化」必须用这个，不能用全轮累计。** 判据是
    ``StepRecord.context_fingerprint``——与 ``SSEA.plasticity._current_window``
    同一个切法，那是这个字段的第一个消费者。它 docstring 里记着不切窗口的实测
    代价：三轮睡眠把 ``memory_gate_threshold`` 从 0.5 一路推到下界 0.15，
    "不是『收敛到合适的阈值』，是『撞到夹子』"。**同一个错法在能量指标上会重演**：
    不切版本，固化**前**的消耗会永远留在分子里，于是"固化有没有降低消耗"
    这个问题被历史数据稀释掉。

    返回每段一个 dict，键为 ``fingerprint`` / ``run_frames`` /
    ``energy_gained`` / ``energy_spent`` / ``damage_taken`` /
    ``energy_spent_per_run_frame``。空 trace 返回空列表；
    指纹为空（``versions={}``，没有版本信息）时退化为**一段**——
    没有版本信息就没有归因可言，与 ``_current_window`` 的取舍一致。
    """

    windows: list[dict[str, Any]] = []
    current_fp: tuple[tuple[str, int], ...] | None = None
    acc: dict[str, Any] | None = None

    for record in trace:
        if record.state != STATE_RUN:
            continue
        fp = record.context_fingerprint
        if fp != current_fp:
            current_fp = fp
            acc = {
                "fingerprint": fp,
                "run_frames": 0,
                "energy_gained": 0.0,
                "energy_spent": 0.0,
                "damage_taken": 0.0,
            }
            windows.append(acc)
        assert acc is not None  # 由上面那个分支保证，仅给类型检查看
        acc["run_frames"] += 1
        if record.feedback is not None:
            change = record.feedback.energy_change
            acc["energy_gained"] += max(0.0, change)
            acc["energy_spent"] += max(0.0, -change)
            acc["damage_taken"] += max(0.0, record.feedback.damage_change)

    for acc in windows:
        n = acc["run_frames"]
        acc["energy_spent_per_run_frame"] = acc["energy_spent"] / n if n else 0.0
    return windows


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
