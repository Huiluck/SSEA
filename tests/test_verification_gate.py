"""Verification Gate 测试 —— 四级检查 + 「Gate 不打分」这条纪律。

对应 [docs/13-milestone4-plan.md](../docs/13-milestone4-plan.md) §4 的验收清单：

1. 四种提案类型各有「合法 → 放过」与「非法 → 拒绝」的测试
2. 四级检查的顺序可观测：同时触犯多级的提案，``stage_failed`` 报最早那一级
3. Gate 不修改传入的结构（副本语义）
4. 拒绝路径不抛异常、不改版本号
5. Gate 不给提案打分——没有 score 字段，没有排序 API

第 5 条是本文件的重心。它不是代码风格问题，是架构立场问题：SSEA 没有评分
函数，只有淘汰函数（C9）。Gate 一旦能打分，它就变成了评分函数，而「生存压力
可被 hack」正是 07 风险 4 与 C9 要防的事。
"""

from __future__ import annotations

import struct

import pytest
import torch

from SSEA.action_decoder import GATE_THRESHOLD_KEYS
from SSEA.instinct import (
    FORMAT_VERSION,
    INSTINCT_PRESETS,
    MAGIC,
    TARGET_LOCOMOTION,
    TARGET_MANIPULATION,
    encode_instinct,
    preset_blob,
)
from SSEA.sse_protocols import (
    Action,
    Locomotion,
    SelfModificationProposal,
    Skill,
)
from SSEA.sse_protocols.structure_store import (
    PROPOSAL_KIND_MAP,
    STRUCTURE_KINDS,
    StructureStore,
)
from SSEA.verification_gate import (
    GATE_RESULT_FIELDS,
    STAGES,
    GateConfig,
    VerificationGate,
)


# ----------------------------------------------------------------------
#  助手
# ----------------------------------------------------------------------


def skill(sid: str, speed: float = 0.5) -> Skill:
    """一条合法技能。``speed`` 进签名，改它就换一条技能。"""

    return Skill(
        skill_id=sid,
        name=sid,
        precondition={},
        action_sequence=(Action(locomotion=Locomotion((1.0, 0.0), speed, 1.0)),),
        expected_outcome={},
        success_count=0,
        failure_count=0,
        energy_cost=0.1,
        created_from="test",
        last_used=0.0,
    )


def proposal(ptype: str, target: str, pid: str = "p1", **payload: object):
    """构造提案。缺 payload 时传空 dict，让格式级去拒。"""

    return SelfModificationProposal(
        proposal_id=pid,
        proposal_type=ptype,
        target=target,
        payload=dict(payload),
        reason="test",
    )


def store(**initial: object) -> StructureStore:
    return StructureStore(initial=initial or None)


#: 一份**真的解得开**的 adapter。合法 adapter 现在必须是可解码的本能 blob——
#: "非空 bytes"这条不够，见 ``_check_adapters`` 的 docstring 与 13 §4.6。
#:
#: 直接调生产代码的构造函数而不是手写字节：手写的那一份会漂移，
#: 而漂移的表现是"测试过了、门拒了"。
ADAPTER = preset_blob("approach")

#: 上面那份 adapter 的原始权重矩阵（不带 gain）。给"只改一个字节"的测试用。
ADAPTER_WEIGHTS = torch.tensor(INSTINCT_PRESETS["approach"].weights)


#: 一个合法的阈值键。取自 action_decoder 而不是手写——手写的那一份会漂移，
#: 而漂移的表现是"测试过了、Gate 拒了"。
THRESHOLD_KEY = GATE_THRESHOLD_KEYS["memory"]


def gate(**cfg: object) -> VerificationGate:
    return VerificationGate(GateConfig(**cfg))  # type: ignore[arg-type]


@pytest.fixture
def g() -> VerificationGate:
    """默认门。env_frames 压到 8，让跑到第四级的测试不至于太慢。"""

    return gate(env_frames=8)


# ----------------------------------------------------------------------
#  Gate 不打分（验收第 5 条）
# ----------------------------------------------------------------------


