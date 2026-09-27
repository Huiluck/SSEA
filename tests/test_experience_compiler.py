"""Experience Compiler 测试 —— 07 §6.6 + 模块 D1。

对应 [docs/13-milestone4-plan.md](../docs/13-milestone4-plan.md) §3 增量 2 的验收：

    能从真实 trace 产出提案，且不产出恒真提案。

「不恒真」是本文件的重心。一个恒真的编译器（不管 trace 是什么都提同样的提案）
能让整条慢环链看起来在工作，而实际上什么也没学到——它只是把一个常数
搬过了验证门。所以下面用四种独立的方式证它**会沉默**：

    空 trace            → 0 条
    没有成功段的 trace  → 0 条
    同一条 trace 第二次 → 0 条（技能已在结构里）
    不同 trace          → 不同提案

最后一条端到端测试是 07 §18 第 7 项「模型可以将成功行为固化为技能」缺的那半条：
Milestone 3 备齐了编译判据，但**没有触发器**。编译器就是那个触发器。
"""

from __future__ import annotations

import math

import pytest
import torch

from SSEA.environment import Environment, EnvironmentConfig
from SSEA.experience_compiler import (
    DELEGATED_DELTAS,
    DEFERRED_DELTAS,
    IMPLEMENTED_DELTAS,
    CompileResult,
    ExperienceCompiler,
    ExperienceConfig,
    make_slow_loop_hook,
    run_slow_loop,
)
from SSEA.fast_loop import STATE_SLEEP, FastLoop, FastLoopConfig
from SSEA.metabolic_monitor import MetabolicMonitor
from SSEA.skill_runner import SkillRunner
from SSEA.sse_protocols import Action, Locomotion, Manipulation, SelfModificationProposal, SkillCall
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate
from tests.conftest import make_context
from tests.test_skill_library import move, record, sub_action_record  # noqa: F401


# ----------------------------------------------------------------------
#  辅助
# ----------------------------------------------------------------------


def successful_trace(n: int = 5, speed: float = 0.5) -> tuple:
    """一段净能量收益为正、且每帧都是直接解码的轨迹。"""

    return tuple(
        record(frame=i, action=move(speed), energy=0.2) for i in range(n)
    )


def failing_trace(n: int = 5) -> tuple:
    """一段净能量为负的轨迹——不该编译出任何技能。"""

    return tuple(
        record(frame=i, action=move(0.3), energy=-0.2) for i in range(n)
    )


def gate() -> VerificationGate:
    return VerificationGate(GateConfig(env_frames=8))


def compiler(**cfg) -> ExperienceCompiler:
    return ExperienceCompiler(ExperienceConfig(**cfg))  # type: ignore[arg-type]


def break_frame() -> object:
    """一帧失效动作——把一段轨迹切成两段，从而产出两条不同签名的技能。"""

    return record(frame=99, action=move(0.1), success=False)


# ----------------------------------------------------------------------
#  能从真实 trace 产出提案
# ----------------------------------------------------------------------


