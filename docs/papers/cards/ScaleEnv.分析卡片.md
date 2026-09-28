# 论文分析卡片 · ScaleEnv

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-02-06 ScaleEnv Scaling Environment Synthesis from Scratch for Generalist.pdf` |
| 标题 | **ScaleEnv: Scaling Environment Synthesis from Scratch for Generalist Interactive Tool-Use Agent Training** |
| 作者 / 机构 | Dunwei Tu\*、Hongyan Hao\*†、Hansi Yang\*、Yihao Chen†、Yi-Kai Zhang†、Zhikang Xia、Yu Yang、Yueqing Sun、Xingchen Liu†、Furao Shen、Qi Gu、Hui Su、Xunliang Cai；南京大学（计算机软件新技术全国重点实验室 / 人工智能学院）、美团、哈尔滨工业大学（深圳）、华东师范大学。通讯：Hongyan Hao、Qi Gu（美团）；† 标注「实习期间于美团完成」 |
| 发表时间 / 出处 | arXiv:2602.06820v1 [cs.AI]，2026-02-06；PDF 标注 Preprint. February 9, 2026 |
| 论文链接 | arXiv:2602.06820 |
| 代码链接 | **无**（检索全文 p1–27 未见 GitHub / 项目页 / 数据发布声明；附录 D 仅给「Job Seeking」域的部分代码清单 Listing 1–2） |
| 标签 | 环境从零合成 · 可执行图（Tool Dependency Graph）· Procedural Testing · 可执行动作验证（EV）· 干扰项注入 · 依赖感知 BFS · LLM 门控扩张 · 规则式奖励 · 域规模缩放曲线 · GRPO |
| **应用裁决** | **B 零件采用**（搬「规则式状态判据 + Procedural Testing 通道准入 + 工具依赖图/依赖感知扩张 + 干扰项注入 + 环境即确定性代码」；**不搬** LLM 策略本体、NL 用户模拟器、GRPO 奖励回路） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：提出 ScaleEnv——一个**完全不依赖外部文档与人工介入**（from scratch）、只用「域关键词」起步就能造出**可执行、可验证、可交互**工具使用环境的合成框架：先由 LLM 自顶向下生成 tool/database schema 并实现为**可执行代码**，用 **Procedural Testing**（Code/Test/Debug 多智能体，三类判定 Success / Anticipated Rejection / Unexpected Failure）保证工具可靠执行，再合并为 **Tool Dependency Graph** `G`；第二阶段用「可执行种子工具链 + 干扰项注入 + 依赖感知 BFS 扩张 + LLM 门控新链」把线性路径「滚雪球」成复杂非线性子图，最后用**规则式评估器**（比对最终数据库状态 `s^env_T` 与真值 `s^env_gt`）作奖励，在 16 个合成域上以 GRPO 训练 Qwen3-SE，在**完全 OOD** 的 τ²-Bench / VitaBench 上取得稳定提升，并给出「**环境多样性比任务数量更关键**」的域规模缩放曲线（p1、p3–8）。
- **对 SSEA 的意义**：它是环境合成族里**判据形状最干净的一件**——把「成功」定义成**环境侧确定性代码对最终状态的检查**（而非 LLM 评委、而非输出字符串），并且**没有** GenEnv / Agent-World 那条「被测个体失败 → 环境难度」的反馈通道（其难度/复杂度由**结构指标 + 固定 oracle 可行性**决定）；但它**不回答「合成环境是否真有判别力」**——它的判别力靠**外部基准**证明，而非环境自身，这恰好是 SSEA「判据饱和 / 指标全绿但行为没变」的同一个病灶，必须补装校准器后才能用。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：把 LLM 从「文本生成器」变成「智能体」需要**动态、有反馈、带可执行工具**的环境来训练；但可交互环境**极度稀缺**，且现有合成方法在**环境多样性**与**可扩展性**上都有明显上限（p1 摘要）。
- **它指出的既有方案缺陷**（p1 Introduction 明列两大挑战）：
  1. **Realism（真实感）**：LLM 直接合成的工具**功能不可靠**；**LLM 模拟器易严重幻觉**（引 Liu 2024、Li 2025）。作者主张：环境必须扎根于**已验证的可执行代码**，而非概率式文本生成。
  2. **Scalability（可扩展性）**：合成**不能**依赖有限的外部文档或人工介入（引 Cai 2025 = AutoForge）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **「从零」= 从域关键词到可执行图**：不需要真实 API、不需要外部文档、不需要人工——域关键词 → tool/database schema → 可执行代码 → 依赖图 `G` → 任务（p1、§4.1 p3–4）。环境与任务被**显式解耦为两阶段**（Executable Graph Construction / Task Instantiation），保证模块化与可扩展（§4 p3）。
2. **可靠性靠「执行」而非「生成」**：工具正确性用 **Procedural Testing** 判定（跑在匹配的数据库实例上，看三种结果）；任务可解性用**可执行种子链 `C1` 真跑一遍**确认；判据 `R` 由 `C1` 执行后的**最终状态**派生——「先可执行、再谈语义」（§4.1.2 p4、§4.2.1 p5）。
3. **难度/复杂度用「结构量 + 固定 oracle」而非「被测者表现」**：扩张由门控 `π(|D_n|, c(H_n), g(D_n))` 决定，其中 `c(H_n)` 是**图的节点/边结构复杂度**、`g(D_n)` 是**一个固定强模型（Qwen3-235B-A22B，best-of-k，k=16）的可行性成功率**——**不含被训练智能体的任何表现信号**（§4.2.2 p6）。这一点与 GenEnv/Agent-World 的「难度对齐共演化」是**结构性区别**。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| **两阶段解耦** | 域关键词 → (可执行图 `G`) → (任务集) | 模块化、可扩展 | §4 p3 |
| **Top-Down Tool Schema 合成** | 域名词 → 工具接口集 `T`（描述/参数/pre-post 条件） | 定动作空间 | §4.1.1 p3 |
| **Database Schema 派生 + tool-db 映射** | tool schema → 数据库表结构 + 完整性约束 + 每工具关联表 | 反推状态结构 | §4.1.1 p3 |
| **规则式奖励 `R`（三档匹配）** | 最终状态 `s^env_T` + 真值 `s^env_gt` → 二值判定；列分三类：**Exempt Fields**（动态 ID/可选列）/ **Hard Constraints**（时间戳/数量，字符级或数值严格相等）/ **Semantic Alignment**（描述性文本，模糊语义匹配） | **判据形状**：判环境状态而非输出字符串；明确拒绝 LLM-as-a-judge（因其贵且易 reward hacking） | §4.1.1 p4 |
| **Database 实现与验证** | schema → 可执行 DB 代码 + 测试脚本；失败 → Debug Agent 迭代至全过 | 稳定存储层 | §4.1.2 p4 |
| **Procedural Testing** | 工具代码 + 匹配 DB 实例 → 三类结果：**Success**（状态转移严格匹配）/ **Anticipated Rejection**（按 schema 抛预定义异常）/ **Unexpected Failure**（其余 → Debug Agent 修工具或修 DB 实例） | **通道可靠性准入** | §4.1.2 p4 |
| **Tool Dependency Graph `G`** | 已验工具两两关系 → 有向边；三维依据：**data flow**（参数传递）/ **pre-post conditions**（逻辑前置）/ **state dependencies**（共享表） | 任务合成的骨架 | §4.1.3 p4 |
| **两条硬约束** | — | **Entity Consistency**（跨表实体一致）+ **Interaction Completeness**（对**任意**合法动作 `a∈A_tool` 都必须返回有效观测，不得因缺条目/实现缺口而中断探索） | §4.2 p4 |
| **可执行种子链采样 `C1=(a_1..a_k)`** | `G` + DB schema → **以可执行代码表示**的参考解链 | 联合建模「工具序列 + 参数」，天然满足 data flow | §4.2.1 p5 |
| **干扰项注入（distractor）** | 初始状态 `s^env_0` → 注入与真值轨迹**功能正交**的额外记录，密度随任务复杂度缩放 | 逼出**精确信息过滤**能力 | §4.2.1 p5 |
| **指令合成（grounded）** | 已验证 `C1` + `s^env_0` → 用户画像 + 指令 `u`；`R` 由 `C1` 执行后的 `s^env_gt` 派生 | 防外部先验/幻觉 | §4.2.1 p5 |
| **依赖感知 BFS 扩张** | `H_1=K(C_1)` 起，仅当新节点 `v` 的输入/输出依赖能被 `H_1` 子集满足才加入（避免 **dependency dead-end**） | 保可解地扩图 | §4.2.2 p5–6 |
| **LLM 门控链扩张 `π`** | `(|D_n|, c(H_n), g(D_n))` → 兼容分 `p∈[0,1]`；`p≥τ` 才采新链 `C_{n+1}` | 平衡多样性与可解性 | §4.2.2 p6 |
| **结构复杂度 `c(H_n)`** | `c(H_n) = (|V_{H_n}| + λ|E_{H_n}|)/S_sat`，`λ=0.5`、`S_sat=50` | 环境结构充分度指标（**非模型标尺**） | §4.2.2 p6 |
| **可行性分 `g(D_n)`** | 固定 oracle（Qwen3-235B-A22B + best-of-16）在候选工具集里找可执行链的**成功率** ∈[0,1] | 可解性下界（**以另一个模型为标尺**） | §4.2.2 p6 |
| **最小探索空间约束** | 若 `|H_n|<20` → 随机采有效辅助链并入 | 保底探索空间 | §4.2.2 p6 |
| **GRPO 训练** | 合成域 + 可验证任务 → 组相对优势（式1、式2） | 参数面更新 | 附录 C p13 |
| **NL 用户模拟器** | 意图 `u` → 自然语言反馈 `O_resp` | 闭合多轮交互环 | 附录 C p13 |

### 2.4 关键表示与数据结构
- **POMDP**：`M=⟨S,A,O,T,R⟩`，状态 `s_t=(s^env_t, h_t, u)`（环境状态 + 交互历史 + 用户意图）；`A=A_resp∪A_tool`；`O=O_resp∪O_tool`；**工具动作 `a∈A_tool` 触发对 `s^env_t` 与 `h_t` 的确定性更新**，而 `a∈A_resp` 只更新 `h_t`、不动 `s^env_t`；终局奖励 `r=R(s^env_T,u)`（p3）。
- **环境 = 可执行代码 + 数据库对象**：DB 用 Pydantic 模型 + `ThreadSafeBase` 实现（如 `JobApplication`、`ApplicationNote`…），主键以 `@with_instance_key(...)` 标注；工具为读写 DB 的 Python 方法（附录 D Listing 1–2，p14–19）。
- **工具 schema**：`name / description / pre-condition / post-condition / parameter`（Fig.1 p3；附录 A Table 6 p11 给实例）。
- **数据库 schema**：表名 / 字段 / 类型 / 约束（主键、外键、默认值）（附录 A Table 7 p12）。
- **Tool Dependency Graph `G`**：有向图，边 = 因果依赖（参数传递 / pre-post / 共享表）。
- **训练宇宙**：`U={(B_k, ψ_j) | ψ_j∈Tasks(B_k)}`（附录 C p13）。
- **成本计量**：单域基础 ≈546k tokens；单任务 ≈93.2k tokens（附录 B.2 Table 9 p13–14）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **Table 1 零样本泛化**（τ²-Bench Retail/Airline/Telecom；VitaBench Cross/Delivery/Instore/OTA） | Qwen3-8B / Qwen3-32B | Qwen3-**SE**-8B：50.9(+12.5) / 37.5(+7.0) / 27.2(+5.7) ‖ 3.0(+1.5) / 26.3(+8.0) / 23.8(+9.0) / 7.0(+2.5)；Qwen3-**SE**-32B：63.6(+4.1) / 48.0(+0.0) / 30.9(+3.7) ‖ 10.8(+5.5) / 31.3(+4.3) / 34.5(+12.0) / 12.5(+8.0) | 准确率(%)；**未给 seed 数 / 方差（未提及）** |
| 同表开源基线 | GPT-OSS-120B-A5B、Qwen3-235B-A22B-2507、Kimi-K2-0905、Seed-OSS-36B、xLAM-2-32B-fc-r | 如 Qwen3-235B-A22B-2507：71.9 / 58.6 / 47.3 ‖ 14.5 / 45.0 / 32.0 / 15.8（**多数列高于 Qwen3-SE-32B**） | 同上 |
| **Table 2 Pass@4（VitaBench）** | Qwen3-8B / 32B | Avg 27.0 → **35.8**（8B）；36.0 → **46.8**（32B）；Cross 6→12、15→**29** | Pass@4，单值 |
| **域规模缩放（Fig.3）** | N=0(基座) → N=2/4/8/16 域，任务数固定 1024 | 两基准上**单调上升**；**N=16 仍未平台化** | Pass@4；**未给 seed/方差** |
| **Table 3 消融：可执行验证 EV（Avg@4，τ²-Bench）** | Qwen3-8B；w/o EV；完整 Qwen3-SE-8B | w/o EV：42.3 / 30.0 / 25.2；完整：50.9 / 37.5 / 27.2；基座：38.4 / 30.5 / 21.5 —— **去掉 EV 仍高于基座**（Retail 42.3 > 38.4） | Avg@4，单值 |
| **Table 4 消融：奖励机制**（3 个 τ² 域均值） | LLM-as-a-Judge vs 规则式 | LLM-Judge：Avg@4 36.5 / Pass@4 58.8 / Pass^4 14.6；**规则式：38.5 / 62.9 / 15.0** | 三域均值 |
| **Table 5 域稳定性（Avg@4，VitaBench）** | 基座 9.8；Set A(4 域) / Set B(4 域) | **13.8 / 13.3**（两组不重叠域均超基座） | 域数=4、任务数=1024 |
| **附录 A：OOD 证据（Fig.4）** | 16 个训练域 vs τ²/Vita 评测域 | t-SNE 工具嵌入显示评测域与训练簇**显著空间分离** | 定性图 |
| **规模统计（附录 B.1）** | — | 16 域；工具数 ~25（Online Learning）~ >70（Entertainment Media Query）；表数 5（Job Seeking）~ 22（Agriculture Environment）；**任务总数 2560**（Table 8） | 16 域，每域 ~50 工具、5–20 表（§5.1） |
| **合成成本（Table 9）** | — | 单域 ≈546k tokens（prompt 379k + completion 167k）；单任务 ≈93.2k tokens | 平均值 |

### 2.6 论文自陈局限与边界条件
- **论文未设独立 Limitations / Future Work 节**（通读 p1–27：p8 结论后为 p9 Impact Statement 与参考文献，p11–16 为附录 A–D，p17–27 为代码清单与轨迹示例）——此为**本卡观察**，非论文主张。
- **假设依赖**：
  - 环境必须是「**可执行代码 + 结构化数据库**」形状；`s^env` 只能通过工具观测推断（POMDP，p3）→ 对连续动力学 / 物理世界 / 无状态域不适用（推断）。
  - **必须存在可判定真值**：`R` 依赖 `s^env_gt`（由执行 `C_1` 得到）→ 只适用于「最终状态可判」的任务；无标准终态的行为不适用（p4–5）。
  - **难度/可解性以固定 oracle 为标尺**：`g(D_n)` 用 Qwen3-235B-A22B best-of-16 的成功率（p6）→ 换 oracle 则 `g` 变，**可复现性依赖该模型**。
  - 合成期依赖多个闭源/大模型：Deepseek-V3.2、GLM-4.7、**GPT-5.1**、Qwen3-32B（§5.1 p6）→ 复现需访问这些模型。
- **明确不适用的情形**（推断，论文未自陈）：生存域（无死亡/资源约束）、连续控制、无工具/无 DB 的封闭域；SSEA 毫秒级快环（见 §5）。
- **Impact Statement 自陈的风险**（p9）：框架域无关，**理论上可被滥用来合成有害/不道德行为的环境**；呼吁对程序化环境合成设伦理约束。这是论文唯一一处「负面边界」的主动陈述。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **◐** | **同向的一半**：环境侧是「结构化状态 `s^env` 外置 + 工具是确定性读写算子的动作 + 确定性状态转移 `T`」（p3），正是控制环友好的形状。**冲突的一半**：被训练的智能体是 LLM、域是生产力/工具调用（Job Seeking 等 16 域，附录 B），**非生存域** | 只搬环境骨架（状态量、动作、转移），把状态量重定义为生存相关量（能量/危险/资源），工具语义换成生存动作；不搬 LLM 策略与域语义 |
| **C2** 自然语言只作观察员接口 | **◐（必须分层判定，见下）** | **离线合成侧 ✓（不违规）**：LLM 只出现在**建造期**——schema/代码/测试/任务/指令/门控（§4.1–4.2 p3–6），产物是**可执行代码与数据**；判定锚点是**语言在编译期而非运行期**。**在线控制闭环 ✗**：`A_resp` 是自然语言动作、`O_resp` 由 **Qwen2.5-72B-Instruct 用户模拟器**生成的 NL 反馈构成，且 `u` 是 NL 意图，语言**直接进环**（p3、附录 C p13） | **只搬离线侧合成管线，不搬在线侧 LLM 策略与 NL 用户模拟器**。切勿笼统判 ✗：环境合成（编译期语言）不构成 C2 违规；违规的是「NL 反馈作为控制环观测」这一在线形态 |
| **C3** 权重/记忆/技能三分离 | **◐** | 环境（DB 代码 + 工具）完全在模型之外、可独立保存（附录 D），与「环境不属于模型」同向；但论文**不涉及记忆与技能**，无三分离语义 | 环境侧可安全外置并版本化；记忆/技能分离仍按 Memento/FLEX/PSN 路线 |
| **C4** 低算力低带宽 | **◐（分层）** | **环境侧 ✓**：状态转移是**确定性 Python 代码**，运行成本极低；**合成侧 ✗**：单域 546k tokens、单任务 93.2k tokens，且用 GPT-5.1/Deepseek-V3.2/GLM-4.7/Qwen3-32B + Qwen3-235B oracle（Table 9 p13、§5.1 p6）；**训练侧 ✗**：GRPO on 8B/32B，batch 1024/2048、48 步（§5.1 p6） | 环境侧可直接用（低成本）；合成侧**离线一次性、可摊销**；训练侧（GRPO）不进 SSEA |
| **C5** 精准回忆历史 | **—** | 论文不涉及记忆机制（无检索/写入/遗忘/合并） | 可反向利用：`s^env` 是**可验证的外部事实源**，可作记忆写入正确性的对照面 |
| **C6** 可自主修改自身 | **◐** | 只覆盖四权中的**参数面应用权**（GRPO 更新 `π_θ`，附录 C p13）；提案权在外部合成管线、验证权在 Procedural Testing + `R`、**边界权无**（无禁止修改区） | 借「验证权外置到可执行判据」的形状；SSEA 仍需自建提案/边界/验证/应用四权拆分 |
| **C7** 保存/恢复/变异/继承 | **◐** | **保存/恢复 ✓（隐含强）**：环境是**确定性可执行代码 + 可序列化 DB 对象**（附录 D），天然**可快照、可复现、可 git 版本化**——这是 GenePackage 最需要的性质。**变异 ◐**：`Controlled Environment Expansion`（依赖感知 BFS + LLM 门控）是**环境侧扩张算子**，与「环境变异」对偶。**继承/淘汰 ✗**：无 GenePackage、无代际、无淘汰-繁衍闭环 | 把「环境包 = 代码 + DB 快照 + 版本号」定为 SSEA 的**环境包契约**，与 GenePackage 版本配对（环境版本 vs 基因版本）；把扩张算子登记为**环境侧变异算子**；继承/淘汰仍由 Gene Manager 承担（**当前缺失**） |
| **C8** 给基因先验，不给知识语料 | **◐** | 「知识留在环境 DB、策略只学交互逻辑」方向同向；但**环境内容由 LLM 合成**（初始状态 + 干扰项，§4.2.1 p5），而非像 Agent-World 那样从真实 Web 挖取 → 知识来源本身是 LLM 生成物；且基座是预训练 Qwen3 | 可作「知识外置到环境」的样板；但 SSEA 侧应提高环境内容的事实性门槛（或改接真实数据源） |
| **C9** 不设评分函数，只有淘汰函数 | **◐（环境合成族里最干净的一件，但仍非合规）** | **同向**：判据是**规则式、确定性、终局**的状态检查（`R(s^env_T,u)`，三档匹配 Exempt/Hard/Semantic），且论文**明确拒绝 LLM-as-a-judge**（因贵且易 reward hacking，Table 4 p8 佐证规则式更优）——这与 SSEA 的「反观察员评分」立场一致。**冲突**：① 该 `R` 仍被用作 **GRPO 奖励**，进入优势估计做**排序与塑形**（附录 C 式1–2 p13），违反「验证门只判合法性、不打分、不排序」；② **Semantic Alignment** 对文本列做「模糊语义匹配」——形似软性评委，判据噪声会直接进奖励。**关键正面差异**：**无**「被测智能体失败 → 环境难度」的反馈通道（`c(H_n)` 是结构量、`g(D_n)` 用**固定 oracle**，不含被训智能体表现，§4.2.2 p6）——这一点**优于 GenEnv / Agent-World** | 见 §5.1 三步剥离：把规则式状态判定降为**环境侧终局淘汰/合法性门**（四级门第四级），只输出「通过 / 淘汰」；**删除 Semantic Alignment 或换成确定性断言**；`R` 绝不进奖励塑形/排序 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | L1 全借用（GRPO [Shao 2024]、BFS、LLM 合成、Pydantic）；创新在环境合成管线（L2/L4）与任务实例化协议（L2） | 无冲突 |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层**（基础网络模块） | 无新算子（GRPO / BFS / LLM / Pydantic 均借用） | 无（符合 C10） |
| **L2 信息流层**（模块如何连接） | **环境-智能体接口的形状**：`s^env` 外置为 DB、动作是确定性读写算子、`T` 确定性、`A=A_resp∪A_tool`、**Interaction Completeness**（任意合法动作必有有效观测）（p3–4）；以及**工具依赖图 → 任务链**的信息流 | **高**：可直接定为 SSEA 环境包与 Action 通道的**通道契约**（回应债务 26/27） |
| **L3 学习层**（如何更新自身） | 仅参数面（GRPO on `π_θ`）；无自修改、无技能固化 | 低-中：SSEA 须经四级门，不直接搬 |
| **L4 演化层**（保存/继承/变异） | **环境多样性缩放曲线**（N=2→16 单调上升，Fig.3）+ **环境扩张算子**（依赖感知 BFS + LLM 门控） | **中-高**：提供「环境侧供给可规模化、多样性驱动泛化」的**实测证据**；但**无遗传/淘汰语义** |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **规则式状态判据 `R`（三档匹配）** | **现有：四级验证门判据** → 判据从「看输出形状」改为「看环境状态 + 可执行断言」（债务 25/28）；**须删除 Semantic Alignment** |
| **Procedural Testing（三类结果）** | **现有：6 个 Action 通道** → 新增**通道可靠性准入**：不可执行 / 无有效观测的通道**准入失败**（债务 26/27） |
| **Interaction Completeness 硬约束** | **现有：通道契约** → 「无消费者通道报成功」失去生存空间（债务 26/27） |
| **Tool Dependency Graph `G`** | **新增：动作通道依赖图**（通道间参数/前置/共享状态依赖） |
| **依赖感知 BFS + `|H_n|≥20` 下限** | **新增：环境覆盖度下限门**（防环境塌缩/过度稀疏） |
| **干扰项注入（density 随复杂度缩放）** | **新增：判别力旋钮候选**（逼出信息过滤；可用于把饱和判据拉离天花板） |
| **环境即确定性可执行代码（附录 D）** | **新增：环境包契约（代码 + DB 快照 + 版本号）** → C7 保存/恢复/版本化（Gene Manager 的前置） |
| **域规模缩放曲线（Fig.3）** | **验收实验设计证据**：支持「环境多样性 > 任务数量」的取舍 |
| **合成成本表（Table 9：546k / 93.2k tokens）** | **睡眠期计算预算（缺失）** → 提供「造一个域 / 造一个任务」的**token 成本锚点** |
| **固定 oracle 可行性 `g(D_n)`** | **仅作对照**（模型依赖标尺，见 §5.2；SSEA 侧须换成结构量） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **债务 25（判据形状错）/ 债务 28（技能失效被判成成功）**：`R` 判**环境最终状态**而非输出字符串，给出判据的**正确形状**（p4）。
  - **债务 26 / 27（无消费者通道报成功 / `skill` 通道无消费者）**：`Interaction Completeness` + Procedural Testing 的可执行准入 → 无消费者/不可执行通道应**准入失败**（p4）。
  - **「睡眠期计算预算未定义」** → **部分回应**：Table 9 给「单域 546k / 单任务 93.2k tokens」的**合成侧成本锚点**（不覆盖「预演多少步」）。
- **不回应**：债务 22（记忆二级门常量阈值）、Gene Manager 缺失、`rules` 零消费者、`retrieve` 键收窄、技能表示（0/33）、DeathHook。
- **可服务的验收实验**：
  - **第四级「环境实测」门**：本篇提供可规模化的**环境供给**与判据形状。
  - **饱和判据（危险回避率两臂均 0.9814）** → **不直接回应，是最大缺口**（见 §5.2 / §8）：本篇**没有**判别力校准机制；须与 **GenEnv α 带 / Agent-World 难度三旋钮**合并。
  - **实验 4/5（缺 Gene Manager 未开跑）**：环境包版本化（代码 + DB 快照）可与 Gene Manager 同步设计，但**不直接解锁**。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **规则式状态判据 `R`（Exempt / Hard / Semantic 三档）** | 算法/表示 | **改造移植**（删 Semantic） | 四级验证门判据 | **债务 25/28**：判据形状错、技能失效被判成功 | 高 |
| 2 | **Procedural Testing（Success / Anticipated Rejection / Unexpected Failure 三类判定 + Debug 回路）** | 协议/工程实现 | **改造移植** | 6 个 Action 通道准入 | **债务 26/27**：无消费者通道被报成功 | 高 |
| 3 | **Interaction Completeness 硬约束**（任意合法动作必返回有效观测） | 协议 | **直接移植** | 通道契约 | 环境对无消费者通道报成功 | 高 |
| 4 | **Tool Dependency Graph + 依赖感知 BFS（避免 dependency dead-end）** | 算法 | 改造移植 | 通道依赖图 / 任务生成 | 任务链不可解、环境稀疏 | 中-高 |
| 5 | **干扰项注入（density 随复杂度缩放）** | 方法 | 改造移植 | **判别力旋钮候选** | 判据饱和 / 天花板压缩 | 中 |
| 6 | **环境即确定性可执行代码 + 可序列化 DB** | 表示/工程实现 | **直接移植** | **环境包契约** | **C7 保存/恢复/版本化**（Gene Manager 前置） | 高 |
| 7 | **合成成本表（546k / 93.2k tokens）** | 基准数据 | 直接引用 | 睡眠期预算 | 「睡眠期计算预算未定义」 | 中 |
| 8 | **域规模缩放曲线（N=2→16 单调，未平台化）** | 基准/证据 | 直接引用 | 实验设计 | 环境多样性 vs 任务数量的取舍 | 中 |
| 9 | **「规则式 > LLM-as-a-judge」的立场与消融（Table 4）** | 思想/证据 | 直接移植 | C9 立场文档 | 拒绝观察员评分 | 高 |
| 10 | **结构复杂度 `c(H_n)`（非模型标尺）** | 表示/指标 | 改造移植 | 环境覆盖度仪表 | 难度标定不依赖被测模型 | 中 |
| 11 | **可执行种子链（工具序列 + 参数联合建模为代码）** | 表示 | 改造移植 | 任务生成器 | 参数实例化与序列脱节 | 中 |
| 12 | 固定 oracle 可行性 `g(D_n)`（Qwen3-235B best-of-16） | 工程实现 | **仅作对照** | — | 可解性下界（但模型依赖） | 低 |

---

## 5. 冲突、代价与风险

### 5.1 与硬约束的冲突（逐条，对应 3.1 中 ✗/◐）
1. **C9 ◐：规则式 `R` 仍进 GRPO 奖励回路**（附录 C 式1–2 p13）。
   → **剥离**：把 `R` 降为**环境侧终局合法性门**——只输出「通过 / 淘汰」二值，只作四级门的第四级判据；**不参与打分、不排序、不进优势估计**（C9：验证门只判合法性）。
2. **C9 ◐：Semantic Alignment 模糊语义匹配**（p4）。
   → **剥离**：文本列改为**确定性断言**（关键字段精确/包含/正则），或直接列入 Exempt；**任何语义模糊判定不得进判据路径**（否则判据噪声会像 LLM 评委一样被 reward hacking）。
3. **C2 ✗（仅在线侧）：NL 用户模拟器 + NL 响应进控制环**（p3、附录 C p13）。
   → **不搬**在线策略与用户模拟器；**只搬离线合成管线**（编译期语言，合规）。**判据锚点：语言出现在编译期而非运行期**——故本篇的环境合成**不**构成 C2 违规，勿笼统判 ✗。
4. **C1 ◐：域非生存、载体是 LLM**。
   → 只搬环境骨架，状态量重定义为生存量。
5. **C4 ◐：合成与训练重资产**。
   → 合成侧离线摊销；环境运行侧（确定性代码）成本低，可直接用；GRPO 不进 SSEA。
6. **C7 ◐：无继承/淘汰**。
   → 环境包版本化先做（零依赖），继承/淘汰留给 Gene Manager。

### 5.2 隐含假设与失效条件
- **【对 SSEA 最要命】论文不回答「合成环境是否有判别力」**：判别力是靠**外部基准**（τ²-Bench / VitaBench）证明的，**不是环境自身的性质**；环境内部的 `R` 只是一个**终局二值状态检查**，粒度粗（Exempt/Hard/Semantic 三档）→ 若状态检查太粗，会**天然饱和**（所有策略都「通过」），正是 SSEA「指标全绿但行为没变」的同一个病。论文**无任何饱和检测 / 判别力校准机制**（未提及）。
- **Table 3（EV 消融）的负面暗示**：去掉可执行验证（EV）后 Retail 仍有 **42.3**（**高于基座 38.4**）、Airline 30.0、Telecom 25.2 → 说明 **EV 的判别贡献是「增量」而非「必需」**；且论文**未对合成管线各组件做逐项消融**（只有 EV / 奖励 / 域稳定性三项），无法归因到底是 schema、procedural testing 还是扩张在起作用。
- **可解性以固定 oracle 定义**：`g(D_n)` 用 Qwen3-235B-A22B best-of-16（p6）→ **换 oracle 则难度标尺变，不可跨项目比较、不可复现**（与 Agent-World 的 Doubao Pass@10 探针同类问题）。
- **环境内容由 LLM 合成**（初始状态 + 干扰项，§4.2.1 p5）→ 若合成内容本身与「真值轨迹」耦合出错，会把**环境 bug 记到智能体账上**（与债务 25/28 同类）。
- **无 seed / 方差 / 置信区间**：Table 1/2/3/4/5 全为单值（未提及）→ 提升幅度不可做显著性判断。
- **无代码 / 无数据发布**：复现成本全自担；且依赖 GPT-5.1 等闭源模型（§5.1 p6）。
- **环境是离散状态 + 确定性工具**（附录 D 全为 DB 文件读写）→ 对连续动力学、噪声、部分可观测延迟等生存要素**未覆盖**。

### 5.3 算力 / 带宽 / 工程代价
- **合成侧**：单域 546k tokens、单任务 93.2k tokens（Table 9）；需多智能体编排（Code/Test/Debug Agent + 门控 + 依赖分析），且用 GPT-5.1 / Deepseek-V3.2 / GLM-4.7 / Qwen3-32B + Qwen3-235B oracle → 重资产，但**离线一次性、可摊销**。
- **环境运行侧**：确定性 Python 代码 + DB 对象 → **极低算力/带宽**（这是本篇相对 Genie 的最大优势：不需要世界模型、不需要 GPU 推理）。
- **训练侧**：GRPO on 8B/32B、batch 1024/2048、48 步（§5.1 p6）→ **SSEA 不需要复现**，省掉全部 RL 开销。
- **工程代价前置**：要给 6 个 Action 通道配「可执行 + 有效观测 + 单测」，才能谈环境规模化——**与债务 27 是同一件事，顺序不可颠倒**。

### 5.4 搬运后的可能退化模式（若失败，会以什么形式失败）
1. **判据饱和（最危险，且正是 SSEA 现状）**：终局二值状态检查粒度太粗 → 所有版本都「通过」→ 症状：淘汰率长期贴 1（或贴 0），指标全绿但行为不变。**本篇无任何机制可检测此症状**。
2. **环境 bug 误记**：LLM 合成的初始状态/干扰项/工具若有缺陷，会把环境失败记成智能体失败 → 症状：同一策略在不同环境版本上成功率大幅抖动。
3. **环境塌缩**：自动扩张若不放回采样，收敛到少数模板 → 淘汰压力多样性下降（论文未讨论抽样策略）。
4. **难度不可复现**：`g(D_n)` 依赖 oracle 模型 → 换模型则难度刻度全变 → 症状：环境无法跨时间/跨项目比较。
5. **语言回流**：若误把在线 NL 用户模拟器也搬进来 → C2 被破，且语言噪声进入控制环。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **同类（环境合成族，须点名并排）** | **Agent-World** | **已被 Agent-World 卡列为基线**（Agent-World Table 1 中 **ScaleEnv-8B τ²-Bench = 38.5**）。二者是同一族的**两极**：Agent-World = ScaleEnv 的**加强版**（真实数据挖库 + 程序化任务 + 诊断 + 共演化）；ScaleEnv = **纯 from scratch、无共演化**。**关键差异**：ScaleEnv 的难度/复杂度**不含被测智能体信号**（`c(H_n)` 结构量 + 固定 oracle `g(D_n)`）→ **规避了 Agent-World/GenEnv 的 C9③ 反馈通道**。Agent-World 卡 §6.1 已点名「应把两篇的可验证性方案合并评估，避免重复造轮子」——本卡回应：**合并后的判据形状取 ScaleEnv 的规则式状态判定 + Agent-World 的 `V_code` 可执行断言** |
| **同类（C9 头号反例）** | **GenEnv** | GenEnv = difficulty-aligned **co-evolution**（α-Curriculum Reward `R_env=exp(−β(p̂−α)²)`，环境难度由智能体近期表现反向驱动）。**ScaleEnv 没有这条通道** → ScaleEnv 是**更干净的 C9 标本**；但 GenEnv 的 **α 带 + Theorem 1 样本量界**恰是 ScaleEnv 缺的**判别力校准器** → **二者互补**：ScaleEnv 供环境 + 判据形状，GenEnv 供「难度调到哪、要多少样本才分得开」 |
| **同类（程序化合成）** | **EnvScaler** | ScaleEnv 参考文献点名（Song et al. 2026, arXiv:2601.05808，「programmatic synthesis」）；EnvScaler 用 **rule-based trajectory validation functions** → 与 ScaleEnv 的规则式 `R` **同源近亲**。Agent-World 卡已证「演化循环」可与具体环境合成方法分离搬运 |
| **同类（自动环境合成）** | **AutoForge** | ScaleEnv 参考文献点名（Cai et al. 2025, arXiv:2512.22857），且 ScaleEnv 的 **Scalability 挑战即引 AutoForge**（p1）。AutoForge 提出 environment-level RL + 环境级优势估计；ScaleEnv 差异：from scratch、规则式奖励、**无环境级 RL** |
| **同类（度量而非训练）** | **AutoEnv** | 跨环境智能体学习的自动化环境（度量迁移）。与 ScaleEnv 互补：ScaleEnv **造**环境、AutoEnv **量**跨环境迁移 |
| **同类（正交域）** | **Endless Terminals** | 终端智能体的 RL 环境规模化（域 = 命令行）。与 ScaleEnv 的「DB + 工具」域**正交**；二者合起来覆盖「离散状态可执行环境」的两大现实形态 |
| **另一端的环境生成** | **Genie** | 无监督、从视频生成可玩世界（潜在动作、连续视觉）。与 ScaleEnv 构成**环境生成的两个极端**：Genie 供连续/想象/无状态标注的世界，ScaleEnv 供离散/可执行/状态外置的世界。SSEA 需要后者做**淘汰判据**、前者做**离线想象**，**不可互换** |
| **互补（最紧，模型内 vs 模型外）** | **Dream-RSI** | 发现历史即重放模拟器（模型内、慢环做梦式离线验证）。ScaleEnv 环境在**模型外**且**确定性可复现** → 接口：重放查无延续时，向 ScaleEnv 环境包申请一次真实交互取状态，**避免用想象结果充当淘汰判据**；且确定性环境**天然可重放** |
| **被点名但未引用的相关论文** | **「Towards General Agentic Intelligence via Environment Scaling」(Fang et al. 2025, arXiv:2509.13311)** / **「Scaling Agent Learning via Experience Synthesis」(Chen et al. 2025, arXiv:2511.03773)** / **TOUCAN (Xu et al. 2025)** / **「Simulating Environments with Reasoning Models」(Li et al. 2025, arXiv:2511.01824)** | 前三为**环境合成族**同侪（已在 papers 目录）；末者是 ScaleEnv **明确批评的 LLM-simulator 路线**（p1）。建议按同一纪律补卡，联通环境合成族图谱 |
| **消费方（技能侧主干）** | **PSN** | PSN 的故障定位/成熟度门控/回滚验证需要**环境**来验证；ScaleEnv 的环境包 + 规则式 `R` 正是 PSN 的验证场 → 解决「技能固化 0/33」的一条具体路径 |
| **消费方（技能流水线）** | **SkillWeaver / Voyager** | 技能提案-练习-打磨/自动课程缺规模化场地；ScaleEnv 提供场地 |
| **门禁复用** | **SEDM** | SCEC 自包含打包 + A/B 准入验证 → 可直接复用为**环境包准入官**（环境包也走「自包含打包 + A/B 准入」） |
| **风险清单** | **Misevolve** | 误演化威胁模型与红队清单。**需新增一条：环境侧判据饱和/环境 bug 误记**（本篇 §5.2/§5.4），此前清单覆盖模型/记忆/工具/工作流四路径 |
| **训练诊断** | **RAGEN** | Echo Trap 诊断 + 不确定性过滤；本篇**无共演化**，故 Echo Trap 风险低于 GenEnv，但「判据饱和」是本篇自带的退化模式，可用 RAGEN 的不确定性过滤思路监控 |
| **形式化参照** | **Gödel Agent / ADAS / MaAS** | 自指递归自改进、自动设计智能体的形式化；本篇的「域关键词 → 可执行图 → 任务」可作为**环境侧**的形式化实例 |

### 6.2 推荐组合方案
- **组合 1（最优先，直接解债务 25/26/27/28）：本篇（规则式 `R` + Procedural Testing + Interaction Completeness）× SSEA 6 通道**
  - **接口形态**：每个 Action 通道 = 一个可执行工具，必须满足「可编译 / 有单测 / 对任意合法调用返回有效观测」；`skill` 通道若无消费者 → **准入失败**（不是成功）。
  - **组合后新增能力**：债务 26/27/28 一次性闭合；「技能失效被判成成功」失去生存空间。
  - **新增风险**：准入过严 → 当前环境大面积不合规，需先做通道盘点（分母 = 6 通道中合规数）。
- **组合 2（补判别力，回应用户核心关切）：本篇（环境 + 判据形状 + 干扰项旋钮）× GenEnv（α 带 + Theorem 1 样本量）**
  - **接口**：ScaleEnv 造环境与终局判据；GenEnv 的 α=0.5 带 + `k_min=0.1` 死区用于**把判据从饱和区拉到可分档区**；`n ≥ (4.5/Δ²)·ln(4/δ)` 反推每臂样本量。
  - **新增能力**：把「判据饱和」拆成「天花板效应」与「门无效」两种可判决情形（**这正是 ScaleEnv 单独做不到的**）。
  - **新增风险**：难度旋钮引入的方差被误读为效应（见 GenEnv 卡 §5.4）。
- **组合 3（判据形状统一）：本篇（规则式状态判定）× Agent-World（`V_code` 可执行断言）× EnvScaler（trajectory validation functions）**
  - **接口**：四级门第四级的判据统一为「环境状态 + 可执行断言」；三者取**最严**形态（ScaleEnv 的 Hard Constraints + Agent-World 的 `V_code`）。
  - **新增能力**：判据形状一次定死，避免三套并存。
- **组合 4（环境版本化 × Gene Manager，缺失）**：环境包 = 代码 + DB 快照 + 版本号，与 GenePackage 版本配对，A/B 对照时两者同时固定；**环境版本号可先做（零依赖）**，Gene Manager 后补。
- **组合 5（离线想象 × 在线淘汰）**：本篇（离散可执行环境，供淘汰判据）× Genie（连续世界模型，供离线想象）——**不得互换**。
- **组合 6（重放 × 环境）**：本篇 × Dream-RSI —— 重放查无延续时向确定性环境包申请一次真实交互。
- **组合 7（防污染）**：本篇 × Misevolve —— 加入「判据饱和 / 环境 bug 误记 / 环境塌缩 / 难度不可复现」四条环境侧红队项。

### 6.3 本篇在组合中的典型角色
- **环境包工厂 + 判据形状供应商 + 通道准入标准**：管「环境从零怎么批量造、动作通道怎么算合规、判定怎么写才不是看输出形状」。
- **明确不是**：**不是判别力校准器**（无饱和检测）、不是记忆组织者（归 Memento/FLEX）、不是技能表示方案（归 PSN）、不是策略训练方法（归 RAGEN）、不是难度调度器（归 GenEnv/Agent-World）。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直接命中债务 25/26/27/28（判据形状 + 通道准入）与第四级环境实测门；环境从零合成是第二阶段「生态」的供给侧（实测：`R` 与 Procedural Testing 机制在 p4 明确给出）。扣分因当前卡点是 Gene Manager 缺失与判据饱和，**不是环境数量** |
| 立场兼容性 | **3** | **环境合成族里最干净的一件**：判据是规则式确定性终局检查、**明确拒绝 LLM-judge**（Table 4 p8）、**无**「被测者失败 → 难度」反馈通道（§4.2.2 p6）→ 优于 GenEnv / Agent-World。但仍有：`R` 进 GRPO 奖励回路（C9）、Semantic Alignment 形似软评委（C9）、NL 用户模拟器进在线环（C2）、LLM 载体与非生存域（C1）（实测） |
| 可搬运性 | **4** | 管线是提示/算法级、无需复现 8B/32B RL；环境是**确定性可执行代码**（附录 D 给出 Pydantic 模型 + 工具实现），可直接照抄形状；附录 A/B 给出 schema 与成本表（实测） |
| 证据强度 | **3** | 加分：7 个 OOD 评测域、域规模缩放曲线（Fig.3）、三项消融（EV / 奖励 / 域稳定性）、t-SNE 佐证 OOD（Fig.4）。扣分：**无合成管线逐组件消融**、**无 seed/方差**（未提及）、**无 Limitations 节**、**无代码/数据发布**、Table 3 显示 EV 增量有限（w/o EV Retail 42.3 > 基座 38.4）、`g(D_n)` 依赖 oracle 模型 |
| 组合价值 | **4** | 与 Agent-World / GenEnv / EnvScaler / AutoForge / AutoEnv / Endless Terminals / Genie / Dream-RSI / PSN / SkillWeaver / Voyager / SEDM / Misevolve 均有明确接口；与 GenEnv（补判别力）、Agent-World（判据合并）互补最紧（推断 + 实测各半） |
| 落地成本 | **3** | 反向口径。**加分**：不需要世界模型、不需要 GPU 训练、环境运行成本极低。**扣分**：合成侧 token 成本高（546k/域 + 93.2k/任务）、需多智能体编排、依赖闭源大模型；前置是给 6 通道配消费者与单测（与债务 27 同一件事） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用「**规则式状态判据 `R`（删 Semantic Alignment）+ Procedural Testing 通道准入 + Interaction Completeness + Tool Dependency Graph/依赖感知 BFS + 干扰项注入 + 环境即确定性可执行代码（环境包契约）**」；**不采用** LLM 策略本体、NL 用户模拟器、GRPO 奖励回路。**未给 A 的原因**：① 存在 C9 ◐（`R` 进奖励回路）与 C2 在线侧冲突，需实质剥离；② **最关键的缺口——本篇不提供「环境判别力」的保证或检测**，而这正是 SSEA 当前最紧的病；③ 证据侧无逐组件消融、无 seed/方差、无代码。
- **优先级：P1** —— 不是 P0，因为当前卡点（Gene Manager 缺失、判据饱和）**不是环境数量问题**；但「规则式状态判据 + 通道准入」是债务 25/26/27/28 的直接解，且环境包版本化是 Gene Manager 的前置，应在记忆/技能主干之后、环境规模化之前落。**若与 GenEnv α 带组合后的判别力实验通过，可升 A。**

### 建议动作（按执行顺序）
1. **通道盘点（先做，零依赖）**：对 6 个 Action 通道逐个判定「是否有消费者 / 是否可执行 / 是否对任意合法调用返回有效观测」，列出合规数（所有后续工作的**分母**）。
2. **落地通道准入**：无消费者 / 不可执行的通道判为**准入失败**而非成功（直接闭合债务 26/27）。
3. **判据形状改造**：四级门判据改为「环境状态 + 可执行断言」（取 ScaleEnv Hard Constraints 形状）；**删除/替换 Semantic Alignment 模糊匹配**；给判据自身加元验证（对已知正确轨迹必须判通过）。
4. **环境包契约 + 版本号**：环境 = 代码 + DB 快照 + 版本号，一经发布即冻结、模型不可读写（C9 第一层的工程保障；先于 Gene Manager 实现）。
5. **判别力校准（关键补装）**：借 GenEnv 的 α 带 + `k_min` 死区 + Theorem 1 样本量界，把判据从饱和区（回避率 0.9814）拉到可分档区；干扰项密度作为难度旋钮候选。
6. **记录合成成本锚点**：把 546k / 93.2k tokens 写入「睡眠期计算预算」草案，作为造域/造任务的单位成本上界。
7. **Misevolve 清单增补**：加入环境侧四条（判据饱和 / 环境 bug 误记 / 环境塌缩 / 难度不可复现）。
8. **与 Agent-World / EnvScaler / GenEnv 合并评估**：判据形状取最严形态、C9 冲突共用一套剥离规则、判别力校准只建一次。

### 最小验证实验：**合成环境的判别力判决实验**（回应「判据饱和」核心关切）
- **目的**：判定 ScaleEnv 式环境**能否区分智能体能力**——即环境本身是否具备判别力，避免「指标全绿但行为没变」的复制。
- **双臂 / 消融设置**：
  - **Arm A（对照，粗判据）**：现有环境 + 现有判据（终局二值、粒度粗）。
  - **Arm B（处理，ScaleEnv 式）**：环境改为「可执行工具 + 规则式状态判据（Hard Constraints 为主）+ 干扰项注入 + 通道准入」。
  - **消融 B1**：只加通道准入与判据形状，**不加干扰项**；**消融 B2**：只加干扰项，不改判据（用于定位各自贡献）。
  - **判别力探针（关键）**：在同一环境上跑**两个能力不同的臂**——完整策略 vs **人为弱化策略**（屏蔽部分工具/技能），各 ≥8 seed，看环境能否把两者分开。
- **判据（分档，先看分母）**：
  1. **机制计数（分母）**：有效 episode 数、通道准入拒绝事件数（**若 =0 说明契约未接入判定路径，实验无效**）、无消费者通道数（分母 = 6）。
  2. **行为差（判别力本体）**：完整臂 vs 弱化臂的成功率差 `Δp̂`——**要求 `Δp̂` 显著 >0 且跨 seed 可重现、换邻近难度仍同号**；这是「环境有判别力」的**唯一硬证据**。
  3. **淘汰结果**：第四级环境实测门淘汰率是否脱离饱和（当前危险回避率两臂均 0.9814）——B 臂应出现**可分档的淘汰率分布**而非全通过。
  4. **复杂度代理**：环境侧结构复杂度（`c(H_n)` 式量）须随难度旋钮上升而非下降。
- **预期与证伪条件**：
  - **预期**：B 臂 `Δp̂` 显著 >0 且淘汰率可分档；B 臂捕获 `skill` 通道准入失败，失效技能不再被判成功。
  - **证伪（环境无判别力）**：若 B 臂 `Δp̂≈0`（环境对弱化臂与完整臂给出同样结果）→ **证明合成环境本身缺乏判别力**，会复制 SSEA 的饱和病 → 必须先加难度旋钮（GenEnv α 带）并标定到 `p̂≈0.5` 档，再谈用此环境做淘汰。
  - **证伪（判据形状错在上游）**：若 B 臂仍把失效技能判成功 → 判据形状错在更上游（技能表示问题），转 PSN / 技能表示议题。
  - **证伪（难度标定失效）**：若 B 臂淘汰率全 0 或全 1 → 干扰项/结构旋钮对 SSEA 域无效。
- 若 **E 不采用**：不适用（裁决为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **「环境判别力」如何定义与检测**：SSEA 是否接受「环境判别力 = 完整臂 vs 弱化臂的成功率差 `Δp̂`」这一操作化定义？若接受，判别力应成为**环境准入的必要条件**（造出的环境若 `Δp̂≈0` 直接判不合格）。
  2. **C9 边界**：把规则式状态判定用作「环境侧终局淘汰门」是否算合规？（本卡倾向：合规，因为它确定性、模型碰不到、且只输出通过/淘汰；但**若它进奖励塑形则违规**。）需团队书面确认。
  3. **环境包版本号与 GenePackage 版本号如何配对**（先做哪个、A/B 对照时如何同时固定）——Gene Manager 未实现前的临时记账方式。
  4. **环境内容是否允许由 LLM 合成**（本篇立场：可以，只要产物是可执行代码、且经 Procedural Testing）？若要求事实性，是否改接 Agent-World 式真实数据挖取？
- **需补查的文献或资料**：
  1. **EnvScaler（arXiv:2601.05808）** 的 rule-based trajectory validation functions 与 ScaleEnv 的规则式 `R` **是否等价**，还是各有更严的判据形状（决定债务 25 的解法取哪个）。
  2. **Agent-World** 的 `V_code` 与本篇 `R` 的**判据强度对比**（一个判答案 + 数据库状态、一个只判数据库状态）。
  3. **AutoForge / AutoEnv / Endless Terminals / 「Towards General Agentic Intelligence via Environment Scaling」(Fang 2025)** 的可验证性方案——四篇均在 papers 目录但**尚无卡片**，建议按同一纪律补卡以联通环境合成族图谱。
  4. 「Simulating Environments with Reasoning Models」(Li et al. 2025, arXiv:2511.01824) 是本篇批评的 LLM-simulator 路线代表，补卡可对照。
- **需人工核对的公式 / 数字 / 实现**：
  1. **Table 3（EV 消融）的解读**：w/o EV 在 Retail 得 42.3（**高于基座 38.4**）、Airline 30.0（≈基座 30.5）、Telecom 25.2（>基座 21.5）→ 需确认「EV 是必要条件」这一摘要主张与数字的关系（EV 增益在 Retail 为 +8.6、Telecom 仅 +2.0）。
  2. **`S_sat=50` 与 `λ=0.5` 的来源**（§4.2.2 p6）：论文未给敏感性分析，需自行确定 SSEA 侧取值。
  3. **`τ`（门控阈值）的具体取值未在正文给出**（`p≥τ` 才采新链，§4.2.2 p6）——需核对附录是否有超参表。
  4. **`g(D_n)` 的 oracle 定义**：Qwen3-235B-A22B + best-of-k（k=16）的「成功率」具体如何统计（是否含多次 rollout）——正文表述简略。
  5. **统计口径**：Table 1–5 是否单次运行 / 多次平均、seed 数——全文未提及，需核对代码或作者主页。
  6. **附录 D 代码清单**（Listing 1–2）为「Job Seeking」域的**部分**实现，未覆盖 16 域全部；Procedural Testing 的 Test Agent 提示词与 DB 匹配实例生成逻辑未在附录逐条核对。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| 摘要："we introduce ScaleEnv, a framework that constructs fully interactive environments and verifiable tasks **entirely from scratch** … ensures environment reliability through **procedural testing**, and guarantees task completeness and solvability via **tool dependency graph expansion** and **executable action verification**" | p1 |
| 两大挑战："The first is **Realism**: tools synthesized directly by LLMs are often functionally unreliable, while LLM-based simulators are prone to severe hallucinations"；"environments must be grounded in **verified, executable code** rather than probabilistic text generation"；"The second challenge is **Scalability**: synthesis cannot rely on finite external documentation or manual human intervention" | p1 |
| POMDP：`M=⟨S,A,O,T,R⟩`；`s_t=(s^env_t,h_t,u)`；`A=A_resp∪A_tool`；`O=O_resp∪O_tool`；工具动作**确定性**更新 `s^env_t` 与 `h_t`；`r=R(s^env_T,u)` | p3 |
| 规则式奖励三档："**Exempt Fields** … **Hard Constraints** … and **Semantic Alignment**: descriptive text that only require fuzzy semantic matching"；拒绝 LLM-as-a-judge（"high computational overhead and vulnerability to **reward hacking**"） | §4.1.1 p4 |
| Procedural Testing 三类判定："**Success** / **Anticipated Rejection** / **Unexpected Failure**"；失败 → Debug Agent 迭代 | §4.1.2 p4 |
| Tool Dependency Graph 三维依据：**data flow**（parameter passing）/ **pre/post-conditions** / **state dependencies**（shared database tables） | §4.1.3 p4 |
| 两条硬约束："**Entity Consistency**" + "**Interaction Completeness** … for any valid tool calling action `a∈A_tool` … the environment `E` must return a valid, semantically meaningful observation" | §4.2 p4 |
| 干扰项注入："populate the database tables … with additional records that act as **distractors** … forcing the agent to acquire precise information filtering capabilities" | §4.2.1 p5 |
| 门控与结构量：`c(H_n)=(|V_{H_n}|+λ|E_{H_n}|)/S_sat`，`λ=0.5`、`S_sat=50`；`g(D_n)` = oracle（**Qwen3-235B-A22B + best-of-k, k=16**）成功率；`π(|D_n|,c(H_n),g(D_n))→p`，`p≥τ` 采新链；`|H_n|≥20` | §4.2.2 p6 |
| 实验设置：合成用 Deepseek-V3.2 / GLM-4.7 / **GPT-5.1** / Qwen3-32B；**16 个合成域**，每域 ~50 工具、5–20 表；Qwen2.5-72B-Instruct 作用户模拟器；8B batch 1024 / 32B batch 2048、48 步、lr 1e-6 | §5.1 p6 |
| Table 1：Qwen3-SE-8B = 50.9(+12.5) / 37.5(+7.0) / 27.2(+5.7) ‖ 3.0(+1.5) / 26.3(+8.0) / 23.8(+9.0) / 7.0(+2.5)；Qwen3-SE-32B = 63.6(+4.1) / 48.0(+0.0) / 30.9(+3.7) ‖ 10.8(+5.5) / 31.3(+4.3) / 34.5(+12.0) / 12.5(+8.0) | Table 1 p7 |
| Table 2：VitaBench **Pass@4**，8B Avg 27.0→35.8；32B 36.0→46.8 | Table 2 p7 |
| 域规模缩放："Performance improves **monotonically** across both benchmarks"（N=2→16）；"performance has **not yet fully plateaued** at N=16" | §5.3 p7–8；Fig.3 |
| Table 3（EV 消融，Avg@4）：**w/o EV 42.3 / 30.0 / 25.2**；完整 50.9 / 37.5 / 27.2；基座 38.4 / 30.5 / 21.5 | Table 3 p8 |
| Table 4（奖励消融，3 域均值）：LLM-as-a-Judge 36.5 / 58.8 / 14.6；**规则式 38.5 / 62.9 / 15.0**；"our rule-based reward enforces rigorous, **database-level fidelity**" | Table 4 p8 |
| Table 5（域稳定性，Avg@4，VitaBench）：基座 9.8；Set A 13.8；Set B 13.3 | Table 5 p8 |
| 结论："**scaling environmental diversity is more critical than task quantity** for cultivating generalist agent capabilities" | §6 p8 |
| Impact Statement："ScaleEnv is **domain-agnostic** and capable of synthesizing arbitrary interactive environments … could be misused to construct environments that model **harmful or unethical behaviors**" | p9 |
| OOD 证据：t-SNE 显示 16 个训练域与 τ²/Vita 评测域**显著空间分离** | 附录 A Fig.4 p11 |
| 规模：工具数 ~25（Online Learning）~ >70（Entertainment Media Query）；表数 5（Job Seeking）~ 22（Agriculture Environment）；任务总数 **2560** | 附录 B.1 p12–14；Table 8 p14 |
| 合成成本：单域 **~546k tokens**（prompt 379k + completion 167k）；单任务 **~93.2k tokens**（prompt 74.6k + completion 18.6k） | 附录 B.2 Table 9 p13–14 |
| GRPO 目标（式1）与组内优势（式2 `Â_i=(r_i−µ)/σ`） | 附录 C p13 |
| 附录 D：Pydantic 数据库模型（`JobApplication`/`ApplicationNote`/`ApplicationStage`/`InterviewSchedule`/`InterviewFeedback`）+ `JobSeekingDB` + 工具实现清单 | 附录 D Listing 1–2 p14–19 |
| 多轮交互轨迹示例（Job Seeking：查询/记录面试/计算转化率/跟进提醒，52 步） | 附录 E p19–27 |
| **无独立 Limitations 节**；全文检索 p1–27 未见 GitHub / 代码 / 数据发布声明 | 全文 |