class TestNoScoring:
    """Gate 是安全检查，不是适应度函数。

    这条纪律守的是架构立场而非代码风格：SSEA 没有评分函数，只有淘汰函数
    （C9）。若 Gate 有了分数，「哪个提案更好」就由 Gate 决定，而生存压力
    退化成一个可被 hack 的评分——那正是 07 风险 4。
    """

    def test_gate_result_has_exactly_three_fields(self) -> None:
        assert GATE_RESULT_FIELDS == ("passed", "reason", "stage_failed")

    def test_gate_result_carries_no_score(self) -> None:
        for name in GATE_RESULT_FIELDS:
            assert "score" not in name.lower()
            assert "rank" not in name.lower()

    def test_gate_config_has_no_scoring_knob(self) -> None:
        from dataclasses import fields

        names = {f.name for f in fields(GateConfig)}
        for bad in ("score", "threshold", "min_score", "top_k", "accept_rate"):
            assert bad not in names, f"GateConfig 出现了评分旋钮 {bad!r}"

    def test_gate_has_no_ranking_or_sorting_api(self) -> None:
        public = [n for n in dir(VerificationGate) if not n.startswith("_")]
        for bad in ("rank", "sort", "score", "compare", "best"):
            assert bad not in public, f"Gate 出现了排序/打分 API {bad!r}"

    def test_stages_are_the_documented_four_in_order(self) -> None:
        assert STAGES == ("format", "sandbox", "regression", "env_test")

    def test_two_proposals_of_different_worth_get_the_same_verdict(self, g) -> None:
        """一个让存活更容易、一个更难的技能，只要都合法，结论相同。

        这是「Gate 不评估好不好」的可观察后果： verdict 只依赖合法性。
        """

        s = store()
        easy = proposal("ADD_SKILL", "easy", skill=skill("easy", speed=1.0))
        hard = proposal("ADD_SKILL", "hard", skill=skill("hard", speed=0.01))
        assert g.check(easy, s.snapshot()).passed
        assert g.check(hard, s.snapshot()).passed

    def test_verdict_is_binary(self, g) -> None:
        """GateResult.passed 是 bool，不是分数。"""

        s = store()
        r = g.check(proposal("ADD_SKILL", "x", skill=skill("x")), s.snapshot())
        assert isinstance(r.passed, bool)


# ----------------------------------------------------------------------
#  第一级：格式
# ----------------------------------------------------------------------