class TestCompilesRealTraces:
    def test_successful_trace_yields_a_proposal(self) -> None:
        r = compiler().compile(successful_trace())
        assert len(r.proposals) == 1
        assert r.proposals[0].proposal_type == "ADD_SKILL"

    def test_payload_matches_the_gate_contract(self) -> None:
        """payload 的键必须是 Gate 格式级认的那一个（``_REQUIRED_PAYLOAD_KEY``）。"""

        r = compiler().compile(successful_trace())
        p = r.proposals[0]
        assert set(p.payload) == {"skill"}
        assert p.payload["skill"].skill_id == p.target

    def test_proposal_passes_the_real_gate(self) -> None:
        """编译出来的提案不是纸面合法——它要真能过门。"""

        g = gate()
        store = StructureStore()
        r = compiler().compile(successful_trace(), structure=store.snapshot())
        assert r.proposals
        for p in r.proposals:
            assert g.check(p, store.snapshot()).passed, g.check(
                p, store.snapshot()
            ).reason

    def test_expected_effect_carries_the_world_price(self) -> None:
        """``expected_effect`` 记的是世界计价物（能量），不是内部评分。"""

        r = compiler().compile(successful_trace())
        eff = r.proposals[0].expected_effect
        assert eff["energy_change"] > 0
        assert eff["frames"] == 5
        assert "score" not in eff and "rank" not in eff

    def test_proposal_id_is_unique_and_traceable(self) -> None:
        """id 唯一，且唯一性来自**内容**而不是调用次数。

        计数器式的 id（第 N 次编译就是 ``exp-N``）也能唯一，但它让
        ``compile()`` 依赖调用历史——同一条 trace 两次编译得到两个 id，
        「这是重复提案」就得靠集合运算才能回答。
        """

        c = compiler()
        r1 = c.compile(successful_trace(5, 0.5))
        r2 = c.compile(successful_trace(5, 0.7))
        ids = {p.proposal_id for p in r1.proposals + r2.proposals}
        assert len(ids) == len(r1.proposals) + len(r2.proposals)
        assert all(i.startswith("exp-") for i in ids)
        # id 里就带着目标——审计日志不必翻 payload 才知道这是关于哪条技能的
        assert all(i == f"exp-{p.target}" for i, p in zip(sorted(ids), r1.proposals))

    def test_same_content_gives_the_same_id(self) -> None:
        """内容相同 → id 相同。这样重复提案在日志里**看起来就是重复的**。"""

        a = compiler().compile(successful_trace()).proposals[0]
        b = compiler().compile(successful_trace()).proposals[0]
        assert a.proposal_id == b.proposal_id
        assert a.target == b.target

    def test_risk_level_is_low_and_says_why(self) -> None:
        """新增一条技能不碰任何已有结构——风险等级是改动半径，不是乐观估计。"""

        r = compiler().compile(successful_trace())
        assert r.proposals[0].risk_level == "low"

    def test_origin_is_none_for_first_compilation(self) -> None:
        """首次固化不是本能内化。内化走 08 §3.4 的 ``consolidated_from:``。"""

        r = compiler().compile(successful_trace())
        assert r.proposals[0].origin is None


# ----------------------------------------------------------------------
#  不产出恒真提案（验收的另一半）
# ----------------------------------------------------------------------


class TestNotTautological:
    def test_empty_trace_yields_nothing(self) -> None:
        assert compiler().compile(()).proposals == ()

    def test_failing_trace_yields_nothing(self) -> None:
        """净能量为负的轨迹不该变成技能——那是把失败固化下来。"""

        r = compiler().compile(failing_trace())
        assert r.proposals == ()
        assert r.skipped == ()

    def test_sub_action_frames_yield_nothing(self) -> None:
        """技能执行中的子动作不参与编译，否则会把已有技能抄一份。"""

        r = compiler().compile(tuple(sub_action_record(i) for i in range(6)))
        assert r.proposals == ()

    def test_same_trace_compiled_twice_yields_nothing_the_second_time(self) -> None:
        """同一条轨迹第二次编译 → 0 条。这是「不恒真」最直接的一条。"""

        store = StructureStore()
        snap = store.snapshot()
        c = compiler()

        first = c.compile(successful_trace(), structure=snap)
        assert len(first.proposals) == 1

        # 把提案应用掉，再拿新快照编译同一条 trace
        store.commit(first.proposals[0], gate().check(first.proposals[0], snap), 1.0)
        second = c.compile(successful_trace(), structure=store.snapshot())

        assert second.proposals == ()
        assert second.skipped, "沉默了就必须留原因，否则与「什么都没看到」不可区分"

    def test_skip_can_be_disabled_to_observe_gate_rejections(self) -> None:
        """关掉过滤后编译器仍会提重复项——Gate 该拒，且理由可观测。"""

        store = StructureStore()
        snap = store.snapshot()
        p = compiler(skip_existing=False).compile(successful_trace(), snap).proposals[0]
        store.commit(p, gate().check(p, snap), 1.0)

        again = compiler(skip_existing=False).compile(
            successful_trace(), store.snapshot()
        )
        assert len(again.proposals) == 1
        verdict = gate().check(again.proposals[0], store.snapshot())
        assert not verdict.passed
        assert verdict.stage_failed == "format"

    def test_different_traces_yield_different_proposals(self) -> None:
        """trace 变了，提案必须变。否则编译器是个常数发生器。"""

        c = compiler()
        a = c.compile(successful_trace(5, 0.5)).proposals
        b = c.compile(successful_trace(6, 0.9)).proposals
        assert {p.target for p in a} != {p.target for p in b}

    def test_duplicate_signatures_within_one_batch_are_collapsed(self) -> None:
        """同批里两条同签名轨迹只提一条——提两条会让第二条被格式级拒掉。

        中间必须夹一帧失效动作断段：两段 4 帧连成一段 8 帧的话，
        ``_windows`` 只会切出**一条**技能，这个测试就什么都没验到。
        """

        trace = (
            successful_trace(4, 0.5) + (break_frame(),) + successful_trace(4, 0.5)
        )
        r = compiler().compile(trace)
        assert len(r.proposals) == 1
        assert any("本批内" in why for _, why in r.skipped)

    def test_compiler_holds_no_structure_state(self) -> None:
        """编译器不持有结构——同一份 trace 喂给两个实例，结论相同。"""

        t = successful_trace()
        a = compiler().compile(t)
        b = compiler().compile(t)
        assert [p.target for p in a.proposals] == [p.target for p in b.proposals]

    def test_compile_is_deterministic(self) -> None:
        t = successful_trace()
        c = compiler()
        r1 = c.compile(t)
        r2 = c.compile(t)
        assert r1 == r2


