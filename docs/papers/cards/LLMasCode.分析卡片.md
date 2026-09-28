# 论文分析卡片 · LLM-as-Code

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-06-14 LLM-as-Code Agentic Programming for Agent Harness.pdf` |
| 标题 | **LLM-as-Code: Agentic Programming for Agent Harness** |
| 作者 / 机构 | Junjia Qi\*、Zichuan Fu\*（Equal contributions）、Jingtong Gao、Wenlin Zhang、Hanyu Yan — City University of Hong Kong；Xian Wu — Tencent Jarvis Lab；Xiangyu Zhao — City University of Hong Kong（p1） |
| 发表时间 / 出处 | Accepted at **KDD 2026 Workshop on Agentic Software Engineering (AgenticSE)**；arXiv:2606.15874v2 [cs.AI]，2026-06-22（p1）；PDF 文件标注 2026-06-14 |
| 论文链接 | arXiv:2606.15874 |
| 代码链接 | **未提及**（论文只描述参考实现与 `@agentic` 装饰器，未给仓库地址，p6–7 App.C） |
| 标签 | agent harness · 控制流归属 · LLM-as-Code · DAG 结构上下文 · 代码驱动工作流 · 自我编程演化 · 代码固化 |
| **应用裁决** | **A 核心借鉴**（范式级 C2 对齐 + L2 可搬零件；其「叶内联 LLM 调用」与 benchmark 分数驱动须剥离） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：主流 agent 框架把「下一步做什么、何时调工具、何时停」交给 LLM，是**类别错误**——
  循环、分支、顺序是确定性工作，而 LLM 的每个输出都是从分布中采样（包括控制流决策）；
  因此 token explosion、control-flow hallucination、unreliable completion **不是实现 bug 而是架构后果**，
  换更强模型或更好提示都不能保证可靠。作者提出 **Agentic Programming**：**程序拥有全部控制流**，
  LLM 只是程序里的一个自适应组件 **LLM-as-Code**，**只在需要推理/生成处被调用**；每次调用内部
  自由推理，但**不能改变程序的执行路径**。上下文由调用图（DAG）构成，长度由**调用深度 O(depth)**
  而非步数 O(steps) 决定。四个部分：代码驱动工作流、DAG 结构上下文、多 agent 协作（即函数调用图）、
  自我编程演化（改进**固化为代码**）。案例：GUI agent 在 OSWorld 上 **15 步达 86.8%**，
  超过所有 100 步基线（最强 80.4）（p1、p4–5、Table 1 p5、Table 2 p7）。
- **对 SSEA 的意义**：这是**「C2（语言不进控制闭环）」最干净的英文形式化**——它明确把「控制流」
  写成**代码**、把自然语言提示限制在**叶调用内部**，并证明「代码非自然语言」这一区别带来可靠性；
  同时它的 **DAG 上下文作用域规则**（祖先链全量 + 已返回子树塌缩为摘要）给出 **C4（缓冲不无界增长）**
  的可搬实现，它的 **「提案→测试→commit as code」**（Algorithm 1）给出 **C7/C8** 的载体形态：
  harness 改进以**可执行代码**固化，天然可打包进 GenePackage。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题

- **问题本身**：主流 LLM agent 框架（ReAct [22]、AutoGen [19]、OpenHands [18]、MetaGPT [5]）
  都把 LLM 当 **orchestrator**：模型自己跑循环、选工具、读结果、判完成。长时程任务（如多文件
  refactor）上反复出现三症状：① **token explosion**（上下文随步数累积，根因假设被截断丢失）；
  ② **control-flow hallucination**（在 verifier 跑之前就报告问题已解决）；③ **unreliable
  completion**（被最新失败测试带偏，放弃先前正确诊断，且**无法保证该跑的步骤真的跑过**）（p1–2）。
- **它指出的既有方案缺陷**（p2 §2.2–2.3、p6 App.A）：每一种「补丁」只治一个症状、**不移动控制权**——
  更大窗口/更聪明的压缩仍是「平铺对话日志」，表示本身就是错的；自我反思（ReAct/Reflexion）只降
  **单步**错误率，控制仍是**采样**，长程失败率仍复利；约束解码只保证控制决策的**形式**（合法 JSON）
  而非**正确性**（仍可跳步/早停）；Plan-and-execute 把控制委托给一个同样采样的「计划」；LangGraph 的图
  **预声明**且共享 state；DSPy 优化图内每调用但**图本身由作者固定**；给 orchestrator 加结构化 state 只是
  让采样去读写 state。作者的判断：**只有把控制移出模型**才能解决类别错误。

### 2.2 核心思想（关键 insight）

1. **确定性 vs 概率性工作必须分层**（p2 §2.1）：循环/分支/顺序/变量绑定/错误处理是**确定性**工作，
   编程语言已完美解决（`for` 恰好迭代 n 次、`if` 当且仅当条件成立时进入、函数调用转移控制并返回）；
   语言理解/摘要/生成/判断是**概率性**工作。把前者交给后者是**类别错误**；「问 LLM『下一步做什么』
   就是从一个概率分布中采样一条控制流边」。
2. **唯一能保证循环执行 n 次的办法就是把循环写出来**（p2）：可靠性的来源是**构造**（by construction），
   不是「更好的提示」——程序执行规则，而非**请求模型遵守**规则。
3. **上下文应跟踪调用图而非平铺日志**（p3 §3.2）：执行历史就是调用图（DAG）；作用域规则 =
   「一次调用看到其**整条祖先链**的完整上下文，而每个栈帧只保留**已返回子节点的一行摘要**」；
   输入长度因此被**当前深度 O(depth)** 而非总步数 O(steps) 界定。
4. **自我改进应固化为代码而非记忆中的文本**（p4 §3.4）：提出新函数是概率性 LLM 调用，但结果
   **以代码提交**（仅在通过调用者测试后接受），此后**像任何其他受保证步骤一样无条件运行**；
   而自我改进的 orchestrator 只是「每次运行被重新读取、重新决定的文本」，是否遵守某个教训本身仍是采样。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **Agentic Programming 四部分** | 代码驱动工作流 / DAG 上下文 / 多 agent 协作 / 自我编程演化 | 范式形式化：程序拥有控制，LLM 在叶 | §3 引言 p3 |
| **代码驱动工作流** | 程序控制执行 → 只在需推理处调 LLM | 合规由运行时保证，不再向模型乞求 | §3.1 p3 |
| **运行时展开的调用图** | 判断触发更多工作 → 被调函数仍是普通代码（内含自身 LLM 调用） | 调用图在运行时展开，而非预先固定 | §3.1 p3、App.C p7 |
| **`@agentic` 装饰器** | 函数签名 + docstring → 填提示模板、调模型、按声明返回类型解析 | 把 LLM 调用伪装成普通函数调用 | App.C p6–7 |
| **DAG 上下文作用域规则** | 祖先链全量 + 已返回子节点一行摘要 | 输入长度 O(depth) 而非 O(steps) | §3.2、Fig.2 p3–4 |
| **harness 级全图保留** | 完整 DAG 留存 → replay / debugging | 无损（无节点看到全图，但全图存在） | §3.2 p4 |
| **多 agent = 函数并行** | 多个 agent 函数 → 并行执行，兄弟分支，类型化返回值合并 | 协调即调用图，无监督模型；失败=失败调用 | §3.3 p4 |
| **程序化 join** | 父级去重/排序/决定展示 | 合并是程序逻辑，可复现、可检查 | §3.3 p4 |
| **自我编程演化（Algorithm 1）** | agentic 函数 f + 测试集 T + 提案 meta 函数 g → f′ | 只在通过全部测试后 commit 为代码 | §3.4、App.D p4、p7 |
| **测试门（回归）** | 单元测试 pin 住 LLM 回复 → 对外层函数输出做确定性断言 | 把「LLM 输出的正确性」变成确定性回归 | §3.4 p4 |
| **失败定位到命名调用** | 失败 → 某个具名调用的返回值 | 替代「五十步 transcript 中的某一轮」 | §3.4 p4 |
| **反模式清单（App.A）** | 逐一驳斥 8 类补丁（更大窗口/反思/约束解码/CodeAct/plan-execute/LangGraph/DSPy/加 state） | 界定「谁拥有控制流」这一分界线 | App.A p6 |

### 2.4 关键表示与数据结构

- **执行历史 = 调用图（DAG）**：节点为函数调用与推理调用；简单情形是树，**并行分支汇合后成 DAG**
  （p3 §3.2）。运行中的调用持**整条祖先链**；已返回的调用**塌缩为一行摘要**（Fig.2 p3–4）。
- **agentic 函数**：`@agentic def summarize(text: str) -> str: """..."""` ——**函数体只有 docstring**，
  运行时取签名 + docstring 填提示模板、调底层模型、按**声明返回类型**解析后交回调用者（App.C p6–7）。
- **类型化返回值作为 agent 间接口**：agent 间接口是**类型化返回值**而非自由文本对话；失败 agent =
  一个失败调用，程序可按自身规则重试/替换/放弃（§3.3 p4）。
- **自我演化表示**：f 带测试集 T；meta 函数 g 提案 f′；接受判据是确定性测试（App.D p7）。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| GUI 自动化 · OSWorld overall | Holo3-35B-A3B 80.4；OpenAPA w/ Gemini-3.1-pro 78.3；Claude Sonnet 4.6 72.1 | **Ours 86.8（仅 15 步）** | 基线取自 OSWorld 公共榜单（accessed 2026-06-02），基线**均 100 步**；Table 1 p5 |
| GUI 自动化 · 分域 | Agent S3/UiPath/HIPPO/VLAA-GUI/OpenAPA/Kimi K2.6/Holo3 等（均 100 步） | Ours **Chrome 93.5 / Multi-Apps 80.0 / OS 100.0 / Overall 86.8**（15 步），最强先前系统 80.4 | Table 2 p7 |
| 规模/工程性 | — | 两个生产 agent（GUI 自动化 + **自主过夜研究流水线**）共享同构：循环拥有迭代与终止，LLM 只在叶推理；**各自顶层循环约 150 行 Python** | §E p7（研究流水线**未给数字**） |
| 无消融 / 无 seed / 无误差棒 | — | **论文未报告** seed 数、多轮重复、方差或 held-out 切分 | — |

### 2.6 论文自陈局限与边界条件

- **明确不主张普适**（p4 §3.4）：「**完全探索性、无已知结构**的任务（如开放式头脑风暴、无阶段模型的
  研究）可能受益于 LLM 驱动的编排，**我们不作争辩**」——本篇只主张「**当工作流有已知结构时，
  该结构应写成程序**」。
- 论文**无独立「Limitations」节**；未提及**沙盒执行**、未提及**回滚机制**、未提及**并发/资源治理**、
  未提及对**自动生成代码的安全审查**（这些均由读者推断其缺口）。
- 证据面窄：单一 benchmark（OSWorld）的一次案例研究，**无消融、无多种子、无 held-out**；
  基线数字**取自公共榜单而非本地复现**（Table 1/2 p5、p7），统计口径**不齐**（Ours 15 步 vs 基线 100 步）。
- 前提假设：工作流**存在可写出的已知结构**；叶调用可返回**可解析的类型化值**。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 优化目标是 **SE 任务成功**（OSWorld GUI 自动化、过夜研究流水线），**无生存信号、无淘汰闭环**（p1、§E p7） | 把「程序拥有控制流」的骨架迁到 **FSL 生存控制环**；叶 LLM 调用移出快环 |
| **C2** 自然语言只作观察员接口 | **◐（偏 ✓）** | **控制流由程序（代码）拥有，不是采样的自然语言**——这是全篇与 C2 最紧的对齐，且明确区分「代码」与「提示」（§2.1 deterministic vs probabilistic、§3.1「workflow lives in the program」）；**但**① 每个 `@agentic` 调用点内部仍是自然语言提示（docstring→prompt 模板，App.C p6），② LLM 在**执行期（叶）被内联调用**做判断，属「在线语言决策」，SSEA 快环要求**运行期零语言** | 保留「控制流=代码」；把叶 LLM 调用移入**慢环编译面**；叶调用产物必须是**结构化值**而非自由文本；快环不内联任何语言调用 |
| **C3** 权重/记忆/技能三分离 | **◐** | 程序/harness 代码与模型权重分离（模型是可替换 API）；DAG 全图在 harness 级留存，可视为独立**记忆面**；但**无「权重/记忆/技能」显式三通道分置** | 程序骨架归 **ΔS 技能侧**；权重冻结；harness 级 DAG 归 **ΔM 记忆侧** |
| **C4** 低算力低带宽 | **✓（偏 ◐）** | **本文核心动机就是消 token 爆炸**：上下文由 O(steps×avg_output) 降为 **O(depth)**（§3.2 p4）；控制流非语言、缓冲**不随步数无界增长**——与 C4「控制环信息少而结构化；缓冲不无界增长」直接同向 | 绝对算力仍不低（前沿 LLM 被调用）；SSEA 需把叶调用限频入慢环 |
| **C5** 精准回忆历史 | **◐** | **完整 DAG 在 harness 级保留供 replay 与 debugging**（§3.2 p4）——历史无损、可回放；但**无检索/写入/遗忘/合并**，且「无节点能看到全图」 | 与 Memento 检索 μ / LightMem 巩固组合补检索与写入 |
| **C6** 可自主修改自身 | **✓/◐** | §3.4 + Algorithm 1：meta 函数 g **提案** f′（采样），**验证**=确定性测试，**应用**=通过后 commit as code；**四权中缺「边界权」**（无不可修改清单/宪法，未提及） | 补边界权（Ouroboros 受保护宪法核） |
| **C7** 保存/恢复/变异/继承 | **✓/◐** | 「改进**以 durable code 提交**，此后无条件运行」（§3.4 p4）——**代码形态天然可保存/可打包**，对 GenePackage 有利；但**无显式版本化仓库、无种群、无跨代继承、无回滚**（未提及） | 代码提交 → 结构库版本；补版本/回滚（PSN/Ouroboros）；补种群与继承 |
| **C8** 给基因先验，不给知识语料 | **◐** | **程序（控制流骨架）是结构性先验**，可入基因；但 `@agentic` 的 docstring/prompt/参数**携带任务知识**，成品 harness 含知识语料（App.C p6） | 基因只放**控制流骨架**；docstring/prompt 归后天、不跨代 |
| **C9** 不设评分函数，只有淘汰函数 | **◐（机制层对齐）** | **Algorithm 1 的接受判据是「通过全部测试」，属合法性门（pass/fail）、不打分、不排序**——与 C9「验证门只判合法性」同向；**但**① 论文实证主张依赖 **OSWorld 外部 benchmark 分数**（Table 1/2），② **无淘汰函数/生存闭环** | 保留「测试即接受判据」；**去掉** benchmark 分数作为驱动；淘汰交环境 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 创新在 **L2**（code-driven workflow、DAG context、多 agent=调用图）、**L3**（self-programmed evolution）、**L4**（代码固化）；**无新 L1 算子**，模型是现成前沿 LLM（p1、§3） | — |

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层**（基础网络模块） | 无新算子；模型是可替换 API | 符合借用立场 |
| **L2 信息流层**（模块如何连接） | **代码驱动工作流 + DAG 结构上下文 + 多 agent=调用图**（§3.1–3.3） | **高**：给 SSEA 快环/慢环提供「控制流=代码」的语言与上下文有界化规则 |
| **L3 学习层**（如何更新自身） | **self-programmed evolution**：meta 函数提案 → 测试 → commit as code（§3.4、App.D） | 中高：有测试闸的代码固化回路 |
| **L4 演化层**（保存/继承/变异） | durable code commit（改进固化为可执行代码） | 中：**GenePackage 的载体形态**；无种群/继承 |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 「程序拥有控制流」范式 | **sse_protocols / 快环 FSL 结构定义**（C2 参照：控制流写代码，语言退到叶） |
| DAG 上下文作用域规则（祖先链全量 + 已返回塌缩为摘要） | **快环上下文有界化（C4）** + harness 级 replay 存储（C5） |
| `@agentic` 装饰器（签名+docstring→prompt，typed return） | **慢环 LLM 调用接口规范化**：叶调用必须返回结构化值 |
| Algorithm 1（提案→测试→commit as code） | **Gene Manager / RuleCompiler 的「代码固化」形态（C7/C8）** |
| 「pin LLM reply + 对外层函数确定性断言」 | **回归门的具体化装置**（债务 25–28 的判据形状） |
| 「失败定位到命名调用的返回值」 | **判据形状**（债务 26/27/28：不再靠 transcript 中某一轮） |
| 反模式清单（App.A 八类补丁） | **风险对照**：逐条说明「不移动控制权」的补丁为何无效 |

### 3.4 债务与验收实验对应

- **可回应的已知债务**：
  - **债务 25/26/27/28（判据形状错、环境对无消费者通道报成功、技能失效被判成功）**：本篇给出两条
    干净范式——**(a)「失败定位到命名调用的返回值」**（不是 transcript 中某一轮）；**(b)「单元测试
    pin 住 LLM 回复、对外层函数输出做确定性断言」**（§3.4 p4）。「控制流由代码拥有 → **该跑的步骤必跑**」
    正面回应债务 27（成功不再由模型「声称」，而由程序保证步骤执行）。
  - **「技能表示够不够」（0/33 之后仍未回答）**：本篇把**技能=可执行函数**，给出技能的最小可验证
    单位——技能失效即**函数测试失败**、可定位（§3.4）。
  - **Gene Manager 缺失**：**durable code commit** 是 GenePackage 载体的最小形态（代码可打包、可版本化）。
  - **睡眠期计算预算未定义**：DAG 上下文 **O(depth)** 有界化**间接**降低慢环预算压力（非直接）。
  - **`retrieve` 键收窄 / 记忆门选择性**：**未回应**（无检索机制）。
- **可服务的验收实验**：为**实验 4/5（架构变异与淘汰、基因继承）**提供「改进=可执行代码 + 测试门」
  的**载体与接受判据**；为「技能表示」提供函数级可验证单位。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **DAG 上下文作用域规则**（祖先链全量 + 已返回子树塌缩为一行摘要） | 表示/算法 | **改造移植** | 快环上下文 / 记忆有界化 | C4 缓冲不无界增长；replay 历史 | 高 |
| 2 | **「程序拥有控制流、LLM 只在叶」的范式**（+确定性 vs 概率性分层论证） | 思想/形式化 | 改造移植 | sse_protocols / 快环结构 | C2：语言退到观察面 | 高 |
| 3 | **Algorithm 1：提案→测试→commit as code**（唯一采样步是提案，接受判据确定性） | 算法/协议 | **改造移植** | Gene Manager / RuleCompiler | C7/C8 代码固化载体 | 高 |
| 4 | **「pin LLM reply + 对外层函数确定性断言」** | 工程实现 | **直接移植** | 回归门 | 债务 25–28 判据形状 | 高 |
| 5 | **「失败定位到命名调用的返回值」** | 思想 | 直接引用 | 判据 / 故障定位 | 债务 26/27/28 | 高 |
| 6 | **`@agentic` 装饰器**（签名+docstring→prompt，typed return） | 工程实现 | 改造移植 | 慢环 LLM 调用接口 | 叶调用必须返回结构化值 | 中 |
| 7 | **harness 级全图保留（replay/debug）** | 表示 | 改造移植 | 慢环重放 / 记忆存储 | 完整历史可回放（C5） | 中 |
| 8 | **反模式清单（App.A 八类补丁逐条驳斥）** | 证据/清单 | 仅借思想 | 设计评审 / 风险对照 | 「不移动控制权」的补丁为何无效 | 高 |
| 9 | **多 agent = 调用图 + 类型化返回 + 程序化 join** | 思想/协议 | 仅借思想 | 未来多子代理扩展 | 协调不靠监督模型 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C1 冲突**：目标是 SE 任务成功而非生存；无淘汰闭环。→ 执行环换生存控制环。
  - **C2 残余冲突**：LLM 在**执行期（叶）内联调用**做语言判断（§3.1、§3.3）；SSEA 快环要求**运行期零语言**。
    → 把叶调用移入慢环编译面；叶调用只返回结构化值。
  - **C8 冲突**：`@agentic` 的 docstring/prompt 携带任务知识（App.C）。→ 基因只放控制流骨架。
  - **C9 冲突**：实证主张依赖 **OSWorld 外部 benchmark 分数**。→ 只取「测试即接受判据」，去掉分数驱动。
- **隐含假设与失效条件**：① 工作流**存在可写出的已知结构**（论文自陈：完全探索性任务不适用，p4）；
  ② 叶调用返回**可解析的类型化值**；③ 能写出**可判定**的测试。若三者不成立（SSEA 生存域中生存判据
  不是单元测试），本篇的「测试门」直接失效。
- **算力 / 带宽 / 工程代价**：机制本身廉价（装饰器 + 作用域规则 + 测试门），但**把工作流预先写成代码
  需人力/工程**；对无结构任务退化回 LLM 编排。
- **搬运后的可能退化模式**（若失败，会以什么形式失败）：
  1. **叶 LLM 调用留在快环** → 快环仍含语言采样，C2 名义满足、实质破；表现为控制流虽在代码、
     但每个叶仍是不可保证的采样。
  2. **把 docstring/prompt 当基因** → C8 破；表现为基因包膨胀、知识跨代污染。
  3. **只搬 DAG 上下文而漏「返回即塌缩为摘要」** → 上下文仍随步数增长，C4 失效。
  4. **测试门写不出**（生存判据非单元测试）→ 自我演化无接受闸，退化为 Gödel 式无闸自改。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 「工作流有已知结构」+ 可判定测试 | 无这两样，范式退化（作者自陈 p4） |
| **互补（最紧）** | **HarnessDev**（B/P1） | HarnessDev 给「LLM 造/演化 harness」的**实测失败模式**（反馈涨/held-out 跌、死代码、executor 适配）；LLM-as-Code 给 harness 的**表示范式**（程序拥有控制流）+「代码固化 + 测试门」。**表示 × 验收**互锁。HarnessDev 卡片 §6.1 已点名本篇为同族 |
| **互补（次紧）** | **Ouroboros**（A/P1） | Ouroboros 提供**受审提交 + 受保护宪法核**（边界权 + 审计链）；LLM-as-Code 提供「改什么（程序/harness 代码）」与「改完怎么固化（commit as code + tests）」。**Ouroboros 卡片 §9 已点名本篇为待补的缺失兄弟** |
| **同题·自指对照** | **Gödel Agent**（B/P1） | Gödel 是**运行时无闸**的自指猴子补丁；本篇 Algorithm 1 是**有测试闸**的代码固化版本，是 Gödel 缺失验证门的直接补丁 |
| **同题·对照** | **ADAS**（B/P2） | ADAS 用**外部搜索**在代码空间找智能体（元体固定）；本篇主张**程序拥有控制流**（结构写死、不搜索）。ADAS=「搜架构」，本篇=「架构应是代码」——两条 L4 路线 |
| **技能侧·对照** | **Voyager**（B/P2）、**PSN**（A/P1） | 本篇「技能=可执行函数 + 测试接受」是二者技能表示的**最小形式**；PSN 的**契约/成熟度门控/回滚**补本篇缺的边界权与恢复。Voyager 的键/值代码技能库是其前身 |
| **工具制造族** | **LLM Agents Making Agent Tools**（未建卡） | 同属「让 LLM 造可执行工具/代码」；区别：本篇关心**控制流归属**（工具住在程序里、由程序决定调用序），工具制造族关心**工具的生产**。二者互补：生产 × 编排 |
| **动作表示族** | **CodeAct**（ref[17]） | 论文自陈：CodeAct 让**每步是代码动作**；本篇让**程序拥有步骤序列**——「code 不只是 LLM 的动作，还应拥有 LLM 在其中行动的循环」（App.A p6） |
| **图式编排族** | **LangGraph**（ref[2]）、**DSPy**（ref[9]） | LangGraph：**预声明**图 + 共享 state vs 本篇**运行时展开**调用图 + 栈回退；DSPy：优化**图内每调用** vs 本篇问**谁固定图**（App.A p6） |
| **经典形状** | **ReAct**（ref[22]）、**Reflexion**（ref[15]） | 论文称二者只降**单步**错误率、控制仍采样（App.A p6）；与已有卡片 Reflexion（B/P2）对照 |
| 训练侧 | RAGEN（B/P1） | 若未来以训练组件替代叶 LLM 调用，RAGEN 接手稳定性 |

### 6.2 推荐组合方案

1. **harness 演化全栈（LLM-as-Code × HarnessDev × Ouroboros）**
   - 形态：**表示**（程序拥有控制流、DAG 上下文、改进 commit as code）→ **验收**（held-out 分离、
     反馈一致性、死代码率）→ **门**（受审提交 + 受保护宪法核 + 指纹）。
   - 新增能力：从「怎么写 harness」到「改完怎么审、怎么上线」的完整链。
   - 新增风险：三套判据口径需先统一「成功」定义。
2. **技能固化（LLM-as-Code × PSN × Voyager）**
   - 形态：技能=带测试的可执行函数；契约/成熟度门控/回滚由 PSN 提供；代码固化由本篇提供。
   - 新增能力：技能表示的最小可验证单位 + 演化安全闸。
3. **重放预筛（LLM-as-Code × Dream-RSI）**
   - 形态：harness 级全图保留（本篇）正好给重放模拟器一个**现成的历史表示**；变体先在重放中跑测试门。
   - 新增能力：廉价离线验证 + 真实环境实测。

### 6.3 本篇在组合中的典型角色

- **L2 信息流层的「表示范式」供给方 / C2 的英文形式化参照**：管「**控制流写在哪**、上下文如何随调用图
  有界、改进如何固化成代码」。它不提供演化安全（Ouroboros）、不提供验收基准（HarnessDev）、
  不提供技能维护（PSN），只提供**「控制权归程序」这一条分界线**与它的两个可搬零件。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 直击 SSEA 的 C2/C4/C7 命题（控制流归属、上下文有界、代码固化）（实测于原文设定） |
| 立场兼容性 | **3** | C2/C4/C10 强对齐；C1 ✗、C8/C9 需改造、C2 有「叶内联语言」残余（实测 + 推断） |
| 可搬运性 | **4** | DAG 上下文规则、`@agentic` 装饰器、Algorithm 1 均为**协议级、干净可拆**（推断）；无开源代码 |
| 证据强度 | **2** | 7 页 workshop position 论文；**单一 benchmark（OSWorld）案例**；**无 seed/消融/held-out/误差棒**；基线取自公共榜单、口径不齐（实测） |
| 组合价值 | **4** | 与 HarnessDev/Ouroboros/Gödel/ADAS/PSN/Voyager/工具制造族多点互补（推断） |
| 落地成本 | **4** | 机制廉价（装饰器 + 作用域规则 + 测试门）；主要成本是把工作流**预先写成代码**（推断） |

---

## 8. 裁决与下一步

- **应用等级：A 核心借鉴** —— 理由：它是 **C2 最干净的英文形式化**（控制流=代码、语言退到叶），
  且提供**两个可直接搬运的 L2 零件**（DAG 上下文作用域规则、Algorithm 1 代码固化 + 测试门），
  并补上 harness 演化族缺失的**表示层**。**不采纳**：① 叶 LLM 内联调用（快环须零语言）；
  ② benchmark 分数驱动（违 C9）；③ docstring/prompt 作为基因（违 C8）。
  ——A 的落脚点是**范式与 L2 零件**，**不是其证据**（证据强度仅 2）。
- **优先级：P1**——C2 的表述与快环上下文有界化是 SSEA 当前结构性命题，零件可立即用。
- **建议动作**：
  1. 在 `sse_protocols` 用「确定性 vs 概率性分层」重述快环 FSL：**控制流=代码，叶调用只返回结构化值**；
  2. 实现 **DAG 上下文作用域规则**（祖先链全量 + 已返回塌缩为摘要），作为快环上下文有界化的候选；
  3. 把 **Algorithm 1（提案→测试→commit as code）** 作为 Gene Manager / RuleCompiler 的代码固化形态；
  4. 用 **「pin LLM reply + 对外层函数确定性断言」** 重写回归门判据，逐条对照债务 25–28；
  5. 明确 **C8 边界**：只有控制流骨架进基因，docstring/prompt 不进。
- **最小验证实验**：
  - **双臂 / 消融设置**：SSEA 任务上——**A 臂**=LLM-as-Orchestrator（ReAct 式，模型决定控制流）；
    **B 臂**=LLM-as-Code（程序拥有控制流，LLM 只在叶）。同任务、同模型、≥8 seed。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：
    ①**机制计数**：应跑步骤的**实际执行率**（分母=规定步骤数）、上下文长度随步数曲线、token 用量；
    ②**行为差**：长时程任务完成率、**控制流幻觉率**（在验证前声称完成的比例）；
    ③**淘汰结果**（模型外）：存活/任务成败。
  - **预期与证伪条件**：预期 B 臂长时程更稳、token 随步数**近似平坦**（O(depth)），A 臂 token 随步数
    线性增长、幻觉率随步数上升。**证伪**：若 B 臂相对 A 臂在 SSEA 生存域**无差异**，则「程序拥有控制流」
    在此域不成立（可能因生存任务本身高度探索性，恰是作者自陈不适用的情形，p4）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 快环**是否允许任何内联 LLM 调用**？（本篇叶调用在执行期；SSEA C2 要求快环零语言）——
     这是快环/慢环边界的第一决策。
  2. 「程序拥有控制流」的代码骨架能否进 GenePackage 而 docstring/prompt 不进（C8 边界的精确切法）？
  3. 生存域的**接受判据**如何写？生存判据不是单元测试——本篇的测试门在 SSEA 需换成什么？
- **需补查的文献或资料**：
  4. 论文**未给代码仓库**——参考实现（`@agentic` 装饰器 + 运行时）是否公开？
  5. 「自主过夜研究流水线」**未给任何数字**（§E p7），其可靠性证据缺失，需核实。
  6. **LLM Agents Making Agent Tools**、**Live-SWE-agent**、**AgentEvolver** 未建卡，需补齐后做
     harness 演化族组合分析（Ouroboros 卡片 §9 亦提出此点）。
- **需人工核对的公式 / 实现**：
  7. Algorithm 1 正文称「唯一采样步是 **line 6**（提案 f′）」而算法伪码中提案在 **line 5**、
     接受检查在 **line 7**、提交在 **line 8**（App.D p7）——**行号引用与伪码编号不一致**，需核对。
  8. Table 1/2 的基线取自公共榜单（accessed 2026-06-02）且**基线 100 步 vs Ours 15 步**，
     口径不齐；「86.8 vs 80.4」是否可直接比较需核对。
  9. 「DAG 上下文 O(depth)」的**摘要压缩质量**对下游正确性的影响，论文未量化。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “the program governs all control flow, and the LLM is itself part of it, an adaptive component we call **LLM-as-Code** and invoke only where a task calls for reasoning or generation.” | p1 Abstract |
| “token explosion, control-flow hallucination, and unreliable completion are **not implementation bugs but architectural consequences** of assigning the deterministic work of looping, branching, and sequencing to a probabilistic system.” | p1 Abstract |
| “asking an LLM to decide ‘what to do next’ is **sampling a control-flow edge from a probability distribution**.” | p2 §2.1 |
| “the only construction that guarantees a loop executes 𝑛 times is **to write the loop**.” | p2 §2.1 |
| “a for loop runs 𝑛 times because the language runtime guarantees it … The rest of the workflow is not begged from the model; it is **executed**.” | p2 §2.2 |
| Fig.1：LLM-as-Orchestrator 重取 url1、漏 url5、早停 vs LLM-as-Code `for url in urls:` 恰跑 8 次 | p3 Fig.1 |
| “A call sees the **full context of its entire ancestor chain**, while each frame keeps only a **summary of the children that have already returned**.” | p3 §3.2 |
| “Input length is therefore bounded by the current depth, **𝑂(depth)**, not by the total number of steps run, 𝑂(steps).” | p4 §3.2 |
| “the **full DAG is retained at the harness level for replay and debugging**, even though no node ever sees all of it.” | p4 §3.2 |
| “the interface between agents is a **typed return value** rather than a free-form conversation, so a failed agent is a failed call.” | p4 §3.3 |
| “Proposing a new function is a probabilistic LLM call, but the result is **committed as code** (accepted only once it passes the caller’s tests) and thereafter runs like any other **guaranteed step**.” | p4 §3.4 |
| “a unit test can **pin an LLM reply** and assert deterministically on the enclosing function’s output … a failure localizes to a **named call’s return value** rather than a single turn within a fifty-step transcript.” | p4 §3.4 |
| “Fully exploratory tasks with no known structure … may benefit from LLM-driven orchestration, **which we do not contest**.” | p4 §3.4 |
| Table 1：Ours **86.8**（15 步）vs Holo3-35B-A3B 80.4 / OpenAPA 78.3 / Claude Sonnet 4.6 72.1（均 100 步） | p5 Table 1 |
| “code should not only be **the LLM’s action**, it should **own the loop the LLM acts within**.”（对 CodeAct 的区别） | p6 App.A |
| LangGraph：图**预声明** + 共享 state vs 本篇**运行时展开**调用图 + 栈回退；DSPy：优化图内每调用 vs 本篇问「谁固定图」 | p6 App.A |
| Algorithm 1：line 5 `f′ ← g(f, tests)`（唯一采样步）；line 7 确定性接受检查；line 8 `f ← f′` commit as code | p7 App.D |
| Table 2：Ours **Chrome 93.5 / Multi-Apps 80.0 / OS 100.0 / Overall 86.8**（15 步）；最强先前系统 Holo3-35B-A3B 80.4 | p7 App.E |
| “Each agent’s top-level loop fits in roughly **150 lines of Python**.”（两个生产 agent：GUI 自动化 + 过夜研究流水线） | p7 App.E |
