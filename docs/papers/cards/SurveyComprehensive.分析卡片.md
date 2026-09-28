# 论文分析卡片 · A Comprehensive Survey of Self-Evolving AI Agents

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-08-10 A Comprehensive Survey of Self-Evolving AI Agents A New Paradigm Bridging.pdf` |
| 标题 | **A Comprehensive Survey of Self-Evolving AI Agents: A New Paradigm Bridging Foundation Models and Lifelong Agentic Systems** |
| 作者 / 机构 | Jinyuan Fang\*、Yanwen Peng\*、Xi Zhang\*、Yingxu Wang、Xinhao Yi、Guibin Zhang、Yi Xu、Bin Wu、Siwei Liu、Zihao Li、Zhaochun Ren、Nikos Aletras、Xi Wang、Han Zhou、Zaiqiao Meng✉（\*等贡献）；University of Glasgow、Sheffield、MBZUAI、NUS、Cambridge、UCL、Aberdeen、Leiden |
| 发表时间 / 出处 | arXiv:2508.07407v2 [cs.AI]，2025-08-31（文件名标注 2025-08-10） |
| 论文链接 | arXiv:2508.07407 |
| 代码链接 | https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents（文献清单仓库，非方法代码） |
| 标签 | 综述 · self-evolving agents · MOP→MOA→MAO→MASE 四阶段谱系 · 四组件反馈环（Inputs/Agent System/Environment/Optimisers）· Three Laws（Endure/Excel/Evolve）· 单/多智能体/领域特定优化分类 |
| **应用裁决** | **D 基准对照**（兼 **C 思想启发**）——见 §8 理由 |
| 优先级 | **P2**（排队；作索引/地图层，最高价值是「指导后续读什么 + 术语统一」） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

> **卡片重心调整说明**：本篇是**综述**而非单篇方法论文。按任务要求，2.3 改为「**分类框架表**」、
> 2.5 改为「**文献覆盖面**」、§4 改为「**术语与地图资产**」、§6 以「**索引层**」角色做组合分析，
> 并**显式对比同目录另一篇综述** `SurveySelfEvolving`（Gao et al., arXiv:2507.21046）。
> 全文 55 页，正文 p1–34，参考文献占 p35–55（约 21 页）。

---

## 1. 一句话定位

- **论文主张**：给出自演化智能体（self-evolving AI agents）的**统一概念框架**——把「智能体演化」
  抽象为一个四组件反馈环（**System Inputs / Agent System / Environment / Optimisers**），据此系统梳理
  面向 foundation model、prompt、memory、tool、workflow、多智能体通信的演化技术，并给出领域特定策略、
  评测/安全/伦理讨论，最后提出 **Three Laws of Self-Evolving AI Agents**（Endure/Excel/Evolve）作为
  安全演化的设计约束（p1、p3、p9–12、p34）。
- **对 SSEA 的意义**：它不提供可搬运的算法零件，而是提供**第二张领域坐标系**——一条
  **MOP→MOA→MAO→MASE** 的范式谱系 + 一个 **Optimiser = (搜索空间 S, 优化算法 H)** 的形式化，
  可用来给 SSEA 的慢环「提案—验证—升版」过程定位，并反向标出 SSEA 仍是空白的分类维度
  （尤其领域特定优化与 Optimiser 形式化）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：绝大多数既有 agent 系统依赖**人工精心配置**，部署后即**静态冻结**，无法适应动态、
  演化的环境；领域缺少一篇把「自演化智能体」作为**独立范式**、并统一其底层反馈环的综述（p1、p3）。
- **它指出的既有方案缺陷**：已有综述把 agent evolution 当作综合 agent taxonomy 的附属章节
  （Luo et al. 2025a；Liu et al. 2025a），或只覆盖语言模型自身的演化（Tao et al. 2024），
  只处理孤立组件，未覆盖**整体 agent 系统**（p3）。
- 由此把问题重新框定为：**LLM-centric 学习如何从静态数据 → 动态环境交互 → 终身自演化**（Fig.1，p2）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **MOP→MOA→MAO→MASE 四阶段范式谱系**：Model Offline Pretraining → Model Online Adaptation →
   Multi-Agent Orchestration → **Multi-Agent Self-Evolving**；交互对象从「静态数据」→「监督信号」→
   「agent 间消息」→「环境信号」，配置从「人工写死」→「数据驱动自演化」（p3、Table 1 p4）。
2. **统一四组件反馈环**：任何自演化过程都可抽象为
   `System Inputs I → Agent System A → Environment（提供反馈）→ Optimiser P → 更新 A → 再部署` 的
   迭代闭环；Optimiser 由**搜索空间 S**与**优化算法 H** 共同定义（Fig.3 p10、p11–12）。
3. **Three Laws（Endure > Excel > Evolve）**：借鉴 Asimov 三定律，给出**层级化**的设计约束——
   I. Endure（安全/稳定）、II. Excel（性能不降）、III. Evolve（自主优化）；后两者不得覆盖前者（p3）。

### 2.3 分类框架表（原「可搬运零件表」改造）

> 综述无可独立搬运的算法零件；下表整理其**分类维度**并标注与 SSEA 的相关度。
> 主分类树见 **Fig.5（p13）**，单智能体概览见 **Fig.4（p12）**，多智能体概览见 **Fig.6（p21）**。

**维度 A — 四组件反馈环（Fig.3，p10）**

| 组件 | 定义 | 关键点 | 与 SSEA 相关度 |
|---|---|---|---|
| **System Inputs I** | 任务设定 | task-level `I={T, D_train}` / instance-level `I={x,y,C}`；无标注时合成 surrogate 数据（p10–11） | 中（≈ 慢环预演输入） |
| **Agent System A** | 被优化对象 | 可分解为 LLM / prompt / memory / tool-use policy；单/多智能体（p11） | **高**（≈ SSEA 的 Δθ/ΔM/ΔS） |
| **Environment** | 运行上下文 + 反馈源 | 反馈由**预定义评测指标**（accuracy/F1/success rate）或 LLM-based evaluator 给出（p11） | 中（但反馈=打分，见 C9） |
| **Optimiser P** | 搜索/更新器 | `A* = arg max_{A∈S} O(A;I)`（式1，p11）；`P=(S, H)`（p12） | **高**（可对齐慢环提案器） |

**维度 B — 单智能体优化四类（Fig.4/Fig.5，p12–21）**

| 类别 | 子类 | 代表方法（原文点名） | 与 SSEA 相关度 |
|---|---|---|---|
| **LLM Behaviour**（权重） | Training-based（SFT/RL/Verifier）、Test-time（Feedback/Search） | STaR、ToRA、Self-Rewarding、DeepSeek-Prover-v1.5、Absolute-Zero、Baldur、ToT | 高（Δθ） |
| **Prompt** | Edit-Based / Generative / Text-Gradient / Evolutionary | GPS、GrIPS、APE、OPRO、MIPRO、StraGo、ProTeGi、TextGrad、EvoPrompt、PromptBreeder | 中（注入面） |
| **Memory** | Short-term / Long-term | COMEDY、ReadAgent、MemoryBank（Ebbinghaus 遗忘曲线）、A-MEM、Mem0、MemGPT、G-Memory、MrSteve、MIRIX、Agent KB | **最高**（ΔM） |
| **Tool** | Training-Based / Inference-Time（Prompt/Reasoning）/ **Tool Creation** | ToolLLM、Confucius、ReTool、ToolRL、EASYTOOL、DRAFT、MCP-Zero、CREATOR、CRAFT、Alita | **高**（ΔS） |

**维度 C — 多智能体优化四维（Fig.6，p21–26）**

| 维度 | 子类 | 代表方法 | 与 SSEA 相关度 |
|---|---|---|---|
| **Prompt** | 多智能体角色/指令搜索 | DSPy、AutoAgents、PromptWizard | 中 |
| **Topology** | **Code-level Workflow** / **Communication Graph** | AutoFlow、AFlow、ScoreFlow、MAS-GPT；GPTSwarm、DynaSwarm、G-Designer、AgentPrune、AGP、MermaidFlow | 中高（≈ L2 信息流） |
| **Unified** | Code-based / Search-based / Learning-based | ADAS、FlowReasoner；EvoAgent、EvoFlow、MASS、DebFlow、MAS-ZERO；MaAS、ANN | 中（MaAS 已有卡片） |
| **LLM Backbone** | Reasoning-oriented / Collaboration-oriented | multi-agent finetuning、Sirius、MALT、MaPoRL、MARFT；COPPER、OPTIMA（2.8× 增益、<10% token，p26） | 中 |

**维度 D — 领域特定优化（p26–30）**

| 领域 | 子类 | 代表方法 | 与 SSEA 相关度 |
|---|---|---|---|
| **Biomedicine** | Medical Diagnosis / Molecular Discovery | MedAgentSim、PathFinder、MDAgents、MDTeamGPT、MMedAgent；CACTUS、LLM-RDF、ChemAgent、OSDA Agent | 低 |
| **Programming** | Code Refinement / Code Debugging | Self-Refine、AgentCoder、OpenHands、VFlow；Self-Debugging、Self-Edit、PyCapsule、RGD | 低 |
| **Financial & Legal** | Financial Decision-Making / Legal Reasoning | FinCon、PEER、FinRobot；LawLuo、AgentCourt、LegalGPT、AgentsCourt | 低（SSEA 生存域不在其清单） |

**维度 E — 评测与安全（p30–32）**

| 类别 | 子类 | 代表 | 与 SSEA 相关度 |
|---|---|---|---|
| Benchmark-based | Tool/API、Web、Multi-Agent、GUI/Multimodal、Domain-Specific | ToolBench、API-Bank、WebArena、GAIA、AgentBench、OSWorld、SWE-bench、AgentClinic | 中（判据形状参考） |
| LLM-based | **LLM-as-a-Judge** / **Agent-as-a-Judge** | pointwise/pairwise；Agent-as-a-Judge（Zhuge et al. 2024b） | 低（评分，与 C9 冲突） |
| Safety/Alignment | 风险基准 + 元评测 | **AgentHarm、RedCode、MobileSafetyBench、MACHIAVELLI、SafeLawBench、R-Judge、AgentEval**（p32） | 中（对照 Misevolve） |

### 2.4 关键表示与数据结构
- **唯一形式化**（p11–12）：优化目标 `A* = arg max_{A∈S} O(A; I)`（式1），其中 `S` = 配置搜索空间、
  `O(A;I) ∈ ℝ` = **把性能映射为标量分数的评测函数**；Optimiser `P = (S, H)`，`H` = 优化算法
  （rule-based / gradient descent / Bayesian / MCTS / RL / evolutionary / learning-based policy）。
- **系统输入表示**：task-level `I={T, D_train}`、instance-level `I={x,y,C}`（p10–11）。
- **Agent System 表示**：可分解为 LLM / prompt / memory / tool-use policy / communication topology（Fig.3 p10）。
- **无 GenePackage / 无继承打包 / 无淘汰函数**：全篇无「可遗传结构包」或「跨代继承」的数据结构。
- 评测侧**无自研指标公式**（与 Gao 综述不同，本篇未给 FGT/BWT/CPG 类公式）。

### 2.5 文献覆盖面（原「实验证据」改造）
- **引用规模**：参考文献占 **p35–55（约 21 页）**，正文引用极密集；`arXiv preprint` 出现约 **160 处**。
  原文**未给出总条数**；本卡按参考文献区「年份标记」计数得 **≈388 条**（`20xx.` 模式，**估算值，
  未逐条清点**，且含少量重复计数风险）→ 量级 **约 380–390 篇**。
- **覆盖子领域**：单智能体（行为/提示/记忆/工具）、多智能体（提示/拓扑/统一/骨干）、领域特定
  （生物医学/编程/金融/法律）、评测（benchmark / LLM-judge / agent-judge）、安全对齐与鲁棒性、
  挑战与未来方向（p12–34）。
- **定量对比表**：**无** apples-to-apples 对比表。全文仅 **Table 1**（MOP/MOA/MAO/MASE 定性对比，p4）
  与 **Fig.1–6**（谱系/框架/分类树，无性能数字）。唯一二手实测数字散见于正文转引，如
  **OPTIMA「2.8× 性能增益、<10% token 成本」**（p26，转引 Chen et al. 2025h），非本篇实验。
- **无对照实验**：作为综述，无自研实验；所有数字均为**转引他人论文**的二手数据。

### 2.6 论文自陈局限与边界条件
- 作者把当前系统定位为「**ambitious vision**」，明确承认**当前系统远未达到安全、鲁棒、开放式
  自演化所需的完整能力**，实际进展仅由「agent evolution and optimisation 技术」近似实现（p3）。
- 明确不适用的情形：正文 §8.1 自陈挑战——(1) 优化管线**重任务指标、轻安全约束**，且动态演化
  使 EU AI Act/GDPR 等**静态假设的法律框架失效**；(2) 奖励建模**不稳定**（数据稀缺、监督噪声、
  反馈不一致）；(3) 优化后的 prompt/topology **跨 backbone 迁移性差**；(4) 多智能体优化的
  **效率—效果权衡未解**；(5) 优化算法**多为纯文本**，缺多模态/空间推理；(6) 工具侧**假设固定工具集**，
  未覆盖工具自主发现/共演化（p32–33）。
- 安全评测自陈：**大多数现有评测是 snapshot-based（单点快照）**，对 MASE 需要**纵向、演化感知**
  的评测，仍是**开放且紧迫的挑战**（p32）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 研究对象是 **self-evolving LLM agents**；驱动力是「环境反馈 = 预定义评测指标（accuracy/F1/success rate）」（p11）。**唯一接近处**：Three Laws 的 **I. Endure（Safety Adaptation）** 是层级化「安全优先」约束（p3），与 SSEA「生存优先」结构同形，但**语义是安全/对齐而非生存**，且是设计原则非控制信号 | 只借其**谱系与分类骨架**，不借控制范式；可把「Three Laws 的层级排序」当作 SSEA「生存 > 其他目标」的**外部同形参照** |
| **C2** 自然语言只作观察员接口 | **◐** | 语言反馈是核心机制：**text gradient**（ProTeGi/TextGrad，p16–17）、LLM-as-judge、自然语言通信；但它**也显式区分** Structured Output（JSON/XML/code）vs Natural Language 通信（p8），并承认 NL 通信有歧义、低效 | 取其**结构化通信**部分（JSON/XML/code、协议），弃其语言反馈闭环；语言仅留日志/解释面 |
| **C3** 权重/记忆/技能三分离 | **✓** | Agent System 显式分解为 LLM / prompt / **memory** / **tool-use policy**（p11）；Fig.5 把 Behaviour（权重）/ Prompt / Memory / Tool 分置为独立优化类（p13） | 四类可对齐 SSEA 的 **Δθ / 注入面 / ΔM / ΔS**；架构/拓扑归入 L2 结构版本 |
| **C4** 低算力低带宽 | **◐** | 有明确的**效率—效果权衡**作为开放问题（p33）；成本感知方法被点名：**OPTIMA 2.8×/<10% token**（p26）、G-Designer（平衡质量与 token 成本，p24）、AgentPrune/AGP（剪枝省 token，p24）、"Efficient Agents"（p31） | 借其**成本—性能权衡**视角做预算度量；但成本是「被优化目标」而非硬约束，SSEA 须把成本**上升为硬约束**（睡眠期预算） |
| **C5** 精准回忆历史 | **✓** | §4.3 记忆优化专章（p17–19）：short/long-term；**memory control**（何时/存什么/更新/丢弃，p18–19）；MemoryBank（Ebbinghaus 遗忘曲线）、A-MEM（自组织链接）、Mem0、MemGPT、MrSteve（what-where-when）、**MIRIX（六类记忆）**、Agent KB（跨 agent 知识迁移） | 直接支撑 SSEA 记忆侧（ΔM）；其「记忆控制机制（what/when/how）」是**记忆二级门选择性**的对照模板 |
| **C6** 可自主修改自身 | **✓** | LLM Behaviour 优化（SFT/RL 改权重，p14–15）；拓扑的 code-level workflow（AFlow/MAS-GPT 改自身代码结构，p23–24）；Self-Edit/Self-Debugging（p28–29）；symbolic learning（p17） | 有「自修改谱系」，但**未拆四权**（提案/边界/验证/应用）；SSEA 的四权拆分是更细的治理，可反向补强其安全章节 |
| **C7** 保存/恢复/变异/继承 | **◐** | 进化/种群方法（EvoPrompt、Promptbreeder、EvoAgent、EvoFlow、MaAS 超网，p17/25）；正文引用 **Darwin Gödel Machine**（Zhang et al. 2025i，p25） | 有「变异+选择」，但**无 GenePackage 式打包**、**无跨代继承的显式机制**（"inherit" 全文 0 次）；SSEA 的「繁衍是挣来的机会」在其框架内无对应 |
| **C8** 给基因先验，不给知识语料 | **✗** | 全篇核心是**知识/经验/技能/工具/工作流的持续积累与迁移**（记忆、工具库、跨 agent 知识库 Agent KB，p19）；无「结构性先验 vs 后天知识」之分，无跨代隔离 | 不借其知识积累立场；SSEA 基因只放本能先验，须明确拒绝其「经验跨代累积」倾向 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（强冲突）** | **式(1) `A* = arg max O(A;I)`** 直接把性能映射为**标量分数**并求极大（p11）；Environment「反馈来自**预定义评测指标**」（p11）；闭环「达到预定义性能阈值或收敛即终止」（p10）；§7.2 LLM-as-a-Judge / Agent-as-a-Judge（p31–32）；§8.1.1「reward modelling」不稳定性（p33）。**全文未区分「外部评分函数」与「环境淘汰函数」** | **本篇对 SSEA 最重要的反面教材**：SSEA 只取其 Optimiser 的**结构（搜索空间×算法）**，拒绝其**打分—求极大**语义；把 `O(A;I)` 改造为「只判合法性的门 + 归环境的淘汰函数」 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 全篇创新集中在 L2（拓扑/通信/信息流）、L3（prompt/memory/tool/权重更新机制）、L4（种群/进化/共演化）；L1 算子（LLM backbone）被当作**可优化对象**而非创新点（§5.2.4 p25–26） | 与其立场一致；可直接用其单/多智能体 + 拓扑/统一分类标注 SSEA 各模块 |

**关于「评分函数 vs 环境淘汰」（对照 C9）**：论文**完全未做此区分**，且立场相反——
它把 `O(A;I)`（评测函数→标量分）与 `arg max` 当作自演化的**定义性内核**（式1，p11），
把 LLM-as-judge / agent-as-judge / reward model 当作**正向工具**（p31–33）。
最接近 C9「内在驱动」的是它讨论的「内部/隐式反馈」思路（§4.2.3 text gradient、§4.1.1 verifier），
但仍以**分数/反馈信号**框定。结论：**它站在 C9 的对立面**，是本卡最主要的对照系。

**关于安全性 / 误演化（对照 Misevolve 卡片）**：**有讨论，但术语与路径均弱于 Gao 综述**。
§7.3（p32）以 **Endure** 为纲，列举风险基准 **AgentHarm / RedCode / MobileSafetyBench /
MACHIAVELLI（reward 优化下的不道德/权力寻求）/ SafeLawBench**，并把 **Agent-as-a-Judge /
AgentEval / R-Judge** 当作「可扩展监督」，指出「accuracy 不足以衡量安全」；结论强调评测须
从 snapshot 转向**纵向、演化感知**。**关键差异**：本篇**全文 0 次出现 "misevolution"**，
也未采用 Misevolve 的 **model/memory/tool/workflow 四路径威胁模型**，只给**原则性清单**（无 Table）。

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；LLM 作 backbone，且 backbone 本身可被优化（§5.2.4） | 符合「借用且可替换」立场 |
| **L2 信息流层** | **四组件反馈环** + **单/多智能体优化分类** + **拓扑即搜索空间**（code-level vs communication-graph） | **高**：给 SSEA 双环/三分离/注入面做第二套坐标 |
| **L3 学习层** | 单智能体四类（行为/提示/记忆/工具）+ 多智能体拓扑/统一优化 | **高**：为 SSEA 自修改/可塑性/技能固化提供术语对照 |
| **L4 演化层** | 进化/种群方法 + 统一优化中的 learning-based（MaAS 超网）+ 引用 DGM | **中**：是 SSEA 缺失的 Gene Manager / 谱系维度的**外部参照**（弱于 Gao，Gao 有专表） |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **四组件反馈环（Inputs/Agent/Environment/Optimiser）** | 与 SSEA 双环做交叉映射：Agent System≈快环只读快照；Optimiser≈慢环 SEL 提案器；Environment 的「预定义指标反馈」须**改造为淘汰函数**（C9） |
| **Optimiser = (S, H)**（p12） | 慢环提案器的形式化外壳：S = 结构版本空间（ΔS/ΔM/ΔR/Δθ），H = 提案搜索算法 |
| **单智能体四类（行为/提示/记忆/工具）** | 对齐 SSEA 的 **Δθ / 注入面 / ΔM / ΔS**；工具三分法（training/inference-time/**tool creation**）作技能表示完备性检查表 |
| **多智能体拓扑即搜索空间**（p23–24） | 对照 SSEA 的 L2 信息流与（未来）多代拓扑；code-level vs communication-graph 两分可作设计选项 |
| **Memory control（what/when/how，p18–19）** | 记忆二级门「开得准不准」选择性缺失的**机制模板**（何时存/更新/丢弃） |
| **效率—效果权衡（p33）+ OPTIMA 成本数字（p26）** | **睡眠期计算预算未定义**债务的度量候选 |
| **评测三层（benchmark / LLM-judge / agent-judge）** | 判据形状参考（但 judge 属打分，须改造为门控口径） |
| **§7.3 安全风险基准清单（p32）** | 安全验收清单（与 Misevolve / Gao Table 12 重叠，本篇更薄） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **记忆二级门常量阈值（半接线）** → 借 §4.3「memory control：what/when/how 存/更新/丢弃」（p18–19）定义**可调**门控维度；
  - **睡眠期计算预算未定义** → 借 §8.1.2「效率—效果权衡」（p33）+ OPTIMA 2.8×/<10% token（p26）定义预算单位；
  - **Gene Manager 缺失 / 实验 4/5** → 借 §5.2 拓扑/统一优化 + DGM 引用（p25）作谱系设计参照（弱于 Gao）；
  - **技能表示够不够（0/33 之后）** → 借 §4.4 工具三分法（training/inference-time/**tool creation**）作表示完备性检查表。
- **可服务的验收实验**：七条中的 **4/5**（Gene Manager 相关）；技能固化实验 3（技能表示完备性检查）。
- **不能回应**：C9 相关（本篇本身违反 C9）、生存信号定义（其框架无生存概念）、`rules` 零消费者、DeathHook（无淘汰概念）。

---

## 4. 术语与地图资产清单（原「可借鉴资产清单」改造）

| # | 资产 | 类型 | 搬运方式 | 落点 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **MOP→MOA→MAO→MASE 四阶段谱系** | 分类框架 | 仅借思想 | 文档定位/术语表 | 一句话说明 SSEA 处于哪一段（≈ MASE 的生存版） | 高 |
| 2 | **四组件反馈环（Inputs/Agent/Environment/Optimiser）** | 分类框架 | 仅借思想 | sse_protocols 术语表 | 给双环/提案器做第二套坐标 | 高 |
| 3 | **Optimiser = (搜索空间 S, 优化算法 H)**；`A*=argmax O(A;I)` | 形式化 | 改造移植 | 慢环提案器形式化 | 慢环「提案搜索」的形式外壳（须去掉 argmax 打分语义） | 高 |
| 4 | **Fig.5 层级分类树**（单/多/领域） | 分类框架 | 仅借思想（作索引层） | 论文阅读规划 | 系统化定位 SSEA 与补读方向 | 高 |
| 5 | **Three Laws（Endure > Excel > Evolve）** | 设计原则 | 仅借思想/对照 | 安全/淘汰优先级声明 | SSEA「生存 > 其他目标」层级排序的外部同形参照 | 中 |
| 6 | **Memory control 维度（what/when/how 存/更新/丢弃）** | 机制分类 | 改造移植 | 记忆二级门 | 记忆门选择性缺失（债务：半接线） | 高 |
| 7 | **工具三分法（training / inference-time / tool creation）** | 分类框架 | 直接引用 | 技能表示检查表 | 技能表示完备性（0/33 之后） | 中 |
| 8 | **评测三层（benchmark / LLM-judge / agent-judge）** | 分类框架 | 仅借思想 | 验收实验设计 | 判据形状（须改造为门控口径） | 中 |
| 9 | **效率—效果权衡 + 成本感知方法清单**（OPTIMA/G-Designer/AgentPrune/AGP） | 度量视角 | 改造移植 | 睡眠期预算定义 | 睡眠期计算预算未定义 | 中 |
| 10 | **标准化协议清单**（A2A / ANP / MCP / Agora，p8） | 协议 | 仅借思想 | 通信/工具接口 | 未来多智能体/工具接口参考 | 中 |
| 11 | **开放问题清单**（p32–33，见 §4.1） | 研究议程 | 仅借思想 | SSEA 定位与选读 | 指出领域空白，反衬 SSEA 差异 | 高 |

### 4.1 论文列出的挑战与未来方向（对 SSEA 定位自身有价值，p32–33）

| # | 挑战/方向（原文，按 Three Laws 分组） | 对 SSEA 的定位价值 |
|---|---|---|
| E1 | **Endure**：安全/法规/对齐——优化管线重指标轻安全，动态演化使静态法规失效（p32–33） | SSEA 四级门 + 淘汰函数即其「evolution-aware audit」的非语言版 |
| E2 | **Endure**：奖励建模与优化不稳定——中间步奖励数据稀缺/噪声/不一致（p33） | 直接印证 C9：SSEA 用淘汰而非奖励，正是规避此不稳定性 |
| X1 | **Excel**：科学/领域场景评测——ground truth 缺失或争议（p33） | SSEA 生存信号（真值由环境给）是其**极端解** |
| X2 | **Excel**：MAS 效率—效果权衡（p33） | **睡眠期预算**债务的对照 |
| X3 | **Excel**：优化后 prompt/topology **跨 backbone 迁移性差**（p33） | 对照 SSEA「基因不跨代」是否牺牲泛化 |
| V1 | **Evolve**：多模态/空间环境优化——算法多为纯文本（p33） | SSEA 若走向具身须回答 |
| V2 | **Evolve**：工具使用与**创建/共演化**——现假设固定工具集（p33） | 技能表示（ΔS）与工具自主发现的对照 |
| F1–F5 | **未来方向**：仿真环境、工具创建、真实世界纵向评测、MAS 效率权衡、领域感知演化（p33） | 全是 SSEA 可率先回答的空白，亦是**后续选读方向** |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C9 最强冲突**：式(1) `arg max O(A;I)` 与「评测函数→标量分」是其定义性内核，SSEA 只能取其
    Optimiser 的**结构**，须整体拒绝其**打分—求极大**语义。
  - **C1/C8 冲突**：语言中心 + 知识/经验跨代积累，与「生存控制 + 基因只放先验」正交。
  - **C4 冲突**：重算力（RL/SFT/种群）是默认方法，成本仅是被优化目标。
- **隐含假设与失效条件**：假设有强 LLM backbone、可获取交互数据、有可靠评测指标/judge；
  在低算力、无 judge、无生存信号的场景失效。
- **算力 / 带宽 / 工程代价**：作为索引层，**零搬运成本**（只读）；唯一代价是**误用风险**——
  若把其「四组件反馈环」中的 Environment 反馈当作 SSEA 的反馈源，会引入 C9 冲突。
- **搬运后的可能退化模式**：若照搬其「评测三层」，会把 SSEA 验收拖回「打分式」评估（违反 C9）；
  若照搬 Three Laws 而不区分「安全优先」与「生存优先」，会把 SSEA 的**生存淘汰**误写成**安全打分**。

---

## 6. 组合分析（作为**索引层**）

### 6.1 关系图谱

| 关系 | 对象 | 说明 |
|---|---|---|
| 前置依赖 | 无（纯索引，可直接用） | 读它之前无需任何卡片 |
| 互补 | 全部已精读卡片 | 为每张卡片提供第二套**外部坐标格**（见 6.2） |
| 互补（并列） | **SurveySelfEvolving（Gao et al.）** | 两篇综述分工互补，见 6.3 |
| 替代 | 无 | 不替代任何方法卡片，只做地图 |

### 6.2 索引层：SSEA 已精读卡片 ↔ 本篇分类维度对应关系

| 本篇维度 | 已精读卡片（点名） | 覆盖状况 |
|---|---|---|
| **单智能体 · LLM Behaviour（权重）** | RAGEN、SEAL、EvolveR、SkillRL、Agent0 | 有覆盖 |
| **单智能体 · Prompt** | ACE、MetaContextEngineering、DynamicCheatsheet、ExperienceToStrategy | 有覆盖 |
| **单智能体 · Memory** | Memento、FLEX、A-MEM、MemRL、LightMem、SEDM、Mem0、MemGen、MemEvolve、ReasoningBank、MemoryAsAction、SelfConsolidation、G-Memory、Mem-alpha、MemSkill、AgentKB、ExperienceSynthesis | **覆盖最厚** |
| **单智能体 · Tool/Skill** | PSN、Voyager、SkillWeaver、AutoSkill、OpenSkill、InducingProgrammaticSkills、SkillNet、SkillRL | 有覆盖 |
| **多智能体 · Topology/Workflow** | ADAS、MaAS、EvoRoute、GroupEvolving、Agent-World、CoMAS | 有覆盖 |
| **多智能体 · Unified** | ADAS、MaAS | 有覆盖 |
| **多智能体 · LLM Backbone** | （RAGEN/SEAL 弱相关） | **偏薄** |
| **领域特定（生物/编程/金融/法律）** | 无（SSEA 生存域不在其清单） | **空白（且是根本分歧）** |
| **评测 / 基准** | EvoTest、HarnessEval、SkillsBench、HarnessDev | 部分覆盖 |
| **安全 / 对齐** | Misevolve、Dream-RSI | 有覆盖（但本篇用词更泛，无 misevolution 术语） |

### 6.3 两篇综述的分工与重叠（直接服务「论文筛选」）

> 同目录另一篇：**`SurveySelfEvolving.分析卡片.md`**（Gao et al., *A Survey of Self-Evolving Agents:
> What, When, How, and Where to Evolve on the Path to ASI*, arXiv:2507.21046，TMLR 01/2026）。
> 注意：**本篇（Fang et al.）在参考文献中引用了 Gao et al. 2025b（p37）**，说明两篇同期、互相知晓。

| 对比项 | **本篇 Fang et al.（SurveyComprehensive）** | **Gao et al.（SurveySelfEvolving）** |
|---|---|---|
| 组织主轴 | **范式谱系 + 优化对象**（MOP→MOA→MAO→MASE；单/多/领域） | **四问坐标**（what/when/how/where） |
| 核心形式化 | 四组件反馈环 + `A*=argmax O(A;I)`、`P=(S,H)`（p10–12） | 自演化 locus 定义 + 三范式对比表（p9/p28） |
| 方法分类 | 单智能体四类 + 多智能体四维 + 领域特定 | Reward / Imitation / Population 三范式 |
| 评测 | benchmark / LLM-judge / agent-judge（**无指标公式**，p30–32） | **有公式**：FGT/BWT、CPG、AULC + ~40 基准目录（p37–47） |
| 领域覆盖 | **强**：生物医学/编程/金融/法律（p26–30） | 弱（Where 维度仅罗列，SSEA 生存域空白） |
| 安全 | §7.3 原则性清单，**0 次 "misevolution"**（p32） | §8.3.1 三路径，**显式引用 misevolution** + Table 12 清单（p50–52） |
| 特色概念 | **Three Laws（Endure/Excel/Evolve）**、MASE 谱系 | **locus of autonomy**、三范式对比、开放问题五条 |
| 篇幅 | 55 页（正文 34 + 参考 21） | 77 页（参考 25） |
| 已有裁决 | D（兼 C）/ P2（本卡） | D（兼 C）/ P2 |

**重叠**：提示优化、记忆、工具、多智能体/工作流、评测、安全——约占两篇内容的 **60–70%**，
且术语高度一致（prompt/memory/tool/topology）。**两篇都读是否值得？——值得，但按分工读、不重复精读**：

1. **各自独有价值**：
   - **本篇（Fang）独有**：(a) **Optimiser 形式化**（搜索空间 S × 算法 H），是 SSEA 慢环提案器的
     现成形式外壳；(b) **领域特定优化分类**（生物/编程/金融/法律），Gao 几乎没有；
     (c) **多智能体拓扑即搜索空间**（code-level vs communication-graph）；(d) **MASE 范式谱系**；
     (e) **Three Laws**。
   - **Gao 独有**：(a) **what/when/how/where 四问轴**（最省脑力的定位词汇）；(b) **三学习范式
     （reward/imitation/population）**及对比表；(c) **locus of autonomy** 判据；(d) **评测指标公式
     （FGT/BWT/CPG/AULC）+ 基准目录**（直接服务 SSEA「判据形状」「睡眠期预算」债务）；
     (e) **显式 misevolution 安全框架**。
2. **筛选建议**：若只读一篇作「地图」，**优先 Gao**（坐标词汇 + 指标公式 + 安全术语更可操作）；
   **本篇作为第二篇补读**，只精读其 **§3（四组件框架，p9–12）、§5.2（多智能体拓扑，p21–26）、
   §6（领域特定，p26–30）、§8（挑战，p32–33）**，其余（提示/记忆/工具/评测）与 Gao 重叠、可略读。
3. **交叉验证价值**：两篇对同一方法（如 ADAS、A-MEM、Voyager、DGM）的分类不同，可互为**交叉校验**，
   降低单一综述的分类偏误。

### 6.4 SSEA 仍是空白的维度（→ 直接指导后续选读）

1. **领域特定优化（Where/domain）全维空白**——本篇清单是生物医学/编程/金融/法律，**SSEA 的「生存域」
   在其中不存在**；与 Gao 结论一致，说明这是**未被两篇综述覆盖的独立赛道**，应在 SSEA 文档中显式声明。
2. **Optimiser 形式化侧偏薄**——已有 MaAS/EvoRoute 卡片，但「搜索空间 × 优化算法」的**通用搜索器**
   仍缺卡片；建议补读其点名的 **ADAS、AFlow、ScoreFlow、EvoAgent、EvoFlow**（DGM≈Gödel-Agent 已读）。
3. **LLM Backbone 优化（多智能体）偏薄**——建议补读 **MaPoRL、MARFT、COPPER、OPTIMA**（关注
   「协作能力训练」，对 SSEA 未来的多代/群体有参照）。
4. **真实世界纵向 / 演化感知评测空白**——本篇自陈「snapshot-based 评测不足」（p32）；建议补读
   **EvoTest、HarnessEval**（已有卡片）与外部 **LifelongAgentBench**，服务「判据形状」债务。
5. **多模态/空间优化空白**（p33）——SSEA 若走向具身需补。
6. **标准化协议（A2A/ANP/MCP/Agora）无卡片**——仅作接口参考，优先级低。

### 6.5 本篇在组合中的典型角色
- **第二领域索引层 / 形式化外壳**：回答「SSEA 的提案器如何用 (S,H) 描述、领域特定维度是否空白」，
  并作**选读路线图**与**术语统一表**。**不提供任何可运行零件。**

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **3** | 是自演化领域全景图，与 SSEA 同域；但语言中心，与生存控制范式正交（推断） |
| 立场兼容性 | **2** | C3/C5/C6/C10 相容，但 **C1/C8/C9 明确冲突**，C9 尤其严重（式1 打分—求极大，实测于原文） |
| 可搬运性 | **2** | 无算法零件可搬运；仅术语/框架/清单可借（实测） |
| 证据强度 | **3** | 覆盖面广（~388 篇量级、55 页），但**无自研实验**、无对比表（实测） |
| 组合价值 | **4** | 作为第二索引层可与**全部**已有卡片建立坐标关系，且与 Gao 综述互补，广度极高（推断） |
| 落地成本 | **5** | 只读使用，零工程成本（实测） |

---

## 8. 裁决与下一步

- **应用等级：D 基准对照（兼 C 思想启发）**——理由：
  1. 它是**综述**，无方法零件可搬运，故非 A/B；
  2. 其核心范式（`argmax O(A;I)` 打分优化、语言中心、经验跨代积累）在 **C1/C8/C9** 上与 SSEA
     直接冲突，不可作思想主干，故非 C 为主；
  3. 其真正价值是**第二坐标系与形式化外壳**：给 SSEA 定位、指出空白、提供 Optimiser=(S,H) 术语，
     这正是 **D 基准对照**的用法；
  4. 「MASE 谱系 / Three Laws / 四组件框架 / 开放问题」具**思想启发**成分，故并列标注 C。
- **优先级：P2**——不改变代码，属索引/规划类资产；其「空白维度」与「与 Gao 的分工结论」可**立即**
  用于排后续阅读队列。
- **建议动作**：
  1. 在 sse_protocols 建「SSEA ↔ 四组件框架」映射表，**显式记录 C1/C8/C9 分歧**；
  2. 用 §6.4 空白清单 + §6.3 分工结论生成后续阅读队列（优先：通用搜索器 ADAS/AFlow/ScoreFlow；
     多智能体骨干 OPTIMA/MaPoRL；真实世界评测）；
  3. 借 §4.3 memory control（what/when/how）校准「记忆二级门选择性」债务的维度；
  4. 把 Three Laws 与 Misevolve / Gao Table 12 合并为单一安全优先级声明（去重）。
- **最小验证实验（对综述的类比：mapping / coverage audit）**：
  - **双臂设置**：臂 A = 用本篇「单/多/领域 + 四组件」给现有 60+ 张卡片打格；
    臂 B = 反向用 SSEA 的 C1–C10 给本篇代表方法打格。
  - **判据（分档）**：先看**分母**（能填入某格的卡片数 / 总卡片数）→ 再看**空格数**
    （SSEA 空白维度计数）→ 最后看**冲突格数**（落入 C1/C8/C9 冲突的方法数）。
  - **预期与证伪**：预期「Memory 格最满、Domain-Specific 全空、C9 冲突格最多」；若出现
    「Domain-Specific 有大量卡片」或「C9 冲突格极少」，则说明本篇与 SSEA 差异比预期小，需重估裁决。
- **若 E 不采用**：不适用（本篇仍有索引与形式化外壳价值）。

---

## 9. 待确认问题

- 需作者 / 团队决策：
  1. SSEA 是否需要在文档中**显式声明**与语言中心自演化范式的分歧（尤其 C9，式1 打分内核）？
  2. 是否采纳其 **Optimiser=(S,H)** 作为慢环提案器的形式化外壳？若采纳，如何把 `argmax O(A;I)`
     替换为「只判合法性的门 + 淘汰函数」？
  3. 「生存域」作为 Domain-Specific 的空白格，是保持独立赛道，还是主动对话 embodied agents？
- 需补查的文献或资料：
  4. 其点名的 **ADAS、AFlow、ScoreFlow、EvoAgent、EvoFlow**（通用搜索器）与 **OPTIMA、MaPoRL**
     （多智能体骨干）的实现细节；
  5. 外部 **LifelongAgentBench** 等纵向评测基准的定义（本篇未给指标公式）；
  6. Three Laws vs Misevolve 四路径 vs Gao Table 12 的差异对照（三份安全清单合并）。
- 需人工核对的公式 / 实现：
  7. 式(1) `A*=argmax O(A;I)` 在 SSEA 生存口径下如何重定义为**门控 + 淘汰**；
  8. 参考文献**精确条数**（本篇未给出，本卡按年份标记估算 ≈388）需人工清点确认。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "self-evolving AI agents, which bridge the static capabilities of foundation models with the continuous adaptability required by lifelong agentic systems." | p1 |
| **Three Laws of Self-Evolving AI Agents**：I. Endure (Safety Adaptation) / II. Excel (Performance Preservation) / III. Evolve (Autonomous Evolution)，层级不可越级 | p3 |
| 四阶段谱系：MOP（Model Offline Pretraining）→ MOA（Model Online Adaptation）→ MAO（Multi-Agent Orchestration）→ **MASE（Multi-Agent Self-Evolving）** | p3、Table 1 p4、Fig.1 p2 |
| 四组件框架：**System Inputs、Agent System、Environment、Optimisers**（Fig.3） | p9–10 |
| "The environment provides … feedback signals, which are derived from **predefined evaluation metrics**" | p10 |
| "The loop terminates once a **predefined performance threshold** is reached or convergence criteria are satisfied." | p10 |
| **式(1)**：`A* = arg max_{A∈S} O(A; I)`，"O(A;I) ∈ ℝ is the evaluation function that maps the performance … to a **scalar score**" | p11 |
| Optimiser 由 `(search space S, optimisation algorithm H)` 定义 | p12 |
| Fig.4 单智能体优化概览：LLM Behaviour / Prompt / Memory / Tool 四类 | p12 |
| Fig.5 层级分类树：Single-Agent（Behaviour/Prompt/Memory/Tool）· Multi-Agent（Prompt/Topology/Unified/LLM Backbone）· Domain-Specific（Biomedicine/Programming/Financial&Legal） | p13 |
| 通信两分：**Structured Output（JSON/XML/code）** vs **Natural Language**；协议 A2A / ANP / MCP / Agora | p8 |
| text gradient（ProTeGi、TextGrad）"generate natural language feedback … referred to as 'text gradient'" | p16–17 |
| 记忆优化：short-term / long-term；MemoryBank（Ebbinghaus 遗忘曲线）；memory control（what/when/how 存/更新/丢弃） | p17–19 |
| 工具优化三分：training-based / inference-time（prompt / reasoning）/ **tool function optimisation（tool creation）** | p19–21 |
| 多智能体拓扑：**code-level workflow**（AutoFlow/AFlow/ScoreFlow/MAS-GPT）vs **communication-graph**（GPTSwarm/DynaSwarm/G-Designer/AgentPrune/AGP/MermaidFlow） | p23–24 |
| 统一优化：code-based（ADAS、FlowReasoner）/ search-based（EvoAgent、EvoFlow、MASS、DebFlow、MAS-ZERO）/ learning-based（**MaAS**、ANN） | p24–25 |
| "OPTIMA … reports a **2.8× performance gain with less than 10% of the token cost**"（转引 Chen et al. 2025h） | p26 |
| 领域特定：Biomedicine（MedAgentSim/MDAgents/MMedAgent；CACTUS/ChemAgent/OSDA Agent）/ Programming（Self-Refine/Self-Debugging）/ Financial&Legal（FinCon/PEER/FinRobot；LawLuo/AgentCourt/LegalGPT） | p26–30 |
| 评测三层：Benchmark-based（ToolBench/WebArena/GAIA/OSWorld/SWE-bench）· **LLM-as-a-Judge**（pointwise/pairwise）· **Agent-as-a-Judge** | p30–32 |
| §7.3 安全基准：**AgentHarm、RedCode、MobileSafetyBench、MACHIAVELLI、SafeLawBench、R-Judge、AgentEval**；"most current evaluations are **snapshot-based** … safety evaluation must itself become dynamic" | p32 |
| §8.1 挑战：Endure（安全/法规、奖励建模不稳定）/ Excel（领域评测、效率—效果、跨 backbone 迁移性）/ Evolve（多模态空间、工具创建） | p32–33 |
| §8.2 未来方向：仿真环境、工具创建、真实世界纵向评测、MAS 效率权衡、领域感知演化 | p33 |
| 参考文献区（无总条数，本卡估算 ≈388 条；arXiv preprint ≈160 处） | p35–55 |
