# SSEA v0.3 第一阶段任务书

**项目名称**：SSEA  
**全称**：Survival-based Self-Evolving Agent Architecture  
**中文名称**：生存式自演化代理架构  
**当前版本**：v0.3  
**阶段名称**：第一阶段 —— 最小模型本体设计  
**阶段目标**：设计并验证一个可运行、可记忆、可学习、可保存、可继承、可小范围自我修改的模型本体。  
**核心原则**：第一阶段不构建完整生态系统，只构建能够进入生态系统的“最小生命体”。

---

## 1. 项目背景

当前主流大模型架构存在以下问题：

1. 高度依赖静态语料投喂训练。
2. 以自然语言 token 作为主要输入输出单位，信息密度低。
3. 知识大量压缩在参数权重中，导致精准回忆困难。
4. 模型自我修改能力弱，难以持续演化。
5. 推理和训练算力、带宽消耗较高。
6. 缺乏具身性、生存压力、能量约束和生命周期机制。

因此，本项目尝试设计一种新的模型架构：

> 一个低算力、低带宽、可精准回忆、可自主训练、可自主修改代码与参数、并能在生态系统中演化生存的模型本体。

第一阶段不直接构建复杂生态系统，而是先完成模型自身的最小可行本体。

---

## 2. 第一阶段总目标

第一阶段的核心目标是：

> 完成 SSEA v0.3 最小模型本体架构设计，并建立一个可运行的最小闭环原型。

该原型应具备以下能力：

1. 接收环境观测。
2. 感知自身身体状态。
3. 维护内部状态。
4. 读取和写入外部记忆。
5. 输出非自然语言动作。
6. 根据环境反馈进行学习。
7. 保存自身基因。
8. 从基因恢复。
9. 产生可变异后代。
10. 进行小范围、安全的自我修改。

第一阶段不要求模型具备复杂语言、社会合作、四季生态、自然灾害等能力。

---

## 3. 阶段范围

### 3.1 第一阶段包含的内容

| 类别 | 包含内容 |
|---|---|
| 模型本体 | 感知编码器、状态核心、记忆系统、行动生成器、学习机制、遗传模块、自我修改模块 |
| 接口协议 | 观测接口、身体状态接口、动作接口、记忆接口、通信接口、基因接口、反馈接口 |
| 最小测试环境 | 简单对象世界、能量反馈、危险反馈、资源反馈 |
| 可复用成果 | Voyager、Darwin Gödel Machine、RAG、LoRA、Weight Inheritance、Dreamer、Mamba/GRU 等 |
| 验证目标 | 可持续运行、记忆召回、技能固化、基因保存恢复、变异、自我修改安全回滚 |

---

### 3.2 第一阶段不包含的内容

| 类别 | 不包含内容 |
|---|---|
| 完整生态系统 | 四季变化、自然灾害、复杂资源循环 |
| 多智能体社会 | 复杂合作、竞争、欺骗、社会结构 |
| 自然语言主接口 | 不以聊天、文本生成作为主要交互方式 |
| 高分辨率视觉 | 不处理真实图像或视频流 |
| 复杂物理引擎 | 不做精细刚体、流体、材质模拟 |
| 全量权重训练 | 不依赖大规模反向传播更新全部权重 |
| 人类知识库接入 | 不直接喂入维基百科、论文、代码库 |
| 观察员评分系统 | 不构建复杂人类评分或奖励函数 |
| 自主联网 | 第一阶段不要求模型真正联网获取外部知识 |

---

## 4. 核心设计原则

### 4.1 模型不是语言模型，而是行动控制器

SSEA 的第一运行目标不是生成自然语言，而是：

```text
感知环境
→
形成内部状态
→
选择动作
→
获得反馈
→
更新记忆与自身
→
继续生存
```

---

### 4.2 自然语言不是第一接口

第一阶段模型主要使用：

```text
低维观测向量
+
结构化动作
+
技能调用
+
记忆写入
+
通信向量
```

自然语言仅作为后续观察员接口或外部工具接口。

---

