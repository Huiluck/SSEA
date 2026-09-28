"""判据健康度实测 —— 给现有验收判据做一次体检（docs/03 §11）。

跑法::

    .venv/Scripts/python.exe -m experiments.measure_judgement_health [帧数]

**这是仪器，不是实验。** 它不改变任何行为，只做三件事：

1. 把现有验收判据的**实测样本**喂给 `sse_protocols.judgement_health`，打印八条子句；
2. 打印 `V_τ`（逐情境跨臂方差）的分布，标出 `V_τ ≈ 0` 的**无分辨率情境**；
3. 把「未声明」的条目列出来——**未声明不是通过**。

为什么要有它：项目已经吃过三次同一个亏，判据在**不变红**时看起来完全正常
（危险回避率两臂均 0.9814、技能固化 0/33、记忆粗粒度签名 7/8 seed 相同）。
在改任何机制之前，先知道尺子还能不能量。
"""

from __future__ import annotations

import sys
from typing import Any, Callable

from experiments._harness import DEFAULT_FRAMES, DEFAULT_SEEDS, print_table
from experiments.exp2_memory_recall import ARMS as EXP2_ARMS
from experiments.exp2_memory_recall import run_arm as exp2_run_arm
from experiments.exp3_skill_consolidation import run_arm as exp3_run_arm
from SSEA.sse_protocols.judgement_health import (
    BOUND_NONE,
    BOUND_UNIT,
    BOUND_ZERO,
    PASS,
    JudgementDeclaration,
    assess,
)

#: 一「臂包」＝ 该臂的逐 seed 原始产物。`gained` 只有实验 3 有（技能生成数量是
#: `run_arm` 算出来的，不落在 `EpisodeResult` 上，所以按臂携带而不是按帧携带）。
Bundle = dict[str, Any]

#: 一条判据的登记：(指标名, 逐 seed 取样函数, 边界, 为什么这么判可证红, can_go_red)。
Sampler = Callable[[Bundle], tuple[Any, ...]]
METRICS: tuple[tuple[str, Sampler, str, str, bool], ...] = (
    (
        '危险回避率（实验2）',
        lambda b: tuple(r.hazard_avoidance_rate for r in b['results']),
        BOUND_UNIT,
        '两臂读数相同 ⇒ 削弱臂拉不动它',
        False,
    ),
    (
        '记忆写入成功率（实验2）',
        lambda b: tuple(r.memory_write_success_rate for r in b['results']),
        BOUND_UNIT,
        '记忆关臂无仪器（n=0）⇒ 天然的零分母对照',
        True,
    ),
    (
        '记忆检索命中率（实验2）',
        lambda b: tuple(r.memory_hit_rate for r in b['results']),
        BOUND_UNIT,
        '记忆关臂无仪器（n=0）',
        True,
    ),
    (
        '可编译段数（实验2）',
        lambda b: tuple(float(r.compileable_segments) for r in b['results']),
        BOUND_ZERO,
        '记忆关臂可作削弱对照',
        True,
    ),
    (
        '危险接触帧（实验2）',
        lambda b: tuple(float(r.hazard_contact_frames) for r in b['results']),
        BOUND_ZERO,
        '记忆关臂可作削弱对照',
        True,
    ),
    (
        '技能调用成功率（实验3）',
        lambda b: tuple(r.skill_call_success_rate for r in b['results']),
        BOUND_UNIT,
        '固化关臂 skill_calls=0 ⇒ n=0；固化开臂 0/33',
        False,
    ),
    (
        '技能生成数量（实验3）',
        lambda b: tuple(float(g) for g in b['gained']),
        BOUND_ZERO,
        '固化关臂恒 0 是定义使然，不是削弱',
        False,
    ),
    (
        '能量消耗变化（实验3）',
        lambda b: tuple(r.energy_change for r in b['results']),
        BOUND_NONE,
        '固化关臂可作对照',
        True,
    ),
)


