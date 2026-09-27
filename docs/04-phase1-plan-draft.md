# 一、第一阶段总目标

我们第一阶段的目标不是做完整生态系统，而是：

> **设计并实现一个最小可行的模型本体：它能感知、行动、记忆、学习、保存、恢复、变异，并具备小范围自我修改能力。**

可以把它理解为：

> 不先造大自然，先造一个能进入大自然的“最小生命体”。

---

# 二、第一阶段任务列表总览

建议分为五个模块：

| 模块 | 目标 | 优先级 |
|---|---|---|
| A. 边界与范围 | 明确模型本体、接口、生态系统的边界 | P0 |
| B. 模型接口协议 | 定义感知、身体、动作、记忆、通信、基因接口 | P0 |
| C. 最小模型架构 | 设计大脑、记忆、行动、学习、遗传模块 | P0 |
| D. 最小测试环境 | 提供一个非生态的简单测试桩 | P1 |
| E. 可复用成果选型 | 决定哪些开源/论文成果可以直接借用 | P0 |

---

# 三、详细任务列表

---

## 模块 A：边界与范围定义

目标：防止项目再次扩散到生态系统、多智能体社会、复杂物理世界。

### A1. 制定“模型架构 / 接口 / 生态系统”边界表

要定义清楚：

- 哪些属于模型内部算法
- 哪些属于模型与环境的接口
- 哪些属于外部生态系统
- 第一阶段不实现哪些内容

产出：

```text
《SSEA v0.3 边界定义表》
```

内容包括：

| 要素 | 模型架构 | 接口 | 生态系统 | 第一阶段是否实现 |
|---|---|---|---|---|
| 身体 | 身体状态表征 | 身体输入/输出接口 | 物理规则 | 接口级实现 |
| 动作 | 动作生成策略 | 动作指令格式 | 动作后果 | 接口级实现 |
| 感知 | 感知编码器 | 观测输入格式 | 世界生成 | 接口级实现 |
| 大脑 | 状态核心 | 内部状态流 | 环境反馈 | 是 |
| 繁衍 | 基因保存/恢复/变异 | 遗传接口 | 繁衍规则 | 基因接口实现 |
| 同族语言 | 通信编码/解码 | 通信向量接口 | 语言演化 | 暂不实现完整语言 |
| 记忆 | 记忆读写机制 | 记忆存储格式 | 历史事件来源 | 是 |

---

### A2. 制定“第一阶段不做清单”

非常重要。建议明确不做：

- 不做完整四季生态
- 不做复杂自然灾害
- 不做多模型社会结构
- 不做自然语言主接口
- 不做高分辨率视觉
- 不做全量权重反向传播训练
- 不做复杂物理引擎
- 不做完整人类语言知识库接入
- 不做观察员评分系统

产出：

```text
《第一阶段不做清单》
```

---

## 模块 B：模型接口协议设计

目标：先定义“生命体如何与世界交换信息”，而不是先写模型。

这是第一阶段最重要的工程基础。

---

### B1. 定义观测接口，Observation

模型接收的环境信息。

建议格式：

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

产出：

```text
《Observation 协议》
```

可用资源：

- 具身智能观测格式：MineDojo / Voyager / SIMA
- 事件相机思想：event-based perception
- 稀疏对象向量：YOLO-like object representation

---

### B2. 定义身体状态接口，BodyState

模型感知自身状态。

建议格式：

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

产出：

```text
《BodyState 协议》
```

可用资源：

- 强化学习环境中的状态空间定义
- 机器人本体感知接口
- 具身智能中的本体感觉表征

---

### B3. 定义动作接口，Action

模型不输出自然语言，而是输出多通道控制信号。

