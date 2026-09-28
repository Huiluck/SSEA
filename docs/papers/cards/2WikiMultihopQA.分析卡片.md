# 论文分析卡片 · 2WikiMultihopQA（短卡）
## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2020-11-02 Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of.pdf` |
| 标题 | Constructing A Multi-hop QA Dataset for Comprehensive Evaluation of Reasoning Steps |
| 作者 / 机构 | Xanh Ho, Anh-Khoa Duong Nguyen, Saku Sugawara, Akiko Aizawa / SOKENDAI、NII、AIST（日本） |
| 发表时间 / 出处 | arXiv:2011.01060v2（2020-11-12）；原稿 2020-11-02；COLING 2020 |
| 论文链接 / 代码 | https://arxiv.org/abs/2011.01060 ／ https://github.com/Alab-NII/2wikimultihop |
| 标签 | NLP / MRC 数据集；模板 + Wikidata 逻辑规则 + Wikipedia 摘要；multi-hop QA、evidence triple、supporting facts |
| **应用裁决** | **E 不采用** |
| 优先级 | P3（备查） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |
## 1. 一句话定位

- **论文主张**：用 Wikipedia 摘要（非结构化）+ Wikidata 语句（结构化）交叉生成 192,606 条多跳问答样本，每题附「证据三元组集合」以完整解释从问题到答案的推理路径，并证明该数据集对多跳模型更难、且确实要求多跳推理。
- **为什么不适用**：这是**纯 NLP 问答基准的构造论文**，输出物是「问题—上下文—答案—证据」四元组数据集与一个 Transformer 基线；不涉及任何**生存控制环、自主性、自修改或演化机制**，与 C1–C10 无回溯路径（连反面教材都算不上），故按 §7 短卡处理。
## 2. 问题 — 机制 — 证据
### 2.1 论文要解决的问题
- 问题本身：既有 multi-hop QA 数据集缺乏对推理过程的完整解释；且被证实大量样本**单跳即可答**（Chen & Durrett 2019；Min et al. 2019），无法检验真正的多跳推理。
- 既有缺陷：ComplexWebQuestions / QAngaroo 无解释信息；HotpotQA 的 sentence-level SFs 只是**二分类**、无法评估推理技能；R4C 仅 4,588 题、太小无法端到端训练（p.2, p.10）。
### 2.2 核心思想
1. **交叉结构化与非结构化数据**：Wikidata 三元组保证推理链**可验证**，Wikipedia 摘要保证答案可 span 抽取、题目自然。
2. **证据即三元组集合**：`(subject, property, object)` 集合兼作 justification 与 introspective explanation，且可自动校验（p.1, p.3）。
3. **逻辑规则造「自然但必须多跳」的问题**：如 `father(a,b)∧father(b,c)⇒grandfather(a,c)`，逐条用 Wikidata 复核（p.3, App. A.3）。
### 2.3 关键机制 / 算法
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| 模板生成（NER 抽象+人工） | HotpotQA 17,456 题 → 模板集 L | 复用句式、剔除单跳模板 | §3.2(1), p.4 |
| 逻辑规则推理（28 条） | (e,r1,e1),(e1,r2,e2) → (e,r,e2) | 造 inference 题 | §3.2, App. A.3 |
| Algorithm 1 / 2 | 实体+关系 → Q/A/Context/SF/Evidence | comparison 与 bridge 题生成 | App. A.6, p.17 |
| 干扰段检索 | 问题 → bigram tf-idf top-50 → 选 8 段 | 构造 10 段 context | §3.2, p.5 |
| Joint 指标 | P_joint=P_ans·P_sup·P_evi | 三任务联合评估 | 式(1), p.3 |
### 2.4 关键表示与数据结构
- 每样本 = 问题 Q + 上下文 C（10 段拼接，bridge-comparison 为 12 段）+ 答案 A + sentence-level SFs（句索引）+ 证据 E（Wikidata 三元组集合）。
- 四类问题：comparison / inference / compositional / bridge-comparison。
### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| Answer 预测 | HotpotQA(distro) vs 本篇 | F1 58.54 vs 40.95；EM 44.48 vs 34.14 | Table 4, p.7 |
| 单跳 BERT 探针 | HotpotQA vs 本篇 | F1 64.6 vs 55.9（低 8.7） | §5.1, p.7 |
| Baseline 三任务 | dev/test | Answer 36.53/43.93；Evidence 1.07/14.94；Joint 0.35/5.41 | Table 5, p.8 |
| 人类上界 | 100 随机 test 样本 ×3 标注员 | Answer 91.0 EM/91.8 F1；Evidence 64.0/78.8 F1 UB | Table 7, p.9 |
### 2.6 论文自陈局限与边界条件
- Wikipedia 与 Wikidata **语义错配**：随机 100 条训练样本中 8 条错配（§5.4, p.9）。
- Evidence 生成任务得分极低（EM≈1），归因于 Wikidata 名称歧义与任务困难。
- Inference 题仅 7,478 条，因「唯一答案」约束丢弃大量样本（§4, App. A.3）；全部题目由**预定义模板**生成，多样性受限。
## 3. SSEA 立场对齐
### 3.1 C1–C10 映射（短卡主要价值：记录「为什么被排除」）
| 裁判标准 | 判定 | 依据 / 为什么不适用 | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | — | 无控制环、无生存信号，是纯语言问答数据集 | 无（不同问题域） |
| **C2** 自然语言只作观察员接口 | ✗ | 语言（问题/答案/证据）即任务本体，语言是唯一输入输出 | 不适用 |
| **C3** 权重/记忆/技能三分离 | — | 不涉及权重、记忆、技能任何一者的分离 | 无 |
| **C4** 低算力低带宽 | ✗ | 每题喂 10 段 Wikipedia 全文 + Transformer 多跳模型，需求高 | 不适用 |
| **C5** 精准回忆历史 | — | 有支持事实 SFs 定位，但那是**单题内证据句**，非跨经历可检索记忆 | 无 |
| **C6** 可自主修改自身 | — | 模型完全冻结，无自我修改、无提案/验证权 | 无 |
| **C7** 可保存/恢复/变异/继承 | — | 无 GenePackage、无繁衍淘汰 | 无 |
| **C8** 给基因先验，不给知识语料 | ✗ | 论文主张正是「提供大规模知识语料（Wikipedia/Wikidata）」 | 与 SSEA 立场相反 |
| **C9** 不设评分函数，只有淘汰函数 | ✗ | EM/F1/Joint 即外部评分函数，用于给模型打分排序 | 不适用 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | — | 贡献在数据与基准，不改进算子，也不落 L2–L4 | 无 |
### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| L1 算子层 | 复用 HotpotQA bi-attention 多跳基线 | 无（借用现成算子，非本篇贡献） |
| L2 信息流层 / L3 学习层 / L4 演化层 | — | 无 |
### 3.3 模块映射
- — 论文构件（数据集、模板、基线）与 SSEA 现有模块无落点。
### 3.4 债务与验收实验对应
- 可回应的已知债务：**无**。可服务的验收实验：**无**。
## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 无可借鉴资产 | — | 仅作对照 | — | 模板式数据构造、EM/F1 外部评分、依赖大规模知识语料，三点均与 SSEA 硬约束冲突，无可干净拆出的零件 | 高 |
## 5. 冲突、代价与风险

