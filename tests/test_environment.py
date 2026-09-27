"""Environment 测试 —— 约束第二执行点 + 淘汰函数归属（08 §2.6.2 / §3.6）。"""

from __future__ import annotations

import pytest

from SSEA.environment import (
    ENV_OPERATIONS,
    KIND_HAZARD,
    KIND_RESOURCE,
    Environment,
    EnvironmentConfig,
)
from SSEA.sse_protocols import (
    Action,
    BodyState,
    EventVector,
    Feedback,
    Locomotion,
    Manipulation,
    Observation,
    default_constraints,
)


def move(direction: tuple[float, float] = (1.0, 0.0), speed: float = 0.5) -> Action:
    return Action(
        locomotion=Locomotion(direction=direction, speed=speed, duration=1.0)
    )


def grasp(target_id: str) -> Action:
    return Action(
        manipulation=Manipulation(
            target_id=target_id, operation="grasp", force=0.5, duration=1.0
        )
    )


class TestStepContract:
    def test_returns_observation_and_feedback(self, env: Environment) -> None:
        obs, fb = env.step(move())
        assert isinstance(obs, Observation)
        assert isinstance(fb, Feedback)

    def test_time_advances(self, env: Environment) -> None:
        env.step(move())
        obs, _ = env.step(move())
        assert obs.time == 2.0

    def test_body_state_is_well_formed(self, env: Environment) -> None:
        obs, _ = env.step(move())
        body = obs.body
        assert isinstance(body, BodyState)
        assert body.energy >= 0.0
        assert 0.0 <= body.fatigue <= 1.0
        assert body.action_constraints is not None

    def test_energy_drops_even_when_idle(self, env: Environment) -> None:
        """不动也耗能——生存压力不能靠原地不动逃避。"""

        obs, fb = env.step(Action(locomotion=Locomotion((0.0, 0.0), 0.0, 0.0)))
        assert fb.energy_change < 0.0
        assert obs.body.energy < 1.0

    def test_moving_costs_more_than_idling(self, env: Environment) -> None:
        idle_env = Environment(seed=3)
        idle_env.step(Action(locomotion=Locomotion((0.0, 0.0), 0.0, 0.0)))
        env.step(move(speed=1.0))
        assert env.energy < idle_env.energy

    def test_reset_restores_initial_state(self, env: Environment) -> None:
        for _ in range(5):
            env.step(move(speed=1.0))
        obs = env.reset()
        assert obs.time == 0.0
        assert obs.body.energy == pytest.approx(1.0)
        assert obs.body.fatigue == pytest.approx(0.0)
        assert env.alive


class TestSecondEnforcementPoint:
    """08 §2.6.2：Environment 是约束的第二执行点，兜住漏网的。"""

    def test_overspeed_is_rejected_not_crashed(self, env: Environment) -> None:
        _, fb = env.step(move(speed=99.0))
        assert fb.action_success is False
        assert "constraint_rejected" in fb.notes
        assert env.alive  # 非法动作不是死亡

    def test_rejected_action_emits_action_failed(self, env: Environment) -> None:
        env.step(move(speed=99.0))
        types = [e.event_type for e in env.event_log()]
        assert "ACTION_FAILED" in types

    def test_rejected_action_still_costs_basal_energy(
        self, env: Environment
    ) -> None:
        _, fb = env.step(move(speed=99.0))
        assert fb.energy_change < 0.0

    def test_rejected_action_does_not_move(self, env: Environment) -> None:
        before = list(env.position)
        env.step(move(speed=99.0))
        assert env.position == before

    def test_empty_action_is_rejected(self, env: Environment) -> None:
        """六个通道全空 = 协议违背，不是"安全的默认值"。

        协议层不拦它（六个字段都可选），拦它的是 ``is_executable()``。
        两个门都在协议里，这里验的是环境这个第二执行点会去看它。
        """

        empty = Action()
        assert not empty.is_executable()
        _, fb = env.step(empty)
        assert fb.action_success is False
        assert "不可执行" in fb.notes

    def test_forbidden_target_is_rejected(self, env: Environment) -> None:
        cfg = EnvironmentConfig(forbidden_targets=("res_0",))
        env2 = Environment(cfg, seed=1)
        _, fb = env2.step(grasp("res_0"))
        assert fb.action_success is False
        assert "forbidden_targets" in fb.notes

    def test_many_random_illegal_actions_never_crash(self, env: Environment) -> None:
        """防御性复核的意义：任何输入都不该让 episode 崩掉。"""

        illegal = [
            move(speed=1e9),
            move(speed=-1.0),
            grasp("nonexistent_object"),
            Action(locomotion=Locomotion((0.0, 0.0), 1.0, 1e9)),
        ]
        for action in illegal:
            try:
                obs, fb = env.step(action)
            except RuntimeError:
                pytest.fail(f"环境因动作崩溃: {action}")
            assert isinstance(obs, Observation)
            assert isinstance(fb, Feedback)


