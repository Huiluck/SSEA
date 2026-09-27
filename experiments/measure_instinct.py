"""②.1 / ②.2 的测量：装上本能之后，世界里**有没有出现可学的成功**。

这不是 §12 那七条验收实验里的任何一条，所以它不叫 ``expN_``、也不进
``run_all.py`` 的 ``EXPERIMENTS``。它是**一次仪器读数**：实验 3 的前置探测
——回答"可学的世界打通了没有"，以及"还卡在哪儿"。

三臂
----
============  ======================================================
``off``       默认世界：``StructureStore()`` 的 ``adapters`` 为空
``approach``  只装趋近先验（②.1）
``grasp``     ``approach`` **加上** ``grasp_in_reach``（②.2）
============  ======================================================

**三臂共用同一个起点**，差异只可能来自播种；而"关本能"那一臂不是一个
特制的开关实现——它就是默认世界本身（理由见 ``experiments/_instinct.py``）。

``grasp`` 臂是**累积**的（趋近 + 操纵），所以 **``approach`` → ``grasp``
这一跳就是 ②.2 的增量**，不含趋近那一层的影响。写成"只装操纵"的臂是错的：
没有趋近，agent 走不到 ``reach = 1.0`` 以内，操纵链再通也无事可做——
那一臂量出来的 0 是"够不着"，不是"操纵没通"。

看什么
------
判据是 **``compileable_segments``（可编译的成功段数）**，不是存活帧数。
``compile_skills`` 的判据是「连续 ≥3 帧直接成功且整段净收益为正」，
所以一段都没有 = 慢环**没有任何东西可以固化** = 实验 3 仍然无米下锅。

存活帧数也打出来，但它是**陪衬**：历史教训是 8 seed 3 次抓取把均寿命
从 67 抬到 72 帧，而可编译段仍是 0。**活得久不等于学到了东西。**

跑法::

    .venv/Scripts/python.exe -m experiments.measure_instinct
    .venv/Scripts/python.exe -m experiments.measure_instinct 400
"""

from __future__ import annotations

import statistics
import sys

from SSEA.instinct import preset_blob
from experiments._harness import (
    DEFAULT_SEEDS,
    print_matrix,
    print_table,
    run_episode,
)
from experiments._instinct import seeded_store_multi

#: 各臂的名字。``off`` 必须排在前面——它是基线，读表时先看它。
ARMS: tuple[str, ...] = ("off", "approach", "grasp")


def adapter_plan(arm: str) -> tuple[tuple[str, bytes], ...]:
    """一臂要播种哪些 adapter。空元组 = 默认世界。

    ``grasp`` 臂含 ``approach`` 是刻意的累积，理由见模块 docstring。
    """

    if arm == "off":
        return ()
    plan: list[tuple[str, bytes]] = [("approach", preset_blob("approach"))]
    if arm == "grasp":
        plan.append(("grasp_in_reach", preset_blob("grasp_in_reach")))
    return tuple(plan)


#: 逐 seed 明细的列。
COLUMNS: tuple[tuple[str, str], ...] = (
    ("seed", "seed"),
    ("frames", "frames"),
    ("run", "run_frames"),
    ("E+", "energy_gained"),
    ("net", "net_energy_change"),
    ("res_d", "mean_nearest_resource_distance"),
    ("haz_d", "mean_nearest_hazard_distance"),
    ("srun", "max_success_run"),
    ("compil", "compileable_segments"),
)


def gained_count(result) -> int:
    """本轮 ``ENERGY_GAINED`` 的次数。

    取 ``event_counts()`` 而不是数 trace：环形缓冲会静默漏早期事件
    （``_harness`` docstring 一），而这个计数器只增不减。
    """

    return int(result.event_totals.get("ENERGY_GAINED", 0))


def measure_arm(arm: str, seeds: tuple[int, ...], frames: int) -> list:
    """跑一臂的全部 seed。"""

    plan = adapter_plan(arm)
    if not plan:
        store = None  # 默认世界：adapters 为空
        print(f"\n[播种] 臂 {arm}：无（默认世界的 adapters 本来就是空的）")
    else:
        store, outcomes = seeded_store_multi(plan)
        # 播种结果必须**逐条显式打出来**，无论成败。静默继续的话，这一臂
        # 实际上是"少装了一份"而输出看起来完全正常——那正是要防的失败形状。
        for outcome in outcomes:
            print(
                f"\n[播种] {outcome.name}: applied={outcome.applied} "
                f"v{outcome.from_version}→v{outcome.to_version} "
                f"bumped={outcome.version_bumped} ({outcome.reason})"
            )
            if not outcome.applied:
                print(
                    f"!! 这一臂不是「装上了 {outcome.name}」："
                    f"{outcome.stage_failed} —— {outcome.reason}"
                )

    return [run_episode(seed, frames=frames, store=store) for seed in seeds]


