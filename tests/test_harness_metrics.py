"""实验脚手架上两个「曾经只有名字」的算式：危险回避率与能量消耗变化。

由来：12 §4.2 与 14 §5.2 的表格里这两个指标长期**只有名字**——没有公式、
没有分母、没有窗口（14 §6.3.4）。算式补在 ``experiments/_harness.py``，
本文件用合成 trace 把它钉住。

**本文件里最重要的一条不是"算得对"，是"算不出来时要说算不出来"**：

``test_no_hazard_visible_is_none_not_one`` —— 分母为 0 时返回 ``None``
而不是 1.0。项目已经咬过一次这个形状：实验 6/7 的四个 ``1.0000`` 里
有两个的分母来自注入样本，自然运行下分母是 0。把 0/0 打印成 100%
会让"世界里没有危险源"伪装成"躲得极好"，而那正好是**最不该被表扬的回合**。
"""

from __future__ import annotations

import pytest

from SSEA.fast_loop import STATE_RUN, STATE_SLEEP, STATE_WAKE, StepRecord
from SSEA.sse_protocols import (
    Action,
    BodyState,
    EnvironmentSummary,
    Feedback,
    Locomotion,
    ObjectVector,
    Observation,
    default_constraints,
)
from experiments._harness import (
    ActionDivergence,
    EpisodeResult,
    FrameAction,
    _context,
    action_divergence,
    pool_action_divergences,
    energy_by_version_window,
    energy_change_between_windows,
    hazard_frames,
    mean_defined,
    resource_frames,
    run_episode,
    survival_summary,
    SurvivalSummary,
)
from experiments._instinct import seeded_store
from SSEA.instinct import preset_blob

FP_A = (("thresholds", 0),)
FP_B = (("thresholds", 1),)


# ----------------------------------------------------------------------
#  合成 trace
# ----------------------------------------------------------------------


def thing(object_id: str, distance: float, *, threat: float = 0.0, value: float = 0.0):
    return ObjectVector(
        object_id=object_id,
        category_id=2 if threat > 0 else 1,
        distance=distance,
        direction=(1.0, 0.0),
        velocity=(0.0, 0.0),
        resource_value=value,
        threat_level=threat,
        affordance=(),
    )


def frame(
    n: int,
    *,
    objects: tuple[ObjectVector, ...] = (),
    energy_change: float = 0.0,
    damage_change: float = 0.0,
    fingerprint: tuple[tuple[str, int], ...] = FP_A,
    state: str = STATE_RUN,
) -> StepRecord:
    """一条 StepRecord。字段够本文件用即可，其余填空。"""

    action = Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0))
    return StepRecord(
        frame=n,
        state=state,
        observation=Observation(
            time=float(n),
            body=BodyState(
                energy=1.0,
                damage=0.0,
                fatigue=0.0,
                position=(0.0, 0.0),
                orientation=(1.0, 0.0),
                action_constraints=default_constraints(),
                internal_state=(),
            ),
            environment=EnvironmentSummary(
                light_level=1.0,
                temperature=0.5,
                danger_level=0.0,
                resource_density=0.0,
                time_phase="day",
            ),
            objects=objects,
        ),
        feedback=Feedback(
            energy_change=energy_change,
            damage_change=damage_change,
            fatigue_change=0.0,
            prediction_error=0.0,
            action_success=True,
            survived=True,
        ),
        decoded_action=action,
        executed_action=action,
        skill_event=None,
        context_fingerprint=fingerprint,
        intent=None,
    )


def result(**overrides) -> EpisodeResult:
    """一个 EpisodeResult，只要本文件关心的那几个字段。"""

    base = dict(
        seed=0,
        frames=1,
        alive=True,
        run_frames=1,
        sleep_frames=0,
        wake_frames=0,
        constraint_rejected=0,
        internal_errors=0,
        max_consecutive_run=1,
        language_crossings=0,
        observation_leaks=0,
        proposals=0,
        applied=0,
        rejected=0,
    )
    base.update(overrides)
    return EpisodeResult(**base)


def _stats(**overrides) -> dict[str, int]:
    """一份 ``MemoryStats.as_dict()`` 形状的字典。

    键名照抄 ``MemoryStats``（``memory_system.py``），**不另起一套**——
    两边漂移的话，本文件的断言会在真读数上失效而测试仍是绿的。
    """

    base = dict(
        frames=0,
        retrievals=0,
        hits=0,
        misses=0,
        writes=0,
        merged=0,
        evicted=0,
        refused=0,
        incompatible=0,
        truncated=0,
    )
    base.update(overrides)
    return base


# ----------------------------------------------------------------------
#  危险回避率：分母为 0 时必须是 None
# ----------------------------------------------------------------------


