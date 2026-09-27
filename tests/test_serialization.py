"""Milestone 1 测试：协议可序列化为 JSON。

**验收依据**：docs/07-ssea-v0.3.1-charter.md §11 Milestone 1 三条验收：

    1. 所有接口可序列化为 JSON。
    2. 所有接口不依赖具体模型实现。
    3. 环境不接受自然语言命令。

第 1 条由本文件覆盖；第 2 条见 test_protocol_consistency.py 的
``TestNoModelDependency``；第 3 条见 ``TestNoNaturalLanguageInLoop``。
"""

from __future__ import annotations

import json

import pytest

from SSEA.sse_protocols import (
    Action,
    ActionConstraints,
    ActionSpace,
    BodyState,
    CommunicationSignal,
    EnvironmentSummary,
    EventVector,
    FastLoopContext,
    Feedback,
    GenePackage,
    Locomotion,
    Manipulation,
    MemoryItem,
    MemoryWrite,
    Observation,
    ObjectVector,
    SelfModificationProposal,
    Skill,
    SkillCall,
    StructureStore,
    default_action_space,
    default_constraints,
    from_json_dict,
    idle_action,
    roundtrip,
    to_json_dict,
)


# ----------------------------------------------------------------------
#  fixtures：每个协议造一个"全字段非空"的实例
# ----------------------------------------------------------------------


def make_action() -> Action:
    return Action(
        locomotion=Locomotion(direction=(1.0, 0.0), speed=0.5, duration=0.1),
        manipulation=Manipulation(
            target_id="obj1", operation="grasp", force=0.3, duration=0.1
        ),
        memory=MemoryWrite(store=True, content=(0.1, 0.2), importance=0.6),
        skill=SkillCall(skill_id="s1", params={"k": 1}),
    )


def make_skill(skill_id: str = "s1") -> Skill:
    return Skill(
        skill_id=skill_id,
        name="forage",
        precondition={"min_energy": 0.2},
        action_sequence=(make_action(), make_action()),
        expected_outcome={"energy_gain": 0.1},
        success_count=3,
        failure_count=1,
        energy_cost=0.05,
        created_from="trace-1",
        last_used=12.5,
        metadata={"origin": "compiled", "executed_frames": 40},
    )


def make_gene() -> GenePackage:
    return GenePackage(
        agent_id="a1",
        created_at=1.0,
        architecture={"state_core": "gru", "hidden": 64},
        core_weights=b"\x00\x01\x02",
        instinct_adapters=(b"\x03\x04",),
        skill_library=(make_skill(),),
        heritable_memory=(
            MemoryItem(
                id="m1",
                timestamp=1.0,
                type="RULE",
                context_vector=(0.1,),
                content_vector=(0.2,),
                outcome="ok",
                importance=0.9,
                retrieval_count=4,
                last_retrieved=1.0,
            ),
        ),
        memory_store_ref="store://a1",
        behavior_policy={"caution": 0.5},
        metabolic_policy={"sleep_energy": 0.7},
        mutation_rate=0.1,
    )


def make_observation() -> Observation:
    return Observation(
        time=3.0,
        body=BodyState(
            energy=0.6,
            damage=0.0,
            fatigue=0.2,
            position=(1.0, 2.0),
            orientation=(0.0, 1.0),
            action_constraints=default_constraints(),
            internal_state=(0.1, 0.2),
        ),
        environment=EnvironmentSummary(
            light_level=0.5,
            temperature=0.4,
            danger_level=0.1,
            resource_density=0.3,
            time_phase="day",
        ),
        objects=(
            ObjectVector(
                object_id="o1",
                category_id=2,
                distance=1.5,
                direction=(1.0, 0.0),
                velocity=(0.0, 0.0),
                resource_value=0.8,
                threat_level=0.0,
                affordance=(1.0, 0.0),
            ),
        ),
        events=(
            EventVector(
                event_id="e1",
                timestamp=3.0,
                event_type="OBJECT_FOUND",
                source_id="o1",
                context_vector=(0.5,),
                importance=0.4,
            ),
        ),
        social_signals=(
            CommunicationSignal(
                sender_id="a1",
                receiver_id="a2",
                signal=(0.1, 0.2),
                timestamp=3.0,
                priority=1,
            ),
        ),
    )