class TestEliminationFunction:
    """08 §3.6：死亡判定权归环境。模型物理上碰不到它。"""

    def test_energy_zero_means_death(self) -> None:
        cfg = EnvironmentConfig(base_drain=1.0)
        env = Environment(cfg, seed=1)
        _, fb = env.step(move(speed=0.0))
        assert fb.survived is False
        assert env.alive is False

    def test_damage_max_means_death(self) -> None:
        cfg = EnvironmentConfig(hazard_damage_rate=10.0, contact_radius=100.0)
        env = Environment(cfg, seed=1)
        # 把 agent 放到一个危险源旁边
        for obj in env.objects:
            if obj.kind == KIND_HAZARD:
                obj.position = list(env.position)
                break
        _, fb = env.step(move(speed=0.0))
        assert fb.survived is False

    def test_death_is_terminal(self) -> None:
        cfg = EnvironmentConfig(base_drain=1.0)
        env = Environment(cfg, seed=1)
        env.step(move(speed=0.0))
        assert not env.alive
        with pytest.raises(RuntimeError, match="淘汰是终态"):
            env.step(move())

    def test_death_survives_reset(self) -> None:
        """reset 是唯一出路——淘汰不可撤销，只能开新 episode。"""

        cfg = EnvironmentConfig(base_drain=1.0)
        env = Environment(cfg, seed=1)
        env.step(move(speed=0.0))
        obs = env.reset()
        assert env.alive
        assert obs.body.energy == pytest.approx(1.0)

    def test_model_side_cannot_modify_the_threshold(self) -> None:
        """淘汰阈值是配置，不在任何 Action 可达的路径上。"""

        env = Environment(seed=1)
        # 遍历全部动作通道，没有任何一个能改 max_damage
        env.step(
            Action(
                locomotion=Locomotion((1.0, 0.0), 0.1, 1.0),
                manipulation=Manipulation("res_0", "none", 0.0, 1.0),
            )
        )
        assert env.config.max_damage == 1.0


