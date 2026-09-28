"""技能固化漏斗的三个分母 —— attempted / passed / reused（docs/03 §11.8）。

**为什么需要它。** 实验 3 的读数曾经是「技能调用成功率 **0/33**」。0/33 是**一个**
零值，而它把三种完全不同的病压成了同一句话：

==================  ==========================  ==========================
零在哪                病在哪                       下一步
==================  ==========================  ==========================
`attempted == 0`     候选根本没被切出来            改切段规则 / 最小帧数 / 能量判据
`passed == 0`        候选切出来了但全被拒          改判据形状或验证门
`reused == 0`        入库了但从来不被调用          改调用面（precondition 太窄 / 规划面不检索技能）
==================  ==========================  ==========================

**三种病指向三个不同的下一步，而只看 0/33 时它们的输出完全一样。** 这就是为什么
「技能表示够不够」这个问题在有三档分母之前无法收敛——它有三种答案。

外部依据：`InducingProgrammaticSkills`（arXiv:2504.06821，ASI）的
attempted_induction / passed_verification / reused 三档分母，以及
`RecordReplay` 的「低层经验 = 参数化动作序列」粒度契约。

**这不是评分。** 本模块只对计数做分类判定，不打分、不排序、不引入奖励（C9）。
"""

from __future__ import annotations

from dataclasses import dataclass

#: 漏斗诊断码。每个码对应**一个**下一步，不是一个笼统的「失败了」。
EMPTY_TRACE = 'EMPTY_TRACE'
NO_WINDOW = 'NO_WINDOW'
NO_POSITIVE_SEGMENT = 'NO_POSITIVE_SEGMENT'
ALL_DUPLICATE = 'ALL_DUPLICATE'
REJECTED_BY_GATE = 'REJECTED_BY_GATE'
NEVER_INVOKED = 'NEVER_INVOKED'
OPEN = 'OPEN'

#: 诊断码 → (卡在哪一段, 下一步做什么)。
DIAGNOSIS: dict[str, tuple[str, str]] = {
    EMPTY_TRACE: (
        '没有帧进入编译',
        '先查快环有没有产出可编译的 trace，而不是查技能表示',
    ),
    NO_WINDOW: (
        '切窗阶段',
        '改切段规则：min_frames / max_frames，或「直接成功」的判据（_is_direct_success）',
    ),
    NO_POSITIVE_SEGMENT: (
        '能量判据阶段',
        '世界给不出净收益为正的连续成功段——先查世界与本能，不要查技能表示',
    ),
    ALL_DUPLICATE: (
        '去重阶段',
        '候选与库中已有技能签名相同——查签名过粗（会把不同行为判成同一条）',
    ),
    REJECTED_BY_GATE: (
        '验证门',
        '候选是真的、门是真的拒——查判据形状（债务 25/26/27/28 那一族）',
    ),
    NEVER_INVOKED: (
        '调用面',
        '技能进了库却一次没被调用——查 precondition（initiation set 太窄）或规划面不检索技能',
    ),
    OPEN: (
        '漏斗已贯通',
        '三档都有非零计数，可以开始看「复用之后有没有用」（行为差 / 环境侧淘汰）',
    ),
}


