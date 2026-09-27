"""FastLoop 测试 —— 闭环可运行 + 状态机 + 注入面（07 §11 / 08 §4.1）。"""

from __future__ import annotations

import pytest
import torch

from SSEA.environment import Environment, EnvironmentConfig
from SSEA.fast_loop import (
    STATE_DEAD,
    STATE_RUN,
    STATE_SLEEP,
    STATE_WAKE,
    STATES,
    FastLoop,
    FastLoopConfig,
    StepRecord,
    ZeroMemoryRetriever,
)
from SSEA.memory_system import MemorySystem
from SSEA.metabolic_monitor import MetabolicMonitor
from SSEA.sse_protocols import (
    Action,
    Locomotion,
    Manipulation,
    Skill,
    idle_action,
)
from SSEA.environment import _unit
from tests.conftest import make_context


def sleepy_monitor() -> MetabolicMonitor:
    """阈值放宽到必然入睡——用来测状态机，不是用来测生存策略。"""

    return MetabolicMonitor(
        sleep_threat_threshold=1.1,
        sleep_fatigue_threshold=0.0,
    )


def never_sleep_monitor() -> MetabolicMonitor:
    """疲劳阈值取 2.0（疲劳上限是 1.0），故恒不入睡。"""

    return MetabolicMonitor(
        sleep_threat_threshold=0.0,
        sleep_fatigue_threshold=2.0,
    )


class TestClosedLoopRuns:
    """07 §11 的验收标准：Observation → perception_vector →
    hidden_state → Action 闭环可运行。"""

    def test_one_frame_produces_a_record(self, loop: FastLoop) -> None:
        record = loop.step()
        assert isinstance(record, StepRecord)
        assert record.state == STATE_RUN

    def test_observation_feeds_perception(self, loop: FastLoop) -> None:
        """感知编码器必须真的看到观测——换成空观测后输出应不同。"""

        obs = loop.observation
        p = loop.perception(obs)
        empty = type(obs)(
            time=0.0,
            body=obs.body,
            environment=obs.environment,
            objects=(),
            events=(),
            social_signals=(),
        )
        assert not torch.allclose(p, loop.perception(empty))

    def test_hidden_state_is_carried_across_frames(self, loop: FastLoop) -> None:
        loop.step()
        first = loop.hidden.clone()
        loop.step()
        assert loop.hidden.shape == first.shape
        assert not torch.allclose(loop.hidden, first)

    def test_action_is_decoded_every_frame(self, loop: FastLoop) -> None:
        for _ in range(5):
            record = loop.step()
            if record.state != STATE_RUN:
                continue
            assert record.decoded_action.is_executable()
            assert record.executed_action.is_executable()

    def test_intent_vector_is_recorded(self, loop: FastLoop) -> None:
        record = loop.step()
        assert record.intent is not None
        assert record.intent.numel() == loop.decoder.config.intent_dim

    def test_energy_decreases(self, loop: FastLoop) -> None:
        before = loop.observation.body.energy
        loop.run(10)
        assert loop.observation.body.energy < before

    def test_many_frames_run_without_crashing(self) -> None:
        env = Environment(seed=11)
        loop = FastLoop(env, make_context(), config=FastLoopConfig(max_frames=120))
        records = loop.run()
        assert len(records) > 0
        assert all(r.observation is not None for r in records)

    def test_loop_terminates_on_death(self) -> None:
        """淘汰是终态——run() 必须自己停下，不能一直跑。"""

        env = Environment(EnvironmentConfig(base_drain=1.0), seed=1)
        loop = FastLoop(env, make_context())
        records = loop.run(50)
        assert loop.state == STATE_DEAD
        assert records[-1].state == STATE_DEAD

    def test_step_after_death_raises(self) -> None:
        env = Environment(EnvironmentConfig(base_drain=1.0), seed=1)
        loop = FastLoop(env, make_context())
        loop.run(5)
        assert loop.state == STATE_DEAD
        with pytest.raises(RuntimeError, match="淘汰不可撤销"):
            loop.step()


class TestPredictionErrorProducer:
    """08 §2.6.1：prediction_error 的生产者是 SurpriseEstimator，不是环境。"""

    def test_feedback_carries_prediction_error(self, loop: FastLoop) -> None:
        loop.run(10)
        errors = [
            r.feedback.prediction_error for r in loop.trace() if r.state == STATE_RUN
        ]
        assert any(e > 0.0 for e in errors)

    def test_environment_does_not_produce_it(self, env: Environment) -> None:
        """环境只是入口，默认 0.0——不填就没有。"""

        _, fb = env.step(Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0)))
        assert fb.prediction_error == 0.0

    def test_error_is_non_negative(self, loop: FastLoop) -> None:
        loop.run(20)
        for record in loop.trace():
            assert record.feedback.prediction_error >= 0.0