### 4.3 知识不全放在权重中

SSEA 将知识分为三类：

| 类型 | 存储位置 | 用途 |
|---|---|---|
| 基础能力 | 小型核心权重 | 感知、控制、推理、行动 |
| 历史经验 | 外部记忆系统 | 精准回忆、事件检索 |
| 可执行行为 | 技能库 / 代码库 | 复用已验证行为 |

---

### 4.4 学习不等于全量权重训练

第一阶段允许的学习方式包括：

1. 写入记忆。
2. 固化技能。
3. 更新规则。
4. 更新小型 adapter。
5. 更新检索策略。
6. 更新行为阈值。
7. 局部参数更新。

第一阶段不要求全局反向传播训练大模型。

---

### 4.5 模型必须具备生命周期

模型必须支持：

```text
出生
→
运行
→
学习
→
保存
→
死亡快照
→
基因提取
→
变异
→
下一代恢复
```

---

## 5. 总体架构

SSEA v0.3 第一阶段模型本体由以下模块组成：

```text
SSEA v0.3 最小模型本体
│
├── Body Interface              身体接口层
│   ├── 身体状态输入
│   └── 动作执行输出
│
├── Perception Encoder          感知编码层
│   ├── 环境对象编码
│   ├── 事件编码
│   └── 社会信号编码
│
├── State Core                  状态核心层
│   ├── 内部状态维护
│   ├── 意图生成
│   └── 行动决策
│
├── Memory System               记忆系统
│   ├── 短期工作记忆
│   ├── 长期事件记忆
│   ├── 技能记忆
│   └── 规则记忆
│
├── Action Head                 行动生成层
│   ├── 运动动作
│   ├── 操作动作
│   ├── 通信动作
│   ├── 记忆动作
│   ├── 技能调用
│   └── 自我修改请求
│
├── Plasticity / Learning       可塑性与学习层
│   ├── 记忆学习
│   ├── 技能固化
│   ├── 局部参数更新
│   └── 规则更新
│
├── Heredity Module             遗传模块
│   ├── 基因保存
│   ├── 基因恢复
│   ├── 基因变异
│   └── 本能继承
│
└── Self-Modification Module    自我修改模块
    ├── 修改提案
    ├── 沙盒验证
    ├── 应用修改
    └── 失败回滚
```

---

## 6. 模型内部数据流

第一阶段模型的基本运行闭环为：

```text
Environment Stub
      ↓
Observation
      ↓
Perception Encoder
      ↓
perception_vector
      ↓
Memory Retrieval
      ↓
memory_context
      ↓
State Core
      ↓
intent_vector / hidden_state
      ↓
Action Head
      ↓
Action
      ↓
Environment Stub
      ↓
Feedback
      ↓
Learning / Memory Update / Skill Update
      ↓
Gene Save / Mutation
```

---

# 7. 关键接口协议

以下接口为第一阶段必须定义的核心协议。

---

## 7.1 Observation，观测接口

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

说明：

- `time`：当前环境时间。
- `body`：模型自身身体状态。
- `environment`：环境摘要。
- `objects`：附近对象列表。
- `events`：近期事件。
- `social_signals`：来自其他模型的通信信号，第一阶段可为空。

---

## 7.2 BodyState，身体状态接口

```python
BodyState = {
    "energy": float,
    "damage": float,
    "fatigue": float,
    "position": list[float],
    "orientation": list[float],
    "available_actions": list[str],
    "internal_state": list[float]
}
```

说明：

- `energy`：能量，低于阈值可死亡。
- `damage`：损伤。
- `fatigue`：疲劳，影响动作效率。
- `position`：位置。
- `orientation`：朝向。
- `available_actions`：当前可执行动作。
- `internal_state`：内部状态向量，可选。

---

## 7.3 EnvironmentSummary，环境摘要接口

```python
EnvironmentSummary = {
    "light_level": float,
    "temperature": float,
    "danger_level": float,
    "resource_density": float,
    "time_phase": str
}
```

说明：

第一阶段环境摘要保持极简，不实现四季和灾害。