class TestHazardAvoidanceDenominator:
    def test_no_hazard_visible_is_none_not_one(self):
        """**本文件最重要的一条。** 只见资源、不见危险源 → 无分母 → None。

        断言写成 `is None` 而不是 `!= 1.0`：0.0 也是错的——
        "没东西可回避"既不是躲得好也不是躲得差，它**没有取值**。
        """

        trace = [
            frame(0, objects=(thing("res_0", 2.0, value=0.5),)),
            frame(1, objects=(thing("res_0", 1.5, value=0.5),)),
        ]
        visible, contact, _ = hazard_frames(trace)
        assert (visible, contact) == (0, 0)

        r = result(hazard_visible_frames=0, hazard_contact_frames=0)
        assert r.hazard_avoidance_rate is None
        assert r.mean_nearest_hazard_distance is None

    def test_empty_trace_is_none(self):
        assert hazard_frames([]) == (0, 0, 0.0)
        assert result().hazard_avoidance_rate is None

    def test_prop_is_not_a_hazard(self):
        """prop 的 threat_level 是 0 → 不构成暴露。判据是 threat_level 不是类别号。"""

        trace = [frame(0, objects=(thing("prop_0", 1.0),))]
        assert hazard_frames(trace)[0] == 0

    def test_threatened_frames_but_never_touched_is_one(self):
        """有分母且一次没被碰到 → 1.0。这一次 1.0 是**挣来的**，分母是 3。"""

        trace = [frame(n, objects=(thing("haz_0", 3.0, threat=0.8),)) for n in range(3)]
        visible, contact, _ = hazard_frames(trace)
        assert (visible, contact) == (3, 0)
        assert result(hazard_visible_frames=visible).hazard_avoidance_rate == 1.0

    def test_half_contacted(self):
        trace = [
            frame(0, objects=(thing("haz_0", 0.5, threat=0.8),), damage_change=0.16),
            frame(1, objects=(thing("haz_0", 0.9, threat=0.8),)),
            frame(2, objects=(thing("haz_0", 0.4, threat=0.8),), damage_change=0.16),
            frame(3, objects=(thing("haz_0", 1.2, threat=0.8),)),
        ]
        visible, contact, _ = hazard_frames(trace)
        assert (visible, contact) == (4, 2)
        r = result(hazard_visible_frames=visible, hazard_contact_frames=contact)
        assert r.hazard_avoidance_rate == pytest.approx(0.5)


# ----------------------------------------------------------------------
#  危险暴露的三个原始量怎么数
# ----------------------------------------------------------------------


class TestHazardFrameCounting:
    def test_only_run_frames_count(self):
        """睡眠/Wake 帧不进分母——它们不产生动作，也不接触危险源。"""

        trace = [
            frame(0, objects=(thing("haz_0", 3.0, threat=0.8),)),
            frame(1, objects=(thing("haz_0", 3.0, threat=0.8),), state=STATE_SLEEP),
            frame(2, objects=(thing("haz_0", 3.0, threat=0.8),), state=STATE_WAKE),
            frame(3, objects=(thing("haz_0", 3.0, threat=0.8),)),
        ]
        assert hazard_frames(trace)[0] == 2

    def test_zero_damage_is_not_a_contact(self):
        """``damage_change == 0.0`` 不算接触——危险源在视野内但没碰到。

        这正是"危险源可见"与"被危险源伤了"的分界，也是这个指标能区分
        "躲开了"与"没遇上"的地方。
        """

        trace = [
            frame(0, objects=(thing("haz_0", 2.0, threat=0.8),), damage_change=0.0),
            frame(1, objects=(thing("haz_0", 2.0, threat=0.8),), damage_change=0.16),
        ]
        assert hazard_frames(trace)[1] == 1

    def test_damage_without_visible_hazard_is_not_counted(self):
        """分子只在分母的帧上取。看不见危险源却受了伤 → 不进分子。

        这保证 ``回避率 = 1 − 分子/分母`` 恒在 [0,1]：分子永远是分母的子集。
        """

        trace = [frame(0, objects=(), damage_change=0.16)]
        assert hazard_frames(trace)[:2] == (0, 0)

    def test_nearest_hazard_distance_uses_the_nearest(self):
        trace = [
            frame(
                0,
                objects=(
                    thing("haz_far", 5.0, threat=0.3),
                    thing("haz_near", 1.5, threat=0.9),
                    thing("res_0", 0.4, value=0.7),  # 资源更近，但不是危险源
                ),
            )
        ]
        visible, _, distance_sum = hazard_frames(trace)
        assert (visible, distance_sum) == (1, 1.5)
        assert result(
            hazard_visible_frames=1, nearest_hazard_distance_sum=1.5
        ).mean_nearest_hazard_distance == pytest.approx(1.5)


