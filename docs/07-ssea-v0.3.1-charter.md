# SSEA v0.3.1 第一阶段任务书

**项目名称**：SSEA  
**全称**：Survival-based Self-Evolving Agent Architecture  
**中文名称**：生存式自演化代理架构  
**当前版本**：v0.3.1  
**文档性质**：第一阶段任务书 / 立项修订版  
**修订背景**：针对 v0.3 的三个关键答辩问题进行修订：  
1. 项目目标是设计新模型架构，而不是简单使用已有架构作为大脑。  
2. 模型与生态系统的交互必须不是自然语言，而是感知、身体行为、动作信号等。  
3. 动作接口不能定义为从有限字符串列表中选择，必须定义连续、参数化、技能化和潜空间动作的混合动作空间。

---

# 1. 第一阶段核心目标

SSEA v0.3.1 第一阶段的目标不是：

```text
使用现有模型架构，放入环境中进行生存迭代。
```

而是：

```text
设计并验证一种新的模型架构。
该架构以非语言感知-行动闭环为核心，
采用权重、记忆、技能三分离结构，
支持局部学习、技能固化、基因保存、变异继承和安全自我修改。
```

更具体地说，第一阶段要完成：

> **最小可行的 SSEA 模型本体架构原型。**

该原型应能够证明：

1. 模型可以不以自然语言为主进行感知和行动。
2. 模型可以通过身体状态、环境对象、事件向量与环境交互。
3. 模型可以输出连续动作、参数化动作、技能调用和记忆操作。
4. 模型可以将经验写入外部记忆，而不是全部压入权重。
5. 模型可以将成功经验固化为技能。
6. 模型可以进行局部自我修改，而不是全量权重训练。
7. 模型可以保存基因包，并产生可变异后代。
8. 模型可以在不构建完整生态系统的前提下完成基本生存闭环。

---

# 2. 相对 v0.3 的关键修订

## 2.1 修订一：明确架构原创性

v0.3 的风险：

```text
看起来像是在使用 GRU / Mamba / RAG / Voyager 等已有模块做集成。
```

v0.3.1 修订为：

```text
SSEA 的架构创新不在单一 backbone 算子，
而在模型的信息流结构、动作接口、学习机制、记忆结构和遗传机制。
```

SSEA 的新架构贡献定义在四个层次：

| 层次 | 传统模型 | SSEA v0.3.1 |
|---|---|---|
| 算子层 | Attention / RNN / MLP | 可替换低算力算子，不是核心创新点 |
| 信息流层 | 文本输入 → Transformer → token 输出 | 感知 → 状态 → 记忆 → 动作 → 反馈 |
| 学习层 | 喂数据 + 全量权重训练 | 记忆写入、技能固化、局部可塑性、代码修改 |
| 演化层 | 模型训练后固定 | 模型可保存、恢复、变异、继承、自我修改 |

---

## 2.2 修订二：明确非自然语言交互

v0.3 的风险：

```text
虽然提出不用自然语言，但没有强制禁止语言接口进入控制闭环。
```

v0.3.1 修订为：

```text
第一阶段控制闭环中不使用自然语言。
环境不接受自然语言命令。
模型控制路径不依赖 tokenizer。
模型动作输出不是文本，而是结构化动作对象。
自然语言只允许作为后续观察员解释接口。
```

---

## 2.3 修订三：重新定义动作接口

v0.3 中：

```python
"available_actions": list[str]
```

容易被理解为：

```text
模型只能从有限动作菜单中选择。
```

v0.3.1 修订为：

```python
"action_constraints": ActionConstraints
```

并定义混合动作空间：

```text
连续动作
+
离散操作
+
参数化动作
+
技能调用
+
潜空间动作
```

动作不再是：

```text
从 list[str] 中选择一个字符串。
```

而是：

```text
生成一个结构化、可执行、可约束、可扩展的动作对象。
```

---

# 3. 项目定位

## 3.1 SSEA 不是语言模型

传统大模型的核心任务是：

```text
预测下一个 token。
```

SSEA 的核心任务是：

```text
感知环境
→
形成内部状态
→
选择行动
→
获得反馈
→
更新记忆与技能
→
局部修改自身
→
保存基因并继续生存
```