---

## 7.4 ObjectVector，对象向量接口

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

说明：

- 不使用 RGB 图像。
- 使用稀疏对象向量表示环境。
- `affordance` 表示对象可被执行的潜在动作。

---

## 7.5 EventVector，事件向量接口

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

事件类型示例：

```text
OBJECT_FOUND
OBJECT_LOST
DAMAGE_RECEIVED
ENERGY_GAINED
ACTION_FAILED
SKILL_SUCCESS
MEMORY_STORED
```

---

## 7.6 CommunicationSignal，通信信号接口

```python
CommunicationSignal = {
    "sender_id": str,
    "receiver_id": str,
    "signal": list[float],
    "timestamp": float,
    "priority": int
}
```

说明：

- 第一阶段不实现完整语言。
- `signal` 为固定长度潜空间向量，例如 64 维或 128 维。
- 同族语言演化留到后续阶段。

---

## 7.7 Action，动作接口

```python
Action = {
    "locomotion": {
        "direction": list[float],
        "speed": float
    },
    "manipulation": {
        "target_id": str,
        "operation": str,
        "force": float
    },
    "communication": {
        "target_id": str,
        "signal": list[float]
    },
    "memory": {
        "store": bool,
        "content": list[float]
    },
    "skill": {
        "call": str,
        "params": dict
    },
    "self_modification": {
        "proposal_type": str,
        "payload": dict
    }
}
```

说明：

动作不是自然语言，而是多通道结构化控制信号。

---

## 7.8 Feedback，环境反馈接口

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

- `Feedback` 不是评分函数。
- 它是环境对动作后果的客观反馈。
- 可用于记忆、学习、淘汰判断，但不作为全局优化奖励。

---

## 7.9 MemoryItem，记忆条目接口

```python
MemoryItem = {
    "id": str,
    "timestamp": float,
    "type": str,
    "context_vector": list[float],
    "content_vector": list[float],
    "outcome": str,
    "importance": float,
    "retrieval_count": int
}
```

记忆类型：

```text
EVENT
SKILL
RULE
BODY_EXPERIENCE
SOCIAL
```

---

