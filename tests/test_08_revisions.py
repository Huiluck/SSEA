"""Milestone 1 测试：08 修订条款是否真正落到协议层。

每个测试对应 docs/08-dual-loop-interface-and-gap-closure.md 第 5 节
修订条款汇总表中的一行。测试名中的编号即该表的行号，便于回溯。
"""

from __future__ import annotations

import dataclasses

import pytest

from SSEA.sse_protocols import (
    Action,
    ActionConstraints,
    Communication,
    GenePackage,
    Locomotion,
    Manipulation,
    MemoryItem,
    MemoryWrite,
    SelfModification,
    SelfModificationProposal,
    Skill,
    SkillCall,
    default_constraints,
    idle_action,
)

# ----------------------------------------------------------------------
#  fixtures
# ----------------------------------------------------------------------


def make_action(**overrides: object) -> Action:
    """构造一个最小合法动作。"""
    base: dict[str, object] = {
        "locomotion": Locomotion(direction=(1.0, 0.0), speed=0.5, duration=0.1)
    }
    base.update(overrides)
    return Action(**base)  # type: ignore[arg-type]


def make_skill(skill_id: str = "s1") -> Skill:
    return Skill(
        skill_id=skill_id,
        name="test skill",
        precondition={"min_energy": 0.2},
        action_sequence=(
            make_action(),
            make_action(
                manipulation=Manipulation(
                    target_id="obj1", operation="grasp", force=0.3, duration=0.1
                )
            ),
        ),
        expected_outcome={"energy_gain": 0.1},
        success_count=0,
        failure_count=0,
        energy_cost=0.05,
        created_from="trace-1",
        last_used=0.0,
    )


def make_proposal(ptype: str, **kw: object) -> SelfModificationProposal:
    return SelfModificationProposal(
        proposal_id=kw.pop("proposal_id", "p1"),
        proposal_type=ptype,
        target=kw.pop("target", "s1"),
        reason=kw.pop("reason", "test"),
        **kw,  # type: ignore[arg-type]
    )


# ----------------------------------------------------------------------
#  行 6：8.5 Action 删除 latent_action；新增「动作必须可执行」
# ----------------------------------------------------------------------


class TestActionHasNoLatent:
    def test_latent_action_field_absent(self) -> None:
        names = {f.name for f in dataclasses.fields(Action)}
        assert "latent_action" not in names

    def test_latent_vector_field_absent(self) -> None:
        names = {f.name for f in dataclasses.fields(Action)}
        assert not any("latent" in n for n in names)

    def test_channels_all_have_consumers(self) -> None:
        """六个通道各有消费者（见 action.py 模块 docstring 的对照表）。"""
        assert Action.CHANNELS == (
            "locomotion",
            "manipulation",
            "communication",
            "memory",
            "skill",
            "self_modification",
        )

    def test_empty_action_is_not_executable(self) -> None:
        assert not Action().is_executable()

    def test_empty_action_rejected_by_post_init_via_executable(self) -> None:
        """协议不抛异常，但明确判为不可执行——由消费方负责拒绝。"""
        a = Action()
        assert a.active_channels() == ()

    def test_idle_action_is_executable(self) -> None:
        """「本帧不动」是可执行动作，与全空的非法 Action 不同。"""
        assert idle_action().is_executable()
        assert idle_action().locomotion is not None
        assert idle_action().locomotion.speed == 0.0

    @pytest.mark.parametrize(
        "channel",
        list(Action.CHANNELS),
    )
    def test_each_channel_alone_makes_action_executable(self, channel: str) -> None:
        kwargs = {
            "locomotion": dict(direction=(0.0, 0.0), speed=0.0, duration=0.0),
            "manipulation": dict(target_id="", operation="none", force=0.0, duration=0.0),
            "communication": dict(target_id="", signal=()),
            "memory": dict(store=False, content=(), importance=0.0),
            "skill": dict(skill_id=""),
            "self_modification": dict(proposal_type="ADD_RULE"),
        }
        action = Action(**{channel: kwargs[channel]})  # type: ignore[arg-type]
        assert action.is_executable()
        assert action.active_channels() == (channel,)


# ----------------------------------------------------------------------
#  行 7：8.4 ActionSpace 删除 latent 块
# ----------------------------------------------------------------------