class TestSleepStateMachine:
    """08 §2.2：睡眠期是一等公民状态，入口窄，出口明确。"""

    def test_states_are_the_documented_four(self) -> None:
        assert set(STATES) == {STATE_RUN, STATE_SLEEP, STATE_WAKE, STATE_DEAD}

    def test_enters_sleep_when_monitor_says_so(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        loop.step()
        assert loop.state == STATE_SLEEP

    def test_sleep_frames_call_rest_not_step(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        loop.step()
        before = env.fatigue
        record = loop.step()
        assert record.state == STATE_SLEEP
        assert env.fatigue < before

    def test_sleep_recovers_fatigue_over_the_phase(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        loop.step()
        fatigues = []
        for _ in range(3):
            record = loop.step()
            fatigues.append(record.observation.body.fatigue)
        assert fatigues == sorted(fatigues, reverse=True)

    def test_wake_follows_sleep_and_returns_to_run(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        states = [loop.step().state for _ in range(6)]
        assert STATE_SLEEP in states
        assert STATE_WAKE in states
        assert states[-1] == STATE_RUN

    def test_sleep_phase_has_exactly_min_frames(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=2),
        )
        states = [loop.step().state for _ in range(5)]
        assert states.count(STATE_SLEEP) == 2

    def test_no_sleep_when_monitor_refuses(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=never_sleep_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        states = [loop.step().state for _ in range(10)]
        assert STATE_SLEEP not in states
        assert STATE_WAKE not in states

    def test_sleep_frames_do_not_advance_the_action_path(self) -> None:
        """睡眠帧没有 intent，也没有真动作——慢环整理的不是"动作"。"""

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
        )
        loop.step()
        record = loop.step()
        assert record.state == STATE_SLEEP
        assert record.intent is None
        assert record.executed_action == idle_action()


class TestInjectionSurface:
    """08 §2.1：慢环只发布新版本，快环只读当前版本。"""

    def test_slow_loop_hook_receives_the_trace(self) -> None:
        seen: list[tuple[StepRecord, ...]] = []

        def hook(trace: tuple[StepRecord, ...]):
            seen.append(trace)
            return None

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=2),
            slow_loop=hook,
        )
        loop.run(8)
        assert seen, "慢环钩子从未被调用"
        assert all(isinstance(r, StepRecord) for r in seen[0])

    def test_new_context_is_applied_on_wake(self) -> None:
        fresh = make_context(s1=None) if False else make_context()

        def hook(trace: tuple[StepRecord, ...]):
            return fresh

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=2),
            slow_loop=hook,
        )
        old = loop.context
        loop.run(8)
        assert loop.context is fresh
        assert loop.context is not old

    def test_returning_none_keeps_the_old_context(self) -> None:
        """Gate 不通过 → 版本号不切换 → 快照不变。
        不存在"回滚"，因为从未应用。"""

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=2),
            slow_loop=lambda trace: None,
        )
        old = loop.context
        loop.run(8)
        assert loop.context is old

    def test_fingerprint_is_recorded_per_frame(self) -> None:
        env = Environment(seed=3)
        loop = FastLoop(env, make_context())
        loop.run(5)
        for record in loop.trace():
            assert record.context_fingerprint == loop.context.fingerprint()

    def test_fast_loop_survives_an_injected_context(self) -> None:
        """换快照不能把快环搞坏——Skill Runner 要跟着重建。"""

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=50, min_sleep_frames=2),
            slow_loop=lambda trace: make_context(),
        )
        records = loop.run(12)
        assert any(r.state == STATE_WAKE for r in records)
        assert loop.state in (STATE_RUN, STATE_SLEEP, STATE_WAKE)


class TestDeathSnapshot:
    """08 §2.2：DEATH_SNAPSHOT 触发器。"""

    def test_on_death_hook_fires(self) -> None:
        seen: list[int] = []

        env = Environment(EnvironmentConfig(base_drain=1.0), seed=1)
        loop = FastLoop(
            env,
            make_context(),
            on_death=lambda trace, obs: seen.append(len(trace)),
        )
        loop.run(10)
        assert seen, "死亡钩子从未触发"
        assert seen[0] >= 1

    def test_terminal_record_is_marked_dead(self) -> None:
        env = Environment(EnvironmentConfig(base_drain=1.0), seed=1)
        loop = FastLoop(env, make_context())
        records = loop.run(10)
        assert records[-1].state == STATE_DEAD
        assert records[-1].feedback.survived is False

    def test_death_hook_receives_final_observation(self) -> None:
        energies: list[float] = []

        env = Environment(EnvironmentConfig(base_drain=1.0), seed=1)
        loop = FastLoop(
            env,
            make_context(),
            on_death=lambda trace, obs: energies.append(obs.body.energy),
        )
        loop.run(10)
        assert energies == [pytest.approx(0.0)]