## 7.10 Skill，技能接口

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
    "last_used": float
}
```

说明：

技能是可复用的动作序列或可执行程序。

---

## 7.11 GenePackage，基因包接口

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

说明：

- 模型死亡时保存 `GenePackage`。
- 下一代可以从 `GenePackage` 恢复。
- 可在恢复时引入变异。

---

# 8. 任务分解

---

## 模块 A：边界冻结

### A1. 制定模型、接口、生态边界表

目标：

明确哪些属于模型本体，哪些属于接口，哪些属于生态系统。

产出：

```text
《SSEA v0.3 边界定义表》
```

内容：

| 要素 | 模型架构 | 接口 | 生态系统 | 第一阶段是否实现 |
|---|---|---|---|---|
| 身体 | 身体状态表征 | 身体输入输出 | 物理规则 | 接口级 |
| 动作 | 动作策略 | 动作格式 | 动作后果 | 接口级 |
| 感知 | 感知编码 | 观测格式 | 世界生成 | 接口级 |
| 大脑 | 状态核心 | 内部状态流 | 环境反馈 | 是 |
| 记忆 | 记忆读写 | 记忆格式 | 历史来源 | 是 |
| 繁衍 | 基因保存恢复变异 | 遗传接口 | 繁衍规则 | 接口级 |
| 同族语言 | 通信编码解码 | 通信向量 | 语言演化 | 后续 |
| 自我修改 | 修改提案与验证 | 修改接口 | 演化选择 | 是 |

优先级：

```text
P0
```

验收标准：

- 所有模块边界清晰。
- 第一阶段不实现项明确列出。
- 后续讨论不再随意扩大到完整生态系统。

---

### A2. 制定第一阶段不做清单

目标：

防止项目范围扩散。

产出：

```text
《SSEA v0.3 第一阶段不做清单》
```

内容包括：

```text
不做完整四季生态
不做自然灾害
不做复杂资源循环
不做多模型社会
不做自然语言主接口
不做高分辨率视觉
不做复杂物理引擎
不做全量权重训练
不做人类知识库直接接入
不做自主联网
```

优先级：

```text
P0
```

---

## 模块 B：接口协议设计

### B1. 定义 Observation 协议

目标：

规定模型如何接收环境信息。

产出：

```text
Observation dataclass / JSON Schema
```

可用资源：

- MineDojo 观测结构
- Voyager 环境观测
- SIMA 具身观测接口
- 事件相机观测思想

优先级：

```text
P0
```

验收标准：

- 可以生成合法 Observation。
- 不包含高维图像。
- 可以被模型编码器消费。

---

### B2. 定义 BodyState 协议

目标：

规定模型如何感知自身。

产出：

```text
BodyState dataclass / JSON Schema
```

可用资源：

- 强化学习环境状态空间
- 机器人本体感知接口
- embodied agent proprioception

优先级：

```text
P0
```

---

### B3. 定义 Action 协议

目标：

规定模型如何输出动作。

产出：

```text
Action dataclass / JSON Schema
```

可用资源：

- Voyager skill call
- tool use / function calling
- 机器人控制动作空间
- program synthesis

优先级：

```text
P0
```

---

### B4. 定义 MemoryItem 协议

目标：

规定模型如何存储和检索记忆。

产出：

```text
MemoryItem dataclass / JSON Schema
```

可用资源：

- RAG
- kNN-LM
- vector database
- Agent Workflow Memory
- modern Hopfield networks

优先级：

```text
P0
```

---

### B5. 定义 CommunicationSignal 协议

目标：

为后续同族通信预留接口。

产出：

```text
CommunicationSignal dataclass / JSON Schema
```

可用资源：

- latent communication
- emergent language
- multi-agent communication

优先级：

```text
P1
```

说明：

第一阶段可暂时空置，不实现语言演化。

---

### B6. 定义 GenePackage 协议

目标：

规定模型如何保存、恢复、继承、变异。

产出：

```text
GenePackage dataclass / JSON Schema
```

可用资源：

- PyTorch state_dict
- safetensors
- LoRA
- model merging
- NEAT
- weight inheritance

优先级：

```text
P0
```

---

### B7. 定义 Feedback 协议

目标：

规定环境如何向模型返回后果。

产出：

```text
Feedback dataclass / JSON Schema
```

优先级：

```text
P0
```

---

## 模块 C：最小模型架构设计

### C1. 感知编码器，Perception Encoder

目标：

将多源观测压缩为低维感知向量。

输入：

```text
BodyState
EnvironmentSummary
Objects
Events
CommunicationSignals
```

输出：

```text
perception_vector
```

可选实现：

```text
MLP Encoder
GRU Encoder
Object-Centric Encoder
Sparse Attention Encoder
```

第一阶段建议：

```text
轻量 MLP + 小型 GRU
```

优先级：

```text
P0
```

验收标准：

- 输入 Observation 可编码为固定长度向量。
- 向量维度可控，例如 128 / 256 / 512。
- 不引入高成本视觉模型。

---

### C2. 状态核心，State Core

目标：

作为模型大脑，维护内部状态并生成行动意图。

输入：

```text
perception_vector
body_state
memory_context
internal_drive
```

输出：

```text
hidden_state
intent_vector
```

候选架构：

| 架构 | 推荐程度 | 原因 |
|---|---|---|
| GRU | 高 | 简单、稳定、低算力 |
| Mamba / SSM | 高 | 低带宽、长状态友好 |
| Liquid Neural Network | 中 | 动态适应强，但工程复杂 |
| Small Sparse Transformer | 中 | 表达能力强，但算力较高 |
| Small MoE | 中 | 稀疏激活，但路由复杂 |

第一阶段建议：

```text
GRU 或小型 Mamba
```

优先级：

```text
P0
```

验收标准：

- 可根据当前观测和历史状态输出意图向量。
- 可保持低算力运行。
- 不依赖长文本生成。

---

### C3. 记忆系统，Memory System

目标：

实现外部记忆读写与检索。

功能：

```text
写入记忆
检索记忆
更新记忆重要度
固化技能记忆
存储规则记忆
```

建议实现：

```text
结构化字段
+
context_vector
+
向量检索
```

优先级：

```text
P0
```

验收标准：

- 模型可以写入事件。
- 模型可以根据当前上下文检索相似记忆。
- 模型可以在行动中使用检索结果。

---

### C4. 行动生成器，Action Head

目标：

将内部意图转换为结构化动作。

输出通道：

```text
运动
操作
通信
记忆写入
技能调用
自我修改请求
```

优先级：

```text
P0
```

验收标准：

- 模型可以输出合法 Action。
- 动作可被环境桩解析。
- 不要求模型输出自然语言。

---

### C5. 学习机制，Plasticity / Learning

目标：

实现非全量权重训练的学习方式。

第一阶段学习机制：

#### 1. 记忆学习

```text
重要事件写入长期记忆
高预测误差事件优先写入
```

#### 2. 技能学习

```text
成功动作序列固化为技能
```

#### 3. 规则学习

```text
重复因果关系形成规则
```

#### 4. 局部参数学习

```text
只更新小型 adapter / policy head / retrieval head
```

优先级：

```text
P0
```

验收标准：

- 模型可以在不重训全部权重的情况下改变行为。
- 模型可以记住历史事件。
- 模型可以复用已成功技能。

---

### C6. 遗传模块，Heredity Module

目标：

让模型可以保存、恢复、变异、继承。

核心接口：

```python
save_gene()
load_gene()
mutate_gene()
inherit_from_parent()
```

遗传内容：

```text
架构
核心权重
本能 adapter
技能库
记忆索引
行为策略
代谢策略
变异率
```

优先级：

```text
P0
```

验收标准：

- 模型可以导出基因包。
- 模型可以从基因包恢复。
- 子代模型可以与父代存在可追踪差异。
- 变异后模型仍可运行。

---

### C7. 自我修改模块，Self-Modification Module

目标：

允许模型安全地修改自身局部结构或行为。

第一阶段允许修改：

```text
技能库
规则库
行动阈值
检索策略
小型 adapter
技能参数
```

第一阶段不允许修改：

```text
核心操作系统
安全沙盒
环境接口
淘汰函数
观察员接口
硬件权限
```

核心流程：

```text
提出修改
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