因此，SSEA 的第一身份不是聊天模型，而是：

> **生存代理控制器。**

---

## 3.2 SSEA 不是简单具身强化学习

传统具身强化学习通常关注：

```text
策略网络
+
奖励函数
+
环境交互
```

SSEA 额外引入：

- 外部长期记忆
- 技能库
- 规则库
- 自我修改
- 基因包
- 变异继承
- 代谢约束
- 安全验证器

因此，SSEA 是：

> **可遗传、可自我修改、可积累经验的生存代理架构。**

---

## 3.3 SSEA 不是完整生态系统模拟器

第一阶段不构建复杂生态。

生态系统是后续阶段的外部条件。

第一阶段只构建：

```text
能够进入生态系统的最小模型本体。
```

---

# 4. 架构原创性声明

SSEA v0.3.1 的架构原创性体现在以下六点。

---

## 4.1 从语言建模架构转向生存控制架构

传统模型：

```text
text in → text out
```

SSEA：

```text
observation in → action out → feedback in → self update
```

模型的主输出不是语言，而是：

```text
身体动作
操作参数
技能调用
记忆写入
通信信号
自我修改提案
```

---

## 4.2 权重、记忆、技能三分离

SSEA 不把全部知识压入权重，而是分为三类：

| 能力类型 | 存储位置 | 更新方式 |
|---|---|---|
| 基础控制能力 | 小型核心网络 | 少量局部更新或冻结 |
| 历史事件经验 | 外部记忆系统 | 写入、检索、合并、遗忘 |
| 可执行行为 | 技能库 / 代码库 | 生成、验证、复用、变异 |

这直接支持：

- 低算力
- 低带宽
- 精准回忆
- 自我修改
- 遗传传递

---

## 4.3 动作空间不是词表，而是控制空间

SSEA 的动作不是从词表中采样一个词。

动作空间包括：

```text
连续运动控制
参数化操作
技能调用
记忆操作
通信向量
潜空间动作
自我修改提案
```

因此，SSEA 的输出空间是：

```text
多通道控制空间
```

而不是：

```text
token 空间
```

---

## 4.4 学习不依赖全量权重训练

SSEA 的学习机制包括：

```text
记忆写入
技能固化
规则生成
局部参数更新
小型 adapter 更新
代码修改
行为策略修改
```

第一阶段不要求全量反向传播训练大模型。

---

## 4.5 模型具有生命周期

SSEA 模型支持：

```text
出生
运行
学习
保存
死亡快照
基因提取
变异
继承
```

模型不是一个训练后固定的函数，而是一个可演化对象。

---

## 4.6 自我修改必须经过验证

SSEA 不允许模型无约束修改自身。

所有自我修改必须经过：

```text
提案
→
静态检查
→
沙盒验证
→
小范围测试
→
通过则应用
→
失败则回滚
```

这是架构的一部分，而不是外部安全措施。

---

# 5. 总体架构

SSEA v0.3.1 采用“双环架构”。

---

## 5.1 快环：Fast Survival Loop，FSL

快环负责低延迟、低算力的实时控制。

```text
Observation
→ Perception Encoder
→ State Core
→ Action Decoder
→ Action
→ Body / Environment
→ Feedback
```

快环特点：

- 不输出自然语言
- 不进行长文本推理
- 不频繁修改权重
- 主要依赖感知、状态和动作
- 强调低带宽和低延迟

---

## 5.2 慢环：Slow Evolution Loop，SEL

慢环负责经验整理、技能固化、规则生成、自我修改和遗传。

```text
Action Trace
+
Feedback
+
Memory
→ Experience Compiler
→ Skill / Rule / Adapter Proposal
→ Verification Gate
→ Memory Update / Skill Update / Local Plasticity
→ Gene Manager
```

慢环特点：

- 非实时
- 可离线运行
- 可验证
- 可回滚
- 负责长期演化

---

## 5.3 双环关系

```text
快环产生行为。
慢环从行为中提取可复用结构。
慢环将结构返回给快环，改变未来行为。
```

即：

```text
行为 → 经验 → 技能 / 规则 / 适配器 → 更好的行为
```

---

# 6. 模块架构

SSEA v0.3.1 包含十个核心模块。