# ----------------------------------------------------------------------
#  能量消耗变化：必须是两个窗口的差，窗口只有一个时无定义
# ----------------------------------------------------------------------


class TestEnergyChangeBetweenWindows:
    def test_needs_two_windows(self):
        """只有一个版本窗口 → ``None``，不是 0.0。

        0.0 会被读成"固化没有降低消耗"，而事实是**没有发生过固化**。
        没有数字比假数字好。
        """

        trace = [frame(n, energy_change=-0.02, fingerprint=FP_A) for n in range(5)]
        assert len(energy_by_version_window(trace)) == 1
        assert energy_change_between_windows(trace) is None
        assert energy_change_between_windows([]) is None


# ----------------------------------------------------------------------
#  资源侧：与危险侧对称，「趋近」这个动作就靠它看
# ----------------------------------------------------------------------


class TestResourceDistance:
    """最近资源距离 = 「本能有没有让它靠近」的**唯一**读数。

    为什么非有它不可：``ENERGY_GAINED`` 为 0 有两种完全不同的成因——
    "根本没靠近"与"靠近了但抓取链没通"——**在它上面长得一模一样**，
    而这两种结论指向完全不同的下一步（查本能接线 vs 做 ②.2）。
    连续量是唯一能把它们分开的东西。
    """

    def test_nothing_visible_is_none_not_zero(self):
        """一帧都没看见资源 → ``None``，不是 0.0。

        0.0 会被读成"贴着资源"，而事实是这个量在那一轮里**不存在**。
        与 ``test_no_hazard_visible_is_none_not_one`` 同一条纪律。
        """

        trace = [frame(0, objects=(thing("prop_0", 2.0),))]
        assert resource_frames(trace) == (0, 0.0)
        assert result().mean_nearest_resource_distance is None

    def test_prop_is_not_a_resource(self):
        """``resource_value == 0`` 的对象不是资源——prop 与危险源都不算。

        判据取 ``resource_value > 0`` 而不是 ``category_id``：后者是环境
        标注的整数，语义**刻意不由模型解释**（``object_vector.py``）。
        """

        trace = [
            frame(
                0,
                objects=(
                    thing("prop_0", 0.1),  # 最近，但不是资源
                    thing("haz_0", 0.2, threat=0.8),  # 更近，但也不是资源
                    thing("res_0", 3.0, value=0.7),
                ),
            )
        ]
        assert resource_frames(trace) == (1, 3.0)

    def test_only_run_frames_count(self):
        trace = [
            frame(0, objects=(thing("res_0", 3.0, value=0.7),)),
            frame(1, objects=(thing("res_0", 3.0, value=0.7),), state=STATE_SLEEP),
            frame(2, objects=(thing("res_0", 3.0, value=0.7),), state=STATE_WAKE),
        ]
        assert resource_frames(trace)[0] == 1

    def test_uses_the_nearest_resource(self):
        trace = [
            frame(
                0,
                objects=(
                    thing("res_far", 5.0, value=0.3),
                    thing("res_near", 0.4, value=0.9),
                ),
            )
        ]
        assert resource_frames(trace) == (1, 0.4)
        assert result(
            resource_visible_frames=1, nearest_resource_distance_sum=0.4
        ).mean_nearest_resource_distance == pytest.approx(0.4)


# ----------------------------------------------------------------------
#  播种的结构必须真的进快环
# ----------------------------------------------------------------------