可用资源：

- Darwin Gödel Machine
- Gödel Agent
- AI Scientist
- DeepSeek DSec sandbox
- 单元测试
- 代码沙盒

优先级：

```text
P1
```

验收标准：

- 模型可以提出修改提案。
- 修改必须经过验证。
- 失败修改可以回滚。
- 核心系统不被直接修改。

---

## 模块 D：最小测试环境

### D1. 环境类型选择

目标：

提供一个最小测试桩，用于验证模型本体。

候选环境：

| 环境 | 推荐程度 | 原因 |
|---|---|---|
| 自研 2D 对象世界 | 高 | 接口干净、可控 |
| MiniGrid 改造版 | 高 | 开源成熟、简单 |
| MineDojo | 低 | 过重，不适合第一阶段 |
| 复杂物理引擎 | 低 | 工程复杂度过高 |

第一阶段建议：

```text
自研极简 2D 对象世界
或
MiniGrid 改造版
```

---

### D2. 最小环境要素

环境只需包含：

```text
一个模型主体
若干资源点
若干危险物
能量系统
损伤系统
简单位置系统
```

示例：

```text
模型：
- 有能量
- 行动消耗能量
- 能量为 0 死亡

资源：
- 接近后可获得能量

危险物：
- 接近后造成损伤或能量损失
```

---

### D3. 环境接口

```python
class EnvironmentStub:
    def reset(self) -> Observation:
        ...

    def step(self, action: Action) -> tuple[Observation, Feedback]:
        ...
```

优先级：

```text
P1
```

验收标准：