def make_feedback() -> Feedback:
    return Feedback(
        energy_change=-0.1,
        damage_change=0.0,
        fatigue_change=0.05,
        prediction_error=0.12,
        action_success=True,
        survived=True,
        notes="debug",
    )


def make_proposal() -> SelfModificationProposal:
    return SelfModificationProposal(
        proposal_id="p1",
        proposal_type="ADD_SKILL",
        target="s1",
        payload={"skill": make_skill(), "nested": {"a": [1, 2, 3]}},
        reason="从 trace 编译",
        expected_effect={"success_rate": 0.7},
        risk_level="medium",
        origin="compiled_from:trace-1",
    )


#: 全部 Milestone 1 交付的协议实例。
ALL_PROTOCOLS = {
    "Action": make_action(),
    "ActionConstraints": default_constraints(),
    "ActionSpace": default_action_space(),
    "Observation": make_observation(),
    "Feedback": make_feedback(),
    "MemoryItem": make_gene().heritable_memory[0],
    "Skill": make_skill(),
    "SelfModificationProposal": make_proposal(),
    "GenePackage": make_gene(),
    "BodyState": make_observation().body,
    "ObjectVector": make_observation().objects[0],
    "EventVector": make_observation().events[0],
    "CommunicationSignal": make_observation().social_signals[0],
    "EnvironmentSummary": make_observation().environment,
    "idle_action": idle_action(),
}


class TestJsonRoundtrip:
    @pytest.mark.parametrize("name,obj", list(ALL_PROTOCOLS.items()))
    def test_roundtrip_preserves_equality(self, name: str, obj: object) -> None:
        """JSON 往返后对象相等。

        这是 Milestone 1 验收第 1 条的直接判定。
        """
        back = roundtrip(obj)
        assert back == obj, f"{name} 往返后不等"

    @pytest.mark.parametrize("name,obj", list(ALL_PROTOCOLS.items()))
    def test_to_json_dict_is_json_dumpable(self, name: str, obj: object) -> None:
        json.dumps(to_json_dict(obj))  # 不抛异常即可

    @pytest.mark.parametrize("name,obj", list(ALL_PROTOCOLS.items()))
    def test_from_json_dict_reconstructs_type(
        self, name: str, obj: object
    ) -> None:
        data = json.loads(json.dumps(to_json_dict(obj)))
        back = from_json_dict(type(obj), data)
        assert type(back) is type(obj)


class TestBytesHandling:
    def test_bytes_roundtrip(self) -> None:
        g = roundtrip(make_gene())
        assert g.core_weights == b"\x00\x01\x02"
        assert g.instinct_adapters == (b"\x03\x04",)

    def test_bytes_wrapped_not_bare(self) -> None:
        d = to_json_dict(make_gene())
        assert isinstance(d["core_weights"], dict)
        assert set(d["core_weights"]) == {"__bytes__"}

    def test_bytes_distinguishable_from_str(self) -> None:
        """bytes 与 str 在 JSON 中可区分——这是包装而非裸 base64 的理由。"""
        from SSEA.sse_protocols import from_json_dict

        # 一个恰好长得像 base64 的 str 不会被误认为 bytes
        class _Holder:
            pass

        # 通过 GenePackage.memory_store_ref（str）与 core_weights（bytes）对照
        d = to_json_dict(make_gene())
        assert isinstance(d["memory_store_ref"], str)
        assert isinstance(d["core_weights"], dict)


