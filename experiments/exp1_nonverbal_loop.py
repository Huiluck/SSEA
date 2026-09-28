"""实验 1：非语言闭环（07 §12）。

**目标**：证明模型可以在不使用自然语言的情况下运行。

**流程**：模型接收结构化观测 → 输出结构化动作 → 环境执行 → 模型接收反馈。

**验收指标**：连续运行步数 / 动作合法率 / 接口异常率 / 是否出现自然语言控制路径。

跑法::

    .venv/Scripts/python.exe -m experiments.exp1_nonverbal_loop

---

这条实验在七个里最"应该早就跑过"——闭环本身从 Milestone 2 起就在跑，
缺的一直是**系统测量**。所以本脚本的产出不是一个新机制，而是把
「它确实在跑」从印象变成数字。

第四个指标（是否出现自然语言控制路径）值得单说：**它有两层**。

- 静态层：协议字段里有没有承载正文的字段。已由
  ``tests/test_protocol_consistency.py::TestNoNaturalLanguageInLoop`` 守着。
- 运行时层：跑起来之后，有没有 str 值真的流过了控制边界。

第二层是这一层新加的，也是唯一能证伪第一层的——「字段里没有 str」
不等于「运行时没有 str 流过去」。判据是**名字 vs 正文**：
对象 id、事件类型、``time_phase`` 是**名字**，允许；
其余任何 str 出现在隐状态或动作里都是**正文**，越界。
"""

from __future__ import annotations

import sys

from experiments._harness import (
    DEFAULT_FRAMES,
    survival_summary,
    DEFAULT_SEEDS,
    print_matrix,
    print_table,
    run_episode,
)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    frames = int(argv[0]) if argv else DEFAULT_FRAMES

    results = [run_episode(s, frames=frames, watch_language=True) for s in DEFAULT_SEEDS]

    print(f"实验 1：非语言闭环    {len(DEFAULT_SEEDS)} seed × {frames} 帧上限")
    print_matrix(
        results,
        (
            ("seed", "seed"),
            ("存活帧", "frames"),
            ("RUN", "run_frames"),
            ("最长春段", "max_consecutive_run"),
            ("合法率", "action_legality_rate"),
            ("异常率", "interface_error_rate"),
            ("语言越界", "language_crossings"),
            ("感知泄漏", "observation_leaks"),
        ),
    )

    # 上限与实测分开印（债务 31）。
    print("  " + survival_summary(results, frames).headline(frames))
    total_run = sum(r.run_frames for r in results)
    total_frames = sum(r.frames for r in results)
    total_rejected = sum(r.constraint_rejected for r in results)
    total_internal = sum(r.internal_errors for r in results)
    total_language = sum(r.language_crossings for r in results)
    total_leaks = sum(r.observation_leaks for r in results)

    print_table(
        "验收指标（全 seed 汇总）",
        (
            ("连续运行步数（单 seed 最长干净连段）",
             max(r.max_consecutive_run for r in results)),
            ("动作合法率", 1.0 - total_rejected / total_run if total_run else 0.0),
            ("接口异常率", total_internal / total_frames if total_frames else 0.0),
            ("是否出现自然语言控制路径",
             "否" if total_language == 0 and total_leaks == 0 else "是"),
            ("—— 参照量 ——", ""),
            ("RUN 帧总数", total_run),
            ("总帧数", total_frames),
            ("被约束执行点拒绝的帧", total_rejected),
            ("触发内部兜底的帧", total_internal),
            ("非标识符 str 跨越决策/发出边界", total_language),
            ("非标识符 str 出现在感知输入", total_leaks),
        ),
    )

    print(
        f"\n判据（第四个指标）：控制边界上只允许**名字**——对象 id、事件类型、\n"
        f"``time_phase``；任何**正文**形态的 str 都算越界。\n"
        f"``Feedback.notes`` 里的自由文本不计入：它是观察员接口，\n"
        f"07 §7.2 明说「调试输出可用自然语言，但不参与感知输入 / 动作输出 /\n"
        f"身体控制 / 实时闭环」。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