def summarize_arm(results: list) -> dict[str, object]:
    """一臂的数字。分母一并给出——``seeds_with_compilable`` 就是那个分母。"""

    return {
        "mean_frames": statistics.mean(r.frames for r in results),
        "total_compileable": sum(r.compileable_segments for r in results),
        "best_success_run": max(r.max_success_run for r in results),
        "seeds_with_compilable": sum(
            1 for r in results if r.compileable_segments > 0
        ),
        "seeds": len(results),
        "total_gains": sum(gained_count(r) for r in results),
        "total_net_energy": sum(r.net_energy_change for r in results),
        "mean_resource_distance": _mean_defined(results, "mean_nearest_resource_distance"),
        "mean_hazard_distance": _mean_defined(results, "mean_nearest_hazard_distance"),
    }


def _mean_defined(results: list, attr: str) -> tuple[float | None, int]:
    """跨 seed 求均值与**分母**，分母是"有几个 seed 真的有定义"。

    跳过 ``None`` 而不是当 0 平均：``None`` 的意思是"这个 seed 上没有可测的
    东西"（一帧都没看见资源 / 危险源），把它当 0 平均进去正好复现项目要治的错
    （14 §5.2：看数字先看分母）。全为 ``None`` 时返回 ``(None, 0)``。

    分母必须一路传到输出里：本轮实测就有 8 个 seed 里 2 个 ``haz_d`` 是
    ``None``，只打均值会让人以为那是 8 个 seed 的平均。
    """

    defined = [getattr(r, attr) for r in results if getattr(r, attr) is not None]
    if not defined:
        return None, 0
    return statistics.mean(defined), len(defined)


def _report(arm: str, results: list, summary: dict[str, object]) -> None:
    print(f"\n===== 臂 {arm} =====")
    print_matrix(results, COLUMNS)
    total = summary["seeds"]
    rows: list[tuple[str, object]] = [
        ("存活帧数（均值）", summary["mean_frames"]),
        ("ENERGY_GAINED（合计）", summary["total_gains"]),
        ("净能量变化（合计）", summary["total_net_energy"]),
        *_distance_rows("最近资源距离", summary["mean_resource_distance"], total),
        *_distance_rows("最近危险源距离", summary["mean_hazard_distance"], total),
        ("最长成功段（最大）", summary["best_success_run"]),
        ("可编译段数（合计）", summary["total_compileable"]),
        (f"有可编译段的 seed 数（/ {total}）", summary["seeds_with_compilable"]),
    ]
    print_table("", rows)


def _distance_rows(label: str, pair: tuple[float | None, int], total: object) -> list:
    """连续量的两行：均值（带分母），以及无定义时的说明。

    **没有定义就不打数字**——打 ``0.0000`` 会被读成"贴着目标"或"离得最远"，
    而事实是那一臂里这个量根本不存在。
    """

    mean, defined = pair
    if mean is None:
        return [(f"{label}（均值）", f"无定义（0 / {total} 个 seed 有定义）")]
    rows = [(f"{label}（均值）", mean)]
    if defined != total:
        rows.append((f"{label}（分母）", f"{defined} / {total} 个 seed 有定义"))
    return rows


def main(argv: list[str]) -> int:
    frames = int(argv[1]) if len(argv) > 1 else 400
    seeds = DEFAULT_SEEDS

    print(f"\n=== 本能：三臂对照（{len(seeds)} seed × {frames} 帧）===")
    print("判据是可编译的成功段数（编译器 min_frames=3），不是存活帧数。")
    print("grasp 臂是累积的（approach + grasp_in_reach），所以")
    print("  off → approach 是 ②.1 的增量，approach → grasp 是 ②.2 的增量。")

    summary: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        results = measure_arm(arm, seeds, frames)
        summary[arm] = summarize_arm(results)
        _report(arm, results, summary[arm])

    print("\n===== 读法 =====")
    for base, step in zip(ARMS, ARMS[1:]):
        _compare(base, step, summary[base], summary[step])
    return 0


