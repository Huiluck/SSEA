"""把本能**经提案路径**播种进结构 —— 「关本能」那一臂才是对照组。

为什么必须走提案，不能直接 ``StructureStore(initial={"adapters": ...})``
--------------------------------------------------------------------------
直接塞初始结构能跑出同样的行为，但它**绕开了四权分立**，于是实验里那个
"装着本能"的个体其实是一个**从未经过验证门的个体**。SSEA 的主张是
「自我修改必须经验证门」（07 §16 / C6），本能先验是结构修改的一种，
所以它必须走完这条链：

    提案 → VerificationGate（四级）→ StructureStore.commit → 换快照

实验脚本走这条路，于是每一轮的审计日志里都留得下
``(proposal_id, from_v, to_v, gate_result, timestamp)``。
这同时让「本能是被验证过的先验」从一句设计口号变成**可查的审计事实**。

为什么默认世界保持空 ``adapters``
--------------------------------
本模块只在实验里被调用。默认世界（``StructureStore()``）的 ``adapters``
是空的，于是**「关本能」不是一个特制的对照实现，就是默认世界本身**。
这比"另写一个关闭开关"强：开关会漂移，而空结构不会。

多份本能：一份一个提案
--------------------
:func:`seeded_store_multi` 每份本能各提交一次 ``UPDATE_ADAPTER``。
理由不是实现方便，是审计：``UPDATE_ADAPTER`` 一次只改一个 target，
而"这一份被拒、那一份过门"只有在两个提案里才留得下两条各自带
``stage_failed`` 的记录。合并成一个提案的话，日志只会说"这一批没通过"，
而实验读数需要知道**是哪一份**没通过。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from SSEA.sse_protocols.self_modification import SelfModificationProposal
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate


@dataclass(frozen=True)
class SeedingOutcome:
    """一次播种的结果。``applied=False`` 时后面几个字段没有意义。"""

    name: str
    applied: bool
    from_version: int
    to_version: int
    stage_failed: str | None
    reason: str

    @property
    def version_bumped(self) -> bool:
        """版本号是否真的切换了。「失败天然回滚」的判据就是它没切。"""
        return self.to_version == self.from_version + 1


def seed_instinct(
    store: StructureStore,
    name: str,
    blob: bytes,
    *,
    proposal_id: str = "seed-instinct",
    env_frames: int = 8,
    timestamp: float = 0.0,
) -> SeedingOutcome:
    """把一份本能先验作为 ``UPDATE_ADAPTER`` 提案提交，返回结果。

    返回而不抛：**被门拒本身是有效结果**，不是异常。调用方据此决定
    「这一臂其实没有装上前提」——把它当异常处理会让人以为脚本崩了，
    而真相是"这份先验不合法"。
    """

    proposal = SelfModificationProposal(
        proposal_id=proposal_id,
        proposal_type="UPDATE_ADAPTER",
        target=name,
        payload={"adapter": blob},
        reason="实验：显式注入趋近本能（C8 的基因先验，不是知识语料）",
    )

    gate = VerificationGate(GateConfig(env_frames=env_frames))
    result = gate.check(proposal, store.snapshot())
    if not result.passed:
        return SeedingOutcome(
            name=name,
            applied=False,
            from_version=store.versions["adapters"],
            to_version=store.versions["adapters"],
            stage_failed=result.stage_failed,
            reason=result.reason,
        )

    record = store.commit(proposal, result, timestamp=timestamp)
    return SeedingOutcome(
        name=name,
        applied=record.applied,
        from_version=record.from_version,
        to_version=record.to_version,
        stage_failed=None,
        reason="过门并应用" if record.applied else "过门但未应用",
    )


def seeded_store(name: str, blob: bytes, **kwargs: object) -> tuple[StructureStore, SeedingOutcome]:
    """开一份**默认世界**的 store（``adapters`` 空），把本能播种进去。

    默认世界那一步是刻意的：``StructureStore()`` 的各类别都空，
    于是"播种前的状态"与"完全不装本能的那一臂"是**同一个东西**——
    两臂共用一个起点，差异只可能来自播种。
    """

    store = StructureStore()
    outcome = seed_instinct(store, name, blob, **kwargs)  # type: ignore[arg-type]
    return store, outcome


def seeded_store_multi(
    adapters: Sequence[tuple[str, bytes]], **kwargs: object
) -> tuple[StructureStore, tuple[SeedingOutcome, ...]]:
    """同一份默认世界里播种**多份**本能，每一份各走一次提案。

    与 :func:`seeded_store` 共用同一个起点（``StructureStore()`` 各类别全空），
    差别只在于这里要装的不止一份。

    **一份一个提案，不是一份提案里塞多个键。** ``UPDATE_ADAPTER`` 一次只改
    一个 target（``_apply_to_copy`` 是 ``current[target] = ...``），而更要紧的
    是审计：一份被门拒、另一份过门这种情形，只有在两个提案里才留得下两条
    各自带 ``stage_failed`` 的记录。合在一个提案里的话，日志只会说"这一批
    没通过"，而实验读数需要知道**是哪一份**没通过。

    调用方必须逐条检查 ``applied``：静默继续的话，某一臂实际是"少装了一份"
    而输出看起来完全正常——那正是这个项目反复要防的失败形状。
    """

    store = StructureStore()
    outcomes: list[SeedingOutcome] = []
    for name, blob in adapters:
        outcomes.append(
            seed_instinct(store, name, blob, proposal_id=f"seed-{name}", **kwargs)  # type: ignore[arg-type]
        )
    return store, tuple(outcomes)