class TestSeededStructureReachesTheFastLoop:
    """``run_episode(store=...)`` 必须意味着「快环从这个结构起步」。

    这个洞真实存在过，而且它**不报错**：``run_episode`` 把 store 交给了慢环，
    初始上下文却仍从 ``make_context()`` 现造一份**空结构**。于是预置在 store
    里的本能进不了快环，除非慢环**恰好应用了一条提案**——而慢环要应用提案
    得先有可编译段，可编译段又要求世界里有成功可学……

    闭环咬住了自己，代价是两臂对照跑出"本能没效果"，而真相是**本能从未装上**。
    最毒的一点：``ENERGY_GAINED`` 两臂都是 0，"没装上"与"装上了但没抓到"
    在数字上完全一样——所以只有**看别处的量**才能发现。

    两条测试的分工要说清，否则会以为它们等价：

    - ``test_context_comes_from_the_store`` 钉的是 ``_context`` **这个函数**的
      契约。它单独跑不出那个洞——它不看调用点。
    - ``test_the_instinct_actually_pulls_the_agent_toward_resources`` 才是
      **真正的守卫**：它跑整条 ``run_episode``，所以调用点退回 ``_context()``
      时它会红（实测红过：两臂距离逐位相同，``2.2526 >= 2.2526``）。
    """

    def test_context_comes_from_the_store(self):
        store, outcome = seeded_store("approach", preset_blob("approach"))
        assert outcome.applied, outcome.reason

        seeded = _context(store)
        assert seeded.adapters, "播种后的快照里应当有 adapter——否则下面那条是废话"
        assert seeded.adapters == store.snapshot().adapters

        # 无 store 时仍是默认空结构：老调用点的行为一位不变。
        assert _context().adapters == {}

    def test_the_instinct_actually_pulls_the_agent_toward_resources(self):
        """逐 seed 断言靠近——**不是均值靠近**，均值会被一个 seed 带偏。

        判据是「本能臂的最近资源距离严格更小」。这个断言在洞存在时会红：
        那时两臂逐位相同，距离也相同。
        """

        seeds = (0, 1)
        frames = 60

        off = [run_episode(s, frames=frames) for s in seeds]
        store, outcome = seeded_store("approach", preset_blob("approach"))
        assert outcome.applied, outcome.reason
        on = [run_episode(s, frames=frames, store=store) for s in seeds]

        for seed, a, b in zip(seeds, off, on):
            assert a.mean_nearest_resource_distance is not None, (
                f"seed {seed} 的对照臂一帧都没看见资源，这条测试失去意义"
            )
            assert b.mean_nearest_resource_distance is not None, f"seed {seed} 无定义"
            assert (
                b.mean_nearest_resource_distance < a.mean_nearest_resource_distance
            ), (
                f"seed {seed}: 装了趋近本能却没更靠近资源 "
                f"({b.mean_nearest_resource_distance:.3f} >= "
                f"{a.mean_nearest_resource_distance:.3f})——"
                f"先查本能有没有进快环，别急着怪本能没用"
            )

    def test_subtracts_later_minus_earlier(self):
        """固化后（后一个窗口）减固化前（前一个窗口），按每 RUN 帧口径。"""

        trace = [
            frame(n, energy_change=-0.02, fingerprint=FP_A) for n in range(5)
        ] + [frame(100 + n, energy_change=-0.01, fingerprint=FP_B) for n in range(4)]

        windows = energy_by_version_window(trace)
        assert [w["run_frames"] for w in windows] == [5, 4]
        assert windows[0]["energy_spent_per_run_frame"] == pytest.approx(0.02)
        assert windows[1]["energy_spent_per_run_frame"] == pytest.approx(0.01)

        # 每帧少花 0.01，所以变化是 −0.01（"固化降低了消耗"是负数）。
        assert energy_change_between_windows(trace) == pytest.approx(-0.01)

    def test_sleep_gain_does_not_offset_spend(self):
        """窗口口径沿用「毛支出」：睡眠期的能量**恢复**不抵消运行期的消耗。

        ``energy_spent`` 是负部绝对值之和，所以同一窗口里 +0.5 的恢复
        与 −0.5 的支出**不会**互相抵消——这正是模块 docstring 一之二第 2 条。
        """

        trace = [
            frame(0, energy_change=-0.5, fingerprint=FP_A),
            frame(1, energy_change=0.5, fingerprint=FP_A),
        ]
        assert energy_by_version_window(trace)[0]["energy_spent"] == pytest.approx(0.5)


# ----------------------------------------------------------------------
#  跨 seed 聚合：None 不进平均，但分母要留下来
# ----------------------------------------------------------------------


class TestMeanDefined:
    def test_skips_none_and_reports_denominator(self):
        mean, n = mean_defined([1.0, None, 0.0, None])
        assert mean == pytest.approx(0.5)
        assert n == 2

    def test_all_none(self):
        assert mean_defined([None, None]) == (None, 0)

    def test_empty(self):
        assert mean_defined([]) == (None, 0)

    def test_zero_is_a_real_value_not_a_gap(self):
        """0.0 是要参与平均的**实测值**（一次都没躲开），不是缺数据。"""

        mean, n = mean_defined([0.0, 0.0])
        assert (mean, n) == (0.0, 2)


# ----------------------------------------------------------------------
#  记忆侧（实验 2）：没有仪器 ≠ 读数为 0
# ----------------------------------------------------------------------