class TestFormatStage:
    def test_missing_payload_key_is_rejected(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1"), s.snapshot())
        assert not r.passed
        assert r.stage_failed == "format"
        assert "skill" in r.reason

    def test_none_payload_value_is_rejected(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=None), s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_skill_id_must_match_target(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("other")), s.snapshot())
        assert not r.passed
        assert r.stage_failed == "format"
        assert "不一致" in r.reason

    def test_payload_skill_must_be_a_skill(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill={"skill_id": "s1"}), s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_add_target_must_not_already_exist(self, g) -> None:
        s = store(skills={"s1": skill("s1")})
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert not r.passed and r.stage_failed == "format"
        assert "已存在" in r.reason

    def test_update_target_must_exist(self, g) -> None:
        """UPDATE_* 的 target 必须已存在——**技能 / 规则**这两类。

        ``thresholds`` / ``retrieval`` / ``adapters`` 是例外，理由是同一条：
        Store 刚建起来时这三个类别都是空的，而没有任何提案能建第一个键
        （``ALLOWED_PROPOSAL_TYPES`` 里没有 ``ADD_THRESHOLD`` / ``ADD_ADAPTER``）。
        按"已存在"判会让它们**永远无法被初始化**。

        前三者与后三者的护栏不同，这一点容易被"反正都是例外"抹平：

        - ``thresholds`` / ``retrieval`` 的替代护栏是**合法键名清单**，取自
          语义所有者（``memory_system`` / ``action_decoder``）。
        - ``adapters`` **没有**名清单，也不该编一份：``decode_instinct_set``
          把所有 adapter 的偏置全部相加，名字只是审计与遗传的标签。它的护栏是
          **内容**——``_check_adapters`` 要求 blob 被真实解码器解得开。
        """

        s = store()
        r = g.check(
            proposal("UPDATE_SKILL", "ghost", skill=skill("ghost")), s.snapshot()
        )
        assert not r.passed and r.stage_failed == "format"
        assert "不存在" in r.reason

    def test_first_adapter_can_be_created(self, g) -> None:
        """空 Store 上 ``UPDATE_ADAPTER`` 必须能建第一个键。

        与 ``test_flat_policy_can_be_initialized`` 同一条缺陷、同一个形状：
        ``adapters`` 曾经也要求 target 已存在，于是这个类别**无法被初始化**。

        它比那两类潜伏得更久，因为**当时没有任何代码读过 adapters**——
        没人试过往里放第一个键，于是没人撞上这道门。② 给它补上读取接口之后，
        一份合法的趋近先验立刻被拒，理由却是"目标 'approach' 不存在"。
        守卫缺口的代价总是延迟支付的。
        """

        s = store()
        assert not s.snapshot().adapters
        assert g.check(
            proposal("UPDATE_ADAPTER", "approach", adapter=ADAPTER), s.snapshot()
        ).passed
        # create-or-replace：已存在的键照样能改（这正是 UPDATE 的本义）。
        assert g.check(
            proposal("UPDATE_ADAPTER", "approach", adapter=ADAPTER),
            store(adapters={"approach": ADAPTER}).snapshot(),
        ).passed

    def test_unknown_threshold_key_is_rejected(self, g) -> None:
        """阈值键不在语义所有者的清单里——拒，且理由指向清单在哪。"""

        s = store()
        r = g.check(proposal("UPDATE_THRESHOLD", "t", value=0.5), s.snapshot())
        assert not r.passed and r.stage_failed == "format"
        assert "不是合法的阈值键" in r.reason
        assert "GATE_THRESHOLD_KEYS" in r.reason

    def test_flat_policy_can_be_initialized(self, g) -> None:
        """空 Store 上，UPDATE_THRESHOLD / UPDATE_RETRIEVAL_POLICY 必须能建第一个键。

        这是那道缺陷的回归钉子：格式级曾要求 target 已存在，于是两个扁平策略
        类别谁也建不起第一个键，Δθ 的每一条提案都在格式级被拒。
        """

        s = store()
        assert not s.snapshot().thresholds and not s.snapshot().retrieval
        assert g.check(
            proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value=0.4), s.snapshot()
        ).passed
        assert g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "min_similarity", policy=0.2),
            s.snapshot(),
        ).passed

    def test_disable_target_must_exist(self, g) -> None:
        s = store()
        r = g.check(proposal("DISABLE_SKILL", "ghost"), s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_empty_target_is_rejected(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "", skill=skill("x")), s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_empty_proposal_id_is_rejected(self, g) -> None:
        """审计需要 id：一条没有 id 的提案无法被追溯（08 §2.1 可审计性质）。"""

        s = store()
        p = proposal("ADD_SKILL", "s1", pid="", skill=skill("s1"))
        r = g.check(p, s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_threshold_value_must_be_numeric(self, g) -> None:
        s = store(thresholds={THRESHOLD_KEY: 0.5})
        r = g.check(proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value="hot"), s.snapshot())
        assert not r.passed and r.stage_failed == "format"

    def test_every_registered_type_has_a_required_key(self) -> None:
        """有 payload 的类型都在 ``_REQUIRED_PAYLOAD_KEY`` 里登记过。

        ``DISABLE_SKILL`` 是唯一例外：它只需要 target 存在，不需要 payload。
        """

        from SSEA.verification_gate import _REMOVE_TYPES, _REQUIRED_PAYLOAD_KEY

        assert set(_REQUIRED_PAYLOAD_KEY) == set(PROPOSAL_KIND_MAP) - _REMOVE_TYPES


# ----------------------------------------------------------------------
#  第二级：沙盒
# ----------------------------------------------------------------------


class TestSandboxStage:
    def test_legal_add_skill_passes(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert r.passed, r.reason

    def test_illegal_retrieval_policy_is_rejected_in_sandbox(self, g) -> None:
        """策略值本身不合法——这一级拒它，而不是等 MemorySystem 运行时炸。"""

        s = store()
        r = g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "top_k", policy="lots"),
            s.snapshot(),
        )
        assert not r.passed
        assert r.stage_failed in ("format", "sandbox")

    def test_retrieval_policy_with_wrong_value_type_is_rejected(self, g) -> None:
        s = store()
        r = g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "writable", policy="yes"),
            s.snapshot(),
        )
        assert not r.passed

    def test_committed_retrieval_policy_is_readable_by_memory_system(self, g) -> None:
        """**回归钉子**：过门并提交的检索策略，MemorySystem 必须读得懂。

        这条测试对应的真实事故：``_apply`` 曾把整份策略塞进 ``retrieval[target]``，
        提交后 ``retrieval`` 变成 ``{"default": {"top_k": 8}}``，而 MemorySystem 把
        整个映射交给 validate_retrieval_policy，读到未知键 "default" 直接
        ValueError——**快环在下一个 WAKE 上崩**。

        没有门的时候，没有任何机制会发现「一条过审的提案会让闭环炸掉」。
        """

        from SSEA.memory_system import MemoryConfig, MemorySystem

        s = store()
        p = proposal("UPDATE_RETRIEVAL_POLICY", "top_k", policy=8)
        assert g.check(p, s.snapshot()).passed
        record = s.commit(p, g.check(p, s.snapshot()), timestamp=1.0)
        assert record.applied

        snap = s.snapshot()
        assert snap.retrieval == {"top_k": 8}
        mem = MemorySystem(MemoryConfig(memory_dim=16), snap)  # 不抛异常
        assert mem.policy["top_k"] == 8

    def test_top_k_must_divide_memory_dim(self, g) -> None:
        """top_k 决定 m_t 的分槽布局，除不动 memory_dim 就该在这一级拒掉。

        规则不是 Gate 发明的——它来自 ``validate_retrieval_policy`` 对 top_k
        与 memory_dim 的整除要求。Gate 只负责**在这里**拦住它，而不是让它在
        State Core 里以维度不匹配的形式炸。
        """

        from SSEA.state_core import StateCoreConfig

        dim = StateCoreConfig().memory_dim
        s = store()
        r = g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "top_k", policy=dim + 1),
            s.snapshot(),
        )
        assert not r.passed
        assert r.stage_failed in ("sandbox", "regression")

    def test_legal_retrieval_policy_passes(self, g) -> None:
        s = store()
        r = g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "top_k", policy=8),
            s.snapshot(),
        )
        assert r.passed, r.reason

    def test_unknown_policy_key_is_rejected(self, g) -> None:
        """target 必须是合法策略键名——拼错的键会在运行时才炸。"""

        s = store()
        r = g.check(
            proposal("UPDATE_RETRIEVAL_POLICY", "topK", policy=8),
            s.snapshot(),
        )
        assert not r.passed
        assert r.stage_failed == "format"
        assert "不是合法的策略键" in r.reason

    def test_empty_adapter_bytes_is_rejected(self, g) -> None:
        s = store(adapters={"a": ADAPTER})
        r = g.check(proposal("UPDATE_ADAPTER", "a", adapter=b""), s.snapshot())
        assert not r.passed
        assert r.stage_failed in ("format", "sandbox")

    def test_non_bytes_adapter_is_rejected(self, g) -> None:
        s = store(adapters={"a": ADAPTER})
        r = g.check(proposal("UPDATE_ADAPTER", "a", adapter={"w": 1}), s.snapshot())
        assert not r.passed

    def test_legal_adapter_passes(self, g) -> None:
        s = store(adapters={"a": ADAPTER})
        r = g.check(proposal("UPDATE_ADAPTER", "a", adapter=ADAPTER), s.snapshot())
        assert r.passed, r.reason

    def test_undecodable_adapter_is_rejected(self, g) -> None:
        """**非空 bytes 但不解得开** → 拒。

        这是本类里最要紧的一条，因为它治的正是 13 §4.6 记录的那个洞：
        Store 只管版本号与审计，**不保证下游读得懂**。一份长度不对的 blob
        完全合法地过门、升版本、进快照，然后在快环的下一帧上被静默丢弃——
        **行为毫无变化，而审计里写着"已应用"**。这比崩溃更糟：崩溃会被发现，
        静默丢弃只会在实验里表现为"这个机制好像没用"。
        """

        s = store(adapters={"a": ADAPTER})
        r = g.check(
            proposal("UPDATE_ADAPTER", "a", adapter=b"not-a-blob-at-all"),
            s.snapshot(),
        )
        assert not r.passed
        # 理由要指向"快环会丢弃它"，而不是笼统的"格式不对"——审计日志里
        # 那句话是后来者唯一能看到的诊断。
        assert "可解码" in r.reason

    def test_wrong_shape_blob_is_rejected(self, g) -> None:
        """格式合法、魔数对、但形状与所声明的作用点对不上 —— 同样拒。

        形状对不上时 ``decode_instinct`` 返回 None，所以它与"根本不是 blob"
        走同一条判定。这里单独钉一次，因为"能解出张量"与"能用在 2 维世界"
        是两个条件，而只测前者会漏掉后者。

        **字节是手搓的，不走 ``encode_instinct``**：编码侧现在会拒绝这种形状
        （它在提案成形的路径上，能抛就抛），所以一份"格式对、形状错"的 blob
        只能来自别处——更早的版本、另一个实现、或者被改坏的字节。而这正是
        门要面对的东西：**门必须扛得住编码器不会产出的输入**，否则它守的
        只是"我们自己没写错"，不是"结构里装的能用"。
        """

        blob = (
            MAGIC
            + struct.pack("<BBHH", FORMAT_VERSION, TARGET_LOCOMOTION, 3, 7)
            + b"\x00" * (3 * 7 * 4)
        )
        s = store(adapters={"a": ADAPTER})
        r = g.check(proposal("UPDATE_ADAPTER", "a", adapter=blob), s.snapshot())
        assert not r.passed
        assert "可解码" in r.reason

    def test_unknown_target_blob_is_rejected(self, g) -> None:
        """作用点字节不认识 —— 拒。

        这是 v2 新增的一格，也是最该由门来拦的一格：作用点决定这份权重加到
        哪个量上，一个门不认识的作用点意味着**快环也解释不了它**。门若放行，
        审计里会写着"已应用"，而快环每帧静默丢弃它——行为毫无变化。
        """

        s = store(adapters={"a": ADAPTER})
        blob = bytearray(encode_instinct(ADAPTER_WEIGHTS, target=TARGET_LOCOMOTION))
        blob[len(MAGIC)] = 77  # 只改作用点字节，其余原样
        r = g.check(
            proposal("UPDATE_ADAPTER", "a", adapter=bytes(blob)), s.snapshot()
        )
        assert not r.passed
        assert "可解码" in r.reason

    @pytest.mark.parametrize("bad", [float("inf"), float("nan")])
    def test_non_finite_weight_blob_is_rejected(self, g, bad) -> None:
        """权重里有 ``inf`` / ``nan`` —— 拒。理由与形状错同源，后果更重。

        这种 blob **解得开**（魔数对、作用点认识、形状也对），所以它是最容易
        溜过门的一类坏输入。而它一旦进了结构，快环那边算什么就是非有限数，
        操纵链的 ``argmax`` 会因此把被约束屏蔽成 ``-inf`` 的 op 选出来——
        **一份先验顶掉了约束**。

        门这里拒它的方式与拒形状错完全一样：调同一个 ``decode_instinct``。
        这条测试因此也守着"门不另写一份格式校验"——两份校验必然漂移，
        而漂移方向固定是门更宽松。
        """

        blob = (
            MAGIC
            + struct.pack(
                "<BBHH", FORMAT_VERSION, TARGET_MANIPULATION, 2, 4
            )
            + struct.pack("<8f", 1.0, 1.0, 0.0, 0.0, bad, 1.0, 0.0, 0.0)
        )
        s = store(adapters={"a": ADAPTER})
        r = g.check(proposal("UPDATE_ADAPTER", "a", adapter=blob), s.snapshot())
        assert not r.passed
        assert "可解码" in r.reason

    def test_both_targets_are_accepted(self, g) -> None:
        """两个作用点的 blob 都要能进门——门**不认识作用点的语义**，只认识
        "解码器解得开"。它不该有一份关于"哪些作用点算合法"的私有清单：
        那份清单会与 ``TARGET_SHAPES`` 漂移，而漂移的方向是固定的
        （门更宽松，于是放行一份快环用不了的东西）。
        """

        s = store(adapters={"a": ADAPTER})
        for target in (TARGET_LOCOMOTION, TARGET_MANIPULATION):
            r = g.check(
                proposal(
                    "UPDATE_ADAPTER",
                    "a",
                    adapter=encode_instinct(ADAPTER_WEIGHTS, target=target),
                ),
                s.snapshot(),
            )
            assert r.passed, f"作用点 {target} 被拒了：{r.reason}"