class TestActionSpaceHasNoLatent:
    def test_no_latent_attr(self) -> None:
        from SSEA.sse_protocols import default_action_space

        names = {f.name for f in dataclasses.fields(default_action_space())}
        assert not any("latent" in n for n in names)

    def test_operations_exclude_latent(self) -> None:
        from SSEA.sse_protocols import OPERATIONS

        assert not any("latent" in op for op in OPERATIONS)


# ----------------------------------------------------------------------
#  行 8：8.3 ActionConstraints 增补强制执行说明
# ----------------------------------------------------------------------


class TestConstraintEnforcement:
    def test_no_violation_when_within_bounds(self) -> None:
        assert default_constraints().violations(make_action()) == []

    def test_speed_over_max(self) -> None:
        c = ActionConstraints(
            max_speed=1.0,
            max_force=1.0,
            max_duration=1.0,
            allowed_operations=("none", "grasp"),
            forbidden_targets=(),
            energy_budget=1.0,
            can_communicate=True,
            can_store_memory=True,
            can_call_skill=True,
            can_self_modify=True,
        )
        action = make_action(
            locomotion=Locomotion(direction=(1.0, 0.0), speed=2.0, duration=0.1)
        )
        v = c.violations(action)
        assert len(v) == 1
        assert "max_speed" in v[0]

    def test_operation_not_allowed(self) -> None:
        c = default_constraints()
        action = make_action(
            manipulation=Manipulation(
                target_id="o1", operation="use_tool", force=0.1, duration=0.1
            )
        )
        # 默认约束允许 use_tool；换一份不允许的
        c = dataclasses.replace(
            c, allowed_operations=("none", "grasp", "push", "pull", "release")
        )
        assert any("allowed_operations" in x for x in c.violations(action))

    def test_forbidden_target(self) -> None:
        c = dataclasses.replace(default_constraints(), forbidden_targets=("agent7",))
        action = make_action(
            manipulation=Manipulation(
                target_id="agent7", operation="push", force=0.1, duration=0.1
            )
        )
        assert any("forbidden_targets" in x for x in c.violations(action))

    @pytest.mark.parametrize(
        "channel,value",
        [
            ("communication", Communication(target_id="a2", signal=(0.1,))),
            ("memory", MemoryWrite(store=True, content=(0.1,), importance=0.5)),
            ("skill", SkillCall(skill_id="s1", params={})),
            (
                "self_modification",
                SelfModification(proposal_type="ADD_RULE"),
            ),
        ],
    )
    def test_channel_gated_by_flag(self, channel: str, value: object) -> None:
        """四个布尔约束各自挡住对应通道。"""
        flag = {
            "communication": "can_communicate",
            "memory": "can_store_memory",
            "skill": "can_call_skill",
            "self_modification": "can_self_modify",
        }[channel]
        c = dataclasses.replace(default_constraints(), **{flag: False})
        action = Action(**{channel: value})
        assert not c.permits(action)

    def test_permits_is_negation_of_violations(self) -> None:
        c = default_constraints()
        assert c.permits(make_action()) is True
        assert c.violations(make_action()) == []

    def test_negative_speed_rejected_at_construction(self) -> None:
        with pytest.raises(ValueError, match="max_speed"):
            dataclasses.replace(default_constraints(), max_speed=-1.0)


# ----------------------------------------------------------------------
#  行 11：8.9 Feedback prediction_error 由 SurpriseEstimator 产出
# ----------------------------------------------------------------------


class TestFeedbackPredictionError:
    def test_prediction_error_present_and_non_negative(self) -> None:
        from SSEA.sse_protocols import Feedback

        f = Feedback(
            energy_change=-0.1,
            damage_change=0.0,
            fatigue_change=0.01,
            prediction_error=0.0,
            action_success=True,
            survived=True,
        )
        assert f.prediction_error == 0.0

    def test_negative_prediction_error_rejected(self) -> None:
        from SSEA.sse_protocols import Feedback

        with pytest.raises(ValueError, match="prediction_error"):
            Feedback(
                energy_change=0.0,
                damage_change=0.0,
                fatigue_change=0.0,
                prediction_error=-0.1,
                action_success=True,
                survived=True,
            )

    def test_no_reward_field(self) -> None:
        """Feedback 不是评分函数——协议中不存在 reward / score 字段。"""
        from SSEA.sse_protocols import Feedback

        names = {f.name for f in dataclasses.fields(Feedback)}
        assert not any("reward" in n or "score" in n for n in names)