class TestMemoryMetrics:
    def test_no_instrument_is_not_the_same_as_zero_writes(self):
        """**这一组最重要的一条。** 零检索器与"记忆开着但什么都没写"
        必须可区分——前者没有仪器（``memory_instrumented`` 为假、
        两个率都是 ``None``），后者有仪器且读数是 0（两个率是数字或
        分母为 0 的 ``None``）。混同会把对照组的"关掉了"读成"没效果"。
        """

        control = result()  # memory_stats 默认空字典 = 没有仪器
        assert control.memory_instrumented is False
        assert control.memory_writes is None
        assert control.memory_write_success_rate is None
        assert control.memory_hit_rate is None

        live = result(memory_stats=_stats(writes=0, retrievals=5, hits=0))
        assert live.memory_instrumented is True
        assert live.memory_writes == 0
        assert live.memory_hit_rate == 0.0, "有检索、零命中，是一个真实的 0"

    def test_write_rate_denominator_is_requests_not_frames(self):
        """分母是**请求数**。用帧数当分母会把它变成"模型有多爱记东西"。"""

        r = result(
            frames=100,
            run_frames=100,
            memory_write_requests=4,
            memory_stats=_stats(writes=3),
        )
        assert r.memory_write_success_rate == pytest.approx(0.75)

    def test_never_requested_is_none_not_one(self):
        """一次都没请求过 → 无定义。写成 1.0 会读成"写入机制很可靠"。

        记忆门控未训练（12 §6 债务 5），所以"一次都没请求"是真会发生的。
        """

        r = result(memory_write_requests=0, memory_stats=_stats(writes=0))
        assert r.memory_write_success_rate is None

    def test_hit_rate_denominator_is_retrievals_not_frames(self):
        """检索受策略 ``stride`` 过滤，``retrievals`` 可以远小于 ``frames``。"""

        r = result(
            frames=100,
            memory_stats=_stats(retrievals=10, hits=4),
        )
        assert r.memory_hit_rate == pytest.approx(0.4)

    def test_no_retrieval_is_none(self):
        r = result(memory_stats=_stats(retrievals=0, hits=0))
        assert r.memory_hit_rate is None


# ----------------------------------------------------------------------
#  技能侧（实验 3）：调用成功率的分母来自运行器，不是事件计数器
# ----------------------------------------------------------------------


class TestSkillMetrics:
    def test_no_call_is_none_not_zero(self):
        """从没请求过 → 无定义。0.0 会被读成"每次调用都失败"。"""

        r = result()
        assert r.skill_calls == 0
        assert r.skill_call_success_rate is None

    def test_all_failed_is_a_real_zero(self):
        """真调用了、全失败 → 0.0。这与"没调用过"是两件事。"""

        r = result(skill_calls=33, skill_failures=33)
        assert r.skill_call_success_rate == 0.0

    def test_rate_is_by_event_not_by_frame(self):
        """一次调用跨多帧，按帧算会把长技能的成功率稀释掉。"""

        r = result(skill_calls=40, skill_successes=3, skill_failures=1)
        assert r.skill_call_success_rate == pytest.approx(0.75)

    def test_the_environment_counter_is_not_the_source(self):
        """**钉住指标来源。** ``event_counts()["SKILL_SUCCESS"]`` 恒为 0——
        这两个事件类型没有生产者（``test_environment.py`` 里有一条测试
        钉着那份无生产者清单）。从计数器读会把"33 次全失败"读成
        "一次都没调用过"，而这两句话指向完全不同的下一步。
        """

        from SSEA.environment import Environment

        env = Environment(seed=1)
        counts = env.event_counts()
        assert counts["SKILL_SUCCESS"] == 0 and counts["SKILL_FAILURE"] == 0
        # 而运行器是有生产者的：
        r = result(skill_calls=33, skill_failures=33)
        assert r.skill_events == 33


# ----------------------------------------------------------------------
#  能量消耗变化（实验 3）：窗口不足两个时无定义
# ----------------------------------------------------------------------


class TestEnergyChangeField:
    def test_no_version_switch_is_none(self):
        r = result(energy_windows=1, energy_change=None)
        assert r.energy_change is None

    def test_zero_change_is_a_real_value(self):
        """固化了但支出没动 → 0.0，不是 ``None``。"""

        r = result(energy_windows=2, energy_change=0.0)
        assert r.energy_change == 0.0


# ----------------------------------------------------------------------
#  第三档判据：两臂动作序列的逐帧差（实验 2）
# ----------------------------------------------------------------------


def act(
    direction: tuple[float, ...] = (1.0, 0.0),
    speed: float = 0.5,
    duration: float = 0.2,
) -> FrameAction:
    return FrameAction(direction=direction, speed=speed, duration=duration)