# ----------------------------------------------------------------------
#  未实现的 Δ 有据可查
# ----------------------------------------------------------------------


class TestDeferredDeltas:
    def test_only_delta_s_is_implemented(self) -> None:
        assert IMPLEMENTED_DELTAS == ("ΔS",)

    def test_deferred_set_is_exactly_the_planned_increments(self) -> None:
        """ΔR / ΔM 各有归属增量。

        这条测试是**文档同步哨兵**：增量落地时必须同步改
        ``experience_compiler.DEFERRED_DELTAS`` 与模块 docstring，
        否则这里失败。
        """

        assert set(DEFERRED_DELTAS) == {"ΔR", "ΔM"}

    def test_delta_theta_moved_from_deferred_to_delegated(self) -> None:
        """Δθ 有生产者了，但生产者不是编译器。

        「有人管但不是我」与「没人管」必须分开记：混在一起的话，
        Δθ 一旦从 DEFERRED 消失，就再也看不出它到底有没有人管。
        """

        assert set(DELEGATED_DELTAS) == {"Δθ"}
        assert "LocalPlasticity" in DELEGATED_DELTAS["Δθ"]

    def test_every_deferred_delta_names_its_increment(self) -> None:
        for delta, why in DEFERRED_DELTAS.items():
            assert "增量" in why, f"{delta} 没说是哪个增量的事"

    def test_no_dead_methods_for_deferred_deltas(self) -> None:
        """没有返回空 tuple 的占位方法——空函数就是死代码（08 §2.4）。"""

        public = [n for n in dir(ExperienceCompiler) if not n.startswith("_")]
        for bad in ("compile_rules", "compile_memory", "compile_params"):
            assert bad not in public

    def test_the_three_sets_are_pairwise_disjoint(self) -> None:
        """一个 Δ 只能处在一种状态里：本模块实现 / 交给别人 / 还没做。"""

        sets = [set(IMPLEMENTED_DELTAS), set(DELEGATED_DELTAS), set(DEFERRED_DELTAS)]
        for i, a in enumerate(sets):
            for b in sets[i + 1 :]:
                assert not a & b


# ----------------------------------------------------------------------
#  编译器不提交（职责边界）
# ----------------------------------------------------------------------