建议格式：

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
        "target": str,
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
        "proposal": str,
        "payload": dict
    }
}
```

产出：

```text
《Action 协议》
```

可用资源：

- Voyager 的 skill library
- 机器人动作空间定义
- LLM tool-use / function calling
- 非自然语言动作接口设计

---

### B4. 定义记忆接口，Memory

模型精准回忆历史，不依赖全部塞进权重。

建议格式：

```python
MemoryItem = {
    "id": str,
    "timestamp": float,
    "type": str,
    "context_vector": list[float],
    "content_vector": list[float],
    "outcome": str,
    "importance": float
}
```

记忆类型：

- 事件记忆
- 技能记忆
- 规则记忆
- 社会记忆，可选
- 身体经验记忆

产出：

```text
《Memory 协议》
```

可用资源：

- RAG
- kNN-LM
- 向量数据库
- Agent Workflow Memory
- modern Hopfield networks

---

### B5. 定义通信接口，CommunicationSignal

第一阶段不设计完整语言，只定义通信向量。

建议格式：

```python
CommunicationSignal = {
    "sender_id": str,
    "receiver_id": str,
    "signal": list[float],
    "timestamp": float,
    "priority": int
}
```

产出：

```text
《Communication 协议》
```

可用资源：

- 多智能体通信学习
- latent communication
- emergent language
- multi-agent signaling

---

### B6. 定义基因接口，GenePackage

模型必须可保存、可复制、可变异、可继承。

建议格式：

```python
GenePackage = {
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

产出：

```text
《GenePackage 协议》
```

可用资源：

- 模型序列化：PyTorch state_dict / safetensors
- LoRA / adapter 保存
- evolutionary NAS
- weight inheritance 论文
- NEAT / HyperNEAT

---

## 模块 C：最小模型架构设计

目标：设计模型内部如何运行。

---

### C1. 设计感知编码器，Perception Encoder

任务：

把外部观测压缩成低维内部向量。

输入：

```text
Objects
Events
BodyState
EnvironmentSummary
```

输出：

```text
perception_vector
```

可用资源：

- 小型 MLP encoder
- sparse attention
- object-centric learning
- event-based encoding
- 视觉特征编码器，可选

第一阶段不建议：

- 直接处理高分辨率图像
- 使用大型视觉 Transformer
- 使用复杂多模态模型

---

### C2. 设计状态核心，State Core

任务：

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

| 架构 | 优点 | 风险 |
|---|---|---|
| GRU | 简单、低算力、易实现 | 长程记忆一般 |
| Mamba / SSM | 低带宽、长序列友好 | 工程复杂度稍高 |
| Liquid Neural Network | 动态适应强 | 生态较小 |
| Small Sparse Transformer | 表达强 | 算力可能偏高 |
| Small MoE | 稀疏激活、低计算 | 路由复杂 |

第一阶段建议：

```text
GRU 或 Mamba 小型状态核心
+
轻量 MLP 行动头
+
外部记忆
```

产出：

```text
《State Core 架构草案》
```

---

### C3. 设计记忆系统，Memory System

任务：

让模型能读写历史经验，而不是全部依赖权重。

包含：

- 短期工作记忆
- 长期事件记忆
- 技能记忆
- 规则记忆

核心机制：

```text
当前状态 → 检索相关记忆 → 融合进状态核心 → 影响行动
```

产出：

```text
《Memory System 设计》
```

可用资源：

- RAG
- vector search
- memory networks
- Agent Workflow Memory
- Voyager skill library

---

### C4. 设计行动生成器，Action Head

任务：

把模型内部意图转换成动作。

输出通道：

```text
运动
操作
通信
记忆写入
技能调用
自我修改请求
```

产出：

```text
《Action Head 设计》
```

可用资源：

- function calling
- tool use
- skill library
- robot control policy
- program synthesis

---

### C5. 设计学习机制，Plasticity / Learning

任务：

改变“必须靠喂数据和全量权重训练”的范式。

第一阶段建议三类学习：

#### 1. 记忆学习

```text
新事件 → 写入记忆
高误差事件 → 高优先级写入
```

#### 2. 技能学习

```text
某行动序列多次成功 → 固化为技能
```

#### 3. 局部参数学习

```text
只更新小型 adapter / policy head / retrieval head
```

产出：

```text
《学习机制设计》
```

可用资源：

- STaR / Quiet-STaR
- self-generated data
- skill consolidation
- LoRA / adapter
- local plasticity
- meta-learning

---

### C6. 设计遗传与继承机制，Heredity

任务：

让模型可以死亡、保存、复制、变异。

核心接口：

```python
save_gene()
load_gene()
mutate_gene()
inherit_from_parent()
```

遗传内容：

- 架构
- 核心权重，可选压缩
- 本能 adapter
- 技能库
- 记忆索引
- 行为策略
- 代谢策略

产出：

```text
《遗传机制设计》
```

可用资源：

- evolutionary algorithms
- weight inheritance
- NEAT
- model merging
- safetensors
- LoRA merging

---

### C7. 设计自我修改机制，Self-Modification

任务：

让模型可以小范围修改自身，但不能失控。

第一阶段只允许修改：

- 技能库
- 行动阈值
- 检索策略
- 小型 adapter
- 提示模板，如果使用
- 规则库

不允许直接修改：

- 核心操作系统
- 淘汰函数
- 观察员接口
- 安全沙盒
- 硬件权限

产出：

```text
《自我修改权限表》
```

可用资源：

- Darwin Gödel Machine
- Gödel Agent
- AI Scientist
- DeepSeek DSec sandbox
- code sandbox
- unit testing

---

## 模块 D：最小测试环境

目标：不是生态系统，只是验证模型本体能否运行。

---

### D1. 选择最小环境类型

候选：

| 环境 | 优点 | 缺点 |
|---|---|---|
| GridWorld | 简单、易调试 | 表达弱 |
| MiniGrid | 开源成熟 | 偏游戏化 |
| 自研 2D 对象世界 | 可控、接口干净 | 需要开发 |
| 简易物理盒子 | 可测试身体动作 | 复杂度稍高 |
| MineDojo | 生态成熟 | 太重 |

第一阶段建议：

```text
自研极简 2D 对象世界
或
MiniGrid 改造版
```

原因：

- 足够测试感知、动作、记忆、学习
- 不会被复杂物理拖住
- 容易控制接口

---

### D2. 定义环境桩，Environment Stub

环境只需要提供：

```python
reset() -> Observation
step(Action) -> Observation, Feedback
```

Feedback 包括：

```python
Feedback = {
    "energy_change": float,
    "damage_change": float,
    "prediction_error": float,
    "task_success": bool,
    "survived": bool
}
```

注意：

这里不是评分函数，而是环境反馈信号。

产出：

```text
《最小环境桩接口》
```

---

## 模块 E：可复用成果选型

目标：明确哪些东西可以直接借鉴，不要重复造轮子。

---

# 四、这一步有什么可用？

下面按我们架构模块列出可用资源。

---

## 1. 外部技能库 / 代码作为动作

可用项目：

| 项目 | 可借鉴点 |
|---|---|
| Voyager | 技能库、自动课程、代码即技能 |
| ASPIRE | 机器人开放式技能发现 |
| Agent Workflow Memory | 工作流记忆复用 |

适合用于：

- Action Head
- Skill Library
- 长期技能记忆

---

## 2. 自我修改代码

可用项目/论文：

| 项目 | 可借鉴点 |
|---|---|
| Darwin Gödel Machine | 自我重写代码 |
| Gödel Agent | 自指代理框架 |
| AI Scientist | 自动提出实验并验证 |
| DeepSeek DSec | 沙盒基础设施 |

适合用于：

- 自我修改模块
- 沙盒验证
- 代码变更安全机制

---

## 3. 遗传、复制、变异、权重继承

可用论文/方法：

| 方法 | 可借鉴点 |
|---|---|
| Weight Inheritance | 父代权重传递给子代 |
| NEAT | 网络结构演化 |
| HyperNEAT | 结构生成 |
| Model Merging | 模型融合 |
| LoRA / Adapter | 小规模可遗传模块 |

适合用于：

- GenePackage
- 繁衍接口
- 本能内化
- 子代初始化

---

## 4. 外部记忆 / 精准回忆

可用方法：

| 方法 | 可借鉴点 |
|---|---|
| RAG | 外部检索 |
| kNN-LM | 检索式语言模型 |
| Agent Workflow Memory | 行动经验复用 |
| Modern Hopfield Networks | 联想记忆 |
| Vector Database | 记忆检索 |

适合用于：

- 长期事件记忆
- 技能记忆
- 历史经验检索

---

## 5. 非自然语言动作 / 潜空间通信

可用方法：

| 方法 | 可借鉴点 |
|---|---|
| Latent Communication | 模型间高维通信 |
| Emergent Language | 自发通信协议 |
| Tool Use / Function Calling | 结构化动作 |
| Robot Control Policy | 连续控制输出 |

适合用于：

- 通信接口
- 动作接口
- 同族语言雏形

---

## 6. 世界模型 / 预测误差学习

可用项目/论文：

| 项目 | 可借鉴点 |
|---|---|
| Dreamer | 世界模型、梦境训练 |
| MuZero | 价值/策略/模型学习 |
| TD-MPC | 模型预测控制 |
| Active Inference | 预测误差驱动 |
| Predictive Coding | 局部预测学习 |

适合用于：

- 世界状态预测
- 无外部数据训练
- 内在好奇/误差学习

---

## 7. 低算力核心网络

可用架构：

| 架构 | 可借鉴点 |
|---|---|
| Mamba / State Space Model | 低带宽、长状态 |
| GRU | 简单稳定 |
| Liquid Neural Network | 动态适应 |
| Sparse Transformer | 稀疏计算 |
| Small MoE | 按需激活专家 |

适合用于：

- State Core
- 低算力大脑
- 事件驱动控制

---

# 五、第一阶段里程碑设计

建议设置五个里程碑。

---

## Milestone 0：边界冻结

目标：

确定第一阶段只做什么、不做什么。

产出：

- 边界表
- 不做清单
- 第一阶段目标说明

验收：

- 团队一致同意不先做完整生态
- 明确模型本体优先

---

## Milestone 1：接口协议完成

目标：

定义模型与环境之间的所有接口。

产出：

- Observation
- BodyState
- Action
- MemoryItem
- CommunicationSignal
- GenePackage
- Feedback

验收：

- 所有接口可以用 Python dataclass 或 JSON Schema 表示
- 不依赖具体模型实现

---

## Milestone 2：最小模型骨架完成

目标：

实现模型内部数据流。

产出：

```text
Observation
→ Perception Encoder
→ State Core
→ Memory Retrieval
→ Action Head
→ Action
```

验收：

- 模型可以接收 Observation
- 模型可以输出合法 Action
- 模型可以写入/读取 Memory

---

## Milestone 3：最小环境桩完成

目标：

提供一个极简环境用于测试。

产出：

- 可运行环境
- reset()
- step()
- 简单物体
- 简单能量变化

验收：

- 模型可以在环境中持续运行若干步
- 环境能返回 Observation 和 Feedback

---

## Milestone 4：遗传与自我修改雏形完成

目标：

模型可以保存、恢复、变异。

产出：

- save_gene()
- load_gene()
- mutate_gene()
- 小型自我修改提案机制

验收：

- 模型死亡后可以保存基因
- 可以从基因恢复模型
- 子代与父代存在可追踪差异

---

# 六、第一周建议任务

如果按一周推进，我建议如下：

## 第 1 天：边界冻结

完成任务：

- 模型架构 / 接口 / 生态边界表
- 第一阶段不做清单

产出：

```text
《SSEA v0.3 第一阶段边界定义》
```

---

## 第 2 天：接口协议

完成任务：

- Observation
- BodyState
- Action
- MemoryItem
- GenePackage

产出：

```text
《SSEA v0.3 接口协议》
```

---

## 第 3 天：最小模型数据流

完成任务：

- 感知编码器
- 状态核心
- 行动头
- 记忆接口

产出：

```text
模型内部数据流图
```

---

## 第 4 天：最小环境桩

完成任务：

- 简单对象世界
- reset/step
- Feedback

产出：

```text
最小测试环境
```

---

## 第 5 天：最小运行循环

完成任务：

```text
模型运行
→ 输出动作
→ 环境反馈
→ 记忆写入
→ 保存基因
```

产出：

```text
可运行 MVP 原型
```

---

# 七、当前最重要的决策点

在开始写代码之前，我们需要确定五个关键决策。

---

## 决策 1：第一阶段使用什么核心网络？

建议候选：

```text
GRU
Mamba
Small MoE
Liquid Neural Network
```

推荐：

```text
先用 GRU 或小型 Mamba。
```

原因：

- 工程简单
- 容易调试
- 低算力
- 适合状态驱动

---

## 决策 2：动作空间是连续、离散还是混合？

建议：

```text
混合动作空间
```

即：

- 运动：连续向量
- 操作：离散目标
- 技能：离散调用
- 通信：连续向量
- 记忆：结构化操作

---

## 决策 3：记忆系统使用向量库还是结构化库？

建议：

```text
第一阶段使用结构化事件 + 向量索引混合。
```

即：

```text
MemoryItem = 结构化字段 + context_vector
```

---

## 决策 4：自我修改范围多大？

建议：

```text
第一阶段只允许修改技能、规则、阈值、小型 adapter。
```

不允许：

- 改核心架构
- 改安全机制
- 改环境接口
- 改淘汰函数

---

## 决策 5：是否接入人类语言？

建议：

```text
第一阶段不接入人类语言作为主接口。
```

最多保留：

```text
可选观察员日志接口
```

模型内部不以自然语言为主。

---

# 八、最终任务清单简版

可以直接作为项目看板：

```text
P0 边界定义
  - 模型架构 / 接口 / 生态边界表
  - 第一阶段不做清单

P0 接口协议
  - Observation 协议
  - BodyState 协议
  - Action 协议
  - MemoryItem 协议
  - CommunicationSignal 协议
  - GenePackage 协议
  - Feedback 协议

P0 最小模型架构
  - Perception Encoder
  - State Core
  - Memory System
  - Action Head
  - Learning / Plasticity
  - Heredity Module
  - Self-Modification Module

P1 最小测试环境
  - Environment Stub
  - Simple Object World
  - Energy / Damage Feedback
  - Run Loop

P1 可复用成果选型
  - Voyager / Skill Library
  - Darwin Gödel Machine / Self-Modification
  - Weight Inheritance / Heredity
  - RAG / Memory
  - Dreamer / World Model
  - Mamba / Low-compute Core
```

---

# 九、我建议下一步先做哪一项？

我建议下一步直接做：

> **《SSEA v0.3 第一阶段任务书》**

内容包含：

1. 第一阶段目标  
2. 边界表  
3. 不做清单  
4. 接口协议  
5. 模块划分  
6. 里程碑  
7. 可复用资源表  
8. 风险清单  

如果你同意，我下一条可以直接输出这份任务书，格式可以直接作为项目立项文档使用。