class TestTrace:
    def test_trace_is_grow_only(self, loop: FastLoop) -> None:
        loop.step()
        first = loop.trace()
        loop.step()
        second = loop.trace()
        assert len(second) == len(first) + 1
        assert second[: len(first)] == first

    def test_frame_numbers_are_sequential(self, loop: FastLoop) -> None:
        loop.run(6)
        frames = [r.frame for r in loop.trace()]
        assert frames == sorted(frames)
        assert len(set(frames)) == len(frames)

    def test_records_carry_both_actions(self, loop: FastLoop) -> None:
        loop.run(4)
        for record in loop.trace():
            assert record.decoded_action is not None
            assert record.executed_action is not None

    def test_same_action_when_no_skill_running(self, loop: FastLoop) -> None:
        """没有技能时，执行的动作就是解码出来的那个。"""

        loop.run(4)
        for record in loop.trace():
            if record.state != STATE_RUN:
                continue
            if record.skill_event is not None:
                continue
            assert record.executed_action is record.decoded_action


class TestSkillIntegration:
    """Skill Runner 插在 Action Decoder 与 Environment 之间。"""

    def test_skill_in_context_can_be_called(self) -> None:
        """技能被调用时，送进环境的是子动作，不是解码器的原产物。

        刻意把 skill 门控的 bias 推成正数：随机初始化的门控是否打开是
        一枚硬币（实测 12 个 seed 里 6 个 60 帧内从不打开），拿它当
        断言等于断言一次抽奖。这里要钉住的是**接线**，不是运气。
        """

        skill = Skill(
            skill_id="s1",
            name="试探技能",
            precondition={},
            action_sequence=(
                Action(locomotion=Locomotion((1.0, 0.0), 0.2, 1.0)),
                Action(locomotion=Locomotion((1.0, 0.0), 0.2, 1.0)),
            ),
            expected_outcome={},
            success_count=0,
            failure_count=0,
            energy_cost=0.0,
            created_from="test",
            last_used=0.0,
        )
        env = Environment(seed=5)
        loop = FastLoop(
            env,
            make_context(s1=skill),
            config=FastLoopConfig(max_frames=60, min_sleep_frames=3),
        )
        with torch.no_grad():
            loop.decoder.gates["skill"].bias.fill_(20.0)

        records = loop.run(10)
        called = [r for r in records if r.decoded_action.calls_skill()]
        assert called, "skill 门控被强制打开却仍未调用——接线断了"
        assert any(
            r.executed_action is not r.decoded_action for r in called
        ), "技能从未被展开过——Skill Runner 没插在解码器与环境之间"

    def test_skill_sub_action_reaches_the_environment(self) -> None:
        """子动作的环境后果必须真的发生——不只是对象被换掉。"""

        skill = Skill(
            skill_id="s1",
            name="移动技能",
            precondition={},
            action_sequence=(
                Action(locomotion=Locomotion((1.0, 0.0), 1.0, 1.0)),
            )
            * 4,
            expected_outcome={},
            success_count=0,
            failure_count=0,
            energy_cost=0.0,
            created_from="test",
            last_used=0.0,
        )
        env = Environment(seed=5)
        loop = FastLoop(
            env,
            make_context(s1=skill),
            config=FastLoopConfig(max_frames=60, min_sleep_frames=3),
        )
        with torch.no_grad():
            loop.decoder.gates["skill"].bias.fill_(20.0)
        start = list(env.position)
        loop.run(4)
        assert env.position != start
        assert loop.skill_runner.stats_for("s1").success_count >= 1

    def test_skill_ids_are_candidates(self) -> None:
        env = Environment(seed=5)
        loop = FastLoop(env, make_context())
        candidates = loop._candidates(loop.observation)
        assert candidates.skill_ids == tuple(loop.context.skills.keys())

    def test_object_ids_come_from_the_observation(self) -> None:
        env = Environment(seed=5)
        loop = FastLoop(env, make_context())
        candidates = loop._candidates(loop.observation)
        assert candidates.object_ids == tuple(
            o.object_id for o in loop.observation.objects
        )


