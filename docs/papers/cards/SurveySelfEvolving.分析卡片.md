# 论文分析卡片 · A Survey of Self-Evolving Agents

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-07-28 A Survey of Self-Evolving Agents What, When, How, and Where to Evolve on.pdf` |
| 标题 | **A Survey of Self-Evolving Agents: What, When, How, and Where to Evolve on the Path to Artificial Super Intelligence** |
| 作者 / 机构 | Huan-ang Gao, Jiayi Geng, Wenyue Hua, Mengkang Hu 等（共 24 位，等贡献）；Princeton、Tsinghua、SJTU、CMU、HKU、UCSB、UIUC、Edinburgh 等 |
| 发表时间 / 出处 | TMLR 01/2026（arXiv:2507.21046v4，2026-01-16；文件名标注 2025-07-28） |
| 论文链接 | arXiv:2507.21046；OpenReview `CTr3bovS5F` |
| 代码链接 | https://github.com/CharlesQ9/Self-Evolving-Agents（文献清单仓库，非方法代码） |
| 标签 | 综述 · self-evolving agents · what/when/how/where 四维分类 · 奖励/模仿/种群三范式 · 自演化评测框架 · 自演化安全 |
| **应用裁决** | **D 基准对照**（兼 **C 思想启发**）——见 §8 理由 |
| 优先级 | **P2**（排队；作为索引/地图层，最高价值用法是指导「下一步读什么」） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

> **卡片重心调整说明**：本篇是**综述**而非单篇方法论文。按任务要求，2.3 改为「分类框架表」、
> 2.5 改为「文献覆盖面」、§4 改为「术语与地图资产」、§6 以「索引层」角色做组合分析。
> 全文 77 页，参考文献占 p53–77。

---

## 1. 一句话定位

- **论文主张**：给出**首个**自演化智能体（self-evolving agents）的系统性综述，把领域组织为
  **what to evolve / when to evolve / how to evolve / where to evolve** 四问；主张「自演化」的
  判据是**自主性所在（locus of autonomy）**而非所用算法，并给出评测框架、应用地图与安全治理清单
  （p1、p2–3）。
- **对 SSEA 的意义**：它不提供可直接搬运的算法零件，而是提供一张**领域坐标系**——把 SSEA 的
  ΔS/ΔM/ΔR/Δθ、双环时序、四级门、GenePackage 放进「演化对象/时机/方法/场景」四格里做对照，
  用于**定位 SSEA 的独特处与空白处**，并反向指出 SSEA 后续该读哪些论文、哪些维度尚无卡片覆盖。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：LLM 本质上是静态的，无法在开放、动态环境中自适应地更新内部参数与行为；
  领域缺少一篇把「自演化智能体」作为**一等研究范式**来系统梳理的综述（p1、p3）。
- **它指出的既有方案缺陷**：已有综述把 agent evolution 当作综合 agent taxonomy 的附属章节
  （Luo et al. 2025a；Liu et al. 2025a），或只覆盖语言模型自身的演化（Tao et al. 2024），
  均只处理孤立组件，未覆盖**整体 agent 系统**（p3）。
- 由此提出三问：*What aspects of an agent should evolve? When should adaptation occur?
  And how should that evolution be implemented?*（p3）

### 2.2 核心思想（关键 insight，1–3 条）
1. **自演化 = 自主性位置，而非算法**：区别于 SFT/RL 等传统流水线（人策管数据、人排更新），
   自演化智能体可**实时**从新数据、交互与经验中持续学习（p1–2）。据此把 self-evolving agents 与
   Curriculum Learning、Lifelong Learning、Model Editing 用「problem-setting vs solution-paradigm」
   两视角区分开（p8–9，Table 1）。
2. **四维坐标系**：**What**（演化对象：Models / Context / Tools / Agentic Architecture 四支柱）
   × **When**（Intra-test-time / Inter-test-time）× **How**（Reward-based / Imitation-based /
   Population-based 三范式）× **Where**（General domain / Specialized domain）（p9–35）。
3. **评测必须转向纵向、成本感知的轨迹视图**：从「单发打分」转为学习曲线、遗忘/后向迁移、
   泛化、效率、安全五维（p35–47）。

### 2.3 分类框架表（原「可搬运零件表」改造）

> 综述无可独立搬运的算法零件；下表整理其**四维分类维度**，并标注每维下与 SSEA 相关的代表方法。

**维度 A — What to Evolve（演化对象，p9–16）**

| 支柱 | 子维度 | 代表方法（原文点名） | 与 SSEA 相关度 |
|---|---|---|---|
| **Models {ψ}** | Policy / Experience | SCA、SELF、SCoRe、TextGrad、AutoRule、RAGEN、DYSTIL、SICA | 高（对应 Δθ 参数与 ΔR 规则） |
| **Context {C}** | Prompt Optimization / Memory Evolution | APE、PromptBreeder、SPO、ACE、DSPy、TextGrad；SAGE、A-MEM、Mem0、Memory-R1、MemGen、Memento、Expel、ReasoningBank、Agent Workflow Memory、MUSE | **最高**（对应 ΔM 记忆 + 提示注入面） |
| **Tools {W}** | Discovery/Creation / Mastery / Management | Voyager、CREATOR、CRAFT、SkillWeaver、Alita、ATLASS、LearnAct、DRAFT、ToolGen、RL-GPT | **高**（对应 ΔS 技能；Mastery=迭代精炼/credit assignment） |
| **Agentic Architecture** | Workflow / Multi-Agent | ADAS、AFlow、DGM、AlphaEvolve、MAS-Zero、Multi-Agent Design、ReMA、EvoMAC、Puppeteer、Agent0 | 中（对应 L2 信息流与 L4 群体） |

**维度 B — When to Evolve（演化时机，p16–19）**

| 时机 | 定义 | 代表方法 | 与 SSEA 相关度 |
|---|---|---|---|
| **Intra-test-time** | 任务执行**期间**实时适配，只服务当前问题实例 | ICL：Reflexion、AdaPlanner、TrustAgent；SFT：Self-adaptive LM、TT-SI；RL：LADDER(TTRL) | 中（≈ SSEA 快环内的即时适应，但 SSEA 快环**只读**） |
| **Inter-test-time** | 任务**之间**回顾式学习，面向任务分布 | ICL：ICRL、AWM；SFT：SELF、STaR、Quiet-STaR、SiriuS、ARIA；RL：RAGEN、WebRL、DigiRL | **高**（≈ SSEA 慢环 SEL 的离线整理/预演） |

**维度 C — How to Evolve（演化方法，p19–31）**

| 范式 | 反馈来源 | 代表方法 | 与 SSEA 相关度 |
|---|---|---|---|
| **Reward-based** | 标量奖励 / 语言反馈 / 内部置信度 / 环境 / 隐式 | Reflexion、SELF-Refine、SICA、RAGEN、WebRL、AgentEvolver、CISC、"Reward Is Enough" | 中——**机制与 C9 冲突**，仅作对照 |
| **Imitation / Demonstration** | 高质量示范轨迹（自生成或跨 agent） | STaR、V-STaR、AdaSTaR、STIC、GENIXER、SiriuS、RISE | 低（SSEA 不靠示范） |
| **Population / Evolutionary** | 适应度分数、竞争信号、种群代际 | DGM、GENOME/GENOME+、EvoLLM-JP、SOAR、SPIN、SPC、Absolute Zero、R-Zero、Socratic-Zero、EvoMAC、Puppeteer、Agent0 | 中高（DGM 档案分支 ≈ L4 谱系） |

**维度 D — Where to Evolve（演化场景，p32–35，Fig.8）**

| 类别 | 子领域 | 代表方法 | 与 SSEA 相关度 |
|---|---|---|---|
| **General Domain** | Memory Mechanism / Model-Agent Co-Evolution / Curriculum-Driven Training | Mobile-Agent-E、MobileSteward、Generative Agents；UI-Genie、WebEvolver、Absolute Zero；WebRL、Voyager | 中（前两者≈SSEA 记忆/课程） |
| **Specialized Domain** | Coding / GUI / Financial / Medical / Education / Others | SICA、EvoMAC、AgentCoder；WebVoyager、ReAP、AutoGUI；QuantAgent、TradingAgents；Agent Hospital、MedAgentSim、EvoPatient、DoctorAgent-RL；PACE、i-vip、EduPlanner、SEFL；Arxiv Copilot、Voyager、Richelieu | **低**（SSEA 的「生存域」不在其清单内，是最根本分歧） |

### 2.4 关键表示与数据结构
- 综述给出的**形式化**（p9、p19）：agent 系统 `Π = (Γ, {ψi}, {Ci}, {Wi})`，自演化策略
  `f : Π → Π′`，即 `Π′ = (Γ′, {ψ′i}, {C′i}, {W′i})`；演化 locus 即「可被经验驱动、持久重写」的
  内部状态集合（p9）。这是**唯一**具形式化色彩的结构，其余均为分类学。
- 评测侧定义了 Retention 的 **FGT**（遗忘）与 **BWT**（后向迁移）公式（p37）、
  **CPG**（Cost-per-Gain）与 **Tool Productivity** TP（p38）、学习曲线面积 **AULC**（p45）。

### 2.5 文献覆盖面（原「实验证据」改造）

- **引用规模**：参考文献列表占 **p53–77（约 25 页）**，正文引用极密集；`arXiv preprint` 出现
  约 233 处（正文+文献混合计数，非精确条数）。原文**未给出总条数**，按 25 页参考页密度估算
  **约 400 篇量级**（**估算值，未逐条清点**）。
- **覆盖子领域**：模型演化、上下文（提示+记忆）、工具/技能、agent 架构与多智能体、奖励/模仿/种群
  三范式、四类时序、通用与专用域应用（coding/GUI/finance/medical/education）、评测指标与基准、
  个性化、泛化、安全治理、多智能体生态（p9–53）。
- **定量对比表**：**有，但作者自陈不可做严格 apples-to-apples**。
  - **Table 11**（p47）把部分方法按 what/when/how 对齐在**近似相同** domain/benchmark/base model 下
    列性能（如 SWE-bench+Gemini-1.5-pro：Reflexion 14.3 vs Learn-by-Interact 18.7；WebArena-Lite
    +GLM-4-9B：DigiRL 31.5 vs WebRL 43.0；GSM8K+GPT-4o-mini：ADAS 90.5 / AFlow 90.8 /
    ScoreFlow 94.6；MATH+Gemini-1.5-pro：ADAS 80.0 / AFlow 76.0 / Mass 84.7）。
  - 作者明确：**latency / cost / safety 报告不一致，Table 11 仅作 illustrative snapshot**（p46–47）。
  - **Table 7**（p41）列出约 40 个基准的名称/域/目标/指标/任务量/时间跨度（如 SWE-bench 2294、
    WebShop 12087、Agent-SafetyBench 20000、LifelongAgentBench 1396、LTMBenchmark 30）。
- **无对照实验**：作为综述，无自研实验；唯一「实测数字」均为**转引他人论文**的二手数据。

### 2.6 论文自陈局限与边界条件
- 作者自陈：该领域**概念边界仍在协商中**，本文定位为 *guiding synthesis* 而非成熟范式的 review（p3）。
- 明确不适用的情形：评测侧自陈四大类缺陷——(1) 报告实践不一致；(2) 评测流水线（prompt/rollout/
  tool/env）差异大；(3) backbone 模型不可比；(4) 架构设计不可比，故**跨方法归一化会过度解读**
  （p46）。
- 覆盖盲区自陈（p46）：长时程 retention × 隐私约束、运行约束下的架构自适应、工具生态自演化、
  协作演化下的多智能体安全，**均无基准覆盖**。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 全篇研究对象是 **self-evolving LLM agents**，驱动力是语言/标量反馈与参数更新，无生存控制环；仅引言引 Darwin 名言作隐喻（p2） | 只借其分类骨架，**不借其控制范式**；SSEA 的「演化」以生存信号为组织原则，与其语言中心论正交 |
| **C2** 自然语言只作观察员接口 | **◐** | 明确把「语言作为奖励通道」（language as a reward channel）当作优势（p21–22），语言反馈是核心机制 | 取其**结构化**部分（记忆/工具/架构的组件演化），弃其语言反馈闭环；语言仅保留在日志/解释面 |
| **C3** 权重/记忆/技能三分离 | **✓** | 四支柱 Models / Context / Tools / Architecture 显式分置，且 Table 3 按「Updated Components」区分 full params / partial params / context / codebase（p20） | 四支柱可对齐 SSEA 的 Δθ/ΔM/ΔS/ΔR；Architecture 支柱 SSEA 归入 L2 结构版本 |
| **C4** 低算力低带宽 | **◐/✗** | 虽有 Efficiency 评测维度与 CPG 成本分类（p38），但主流方法是 RL/SFT/种群搜索，计算昂贵；成本是「被评测项」而非「硬约束」 | 借其 **CPG / 成本分类法**做预算度量，拒绝其重算力方法；SSEA 需把成本上升为硬约束 |
| **C5** 精准回忆历史 | **✓** | Context/Memory Evolution 专章（p11–12）：Mem0 的 ADD/MERGE/DELETE、Memory-R1 的 RL 记忆管理、A-MEM 的 Zettelkasten 链接、MemGen 潜在空间生成记忆 | 直接支撑 SSEA 记忆侧（ΔM）；其「检索策略可学习」与 Memento/FLEX 卡片呼应 |
| **C6** 可自主修改自身 | **✓** | Models 支柱（自生成监督改权重）、SICA/DGM 直接改自身代码库（p10–11、p25）；但**未拆四权**（提案/边界/验证/应用） | 借其「自修改谱系」做对照；SSEA 的四权拆分是**更细**的治理，可反向作为其安全章节的补强 |
| **C7** 保存/恢复/变异/继承 | **◐** | DGM 维护历史版本档案、可从任意「物种」分支（p25）；GENOME/GENOME+ 参数空间继承与集成（p25）；种群/自博弈代际 | 有「档案+分支+继承」，但**无 GenePackage 式打包**，且繁衍由适应度分数驱动；SSEA 的「繁衍是挣来的机会」在其框架内无对应 |
| **C8** 给基因先验，不给知识语料 | **✗** | 全篇核心是**经验/知识/技能的持续积累**（记忆蒸馏、技能库、课程），无「结构性先验 vs 后天知识」的区分与跨代隔离 | 不借其知识积累立场；SSEA 的基因只放本能先验，需明确拒绝其「经验跨代累积」倾向 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（强冲突）** | Reward-based 是三范式之一且置于首位（p19–22）：scalar reward、ORM/PRM、fitness score、self-reward model 全是**评分**；未区分「外部评分函数」与「环境淘汰函数」。作者仅承认奖励设计敏感（"trading stability and safety for adaptability"，p22） | **这是本篇对 SSEA 最重要的反面教材**：SSEA 只取其三范式**分类名**，拒绝其奖励机制；其内部置信度奖励（CISC 等，p21）是 SSEA「内在驱动」的最接近类比，但仍属打分，须改造为「定义不可改的内在信号」 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 全篇创新集中在 L2（组件/信息流）、L3（学习/更新机制）、L4（种群/继承/共演化）；L1 算子未涉及 | 与其立场一致；可直接用其 L2/L3/L4 术语标注 SSEA 各模块 |

**关于「评分函数 vs 环境淘汰」（对照 C9）**：论文**未做此区分**。它把奖励视为「显式优化 + 强自主」的
手段（p22），并把「外部奖励 / 内部置信度奖励 / 隐式奖励」并列讨论（p21–22），最接近 C9 的是
**internal confidence-based rewards**（CISC、Self-Ensemble、Self-Rewarding LM），但原文仍以「奖励」
框定。结论：**它站在 C9 的对立面**，但恰可作为 SSEA「无评分」立场的**对照组**。

**关于安全性/误演化（对照 Misevolve 卡片）**：**有讨论，且直接引用 Misevolve 原文**。
§8.3.1（p50–51）以 **model / memory / tools** 三条演化路径列举涌现风险，明确点名
"misevolution (Shao et al., 2025)"：模型演化的安全对齐灾难性遗忘、记忆演化的部署期奖励黑客
（"不必要的退款"例子）、自建/摄入外部工具的安全漏洞；并引入 **Alignment Tipping Process (ATP)**
（Han et al. 2025）。§8.3.2（p51）给出 prescriptive guardrails（沙箱+静态验证、审计轨迹+回滚、
持续监控+红队、审批门），并汇总为 **Table 12 合规清单**（p52）。注意：它只列**三**路径
（未单列 workflow/architecture），比 Misevolve 四路径少一条。

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子，LLM 作 backbone | 符合「借用且可替换」立场 |
| **L2 信息流层** | **What to Evolve 四支柱** + When 两时序 + Where 两域，构成组件/信息流地图 | **高**：可用于给 SSEA 双环、三分离、注入面做坐标系定位 |
| **L3 学习层** | **How to Evolve 三范式** + online/offline、on/off-policy、reward granularity 三个正交轴（Table 4，p28） | **高**：为 SSEA 自修改/可塑性/技能固化提供术语对照 |
| **L4 演化层** | Population/自博弈、DGM 版本档案、GENOME 继承、多智能体共演化（p24–27） | **中高**：是 SSEA 缺失的 Gene Manager / 谱系维度的**外部参照系** |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 四支柱 Models/Context/Tools/Architecture | 与 SSEA 四类结构版本 **Δθ / ΔM / ΔS / ΔR** 做交叉映射表（建议写入 sse_protocols 术语表） |
| Intra-test / Inter-test 时序 | 对照 **快环 FSL / 慢环 SEL**：SSEA 快环只读→无 intra-test 自修改，是其**结构性差异点** |
| Reward / Imitation / Population 三范式 | 标注 SSEA 为**第四类**：生存淘汰驱动（非奖励、非示范、非适应度） |
| Retention FGT / BWT 公式（p37） | 记忆门「开得准不准」选择性缺失的**度量候选**（债务：记忆二级门常量阈值） |
| CPG / 成本分类（token/time/step/tool/memory/human，p38） | **睡眠期计算预算未定义**债务的直接模板 |
| 学习曲线 / AULC / success-by-iteration（p45） | 判据形状错（债务 25–28）的**评测形状**参考 |
| Table 12 合规清单（p52） | Gate / HeritableFilter / RuleCompiler / DeathHook 的**验收清单**（与 Misevolve 卡片重叠） |
| §8.3.1 三路径误演化 | 安全章节的风险登记（Misevolve 四路径的子集） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **睡眠期计算预算未定义** → 借 Table 5/CPG 成本分类（p38）定义慢环预算单位；
  - **记忆门「开得准不准」的选择性缺失** → 借 FGT/BWT（p37）定义记忆选择性指标；
  - **判据形状错（25/26/27/28）** → 借 success-by-iteration / AULC（p45）校准判据形状；
  - **Gene Manager 缺失** → 借 DGM 版本档案 + GENOME 继承（p25）作为谱系设计参照。
- **可服务的验收实验**：**七条中的 4/5**（Gene Manager 相关）与**技能固化实验 3**（技能表示是否够
  → Tools 支柱的 discovery/mastery/management 三分法可作表示完备性检查表）。
- **不能回应**：C9 相关（它本身违反 C9）、生存信号定义（其框架无生存概念）。

---

## 4. 术语与地图资产清单（原「可借鉴资产清单」改造）

| # | 资产 | 类型 | 搬运方式 | 落点 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **what/when/how/where 四维分类骨架** | 分类框架 | 仅借思想（作索引层） | 论文阅读规划 / 术语表 | 系统化定位 SSEA 与补读方向 | 高 |
| 2 | **L2/L3/L4 术语集**：intra-/inter-test、reward/imitation/population、online/offline、on/off-policy、outcome/process/hybrid reward | 术语 | 直接引用 | sse_protocols 术语表 | 与外部文献对齐、减少自造词 | 高 |
| 3 | **评测五维框架**：Adaptivity / Retention / Generalization / Efficiency / Safety + 指标（FGT/BWT、CPG、AULC） | 基准/度量 | 改造移植 | 验收实验设计 | 记忆/效率/安全的度量缺口 | 高 |
| 4 | **成本分类法**（token/time/step/tool/memory/human，Table 5） | 度量 | 改造移植 | 睡眠期预算定义 | 「睡眠期计算预算未定义」 | 高 |
| 5 | **标准化评测协议**（short-horizon K_short / long-horizon K_stage,K_total，Table 10） | 协议 | 仅借思想 | 验收实验协议 | 判据形状与日志规范 | 中 |
| 6 | **Table 12 部署合规清单**（沙箱/审计/回滚/监控/红队/审批门） | 清单 | 改造移植 | Gate/HeritableFilter/RuleCompiler/DeathHook | 自修改安全验收 | 中（与 Misevolve 重叠） |
| 7 | **§8.3.1 三路径误演化风险 + ATP** | 风险分类 | 直接引用 | 安全风险登记 | 安全治理（Misevolve 子集） | 中 |
| 8 | **开放问题清单**（见下方 §4.1） | 研究议程 | 仅借思想 | SSEA 定位与选读 | 指出领域空白，反衬 SSEA 差异 | 高 |

### 4.1 论文列出的开放问题（对 SSEA 定位自身极有价值，p48–53）

| # | 开放问题（原文） | 对 SSEA 的定位价值 |
|---|---|---|
| O1 | **个性化（cold-start）**：无高质量大规模用户数据时如何逐步构建用户画像；并防止放大偏见（p48–49） | SSEA 不个性化，但其「记忆不跨代」立场是此问题的**极端解**（拒绝长期个性化记忆） |
| O2 | **泛化**：专用化 vs 广泛适应的张力；灾难性遗忘的 stability-plasticity 困境；知识可迁移性差（p49–50） | 直指 SSEA「基因先验不跨代」是否牺牲泛化——**SSEA 需要回答的对照问题** |
| O3 | **安全可控**：自演化涌现风险与「安全生命周期」治理（p50–52） | SSEA 四级门 + 淘汰函数即其「safety lifecycle」的非语言版 |
| O4 | **多智能体生态**：个体 vs 集体推理的平衡、群体安全的社会传染（p51–53） | SSEA 若走向多智能体/多代，须回答此问题 |
| O5 | **评测盲区**（p46）：长时程 retention×隐私、运行约束下的架构自适应、工具生态自演化、协作演化安全 | 全是 SSEA 可率先回答的空白，亦是**后续选读论文的方向** |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C9 最强冲突**：奖励/适应度驱动是其「How」的核心，SSEA 只能取其分类名，须整体拒绝其机制。
  - **C1/C8 冲突**：语言中心 + 经验知识跨代积累，与「生存控制 + 基因只放先验」正交。
  - **C4 冲突**：重算力方法被当作默认，成本仅是被测项。
- **隐含假设与失效条件**：假设有强 LLM backbone、可获取大规模交互/标注、有可靠 reward/judge；
  在低算力、无 judge、无生存信号的场景失效。
- **算力 / 带宽 / 工程代价**：作为索引层，**零搬运成本**（只读）；唯一代价是**误用风险**——
  若把其分类术语误当架构建议，会引入 C9 冲突。
- **搬运后的可能退化模式**：若照搬其「评测五维」，可能把 SSEA 验收拖回「打分式」评估（违反 C9）；
  须把 Safety/Retention 指标改造为**门控/淘汰口径**而非分数。

---

## 6. 组合分析（作为**索引层**）

### 6.1 关系图谱

| 关系 | 对象 | 说明 |
|---|---|---|
| 前置依赖 | 无（纯索引，可直接用） | 读它之前无需任何卡片 |
| 互补 | 全部已精读卡片 | 为每张卡片提供一个**外部坐标格**（见 6.2） |
| 替代 | 无 | 不替代任何方法卡片，只做地图 |

### 6.2 索引层：SSEA 已精读卡片 ↔ 本篇分类维度对应关系

| 本篇维度 | 已精读卡片（点名） | 覆盖状况 |
|---|---|---|
| **What · Models** | RAGEN、SEAL、EvolveR、SkillRL、Agent0 | 有覆盖 |
| **What · Context/Memory** | Memento、FLEX、A-MEM、MemRL、LightMem、SEDM、Mem0、MemGen、MemEvolve、ReasoningBank、DynamicCheatsheet、MemoryAsAction、SelfConsolidation、ACE | **覆盖最厚** |
| **What · Tools/Skills** | PSN、Voyager、SkillWeaver、AutoSkill、OpenSkill、InducingProgrammaticSkills、MemSkill | 有覆盖 |
| **What · Architecture** | ADAS、MaAS、EvoRoute、GroupEvolving、Agent-World | 有覆盖 |
| **When · Intra-test** | Reflexion、DynamicCheatsheet | 有覆盖 |
| **When · Inter-test** | Dream-RSI、FLEX、SelfConsolidation、LightMem（睡眠期离线巩固） | 有覆盖 |
| **How · Reward-based** | WebRL、RAGEN | 有覆盖（但 SSEA 立场相反） |
| **How · Imitation** | Voyager（弱） | **偏薄** |
| **How · Population/Evolutionary** | ADAS、Gödel-Agent、GroupEvolving、Agent0 | 偏薄 |
| **Where · General domain** | 无专门卡片 | **空白** |
| **Where · Specialized domain** | 无（SSEA 生存域不在其清单） | **空白（且是根本分歧）** |
| **安全/误演化** | Misevolve、Dream-RSI | 有覆盖 |

### 6.3 SSEA 仍是空白的维度（→ 直接指导后续选读）

1. **Where（应用场景）全维空白**——尤其 SSEA 的「生存域」在本篇坐标系中**不存在**，说明这是一条
   **未被综述覆盖的独立赛道**；不必强补，但应在 SSEA 文档中显式声明这一分歧。
2. **Population / L4 演化（Gene Manager 缺失的对应侧）**——建议补读其点名的 **DGM、GENOME/GENOME+、
   SPIN、Agent0**（已有 Agent0 卡片，DGM≈Gödel-Agent 已读），重点看**版本档案与继承**。
3. **Imitation/Demonstration** 偏薄——可补读 STaR、SiriuS、V-STaR（若 SSEA 需要课程侧）。
4. **评测/基准**几乎无卡片——建议补读 **LifelongAgentBench、EvalLearn、LTMBenchmark**，
   直接服务「判据形状」与「长时程 retention」债务。
5. **多智能体生态与群体安全**空白——对应 O4，若 SSEA 走向多代/群体需补。
6. **个性化 cold-start**空白——SSEA 立场可能不需要，但需在文档中给出拒绝理由。

### 6.4 本篇在组合中的典型角色
- **领域索引层 / 坐标系**：回答「SSEA 的每个模块在领域地图的哪一格、哪几格是空白」，
  并作为**选读路线图**与**术语统一表**。**不提供任何可运行零件。**

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **3** | 是自演化领域全景图，与 SSEA 同域；但语言中心，与生存控制范式正交（推断） |
| 立场兼容性 | **2** | C3/C5/C6/C10 相容，但 **C1/C8/C9 明确冲突**，C9 尤其严重（实测于原文） |
| 可搬运性 | **2** | 无算法零件可搬运；仅术语/骨架/清单可借（实测） |
| 证据强度 | **3** | 覆盖面极广（~400 篇量级、77 页），但**无自研实验**，定量对比作者自陈不可比（实测） |
| 组合价值 | **4** | 作为索引层可与**全部**已有卡片建立坐标关系，指导选读，广度极高（推断） |
| 落地成本 | **5** | 只读使用，零工程成本（实测） |

---

## 8. 裁决与下一步

- **应用等级：D 基准对照（兼 C 思想启发）**——理由：
  1. 它是**综述**，无方法零件可搬运，故非 A/B；
  2. 其核心范式（奖励/适应度驱动、语言中心、经验跨代积累）在 **C1/C8/C9** 上与 SSEA 直接冲突，
     不可作为思想主干，故非 C 为主；
  3. 其真正价值是**坐标系与对照系**：用于给 SSEA 定位、指出空白、校准术语与评测形状，
     这正是 **D 基准对照**的用法；
  4. 「术语集 / 开放问题 / 评测五维 / 合规清单」具**思想启发**成分，故并列标注 C。
- **优先级：P2**——不改变代码，属索引/规划类资产；但其「空白维度」清单可**立即**用于排后续阅读队列。
- **建议动作**：
  1. 在 sse_protocols 建「SSEA ↔ 四维坐标」映射表，显式记录 C1/C8/C9 分歧；
  2. 用 §6.3 空白清单生成后续论文阅读队列（优先 DGM/GENOME、LifelongAgentBench/EvalLearn）；
  3. 借 Table 5 成本分类与 FGT/BWT 校准「睡眠期预算」与「记忆选择性」两项债务的度量；
  4. 将 Table 12 合规清单与 Misevolve 卡片合并为单一安全验收清单（去重）。
- **最小验证实验（对综述的类比：映射审计 / coverage audit）**：
  - **双臂设置**：臂 A = 用本篇 what/when/how/where 四维给现有 40+ 张卡片打格；臂 B = 反向用
    SSEA 的 C1–C10 给本篇代表方法打格。
  - **判据（分档）**：先看**分母**（能填入某格的卡片数 / 总卡片数）→ 再看**空格数**（SSEA 空白维度
    计数）→ 最后看**冲突格数**（落入 C1/C8/C9 冲突的方法数）。
  - **预期与证伪**：预期「Context/Memory 格最满、Where 全空、C9 冲突格最多」；若出现「Where 有大量
    卡片」或「C9 冲突格极少」，则说明本篇与 SSEA 的差异比预期小，需重估裁决。
- **若 E 不采用**：不适用（本篇仍有索引价值）。

---

## 9. 待确认问题

- 需作者 / 团队决策：
  1. SSEA 是否需要在文档中**显式声明**与语言中心自演化范式的分歧（尤其 C9）？
  2. 「生存域」作为 Where 维度的空白格，是保持独立赛道，还是主动寻找可对话的既有域（如 embodied
     agents）？
- 需补查的文献或资料：
  3. 其点名的 **DGM、GENOME/GENOME+、SPIN、Agent0** 的版本档案/继承机制（对应 Gene Manager）；
  4. **LifelongAgentBench、EvalLearn、LTMBenchmark** 的 retention 度量定义；
  5. Misevolve 四路径 vs 本篇三路径的差异（workflow 路径是否被本篇遗漏）。
- 需人工核对的公式 / 实现：
  6. FGT / BWT（p37）与 CPG（p38）公式在 SSEA 生存口径下如何重定义；
  7. 参考文献**精确条数**（本篇未给出，本卡为估算）需人工清点确认。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "we define self-evolution not merely by the algorithms used, but by the **locus of autonomy**" | p2 |
| "This survey provides the first systematic and comprehensive review of self-evolving agents, organizing the field around three foundational dimensions — what to evolve, when to evolve, and how to evolve." | p1 |
| 三问："What aspects of an agent should evolve? When should adaptation occur? And how should that evolution be implemented in practice?" | p3 |
| 形式化：`Π = (Γ, {ψi}, {Ci}, {Wi})`，演化 locus = 可被经验驱动、持久重写的内部状态 | p9 |
| Table 2：四支柱（Model/Context/Tool/Architecture）代表方法定位（SCA、RAGEN、AgentGen、Mem0、Alita、TextGrad、DGM、AlphaEvolve、ADAS、AFlow、SkillWeaver、Voyager 等） | p10 |
| Table 1：Self-evolving Agents 在 Runtime Context/Toolset/Dynamic Tasks/…/Self-reflect 七项全 ✓，区别于 Curriculum/Lifelong/Model Editing | p9 |
| Table 3：按 Feedback Type/Source、Learning Method、Updated Components、Update Timing 分类方法 | p20 |
| Table 4：Reward/Imitation/Population 三范式在 Feedback、Data Source、Granularity、Online/Offline、On/Off-policy、Sample Efficiency、Stability、Scalability 上的对比 | p28 |
| "reward-based evolution provides explicit optimization and strong autonomy but remains sensitive to reward design, often trading stability and safety for adaptability and openness." | p22 |
| Fig.8：Where to evolve = General Domain（Memory / Model-Agent Co-Evolution / Curriculum）vs Specific Domain（Coding/GUI/Financial/Medical/Education/Others） | p32 |
| FGT 与 BWT 公式 | p37 |
| CPG = Total Cost / Performance Gain；Table 5 成本分类（token/time/step/tool/memory/human） | p38 |
| 自定向性权衡：WebRL 4.8%→42.4%、SEAgent 11.3%→34.5%；alignment faking 12%→78%（Greenblatt et al. 2024） | p39 |
| Table 6：评测五维指标（Adaptivity/Retention/Generalization/Efficiency/Safety） | p40 |
| Table 7：约 40 个基准目录（含 LifelongAgentBench 1396、Agent-SafetyBench 20000、LTMBenchmark 30） | p41 |
| Table 11：近似同设定下的跨方法性能快照（作者自陈 illustrative、非 apples-to-apples） | p47 |
| "**misevolution** (Shao et al., 2025)" 及 model/memory/tool 三路径涌现风险；ATP | p50–51 |
| Table 12：部署合规清单（沙箱/审计轨迹/回滚/持续监控/红队/审批门/记忆防御/隐私） | p52 |
| 开放问题：个性化 cold-start、泛化与灾难性遗忘、安全可控、多智能体生态 | p48–53 |
