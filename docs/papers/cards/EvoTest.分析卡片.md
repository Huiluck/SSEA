# 论文分析卡片 · EvoTest

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-10-15 EvoTest Evolutionary Test-Time Learning for Self-Improving Agentic Systems.pdf` |
| 标题 | **EvoTest: Evolutionary Test-Time Learning for Self-Improving Agentic Systems** |
| 作者 / 机构 | Yufei He、Juncheng Liu、Yue Liu、Yibo Li、Tri Cao、Zhiyuan Hu、Xinxing Xu、Bryan Hooi；National University of Singapore + Microsoft Research（含 MSRA-Singapore） |
| 发表时间 / 出处 | **ICLR 2026** conference paper；arXiv:2510.13220v2 [cs.AI]，v2 日期 2026-04-17；PDF 文件名标注 2025-10 |
| 论文链接 | arXiv:2510.13220（首页脚注） |
| 代码链接 | https://github.com/yf-he/EvoTest |
| 标签 | 测试时学习(TTL) · **无梯度演化** · 整机配置演化 · 成功/失败双记忆 · UCB 选择 · J-TTL 基准 · 叙事式 credit assignment |
| **应用裁决** | **B 零件采用**（采用「无梯度整机演化」的证据与形状、四通道配置/双库记忆表示、可量化预算账本与 J-TTL 协议；**不采用** UCB 评分选择、语言 Evolver 在环、任务专用过拟合产物） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：提出 **J-TTL**（Jericho Test-Time Learning）基准 + **EvoTest** 框架——在**不做任何微调、不用任何梯度**的前提下，用「Actor Agent（固定骨干 LLM）+ Evolver Agent（LLM）」两体循环，每集结束后**演化整个 agentic 配置 χ = (prompt, memory, hyperparameters, tool-use routines)**，并以 UCB 选择下一代配置；在 6 个 Jericho 文本冒险游戏上 AUC 平均 **0.47（gemini-2.5-flash）/ 0.50（claude-4-sonnet）**，超过反思/记忆/prompt 优化与在线微调基线，且是**唯一赢下两局（Detective、Library）**的方法（p1、p7–8）。
- **对 SSEA 的意义**：它是 SSEA 目前能找到的**「测试时学习 + 演化 + 完全不动权重」最强证据样本**——作者在局限节明确承认其学习「被限制在符号层，而非模型权重的参数层」（App.A p16），直接支撑 **C3 三分离**与「参数侧 Δθ 留在 DEFERRED_SCOPES 不做」的决策；同时给出**慢环计算预算的可量化账本**（每周期 1 次 LLM 前向、20–30 s、CPU+网络、无梯度显存）。但它的选择压力用 **UCB 对平均环境得分取 argmax**，是 **C9 硬冲突**。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：当前 AI agent 无法在**测试时现学**复杂技能，在新环境里像「clever but clueless interns」——能执行指令但不能从经验重构自身流程（p1）；领域缺乏专门衡量「同一任务连续多次尝试、逐步变好」能力的测试台（p1）。
- **它指出的既有方案缺陷**（p2、App.G p22–23）：
  1. **静态 agent** 无学习机制，会重复同样错误，分数曲线平坦；
  2. **在线 SFT** 在失败集里没有好数据可学（"trapped because it cannot generate the very data it needs"），且只学「涨分动作」会漏掉大量**零奖励但必要**的动作（如 `UNLOCK DOOR WITH KEY`）；
  3. **在线 RL（GRPO）** 在稀疏奖励下 credit assignment 失败——无效动作的 `reward=0` 与「中性但必要」动作的 `reward=0` 无法区分，单次更新信号太弱；
  4. **Reflexion / memory 系** 只改 prompt 或只增强回忆，**不改决策逻辑与工具使用**；
  5. **prompt 优化系（TextGrad/Promptbreeder/EvoPrompt）** 只沿**单一轴（prompt）**优化，无法同时调探索强度或知识使用方式。

### 2.2 核心思想（关键 insight，3 条）
1. **学习对象是「整个 agentic 配置」而非仅 prompt**：χ = (p, M, h, u) 四通道**联合演化**（"whole-system evolution"）——能发现并解决单通道方法看不到的复合瓶颈（如「早集提高温度 + 加一条策略启发」同时做）（§4.1 p5、§5.2 p8）。
2. **学习信号从「稀疏标量奖励」换成「整段 episode 叙事文本」**：Evolver 对 transcript 做语义 credit assignment（"credit assignment via narrative analysis"），比反向传播更 **data-efficient**——一次经验即可做定向结构编辑（§5.2 p9）。
3. **完全无梯度**：骨干 LLM **冻结、不可训练**；改进只落在**外部符号结构**上，单次更新成本 = 一次前向调用（§4 p4、App.E p20–21）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **Actor Agent** | 配置 χ(e) + 观测 o_t → 动作 a_t；产出轨迹 τ(e) 与回报 R(e) | 执行一集 | §4.2 p5 |
| **Evolver Agent** | (τ(e), χ(e)) → m 个子配置 C(e+1) | 提案 / 演化 | §4.2 p5 |
| **Agentic Configuration χ=(p,M,h,u)** | 完整操作策略元组 | 可演化单元 | §4.1 p5 |
| **Prompt Mutation** | p → p̃（生成 Walkthrough/Essential Actions + Actions to Avoid + Exploration Plan 三段） | 策略演化（主驱动） | §4.2 p5、App.H p25 |
| **Memory Update** | τ(e) → success 表 + failure 表 | 记忆写入 | §4.2 p5–6、App.J p26–32 |
| **Hyperparameter Tuning** | h → h̃（如 temperature） | 探索/利用调节 | §4.2 p6、App.M p37 |
| **Tool-Use Refinement** | u → ũ（含**生成 Python `extract_state` 函数** + 一句 memory 交互逻辑） | 工具/状态抽象演化 | §4.2 p6、App.H p25 |
| **UCB Selection** | {χ(e)}∪C(e+1) → χ(e+1)，argmax μ̂(χ)+β√(log N/(1+n(χ))) | 选择下一代（**C9 违规点**） | §4.3 Eq.5 p6 |
| **Success Memory** | (state_hash, action) → score_delta | 高分动作查表 | §4.1 p5、App.J.1 p26–31 |
| **Failure Memory** | 「state 与 score 均不变」的动作序列 → verbal guardrail | 循环/死路规避 | App.J.2 p31–32 |
| **J-TTL 协议** | 同游戏 K=50 连续集、T=110 步上限、每集重置到同初始态 | 评估协议 | §3 p4、App.C.1 p17 |
| **AUC 度量** | ΣR(e)/(K·Rmax) | 学习曲线量化 | §3 Eq.4 p4 |

### 2.4 关键表示与数据结构
- **配置元组** χ = (p, M, h, u)：policy prompt / deployment-time memory / hyperparameters / tool-use routines（§4.1 p5）。
- **success memory.json**：`state_hash → (action, score_delta)`，由 Evolver 逐集程序化解析 transcript 写入（App.J.1 p31）。
- **failure memory**：检测「动作后 state 与 score 均不变」的循环序列，**不存 DB**，而是直接改写 prompt 加 "Known Dead Ends / Wasted Actions" 段（App.J.2 p31–32）。
- **生成的 `extract_state(game_history)`**：可执行 Python 函数，从原始冗长历史抽 milestone 摘要字符串（如 `"Milestone: Found the map."`），降低每步上下文带宽（§4.1 p5、App.H p25）。
- **轨迹** τ(e) = (o₁,a₁,r₁,…,o_T,a_T,r_T)（Eq.1 p4）；游戏建模为 POMDP (S,A,T,R,Ω,T)（§3 p4）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| J-TTL 6 games AUC（gemini-2.5-flash） | Static 0.11 / Memory 0.13 / Reflexion 0.32 / EvoPrompt 0.34 / GRPO 0.30 | **EvoTest 0.47** | Table 1 p7 |
| J-TTL 6 games AUC（claude-4-sonnet） | Static 0.12 / EvoPrompt 0.36 / GRPO 0.26 | **EvoTest 0.50** | Table 1 p7 |
| Detective / Library（胜负） | 所有基线均**未赢任何一局** | EvoTest **0.94/0.77** vs Reflexion 0.58/0.41 | Table 1 p7 |
| 5-seed 均值（flash） | Static 0.11±.01 / EvoPrompt 0.35±.03 / GRPO 0.31±.03 | **EvoTest 0.48±.01** | Table 8 p22，**5 random seeds** |
| 组件消融（Detective） | w/o Prompt **0.52** / w/o UCB 0.68 / w/o Memory 0.82 / w/o Hyperpara 0.89 / w/o Tool-Use 0.91 | Full **0.94** | Table 3 p9（prompt 通道贡献最大） |
| Evolver LLM 消融（Detective） | qwen3-8b 0.68 / qwen3-32b 0.82 / deepseek-r1 0.90 | o3 **0.94** | Table 4 p9 |
| 同骨干对照（actor=qwen3-32b） | SFT 0.24 / GRPO 0.31 | EvoTest(qwen evolver) **0.35**；+o3 evolver **0.40** | Table 6 p10 |
| 单次学习更新成本 | SFT/GRPO **5–10 min，4×H100** | EvoTest **20–30 s，1 LLM call，CPU+网络** | Table 2 p9、Table 7 p22、App.C.2 p17 |

> 注：Zork1/Zork3 等难游戏 EvoTest AUC 仍近 0（0.14/0.35），6 局中仅赢 2 局——增益高度集中在中低难度、奖励较密的游戏上（推断，Table 1 p7）。

### 2.6 论文自陈局限与边界条件（App.A p16–17，四条）
1. **不修改权重的代价**：学习被限制在**符号层而非参数层**；无法教出骨干没有的**低层推理模式**，性能上限被冻结骨干的固有能力封顶。作者建议未来 **hybrid**：EvoTest 做快速集间适应 + **极慢后台微调**逐步增强核心能力（p16）。
2. **任务专用过拟合 vs 通用技能获取**：学到的策略与 verbal guardrail（如 `unlock door with key`）是对**当前任务实例的战略性过拟合**，**brittle**，对轻微环境变化（如钥匙换房间）不泛化；未来方向 = 把符号策略**收集并抽象成通用技能库**（p16）。
3. **依赖强 Evolver Agent**：性能与 Evolver LLM 能力正相关（Table 4），成功依赖一个**昂贵 optimizer 模型**（p16）。
4. **演化搜索空间复杂**：只用简单 **(1+m) 演化策略 + UCB**，可能收敛到局部最优；未来可探索种群式演化、quality-diversity、程序合成（p17）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 域是文本冒险游戏，动作接口就是自然语言命令（§3 p4）；但 **Act–Evolve 双相循环与 SSEA 快环/慢环结构同构**（Fig.1 p3） | 把演化对象从「游戏命令策略」换成「生存行为流的结构化信号」；机制整体平移 |
| **C2** 自然语言只作观察员接口 | **✗** | 自然语言**就是**动作与观测通道；Evolver 是 **LLM，以语言改写 prompt**，语言处于**改进闭环内**（§4.2 p5、App.H p25） | 删除语言 Evolver，改由 `ExperienceCompiler` 承担；`extract_state` 式工具保留但输入输出改结构化张量；语言只留审计/观察员面 |
| **C3** 权重/记忆/技能三分离 | **✓（强证据）** | 骨干 LLM **冻结、不可训练**（§4 p4、App.A p16）；记忆**外置**为 success/failure DB；技能/策略落在外部的 prompt+超参+工具代码上。三者来源与生命周期分离 | 唯一改造点：χ 把 p/M/h/u **打包成单一配置联合演化 + 联合选择**，与「必须分置」有张力 → 提案与应用须按通道分置（ΔS/ΔM/ΔR/Δθ 各走各的门） |
| **C4** 低算力低带宽 | ✓ | 无梯度、**无 GPU**（CPU+网络）；单次更新 **20–30 s / 1 次 LLM 调用** vs GRPO 5–10 min / 4×H100（Table 2 p9、Table 7 p22）；`extract_state` 把冗长历史压成 milestone 字符串（§4.1 p5） | 扣分点：Evolver 是**前沿大模型 API（o3）**，绝对算力不低；SSEA 慢环若引此形状，须限定 Evolver 规模并设预算硬上限 |
| **C5** 精准回忆历史 | ◐ | 有结构化可检索记忆（`state_hash → action`，精确查表，App.J p31）；但**键是精确哈希，泛化为零**，作者自陈 brittle（App.A p16）；failure 记忆**不进 DB** 而是烧进 prompt | 键须放宽为语义/特征键；failure 模式也须结构化入库（而非只写 prompt）；与 LightMem/A-MEM 式可检索条目并存 |
| **C6** 可自主修改自身 | ◐ | 确实修改自身配置，含**生成可执行 Python 工具代码** `extract_state`（App.H p25）；但**四权不分**：Evolver 握提案、UCB 握应用/选择，无独立边界权与验证权 | 纳入四权拆分：提案归慢环、边界归预算、验证归四级门、应用归原子升版 |
| **C7** 可保存/恢复/变异/继承 | ◐ | 配置被版本化，子配置**继承父配置更新后的记忆**（"This updated memory M(e+1) is then inherited by all child configurations" §4.2 p6）；但**无跨个体继承、无种群繁衍/淘汰**，是 (1+m) 单线演化，学习内容随任务重置 | 配置序列化进 GenePackage 作格式参照；**记忆内容不遗传**（见 C8）；繁衍/淘汰交 Gene Manager |
| **C8** 给基因先验，不给知识语料 | ◐ | 演化出的 prompt/记忆装的是**后天任务知识**（walkthrough、具体动作、guardrail），属知识而非结构先验；但这些知识是 **session-local、不跨代**，故不直接违反 C8；作者未来方向「抽象成技能库」若跨代则须过滤 | 跨代只传**结构**（配置模式、演化算子、超参空间），不传**内容**（具体动作/walkthrough）；与 HeritableFilter 明确隔离 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（硬冲突）** | **UCB 对平均环境得分 μ̂(χ) 取 argmax + 探索奖励**（Eq.5 p6）——显式**评分 + 排序 + 选择**；整个「fitness」= 游戏最终分 R(e)（App.D p20） | 选择压力确实来自**环境侧可验证结果**（游戏最终分，本属①层信号），但 EvoTest 把它**变成「打分并排序」的机制**，正是 C9 禁止的。改造：环境分只作**事实**（类比 `Feedback.energy_change`）；**去掉 argmax/UCB**，改为**淘汰**——保留 parent 除非 child 过不了合法性门；选择推迟到生态阶段的种群淘汰 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 无新算子，骨干 LLM 借用；创新在 L2（双相循环+四通道配置）、L3（无梯度整机演化）、L4（配置版本化） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子，用现成 LLM 骨干（gemini/claude/o3/qwen） | 符合「L1 借用」立场 |
| **L2 信息流层** | Act–Evolve 双相循环（Fig.1）、四通道配置 χ、memory 交互逻辑、状态抽象工具 | **高**：与 SSEA 双环、注入面天然同构，可直接丰富慢环语义 |
| **L3 学习层** | **无梯度整机演化**（Evolver）、叙事式 credit assignment、组件消融 | **高**：慢环 ΔS 的提案回路 + 一个「不更新权重也能改进」的实证形态 |
| **L4 演化层** | (1+m) 演化 + UCB 选择、配置版本化、记忆继承（无繁衍/淘汰/跨代） | 中：为 GenePackage 提供内容与格式参照 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| Actor Agent + χ | **快环 FSL 的只读不可变配置快照** |
| Evolver Agent | **`experience_compiler.py`（ΔS 提案）+ 慢环 SEL** |
| success / failure memory | **`memory_system.py`** 的写入与检索（C5）——success 表做精确查表、failure 表做循环检测 |
| `extract_state` 生成式 Python 工具 | **技能/工具层候选表示**（PSN 式可执行技能） |
| UCB Selection | **✗ 不进模型**；由 `verification_gate.py` 只判合法性 + 模型外淘汰替代 |
| J-TTL 协议 + AUC | `experiments/` 验收实验协议参照 |
| 复杂度账本 Eq.6–8 + Table 2/7 | **睡眠期预算建模**（回顾侧） |

### 3.4 债务与验收实验对应
- **「睡眠期计算预算未定义」→ 直接回应（回顾侧）**：给出可量化账本 `CostEvoTest = T·CostLLM(C̄,La) + CostLLM(τL, L_config)`（Eq.8 p21），即**每周期一次 acting 前向 + 一次 evolution 前向**，无梯度显存；实测 20–30 s / 1 次 LLM 调用（Table 2 p9）。但**未定义触发者/周期/停机判据**（用固定 K=50），停机侧仍需 FLEX 的 logistic 曲线补。
- **「技能/记忆表示够不够」（0/33）→ 部分回应**：EvoTest 给**四通道表示**（prompt 文本 + 记忆 DB + 超参 + **可执行代码**），消融证明多通道优于单通道（w/o Prompt 0.94→0.52 掉最多，但 memory/hyper/tool 通道也有正贡献，Table 3 p9）；但作者自陈学到的技能 brittle、任务专用、不泛化，并把「抽象成通用技能库」列为**未来工作**（App.A p16）→ **未解决，只提供方向与反面证据**。
- **记忆二级门常量阈值（债务 22）**：failure memory 用「state 与 score 均不变」作写入/规避触发，是一版**结构化「何时该写」判据**。
- **`retrieve` 键收窄（召回精度上限低）**：**反面证据**——`state_hash` 精确匹配泛化为零、作者自陈 brittle，警示纯哈希键不可取。
- **判据形状错（债务 25/26/27）**：AUC/学习曲线 + 组件消融提供「机制计数 → 行为差」分档的仪器参照。
- 可服务的验收实验：**实验 3（技能固化）**的表示通道改造；**实验 7（睡眠期编译）**的预算建模。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **无梯度整机演化**（Δθ 的替代形态，骨干冻结） | 思想 + 证据 | 仅借思想 / 直接引用证据 | 慢环 ΔS | 证明不更新权重也能持续改进（支撑 C3 与 DEFERRED Δθ） | 高 |
| 2 | **四通道配置 χ=(p,M,h,u)** 联合演化 | 表示 | 改造移植 | ExperienceCompiler / GenePackage | 技能表示太窄（0/33） | 中 |
| 3 | **success（state→action→delta）+ failure（循环→guardrail）双库** | 表示 | 改造移植 | memory_system | C5 记忆写入/检索；债务 22 | 高 |
| 4 | **可执行工具例程**（Evolver 生成的 `extract_state` Python） | 工程实现 | 改造移植 | 技能/工具层 | 技能可执行表示 | 中 |
| 5 | **复杂度账本**（Eq.6–8 + Table 2/7：1 次前向/周期、CPU+网络） | 度量 | 直接引用 | 睡眠期预算建模 | 睡眠期预算未定义 | 高 |
| 6 | **J-TTL 协议**（K 连续集 / 同初始态 / AUC） | 协议 / 基准 | 改造移植 | experiments 验收 | 验收实验协议缺失 | 高 |
| 7 | **组件消融方法**（w/o 每通道，先看分母） | 方法 | 直接移植 | experiments | 判据形状（债务 25/26/27） | 中 |
| 8 | **叙事式 credit assignment**（整段 transcript 作信号） | 思想 | 仅借思想 | 慢环 | 稀疏奖励下信号稀缺 | 中 |
| 9 | **「任务专用过拟合 / brittle」反面证据** | 证据 | 直接引用 | 支撑 C7/C8 决策 | 拒绝跨代知识继承 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（逐条，对应 3.1 中 ✗/◐）**：
  1. **C9 ✗（最硬）**：UCB 对平均环境得分 argmax + 探索奖励（Eq.5 p6），是显式**评分 + 排序 + 选择**。**注意**：选择压力来自环境侧可验证结果（游戏最终分），这本属 C9 的①层信号；但 EvoTest **把它转成了打分排序机制**，因此违规。→ 必须改造：环境分只作事实，选择改为「合法性门 + 模型外淘汰」，去掉 argmax。
  2. **C2 ✗**：自然语言在控制环（命令即动作）与改进环（LLM Evolver 改 prompt）内。
  3. **C1 ◐**：非生存控制域（文本游戏）。
  4. **C3 张力**：χ 把 p/M/h/u 打包联合选择，需按通道分置。
- **隐含假设与失效条件**：
  - 假设环境能给**可验证的最终标量分** R(e)（App.D p20）；SSEA 只有淘汰函数，映射不显然。
  - 假设骨干 LLM 已具备任务所需的潜在知识（App.A p16）——骨干越强增益越大（Table 10 p37）；弱骨干上增益衰减。
- **算力 / 带宽 / 工程代价**：
  - 正面：单次更新 20–30 s、1 次 LLM 调用、**CPU+网络无 GPU**（Table 2 p9、Table 7 p22）。
  - 负面：**依赖前沿大模型 Evolver（o3）**；Evolver 弱则性能掉（Table 4：o3 0.94 → qwen3-8b 0.68）。慢环算力被大模型调用主导，与 C4「低算力」有张力。
- **搬运后的可能退化模式（若失败，会以什么形式失败）**：
  - **任务专用过拟合**：学到的策略/guardrail 对轻微环境变化失效（作者自陈，App.A p16）——SSEA 中表现为「换个场景技能全废」。
  - **静默污染**：failure 记忆烧进 prompt 且不可定点删除（对照 Misevolve 记忆/参数路径红队清单）。
  - **Evolver 依赖放大**：慢环成本与 Evolver 模型规模绑定，弱化骨干即失能。
  - **UCB 改造风险**：去掉 argmax 后「不劣于现状」的保证需另建（合法性门只保证「不破坏」，保证不了「选得好」）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **最直接同工（被替代方）** | **SelfConsolidation（EvoSC）** | EvoSC 卡片已把 EvoTest 列为「**替代（SSEA 更友好）**」并建议优先走 EvoTest 路线（其卡 §6.1）；本篇正是该建议的落地对象——EvoSC 用**梯度蒸馏进权重**，EvoTest **无梯度、产物可检查可回滚**，正面对照 |
| **互补（重放评估场）** | **Dream-RSI** | Dream-RSI 提供「发现历史即重放模拟器」的**确定性廉价评估**；EvoTest 提供**四通道提案**。两者共享「一次在线 → 多次离线」主题，可拼成「提案（EvoTest）→ 评估（Dream-RSI 重放）」 |
| **互补（记忆组织 + 停机判据）** | **FLEX** | FLEX 的 **golden/warning 双区** ≈ EvoTest 的 **success/failure 双库**；FLEX 的 **logistic 增长曲线**可补 EvoTest 缺的**停机判据**（EvoTest 用固定 K=50，无自适应停） |
| **互补（选择/淘汰与风险治理）** | **Misevolve / MemEvolve** | EvoTest 的 UCB 选择是 C9 违规点，需用「淘汰」替代；Misevolve 提供误演化（模型/记忆/工具/工作流四路径）红队清单 |
| **前置依赖（形式化母框架）** | **ADAS**（演化搜索） | ADAS 的「代码空间 × 搜索 × 评估」是 EvoTest 配置搜索的**形式化母框架**；EvoTest = ADAS 在 TTL 设定下的一个具体实例（搜索空间 = χ，评估 = J-TTL AUC） |
| **互补（自指北极星）** | **Gödel Agent** | Gödel Agent 提供**自指递归自改进的形式化北极星**；EvoTest 是其中「只改外部配置、不动权重」的一个**受限、可工程化的实例**（且确实自生成工具代码） |
| **同族（回顾式经验复用）** | **RetroAgent**（同批卡片；**本目录暂无卡片**，机制待核） | 与 EvoTest 的 **Evolve 相位**同属「集后回顾」，具体机制需补卡后确认 |
| **技能侧对接** | **PSN / SkillWeaver / Voyager** | EvoTest 的 prompt-section 技能与可执行 `extract_state` 可对接 PSN 的**带契约技能网络** |
| **对照（经典外环，被超越）** | **Reflexion** | EvoTest 直接以 Reflexion 为基线并显著超越（Detective 0.94 vs 0.58，Table 1 p7）——是「多通道 > 单通道」的**实测证据** |

### 6.2 推荐组合方案
- **组合（首选）**：**EvoTest（四通道提案）+ Dream-RSI（确定性重放评估）+ FLEX（golden/warning 双区 + logistic 停机）+ VerificationGate（只判合法性）**。
  - **接口形态**：慢环读 episode/经验缓冲 → **EvoTest Evolver 生成多通道候选** → **Dream-RSI 在已记录历史上确定性重放评估**（不重跑环境）→ **FLEX 双区组织 + 增长曲线判停机** → **Gate 合法性过滤** → 原子升版；**选择由模型外淘汰替代 UCB**。
  - **组合后新增能力**：无梯度、多通道、常数带宽的**慢环提案-验证-组织回路** + 可量化预算账本 + 停机判据。
  - **新增风险**：Evolver 依赖大模型；C9 需自建淘汰替代 UCB；域迁移（文本游戏 → 生存）未证。
- **组合（极简版，只取证据）**：**EvoTest 的预算账本 + 双库记忆** 单独接入 SSEA 慢环——不引 Evolver LLM、不引 UCB，只搬「1 次前向/周期」的记账与「success/failure 双库」的表示。

### 6.3 本篇在组合中的典型角色
- **慢环「无梯度整机演化器 / 提案引擎」** + **计算预算账本提供者**：一端接快环经验（记忆），一端向技能库/验证门供给经过叙事分析的多通道结构提案，同时给出「每周期一次前向」的预算形状，直接服务 SSEA「睡眠期预算未定义」缺口。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击「测试时学习 + 演化 + 无梯度」与 SSEA 慢环 ΔS、以及「睡眠期预算」缺口；扣 1 分因域为文本游戏而非生存（实测） |
| 立场兼容性 | **2** | C3/C4/C10 强支持、C5/C6/C7/C8 部分支持；但 **C9 ✗（UCB 评分排序）、C2 ✗（语言在环）、C1 ◐** 三处冲突（实测于原文） |
| 可搬运性 | **4** | 框架概念轻、配置元组与双库记忆可干净拆出、**已开源**；但 Evolver LLM 依赖重、C9 改造需重设计选择规则（推断） |
| 证据强度 | **4** | 6 游戏、5 seeds（Table 8）、完整组件消融（Table 3/4/5）、同骨干受控对照（Table 6）、成本分析（Table 2/7）；扣分因：**6 局仅赢 2 局**、Zork1/Zork3 近 0、收益依赖任务专用评分 |
| 组合价值 | **4** | 与 SelfConsolidation/Dream-RSI/FLEX/ADAS/Gödel Agent/PSN/Misevolve 均有明确接口（推断） |
| 落地成本 | **3** | 概念与实现成本低（无梯度、纯 API）；但需替换 UCB、需承担 Evolver 大模型调用、C9 改造是主要成本（反向口径） |

（合计 21/30，落在「B 零件采用」区间。）

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用三件：① **无梯度整机演化**的证据与形状（支撑 C3 与 Δθ 缓议）；② **四通道配置 χ + success/failure 双库记忆**表示；③ **计算预算账本 + J-TTL 协议**。**明确不采用**：UCB 评分选择（C9）、语言 Evolver 在控制/改进环（C2）、任务专用过拟合产物跨代（C7/C8）。
- **优先级：P1**（与 SelfConsolidation 同级；SSEA 目前最紧的仍是债务 26 修复，本篇可在其完成后接入）。

### 建议动作（具体到原型 / issue / 实验）
1. 用 Eq.6–8 的账本给**慢环回顾侧预算建模**（每周期 1 次前向），在 `rules` 里写死上限与「超预算降级」路径（`rules` 当前零消费者，需先接消费者）。
2. 把 **success/failure 双库**作为 `memory_system.py` 写入候选，含「state 与 score 均不变」的**循环检测判据**（修债务 22/25）。
3. 做 **UCB 替换实验**：把选择改为「Gate 合法性 + 模型外淘汰」，验证不劣于 UCB（守 C9）。
4. 把 `extract_state` 式**可执行工具例程**作为技能表示的一个候选通道，**重跑实验 3 看 0/33 是否变化**。
5. 加变异测试守卫：扫描模型内任何排序/打分入口（守 C9）。

### 最小验证实验
- **双臂 / 消融设置**（≥8 个固定 seed）：
  - A 单通道（仅 prompt / 仅技能）；
  - B **四通道联合**（prompt+记忆+超参+工具）；
  - C 四通道 + **UCB 选择**；
  - D 四通道 + **淘汰替代选择**。
- **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：
  1. **机制计数**：提案数、过门率、每周期前向次数与耗时（**先确认分母真的非零**，对齐 Dream-RSI 卡的纪律）；
  2. **行为差**：逐帧动作差（沿用债务 21 第三档判据）——**主判据**；
  3. **淘汰结果**：模型外环境淘汰率（注意危险回避率已饱和 0.9814，两臂区分度不足，**不可作主判据**）。
- **预期与证伪条件**：
  - 预期：**B > A**（多通道有效，破 0/33）；**D ≥ C**（淘汰可替代 UCB，守 C9 不损性能）。
  - 证伪：若 **B 与 A 无差**，则四通道件不进主链，只保留预算账本与双库记忆；若 **D 显著差于 C**，则 C9 与性能存在真实张力，**须上报作者决策**（不得静默引入 UCB）；若行为无差异，按纪律**先怀疑尺子**，不得直接读作「机制无效」。

---

## 9. 待确认问题

### 需作者 / 团队决策
1. **UCB 在 C9 下如何替换**、同时保留「不劣于现状」保证？（选择是否推迟到生态种群淘汰？第一阶段是否需要确定性的「应用/不应用」规则？）
2. **Evolver 由谁承担**？C2 禁止语言在环，SSEA 需一个非语言等价物（`ExperienceCompiler`）；若坚持不用 LLM，则「叙事 credit assignment」整体失效，本篇只剩记忆/预算两件。
3. **演化出的技能是否允许跨代继承**？（C8 判据：内容 vs 结构；作者未来方向「抽象成技能库」直接触及此问）
4. `extract_state` 由 LLM **生成代码**并在环内执行——边界权/沙盒/回滚如何界定？

### 需补查的文献 / 资料
5. **RetroAgent**（同批卡片）：本目录**暂无卡片**，需补卡后确认其与 EvoTest「Evolve 相位」的确切关系。
6. 作者同族后续工作 **EvoClinician**（arXiv:2601.22964，多轮医疗诊断的 test-time evolutionary learning）与 **Just-in-Time RL**（arXiv:2601.18510，无梯度持续学习）——是否给出 TTL 的更细机制。
7. 是否有「无评分选择」的演化搜索工作（quality-diversity / novelty search），用于替换 UCB 补 C9。

### 需人工核对的公式 / 实现
8. Eq.5 UCB 的 β、N、n(χ) 具体取值与「配置」计数口径（同一 χ 文本完全相同才算同一 arm？）论文未给。
9. Table 1 中 SFT/GRPO 列只有 4 个数字（缺 Library/Temple 两列），口径需核对（p7）。
10. App.J 的 `state_hash` 具体哈希方式（全文本 hash？截断？）影响可复现性，论文未细述。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "we present EvoTest, an evolutionary test-time learning framework that improves an agent **without any fine-tuning or gradients**—by evolving the entire agentic system after every episode" | p1（摘要） |
| "our method is the only one capable of winning two games (Detective and Library), while all baselines fail to win any" | p1（摘要） |
| Fig.1：Act–Evolve loop，Evolver 对整段 transcript 做 "**gradient-free, whole-system evolution** on the agent's entire configuration" | p3（Fig.1） |
| "Unlike methods that perform gradient-based updates on model weights, EvoTest operates on a **fixed, non-trainable backbone LLM**." | p4（§4 开头） |
| 配置定义：χ = (p, M, h, u) = Policy Prompt / Deployment-time Memory / Hyperparameters / Tool-Use Routines | p5（§4.1） |
| 记忆更新："This updated memory M(e+1) is then **inherited by all child configurations**." | p6（§4.2） |
| UCB 选择式：χ(e+1) = arg max [ μ̂(χ) + β√( log N / (1+n(χ)) ) ] | p6（§4.3 Eq.5） |
| "credit assignment via **narrative analysis**"（相对 backprop 的 data-efficient 机制） | p9（§5.2） |
| Table 2：单次学习更新 SFT/GRPO **5–10 min**（4×H100） vs EvoTest **20–30 sec / 1 LLM call** | p9（Table 2） |
| Table 3 消融（Detective）：Full 0.94 → w/o Prompt **0.52** / w/o UCB 0.68 / w/o Memory 0.82 | p9（Table 3） |
| Table 8：**5 random seeds** 平均，EvoTest 0.48±.01，Static 0.11±.01 | p22（Table 8） |
| 复杂度：CostEvoTest = T·CostLLM(C̄,La) + CostLLM(τL,L_config)；硬件 **CPU + Network** vs GRPO 的 High-VRAM GPU | p21（Eq.8、Table 7） |
| App.A 局限 1："constraining learning to the **symbolic level, rather than the parametric level** of the model's weights"；"cannot instill fundamentally new, low-level reasoning patterns" | p16（App.A） |
| App.A 局限 2：学到的策略是 "a form of **strategic overfitting** to the current task instance ... **brittle** and may not generalize"；未来方向 "build a **library of general-purpose skills**" | p16（App.A） |
| App.A 局限 3："strong **dependency on the reasoning capabilities of the Evolver LLM**"（Table 4 佐证） | p16（App.A） |
| App.H：Evolver master prompt 四段——Prompt / Memory updates / Hyperparameter / Tool-use（含生成 `def extract_state(game_history)` Python） | p24–25（App.H） |
| App.J.1：success memory.json = `state_hash → (action, score_delta)` | p31（App.J.1） |
| App.J.2：failure memory 检测「state 与 score 均不变」的循环 → 写入 prompt 的 "Known Dead Ends / Wasted Actions" | p31–32（App.J.2） |
| App.C.1：K=50 episodes/session，T=110 steps/episode，每集重置到同初始态 | p17（App.C.1） |
| App.C.2：梯度自由方法**无需专用硬件**（CPU+网络）；SFT/GRPO 在 **4×H100** 上训练 | p17（App.C.2） |