class TestZeroMemory:
    """ZeroMemoryRetriever 现在是**消融对照组**，不是默认值。

    Milestone 2 时它是默认——那时记忆系统未实现，m_t 必须是诚实的空。
    Milestone 3 起默认换成 MemorySystem，本类守住的是另一半：
    "把记忆关掉"这条对照路径必须还能走，否则"记忆贡献了多少"无法消融。
    """

    def test_returns_zeros_of_declared_dim(self) -> None:
        r = ZeroMemoryRetriever(dim=8)
        out = r.retrieve(torch.zeros(4))
        assert out.shape == (8,)
        assert float(out.abs().sum()) == 0.0

    def test_does_not_depend_on_inputs(self) -> None:
        r = ZeroMemoryRetriever(dim=4)
        a = r.retrieve(torch.ones(4))
        b = r.retrieve(torch.full((4,), -9.0))
        assert torch.allclose(a, b)

    def test_now_is_accepted_and_ignored(self) -> None:
        """签名与 MemorySystem 对齐（Protocol 要求），但零检索器没有时间概念。"""

        r = ZeroMemoryRetriever(dim=4)
        assert torch.allclose(r.retrieve(torch.ones(4), now=1.0), r.retrieve(torch.ones(4)))

    def test_use_context_is_a_no_op(self) -> None:
        """Protocol 的第二个方法。无状态实现必须留空操作而不是没有这个方法。"""

        r = ZeroMemoryRetriever(dim=4)
        assert r.use_context(make_context()) is None

    def test_loop_runs_with_memory_disabled(self) -> None:
        """对照组要能真的跑完一个 episode——否则它不是可用的对照。"""

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            memory_retriever=ZeroMemoryRetriever(16),
            config=FastLoopConfig(max_frames=30, min_sleep_frames=3),
        )
        records = loop.run()
        assert records
        assert not isinstance(loop.memory, MemorySystem)


