"""`experiments/run_all.py` 的登记表守卫。

**为什么需要它**：`EXPERIMENTS` 是一张**声明式清单**——编号、名字、模块名、
状态字符串。它同时被三处读：`run_all` 表头、`run_all` 的运行循环、
以及人读的文档（12 §4.2 / `experiments/README.md`）。三处里只有第一处
会被人看，而**状态字符串是手写的，没有任何东西守着它**。

于是有一个很安静的失败形状：把状态从「未落地」改成「已跑」而忘了填模块，
或者模块名打错一个字母。前者让表头宣称某实验跑过了而实际没有，
后者会让 `subprocess.call` 返回非零——但那时已经跑完四个实验了。

这类清单在本项目里已经有过一次教训：`test_channels_all_have_consumers`
名字说的是消费者，实际只断言了通道名元组（14 §5.3）。
**守卫的名字与它守的东西要对得上。**

**双向断言**是刻意的（与 `DEFERRED_SCOPES` / `NO_CONSUMER_YET` 同一形状）：
只查「有模块的条目能 import」不够——还要查「声明已跑的条目必须有模块」，
否则清单会朝着"看起来越来越完整"的方向烂掉。
"""

from __future__ import annotations

import importlib
import importlib.util

import pytest

from experiments.run_all import ACCEPTANCE, EXPERIMENTS

#: 状态字符串里出现它就表示「这条已经跑过了」。
#: 与 `run_all.py` 里的写法绑定，改那边要一起改。
RUN_MARKER = "已跑"
MISSING_MARKER = "未落地"


def test_registry_shape_is_well_formed() -> None:
    """编号 1–7 各一条，名字与模块名非空——先保证表本身能被读。"""

    numbers = [n for n, _, _, _ in EXPERIMENTS]
    assert numbers == list(range(1, 8)), numbers
    for number, name, module, status in EXPERIMENTS:
        assert name and status, (number, name, status)
        if module is not None:
            assert isinstance(module, str) and module.startswith("experiments."), module


def test_every_registered_module_is_importable() -> None:
    """**这条是那个打错一个字母的形状的直接守卫。**

    用 ``find_spec`` 而不是 ``import_module``：登记表里有 5 个模块，
    逐个真 import 会把 torch 拉进来跑一遍副作用，而这里要问的只是
    「这个名字指向一个真实存在的模块吗」。
    """

    for number, _, module, _ in EXPERIMENTS:
        if module is None:
            continue
        assert importlib.util.find_spec(module) is not None, (
            f"实验 {number} 登记了模块 {module!r}，但它 import 不到"
        )


def test_status_and_module_agree_both_ways() -> None:
    """**双向断言**：状态不能比模块乐观，也不能比模块悲观。

    - 说「已跑」却没有模块 → 表头宣称跑过了，实际没有。这是**假证据**，
      正是本项目一直在防的形状。
    - 有模块却说「未落地」 → 跑得起来的实验不出现在运行列表里，
      人会以为它还没做。这是**漏报**，比假证据轻，但同样是清单在烂。
    """

    for number, _, module, status in EXPERIMENTS:
        runs = RUN_MARKER in status
        assert runs == (module is not None), (
            f"实验 {number}: 状态 {status!r} 与模块 {module!r} 不一致"
        )
        if not runs:
            assert MISSING_MARKER in status, status


def test_every_runnable_experiment_has_acceptance_columns() -> None:
    """跑得起来的实验必须在 `ACCEPTANCE` 里有判据。

    没有的话表头那一列打的是 `—`，读起来像「这条实验没有验收指标」，
    而 `ACCEPTANCE` 的缺失只是**登记时漏了**。两者在输出里长得一样。
    """

    for number, name, module, _ in EXPERIMENTS:
        if module is None:
            continue
        assert number in ACCEPTANCE, f"实验 {number}（{name}）缺验收指标"
        assert ACCEPTANCE[number].strip(), ACCEPTANCE[number]


def test_acceptance_has_no_orphan_entries() -> None:
    """反向：`ACCEPTANCE` 里不许有指向未落地实验的条目。

    孤儿条目不会报错，但它会让「这个实验的判据已经想好了」看起来成立，
    而实际连脚本都没有——判据写得再清楚也无处可跑。
    """

    registered = {n for n, _, module, _ in EXPERIMENTS if module is not None}
    orphans = sorted(set(ACCEPTANCE) - registered)
    assert not orphans, f"ACCEPTANCE 里有未落地实验的条目：{orphans}"


@pytest.mark.parametrize("module", [
    "experiments.exp2_memory_recall",
    "experiments.exp3_skill_consolidation",
])
def test_experiment_scripts_expose_main(module: str) -> None:
    """实验脚本要有可调用的 ``main``——`run_all` 靠 ``-m`` 跑它们。

    这一条比 ``find_spec`` 更进一步：名字对但文件是个空壳也能 import 成功，
    而 ``python -m`` 会以 0 退出，`run_all` 于是报告「跑完，退出码 0」。
    **一个什么都不打印的空壳比一个崩掉的脚本更危险**——崩掉会被看见。
    """

    spec = importlib.util.find_spec(module)
    assert spec is not None and spec.loader is not None, module

    imported = importlib.import_module(module)
    assert callable(getattr(imported, "main", None)), f"{module} 没有 main()"