class TestResources:
    def test_resources_exist_in_the_world(self, env: Environment) -> None:
        resources = [o for o in env.objects if o.kind == KIND_RESOURCE]
        assert len(resources) == env.config.n_resources

    def test_some_resources_are_visible_at_start(self, env: Environment) -> None:
        """开局不能全盲，否则前几帧无候选可挑。"""

        obs = env.reset()
        assert any(o.resource_value > 0 for o in obs.objects)

    def test_grasping_a_resource_gains_energy(self, env: Environment) -> None:
        """先耗掉一些能量——能量上限 1.0 让"满血时抓资源"变成浪费，
        这正是环境强加的策略压力，不是数值意外。"""

        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        env.position = list(target.position)
        for _ in range(20):
            env.step(move(speed=0.0))
        before = env.energy
        _, fb = env.step(grasp(target.object_id))
        assert fb.energy_change > 0.0
        assert env.energy > before

    def test_energy_is_capped_at_one(self, env: Environment) -> None:
        """满血时抓资源，收益被 1.0 的上限吃掉，只剩基础代谢的损耗。"""

        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        env.position = list(target.position)
        _, fb = env.step(grasp(target.object_id))
        assert "grasp: +" in fb.notes  # 增益确实发生了
        assert env.energy == pytest.approx(1.0 - env.config.base_drain)

    def test_grasped_resource_is_consumed(self, env: Environment) -> None:
        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        env.position = list(target.position)
        env.step(grasp(target.object_id))
        assert env._find(target.object_id) is None

    def test_out_of_reach_grasp_fails(self, env: Environment) -> None:
        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        env.position = [0.0, 0.0]
        target.position = [env.config.reach + 5.0, 0.0]
        _, fb = env.step(grasp(target.object_id))
        assert fb.action_success is False
        assert "unreachable" in fb.notes

    def test_grasping_a_prop_fails(self, env: Environment) -> None:
        prop = next(o for o in env.objects if o.kind == "prop")
        env.position = list(prop.position)
        _, fb = env.step(grasp(prop.object_id))
        assert fb.action_success is False
        assert "not graspable" in fb.notes

    def test_action_success_is_always_a_bool(self, env: Environment) -> None:
        """``Feedback.action_success`` 必须是严格的 bool。

        某个 ``_apply_*`` 漏写 return 时会返回 None——None 是 falsy 但不是
        False，会原样流进这个字段。那种类型错误不在任何地方报错，只会让
        Skill Runner 的中止判据变成"不确定"。
        """

        actions = [
            move(),
            move(speed=0.0),
            move(speed=99.0),
            grasp("nonexistent"),
            Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0)),
        ]
        for action in actions:
            _, fb = env.step(action)
            assert fb.action_success is True or fb.action_success is False

    def test_action_success_agrees_with_event_log(self, env: Environment) -> None:
        """action_success 与 ACTION_FAILED 事件必须是同一个判断。

        前者是 Skill Runner 的中止判据，后者是慢环的检索依据。若各说各话，
        一个技能会在"明明抓空了"的情况下跑完整个 action_sequence。
        """

        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        target.position = [env.config.reach + 5.0, 0.0]
        _, fb = env.step(grasp(target.object_id))
        failed = any(e.event_type == "ACTION_FAILED" for e in env.event_log())
        assert failed is (fb.action_success is False)

    def test_energy_gained_event_is_emitted(self, env: Environment) -> None:
        target = next(o for o in env.objects if o.kind == KIND_RESOURCE)
        env.position = list(target.position)
        env.step(grasp(target.object_id))
        assert any(e.event_type == "ENERGY_GAINED" for e in env.event_log())


class TestHazards:
    def test_contact_causes_damage(self) -> None:
        cfg = EnvironmentConfig(hazard_damage_rate=0.5)
        env = Environment(cfg, seed=1)
        hazard = next(o for o in env.objects if o.kind == KIND_HAZARD)
        hazard.position = list(env.position)
        _, fb = env.step(move(speed=0.0))
        assert fb.damage_change > 0.0
        assert any(e.event_type == "DAMAGE_RECEIVED" for e in env.event_log())

    def test_no_contact_no_damage(self, env: Environment) -> None:
        for obj in env.objects:
            if obj.kind == KIND_HAZARD:
                obj.position = [env.config.world_radius, env.config.world_radius]
        _, fb = env.step(move(speed=0.0))
        assert fb.damage_change == pytest.approx(0.0)

    def test_use_tool_reduces_threat(self, env: Environment) -> None:
        hazard = next(o for o in env.objects if o.kind == KIND_HAZARD)
        env.position = list(hazard.position)
        before = hazard.threat_level
        env.step(
            Action(
                manipulation=Manipulation(
                    hazard.object_id, "use_tool", force=0.5, duration=1.0
                )
            )
        )
        assert hazard.threat_level < before


class TestFatigue:
    def test_fatigue_accumulates(self, env: Environment) -> None:
        _, fb = env.step(move(speed=0.0))
        assert fb.fatigue_change > 0.0

    def test_fatigue_is_capped_at_one(self) -> None:
        cfg = EnvironmentConfig(fatigue_rate=10.0)
        env = Environment(cfg, seed=1)
        obs, _ = env.step(move(speed=0.0))
        assert obs.body.fatigue == pytest.approx(1.0)

    def test_fatigue_makes_sleep_reachable(self, env: Environment) -> None:
        """睡眠状态机要可被走到，否则 08 §2.2 的设计无法验证。"""

        cfg = EnvironmentConfig(fatigue_rate=0.05, base_drain=0.0)
        env = Environment(cfg, seed=1)
        for _ in range(15):
            obs, fb = env.step(move(speed=0.0))
            assert fb.survived
        assert obs.body.fatigue >= 0.6