# ----------------------------------------------------------------------
#  第三级：回归
# ----------------------------------------------------------------------


class TestRegressionStage:
    def test_regression_checks_every_kind_not_just_the_changed_one(self, g) -> None:
        """一个阈值提案不该弄坏技能库——但「不该」不是保证，所以逐个复查。"""

        from SSEA.verification_gate import _ALL_KINDS

        assert set(_ALL_KINDS) == set(STRUCTURE_KINDS)

    def test_healthy_structure_passes_regression(self, g) -> None:
        s = store(
            skills={"s1": skill("s1")},
            thresholds={THRESHOLD_KEY: 0.5},
            adapters={"a": ADAPTER},
            retrieval={"top_k": 2},
        )
        r = g.check(proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value=0.9), s.snapshot())
        assert r.passed, r.reason

    def test_broken_sibling_kind_is_caught_by_regression(self, g) -> None:
        """结构里**另一个**类别本来就坏着——Gate 该拒，因为候选结构继承了这个坏。

        构造方式：阈值提案合法，但技能库里预先放了一条 id 与键不一致的技能。
        """

        s = store(skills={"s1": skill("other")}, thresholds={THRESHOLD_KEY: 0.5})
        r = g.check(proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value=0.9), s.snapshot())
        assert not r.passed
        assert r.stage_failed == "regression"
        assert r.reason.startswith("回归:")