class TestNestedStructures:
    def test_nested_skill_in_proposal_payload(self) -> None:
        p = roundtrip(make_proposal())
        assert isinstance(p.payload["skill"], Skill)
        assert p.payload["skill"].skill_id == "s1"
        assert p.payload["nested"] == {"a": [1, 2, 3]}

    def test_observation_nested_graph(self) -> None:
        o = roundtrip(make_observation())
        assert isinstance(o.body, BodyState)
        assert isinstance(o.body.action_constraints, ActionConstraints)
        assert isinstance(o.objects[0], ObjectVector)
        assert isinstance(o.events[0], EventVector)
        assert isinstance(o.social_signals[0], CommunicationSignal)
        assert o.objects[0].direction == (1.0, 0.0)

    def test_tuples_come_back_as_tuples(self) -> None:
        """协议用 tuple，往返后仍是 tuple，不退化成 list。"""
        o = roundtrip(make_observation())
        assert isinstance(o.body.position, tuple)
        assert isinstance(o.objects[0].direction, tuple)
        g = roundtrip(make_gene())
        assert isinstance(g.instinct_adapters, tuple)
        assert isinstance(g.skill_library, tuple)
        assert isinstance(g.heritable_memory, tuple)

    def test_mapping_becomes_dict(self) -> None:
        store = StructureStore(
            initial={"retrieval": {"default": {"top_k": 4}}}
        )
        ctx = store.snapshot()
        back = roundtrip(ctx)
        assert isinstance(back, FastLoopContext)
        assert back.retrieval == {"default": {"top_k": 4}}
        assert back.versions == ctx.versions

    def test_empty_containers(self) -> None:
        store = StructureStore()
        ctx = store.snapshot()
        back = roundtrip(ctx)
        assert back == ctx
        assert back.skills == {}
        assert back.adapters == {}


class TestNoModelDependency:
    """Milestone 1 验收第 2 条：所有接口不依赖具体模型实现。

    注意扫描范围是 ``sse_protocols/`` 而**不是**整个 ``SSEA/``。协议层
    不得依赖模型库；模型层（state_core / action_decoder / ...）本来就该
    依赖 torch。这条边界由下面两个测试共同守住。
    """

    def test_protocol_layer_imports_no_ml_libs(self) -> None:
        """协议层只依赖标准库。"""
        import pathlib

        banned = ("torch", "numpy", "tensorflow", "jax", "sklearn")
        offenders = []
        for path in (pathlib.Path("SSEA") / "sse_protocols").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for lib in banned:
                if f"import {lib}" in text or f"from {lib}" in text:
                    offenders.append(f"{path}: {lib}")
        assert not offenders, f"协议层不得依赖模型库: {offenders}"

    def test_model_layer_does_import_torch(self) -> None:
        """反向守卫：模型层确实在协议层之外。

        若有人把 torch 挪进协议层，上一条会失败；若有人把模型代码搬进
        ``sse_protocols/``，这一条会失败。两边都跑才算边界清楚。
        """

        import pathlib

        model_modules = (
            "state_core.py",
            "action_decoder.py",
            "perception_encoder.py",
            "fast_loop.py",
        )
        root = pathlib.Path("SSEA")
        for name in model_modules:
            path = root / name
            assert path.exists(), f"模型模块 {name} 应位于协议层之外"
            text = path.read_text(encoding="utf-8")
            assert "import torch" in text, f"{name} 应依赖 torch"

    def test_core_weights_is_opaque_bytes(self) -> None:
        """基因包不绑定张量格式——core_weights 是不透明 bytes。"""
        g = make_gene()
        assert isinstance(g.core_weights, bytes)
        assert isinstance(g.instinct_adapters[0], bytes)

    def test_action_space_has_no_learnable_params(self) -> None:
        """ActionSpace 只声明维度与取值，不持有可学习参数。"""
        space = default_action_space()
        for value in list(space.continuous_dims.values()) + [
            v for vs in space.discrete_values.values() for v in vs
        ]:
            assert isinstance(value, (int, str))


class TestEnvironmentRejectsNaturalLanguage:
    """Milestone 1 验收第 3 条：环境不接受自然语言命令。

    协议层无法阻止有人写 ``env.step("向前走")``，但可以保证
    Action 上不存在承载命令的字符串字段——见
    test_protocol_consistency.TestNoNaturalLanguageInLoop。
    """

    def test_action_has_no_command_field(self) -> None:
        import dataclasses

        names = {f.name for f in dataclasses.fields(Action)}
        assert not names & {"command", "text", "instruction", "utterance"}

    def test_action_requires_structured_channels(self) -> None:
        assert Action().is_executable() is False
        assert idle_action().is_executable() is True