class TestCompilerDoesNotCommit:
    def test_compile_takes_no_store_and_returns_no_record(self) -> None:
        """返回值里没有 AuditRecord——提交不是编译器的事。"""

        r = compiler().compile(successful_trace())
        assert isinstance(r, CompileResult)
        assert not any(
            "record" in name.lower() for name in vars(r)
        ), "CompileResult 不该带提交结果"

    def test_proposals_are_frozen_dataclasses(self) -> None:
        """提案不可变——它是一条待审的记录，不是一份可改的草稿。"""

        p = compiler().compile(successful_trace()).proposals[0]
        assert isinstance(p, SelfModificationProposal)
        with pytest.raises(Exception):
            p.target = "hacked"  # type: ignore[misc]


# ----------------------------------------------------------------------
#  慢环一步：编译 → 过门 → 提交
# ----------------------------------------------------------------------


class TestSlowLoopStep:
    def test_legal_proposal_is_committed(self) -> None:
        store = StructureStore()
        out = run_slow_loop(successful_trace(), store, gate(), timestamp=1.0)

        # 目标 id 由签名决定（sha1），不是可预测的字面量——先编译一次拿到它。
        target = compiler().compile(successful_trace()).proposals[0].target

        assert out.applied == 1
        assert out.rejected == 0
        assert out.context is not None
        assert store.versions["skills"] == 1
        assert set(store.snapshot().skills) == {target}
        assert store.snapshot().get_skill(target) is not None

    def test_nothing_to_compile_returns_no_context(self) -> None:
        """没有可编译的东西 → context 是 None，旧快照继续有效。"""

        store = StructureStore()
        out = run_slow_loop(failing_trace(), store, gate())
        assert out.records == ()
        assert out.context is None
        assert store.versions["skills"] == 0

    def test_rejection_does_not_raise_and_does_not_bump(self) -> None:
        """拒绝是正常路径——这就是慢环能写成一条直线的原因。"""

        store = StructureStore()
        # 先手工塞一条同 id 的技能，让编译出来的提案撞上「已存在」
        existing = compiler().compile(successful_trace()).proposals[0]
        store.commit(existing, gate().check(existing, store.snapshot()), 0.0)
        before = dict(store.versions)

        out = run_slow_loop(
            successful_trace(), store, gate(), compiler=compiler(skip_existing=False)
        )

        assert out.rejected == 1
        assert out.applied == 0
        assert out.context is None
        assert dict(store.versions) == before

    def test_audit_log_records_both_paths(self) -> None:
        """应用与驳回都进审计日志——拒绝留痕，不是静默丢弃。"""

        store = StructureStore()
        g = gate()
        run_slow_loop(successful_trace(), store, g, timestamp=1.0)
        # 关掉 skip_existing，让同一条提案再撞一次「已存在」→ 格式级拒
        run_slow_loop(
            successful_trace(),
            store,
            g,
            compiler=compiler(skip_existing=False),
            timestamp=2.0,
        )

        log = store.audit_log()
        assert len(log) == 2
        assert log[0].applied and log[0].gate_result == "pass"
        assert log[0].from_version == 0 and log[0].to_version == 1
        assert not log[1].applied
        assert log[1].gate_result == "reject:format"
        assert log[1].from_version == log[1].to_version == 1
        assert "已存在" in log[1].reason

    def test_gate_sees_a_fresh_snapshot_per_proposal(self) -> None:
        """提案 2 该看到提案 1 应用后的结构，不是循环开始时的那个。"""

        seen: list[tuple] = []

        class SpyGate:
            def check(self, proposal, structure):
                seen.append((proposal.target, tuple(sorted(structure.skills))))
                return gate().check(proposal, structure)

        store = StructureStore()
        # 两条不同签名的技能，一批提出。中间夹一帧失效动作断段——
        # 否则 8 帧连成一段，只会切出**一条**技能，这个测试就什么也没验。
        trace = (
            successful_trace(4, 0.5) + (break_frame(),) + successful_trace(4, 0.9)
        )
        run_slow_loop(trace, store, SpyGate(), timestamp=1.0)  # type: ignore[arg-type]

        assert len(seen) == 2
        assert seen[0][1] == ()
        assert seen[1][1] != (), "第二条提案看到的技能库是空的——它在看旧快照"