class TestActionDivergence:
    """``action_divergence`` 的算式本身。

    这一档是 2026-09-28 补的：前两档（5 个整数 / 门决策计数）在 1e-3
    量级的扰动上量不出差，而它们量不出时的输出与「两臂真的一样」
    **完全一样**。本类是那个洞的回归钉子（12 §6 债务 21）。
    """

    def test_identical_traces_differ_on_nothing(self):
        a = [act(), act(), act()]
        d = action_divergence(a, list(a))
        assert d.compared == 3
        assert d.differing_frames == 0
        assert d.direction_max == 0.0
        assert d.lengths_differ is False

    def test_a_one_milli_epsilon_direction_change_is_visible(self):
        """**这一条是本类存在的理由**：1e-3 的扰动必须被看见。

        第一档（5 个整数）看不见它——见下面
        ``TestCoarseSignatureIsBlindToIt``。
        """

        a = [act() for _ in range(10)]
        b = [act(direction=(1.0, 1e-3)) for _ in range(10)]
        d = action_divergence(a, b)
        assert d.differing_frames == 10
        assert d.differing_ratio == 1.0
        assert d.direction_median == pytest.approx(1e-3, rel=0.01)
        assert d.direction_max == pytest.approx(1e-3, rel=0.01)

    def test_length_mismatch_is_reported_not_hidden(self):
        """静默截断会把「两臂长度不同」藏起来，而长度本身是行为差。"""

        d = action_divergence([act()] * 5, [act()] * 3)
        assert d.frames == (5, 3)
        assert d.compared == 3
        assert d.lengths_differ is True

    def test_dimension_mismatch_is_counted_not_zipped_away(self):
        """3 维对 2 维不能靠 ``zip`` 截成"差得很小"——那是假数字。"""

        d = action_divergence([act(direction=(1.0, 0.0, 5.0))], [act((1.0, 0.0))])
        assert d.dim_mismatches == 1
        assert d.direction_diffs == ()
        assert d.differing_frames == 0

    def test_nothing_compared_is_zero_not_a_verdict(self):
        """没有帧可比时比率为 0，但**那什么都没说**——调用方要看 ``compared``。"""

        d = action_divergence([], [])
        assert d.compared == 0
        assert d.differing_ratio == 0.0
        assert d.direction_median == 0.0
        assert d.direction_max == 0.0

    def test_percentiles(self):
        d = ActionDivergence(
            frames=(10, 10),
            compared=10,
            dim_mismatches=0,
            direction_diffs=tuple(float(i) for i in range(10)),
            speed_diffs=(),
            duration_diffs=(),
        )
        assert d.direction_median == pytest.approx(4.5)
        assert d.direction_p90 == pytest.approx(8.1)


class TestPoolActionDivergences:
    def test_pooling_concatenates_and_sums(self):
        one = action_divergence([act()], [act(direction=(0.0, 1.0))])
        two = action_divergence([act()] * 3, [act()] * 3)
        pooled = pool_action_divergences([one, two])
        assert pooled.compared == 4
        assert pooled.frames == (4, 4)
        assert pooled.differing_frames == 1
        assert len(pooled.direction_diffs) == 4

    def test_pooling_does_not_average_per_seed_medians(self):
        """合池而不是平均中位数——平均会把双峰分布抹平。"""

        # seed 甲：完全一样；seed 乙：差得很大。平均中位数会得到中间值。
        quiet = action_divergence([act()] * 10, [act()] * 10)
        loud = action_divergence([act()] * 10, [act(direction=(0.0, 1.0))] * 10)
        pooled = pool_action_divergences([quiet, loud])
        assert pooled.differing_frames == 10  # 不是 5
        assert pooled.compared == 20


class TestCoarseSignatureIsBlindToIt:
    """**债务 21 的回归钉子**：粗档说"一样"，细档说"不一样"。

    这一条把 2026-09-28 那次误读的形状钉死了——两个 ``EpisodeResult``
    的 5 个整数完全相同，而动作序列逐帧不同。谁要是再把
    ``coarse_signature`` 的相等读成「两臂逐位相同」，先看这里。
    """

    def _pair(self) -> tuple[EpisodeResult, EpisodeResult]:
        base = dict(frames=3, run_frames=3, compileable_segments=0)
        a = result(**base, action_trace=tuple(act() for _ in range(3)))
        b = result(
            **base,
            action_trace=tuple(act(direction=(1.0, 1e-3)) for _ in range(3)),
        )
        return a, b

    def test_coarse_signature_says_identical(self):
        from experiments.exp2_memory_recall import coarse_signature

        a, b = self._pair()
        assert coarse_signature(a) == coarse_signature(b)

    def test_action_divergence_says_different(self):
        a, b = self._pair()
        assert action_divergence(a.action_trace, b.action_trace).differing_frames == 3