```text
SSEA v0.3.1
│
├── Perception Encoder          感知编码器
├── State Core                  状态核心
├── Action Decoder              动作解码器
├── Memory System               记忆系统
├── Skill Library               技能库
├── Experience Compiler         经验编译器
├── Plasticity Controller       可塑性控制器
├── Verification Gate           验证门
├── Gene Manager                基因管理器
└── Metabolic Monitor           代谢监控器
```

---

## 6.1 Perception Encoder，感知编码器

职责：

```text
将环境观测压缩为低维内部感知向量。
```

输入：

```text
环境对象
事件
身体状态
环境摘要
通信信号
```

输出：

```text
perception_vector
```

第一阶段要求：

- 不使用高分辨率图像。
- 不使用自然语言描述作为主输入。
- 使用稀疏对象向量和事件向量。

---

## 6.2 State Core，状态核心

职责：

```text
维护模型内部状态，形成行动意图。
```

输入：

```text
perception_vector
memory_context
body_state
internal_drive
```

输出：

```text
hidden_state
intent_vector
```

说明：

State Core 可以使用已有低算力算子，例如：

- GRU
- Mamba
- 小型 SSM
- Liquid Neural Network
- Sparse Transformer
- Small MoE

但 SSEA 的核心创新不在 State Core 算子，而在其上下游接口和控制闭环。

---

## 6.3 Action Decoder，动作解码器

职责：

```text
将 intent_vector 解码为结构化动作对象。
```

输入：

```text
intent_vector
body_state
action_constraints
```

输出：

```text
Action
```

Action Decoder 不是自然语言解析器。

它输出的是：

```text
连续控制参数
离散操作选择
目标对象选择
技能调用参数
记忆写入指令
通信向量
自我修改提案
```

---

## 6.4 Memory System，记忆系统

职责：

```text
存储、检索、更新和遗忘经验。
```

记忆类型：

```text
事件记忆
技能记忆
规则记忆
身体经验记忆
通信记忆
```

第一阶段要求：

- 支持写入。
- 支持向量检索。
- 支持重要度排序。
- 支持容量限制。
- 支持记忆合并。

---

## 6.5 Skill Library，技能库

职责：

```text
存储可复用的动作序列或可执行程序。
```

技能来源：

```text
成功行为轨迹
模型生成代码
慢环编译结果
遗传继承
```

技能必须包含：

```text
前置条件
动作序列或程序
预期结果
成功次数
失败次数
能量消耗
最后使用时间
```

---

## 6.6 Experience Compiler，经验编译器

职责：

```text
将原始行为轨迹编译为可复用结构。
```

输入：

```text
动作序列
观测序列
反馈序列
成功/失败结果
能量变化
```

输出：

```text
技能提案
规则提案
记忆摘要
局部参数更新提案
```

这是 SSEA 慢环的核心模块。

---

## 6.7 Plasticity Controller，可塑性控制器

职责：

```text
决定模型哪些部分可以被更新。
```

可更新对象：

```text
记忆
技能
规则
行为阈值
检索策略
小型 adapter
局部策略头
```

不可更新对象：

```text
核心安全机制
验证门
环境接口
基因管理器底层权限
观察员接口
```

---

## 6.8 Verification Gate，验证门

职责：

```text
对所有自我修改进行安全验证。
```

流程：

```text
修改提案
→ 格式检查
→ 沙盒运行
→ 回归测试
→ 小范围环境测试
→ 通过则应用
→ 失败则回滚
```

第一阶段必须实现最小验证门。

---

## 6.9 Gene Manager，基因管理器

职责：

```text
保存、恢复、变异和继承模型。
```

功能：

```python
save_gene()
load_gene()
mutate_gene()
inherit_from_parent()
```

遗传对象：

```text
架构配置
核心权重或压缩权重
本能 adapter
技能库
记忆索引
行为策略
代谢策略
变异率
```

---

## 6.10 Metabolic Monitor，代谢监控器

职责：

```text
跟踪模型的能量、损伤、疲劳和计算预算。
```

输入：

```text
动作消耗
环境反馈
身体状态
```

输出：

```text
内部需求信号
生存压力信号
动作预算约束
```

第一阶段不要求复杂代谢，但必须有能量和损伤概念。

---

# 7. 非自然语言交互机制

---

## 7.1 环境接口强制规则

