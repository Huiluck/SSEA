"""Milestone 2 / 3 测试共享夹具。

集中放"构造一个能跑的世界 + 一个能跑的环"，避免每个测试文件重复
二十行装配代码——重复的装配代码会漂移，而漂移的夹具比没有夹具更糟。
"""

from __future__ import annotations

import pytest

from SSEA.action_decoder import ActionDecoder, ActionDecoderConfig
from SSEA.environment import Environment, EnvironmentConfig
from SSEA.fast_loop import FastLoop, FastLoopConfig
from SSEA.metabolic_monitor import MetabolicMonitor
from SSEA.perception_encoder import PerceptionConfig, PerceptionEncoder
from SSEA.sse_protocols import FastLoopContext, default_constraints
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.state_core import StateCore, StateCoreConfig


def make_context(
    *,
    retrieval: dict | None = None,
    adapters: dict | None = None,
    **skills: object,
) -> FastLoopContext:
    """从 Structure Store 取一份快照，可顺便塞进技能、检索策略与本能 adapter。

    技能必须走 ``StructureStore(initial=...)`` 这个正规入口。
    ``store.skills = {...}`` 那种写法会静默无效——``snapshot()`` 读的是
    ``_slots["skills"]``，不是这个新属性——于是每个"注入了技能"的测试
    都在对着一个空技能库跑，却一路通过。

    ``adapters`` 同一条规矩，理由更强一层：直到 2026-09-27 之前，"注入了
    adapter" 这个动作**没有任何地方会去读**——``UPDATE_ADAPTER`` 能写进去、
    门会校验、Store 会升版本号、审计会记一笔，而行为侧零影响。现在读它的
    是 ``decode_instinct_set(context.adapters)``，读的是**字段本身**；
    曾短暂存在的 ``get_adapter()`` 已因零调用方删除
    （见 ``tests/test_consumer_surface.py`` 的 ``DELETED_ACCESSORS``）。
    """

    initial: dict[str, dict] = {}
    if skills:
        initial["skills"] = dict(skills)
    if retrieval is not None:
        initial["retrieval"] = dict(retrieval)
    if adapters is not None:
        initial["adapters"] = dict(adapters)
    return StructureStore(initial=initial or None).snapshot()


@pytest.fixture
def context() -> FastLoopContext:
    return make_context()


@pytest.fixture
def env() -> Environment:
    """固定 seed 的世界。"""

    return Environment(seed=7)


@pytest.fixture
def encoder() -> PerceptionEncoder:
    return PerceptionEncoder()


@pytest.fixture
def core() -> StateCore:
    return StateCore()


@pytest.fixture
def decoder() -> ActionDecoder:
    return ActionDecoder()


@pytest.fixture
def monitor() -> MetabolicMonitor:
    return MetabolicMonitor()


@pytest.fixture
def loop(env: Environment, context: FastLoopContext) -> FastLoop:
    """装配好的快环。默认 5 帧睡眠期，便于测试状态机。"""

    return FastLoop(
        env,
        context,
        config=FastLoopConfig(max_frames=50, min_sleep_frames=3),
    )


__all__ = [
    "EnvironmentConfig",
    "PerceptionConfig",
    "StateCoreConfig",
    "ActionDecoderConfig",
    "default_constraints",
    "make_context",
]
