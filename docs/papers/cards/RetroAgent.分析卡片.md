# 论文分析卡片 · RetroAgent

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-03-09 RetroAgent From Solving to Evolving via Retrospective Dual Intrinsic.pdf` |
| 标题 | **RetroAgent: From Solving to Evolving via Retrospective Dual Intrinsic Feedback** |
| 作者 / 机构 | Xiaoying Zhang（上海 AI Lab，项目负责人）、Zichen Liu（NUS）、Yipeng Zhang（独立）、Xia Hu（上海 AI Lab）、Wenqi Shao（上海 AI Lab，通讯）；核心贡献者 = Xiaoying / Zichen / Yipeng（p1 脚注） |
| 发表时间 / 出处 | 文件名日期 2026-03-09；PDF 版头 **arXiv:2603.08561v6 [cs.AI] 9 Jun 2026**（评估所见为 v6） |
| 论文链接 | arXiv:2603.08561 |
| 代码链接 | https://github.com/zhangxy-2019/RetroAgent |
| 标签 | 自演化智能体 · 在线 RL · 回顾式自我反思 · **双重内在反馈（数值 + 语言）** · SimUtil-UCB 检索 · GRPO/REINFORCE · 测试期适应 |
| **应用裁决** | **B 零件采用**（采用「回顾式双通道」的**回路形状**、**相对历史基线的进展信号**（去奖励化后）、**SimUtil-UCB 检索协议**、**pairwise 对比归纳**、**半组增强防早收敛**；不采用「内在奖励进梯度」「奖励塑形」「语言控制器」） |
| 优先级 | **P1**（慢环回顾编译通路的双通道形状来源 + 记忆检索打分协议 + 债务 22 / 「记忆门选择性」的直接参照） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：提出 **RetroAgent**——一个**在线 RL** 框架，在每个 episode 结束后用 **hindsight 自我反思** 生成**双重内在反馈**：① **Intrinsic Numerical Feedback**（把「相对既往最好水平的增量子任务进度」折算成 capability-evolution 内在奖励）；② **Intrinsic Language Feedback**（把成败轨迹蒸馏成可复用文本教训，存入记忆缓冲，用 **SimUtil-UCB** 检索复用）；在 ALFWorld / WebShop / Sokoban / MineSweeper 四基准上取得 SOTA（RL-Trained 变体 95.6 / 82.3 / 38.3 / 48.2 %，Table 1 p12），相对 GRPO 分别 +18.3 / +15.4 / +27.1 / +8.9 个百分点（Abstract p1，口径为 RL-Trained 变体）。
- **对 SSEA 的意义**：它把 SSEA 慢环**「回顾编译通路」**给出了一个**可运行的双通道实例**——「一条数值通道管探索、一条语言通道管复用」，并给出两个**能直接搬的协议**：① **历史基线 Φ_x + 整流增益 `[ϕ − Φ_x]₊`**（自归一、单调、只奖励「超越当前能力」的进展，天然排斥「无向新奇」）——这正是 SSEA **C9 修订版**所指「模型内部内在驱动（预测误差/内驱向量）」的最接近工业实现；② **SimUtil-UCB**（语义 + 历史效用 + UCB 探索奖励）——直击 SSEA「记忆门开得准不准的选择性缺失」与「retrieve 键收窄」。代价：它把内在信号**接进了 GRPO 梯度**并做**奖励塑形**（C9 明文违规），且语言深度在环（C2）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题

- **问题本身**（p1–3）：标准 RL 只优化 **extrinsic 任务奖励**，导致两个后果——① **过早收敛**：智能体过度利用早期成功、收敛到次优策略而不去探索替代路径；② **经验隐式化**：有用的经验只被**隐式编码进模型参数**，难以检索、检视、复用于后续策略改进。
- **它指出的既有方案缺陷**（§1 p2、§2 p3–4）：
  - *探索导向方法*（meta-RL 跨 episode 训练 / 不确定性调制奖励）：拓宽了搜索，但**不显式保存可复用经验**；
  - *记忆增强方法*：存原始轨迹或蒸馏技能/规则/教训，但记忆只作**被动上下文增强**——检索由**固定相似度**支配、**与下游效用无关**、且**与策略优化解耦**（"retrieval is governed by fixed similarity metrics, regardless of downstream utility, and remains decoupled from policy optimization"）；记忆噪声大时智能体变脆，过度依赖检索又抑制探索；
  - 两类方法**彼此分离**：探索的不管记忆、记忆的不管探索。
- **核心追问**（p2）：能否让探索与经验复用**耦合**，使经验**引导策略演化并被逐渐内化**，而不是被外部记忆缓冲长期供给？更广地，能否**从自身轨迹的内在信号**在稀疏外部监督下演化？

### 2.2 核心思想（关键 insight）

1. **「回顾」要把一次 episode 拆成两条互补信号，而不是一条**：数值信号回答 **「哪些轨迹有希望」**（whic），语言信号回答 **「该怎么做」**（how）——论文用消融证明二者**互补**（Table 7 p17：任一单独用 ≈78–80%，合并 ≈82.3%；p11 明说「textual memory alone is insufficient without progress-aware exploration signals」）。
2. **内在数值信号要相对「历史最好水平」而不是绝对进步**：`R_int = [ϕ(x,τ) − Φ_x]₊`，`Φ_x` 是该任务**历史最大组均值外在成功率**（Eq.5–6 p6）。性质：**progress-sensitive**（失败轨迹也可得正奖励）+ **self-normalizing**（Φ 单调不降 → 只有**超越当前能力阈值**的轨迹才拿分 → 奖励「能力提升」而非「无向新奇/重复的部分行为」，Prop 2/3 p6–7）。
3. **「From Solving to Evolving」的相变点 = 经验被内化进参数、不再依赖外部缓冲**：论文的判据是**测试期关掉记忆检索后性能几乎不掉**（Table 2 p13：in-context Discovery@1 78.9→76.8，Discovery@3 不变）→「dual intrinsic feedback is largely **absorbed into the policy parameters**」（p12）。这与 SSEA「慢环发布结构新版本、快环只读快照」在**相位结构**上同构，但**内化方向相反**（见 §5 C3/C8）。
4. **检索必须同时平衡相关性、历史效用与探索**：纯相似度会让少数记忆被反复引用（Fig.7a p16，多数条目 >15 次），加 **UCB 探索奖励**后访问更均匀（Fig.7c，多数 ≈5 次），性能也更好（Table 6 p16：相似度 70.1% → SimUtil-UCB 78.6%）。
5. **对比式归纳（pairwise induction）优于单轨迹归纳**：给反思函数额外喂一条**结局相反的参考轨迹** `τ_ref`，显著降低幻觉率并提升教训可用性（Table 3 p13；Fig.5/13 p14/p35）。
6. **记忆增强只能覆盖一半采样**：半组增强（ρ=1/2）优于全组（75.3% vs 72.9%，Table 4 p15）——全组会**降低多样性、促成过早收敛**（保留无引导探索）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| # | 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|---|
| **P1** | **Hindsight 自我反思元组** `z = (ϕ(x,τ), c, l)` | 轨迹 τ → 标量潜力分 ϕ∈[0,1] + 二元成败预测 c + 自然语言教训 l | 一次回顾同时产出数值与语言两条信号 | §3.1 p5 |
| **P2** | **Pairwise 归纳** `z = f_reflect(τ_ref, I_ext, τ)` | 当前轨迹 + **结局相反的参考轨迹** + 结局指示 → 反思元组 | 对比使模型「从相对差异推断结果」，降低幻觉、提升教训质量 | §3.1 p5；Table 3 p13 |
| **P3** | **历史基线 Φ_x** | `Φ_x^(k+1) = max{Φ_x^(k), 组均值外在成功率}` | 单调不降的「当前能力阈值」，自归一 | Eq.5 p6 |
| **P4** | **Capability-evolution 内在奖励** | `R_int = [ϕ(x,τ) − Φ_x]₊` | 只给**超越当前能力**的进展发内在分；失败轨迹也可得正分 | Eq.6 p6 |
| **P5** | **反思策略奖励**（RL-Trained 变体） | `R_reflect = R_ext · 1{c = I_ext}` | 用「成败预测是否与外在结局一致」训练反思能力 | Eq.3 p5 |
| **P6** | **记忆条目结构** | `m_i = (x_i, l_i, τ_i, u_i, n_i, d_i)` | 任务指令 + 教训 + **源轨迹回指** + 经验效用 + 检索计数 + 结局标签 | §3.3 p7 |
| **P7** | **SimUtil-UCB 检索** | `s_rel = cos(E(x), E(x_i))`（<0.4 丢弃）；`u_UCB = u_i + κ√(ln N_M / max(n_i,1))`；`S = α·s_rel + (1−α)·u_UCB`，取 top-K | 相关性 + 历史效用 + 探索的三合一排序 | Eq.8–10 p7 |
| **P8** | **效用 EMA 更新** | `u_i ← (1−β_util)u_i + β_util·û_t`（û_t = 该次 episode 的外在成功分） | 用**外在成败事实**更新记忆效用 | §3.3 p7 |
| **P9** | **半组记忆增强 rollout** | 每 prompt 采 N 条：N/2 用 base prompt，N/2 用记忆增强 prompt（ρ=1/2） | 既用经验又保留独立探索，防过早收敛 | §3.4 p9；Table 4 p15；附录 A Eq.14 p32 |
| **P10** | **GRPO 决策目标（复合回报）** | `G = Σ γᵗ(R_ext + R_int)` → 组内标准化优势 → clipped surrogate + KL | 把内在分并入策略优化 | Eq.11 p9 |
| **P11** | **REINFORCE 反思目标** | `J_Self-Reflection = E[Σ log φθ(z_j|τ) · R_reflect]` | 让反思能力与决策策略**联合演化** | Eq.12–13 p9 |
| **P12** | **Discovery@k 测试期适应度量** | `P(⋁_{i=1..k} r(y_i|x)=1)` | 量化「重复尝试下的自适应」——相变点的可测指标 | §4.3 p12 |

### 2.4 关键表示与数据结构

- **反思元组** `z = (ϕ, c, l)`：ϕ∈[0,1] 子任务完成率；c∈{success, failure}；l = 自然语言教训（WebShop 分 `action_lesson` / `navigation_lesson` 两字段，附录 E.1 p37–38；Sokoban 6 个子任务 + `trajectory_value`，附录 E.2 p46–47）。
- **记忆条目** `m_i = (x_i, l_i, τ_i, u_i, n_i, d_i)`：含**源轨迹回指 τ_i**（可审计、可重放）；`u_i` 初值 0.5；`n_i` 检索计数；`d_i` 起源结局（§3.3 p7）。**注意**：全文未给 `M` 的容量上限或淘汰机制——论文自述「memory buffer M (**which grows over time**)」（p5）。
- **句向量**：`sentence-transformers/all-MiniLM-L6-v2`（附录 B p35）；`E(x)` 与 `E(x_i)` 的余弦相似度作相关性。
- **轨迹 τ**：ReAct 格式（`<think>` + `<action>`）的状态—动作序列；max prompt 16384 / max response 2048 token（Table 10 p36）。
- **超参（Table 10 p36）**：N=8；γ=0.95；KL β=0.01；R_ext∈{0,10}；R_int∈[0,1]；β_util=0.05；κ=1.0；α=0.7（**但 §4.10 p19 显示 α=0.3 更优**）；memory-augmented ratio 1:1；λ_reflect=1.0；temperature 0.4。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 主结果 ALFWorld | GRPO 77.3±4.3；GiGPO 90.8±1.3 | **In-Context 91.7±1.2 / RL-Trained 95.6±2.3** | Table 1 p12；Success %，3 次独立运行，p<0.01 |
| 主结果 WebShop | GRPO 66.9±1.2；GiGPO 72.8±3.2；SkillRL 72.7 | **78.9±3.6 / 82.3±1.6** | Table 1 p12 |
| 主结果 Sokoban | GRPO 11.2±2.5；GiGPO 21.9±2.8 | **32.6±4.6 / 38.3±3.4** | Table 1 p12 |
| 主结果 MineSweeper | GRPO 39.3±2.7；GiGPO 41.1±1.2 | **47.9±2.0 / 48.2±2.0** | Table 1 p12 |
| **vs EvolveR（原始轨迹复用）** | EvolveR WebShop 17.6；ALFWorld 43.8 | RetroAgent WebShop **78.9–82.3** vs 17.6 | Table 1 p12；论文称「raw trajectories may contain noisy or task-specific details」（p11） |
| vs MemRL / Mem0 / SimpleMem+GRPO | MemRL WebShop 9.2；Mem0+GRPO 37.5；SimpleMem+GRPO 46.9 | RetroAgent 78.9–82.3 | Table 1 p12 |
| 测试期关记忆检索 | — | In-Context Discovery@1 78.9→**76.8**，@3 98.4→97.9；RL-Trained @3 不变 | Table 2 p13；→ 经验已内化 |
| 归纳方式（GPT-4o 评估） | 单轨迹归纳 | 幻觉率 失败 8.8→**3.8** / 成功 15.1→**11.9**；高可用分 76.7→**76.7**（失败）/ 12.2→**17.6**（成功） | Table 3 p13；800 条抽样，每 10 步 4 条/任务（附录 C p35） |
| 归纳方式下游影响 | GRPO 66.9 | 单归纳 70.3 / pairwise 72.9 / **pairwise+半组 75.3** | Table 4 p15；WebShop Success |
| 数值反馈消融 | GRPO 66.9 | 折扣回报 74.7 / +progress-guided 75.0 / **+capability-evolution 79.7** | Table 5 p15 |
| 语言反馈消融 | GRPO+折扣回报 74.7 | 相似度检索 70.1 / 相似度+效用 69.5 / **SimUtil-UCB 78.6** | Table 6 p16 |
| 双通道合并 | GRPO 66.9 | 仅数值 79.7 / 仅语言 78.6 / **In-Context 双 78.9** / **RL-Trained 双 82.3** | Table 7 p17 |
| 轨迹多样性（Vendi Score） | GRPO 成功 1.85 | 数值 2.04 / 语言 2.13 / In-Context 2.01 / **RL-Trained 2.20** | Table 8 p18 |
| 训练时间（WebShop，墙钟） | GRPO 11.78h | In-Context **14.61h**（追平 GRPO 峰值用时 6.33h，−46.26%）；RL-Trained **16.94h**（8.02h，−31.92%） | Fig.10 p19 |
| 跨架构（Llama-3.1-8B） | GRPO | ALFWorld 91.4–93.1 / WebShop 87.8–89.5 / Sokoban 24.5–39.1 / MineSweeper 52.3–59.9 | Table 9 p19；3 seeds，p<0.01 |
| 跨规模（7B→14B） | GiGPO | 任务分 +0.9%~+3.8%，成功率 +1.3%~+1.6% | Fig.11 p20 |
| 超参敏感性 | — | α：0.3（偏效用）> 0.7（偏相关）；λ_reflect 0→1 使成功率 75.8→82.3 | Fig.9 p18 |
| **算力** | — | **4×NVIDIA H200**；7B/8B；N=8；150/300 steps | 附录 B p35；Table 10 p36 |

> **口径警示（实测）**：Abstract 的 +18.3/+15.4/+27.1/+8.9 对应 **RL-Trained** 变体；§4.2 p11 的 +14.4/+12.0/+21.4/+8.6 对应 **In-Context** 变体；§3 p3 的「+10% WebShop / +16% Sokoban」是对**前 SOTA（GiGPO）**的差。**三套数字不同源，引用时必须标变体**。

### 2.6 论文自陈局限与边界条件

- **论文未设独立 Limitations 章节**（全文只有 Conclusion p20–21 与 Ethics p22）——这是一个**证据纪律缺口**，以下为散见自陈：
  - **多目标冲突**（自陈）：RL-Trained 变体在 ALFWorld / Sokoban 上**略低于** In-Context（Table 9 p19），论文归因「the auxiliary reflection loss may weaken the primary policy-gradient signal」，并「leave improved multi-objective balancing to future work」（p20）。
  - **双通道互相干扰**（自陈）：In-Context 双通道**略低于**「仅 capability-evolution 奖励」（Table 7 p17），论文称「simultaneous exploration signals from both feedback channels might interfere with each other during action selection」。
  - **对比归纳的悖论**（自陈）：pairwise 归纳**反思准确率最高**（Fig.8b 绿线）但**任务性能未提升**（Table 7 p17），论文解释为「the reflector infers outcomes from relative differences rather than developing robust standalone evaluation capability」——**意味着该机制可能学到的是「相对捷径」而非稳健评估**。
  - **规模收益有限**（自陈）：7B→14B 仅 +0.9%~+3.8%（Fig.11 p20）。
  - **未覆盖**：仅四个**模拟沙盒**任务（ALFWorld/WebShop/Sokoban/MineSweeper），未涉真实系统；未来工作提「multi-agent and open-ended settings」（p21）。
- **统计口径**：主结果**报 3 seed 均值±std 且 p<0.01**（Table 1 p12）——**优于 EvolveR 的无方差报告**；但 **Fig.9 敏感性、Fig.11 规模曲线未报方差**。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 任务域为文本具身（ALFWorld）/网页购物 / 网格谜题；状态与动作均为文本 token（ReAct 格式，§4.1 p11）；「成败」由任务成功判定 | 只搬**相位结构**（episode → 回顾 → 双通道结构 → 复用），控制对象换成生存结构化信号。**局部加分**：Sokoban/MineSweeper 的动作空间是**结构化**的（`up/down/left/right`、`(row,col)`，附录 E.2 p46/p48）→ 提示「结构化动作 + 回顾编译」可行 |
| **C2** 自然语言只作观察员接口 | **✗** | 语言深度在环：动作是文本、教训是 NL、反思靠 prompt、检索到的教训直接拼进输入 `f_memory(x,M) = x ⊕ l_retrieved`（§3.3 p7） | 语言通道**只能作观察员面**；数值通道（P3+P4）是唯一可进控制环的部分。**可借其发现**：语言教训若**不可执行**则无效——pairwise 归纳提升的是**具体性/因果准确性**（附录 E.3 p50 评分维度），与 EvolveR Table 6 的 Vague 结论一致 |
| **C3** 权重/记忆/技能三分离 | **◐** | 记忆**外置**（缓冲 M + MiniLM 嵌入，p7）；但论文**刻意把经验内化进 θ**（「largely absorbed into the policy parameters」，p12），与 EvolveR 的 exp-absorb 负结果**方向相反**；无技能层 | **必须二选一并写进判据**：SSEA 采「记忆与权重分离」（EvolveR 实证），**拒绝** RetroAgent 的内化路线。RetroAgent 的 Table 2（关检索不掉分）只证明**它的**内化有效，**不能**外推到 SSEA |
| **C4** 低算力低带宽 | **✗** | 4×H200；7B/8B；WebShop 墙钟 11.78h（GRPO）→ 14.61/16.94h；N=8 rollout；max prompt 16384 + response 2048；**记忆缓冲无上界增长**（p5） | 可搬的轻件：SimUtil-UCB 检索（top-K 打分）、Φ_x 单计数器更新、pairwise 归纳的**对比结构**（不含 LLM 调用）。重件（GRPO/REINFORCE 训练、每轨迹反思调用）**不进睡眠期预算**。缓冲无上界增长**直接违反**「缓冲不无界增长」，搬用必须补淘汰 |
| **C5** 精准回忆历史 | **◐** | 记忆条目含**源轨迹回指 τ_i** + 效用 + 检索计数 + 结局标签（p7）；检索是「语义 + 效用 + 探索」三合一（Eq.10 p7）。但**无遗忘/合并/剪枝**，M 只增不减 | **强件**：`τ_i` 回指指针（抽象 ←→ 具体可审计，同 EvolveR `source_traces[]`）；**弱件**：无遗忘 → 与 EvolveR 的 θ_prune 剪枝、MemRL 的遗忘率 FR 组合补齐 |
| **C6** 可自主修改自身 | **◐** | 提案权 ✓（自产教训与反思）；**边界权 ✗**（无白名单/范围约束）；**验证权 ✗**（无验证门，只有奖励）；应用权 ✓（GRPO 更新权重）；RL-Trained 变体甚至让模型**改写自身反思策略 φθ**（Eq.12 p9） | 补 SSEA 四权：边界权归白名单、验证权归四级验证门（只判合法性不打分）、应用权归原子升版。**RL-Trained 变体属「模型改自己的内在信号定义」→ 明确不采用**（见 C9） |
| **C7** 可保存/恢复/变异/继承 | **✗** | 无世代、无 GenePackage、无变异/继承；记忆与策略只在单次训练寿命内延续 | 同 EvolveR：可遗传的只有**回顾编译算子与门控参数**（Φ 口径、κ、α、半组比例），记忆内容与权重不可遗传 |
| **C8** 给基因先验，不给知识语料 | **✗**（若原样继承）/ **—**（原文无基因概念） | 记忆缓冲里是**纯后天教训**（NL 语料）；但「回顾编译的算子与门控参数」是结构性先验 | 明确的切分线（同 EvolveR）：可进基因 = Φ 更新口径 / SimUtil-UCB 的 κ,α / 半组比例；**不可进基因** = 教训内容本身。**且注意**：RetroAgent 的**内化路线**（教训进 θ）在 SSEA 里等价于「后天知识进权重」→ 双重违规 |
| **C9** 不设评分函数，只有淘汰函数 | **✗**（核心冲突；「第二层信号」本身仅 ◐） | 见下方三条判定表 | 见下方改造方向 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子；Qwen2.5 / Llama-3.1 / GRPO / REINFORCE / all-MiniLM / Verl 全借用（§4.1 p11、附录 B p35）；创新在**双通道反馈协议（L2）**与**回顾式反思方法（L3）** | — |

#### C9 专项：三条判定（针对「模型内部内在驱动」作第二层信号）

| # | 条件 | 判定 | 依据 |
|---|---|---|---|
| **①** | **信号源在模型内部**（非外部评分/观察员） | **◐** | 两个信号都由 hindsight self-reflection **自产**（p5）。**但**：数值信号的基线 `Φ_x` 由**外部 extrinsic 成功率**定义（Eq.5 p6）；语言信号的效用 `u_i` 由**外部 extrinsic 成功分** û_t 的 EMA 更新（p7）。即「**内部生成、外部标定**」。评测环节用 GPT-4o 作外部裁判（附录 C p35、E.3 p50），但**不在控制回路内**（仅评估） |
| **②** | **定义不可被模型修改** | **◐** | In-Context 变体：定义 = 人类写死的 prompt + 每个环境的子任务清单（附录 E.1/E.2 p37–49）→ **✓**。RL-Trained 变体：用 REINFORCE 训练反思策略 φθ（Eq.12 p9），**模型直接改写自己内在信号的生成过程** → **✗**。两变体合并 = **◐** |
| **③** | **不进入淘汰判定** | **✗** | `R_int` 直接加进 `R_aug = R_ext + R_int`（p6），经 GRPO 组内标准化优势（Eq.11 p9）**驱动策略选择/淘汰**；SimUtil-UCB 的 `S = α·s_rel + (1−α)·u_UCB`（Eq.10 p7）是**排序打分**并决定检索注入 → 进入决策回路。C9 明文「**奖励塑形…一律违规**」，此条正命中 |

- **C9 综合裁决：✗**。理由：论文的核心卖点恰是「把内在反馈**塑形进奖励**并**用于策略优化**」——这是 C9 点名禁止的**奖励塑形**。三条判定为 ◐ / ◐ / ✗。
- **改造方向（可救回部分）**：**只保留 P3+P4（`Φ_x` 与 `[ϕ−Φ_x]₊`）作为「结构提案的触发门」**——即当进展信号超过历史基线时**触发一次 ΔS/ΔR 提案**，由四级验证门**只判合法性、不打分、不排序**；**从 GRPO 优势中完全剥离**。同时把 SimUtil-UCB 的效用项 `u_i`（外部成功率 EMA）改为**事实口径**（如「被引用后行为是否改变」的机制计数），使检索排序退化为**事实淘汰**。**RL-Trained 变体（模型改写自身信号定义）整段不采用**。

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无（Qwen2.5-7B / Llama-3.1-8B / GRPO / REINFORCE / all-MiniLM / Verl 全借用） | 符合借用立场，零价值零风险 |
| **L2 信息流层** | **双通道内在反馈**（数值 + 语言）作为两条独立信号；**半组记忆增强 rollout**（ρ=1/2，base 与 memory-augmented 共享参数）；检索结果直接进输入 | **高**：SSEA 慢环「回顾编译通路」的**双通道形状**来源——一条管探索、一条管复用；半组增强是**防 Echo Trap** 的信息流设计 |
| **L3 学习层** | hindsight 自我反思（pairwise 归纳）、**相对历史基线的能力演化信号**、反思策略与决策策略**联合优化** | **高**：`Φ_x` 相对增益信号是 SSEA「内驱向量」的最近似工业实现；联合优化给出「反思能力自身可演化」的形状（但 SSEA 需去掉梯度耦合） |
| **L4 演化层** | 无（无变异/继承/世代） | **中**：提供反面界定——记忆与权重不可遗传（同 EvolveR） |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| episode → 回顾 → 双通道 → 复用 | 慢环 SEL 的**回顾编译通路**：trace → 抽象 → ΔS/ΔM/ΔR/Δθ。**注意相位差异**：RetroAgent 是**在线每回合**，SSEA 是**睡眠期离线**；SSEA 需把「每回合回顾」改为「睡眠期批量回顾」 |
| `Φ_x` 历史基线 + `[ϕ−Φ_x]₊` | **缺失组件（新增建议）**：SSEA「内在驱动第二层信号」的候选实现。落点 = 慢环的**进展门**，**只作结构提案触发**，不进淘汰判定 |
| SimUtil-UCB（Eq.8–10） | **记忆检索门**：直击「**记忆门开得准不准的选择性缺失**」与「`retrieve` 键收窄」。`u_UCB` 的探索项是 SSEA 当前检索所缺的「反过度利用」机制 |
| 记忆条目 `m_i = (x_i, l_i, τ_i, u_i, n_i, d_i)` | 记忆条目增加 `source_trace`（**回指**，同 EvolveR `source_traces[]`）+ `use_count` + `outcome` 三字段 → **债务 22**（记忆二级门用常量阈值）的「逐条目计数器」升级 |
| Pairwise 归纳（对比参考轨迹） | **抽象算子的质量控制**：与「技能表示够不够 / 0/33」直接相关——论文用**幻觉率**（失败 8.8→3.8%）与**可用性分档**（附录 E.3 p50 的 Specificity / Causal Accuracy / Utility）作判据 → 债务 25/26/27/28 的**判据形状**参照 |
| 半组记忆增强（ρ=1/2） | 快环 `retrieve` 的**调用预算与频率控制**：不自动注入，只对一半轨迹注入；可作 SSEA 的**探索—利用配比**初始值 |
| Discovery@k 测试期适应度量 | **验收指标**：量化「重复尝试下的自适应」——SSEA 可用它刻画「记忆/技能是否被内化/固化」 |
| 4×H200 / 14.61–16.94h | **睡眠期计算预算**的标定锚点（与 EvolveR 的 39.4h×8×A100 互为参照） |
| **内化路线（教训进 θ）** | **反例 / 冲突点**：与 EvolveR 的 exp-absorb 负结果**正面矛盾**，须写进 C3 判据文档 |

### 3.4 债务与验收实验对应

- **债务 22（记忆二级门用常量阈值，慢环不可调）**：RetroAgent 给「**逐条目计数器 `n_i` + 效用 `u_i` + UCB 探索项**」的形状——`n_i` 是**机制计数**（可对齐 C9 的「事实口径」），`u_i` 是外部成功率 EMA（**需去外部化**）。**UCB 探索项 `κ√(ln N_M/max(n_i,1))` 是纯计数、无外部评分**，可**直接移植**用于 SSEA 的记忆门。
- **记忆门「开得准不准」的选择性缺失**：SimUtil-UCB 的**三合一排序**（相关性 + 效用 + 探索）给出「开得准」的一个协议模板；Fig.7 p16 的访问分布（相似度 → 少数条目 >15 次；SimUtil-UCB → 多数 ≈5 次）是**分布形状判据**的现成参照。
- **`retrieve` 键收窄 → 召回精度上限低**：RetroAgent **同病**（MiniLM 语义相似 + 0.4 阈值，p7），但它证明**「提高检索打分维度」比「改键」更有效**（Table 6 p16：相似度 70.1 → SimUtil-UCB 78.6）。
- **技能表示够不够（0/33 之后仍未回答）**：pairwise 归纳的**判据维度**（Specificity / Causal Accuracy / Utility，附录 E.3 p50）给出「可执行性」之外的两个维度（**因果准确性**、**具体性**）；且论文揭示**反思准确率最高 ≠ 任务性能最好**（Fig.8b vs Table 7）→ 提示 SSEA 的判据**不能只看「信号是否准确」，要看「信号是否改变行为」**。
- **睡眠期计算预算未定义**：给出成本分解参照——**重件**（GRPO/REINFORCE 训练、每轨迹一次 LLM 反思调用、4×H200）；**轻件**（Φ_x 单计数器更新、SimUtil-UCB top-K 打分、UCB 计数）。**可搬零件几乎全在轻侧**。
- **可服务的验收实验（均为推断）**：实验 2（记忆召回，命中率 0.5164 基线）——SimUtil-UCB 的效用 + 探索项应改变命中率结构与访问分布；实验 3（技能固化 0/33）——pairwise 判据维度可重设判据形状。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **历史基线 + 整流增益 `R_int = [ϕ − Φ_x]₊`，`Φ_x` 单调不降**（去奖励化后只作提案触发门） | 算法/表示 | 改造移植 | 慢环「进展门」 | SSEA 缺「内在驱动第二层信号」的候选；自归一、排斥无向新奇 | 中 |
| 2 | **SimUtil-UCB 检索协议**（语义 + 效用 + UCB 探索项，Eq.8–10） | 算法 | 改造移植（效用项去外部化） | 记忆检索门 | 记忆门选择性缺失；检索键收窄；过度利用少数记忆 | 高 |
| 3 | **UCB 探索项 `κ√(ln N_M/max(n_i,1))`**（纯计数、无外部评分） | 算法 | **直接移植** | 记忆检索门 | 访问分布不均（Fig.7a→7c）；对齐 C9 的「无评分」 | 高 |
| 4 | **Pairwise 对比归纳**（喂一条结局相反的参考轨迹） | 方法/提示设计 | 改造移植（非语言版对比） | 回顾编译的抽象算子 | 抽象算子质量（幻觉率 8.8→3.8%）；0/33 判据形状 | 中 |
| 5 | **半组记忆增强（ρ=1/2）** | 协议 | 直接移植 | 快环 retrieve 调用策略 | 过早收敛 / Echo Trap；探索—利用配比初值 | 中 |
| 6 | **记忆条目带源轨迹回指 `τ_i`** | 表示 | 直接移植 | 记忆条目 `source_trace` | 抽象不丢证据；可审计、可重放、对接 Dream-RSI | 高 |
| 7 | **Discovery@k 测试期适应度量** | 基准/指标 | 直接移植 | 验收指标 | 量化「经验是否被内化/固化」 | 中 |
| 8 | **「反思准确率最高 ≠ 性能最好」（Fig.8b vs Table 7）** | 证据 | 直接引用 | 债务 25/26/27/28 判据 | 判据不能只看信号准确性，要看行为改变 | 高 |
| 9 | **「半组 > 全组」（75.3% vs 72.9%，Table 4）** | 证据 | 直接引用 | 防早收敛论证 | 全量注入记忆会降多样性、促早收敛 | 高 |
| 10 | **教训质量三分类评分协议**（Specificity / Causal Accuracy / Utility / is_hallucination，附录 E.3 p50） | 基准/方法 | 改造移植 | 判据形状 | 债务 25–28；「可执行性」之外的因果/具体性维度 | 中 |
| 11 | **「蒸馏教训 > 原始轨迹」（WebShop 78.9–82.3% vs EvolveR 17.6%）** | 证据 | 直接引用 | C5/C2 论证 | 原始轨迹噪声大；抽象更可迁移 | 高 |
| 12 | **成本锚点 4×H200 / 14.61–16.94h / N=8 / 16384 token** | 证据 | 直接引用 | 睡眠期计算预算 | 给未定义预算一个数量级锚点 | 高 |
| 13 | **RL-Trained 反思策略（反思能力与决策策略联合优化）** | 思想 | **仅作对照**（不采用） | — | 展示「信号定义可被模型改写」的失败模式 | 低 |
| 14 | **内化路线（教训进 θ）** | 反例 | **仅作对照** | C3 判据文档 | 与 EvolveR exp-absorb 负结果正面矛盾 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（逐条对应 3.1 的 ✗/◐）**
  1. **C9（最严重）**：① `R_int` 加进 `R_aug` 并用于 GRPO 优势 → **奖励塑形**，明文违规；② SimUtil-UCB 的 `u_i` 是**外部成功率 EMA** → 打分排序；③ RL-Trained 变体让模型**改写自身内在信号定义**（违反「定义不可被模型修改」）；④ **无任何验证门**。→ 只有「Φ_x 相对增益信号」在**剥离梯度**后可用。
  2. **C2**：语言深度在环（动作、教训、反思 prompt、检索拼接全为 NL）→ **语言通道不可进控制环**，只有数值通道可救。
  3. **C1**：任务域是文本具身/购物/谜题，不是生存控制。
  4. **C4**：4×H200、7B/8B、14.61–16.94h、N=8、16384 token；且**记忆缓冲无上界增长**（p5）——**直接违反「缓冲不无界增长」**。
  5. **C3/C8**：论文**刻意把经验内化进 θ**（p12），与 EvolveR 的 exp-absorb 负结果（0.382→0.371）**正面矛盾**；无世代/继承；教训内容为纯后天知识。
- **隐含假设与失效条件**
  - 需要**可判定的外在成败标签**（任务成功 / 购买匹配）来定义 `Φ_x` 与 `u_i`——SSEA 生存环境反馈更稀疏、且个体死亡后不再产轨迹 → **归因链更弱**；
  - 需要**同一任务可重复采样**（N=8、Discovery@k 的 k 次尝试）才有 `Φ_x` 组均值与检索计数；生存环境不可重放同一情境，除非有 Dream-RSI 式重放模拟器；
  - 需要 **LLM 反思算子**（附录 E 的 prompt）——SSEA 无 LLM，**抽象算子必须自建**（这是最大缺口，与 EvolveR 同病）。
- **算力 / 带宽 / 工程代价**
  - 重：GRPO + REINFORCE 训练（4×H200，14.61–16.94h）、**每条轨迹一次 LLM 反思调用**、max prompt 16384 + response 2048。
  - 轻：`Φ_x` 单计数器 max 更新、SimUtil-UCB top-K 打分、UCB 计数、`u_i` EMA。
  - **结论**：可搬零件全在轻侧；重侧（反思算子 + RL）恰是 SSEA 拿不到的两种能力（无 LLM、禁奖励）。
- **搬运后的可能退化模式**
  - 若照搬「内在奖励 + 自生成轨迹 + 自造教训」的 RL 配置 → 重演 **RAGEN 的 Echo Trap**（内部信号自我放大 → 方差塌缩 → 熵塌缩）；RetroAgent 的 `R_int` + `R_reflect` 是**双层内部信号**，风险高于单层。**半组增强（P9）是它自带的缓解手段**，可作对照。
  - 若只搬「记忆 + 效用打分」而丢掉抽象算子 → 库中将堆满**不可执行教训**（与 EvolveR 低分档 50% Vague 同类），而 SSEA 无 LLM 识别 → **库静默膨胀**。
  - 若照搬内化路线 → **C3/C8 双违规**（后天知识进权重、无分离）。
  - 记忆缓冲无上界增长 → **C4 违规**；且论文未给容量—性能曲线，**拐点未知**（对比 EvolveR 有 4.2k→50k 的曲线）。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **直接对照 / 最强证据** | **EvolveR** | RetroAgent 在 Table 1 把 EvolveR 作为基线并**大幅超越**（WebShop 78.9–82.3% vs **17.6%**；ALFWorld 91.7 vs 43.8），论点「raw trajectories may contain noisy or task-specific details」（p11）→ 这是 **EvolveR「存原始轨迹」路线的直接反证**。**但同时**：两篇在**内化**上**结论相反**——EvolveR 的 exp-absorb 消融证明「经验进权重反而退化」（0.382→0.371），RetroAgent 的 Table 2 证明「经验已内化、关检索不掉分」（78.9→76.8）。**这一对矛盾必须写进 SSEA 的 C3 判据文档**，并作为「内化是否安全」的待裁决问题 |
| **互补（记忆侧主干）** | **FLEX** | FLEX 是「冻结 LLM + 分层经验库（golden/warning）+ updater 写入三分支」，是 SSEA **记忆组织/写入侧主干**；RetroAgent 补 **检索侧**（SimUtil-UCB 的效用 + UCB 探索）。接口：FLEX 的 golden/warning 分层可作 RetroAgent 教训条目的**层标签**；RetroAgent 的 `u_UCB` 可作 FLEX 写入分支的**准入参考** |
| **互补（检索键）** | **Memento** | Memento 给「冻结 LLM + 案例库 + **可学习检索 μ**」；RetroAgent 的 SimUtil-UCB 是**手工设计**检索（α, κ）。**互补**：Memento 的可学习 μ 替换 RetroAgent 的固定 α/κ；RetroAgent 的效用 + UCB 给 Memento 的检索**加效用与探索维度** |
| **互补（检索/遗忘）** | **MemRL** | MemRL 两阶段检索 + 冻结库迁移验收 + **遗忘率 FR**；RetroAgent 的 `n_i` 计数与 `u_i` 效用可给 MemRL 的 FR 提供**分布侧**指标（FR 是率，`u_i` 直方图是分布）；且两篇在「策略是否冻结」上**对照**（MemRL 冻结策略、RetroAgent 训练策略） |
| **前置依赖 / 警告** | **RAGEN** | RetroAgent 的「内在奖励 + 自生成轨迹 + 自造教训 + 策略训练」是 Echo Trap 的**高危配置**；且它**自带一条实据**支持 RAGEN 的诊断——半组增强优于全组（75.3% vs 72.9%）、全组降多样性（Table 4 p15）→ **可直接引用为「防 Echo Trap」的正面案例**。若 SSEA 启用任何 Δθ 路径，**必须先挂** RAGEN 的奖励 std / 熵 / 梯度范数监控 |
| **互补（离线验证场）** | **Dream-RSI** | RetroAgent 的 `Φ_x` 与 Discovery@k 依赖**可重复尝试**；Dream-RSI 的离线重放模拟器可提供「淘汰/提案前的反事实重放」，使 `Φ_x` 无需真实死亡即可更新。**接口**：Dream-RSI 生成的重放轨迹 → RetroAgent 式回顾编译 → 结构提案 |
| **互补（巩固协议）** | **Self-Consolidation** | Self-Consolidation 提供「睡眠期把经验固化为可复用结构」的**协议**；RetroAgent 的「教训 → 内化」是同一动作的**信号源**。**注意**：RetroAgent 的固化为「进 θ」，SSEA 的固化为「发布结构新版本」——**协议可借，方向须改** |
| **同族对照 / 前置** | **Reflexion** | RetroAgent 的自我反思是 Reflexion 的**可训练 + 双通道升级版**；论文把 Reflexion 归为 prompting-based 基线（Table 1 p12：WebShop 28.8% vs RetroAgent 78.9–82.3%）。Reflexion 是 SSEA 已有的 P2 卡片，RetroAgent 说明「反思若只作 transient hint（不改变策略本体）则上限低」 |
| **同族对照** | **Mem0 / SimpleMem** | Table 1 直接对比（Mem0+GRPO 37.5%、SimpleMem+GRPO 46.9%）；两篇是 SSEA 已有记忆卡片的近邻，RetroAgent 用「效用 + 探索检索」超越 |
| **同族对照（技能侧）** | **SkillRL / PSN / SkillWeaver** | SkillRL（教师模型诱导技能）是 Table 1 的强基线（WebShop 72.7%），与 **PSN** 的「带契约可执行技能网络」同族；RetroAgent 的教训是**非执行型**的——PSN 的契约式技能可替换 RetroAgent 的语言教训，一次性消掉 C2 与 C9 冲突 |
| **理论近亲** | **Gödel Agent / 自指自改进** | RL-Trained 变体让「反思策略」自我优化，是自指自改进的一个工程实例（但方向与 SSEA 相反：模型改自己的信号定义 = C9 违规） |
| **替代** | 固定相似度检索的记忆库（ExpeL / 纯 RAG 式） | 以「语义 + 效用 + UCB 探索」的三合一检索替换固定相似度 |

### 6.2 推荐组合方案

1. **记忆侧（最高优先）：FLEX（写入/分层）× RetroAgent（检索）× Memento（可学习键）× MemRL（遗忘）**
   - 接口形态：FLEX 的 golden/warning 分层作条目层标签；RetroAgent 的 SimUtil-UCB 作**检索打分**（效用项去外部化）；Memento 的可学习 μ 替换固定 α/κ；MemRL 的 FR 作遗忘率。
   - 新增能力：记忆的**写入—检索—遗忘**闭环，且检索同时考虑相关性、效用与探索。
   - 新增风险：四套机制串行后延迟上升；须先测「检索命中率」（对照现有 0.5164）与「访问分布」两个分母。
2. **回顾编译侧：RetroAgent（双通道形状）× PSN（技能表示）× Self-Consolidation（巩固协议）**
   - 接口形态：RetroAgent 的双通道作**外骨架**（数值管探索、语言管复用）；PSN 的**带契约可执行技能网络**替换语言教训；Self-Consolidation 的巩固协议替换「进 θ」的内化。
   - 新增能力：经验 → 可执行技能（而非文本建议）；进展信号只**触发提案**、由 PSN 成熟度门 + 回滚验证判合法性。
   - 新增风险：可执行技能的错误传播面更大，需 SEDM 式准入兜底。
3. **验证场：Dream-RSI × RetroAgent 的 Φ_x / Discovery@k**
   - 接口形态：Dream-RSI 的离线重放提供可重复尝试 → 更新 `Φ_x`、算 Discovery@k。
   - 新增能力：无需真实死亡即可标定「能力阈值」与「测试期适应」。
   - 新增风险：重放与真实分布的偏差会污染 `Φ_x`。
4. **训练侧（若且仅若启用 Δθ）：RAGEN × RetroAgent 的半组增强**
   - 接口形态：任何权重更新必须挂 Echo Trap 三件套监控；**采用** RetroAgent 的「半组增强 + 保留无引导探索」，**禁止**照搬复合奖励。

### 6.3 本篇在组合中的典型角色

- **双通道回顾编译通路的形状提供者**（一条数值通道管探索、一条语言通道管复用）+ **记忆检索协议源**（SimUtil-UCB 三合一打分、UCB 探索项）+ **「内在驱动第二层信号」的最近似实现**（`Φ_x` 相对增益）+ **C3 内化争议的反方证人**（与 EvolveR 正面矛盾）+ **防早收敛的实据**（半组 > 全组）。
- **它不是主干**：反思算子（LLM）与动力源（GRPO/REINFORCE 奖励）都不可搬，因此定位为**零件采用（B）**；主干仍由 **FLEX/Memento（记忆）** 与 **PSN（技能）** 承担。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 「回顾式双通道 + 相对基线的进展信号」正是 SSEA 慢环回顾编译通路与 C9 修订版「内驱第二层信号」的核心关切（实测：双通道机制完整，§3.2–3.3 p6–7）；扣分项是任务域为文本具身/购物/谜题，控制对象为语言模型（实测） |
| 立场兼容性 | **2** | C1/C2/C9 三重明确冲突（实测：奖励塑形 + 语言在环），C3/C4/C8 亦冲突（实测：内化进 θ、4×H200、无上界缓冲）；加分项是 **UCB 探索项本身无外部评分**、C10 ✓（推断） |
| 可搬运性 | **3** | UCB 探索项与 `Φ_x` 相对增益信号在**协议层**可干净拆出（推断）；但**反思算子是 LLM 调用**、动力源是 RL，两者均不可搬——这是本篇核心部件，故封顶 3 |
| 证据强度 | **4** | 4 基准 × 2 模型族、**3 seed 均值±std、p<0.01**、系统消融（Table 2–9）+ 理论（Prop 2/3/7、Thm 6/9）+ GPT-4o 反思质量审计（800 条）+ **明确披露算力**（实测）；扣分：**无独立 Limitations 章节**、外部裁判是 GPT-4o（近似循环）、「内化」结论由 Discovery@1 小幅下降推得、Fig.9/11 无方差 |
| 组合价值 | **5** | 与 EvolveR（直接对照）、FLEX、Memento、MemRL、RAGEN、Dream-RSI、Self-Consolidation、Reflexion、Mem0/SimpleMem、PSN/SkillRL **十条线都能点名接上**（推断） |
| 落地成本 | **3** | 反向口径：协议件（UCB 检索、Φ 计数、半组比例）重实现廉价；但完整搬运需 4×H200×14.61–16.94h，且「非语言反思算子」需自建（隐性高成本）（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用 ① **双通道回顾编译的回路形状**（数值管探索 + 语言管复用，在线→离线改造），② **SimUtil-UCB 检索协议**（含**可直接移植**的 UCB 探索项），③ **`Φ_x` 历史基线 + 整流增益**作「内在驱动第二层信号」的候选（**必须去奖励化、只作提案触发门**），④ **pairwise 对比归纳**与**教训质量判据维度**，⑤ **半组增强**与**Discovery@k** 两个协议件，⑥ 成本锚点 4×H200 / 14.61–16.94h。**不采用**：内在奖励进 GRPO 梯度（C9）、RL-Trained 反思策略（模型改写自身信号定义）、语言控制器本身（C2）、教训内化进 θ（C3/C8）。
- **优先级：P1** —— 不是立即动手（P0），但应在**慢环回顾编译通路设计定稿前**与**记忆门改造（债务 22）时**强制参照。

- **建议动作**
  1. **先搬 UCB 探索项（最干净）**：记忆检索打分增加 `κ√(ln N_M / max(n_i,1))`（**纯计数、无外部评分**，对齐 C9），`n_i` 逐条目维护；这直接回应「记忆门选择性缺失」与「访问分布不均」。
  2. **把 `Φ_x` 相对增益改造成「提案触发门」**：`Φ_x` 用**环境侧事实**（存活/回避事件计数）维护、单调不降；当 `[进展 − Φ_x]₊ > 0` 时**触发一次 ΔS/ΔR 提案**，交由四级验证门**只判合法性**，**不进梯度、不进淘汰判定**。
  3. **检索效用项去外部化**：把 `u_i`（外部成功率 EMA）改写为事实口径（如「被引用后行为是否改变」的机制计数），使检索排序退化为**事实淘汰**（对齐 C9）。
  4. **写进 C3 判据文档**：记录 **EvolveR（内化有害）vs RetroAgent（内化有益）的直接矛盾**，并把「是否允许经验进 θ」列为待裁决；SSEA 默认采 EvolveR 侧（记忆与权重分离）。
  5. **建 issue：非语言反思算子**——本篇证明反思算子存在且关键（pairwise 归纳降幻觉 8.8→3.8%），但 SSEA 无 LLM，需自建；与「技能表示够不够 / 0/33」合并处理。
  6. **建 issue：记忆缓冲上界**——RetroAgent 的 M **无上界增长**，搬用前必须补淘汰机制（借 EvolveR 的周期剪枝或 MemRL 的 FR）。

- **最小验证实验（回顾式进展门双臂，服务实验 2 记忆召回 + 实验 3 技能固化）**
  - **双臂 / 消融设置**：A 臂 = 现有记忆检索（无 UCB 探索项、无逐条目计数）；B 臂 = 检索打分加 **UCB 探索项 + `n_i` 计数**，并加**进展门**（`[进展−Φ_x]₊>0` 才触发结构提案，提案只走四级验证门）。两臂 ≥8 seed，跑现有生存环境，任务与初始条件固定。
  - **判据（分档，先看分母）**：
    1. **机制计数（分母先查）**：检索条目总数、`n_i` 分布（对照 Fig.7 的「少数 >15 次」）、提案触发次数、Φ_x 更新次数、写入被拒率；
    2. **行为差**：逐帧动作差、`retrieve` 命中率（对照现有 **0.5164**）、动作分布熵/多样性（对照 Table 8 的 Vendi Score 思路）；
    3. **淘汰结果**：危险回避率 —— 注意两臂现均为 **0.9814（饱和）**，此项**已无分辨率**，须换更高难度环境或换指标，否则不得据此项下结论。
  - **预期与证伪**：预期 B 臂检索访问分布更均匀（KDE 从长尾转向集中）、命中率上升、提案数量不爆炸。证伪条件：① 若 `n_i` 分布无变化，说明当前检索量根本没到需要探索的程度，实验应推迟；② 若提案触发频繁但**行为不变**（呼应论文 Fig.8b vs Table 7 的「准确率高 ≠ 性能好」），说明进展信号与动作无耦合，应回头做动作 5；③ 若 B 臂命中率不升反降，说明 UCB 探索项在 SSEA 的小库规模下引入了噪声。

- **若 E 不采用**：不适用（确实有可搬零件）。

---

## 9. 待确认问题

1. **`Φ_x` 在无重复尝试的生存环境下如何定义（最关键）**：RetroAgent 的 `Φ_x` 是「同一任务历史最大组均值外在成功率」，依赖 N=8 可重复采样；SSEA 生存环境不可重放同一情境 → `Φ_x` 是否需要 Dream-RSI 式重放才能更新？
2. **「内化有益」还是「内化有害」**：RetroAgent（Table 2：关检索仅 78.9→76.8，称已内化）与 EvolveR（Table 11：exp-absorb 0.382→0.371，内化有害）**正面矛盾**。差异是否来自任务域（QA vs 具身/谜题）或训练范式（GRPO 复合回报 vs 离线蒸馏）？**这是 SSEA C3 判据的悬案**。
3. **去奖励化的等价物**：`[ϕ−Φ_x]₊` 剥离梯度后，还剩多少「引导探索」的能力？会不会退化成「只作日志」而失去作用？需在设计阶段就定死判据（同 EvolveR 待确认问题 2）。
4. **α 的口径矛盾**：Table 10（p36）默认 α=0.7（偏相关），但 §4.10（p19）说 α=0.3（偏效用）更优——**默认值与最优值不一致**，论文未解释；这直接影响 SSEA 检索权重初值。
5. **「反思准确率高 ≠ 性能好」的机理**：论文归因为「相对捷径」，但未给机制级解释；若 SSEA 采用对比式回顾，**须先验证它学到的不是捷径**。
6. **记忆缓冲上界与拐点**：RetroAgent 未给 M 的容量—性能曲线（对比 EvolveR 有 4.2k→50k 的曲线）；SSEA 搬运时**无法预判拐点**。
7. **算力口径**：Fig.10 的墙钟时间是否含**每轨迹的 LLM 反思调用**？论文只说「training time」，未明说（同 EvolveR 待确认问题 6）。
8. **需补查文献**：GiGPO（Feng et al. 2025，当前 SOTA 基线）、LaMer（Jiang et al. 2025，meta-RL 基线）、SkillRL（Xia et al. 2026，教师模型诱导技能）、LLF（Xu et al. 2025，语言反馈学习的理论框架，Thm 6 来源）——用于确认「效用 + 探索检索」是否已有更早等价方案。
9. **需团队决策**：SSEA 的 `rules` 通道当前**零消费者**；RetroAgent 的**教训（lesson）**是否作 `rules` 的第一批内容形态？还是等 PSN 的契约式技能先落地？

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “Standard reinforcement learning (RL) for large language model (LLM) agents primarily optimizes **extrinsic task rewards**, often favoring isolated task completion over continual adaptation.” | p1 |
| “RetroAgent augments extrinsic rewards with **hindsight-generated dual intrinsic feedback**: (i) **Intrinsic Numerical Feedback**… (ii) **Intrinsic Language Feedback**…” | p1 |
| 两变体：“(i) an **in-context** self-reflection mechanism, and (ii) an **RL-trained** self-reflection mechanism whose reflective capability is jointly optimized with the decision policy.” | p3 |
| 缺陷批评：“memory is typically used as **passive context augmentation**: retrieval is governed by **fixed similarity metrics, regardless of downstream utility**, and remains **decoupled from policy optimization**.” | p2 |
| 核心追问：“Can an agent couple exploration with explicit experience reuse so that experience guides policy evolution and is **gradually internalized**, rather than being persistently supplied by an external memory buffer?” | p2 |
| 反思元组 `z = (ϕ(x,τ), c, l)`：标量潜力分 + 二元成败预测 + NL 教训 | p5 |
| **Eq.3** `R_reflect := R_ext,(i) · 1{c = I_ext}`（反思奖励 = 外在奖励 × 预测正确指示） | p5 |
| **Eq.5** `Φ_x^(k+1) = max{Φ_x^(k), Ī_ext_k(x)}`（历史基线单调不降） | p6 |
| **Eq.6** `R_int_k(τ) = [ϕ(x,τ)_k − Φ_x^(k)]₊`；性质：**progress-sensitive** + **self-normalizing** | p6 |
| **Prop 2**：`J_aug(π;x) ≥ J_ext(π;x) + δ·p_{k,δ}(π;x)`；**Prop 3**：`R_int > 0 ⟺ ϕ > Φ_x` | p6–7 |
| 记忆条目 `m_i = (x_i, l_i, τ_i, u_i, n_i, d_i)` | p7 |
| **Eq.8** `s_rel = cos(E(x), E(x_i))`，`s_rel < 0.4` 丢弃；**Eq.9** `u_UCB = u_i + κ√(ln N_M / max(n_i,1))`；**Eq.10** `S = α·s_rel + (1−α)·u_UCB` | p7 |
| **Def.4** memory-informative；**Thm.6** `dim_TE(H, Cℓ, ε|M) ≤ dim_E(R_H, ε)`（记忆降低探索复杂度）；**Prop.7** SimUtil-UCB 三性质 | p8–9 |
| **Eq.11** GRPO 决策目标（含 KL）；**Eq.12** REINFORCE 反思目标；**Eq.13** `J = J_Decision + λ_reflect·J_Self-Reflection` | p9 |
| Algorithm 1（训练框架，含 Φ_x 更新、`R_int ← max(0, ϕ − Φ_x)`、效用 EMA） | p10 |
| 主结果：RetroAgent In-Context **91.7/87.6/78.9/32.6/47.9**；RL-Trained **95.6/88.9/82.3/38.3/48.2**；GRPO **77.3/75.5/66.9/11.2/39.3** | p12 (Table 1) |
| 论文自述“RetroAgent achieves… outperforming GRPO by **+14.4, +12.0, +21.4, +8.6** percentage points”（对应 In-Context） | p11 |
| Abstract 的 +18.3 / +15.4 / +27.1 / +8.9（对应 **RL-Trained**） | p1 |
| **vs EvolveR**：“on WebShop, RetroAgent achieves **78.9–82.3%** success versus **17.6%** for EvolveR… raw trajectories may contain noisy or task-specific details” | p11 |
| **Table 2**：关记忆检索 In-Context Discovery@1 **78.9→76.8**，@3 98.4→97.9 → “dual intrinsic feedback is largely **absorbed into the policy parameters**” | p12–13 |
| **Table 3**：pairwise vs single 归纳——幻觉率 失败 **8.8→3.8**、成功 **15.1→11.9** | p13 |
| **Table 4**：pairwise+**半组 75.3%** > pairwise 全组 72.9% > single 全组 70.3% > GRPO 66.9% | p15 |
| **Table 5**：GRPO 66.9 → 折扣回报 74.7 → +progress-guided 75.0 → **+capability-evolution 79.7** | p15 |
| **Table 6**：相似度检索 70.1、相似度+效用 69.5、**SimUtil-UCB 78.6** | p16 |
| **Fig.7**：相似度检索 → 多数条目 >15 次；SimUtil-UCB → 多数 ≈5 次 | p16 |
| **Table 7**：仅数值 79.7 / 仅语言 78.6 / 双 In-Context 78.9 / 双 RL-Trained **82.3** | p17 |
| **Table 8**：Vendi Score 成功轨迹 GRPO 1.85 → RL-Trained **2.20** | p18 |
| **Fig.10**：GRPO 11.78h / In-Context **14.61h**（追平用时 6.33h，−46.26%）/ RL-Trained **16.94h**（8.02h，−31.92%） | p19 |
| **Fig.9**：α=0.3（偏效用）优于 0.7；λ_reflect 0→1 使成功率 75.8→82.3 | p18–19 |
| **Table 9**：Llama-3.1-8B 上 RL-Trained 在 ALFWorld/Sokoban **略低于** In-Context（“interference between reflection and decision-making objectives”） | p19–20 |
| **Table 10**：N=8、γ=0.95、β=0.01、R_ext{0,10}、R_int[0,1]、β_util=0.05、κ=1.0、α=0.7、ratio 1:1、λ_reflect=1.0、16384/2048 token | p36 |
| **算力**：“All experiments were conducted on **4 NVIDIA H200 GPUs**”；句向量 all-MiniLM-L6-v2 | p35 |
| 附录 E.3 教训质量判据：`lesson_quality_score`(1–10)、`specificity_rating`、`utility_rating`、`is_hallucination`（GPT-4o 作外部裁判） | p50 |
| 局限（散见）：“the auxiliary reflection loss may **weaken the primary policy-gradient signal**”；“simultaneous exploration signals from both feedback channels might **interfere with each other**”；pairwise 归纳“**does not improve task performance**” | p17 / p20 |