# ----------------------------------------------------------------------
#  端到端：睡眠期真的整理经验（07 §18 第 7 项缺的那半条）
# ----------------------------------------------------------------------


class TestSleepActuallyCompiles:
    """Milestone 3 备齐了编译判据，但没有触发器——慢环钩子默认 None。

    下面这条是触发器存在的证明：跑一个真快环，让它睡一觉，
    醒来时技能库里多了一条它自己编译出来的技能。

    **为什么这里要脚本化策略与睡眠判据**（不是走默认配置）：

    - 默认 Action Decoder 是随机初始化，从不 emit grasp；而这个世界里
      唯一的正能量来源是 grasp 资源。所以默认配置下跑一万帧也编译不出
      任何东西——这不是编译器的缺陷，是世界还没给出可学的成功。
      脚本化策略替换的是**策略**，状态机 / Skill Runner / Environment /
      Gate / Store 全是真的。
    - 睡眠判据用「攒满 n 帧才准睡」：若第一帧就睡（thresholds 全放宽），
      trace 里永远只有 1 帧 RUN，短于 ``min_frames``，编译器无事可做。
    - ``resource_gain=0.2``：能量上限是 1.0，而 agent 开局就满。增益太大的话
      第一抓就把头寸吃满，后续各抓的 ``energy_change`` 全是 0.0，
      连续正收益段就拼不起来。压低增益让 3 帧连抓都记为正。

    这三条都是**环境与策略的现实约束**，记录下来是为了让后来者知道
    这个测试为什么长这样，而不是把结论误读成"慢环已经能在真实世界上学了"。
    """

    N_WARMUP = 24
    N_SLEEP_AFTER = 28

    @staticmethod
    def _policy(env: Environment):
        """出去再回来（耗掉能量上限的头寸），然后连抓资源簇。"""

        def decode(intent, constraints, drive, candidates=None, gate_thresholds=None):
            if env.time < TestSleepActuallyCompiles.N_WARMUP:
                out = env.time < TestSleepActuallyCompiles.N_WARMUP / 2
                return Action(
                    locomotion=Locomotion((1.0, 0.0) if out else (-1.0, 0.0), 1.0, 1.0)
                )
            reachable = [
                o
                for o, _ in env.visible_objects()
                if o.resource_value > 0
            ]
            if not reachable:
                return Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0))
            target = min(
                reachable, key=lambda o: math.dist(o.position, env.position)
            )
            if math.dist(target.position, env.position) <= 0.95:
                return Action(
                    manipulation=Manipulation(
                        target_id=target.object_id,
                        operation="grasp",
                        force=0.5,
                        duration=1.0,
                    )
                )
            dx = target.position[0] - env.position[0]
            dy = target.position[1] - env.position[1]
            norm = max((dx * dx + dy * dy) ** 0.5, 1e-9)
            return Action(locomotion=Locomotion((dx / norm, dy / norm), 1.0, 1.0))

        return decode

    @staticmethod
    def _monitor(n: int) -> MetabolicMonitor:
        """攒满 n 帧 RUN 才准睡。包装而非继承：判据本身仍归 MetabolicMonitor。"""

        inner = MetabolicMonitor(
            sleep_threat_threshold=1.1,
            sleep_fatigue_threshold=0.0,
        )
        runs = [0]

        class SleepAfterN:
            def drive_vector(self, body):
                return inner.drive_vector(body)

            def observe(self, obs):
                return inner.observe(obs)

            def wants_sleep(self, body, obs) -> bool:
                runs[0] += 1
                return runs[0] >= n and inner.wants_sleep(body, obs)

            def reset(self) -> None:
                inner.reset()

        return SleepAfterN()  # type: ignore[return-value]

    @staticmethod
    def _world() -> Environment:
        """8 个资源全堆在原点头上，0 危险源——策略只管抓，不用躲。"""

        return Environment(
            EnvironmentConfig(
                n_resources=8,
                spawn_near_count=8,
                spawn_near_radius=0.0,
                n_hazards=0,
                n_props=0,
                resource_gain=0.2,
            ),
            seed=0,
        )

    def _loop(self) -> tuple[FastLoop, StructureStore]:
        """一条接好了慢环钩子的真快环。策略与环共享同一个 Environment。"""

        env = self._world()
        store = StructureStore()
        loop = FastLoop(
            env,
            make_context(),
            action_decoder=self._policy(env),
            metabolic_monitor=self._monitor(self.N_SLEEP_AFTER),
            config=FastLoopConfig(max_frames=40, min_sleep_frames=2),
            slow_loop=make_slow_loop_hook(store, gate()),
        )
        return loop, store

    def test_fast_loop_sleep_compiles_a_skill(self) -> None:
        """端到端：模型自己抓对了 → 睡着 → 醒来技能库里多了一条。"""

        torch.manual_seed(0)
        loop, store = self._loop()
        loop.run(40)

        compiled = store.snapshot().skills
        assert len(compiled) == 1, (
            "睡了几次却一条技能都没有——触发器没接上，或者编译判据失效"
        )
        skill = next(iter(compiled.values()))
        assert skill.skill_id in compiled
        assert skill.created_from.startswith("skill_compiler")
        assert skill.total_frames() >= 3
        assert skill.expected_outcome["outcome"] == "energy_gain"
        assert skill.expected_outcome["energy_change"] > 0

        # 醒来后快环自己看到的快照里也有它——注入面真的通了
        assert set(loop.context.skills) == set(compiled)
        assert loop.context.get_skill(skill.skill_id) is not None

    def test_later_sleeps_stay_silent(self) -> None:
        """第二次睡同一条轨迹 → 没有新提案。

        这一条把「不恒真」放在它该在的地方：不是靠单测里的两个实例，
        而是在一个真快环的连续睡眠里。技能一旦进了结构，
        后面的每一次睡眠都该沉默。
        """

        torch.manual_seed(0)
        loop, store = self._loop()
        records = loop.run(40)
        sleeps = sum(1 for r in records if r.state == STATE_SLEEP)

        assert sleeps >= 2, "至少得睡两觉，这条测试才有意义"
        assert len(store.snapshot().skills) == 1
        assert len(store.audit_log()) == 1, (
            "睡了好几觉却提了多次案——重复提案正在污染审计日志"
        )

    def test_compiled_skill_is_invocable_by_the_runner(self) -> None:
        """编译出来的技能不是摆设——Skill Runner 能查表并展开它。"""

        torch.manual_seed(0)
        loop, store = self._loop()
        loop.run(40)

        skill = next(iter(store.snapshot().skills.values()))
        runner = SkillRunner(loop.context)
        runner.submit(
            Action(skill=SkillCall(skill_id=skill.skill_id, params=())),
            loop.observation.body,
            loop.observation,
        )
        sub = runner.current_action(
            Action(locomotion=Locomotion((1.0, 0.0), 0.5, 1.0))
        )
        # 子动作本身不带 skill 字段（它是被展开的那个），"正在跑哪条技能"
        # 由 runner 的 running_skill_id 说话。
        assert runner.running_skill_id == skill.skill_id
        assert sub == skill.action_sequence[0], "展开出来的不是该技能的第一个动作"

    def test_hook_returns_none_when_nothing_was_applied(self) -> None:
        """没有应用 → None → 快环继续用旧快照（08 §2.1 失败天然回滚）。"""

        store = StructureStore()
        hook = make_slow_loop_hook(store, gate())
        assert hook(failing_trace()) is None

    def test_hook_returns_a_context_when_something_was_applied(self) -> None:
        store = StructureStore()
        hook = make_slow_loop_hook(store, gate())
        ctx = hook(successful_trace())
        assert ctx is not None
        assert len(ctx.skills) == 1

    def test_old_snapshot_is_untouched_by_the_slow_loop(self) -> None:
        """快环零改动：已交出的快照不因慢环提交而变化。"""

        store = StructureStore()
        old = store.snapshot()
        run_slow_loop(successful_trace(), store, gate(), timestamp=1.0)
        assert old.skills == {}
        assert len(store.snapshot().skills) == 1