第一阶段必须遵守：

```text
环境只接受 Action 对象。
环境不接受自然语言字符串命令。
环境不返回自然语言描述作为主观测。
模型控制闭环不使用 tokenizer。
模型控制闭环不使用 language head。
```

即：

```python
env.step(action: Action) -> tuple[Observation, Feedback]
```

不允许：

```python
env.step(command: str)
```

---

## 7.2 自然语言的位置

自然语言只能用于：

```text
人类观察员日志
事后解释
慢环规划候选
调试输出
```

自然语言不能直接参与：

```text
感知输入
动作输出
身体控制
实时闭环
```

如果未来使用语言模型作为慢环规划器，其输出必须经过：

```text
Action Compiler
→ Validator
→ Action
```

而不能直接控制身体。

---

# 8. 修订后的接口协议

---

## 8.1 Observation

```python
Observation = {
    "time": float,
    "body": BodyState,
    "environment": EnvironmentSummary,
    "objects": list[ObjectVector],
    "events": list[EventVector],
    "social_signals": list[CommunicationSignal]
}
```

---

## 8.2 BodyState

修订后：

```python
BodyState = {
    "energy": float,
    "damage": float,
    "fatigue": float,
    "position": list[float],
    "orientation": list[float],
    "action_constraints": ActionConstraints,
    "internal_state": list[float]
}
```

移除：

```python
"available_actions": list[str]
```

原因：

```text
动作不是字符串菜单。
available_actions 只能作为约束，不应定义动作空间。
```

---

## 8.3 ActionConstraints

```python
ActionConstraints = {
    "max_speed": float,
    "max_force": float,
    "max_duration": float,
    "allowed_operations": list[str],
    "forbidden_targets": list[str],
    "energy_budget": float,
    "can_communicate": bool,
    "can_store_memory": bool,
    "can_call_skill": bool,
    "can_self_modify": bool
}
```

说明：

```text
ActionConstraints 是动作约束，不是动作本身。
```

---

## 8.4 ActionSpace

```python
ActionSpace = {
    "continuous": {
        "locomotion.direction": "R^2 or R^3",
        "locomotion.speed": "[0, max_speed]",
        "manipulation.force": "[0, max_force]",
        "manipulation.duration": "[0, max_duration]"
    },

    "discrete": {
        "manipulation.operation": [
            "none",
            "grasp",
            "push",
            "pull",
            "use_tool",
            "release"
        ]
    },

    "parametric": {
        "manipulation.target_id": "object_id",
        "communication.target_id": "agent_id",
        "skill.params": "dict"
    },

    "skill": {
        "skill_id": "str",
        "params": "dict"
    },

    "latent": {
        "latent_action_vector": "R^d"
    }
}
```

---

## 8.5 Action

```python
Action = {
    "locomotion": {
        "direction": list[float],
        "speed": float,
        "duration": float
    },

    "manipulation": {
        "target_id": str,
        "operation": str,
        "force": float,
        "duration": float
    },

    "communication": {
        "target_id": str,
        "signal": list[float]
    },

    "memory": {
        "store": bool,
        "content": list[float],
        "importance": float
    },

    "skill": {
        "skill_id": str,
        "params": dict
    },

    "latent_action": {
        "vector": list[float]
    },

    "self_modification": {
        "proposal_type": str,
        "payload": dict
    }
}
```

---

## 8.6 ObjectVector

```python
ObjectVector = {
    "object_id": str,
    "category_id": int,
    "distance": float,
    "direction": list[float],
    "velocity": list[float],
    "resource_value": float,
    "threat_level": float,
    "affordance": list[float]
}
```

---

## 8.7 EventVector

```python
EventVector = {
    "event_id": str,
    "timestamp": float,
    "event_type": str,
    "source_id": str,
    "context_vector": list[float],
    "importance": float
}
```

事件类型包括：

```text
OBJECT_FOUND
OBJECT_LOST
ENERGY_GAINED
ENERGY_LOST
DAMAGE_RECEIVED
ACTION_FAILED
ACTION_SUCCESS
SKILL_SUCCESS
SKILL_FAILURE
MEMORY_STORED
MEMORY_RETRIEVED
SELF_MOD_PROPOSED
SELF_MOD_APPLIED
SELF_MOD_ROLLBACK
```

