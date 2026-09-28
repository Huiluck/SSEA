"""实验 2：记忆召回（07 §12）。

**目标**：证明记忆机制真的改变了行为——不是"记忆被调用了"，是**开与不开不一样**。

**验收指标**：记忆写入成功率 / 记忆检索命中率 / 危险回避率。

跑法::

    .venv/Scripts/python.exe -m experiments.exp2_memory_recall [帧数]

---

两臂怎么摆
----------

| 臂 | 检索器 | 含义 |
|---|---|---|
| 记忆关 | ``ZeroMemoryRetriever()`` | **对照组**：接口在、记忆不在 |
| 记忆开 | ``FastLoop`` 默认（``MemorySystem``） | 真记忆 |

「关」不是本脚本的一个布尔开关，是一个**显式的检索器实现**
（理由见 ``SSEA/fast_loop.py`` 里 ``ZeroMemoryRetriever`` 的 docstring：
零尺寸的 ``MemorySystem`` 仍会把 ``MEMORY_WRITTEN`` 事件打进环境，
那不是"关"，是"开着但容量为零"）。所以本脚本里没有 ``if memory_on:``
这样的分支——两臂的差别**全部**在那一个构造参数上。

本能两臂都装
------------

两臂都播种同一份本能（``approach`` + ``grasp_in_reach``），否则 agent 走不到
资源跟前，记忆里既没有可写的成功也没有可检索的条目，"开不开记忆"就无从比。
**本能是两臂的公共前提，不是自变量**——自变量只有记忆。

**每个 (臂, seed) 一份全新的 store。** 慢环会改 store（技能、阈值），
共用一份的话后面的 seed 会继承前面的技能，两臂的数字就不再是同一场实验。
``_instinct.seeded_store_multi`` 每次都从 ``StructureStore()`` 起步，
"播种前的状态"与"完全不装本能的那个世界"是同一个东西。

一行 ``writes = 0`` 有两个来源
------------------------------

``EpisodeResult.memory_instrumented`` 区分「没有仪器」（对照组）与
「有仪器、读数为 0」。**这个区分是实验 2 的全部要害**：两者在输出里
长得一模一样，而结论相反——一个是"记忆关着"，一个是"记忆开着但一次都没触发"。
所以下面的明细表里，对照组的 ``落库`` / ``检索`` / ``命中`` 打的是 ``-``
而不是 ``0``：``0`` 是一个读数，``-`` 是**没有仪器**。

判据与它的已知缺陷
------------------

**危险回避率在对照组里是饱和的。** 默认世界里危险源很少进入视野，
实测对照组就有 0.98 左右——**天花板效应**，两臂差不出东西来。
所以本脚本除了它，还打三个原始计数（暴露帧 / 接触帧 / 最近距离均值），
并**明说哪一个能作数**。一个饱和的率不能当证据，哪怕它很好看。

「它改变了行为吗」要分三档量
----------------------------

| 档 | 判据 | 分辨率 |
|---|---|---|
| 一（粗） | ``coarse_signature``：5 个整数 | 只有扰动大到改变了生死才动 |
| 二（中） | ``gate_signature``：记忆门决策次数 | 扰动大到改了"要不要写"才动 |
| 三（细） | ``action_divergence``：逐帧动作差范数 | **1e-3 量级就能看见** |

**第一版只有前两档，于是读错了。** 两臂的 5 个整数在 7/8 个 seed 上相同，
被写成了「两臂逐位相同」，进而推出「机制空转」；而逐帧重量显示动作在
**5/8 个 seed 上不同**（变化 seed 内 56–99% 的帧不同，中位幅度 3.5e-4 ~ 1.8e-3）——推得动，是**尺子太粗**
（12 §6 债务 21）。三档一起打，是为了让「量不出」不再冒充「没有」。
"""

from __future__ import annotations

import sys

