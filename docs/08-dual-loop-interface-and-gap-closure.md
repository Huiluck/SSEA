# SSEA v0.3.1 双环接口与模糊地带补全设计

**文档性质**：补全设计 / 任务书 07 的修订依据
**修订对象**：[07-ssea-v0.3.1-charter.md](07-ssea-v0.3.1-charter.md)（当前有效任务书）
**产生原因**：逐条核对 v0.3.1 后发现 13 处模糊地带，其中 7 处阻塞 Milestone 1（接口协议）与 Milestone 2（快环原型）；另发现 1 项模块数变更
**覆盖方式**：本文 2.1–2.6 覆盖 7 处阻塞项（2.6 一节含两项），3.1–3.7 覆盖其余 6 处加模块数变更
**本阶段边界**：只补设计，不重写任务书，不写模型代码

---

## 1. 补全的裁判标准

模糊地带一律按以下十条推导。任何结论若无法回溯到其中至少一条，即视为偏离 SSEA 立场，不予采纳。

| # | 约束 | 出处 |
|---|---|---|
| C1 | 生存控制架构，非语言生成架构 | 07 修订二、4.1 |
| C2 | 自然语言只作观察员接口，不进控制闭环 | 07 修订二、7.2 |
| C3 | 权重 / 记忆 / 技能三分离 | 07 4.2 |
| C4 | 低算力、低带宽 | README 项目目标、07 5.1 |
| C5 | 精准回忆历史 | README 项目目标 |
| C6 | 可自主修改自身代码与参数权重 | README 项目目标 |
| C7 | 可保存 / 恢复 / 变异 / 继承 | README 项目目标、07 4.5 |
| C8 | 给基因先验，不给知识语料 | 03 第九节 |
| C9 | 不设评分函数，只有淘汰函数 | 01 原始构想、07 8.9 |
| C10 | 创新在 L2 信息流 / L3 学习 / L4 演化，不在 L1 算子 | 06 问题 1、07 2.1 |

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

实测修正后 7/8 seed 可达、睡眠占寿命 6%–12%。完整推导与数字见
[14-overview-and-roadmap.md](14-overview-and-roadmap.md) §6.3.1 与
[13-milestone4-plan.md](13-milestone4-plan.md) §6.6；
实现见 `SSEA/metabolic_monitor.py::MetabolicMonitor.wants_sleep`。

**对任务书的改动**：第 5 节新增 5.5「慢环触发时机」；第 6.10 代谢监控器增补睡眠判定条件；第 12 节验收实验增补一项睡眠期实验（见第 4 节）。

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

C9 要求不设评分函数，但模型必须有内在生存动力，否则会退化成不动（07 风险 5）。这三个信号就是替代评分函数的内在驱动来源，必须接线，否则风险 5 的缓解措施落空。

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