class TestSleepStep:
    def test_rest_recovers_fatigue(self, env: Environment) -> None:
        for _ in range(5):
            env.step(move(speed=1.0))
        before = env.fatigue
        obs, fb = env.rest()
        assert obs.body.fatigue < before
        assert fb.fatigue_change < 0.0

    def test_rest_does_not_drain_energy(self, env: Environment) -> None:
        """"在安全时允许无损整理经验"——睡眠不耗能。"""

        before = env.energy
        obs, _ = env.rest()
        assert obs.body.energy >= before

    def test_rest_advances_time(self, env: Environment) -> None:
        obs, _ = env.rest()
        assert obs.time == 1.0

    def test_rest_emits_no_action_success(self, env: Environment) -> None:
        env.rest()
        assert not any(e.event_type == "ACTION_SUCCESS" for e in env.event_log())


class TestObservationShape:
    def test_objects_are_relative_not_absolute(self, env: Environment) -> None:
        obs = env.step(move(speed=1.0))[0]
        for obj in obs.objects:
            assert obj.distance >= 0.0
            assert obj.distance <= env.config.perception_radius + 1e-6

    def test_perception_radius_is_a_hard_bound(self) -> None:
        cfg = EnvironmentConfig(perception_radius=2.0, spawn_near_radius=1.0)
        env = Environment(cfg, seed=5)
        obs = env.reset()
        assert all(o.distance <= 2.0 + 1e-6 for o in obs.objects)

    def test_object_count_varies_but_protocol_is_fixed(
        self, env: Environment
    ) -> None:
        """对象数可变，Observation 结构不变——低带宽靠稀疏列表实现。"""

        obs = env.reset()
        assert isinstance(obs.objects, tuple)
        if obs.objects:
            assert all(isinstance(o, type(obs.objects[0])) for o in obs.objects)

    def test_empty_observation_is_still_valid(self) -> None:
        """视野内空集是合法观测，不是异常。"""

        cfg = EnvironmentConfig(
            perception_radius=0.01,
            reach=0.001,
            spawn_near_radius=0.0005,
            n_resources=0,
        )
        env = Environment(cfg, seed=1)
        obs = env.reset()
        assert obs.objects == ()
        assert obs.environment.danger_level == 0.0

    def test_environment_summary_is_well_formed(self, env: Environment) -> None:
        obs, _ = env.step(move())
        assert 0.0 <= obs.environment.danger_level <= 1.0
        assert obs.environment.time_phase in ("dawn", "day", "dusk", "night")

    def test_time_phase_cycles(self) -> None:
        # 关掉代谢，否则 100 帧后已淘汰，走不到相位循环的尽头。
        cfg = EnvironmentConfig(base_drain=0.0, fatigue_rate=0.0)
        env = Environment(cfg, seed=1)
        phases = set()
        for _ in range(120):
            obs, _ = env.step(move(speed=0.0))
            phases.add(obs.environment.time_phase)
        assert phases == {"dawn", "day", "dusk", "night"}

    def test_no_natural_language_in_observation(self, env: Environment) -> None:
        """C2：自然语言只作观察员接口，不进控制闭环。"""

        obs, fb = env.step(move())
        for field_value in (
            obs.environment.time_phase,
            fb.notes,
        ):
            assert isinstance(field_value, str)
        # 事件类型是协议枚举，不是自由文本
        for event in env.event_log():
            assert event.event_type in {
                "OBJECT_FOUND",
                "OBJECT_LOST",
                "ENERGY_GAINED",
                "ENERGY_LOST",
                "DAMAGE_RECEIVED",
                "ACTION_FAILED",
                "ACTION_SUCCESS",
                "SKILL_SUCCESS",
                "SKILL_FAILURE",
                "MEMORY_STORED",
                "MEMORY_RETRIEVED",
                "SELF_MOD_PROPOSED",
                "SELF_MOD_APPLIED",
                "SELF_MOD_ROLLBACK",
            }


