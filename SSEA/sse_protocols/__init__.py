"""SSEA v0.3.1 —— 接口协议层（Milestone 1）

本包按 docs/07-ssea-v0.3.1-charter.md 第 8 节定义模型与环境之间的数据格式，
并按 docs/08-dual-loop-interface-and-gap-closure.md 第 5 节修订条款汇总表实现。
凡 08 修订过的协议，模块 docstring 均标注修订依据。

设计约定
--------
1. **协议用 frozen dataclass，不用裸 dict**。07 第 8 节用 dict 记法描述协议，
   但 dict 无法阻止字段拼写错误，也无法执行「动作必须可执行」（08 §2.4）这类
   明文约束。dataclass 让协议可被验证，也让 Milestone 2 的模型代码有确定签名。
2. **向量用 tuple[float, ...]，不用 numpy/torch**。协议是接口，必须可序列化、
   可 diff、可跨进程。张量化发生在模型边界，不发生在协议层。
3. **规则属于协议，执行点属于模块**。例如 ``ActionConstraints.violations()``
   定义规则，Action Decoder（第一执行点）与 Environment（第二执行点）共用
   同一份规则（08 §2.6.2）。

与 07 §8 的差异（全部来自 08 的修订条款）
---------------------------------------
==========================  ============================================
协议                        修订
==========================  ============================================
``Action``                  删除 ``latent_action``；新增「动作必须可执行」
``ActionSpace``             删除 ``latent`` 块
``ActionConstraints``       增补强制执行语义（双执行点）
``Feedback``                ``prediction_error`` 生产者 = SurpriseEstimator
``MemoryItem``              增补可继承性判定 ``is_heritable()``
``Skill``                    ``precondition`` 检查方 = Skill Runner；
                             增补 ``is_consolidatable()``
``SelfModificationProposal`` 增补 ``origin``；代码段只走技能提案
``GenePackage``              增补 ``heritable_memory``；
                             ``memory_index`` → ``memory_store_ref``；
                             ``mutation_rate`` 增补作用范围
==========================  ============================================

新增两个协议组件（07 中没有）：``StructureStore`` 与 ``FastLoopContext``。
"""

from .action import (
    Action,
    Communication,
    Locomotion,
    Manipulation,
    MemoryWrite,
    SelfModification,
    SkillCall,
    idle_action,
)
from .action_constraints import ActionConstraints, default_constraints
from .action_space import OPERATIONS, ActionSpace, default_action_space
from .body_state import BodyState
from .communication_signal import CommunicationSignal
from .environment_summary import EnvironmentSummary
from .event_vector import EVENT_TYPES, EventVector
from .fast_loop_context import FastLoopContext
from .feedback import Feedback
from .gene import MUTATION_SCOPES, NON_MUTABLE, GenePackage
from .memory import HERITABLE_TYPES, MEMORY_TYPES, MemoryItem
from .observation import Observation
from .object_vector import ObjectVector
from .self_modification import (
    ALLOWED_PROPOSAL_TYPES,
    FORBIDDEN_PROPOSAL_TYPES,
    ORIGIN_CONSOLIDATED_PREFIX,
    SelfModificationProposal,
)
from .serialization import from_json_dict, roundtrip, to_json_dict
from .skill import Skill
from .structure_store import (
    PROPOSAL_KIND_MAP,
    STRUCTURE_KINDS,
    AuditRecord,
    GateResult,
    StructureStore,
)

__all__ = [
    # 8.1 / 8.2 / 8.3
    "Observation",
    "BodyState",
    "ActionConstraints",
    "default_constraints",
    # 8.4 / 8.5
    "ActionSpace",
    "default_action_space",
    "OPERATIONS",
    "Action",
    "Locomotion",
    "Manipulation",
    "Communication",
    "MemoryWrite",
    "SkillCall",
    "SelfModification",
    "idle_action",
    # 8.6 / 8.7 / 8.8 / EnvironmentSummary
    "ObjectVector",
    "EventVector",
    "EVENT_TYPES",
    "CommunicationSignal",
    "EnvironmentSummary",
    # 8.9 / 8.10 / 8.11
    "Feedback",
    "MemoryItem",
    "MEMORY_TYPES",
    "HERITABLE_TYPES",
    "Skill",
    # 8.12 / 8.13
    "SelfModificationProposal",
    "ALLOWED_PROPOSAL_TYPES",
    "FORBIDDEN_PROPOSAL_TYPES",
    "ORIGIN_CONSOLIDATED_PREFIX",
    "GenePackage",
    "MUTATION_SCOPES",
    "NON_MUTABLE",
    # 08 §2.1 新增
    "StructureStore",
    "GateResult",
    "AuditRecord",
    "STRUCTURE_KINDS",
    "PROPOSAL_KIND_MAP",
    "FastLoopContext",
    # 序列化（Milestone 1 验收：所有接口可序列化为 JSON）
    "to_json_dict",
    "from_json_dict",
    "roundtrip",
]