@dataclass(frozen=True)
class InductionFunnel:
    """一次编译周期的漏斗计数。**每个字段都是一个分母。**

    字段顺序就是漏斗顺序：帧 → 窗 → 候选 → 去重 → 入库 → 复用。
    任何一段为 0，后面的段全部无意义（计数必为 0），所以诊断必须**从前往后**
    找第一个 0，而不是从后往前看那个最显眼的 0。
    """

    frames: int = 0
    windows: int = 0
    positive: int = 0
    new_candidates: int = 0
    committed: int = 0
    reused: int = 0

    def __post_init__(self) -> None:
        for name in ('frames', 'windows', 'positive', 'new_candidates', 'committed', 'reused'):
            value = getattr(self, name)
            if value < 0:
                raise ValueError(f'漏斗计数不得为负：{name}={value}')
        # 漏斗是单调不增的：后面的段不可能比前面多。
        # 违反它说明**计数来自不同的来源**（例如 committed 由库给、positive 由探针给），
        # 那比计数为 0 更难发现，所以在这里直接拒收。
        stages = (
            ('frames', self.frames),
            ('windows', self.windows),
            ('positive', self.positive),
            ('new_candidates', self.new_candidates),
            ('committed', self.committed),
        )
        for (prev_name, prev), (name, value) in zip(stages, stages[1:]):
            if value > prev:
                raise ValueError(
                    f'漏斗不单调：{prev_name}={prev} < {name}={value}；'
                    f'计数可能来自不同来源'
                )

    @property
    def attempted(self) -> int:
        """ASI 的 attempted：**真的成为候选**的段数（净收益为正）。"""

        return self.positive

    @property
    def passed(self) -> int:
        """ASI 的 passed：过门并入库的技能数。"""

        return self.committed

    @property
    def losses(self) -> tuple[tuple[str, str, int], ...]:
        """逐段流失：`(上游, 下游, 丢了多少)`。全为 0 时返回空——那是漏斗贯通。"""

        pairs = (
            ('帧', '窗', self.frames, self.windows),
            ('窗', '候选', self.windows, self.positive),
            ('候选', '去重', self.positive, self.new_candidates),
            ('去重', '入库', self.new_candidates, self.committed),
        )
        return tuple(
            (up, down, up_n - down_n) for up, down, up_n, down_n in pairs
        )

    @property
    def first_empty_stage(self) -> str | None:
        """从前往后**第一个**为 0 的段名。全非 0 时返回 None。"""

        for name in ('frames', 'windows', 'positive', 'new_candidates', 'committed'):
            if getattr(self, name) == 0:
                return name
        if self.reused == 0:
            return 'reused'
        return None

    @property
    def reuse_rate(self) -> float | None:
        """复用率 = reused / committed。

        **committed == 0 → `None`，不是 0.0**：分母为 0 时「复用率为 0」是
        一个假读数，它会让「没有技能可复用」读成「技能都没被复用」。
        """

        if self.committed == 0:
            return None
        return self.reused / self.committed

    @property
    def is_open(self) -> bool:
        """漏斗贯通（三档全非零）。委托模块级 ``diagnose``——判定只有一处。"""

        return diagnose(self).code == OPEN


@dataclass(frozen=True)
class FunnelDiagnosis:
    """漏斗诊断。`code` 决定下一步，`stage` 说明卡在哪一段。"""

    code: str
    stage: str
    next_action: str
    first_empty_stage: str | None

    @property
    def is_open(self) -> bool:
        return self.code == OPEN


def diagnose(funnel: InductionFunnel) -> FunnelDiagnosis:
    """从前往后找第一个 0，给出**一个**下一步。

    顺序不可颠倒：`reused == 0` 在 `windows == 0` 时是**必然**的，把它报成
    「调用面有问题」会让人去改 precondition，而真正的问题在切段。
    这正是只看 0/33 会犯的错。
    """

    if funnel.frames == 0:
        code = EMPTY_TRACE
    elif funnel.windows == 0:
        code = NO_WINDOW
    elif funnel.positive == 0:
        code = NO_POSITIVE_SEGMENT
    elif funnel.new_candidates == 0:
        code = ALL_DUPLICATE
    elif funnel.committed == 0:
        code = REJECTED_BY_GATE
    elif funnel.reused == 0:
        code = NEVER_INVOKED
    else:
        code = OPEN

    stage, action = DIAGNOSIS[code]
    return FunnelDiagnosis(
        code=code,
        stage=stage,
        next_action=action,
        first_empty_stage=funnel.first_empty_stage,
    )


__all__ = [
    'EMPTY_TRACE',
    'NO_WINDOW',
    'NO_POSITIVE_SEGMENT',
    'ALL_DUPLICATE',
    'REJECTED_BY_GATE',
    'NEVER_INVOKED',
    'OPEN',
    'DIAGNOSIS',
    'InductionFunnel',
    'FunnelDiagnosis',
    'diagnose',
]