class TestDeterminism:
    def test_same_seed_same_world(self) -> None:
        a = Environment(seed=42)
        b = Environment(seed=42)
        assert [o.object_id for o in a.objects] == [o.object_id for o in b.objects]
        assert [o.position for o in a.objects] == [o.position for o in b.objects]

    def test_different_seed_different_world(self) -> None:
        a = Environment(seed=1)
        b = Environment(seed=2)
        assert [o.position for o in a.objects] != [o.position for o in b.objects]

    def test_same_seed_same_trajectory(self) -> None:
        """确定性必须落在**与世界交互过的**轨迹上。

        只测纯移动的话，能量只取决于走过的距离，与 seed 无关——
        那样的断言恒真，守不住任何东西。
        """

        def run(seed: int) -> tuple[float, float, int]:
            env = Environment(seed=seed)
            for _ in range(10):
                # 朝最近可见资源走，够近就抓
                pairs = env.visible_objects()
                resources = [(o, d) for o, d in pairs if o.kind == KIND_RESOURCE]
                if resources:
                    target, _ = min(resources, key=lambda pair: pair[1])
                    env.position = list(target.position)
                    env.step(grasp(target.object_id))
                else:
                    env.step(move(speed=0.5))
            return (env.energy, env.position[0], len(env.objects))

        assert run(9) == run(9)
        assert run(9) != run(10)


class TestConfigValidation:
    def test_positive_geometry_required(self) -> None:
        with pytest.raises(ValueError):
            EnvironmentConfig(world_radius=0)
        with pytest.raises(ValueError):
            EnvironmentConfig(perception_radius=-1)
        with pytest.raises(ValueError):
            EnvironmentConfig(max_damage=0)

    def test_reach_cannot_exceed_perception(self) -> None:
        """可达但不可见的目标会让 Action Decoder 无从选择。"""

        with pytest.raises(ValueError, match="reach"):
            EnvironmentConfig(reach=10.0, perception_radius=1.0)


class TestChannels:
    def test_memory_write_is_recorded(self, env: Environment) -> None:
        from SSEA.sse_protocols import MemoryWrite

        action = Action(memory=MemoryWrite(store=True, content=(0.1,), importance=0.7))
        env.step(action)
        assert len(env.memory_requests) == 1
        assert any(e.event_type == "MEMORY_STORED" for e in env.event_log())

    def test_memory_write_false_is_ignored(self, env: Environment) -> None:
        from SSEA.sse_protocols import MemoryWrite

        env.step(Action(memory=MemoryWrite(store=False, content=(0.1,), importance=0.7)))
        assert env.memory_requests == []

    def test_communication_is_echoed(self, env: Environment) -> None:
        from SSEA.sse_protocols import Communication

        obs, _ = env.step(
            Action(communication=Communication(target_id="peer", signal=(0.1, 0.2)))
        )
        assert len(obs.social_signals) == 1
        assert obs.social_signals[0].signal == (0.1, 0.2)

    def test_echo_can_be_disabled(self) -> None:
        from SSEA.sse_protocols import Communication

        env = Environment(EnvironmentConfig(echo_communication=False), seed=1)
        obs, _ = env.step(
            Action(communication=Communication(target_id="peer", signal=(0.1,)))
        )
        assert obs.social_signals == ()

    def test_self_modification_is_recorded_not_applied(self) -> None:
        """环境是自我修改的观察方，不是执行方。"""

        env = Environment(EnvironmentConfig(allow_self_modify=True), seed=1)
        from SSEA.sse_protocols import SelfModification

        env.step(
            Action(
                self_modification=SelfModification(
                    proposal_type="ADD_RULE", payload={"target": "rules"}
                )
            )
        )
        assert len(env.proposals) == 1
        assert env.proposals[0].proposal_type == "ADD_RULE"
        assert any(e.event_type == "SELF_MOD_PROPOSED" for e in env.event_log())

    def test_self_modification_blocked_by_default(self, env: Environment) -> None:
        """第一阶段环境不开放这条通道——自我修改只走慢环。"""

        from SSEA.sse_protocols import SelfModification

        _, fb = env.step(
            Action(
                self_modification=SelfModification(
                    proposal_type="ADD_RULE", payload={}
                )
            )
        )
        assert fb.action_success is False
        assert "can_self_modify" in fb.notes


