"""Milestone 1 测试：Structure Injection Surface（08 §2.1）。

本文件是 Milestone 1 最重要的测试。它证明的不是"字段存在"，
而是 08 §2.1 列出的四条性质是**结构事实**，不依赖调用方自觉：

    - 快环零改动
    - 失败天然回滚（不存在"回滚"操作，因为从未应用）
    - 可遗传
    - 可审计
"""

from __future__ import annotations

import copy

import pytest

from SSEA.sse_protocols import (
    Action,
    GateResult,
    Locomotion,
    SelfModificationProposal,
    Skill,
    StructureStore,
)


def make_action() -> Action:
    return Action(
        locomotion=Locomotion(direction=(1.0, 0.0), speed=0.5, duration=0.1)
    )


def make_skill(skill_id: str = "s1") -> Skill:
    return Skill(
        skill_id=skill_id,
        name="forage",
        precondition={"min_energy": 0.2},
        action_sequence=(make_action(), make_action()),
        expected_outcome={"energy_gain": 0.1},
        success_count=0,
        failure_count=0,
        energy_cost=0.05,
        created_from="trace-1",
        last_used=0.0,
    )


def add_skill_proposal(skill_id: str = "s1") -> SelfModificationProposal:
    return SelfModificationProposal(
        proposal_id=f"p-{skill_id}",
        proposal_type="ADD_SKILL",
        target=skill_id,
        payload={"skill": make_skill(skill_id)},
        reason="从 trace 编译",
    )


# ----------------------------------------------------------------------
#  版本化与五类结构
# ----------------------------------------------------------------------


class TestVersioning:
    def test_five_kinds_each_with_own_version(self) -> None:
        store = StructureStore()
        assert store.versions == {
            "skills": 0,
            "rules": 0,
            "adapters": 0,
            "thresholds": 0,
            "retrieval": 0,
        }

    def test_commit_bumps_only_affected_kind(self) -> None:
        store = StructureStore()
        before = dict(store.versions)
        store.commit(add_skill_proposal(), GateResult(passed=True), timestamp=1.0)
        after = store.versions
        assert after["skills"] == before["skills"] + 1
        assert {k: after[k] for k in after if k != "skills"} == {
            k: before[k] for k in before if k != "skills"
        }

    @pytest.mark.parametrize(
        "ptype,target,payload",
        [
            ("ADD_SKILL", "s1", {"skill": make_skill()}),
            ("UPDATE_SKILL", "s1", {"skill": make_skill()}),
            ("DISABLE_SKILL", "s1", {}),
            ("ADD_RULE", "r1", {"rule": {"if": "energy<0.2", "then": "flee"}}),
            ("UPDATE_RULE", "r1", {"rule": {"if": "a", "then": "b"}}),
            ("UPDATE_THRESHOLD", "caution", {"value": 0.7}),
            # retrieval 是**一份扁平策略**（键即策略字段名），所以 target 是策略
            # 键名、policy 是它的新值——与 UPDATE_THRESHOLD 同形。写
            # ("default", {"policy": {"top_k": 8}}) 会产出 retrieval["default"]，
            # 而 MemorySystem 把整个映射当策略读，见到未知键 "default" 就 ValueError。
            # 见 tests/test_verification_gate.py 的回归钉子。
            ("UPDATE_RETRIEVAL_POLICY", "top_k", {"policy": 8}),
            ("UPDATE_ADAPTER", "instinct_1", {"adapter": b"\x01\x02"}),
        ],
    )
    def test_every_proposal_type_maps_to_a_kind(
        self, ptype: str, target: str, payload: dict
    ) -> None:
        store = StructureStore()
        rec = store.commit(
            SelfModificationProposal(
                proposal_id="p1",
                proposal_type=ptype,
                target=target,
                payload=payload,
            ),
            GateResult(passed=True),
            timestamp=1.0,
        )
        assert rec.applied
        assert rec.from_version == 0
        assert rec.to_version == 1

    def test_committed_retrieval_policy_is_readable_downstream(self) -> None:
        """提交后的检索策略，MemorySystem 必须读得懂。

        Store 只负责版本号与审计，**不负责下游读得懂**——但「过审的提案让
        闭环在下一个 WAKE 上崩」是必须被堵住的洞。这条测试把堵洞的责任钉在
        Store 自己身上：它产出的快照，消费方要能直接用。
        """

        from SSEA.memory_system import MemoryConfig, MemorySystem

        store = StructureStore()
        store.commit(
            SelfModificationProposal(
                proposal_id="p1",
                proposal_type="UPDATE_RETRIEVAL_POLICY",
                target="top_k",
                payload={"policy": 8},
            ),
            GateResult(passed=True),
            timestamp=1.0,
        )
        snap = store.snapshot()
        assert snap.retrieval == {"top_k": 8}
        assert MemorySystem(MemoryConfig(memory_dim=16), snap).policy["top_k"] == 8

    def test_unknown_kind_in_initial_rejected(self) -> None:
        with pytest.raises(ValueError, match="未知的结构类别"):
            StructureStore(initial={"weights": {}})

    def test_disable_skill_removes_it(self) -> None:
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        assert store.snapshot().get_skill("s1") is not None
        store.commit(
            SelfModificationProposal(
                proposal_id="p2", proposal_type="DISABLE_SKILL", target="s1"
            ),
            GateResult(passed=True),
            timestamp=2.0,
        )
        assert store.snapshot().get_skill("s1") is None