from SSEA.fast_loop import ZeroMemoryRetriever
from SSEA.instinct import preset_blob
from experiments._harness import (
    DEFAULT_FRAMES,
    survival_summary,
    DEFAULT_SEEDS,
    EpisodeResult,
    action_divergence,
    mean_defined,
    pool_action_divergences,
    print_matrix,
    print_table,
    run_episode,
)
from experiments._instinct import seeded_store_multi

#: 两臂共用的本能前提。趋近把 agent 送到资源跟前，操纵链让它抓得到——
#: 没有这两样，记忆里既没有可写的成功，也没有可检索的条目。
PLAN = (
    ("approach", preset_blob("approach")),
    ("grasp_in_reach", preset_blob("grasp_in_reach")),
)

#: ``(臂名, 检索器工厂, 是否预算匹配)``。``None`` = 让 ``FastLoop`` 用它自己的
#: 默认（``MemorySystem``）——**不是**这里另写一个构造，否则两臂会在
#: "默认到底是什么"上分叉。
#:
#: **第三臂是 HarnessEval 意义的预算匹配基线。** 它让记忆系统**照跑**
#: （写入、检索、命中计数全发生），但把注入的 `m_t` 换成零向量。于是
#: 「记忆开」相对「记忆关」多花的那部分算力被单独控制住，两臂的差别只剩
#: **「记忆有没有影响决策」**。没有它，「增益」可能只是「多跑了一件事」。
#:
#: 三臂的正确读法：**记忆关 → 预算匹配** 之间是「记忆系统跑过一遍」的效应，
#: **预算匹配 → 记忆开** 之间才是「记忆影响了决策」的效应。
ARMS: tuple[tuple[str, object, bool], ...] = (
    ("记忆关", ZeroMemoryRetriever, False),
    ("记忆开", None, False),
    ("预算匹配", None, True),
)


def fresh_store():
    """一份新 store，本能已过验证门。**每 (臂, seed) 调一次。**"""

    store, outcomes = seeded_store_multi(PLAN)
    assert all(o.applied for o in outcomes), outcomes
    return store


def run_arm(
    name: str, factory: object, frames: int, budget_matched: bool = False
) -> list[EpisodeResult]:
    results = []
    for seed in DEFAULT_SEEDS:
        retriever = None if factory is None else factory()  # type: ignore[operator]
        results.append(
            run_episode(
                seed,
                frames=frames,
                store=fresh_store(),
                memory_retriever=retriever,
                memory_budget_matched=budget_matched,
            )
        )
    return results


def memory_column(r: EpisodeResult, key: str) -> str:
    """``-`` = 没有仪器（对照组），不是"读数为 0"。

    这一格是本脚本最容易被读错的地方，所以它有一个专门的名字。
    """

    if not r.memory_instrumented:
        return "-"
    return str(r.memory_stats.get(key, 0))


def coarse_signature(r: EpisodeResult) -> tuple[object, ...]:
    """**粗粒度行为**：帧数 / RUN / 可编译段 / 抓取次数 / 危险接触帧。

    这是"两臂在这个 seed 上有没有走出不同的路"的判据。刻意不取能量小数——
    ``round(..., 6)`` 的累积差会让每个 seed 都"不一样"，那个差异没有意义。
    """

    return (
        r.frames,
        r.run_frames,
        r.compileable_segments,
        r.event_totals.get("ENERGY_GAINED", 0),
        r.hazard_contact_frames,
    )