- 模型可以持续运行若干步。
- 环境可以返回观测和反馈。
- 环境不包含复杂生态规则。

---

## 模块 E：可复用成果选型

### E1. 技能库与代码动作

可用成果：

| 成果 | 可复用点 |
|---|---|
| Voyager | 技能库、代码即技能、自动课程 |
| ASPIRE | 开放式技能发现 |
| Agent Workflow Memory | 工作流记忆复用 |

用于：

```text
Action Head
Skill Library
长期技能记忆
```

---

### E2. 自我修改代码

可用成果：

| 成果 | 可复用点 |
|---|---|
| Darwin Gödel Machine | 自我重写代码 |
| Gödel Agent | 自指代理框架 |
| AI Scientist | 自动实验与验证 |
| DeepSeek DSec | 沙盒基础设施 |

用于：

```text
自我修改模块
沙盒验证
安全回滚
```

---

### E3. 遗传与权重继承

可用成果：

| 成果 | 可复用点 |
|---|---|
| Weight Inheritance | 父代权重传递给子代 |
| NEAT | 网络结构演化 |
| Model Merging | 模型融合 |
| LoRA / Adapter | 小规模可遗传模块 |
| safetensors | 权重安全保存 |

用于：

```text
GenePackage
本能继承
子代初始化
模型变异
```

---

### E4. 外部记忆

可用成果：

| 成果 | 可复用点 |
|---|---|
| RAG | 外部检索 |
| kNN-LM | 检索式记忆 |
| Vector Database | 记忆检索 |
| Agent Workflow Memory | 行动经验复用 |
| Modern Hopfield Networks | 联想记忆 |

用于：

```text
长期事件记忆
技能记忆
规则记忆
精准回忆
```

---

### E5. 世界模型与预测学习

可用成果：

| 成果 | 可复用点 |
|---|---|
| Dreamer | 世界模型、梦境推演 |
| MuZero | 策略、价值、模型学习 |
| TD-MPC | 模型预测控制 |
| Active Inference | 预测误差驱动 |
| Predictive Coding | 局部预测学习 |

用于：

```text
环境预测
误差学习
内在探索动力
```

---

### E6. 低算力核心网络

可用成果：

| 成果 | 可复用点 |
|---|---|
| GRU | 简单低算力 |
| Mamba / SSM | 低带宽、长状态 |
| Liquid Neural Network | 动态适应 |
| Sparse Transformer | 稀疏计算 |
| Small MoE | 按需激活 |

用于：

```text
State Core
低算力大脑
事件驱动控制
```

---

# 9. 第一阶段里程碑

---

## Milestone 0：边界冻结

目标：

确定第一阶段范围。

交付物：

```text
《SSEA v0.3 边界定义表》
《SSEA v0.3 第一阶段不做清单》
```

验收标准：

- 模型、接口、生态边界清晰。
- 团队一致同意不先做完整生态。

---

## Milestone 1：接口协议完成

目标：

完成模型与环境之间的全部基础协议。

交付物：

```text
Observation 协议
BodyState 协议
Action 协议
MemoryItem 协议
CommunicationSignal 协议
GenePackage 协议
Feedback 协议
```

验收标准：

- 所有接口可用 Python dataclass 表示。
- 所有接口可序列化为 JSON。
- 接口不依赖具体模型实现。

---

## Milestone 2：最小模型骨架完成

目标：

实现模型内部基本数据流。

交付物：

```text
Perception Encoder
State Core
Memory System
Action Head
```

验收标准：

```text
Observation
→ perception_vector
→ hidden_state
→ Action
```

闭环可以运行。

---

## Milestone 3：最小环境桩完成

目标：

提供可运行测试环境。

交付物：

```text
EnvironmentStub
SimpleObjectWorld
```

验收标准：

- 环境可以 `reset()`。
- 环境可以 `step(action)`。
- 环境可以返回 Observation 和 Feedback。

---

## Milestone 4：最小学习闭环完成

目标：

模型可以根据反馈改变行为。

交付物：

```text
记忆写入机制
技能固化机制
局部更新机制
```

验收标准：

