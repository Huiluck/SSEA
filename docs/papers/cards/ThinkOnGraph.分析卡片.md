# 论文分析卡片 · Think-on-Graph（ToG）

> 短卡模式（§7）：与 SSEA 立场无回溯路径（外挂人工知识图谱 + LLM 打分排序）；
> 但「在图上逐步探索」的形状与 SSEA 记忆/技能图结构检索同构，保留作对照臂。
## 0. 卡片头（速览）
| 项 | 内容 |
|---|---|
| 文件名 | `2023-07-15 Think-on-Graph Deep and Responsible Reasoning of Large Language Model on.pdf` |
| 标题 | **Think-on-Graph: Deep and Responsible Reasoning of LLM on Knowledge Graph** |
| 作者 / 机构 | Jiashuo Sun, Chengjin Xu, Lumingyuan Tang 等；IDEA Research、厦门大学、USC、HKUST、MSRA（p1） |
| 发表时间 / 出处 | ICLR 2024；arXiv:2307.07697v6，2024-03-24（31 页） |
| 论文链接 / 代码 | arXiv:2307.07697 / https://github.com/IDEA-FinAI/ToG |
| 标签 | KBQA · LLM⊗KG · beam search on graph · 可追溯/可纠正 · 免训练 prompting |
| **应用裁决** | **D 基准对照**（外挂人工 KG + LLM 打分排序，撞 C8/C9；仅作「逐步图检索」对照臂） |
| 优先级 | **P3** |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |
## 1. 一句话定位
- **论文主张**：提出 **LLM⊗KG** 紧耦合范式——把 LLM 当 agent，在外部知识图谱上做 **beam search（深度 D、宽度 N）**，逐步探索「关系→实体」得 top-N 推理路径，直到 LLM 判定信息足够或到深度上限；免训练即在 9 数据集中 6 个取得 SOTA（摘要 p1；§3.2 p6–7）。
- **对 SSEA 的意义 / 为什么不适用**：它解决「LLM 多跳问答幻觉/不可解释」，用**外部人工 KG（Freebase/Wikidata）**且以 **LLM 打分排序路径**——直接撞 C8、C9；其「逐步 search→prune→reason」形状可作 SSEA 记忆/技能图检索的对照。
## 2. 问题 — 机制 — 证据
### 2.1 论文要解决的问题
- 问题本身：LLM 需长逻辑链、多跳知识推理时易幻觉，缺可解释性/可追溯性（p1–2）。
- 既有方案缺陷：LLM-only（CoT）用陈旧内参；LLM⊕KG（LLM 生成 SPARQL）检索命中即断，信息不足即失败（Fig.1 p2）。
### 2.2 核心思想
1. LLM 不一次读完 KG，而像 agent **逐跳交互探索**，每跳只让 LLM 在候选关系/实体中挑 top-N（把「遍历图」降为「局部打分选择」）。
2. 两段式探索：先探关系、再用选中关系引导实体探索，避免一次喂入海量邻居（§2.1.2 p4）。
### 2.3 关键机制 / 算法（零件清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| 主题实体抽取 | 问题 → top-N 起始实体 | 定位搜索起点 | §2.1.1 p3–4 |
| 关系/实体探索 Search+Prune | 实体/关系 → top-N 候选 | 收窄空间（两段式） | §2.1.2 p4 |
| Reasoning 早停 | 当前路径 → Yes/No | 判信息是否足够 | §2.1.3 p5 |
| ToG-R 变体 | 关系链 + 随机 entity prune | 省约一半 LLM 调用 | §2.2 p5 |
| 知识可追溯/可纠正 | 错误答案 → 回溯可疑三元组并改 | 反哺 KG 质量 | §3.3 p8–9 |
### 2.4 关键表示与数据结构
- 推理路径 `P={p1..pN}`：每条 `pn` 是 `D-1` 个三元组 `(e_s, r_j, e_o)` 的链；候选集 `R^D_cand`/`E^D_cand`（§2.1.2 p4）。
- 搜索由预定义 SPARQL/API 完成，**零训练成本**（§2.1.2 p4；附录 E）。
### 2.5 实验证据
| 任务/基准 | 对照 | 关键数字 | 统计口径 |
|---|---|---|---|
| CWQ / WebQSP | FT SOTA 70.4 / 82.1 | ToG GPT-4 67.6 / 82.6（ToG-R 69.5 / 81.9） | EM Hits@1，Table 1/10–11 p6/23 |
| GrailQA / QALD10 | FT SOTA 75.4 / 45.4 | ToG GPT-4 81.4 / 53.8 | 同上，Table 12–13 p24 |
| 剪枝工具消融 | ChatGPT vs BM25/SBERT | CWQ −8.4%，WebQSP −15.1% | Table 5 p8 |
| KG 来源消融 | Freebase vs Wikidata | CWQ 58.8 vs 54.9；WebQSP 76.2 vs 68.6 | Table 3 p7 |
### 2.6 论文自陈局限与边界条件
- **依赖 KB 正确性**：KB 过时即答错（Phillie Phanatic 案 Table 22 p27 明确指出）。
- 默认 depth=width=3；格式错误略增（<3%）；约 20% 正确答案纯靠 LLM 内参（§B.2 p18–19）。
## 3. SSEA 立场对齐
### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据 | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构 | ✗ | 语言问答控制环，无生存/结构化信号 | 不适用 |
| **C2** 语言只作观察员接口 | ✗ | 自然语言 prompt 即推理与控制本身 | 不适用 |
| **C3** 权重/记忆/技能三分离 | ◐ | LLM 权重与外置 KG 分离，方向与「知识不进权重」一致，但无技能层 | 仅借「知识外置」方向 |
| **C4** 低算力低带宽 | ✗ | 需 GPT-4，每题 10–15 次调用，约 21× CoT 时间（§2.1.3 p5、§C p21–22） | 不适用 |
| **C5** 精准回忆历史 | ✗ | 检索对象是**外部 KB 事实**，非智能体自身经历 | 不适用 |
| **C6** 自改代码/权重 | ✗ | 明确 training-free，不改自身 | 不适用 |
| **C7** 保存/恢复/变异/继承 | ✗ | 无 GenePackage / 无遗传 | 不适用 |
| **C8** 给基因先验，不给知识语料 | ✗ | 核心即外挂人工 KG（Freebase/Wikidata） | 换成 SSEA 自生记忆/技能图 |
| **C9** 不设评分函数 | ✗ | LLM 对 relation/entity 打 0–1 分并排序取 top-N | 用非评分机制替换排序 |
| **C10** 创新在 L2/L3/L4 | ◐ | LLM⊗KG 交互探索属 L2 信息流形状；依赖 LLM L1 算子 | 仅作 L2 对照 |
### 3.2–3.4 层级与模块（简）
- L1：无（借用 GPT-4/ChatGPT/Llama-2）；L2：**LLM⊗KG 交互探索回路**（逐步 search→prune→reason）；L3/L4：无（免训练）。
- 模块落点：逐步图探索 → 记忆/技能图检索**对照臂**；top-N beam + 早停 → 慢环检索预算/早停**对照**。
- 债务对应：可回应「`retrieve` 键收窄 → 召回精度上限低」（作反例对照）；无直接验收实验落点。
## 4. 可借鉴资产清单
| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 两段式逐步图探索（relation→entity, search→prune） | 思想 | 仅作对照 | 记忆/技能图检索 | 召回精度上限 | 中 |
| 2 | top-N beam 多路径保留 + Reasoning 早停 | 思想 | 仅作对照 | 慢环检索预算 | 早停判据形状 | 中 |
| 3 | 知识可追溯/可纠正（trace→localize→correct）协议 | 协议 | 仅借思想 | 观察员解释面 | 可解释性 | 低 |
## 5. 冲突、代价与风险
- **与硬约束冲突**：C8（外挂人工知识语料）、C9（LLM 打分排序）、C4（高算力/高调用）。
- **隐含假设与失效条件**：假设存在一张**覆盖问题所需事实的、正确的**外部 KG；KB 错则全错（Table 22 p27）。
- **工程代价**：每题 10–22 次 LLM 调用；依赖 SPARQL/API 与实体链接。
- **退化模式**：搬入 SSEA 若保留 LLM 打分，会重新引入外部评分与高算力；若换图来源但保留形状，可能因缺 LLM 打分而召回下降（见 §8 证伪条件）。
## 6. 组合分析
### 6.1 关系图谱
| 关系 | 对象 | 说明 |
|---|---|---|
| 前置依赖 | — | 需一张可查询的图；SSEA 目前无记忆/技能图 |
| 对照/互补 | **A-MEM**（链接拓扑）、**G-Memory**（三层图）、**ExperienceToStrategy**（可训练图）、**SkillNet**（pre/post 可达性） | 四者都在**智能体自生图**上做结构检索；ToG 是同一「图结构检索」问题的**外部人工 KG 版本对照臂**——借它的逐步 search→prune→早停形状，但须把图来源换成 SSEA 自有记忆/技能图，并把 LLM 打分排序换成非评分机制（否则撞 C9） |
| 替代 | SSEA `retrieve` | 仅作对照，不作替代 |
| 提及未出卡 | DeepDive | 尚未出卡，暂不连接 |
### 6.2 推荐组合方案
- **组合**：本篇（形状）+ SSEA 自生记忆/技能图（G-Memory 三层图 / A-MEM 链接拓扑）。
- **接口形态**：把「逐步 search→prune→reason」当**检索调度形状**，图换成 SSEA 自图，打分换成非评分准入。
- **新增能力**：多跳、可早停的结构化检索对照基线。**新增风险**：去打分后排序可能退化；图不完整时早停误判。
### 6.3 本篇在组合中的典型角色
- **外部知识版「逐步图检索」的对照臂 / 反例**（证明「图探索」本身可搬，但「外挂 KG + 打分排序」不可搬）。
## 7. 多维度评分（1–5）
| 维度 | 分值 | 理由（证据性质） |
|---|---|---|
| 项目相关性 | 2 | 图检索形状相关，但对象是外部 KB（推断） |
| 立场兼容性 | 1 | 撞 C8/C9/C4（实测机制） |
| 可搬运性 | 2 | 形状可拆，但打分/图来源必须换（推断） |
| 证据强度 | 4 | 9 数据集、多主干、完整消融（实测） |
| 组合价值 | 3 | 可作 A-MEM/G-Memory/E2S/SkillNet 的对照臂（推断） |
| 落地成本 | 2 | 需自建图与替换打分，成本中高（推断） |
## 8. 裁决与下一步
- **应用等级**：**D 基准对照**——理由：外部人工 KG 撞 C8、LLM 打分排序撞 C9、高算力撞 C4，不能进 SSEA 控制环；但「逐步图探索 + top-N beam + 早停」与 SSEA 记忆/技能图检索同构，作对照臂。
- **优先级**：P3。
- **建议动作**：仅在「记忆/技能图检索召回」实验中作**外部 KG 版对照基线**记录。
- **最小验证实验**：
  - 双臂：A 臂 = SSEA 自有图检索（现状命中率 0.5164）；B 臂 = 借 ToG 形状（逐步 search→prune→早停）但**图=SSEA 自图、排序=非评分机制**。
  - 判据（先看分母）：机制计数（图规模、跳数分布）→ 行为差（召回命中率 Δ）→ 淘汰结果。
  - 预期与证伪：若 B 臂在非评分排序下召回不低于 A 臂，则形状可搬；若必须 LLM 打分才不退化，则该形状依赖 C9 违规机制，**弃用**。
## 9. 待确认问题
- 需人工核对：ToG 的 `Reasoning` 早停阈值是否有可替代的非评分实现（论文未提及）。
- 需补查：DeepDive 出卡后是否与「图探索」形状重叠。
## 附：关键摘录与出处
| 摘录 | 页码 |
|---|---|
| “treats the LLM as an agent to interactively explore related entities and relations on KGs” | p1（摘要） |
| “ToG requires 2ND + D + 1 LLM calls … about 21 times longer than that of LLM-only” | p22（附录 C） |
| “this example exemplifies a constraint of ToG … its dependence on the correctness of the KB” | p26–27（Table 22） |
| “performance improves with the search depth and width … we set both the depth and width to 3” | p7（§3.2.3） |