class TestFrameActionOf:
    def test_reads_the_decoded_locomotion(self):
        action = Action(
            locomotion=Locomotion(direction=(0.25, -0.5), speed=0.75, duration=0.5),
            manipulation=None,
            communication=None,
            memory=None,
            skill=None,
            self_modification=None,
        )
        fa = FrameAction.of(action)
        assert fa.direction == (0.25, -0.5)
        assert fa.speed == 0.75
        assert fa.duration == 0.5

    def test_run_episode_captures_one_frame_action_per_trace_record(self):
        store, _ = seeded_store("approach", preset_blob("approach"))
        r = run_episode(0, frames=12, store=store)
        assert len(r.action_trace) == r.frames


#: 派生量**不得**引用的名字——引用了就等于把「配置上限」当成了分母。
CAP_NAMES = ("max_frames", "DEFAULT_FRAMES")


def _references_cap(source: str) -> bool:
    """这段源码有没有引用配置上限。**抽出来是为了让它可被单独证红。"""

    return any(name in source for name in CAP_NAMES)


def _metrics_that_reference_the_cap() -> list:
    """扫 ``EpisodeResult`` 的**全部派生指标**，找出引用了「配置上限」的那些。

    一个从不报警的扫描器与一份健康的代码在输出上无法区分（项目的守卫纪律），
    所以判定逻辑被抽成 :func:`_references_cap`，由测试**两个方向**都钉住。
    """

    import inspect

    from experiments._harness import EpisodeResult

    offenders = []
    for name, member in vars(EpisodeResult).items():
        if isinstance(member, property) and member.fget is not None:
            if _references_cap(inspect.getsource(member.fget)):
                offenders.append(name)
    return sorted(offenders)


class TestFrameCapIsNotADenominator:
    """债务 31：**上限是上限，不是分母**。

    2026-09-29 实测：8/8 个 seed 全部在 66–182 帧死亡，**0/8** 活到 200。
    审计结论是「代码里没有一处拿上限当分母」——但那句话必须**可执行**，
    否则它只是一句读过代码的人的断言。本类把它钉成两条守卫。
    """

    def test_raising_the_cap_does_not_change_the_episode(self) -> None:
        """**本类的主守卫。** 同一个 seed，上限 200 与 1000 必须给出**同一条**轨迹。

        若哪天有人把上限接进了任何判据/派生量，这条会红——因为两次跑的上限不同。
        """

        from experiments._harness import run_episode
        from experiments.exp3_skill_consolidation import fresh_store

        low = run_episode(3, frames=200, store=fresh_store(), slow_loop=lambda t: None)
        high = run_episode(3, frames=1000, store=fresh_store(), slow_loop=lambda t: None)
        assert low.frames == high.frames
        assert low.alive is False and high.alive is False
        assert low.action_trace == high.action_trace

    def test_no_derived_metric_references_the_cap(self) -> None:
        assert _metrics_that_reference_the_cap() == []

    def test_the_scanner_can_actually_go_red(self) -> None:
        """判定逻辑必须**两个方向**都能出结果——否则上一条是假守卫。"""

        assert _references_cap("return 1.0 / DEFAULT_FRAMES") is True
        assert _references_cap("return self.internal_errors / self.frames") is False

    def test_a_real_property_source_is_visible_to_the_scanner(self) -> None:
        """`inspect.getsource` 在真实属性上确实拿得到源码。

        拿不到时 ``_metrics_that_reference_the_cap`` 会抛 ``OSError`` 而不是
        静默返回空列表——但这条把「拿得到」本身钉住，免得哪天换成打包/冻结
        运行方式后它变成一条永远为真的守卫。
        """

        import inspect

        from experiments._harness import EpisodeResult

        src = inspect.getsource(EpisodeResult.interface_error_rate.fget)
        assert "self.frames" in src


class TestSurvivalSummary:
    """存活读数是**淘汰函数的输出**——唯一一条模型碰不到的判据。"""

    def test_headline_keeps_cap_and_measurement_apart(self) -> None:
        summary = SurvivalSummary(8, 8, 122.5, 66, 182, 0)
        line = summary.headline(200)
        assert "200" in line and "66–182" in line
        assert "8/8 未活到上限" in line

    def test_rows_put_survival_first(self) -> None:
        summary = SurvivalSummary(8, 8, 122.5, 66, 182, 0)
        rows = summary.rows()
        assert rows[0][0].startswith("存活帧")
        assert "8/8" in str(rows[1][1])

    def test_no_results_is_none_not_zero(self) -> None:
        summary = survival_summary([], 200)
        assert summary.median_frames is None
        assert "一轮都没跑起来" in summary.headline(200)

    def test_at_cap_counts_only_frames_at_or_above_the_cap(self) -> None:
        from experiments.exp3_skill_consolidation import fresh_store
        from experiments._harness import run_episode

        rs = [run_episode(0, frames=40, store=fresh_store(), slow_loop=lambda t: None)]
        s = survival_summary(rs, 40)
        assert s.n == 1
        # 上限 40 时那一轮会活到上限（自然死亡在 60–90 帧之后）
        assert s.at_cap == 1
        assert survival_summary(rs, 200).at_cap == 0