class TestEvents:
    def test_event_log_is_bounded(self) -> None:
        cfg = EnvironmentConfig(max_events=5)
        env = Environment(cfg, seed=1)
        for _ in range(20):
            env.step(move(speed=0.5))
        assert len(env.event_log()) <= 5

    # ---- 下面三条是债务 10 的回归钉子（12 §6）----------------------------
    #
    # 上面那条断言缓冲**是**有界的，下面这条断言计数**不是**。两条互为反面，
    # 摆在一起才读得懂：缓冲会截断是**设计**（省内存，C4），
    # 而"跑完再遍历事件流做统计"会静默算错是**后果**。
    # 曾经的实测症状：统计 ENERGY_GAINED 得到 0 次，而逐帧追踪显示第 10 帧
    # 确实 grasp 成功——错的方向偏向零，正好把有效果的实验读成没效果。

    def test_event_counts_survive_truncation(self) -> None:
        """缓冲截断，但累计计数不截断——这就是债务 10 的修法。"""

        cfg = EnvironmentConfig(max_events=5)
        env = Environment(cfg, seed=1)
        for _ in range(20):
            env.step(move(speed=0.5))
        counts = env.event_counts()
        total = sum(counts.values())
        # 缓冲被截到底，计数没有——两者必须都成立，缺一条这个测试就没意义。
        assert len(env.event_log()) <= 5
        assert total > len(env.event_log())
        assert counts["ACTION_SUCCESS"] > len(env.event_log())

    def test_event_counts_equal_event_seq(self) -> None:
        """``sum(event_counts()) == _event_seq``：不漏、不重、不漏播种。

        这一条同时挡住三种错：某个键忘了加、一个事件加了两次、
        以及 ``EVENT_TYPES`` 增了类型而计数器的键集没跟着变。
        它成立的前提是词表闭合（``EventVector`` 已经保证了这一点），
        所以它一旦不成立，说明有人绕过了那道校验。
        """

        cfg = EnvironmentConfig(max_events=5)
        env = Environment(cfg, seed=1)
        for _ in range(20):
            env.step(move(speed=0.5))
        assert sum(env.event_counts().values()) == env._event_seq

    def test_event_counts_are_keyed_by_the_closed_vocabulary(self) -> None:
        """键集恰为 ``EVENT_TYPES``，含 0 值——稀疏 dict 会混掉"0 次"与"没测"。"""

        from SSEA.sse_protocols import EVENT_TYPES

        env = Environment(seed=1)
        counts = env.event_counts()
        assert set(counts) == set(EVENT_TYPES)
        # 注意：**不是**全零。``__init__`` 末尾会 ``_diff_visibility()``，
        # 那是构造期的第一次观测，本身就会发 OBJECT_FOUND。
        # 所以"新环境计数器全零"这个直觉是错的——基线就是这条。
        assert counts["OBJECT_FOUND"] > 0
        assert counts["ACTION_SUCCESS"] == 0, "还没 step 过，不该有动作事件"

    def test_event_counts_name_the_producerless_types(self) -> None:
        """5 个类型恒为 0，因为**没有生产者**——钉住它，这是缺口不是成绩。

        见 ``Environment.event_counts()`` 的 docstring。稀疏 dict 下这 5 个
        只是"不出现"，没人会注意；全键含零之后它们是一行看得见的 0，
        于是就有了被误读成"从没发生过"的风险——所以在这里把它写成断言。

        **故意不断言"每个类型都有生产者"**：那会把套件在今天变红。
        补 ``ENERGY_LOST`` / ``SKILL_*`` 的生产者是独立的一件事。
        """

        env = Environment(seed=1)
        for _ in range(20):
            env.step(move(speed=0.5))
        counts = env.event_counts()
        for event_type in (
            "ENERGY_LOST",
            "SKILL_SUCCESS",
            "SKILL_FAILURE",
            "SELF_MOD_APPLIED",
            "SELF_MOD_ROLLBACK",
        ):
            assert counts[event_type] == 0, (
                f"{event_type} 有生产者了——请更新 event_counts() 的 docstring "
                f"与这条测试里的无生产者清单"
            )

    def test_event_counts_reset_with_the_world(self) -> None:
        """``reset()`` 把计数带回**构造期基线**——否则会跨 FastLoop 实例累积。

        ``FastLoop.__init__`` 会调 ``reset()``（见 fast_loop.py），
        一个"活过 reset"的计数器会把上一轮的计数带进下一轮，
        而且看起来完全正常。这是债务 10 同一形状的错，只是方向偏大。

        **基线不是全零**：``reset()`` 自己末尾就 ``_diff_visibility()``，
        会发 OBJECT_FOUND。所以判据是"回落到与新建时同一个基线"，
        不是"归零"——写成归零会漏掉"reset 之后仍在涨"这种半吊子修法。
        """

        baseline = sum(Environment(seed=1).event_counts().values())
        env = Environment(seed=1)
        for _ in range(20):
            env.step(move(speed=0.5))
        assert sum(env.event_counts().values()) > baseline
        env.reset()
        assert sum(env.event_counts().values()) == baseline
        # 同一个 seed 重建世界，基线事件也该一模一样。
        assert env.event_counts() == Environment(seed=1).event_counts()
        assert env._event_seq == baseline

    def test_event_counts_returns_a_copy(self) -> None:
        """返回副本——调用方改它不该动到内部状态。"""

        env = Environment(seed=1)
        env.step(move(speed=0.5))
        before = env.event_counts()
        before["ACTION_SUCCESS"] = 999
        assert env.event_counts()["ACTION_SUCCESS"] != 999

    def test_max_events_must_be_positive(self) -> None:
        """``max_events=0`` 会让 ``del lst[:-0]`` 退化成不删——缓冲静默无界。"""

        with pytest.raises(ValueError, match="max_events"):
            EnvironmentConfig(max_events=0)

    def test_events_have_fixed_context_length(self, env: Environment) -> None:
        env.step(move(speed=1.0))
        for event in env.event_log():
            assert len(event.context_vector) == 4

    def test_object_found_and_lost_are_emitted(self, env: Environment) -> None:
        env.reset()
        for _ in range(10):
            env.step(move(speed=1.0))
        types = {e.event_type for e in env.event_log()}
        assert "OBJECT_FOUND" in types

    def test_event_notes_explain_failures(self, env: Environment) -> None:
        env.step(grasp("nonexistent"))
        notes = env.event_notes()
        assert notes
        time, event_type, source, extra = notes[-1]
        assert event_type == "ACTION_FAILED"
        assert "nonexistent" in extra


