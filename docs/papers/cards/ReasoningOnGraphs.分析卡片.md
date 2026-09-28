# 论文分析卡片 · RoG（Reasoning on Graphs）

> 短卡模式（§7）：本篇与 SSEA 立场无回溯路径（语言域 KGQA），仅作 D 基准对照。
> 篇幅 80–120 行；3.1 逐条判定是本卡主要价值。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2023-10-02 Reasoning on Graphs Faithful and Interpretable Large Language Model.pdf` |
| 标题 | Reasoning on Graphs: Faithful and Interpretable Large Language Model Reasoning |
| 作者 / 机构 | Linhao Luo, Yuan-Fang Li, Gholamreza Haffari（Monash University）；Shirui Pan（Griffith University） |
| 发表时间 / 出处 | ICLR 2024；arXiv:2310.01061v2（v1 2023-10-02，v2 2024-02-24） |
| 论文链接 | https://arxiv.org/abs/2310.01061 |
| 代码链接 | https://github.com/RManLuo/reasoning-on-graphs |
| 标签 | 领域：KGQA / LLM×KG；方法族：planning-retrieval-reasoning + 指令微调；关键词：faithful plan, relation path, interpretability |
| **应用裁决** | **D 基准对照**（不采用为组件） |
| 优先级 | P3（备查） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

## 1. 一句话定位

- **论文主张**：把 LLM 的「生成计划」接地到外部 KG 的**关系路径**上，再按该路径用约束 BFS 检索出
  **推理路径**供 LLM 作答，从而在 KGQA 上同时得到 SOTA 精度与「忠实、可解释」的推理链。
- **对 SSEA 的意义**：不适用——其图是**外部知识语料 KG**（撞 C8）、NL 在推理闭环（撞 C2）。
  唯一价值是「**忠实 = 可回溯到外部符号存储的可执行路径**」这一**判据形状**，可作 SSEA 审计链
  （Ouroboros 缺失防御）与可解释结构提案的**对照臂**，而非可搬运组件。

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- 问题本身：LLM 做多跳 KGQA 时缺最新知识、易幻觉（Fig.1：误判 Justin Bieber 兄弟关系）。
- 指出的既有缺陷：语义解析法生成的逻辑查询常不可执行 → 无答案；检索增强法只把 KG 当事实库、
  丢掉**结构信息**（关系路径）。

### 2.2 核心思想
1. 用**关系路径**（relation path，relation 序列）而非实体做计划——关系比实体稳定，且总能检索到最新知识。
2. 计划必须**被 KG 接地**（grounded）：生成的路径要在 KG 上存在实例路径，才保证「忠实」。
3. 计划与推理**共享同一 LLM**、联合指令微调；推理时计划模块可插拔给任意 LLM。

### 2.3 关键机制 / 零件
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| Relation path as faithful plan | question → z={r1..rl} | LLM 生成、被 KG 接地的计划 | §4.1, Eq.4, Fig.2 |
| Constrained BFS retrieval | (q, z, KG) → Wz | 按关系路径在 KG 上取实例路径 | §4.4 Eq.9, Alg.1(p.17) |
| FiD reasoning over paths | (q, Wz) → answer a | 多路径独立聚合、去噪作答 | §4.4 Eq.5–6 |
| Planning distillation | shortest paths Z* → Pθ(z\|q) | 用 KG 最短路监督规划 | §4.2 Eq.4 |
| Explanation prompt | reasoning paths → NL 解释 | 观察员面解释输出 | A.10(p.23), Table 20 |

### 2.4 关键表示与数据结构
- KG：G={(e,r,e′)}（三元组集合）；relation path z 是 relation 序列；reasoning path wz 是实例路径
  e0→r1→e1→…→el（§3）。计划以特殊 token 序列化：`<PATH>r1<SEP>…<SEP>rl</PATH>`（§4.3）。
- 微调数据：planning 216,006 / retrieval-reasoning 30,465 / interpretability 2,000（Table 11, p.18）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| KGQA WebQSP | 21 baselines（5 类） | Hits@1 **85.7** / F1 **70.8** | Table 1, p.7, test split，单次报告 |
| KGQA CWQ | UniKGQA / DECAF | Hits@1 **62.6** / F1 **56.2**（vs UniKGQA +22.3/+14.4） | Table 1, p.7 |
| 消融 w/o planning | RoG 本体 | WebQSP F1 74.77 → **49.69** | Table 2, p.8 |
| 消融 w/o reasoning | RoG 本体 | WebQSP Precision 74.77 → 46.90（Recall 反升） | Table 2, p.8 |
| 插拔计划模块 | ChatGPT 等 | ChatGPT Hits@1 66.77 → **81.51** | Table 3, p.8 |
| 迁移 MetaQA-3hop | train-from-scratch | 88.98 vs 84.81 Hits@1（transfer 更优） | Table 12, p.20 |

### 2.6 论文自陈局限与边界条件
- **未提及**：全文无独立 Limitations 节（仅 Ethics / Reproducibility 声明，p.10）。
- 推断假设依赖：问题实体与答案**已被标注并链接到 KG**（§3 明写 Tq,Aq⊆E）；KG 需完整、结构化。
- 推断不适用情形：无 KG 或实体链接失败 → 检索不到路径 → 无答案（复现语义解析法的病）；KGQA 专用。

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据 | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构 | ✗ | 全文为 LLM 语言生成式 KGQA（生成 path/answer/explanation），无生存控制环、无感知—行动快环 | 不适用；仅可借「接地计划」形状 |
| **C2** NL 只作观察员接口 | ✗ | LLM 生成的 relation path 与 answer 位于核心推理闭环；plan 生成即 NL 进控制面 | 把 plan 降级为结构化符号路径，NL 只留解释面（Table 20 的解释面可搬） |
| **C3** 权重/记忆/技能三分离 | ◐ | 有三方：KG（外部知识）、LLM 权重（参数）、relation path（近似计划/技能）；但 KG 知识经微调**蒸馏进权重**，边界被抹 | KG 只读、不蒸馏；权重侧不吸收事实 |
| **C4** 低算力低带宽 | ✗ | 2×A100-80G、38h 训练（A.6, p.19）；检索量随 top-K 膨胀（Fig.4, p.21） | 只借「约束 BFS」的窄检索，不借规模 |
| **C5** 精准回忆历史 | ◐ | 有精准检索（约束 BFS 按关系路径取实例路径，Eq.9/Alg.1），但对象是 KG **事实**非**经历**；无写入/遗忘/合并 | 检索键从「事实实体」换成「经历索引」 |
| **C6** 可自主修改自身 | ✗ | 仅监督式指令微调（Eq.4 用 KG 最短路监督）；无提案/边界/验证/应用四分，修改不自发 | 不采用；自修改改用 Gödel Agent / PSN 形状 |
| **C7** 保存/恢复/变异/继承 | ✗ | 无 GenePackage、无变异/继承 | planning 数据（216,006）可作可打包结构，但需重构 |
| **C8** 给基因先验，不给知识语料 | ✗（关键冲突） | 把 Freebase 事实语料（8,309,195 triples, Table 10；216,006 planning, Table 11）**蒸馏进权重**，正是「给知识语料」 | 只留结构先验（planning-retrieval-reasoning 骨架 + 关系路径 schema）；事实留外部只读、按需检索、不入权重、不跨代 |
| **C9** 不设外部评分，只有淘汰函数 | ✗ | 规划损失用 KG 最短路作**外部监督**（Eq.4）；评测用 Hits@1/F1（外部评分） | 以内在预测误差替换最短路监督；评测只留淘汰式判据 |
| **C10** 创新在 L2/L3/L4 | ✓（L2） | 创新在信息流：plan→retrieve→reason 的接地控制骨架（Fig.2）；L1 是借用的 LLaMA2 | 符合「创新不在 L1 算子」；但属**语言域** L2 |

### 3.2 L1–L4 层级定位
| 层次 | 论文提供 | 对 SSEA 价值 |
|---|---|---|
| L1 算子层 | LLaMA2-Chat-7B（借用，可替换） | 无（已属 L1 借用） |
| L2 信息流层 | planning-retrieval-reasoning 骨架 + 约束 BFS | 借「接地计划→可检索验证」的信息流**形状** |
| L3 学习层 | 双任务联合指令微调（Eq.7） | 仅对照（外部监督学习） |
| L4 演化层 | — 未提及 | 无 |

### 3.3 模块映射
| 论文构件 | SSEA 落点 |
|---|---|
| relation path as plan | 结构提案（ΔS/ΔR）的**可验证形状**（对照，非采纳） |
| constrained BFS retrieval | 记忆检索（`retrieve`）的窄检索对照 |
| interpretable explanation | 观察员面（C2 合规）日志/解释模板 |
| planning distillation | 冲突：外部知识蒸馏，需改造为内在驱动 |

### 3.4 债务与验收实验对应
- 可回应债务：无直接回应。间接：为「判据形状错（25/26/27/28）」提供「忠实 = 可回溯到外部存储」
  的判据口径参照；为 Gene Manager 的结构提案提供「可执行 + 可验证」的提案格式参照（对照）。
- 可服务验收实验：作实验 3（技能固化 0/33）的**对照臂**——RoG 的 faithfulness 判据（检索命中可验证路径）
  与 SSEA「技能是否真被执行」同属「接地验证」，其「答案覆盖率 vs top-K」曲线形状（Fig.3, p.8）可借来设计技能判据分档。

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 「忠实计划 = 被外部符号存储接地的约束路径」判据形状 | 思想/协议 | 仅借思想 | 审计链 / 四级验证门 | 给结构提案一个可回溯、可执行、可证伪的表示 | 中 |
| 2 | 推理面与解释面分离的 prompt 模板（Table 20, A.10） | 提示设计 | 改造移植 | 观察员面日志 | C2 合规的解释输出面 | 中 |
| 3 | 约束 BFS 按关系路径检索（Alg.1） | 算法 | 仅借思想 | 记忆检索 | 窄而精的检索对照 | 低 |

## 5. 冲突、代价与风险

- **与硬约束的冲突**：C8（外部 KG 知识语料蒸馏进权重，8.3M triples）为硬冲突；另撞 C2（NL 在闭环）、
  C9（外部监督 + 外部评分）、C4（高算力）。
- **隐含假设与失效条件**：假设 Tq,Aq⊆E（实体已链接）；KG 不完整/链接错误 → 无路径 → 无答案。
- **算力 / 带宽 / 工程代价**：2×A100-80G / 38h（A.6）；检索时间随 top-K 线性增长（Fig.4）。
- **搬运后的可能退化模式**：若把 RoG 的 faithfulness 判据直接搬到 SSEA，会把「能检索到外部事实」
  误当「结构合法」——**重演债务 25/26「判据形状错」**。

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象 | 说明 |
|---|---|---|
| 前置依赖 | 结构化外部存储（KG / SSEA 记忆·技能库） | 无接地存储则 faithfulness 无从定义 |
| 互补 | **Ouroboros**（审计链 / 缺失防御清单） | RoG 的「接地计划」提供审计链中「提案→可验证溯源」的表示范式 |
| 互补 | **A-MEM** / **G-Memory**（图式记忆） | 三者同为「图结构 + 检索」组织形态：A-MEM 是 Zettelkasten 链接拓扑、G-Memory 是图记忆，RoG 提供「**路径式**检索」对照 |
| 替代 / 近亲 | **ThinkOnGraph** | 同为 LLM×KG 的 agentic 推理（均引 Sun et al. 2024）；RoG 走「先规划后检索」而非「逐步游走」 |
| 对照 | **ExperienceToStrategy** / **Misevolve** | RoG 的忠实是「对外部事实忠实」，缺「经历」与「演化威胁」两维；Misevolve 关心误演化威胁，ExperienceToStrategy 关心经历→策略，正补 RoG 所缺 |

### 6.2 推荐组合方案
- **组合**：本篇（仅形状）+ Ouroboros（审计链）+ A-MEM / G-Memory（图记忆）
- **接口形态**：把 RoG 的 relation path 形状（e0→r1→e1→…）当作审计链「可验证路径记录」的**格式**，
  弃外部 KG 蒸馏
- **组合后新增能力**：结构提案（ΔS/ΔR）带可回溯溯源路径，使验证门「只判合法性」有可执行载体
- **新增风险**：误把「检索到」当「合法」；引入外部语料违反 C8

### 6.3 本篇在组合中的典型角色
- **对照臂 / 判据形状参照**（faithful-plan 的可验证性范式），非可用组件。

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由 |
|---|---|---|
| 项目相关性 | 2 | KGQA 语言任务，与生存域无关；仅 faithfulness 概念与审计链相关（推断） |
| 立场兼容性 | 1 | 撞 C8/C2/C9/C4（推断） |
| 可搬运性 | 2 | 仅「判据形状 / 解释面模板」可干净拆出，其余强耦合 KGQA |
| 证据强度 | 4 | ICLR 2024，21 baselines，两 benchmark SOTA，消融完整（实测） |
| 组合价值 | 2 | 作审计链判据形状参照（推断） |
| 落地成本 | 3 | 借形状成本低，但需防误用（反向口径） |

## 8. 裁决与下一步

- **应用等级**：**D 基准对照**——理由：其图是外部 KG 知识语料（撞 C8）、NL 在推理闭环（撞 C2）、
  外部监督与评分（撞 C9）、高算力（撞 C4），不可作为组件；但「忠实 = 可回溯到外部符号存储的
  可执行路径」是 SSEA 审计链与可解释结构提案的有效**对照形状**，值得保留在论文池。
- **优先级**：P3
- **建议动作**：
  1. 在审计链（Ouroboros）设计文档中，把 RoG 的 relation path 形状登记为「溯源路径记录」的候选格式。
  2. 不落地任何 RoG 代码；只在实验 3 的判据设计时引用其「覆盖率 vs top-K」曲线形状。
- **最小验证实验**：
  - 双臂 / 消融：A = 结构提案（ΔS/ΔR）须附**可回溯到外部存储的路径**；B = 现状（无溯源路径）。
  - 判据分档：机制计数（多少提案带可验证溯源路径）→ 行为差（验证门误纳率 / 拒绝率）→ 淘汰结果（升版后回归）。
  - 预期与证伪：预期 A 臂验证门误纳率下降；**证伪 = 溯源路径存在但误纳率不变**（说明路径只是装饰、未接入验证门）
    ——这正是债务 25/26 的复现。
- 若 **D 基准对照**：作为对照臂使用，不进入 SSEA 实现。

## 9. 待确认问题

- RoG 无独立 Limitations 节，2.6 的边界均为**推断**，需作者确认。
- 论文的「faithfulness」主要为 answer coverage / retrieval precision 的**量化**，未做因果忠实性
  （explanation = 真实计算过程）检验——需核对它是否等价于「解释即真实因果」。
- Table 3（p.8）正文称 ChatGPT/Alpaca/LLaMA2/Flan-T5 提升「8.5%, 15.3%, 119.3%」，列了 4 个模型
  却只给 3 个百分比，疑原文笔误，需核对。

## 附：关键摘录与出处

| 摘录 | 页码 |
|---|---|
| "we present a planning-retrieval-reasoning framework, where RoG first generates relation paths grounded by KGs as faithful plans" | p.1（Abstract） |
| Q(z)≃Q(z\|a,q,G)=1/\|Z\|（有效路径均匀分布）；用最短路 Z*⊂Z 作监督 Lplan=−1/\|Z*\| Σ logPθ(z\|q) | p.5（Eq.3–4） |
| 假设 "the entities eq∈Tq mentioned in q and answers a∈Aq are labeled and linked to the corresponding entities in G, i.e., Tq,Aq⊆E" | p.3（§3） |
| Freebase：2,566,291 entities / 8,309,195 triples；指令数据 planning 216,006 / retrieval-reasoning 30,465 | p.18（Table 10–11） |
| RoG 85.7/70.8（WebQSP），62.6/56.2（CWQ） | p.7（Table 1） |
| 消融 w/o planning WebQSP F1 49.69；w/o reasoning Precision 46.90 | p.8（Table 2） |
| 训练 "2 A100-80G GPUs for 38 hours"，batch 4，lr 2e-5，3 epochs | p.19（A.6） |
