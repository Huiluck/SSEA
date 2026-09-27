"""把已落地的实验一次跑完，输出 12 §4.2 那张表。

跑法::

    .venv/Scripts/python.exe -m experiments.run_all [帧数]

七个实验里**只有三个**有脚本，其余四个的前置还没就绪（缺组件或缺口，
见 14 §6.4 与 13 §6.6）。本脚本不假装它们跑过了——没跑的就不出现在
表里，宁少不假。这正是 12 §4.2 一直写着「一个都还没有」的原因：
**没有数字比假数字好**。
"""

from __future__ import annotations

import subprocess
import sys

#: (编号, 名称, 模块, 状态)。状态是给人看的，不参与运行。
#: 编号与名称依 07 §12 原文（1–6）；实验 7 是 08 新增的。
EXPERIMENTS = (
    (1, "非语言闭环", "experiments.exp1_nonverbal_loop", "已跑"),
    (2, "记忆召回", None, "未落地：无脚本"),
    (3, "技能固化", None, "未落地：依赖债务 6b"),
    (4, "基因保存恢复", None, "未落地：缺 Gene Manager"),
    (5, "变异", None, "未落地：缺 Gene Manager"),
    (6, "安全自我修改", "experiments.exp6_safe_self_modification", "已跑"),
    (7, "睡眠期编译", "experiments.exp7_sleep_compilation", "已跑"),
)

#: 每个实验能写进 12 §4.2 的那几列。值在运行时从脚本输出里人读，
#: 不在这里各存一份——两份数字必然漂移。
ACCEPTANCE = {
    1: "连续运行步数 / 动作合法率 / 接口异常率 / 是否出现自然语言控制路径",
    6: "提案数量 / 验证通过率 / 失败回滚率 / 核心系统未被破坏率",
    7: "睡眠进入率 / 慢环触发成功率 / 被驳回提案对应的行为未改变率 / 版本切换审计记录完整率",
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = argv[0] if argv else "200"

    # flush 是必要的：子进程直接写 fd，父进程 stdout 是管道（块缓冲），
    # 不 flush 的话表头会被冲到子进程输出**后面**，看着像没打印。
    print(f"{'#':>2}  {'实验':<12} {'状态':<34} 验收指标")
    print("-" * 100)
    for number, name, _, status in EXPERIMENTS:
        print(f"{number:>2}  {name:<12} {status:<34} {ACCEPTANCE.get(number, '—')}")

    runnable = [(n, m) for n, _, m, _ in EXPERIMENTS if m]
    print(
        f"\n跑 {len(runnable)} 个已就绪的实验"
        f"（{len(EXPERIMENTS) - len(runnable)} 个缺前置）\n",
        flush=True,
    )

    failed = []
    for number, module in runnable:
        print("=" * 100)
        print(f"实验 {number}  →  {module}")
        print("=" * 100)
        code = subprocess.call([sys.executable, "-m", module, frames])
        if code != 0:
            failed.append((number, code))

    print("\n" + "=" * 100)
    if failed:
        print(f"失败的实验：{failed}")
        return 1
    print(f"全部 {len(runnable)} 个已就绪实验跑完，退出码 0。")
    print(
        "\n提醒：跑通不等于达标。每个实验的「验收指标」列是**判据**，\n"
        "脚本打印的是**实测值**；两者要人工比对后才写进 12 §4.2。\n"
        "本脚本不替这一步做判断——自动比对会把「脚本没崩」当成「指标达标」。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