class TestActionSideDenominator:
    """`run_action_success_rate` —— 「动作全失败」这一档的分母。

    2026-09-29 实测：8 个 seed 里有 **3 个**是 `0/68`、`0/74`、`0/65`——
    它们靠睡眠活着，而 `ACTION_FAILED` 与帧数相等。没有这个分母，
    「一帧 RUN 都没跑过」与「跑了但一次没成功」在 `0` 上长得一样。
    """

    def test_zero_denominator_is_none_not_zero(self) -> None:
        from SSEA.sse_protocols import StructureStore
        from experiments._harness import run_episode

        r = run_episode(0, frames=1, store=StructureStore(), slow_loop=lambda t: None)
        if r.run_success_frames + r.run_failed_frames == 0:
            assert r.run_action_success_rate is None

    def test_rate_is_the_ratio_when_defined(self) -> None:
        from experiments.exp3_skill_consolidation import fresh_store
        from experiments._harness import run_episode

        # seed 3 是实测的「动作全失败」标本：RUN 帧不少，成功 0。
        r = run_episode(3, frames=200, store=fresh_store(), slow_loop=lambda t: None)
        assert r.run_success_frames == 0
        assert r.run_failed_frames > 0
        assert r.run_action_success_rate == 0.0


class TestBudgetMatchedArm:
    """预算匹配臂必须**真的切断发布**，而不是看起来像切断了。

    第一版实现只把慢环绑到**另一个 store**（弃置场）上就交了差，实测它**什么都没
    改变**——``FastLoop._step_wake`` 认的是慢环的**返回值**，不是 store。那一版跑出了
    与处理臂**逐位相同**的 33 次调用与同一个能量值，看上去像一条重大发现
    （「结构没进快环也照样被调用」），实际是**这一臂根本没被改动**。

    本类是那条教训的守卫：**预算匹配钩子必须恒返回 None**。
    """

    def _real_trace(self):
        """跑一小段，把慢环实际收到的那条 trace 抓出来。"""

        from experiments._harness import build_slow_loop, run_episode
        from experiments.exp3_skill_consolidation import fresh_store

        store = fresh_store()
        captured: dict = {}
        inner = build_slow_loop(store, plasticity=False)

        def hook(trace):
            captured["trace"] = tuple(trace)
            return inner(trace)

        run_episode(0, frames=200, store=store, slow_loop=hook)
        assert captured.get("trace"), "这一跑没触发慢环，夹具失效"
        return store, captured["trace"]

    def test_budget_matched_hook_always_returns_none(self) -> None:
        """**本类的全部理由。** 返回非 None 就等于发布，臂会静默退化成处理臂。"""

        from SSEA.sse_protocols import StructureStore
        from experiments._harness import build_budget_matched_slow_loop

        _store, trace = self._real_trace()
        hook = build_budget_matched_slow_loop(
            throwaway=StructureStore(), plasticity=False
        )
        assert hook(trace) is None

    def test_publishing_hook_returns_a_context_on_the_same_trace(self) -> None:
        """对照组：同一个 trace、同一个钩子形状，**发布版**必须给出非 None。

        没有这一条，上面的断言可能只是因为这份夹具根本产生不出可供提交的东西。
        """

        from SSEA.sse_protocols import StructureStore
        from experiments._harness import build_slow_loop

        # 用**空**store：`_real_trace()` 跑过的那一份已经把它编译出的技能收进去了，
        # 对同一条 trace 再来一次会被 `new_skills()` 去重掉 → 不提交 → 返回 None。
        # 那是去重的正确行为，不是发布通道失效。
        _store, trace = self._real_trace()
        assert build_slow_loop(StructureStore(), plasticity=False)(trace) is not None

    def test_memory_budget_matched_keeps_the_instrument(self) -> None:
        """记忆侧的预算匹配臂**仍然有仪器**——它确实跑了记忆系统。

        把 ``stats`` 抹成空字典会让人把它读成「记忆关臂」，而两者要问的是
        完全不同的问题（见 ``BudgetMatchedRetriever.stats`` 的 docstring）。"""

        from experiments.exp3_skill_consolidation import fresh_store
        from experiments._harness import run_episode

        store = fresh_store()
        r = run_episode(0, frames=40, store=store, slow_loop=lambda t: None,
                        memory_budget_matched=True)
        assert r.memory_instrumented is True

