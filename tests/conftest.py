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
    **skills: object,
) -> FastLoopContext:
    """从 Structure Store 取一份快照，可顺便塞进技能与检索策略。

    技能必须走 ``StructureStore(initial=...)`` 这个正规入口。
    ``store.skills = {...}`` 那种写法会静默无效——``snapshot()`` 读的是
    ``_slots["skills"]``，不是这个新属性——于是每个"注入了技能"的测试
    都在对着一个空技能库跑，却一路通过。
    """

    initial: dict[str, dict] = {}
    if skills:
        initial["skills"] = dict(skills)
    if retrieval is not None:
        initial["retrieval"] = dict(retrieval)
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