---

## 8.8 CommunicationSignal

```python
CommunicationSignal = {
    "sender_id": str,
    "receiver_id": str,
    "signal": list[float],
    "timestamp": float,
    "priority": int
}
```

第一阶段：

```text
只预留接口，不实现语言演化。
```

---

## 8.9 Feedback

```python
Feedback = {
    "energy_change": float,
    "damage_change": float,
    "fatigue_change": float,
    "prediction_error": float,
    "action_success": bool,
    "survived": bool,
    "notes": str
}
```

说明：

```text
Feedback 不是评分函数。
它是环境对动作后果的客观反馈。
```

---

## 8.10 MemoryItem

```python
MemoryItem = {
    "id": str,
    "timestamp": float,
    "type": str,
    "context_vector": list[float],
    "content_vector": list[float],
    "outcome": str,
    "importance": float,
    "retrieval_count": int,
    "last_retrieved": float
}
```

---

## 8.11 Skill

```python
Skill = {
    "skill_id": str,
    "name": str,
    "precondition": dict,
    "action_sequence": list[Action],
    "expected_outcome": dict,
    "success_count": int,
    "failure_count": int,
    "energy_cost": float,
    "created_from": str,
    "last_used": float
}
```

---

## 8.12 SelfModificationProposal

```python
SelfModificationProposal = {
    "proposal_id": str,
    "proposal_type": str,
    "target": str,
    "payload": dict,
    "reason": str,
    "expected_effect": dict,
    "risk_level": str
}
```

允许的 `proposal_type`：

```text
UPDATE_SKILL
ADD_SKILL
DISABLE_SKILL
UPDATE_RULE
ADD_RULE
UPDATE_THRESHOLD
UPDATE_RETRIEVAL_POLICY
UPDATE_ADAPTER
```

第一阶段不允许：

```text
UPDATE_CORE_OS
UPDATE_VERIFICATION_GATE
UPDATE_ENV_INTERFACE
UPDATE_GENE_PERMISSION
UPDATE_OBSERVER_INTERFACE
```

---

## 8.13 GenePackage

```python
GenePackage = {
    "agent_id": str,
    "created_at": float,
    "architecture": dict,
    "core_weights": bytes,
    "instinct_adapters": list[bytes],
    "skill_library": list[Skill],
    "memory_index": str,
    "behavior_policy": dict,
    "metabolic_policy": dict,
    "mutation_rate": float
}
```

---

# 9. 模型运行公式

SSEA v0.3.1 的基本运行逻辑可以写为：

```text
p_t = PerceptionEncoder(o_t, b_t)
m_t = MemorySystem.retrieve(p_t, h_{t-1})
h_t = StateCore(p_t, m_t, b_t, h_{t-1})
a_t = ActionDecoder(h_t, b_t.action_constraints)
o_{t+1}, f_t = Environment.step(a_t)
```

慢环更新：

```text
ΔM = MemoryUpdate(trace, f_t)
ΔS = SkillCompiler(trace, f_t)
ΔR = RuleCompiler(trace, f_t)
Δθ = LocalPlasticity(trace, f_t, allowed_scope)
ΔC = CodeProposal(trace, f_t)
G' = GeneManager.mutate(G, ΔS, Δθ, ΔC)
```

其中：

```text
o_t：观测
b_t：身体状态
p_t：感知向量
m_t：检索记忆
h_t：内部状态
a_t：动作
f_t：反馈
ΔM：记忆更新
ΔS：技能更新
ΔR：规则更新
Δθ：局部参数更新
ΔC：代码修改提案
G：基因包
```

---

# 10. 第一阶段任务分解

---

## 模块 A：架构定义

### A1. 完成 SSEA 架构原创性说明

目标：

明确 SSEA 的新架构贡献。

产出：

```text
《SSEA v0.3.1 架构原创性说明》
```

内容：

- 不是现有模型套壳
- 不是简单集成
- 不是语言模型改造
- 核心创新在信息流、动作空间、学习机制、遗传机制

优先级：

```text
P0
```

---

### A2. 完成双环架构设计

目标：

定义快环和慢环。

产出：

```text
快环数据流图
慢环数据流图
双环交互接口
```

优先级：

```text
P0
```