def _compare(base: str, step: str, b: dict, s: dict) -> None:
    """相邻两臂的对照读数。**一个没有对照的数字什么也说明不了。**"""

    print(f"\n--- {base} → {step} ---")
    print(
        f"可编译段数：{b['total_compileable']} → {s['total_compileable']}"
        f"（差 {s['total_compileable'] - b['total_compileable']:+d}）"
    )
    print(
        f"ENERGY_GAINED：{b['total_gains']} → {s['total_gains']}"
        f"（差 {s['total_gains'] - b['total_gains']:+d}）"
    )
    print(f"存活帧数：{b['mean_frames']:.1f} → {s['mean_frames']:.1f}")

    # 「走到位了没有」只能看连续量。ENERGY_GAINED 为 0 时，"没靠近"与
    # "靠近了但抓取链没通"在它上面长得一模一样。
    (d_b, n_b), (d_s, n_s) = b["mean_resource_distance"], s["mean_resource_distance"]
    if d_b is None or d_s is None:
        print(
            f"最近资源距离至少一臂无定义——先别下结论：{base} 有定义的 seed "
            f"{n_b}/{b['seeds']}，{step} 是 {n_s}/{s['seeds']}。\n"
            "  没有任何 seed 在 RUN 帧上看见过资源，说明这轮里资源根本不在"
            "感知半径内。"
        )
    else:
        print(
            f"最近资源距离：{base}={d_b:.3f}（{n_b} seed）"
            f" → {step}={d_s:.3f}（{n_s} seed）"
            f"（{'靠近' if d_s < d_b else '没靠近'} {abs(d_s - d_b):.3f}）"
        )

    if s["total_compileable"] > b["total_compileable"]:
        print(
            f"  {step} 臂出现了 {base} 臂没有的可编译成功段 —— 这正是要的形态：\n"
            "  世界里出现了可学的成功，且它可归因于那份经提案路径播种的基因先验。"
        )
        if (d_b is not None and d_s is not None and d_s > d_b):
            print(
                "  上面那行「没靠近」在这里**不是退步，是成效的副产品**：抓取成功会\n"
                "  把那份资源从世界里移除（``environment._apply_manipulation`` 按身份\n"
                "  删对象），于是近处的被吃掉之后，「最近资源」自然变远。\n"
                "  所以一旦出现可编译段，资源距离就不再是这一格的判据了——\n"
                "  判据是可编译段数，距离只在「两臂都没抓到」时才是诊断工具。"
            )
        return

    if s["total_gains"] == 0 and b["total_gains"] == 0:
        if d_b is None or d_s is None or d_s >= d_b:
            print(
                "  两臂都一次没抓到，且没看出更靠近资源 —— 问题可能在**本能这一侧**\n"
                "  （快照 / 门 / 解码）。先在 `_instincts` 那道缝上看两个偏置到底\n"
                "  有没有算出来；此时谈操纵链是错的。"
            )
        else:
            print(
                "  确实更靠近资源，却一次都没抓到 —— 卡住的是操纵链\n"
                "  （门 / op / 目标打分）。下一步就是给那一层补先验。"
            )
    elif s["total_gains"] > b["total_gains"] and s["total_compileable"] == 0:
        print(
            f"  抓到了（ENERGY_GAINED {s['total_gains'] - b['total_gains']:+d}）"
            "但一段都编译不出来 ——\n"
            "  抓取是**孤立**的：编译器要连续 ≥3 帧直接成功，且整段净收益为正。\n"
            "  下一步要看相邻帧之间发生了什么（移动耗能 / 目标切换 / 门抖动），\n"
            "  不是继续加大本能。"
        )
    else:
        print(
            f"  {step} 臂没有超过 {base} 臂 —— 先别下结论：看逐 seed 明细，\n"
            "  两边是否都是「个别 seed 有段、多数没有」。门控开不开由随机初始化\n"
            "  决定（12 §4.3），八 seed 上的差异可能还不够把两臂分开。"
        )
    if b["total_compileable"] > 0:
        print(
            f"  注意 {base} 臂自己就有可编译段：默认策略能产生成功段的话，\n"
            "  「缺可学的成功」这个诊断本身就要重写——先查那些段是怎么来的。"
        )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