- **与硬约束的冲突**：C2（语言进控制闭环）、C4（高带宽）、C8（给知识语料）、C9（外部评分函数）——四项直接冲突，且非「改造即可用」，是**问题域不同**。
- **隐含假设与失效条件**：把「多跳推理」等同于「在固定段集合上做 span 抽取 + 证据定位」，与 SSEA「快慢环 + 原子升版」的时序自我演化无交集。
- **算力 / 带宽 / 工程代价**：搬运需引入完整 MRC 训练栈与 10 段上下文，代价远高于收益。
- **为什么仍保留在论文池**：作为**「外部评分 / 知识语料注入」路线的典型反例**，可对照说明 SSEA 为何拒绝 EM/F1 式打分与预置知识语料（C8/C9）。
## 6. 组合分析

- **组合方案**：—（不作组合）。
- **可作对照臂**：可作为「QA 式外部评分判据」的**反例**，供实验 2 / 技能固化（0/33 判据形状问题）参照——「答案对得上」不等于「机制跑通」，与债务 25–28「判据形状错」同源。
- **典型角色**：反面参照物（外部评分 + 知识语料路线的边界样本），非可复用组件。
## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（证据性质） |
|---|---|---|
| 项目相关性 | 1 | 与 SSEA 生存控制/演化目标几乎无交集（推断） |
| 立场兼容性 | 1 | C2/C4/C8/C9 四项直接冲突（实测：论文明确用 EM/F1 与大规模语料） |
| 可搬运性 | 1 | 无干净可拆构件（推断） |
| 证据强度 | 4 | 192,606 题数据集 + 人类上界 + 多跳探针，论文内部证据扎实（实测） |
| 组合价值 | 1 | 无组合接口，仅可作反例（推断） |
| 落地成本 | 2 | 反向口径：强行搬运需引入完整 MRC 栈，成本高 |
## 8. 裁决与下一步

- **应用等级**：**E 不采用** —— 理由：问题域为 NLP 问答基准，与 C1–C10 无回溯路径，且 C2/C4/C8/C9 直接冲突。
- **优先级**：P3（备查）。
- **建议动作**：归档为「外部评分 + 知识语料」路线的反例样本，不进入任何组合方案。
- **最小验证实验**：不适用（E 不采用）。
- **若 E 不采用**：原因——① 目标（造 QA 数据集与排行榜）与 SSEA（非语言生存演化架构）问题域不同；② 核心手段（大规模知识语料 + EM/F1 外部评分 + 语言进闭环）恰为 C2/C4/C8/C9 所禁；③ 无可拆出的工程零件，保留仅作立场对照。
## 9. 待确认问题

- 需作者 / 团队决策：—（无需 SSEA 团队动作）。需补查文献：—。需核对公式：Joint 指标式(1) 已核对（p.3）。
## 附：关键摘录与出处

| 摘录 | 页码 |
|---|---|
| "we introduce the evidence information containing a reasoning path for multi-hop questions" | p.1 |
| "sentence-level supporting facts (SFs) ... a binary classification task that is incapable of evaluating the reasoning and inference skills" | p.1 |
| "The result of our dataset is lower than the result of HotpotQA by 8.7 F1" | p.2, p.7 |
| "We obtained eight out of 100 samples that have a mismatch between Wikipedia article and Wikidata triple." | p.9 |
| "Joint F1 = 2 P_joint R_joint / (P_joint + R_joint)，P_joint = P_ans P_sup P_evi" | 式(1), p.3 |