# ----------------------------------------------------------------------
#  失败天然回滚 —— 不存在"回滚"操作，因为从未应用
# ----------------------------------------------------------------------


class TestFailureRollsBackNaturally:
    def test_rejected_proposal_does_not_bump_version(self) -> None:
        store = StructureStore()
        rec = store.commit(
            add_skill_proposal(), GateResult(passed=False, reason="sandbox failed"), timestamp=1.0
        )
        assert not rec.applied
        assert rec.from_version == rec.to_version == 0
        assert store.versions["skills"] == 0

    def test_rejected_proposal_does_not_change_snapshot(self) -> None:
        store = StructureStore()
        before = store.snapshot()
        store.commit(
            add_skill_proposal(),
            GateResult(passed=False, stage_failed="regression"),
            timestamp=1.0,
        )
        after = store.snapshot()
        assert before.fingerprint() == after.fingerprint()
        assert after.get_skill("s1") is None

    def test_no_rollback_api_exists(self) -> None:
        """结构事实：StructureStore 没有 rollback / revert 方法。

        回滚之所以不需要，是因为被驳回的提案从未被应用——
        版本号不切换，快照继续用旧版（08 §2.1）。
        """
        public = {n for n in dir(StructureStore) if not n.startswith("_")}
        assert not (public & {"rollback", "revert", "undo", "restore"})

    def test_snapshot_survives_later_rejection(self) -> None:
        """已应用的结构不因后续驳回而失效。"""
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        ctx = store.snapshot()
        assert ctx.get_skill("s1") is not None
        store.commit(
            add_skill_proposal("s2"),
            GateResult(passed=False, reason="bad precondition"),
            timestamp=2.0,
        )
        # 旧快照不受影响；新快照只含 s1
        assert ctx.get_skill("s1") is not None
        assert ctx.get_skill("s2") is None
        assert store.snapshot().get_skill("s2") is None

    def test_partial_failure_keeps_earlier_success(self) -> None:
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        store.commit(
            add_skill_proposal("s2"),
            GateResult(passed=False, stage_failed="format"),
            timestamp=2.0,
        )
        store.commit(add_skill_proposal("s3"), GateResult(passed=True), timestamp=3.0)
        assert store.versions["skills"] == 2
        assert store.applied_count() == 2
        assert store.rejected_count() == 1


# ----------------------------------------------------------------------
#  快环零改动 —— 快照与 Store 脱钩
# ----------------------------------------------------------------------


class TestFastLoopIsolation:
    def test_snapshot_is_immutable(self) -> None:
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        ctx = store.snapshot()
        with pytest.raises(Exception):
            ctx.skills = {}  # type: ignore[misc]

    def test_snapshot_does_not_change_after_later_commit(self) -> None:
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        ctx = store.snapshot()
        fp_before = ctx.fingerprint()
        store.commit(add_skill_proposal("s2"), GateResult(passed=True), timestamp=2.0)
        assert ctx.fingerprint() == fp_before
        assert ctx.get_skill("s2") is None  # 旧快照看不到新技能

    def test_fast_loop_reads_only_snapshot(self) -> None:
        """快环的读取面就是 FastLoopContext，不含 Store 的写入方法。"""
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        ctx = store.snapshot()
        public = {n for n in dir(ctx) if not n.startswith("_")}
        assert not (public & {"commit", "apply", "write", "reject"})

    def test_snapshot_none_field_rejected(self) -> None:
        """五个结构字段都不接受 None——空结构用空 Mapping。"""
        from SSEA.sse_protocols import FastLoopContext

        with pytest.raises(ValueError, match="不能为 None"):
            FastLoopContext(
                skills=None,  # type: ignore[arg-type]
                rules={},
                adapters={},
                thresholds={},
                retrieval={},
                versions={},
            )