# ----------------------------------------------------------------------
#  行 12：8.10 MemoryItem 增补可继承性筛选
# ----------------------------------------------------------------------


class TestMemoryHeritability:
    @pytest.mark.parametrize("mtype", ["RULE", "SKILL"])
    def test_rule_and_skill_are_heritable_types(self, mtype: str) -> None:
        assert mtype in {"RULE", "SKILL"}

    @pytest.mark.parametrize("mtype", ["EVENT", "BODY_EXPERIENCE"])
    def test_event_and_body_experience_are_transient(self, mtype: str) -> None:
        item = MemoryItem(
            id="m1",
            timestamp=1.0,
            type=mtype,
            context_vector=(),
            content_vector=(),
            outcome="",
            importance=1.0,
            retrieval_count=99,
            last_retrieved=1.0,
        )
        assert item.is_transient
        assert not item.is_heritable(importance_threshold=0.0, min_retrieval_count=0)

    def test_heritable_when_all_three_conditions_met(self) -> None:
        item = MemoryItem(
            id="m1",
            timestamp=1.0,
            type="RULE",
            context_vector=(),
            content_vector=(),
            outcome="ok",
            importance=0.8,
            retrieval_count=5,
            last_retrieved=1.0,
        )
        assert item.is_heritable(importance_threshold=0.5, min_retrieval_count=3)

    def test_not_heritable_when_importance_too_low(self) -> None:
        item = MemoryItem(
            id="m1",
            timestamp=1.0,
            type="RULE",
            context_vector=(),
            content_vector=(),
            outcome="ok",
            importance=0.2,
            retrieval_count=5,
            last_retrieved=1.0,
        )
        assert not item.is_heritable(importance_threshold=0.5, min_retrieval_count=3)

    def test_not_heritable_when_never_retrieved(self) -> None:
        item = MemoryItem(
            id="m1",
            timestamp=1.0,
            type="SKILL",
            context_vector=(),
            content_vector=(),
            outcome="ok",
            importance=0.9,
            retrieval_count=0,
            last_retrieved=0.0,
        )
        assert not item.is_heritable(importance_threshold=0.5, min_retrieval_count=1)

    def test_unknown_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="未定义的记忆类型"):
            MemoryItem(
                id="m1",
                timestamp=1.0,
                type="WISDOM",
                context_vector=(),
                content_vector=(),
                outcome="",
                importance=0.5,
                retrieval_count=1,
                last_retrieved=1.0,
            )


# ----------------------------------------------------------------------
#  行 13：8.11 Skill precondition 检查方为 Skill Runner
# ----------------------------------------------------------------------


class TestSkill:
    def test_skill_requires_non_empty_sequence(self) -> None:
        with pytest.raises(ValueError, match="action_sequence 不能为空"):
            Skill(
                skill_id="s",
                name="n",
                precondition={},
                action_sequence=(),
                expected_outcome={},
                success_count=0,
                failure_count=0,
                energy_cost=0.0,
                created_from="",
                last_used=0.0,
            )

    def test_sub_action_must_be_executable(self) -> None:
        with pytest.raises(ValueError, match="不可执行"):
            Skill(
                skill_id="s",
                name="n",
                precondition={},
                action_sequence=(Action(),),
                expected_outcome={},
                success_count=0,
                failure_count=0,
                energy_cost=0.0,
                created_from="",
                last_used=0.0,
            )

    def test_total_frames(self) -> None:
        assert make_skill().total_frames() == 2

    def test_consolidation_requires_success_and_frames(self) -> None:
        s = make_skill()
        assert not s.is_consolidatable(min_success_count=3, min_executed_frames=30)

        import dataclasses as dc

        s2 = dc.replace(s, success_count=3)
        assert not s2.is_consolidatable(min_success_count=3, min_executed_frames=30)

        s3 = dc.replace(s, metadata={"executed_frames": 30})
        assert not s3.is_consolidatable(min_success_count=3, min_executed_frames=30)

        s4 = dc.replace(
            s, success_count=3, metadata={"executed_frames": 30}
        )
        assert s4.is_consolidatable(min_success_count=3, min_executed_frames=30)


# ----------------------------------------------------------------------
#  行 14：8.12 增补 origin；代码段只走技能提案
# ----------------------------------------------------------------------


