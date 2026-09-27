"""Structure Store —— 版本化结构仓库。

**新增依据**：docs/08-dual-loop-interface-and-gap-closure.md §2.1
（双环注入接口：Structure Injection Surface）。

07 第 5.3 节只有一句话「慢环将结构返回给快环，改变未来行为」——未定义返回什么、
何时返回、失败怎么办、快环如何消费。本组件补上这个接口。

数据流::

    Verification Gate（格式→沙盒→回归→小范围环境测试）
          │ pass
          ▼
    Structure Store（版本化）
          skills@v7   rules@v3   adapters@v2   thresholds@v5   retrieval@v1
          │ 原子切换版本号
          ▼
    FastLoopContext（不可变快照）── read ──► 快环 FSL

四条性质，逐条对应 SSEA 约束：

- **快环零改动** —— 快环只读 ``FastLoopContext``，不知道慢环存在；
  换版本 = 换句柄。（C4 低算力：注入不每步发生）
- **失败天然回滚** —— Gate 不通过则版本号不切换，快照继续用旧版。
  **不存在"回滚"这个操作，因为从未应用。**（07 §4.6：这是架构的一部分，
  而不是外部安全措施）
- **可遗传** —— 快照内容就是 GenePackage 的 ``skill_library`` /
  ``instinct_adapters`` / ``behavior_policy`` 来源。注入面是遗传面的子集，
  两套机制共用一份结构定义。（C7、C3）
- **可审计** —— 每次切换记录 ``(proposal_id, from_v, to_v, gate_result,
  timestamp)``。（C7）

五类可注入结构，严格落在权重 / 记忆 / 技能三分离内，**不含裸梯度**：

    SkillProposal            技能     Action 的 skill 通道
    RuleProposal             规则     State Core 的门控 / 偏置
    AdapterProposal          权重     State Core 的可插拔算子
    ThresholdProposal        行为策略  Action Decoder 决策阈值
    RetrievalPolicyProposal  记忆策略  Memory System 检索参数
"""

from __future__ import annotations

import threading
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .self_modification import SelfModificationProposal


#: 五类可注入结构。顺序即审计日志的排序依据。
STRUCTURE_KINDS: tuple[str, ...] = (
    "skills",
    "rules",
    "adapters",
    "thresholds",
    "retrieval",
)

#: proposal_type → 结构类别的映射。
#: 一个提案只影响一个类别，因此版本号按类别独立递增。
PROPOSAL_KIND_MAP: dict[str, str] = {
    "ADD_SKILL": "skills",
    "UPDATE_SKILL": "skills",
    "DISABLE_SKILL": "skills",
    "ADD_RULE": "rules",
    "UPDATE_RULE": "rules",
    "UPDATE_THRESHOLD": "thresholds",
    "UPDATE_RETRIEVAL_POLICY": "retrieval",
    "UPDATE_ADAPTER": "adapters",
}


@dataclass(frozen=True)
class GateResult:
    """Verification Gate 的结论。

    Milestone 1 只定义结构，不实现 Gate 本体（Gate 是 Milestone 2+ 的模块）。
    Structure Store 只要求调用方给出 ``passed`` 与 ``reason``——
    这让 Store 在 Gate 实现之前就可被测试。
    """

    passed: bool
    reason: str = ""
    stage_failed: str | None = None  # format / sandbox / regression / env_test


@dataclass(frozen=True)
class AuditRecord:
    """一次版本切换（或驳回）的审计记录。对应 08 §2.1 的可审计性质。"""

    proposal_id: str
    kind: str
    from_version: int
    to_version: int
    gate_result: str
    timestamp: float
    applied: bool
    reason: str = ""


@dataclass
class _Slot:
    """一个结构类别的当前值与版本号。"""

    value: dict[str, Any]
    version: int = 0