def gate_signature(r: EpisodeResult) -> int:
    """**记忆门的决策次数**（模型请求写入的帧数）——比粗粒度行为灵敏得多。

    为什么需要第二档：记忆检索出来的条目是喂进隐状态的，所以它**一定**会
    扰动轨迹；问题是这个扰动走不走到粗粒度行为上去。门决策次数直接量
    "隐状态被扰动得改了主意没有"，而 ``frames`` / ``RUN`` 那几个量
    要到扰动大到改变了生死才会动。

    两档一起看，才能把「机制没接上」与「机制接上了但推不动行为」
    分开——这两句话指向完全不同的下一步，而在只看粗粒度那一档时
    **它们的输出是一样的**。

    **2026-09-28 补记：实测结果是第三种。** 逐帧重量显示两臂动作在
    5/8 个 seed 上不同（变化 seed 内 56–99% 的帧不同，中位幅度 3.5e-4 ~ 1.8e-3），所以「推不动行为」这句是错的
    ——推得动，只是**这两档都太粗**，量不出 1e-3 量级的增益。
    `coarse_signature` 的 docstring 一直写的是「粗粒度行为」，
    代码没说谎，是正文把它读成了「逐位相同」（12 §6 债务 21）。
    **第三档已落地**：``action_divergence``，比的是动作序列本身。
    """

    return r.memory_write_requests


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = int(argv[0]) if argv else DEFAULT_FRAMES

    print(f"实验 2：记忆召回    {len(DEFAULT_SEEDS)} seed × {frames} 帧上限")
    print(
        "三臂：记忆关 = ZeroMemoryRetriever；记忆开 = FastLoop 默认 MemorySystem；"
        "预算匹配 = 默认 MemorySystem **照跑**但注入被抹成零向量（HarnessEval 意义的预算匹配基线）。\n"
        "三臂都播种同一份本能（approach + grasp_in_reach），每个 (臂, seed) 一份新 store。"
    )

    by_arm = {
        name: run_arm(name, factory, frames, budget) for name, factory, budget in ARMS
    }

    # 上限与实测分开印。**这一行是债务 31 的正解**：不印它，
    # 「× 200 帧上限」会被读成「跑了 200 帧」，而实测 0/8 活到上限。
    for name, results in by_arm.items():
        print(f"  [{name}] {survival_summary(results, frames).headline(frames)}")

    for name, results in by_arm.items():
        instrumented = sum(1 for r in results if r.memory_instrumented)
        print(f"\n{'=' * 78}\n臂：{name}    （有仪器的 seed：{instrumented}/{len(results)}）\n{'=' * 78}")
        print_matrix(
            results,
            (
                ("seed", "seed"),
                ("帧", "frames"),
                ("RUN", "run_frames"),
                ("门开(请求)", "memory_write_requests"),
                ("可编译段", "compileable_segments"),
                ("暴露帧", "hazard_visible_frames"),
                ("接触帧", "hazard_contact_frames"),
                ("技能调用", "skill_calls"),
            ),
        )
        print("  —— 记忆侧逐 seed 明细（`-` = 没有仪器，不是读数为 0）——")
        header = f"  {'seed':>4}  {'落库':>6} {'检索':>6} {'命中':>6} {'写入成功率':>10} {'检索命中率':>10}  通路"
        print(header)
        powered = 0
        for r in results:
            rate = r.memory_write_success_rate
            hit = r.memory_hit_rate
            state = (
                "断电（门一次没开）"
                if r.memory_write_requests == 0
                else "通电"
            )
            powered += 1 if r.memory_write_requests else 0
            print(
                f"  {r.seed:>4}  {memory_column(r, 'writes'):>6} "
                f"{memory_column(r, 'retrievals'):>6} {memory_column(r, 'hits'):>6} "
                f"{'None' if rate is None else f'{rate:.3f}':>10} "
                f"{'None' if hit is None else f'{hit:.3f}':>10}  {state}"
            )
        print(f"  通路通电的 seed：{powered}/{len(results)}")

    # ---- 验收指标（两臂并排）----
    rows: list[tuple[str, object]] = []
    for name, results in by_arm.items():
        write_rate, write_n = mean_defined([r.memory_write_success_rate for r in results])
        hit_rate, hit_n = mean_defined([r.memory_hit_rate for r in results])
        avoid, avoid_n = mean_defined([r.hazard_avoidance_rate for r in results])
        dist, dist_n = mean_defined([r.mean_nearest_hazard_distance for r in results])
        res_dist, res_n = mean_defined([r.mean_nearest_resource_distance for r in results])
        rows.extend(
            # 存活帧排在最前：它是**淘汰函数的输出**，是这一堆读数里唯一一条
            # 模型碰不到的（C9 把淘汰判给环境）。其余都是机制计数。
            survival_summary(results, frames).rows()
            + (
                (f"[{name}] 记忆写入成功率", f"{write_rate}  (n={write_n})"),
                (f"[{name}] 记忆检索命中率", f"{hit_rate}  (n={hit_n})"),
                (f"[{name}] 危险回避率", f"{avoid}  (n={avoid_n})"),
                (f"[{name}] 最近危险源距离均值", f"{dist}  (n={dist_n})"),
                (f"[{name}] 最近资源距离均值", f"{res_dist}  (n={res_n})"),
                ("", ""),
            )
        )
    print_table("验收指标（两臂并排；n = 有定义的 seed 数）", rows)

    # ---- 原始分母：一个饱和的率不能作证据，得看它底下有多少次机会 ----
    print_table(
        "危险侧与资源侧的原始计数（判断上面的率是否饱和）",
        tuple(
            (f"[{name}] {label}", value)
            for name, results in by_arm.items()
            for label, value in (
                ("危险源可见帧（回避率的分母）", sum(r.hazard_visible_frames for r in results)),
                ("受危险源损伤帧（分子）", sum(r.hazard_contact_frames for r in results)),
                ("资源可见帧", sum(r.resource_visible_frames for r in results)),
                ("存活帧合计", sum(r.frames for r in results)),
                ("可编译段合计", sum(r.compileable_segments for r in results)),
                ("ENERGY_GAINED 合计", sum(r.event_totals.get("ENERGY_GAINED", 0) for r in results)),
            )
        ),
    )

    # ---- 机制被调用了多少 vs 行为变了多少（两档灵敏度）----
    off, on = by_arm["记忆关"], by_arm["记忆开"]
    coarse_diff = [
        a.seed for a, b in zip(off, on) if coarse_signature(a) != coarse_signature(b)
    ]
    gate_diff = [
        a.seed for a, b in zip(off, on) if gate_signature(a) != gate_signature(b)
    ]
    total_writes = sum(r.memory_writes or 0 for r in on)
    total_retrievals = sum(int(r.memory_stats.get("retrievals", 0)) for r in on)
    total_hits = sum(int(r.memory_stats.get("hits", 0)) for r in on)

    print_table(
        "机制被调用了多少 vs 行为变了多少",
        (
            ("记忆开臂：落库条数（合计）", total_writes),
            ("记忆开臂：检索次数（合计）", total_retrievals),
            ("记忆开臂：命中次数（合计）", total_hits),
            ("—— 分界 ——", ""),
            ("记忆门决策改变的 seed（请求数不同）", f"{len(gate_diff)}/{len(off)}  {gate_diff}"),
            ("粗粒度行为改变的 seed（帧数/RUN/可编译段/抓取/接触帧）",
             f"{len(coarse_diff)}/{len(off)}  {coarse_diff}"),
        ),
    )
    print(
        "  上表是本实验最要紧的一格：**记忆确实在运转**（落库、检索、命中都不是 0），\n"
        "  但它改变门决策的 seed 数与改变粗粒度行为的 seed 数是**两个不同的数**。\n"
        "  只看落库条数会把「机制在转」读成「机制有用」。"
    )

    # ---- 第三档：逐帧动作差分布。前两档都是整数/计数，这一档比的是轨迹本身。
    per_seed = [
        action_divergence(a.action_trace, b.action_trace) for a, b in zip(off, on)
    ]
    pooled = pool_action_divergences(per_seed)
    moved = [a.seed for a, d in zip(off, per_seed) if d.differing_frames]

    print(f"\n  —— 第三档逐 seed（`动作改变` 一列是这一档真正的判据）——")
    print(
        f"  {'seed':>4}  {'比较帧':>6} {'方向不同':>8} {'占比':>7} "
        f"{'中位差':>10} {'最大差':>10}  动作改变"
    )
    for a, d in zip(off, per_seed):
        print(
            f"  {a.seed:>4}  {d.compared:>6} {d.differing_frames:>8} "
            f"{d.differing_ratio:>6.1%} {d.direction_median:>10.3e} "
            f"{d.direction_max:>10.3e}  {'是' if d.differing_frames else '—— 没动'}"
        )
    print(
        "  注意合池与逐 seed 是**两个不同的读数**：门从没开的 seed 两臂逐帧全同，\n"
        "  它们会把合池中位数拉到 0。**判据是「有几个 seed 动了」，不是合池中位数。**"
    )

    print_table(
        "第三档：两臂动作序列的逐帧差（8 seed 合池，比的是解码后的 locomotion）",
        (
            ("参与比较的帧数", f"{pooled.compared}（两臂合计 {sum(pooled.frames)} 帧）"),
            ("方向不同的帧", f"{pooled.differing_frames}（{pooled.differing_ratio:.1%}）"),
            (
                "方向差 中位 / p90 / 最大",
                f"{pooled.direction_median:.3e} / {pooled.direction_p90:.3e} "
                f"/ {pooled.direction_max:.3e}",
            ),
            ("speed 最大差", f"{pooled.speed_max:.3e}"),
            ("duration 最大差", f"{pooled.duration_max:.3e}"),
            ("维数不一致的帧", pooled.dim_mismatches),
            ("两臂帧数不等的 seed", sum(1 for d in per_seed if d.lengths_differ)),
            ("—— 分界 ——", ""),
            ("动作真的改变了的 seed", f"{len(moved)}/{len(off)}  {moved}"),
        ),
    )
    print(
        "  三档的分辨率依次是：粗粒度签名（5 个整数）< 门决策计数 < 逐帧动作差。\n"
        "  **只有第三档能在 1e-3 量级的扰动上分辨出两臂不同**——前两档量不出，\n"
        "  而它们量不出时的输出与「两臂真的一样」**完全一样**。\n"
        "  这就是 2026-09-28 那次误读的形状：把「尺子太粗」读成了「机制空转」\n"
        "  （12 §6 债务 21）。判读时先看这一档，再看上面两档。"
    )

    print(
        "\n判读须知：\n"
        "1. **危险回避率在默认世界里是饱和的**（两臂都在 0.97 以上），\n"
        "   天花板效应，差不出东西来。它下面的原始计数才是能作数的东西——\n"
        "   分母（危险源可见帧）小到只有几十帧时，一个接触与否就能让率跳 3 个百分点。\n"
        "   本脚本把分母一起打出来，就是为了让这一步能被人工核对。\n"
        "2. **写入成功率与检索命中率的分母不同**：前者是模型请求写入的帧数，\n"
        "   后者是 ``retrieve()`` 真的执行了的次数（受策略 ``stride`` 过滤）。\n"
        "   两个率都跳过 ``None`` 求均值，n 是有定义的 seed 数——\n"
        "   **没有数字比假数字好**（12 §4.2）。\n"
        "3. 「通路断电」的 seed 不是缺陷也不剔除，它是一个**双峰现象的读数**：\n"
        "   记忆门控是未训练的（12 §6 债务 5），开不开由随机初始化决定。\n"
        "   跨 seed 的均值要把这件事说出来，否则「一半 seed 门恒闭」会被\n"
        "   平均成一个看起来很平庸的数字，而真相是分布本身就是两堆。\n"
        "4. **「它改变了行为吗」有三档，判读顺序是从细到粗**：逐帧动作差\n"
        "   （第三档）→ 门决策数（第二档）→ 5 个整数（第一档）。\n"
        "   粗档说「一样」而细档说「不一样」时，**以细档为准**——\n"
        "   粗档的「一样」是它分辨不出，不是真的没有。反过来不成立：\n"
        "   细档说一样，才是真的没动。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