- 模型可以记住危险或资源。
- 模型可以复用成功技能。
- 模型可以在不完全重训权重的情况下改变行为。

---

## Milestone 5：遗传与自我修改雏形完成

目标：

模型可以保存、恢复、变异，并进行安全自我修改。

交付物：

```text
save_gene()
load_gene()
mutate_gene()
self_modify_proposal()
validate_change()
rollback_change()
```

验收标准：

- 模型死亡后可保存基因。
- 基因可恢复为新模型。
- 子代可继承父代部分技能或本能。
- 自我修改失败可回滚。

---

# 10. 第一阶段验收实验

---

## 实验 1：持续运行实验

目标：

验证模型能否在最小环境中稳定运行。

流程：

```text
reset environment
run model for N steps
check crashes
check action legality
```

验收指标：

```text
连续运行步数
动作合法率
接口异常率
```

---

## 实验 2：记忆召回实验

目标：

验证模型是否能精准回忆历史。

流程：

```text
模型第一次遇到危险物
模型写入记忆
模型再次遇到同类危险物
模型检索历史并改变动作
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

验证模型是否能将成功行为固化为技能。

流程：

```text
模型多次成功接近资源
动作序列被记录
成功次数超过阈值
生成技能
后续调用技能
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

验证模型生命周期能力。

流程：

```text
模型运行
模型死亡或主动保存
导出 GenePackage
从 GenePackage 恢复模型
比较行为一致性
```

验收指标：

```text
保存成功率
恢复成功率
权重一致性
技能继承率
```

---

## 实验 5：变异实验

目标：

验证模型能否产生可运行后代。

流程：

```text
父代 GenePackage
mutate_gene()
生成子代模型
运行子代
比较差异
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

验证模型自我修改是否可控。

流程：

```text
模型提出修改提案
验证器检查
沙盒运行
成功则应用
失败则回滚
```

验收指标：

```text
修改提案数量
验证通过率
失败回滚率
核心系统未被破坏率
```

---

# 11. 技术选型建议

---

## 11.1 第一阶段推荐技术栈

| 模块 | 推荐选择 | 备选 |
|---|---|---|
| 编程语言 | Python | Rust 用于后期性能模块 |
| 模型框架 | PyTorch | JAX |
| 核心网络 | GRU 或小型 Mamba | Liquid Neural Network |
| 记忆存储 | 结构化 JSON + 向量索引 | SQLite + vector DB |
| 向量检索 | FAISS / Chroma / LanceDB | 简易 cosine search |
| 权重保存 | safetensors | PyTorch state_dict |
| 可遗传模块 | LoRA / Adapter | 小型 policy head |
| 代码沙盒 | Docker / subprocess sandbox | WebAssembly sandbox |
| 测试环境 | 自研 2D 对象世界 | MiniGrid |

---

## 11.2 第一阶段不推荐技术

| 技术 | 不推荐原因 |
|---|---|
| 大型 Transformer | 算力和带宽高 |
| 自然语言主接口 | 信息密度低，不利于行动控制 |
| 高分辨率视觉 | 数据带宽过高 |
| 复杂物理引擎 | 工程负担重 |
| 全量反向传播训练 | 不适合持续演化 |
| 真实互联网接入 | 安全风险高，第一阶段不需要 |

---

# 12. 风险与缓解措施

---

## 风险 1：项目范围再次扩散

风险描述：

重新讨论生态系统、社会、语言、自然灾害等复杂问题，导致第一阶段无法落地。

缓解措施：

- 严格执行不做清单。
- 所有新想法先记录到后续阶段池。
- 第一阶段只验收模型本体能力。

---

## 风险 2：模型无法在没有语料的情况下学习

风险描述：

如果完全不用传统数据，模型可能无法形成初始能力。

缓解措施：

- 给“基因先验”，不给“知识语料”。
- 使用最小环境反馈作为学习信号。
- 使用记忆、技能、规则作为主要学习方式。

---

## 风险 3：自我修改导致系统失控

风险描述：

模型修改自身代码或参数后崩溃，或绕过安全机制。

缓解措施：

- 分级权限。
- 沙盒验证。
- 修改前快照。
- 失败自动回滚。
- 核心系统只读。

---

## 风险 4：记忆系统无限膨胀

风险描述：

模型不断写入记忆，导致存储和检索成本过高。

缓解措施：

- 设置记忆容量。
- 设置重要度衰减。
- 定期合并相似记忆。
- 低重要度记忆可删除。

---

## 风险 5：模型行为退化

风险描述：

模型可能选择不动、不探索、只保存能量，导致演化停滞。

缓解措施：

- 引入能量衰减。
- 引入资源损耗。
- 引入预测误差记录。
- 引入技能多样性观察指标。
- 不奖励，但淘汰长期无变化个体。

---

# 13. 安全约束

第一阶段必须设置以下安全边界：

```text
模型不可直接访问真实互联网。
模型不可直接访问宿主文件系统。
模型不可修改淘汰函数。
模型不可修改观察员接口。
模型不可修改沙盒本身。
模型不可绕过验证器应用修改。
模型所有自我修改必须可回滚。
模型所有基因保存必须可审计。
```

---

# 14. 第一阶段交付物清单

第一阶段结束后，应交付以下文档和代码：

---

## 14.1 文档交付物

```text
《SSEA v0.3 边界定义表》
《SSEA v0.3 第一阶段不做清单》
《SSEA v0.3 接口协议》
《SSEA v0.3 模型架构设计》
《SSEA v0.3 学习机制设计》
《SSEA v0.3 遗传机制设计》
《SSEA v0.3 自我修改安全设计》
《SSEA v0.3 最小实验报告》
```

---

## 14.2 代码交付物

```text
sse_protocols/
    observation.py
    body_state.py
    action.py
    memory.py
    communication.py
    gene.py
    feedback.py

