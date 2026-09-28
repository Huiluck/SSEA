# 论文分析卡片 · On the Measure of Intelligence

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2019-11-05 On the Measure of Intelligence.pdf` |
| 标题 | **On the Measure of Intelligence** |
| 作者 / 机构 | François Chollet（Google, Inc.）；致谢 José Hernández-Orallo、Julian Togelius、Christian Szegedy、Martin Wicke（p1 脚注） |
| 发表时间 / 出处 | 2019-11-05（arXiv:1911.01547v2 [cs.AI]，2019-11-25）；64 页 |
| 论文链接 | arXiv:1911.01547 |
| 代码链接 | ARC 数据集 `github.com/fchollet/ARC`（p46） |
| 标签 | 智能的**形式化定义** · Algorithmic Information Theory · **skill-acquisition efficiency** · Generalization Difficulty · priors/experience 三要素 · developer-aware generalization · 泛化谱（robustness/flexibility/generality）· Core Knowledge priors · ARC 基准 · **理论论文** |
| **应用裁决** | **C 思想启发**（采用其**理论透镜**：智能=技能获得效率、Generalization Difficulty、priors/experience 分解、developer-aware generalization——为 SSEA 的 **C9** 与「**判据健康度**」提供理论根据；**不采用**其 `Scoring` 函数与 ARC 的「解出比例」评分口径——那是 C9 的反面标本） |
| 优先级 | **P1**（直击 C9 的理论根基与当前最紧的「判据饱和 / 指标全绿但行为没变」；但它是**理论论文**、无代码零件，落地在「判据设计原则」层） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：仅测「任务上的技能（skill）」不足以度量智能，因为**技能被先验知识与经验强烈调制**——无限的 priors 或无限的训练数据让实验者能「**买**」出任意技能水平，从而**掩盖系统自身的泛化能力**（摘要 p1、II.1.1 p18–20）；作者用 **Algorithmic Information Theory** 给出新形式定义——**智能 = 在一组任务上的 skill-acquisition efficiency（技能获得效率）**，随 **priors、experience、generalization difficulty** 三者分解（II.2.1 p27–40），并据此提出理想基准的判据（II.3.2 p45），最后给出具体基准 **ARC**（III p46–55）。
- **对 SSEA 的意义**：它是 SSEA **C9（不设外部评分函数，只有淘汰函数）** 的**理论根**——「任何既定目标都会被捷径满足」「技能可被 priors/数据买出来」正是「**外部评分会被刷分**」的形式化陈述；其 **Generalization Difficulty** 与「**skill ≠ intelligence**」为 SSEA 的「**判据健康度**」提供了可引用的理论判据（判据是否在测泛化、还是在测记忆），并正面支撑 **C8（给基因先验，不给知识语料）**。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（摘要 p1、I.1 p3）：要让 AI 走向更通用/更像人的智能，必须有一个**恰当的反馈信号**——能定义并评估智能、支持系统间与人机比较。但当代 AI 仍以「在具体任务上比技能」来标定智能（棋类、游戏）。
- **它指出的既有方案缺陷**（II.1.1 p18–20）：
  1. **技能 ≠ 智能**：技能是「智能过程」的**产物**，不是过程本身；靠硬编码先验或堆训练数据即可「买」出高技能而**不产生任何泛化能力**（p19–20）。
  2. **目标一旦确定，解就倾向走捷径**：「from the moment the objective is settled, the process of developing a solution will be prone to taking all shortcuts available to satisfy the objective of choice」（p18）——这正是「刷分」的机理。
  3. **两类刷分通道**：① 无限先验（如 DeepBlue/if-else 聊天机器人）；② 无限训练数据（如 locality-sensitive hashtable 可「解」任何能无限生成数据的任务）（p19–20）。
  4. **忽略泛化谱与先验**：现有评测未控制 priors、experience 与 generalization difficulty，无法区分「局部泛化」与「极端泛化」（I.3.2 p9–11）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **智能是「转换率」而非「分数」**：智能 = 学习系统**把 priors 与 experience 转化为新技能**的效率；技能只是该过程的输出产物（p27、p40、p57）。形式化上，每任务的贡献是 `Expectation[ skill·generalization / (priors + experience) ]`（p39）。
2. **三要素必须被控制**：任何有意义的智能度量必须同时控制 **priors（起点先验）、experience（课程经验）、generalization difficulty（任务含多少不确定性）**（p57）。忽略任何一项，技能分数就会说谎。
3. **区分 system-centric 与 developer-aware 泛化**（I.3.2 p10）：前者是系统没见过的情形；后者是**连系统开发者也没见过**的情形。只有 developer-aware 泛化才排除「开发者把答案硬编码进系统」的作弊——这是**判据可信度的关键分界**。
4. **泛化谱**（I.3.2 p10–11）：无泛化 → 局部泛化/robustness（已知未知）→ 广义泛化/flexibility（未知未知，跨相关任务）→ 极端泛化/generality（未知未知，跨未知领域；人类）→ universality（作者明确**拒绝**作为目标，II.1.2 p21–24）。
5. **先验应为结构性 Core Knowledge**：人脑先验分三类（低级感觉运动 / 元学习 / 高级知识）；其中**知识先验**应被度量所控制，且测试应只假设**与人类先天 Core Knowledge 接近的先验**，不含后天习得知识（语言、符号、概念）（II.1.3 p24–27、III.1.2 p47–50）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处（节/式/页） |
|---|---|---|---|
| **Task 形式化** `T=(TaskState, SituationGen, Scoring, TaskUpdate)` | 状态 → 情境/分数+反馈/新状态 | 把「任务」拆成生成/评分/更新三件 | II.2.1 p28–29 |
| **IS 形式化** `IS=(ISState, SkillProgramGen, ISUpdate)` | 状态 → 技能程序 / 新状态 | 把「智能系统（过程）」与「技能程序（产物）」分离 | II.2.1 p29–30 |
| **SkillProgram（技能程序）** | (Situation, SPState) → (Response, SPState) | 「冻结的任务专属能力快照」——智能过程的**产物** | II.2.1 p29 |
| **Skill / Optimal skill / 充分技能阈值 θ_T** | 评估期分数和 → 标量 | 把「技能」定义为评估结果的概率平均 | II.2.1 p32 |
| **Generalization Difficulty `GD^θ_{T,C}=H(Sol^θ_T|TrainSol^opt_{T,C})/H(Sol^θ_T)`** | 任务+课程+阈值 → [0,1] | 量化「评估期行为要多偏离训练期最优解」 | II.2.1 p35（式） |
| **Developer-aware GD `GD^θ_{IS,T,C}=H(Sol^θ_T|TrainSol^opt_{T,C},IS_{t=0})/H(Sol^θ_T)`** | 任务+系统+课程 → [0,1] | 排除开发者注入的先验（作弊）后的泛化难度 | II.2.1 p36（式） |
| **Priors `P^θ_{IS,T}=[H(Sol^θ_T)−H(Sol^θ_T|IS_{t=0})]/H(Sol^θ_T)`** | 系统+任务 → [0,1] | 「系统起点离解有多近」的信息量 | II.2.1 p37（式） |
| **Experience `E^θ_{IS,T,C}=(1/H(Sol^θ_T))Σ_t[H(Sol^θ_T|IS_t)−H(Sol^θ_T|IS_t,data_t)]`** | 课程 → 累积信息量 | 只计**相关且新颖**的信息；不惩罚噪声/重复课程 | II.2.1 p37–38（式） |
| **Intelligence `I^θT_{IS,scope}=Avg_T[ω·θ·Σ_C[P_C·GD/(P+E)]]`** | 系统+scope → 标量 | 智能=技能获得效率（信息效率版） | II.2.1 p39（式） |
| **其它效率项**（算力/时间/能量/**风险**） | — | 可作正则项加入；**risk efficiency** 与生物/演化高度相关 | II.2.2 p41–42 |
| **理想基准判据清单**（有效性/可靠性/测 broad+developer-aware 泛化/控制经验/显式列先验/人机公平） | 基准设计 → 合规/不合规 | 可直接作**判据设计检查表** | II.3.2 p45 |
| **ARC**（400 训练 / 600 评估：400 公开 + 200 私有） | 网格任务 → 解出比例 | 论文的具体实例化（非算法零件） | III.1.1 p46–47 |

### 2.4 关键表示与数据结构
- **一切对象都是二元串**：状态、程序、情境、响应均为 binary string；分数/潜力为标量（II.2.1 p34）。程序可表示为串，故可用 Algorithmic Complexity 讨论其信息量。
- **训练/评估两阶段**：训练期 IS 反复生成技能程序并据反馈更新 `ISUpdate`；评估期**只有固定技能程序**、**不再含 IS**（II.2.1 p30–32）。
- **Curriculum（课程）**：任务与 IS 之间交互序列 `(situation, response, feedback)`；由随机分量参数化，可建模教学与主动学习（p33）。**Optimal curriculum / sufficient curriculum** 分别导向最高技能/充分技能（p33）。
- **ARC 任务**：网格（10 个符号；1×1–30×30，中位 9×10）；平均 3.3 个示范样例；二元成败；每个测试样例允许 3 次尝试；系统分数 = **评估集解出任务比例**（III.1.1 p46–47）。

### 2.5 实验证据

> **证据性质说明**：本篇是**理论/立场论文**，**无实验章节、无对照实验、无统计口径**。其「证据」是**形式推导的自洽性** + **ARC 作为存在性实例**。以下逐条标注证据类型。

| 主张 | 证据形态 | 关键内容 | 出处 |
|---|---|---|---|
| 智能=技能获得效率 | **形式推导**（非实测） | 给出 `I=Avg_T[ωθ·Σ_C P_C·GD/(P+E)]` 及分解 | II.2.1 p39 |
| GD=0 ⇒ 任务不含泛化 | **形式推导 + 玩具例** | 「若训练最优程序也达充分技能，则 GD=0」；举例：3 个一维点，最短训练解 `x>0`/`ceil(x)` 在评估点失败，而最近邻存全部数据才泛化 | II.2.1 p35–36 |
| ARC 人类可解 | **弱实测（存在性）** | 每个任务被 3 名高智商人类（互不通信）中至少一人解出；「typical human 可解多数任务、无需训练」（**未给大样本人类统计**） | III.1.4 p51–52 |
| ARC 当前 ML 无法有意义逼近 | **断言（作者判断）** | 「to the best of our knowledge, ARC does not appear to be approachable by any existing ML technique (including Deep Learning)」（**无基准数字、无跑分表**） | III.1.4 p52 |
| 泛化谱与 g 因子对应 | **类比论证**（引 CHC/g-VPR） | 极端泛化↔g；广义泛化↔broad ability；局部泛化↔task-specific skill | I.3.2 p12（Fig.1） |

> **口径警示**：本篇**无任何「实测涨点」数字**。任何引用其「ARC 难解」的说法都只是作者 2019 年的**判断**，不是实测（III.1.4 p52 原文即「we posit」/「highly speculative」）。

### 2.6 论文自陈局限与边界条件
- **自陈（ARC 的弱点，III.2 p53–54）**：
  1. **泛化未被量化**：只声明测「广义泛化」，但**未给出评估集相对测试集的泛化难度量化**（计划用人类表现估计）；
  2. **测试效度未建立**（validity 未证）；
  3. **数据集规模/多样性有限**（仅 1000 任务，可能有概念重叠 → 可能被捷径攻破）；
  4. **评测格式过度闭式/二值**（0/1 缺粒度；建议改为可交互的示例生成器，以「需要多少反馈才学会」为分数）；
  5. **Core Knowledge 先验本身未被充分理解**，ARC 是否正确捕获它们**不明**。
- **作者自陈框架定位（p57）**：其定义/形式/判据「**were developed to be actionable, explanatory, and quantifiable, rather than being descriptive, exhaustive, or consensual**」，只求作**指导研究的 objective function**，**不声称是唯一真定义**。
- **明确不适用**：拒绝 universal intelligence（Universal Psychometrics / Legg-Hutter）为绝对标尺（II.1.2 p24）；明确**人类中心**是必要参考系。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 形式化是**架构中立**的「情境→响应→反馈→更新」控制环，可建模 FSL/RL/监督（II.2.1 p28）；把「IS（过程）」与「SkillProgram（冻结产物）」分离，与 SSEA「快环只读不可变快照 / 慢环发布新版本」**同构**（p29–31）。但无生存组织原则 | 借「过程/产物分离」与「快照-更新」形状，套到 FSL/SEL 双环；淘汰压力换为生存事实 |
| **C2** 自然语言只作观察员接口 | ✓ | ARC 刻意**不含语言**（III.1.3 p50–51：「ARC does not involve language, pictures of real-world objects, or real-world common sense」） | —（正面示范：非语言结构化任务可测抽象能力） |
| **C3** 权重/记忆/技能三分离 | ◐ | 明确分离 **SkillProgram（技能产物）** 与 **IS（含算法+状态）**（p29–31）——为「技能层」提供强形状；但记忆仅作为 `SPState`（工作记忆），无三分离语义 | 技能产物↔ΔS；IS 的 `ISState` 拆为 Δθ/ΔM；补记忆层的独立生命周期 |
| **C4** 低算力低带宽 | ◐ | 形式化不涉及算力；但 ARC 设计为 **few-shot**（平均 3.3 样例，p46）、且主张「**控制 experience**」（p45）——精神与 C4 一致 | ARC 的 few-shot 设计原则可借；算力预算另议 |
| **C5** 精准回忆历史 | — | 除 `SPState`（技能程序工作记忆）外**无记忆机制**；无检索/写入/遗忘/合并（全文未提及） | 不搬；精准回忆仍走 Memento/FLEX 主干 |
| **C6** 可自主修改自身 | ◐ | IS 有 **`ISUpdate`（自更新函数）**，据反馈改变自身状态（p30）；但**四权不分**（提案=SkillProgramGen、验证/应用未分离） | 借「自更新原语」，但验证权交验证门、应用权交淘汰函数 |
| **C7** 可保存/恢复/变异/继承 | ◐ | 技能程序是「**冻结版本**」（frozen version，p29）——保存/恢复的原型；IS 状态跨训练保留（p30）；但**无 GenePackage、无变异、无继承、无淘汰** | 技能程序冻结↔ΔS 快照；遗传机制另寻（GenePackage） |
| **C8** 给基因先验，不给知识语料 | **✓（强证据）** | 全篇核心：先验应是**结构性 Core Knowledge**（objectness/agentness/numbers/geometry，II.1.3 p24–27）；测试应**只假设先天先验、不含后天习得知识**（p26、III.1.2 p47–50）——正是 C8 | —（直接为「基因只放结构先验」背书） |
| **C9** 不设评分函数，只有淘汰函数 | **✗（作为机制）/ ◐（作为理论根据）** | ① Task 形式化**内置 `Scoring:[Situation,Response,TaskState]→[Score,Feedback]`**，且 `ISUpdate` 消费 `feedback`（p29–31）→ **环内有评分/反馈通道**；② ARC 的度量是「**解出比例**」（p47）→ 外部评分。**但**其批判「目标既定即走捷径」「技能可被先验/数据买出」（p18–20）正是 C9 的**理论根据** | 见 §5.1 三层拆分：**只取其「为何评分会骗人」的理论**，**不取其 Scoring 机制**；SSEA 的评分位置改由环境侧淘汰事实承担 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 无新算子；贡献是**概念/形式层**（智能定义、泛化谱、GD、判据原则） | — |

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无（不涉及具体网络/算子） | 符合借用立场 |
| **L2 信息流层** | **过程/产物分离**（IS vs SkillProgram）+ 情境→响应→反馈→更新环 + 训练/评估两阶段分离 | **高**：为「慢环发布 ΔS 快照、快环只读」提供理论命名；「评估期不含 IS」= 判据只测冻结产物 |
| **L3 学习层** | **skill-acquisition efficiency**、priors/experience 分解、GD——「学习把信息转成技能」的度量 | **高**：为「技能固化」实验提供「技能≠智能、要看获得效率」的判据框架 |
| **L4 演化层** | curriculum 概念、optimal/sufficient curriculum；scope/potential | **中**：课程概念可对接 GenEnv/TTCS 的难度带；无遗传机制 |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **IS / SkillProgram 分离** | 慢环 SEL（IS）× ΔS 技能快照（SkillProgram）；「评估期不含 IS」= 判据只测冻结快照 |
| **Generalization Difficulty（GD）** | **新增：判据健康度判据**——「训练期最优解是否也能通过评估」；若 GD≈0 则判据只测记忆（对标 AutoEnv 差分检查、HarnessEval held-out） |
| **Developer-aware GD** | **新增：验收纪律**——判据任务须**对开发者/慢环未知**（对标 HarnessEval 的搜索/评测分离、禁止预拟合） |
| **Priors / Experience 分解** | **新增：验收记录字段**——每臂须声明「起点先验」与「消耗经验（episode/数据）」；对标 HarnessEval「预算匹配基线」 |
| **「技能可被数据/先验买出」** | **判据诊断**——「指标全绿」可能只是 priors/experience 堆出来的，须先扣掉 priors/experience 再看行为 |
| **理想基准判据清单（II.3.2）** | **现有：七条验收的判据设计检查表**——与 HarnessEval 检查表合并 |
| **Core Knowledge priors** | **GenePackage 结构先验的样板**（C8）；但须是**结构性**而非知识性 |
| **ARC / Scoring 函数** | **仅作对照/反例**——C9 反面标本，不入 SSEA |

### 3.4 债务与验收实验对应
- **可回应的已知债务/缺口**：
  - **C9 的理论根基**：本文给出「为何外部评分会被刷分」的形式化理由（p18–20）——支撑「不设评分函数」不是教条而是**必要**。
  - **判据饱和（危险回避率两臂均 0.9814）**：本文的 **GD=0** 情形给出**理论形式**——「训练最优解也能过评估」即判据不含泛化，与饱和同构。
  - **「指标全绿但行为没变」**：本文的「skill ≠ intelligence / 技能可被买出」给出**理论解释**——分数变了不等于智能（行为泛化）变了。
  - **债务 25（记录数字不复现）**：II.3.2 的 **reliability（可复现）** 判据（p45）为记录纪律提供理论根据。
  - **债务 26/27/28（判据形状错/无消费者通道报成功/技能失效被判成功）**：属「GD≈0 的假判据」——本文给出「该判据是否在测泛化」的理论追问。
  - **技能表示够不够（0/33 之后未答）**：本文的「技能=冻结产物、智能=获得效率」提示——0/33 可能是**产物层**（表示）问题，也可能是**过程层**（效率）问题，须分开。
- **可服务的验收实验**：**全部七条**的判据设计层；不解决 Gene Manager 缺口（实验 4/5 仍卡）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **智能=skill-acquisition efficiency（技能≠智能）** | 思想/定义 | 仅借思想 | C9 理论根据 / 判据设计 | 「指标全绿但行为没变」 | 高（论证严谨，推断其适用性） |
| 2 | **Generalization Difficulty（GD）+ developer-aware GD** | 思想/形式 | 仅借思想（不可计算，降为**定性检查**） | 判据健康度 | 判据饱和 / 判据形状错 | 高（形式自洽；落地为定性追问） |
| 3 | **priors / experience / GD 三要素控制** | 协议/原则 | 改造移植 | 验收实验记录与基线 | 「涨点来自设计还是先验/数据」 | 高 |
| 4 | **「目标既定即走捷径」+ 两类刷分通道** | 思想 | 直接引用 | C9 论证 / 红队清单 | 奖励黑客、刷分 | 高 |
| 5 | **理想基准判据清单（II.3.2，7 条）** | 检查表 | 改造移植 | 七条验收的判据前置 | 判据设计缺陷 | 中高 |
| 6 | **Core Knowledge priors（四系统）** | 思想/结构先验 | 仅借思想 | GenePackage 结构先验 | C8 | 中（先验本身作者自陈未充分理解，p54） |
| 7 | **泛化谱（robustness/flexibility/generality）** | 分类 | 直接引用 | 判据定性分级 | 判据测的是哪一级泛化 | 中 |
| 8 | **过程/产物分离（IS vs SkillProgram）** | 表示 | 改造移植 | 慢环/快环命名 | 技能快照语义 | 中 |
| 9 | **risk efficiency 作为效率项** | 思想 | 仅借思想 | 生存域效率度量 | 生存代价可作正则 | 低（未展开） |

---

## 5. 冲突、代价与风险

### 5.1 与硬约束的冲突（C9 是主战场，须先回答「它的评分是描述性度量还是可刷分奖励」）

**这是本篇裁决的核心问题。必须逐层拆开：**

| 层 | 论文的实际做法 | 是「描述性度量」还是「可被刷分的奖励」？ |
|---|---|---|
| Task 的 `Scoring` 函数（p29） | `Scoring:[Situation,Response,TaskState]→[Score,Feedback]`，是**任务**的组成部分 | **外部评分函数**：它是「任务」给响应打的标量分——**结构上正是 C9 禁止之物** |
| `ISUpdate` 消费 `feedback`（p30） | 训练期 IS 据反馈更新自身状态；简单情形「feedback 即 score」 | **反馈通道**：分数直接进 IS 的更新环 → **奖励塑形风险** |
| ARC 的度量（p47） | 「系统分数 = 评估集**解出任务比例**」 | **外部评分**：一个 0–1 的百分比分 |
| 作者对 `Scoring` 的定位（p30、p40、p57） | 「**We do not attempt to model why the IS should pursue this goal**」；框架是「actionable, explanatory, quantifiable… a useful **objective function to guide research**」 | **描述性/解释性度量**：它是**研究者用来刻画系统**的仪器，**不是**被告知给智能体去最大化的运行时奖励 |

**明确判定**：本篇的 `Scoring` **在结构上是外部评分函数**（若照搬即违反 C9①），**但其**功能定位是**研究者侧的描述性度量/研究目标函数**，而非智能体的运行时奖励——作者明确不建模 IS 为何追求该目标（p30）。因此：

1. **作为「机制」→ 冲突（✗）**：`Scoring`+`feedback` 构成「评分进环」的完整形状；ARC 的「解出比例」是典型外部评分。**SSEA 不得照搬此形状**——这正是 HarnessEval/AutoEnv 卡片已识别的同一坑。
2. **作为「理论」→ 支持（◐→✓）**：本篇给出「**为何评分会骗人**」的形式化理由——① 目标既定即走捷径（p18）；② 技能可被 priors/数据买出（p19–20）；③ 技能 ≠ 智能（p40）。这三条**正是 C9 的正当性根据**，且比 SSEA 自己的表述更早、更形式化。
3. **裁决含义**：正因为它**既提供 C9 的理论根据、又在机制上是 C9 的反面标本**，它**不是 B（无干净零件可拆）**、**不是 D（ARC 非 SSEA 所用基准）**，而是 **C（思想启发）**——取「理论透镜」而弃「Scoring 机制」。

**三步剥离方案（把可用的理论从违规机制里取出来）**：
1. **弃机制**：不采用 `Scoring`/`feedback` 进环的形状；SSEA 的「成败」仍只由**环境侧淘汰事实**（存活/死亡）承担。
2. **留理论**：把「智能=获得效率」「GD」「skill≠intelligence」「两类刷分通道」作为**研究者侧判据设计原则**（无学习、无打分、无排序）。
3. **限用途**：AIT 量（H、GD、P、E）**不可计算**（Kolmogorov 复杂度不可判定），只能降为**定性追问**，**绝不可实现为运行时数值**——否则等价于新建一套外部评分（C9 违规）。

**其余冲突**：
- **C4/C6/C7**：论文不涉及算力预算、四权分离、遗传机制 → 只能借形状，不能借机制。
- **不可计算性（本篇最大落地障碍）**：`H(·)`、`GD`、`P`、`E` 均以 Kolmogorov 复杂度定义，**理论上不可计算**（II.2.1 p34–38）。任何「把 GD 算成数」的尝试都会退化为启发式近似（作者自陈 ARC 的 GD 量化是**未来工作**，p53–54）。

### 5.2 隐含假设与失效条件
- **假设「可定义 scope 与 skill 阈值」**：比较需共享 scope + 固定技能阈值（II.3.1 p43–44）；SSEA 的「生存」scope 与阈值未定义。
- **假设「priors 可显式列举」**：Core Knowledge 清单本身**未被充分理解**（作者自陈 p54）→ 假设不牢。
- **失效条件**：若任务 GD≈0（训练最优解也能过评估），该判据**测不到泛化**——此时无论分数多高都无意义（p35）。
- **人类中心参考系的边界**：作者明确**拒绝** universality 为绝对目标（p24）；SSEA 的「生存」是否属「人类相关 scope」需自行判定。

### 5.3 算力 / 带宽 / 工程代价
- **理论搬运成本极低**：只借「判据设计原则 + 追问清单」，无模型、无训练、无带宽。
- **真实代价在「把 AIT 落地」**：若要量化 GD/P/E，须自造可计算近似（启发式），**成本高且易引入新的外部评分**——建议**不做**，只保留定性检查。
- **ARC 若被误用**：把 ARC 当 SSEA 的验收基准会引入**一整套外部评分**（解出比例），直接违反 C9。

### 5.4 搬运后的可能退化模式（若失败，会以什么形式失败）
1. **「把理论当零件」**：试图实现 `I=Avg[ωθ·Σ_C P_C·GD/(P+E)]` → 得到一个**不可计算/无意义**的数值 → 退化为一套**新的外部评分**（C9 违规）。
2. **「把 GD 当分数」**：用启发式近似把 GD 算成 0–1 分并用于排序/选优 → 又变成奖励函数。
3. **「把 skill≠intelligence 当免检」**：只引用其名言而不改判据形状 → 「指标全绿但行为没变」**依旧存在**。
4. **「把 ARC 当基准」**：引入「解出比例」评分 → C9 违规，且与 SSEA 非语言生存域不匹配。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **理论根据（对 C9）** | **Misevolve** | Misevolve 给「**该防什么风险**」（记忆奖励黑客、工具/工作流级联）；本篇给「**为什么外部评分必然被刷分**」的**理论根**（目标既定即走捷径、技能可被 priors/数据买出）。二者合为「C9 的实证 + 理论」两半：Misevolve 是现象，本篇是机理 |
| **理论根据（对判据健康度）** | **HarnessEval** | HarnessEval 给「**怎么测才公平**」（预算匹配基线 + 搜索/评测分离 + pass@1/pass@k + 分母口径）；本篇给「**为什么必须控制 priors/experience/GD**」的**理论根据**——「涨点来自设计还是先验/数据」正是 HarnessEval 的「搜索税」，而本篇在 2019 年已形式化。**本篇 = HarnessEval 检查表的理论前言** |
| **理论根据（对判据饱和）** | **AutoEnv** | AutoEnv 给「判据是否饱和」的**操作检查**（差分可靠性：弱≥强 ⇒ 不可信；Skin-Inverse 控制消融）；本篇给「**饱和的判据在理论上是什么**」——**GD≈0**：训练最优解也能过评估，则判据不含泛化。二者合为「饱和的**理论定义 + 操作检测**」 |
| **理论根据（对难度带）** | **GenEnv** | GenEnv 给 α 难度带（把成功率钉在 0.5）与 Theorem 1 样本量界；本篇给「**为什么要把任务放在有泛化难度的位置**」——**GD>0 才含不确定性**，GD≈0 的任务无论分数多高都测不到能力。GenEnv 的 α 带 = 让判据落在「GD 充分」区的**工程手段** |
| **理论根据（对无标签前沿带）** | **TTCS** | TTCS 用**自洽性 s≈0.5** 作无标签难度代理；本篇提醒「**度量必须涉及学习与不确定性**」「**intelligence is not curve-fitting**」（p40）——s≈0.5 只说明模型「拿不准」，**不保证题目含真实泛化难度**（可能只是环境噪声），须补「环境侧事实」锚点。本篇 = TTCS 前沿带的**理论边界说明** |
| **前置/互补（记忆侧）** | **Memento / FLEX / MemRL** | 本篇无记忆机制（C5 —）；记忆组织/写入/检索仍走记忆族主干 |
| **前置/互补（技能侧）** | **PSN / Voyager / SkillWeaver** | 本篇「技能程序=冻结产物」为 ΔS 快照提供语义；技能固化/成熟度门仍走 PSN |
| **互补（廉价验证场）** | **Dream-RSI** | 本篇的「评估期不含 IS、只测冻结技能程序」可在 Dream-RSI 重放中先跑，避免污染 |
| **互补（训练诊断）** | **RAGEN** | RAGEN 的 Echo Trap 诊断「尺子在说谎」（方差先于均值）与本篇「分数会说谎」同族 |
| **风险对照** | **Gödel Agent** | 自指自改进的形式化北极星；本篇的「ISUpdate 自更新」是其最简原型，但须配 C9 约束 |
| **替代/上位** | Legg-Hutter Universal Intelligence / Universal Psychometrics | 本篇明确**取代**其「绝对标尺」路线，主张人类中心 scope（p24） |
| **反例/警示** | **一切「以分数证明智能」的自评报告**（含 SSEA 自身历史） | 本篇是「**别把技能当智能**」的理论反例集 |

### 6.2 推荐组合方案
- **组合**：本篇 **× HarnessEval × AutoEnv × GenEnv × TTCS**（+ 执行侧 PSN / Dream-RSI；风险侧 Misevolve）
- **接口形态**：
  - **本篇** 提供**理论判据**：「该判据在测泛化还是记忆？」（GD 定性检查）+「该涨点来自设计还是 priors/数据？」（三要素控制）；
  - **HarnessEval** 提供**公平性协议**（预算匹配基线 + 搜索/评测分离 + pass@1/pass@k + 分母口径）；
  - **AutoEnv** 提供**饱和检测**（差分可靠性 + Skin-Inverse）；
  - **GenEnv / TTCS** 提供**难度定位**（α 带 / s≈0.5 前沿带 + 样本量界）；
  - **Misevolve** 提供**威胁清单**（该防哪些风险）；
  - **PSN / Dream-RSI** 提供门控/回滚执行点与廉价重放场。
  六者组成 **SSEA 验收的「判据健康度套件」**：理论追问（本篇）→ 威胁面（Misevolve）→ 判据合法/有区分度/敏感（AutoEnv）→ 公平归因（HarnessEval）→ 难度定位（GenEnv/TTCS）→ 淘汰执行（PSN/Dream-RSI）。
- **组合后新增能力**：SSEA 的七条验收在**开跑前**即可被「体检」，且每次「涨点」都被追问「是设计变好，还是 priors/数据买出来的」。
- **新增风险**：六套度量若不加约束会合流成**新的外部评分系统**（C9 违规）；须硬性规定：**本篇的 AIT 量只作定性追问（不实现为数值）、其余五套只输出通过/拒绝/存活（淘汰式），不输出分数、不排序**。

### 6.3 本篇在组合中的典型角色
- **C9 的理论根据 / 判据健康度的「元判据」**——管「**这条判据到底在测什么**：泛化、还是记忆？涨点来自设计、还是先验与数据？」；**不是**评分器、**不是**基准、**不是**算法零件。
- 附带身份：**C9 的「反向标本」**——其 `Scoring` 函数与 ARC 的「解出比例」界定了「**什么叫做把分数接进环**」，供 SSEA 明确拒绝。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 直接给出 C9 的**理论根**与「判据健康度」的理论形式（GD、skill≠intelligence、两类刷分通道）；对应 SSEA 当前最紧的判据饱和/指标全绿（论文为理论推导，非实测；项目现状为实测） |
| 立场兼容性 | **3** | **理论层 ✓**（C9 根据、C8 强支撑、C2 正面示范、过程/产物分离）；**机制层 ✗**（`Scoring`+`feedback` 进环、ARC 解出比例，p29–31/p47）——冲突集中在「评分」一处，可剥离（推断） |
| 可搬运性 | **2** | **AIT 量不可计算**（p34–38），无法作为数值零件；只能搬「定性追问 + 判据设计原则」（推断）；无代码可复用 |
| 证据强度 | **3** | **理论论文**：形式推导自洽、论证充分、引用扎实；ARC 为存在性实例。**扣分**：无实验、无对照、无统计口径；作者自陈 ARC 的 validity 未建立、GD 未量化（p53–54），「ML 无法逼近 ARC」只是判断（p52） |
| 组合价值 | **4** | 与 HarnessEval / AutoEnv / GenEnv / TTCS / Misevolve 五篇**天然咬合**，作为它们共同缺的「理论前言」（推断为主） |
| 落地成本 | **4** | 反向口径。只借「原则 + 追问」成本极低；**但若试图量化 GD/P/E 则成本高且危险**（易造新外部评分） |

---

## 8. 裁决与下一步

- **应用等级：C 思想启发** —— 理由：本篇是**理论论文**，其价值不在可插拔的算法零件（AIT 量不可计算），而在**为 SSEA 的 C9 与「判据健康度」提供理论根据**：① 「目标既定即走捷径」+「技能可被 priors/数据买出」是 C9 的形式化正当性；② 「skill ≠ intelligence」解释「指标全绿但行为没变」；③ **Generalization Difficulty** 为「判据是否在测泛化」给出理论判据；④ 强支撑 C8。其 `Scoring` 函数与 ARC 解出比例是 **C9 的反面标本**（**不采用**）。因无干净零件可拆 → **非 B**；ARC 非 SSEA 所用基准 → **非 D**。
- **优先级：P1** —— C9 与判据健康度是当前最高优先级的阻塞项；本篇给的是**理论根据**（不是又一个待建系统），可与 HarnessEval（P0）、AutoEnv（P1）、GenEnv（P1）、TTCS（P1）的检查表**合并为同一份判据设计文档**。
- **建议动作**（具体到原型 / issue / 实验）：
  1. 在 `sse_protocols` 的**判据设计章节**写入本篇的三条**元判据追问**：(i) 该判据是否只测记忆（GD≈0）？(ii) 该涨点扣掉 priors/experience 后还在吗？(iii) 该判据的任务对开发者/慢环是否未知（developer-aware）？
  2. 把 **GD 定性检查**挂到实验 2（危险回避率饱和）与实验 3（技能固化 0/33）：先问「训练期最优解是否也能过该判据」，再判「能力 vs 判据」。
  3. 把「**技能 ≠ 智能**」写进验收记录：任何「技能固化成功」须同时报**获得效率**（多少经验/多少 episode 换来的），而非只报最终技能分。
  4. 明确**禁止**：不实现 `I` 公式、不把 GD/P/E 算成数值、不引入 ARC 评分口径（C9）。
  5. 建立 issue：`C9 理论根据与判据元判据（MeasureOfIntelligence）`，与 `判据健康度检查表（HarnessEval）`、`判据健康度检查（AutoEnv）` **合并为同一份文档**。
- **最小验证实验（判据的 GD 定性检查，服务实验 2/3）**：
  - **双臂 / 消融设置**：取「危险回避率两臂均 0.9814」。**臂 A**＝现判据；**臂 B**＝现判据 + 本篇元判据检查——(i) **GD 检查**：构造「训练期最优行为」（如把危险区完全记入记忆/硬编码避让），看它是否**也通过评估判据**；若通过 ⇒ GD≈0，判据只测记忆；(ii) **三要素检查**：显式记录两臂各自的 priors（起点结构）与 experience（episode 数），要求**等先验、等经验**后再比行为差；(iii) **developer-aware 检查**：判据任务是否对慢环/开发者未知。
  - **判据（分档，先看分母）**：① 机制计数（分母：多少 seed / 多少 episode / 多少 held-out 条件）→ ② **GD 判定**（「训练最优解」是否也过判据）→ ③ 行为差（等先验等经验后两臂之差，要求跨 seed 可重现）→ ④ 淘汰结果（该判据是否被判 GD≈0 并弃用/改造）。
  - **预期与证伪条件**：
    - **预期**：若「训练期最优行为」也通过判据（GD≈0）⇒ 判据**只测记忆、不含泛化**，0.9814 与 0/33 同源，应弃用或改造（与 AutoEnv 差分检查、HarnessEval held-out 结论互证）。
    - **证伪条件**：若「训练期最优行为」**不能**通过评估判据（GD>0），且等先验等经验后两臂行为差显著、跨 seed 可重现 ⇒ 说明该判据**真在测泛化**，0.9814 反映真实能力，应保留判据并另找饱和成因。
- 若 **E 不采用**：不适用（裁决为 C）。但需明确：**若团队把本篇当「零件库」而非「理论透镜」，试图实现其 AIT 公式或引入 ARC 评分，则本篇退化为 D 基准对照（甚至 C9 违规源）**——其全部价值都建立在「只取理论、不取评分机制」这一约束上。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **C9 边界（关键）**：把本篇的 `Scoring` 定位为「**研究者侧描述性度量**」（非运行时奖励），是否足以判定其理论可用而机制不可用？建议口径：**理论层（判据设计追问）合规；机制层（Scoring/feedback 进环、ARC 解出比例）违规**。需团队书面确认——此口径同时适用于 HarnessEval/AutoEnv 的「外部评分」判定。
  2. **GD 的 SSEA 操作化**：「训练期最优解是否也通过评估判据」在生存域如何构造？候选：把「记忆/硬编码避让」当作训练期最优行为，看它是否也满足存活/回避判据。须确定其可操作性。
  3. **priors/experience 的 SSEA 口径**：SSEA 的「起点先验」（基因）与「经验」（episode/睡眠期）如何度量与配平，才能满足「等先验、等经验后比行为」？
- **需补查的文献或资料**：
  4. 本篇是 ARC 的**理论奠基**；若后续评估 ARC 相关方法（如程序合成 solver、DreamCoder 类），应先读本篇以对齐 GD/priors 概念。papers 目录中 ARC 相关论文（若有）须按同一纪律补卡。
  5. 作者引用并明确**反对**的 **Legg-Hutter Universal Intelligence [54]**、**Universal Psychometrics [39]**、**Hernández-Orallo 的 C-Test [40]**——若项目要写「智能度量」专题，应补查以完成「度量族」图谱。
  6. 项目 `docs/06` 中债务 25–28 的原文定义，以精确对齐「判据形状/记录不复现」措辞。
- **需人工核对的公式 / 实现**：
  7. **AIT 量的不可计算性**：`H(·)`、`GD`、`P`、`E` 均以 Kolmogorov 复杂度定义（p34–38），**不可判定**——须确认 SSEA 侧**只作定性使用**，不得实现为数值（否则造新外部评分）。
  8. **GD 的「反直觉」点**：作者强调「Occam 剃刀会误导——最简单的训练解未必泛化」（p35）——须确认 SSEA 的判据设计是否也踩此坑（把「最简通过」当成「泛化好」）。
  9. ARC 的评分口径（解出比例、3 次尝试、二元成败，p47）**不采用**；若团队曾计划以 ARC 作对照，须核对是否与 C9 冲突。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “skill is heavily modulated by prior knowledge and experience: unlimited priors or unlimited training data allow experimenters to ‘buy’ arbitrary levels of skills for a system, in a way that masks the system’s own generalization power.” | 摘要 p1 |
| “we articulate a new formal definition of intelligence based on Algorithmic Information Theory, describing intelligence as skill-acquisition efficiency and highlighting the concepts of scope, generalization difficulty, priors, and experience.” | 摘要 p1 |
| “from the moment the objective is settled, the process of developing a solution will be prone to taking all shortcuts available to satisfy the objective of choice.” | II.1.1 p18 |
| “Hard-coding prior knowledge into an AI is not the only way to artificially ‘buy’ performance … There is another way: adding more training data.” | II.1.1 p19 |
| “The intelligence of a system is a measure of its skill-acquisition efficiency over a scope of tasks, with respect to priors, experience, and generalization difficulty.” | II.2.1 p27 |
| Task 形式化：`T = (TaskState, SituationGen, Scoring, TaskUpdate)`；`Scoring : [Situation,Response,TaskState] → [Score,Feedback]` | II.2.1 p28–29 |
| IS 形式化：`IS = (ISState, SkillProgramGen, ISUpdate)`；“a skill program represents a frozen version of the system’s task-specific capabilities” | II.2.1 p29 |
| “We do not attempt to model why the IS should pursue this goal.”（IS 的目标不被建模 → 评分是研究者侧度量） | II.2.1 p30 |
| `GD^θ_{T,C} = H(Sol^θ_T|TrainSol^opt_{T,C}) / H(Sol^θ_T)`；“If the shortest skill program that performs optimally during training also happens to perform at a sufficient skill level during evaluation, the task has **zero generalization difficulty**.” | II.2.1 p35 |
| `GD^θ_{IS,T,C} = H(Sol^θ_T|TrainSol^opt_{T,C},IS_{t=0}) / H(Sol^θ_T)`（developer-aware GD） | II.2.1 p36 |
| `P^θ_{IS,T} = [H(Sol^θ_T) − H(Sol^θ_T|IS_{t=0})] / H(Sol^θ_T)`（priors） | II.2.1 p37 |
| `E^θ_{IS,T,C} = (1/H(Sol^θ_T)) Σ_t [H(Sol^θ_T|IS_t) − H(Sol^θ_T|IS_t,data_t)]`（experience，只计相关且新颖信息） | II.2.1 p37–38 |
| `I^θT_{IS,scope} = Avg_{T∈scope}[ ω_{T·θT} Σ_{C∈Cur}[ P_C · GD^θT_{IS,T,C} / (P^θT_{IS,T} + E^θT_{IS,T,C}) ] ]`；示意：`Expectation[ skill·generalization / (priors+experience) ]` | II.2.1 p39 |
| “intelligence is the rate at which a learner turns its experience and priors into new skills at valuable tasks that involve uncertainty and adaptation.” | II.2.1 p40 |
| “Skill is not possessed by an intelligent system, it is a property of the output artifact … High skill is not high intelligence: these are different concepts altogether.” | II.2.1 p40 |
| “Intelligence is not curve-fitting.”；“An intelligent system must generate behavioral programs that account for future uncertainty.” | II.2.1 p40 |
| 泛化谱：absence / local generalization（robustness）/ broad generalization（flexibility）/ extreme generalization / universality；system-centric vs developer-aware generalization | I.3.2 p10–11 |
| 其它效率项：computation / time / energy / **risk** efficiency（可作正则项） | II.2.2 p41–42 |
| 理想基准判据：validity、reliability、测 broad+developer-aware 泛化、**控制 experience（不能靠无限数据「买」性能；应是「无法预先练习的游戏」）**、显式列 priors、人机公平 | II.3.2 p45 |
| ARC：400 训练 / 600 评估（400 公开 + 200 私有）；网格 1×1–30×30、10 符号；平均 3.3 示范样例；3 次尝试；**分数 = 解出任务比例** | III.1.1 p46–47 |
| “ARC does not involve language, pictures of real-world objects, or real-world common sense.”（C2 正面示范） | III.1.3 p50–51 |
| ARC 自陈弱点：泛化未量化、validity 未建立、规模/多样性有限、格式过度二值闭式、Core Knowledge 先验未被充分理解 | III.2 p53–54 |
| “which do not capture all facets of intelligence, were developed to be actionable, explanatory, and quantifiable, rather than being descriptive, exhaustive, or consensual … they are meant to serve as a useful objective function to guide research”（框架=研究者侧目标函数，非运行时奖励） | Taking stock p57 |
| “Intelligence is the efficiency with which a learning system turns experience and priors into skill at previously unknown tasks.”；“a measure of intelligence must account for priors, experience, and generalization difficulty.” | Taking stock p57 |