class StructureStore:
    """版本化结构仓库。

    用法::

        store = StructureStore()
        store.commit(proposal, GateResult(passed=True))
        ctx = store.snapshot()          # 不可变快照
        fast_loop.read(ctx)             # 快环只读快照

    **线程 / 进程边界**：commit 与 snapshot 都应是原子的。第一阶段单线程，
    用一把锁保证 snapshot 不会读到半切换状态。
    """

    def __init__(self, initial: dict[str, dict[str, Any]] | None = None) -> None:
        initial = initial or {}
        unknown = set(initial) - set(STRUCTURE_KINDS)
        if unknown:
            raise ValueError(f"未知的结构类别: {sorted(unknown)}")
        self._slots: dict[str, _Slot] = {
            kind: _Slot(value=dict(initial.get(kind, {}))) for kind in STRUCTURE_KINDS
        }
        self._audit: list[AuditRecord] = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 写入侧（慢环）
    # ------------------------------------------------------------------

    def commit(
        self,
        proposal: SelfModificationProposal,
        gate: GateResult,
        timestamp: float,
    ) -> AuditRecord:
        """提交一个**已过门**的提案，提升对应类别的版本号。

        Gate 不通过时**不抛异常**，只记录一条 ``applied=False`` 的审计项并
        原样返回——拒绝是正常路径，不是错误路径。

        返回 AuditRecord 而非新旧版本号，是为了让调用方（慢环）能直接
        把记录写进 trace，无需再查一次审计日志。
        """

        kind = PROPOSAL_KIND_MAP.get(proposal.proposal_type)
        if kind is None:
            raise ValueError(
                f"提案类型 {proposal.proposal_type!r} 无对应结构类别"
            )

        with self._lock:
            slot = self._slots[kind]
            from_v = slot.version

            if not gate.passed:
                # 版本号不切换。快照继续用旧版——不存在"回滚"，因为从未应用。
                record = AuditRecord(
                    proposal_id=proposal.proposal_id,
                    kind=kind,
                    from_version=from_v,
                    to_version=from_v,
                    gate_result=f"reject:{gate.stage_failed or 'gate'}",
                    timestamp=timestamp,
                    applied=False,
                    reason=gate.reason,
                )
                self._audit.append(record)
                return record

            slot.value = self._apply(kind, slot.value, proposal)
            slot.version = from_v + 1
            record = AuditRecord(
                proposal_id=proposal.proposal_id,
                kind=kind,
                from_version=from_v,
                to_version=slot.version,
                gate_result="pass",
                timestamp=timestamp,
                applied=True,
                reason=gate.reason,
            )
            self._audit.append(record)
            return record

    @staticmethod
    def _apply(
        kind: str,
        current: dict[str, Any],
        proposal: SelfModificationProposal,
    ) -> dict[str, Any]:
        """把提案 payload 合并进当前结构。返回新 dict，不原地修改。

        复制而非原地改，是为了保证 ``snapshot()`` 交出的快照永不随后续
        commit 变化——不可变性是「快环零改动」的前提。
        """

        nxt = dict(current)
        target = proposal.target
        ptype = proposal.proposal_type

        if ptype == "DISABLE_SKILL":
            nxt.pop(target, None)
            return nxt
        if ptype in ("ADD_SKILL", "UPDATE_SKILL"):
            nxt[target] = proposal.payload.get("skill")
            return nxt
        if ptype in ("ADD_RULE", "UPDATE_RULE"):
            nxt[target] = proposal.payload.get("rule")
            return nxt
        if ptype == "UPDATE_THRESHOLD":
            nxt[target] = proposal.payload.get("value")
            return nxt
        if ptype == "UPDATE_RETRIEVAL_POLICY":
            nxt[target] = proposal.payload.get("policy")
            return nxt
        if ptype == "UPDATE_ADAPTER":
            nxt[target] = proposal.payload.get("adapter")
            return nxt
        raise ValueError(f"未处理的结构类别 {kind!r}")

    # ------------------------------------------------------------------
    # 读取侧（快环）
    # ------------------------------------------------------------------

    def snapshot(self) -> FastLoopContext:
        """导出不可变快照。

        快照与 Store 脱钩：后续 commit 不影响已交出的快照。快环持有一个
        快照跑到底，换版本只需再取一次。
        """

        from .fast_loop_context import FastLoopContext

        with self._lock:
            versions = {kind: slot.version for kind, slot in self._slots.items()}
            # deepcopy 而非 dict()：浅拷贝会让快照与 Store 共享嵌套结构，
            # 消费方改一个嵌套字段就能污染后续快照。快照只在换版本时取一次，
            # 深拷贝的代价可接受——而不可变性是「快环零改动」的前提，不能省。
            values = {
                kind: deepcopy(slot.value) for kind, slot in self._slots.items()
            }
        return FastLoopContext(
            skills=values["skills"],
            rules=values["rules"],
            adapters=values["adapters"],
            thresholds=values["thresholds"],
            retrieval=values["retrieval"],
            versions=versions,
        )

    # ------------------------------------------------------------------
    # 审计
    # ------------------------------------------------------------------

    @property
    def versions(self) -> dict[str, int]:
        """各类别当前版本号。"""
        with self._lock:
            return {kind: slot.version for kind, slot in self._slots.items()}

    def audit_log(self) -> tuple[AuditRecord, ...]:
        """完整审计日志，按提交顺序。"""
        with self._lock:
            return tuple(self._audit)

    def applied_count(self) -> int:
        return sum(1 for r in self._audit if r.applied)

    def rejected_count(self) -> int:
        return sum(1 for r in self._audit if not r.applied)