sse_model/
    perception_encoder.py
    state_core.py
    memory_system.py
    action_head.py
    plasticity.py
    heredity.py
    self_modifier.py

sse_env/
    environment_stub.py
    simple_object_world.py

tests/
    test_run_loop.py
    test_memory_recall.py
    test_skill_consolidation.py
    test_gene_save_load.py
    test_mutation.py
    test_self_modification.py
```

---

# 15. 推荐执行顺序

建议按以下顺序执行：

```text
第 1 步：边界冻结
第 2 步：接口协议定义
第 3 步：最小模型骨架
第 4 步：最小环境桩
第 5 步：运行闭环
第 6 步：记忆与技能学习
第 7 步：基因保存恢复
第 8 步：变异与自我修改
第 9 步：最小实验验收
第 10 步：进入第二阶段设计
```

---

# 16. 第一阶段完成标准

当以下条件全部满足时，认为第一阶段完成：

```text
1. 模型可以在最小环境中持续运行。
2. 模型可以接收观测并输出合法动作。
3. 模型可以写入和检索记忆。
4. 模型可以通过记忆改变行为。
5. 模型可以固化成功技能。
6. 模型可以保存基因。
7. 模型可以从基因恢复。
8. 模型可以产生可运行变异后代。
9. 模型可以提出自我修改提案。
10. 自我修改可以通过验证并安全回滚。
```

---

# 17. 下一阶段预告

第一阶段完成后，进入第二阶段：

```text
SSEA v0.4：多模型交互与最小生态接口
```

第二阶段可能包括：

- 多个模型共存
- 简单资源竞争
- 通信信号演化
- 同族/野兽角色
- 死亡与繁衍规则
- 淘汰函数
- 观察员系统
- 技能与基因的群体传播

但第一阶段不实现这些内容。

---

# 18. 结论

SSEA v0.3 第一阶段的核心不是建造一个世界，而是建造一个能够进入世界的最小生命体。

第一阶段应聚焦：

```text
可感知
可行动
可记忆
可学习
可保存
可恢复
可变异
可安全自我修改
```

完成这一阶段后，项目才具备进入生态系统、群体演化、自主语言、自主联网和自主科研的基础。