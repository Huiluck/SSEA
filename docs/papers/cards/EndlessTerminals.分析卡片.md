# 论文分析卡片 · Endless Terminals

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-01-23 Endless Terminals Scaling RL Environments for Terminal Agents.pdf` |
| 标题 | **Endless Terminals: Scaling RL Environments for Terminal Agents** |
| 作者 / 机构 | Kanishk Gandhi\*（Stanford University）、Shivam Garg（Microsoft Research）、Noah D. Goodman（Stanford University）、Dimitris Papailiopoulos（Microsoft Research / UW-Madison）；\* 标注「部分工作于 MSR 暑期实习期间完成」 |
| 发表时间 / 出处 | arXiv:2601.16443**v3** [cs.LG]，2026-02-14；PDF 页眉标注 Preprint（文件名日期 2026-01-23）；11 页 |
| 论文链接 | arXiv:2601.16443 |
| 代码链接 | **有**：https://github.com/kanishkg/endless-terminals（p1 脚注 1） |
| 标签 | 环境规模化 · 程序化任务合成（procedural generation）· 终端/命令行域 · 容器化环境（Apptainer/Docker）· 隐藏真值（privileged ground truth）· 完成测试（completion tests）· 可解性过滤（pass@16）· 二元回合奖励 · vanilla PPO · 最小 scaffold |
| **应用裁决** | **B 零件采用**（搬「**四阶段无人工环境合成管线**」+「**隐藏真值 + 环境侧确定性完成测试**」+「初始状态前置测试」+「迭代构建-修复回路」+「可解性过滤门」+「容器定义即环境包」；**不搬** LLM 策略本体、PPO 二元奖励回路、固定前沿模型（o3）作难度标尺） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：提出 Endless Terminals——一条**完全自主、无人工标注、无蒸馏**的**四阶段程序化管线**（① 跨「类别 × 复杂度 × 场景」采样生成任务描述 + **隐藏真值**；② 生成容器定义并用**自写前置测试**迭代验证（最多 k=3 轮）；③ 生成**完成测试**校验期望终态；④ 用强模型（**o3**）采样 **n=16** 个解做**可解性过滤**），产出 **3255 个可验证终端任务**；用**vanilla PPO + 二元回合奖励 + 最小 scaffold（无检索/无工具/无多智能体）**训练三个 3B–8B 模型，在自建 dev 集与**人类策展**的 TerminalBench 2.0 上均取得提升，主张「**环境规模化后，简单 RL 就能成功**」（p1 摘要、p4 §3、p6 §5）。
- **对 SSEA 的意义**：它给出了 SSEA 目前最缺的那一类供给——**可批量、无人工、判定确定性、且判定归环境**的**淘汰压力来源**：完成测试在容器内执行、检查文件/进程/配置的**最终状态**，且**隐藏真值从不暴露给被考智能体**，这正是 **C9 第一层「淘汰函数归环境、模型碰不到」的近乎教科书形态**；若采用，SSEA 的第四级「环境实测」门可从「手写 6 通道、`skill` 通道无消费者」升级为「程序化供给的可验证环境族」，但必须把「二元奖励」剥离为**只判通过/淘汰**，并自行补装**判别力校准**（本篇不提供）与**难度标尺去前沿模型依赖**（本篇的 o3 天花板是硬限制）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：RL「渴望环境」。数学推理与代码生成的进展依赖**大量、多样、自动可验证**的任务，但**多轮终端/计算机操作任务**没有可规模化的环境——人工策展昂贵，现有 benchmark **至多数百个任务**，远不足以支撑稳健 RL 训练（p2 Introduction）。
- **它指出的既有方案缺陷**（p2）：
  1. **把固定评测 benchmark 挪作训练**：有**过拟合到窄任务分布**的风险；
  2. **从更强专有模型蒸馏**（SFT）：继承教师模型的**能力天花板**，且需要昂贵 API 访问；
  3. **人工策展的 coding/shell 数据集**（Team 2025a；Lin et al. 2018 = NL2Bash）：**标注成本限制规模与多样性**。
  → 「仍然缺失的是一条**完全自主**的管线，能生成**无尽流**的终端任务：含初始环境、任务规格与验证测试，且人工监督最小」（p2）。
- **对最近邻的批评**（p3 Related Work「Synthetic Environment Generation」）：**SWEGym**（Pan et al. 2024，2438 个带可执行测试的 Python 任务）**依赖既有 GitHub issues，而非程序化生成**；**OpenThoughts Agent**（Team 2025a）最近，但其 RL 数据集的 query/command **来自人工生成的 NL2Bash**，且**在 TerminalBench 2.0 上无增益、也无自主生成的 dev 集**。

### 2.2 核心思想（关键 insight，1–3 条）
1. **「无尽流」而非「数据集」**：环境的瓶颈是**管线（pipeline）而非数据（dataset）**——「RL 需要的是一条可规模化的管线，而不只是一个数据集」（p1 摘要）。四个阶段**逐级自动验证**，失败任务自动丢弃、可并行处理（p4 §3）。
2. **可验证性来自「隐藏真值 + 环境侧确定性终态测试」**：Phase I 同时产出 `<task>`（给智能体看的规格）与 `<truth>`（**特权真值**：精确文件内容/路径/期望状态，**永不暴露给被考智能体**，p3 Fig.2、p4 §3）；Phase III 据此生成**完成测试**，且**显式验证该测试在初始状态下不通过**（防 trivial 通过，p4 §3）。
3. **难度由「强模型可解性」定义，而非人工难度表**：Phase IV 用 o3 采样 16 个解，**保留 pass@16>0 的任务**、丢弃其余（约一半候选被丢弃，p5 §5、p8 §6）；由此得到一个**有难度分布的**任务集——「约一半任务被全部 16 次尝试解出，其余跨越一系列难度」（p5 §5、Fig.6 右）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| **四阶段管线** | 采样提示（类别×复杂度×场景）→ 3255 个可验证任务 | 无人工、可并行、失败自动丢弃 | §3 p4；Fig.2 p3 |
| **Phase I 任务描述生成** | 随机采样的 `{category}`、`{complexity}`、`{context}` → `<task>`（规格）+ `<truth>`（**隐藏特权真值**） | 保证多样性 + 供自动验证 | Fig.2 p3；§3 p4 |
| **Phase II 容器构建 + 前置测试** | 任务描述 + 真值 → 容器定义文件（Apptainer/Dockerfile）+ **初始状态测试**（校验前置文件/目录/进程/仓库） | 环境可建、可复现 | Fig.2 p3；§3 p4 |
| **迭代构建-修复回路** | 构建失败输出 → 反馈给模型修正；**最多 k=3 轮**或直到测试通过 | 自动修复容器 | §3 p4 |
| **Phase III 完成测试生成** | 任务描述 + 真值 + 初始测试 → **终态测试**（文件内容/配置/计算结果） | 判定任务完成 | Fig.2 p3；§3 p4 |
| **完成测试的元验证** | 完成测试在**初始状态**下运行 → **必须不通过** | 防「trivial 通过」（判据自检） | §3 p4 |
| **Phase IV 可解性过滤** | **o3** 的 **n=16** 次交互式求解 → 保留 pass@16>0 | 剔除欠规格/不可解任务，确认可解 | §3 p4；§5 p5；Fig.6 右 p7 |
| **最小交互协议** | 模型输出 `<command>...</command>` 或 `<command>done</command>` | 单命令/回合，非交互式 flag | §4 p4–5 |
| **持久 shell 环境** | Apptainer 持久 PTY / Docker(harbor) 会话 → 跨回合保留**文件系统状态、环境变量、运行进程** | 有状态、多轮 | §4 p5 |
| **结构化观测** | 命令执行 → `(成功/失败标志, stdout+stderr, exit code)` 追加为下一条 user 消息 | 控制环友好的观测形状 | §4 p5 |
| **回合终止条件** | done / 最大回合数（训练 16）/ 最大 token（训练 16k）/ 5 分钟环境超时 | 预算封顶 | §4 p5；§5 p6 |
| **二元回合奖励** | 终局完成测试通过 → 1，否则 0，**无中间奖励** | PPO 信号 | §5 p6 |
| **vanilla PPO** | 每 prompt 16 rollouts、≤16 回合、每回合 ≤2048 tokens、总 16k 上下文；ε_low=0.2、ε_high=0.28、**无 KL 惩罚** | 参数更新 | §5 p6 |
| **失败模式诊断** | 失败轨迹 → loop 失败 / 回合耗尽 / 早停 | 诊断旋钮 | §5 p7–8；Fig.5 p7 |
| **命令多样性度量** | 首次错误后「唯一命令数/总命令数」→ 成功 0.49 vs 循环失败 0.18 | 行为诊断指标 | §5 p8 |

### 2.4 关键表示与数据结构
- **任务二元组**：`<task>`（自然语言规格，写成像用户会问 AI 助手的形式，**不给命令**，智能体须自行推断解法）+ `<truth>`（特权真值：精确文件内容、路径、期望状态；**永不进入智能体上下文**）（p3 Fig.2、p4 §3）。
- **环境包**：**容器定义文件**（Apptainer definition / Dockerfile）+ **初始状态测试文件** + **完成测试文件**——三者构成可构建、可复现、可版本化的环境单元（p4 §3；Fig.2 p3）。
- **容器实例**：持久 shell 会话（Apptainer PTY / Docker harbor），跨回合保留文件系统、环境变量、进程；观测 = `(success/fail, stdout+stderr, exit code)`（p5 §4）。
- **交互协议**：`<command>…</command>` / `<command>done</command>`；允许命令前任意推理文本，推理**进入后续上下文**（p4–5 §4）。
- **数据集构成**（p5 §5、Fig.4）：3255 个 Apptainer 任务（约 2500 个另转 Harbor 格式）；类别含**文件操作（最大类）、日志管理、数据处理、文本处理、脚本、归档压缩、数据库操作**；解法长度多在 1000–4000 字符、长尾 >10000 字符（Fig.6 左 p7）。
- **规模统计**：**3255** 任务；可解性过滤**丢弃约一半**候选（p5 §5、p8 §6）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **自建 dev 集**（held-out） | 各基座模型自身 | Llama-3.2-3B **4.0% → 18.2%**；Qwen2.5-7B **10.7% → 53.3%**；Qwen3-8B-openthinker-sft **42.6% → 59.0%** | pass 率（%）；**未给 seed 数 / 方差（未提及）** |
| **TerminalBench 2.0**（人类策展，未见） | 各基座 + 其他微调变体（含 OpenThoughts-Agent RL 配方、Terminus-2 scaffold） | Llama-3.2-3B **0.0% → 2.2%**；Qwen2.5-7B **2.2% → 3.4%**；Qwen3-8B-open-thoughts-sft **1.1% → 6.7%**；**本方法结果对 5 次运行取平均** | pass 率（%）；本方法 5 runs 平均（p6 Fig.3 注） |
| **OpenThinker dev 集** | 同上 | 0.0→1.0 / 3.9→8.5 / 9.7→10.2（增益较小，含通用软件工程任务） | pass 率（%）；未给 seed |
| **难度分层**（TerminalBench 2.0，pass@5） | — | easy **25% (1/4)**、medium **14.5% (8/55)**、hard **10% (3/30)** | pass@5（5 次尝试至少 1 次成功）；n 已给 |
| **类别分层**（pass@5） | — | SWE **6/26**、data-science 1/8、optimization 1/2、scientific-computing 1/8、sysadmin 1/9、data-processing 1/4、security 1/8；**math 0/4、ML 0/3、model-training 0/4** | 分子/分母已给 |
| **失败模式**（最强模型在 TB2.0 全零任务） | — | **loop 失败 39%（30 任务）**、**回合耗尽 26%（20 任务）**、两者重叠 11 任务、**其余 49% 早停于错误解** | 占比 + 任务数（n=77 失败任务，推断） |
| **命令多样性** | — | 成功任务 **0.49** vs 循环失败 **0.18**（首次错误后唯一命令/总命令） | 均值 |
| **参考点（非本方法）** | — | Claude Sonnet 4.5 + Terminus-2：**42.8%**（200 回合 + agentic scaffold）vs 本方法 **6.7%**（64 回合、无 scaffold） | 单值 |

### 2.6 论文自陈局限与边界条件
- **论文有明确的局限性讨论**（§6 Discussion p9，共三条，本卡摘录）：
  1. **任务过于「竞赛编程化」**：「程序化生成的任务更**像竞赛编程题**，而不像用户实际提出的**混乱、欠规格**的请求」——真实终端使用含**歧义目标、隐含上下文、需要澄清提问**，这些在**不牺牲可验证性**的前提下难以自动生成（p9）。
  2. **可解性过滤引入能力天花板**：过滤用 **o3 pass@16**，保留「至少一解成功」者，**丢弃约一半候选**；它同时**丢弃了超出 o3 能力的任务** →「**管线无法生成超出前沿模型能力的任务**」；依赖固定前沿验证器**限制了在真正新问题上训练智能体的能力**；作者建议**self-play**（模型迭代生成「略超出当前能力」的任务）以**自适应地扩难度**（p9）。
  3. **人工介入会牺牲可扩展性**：加人工验证或自然主义描述能提升质量与多样性，但**增加成本、降低可扩展性**（p9）。
  - 其余作者点名的未来方向：更丰富的 agentic scaffold、**部分奖励**（按通过测试数而非二元）、**学习终端动力学世界模型 / 经验模型**以做想象 rollout（p9）。
- **假设依赖**（推断，论文未逐条自陈）：
  - 环境必须是**容器 + shell + 文件/进程状态**形状，且任务终态**可被确定性测试判定** → 对无终态、连续动力学、主观/歧义目标不适用；
  - 验证正确性依赖**测试生成正确**（若完成测试有 bug，会把环境失败记到智能体账上）；
  - 难度刻度依赖**o3 的可解性**（换验证器则难度分布变，p9 自陈）。
- **明确不适用的情形**（推断）：生存域（无死亡/资源约束）、连续控制、非结构化对话目标；SSEA 毫秒级快环（见 §5）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **◐** | **同向的一半**：观测被显式结构化为 `(成功/失败标志, stdout+stderr, exit code)`（p5 §4），状态外置于**容器文件系统/进程**，动作是**确定性 shell 命令**——是控制环友好的形状。**冲突的一半**：被训练智能体是 LLM、域是终端生产力任务（文件操作/日志/数据库，p5 Fig.4），**非生存域**，且推理文本进上下文（p4 §4） | 只搬**环境骨架 + 判据形状**（终态事实、结构化观测、确定性动作）；状态量重定义为生存相关量（能量/危险/资源），shell 命令语义换成生存动作；不搬 LLM 策略与终端域语义 |
| **C2** 自然语言只作观察员接口 | **◐（分层判定）** | **离线合成侧 ✓（不违规）**：LLM 只出现在**建造期**（四阶段生成任务/容器/测试，p3–4 §3），产物是**容器定义与可执行测试**；**判据锚点在编译期**。**在线控制环 ✗**：模型输出的是 `<command>` 且**允许命令前任意推理文本，推理进入后续上下文供模型引用**（p4–5 §4）——语言**直接进环** | **只搬离线合成管线，不搬在线推理形态**。切勿笼统判 ✗：环境合成（编译期语言）不构成 C2 违规；违规的是「推理文本作为控制环内部状态」这一在线形态。SSEA 侧语言只能出现在日志/解释面 |
| **C3** 权重/记忆/技能三分离 | **◐** | 环境（容器定义 + 测试）完全在模型之外、可独立构建与版本化（p4 §3）；但论文**不涉及记忆与技能**语义（无检索/写入/遗忘；上下文超限时把历史折叠进首条 user 消息，属上下文管理而非记忆，p6 §5） | 环境侧可安全外置并版本化；记忆/技能分离仍按 Memento/FLEX/PSN 路线 |
| **C4** 低算力低带宽 | **◐（分层）** | **环境运行侧 ◐**：单步是 shell 命令 + 容器内测试，**逻辑成本低**，但需容器基础设施（Apptainer/Docker，p5 §4）。**合成侧 ✗**：Phase IV 每个候选任务需 **o3 × 16 次交互式求解**，且约**一半候选被丢弃** → 为得 3255 任务需生成并求解 **>6500** 个候选（p5 §5、p8 §6）。**训练侧 ✗**：PPO on 3B–8B，4×A100 约 2 天 / 8×B200 约 8 小时（p6 §5） | 环境运行侧可用（低成本）；合成侧**离线一次性、可摊销**；PPO 训练不进 SSEA；Phase IV 的 o3 采样须替换为**结构化难度度量**（见 C9 行） |
| **C5** 精准回忆历史 | **—** | 论文不涉及记忆机制（无检索/写入/遗忘/合并）；仅有上下文折叠（超限时把历史命令追加到首条 user 消息，p6 §5） | 可反向利用：**容器文件系统/进程是确定性外部事实源**，可作记忆写入正确性的对照面（同 ScaleEnv 的 `s^env`） |
| **C6** 可自主修改自身 | **◐** | 只覆盖四权中的**参数面应用权**（PPO 更新 `π_θ`，p6 §5）；提案权在外部合成管线、验证权在完成测试、**边界权无**（无禁止修改区） | 借「验证权外置到可执行判据」的形状；SSEA 仍需自建提案/边界/验证/应用四权拆分 |
| **C7** 保存/恢复/变异/继承 | **◐** | **保存/恢复 ✓（强）**：环境 = **容器定义文件（Apptainer/Dockerfile）+ 测试文件**（p4 §3）→ 天然**可构建、可复现、可 git 版本化、可快照**——这是 GenePackage 最需要的性质，且比 ScaleEnv 的「代码 + DB」更贴近 SSEA 的「可执行环境包」。**变异 ◐**：Phase I 的「类别 × 复杂度 × 场景」采样是**环境侧内容变异算子**（p4 §3）。**继承/淘汰 ✗**：无 GenePackage、无代际、无淘汰-繁衍闭环 | 把「**环境包 = 容器定义 + 前置测试 + 完成测试 + 版本号**」定为 SSEA 的环境包契约，与 GenePackage 版本配对；把「类别×复杂度×场景」采样登记为**环境侧变异算子**；继承/淘汰仍由 Gene Manager 承担（**当前缺失**） |
| **C8** 给基因先验，不给知识语料 | **◐** | 「知识留在环境（文件/配置/进程）、策略只学交互逻辑」方向同向；但基座是预训练 LLM，且 Qwen3-8B-openthinker-sft 先在 **15000 条蒸馏轨迹**（NL2Bash + InferredBugs，来自 GLM-4.6）上 SFT（p6 §5）→ **知识确在模型内**；环境内容由 LLM 合成而非真实数据源 | 可作「知识外置到环境」的样板；SSEA 侧应提高环境内容的事实性门槛（或改接真实数据源，见 Agent-World 式挖库） |
| **C9** 不设评分函数，只有淘汰函数 | **◐（环境合成族里最贴近 C9 第一层的一件）** | **同向（强）**：判定是**环境侧、确定性、终局**的事实检查——完成测试在**容器内**执行，检查**文件/目录/进程/配置/计算结果**的终态（p4 §3）；**特权真值 `<truth>` 永不暴露给被考智能体**（p3 Fig.2、p4 §3）；**无 LLM-as-judge**、**无 NL 用户模拟器**、**无「被测者失败→环境难度」反馈通道**。→ 这正是「**淘汰函数归环境（模型碰不到）**」的工程形态。**冲突**：① 该完成测试的结果被用作 **PPO 的二元回合奖励（1/0）**，进入优势估计做**排序与塑形**（p6 §5），违反「验证门只判合法性、不打分、不排序」；② Phase IV 的**可解性过滤以 o3 为难度标尺**（pass@16>0，p8 §6），难度刻度**绑定在一个前沿模型**上——虽不直接进 SSEA 判据，但若照搬会引入**模型依赖的难度定义** | 见 §5.1 两步剥离：把完成测试**降为环境侧终局淘汰/合法性门**（四级门第四级），只输出「**通过 / 淘汰**」二值；**二元奖励绝不进优势估计/奖励塑形/排序**；Phase IV 的 o3 过滤**只作任务有效性门**（保证可解），**不作难度标尺**——难度改用**结构量**（ScaleEnv `c(H_n)` 式）或 **GenEnv α 带**标定 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | L1 全借用（PPO、容器/Apptainer/Docker、LLM 生成、XML 协议）；创新在**环境合成管线**（L2/L4）与**任务验证协议**（L2） | 无冲突 |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层**（基础网络模块） | 无新算子（PPO / 容器 / LLM / XML 均借用） | 无（符合 C10） |
| **L2 信息流层**（模块如何连接） | **环境-智能体接口形状**：持久 shell（保留文件系统/环境变量/进程）+ 结构化观测 `(成功标志, stdout+stderr, exit code)` + 单命令/回合协议 + **隐藏真值**（p4–5 §4、p3 Fig.2）；以及**四阶段合成管线的信息流**（任务描述 → 容器 → 测试 → 过滤） | **高**：可直接定为 SSEA 环境包与 Action 通道的**通道契约**（回应债务 26/27），以及**淘汰判据的「隐藏真值」形状** |
| **L3 学习层**（如何更新自身） | 仅参数面（vanilla PPO）；无自修改、无技能固化 | 低-中：SSEA 须经四级门，不直接搬 |
| **L4 演化层**（保存/继承/变异） | **无人工环境生成管线**（四阶段，失败自动丢弃、可并行，p4 §3）+ **环境侧内容变异算子**（类别×复杂度×场景采样）+ **可解性过滤门** | **中-高**：提供「**可规模化的淘汰压力来源**」的实测证据（3255 任务、跨 3 模型提升、迁移到人类策展 benchmark）；但**无遗传/淘汰语义**，且难度天花板受前沿模型限制 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **四阶段合成管线（Phase I–IV）** | **新增：环境供给工厂**（回应「环境是手写的、通道封闭」与「可规模化淘汰压力来源」） |
| **隐藏真值 `<truth>` + 环境侧完成测试** | **现有：四级验证门第四级判据** → 判据形状从「看输出形状」改为「**看环境终态 + 隐藏真值比对**」（债务 25/28）；**须剥离为只判通过/淘汰** |
| **完成测试的元验证（初始状态必须不通过）** | **新增：判据元验证**（防 trivial 通过）——与 ScaleEnv 的「对已知正确轨迹必须判通过」对偶 |
| **初始状态前置测试** | **现有：6 个 Action 通道** → **通道/环境包自检**：前置不满足则环境包**构建失败**（债务 26/27） |
| **迭代构建-修复回路（k=3）** | **新增：环境包构建的自动修复回路** |
| **可解性过滤（o3 pass@16>0）** | **新增：任务有效性门**（只保证可解）；**难度标尺须另装**（结构量/α 带，见 §5.2） |
| **容器定义文件（Apptainer/Dockerfile）** | **新增：环境包契约（容器定义 + 测试 + 版本号）** → C7 保存/恢复/版本化（Gene Manager 的前置） |
| **最小 XML 命令协议 + 持久 shell + 结构化观测** | **现有：Action 通道契约** → 单命令/回合、观测 = `(标志, 输出, exit code)`、跨回合保留状态（债务 26/27） |
| **二元回合奖励** | **须改造**：SSEA 侧**不是奖励**，是**淘汰/生存信号**——只输出通过/淘汰，不进梯度 |
| **失败模式诊断（loop / 回合耗尽 / 命令多样性）** | **仅作对照**：SSEA 淘汰诊断的参照指标（成功 0.49 vs 循环 0.18） |
| **合成成本锚点（3255 任务、丢弃约一半、k=3 轮、o3×16/任务）** | **睡眠期计算预算（缺失）** → 提供「造一个环境/任务」的**rollout 计数**锚点（非 token 成本，论文未给 token） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **债务 25（判据形状错）/ 债务 28（技能失效被判成成功）**：完成测试判**环境终态**（文件/进程/配置）而非输出字符串，给出判据的**正确形状**（p4 §3）。
  - **债务 26 / 27（环境对无消费者通道报成功 / `skill` 通道无消费者）**：**初始状态前置测试 + 完成测试**构成「环境必须真正消费动作才有终态变化」的机制——无消费者通道的调用**不改变终态** → 完成测试**不通过**，不再有「报成功」的生存空间（p4 §3）。
  - **「睡眠期计算预算未定义」** → **部分回应**：给出**rollout 计数**锚点（Phase IV 每任务 16 次强模型求解、约一半候选被丢弃、容器构建 ≤3 轮），但**未给 token 成本**。
  - **「环境是手写的、通道封闭（6 个 Action 通道）」** → **直接回应**：四阶段管线给出**无人工批量供给**的范式（p4 §3）。
- **不回应**：债务 22（记忆二级门常量阈值）、Gene Manager 缺失、`rules` 零消费者、`retrieve` 键收窄、技能表示（0/33）、DeathHook。
- **可服务的验收实验**：
  - **第四级「环境实测」门**：本篇提供**可规模化环境供给** + **环境侧确定性终态判据**的形状。
  - **饱和判据（危险回避率两臂均 0.9814）** → **不直接回应，是最大缺口**（见 §5.2 / §8）：本篇**没有判别力校准机制**，其难度分布「约一半任务被全部 16 次解出」**天花板偏重**；须与 **GenEnv α 带 / AutoEnv Skin-Inverse / ScaleEnv 干扰项**合并。
  - **实验 4/5（缺 Gene Manager 未开跑）**：环境包版本化（容器定义 + 测试）可与 Gene Manager 同步设计，但**不直接解锁**。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **四阶段无人工环境合成管线**（描述→容器→完成测试→可解性过滤） | 思想/协议 | **改造移植** | 环境供给工厂 | 环境手写、通道封闭；可规模化淘汰压力来源 | 高 |
| 2 | **隐藏真值（privileged ground truth）+ 环境侧确定性完成测试** | 表示/协议 | **改造移植**（剥离为只判通过/淘汰） | 四级门第四级判据 | **债务 25/28**；C9 第一层「淘汰函数归环境」 | 高 |
| 3 | **完成测试的元验证（初始状态必须不通过）** | 协议 | **直接移植** | 判据元验证 | 判据 trivial 通过 / 饱和 | 高 |
| 4 | **初始状态前置测试（prerequisite tests）** | 协议 | **直接移植** | 环境包自检 / 通道准入 | **债务 26/27**：无消费者通道被报成功 | 高 |
| 5 | **迭代构建-修复回路（失败输出反馈，≤k 轮）** | 工程实现 | **改造移植** | 环境包构建 | 环境包不可建、构建期错误 | 中-高 |
| 6 | **可解性过滤门（强模型 pass@16>0）** | 算法 | **改造移植**（只作有效性门，不作难度标尺） | 任务有效性门 | 欠规格/不可解任务入池 | 中-高 |
| 7 | **容器定义即环境包（Apptainer/Dockerfile + 测试）** | 表示/工程实现 | **直接移植** | **环境包契约** | **C7 保存/恢复/版本化**（Gene Manager 前置） | 高 |
| 8 | **最小 XML 命令协议 + 持久 shell + 结构化观测（exit code）** | 协议 | **改造移植** | Action 通道契约 | 观测形状、跨回合状态保持 | 中-高 |
| 9 | **「类别 × 复杂度 × 场景」采样变异算子** | 方法 | **改造移植** | 环境侧变异算子 | 环境多样性 / 淘汰压力多样性 | 中 |
| 10 | **失败模式诊断（loop 39% / 回合耗尽 26% / 命令多样性 0.49 vs 0.18）** | 诊断/基准 | **仅借思想** | 淘汰诊断 | 淘汰失败归因 | 中 |
| 11 | **「简单 RL + 规模化环境 > 复杂 scaffold」的立场**（vanilla PPO + 最小 scaffold 胜出） | 思想/证据 | **直接引用** | 路线选择文档 | 「环境优先」的路线论证 | 高 |
| 12 | **合成侧 rollout 计数锚点（3255 任务、丢弃约一半、o3×16/任务、k=3 轮）** | 基准数据 | 直接引用 | 睡眠期预算 | 「睡眠期计算预算未定义」（部分） | 中 |

---

## 5. 冲突、代价与风险

### 5.1 与硬约束的冲突（逐条，对应 3.1 中 ✗/◐）
1. **C9 ◐：完成测试的结果被用作 PPO 二元奖励（1/0）**（p6 §5）。
   → **剥离**：把完成测试降为**环境侧终局合法性门**——只输出「**通过 / 淘汰**」二值，只作四级门的第四级判据；**不参与打分、不排序、不进优势估计**（C9：验证门只判合法性）。**这是本篇最需要的一处改造，也是与 ScaleEnv 完全同构的一处。**
2. **C9 ◐：Phase IV 可解性过滤以 o3 为难度标尺**（p8 §6 自陈「依赖固定前沿验证器限制了在真正新问题上训练的能力」）。
   → **剥离**：o3 过滤**只作任务有效性门**（保证可解、剔除欠规格），**不作难度刻度**；难度改用**结构量**（ScaleEnv `c(H_n)` 式）或 **GenEnv α 带**标定，避免「淘汰压力天花板 = 某模型能力」。
3. **C2 ✗（仅在线侧）：推理文本进控制环**（p4–5 §4）。
   → **不搬**在线推理形态；**只搬离线合成管线**（编译期语言，合规）。**判据锚点：语言出现在编译期而非运行期**——故本篇的环境合成**不**构成 C2 违规，勿笼统判 ✗。
4. **C1 ◐：域非生存、载体是 LLM**。
   → 只搬环境骨架 + 判据形状，状态量重定义为生存量。
5. **C4 ◐：合成侧与训练侧重资产**。
   → 环境运行侧（容器 + shell）成本可控；合成侧**离线一次性、可摊销**；PPO 不进 SSEA。Phase IV 的 o3×16 是**最大合成开销**，须评估是否用更弱/本地模型替代。
6. **C7 ◐：无继承/淘汰**。
   → 环境包版本化先做（零依赖），继承/淘汰留给 Gene Manager。

### 5.2 隐含假设与失效条件
- **【对 SSEA 最要命】论文不回答「合成环境是否有判别力」**：判别力是靠**训练增益 + 迁移到人类策展 benchmark**证明的，**不是环境自身的性质**；其难度分布自陈「**约一半任务被全部 16 次尝试解出**」（p5 §5、Fig.6 右 p7）——**天花板偏重**，与 SSEA「危险回避率两臂均 0.9814（饱和）」是**同一病灶**。论文**无任何饱和检测 / 判别力校准机制**（未提及）。
- **难度天花板硬限制**：可解性过滤「**无法生成超出前沿模型（o3）能力的任务**」（p9 自陈）→ **淘汰压力无法随 SSEA 能力增长而持续升高**，一旦 SSEA 逼近该前沿，环境即失效。作者建议 self-play 补此，但**未实现**。
- **难度刻度不可复现**：难度由 o3 pass@16 定义（p8 §6）→ 换验证器则难度分布全变，**不可跨时间/跨项目比较**（与 ScaleEnv `g(D_n)`、Agent-World Doubao Pass@10 探针同类问题）。
- **无管线逐组件消融**：论文只做「PPO 训练前后」「与其它微调变体对比」，**未消融四阶段中任一阶段**（如去可解性过滤、去前置测试）→ 无法归因到底是哪一步在起作用。
- **无 seed / 方差**：dev 集与 OpenThinker 集为单值（未提及）；仅 TerminalBench 2.0 本方法**5 runs 平均**（p6 Fig.3 注）。
- **测试生成 bug 会误记**：若完成测试本身有缺陷（过松/过紧），会把**环境 bug 记到智能体账上**（与债务 25/28 同类）；论文未讨论测试质量审计。
- **任务欠自然**：自陈「像竞赛编程题，不像混乱欠规格的真实请求」（p9）→ 与 SSEA 需要的**生存压力**（歧义、延迟、部分可观测）形态距离远。

### 5.3 算力 / 带宽 / 工程代价
- **合成侧**：四阶段 + 容器构建（≤3 轮修复）+ **o3 每任务 16 次交互式求解**，且约**一半候选被丢弃** → 为得 3255 任务需生成并求解 **>6500** 个候选；**重资产，但离线一次性、可摊销**（p5 §5、p8 §6）。
- **环境运行侧**：容器 + 持久 shell + 确定性测试 → **逻辑成本低**，但需容器基础设施（Apptainer/Docker，p5 §4）。
- **训练侧**：vanilla PPO on 3B–8B、每 prompt 16 rollouts、16 回合、16k 上下文、无 KL 惩罚（p6 §5）→ **SSEA 不需要复现**，省掉全部 RL 开销。
- **工程代价前置**：要给 6 个 Action 通道配「可执行 + 有消费者 + 可判定终态」才能谈环境规模化——**与债务 27 是同一件事，顺序不可颠倒**。

### 5.4 搬运后的可能退化模式（若失败，会以什么形式失败）
1. **淘汰压力天花板（最危险）**：难度由固定前沿模型定义 → 一旦 SSEA 逼近该前沿，**淘汰率长期贴 1（全通过）**，症状与现有饱和判据一致。**本篇无任何机制可检测此症状**。
2. **判据饱和（粗终态检查）**：若完成测试只查「文件存在」这类粗终态 → 所有版本都「通过」→ 指标全绿但行为不变。
3. **环境/测试 bug 误记**：容器或测试生成有缺陷 → 同一策略在不同环境版本上成功率大幅抖动。
4. **环境塌缩**：程序化采样若不放回、或提示收敛 → 任务模板趋同 → 淘汰压力多样性下降（论文未讨论抽样策略）。
5. **语言回流**：若误把在线推理文本也搬进控制环 → C2 被破，且语言噪声进入控制环。
6. **容器基础设施依赖**：环境包绑定 Apptainer/Docker → 移植到 SSEA 的运行环境可能引入额外系统依赖与安全面。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **同类（环境合成族，正交域，须点名并排）** | **ScaleEnv** | **ScaleEnv 卡 §6.1 已点名「Endless Terminals：终端智能体的 RL 环境规模化（域 = 命令行），与 ScaleEnv 的『DB + 工具』域正交；二者合起来覆盖『离散状态可执行环境』的两大现实形态」——本卡回应此点名**。两者**同源近亲**：都 from-scratch、都用**规则式确定性判据**、都**明确拒绝 LLM-as-judge**、都**无「被测者失败→难度」反馈**。**差异**：ScaleEnv 判 **DB 状态**、Endless Terminals 判 **文件/进程/配置状态**；ScaleEnv 有**难度旋钮**（`c(H_n)` 结构量 + 干扰项注入 + 依赖感知 BFS），Endless Terminals 有**自然难度分布**（o3 pass@16）但**无难度控制旋钮**；ScaleEnv **无代码发布**，Endless Terminals **有**（GitHub）。→ **合并判据形状取最严**：ScaleEnv 的 Hard Constraints + 本篇的「隐藏真值 + 终态测试」；**难度旋钮取 ScaleEnv，有效性门取本篇** |
| **同类（C9 头号反例）** | **GenEnv** | GenEnv = difficulty-aligned **co-evolution**（`R_env=exp(−β(p̂−α)²)`，环境难度由智能体近期表现**反向驱动**）。**本篇没有这条通道** → **本篇是比 GenEnv 更干净的 C9 标本**；但 GenEnv 的 **α 带 + Theorem 1 样本量界**恰是本篇缺的**判别力校准器与难度调度器** → **二者互补**：本篇供环境供给 + 判据形状，GenEnv 供「难度调到哪、要多少样本才分得开」（直接回应本篇「约一半任务被全部 16 次解出」的天花板偏重） |
| **同类（真实数据挖库 + 共演化）** | **Agent-World** | Agent-World = deep-research 从真实 Web 挖库 + MCP 工具生态 + **失败驱动共演化** + `V_code`（同时校验答案与 DB 状态）。本篇 = **纯程序化、容器、无共演化**。**关键差异**：Agent-World 的难度/扩张含**被测智能体失败信号**（C9③ 风险），本篇**无**；Agent-World 有**真实事实性**（本篇自陈任务「像竞赛编程题」，欠真实）。→ **互补**：本篇供**纯程序化、低事实性依赖**的环境，Agent-World 供**真实数据与事实性门槛**；判据合并取 `V_code` + 终态测试的最严形态 |
| **同类（程序化合成 + 轨迹验证）** | **EnvScaler** | EnvScaler 用 **rule-based trajectory validation functions**（ScaleEnv 卡已点名其为「同源近亲」）→ 与**本篇的确定性完成测试**属同一族判据形状；三篇（ScaleEnv/EnvScaler/本篇）应**合并评估判据形状**，避免三套并存 |
| **同类（环境级 RL）** | **AutoForge** | AutoForge 提出 environment-level RL + 环境级优势估计；本篇**明确走相反方向**——**vanilla PPO、最小 scaffold、无环境级 RL**，主张「简单 RL 成功靠环境规模化」。→ **对照价值**：本篇是「环境规模化优先于算法复杂度」的**最干净论据** |
| **互补（度量 vs 生成）** | **AutoEnv** | AutoEnv **量**跨环境学习（三层环境抽象 `Base/Obs/Skin`、三阶段验证、**差分模型测试**、**Skin-Inverse 控制消融**、validator 合法性检查）；本篇**造**环境。**接口**：本篇供环境供给，AutoEnv 的 **Skin-Inverse + 差分模型测试**供**判别力/指标健康度校准**——直接补本篇「无饱和检测」的缺口 |
| **另一端的环境生成** | **Genie** | 无监督、从视频生成可玩世界（潜在动作、连续视觉）。与本篇构成**环境生成的两个极端**：Genie 供连续/想象世界，本篇供**离散/可执行/状态外置**世界。SSEA 需要本篇做**淘汰判据**、Genie 做**离线想象**，**不可互换** |
| **互补（最紧，模型内 vs 模型外）** | **Dream-RSI** | 发现历史即重放模拟器（模型内、慢环做梦式离线验证）。本篇环境在**模型外**且**确定性可复现** → 接口：重放查无延续时，向本篇环境包申请一次真实交互取终态，**避免用想象结果充当淘汰判据** |
| **消费方（技能侧主干）** | **PSN** | PSN 的故障定位/成熟度门控/回滚验证需要**环境**来验证；本篇的容器环境包 + 确定性终态测试正是 PSN 的验证场 → 解决「技能固化 0/33」的一条具体路径（**须与 ScaleEnv 的场地竞争取舍：终端域 vs DB 域**） |
| **消费方（技能流水线）** | **SkillWeaver / Voyager** | 技能提案-练习-打磨/自动课程缺规模化场地；本篇提供场地（且是**有状态多轮**场地，比单轮更接近技能固化场景） |
| **门禁复用** | **SEDM** | SCEC 自包含打包 + A/B 准入验证 → 可复用为**环境包准入官**（环境包也走「自包含打包 + A/B 准入」） |
| **风险清单** | **Misevolve** | 误演化威胁模型与红队清单。**需新增两条：环境侧判据饱和 / 难度天花板（固定前沿验证器）**——此前清单覆盖模型/记忆/工具/工作流四路径 |
| **训练诊断** | **RAGEN** | Echo Trap 诊断 + 不确定性过滤；本篇**无共演化**，Echo Trap 风险低于 GenEnv，但「loop 失败 39%」是本篇特有的退化模式（可用命令多样性 0.49 vs 0.18 监控），可作 SSEA 淘汰诊断的参照指标 |
| **形式化参照** | **Gödel Agent / ADAS / MaAS** | 自指递归自改进、自动设计智能体的形式化；本篇「提示采样 → 容器 → 测试 → 过滤」可作为**环境侧**的形式化实例 |

### 6.2 推荐组合方案
- **组合 1（最优先，直解「可规模化淘汰压力来源」）：本篇（四阶段合成管线 + 隐藏真值 + 终态测试）× SSEA 6 通道**
  - **接口形态**：每个 Action 通道 = 一个可执行动作，环境包 = 容器定义 + 前置测试 + 完成测试（**隐藏真值**）；`skill` 通道若无消费者 → **终态不变 → 完成测试不通过**（不是成功）。
  - **组合后新增能力**：环境供给从「手写 6 通道」升级为「程序化批量供给」；债务 26/27/28 一次性闭合。
  - **新增风险**：容器基础设施依赖；合成成本（o3×16/任务）需评估替代方案。
- **组合 2（补判别力与难度调度，回应用户核心关切）：本篇（环境 + 判据形状）× GenEnv（α 带 + Theorem 1 样本量）× AutoEnv（Skin-Inverse + 差分模型测试）**
  - **接口**：本篇造环境与终态判据；GenEnv 的 α=0.5 带 + `k_min=0.1` 死区把难度从「约一半被全部 16 次解出」的天花板偏重**拉回可分档区**；AutoEnv 的差分模型测试判「判据是否已饱和（弱模型≥强模型即不可信）」。
  - **新增能力**：把「判据饱和」拆成「**难度天花板**」与「**门无效**」两种可判决情形（**这正是本篇单独做不到的**）。
  - **新增风险**：难度旋钮引入的方差被误读为效应（见 GenEnv 卡 §5.4）。
- **组合 3（判据形状统一）：本篇（隐藏真值 + 终态测试）× ScaleEnv（Hard Constraints）× Agent-World（`V_code`）× EnvScaler（trajectory validation）**
  - **接口**：四级门第四级判据统一为「**环境终态 + 可执行断言 + 隐藏真值比对**」；四者取**最严**形态。
  - **新增能力**：判据形状一次定死，避免四套并存（终端域取本篇、DB 域取 ScaleEnv）。
- **组合 4（环境版本化 × Gene Manager，缺失）**：环境包 = 容器定义 + 测试 + 版本号，与 GenePackage 版本配对，A/B 对照时两者同时固定；**环境版本号可先做（零依赖）**，Gene Manager 后补。
- **组合 5（离线想象 × 在线淘汰）**：本篇（离散可执行环境，供淘汰判据）× Genie（连续世界模型，供离线想象）——**不得互换**。
- **组合 6（重放 × 环境）**：本篇 × Dream-RSI —— 重放查无延续时向确定性环境包申请一次真实交互。
- **组合 7（防污染）**：本篇 × Misevolve —— 加入「**难度天花板（固定前沿验证器）** / 判据饱和 / 环境与测试 bug 误记 / 环境塌缩」四条环境侧红队项。

### 6.3 本篇在组合中的典型角色
- **淘汰压力来源工厂 + 判据形状供应商（C9 第一层样板）**：管「环境怎么**无人工批量造**、判定怎么写成**环境侧确定性终态事实检查**、真值怎么**藏在模型碰不到的地方**」。
- **明确不是**：**不是判别力校准器**（无饱和检测、难度天花板受前沿模型限制）、不是难度调度器（归 GenEnv/Agent-World）、不是记忆组织者（归 Memento/FLEX）、不是技能表示方案（归 PSN）、不是策略训练方法（归 RAGEN）。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直接命中 SSEA 两条战略需求：①「**可规模化的淘汰压力来源**」（四阶段无人工管线，p4 §3 实测）；②「**C9 第一层淘汰函数归环境**」的形状（隐藏真值 + 环境侧终态测试，p3–4 实测）。也部分回应债务 25/26/27/28。扣分因当前卡点是 Gene Manager 缺失与判据饱和，**不是环境数量** |
| 立场兼容性 | **4** | **环境合成族里最贴近 C9 第一层的一件**：判定是环境侧、确定性、终局的事实检查，**真值对模型不可见**，**无 LLM-judge、无 NL 用户模拟器、无共演化反馈通道**（p3–4 §3、§4）。扣分因：完成测试结果被用作 **PPO 二元奖励**（C9 打分/排序，p6）、**难度绑定 o3**（p8）、在线推理文本进环（C2 ✗）（实测） |
| 可搬运性 | **4** | 管线是提示/协议级、**代码已开源**（GitHub）；环境是**容器定义 + 测试文件**，可直接照抄形状；无需求解 3B–8B RL（实测）。扣分：容器基础设施依赖（Apptainer/Docker）、Phase IV 的 o3 成本 |
| 证据强度 | **4** | 加分：**3 个模型 × 2 个 held-out benchmark**、TerminalBench 2.0 本方法 **5 runs 平均**、**失败模式分析**（loop/回合耗尽/命令多样性）、**难度与类别分层**（pass@5）、**代码开源**、任务生成早于 TB2.0 发布（无泄漏）。扣分：**无管线逐组件消融**、dev 集**无 seed/方差**、**无独立 Limitations 之外的系统边界分析**、难度定义依赖 o3 |
| 组合价值 | **4** | 与 ScaleEnv / Agent-World / GenEnv / AutoEnv / AutoForge / EnvScaler / Genie / Dream-RSI / PSN / SkillWeaver / Voyager / SEDM / Misevolve / RAGEN 均有明确接口；与 GenEnv（补判别力）、ScaleEnv（判据合并 + 域正交）、AutoEnv（补度量）互补最紧（推断 + 实测各半） |
| 落地成本 | **3** | 反向口径。**加分**：环境运行侧成本低（容器 + shell + 确定性测试）；不需要 GPU 训练；代码开源。**扣分**：合成侧需容器基础设施 + **o3×16/任务**且约一半丢弃（重资产）；前置是给 6 通道配消费者与终态判据（与债务 27 同一件事） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用「**四阶段无人工环境合成管线 + 隐藏真值 + 环境侧确定性完成测试（剥离为只判通过/淘汰）+ 完成测试元验证 + 初始状态前置测试 + 迭代构建-修复回路 + 可解性过滤门（只作有效性门）+ 容器定义即环境包**」；**不采用** LLM 策略本体、PPO 二元奖励回路、o3 作难度标尺。**未给 A 的原因**：① 存在 C9 ◐（终态测试进 PPO 奖励回路）与 C2 在线侧冲突，需实质剥离；② **最关键的缺口——本篇不提供「环境判别力」的保证或检测**，且**难度天花板被固定前沿模型（o3）锁死**，而这正是 SSEA 当前最紧的病（饱和 + 需要可持续升高的淘汰压力）；③ 证据侧无逐组件消融、dev 集无 seed/方差。
- **优先级：P1** —— 不是 P0，因为当前卡点（Gene Manager 缺失、判据饱和）**不是环境数量问题**；但「**可规模化淘汰压力来源**」是 SSEA 第二阶段「生态」的供给侧刚需，且「隐藏真值 + 环境侧终态测试」是债务 25/26/27/28 的直接解、环境包版本化是 Gene Manager 的前置，应在记忆/技能主干之后、环境规模化之前落。**若与 GenEnv α 带 + AutoEnv Skin-Inverse 组合后的判别力实验通过，可升 A。**

### 建议动作（按执行顺序）
1. **通道盘点（先做，零依赖）**：对 6 个 Action 通道逐个判定「是否有消费者 / 是否可执行 / 是否产生可判定的终态变化」，列出合规数（所有后续工作的**分母**）。
2. **落地「终态判据」形状**：四级门判据改为「**环境终态 + 隐藏真值比对 + 可执行断言**」；给判据加**元验证**（初始状态必须不通过、已知正确轨迹必须通过）。**终态判据只输出通过/淘汰，绝不进梯度/排序**（剥离 PPO 二元奖励形态）。
3. **环境包契约 + 版本号**：环境 = 容器定义 + 前置测试 + 完成测试 + 版本号，一经发布即冻结、模型不可读写（C9 第一层的工程保障；先于 Gene Manager 实现）。
4. **小规模试造环境族**：用四阶段管线（可先不接容器，改用进程/文件沙盒）试造 N=10–20 个环境，验证「无消费者通道 → 终态不变 → 不通过」。
5. **判别力校准（关键补装）**：借 GenEnv 的 α 带 + `k_min` 死区 + Theorem 1 样本量界 + AutoEnv 的 Skin-Inverse / 差分模型测试，把判据从饱和区（回避率 0.9814）拉到可分档区；**难度标尺必须去 o3 依赖**（改用结构量）。
6. **记录合成成本锚点**：把「3255 任务、丢弃约一半、o3×16/任务、容器构建 ≤3 轮」写入「睡眠期计算预算」草案（**注意论文未给 token 成本，只有 rollout 计数**）。
7. **Misevolve 清单增补**：加入环境侧「**难度天花板（固定前沿验证器）** / 判据饱和 / 环境与测试 bug 误记 / 环境塌缩」四条。
8. **与 ScaleEnv / Agent-World / GenEnv / AutoEnv / EnvScaler 合并评估**：判据形状取最严形态、C9 冲突共用一套剥离规则、判别力校准只建一次、域选择（终端 vs DB）一次定死。

### 最小验证实验：**程序化环境能否提供可持续升高的淘汰压力**（回应核心关切）
- **目的**：判定「Endless Terminals 式程序化环境」能否为 SSEA 提供**判别力足够、且不随能力增长而饱和**的淘汰压力来源。
- **双臂 / 消融设置**：
  - **Arm A（对照，手写环境）**：现有手写环境 + 现有判据（终态粒度粗）。
  - **Arm B（处理，程序化环境）**：四阶段管线造的环境 + **隐藏真值 + 确定性终态测试**（只判通过/淘汰）+ 前置测试 + 元验证。
  - **消融 B1**：去「可解性过滤」；**消融 B2**：去「前置测试/元验证」（用于定位各自贡献）；**消融 B3**：把终态判据退化为「文件存在」粗检查（复现饱和）。
  - **判别力探针（关键）**：在同一环境族上跑**两个能力不同的臂**——完整策略 vs **人为弱化策略**（屏蔽部分通道/技能），各 ≥8 seed，看环境能否把两者分开。
  - **难度递升探针（本篇特有缺口）**：把「能力最强臂」的成功率**逐档抬高**（加环境难度/换更强策略），检验**淘汰率是否出现天花板**（一旦全通过即证明 o3 天花板问题被继承）。
- **判据（分档，先看分母）**：
  1. **机制计数（分母）**：环境包数、可判定终态测试数、无消费者通道数（分母 = 6）、**前置测试拒绝事件数（若 =0 说明契约未接入判定路径，实验无效）**。
  2. **行为差（判别力本体）**：完整臂 vs 弱化臂的成功率差 `Δp̂`——**要求 `Δp̂` 显著 >0 且跨 seed 可重现、换邻近难度仍同号**。
  3. **淘汰结果**：第四级环境实测门淘汰率是否**可分档**（当前危险回避率两臂均 0.9814）——B 臂应出现可分档分布而非全通过。
  4. **天花板检测（本篇核心）**：随策略能力抬升，**淘汰率是否单调下降而非贴 1**；若在弱化臂之前就已全通过 → 证明难度天花板过早到来。
- **预期与证伪条件**：
  - **预期**：B 臂 `Δp̂` 显著 >0、淘汰率可分档；B 臂捕获 `skill` 通道「终态不变 → 不通过」，失效技能不再被判成功；能力抬升后淘汰率仍非全通过。
  - **证伪（环境无判别力）**：若 B 臂 `Δp̂≈0` → **程序化环境本身缺乏判别力**，会复制 SSEA 的饱和病 → 必须先加难度旋钮（GenEnv α 带）并标定到 `p̂≈0.5` 档。
  - **证伪（难度天花板过早）**：若「能力抬升 → 淘汰率很快贴 1」→ **o3 天花板问题被继承**，淘汰压力**不可持续升高** → 必须去前沿模型依赖，改用结构量标定。
  - **证伪（判据形状错在上游）**：若 B 臂仍把失效技能判成功 → 判据形状错在更上游（技能表示问题），转 PSN / 技能表示议题。
  - **证伪（合成成本不可接受）**：若造一个可用环境的 rollout 成本超出「睡眠期预算」可行范围 → 降级为「仅借思想」（手工 + 半自动生成）。
- 若 **E 不采用**：不适用（裁决为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **「淘汰压力可持续性」如何定义与检测**：SSEA 是否接受「淘汰压力可持续 = 随策略能力抬升，淘汰率单调下降且不提前贴 1」这一操作化定义？若接受，它应成为**环境准入的必要条件**。
  2. **C9 边界**：把确定性完成测试用作「环境侧终局淘汰门」是否算合规？（本卡倾向：合规，因为它确定性、真值模型碰不到、且只输出通过/淘汰；但**若它进奖励塑形则违规**。）需团队书面确认——与 ScaleEnv 卡 §9 同一议题。
  3. **环境包版本号与 GenePackage 版本号如何配对**（先做哪个、A/B 对照时如何同时固定）——Gene Manager 未实现前的临时记账方式。
  4. **环境域选择**：SSEA 的环境族取**终端域**（本篇，有状态多轮）还是 **DB/工具域**（ScaleEnv），或两者并存？容器基础设施（Apptainer/Docker）是否可接受。
  5. **Phase IV 的强模型过滤**：SSEA 是否接受用外部强模型（o3 类）做**任务有效性门**（只要它不参与 SSEA 判据/淘汰）？若要求全自主，是否改用 self-play（作者建议但未实现）？
- **需补查的文献或资料**：
  1. **代码库 https://github.com/kanishkg/endless-terminals**：核对四阶段提示词、容器构建修复回路、完成测试生成器、可解性过滤脚本的实际实现（本卡事实来源为 PDF）。
  2. **EnvScaler** 的 rule-based trajectory validation functions 与本篇的完成测试**是否等价**，还是各有更严的判据形状（决定债务 25 的解法取哪个）。
  3. **Agent-World** 的 `V_code`（答案 + DB 状态）与本篇终态测试（文件/进程状态）的**判据强度对比**。
  4. **AutoForge / EnvScaler / AutoEnv / Agent-World / GenEnv / ScaleEnv** 的可验证性方案——本篇与它们同族，建议按同一纪律合并评估，联通环境合成族图谱（ScaleEnv 卡 §9 已提出同一建议）。
  5. **Poesia et al. 2024（self-play / intrinsic motivation）与 Zhao et al. 2025（Absolute Zero）**：本篇自陈的 self-play 替代方案，若 SSEA 要去 o3 依赖，需细读。
- **需人工核对的公式 / 数字 / 实现**：
  1. **统计口径**：dev 集 / OpenThinker 集是否单次运行、seed 数——全文未提及（仅 TerminalBench 2.0 本方法 5 runs 平均，p6 Fig.3 注），需核对代码或作者主页。
  2. **「丢弃约一半候选」的具体口径**（p5 §5、p8 §6）：是相对「所有生成候选」还是「通过容器构建的候选」？影响合成成本估算。
  3. **合成侧 token 成本未给**（仅有 rollout 计数与容器构建轮数）→ 需自行估算或向作者索取。
  4. **Phase IV 的 `n=16` 与训练侧 `16 rollouts/prompt` 是同一数量级的巧合还是有意对齐**——正文未说明。
  5. **失败模式分母**：loop 39%（30 任务）、回合耗尽 26%（20 任务）、重叠 11 → 需核对总失败任务数（本卡按 n≈77 推断）。
  6. **容器构建 `k=3` 轮的敏感性**：正文未给「提高 k 会保留多少任务」的分析。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| 摘要："Environments are the bottleneck for self-improving agents. Current terminal benchmarks were built for evaluation, not training; reinforcement learning requires a scalable pipeline, not just a dataset." | p1 |
| 摘要："a fully autonomous pipeline that procedurally generates terminal-use tasks **without human annotation**. The pipeline has four stages: generating diverse task descriptions, building and validating containerized environments, producing completion tests, and filtering for solvability. From this pipeline we obtain **3255 tasks**" | p1 |
| 摘要："We train agents using **vanilla PPO with binary episode level rewards** and a **minimal interaction loop: no retrieval, multi-agent coordination, or specialized tools**." | p1 |
| 摘要："These results demonstrate that **simple RL succeeds when environments scale**." | p1 |
| 摘要结果："Llama-3.2-3B improves from **4.0% to 18.2%**, Qwen2.5-7B from **10.7% to 53.3%**, and Qwen3-8B-openthinker-sft from **42.6% to 59.0%**"；TerminalBench 2.0："**0.0% to 2.2%** / **2.2% to 3.4%** / **1.1% to 6.7%**" | p1 |
| 问题陈述："What remains missing is a **fully autonomous pipeline** that can generate an endless stream of terminal tasks: complete with initial environments, task specifications, and verification tests, with **minimal human supervision**." | p2 |
| 既有缺陷：① benchmark 挪作训练有过拟合风险；② 蒸馏继承教师天花板 + 昂贵 API；③ 人工策展标注成本限制规模与多样性 | p2 |
| Fig.2 阶段 I：`<task>`（"Detailed specification of the desired final system state… **No commands given—agent must infer the solution**"）+ `<truth>`（"**Hidden ground-truth data** for automated verification"） | p3 |
| Fig.2 阶段 II："Write a test file that validates the environment before an agent performs a task…test for the presence of all required prerequisites"；阶段 III："validates the environment **after** an agent performs a task…exact expected end state"；阶段 IV："**Generate 16 solutions from o3 & Filter out unsolved tasks**" | p3 |
| 管线四阶段："1) generating task descriptions, 2) setting up an environment while validating it with self-written tests, 3) generating tests to verify completion of a task, and 4) generating several solutions from a strong model to ensure the validity of a task. Each stage builds on the previous, with **automatic verification ensuring validity at every step**." | p4 §3 |
| 隐藏真值："a separate privileged information section containing exact file contents, paths, and expected states that automated tests will use for verification. **The privileged information section is never revealed to the agent** interacting with the environment." | p4 §3 |
| 迭代构建："the model generates a container definition, we build it and run the initial tests inside, and if tests fail, we feed the failure output back to the model for correction. This continues for **up to k=3 rounds** or until tests pass. Tasks that cannot produce a valid container are discarded." | p4 §3 |
| 完成测试元验证："We verify that these tests **do not pass in the initial state**, ensuring they meaningfully assess task completion rather than **trivially succeeding**." | p4 §3 |
| 可解性过滤："we sample **n=16** solution attempts from a capable model (**o3**)… We retain tasks where **at least one solution succeeds (pass@16 > 0)** and discard the rest." | p4 §3 |
| 交互协议："`<command>...</command>` wraps shell commands, and `<command>done</command>` indicates task completion. The model can include arbitrary reasoning before its command… the model can reference prior reasoning, correct mistakes, or build on partial progress." | p4–5 §4 |
| 持久 shell："The agent connects to an Apptainer container instance that **remains alive across all turns** of an episode, **preserving filesystem state, environment variables, and running processes** between commands."；观测："We capture both **stdout and stderr, along with the exit code**, and return a structured observation: whether the command succeeded or failed, followed by the output." | p5 §4 |
| 回合终止："An episode ends when the agent emits the done action, reaches a maximum number of turns (**16 while training**) or tokens (**16k while training**). We execute the held-out final tests **inside the container** to determine success." | p5 §4 |
| 数据集规模："Our pipeline produces **3255 tasks** in Apptainer format, of which approximately 2500 are also converted to Harbor format."；过滤："Solvability filtering **discards roughly half of all generated candidates**, those where o3 fails all 16 attempts" | p5 §5 |
| 难度分布："roughly **half the tasks are solved by all 16 attempts**, with the remainder spanning a range of difficulties" | p5 §5；Fig.6 右 p7 |
| 训练设置："we sample **16 rollouts per prompt** for up to 16 turns, with a maximum of 2048 tokens generated per turn and a total context window of 16k tokens"；"temperature of 0.6"；"we treat each complete episode as a single reward signal: the agent receives reward **1 if the final tests pass and 0 otherwise, with no intermediate rewards**"；"clipping bounds ε_low=0.2 and ε_high=0.28"；"**We do not use a KL penalty**"；"a **5 minute environment timeout**" | p6 §5 |
| 训练成本："Llama-3.2-3b and Qwen2.5-7b were trained on **4 A100s for about 2 days**. Qwen3-8b-openthoughts-sft was trained on **8 B200s for about 8 hours**." | p6 §5 |
| 结论句："Our setup uses vanilla PPO with binary episode level rewards, no intermediate shaping, no KL penalty, and a minimal agent architecture… The gains come **not from algorithmic sophistication but from scaling the environments**" | p7 §5 |
| 迁移："our tasks were generated **before the release of TerminalBench 2.0**, ensuring **no data leakage**." | p7 §5 |
| 难度分层（pass@5）："**25% (1/4) easy, 14.5% (8/55) medium, and 10% (3/30) hard**" | p7–8 §5；Fig.7 |
| 失败模式："1) **loop failures**… accounting for **39% of failures (30 tasks)**, and 2) **turn exhaustion**… affecting **26% of failures (20 tasks)**. These categories overlap, with 11 tasks exhibiting both… The remaining failures (**49%**) terminate early with incorrect solutions" | p7–8 §5；Fig.5 |
| 命令多样性："Successful tasks exhibit significantly higher command diversity (**0.49** on average) compared to failed tasks with loop behavior (**0.18** on average)" | p8 §5 |
| 局限 1："the procedurally generated tasks tend to **resemble competitive programming problems more than the messy, underspecified requests** that users actually pose to AI assistants." | p9 §6 |
| 局限 2："Our filter for solvability introduces a **capability ceiling**. We filter using pass@16 from o3… **our pipeline cannot generate tasks beyond the frontier model's capability**… Self-play approaches… could adaptively scale difficulty without relying on a fixed frontier validator" | p9 §6 |
| 局限 3："Incorporating humans in the loop… could improve both task quality and diversity beyond what purely synthetic generation achieves, albeit at the increasing the cost of generating tasks, **making the pipeline less scalable**." | p9 §6 |
| 未来方向："Partial rewards based on the number of test cases passed, rather than binary episode-level rewards, could provide denser training signal"；"learning **world models of terminal dynamics**… could enable more sample-efficient training by allowing agents to plan and simulate outcomes through **imagined rollouts** before executing commands" | p9 §6 |
| 代码："Code available at **https://github.com/kanishkg/endless-terminals**" | p1 脚注 1 |
| 相关工作中被点名批评/对照：SWEGym（2438 Python 任务但依赖 GitHub issues）、OpenThoughts Agent（最近邻，但 query 来自人工 NL2Bash、无 TB2.0 增益）、Poesia et al. 2024（self-play 单轮）、Chen et al. 2025（experience synthesis / world model 蒸馏） | p3 §2 |
| **有独立 Limitations 讨论（§6 Discussion 三条）**；全文检索 p1–11 未见数据发布声明，但**有 GitHub 代码链接** | 全文 |