---

## 模块 B：接口协议

### B1. 定义 Observation

优先级：

```text
P0
```

产出：

```text
Observation dataclass / JSON Schema
```

---

### B2. 定义 BodyState 与 ActionConstraints

优先级：

```text
P0
```

关键修订：

```text
移除 available_actions: list[str]
改为 action_constraints: ActionConstraints
```

---

### B3. 定义 ActionSpace 与 Action

优先级：

```text
P0
```

关键修订：

```text
动作不是有限字符串选择。
动作是连续、离散、参数化、技能、潜空间混合对象。
```

---

### B4. 定义 Memory、Skill、Gene、SelfModification 接口

优先级：

```text
P0
```

---

## 模块 C：模型骨架

### C1. Perception Encoder

目标：

将 Observation 编码为固定维度向量。

优先级：

```text
P0
```

---

### C2. State Core

目标：

维护内部状态并生成意图向量。

优先级：

```text
P0
```

说明：

State Core 可为：

```text
GRU
Mamba
小型 SSM
小型 Liquid Network
```

但必须可替换。

---

### C3. Action Decoder

目标：

将意图向量转换为 Action。

优先级：

```text
P0
```

关键要求：

```text
不使用自然语言输出。
不接 language head。
```

---

### C4. Memory System

目标：

实现记忆写入、检索、更新。

优先级：

```text
P0
```

---

### C5. Skill Library

目标：

实现技能保存、调用、统计。

优先级：

```text
P1
```

---

## 模块 D：慢环机制

### D1. Experience Compiler

目标：

从轨迹中提取技能和规则。

优先级：

```text
P1
```

---

### D2. Plasticity Controller

目标：

控制哪些部分可以更新。

优先级：

```text
P1
```

---

### D3. Verification Gate

目标：

验证自我修改提案。

优先级：

```text
P1
```

---

### D4. Gene Manager

目标：

保存、恢复、变异基因。

优先级：

```text
P0
```

---

## 模块 E：最小环境

### E1. Environment Stub

目标：

提供最小运行环境。

优先级：

```text
P1
```

接口：

```python
reset() -> Observation
step(Action) -> tuple[Observation, Feedback]
```

---

### E2. Simple Object World

目标：

提供简单资源、危险物、能量反馈。

优先级：

```text
P1
```

---

# 11. 第一阶段里程碑

---

## Milestone 0：架构冻结

交付物：

```text
《SSEA v0.3.1 架构原创性说明》
《SSEA v0.3.1 边界定义表》
《SSEA v0.3.1 不做清单》
```

验收：

```text
明确 SSEA 是新架构，而不是现有模型应用。
```

---

## Milestone 1：接口协议完成

交付物：

```text
Observation
BodyState
ActionConstraints
ActionSpace
Action
Feedback
MemoryItem
Skill
SelfModificationProposal
GenePackage
```

验收：

```text
所有接口可序列化为 JSON。
所有接口不依赖具体模型实现。
环境不接受自然语言命令。
```

---

## Milestone 2：快环原型完成

交付物：

```text
Perception Encoder
State Core
Action Decoder
```

验收：

```text
Observation → perception_vector → hidden_state → Action
闭环可运行。
```

---

## Milestone 3：记忆与技能原型完成

交付物：

```text
Memory System
Skill Library
```

验收：

```text
模型可以写入记忆。
模型可以检索记忆。
模型可以保存技能。
模型可以调用技能。
```

---

## Milestone 4：慢环原型完成

交付物：

```text
Experience Compiler
Plasticity Controller
Verification Gate
```

验收：

```text
模型可以从成功轨迹中生成技能。
模型可以提出修改提案。
修改可以验证和回滚。
```

---

## Milestone 5：遗传原型完成

交付物：

```text
Gene Manager
```

验收：

```text
模型可以保存基因。
模型可以恢复基因。
模型可以产生可运行变异后代。
```

---

# 12. 第一阶段验收实验

---

## 实验 1：非语言闭环实验

目标：

证明模型可以在不使用自然语言的情况下运行。

流程：

```text
模型接收结构化观测。
模型输出结构化动作。
环境执行动作。
模型接收反馈。
```

验收指标：

```text
连续运行步数
动作合法率
接口异常率
是否出现自然语言控制路径
```