class TestNoRewardSurface:
    """C9：SSEA 只有淘汰函数，没有评分函数。

    这一组守的是**环境不该长出评分接口**。写法照
    ``tests/test_verification_gate.py::test_gate_has_no_ranking_or_sorting_api``
    ——按名字扫公开面。

    **说清楚它守得住什么、守不住什么。** 它挡得住"有人给 Environment 加一个
    ``reward()`` / ``fitness()`` 访问器"，挡不住"有人拿 ``event_counts()``
    在快环里算个分数"。后者**没有物理屏障**：``FastLoop`` 手里就握着
    ``self.environment``（fast_loop.py）。淘汰函数在模型之外、模型物理上碰不到，
    但观察员面**没有**这种隔离，靠的是约定 —— 所以这几条测试是**约定的一部分**，
    不是架构保证。写成"结构上进不了控制闭环"就过头了。
    """

    def test_environment_has_no_scoring_api(self) -> None:
        public = [n for n in dir(Environment) if not n.startswith("_")]
        for bad in ("reward", "score", "fitness", "rank", "best", "compare"):
            assert bad not in public, f"Environment 出现了评分 API {bad!r}"

    def test_environment_config_has_no_scoring_knob(self) -> None:
        from dataclasses import fields

        names = {f.name for f in fields(EnvironmentConfig)}
        for bad in ("reward", "score", "fitness", "fitness_fn", "weight"):
            assert bad not in names, f"EnvironmentConfig 出现了评分旋钮 {bad!r}"

    def test_counter_is_not_in_the_perception_path(self) -> None:
        """计数器不在 ``Observation`` / ``BodyState`` 的字段里。

        **注意这条是既有事实的复述，不是新防线**：``EXPECTED_FIELDS``
        （``tests/test_protocol_consistency.py``）已经把这两个类型的字段集
        钉死了，所以本测试多挡不住任何东西。留着只是因为便宜，
        且它把"感知输入里没有累计历史"这句话放在离计数器最近的地方。
        """

        from dataclasses import fields

        for cls in (Observation, BodyState):
            names = {f.name for f in fields(cls)}
            assert "event_counts" not in names
            assert not any("count" in n for n in names), (
                f"{cls.__name__} 里出现了计数型字段——累积历史不该进感知输入"
            )


class TestOperationsMatchProtocol:
    def test_env_operations_match_action_space(self) -> None:
        from SSEA.sse_protocols import OPERATIONS

        assert set(ENV_OPERATIONS) == set(OPERATIONS)

    def test_none_is_a_legal_no_op(self, env: Environment) -> None:
        _, fb = env.step(
            Action(manipulation=Manipulation("res_0", "none", 0.0, 1.0))
        )
        assert fb.action_success is True