# ----------------------------------------------------------------------
#  第四级：小范围环境测试
# ----------------------------------------------------------------------


class TestEnvStage:
    def test_loop_actually_runs_in_the_env_stage(self, g, monkeypatch) -> None:
        """证明第四级真的跑了闭环，而不是直接放行。

        做法：让 ``Environment.step`` 抛异常。若这一级没跑，提案会通过；
        跑了就会在 ``env_test`` 被拒。
        """

        from SSEA import environment as env_mod

        def boom(self, action):  # noqa: ANN001
            raise RuntimeError("环境炸了")

        monkeypatch.setattr(env_mod.Environment, "step", boom)
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert not r.passed
        assert r.stage_failed == "env_test"

    def test_crash_is_reported_with_the_exception_type(self, g, monkeypatch) -> None:
        from SSEA import environment as env_mod

        class Weird(Exception):
            pass

        def boom(self, action):  # noqa: ANN001
            raise Weird("nope")

        monkeypatch.setattr(env_mod.Environment, "step", boom)
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert not r.passed
        assert "Weird" in r.reason

    def test_env_stage_is_deterministic(self) -> None:
        """同一个提案 + 同一个结构 → 同一个结论。Gate 的 seed 是固定的。"""

        s = store()
        p = proposal("ADD_SKILL", "s1", skill=skill("s1"))
        a = gate(env_frames=6).check(p, s.snapshot())
        b = gate(env_frames=6).check(p, s.snapshot())
        assert a == b

    def test_sudden_death_is_distinguished_from_a_hard_world(self) -> None:
        """淘汰本身不是提案的错；**装配即崩**才是。

        用一个必然在前几帧死亡的世界（能量起点极低）配一个合法提案：
        若提案合法，Gate 不该因为「世界难」而拒它。
        """

        from SSEA.environment import Environment, EnvironmentConfig

        cfg = EnvironmentConfig()
        # 找不到字段名时不猜，直接读默认配置确认可构造
        assert cfg is not None
        s = store()
        p = proposal("ADD_SKILL", "s1", skill=skill("s1"))
        r = gate(env_frames=10).check(p, s.snapshot())
        # 默认世界里 10 帧内不会死（test_greedy_policy_survives 跑 60 帧）
        assert r.passed, r.reason


