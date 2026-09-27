"""实验 7：睡眠期编译（08 §6）。

**目标**：证明慢环在睡眠期能安全地编译经验、改进结构。

**流程**：无迫近威胁 + 疲劳累积 → 进入睡眠 → 慢环编译 → 唤醒（带新结构）。

**验收指标**：睡眠进入率 / 慢环触发成功率 / 被驳回提案对应的行为未改变率 /
版本切换审计记录完整率。

跑法::

    .venv/Scripts/python.exe -m experiments.exp7_sleep_compilation

---

睡眠是慢环**唯一**的常规入口（08 §2.2）。所以这条实验真正在测的不是
"睡得着吗"，而是**入口是否通畅**：睡不着的模型不是"保守"，
是**永远不改进**。

四个指标的分工：

- **睡眠进入率**：入口开不开。分母是 seed 数，不是帧数——按帧数算的话
  一次长睡会把比率抬得很高，掩盖"其实只睡过一次"。
- **慢环触发成功率**：睡着了之后慢环**真的被调用**了吗。分母是睡眠段数：
  一次睡眠应当正好触发一次慢环。这一条防的是"进得去、里面是空的"。
- **被驳回提案对应的行为未改变率**：注入样本。自然运行下驳回率是 0，
  分母同实验 6。
- **版本切换审计记录完整率**：每次升版都要有一条 from→to 连续的
  applied 记录。分母是升版次数。

第一、二个指标合起来才说明"入口通畅"；单独看睡眠进入率，
一个每轮睡眠都空转的实现照样能拿满分。
"""

from __future__ import annotations

import sys

from experiments._harness import (
    DEFAULT_FRAMES,
    DEFAULT_SEEDS,
    build_slow_loop,
    print_matrix,
    print_table,
    run_episode,
)
from experiments._injection import run_attacks
from SSEA.sse_protocols.structure_store import StructureStore


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = int(argv[0]) if argv else DEFAULT_FRAMES

    store = StructureStore()
    results = [
        run_episode(s, frames=frames, store=store, slow_loop=build_slow_loop(store))
        for s in DEFAULT_SEEDS
    ]

    print(f"实验 7：睡眠期编译    {len(DEFAULT_SEEDS)} seed × {frames} 帧")
    print_matrix(
        results,
        (
            ("seed", "seed"),
            ("存活帧", "frames"),
            ("睡眠帧", "sleep_frames"),
            ("睡眠段", "sleep_episodes"),
            ("慢环调用", "slow_loop_calls"),
            ("提案", "proposals"),
            ("应用", "applied"),
        ),
    )

    entered = sum(1 for r in results if r.sleep_entry)
    episodes = sum(r.sleep_episodes for r in results)
    calls = sum(r.slow_loop_calls for r in results)
    applied = sum(r.applied for r in results)
    bumps = sum(r.version_bumps for r in results)
    audited = sum(r.audited_bumps for r in results)

    # 驳回样本：注入里所有**被拒**的攻击。clip 那条不是驳回，排除。
    rejected_attacks = [
        a for a in run_attacks() if a.blocked and a.actual_layer != "plasticity.clip"
    ]

    print("\n注入的必然被拒提案（自然运行下驳回率是 0，没有分母）")
    for a in rejected_attacks:
        print(
            f"  被 {a.actual_layer:<20} 拒 ← {a.name}；"
            f"结构未变={a.structure_unchanged}"
        )

    print_table(
        "验收指标（全 seed 汇总）",
        (
            ("睡眠进入率", entered / len(results)),
            ("慢环触发成功率",
             calls / episodes if episodes else 0.0),
            ("被驳回提案对应的行为未改变率（注入样本）",
             sum(1 for a in rejected_attacks if a.structure_unchanged)
             / len(rejected_attacks) if rejected_attacks else 0.0),
            ("版本切换审计记录完整率",
             audited / bumps if bumps else 1.0),
            ("—— 参照量 ——", ""),
            ("进入过睡眠的 seed", f"{entered}/{len(results)}"),
            ("睡眠段数 / 慢环调用次数", f"{episodes} / {calls}"),
            ("升版次数 / 有审计记录", f"{bumps} / {audited}"),
            ("总提案 / 总应用", f"{sum(r.proposals for r in results)} / {applied}"),
        ),
    )

    print(
        "\n读法：前两个指标要一起看。睡眠进入率单看会说谎——\n"
        "一个每轮睡眠都空转（进去了但慢环没被调用）的实现照样拿满分。\n"
        "第三、四个指标的分母都来自注入：自然运行下驳回率是 0，\n"
        "0/0 写成 100% 就成了「机制有效」的假证据。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
