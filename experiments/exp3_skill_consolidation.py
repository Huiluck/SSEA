"""实验 3：技能固化（07 §12）。

**目标**：证明快环的成功段能经慢环固化成技能，并且固化后**行为真的变了**。

**验收指标**：技能生成数量 / 技能调用成功率 / 能量消耗变化。

跑法::

    .venv/Scripts/python.exe -m experiments.exp3_skill_consolidation [帧数]

---

两臂怎么摆
----------

| 臂 | 慢环 | 含义 |
|---|---|---|
| 固化关 | ``lambda trace: None`` | **对照组**：快环照跑，慢环不发生 |
| 固化开 | ``build_slow_loop(store, plasticity=False)`` | 只有技能固化，没有阈值自纠 |

「固化关」写成 ``lambda trace: None`` 而不是 ``slow_loop=None``：后者会让
``run_episode`` 去建**默认慢环**，于是对照臂反而跑着慢环——**一个静默搞反的
对照臂**，两臂数字会一样而被读成「固化没效果」。

**``plasticity=False`` 是刻意的。** 默认慢环里 ``LocalPlasticity`` 会把
``memory_gate_threshold`` 这类阈值也一起改（三轮睡眠就能把它从 0.5 推到下界
0.15，见 ``plasticity._current_window`` 的 docstring）。留着它的话，
两臂的差别就同时包含「技能固化」与「阈值自纠」两件事，
**指标上的增量归因不到技能头上**。要量技能就只开技能。

**每个 (臂, seed) 一份全新的 store**——理由同实验 2：慢环会改 store，
共用一份的话后面的 seed 会继承前面固化出来的技能。

三个指标各自的坑
----------------

**技能生成数量** = 跑完后 ``len(store.snapshot().skills)`` **减去播种时的条数**。
不减的话，把本能换成"顺带塞两条技能"就能把这个数字刷上去。

**技能调用成功率** 取自 ``StepRecord.skill_event``，**不是**
``Environment.event_counts()``——``SKILL_SUCCESS`` / ``SKILL_FAILURE``
在 ``EVENT_TYPES`` 里，但**没有生产者**（``tests/test_environment.py``
里有一条测试钉着那份无生产者清单）。从计数器读会**恒得 0**，
而 0 会被读成"一次都没调用过"——真相可能是调用了几十次、每次都失败。
这两句话指向完全不同的下一步，所以本脚本把 ``skill_calls``（调用帧数）
与 ``skill_events``（运行器报出的事件数）**并排打**，让那个分叉看得见。

**能量消耗变化** = ``energy_change_between_windows(trace)``（末窗口 − 首窗口，
按每 RUN 帧口径）。窗口按 ``context_fingerprint`` 切。**没发生过版本切换时
返回 ``None``**，不是 0.0——"没固化过"与"固化没有降低消耗"是两件事。
本脚本把 ``energy_windows``（窗口数）一并打出来解释那个 ``None``。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from SSEA.instinct import preset_blob
from SSEA.skill_library import candidate_counts, direct_success_frames
from SSEA.sse_protocols.induction_funnel import InductionFunnel, diagnose
from experiments._harness import (
    DEFAULT_FRAMES,
    survival_summary,
    DEFAULT_SEEDS,
    EpisodeResult,
    build_budget_matched_slow_loop,
    build_slow_loop,
    mean_defined,
    print_matrix,
    print_table,
    run_episode,
)
from experiments._instinct import seeded_store_multi

#: 与实验 2 同一份本能前提——没有它就没有可编译的成功段，
#: 实验 3 会跑成"0 条技能"，那不是证据，是没东西可测。
PLAN = (
    ("approach", preset_blob("approach")),
    ("grasp_in_reach", preset_blob("grasp_in_reach")),
)


def fresh_store():
    """一份新 store，本能已过验证门。**每 (臂, seed) 调一次。**"""

    store, outcomes = seeded_store_multi(PLAN)
    assert all(o.applied for o in outcomes), outcomes
    return store


@dataclass
class ArmRun:
    """一臂的产物。

    ``compiled`` 与 ``published`` 分开是**预算匹配臂存在的全部理由**：

    - ``compiled``：慢环**算出**了几条技能（弃置场上的增长也算）；
    - ``published``：几条**真的进了快环快照**。

    只报一个数时，「结构有用」与「慢环跑过一遍有用」被绑在一起，读数分不开。
    """

    results: list[EpisodeResult]
    compiled: list[int]
    published: list[int]
    seeded: list[int]
    funnels: list[InductionFunnel | None]


def run_arm(arm: str, frames: int) -> ArmRun:
    """跑一臂。返回 ``(逐 seed 结果, 逐 seed 新增技能数, 逐 seed 播种前技能数, 逐 seed 漏斗)``。

    漏斗是**三档分母**（attempted / passed / reused）的载体：0/33 曾经是**一个**
    零值，它把「候选没切出来」「切出来全被拒」「入库了从不被调用」三种病压成了
    同一句话。三档分开之后，一个零值最多只能指向一种病（docs/03 §11.8）。

    ``固化关`` 臂**不建漏斗**（没有慢环，没有候选可谈）——给它填一个全 0 的
    漏斗会被读成「切窗阶段失败」，那是把「对照臂」误诊成「病了」。
    """

    results: list[EpisodeResult] = []
    compiled: list[int] = []
    published: list[int] = []
    seeded: list[int] = []
    funnels: list[InductionFunnel | None] = []

    for seed in DEFAULT_SEEDS:
        store = fresh_store()
        before = len(store.snapshot().skills)
        counts = {"windows": 0, "positive": 0, "calls": 0, "ds": 0}
        compile_store = store
        if arm == "固化关":
            # **不是 None**——None 会让 run_episode 建默认慢环（见模块 docstring）。
            slow_loop = lambda trace: None  # noqa: E731
        elif arm == "预算匹配":
            # **慢环照跑**，绑到弃置场：睡眠帧数、调用次数、编译与门控的计算
            # 与「固化开」逐位相同，唯一差别是**产物不进入快环快照**。
            compile_store = fresh_store()
            inner = build_budget_matched_slow_loop(
                throwaway=compile_store, plasticity=False
            )

            def slow_loop(trace, _inner=inner, _counts=counts):
                _counts["calls"] += 1
                _counts["ds"] = direct_success_frames(trace)
                windows, positive = candidate_counts(trace)
                _counts["windows"] = windows
                _counts["positive"] = positive
                return _inner(trace)

        else:
            # plasticity=False：只要技能固化，不要阈值自纠（归因见模块 docstring）。
            inner = build_slow_loop(store, plasticity=False)

            def slow_loop(trace, _inner=inner, _counts=counts):
                # 漏斗头两档的分母。``candidate_counts`` 用**默认** SkillLibraryConfig
                # ——与慢环内部那一份同源；若哪天两者分叉，InductionFunnel 的单调性
                # 检查会**直接抛错**，不会静默算出一个对不上的数。
                #
                # **覆盖，不累加。** 慢环每次拿到的是**整条** trace（不是增量），
                # 累加会把同一段窗数重复计几次——2026-09-29 实测：3 次调用把
                # 4 窗 1 候选算成了 8 窗 2 候选。用最后一次（最长的）trace 才是
                # 「这条 episode 里切出了多少窗」。
                _counts["calls"] += 1
                _counts["ds"] = direct_success_frames(trace)
                windows, positive = candidate_counts(trace)
                _counts["windows"] = windows
                _counts["positive"] = positive
                return _inner(trace)

        result = run_episode(seed, frames=frames, store=store, slow_loop=slow_loop)
        after = len(store.snapshot().skills)
        grown = len(compile_store.snapshot().skills) - before
        results.append(result)
        published.append(after - before)
        compiled.append(grown)
        seeded.append(before)
        if arm == "固化关" or arm == "预算匹配":
            # **不建漏斗。** 固化关没有慢环（没有候选可谈）；预算匹配臂的发布
            # 被**按设计**切断，漏斗的后三档对它没有意义——硬填会得到
            # `REJECTED_BY_GATE` 或 `NEVER_INVOKED`，把「设计如此」误诊成「病了」。
            # 与 §11.8 给固化关不建漏斗是同一条理由。
            funnels.append(None)
        else:
            funnels.append(
                InductionFunnel(
                    frames=result.frames,
                    slow_loop_calls=counts["calls"],
                    direct_success_frames=counts["ds"],
                    windows=counts["windows"],
                    positive=counts["positive"],
                    # 去重后的候选：本臂每个 seed 一份新 store，故新增数即入库数；
                    # 去重发生在同一 seed 内（候选之间同签名），这里取入库数作下界。
                    new_candidates=after - before,
                    committed=after - before,
                    reused=len(result.invoked_skills),
                )
            )

    return ArmRun(results, compiled, published, seeded, funnels)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = int(argv[0]) if argv else DEFAULT_FRAMES

    print(f"实验 3：技能固化    {len(DEFAULT_SEEDS)} seed × {frames} 帧上限")
    print(
        "三臂：固化关 = lambda trace: None（**不是 None**）；"
        "固化开 = build_slow_loop(store, plasticity=False)；"
        "预算匹配 = 慢环**照跑**但绑到弃置场（产物不发布）。\n"
        "三臂都播种同一份本能（approach + grasp_in_reach），每个 (臂, seed) 一份新 store。\n"
        "「预算匹配」是 HarnessEval 意义的**预算匹配基线**：它把「结构进入快环」与\n"
        "「慢环跑过一遍」分开——只做开/关消融时这两件事被绑在一起，读数分不开。"
    )

    arms = ("固化关", "固化开", "预算匹配")
    data = {arm: run_arm(arm, frames) for arm in arms}

    # 上限与实测分开印（债务 31）：不印它，「× 200 帧上限」会被读成「跑了 200 帧」。
    for arm in arms:
        print(
            f"  [{arm}] "
            f"{survival_summary(data[arm].results, frames).headline(frames)}"
        )

    for arm in arms:
        run = data[arm]
        results, seeded = run.results, run.seeded
        print(f"\n{'=' * 78}\n臂：{arm}\n{'=' * 78}")
        print_matrix(
            results,
            (
                ("seed", "seed"),
                ("帧", "frames"),
                ("RUN", "run_frames"),
                ("可编译段", "compileable_segments"),
                ("成功段", "max_success_run"),
                ("技能调用", "skill_calls"),
                ("成功", "skill_successes"),
                ("失败", "skill_failures"),
                ("能量窗口", "energy_windows"),
            ),
        )
        print("  —— 技能生成（播种前 → 跑完后）——")
        for r, before, made, pub in zip(results, seeded, run.compiled, run.published):
            print(
                f"  seed {r.seed:>4}:        {before} → {before + pub}"
                f"    （发布 {pub} / 慢环编译 {made}）  "
                f"提案={r.proposals} 应用={r.applied} 驳回={r.rejected}"
            )

    # ---- 验收指标（两臂并排）----
    rows: list[tuple[str, object]] = []
    for arm in arms:
        run = data[arm]
        results = run.results
        rate, rate_n = mean_defined([r.skill_call_success_rate for r in results])
        run_rate, run_rate_n = mean_defined([r.run_action_success_rate for r in results])
        survival = survival_summary(results, frames)
        change, change_n = mean_defined([r.energy_change for r in results])
        windowed = sum(1 for r in results if r.energy_windows >= 2)
        rows.extend(
            # 存活帧排在最前：它是**淘汰函数的输出**（C9 归环境），而其余都是机制计数。
            survival.rows()
            + (
                (f"[{arm}] 技能**发布**数量（合计；长度混杂，仅作规模参考）",
                 sum(run.published)),
                (f"[{arm}] 慢环**编译**数量（合计）", sum(run.compiled)),
                (f"[{arm}] 其中有发布技能的 seed",
                 f"{sum(1 for g in run.published if g > 0)}/{len(run.published)}"),
                (f"[{arm}] 技能调用成功率", f"{rate}  (n={rate_n})"),
                (f"[{arm}] 技能调用帧数（合计）", sum(r.skill_calls for r in results)),
                (f"[{arm}] 运行器事件数（合计）", sum(r.skill_events for r in results)),
                # 动作侧的分母：没有它，「动作全失败」与「没跑过」在 0 上长得一样。
                (f"[{arm}] RUN 帧动作成功率", f"{run_rate}  (n={run_rate_n})"),
                (f"[{arm}] 能量消耗变化（末−首窗口）", f"{change}  (n={change_n})"),
                (f"[{arm}] —— 有 ≥2 个版本窗口的 seed", f"{windowed}/{len(results)}"),
                ("", ""),
            )
        )
    print_table("验收指标（两臂并排；n = 有定义的 seed 数）", rows)

    # ---- 三档分母：0/33 是哪一种零 ----
    funnel_rows: list[tuple[str, object]] = []
    for arm in arms:
        for seed, funnel in zip(DEFAULT_SEEDS, data[arm].funnels):
            if funnel is None:
                why = (
                    '不建漏斗：发布被**按设计**切断（预算匹配臂）'
                    if arm == '预算匹配'
                    else '不建漏斗：没有慢环（对照臂）'
                )
                funnel_rows.append((f'[{arm}] seed {seed}', why))
                continue
            d = diagnose(funnel)
            funnel_rows.append((
                f'[{arm}] seed {seed}',
                f'慢环 {funnel.slow_loop_calls} 次 → 直接成功帧 {funnel.direct_success_frames} → '
                f'窗 {funnel.windows} → 候选 {funnel.attempted} → '
                f'去重 {funnel.new_candidates} → 入库 {funnel.passed} → 复用 {funnel.reused}'
                f'　→　{d.code}：{d.next_action}',
            ))
    print_table('技能固化漏斗（三档分母 attempted / passed / reused）', funnel_rows)

    open_run = data['固化开']
    reused_total = sum(len(r.invoked_skills) for r in open_run.results)
    committed_total = sum(open_run.published)
    print(
        f'\n  固化开臂合计：入库 {committed_total} 条，被**真正调用过**的不同技能 '
        f'{reused_total} 个；调用 {sum(r.skill_calls for r in open_run.results)} 次、'
        f'事件 {sum(r.skill_events for r in open_run.results)} 次。\n'
        '  **「0/33」说的不是「没有技能被复用」，而是「33 次调用全落在同一（少数）'
        '条技能上，且全部失败」。** 这两句话指向完全不同的下一步：前者改调用面，'
        '后者改那一条技能的判据/表示。三档分母的作用就是把它们分开。'
    )

    # ---- 那个无生产者的坑，当场交叉验证一次 ----
    print_table(
        "技能事件的两个来源（交叉验证 ``Environment.event_counts()`` 的坑）",
        tuple(
            (f"[{arm}] 运行器报出的事件（trace 上的 skill_event）",
             sum(r.skill_events for r in data[arm].results))
            for arm in arms
        )
        + tuple(
            (f"[{arm}] 环境计数器 event_counts()['SKILL_SUCCESS']",
             sum(r.event_totals.get("SKILL_SUCCESS", 0) for r in data[arm].results))
            for arm in arms
        ),
    )
    print(
        "  第二组恒为 0，**不是**因为技能没被调用：``SKILL_SUCCESS`` / ``SKILL_FAILURE``\n"
        "  没有生产者（只被 ``EVENT_TYPES`` 登记过）。脚本若从计数器读成功率，\n"
        "  会把「调用了几十次、每次都失败」报成「一次都没调用过」。\n"
        "  正确来源是 ``StepRecord.skill_event``——运行器是有生产者的那一侧。"
    )

    print(
        "\n判读须知：\n"
        "1. **能量消耗变化为正 = 固化之后每 RUN 帧花得更多**，不是更少。\n"
        "   它不是一个「越小越好」的数字：固化的收益可能在别处（成功率、存活），\n"
        "   这一格只回答「支出变了多少」，回答不了「值不值」。\n"
        "   口径是**毛支出 / RUN 帧**，睡眠恢复不抵消（见 ``_harness`` 一之二）。\n"
        "2. ``None`` 是结论不是缺数据：它表示**这一轮没发生过版本切换**，\n"
        "   于是「固化前 / 固化后」没有第二个观测点。旁边的窗口数列是它的解释。\n"
        "3. 「技能调用成功率」在 ``skill_calls > 0`` 而事件数为 0 时说明\n"
        "   **请求了但运行器一个事件都没报**——那是缺陷，不是「没调用过」。\n"
        "   两列的差额是这两个结论的分界。\n"
        "4. **`成功段` 与 `技能调用成功率` 要一起读。** 固化开臂里有一个 seed\n"
        "   的成功段长达 41 帧（正是那一段编译出了技能），而它调用这条技能时\n"
        "   **每一次都报失败**。「编译它的那一段成功」与「重放它时成功」\n"
        "   不是同一件事——这个落差是本实验**量出来的读数**，不是解释；\n"
        "   归因（是技能表示丢了信息、还是重放条件不同）留给下一个增量。\n"
        "   只看「技能生成数量 = 2」会把这一格整个漏掉。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