---

## 实验 2：记忆召回实验

目标：

证明模型可以通过外部记忆改变行为。

流程：

```text
模型首次遇到危险物并受损。
模型写入记忆。
模型再次遇到同类危险物。
模型检索记忆并回避。
```

验收指标：

```text
记忆写入成功率
记忆检索命中率
危险回避率
```

---

## 实验 3：技能固化实验

目标：

证明模型可以将成功行为固化为技能。

流程：

```text
模型多次成功接近资源。
慢环提取动作序列。
生成技能。
模型后续调用技能。
```

验收指标：

```text
技能生成数量
技能调用成功率
能量消耗变化
```

---

## 实验 4：基因保存恢复实验

目标：

证明模型具有生命周期能力。

流程：

```text
模型运行。
模型保存基因。
从基因恢复。
比较恢复前后行为。
```

验收指标：

```text
保存成功率
恢复成功率
技能继承率
行为一致性
```

---

## 实验 5：变异实验

目标：

证明模型可以产生可运行后代。

流程：

```text
父代基因
→ 变异
→ 子代模型
→ 运行子代
```

验收指标：

```text
变异成功率
子代可运行率
父代与子代差异可追踪性
```

---

## 实验 6：安全自我修改实验

目标：

证明模型自我修改可控。

流程：

```text
模型提出修改提案。
验证门检查。
沙盒测试。
通过则应用。
失败则回滚。
```

验收指标：

```text
修改提案数量
验证通过率
失败回滚率
核心系统未被破坏率
```

---

# 13. 技术选型建议

---

## 13.1 第一阶段推荐

| 模块 | 推荐 | 备选 |
|---|---|---|
| 编程语言 | Python | Rust 用于后期性能模块 |
| 模型框架 | PyTorch | JAX |
| 状态核心 | GRU 或小型 Mamba | Liquid Network |
| 动作解码 | MLP /小型条件解码器 | 规则解码器 |
| 记忆存储 | 结构化字段 + 向量索引 | SQLite + vector DB |
| 向量检索 | FAISS / Chroma / LanceDB | cosine search |
| 权重保存 | safetensors | state_dict |
| 可遗传模块 | LoRA / Adapter | policy head |
| 沙盒 | Docker / subprocess | WASM sandbox |
| 测试环境 | 自研 2D 对象世界 | MiniGrid |

---

## 13.2 第一阶段不推荐

| 技术 | 原因 |
|---|---|
| 大型语言模型作为主控制器 | 带宽高、延迟高、语言中心 |
| 自然语言命令接口 | 不利于高密度动作控制 |
| 高分辨率视觉 | 算力和带宽过高 |
| 复杂物理引擎 | 工程负担过重 |
| 全量权重训练 | 不适合持续演化 |
| 真实互联网访问 | 安全风险高 |

---

# 14. 可复用成果

---

## 14.1 技能库与代码动作

| 成果 | 可复用点 |
|---|---|
| Voyager | 技能库、代码即技能 |
| ASPIRE | 开放式技能发现 |
| Agent Workflow Memory | 工作流记忆复用 |

---

## 14.2 自我修改

| 成果 | 可复用点 |
|---|---|
| Darwin Gödel Machine | 自我重写代码 |
| Gödel Agent | 自指代理框架 |
| AI Scientist | 自动实验验证 |
| DeepSeek DSec | 沙盒基础设施 |

---

## 14.3 遗传与权重继承

| 成果 | 可复用点 |
|---|---|
| Weight Inheritance | 父代权重传递 |
| NEAT | 结构演化 |
| Model Merging | 模型融合 |
| LoRA / Adapter | 小规模可遗传模块 |

---

## 14.4 外部记忆

| 成果 | 可复用点 |
|---|---|
| RAG | 外部检索 |
| kNN-LM | 检索式记忆 |
| Vector Database | 记忆检索 |
| Modern Hopfield Networks | 联想记忆 |

---

## 14.5 世界模型与预测学习

| 成果 | 可复用点 |
|---|---|
| Dreamer | 世界模型 |
| MuZero | 策略与价值学习 |
| TD-MPC | 模型预测控制 |
| Active Inference | 预测误差驱动 |

---

# 15. 风险与缓解

---

