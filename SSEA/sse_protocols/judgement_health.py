"""判据健康度检查表 —— 验收判据的「体检」协议（docs/03 §11）。

**为什么住在这里。** 协议层的定义是「被多处引用的规则」：本模块同时被
`experiments/measure_judgement_health.py`（实测）与 docs/03 §11（权威条款）
引用，且必须 stdlib-only、可序列化、可跨进程——与 8.x 的接口协议同一套约束。

**外部依据**（卡片库，见 docs/papers/cards/SSEA-应用图谱.md §3 S1）：

- HarnessEval（arXiv:2607.12227）：预算匹配基线 / 搜索-评测分离 / pass@1 vs pass@k
- AutoEnv（arXiv:2511.19304）：validator 合法性 + **差分可靠性**（削弱臂必须能拉开）
- GenEnv（arXiv:2601.02667）：α 难度带 + 样本量界
- ExperienceSynthesis（arXiv:2511.03773）：奖励熵难度选择器 `V_τ`
- Aspire（arXiv:2608.31111）：三层产出记账，**以 base 为参照**

**为什么必须有它。** 项目已经吃过三次同一个亏：判据在**不变红**的时候
看起来完全正常——

============  ====================================================
判据           实测病象
============  ====================================================
危险回避率      两臂均 **0.9814**（贴界，无余量）
技能固化        调用成功率 **0/33**（分母在，分子恒 0；**形状错**）
记忆粗粒度签名   5 个整数签名 **7/8 seed 相同**（整数量化，分辨率不足）
============  ====================================================

三次都不是「机制坏了」，是**尺子坏了**。本协议把「这条判据还分不分得开」
从一句判断变成一次可计算、**可证红**的检查。

**八条子句**：H1–H4 由数据算出，H5–H8 由实验登记时声明。

**三条不可协商的口径**（与 memory/skill 协议同源）：

1. **分母为 0 → `None`，不是 `0.0`**。`n_defined == 0` 时所有派生量一律
   `None`。「没有观测」与「观测到 0」是两回事，混同会把死判据读成健康。
2. **不注入样本**。本模块只接收调用方给的样本，**不补齐、不插值、不按 n 放大**。
3. **贴界必须报**。比率型判据贴到 0 或 1 时，剩余可分辨空间为零；这不是
   「表现好」，是「尺子到头了」。
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

#: 边界类型。决定「贴界」怎么算。
BOUND_UNIT = 'unit'   # 定义域 [0, 1]，贴 0 或 1
BOUND_ZERO = 'zero'   # 定义域 [0, inf)，贴 0
BOUND_NONE = 'none'   # 无自然边界（差值型、计数型）
BOUNDS: tuple[str, ...] = (BOUND_UNIT, BOUND_ZERO, BOUND_NONE)

#: 子句编号 → 一句话。判定逻辑见 `assess()`。
CLAUSES: tuple[tuple[str, str], ...] = (
    ('H1', '分母存在：有定义的样本数 > 0'),
    ('H2', '未贴界：距边界有余量，且不是全部样本贴在边界上'),
    ('H3', '两臂可分：被报的那个统计量能分开两臂'),
    ('H4', '分辨率充足：取值不是常数、也不是整数化到无信息'),
    ('H5', '有预算匹配基线（同等反馈/推理预算的简单基线臂）'),
    ('H6', '搜索集与评测集分离（held-out）'),
    ('H7', '报 pass@1（best-of-k 增益不得当作单次能力增益）'),
    ('H8', '可证红：存在能把它拉红的削弱臂'),
)

#: 子句编号常量。放在这里（而不是文件末尾）是因为 `assess()` 引用它们；
#: 靠「调用时再查全局」虽然也能跑，但读的人得翻到文件底才知道这些名字从哪来。
H1_C, H2_C, H3_C, H4_C, H5_C, H6_C, H7_C, H8_C = (c for c, _ in CLAUSES)

#: 判定档。`UNKNOWN` 表示**未声明**，不是「通过」——汇总时按最坏者计。
PASS = 'pass'
WARN = 'warn'
FAIL = 'fail'
UNKNOWN = 'unknown'

_ORDER = {PASS: 0, WARN: 1, FAIL: 2, UNKNOWN: 1}

#: H2 的余量下限。**这是一个约定，不是标定值**——它等价于「判据至少留出
#: 5% 的可分辨空间」，改它需要一次明文裁决（与 ρ 同规格）。
MARGIN_FLOOR = 0.05

#: H4 的分辨率下限：不同取值数 / 有定义样本数。
RESOLUTION_FLOOR = 0.25

#: 视为「贴界」的精确边界质量上限：全部样本都贴在边界上时**无需阈值**即可判红。
EDGE_MASS_LIMIT = 1.0

#: H4 判红的最少样本数——样本少时「取值数少」是正常现象，不是病。
RESOLUTION_MIN_SAMPLES = 8


def v_tau(values: 'list[float | None] | tuple[float | None, ...]') -> float | None:
    """跨样本方差（总体方差，除以 n，不是 n−1）。

    用途是 ExperienceSynthesis 的**情境预筛**：`V_τ ≈ 0` 的情境对两臂没有
    分辨力，先把它标出来，不要拿它下结论。

    **0 个有定义样本 → `None`**（分母为 0，不是「方差为 0」）。
    1 个有定义样本 → `0.0`，这是**真实的 0**（单个观测没有离散度），
    两者不是同一件事，所以不能合并成一个返回值。
    """

    defined = [float(v) for v in values if v is not None]
    if not defined:
        return None
    mean = sum(defined) / len(defined)
    return sum((x - mean) ** 2 for x in defined) / len(defined)


@dataclass(frozen=True)
class JudgementDeclaration:
    """一条判据的**声明部分**——机器算不出来的那四条（H5–H8）住在这里。

    `None` = **未声明**（判 `UNKNOWN`）；要表达「已声明为无」，传空字符串或
    `False`。这个区分是刻意的：未声明与声明为无，下一步动作不同
    （前者去补登记，后者去改实验）。
    """

    name: str
    bound: str = BOUND_NONE
    purpose: str = ''
    matched_baseline: str | None = None
    search_seeds: tuple[int, ...] | None = None
    eval_seeds: tuple[int, ...] | None = None
    reported_as: str | None = None
    can_go_red: bool | None = None

    def __post_init__(self) -> None:
        if self.bound not in BOUNDS:
            raise ValueError(f'未定义的边界类型 {self.bound!r}；合法值见 BOUNDS')
        if self.reported_as not in (None, 'pass@1', 'pass@k', 'both'):
            raise ValueError(
                f'reported_as 必须是 None / pass@1 / pass@k / both：{self.reported_as!r}'
            )


@dataclass(frozen=True)
class JudgementHealth:
    """一条判据的体检结果。派生量一律**分母为 0 时为 None**。"""

    name: str
    n_total: int
    n_defined: int
    n_arms_with_data: int
    minimum: float | None
    maximum: float | None
    median: float | None
    distinct: int
    distinct_ratio: float | None
    edge_mass: float | None
    boundary_margin: float | None
    arm_gap: float | None
    separable: bool | None
    v_tau_by_scenario: tuple[float | None, ...]
    clauses: tuple[tuple[str, str, str], ...]

    @property
    def failing(self) -> tuple[str, ...]:
        return tuple(cid for cid, verdict, _ in self.clauses if verdict == FAIL)

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(cid for cid, verdict, _ in self.clauses if verdict == UNKNOWN)

    @property
    def verdict(self) -> str:
        if self.failing:
            return FAIL
        worst = max((_ORDER[v] for _, v, _ in self.clauses), default=0)
        return {0: PASS, 1: WARN, 2: FAIL}[worst]

    @property
    def is_healthy(self) -> bool:
        return self.verdict == PASS

    def clause(self, clause_id: str) -> str:
        for cid, verdict, _ in self.clauses:
            if cid == clause_id:
                return verdict
        raise KeyError(clause_id)

    def explain(self, clause_id: str) -> str:
        for cid, _, reason in self.clauses:
            if cid == clause_id:
                return reason
        raise KeyError(clause_id)


def _worst(verdicts: 'list[str]') -> str:
    if not verdicts:
        return UNKNOWN
    return max(verdicts, key=lambda v: _ORDER[v])


def assess(
    declaration: JudgementDeclaration,
    arms: 'tuple[tuple[str, tuple[float | None, ...]], ...]',
) -> JudgementHealth:
    """给一条判据做体检。

    `arms` 是 `(臂名, 逐情境取值)`；**取值按情境对齐**（第 i 个元素是同一个
    情境在第 arm 臂上的读数），因为 `V_τ` 要**在同一情境内跨臂**算方差。

    情境对齐不是可选项：跨情境算方差量到的是「情境之间本来就不一样」，
    与「两臂有没有差别」无关——那正是把 `V_τ` 用错的方式。
    """

    n_total = sum(len(values) for _, values in arms)
    defined = [float(v) for _, values in arms for v in values if v is not None]
    n_defined = len(defined)
    n_arms_with_data = sum(1 for _, values in arms if any(v is not None for v in values))

    clauses: list[tuple[str, str, str]] = []

    # ---- H1 分母存在 ----
    if n_defined > 0:
        clauses.append((H1_C, PASS, f'{n_defined}/{n_total} 个样本有定义'))
    else:
        clauses.append((H1_C, FAIL, f'{n_defined}/{n_total} 个样本有定义——分母为 0，所有派生量均为 None'))

    # ---- 派生量（分母为 0 一律 None）----
    if n_defined == 0:
        minimum = maximum = med = None
        distinct = 0
        distinct_ratio = None
        edge_mass = None
        margin = None
    else:
        minimum = min(defined)
        maximum = max(defined)
        med = median(defined)
        distinct = len(set(defined))
        distinct_ratio = distinct / n_defined
        if declaration.bound == BOUND_UNIT:
            edge_mass = sum(1 for v in defined if v <= 0.0 or v >= 1.0) / n_defined
            margin = min(minimum, 1.0 - maximum)
        elif declaration.bound == BOUND_ZERO:
            edge_mass = sum(1 for v in defined if v <= 0.0) / n_defined
            margin = minimum
        else:
            edge_mass = 0.0
            margin = None

    # ---- H2 未贴界 ----
    if declaration.bound == BOUND_NONE:
        clauses.append((H2_C, PASS, '该判据无自然边界，贴界检查不适用'))
    elif margin is None:
        clauses.append((H2_C, UNKNOWN, '无有定义样本，贴界无从判断'))
    elif edge_mass is not None and edge_mass >= EDGE_MASS_LIMIT:
        clauses.append((H2_C, FAIL, f'全部 {n_defined} 个样本都贴在边界上：可分辨空间为 0'))
    elif margin < MARGIN_FLOOR:
        clauses.append((
            H2_C, WARN,
            f'距边界余量 {margin:.4g} < {MARGIN_FLOOR}（贴界质量 {edge_mass:.1%}）——'
            f'接近饱和，两臂差异会被压到读不出',
        ))
    else:
        clauses.append((H2_C, PASS, f'距边界余量 {margin:.4g}'))

    # ---- H3 两臂可分 ----
    medians: list[float] = []
    for _, values in arms:
        dv = [float(v) for v in values if v is not None]
        if dv:
            medians.append(median(dv))
    if len(medians) < 2 or n_defined == 0:
        arm_gap = None
        separable = None
        clauses.append((H3_C, UNKNOWN, f'只有 {len(medians)} 臂有数据，无法比较'))
    else:
        arm_gap = abs(max(medians) - min(medians))
        lo = [min(float(v) for v in values if v is not None) for _, values in arms
              if any(v is not None for v in values)]
        hi = [max(float(v) for v in values if v is not None) for _, values in arms
              if any(v is not None for v in values)]
        # **严格**不等：两臂取值完全相同时 `a <= b` 恒真，那会被读成「可分」，
        # 而它恰恰是「分不开」本身。这一处曾把 0.9814 两臂相同判成 separable=True。
        separable = (max(lo) < min(hi)) or (max(hi) < min(lo))
        if arm_gap == 0.0 and not separable:
            clauses.append((
                H3_C, FAIL,
                f'两臂中位数相同（{medians[0]:.6g}），且没有被严格分开——'
                f'被报的那个统计量分不开两臂',
            ))
        elif arm_gap == 0.0:
            clauses.append((H3_C, WARN, f'中位数相同但区间不重叠（separable={separable}）'))
        else:
            clauses.append((H3_C, PASS, f'中位差 {arm_gap:.4g}，separable={separable}'))

    # ---- H4 分辨率充足 ----
    if distinct_ratio is None:
        clauses.append((H4_C, UNKNOWN, '无有定义样本'))
    elif distinct == 1 and n_defined >= RESOLUTION_MIN_SAMPLES:
        clauses.append((
            H4_C, FAIL,
            f'{n_defined} 个样本只有 1 个取值——该判据在这批情境上是常数，信息量为 0',
        ))
    elif distinct_ratio < RESOLUTION_FLOOR:
        clauses.append((
            H4_C, WARN,
            f'{distinct} 个取值 / {n_defined} 个样本 = {distinct_ratio:.2f} < '
            f'{RESOLUTION_FLOOR}——整数量化或强离散，量不出细差',
        ))
    else:
        clauses.append((H4_C, PASS, f'{distinct} 个取值 / {n_defined} 个样本 = {distinct_ratio:.2f}'))

    # ---- H5 预算匹配基线 ----
    if declaration.matched_baseline is None:
        clauses.append((H5_C, UNKNOWN, '未声明：登记时须写明同等预算的基线臂是什么'))
    elif declaration.matched_baseline == '':
        clauses.append((H5_C, FAIL, '已声明为「无匹配基线」——增益无法归因（更好的设计 vs 更多的搜索）'))
    else:
        clauses.append((H5_C, PASS, f'基线臂：{declaration.matched_baseline}'))

    # ---- H6 搜索/评测分离 ----
    if declaration.search_seeds is None or declaration.eval_seeds is None:
        clauses.append((H6_C, UNKNOWN, '未声明搜索集/评测集'))
    else:
        shared = set(declaration.search_seeds) & set(declaration.eval_seeds)
        if shared:
            clauses.append((H6_C, FAIL, f'搜索集与评测集有 {len(shared)} 个共同 seed：{sorted(shared)}'))
        else:
            clauses.append((H6_C, PASS, '搜索集与评测集不相交'))

    # ---- H7 报 pass@1 ----
    if declaration.reported_as is None:
        clauses.append((H7_C, UNKNOWN, '未声明报的是 pass@1 还是 pass@k'))
    elif declaration.reported_as == 'pass@k':
        clauses.append((H7_C, FAIL, '只报 pass@k：best-of-k 增益不是单次能力增益'))
    else:
        clauses.append((H7_C, PASS, f'reported_as={declaration.reported_as}'))

    # ---- H8 可证红 ----
    if declaration.can_go_red is None:
        clauses.append((H8_C, UNKNOWN, '未声明是否存在能拉红它的削弱臂'))
    elif not declaration.can_go_red:
        clauses.append((H8_C, FAIL, '已声明「无法被削弱臂拉红」——无区分度的判据应弃用或改造'))
    else:
        clauses.append((H8_C, PASS, '存在能拉红它的削弱臂'))

    # ---- V_τ：逐情境跨臂方差 ----
    width = min((len(values) for _, values in arms), default=0)
    v_by_scenario: list[float | None] = []
    for i in range(width):
        v_by_scenario.append(v_tau([values[i] for _, values in arms]))

    return JudgementHealth(
        name=declaration.name,
        n_total=n_total,
        n_defined=n_defined,
        n_arms_with_data=n_arms_with_data,
        minimum=minimum,
        maximum=maximum,
        median=med,
        distinct=distinct,
        distinct_ratio=distinct_ratio,
        edge_mass=edge_mass,
        boundary_margin=margin,
        arm_gap=arm_gap,
        separable=separable,
        v_tau_by_scenario=tuple(v_by_scenario),
        clauses=tuple(clauses),
    )


__all__ = [
    'BOUND_UNIT',
    'BOUND_ZERO',
    'BOUND_NONE',
    'BOUNDS',
    'CLAUSES',
    'PASS',
    'WARN',
    'FAIL',
    'UNKNOWN',
    'MARGIN_FLOOR',
    'RESOLUTION_FLOOR',
    'EDGE_MASS_LIMIT',
    'RESOLUTION_MIN_SAMPLES',
    'v_tau',
    'JudgementDeclaration',
    'JudgementHealth',
    'assess',
]