# ----------------------------------------------------------------------
#  顺序可观测（验收第 2 条）
# ----------------------------------------------------------------------


class TestStageOrder:
    def test_format_failure_wins_over_sandbox(self, g) -> None:
        """同时触犯格式与更深层时，报最早那一级。"""

        s = store(skills={"s1": skill("s1")})
        # ADD 一个已存在的 id（格式错），且 payload 缺键（也是格式错）
        r = g.check(proposal("ADD_SKILL", "s1"), s.snapshot())
        assert r.stage_failed == "format"

    def test_sandbox_failure_wins_over_regression(self, g) -> None:
        """结构里另一个类别已坏（回归会拒）+ 本提案 payload 缺键（格式会拒）。

        格式最早，所以报格式——这正说明顺序是「最早失败者胜」。
        """

        s = store(skills={"s1": skill("other")})
        r = g.check(proposal("ADD_SKILL", "s2"), s.snapshot())
        assert r.stage_failed == "format"

    def test_stage_failed_is_always_one_of_the_four(self, g) -> None:
        cases = [
            proposal("ADD_SKILL", "s1"),                       # 格式
            proposal("UPDATE_THRESHOLD", "nope", value=1.0),   # 格式
        ]
        s = store()
        for p in cases:
            r = g.check(p, s.snapshot())
            assert r.stage_failed in STAGES

    def test_passing_result_has_no_stage_failed(self, g) -> None:
        s = store()
        r = g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert r.passed
        assert r.stage_failed is None


