"""Milestone 1 测试：协议层自洽性。

前两个文件测「修订是否落地」。本文件测「协议本身是否自洽」——
字段引用的类型是否都存在、每个协议的字段是否与 07 §8 原文对齐、
模块导入图是否无环。

这类检查的价值在后续：每加一个协议或改一个字段，本文件立刻指出破坏点。
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
import pkgutil
import re
from typing import get_args, get_type_hints

import pytest

import SSEA.sse_protocols as pkg
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
    MemoryItem,
    Observation,
    ObjectVector,
    SelfModificationProposal,
    Skill,
    StructureStore,
)


# ----------------------------------------------------------------------
#  协议字段与 07 §8 原文逐节对齐
# ----------------------------------------------------------------------


#: 07 §8 各协议应有的字段集合。这是 Milestone 1 的验收基线：
#: 08 的修订只**删除或新增**特定字段，其余字段必须与原文一致。
EXPECTED_FIELDS: dict[type, frozenset[str]] = {
    # 8.2 BodyState
    BodyState: frozenset(
        {
            "energy",
            "damage",
            "fatigue",
            "position",
            "orientation",
            "action_constraints",
            "internal_state",
        }
    ),
    # 8.3 ActionConstraints
    ActionConstraints: frozenset(
        {
            "max_speed",
            "max_force",
            "max_duration",
            "allowed_operations",
            "forbidden_targets",
            "energy_budget",
            "can_communicate",
            "can_store_memory",
            "can_call_skill",
            "can_self_modify",
        }
    ),
    # 8.5 Action —— 已删除 latent_action
    Action: frozenset(
        {
            "locomotion",
            "manipulation",
            "communication",
            "memory",
            "skill",
            "self_modification",
        }
    ),
    # 8.6 ObjectVector
    ObjectVector: frozenset(
        {
            "object_id",
            "category_id",
            "distance",
            "direction",
            "velocity",
            "resource_value",
            "threat_level",
            "affordance",
        }
    ),
    # 8.7 EventVector
    EventVector: frozenset(
        {
            "event_id",
            "timestamp",
            "event_type",
            "source_id",
            "context_vector",
            "importance",
        }
    ),
    # 8.8 CommunicationSignal
    CommunicationSignal: frozenset(
        {
            "sender_id",
            "receiver_id",
            "signal",
            "timestamp",
            "priority",
        }
    ),
    # 8.9 Feedback
    Feedback: frozenset(
        {
            "energy_change",
            "damage_change",
            "fatigue_change",
            "prediction_error",
            "action_success",
            "survived",
            "notes",
        }
    ),
    # 8.10 MemoryItem
    MemoryItem: frozenset(
        {
            "id",
            "timestamp",
            "type",
            "context_vector",
            "content_vector",
            "outcome",
            "importance",
            "retrieval_count",
            "last_retrieved",
        }
    ),
    # 8.11 Skill —— 07 原文 10 字段 + metadata（08 未要求新增，见下）
    Skill: frozenset(
        {
            "skill_id",
            "name",
            "precondition",
            "action_sequence",
            "expected_outcome",
            "success_count",
            "failure_count",
            "energy_cost",
            "created_from",
            "last_used",
            "metadata",
        }
    ),
    # 8.12 SelfModificationProposal —— 07 原文 7 字段 + origin
    SelfModificationProposal: frozenset(
        {
            "proposal_id",
            "proposal_type",
            "target",
            "payload",
            "reason",
            "expected_effect",
            "risk_level",
            "origin",
        }
    ),
    # 8.13 GenePackage —— 08 修订后
    GenePackage: frozenset(
        {
            "agent_id",
            "created_at",
            "architecture",
            "core_weights",
            "instinct_adapters",
            "skill_library",
            "heritable_memory",
            "memory_store_ref",
            "behavior_policy",
            "metabolic_policy",
            "mutation_rate",
        }
    ),
    # 8.1 Observation
    Observation: frozenset(
        {
            "time",
            "body",
            "environment",
            "objects",
            "events",
            "social_signals",
        }
    ),
    # 05 §7.3 EnvironmentSummary
    EnvironmentSummary: frozenset(
        {
            "light_level",
            "temperature",
            "danger_level",
            "resource_density",
            "time_phase",
        }
    ),
}


class TestProtocolFieldsMatchCharter:
    @pytest.mark.parametrize("cls", list(EXPECTED_FIELDS))
    def test_fields_exactly_match(self, cls: type) -> None:
        actual = frozenset(f.name for f in dataclasses.fields(cls))
        expected = EXPECTED_FIELDS[cls]
        missing = expected - actual
        extra = actual - expected
        assert not missing, f"{cls.__name__} 缺少字段: {sorted(missing)}"
        assert not extra, f"{cls.__name__} 多出未登记字段: {sorted(extra)}"


# ----------------------------------------------------------------------
#  协议引用闭包：字段类型必须可解析
# ----------------------------------------------------------------------


class TestTypeReferencesResolve:
    """每个协议字段标注的类型必须能解析，且引用的协议类确实存在。

    这条测试抓的是"协议引用了一个不存在的类型"——dict 记法时代这类错误
    无声无息，dataclass 时代至少能在此处暴露。
    """

    PROTOCOL_CLASSES = [
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
        MemoryItem,
        Observation,
        ObjectVector,
        SelfModificationProposal,
        Skill,
        StructureStore,
    ]

    @pytest.mark.parametrize("cls", PROTOCOL_CLASSES)
    def test_annotations_resolve(self, cls: type) -> None:
        if not dataclasses.is_dataclass(cls):
            pytest.skip(f"{cls.__name__} 不是 dataclass")
        try:
            hints = get_type_hints(cls)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"{cls.__name__} 类型标注无法解析: {exc}")
        assert hints, f"{cls.__name__} 无可解析的类型标注"

    def test_action_references_only_known_channels(self) -> None:
        """Action 的每个通道字段都是已登记通道，且类型是已定义的子协议。"""
        for f in dataclasses.fields(Action):
            assert f.name in Action.CHANNELS

    def test_gene_references_skill_and_memory(self) -> None:
        gfields = {f.name for f in dataclasses.fields(GenePackage)}
        assert "skill_library" in gfields
        assert "heritable_memory" in gfields


# ----------------------------------------------------------------------
#  模块导入图无环
# ----------------------------------------------------------------------


class TestModuleGraph:
    def test_all_modules_importable(self) -> None:
        mods = [
            m.name
            for m in pkgutil.iter_modules(pkg.__path__)
            if not m.name.startswith("_")
        ]
        assert len(mods) >= 15, f"协议模块数量异常: {len(mods)}"
        for name in mods:
            importlib.import_module(f"SSEA.sse_protocols.{name}")

    def test_no_circular_import(self) -> None:
        """重新导入整个包不应触发循环导入。

        structure_store 在 snapshot() 内延迟导入 fast_loop_context，
        fast_loop_context 导入 skill —— 这条边是本设计唯一的反向依赖。
        """
        importlib.reload(pkg)
        assert hasattr(pkg, "StructureStore")
        assert hasattr(pkg, "FastLoopContext")

    def test_lazy_import_documented(self) -> None:
        """确认延迟导入确实存在（而非偶然）。"""
        src = inspect.getsource(StructureStore.snapshot)
        assert "import" in src


# ----------------------------------------------------------------------
#  三分离：协议中不存在裸梯度
# ----------------------------------------------------------------------


class TestNoRawGradients:
    def test_proposal_kinds_are_five(self) -> None:
        """注入物五类，严格落在三分离内（08 §2.1）。"""
        from SSEA.sse_protocols import STRUCTURE_KINDS

        assert STRUCTURE_KINDS == (
            "skills",
            "rules",
            "adapters",
            "thresholds",
            "retrieval",
        )

    def test_every_proposal_type_maps_to_exactly_one_kind(self) -> None:
        from SSEA.sse_protocols import (
            ALLOWED_PROPOSAL_TYPES,
            PROPOSAL_KIND_MAP,
        )

        assert set(ALLOWED_PROPOSAL_TYPES) == set(PROPOSAL_KIND_MAP)
        assert len(set(PROPOSAL_KIND_MAP.values())) == 5

    def test_no_gradient_or_weight_field_on_proposal(self) -> None:
        names = {f.name for f in dataclasses.fields(SelfModificationProposal)}
        assert not any(
            "grad" in n or "weight" in n or "delta" in n for n in names
        ), "提案不得携带裸梯度/权重增量——学习产物必须是五类结构之一"


# ----------------------------------------------------------------------
#  自然语言不进控制闭环
# ----------------------------------------------------------------------


class TestNoNaturalLanguageInLoop:
    def test_observation_has_no_text_field(self) -> None:
        names = {f.name for f in dataclasses.fields(Observation)}
        assert not any(
            n in ("text", "description", "language", "prompt", "tokens")
            for n in names
        )

    def test_action_has_no_string_command_field(self) -> None:
        """env.step(command: str) 不被允许（07 §7.1）。"""
        names = {f.name for f in dataclasses.fields(Action)}
        assert not any(
            n in ("command", "text", "utterance", "instruction") for n in names
        )

    def test_notes_is_the_only_free_text_field(self) -> None:
        """协议中不存在承载人类语言正文的字段。

        str 字段只允许是**标识符**（id / type / event_type / source_id）与
        结果标记（outcome），加上 Feedback.notes 这一个调试用自由文本——
        后者是 07 §8.9 原文字段，且不进控制闭环（07 §7.2：调试输出可用
        自然语言，但不参与感知输入 / 动作输出 / 身体控制 / 实时闭环）。
        """
        text_fields: dict[str, str] = {}
        for cls in (Observation, Feedback, EventVector, MemoryItem):
            hints = get_type_hints(cls)
            for name, hint in hints.items():
                if hint is str:
                    text_fields[f"{cls.__name__}.{name}"] = "str"

        assert set(text_fields) == {
            "EventVector.event_id",
            "EventVector.event_type",
            "EventVector.source_id",
            "MemoryItem.id",
            "MemoryItem.type",
            "MemoryItem.outcome",
            "Feedback.notes",
        }

    def test_no_field_name_suggests_prose(self) -> None:
        """没有字段名暗示"这里放一段话"。

        用词边界匹配而非裸子串——否则 ``context_vector`` 会被
        "con**text**_vector" 误判。
        """
        banned = (
            "text",
            "description",
            "message",
            "utterance",
            "sentence",
            "paragraph",
            "explanation",
            "rationale",
            "prompt",
            "token",
            "language",
        )
        pattern = re.compile(r"\b(" + "|".join(banned) + r")\b", re.IGNORECASE)
        for cls in (Observation, Feedback, EventVector, MemoryItem, Action):
            for f in dataclasses.fields(cls):
                assert not pattern.search(f.name), (
                    f"{cls.__name__}.{f.name} 疑似自然语言字段"
                )

    def test_action_channels_have_no_unaccounted_text_field(self) -> None:
        """``Action`` 六个通道**内部**的 str 字段必须逐个登记。

        这条补的是一个**守卫缺口**，不是修一个违规。上面三条检查的覆盖面是：

        - ``test_notes_is_the_only_free_text_field`` 的类集合是
          ``Observation, Feedback, EventVector, MemoryItem``——**没有 Action**。
        - ``test_action_has_no_string_command_field`` 只查 ``Action`` 的
          **顶层**字段名（六个通道名），通道**内部**一个都没查。

        于是 ``Manipulation.operation`` 这类字段从来没被任何检查看过一眼。
        它们实际装的确实是名字（对象 id、操作码），所以**不是违规**；
        但"没人检查过"与"检查过没问题"是两件事。

        下表的用途是让**新增**一个 str 字段变成一次显式决定，
        而不是悄悄溜过去。
        """

        # 通道字段是 ``X | None``（本次实测：直接 is_dataclass 判不出来，
        # 会得到空列表然后"前提失效"——这个断言先于结论报了警）。
        action_hints = get_type_hints(Action)
        channel_types = []
        for f in dataclasses.fields(Action):
            hint = action_hints[f.name]
            inner = [a for a in get_args(hint) if a is not type(None)]
            candidate = inner[0] if inner else hint
            assert dataclasses.is_dataclass(candidate), (
                f"Action.{f.name} 不再是通道结构: {hint}"
            )
            channel_types.append(candidate)

        found: set[str] = set()
        for channel in channel_types:
            for name, hint in get_type_hints(channel).items():
                if hint is str:
                    found.add(f"{channel.__name__}.{name}")

        assert found == {
            # 对象 id / 空串表示无目标 —— 名字
            "Manipulation.target_id",
            "Communication.target_id",
            "SkillCall.skill_id",
            # 操作码与提案类型 —— **名字，且约定取自闭集**
            "Manipulation.operation",
            "SelfModification.proposal_type",
        }, f"Action 通道内出现了未登记的 str 字段: {sorted(found)}"

    def test_opcode_fields_are_convention_bound_not_type_bound(self) -> None:
        """记一笔已知的弱点：操作码字段**类型上不受约束**。

        ``Manipulation.operation`` 与 ``SelfModification.proposal_type``
        都只是 ``str``，只在 docstring 里约定"取值见 ``OPERATIONS`` /
        ``ALLOWED_PROPOSAL_TYPES``"。协议层**没有**运行时校验：

        >>> Manipulation(target_id="o1", operation="把那个东西拿过来", ...)
        是能构造出来的。

        这不是当前的实际风险——写出这两个字段的是 ActionDecoder 与
        LocalPlasticity，它们只从闭集里取。真正的守卫是**运行时**的：
        ``experiments/_harness.py::count_strs_deep`` 在跑起来之后逐帧
        检查这两个字段的值有没有落在闭集里，实测 637 帧 0 次越界。

        本测试固化的是"当前不受约束"这一事实，让将来某次收紧成
        ``Literal[...]`` 或 ``__post_init__`` 校验时有人会注意到这里，
        而不是让这个弱点在文档里烂掉。
        """

        from SSEA.sse_protocols.action import Manipulation
        from SSEA.sse_protocols.action_space import OPERATIONS
        from SSEA.sse_protocols.self_modification import ALLOWED_PROPOSAL_TYPES

        hints = get_type_hints(Manipulation)
        assert hints["operation"] is str, (
            "operation 已不再是裸 str——若已收紧为 Literal/枚举，"
            "请删掉本测试并更新 experiments/README.md 的守卫缺口一节"
        )
        # 闭集本身必须存在且非空，否则"取自闭集"是句空话。
        assert OPERATIONS and ALLOWED_PROPOSAL_TYPES