# ----------------------------------------------------------------------
#  可遗传 —— 注入面是遗传面的子集
# ----------------------------------------------------------------------


class TestInheritanceSurface:
    def test_snapshot_fields_feed_gene_package(self) -> None:
        """快照的三个字段直接对应 GenePackage 的三个字段来源（08 §2.1）。"""
        store = StructureStore()
        store.commit(add_skill_proposal("s1"), GateResult(passed=True), timestamp=1.0)
        store.commit(
            SelfModificationProposal(
                proposal_id="p2",
                proposal_type="UPDATE_THRESHOLD",
                target="caution",
                payload={"value": 0.7},
            ),
            GateResult(passed=True),
            timestamp=2.0,
        )
        store.commit(
            SelfModificationProposal(
                proposal_id="p3",
                proposal_type="UPDATE_ADAPTER",
                target="instinct_1",
                payload={"adapter": b"\x01\x02"},
            ),
            GateResult(passed=True),
            timestamp=3.0,
        )
        ctx = store.snapshot()

        # 注入面 → 遗传面：同一份结构定义，两处消费
        assert ctx.skills  # → GenePackage.skill_library
        assert ctx.adapters  # → GenePackage.instinct_adapters
        assert ctx.thresholds  # → GenePackage.behavior_policy

    def test_threshold_roundtrip(self) -> None:
        store = StructureStore()
        store.commit(
            SelfModificationProposal(
                proposal_id="p1",
                proposal_type="UPDATE_THRESHOLD",
                target="caution",
                payload={"value": 0.7},
            ),
            GateResult(passed=True),
            timestamp=1.0,
        )
        # 读**字段本身**，与真消费者的读法一致（`fast_loop.py` 取
        # `dict(context.thresholds)` 交给解码器）。曾有一对断言用
        # `get_threshold()`——那是个零调用方的访问器，它的 `default=0.0`
        # 与两个真消费者的回落都对不上，2026-09-28 随访问器一并删除。
        assert store.snapshot().thresholds["caution"] == 0.7
        assert "missing" not in store.snapshot().thresholds

    def test_snapshot_fields_are_read_only(self) -> None:
        """快照顶层只读——``frozen=True`` 只挡**重新绑定**，不挡**就地改**。

        就地改快照是一次**绕过「提案 → 验证门 → Structure Store」的行为变更**
        （07 §16「模型不可绕过验证器应用修改」），而且不留版本号、不进审计。
        字段注解写的是 ``Mapping``（只读承诺），此前装的却是可变 ``dict``——
        承诺与事实差一层。现在顶层包成 ``MappingProxyType``。

        *本测试只声称顶层*：``MappingProxyType`` 是浅的。深度不可变是更深一层
        的题目，见 ``fast_loop_context`` 模块 docstring 的边界说明。
        """

        ctx = StructureStore(initial={"retrieval": {"top_k": 4}}).snapshot()
        for name in ("skills", "rules", "adapters", "thresholds", "retrieval", "versions"):
            with pytest.raises(TypeError):
                getattr(ctx, name)["x"] = 1  # type: ignore[index]
        # 就地写的其它写法在 mappingproxy 上连方法都没有。
        with pytest.raises(AttributeError):
            ctx.retrieval.update({"top_k": 999})  # type: ignore[attr-defined]
        assert ctx.retrieval["top_k"] == 4, "快照内容被改动了"

    def test_the_wrap_is_what_makes_it_read_only(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """证明「只读」确实来自 ``__post_init__`` 那层包装，不是来自别处。

        把 ``__post_init__`` 换成不做包装的版本，同一个写入就必须**成功**。
        没有这条，上面那条测试可能只是碰巧在别的机制上空的绿——**而
        「碰巧绿」正是本项目反复咬到的形状**（守卫名不副实、断言测的是名字）。
        """

        from SSEA.sse_protocols import FastLoopContext

        def _no_wrap(self: object) -> None:
            for name in (
                "skills",
                "rules",
                "adapters",
                "thresholds",
                "retrieval",
                "versions",
            ):
                if getattr(self, name) is None:
                    raise ValueError(f"{name} 不能为 None；空结构用空 Mapping")

        monkeypatch.setattr(FastLoopContext, "__post_init__", _no_wrap)
        ctx = StructureStore(initial={"retrieval": {"top_k": 4}}).snapshot()

        ctx.retrieval["top_k"] = 999  # type: ignore[index]
        assert ctx.retrieval["top_k"] == 999, (
            "去掉包装后写入仍被挡住了——那说明「只读」另有来源，"
            "上面那条测试守的不是这层包装"
        )

    def test_deepcopy_of_a_snapshot_works(self) -> None:
        """``deepcopy(ctx)`` 必须可用——默认路径在本类上是坏的。

        ``deepcopy`` 一个 ``mappingproxy`` 抛 ``TypeError: cannot pickle
        'mappingproxy' object``（实测），所以 ``__deepcopy__`` 不是锦上添花：
        没有它，本类在「深拷贝」这个基础操作上直接坏掉。而没有这条测试，
        那个 ``__deepcopy__`` 就是一段谁也没走过的代码。
        """

        ctx = StructureStore(initial={"retrieval": {"top_k": 4}}).snapshot()
        clone = copy.deepcopy(ctx)
        assert clone == ctx
        assert clone.retrieval is not ctx.retrieval, "深拷贝与原件共享了容器"


# ----------------------------------------------------------------------
#  可审计
# ----------------------------------------------------------------------


class TestAuditability:
    def test_audit_record_fields(self) -> None:
        store = StructureStore()
        rec = store.commit(add_skill_proposal(), GateResult(passed=True), timestamp=7.5)
        assert rec.proposal_id == "p-s1"
        assert rec.kind == "skills"
        assert rec.from_version == 0
        assert rec.to_version == 1
        assert rec.gate_result == "pass"
        assert rec.timestamp == 7.5
        assert rec.applied

    def test_audit_log_preserves_order(self) -> None:
        store = StructureStore()
        for i in range(3):
            store.commit(
                add_skill_proposal(f"s{i}"), GateResult(passed=True), timestamp=float(i)
            )
        log = store.audit_log()
        assert [r.proposal_id for r in log] == ["p-s0", "p-s1", "p-s2"]
        assert [r.to_version for r in log] == [1, 2, 3]

    def test_rejection_recorded_with_stage(self) -> None:
        store = StructureStore()
        rec = store.commit(
            add_skill_proposal(),
            GateResult(passed=False, stage_failed="sandbox", reason="timeout"),
            timestamp=1.0,
        )
        assert rec.gate_result == "reject:sandbox"
        assert rec.reason == "timeout"
        assert not rec.applied

    def test_counts(self) -> None:
        store = StructureStore()
        store.commit(add_skill_proposal("a"), GateResult(passed=True), timestamp=1.0)
        store.commit(
            add_skill_proposal("b"), GateResult(passed=False), timestamp=2.0
        )
        store.commit(add_skill_proposal("c"), GateResult(passed=True), timestamp=3.0)
        assert store.applied_count() == 2
        assert store.rejected_count() == 1
        assert len(store.audit_log()) == 3


# ----------------------------------------------------------------------
#  验收实验 7 的可执行骨架（08 §6）
# ----------------------------------------------------------------------


class TestSleepCompilationExperimentShape:
    """08 §6 建议的验收实验 7：慢环在一等公民状态中被触发，且注入可回滚。

    Milestone 1 只提供协议骨架，不提供代谢判定与 Gate 本体；
    此处验证该实验的**结构前提**已具备：提案可被分别放过与驳回，
    且只有被放过的提案改变快环行为。
    """

    def test_gate_selectively_passes(self) -> None:
        store = StructureStore()
        proposals = [add_skill_proposal(f"s{i}") for i in range(4)]
        # 放过偶数，驳回奇数
        for i, p in enumerate(proposals):
            store.commit(
                p,
                GateResult(passed=(i % 2 == 0), stage_failed=None if i % 2 == 0 else "regression"),
                timestamp=float(i),
            )
        ctx = store.snapshot()
        assert ctx.get_skill("s0") is not None
        assert ctx.get_skill("s1") is None
        assert ctx.get_skill("s2") is not None
        assert ctx.get_skill("s3") is None
        assert store.versions["skills"] == 2

    def test_audit_completeness_for_experiment(self) -> None:
        """版本切换审计记录完整率 = 100% 是可判定的。"""
        store = StructureStore()
        for i, p in enumerate([add_skill_proposal(f"s{i}") for i in range(3)]):
            store.commit(
                p, GateResult(passed=(i != 1)), timestamp=float(i)
            )
        log = store.audit_log()
        assert len(log) == 3
        assert all(
            r.from_version is not None and r.to_version is not None for r in log
        )
        # 驳回项 from == to
        rejected = [r for r in log if not r.applied]
        assert all(r.from_version == r.to_version for r in rejected)