class TestMemoryIntegration:
    """Milestone 3：m_t 现在是真实记忆的产物，不再是零。"""

    def test_default_memory_is_a_real_system(self, loop: FastLoop) -> None:
        assert isinstance(loop.memory, MemorySystem)

    def test_retrieval_is_attempted_every_run_frame(self, loop: FastLoop) -> None:
        loop.run(10)
        run_frames = sum(1 for r in loop.trace() if r.state == STATE_RUN)
        assert loop.memory.stats.frames == run_frames

    def test_empty_memory_gives_zeros(self, loop: FastLoop) -> None:
        """没有记忆时 m_t 必须与 ZeroMemoryRetriever 不可区分——
        这是"诚实的空"在真实实现上的对应物。

        先把记忆门控按死：随机初始化的门控是否打开是一枚硬币，
        拿它当断言等于断言一次抽奖。这里要钉住的是空库的输出，不是运气。
        """

        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(-20.0)
            loop.decoder.mem_store.bias.fill_(-20.0)
        loop.run(5)
        assert len(loop.memory) == 0
        assert loop.memory.stats.writes == 0
        assert loop.memory.stats.misses == loop.memory.stats.retrievals

    def test_write_reaches_the_memory_system(self) -> None:
        """强制打开记忆通道门控与 store 门控后必须有东西落库。"""

        env = Environment(EnvironmentConfig(base_drain=0.005), seed=4)
        loop = FastLoop(env, make_context(), config=FastLoopConfig(max_frames=30))
        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(20.0)
            loop.decoder.mem_store.bias.fill_(20.0)
        loop.run()
        assert loop.memory.stats.writes > 0
        assert len(loop.memory) > 0

    def test_written_memory_is_retrievable_later(self) -> None:
        """写入的那条要在下一个相似情境里被检索到——否则写入没有意义。"""

        env = Environment(EnvironmentConfig(base_drain=0.005), seed=4)
        loop = FastLoop(env, make_context(), config=FastLoopConfig(max_frames=30))
        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(20.0)
            loop.decoder.mem_store.bias.fill_(20.0)
        loop.run()
        assert loop.memory.stats.hits > 0

    def test_hit_is_visible_in_the_event_stream(self) -> None:
        """MEMORY_RETRIEVED 必须有生产者——EVENT_TYPES 里不留空头类型。"""

        env = Environment(EnvironmentConfig(base_drain=0.005), seed=4)
        loop = FastLoop(env, make_context(), config=FastLoopConfig(max_frames=30))
        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(20.0)
            loop.decoder.mem_store.bias.fill_(20.0)
        loop.run()
        types = [e.event_type for e in loop.environment.event_log()]
        assert "MEMORY_RETRIEVED" in types
        assert "MEMORY_STORED" in types

    def test_memory_survives_a_structure_version_switch(self) -> None:
        """记忆不在快照里——换版本不能把它重置（C3 三分离）。"""

        env = Environment(seed=3)
        loop = FastLoop(
            env,
            make_context(),
            metabolic_monitor=sleepy_monitor(),
            config=FastLoopConfig(max_frames=40, min_sleep_frames=2),
            slow_loop=lambda trace: make_context(),
        )
        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(20.0)
            loop.decoder.mem_store.bias.fill_(20.0)
        loop.run()
        assert any(r.state == STATE_WAKE for r in loop.trace())
        assert len(loop.memory) > 0, "换版把记忆清空了——记忆被放进了快照"

    def test_policy_comes_from_the_snapshot(self) -> None:
        """retrieval 是五类注入物之一：策略由快照给，不由代码写死。"""

        ctx = make_context(retrieval={"top_k": 2, "stride": 3})
        env = Environment(seed=3)
        loop = FastLoop(env, ctx)
        assert loop.memory.policy["top_k"] == 2
        assert loop.memory.policy["stride"] == 3
        # 未给的键仍取默认值——策略是逐键覆盖，不是整体替换。
        assert loop.memory.policy["min_similarity"] == 0.1

    def test_memory_dim_matches_state_core(self, loop: FastLoop) -> None:
        """m_t 的维度必须与 StateCore 的 memory 输入段一致。"""

        loop.run(5)
        assert loop.memory.config.memory_dim == loop.state_core.config.memory_dim
        assert loop.memory.stats.frames >= 0

    def test_bad_policy_fails_loudly(self) -> None:
        """策略写错必须立刻炸，不能静默关掉一个机制。"""

        with pytest.raises(ValueError, match="整除"):
            FastLoop(Environment(seed=3), make_context(retrieval={"top_k": 3}))

    def test_unknown_policy_key_fails_loudly(self) -> None:
        with pytest.raises(ValueError, match="未知键"):
            FastLoop(
                Environment(seed=3), make_context(retrieval={"top_k": 4, "topK": 2})
            )

    def test_retrieval_event_and_stored_event_can_disagree(self) -> None:
        """环境记的 MEMORY_STORED 是"请求已发出"，不是"已入库"。

        策略关掉写入时环境照样记事件（通道被走过），而 memory.stats.writes
        不动。两个计数各说各话是有意的——与 M2 的 action_success /
        ACTION_FAILED 同构：一个是世界的观察，一个是模型的账。
        """

        ctx = make_context(retrieval={"writable": False})
        env = Environment(EnvironmentConfig(base_drain=0.005), seed=4)
        loop = FastLoop(env, ctx, config=FastLoopConfig(max_frames=30))
        with torch.no_grad():
            loop.decoder.gates["memory"].bias.fill_(20.0)
            loop.decoder.mem_store.bias.fill_(20.0)
        loop.run()
        assert loop.memory.stats.refused > 0
        assert loop.memory.stats.writes == 0
        assert len(loop.memory) == 0
        types = [e.event_type for e in env.event_log()]
        assert "MEMORY_STORED" in types


class TestSurvivability:
    """闭环"能跑"不等于"能活"——但必须证明活下来是可能的，
    否则 Milestone 4 的学习没有可学的东西。"""

    def test_greedy_policy_survives(self) -> None:
        """手写贪心策略：朝最近资源走，够近就抓。
        它必须活得比随机解码器久——这是对世界可生存性的下界证明。"""

        cfg = EnvironmentConfig(base_drain=0.005, move_cost_factor=0.01)
        env = Environment(cfg, seed=4)
        env.reset()
        for _ in range(60):
            if not env.alive:
                break
            pairs = env.visible_objects()
            resources = [(o, d) for o, d in pairs if o.resource_value > 0]
            if resources:
                target, dist = min(resources, key=lambda pair: pair[1])
                if dist <= env.config.reach:
                    action = Action(
                        manipulation=Manipulation(
                            target.object_id, "grasp", 0.5, 1.0
                        )
                    )
                else:
                    delta = [
                        target.position[i] - env.position[i] for i in range(2)
                    ]
                    action = Action(locomotion=Locomotion(_unit(delta), 1.0, 1.0))
            else:
                action = Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0))
            obs, fb = env.step(action)
        assert env.alive, "贪心策略也活不下来——世界的代谢与资源不成比例"
        assert env.energy > 0.0