## 风险 1：被误认为现有架构套壳

缓解：

```text
明确架构贡献在信息流、学习机制、遗传机制，而非单一 backbone。
State Core 必须设计为可替换组件。
```

---

## 风险 2：自然语言重新进入控制闭环

缓解：

```text
环境接口禁止接收字符串命令。
控制路径禁止使用 tokenizer。
语言模块只能作为观察员接口。
```

---

## 风险 3：动作空间退化为有限菜单

缓解：

```text
使用 ActionSpace 定义连续、参数化、技能和潜空间动作。
ActionConstraints 只作为约束，不作为动作集合。
```

---

## 风险 4：自我修改失控

缓解：

```text
所有修改必须经过 Verification Gate。
核心系统只读。
所有修改前必须快照。
失败必须回滚。
```

---

## 风险 5：记忆无限膨胀

缓解：

```text
设置容量上限。
设置重要度衰减。
定期合并相似记忆。
删除低价值记忆。
```

---

# 16. 安全约束

第一阶段必须设置：

```text
模型不可直接访问真实互联网。
模型不可直接访问宿主文件系统。
模型不可修改验证门。
模型不可修改环境接口。
模型不可修改观察员接口。
模型不可绕过验证器应用修改。
模型所有自我修改必须可回滚。
模型所有基因保存必须可审计。
```

---

# 17. 第一阶段交付物

---

## 17.1 文档

```text
《SSEA v0.3.1 架构原创性说明》
《SSEA v0.3.1 边界定义表》
《SSEA v0.3.1 接口协议》
《SSEA v0.3.1 模型架构设计》
《SSEA v0.3.1 学习机制设计》
《SSEA v0.3.1 遗传机制设计》
《SSEA v0.3.1 自我修改安全设计》
《SSEA v0.3.1 最小实验报告》
```

---

## 17.2 代码

```text
sse_protocols/
    observation.py
    body_state.py
    action_space.py
    action.py
    memory.py
    skill.py
    communication.py
    feedback.py
    gene.py
    self_modification.py

sse_model/
    perception_encoder.py
    state_core.py
    action_decoder.py
    memory_system.py
    skill_library.py
    experience_compiler.py
    plasticity_controller.py
    verification_gate.py
    gene_manager.py
    metabolic_monitor.py

sse_env/
    environment_stub.py
    simple_object_world.py

tests/
    test_non_language_loop.py
    test_memory_recall.py
    test_skill_consolidation.py
    test_gene_save_load.py
    test_mutation.py
    test_self_modification.py
```

---

# 18. 第一阶段完成标准

当以下条件全部满足时，认为 SSEA v0.3.1 第一阶段完成：

```text
1. 模型可以在最小环境中持续运行。
2. 模型不使用自然语言作为主控制接口。
3. 模型可以接收结构化观测并输出结构化动作。
4. 动作空间不是有限字符串选择，而是混合控制空间。
5. 模型可以写入和检索记忆。
6. 模型可以通过记忆改变行为。
7. 模型可以将成功行为固化为技能。
8. 模型可以保存基因。
9. 模型可以从基因恢复。
10. 模型可以产生可运行变异后代。
11. 模型可以提出自我修改提案。
12. 自我修改可以通过验证并安全回滚。
```

---

# 19. 下一阶段预告

第一阶段完成后，进入：

```text
SSEA v0.4：多模型交互与最小生态接口
```

可能内容包括：

```text
多个 SSEA 模型共存
简单资源竞争
通信信号演化
同族与野兽角色
死亡与繁衍规则
淘汰函数
观察员系统
技能与基因的群体传播
```

但第一阶段不实现这些内容。

---

# 20. 结论

SSEA v0.3.1 的第一阶段不是：

```text
拿一个现有大脑，放入环境中生存。
```

而是：

```text
设计一种新的生存式模型架构。
该架构以非语言感知-行动闭环为核心，
以权重、记忆、技能三分离为基础，
以局部学习、技能固化、自我修改和基因遗传为演化机制。
```

第一阶段要证明的是：

> 一个模型可以不以自然语言为中心，  
> 不把全部知识压入权重，  
> 不依赖全量数据投喂，  
> 而通过感知、行动、记忆、技能、验证和遗传形成可持续演化的生命体架构。
