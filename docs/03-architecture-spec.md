# 03 · 架构规范（当前权威）

**项目**：SSEA — Survival-based Self-Evolving Agent Architecture（生存式自演化代理架构）
**版本**：v0.3.1，第一阶段（不建生态系统，只建「能进入生态系统的最小生命体」）

本规范由两部分构成，是动手写代码前的权威依据：

<a id="part-i"></a>
## Part I · v0.3.1 第一阶段任务书

> **权威说明**：Part I 为任务书原文；其第 5、6、8、9 节及运行公式已被 Part II 修订。
> **凡 Part I 与 Part II 冲突，一律以 Part II 为准。**
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
<a id="part-ii"></a>
## Part II · 双环接口与模糊地带补全（对 Part I 的 13 处修订）

> 本 Part 对 Part I 的 13 处模糊地带给出补全设计，是实现接口协议与快环原型前的必读；
> 关键新增：Skill Runner（第 11 个模块）、睡眠期一等公民状态、惊奇估计器、结构注入面。
**文档性质**：补全设计 / 任务书 07 的修订依据
**修订对象**：[Part I](#part-i)（当前有效任务书）
**产生原因**：逐条核对 v0.3.1 后发现 13 处模糊地带，其中 7 处阻塞 Milestone 1（接口协议）与 Milestone 2（快环原型）；另发现 1 项模块数变更
**覆盖方式**：本文 2.1–2.6 覆盖 7 处阻塞项（2.6 一节含两项），3.1–3.7 覆盖其余 6 处加模块数变更
**本阶段边界**：只补设计，不重写任务书，不写模型代码

---

## 1. 补全的裁判标准

模糊地带一律按以下十条推导。任何结论若无法回溯到其中至少一条，即视为偏离 SSEA 立场，不予采纳。

| #   | 约束                                  | 出处                 |
| --- | ----------------------------------- | ------------------ |
| C1  | 生存控制架构，非语言生成架构                      | 07 修订二、4.1         |
| C2  | 自然语言只作观察员接口，不进控制闭环                  | 07 修订二、7.2         |
| C3  | 权重 / 记忆 / 技能三分离                     | 07 4.2             |
| C4  | 低算力、低带宽                             | README 项目目标、07 5.1 |
| C5  | 精准回忆历史                              | README 项目目标        |
| C6  | 可自主修改自身代码与参数权重                      | README 项目目标        |
| C7  | 可保存 / 恢复 / 变异 / 继承                  | README 项目目标、07 4.5 |
| C8  | 给基因先验，不给知识语料                        | 03 第九节             |
| C9  | 不设**外部**评分函数，只有淘汰函数（内在驱动是第三层信号，见 §8.1） | 01 原始构想、07 8.9；**2026-09-28 修订，见 §8.1** |
| C10 | 创新在 L2 信息流 / L3 学习 / L4 演化，不在 L1 算子 | 06 问题 1、07 2.1     |

---

## 2. P0 补全设计（阻塞 Milestone 1 / 2，共 7 处）

七个阻塞项分布在 2.1–2.6 六节中，其中 2.6 一节含两项（`prediction_error` 无生产者、`ActionConstraints` 无强制执行点）。

### 2.1 双环注入接口 —— Structure Injection Surface

**症状**

07 第 5.3 节只有一句：

> 慢环将结构返回给快环，改变未来行为。

未定义四件事：返回什么结构、何时返回、失败怎么办、快环如何消费。Milestone 2 要写快环代码，这件事不落地就无法开工。

**约束推导**

| 需求 | 来自 |
|---|---|
| 注入机制必须内建安全性，不能靠外部锁/事务 | 07 4.6："这是架构的一部分，而不是外部安全措施" |
| 注入不能每步发生 | 07 5.1 快环特点："不频繁修改权重、低带宽低延迟"（C4） |
| 注入物必须是 权重/记忆/技能 三类结构，不能是裸梯度 | C3 |
| 注入物必须能进 GenePackage，可遗传可审计 | C7 |

**设计**

慢环不调用快环。慢环只**发布结构的新版本**，快环只**读取当前版本**。

```
                    ┌────────────────────────────────┐
                    │        Verification Gate       │
                    │  格式 → 沙盒 → 回归 → 小范围环境 │
                    └───────────────┬────────────────┘
                                    │ pass
                                    ▼
                    ┌────────────────────────────────┐
                    │   Structure Store（版本化）      │
                    │   skills@v7      rules@v3       │
                    │   adapters@v2    thresholds@v5  │
                    │   retrieval@v1                  │
                    └───────────────┬────────────────┘
                                    │ 原子切换版本号
                                    ▼
  ┌──────────────┐   read   ┌────────────────────────────────┐
  │   快环 FSL    │ ◄─────── │  FastLoopContext（不可变快照）  │
  │              │          │  {skills, rules, adapters,     │
  │              │          │   thresholds, retrieval}       │
  └──────────────┘          └────────────────────────────────┘
```

四条性质，逐条对应上表的约束：

- **快环零改动** —— 快环代码只读 `FastLoopContext`，不知道慢环存在；换版本 = 换句柄。（C4）
- **失败天然回滚** —— Gate 不通过则版本号不切换，快照继续用旧版。**不存在"回滚"这个操作，因为从未应用**。（07 4.6）
- **可遗传** —— `FastLoopContext` 的内容就是 GenePackage 的 `skill_library` / `instinct_adapters` / `behavior_policy` 的直接来源。注入面是遗传面的子集，两套机制共用一份结构定义。（C7、C3）
- **可审计** —— 每次版本切换记录 `(proposal_id, from_v, to_v, gate_result, timestamp)`。（C7）

**注入物五类**（严格落在三分离内，不含裸梯度）：

| 注入物 | 落入 | 快环消费点 |
|---|---|---|
| SkillProposal | 技能 | Action 的 `skill` 通道 |
| RuleProposal | 规则 | State Core 的门控 / 偏置 |
| AdapterProposal | 权重 | State Core 的可插拔算子 |
| ThresholdProposal | 行为策略 | Action Decoder 决策阈值 |
| RetrievalPolicyProposal | 记忆策略 | Memory System 检索参数 |

**对任务书的改动**：第 5 节新增 5.4「结构注入面」小节；第 6 节模块清单新增 Structure Store 与 FastLoopContext 两个数据组件（非计算模块）。

---

### 2.2 慢环触发器与睡眠期

**症状**

07 第 5.2 节只说慢环"非实时、可离线运行、可验证、可回滚"，**从未说何时触发**。v0.3.1 全文没有"睡眠"二字。

**约束推导**

睡眠期不是工程便利，是补上 doc 01 留下的空白。doc 01 原话：

> 生存压力和美好需要定义

doc 02 给了四个候选（好奇心与惊奇感、心流状态、社会性连接、记忆回放的安宁），v0.3.1 把"美好"整体删掉了。若慢环无触发时机，"美好"在第一阶段继续无定义。

**设计**

| 触发器 | 条件 | 性质 |
|---|---|---|
| **SLEEP** | 代谢监控器判定：无迫近威胁 + 疲劳累积 | 慢环的**唯一常规入口** |
| **DEATH_SNAPSHOT** | 环境判定死亡前 | 最终编译 + 基因快照 |

睡眠期设计为**一等公民状态**，与 RUN 并列，不是调试功能。

> **睡眠期即"美好"的第一阶段可操作定义：在安全时允许无损整理经验，这本身就是系统给予的美好。**

这让慢环不只是工程便利——模型主动获得一段无生存压力、无预测误差惩罚的时间来整理自身，是系统给予的偶然温暖（对应 doc 01"系统给予模型生存压力，同时又给予模型偶然的美好"）。

**2026-09-27 修订：SLEEP 的条件从三条减为两条。** 原文第三条是「能量充足」
（`energy ≥ 0.7`），实施后实测发现**那一条必须移除**，理由有两条：

1. 它与「疲劳累积」在默认代谢参数下**算术互斥**——能量单调降、疲劳单调升，
   合取取到的是**空集**而非窄入口。实测 8 个 seed **0/8 进入过睡眠**。
2. 更根本的是，`Environment.rest()` 不扣基础代谢、反而每帧 `+0.01` 能量，
   于是「能量充裕」是睡眠自己生产的前提，拿它当门槛构成**正反馈**：
   实测 `safe ∧ energy ≥ 0.7` 下 4/8 seed 锁进睡-醒循环，**65%–72% 的寿命
   在睡眠中度过**却几乎不产出提案（**模型学会了不行动**），另 4/8 seed 从不睡眠。
   后一条正是上面那句「若睡眠也耗能……慢环的唯一常规入口会被生存压力挤掉」
   的**反面**：睡眠既然不耗能，就不该反过来用能量把它关掉。

上方「在**安全**时允许无损整理经验」这句原始推导本就**只提安全一个条件**，
是条件表把它扩成了三条。修订即回到原推导：**安全是本质条件，疲劳是自然的
进入理由，能量不参与判定。**「入口必须窄」由疲劳单独承担——它是自限的
（睡眠每帧恢复 0.15，醒来归零，约 30 帧不应期），而能量没有不应期、只有正反馈。

实测修正后 **8/8 seed 可达**（2026-09-28 复跑，8 个 seed 全部进入过睡眠；
记录原为 7/8，见 [12](06-status-roadmap.md) §6 债务 25）、睡眠占寿命 6%–12%。完整推导与数字见
[06-status-roadmap.md](06-status-roadmap.md) §6.3.1 与
[06-status-roadmap.md](06-status-roadmap.md) §6.6；
实现见 `SSEA/metabolic_monitor.py::MetabolicMonitor.wants_sleep`。

**对任务书的改动**：第 5 节新增 5.5「慢环触发时机」；第 6.10 代谢监控器增补睡眠判定条件；第 12 节验收实验增补一项睡眠期实验（见第 4 节）。

> **2026-09-28 扩展**：本节定义的睡眠期只挂了**回顾编译**一条通路。
> 裁决三已将其扩为「**回顾编译 + 前瞻预演**」双通路，权威条款见 §8.3。
> ⚠️ 本节登记的「一次睡眠够不够跑完整条慢环流程」这个疑问**至今未定义**，
> 而它现在是实现前瞻预演的**硬门槛**（§8.3 第 1 条）。

---

### 2.3 Skill Runner（第 11 个模块）

**症状**

07 第 8.11 节定义：

```python
Skill = {
    ...
    "action_sequence": list[Action],
    ...
}
```

但快环公式每步只产出一个动作：

```
a_t = ActionDecoder(h_t, b_t.action_constraints)
o_{t+1}, f_t = Environment.step(a_t)
```

十个模块里**没有一个**负责把 `list[Action]` 逐帧执行。技能被定义了，却无法运行。

**约束推导**

若让 Environment 执行序列，违背 07 7.1「环境只接受原子 Action」的强制规则，且让环境承担模型内部语义。若把 Skill 降级为单步参数化策略，则丢失多步行为压缩，实验 3 的「能量消耗变化」指标失去意义。

**设计**

新增 **Skill Runner**，置于 Action Decoder 之后、Environment 之前：

```
State Core → intent_vector
                  ↓
          Action Decoder → Action
                  ↓
          Skill Runner ← 若 skill 通道非空：查 Skill Library，
          │               取 action_sequence，按 params 实例化，
          │               逐帧吐出子动作（每步一个）
          ↓
          Environment.step(sub_action)
```

**中止条件**（任一命中即中断并回报 `SKILL_FAILURE`）：

- 前置条件 `precondition` 不再满足
- 能量低于该技能 `energy_cost` 的剩余需求
- 环境变化使后续子动作非法（由 Environment 第二执行点检出）

正常完成后回报 `SKILL_SUCCESS`，并累计 `success_count` / `failure_count` / `last_used`。

**SSEA 意义**：技能是压缩的行为先验，**查表比每步重新推理更省算力**。这是 C4「低算力」真正的落地机制，也解释了为什么技能库增长不会导致算力爆炸——技能是查表，不是搜索。

**对任务书的改动**：第 6 节模块清单加入 Skill Runner；第 6.5 技能库增补"由 Skill Runner 执行"的所有权说明；第 8.11 Skill 协议增补 `precondition` 的检查方；第 9 节快环公式插入一行。

---

### 2.4 移除 `latent_action`

**症状**

07 第 8.5 节 Action 协议含：

```python
"latent_action": {
    "vector": list[float]
},
```

全文没有任何模块或环境消费它。它是一个永远为空的死字段。

**约束推导**

07 7.1 规定"环境只接受 Action 对象"，但未规定每个 Action 字段都必须可执行。引入一条明文约束：

> **动作必须可执行。协议中不允许存在无消费者的通道。**

否则 Milestone 1 会把一个无法验证的字段写进协议，且后续每轮修订都要重新解释它是什么。

**设计**

- Action 协议**删除** `latent_action` 字段
- 潜空间职责由 State Core 输出的 `intent_vector` 承担（模型内部表示，不进入协议）
- 对外的潜空间通道**仅保留** `CommunicationSignal.signal` —— 这正对应 doc 01 的原始构想：

> 能否直接让模型之间以二进制或其它方式交流形成模型自身的语言

即：潜空间是模型间"自身语言"的雏形，不是身体动作。第一阶段只预留接口，不实现语言演化（与 07 8.8 一致）。

**对任务书的改动**：8.5 Action 协议删除 `latent_action` 块；8.4 ActionSpace 删除 `latent` 子块；新增明文约束"动作必须可执行"。

---

### 2.5 `internal_drive` 与 Metabolic Monitor 输出接线

**症状**

07 第 6.2 节列 State Core 输入含 `internal_drive`，但第 9 节运行公式里**没有它**：

```
h_t = StateCore(p_t, m_t, b_t, h_{t-1})
```

同时第 6.10 节说代谢监控器输出"内部需求信号、生存压力信号、动作预算约束"三个信号——这三个信号**没接回任何公式**。模块定义了，线没接。

**约束推导**

C9 要求不设**外部**评分函数（2026-09-28 修订，见 §8.1），但模型必须有内在生存动力，否则会退化成不动（07 风险 5）。这三个信号就是替代**外部**评分函数的内在驱动来源，必须接线，否则风险 5 的缓解措施落空。

> ⚠️ **本节是 C9 修订的直接起因**：这里明确要接线「内在驱动」，而 C9 旧表述写的是
> 「不设评分函数」——两者在同一份文档里并存了很久，且没有任何红灯。
> §8.1 的三层信号表就是为消除这处矛盾而写的。

**设计**

代谢监控器产出统一向量：

```python
internal_drive_vector = [
    energy_deficit,    # 能量缺口（归一化）
    surprise_ema,      # 惊奇指数滑动平均（来自 SurpriseEstimator，见 2.6）
    damage_urgency,    # 损伤紧迫度 —— 第一阶段置 0 预留
    fatigue,           # 疲劳度   —— 第一阶段置 0 预留
]
```

该向量有两个消费点：

1. **State Core 的 `internal_drive` 输入** —— 对应 doc 02 的内在动机设计（好奇心与惊奇感）
2. **Action Decoder 的能量预算约束来源** —— 与 `b_t.action_constraints` 合并后作为约束输入

`energy_deficit` 与 `surprise_ema` 第一阶段实现，其余置 0 预留（符合 C8：给结构先验，不给满能力）。

**对任务书的改动**：第 9 节快环公式 StateCore 增补 `d_t` 参数、ActionDecoder 增补 `d_t` 参数；6.10 代谢监控器输出定义改为 `internal_drive_vector`。

---

### 2.6 SurpriseEstimator 与约束强制执行

#### 2.6.1 SurpriseEstimator（补 `prediction_error` 的生产者）

**症状**

07 第 8.9 节 Feedback 含 `prediction_error`，但 v0.3.1 的十个模块里**没有 World Model、没有 Predictor**。字段无生产者。

**约束推导**

doc 03 第一节明确：

> 没有显式评分函数，但有：预测误差、生存误差、能量消耗、死亡。

预测误差是 SSEA 替代评分函数的核心学习信号（C9）。若第一阶段就把它置空，Milestone 4 慢环的「规则生成」将失去触发器——重复因果关系正是从预测误差中提炼的。届时必须返工。

**设计**

SurpriseEstimator 作为 **Metabolic Monitor 的子组件**（不单列为第 12 个模块，因其零权重、无梯度、纯统计）。

对三类标量流做**一阶持久化预测**：

| 标量流 | 预测假设 | 来源 |
|---|---|---|
| `energy` | 下一帧 = 当前帧 | BodyState |
| `damage` | 下一帧 = 当前帧 | BodyState |
| `nearest_resource_dist` | 下一帧 = 当前帧 | ObjectVector |

```
prediction_error_t = mean(|实际_t − 预测_t|)   # 三类归一化后取均值
```

写入 `f_t.prediction_error`，并经 EMA 进入 `internal_drive_vector.surprise_ema`（见 2.5）。

**为什么不引入 World Model**：07 第 13.2 节明确不推荐重模块；一阶持久化预测只需几行代码即可让慢环有触发器，完整状态转移模型留到 v0.4+。

**对任务书的改动**：6.10 代谢监控器增补 SurpriseEstimator 子组件定义；8.9 Feedback 的 `prediction_error` 增补生产者说明。

#### 2.6.2 约束强制执行点

**症状**

`ActionConstraints` 定义了 `max_speed` / `allowed_operations` / `forbidden_targets` / `can_self_modify` 等，但模型输出违规动作时，**谁拒绝**未定义。

**设计**：双点强制执行。

| 执行点 | 职责 |
|---|---|
| **Action Decoder（第一）** | 模型内、本就接收 `action_constraints` 作为输入，输出前即裁剪/否决。这是主路径 |
| **Environment（第二）** | 防御性复核。检出非法 Action 时**不崩溃**，记 `ACTION_FAILED` 事件并返回 `action_success=False` |

第二点是必要的：Skill Runner 吐出的子动作序列可能跨越多个步长，期间约束可能变化（如 `energy_budget` 下降），Environment 必须能兜住。

**对任务书的改动**：6.3 Action Decoder 增补第一执行点职责；8.3 ActionConstraints 增补强制执行说明。

---

## 3. P1 / P2 补全设计（阻塞 Milestone 3 / 4 / 5）

其余 6 处模糊地带加 1 项模块数变更，共 7 项。按同一四段式，只记结论与改动条款。

### 3.1 `ΔC = CodeProposal` 折叠进 `ΔS`

**症状**：慢环公式有 `ΔC = CodeProposal(trace, f_t)`，但十个模块里没有代码提案模块；且 8.12 允许的 `proposal_type` 列表里**没有 CODE 类型**。产物是孤儿。

**推导**：C6 要求可自主修改自身代码，但 07 第 16 节安全约束要求"所有自我修改必须可回滚"。第一阶段开放任意代码执行违背此条。

**设计**：第一阶段不开放任意代码执行。`ΔC` 折叠进 `ΔS`——代码仅作为 `Skill.action_sequence` 内的代码段存在，归入 `ADD_SKILL` / `UPDATE_SKILL` 两类提案，从而自动经过 Verification Gate。

**改动**：慢环公式删除 `ΔC` 独立项；8.12 增补说明"第一阶段代码只能以技能代码段形式存在"。

### 3.2 `ΔM` 补入 `GeneManager.mutate`

**症状**：`G' = GeneManager.mutate(G, ΔS, Δθ, ΔC)` 漏了 `ΔM`，但 GenePackage 又含 `memory_index`。记忆更新到不了基因。

**推导**：C7 要求模型可保存 / 恢复 / 变异 / 继承。基因包若只带技能与权重而不带任何记忆，"继承"就退化成"继承行为模板"——而 doc 01 明确要传递"知识、思想"。同时 C3 三分离中记忆是独立一类，基因包必须为它留出入口。

**设计**：新增 HeritableFilter，公式改为：

```
ΔM_h = HeritableFilter(ΔM)
G' = GeneManager.mutate(G, ΔS, Δθ, ΔM_h)
```

筛选规则见 3.3。

**改动**：第 9 节慢环公式；6.6 经验编译器增补 HeritableFilter 职责。

### 3.3 `memory_index` 继承语义

**症状**：`memory_index: str` 只是一个字符串。子代拿到的是指针还是副本？哪些记忆可遗传？未定义。

**推导**：doc 01 原话"将自身的知识、思想等传递到下一代或内化成类似本能传递到下一代"（C7）；同时 07 风险 5 要求记忆不可无限膨胀（C4/C5）。

**设计**：记忆分两类，继承策略不同。

| 类别 | 类型 | 继承策略 |
|---|---|---|
| **可继承记忆** | `RULE` / `SKILL`，且 `importance ≥ 阈值` 且 `retrieval_count ≥ N` | 复制进子代 `heritable_memory` |
| **瞬时记忆** | `EVENT` / `BODY_EXPERIENCE` | 只留 `memory_store_ref` 引用，子代**不加载**，仅供审计与观察员 |

GenePackage 协议变更：

```python
GenePackage = {
    ...
    "heritable_memory": list[MemoryItem],   # 新增：已筛选的可继承记忆副本
    "memory_store_ref": str,                # 原 memory_index，更名，仅审计用
    ...
}
```

这同时落地了 07 风险 5 的缓解措施：子代不继承瞬时记忆，记忆规模不随世代累积。

**改动**：8.13 GenePackage 协议；8.10 MemoryItem 增补可继承性筛选字段说明。

### 3.4 instinct adapter 内化规则

**症状**：GenePackage 含 `instinct_adapters: list[bytes]`，Plasticity Controller 可更新"小型 adapter"，但**学习得到的 adapter 如何变成"本能"**无规则。

**推导**：这正是 doc 01 的核心目标之一——"内化成类似本能传递到下一代"。v0.3.1 列了字段却无转换规则，等于目标被静默搁置。

**设计**：AdapterProposal 可携带来源标记：

```python
"origin": "consolidated_from:<skill_id>"
```

**内化条件**（任一技能满足即由 Experience Compiler 提议内化）：

- 该技能 `success_count ≥ K`
- 且被 Skill Runner 累计执行的帧数 ≥ F

产物写入 `instinct_adapters`，可遗传。这是 doc 01"本能内化"的第一阶段最小实现——**本能 = 被反复验证后压缩成权重形式的行为先验**，与 C3 三分离一致：技能是行为，adapter 是权重，二者可互相转化但存储位置不同。

**改动**：8.12 SelfModificationProposal 增补 `origin` 语义；6.7 可塑性控制器增补内化条件。

### 3.5 `architecture` 变异禁止

**症状**：`mutation_rate` 未说明作用范围；doc 04 提过 NEAT / HyperNEAT 结构演化，易误解为第一阶段开放。

**设计**：**不允许结构变异**。`architecture` 仅作配置记录与遗传；`mutation_rate` 只作用于 adapter / 阈值 / 技能参数三类，不作用于网络结构。NEAT 式结构演化留至 v0.4+。

理由：C10 明确 SSEA 的创新不在 L1 算子层；第一阶段改结构只会让变异实验（实验 5）的"差异可追踪性"退化成不可比。

**改动**：6.9 基因管理器增补禁止条款；8.13 GenePackage 的 `mutation_rate` 增补作用范围说明。

### 3.6 死亡判定权归属

**症状**：Metabolic Monitor 跟踪能量/损伤，但 07 第 16 节安全约束说"模型不可修改淘汰函数"——暗示淘汰函数存在于某处，未说在哪。

**设计**：**环境拥有淘汰函数**。死亡由 Environment 判定（`energy ≤ 0` 或 `damage ≥ max`）。Metabolic Monitor 是模型侧的**预测与预算镜像**，不拥有判定权。

这使安全约束天然成立——淘汰函数在模型之外，模型物理上碰不到它。也符合 C9：淘汰是环境对模型的筛选，不是模型对自己的评分。

**改动**：写入边界表（见 3.7）；6.10 代谢监控器增补"不拥有死亡判定"。

### 3.7 模块数从 10 变 11

**推导**：此项不是独立设计，是 2.1 与 2.3 的必然结果——2.3 新增 Skill Runner 使计算模块变为 11 个，2.1 新增 Structure Store 与 FastLoopContext 两个数据组件。C10 要求创新落在 L2 信息流层，模块清单必须如实反映信息流的变化，否则任务书与实现脱节。

**设计**：模块清单更新为：

```
SSEA v0.3.1（经 08 修订）
│
├── Perception Encoder          感知编码器
├── State Core                  状态核心
├── Action Decoder              动作解码器
├── Skill Runner                技能执行器          ← 新增（第 11 模块）
├── Memory System               记忆系统
├── Skill Library               技能库
├── Experience Compiler         经验编译器
├── Plasticity Controller       可塑性控制器
├── Verification Gate           验证门
├── Gene Manager                基因管理器
└── Metabolic Monitor           代谢监控器
     └── SurpriseEstimator      惊奇估计器          ← 子组件，非独立模块
```

另有两个**数据组件**（非计算模块）：`Structure Store` 与 `FastLoopContext`，见 2.1。

**改动**：第 6 节模块清单。

---

## 4. 更新后的运行公式

### 4.1 快环（FSL）

```
p_t = PerceptionEncoder(o_t, b_t)
m_t = MemorySystem.retrieve(p_t, h_{t-1})              # 受 retrieval_policy 约束，非每步全量检索
d_t = MetabolicMonitor.drive(p_t, b_t)                 # 新增：internal_drive_vector
h_t = StateCore(p_t, m_t, b_t, d_t, h_{t-1})           # 修正：补 d_t
a_t = ActionDecoder(h_t, b_t.action_constraints, d_t)  # 修正：补 d_t
u_t = SkillRunner(a_t, ctx.skills)                     # 新增：逐帧吐子动作
o_{t+1}, f_t = Environment.step(u_t)
f_t.prediction_error = MetabolicMonitor.surprise(o_t, o_{t+1})   # 新增
```

### 4.2 慢环（SEL）

```
触发条件: SLEEP | DEATH_SNAPSHOT

ΔM   = MemoryUpdate(trace, f_t)
ΔM_h = HeritableFilter(ΔM)                             # 新增
ΔS   = SkillCompiler(trace, f_t)                       # 已含原 ΔC（代码段）
ΔR   = RuleCompiler(trace, f_t)
Δθ   = LocalPlasticity(trace, f_t, allowed_scope)

for p in ExperienceCompiler(ΔM, ΔS, ΔR, Δθ):
    gate = VerificationGate(p)                         # 格式→沙盒→回归→小范围环境测试
    gate.pass ? StructureStore.commit(p, v + 1) : reject(p)

G' = GeneManager.mutate(G, ΔS, Δθ, ΔM_h)               # 修正：补 ΔM_h，去 ΔC
```

### 4.3 睡眠期状态机

```
        ┌──────┐
        │ RUN  │ ◄────────────────┐
        └──┬───┘                  │
           │ 代谢判定：无迫近威胁    │ 慢环完成，结构新版本已提交
           │ + 疲劳累积             │
           ▼                      │
        ┌──────┐            ┌──────────┐
        │ SLEEP│ ─────────► │  WAKE    │
        └──┬───┘            └──────────┘
           │ 触发 SEL
           ▼
        ┌──────────┐
        │  SEL     │ → StructureStore.commit() → FastLoopContext 换版
        └──────────┘

任意状态 + 环境判定死亡 ──► DEATH_SNAPSHOT ──► 最终 SEL + GeneManager.save()
```

**SEL 内部的两条通路**（2026-09-28 扩展，权威条款见 §8.3）：

```
        ┌─────────── SEL（同一个 SLEEP 窗口、同一个预算）───────────┐
        │                                                          │
        │  ① 回顾编译（既有）  trace + feedback ─► ΔS/ΔM/ΔR/Δθ       │
        │         │                          **优先**，预算先给它    │
        │         ▼                                                │
        │  ② 前瞻预演（新增）  当前状态 + 已有技能 ─► 预演候选        │
        │         │            仅在①已提交且预算有剩余时启动         │
        │         ▼                                                │
        │    两条通路的产物**汇入同一条出口**：                       │
        │    VerificationGate（四级）─► StructureStore.commit()      │
        └──────────────────────────────────────────────────────────┘
```

⚠️ 预演通路**只拥有提案权**，与回顾通路完全同级；**不得绕过 Gate**直接写技能
（否则支柱 8 的四权分立出现缺口）。评价预演候选只能用它自己的前向模型预测后果，
**不得引入外部评分**（守 §8.1 修订后的 C9）。

---

## 5. 修订条款汇总表

供后续 v0.3.2 任务书机械套用。

| 任务书章节 | 现状 | 改为 |
|---|---|---|
| 第 5 节 | 5.1 快环 / 5.2 慢环 / 5.3 双环关系 | 增补 5.4 结构注入面、5.5 慢环触发时机 |
| 第 6 节 模块清单 | 10 个模块 | 11 个模块（+Skill Runner），SurpriseEstimator 列为代谢监控器子组件 |
| 6.3 Action Decoder | 职责描述 | 增补"约束第一执行点" |
| 6.5 Skill Library | 职责描述 | 增补"由 Skill Runner 执行" |
| 6.6 Experience Compiler | 职责描述 | 增补 HeritableFilter |
| 6.9 Gene Manager | 职责描述 | 增补"禁止结构变异" |
| 6.10 Metabolic Monitor | 输出三个信号 | 改为 `internal_drive_vector` + SurpriseEstimator + 睡眠判定 + 不拥有死亡判定 |
| 8.3 ActionConstraints | 字段定义 | 增补强制执行说明 |
| 8.4 ActionSpace | 含 `latent` 块 | 删除 `latent` 块 |
| 8.5 Action | 含 `latent_action` | 删除 `latent_action` 块；新增明文约束"动作必须可执行" |
| 8.9 Feedback | `prediction_error` 无说明 | 增补生产者（SurpriseEstimator） |
| 8.10 MemoryItem | 字段定义 | 增补可继承性筛选说明 |
| 8.11 Skill | 字段定义 | 增补 `precondition` 检查方为 Skill Runner |
| 8.12 SelfModificationProposal | `proposal_type` 列表 | 增补 `origin` 语义；增补"第一阶段代码只能以技能代码段形式存在" |
| 8.13 GenePackage | 含 `memory_index` | 增补 `heritable_memory`；`memory_index` 更名 `memory_store_ref`；`mutation_rate` 增补作用范围 |
| 第 9 节 运行公式 | 快环 5 行 / 慢环 5 行 | 按 4.1 / 4.2 替换 |
| 第 11 节 里程碑 | Milestone 0–5 | 不变；Milestone 2 验收增补 Skill Runner |
| 第 12 节 验收实验 | 实验 1–6 | 增补实验 7「睡眠期编译实验」 |
| 第 18 节 完成标准 | 12 条 | 不变；第 2 条措辞对齐"动作必须可执行" |
| 第 1 节 核心目标 | "不缩减智力" | 改为"保留语言之下的完整认知基底 + 明列放弃项"（**§8.2**） |
| 第 8 节 裁判标准 C9 | "不设评分函数，只有淘汰函数" | 改为"不设**外部**评分函数"，并补三层信号表（**§8.1**） |
| 第 5.5 节 慢环触发时机 | 睡眠期只挂回顾编译 | 增补**前瞻预演**第二通路；前置条件为睡眠期计算预算已定义（**§8.3**） |

---

## 6. 建议增补的验收实验 7

**睡眠期编译实验**

目标：证明慢环可以在一等公民状态中被触发，且注入可回滚。

流程：

```
模型运行至无迫近威胁、疲劳累积
→ 代谢监控器判定进入 SLEEP
→ 触发慢环：ExperienceCompiler 产出提案
→ Verification Gate 分别放过与驳回若干提案
→ StructureStore 只提升被放过提案的版本号
→ WAKE，快环读取新 FastLoopContext
→ 验证被驳回的提案对应的行为未改变
```

验收指标：

```
睡眠进入率
慢环触发成功率
提案验证通过率
被驳回提案对应的行为未改变率
版本切换审计记录完整率
```

---

## 7. 与 Milestone 1 的关系

Milestone 1 的接口协议代码化（`sse_protocols/`）应直接按本文第 5 节的修订条款实现，而非按 07 第 8 节原文。具体影响：

| 协议文件 | 影响 |
|---|---|
| `action_space.py` | 删除 `latent` 块 |
| `action.py` | 删除 `latent_action` 块 |
| `body_state.py` | `action_constraints` 增补强制执行语义 |
| `feedback.py` | `prediction_error` 由 SurpriseEstimator 产出 |
| `memory.py` | 增补可继承性筛选字段 |
| `skill.py` | `precondition` 检查方为 Skill Runner |
| `self_modification.py` | 增补 `origin`；代码段只走技能提案 |
| `gene.py` | 增补 `heritable_memory`；`memory_index` → `memory_store_ref` |

新增两个协议组件：`structure_store.py`（版本化结构存储）、`fast_loop_context.py`（不可变快照）。

---

## 8. 2026-09-28 三项裁决的落地（当前权威）

[02-nonverbal-cognition.md](02-nonverbal-cognition.md) §7.2 留了三个岔路口，用户已于
2026-09-28 裁决：**三项全部采纳扩展方向**。本节是这三项裁决的**规范落地**——
凡与本文其他章节冲突，**以本节为准**（Part II 对 Part I 的优先规则同样适用于本节
对 Part II 前七节）。

裁决依据的理论论证见 [02](02-nonverbal-cognition.md)：§4.2（目标表述）、
§3.4 与 §6.1（C9 与自由能原理）、§3.1 与 §7.2 岔路口三（睡眠期双通路）。

### 8.1 裁决二落地：C9 改为「不设**外部**评分函数」，正式结盟自由能原理

**修订前**：C9 = 「不设评分函数，只有淘汰函数」。

**修订后**：

> **C9 —— 不设外部评分函数，只有淘汰函数。**
> 环境不给行为打分，只决定活不活；模型内部**允许**存在驱动信号，但其定义
> 不可被模型修改、不可被提案触碰、不进入淘汰判定。

**为什么必须改**（[02](02-nonverbal-cognition.md) §6.1）：修订前的表述与已落地的
设计**不符**，而且没有任何红灯会提示这件事——这是项目自己定义的「**措辞债**」
（代码/设计写对了、正文名不副实，见 [05-glossary.md](05-glossary.md) §四）。具体地：
`SurpriseEstimator` 生产 `prediction_error`、`MetabolicMonitor` 生产
`internal_drive_vector`（见 §2.5、§2.6.1），两者都进 State Core 并**直接改变行为**。
它们在功能上就是一种评分——只是评分者是模型自己而非环境。继续用旧表述，
每一次引用 C9 都要额外解释一遍「其实有内在信号，但那不算」。

**三层信号的正式区分**（这是修订后 C9 的实体内容）：

| 层 | 信号 | 归属 | 模型能否修改其定义 | 是否进入淘汰判定 |
|---|---|---|---|---|
| **① 淘汰函数** | `energy ≤ 0` / `damage ≥ max` | **环境**（§3.6） | **不能**——模型侧连只读镜像都不做 | **是**（它就是淘汰本身） |
| **② 内在驱动** | `prediction_error`、`internal_drive_vector`（能量缺口、惊奇 EMA） | **模型内部** | **不能**——不可更新清单先于白名单匹配（支柱 8 边界权） | **否** |
| **③ 结构提案** | ΔS / Δθ / ΔR / ΔM | 慢环产物 | 提案可改**结构**，不可改①②的定义 | **否**——Gate 只判合法性、不打分 |

**C9 的真正承重点是①的归属，不是②的有无。** 「淘汰函数在模型之外、模型物理上
碰不到它」这条安全属性，与「模型内部有没有驱动信号」**无关**。修订把承重点从
一句容易被反例击穿的否定式表述（「不设评分函数」），移到一条结构性事实
（「淘汰归环境，模型无判定权」）上。

**正式结盟自由能原理（FEP）/ 主动推理**：

- SSEA 的学习信号形态与主动推理**同构**：适应性行为由**预测误差最小化**驱动，
  偏好编码为**先验**而非外部奖励（Friston 2010；Friston et al. 2017）。
- `MetabolicMonitor` → `internal_drive_vector` 这条通路对应 Seth 2016 的
  **interoceptive inference**：情绪/驱动是对**内稳态预测误差**的感知。这给了
  「能量/损伤/疲劳 → 内部驱动」一个正式的理论名字。
- Schwartenbeck et al. 2015 的实验证据显示人类选择行为更符合 **surprise
  minimization** 而非 **value maximization**——即 C9 的形态不只是可行，
  它有实证先例。
- ⚠️ **结盟的代价必须同时写明**：FEP 的批评者指出「先验偏好」在数学上**等价于**
  内置目标函数。所以 SSEA **不得**声称「本架构完全没有目标函数」；正确的声称是
  「**没有外部设计的、可被刷分的奖励函数**」。任何对外表述都用后者。
- 证据分档：FEP 整体为 **B 级**（理论框架强、实验支持增长中，但可证伪性与实现
  细节仍是活跃争论）。**B 级依据可以支撑设计选择，不得当作已证结论引用。**

**连带修订**（旧表述散落在多份文档，须一并对齐）：

| 位置 | 原文 | 改为 |
|---|---|---|
| 根 [README.md](../README.md) C9 格 | 「不设评分函数，只有淘汰函数」 | 「不设**外部**评分函数，只有淘汰函数」 |
| 根 README「动手改代码前必须知道的六件事」第 6 条 | 「不要在这里长出评分函数。C9 是硬约束：只有淘汰函数，没有奖励」 | 保留禁令，但把对象限定为**外部评分/奖励塑形**；并明写「②内在驱动不属于本条禁止范围，其定义不可被修改」 |
| [01-philosophy.md](01-philosophy.md) 支柱 10 | 「C9 —— 不设评分函数，只有淘汰函数」 | 同上加「外部」，并补三层信号表 |
| [01-philosophy.md](01-philosophy.md) §4.3、支柱 11、§六第 5 条、§七表格 | 「不设评分函数」/「无评分」 | 加「外部」限定 |
| [04-boundaries.md](04-boundaries.md) 消融表 | 「惊奇估计器 → 必须引入奖励函数，违背 C9」 | 改为「必须引入**外部**奖励函数，违背 C9」 |
| [04-boundaries.md](04-boundaries.md) 不做清单 #11 | 「违背 C9『不设评分函数』」 | 改为「违背 C9『不设**外部**评分函数』」；#11 本身**继续不做**——观察员评分系统与奖励塑形仍然禁止 |
| [05-glossary.md](05-glossary.md) §三 C9 词条 | 「只有淘汰函数，没有评分函数」 | 按三层信号重写，并新增「内在驱动」「措辞债（C9 首例）」两条 |

⚠️ **不因此放开的东西**（防止修订被误读为「可以加奖励了」）：
- 「接近资源给分」这类**奖励塑形**仍然直接违规（[06-status-roadmap.md](06-status-roadmap.md) 已否决项）。
- **观察员评分系统**仍然不做（不做清单 #11）。
- **验证门仍然不打分**：Gate 只判合法性（支柱 8 验证权「刻意不做」）。
- **编译器仍然不排序**：提案无优先级评分（悬置项「提案优先级策略」仍未解决，
  见 [02](02-nonverbal-cognition.md) 附录 B——修订 C9 **没有**给它答案）。

### 8.2 裁决一落地：目标表述从「不缩减智力」改为「保留认知基底 + 明列放弃项」

**修订前**（散见于根 README、[docs/README.md](README.md)、
[01-philosophy.md](01-philosophy.md)）：

> 在减少算力与内存带宽消耗的同时**不缩减智力**。

**修订后（权威表述）**：

> 在减少算力与内存带宽消耗的同时，**保留语言之下那个完整的认知基底**——
> 多步规划、因果知觉、情景记忆、技能累积、非语言元认知、内在驱动；
> 并**明确放弃语言作为认知工具所提供的那部分能力**（精确离散符号运算、
> 递归组合生成、抽象概念的公共约定、显式自我叙述），把它们列入不做清单。

**为什么必须改**（[02](02-nonverbal-cognition.md) §4.2、§4.3）：「智力」不是标量。
按 §4.3 的逐项对照，六项 LLM 涌现能力里有**两项没有已知的非语言替代路径**
（精确符号运算、递归组合生成），一项只能部分替代（抽象推理），一项只能做到一阶
（自我反思）。**而这两项不可行的，恰好是 LLM 最擅长也最贵的两项。**

所以旧表述是一个**必输的辩论位置**：任何批评者举出「精确算术」一个反例，就能
宣称目标未达成——**而那个反例是真的**。

新表述的三处好处：
1. **可检验**：「保留基底」的六项各对应一条可设计的消融实验；「不缩减智力」不对应任何实验。
2. **诚实**：主动列出放弃项，而不是等批评者举出来——与 [04-boundaries.md](04-boundaries.md) §5「我们不声称什么」同一纪律。
3. **符合项目自己的方法论**：「机制 ≠ 能力，每条能力必须成对写出它做不到什么」这条纪律，本来就该用在目标表述自己身上。

**同时采纳的重新定位**（[02](02-nonverbal-cognition.md) §4.3 末）：

> SSEA 与 LLM **不是同一件事的两种实现，而是两个不同的能力剖面**。
> LLM 的剖面是「符号运算强、具身控制无」；SSEA 的剖面是「具身控制与规划强、
> 符号运算无」。**「不缩减智力」这个横向比较本身就是错的提问方式**——
> 正确的提问是「在需要低算力实时生存控制的场景里，哪个剖面更有用」。

**连带修订**：

| 位置 | 改动 |
|---|---|
| 根 [README.md](../README.md) 第 9 行 | 换成新表述 |
| [docs/README.md](README.md) 第 5 行 | 换成新表述 |
| [01-philosophy.md](01-philosophy.md) 〇、一句话总纲 | 补一句「保留认知基底、明列放弃项」 |
| [04-boundaries.md](04-boundaries.md) 不做清单 | **新增三项**：精确离散符号运算、递归组合生成、二阶自我解释（依据 [02](02-nonverbal-cognition.md) §5.1 / §5.2 / §5.5） |
| [04-boundaries.md](04-boundaries.md) §5「我们不声称什么」 | **新增第八项**：「不声称具备跨域的抽象关系推理能力」（依据 [02](02-nonverbal-cognition.md) §5.6，Penn, Holyoak & Povinelli 2008 的反方证据；这是 A1 唯一未关闭的子问题） |

⚠️ **原始构想文件不动**：[Original Project Philosophy.md](Original%20Project%20Philosophy.md)
第 10 行仍写「不会缩减智力」——那是**历史原文**，按项目纪律保留原貌，不做追改。
新表述只作用于当前有效文档。

⚠️ **递归组合仍是一个未决的设计问题**，修订目标表述**不等于**回答了它：
`Skill.action_sequence` 能否嵌套调用另一个 `Skill`？若能，SSEA 就有了递归组合
（那么「放弃递归组合生成」这一条要重新措辞）；若不能，技能库的表达力被限制在
「固定长度的动作序列」，是一个**硬上限**，必须在 [04](04-boundaries.md) §5 明写。
**这条必须在设计层决定，不能留给实现**（见 [02](02-nonverbal-cognition.md) §5.2）。
§8.3 的睡眠期预演给了它一条**不违反 C2、也不需要闭环内递归**的出路。

### 8.3 裁决三落地：睡眠期双通路 —— 回顾编译 + 前瞻预演

**修订前**（§2.2）：睡眠期是慢环的唯一常规入口，进入后触发 `ExperienceCompiler`
吃 trace 吐提案——**只有回顾一条通路**。

**修订后**：睡眠期包含**两条并列通路**，共用同一个 SLEEP 窗口与同一套
Gate → StructureStore 出口：

| 通路 | 输入 | 产物 | 生物学原型 |
|---|---|---|---|
| **① 回顾编译**（既有） | 已发生的 action trace + feedback | ΔS / ΔM / ΔR / Δθ 提案 | 海马 → 新皮层的 replay 巩固（CLS，[02](02-nonverbal-cognition.md) §3.1，**A 级**） |
| **② 前瞻预演**（新增） | 当前状态 + 已有技能/规则 + 惊奇高位处 | **预演候选**（离线试组合的动作序列），经验证后可固化为新 `Skill` | **replay 也参与规划，不只是回顾**（Ólafsdóttir et al. 2018；Kabadayi & Osvath 2017 渡鸦为 17 小时后的任务提前备工具） |

**为什么扩展**：Ólafsdóttir et al. 2018 的综述指出 replay **不只回顾、也参与规划**。
SSEA 只用回顾，是**把同一套机制用窄了**。而前瞻预演恰好补上项目两处悬而未决的问题：

1. **§8.2 留下的递归组合出路**：技能能否嵌套调用，如果放在**闭环内**做，就要面对
   无限递归与实时性（C4）；放在**睡眠期离线**做，则是「在安全状态下试组合」——
   不需要闭环内递归，不消耗实时预算，而且失败天然无害（预演不作用于世界）。
   **这是 §5.2「技能库表达力上限」问题的解法方向。**
2. **Donald 的 mimetic culture 只落地了一半**：[02](02-nonverbal-cognition.md) §2.3
   指出 SSEA 的慢环与 mimetic culture 同构，而 mimetic 的核心是
   **rehearsal as representation（排练即表征）**——「排练本身就是思维的载体」。
   现有的回顾编译只对应 **voluntary recall**；**前瞻预演才是 rehearsal**。
   补上它，同构关系才完整。

**⚠️ 扩展的前置条件：容量问题必须先回答，否则不得实现。**

这是本裁决**唯一的硬门槛**，[02](02-nonverbal-cognition.md) §7.2 岔路口三已点明：

- 实测睡眠只占寿命 **6%–12%**（§2.2 修订后，8/8 seed 可达）。
- 一次睡眠窗口内要跑完的是：`ExperienceCompiler` → `VerificationGate` **四级**
  （格式 → 沙盒 → 回归 → 小范围环境测试）→ `StructureStore.commit`。
- §2.2 已经登记过这个疑问且**至今未定义**：「一次睡眠够不够跑完整条慢环流程」。
- 现在要往同一个窗口里再塞一条通路，**容量压力翻倍**。

因此规定：

1. **顺序不可颠倒**：先定义并实测「睡眠期计算预算」（单次 SLEEP 允许消耗多少
   帧等效算力 / 多少提案 / 多少次 Gate 调用），**再**实现前瞻预演。
2. **预算不足时的降级规则必须先写死**，不得留给实现临场决定。建议形态：
   **回顾优先**——预演只在回顾通路已产出且已提交之后、且预算仍有剩余时才启动。
   理由：回顾处理的是**已发生**的证据（确定的），预演处理的是**假设**（不确定的）；
   C4 之下先花预算在确定的事上。
3. **未回答容量问题之前，前瞻预演只存在于本节，不得进入代码**。若提前实现，
   极可能出现「睡眠期被预演占满 → 回顾提案提交不了 → 慢环实质停摆」，
   而这个故障**不会被任何现有测试抓到**（睡眠进入率仍是 1.0000，
   慢环触发成功率仍是 1.0000——两个指标都量不到「窗口被谁占了」）。
   ⚠️ 这正是项目反复踩的「**空转**」形态（[05-glossary.md](05-glossary.md) §二）。
4. **预演产物必须走同一条 Gate**。前瞻预演**不得**绕过验证门直接写技能——
   否则支柱 8 的四权分立出现缺口（提案权与验证权被合并）。预演通路只拥有
   **提案权**，与回顾通路完全同级。
5. **预演不得引入外部评分**。判断一个预演候选「好不好」只能用它自己的
   **前向模型预测后果**（能量收支、是否触发淘汰条件），**不得**给它打分排序。
   这与 §8.1 修订后的 C9 一致：内在驱动可以有，外部评分不行。
   ⚠️ 而「多个预演候选谁先提交」正是 [02](02-nonverbal-cognition.md) 附录 B
   悬置的**提案优先级策略**问题——扩展预演会**放大**这个悬置项，
   不会自动解决它。

**连带修订**：

| 位置 | 改动 |
|---|---|
| §2.2 慢环触发器与睡眠期 | 增补一句指向本节：睡眠期含回顾与前瞻两条通路 |
| §4.3 睡眠期状态机 | `SEL` 节点内标注两条通路（回顾 → 前瞻），共用 Gate 与 commit 出口 |
| §5 修订条款汇总表 | 新增一行：第 5.5 节「慢环触发时机」增补睡眠期双通路 |
| [01-philosophy.md](01-philosophy.md) 支柱 6 | 慢环职责从「离线整理经验」扩为「离线整理经验**与预演候选**」；理论根据补 CLS + replay 参与规划 |
| [01-philosophy.md](01-philosophy.md) 支柱 11「安宁的回放」 | 该形态从「无损巩固记忆」扩为「巩固 + 排练」，与 rehearsal as representation 对齐 |
| [06-status-roadmap.md](06-status-roadmap.md) | 里程碑路线新增一项**前置任务**：定义并实测睡眠期计算预算（阻塞前瞻预演的实现） |

**新增验收指标**（挂在既有实验 7 上，不新开实验）：

```
睡眠窗口内两条通路各自的完成率
预算耗尽时的降级是否正确触发（回顾优先）
预演产物是否 100% 经过 Gate（绕过数必须为 0）
```

⚠️ 第三条的分母若为 0（尚无预演产物），按项目测量纪律**必须返回 `None`，
不得写成 1.0**（[05-glossary.md](05-glossary.md) §四「分母为 0」）。

### 8.4 三项裁决之间的关系

这三项不是并列的三个改动，它们互相咬合：

```
裁决二（C9 加「外部」）
   │  承认模型内部允许有驱动信号
   │  → 于是「内在驱动」成为合法的第三层信号
   ▼
裁决三（睡眠期前瞻预演）
   │  预演要用内在驱动来评价候选后果（能量收支、是否触发淘汰）
   │  → 它的合法性来自裁决二
   │  ⚠️ 若 C9 未修订，前瞻预演会被读成「在睡眠期偷偷打分」
   ▼
裁决一（目标改为「保留基底 + 明列放弃」）
      「多步规划」在保留清单里，「递归组合生成」在放弃清单里
      → 而 §8.3 的离线预演正好是「不做闭环内递归、也能扩展技能组合」的出路
      → 所以裁决一里那条「放弃递归组合生成」的措辞，可能要因裁决三而收窄
```

**一个必须记住的依赖顺序**：裁决二是另外两项的**前提**。C9 不先修订，
前瞻预演就没有合法地位（它必然要评价候选）；而目标表述里的「放弃项」清单，
也要等前瞻预演的表达力边界确定后才能定稿。

**因此文档改动顺序是：§8.1 → §8.3 → §8.2**（而不是编号顺序）。

### 8.5 本节未解决、仍开放的问题

采纳三项裁决**不**意味着以下问题被关闭：

| 问题 | 状态 | 出处 |
|---|---|---|
| 淘汰函数**没有形式化**，且当前形态是绝对阈值（`energy ≤ 0`），**没有选择力**——自然选择的压力来自**相对适应度差异** | **仍开放**，v0.4 种群级淘汰的前提 | [02](02-nonverbal-cognition.md) 附录 A2 |
| **跨域关系抽象**能否非语言进行（学界无共识） | **仍开放**，处置为「不声称」 | [02](02-nonverbal-cognition.md) §5.6 |
| **提案优先级策略**：C9 之下没有评分，多个提案谁先提交 | **仍开放**，且被 §8.3 **放大** | [02](02-nonverbal-cognition.md) 附录 B |
| **睡眠期计算预算**未定义 | **仍开放**，且现在是 §8.3 的**硬门槛** | §2.2、§8.3 |
| 支柱 11「偶然的美好」只有否定性边界（偶然/具身/非通货），**没有肯定性机制** | **仍开放**；§8.1 结盟 FEP 后，「内在驱动」是目前最接近的肯定性回答，但**不等于**解决了「美好」 | [02](02-nonverbal-cognition.md) 附录 A3 |
| C10 与 C4 潜在冲突（若低带宽依赖算子特定性质，L1 就不是无关紧要的） | **仍开放** | [02](02-nonverbal-cognition.md) 附录 A4 |
| `HeritableFilter` 的 `importance` 阈值与 `retrieval_count ≥ N` 的 N、本能内化的 K/F 阈值 | **仍开放**；N 的理论根据已给出（mimetic 传递需高频重复补偿保真度损失），**定标方法未给** | [02](02-nonverbal-cognition.md) §6.3 |
| Milestone 5 验收标准应按 **mimetic 速率**定，不按 mythic 速率定 | **待写入** M5 规划（M5 尚未开始，正是定标准的时候） | [02](02-nonverbal-cognition.md) §6.3(2) |
| 实验 1 缺「用语言」对照臂 | **仍开放**；⚠️补对照臂与 C2 冲突，须走 [04](04-boundaries.md) §3 突破清单流程 | [02](02-nonverbal-cognition.md) §6.4 |
| `ActionConstraints` 从枚举式升级为关系式（affordance） | **仍开放**；⚠️该函数横跨模型/生态边界，需新增一条平局裁决 | [02](02-nonverbal-cognition.md) §6.5 |
| 债务 26 的修法：用 options / 半 MDP 的 **initiation set** 语义重定义 `precondition`（状态谓词，不是瞬时标量下界） | **已实现「能量 > X」这一半**（2026-09-28，`skill_library._pre_action_energy` 取首帧动作前能量）；**「且目标可及」那一半仍开放**（协议只支持 `min_energy` 一个键） | [02](02-nonverbal-cognition.md) §3.3、[06](06-status-roadmap.md) §3.3 |
| **技能嵌套调用**（`action_sequence` 内能否再调一个 `Skill`） | **已于 2026-09-28 裁决**：第一阶段**禁止**，且须在协议级强制。见 §9 | §9 |

---

## 9. 技能嵌套调用的裁决（#22，2026-09-28）

### 9.1 问题的真实形状：不是「要不要允许」，是「已经允许了，但会静默失败」

[04-boundaries.md](04-boundaries.md) 不做清单 #22 与 §8.2 把这件事记成「一个待决定的
设计问题」。实测之后必须先纠正这个定性——**它在协议层早就被允许了，只是没有人
消费它，于是它静默失败。**

三处协议事实（均已实测，2026-09-28）：

1. `Skill.action_sequence` 的类型是 `list[Action]`（§8.11）。
2. `Action` 有 `skill` 通道（`skill_id` + `params`，§8.5）。
3. 因此 **`action_sequence` 里的某一帧完全可以是「调用另一个技能」**——类型系统
   不拦、协议不拦、`Action.__post_init__` 的通道登记检查也不拦（`skill` 是六个
   已登记通道之一）。

而这个动作被送进环境之后：

```
Environment._apply() 处理 5 个通道：
    locomotion / manipulation / communication / memory / self_modification
    —— 唯独没有 skill
```

**实测结果**（一个只带 `skill` 通道的 Action 直接送进 `Environment.step`）：

| 观测项 | 实测值 |
|---|---|
| `Action.is_executable()` | `True`（协议认为它可执行——因为 `skill` 通道非空） |
| `Feedback.action_success` | **`True`** |
| `Feedback.energy_change` | `-0.01`（只扣基础代谢） |
| `Feedback.notes` | `''`（空） |
| `ACTION_FAILED` 事件计数 | **`0`** |
| `SKILL_FAILURE` 事件计数 | **`0`** |

**这一帧既没有被拒绝，也没有产生任何后果，也没有发出任何事件。** 它报告成功，
烧掉一帧的基础代谢，然后什么都不做。

这正是 [05-glossary.md](05-glossary.md) §二定义的「**空转**」：机制在跑、
`action_success` 是 `True`、没有任何红灯，但对行为毫无影响。而且它比一般的空转
更隐蔽——它**主动报告成功**。

### 9.2 端到端实测：嵌套技能被静默吞掉

构造一条父技能，序列 3 帧，第 2 帧是「调用子技能」，子技能本应让 y 坐标 +0.5：

```
帧 | 交给环境的子动作通道 | success |    y   | 事件          | Runner 在跑
0  | ('locomotion',)      | True    | 0.0000 | None          | sk_parent
1  | ('skill',)           | True    | 0.0000 | None          | sk_parent   ← 嵌套帧
2  | ('locomotion',)      | True    | 0.0000 | SKILL_SUCCESS | None
```

**子技能从未执行**（y 恒为 0.0），但父技能报告 `SKILL_SUCCESS`，全程零事件、
零报错、零中止。`SkillRunner` 只维护单个 `_run`，它把子动作**原样**交给环境，
从不检查子动作自己是否又带 `skill` 通道。

### 9.3 可达性：这条路现在走不通，但拦住它的是巧合而不是设计

必须诚实界定严重性。分两条路：

**路一：编译器自动产出嵌套技能 —— 目前被挡住，但挡它的东西是错的。**

`compile_skills` 的序列取自 `rec.executed_action`，而 `_is_direct_success` 要求
`executed_action is decoded_action`（「抄一条已有技能的动作序列得到新技能是复制
不是学习」）。实测确认：**「调用一个不存在的技能」的帧，四个条件全部为真**——

```
帧 | 通道          | success | executed is decoded | _is_direct_success
4  | ('skill',)    | True    | True                | True   ← 关键
5  | ('skill',)    | True    | True                | True
```

原因链是：`SkillRunner.submit` 发现技能不存在 → 不启动执行、`_run = None` →
`current_action(fallback)` 返回 `fallback`（**就是解码器的原产物**）→
于是 `executed_action is decoded_action` 成立 → 而环境又给它 `action_success=True`
（§9.1）→ **这一帧被判定为「模型自己做对了一个动作」**。

这条路径最终没有产出技能，是因为 `_segments` 还要求整段**净能量变化 > 0**，
而 ghost-skill 帧只耗能（`-0.01`）不产出，混在段里会把净值拖负。实测两次构造
（净 `-0.10`）均产出 0 条技能。

⚠️ **但这个防护是巧合，不是设计**：它拦下 ghost 帧的理由是「能量不划算」，
而不是「技能调用不能出现在技能序列里」。**只要有一段净收益足够正的轨迹，
中间混进一帧 ghost-skill 就会被固化成嵌套技能**，而固化之后那一帧永久静默空转。
更直接的是：**`ADD_SKILL` 提案不止来自 `compile_skills`**——本能内化
（§3.4 的 `consolidated_from:<skill_id>`）、§8.3 的前瞻预演、以及实验里的注入样本
都能产出 `ADD_SKILL`，而 **`VerificationGate._check_format` 不检查
`action_sequence` 内部有没有 `skill` 通道**（实测确认：格式级只查提案类型、
target 存在性、策略键合法性）。

**路二：手工/注入构造嵌套技能 —— 完全畅通。** §9.2 的实测就是这条路，
它一路绿到 `SKILL_SUCCESS`。

**结论**：#22 不是一个「等以后决定」的开放设计题，它是一个**已存在的缺陷**，
只是被一个不相干的能量判据暂时掩盖着。

### 9.4 裁决：第一阶段禁止技能嵌套，且必须在协议级强制

**裁决**：`Skill.action_sequence` 内的 Action **不得**携带 `skill` 通道。
技能是**扁平的**——它是一段原子动作序列，不是可递归调用的程序。

**理由四条**：

1. **执行语义不存在**。`SkillRunner` 只维护单个 `_run`，没有调用栈。要支持嵌套
   就必须引入栈、深度上限、子技能中止如何冒泡到父技能、`success_count` /
   `failure_count` 记在谁头上、`energy_cost` 预算怎么在父子之间分摊——**这些一条
   都没有定义**。在没有语义的情况下允许它，等于允许静默空转（§9.1）。
2. **递归组合是已放弃项**。裁决一已把「递归组合生成」列入不做清单 #22，理由是
   NSL 研究表明递归涌现之后**它就成了符号系统**（[02](02-nonverbal-cognition.md)
   §5.2）。技能嵌套正是递归组合的一种形态，允许它与裁决一直接冲突。
3. **C4 低带宽**。查表比每步重新推理省算力，这是 Skill Runner 的存在理由
   （§2.3）。嵌套把「查表」变成「递归展开」，深度不受控时展开成本也不受控，
   而它在**快环的实时路径**上。
4. **前瞻预演已经给了出路**。§8.3 的睡眠期前瞻预演就是「在离线状态下试组合」——
   **它不需要闭环内递归**：预演产出的是一条**已经展开好的扁平序列**，
   经 Gate 验证后固化为新技能。组合能力由此获得，而递归风险为零。
   这正是 §8.4 所说「裁决三给了裁决一里那条『放弃递归组合生成』一个出路」的
   **具体机制**。

**⚠️ 但「禁止」不能只写在文档里。** 这是本裁决最重要的一半。
项目自己的纪律（[05-glossary.md](05-glossary.md) §二「约定只读 vs 结构事实」）
说得清楚：**约定只读＝文档说别写，写下去照样成功；结构事实＝写下去抛异常。**
现状是「约定禁止」，而实测证明写下去**不但不失败，还报告成功**。

所以必须在**三处**设防，且三处都要能被变异测试证红：

| # | 防线 | 位置 | 行为 |
|---|---|---|---|
| 1 | **协议级**（主） | `Skill.__post_init__` | 序列中任一 Action 携带 `skill` 通道 → **抛异常**，构造即失败。这是结构事实，不是约定 |
| 2 | **验证门格式级** | `VerificationGate._check_format` | `ADD_SKILL` / `UPDATE_SKILL` 的 payload 里若含嵌套 → **`passed=False`**，`reason` 写明「技能序列不得含 skill 通道」。这条必须加，因为提案可以携带手工构造的 `Skill` 绕过 `__post_init__`（反序列化路径） |
| 3 | **环境兜底** | `Environment._apply` | 只带 `skill` 通道的动作**不得**报 `action_success=True`。应记 `ACTION_FAILED` 并返回 `False`——与既有的第二执行点职责一致（§2.6.2） |

**为什么必须三处都设**：防线 1 挡住正常构造，防线 2 挡住提案与反序列化，
防线 3 是**最后一道**——它保证「万一前两道都漏了，这一帧不会假装成功」。
⚠️ 防线 3 修的是 §9.1 那个**独立于嵌套问题的缺陷**：环境把「它根本不认识的通道」
报成成功。即使技能嵌套永远不发生，这个缺陷也会让任何未来的无消费者通道静默空转。

### 9.5 连带发现的缺陷（须登记，不在本节修）

§9.1 与 §9.3 的实测暴露了两个**与嵌套问题独立**的缺陷，按项目纪律先登记再动手：

| 编号 | 缺陷 | 症状 | 为什么危险 |
|---|---|---|---|
| **27** | **环境把「无消费者的通道」报成成功** | `Environment._apply` 只处理 5 个通道，`skill` 通道无分支；只带 `skill` 的动作得到 `action_success=True`、零事件、只扣基础代谢 | 它**主动报告成功**。任何未来新增而无消费者的通道都会静默空转，且现有守卫抓不到——`test_consumer_surface.py` 扫的是**结构类别 / 访问器 / Action 六通道**三个面，扫不到「环境有没有消费这个通道」 |
| **28** | **`_is_direct_success` 把「技能没找到」判成「模型自己做对了」** | `SkillRunner.submit` 找不到技能时 `_run=None`，`current_action` 回退成解码器原产物，于是 `executed_action is decoded_action` 成立；配合债务 27 的 `success=True`，四条件全真 | 那条 `is` 判据的原意是「排除技能展开出来的子动作」，但它**同时把「技能调用彻底失败」也排除了**——两者在身份上不可区分。结果是**无效帧可以被固化进技能** |

⚠️ **债务 28 与债务 26 同根**：26 是「`precondition` 这个**描述**被当成了**判据**」，
28 是「`executed_action is decoded_action` 这个**身份判据**被当成了**语义判据**」。
两者都是「一个代理指标被当成了它想代理的那件事」。这属于
[05-glossary.md](05-glossary.md) §二「缺陷的五种来路」的**第五种**——
两处单看都说得通，只在「它们是不是在量同一件事」被问出来之后才现形。
本次是**第六种来路**的候选：它是在**为一个设计问题做实测取证**时撞出来的，
而不是在找缺陷时找到的。

### 9.6 对 #22 措辞的定稿

[04-boundaries.md](04-boundaries.md) 不做清单 #22 原文把状态记为「**待定**
（取决于技能嵌套的设计决定）」。现定稿为：

> **22 · 递归组合生成 / 无限生成能力** —— **永不**（能力剖面差异，非延期）。
> 技能是**扁平的**：`action_sequence` 内不得携带 `skill` 通道，协议级强制
> （见 [03](03-architecture-spec.md) §9.4）。技能库的表达力因此有**硬上限**：
> 固定长度的原子动作序列，**SSEA 明确不声称具备无限生成能力**
> （见 [04](04-boundaries.md) §5 第八项）。
> ⚠️ **组合能力不因此消失**，它换了位置：由 §8.3 的睡眠期**前瞻预演**在离线
> 状态下试组合，产出**已展开的扁平序列**再固化。递归风险为零，因为它从不发生在
> 闭环里。

同时 [04](04-boundaries.md) §5「后续阶段池」里的「技能嵌套调用」条目应**移出**
——它不再是「待评估的想法」，而是「已裁决禁止 + 已给出替代机制」。

### 9.7 落地顺序

本节是**设计裁决**，代码尚未改动。落地顺序按「先堵静默成功，再谈嵌套」：

1. **债务 27**（环境对无消费者通道报成功）——最优先。它独立于嵌套问题，
   且它是「主动报告成功」，比一般的空转更难发现。
2. **协议级防线**（`Skill.__post_init__`）+ **变异测试证红**。
3. **Gate 格式级防线**（`_check_format` 检查 `action_sequence` 内部通道）。
4. **债务 28**（`_is_direct_success` 的身份判据）。⚠️ **2026-09-28 更正**：本条原写
   「与债务 26 一并处理，因为两者同根，分开修会各修一半」——**债务 26 已于同日单独偿还**
   （它修的是 `skill_library._skill_for` 的**取值**：改取首帧动作前能量），而 28 未动。
   **不是「只修了一半」：两者同属一个病种，但不在同一个代码位置。**
   28 的真实耦合对象是**债务 27**——它四条件里的 `action_success` 正是 27 报出来的那个
   假成功。所以 28 排在 27 之后顺理成章：**先让环境不再报假成功，28 的「无效帧可被
   固化」才收得住。**
5. 以上四条完成后，`test_consumer_surface.py` 应**扩到第四个面**：
   「Action 的每个通道在环境侧都有消费者」。这条守卫现在缺，
   而它正是能抓住债务 27 的那一类。

⚠️ 顺序不可颠倒：先加协议级防线（第 2 步）会让**构造**失败，于是第 1 步的
环境缺陷**再也无法被触发**——缺陷还在，只是再也测不到了。
**先修环境，再堵协议**，这样每一步都有可证红的守卫。