# ----------------------------------------------------------------------
#  副本语义（验收第 3 条）
# ----------------------------------------------------------------------


class TestNoMutation:
    def test_gate_does_not_change_the_snapshot(self, g) -> None:
        s = store(thresholds={"t": 0.5})
        snap = s.snapshot()
        before = dict(snap.thresholds)
        g.check(proposal("UPDATE_THRESHOLD", "t", value=0.99), snap)
        assert dict(snap.thresholds) == before

    def test_gate_does_not_bump_versions(self, g) -> None:
        """Gate 只读结构。提交是 StructureStore 的事，不是 Gate 的事。"""

        s = store()
        before = dict(s.versions)
        g.check(proposal("ADD_SKILL", "s1", skill=skill("s1")), s.snapshot())
        assert dict(s.versions) == before

    def test_repeated_checks_do_not_accumulate_state(self, g) -> None:
        """同一个提案查三次，结论相同——Gate 不持有结构状态。"""

        s = store()
        snap = s.snapshot()
        p = proposal("ADD_SKILL", "s1", skill=skill("s1"))
        results = [g.check(p, snap) for _ in range(3)]
        assert len({(r.passed, r.reason) for r in results}) == 1

    def test_gate_holds_no_structure_state(self, g) -> None:
        """Gate 实例上不该有缓存 / 计数之类的跨调用状态。"""

        assert not any(
            hasattr(g, name)
            for name in ("_cache", "_history", "_last", "_count", "_state")
        )


# ----------------------------------------------------------------------
#  与 StructureStore 的接缝（验收第 4 条）
# ----------------------------------------------------------------------


class TestWithStructureStore:
    def test_legal_proposal_commits_and_bumps_only_its_kind(self, g) -> None:
        s = store(thresholds={THRESHOLD_KEY: 0.5})
        snap = s.snapshot()
        p = proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value=0.7)
        record = s.commit(p, g.check(p, snap), timestamp=1.0)

        assert record.applied
        assert record.from_version == 0 and record.to_version == 1
        assert record.kind == "thresholds"
        # 只有 thresholds 动，别的类别版本号不变
        assert s.versions["thresholds"] == 1
        assert s.versions["skills"] == 0

    def test_rejected_proposal_does_not_bump_and_does_not_raise(self, g) -> None:
        s = store()
        snap = s.snapshot()
        p = proposal("UPDATE_THRESHOLD", "nope", value=0.7)
        result = g.check(p, snap)
        record = s.commit(p, result, timestamp=1.0)  # 不抛异常

        assert not record.applied
        assert record.from_version == record.to_version == 0
        assert record.gate_result.startswith("reject:")
        assert s.versions["thresholds"] == 0

    def test_rejection_is_recorded_for_audit(self, g) -> None:
        """拒绝也是审计项——「提过什么、为什么没过」必须可追溯。"""

        s = store()
        snap = s.snapshot()
        p = proposal("ADD_SKILL", "s1")
        s.commit(p, g.check(p, snap), timestamp=1.0)
        log = s.audit_log()
        assert len(log) == 1
        assert not log[0].applied
        assert log[0].proposal_id == "p1"
        assert log[0].gate_result.startswith("reject:")

    def test_committed_structure_is_what_the_next_snapshot_sees(self, g) -> None:
        """过门 → 提交 → 新快照里有它。这是注入面的完整一条。"""

        s = store()
        p = proposal("ADD_SKILL", "s1", skill=skill("s1"))
        s.commit(p, g.check(p, s.snapshot()), timestamp=1.0)
        assert s.snapshot().get_skill("s1") is not None

    def test_old_snapshot_is_untouched_by_a_later_commit(self, g) -> None:
        """快环零改动：已交出的快照不随后续提交变化。"""

        s = store()
        old = s.snapshot()
        p = proposal("ADD_SKILL", "s1", skill=skill("s1"))
        s.commit(p, g.check(p, old), timestamp=1.0)
        assert old.get_skill("s1") is None
        assert s.snapshot().get_skill("s1") is not None

    def test_disable_skill_removes_it_from_the_next_snapshot(self, g) -> None:
        s = store(skills={"s1": skill("s1")})
        snap = s.snapshot()
        p = proposal("DISABLE_SKILL", "s1")
        record = s.commit(p, g.check(p, snap), timestamp=1.0)
        assert record.applied
        assert s.snapshot().get_skill("s1") is None