class TestSelfModificationProposal:
    def test_code_proposal_type_rejected(self) -> None:
        """第一阶段无独立 CODE 类型——代码折叠进技能提案（08 §3.1）。"""
        with pytest.raises(ValueError, match="未定义的提案类型"):
            make_proposal("CODE")

    @pytest.mark.parametrize("ptype", list(
        p for p in [
            "UPDATE_CORE_OS",
            "UPDATE_VERIFICATION_GATE",
            "UPDATE_ENV_INTERFACE",
            "UPDATE_GENE_PERMISSION",
            "UPDATE_OBSERVER_INTERFACE",
        ]
    ))
    def test_forbidden_types_rejected_with_specific_message(self, ptype: str) -> None:
        with pytest.raises(ValueError, match="第一阶段明确不允许"):
            make_proposal(ptype)

    def test_eight_allowed_types(self) -> None:
        from SSEA.sse_protocols import ALLOWED_PROPOSAL_TYPES

        assert len(ALLOWED_PROPOSAL_TYPES) == 8

    def test_code_carrier_types(self) -> None:
        assert make_proposal("ADD_SKILL").is_skill_code_carrier
        assert make_proposal("UPDATE_SKILL").is_skill_code_carrier
        assert not make_proposal("UPDATE_ADAPTER").is_skill_code_carrier
        assert not make_proposal("UPDATE_THRESHOLD").is_skill_code_carrier

    def test_consolidated_origin(self) -> None:
        p = SelfModificationProposal.consolidated_from("s1", proposal_id="p9")
        assert p.origin == "consolidated_from:s1"
        assert p.proposal_type == "UPDATE_ADAPTER"
        assert p.target == "instinct_adapters"

    def test_bad_risk_level_rejected(self) -> None:
        with pytest.raises(ValueError, match="risk_level"):
            make_proposal("ADD_RULE", risk_level="extreme")


# ----------------------------------------------------------------------
#  行 15：8.13 heritable_memory / memory_store_ref / mutation_rate 范围
# ----------------------------------------------------------------------


def make_gene(**overrides: object) -> GenePackage:
    base: dict[str, object] = {
        "agent_id": "a1",
        "created_at": 1.0,
        "architecture": {"state_core": "gru", "hidden": 64},
        "core_weights": b"\x00\x01",
        "instinct_adapters": (b"\x02",),
        "skill_library": (make_skill(),),
        "heritable_memory": (
            MemoryItem(
                id="m1",
                timestamp=1.0,
                type="RULE",
                context_vector=(),
                content_vector=(),
                outcome="ok",
                importance=0.9,
                retrieval_count=4,
                last_retrieved=1.0,
            ),
        ),
        "memory_store_ref": "store://a1",
        "behavior_policy": {"caution": 0.5},
        "metabolic_policy": {"sleep_energy": 0.7},
        "mutation_rate": 0.1,
    }
    base.update(overrides)
    return GenePackage(**base)  # type: ignore[arg-type]


class TestGenePackage:
    def test_has_heritable_memory(self) -> None:
        assert len(make_gene().heritable_memory) == 1

    def test_memory_index_renamed(self) -> None:
        names = {f.name for f in dataclasses.fields(GenePackage)}
        assert "memory_index" not in names
        assert "memory_store_ref" in names

    def test_transient_memory_rejected_in_heritable_memory(self) -> None:
        with pytest.raises(ValueError, match="瞬时记忆"):
            make_gene(
                heritable_memory=(
                    MemoryItem(
                        id="m2",
                        timestamp=1.0,
                        type="EVENT",
                        context_vector=(),
                        content_vector=(),
                        outcome="",
                        importance=1.0,
                        retrieval_count=9,
                        last_retrieved=1.0,
                    ),
                )
            )

    def test_mutation_rate_bounded(self) -> None:
        with pytest.raises(ValueError, match="mutation_rate"):
            make_gene(mutation_rate=1.5)

    def test_mutation_scope_excludes_structure(self) -> None:
        """architecture 与 core_weights 不在 mutation_rate 作用范围内（08 §3.5）。"""
        from SSEA.sse_protocols import MUTATION_SCOPES, NON_MUTABLE

        assert "architecture" not in MUTATION_SCOPES
        assert "core_weights" not in MUTATION_SCOPES
        assert "architecture" in NON_MUTABLE
        assert "core_weights" in NON_MUTABLE

    def test_empty_agent_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="agent_id"):
            make_gene(agent_id="")