def _declaration(name: str, bound: str, can_go_red: bool) -> JudgementDeclaration:
    """现有验收实验的**如实登记**。

    `matched_baseline=''` 与 `search_seeds == eval_seeds` 都是如实填的，不是为了让
    它变红好写报告：SSEA 现有两臂是「机制开 / 机制关」的**消融**，不是 HarnessEval
    意义上的**预算匹配基线**（同等反馈预算下多试 K 次 / 重置）；而技能是在 seed i 上
    编译、又在同一个 seed i 上测调用的。这两条本来就该红，红了才知道下一步改什么。
    """

    return JudgementDeclaration(
        name=name,
        bound=bound,
        matched_baseline='',
        search_seeds=DEFAULT_SEEDS,
        eval_seeds=DEFAULT_SEEDS,
        reported_as='pass@1',
        can_go_red=can_go_red,
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = int(argv[0]) if argv else DEFAULT_FRAMES

    print(f'判据健康度实测    {len(DEFAULT_SEEDS)} seed × {frames} 帧上限')
    print('跑的是既有两臂，不改任何行为；输出是**判据的体检报告**，不是实验结果。')

    bundles: dict[str, Bundle] = {}
    for name, factory in EXP2_ARMS:
        bundles[f'exp2/{name}'] = {'results': exp2_run_arm(name, factory, frames), 'gained': None}
    for arm in ('固化关', '固化开'):
        results, gained, _seeded, _funnels = exp3_run_arm(arm, frames)
        bundles[f'exp3/{arm}'] = {'results': results, 'gained': gained}

    exp2_names = tuple(f'exp2/{n}' for n, _ in EXP2_ARMS)
    exp3_names = ('exp3/固化关', 'exp3/固化开')

    rows: list[tuple[str, object]] = []
    reports = []
    for name, sampler, bound, why, can_go_red in METRICS:
        arms = exp2_names if '实验2' in name else exp3_names
        samples = tuple((a, sampler(bundles[a])) for a in arms)
        report = assess(_declaration(name, bound, can_go_red), samples)
        reports.append(report)
        rows.append((name, report.verdict.upper()))
        margin = '—' if report.boundary_margin is None else f'{report.boundary_margin:.4g}'
        rows.append((
            '    n / 取值 / 边界余量',
            f'{report.n_defined}/{report.n_total} 有定义 · {report.distinct} 个取值 · 余量 {margin}',
        ))
        gap = '—' if report.arm_gap is None else f'{report.arm_gap:.4g}'
        rows.append(('    两臂中位差 / 可分', f'{gap} · {report.separable}'))
        for cid, verdict, reason in report.clauses:
            if verdict != PASS:
                rows.append((f'    {cid} {verdict}', reason))
        rows.append((f'    （可证红理由）', why))
    print_table('判据健康度（八条子句；只列非 PASS 项）', rows)

    print('\n' + '=' * 86)
    print('V_τ（逐情境跨臂方差）—— ExperienceSynthesis 的情境预筛：V_τ ≈ 0 的情境没有分辨力')
    print('=' * 86)
    vrows: list[tuple[str, object]] = []
    for report in reports:
        vals = [v for v in report.v_tau_by_scenario if v is not None]
        if not vals:
            vrows.append((report.name, '无有定义情境（逐情境全为 None）'))
        else:
            zero = sum(1 for v in vals if v == 0.0)
            vrows.append((report.name, f'{zero}/{len(vals)} 个情境 V_τ = 0 · 最大 {max(vals):.6g}'))
    print_table('逐情境 V_τ', vrows)

    failing = [(r.name, r.failing) for r in reports if r.failing]
    unresolved = [(r.name, r.unresolved) for r in reports if r.unresolved]
    print('\n' + '=' * 86)
    print(f'判红的判据：{len(failing)}/{len(reports)}')
    for name, ids in failing:
        print(f'  - {name}：{" ".join(ids)}')
    print(f'\n有未声明项的判据：{len(unresolved)}/{len(reports)}')
    for name, ids in unresolved:
        print(f'  - {name}：{" ".join(ids)}')
    print(
        '\n判读须知：\n'
        '1. **H5 / H6 全红是如实的，不是脚本苛刻。** 现有两臂是「机制开/关」消融，\n'
        '   没有 HarnessEval 意义上的预算匹配基线；技能在 seed i 上编译又在同一 seed i\n'
        '   上测调用，搜索集与评测集没分离。这两条是**下一轮实验设计要改的**。\n'
        '2. **UNKNOWN 不是通过。** 未声明的条目要么补登记，要么改实验——不要读成「没问题」。\n'
        '3. 本脚本只体检，不给结论。降级/弃用一条判据是裁决，写在 docs/03 §11 里。'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