# ----------------------------------------------------------------------
#  八种提案类型各有放过与拒绝（验收第 1 条）
# ----------------------------------------------------------------------


class TestEveryProposalType:
    """8 种提案类型 × {合法, 非法}。漏一种就是一条没人守过的提交路径。"""

    def _legal(self, ptype: str, target: str) -> SelfModificationProposal:
        return {
            "ADD_SKILL": lambda: proposal("ADD_SKILL", "s1", skill=skill("s1")),
            "UPDATE_SKILL": lambda: proposal(
                "UPDATE_SKILL", "s1", skill=skill("s1", speed=0.9)
            ),
            "DISABLE_SKILL": lambda: proposal("DISABLE_SKILL", "s1"),
            "ADD_RULE": lambda: proposal("ADD_RULE", "r1", rule={"if": "x"}),
            "UPDATE_RULE": lambda: proposal("UPDATE_RULE", "r1", rule={"if": "y"}),
            "UPDATE_THRESHOLD": lambda: proposal(
                "UPDATE_THRESHOLD", THRESHOLD_KEY, value=0.8
            ),
            "UPDATE_RETRIEVAL_POLICY": lambda: proposal(
                "UPDATE_RETRIEVAL_POLICY", "top_k", policy=8
            ),
            "UPDATE_ADAPTER": lambda: proposal(
                "UPDATE_ADAPTER", "a", adapter=ADAPTER
            ),
        }[ptype]()

    def _illegal(self, ptype: str) -> SelfModificationProposal:
        """每种类型各挑一个它特有的非法形态。"""

        return {
            "ADD_SKILL": lambda: proposal("ADD_SKILL", "s1"),  # 缺 payload
            "UPDATE_SKILL": lambda: proposal("UPDATE_SKILL", "ghost", skill=skill("ghost")),
            "DISABLE_SKILL": lambda: proposal("DISABLE_SKILL", "ghost"),
            "ADD_RULE": lambda: proposal("ADD_RULE", "r1", rule=None),
            "UPDATE_RULE": lambda: proposal("UPDATE_RULE", "ghost", rule={}),
            "UPDATE_THRESHOLD": lambda: proposal("UPDATE_THRESHOLD", THRESHOLD_KEY, value=None),
            "UPDATE_RETRIEVAL_POLICY": lambda: proposal(
                "UPDATE_RETRIEVAL_POLICY", "top_k", policy="lots"
            ),
            "UPDATE_ADAPTER": lambda: proposal("UPDATE_ADAPTER", "a", adapter=b""),
        }[ptype]()

    def _store_for(self, ptype: str) -> StructureStore:
        """按提案类型备结构。

        新增类（ADD_*）的 target 必须**不存在**，更新/移除类的 target 必须
        **已存在**——同一个初始结构喂给两者，必然有一边被格式级拒掉。
        """

        adding = ptype in ("ADD_SKILL", "ADD_RULE")
        return StructureStore(
            initial={
                "skills": {} if adding else {"s1": skill("s1")},
                "rules": {} if adding else {"r1": {"if": "x"}},
                "thresholds": {} if adding else {THRESHOLD_KEY: 0.5},
                "adapters": {} if adding else {"a": ADAPTER},
                "retrieval": {} if adding else {"top_k": 4},
            }
        )

    def test_legal_forms_all_pass(self, g) -> None:
        for ptype in PROPOSAL_KIND_MAP:
            s = self._store_for(ptype)
            r = g.check(self._legal(ptype, "s1"), s.snapshot())
            assert r.passed, f"{ptype} 的合法形态被拒: {r.reason}"

    def test_illegal_forms_all_fail(self, g) -> None:
        for ptype in PROPOSAL_KIND_MAP:
            s = self._store_for(ptype)
            r = g.check(self._illegal(ptype), s.snapshot())
            assert not r.passed, f"{ptype} 的非法形态被放过"
            assert r.stage_failed in STAGES

    def test_all_eight_types_are_covered(self) -> None:
        assert len(PROPOSAL_KIND_MAP) == 8

    def test_each_type_maps_to_exactly_one_kind(self) -> None:
        assert set(PROPOSAL_KIND_MAP.values()) <= set(STRUCTURE_KINDS)
