# 论文分析卡片 · ExperienceSynthesis（DreamGym）

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-11-05 Scaling Agent Learning via Experience Synthesis.pdf` |
| 标题 | **Scaling Agent Learning via Experience Synthesis**（框架名 **DreamGym**） |
| 作者 / 机构 | Zhaorun Chen\*, Zhuokai Zhao, Kai Zhang, Bo Liu, Qi Qi, Yifan Wu, Tarun Kalluri, Sara Cao, Yuanhao Xiong, Haibo Tong, Huaxiu Yao, Hengduo Li, Jiacheng Zhu, Xian Li, Dawn Song, Bo Li, Jason Weston†, Dat Huynh†；Meta Superintelligence Labs、FAIR at Meta、University of Chicago、UNC、UC Berkeley（\*work done at Meta，†joint last author） |
| 发表时间 / 出处 | 文件名日期 2025-11-05；PDF 首页 `Date: November 7, 2025`；**arXiv:2511.03773v2 [cs.AI] 10 Nov 2025**；27 页 |
| 论文链接 | arXiv:2511.03773 |
| 代码链接 | **无**（全文 27 页未见 GitHub / 项目页 / 数据发布声明） |
| 标签 | 经验合成 · 推理式经验模型（reasoning experience model）· 抽象文本状态空间 · 经验重放缓冲（active replay buffer）· 奖励熵课程任务生成 · 抽象空间策略改进理论界 · GRPO/PPO · sim-to-real · WebShop/ALFWorld/WebArena |
| **应用裁决** | **B 零件采用**（采 ①「**合成经验作反事实对照素材**」这一能力形态、②**奖励熵难度选择器** `V_τ`、③**四维经验评委**（含 Hallucination & Failure Feedback）、④**Theorem 1 的两项误差口径** `(εR, εP)`；**不采**其 outcome 奖励 + GRPO/PPO 回路（C9）、LLM 经验模型本体与语言状态空间（C1/C2）、以及把蒸馏进 Mexp 的外部环境知识当先验遗传（C8）） |
| 优先级 | **P1**（直击当前最紧的「判据饱和 / 指标全绿但行为没变 / 环境对无消费者通道报成功」；且是「经验合成族」的核心对照，须在慢环提案验证与判据重设前参照） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：提出 **DreamGym**——不用真实环境 rollout，而是把一个 **推理式经验模型 Mexp** 当作环境动力学：在**抽象文本状态空间**里用 CoT 逐步推导 `(下一状态, 奖励)`，配合**经验重放缓冲**（offline 真实数据初始化 + 在线补充）与**奖励熵课程任务生成**，纯合成经验即可训练 RL 智能体；WebArena（非 RL-ready）上「超所有基线 >30%」（摘要 p1；Table 1 p7 给出 13.3 vs GRPO 传统 7.3），WebShop/ALFWorld 上以 **0 真实交互**追平 80K 真实交互的 GRPO/PPO（Table 1 p7），且训练开销降至真实环境 RL 的约 **1/3–1/5**（p8）。
- **对 SSEA 的意义**：它正面回答 SSEA 最缺的那一问——**当真实经验稀缺/重复时，如何获得有判别力的训练/验证素材**——答案是「不采集，**合成反事实**」（"若采取动作 a，环境会如何回应"），并附赠一个专挑「两臂有差别」情境的**难度选择器**（奖励熵 `V_τ`）与一个专查「**幻觉成功**」的验收维度。它对 SSEA 的**唯一正面用途**是把「合成素材」降格为**对照物/校准器**（而非训练动力源）：SSEA 的淘汰函数必须仍归环境。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题

- **问题本身**（p1–2）：用 RL 训练 LLM 智能体有四大障碍——**rollout 昂贵、任务多样性有限、奖励信号不可靠、基础设施复杂**，四者共同阻碍「可扩展经验数据」的采集。
- **它指出的既有方案缺陷**（§2.1 p3、§2.2 p3–4）：
  1. **静态专家轨迹 / 离线模仿**（SFT、DPO、oracle 脚本轨迹）：需大量人工标注，缺多样性与自适应性；
  2. **从间接知识造轨迹**（AgentTrek、Synatra）与**合成任务扩展**（AgentSynth、SCA）：仍然依赖真实环境的数据采集，**scalability 问题原封不动**；
  3. **world model 路线**（AlphaGo、Dreamer、WebDreamer、WebEvolver）：在**原始像素空间**重建世界，data-hungry 且昂贵；
  4. **最接近的 UI-Simulator**（Wang et al. 2025b）：也把 LLM 当逐步模拟器，但**需大量专家工程适配新环境**，且**只能生成轨迹变体供 SFT**，不支持通用 RL。
  - 对环境的直接批评：网页/GUI 高度动态 → 奖励噪声、稀疏甚至**假反馈**；动作不可逆（真网站删条目）；**多数环境没有可靠 reset 机制**（p2）。

### 2.2 核心思想（关键 insight）

1. **在抽象元表示空间合成状态转移**：丢掉原始观察里的无关维度（raw HTML、header、tag），直接合成干净的元素列表——**更 informative、更省 token**，且经验模型训练**样本高效**（§4.1 p5；Fig.5 p10 实测 2k–10k 样本即具竞争力）。
2. **推理（CoT）是经验质量的关键，history 是因果连贯的关键**：显式推理轨迹 `R_t` 让状态转移因果可溯；**去掉 reasoning** → informativeness 下降、**hallucination 上升**；**去掉 history** → consistency 下降（Fig.4 p9、Table 2 p9）。经验模型必须「结构化、推理驱动」。
3. **难度是「选」出来的，不是「设」出来的**：用 **group-based reward entropy** `V_τ = (1/n)Σ(r_i − r̄)²`（Eq.7 p6）挑种子任务——**非零方差**意味着智能体在该任务上既有成功也有失败，即「可行但困难」；成功/失败**均衡时熵最大、信息增益最大**（p6，与「LLM 从中等难度任务学得最好」一致，引 Gao et al. 2025）。
4. **合成环境只需保真「学习相关信号」，不需克隆原始状态**：Theorem 1（Eq.9 p17）给出真实环境策略改进下界，真实/合成环境的性能 gap `Δmodel` **只依赖奖励准确度 `εR` 与域一致性 `εP`，不依赖状态重建误差**（Lemma 1 p18：`|J_M(π)−J_M̂(π)| ≤ εR/(1−γ) + 2γRmax/(1−γ)²·εP`）。
5. **合成经验可作 sim-to-real 的暖启动**：先纯合成训练，再用**少量**真实 rollout 微调（DreamGym-S2R，5K 真实数据），稳定超过从零在真实环境训练的 GRPO/PPO（§5.2 p8、Table 1 p7）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| # | 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|---|
| **P1** | **推理式经验模型 Mexp** | `(s_t, a_t)` + history `{(s_i,a_i)}` + 任务 τ + top-k demos `{d_j}` → `(s_{t+1}, r_{t+1})` + 推理轨迹 `R_t` | 用 CoT 逐步推导环境响应；**无效动作则转移到失败态并给 0 奖励** | Eq.4 §4.1.1 p5 |
| **P2** | **抽象文本状态空间 S** | raw observation → 清洗后的元素列表（丢 HTML/tag/无关结构） | 降维、省 token、提高 informative 度；使 Mexp 训练样本高效 | §4.1 p5 |
| **P3** | **active replay buffer** | offline 真实轨迹初始化 → 在线合成交互持续补充；`{d_j}=Topk(cos(φ(s_t,a_t), φ(s_i,a_i)))` | 用相似历史经验**降低幻觉、提高事实性**；随策略共同演化 | §4.1.1 p5、Fig.2 p4 |
| **P4** | **经验模型 SFT 联合目标** | 标注推理轨迹 `R*_t` 的 transition 数据集 → Mexp 参数 | 同时学「生成忠实推理」与「据推理预测下一状态」 | Eq.5 p6 |
| **P5** | **课程任务生成器 `M_task`** | m 个种子任务 → 变体任务（与 Mexp 共享参数） | 持续产出渐进更难的任务；选择标准「最具挑战但仍可行」 | Eq.6 p6；选择 prompt 附录 C.1/C.2/C.3 p19–23 |
| **P6** | **奖励熵任务价值 `V_τ`** | n 次 rollout 的 outcome 奖励 `{r_i}` → `V_τ = (1/n)Σ(r_i − r̄)²` | **只用于挑种子任务**（选高熵 = 最大信息增益）；`λ` 限制每轮合成任务比例以稳住训练 | Eq.7 p6 |
| **P7** | **outcome 奖励口径** | 轨迹 → `r=1` 仅终步成功，其余 `r=0` | 供 GRPO/PPO 训练策略 | §4.1.1 p5（following Feng et al. 2025） |
| **P8** | **经验模型四维评委** | 100 条随机轨迹 + GPT-4o judge → 4 维各 `{0,1,2}` | 诊断经验质量：**Causal State Consistency / Diversity & State Variation / Informativeness / Hallucination & Failure Feedback** | 附录 C.4 p27、Fig.4 p9 |
| **P9** | **sim-to-real 状态空间对齐** | 合成态 ↔ 真实态 → 同一 rule-based mapping 函数或轻量微调模型 | 保证转移无缝（合成→真实） | §4.3 p7 |
| **P10** | **策略改进理论界** | `(εR, εP, δ, γ, Rmax)` → `J_M(π′)−J_M(π) ≥ 合成增益 − 信赖域罚 − 2Δmodel` | 把「合成环境够不够用」变成**两项可测误差**的问题 | Theorem 1 Eq.9 p17；Lemma 1 Eq.26 p18 |

### 2.4 关键表示与数据结构

- **MDP**：`M = (S,A,T,R,γ,ρ_0)`；`S` 为**抽象文本状态空间**，`τ_0` 为自然语言任务指令（§3.1 p3–4）。
- **经验模型输入四件套**：当前 `(s_t,a_t)` + interaction history + task instruction `τ` + top-k 检索 demos（§4.1.1 p5）。
- **经验模型输出**：`(s_{t+1}, r_{t+1})` 与**显式推理轨迹** `R_t`（Eq.4 p5）。
- **replay buffer**：语义嵌入检索（`φ(·)` 为任意语义编码器）+ top-k；offline 数据初始化、在线持续 `retrieve/update`（Fig.2 p4）。
- **课程任务记录**：任务 ID + Reward + **Entropy**（Fig.2 p4 的 `T3/T7/T15` 表）——即任务价值表。

### 2.5 实验证据

| 实验 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **WebArena-Lite**（非 RL-ready，165 任务） | SFT 6.1 / DPO 5.5 / GRPO 传统(80K) 7.3 / PPO 传统(80K) 6.7（均为 L3.2-3B） | **DreamGym 13.3**（L3.2-3B）/ 9.1（L3.1-8B）/ 12.7（Q2.5-7B）；DreamGym-S2R 13.9 / 9.7 / 11.2 | Table 1 p7；成功率 %；**真实数据 0**（S2R 为 5K） |
| **WebShop**（RL-ready） | GRPO 传统 62.1 / 65.0 / 66.1；PPO 传统 59.9 / 64.2 / 68.1（80K 真实交互） | **DreamGym 59.3 / 63.9 / 68.3（0 真实交互，追平）**；DreamGym-S2R 70.5 / 75.0 / 72.1（5K，**超基线**） | Table 1 p7；成功率 % |
| **ALFWorld**（RL-ready） | GRPO 传统 65.3 / 70.9 / 79.8；PPO 传统 47.0 / 72.9 / 81.1 | DreamGym 62.1 / 66.3 / 71.0；**DreamGym-S2R 65.0 / 75.9 / 82.4** | Table 1 p7；成功率 % |
| **组件消融**（WebShop / WebArena） | — | 全量 63.9 / 13.3；**w/o Exp. Replay 59.2 / 9.7**；**w/o Exp. Reasoning 55.8 / 7.3**；**w/o Task Generation 57.3 / 7.3**（去任务生成 −6.6 / −6.0） | Table 2 p9；成功率 % |
| **经验模型四维评委** | 传统真实环境 / DreamGym / w/o History / w/o Reasoning | **w/o History → consistency 显著降**；**w/o Reasoning → informativeness 降 + hallucination 升**；全量在四维最优或近最优 | Fig.4 p9；**100 条随机轨迹**，GPT-4o judge，每维 `{0,1,2}`（附录 C.4 p27） |
| **经验模型样本效率 / 骨干** | WebDreamer（微调过的 web world model） | 2k–10k 样本即具竞争力；L3.1-8B 在 WebShop **10k 样本 >50%**；L3.2-3B **20k 样本 ≈55%**；WebArena 低数据下 WebDreamer ≈13% 领先、**随数据增多被追平** | Fig.5 p10；成功率 % |
| **训练开销** | 真实环境 RL 基线 | DreamGym 把训练开销（rollout 采样 + GPU 小时）降至真实环境 RL 的约 **1/3 甚至 1/5** | p8（Fig.3 Left p8）；无绝对 GPU-hours |
| **跨域迁移** | 直接在该域训练的 SFT | WebShop↔WebArena 互相迁移**超过**目标域 SFT；但 **web→ALFWorld 域差距过大时性能显著下降** | Fig.3 Middle p8 |
| **算力资源** | — | 全部实验（含基线）**8 nodes × A100 + 4 nodes × H100**；WebArena 基线仅能开 **4 台 AWS server（≤4 并行 session）** | 附录 A.1/A.2/A.3 p15–16；**未给 GPU-hours** |

> 统计口径缺口：全文**未报告 seed 数与方差**；WebArena 上论文自陈「部分轨迹未能正确执行、某些任务被 WebArena 原始评估函数误判」，且「为公平保留全部轨迹 as-is」（A.3 p16）——**该基准的数字本身带已知噪声**。

### 2.6 论文自陈局限与边界条件

- **假设依赖**：① 需要**可判定成败的 outcome 标签**（`r∈{0,1}`，QA/任务完成式）；② 需要**离线真实轨迹语料**冷启动 Mexp（WebShop 1,600 人类演示 + 2,000 oracle/random；ALFWorld 3,200 专家 + 2,000；WebArena 4,800 条取自排行榜高分 agent——A.1/A.2/A.3 p15–16）——**不是 zero-data**；③ 需要**同域**（跨域过大即退化）。
- **明确不适用的情形**：论文自陈**只研究单环境学习**，universal world model 是**未来工作**（Limitations p11）；域差距过大（web→ALFWorld）性能显著下降（p8）。
- **经验模型质量受基座约束**：L3.2-3B 弱于 L3.1-8B（Fig.5 p10）；低数据下专门微调的 WebDreamer 反超通用 8B 模型（p10）。
- **未披露**：seed 数、方差、显著性、绝对 GPU-hours；**未做**合成经验「是否引入幻觉捷径」的端到端对照实验（只有 LLM 评委的诊断分）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 任务是 web 导航 / 电商 / 具身文本控制；控制对象是 LLM 的文本动作策略（§3.1 p3–4、Table 1 p7），无生存/结构化信号 | **只搬「合成对照素材」这一功能位，不搬控制对象**：把「Mexp 预测下一状态」映射为 SSEA 慢环的**反事实模拟器**，其输入输出换成结构化状态，其产物**只进验证/对照面，不进快环闭环** |
| **C2** 自然语言只作观察员接口 | **✗**（语言即状态空间本体） | 状态是「抽象**文本**状态空间」（§4.1 p5）；动作是文本/工具调用；推理靠 CoT prompt（附录 C p19–25） | 抽象算子必须换成 SSEA 的非语言算子。**但有一处可借的思想**：抽象化 = **丢无关维度、保学习相关信号**（P2），SSEA 可照此定义结构化状态；另 Fig.4 证明「**去掉推理 → 幻觉上升**」——推理降低幻觉这一点与语言无关，SSEA 的内在预测误差机制同向 |
| **C3** 权重/记忆/技能三分离 | **◐**（记忆轴 ✓，技能轴缺失） | replay buffer **完全外置**（offline 初始化 + 在线补充 + top-k 检索，§4.1.1 p5）与策略权重分离；但**无技能层**；且 Mexp 本身是训练进权重的 LLM | 借「外置重放缓冲」作 SSEA 记忆库的一种形态；**关键区分**：SSEA 的**合成器进权重是可接受的**（它是工具/算子），**知识库内容不进权重**（与 EvolveR 的 exp-absorb 负结果同向） |
| **C4** 低算力低带宽 | **◐**（绝对重 / 相对降本） | 绝对：8 nodes A100 + 4 nodes H100（A.1 p15），**未给 GPU-hours**；WebArena 基线只能 4 并行 session。相对：抽象状态空间**降 token**、训练开销降至真实 RL 的 **1/3–1/5**（p8） | 搬**相对降本的两条原理**：① 抽象降维状态空间（信息少而结构化）；② 「合成 rollout 比真实 rollout 便宜」。**不搬绝对规模**；「睡眠期预算」可用「合成轻 / 训练重」的成本分解 |
| **C5** 精准回忆历史 | **◐** | replay buffer 按**语义相似** top-k 检索（`cos(φ(s,a),φ(si,ai))`，§4.1.1 p5）；无结构化寻址、无写入/遗忘治理 | 检索精度问题**同病**（与 Memento/MemRL 的纯嵌入相似一致），交 Memento 的 μ 与 MemRL 两阶段检索；本篇只贡献「**用相似经验降低幻觉**」这一检索动机 |
| **C6** 可自主修改自身 | **✗** | 无自修改；Mexp 训练完成后冻结，只训练 agent policy；无提案/边界/验证/应用四权 | 无可用零件；SSEA 的四级验证门仍须自建 |
| **C7** 可保存/恢复/变异/继承 | **✗** | 无世代、无 GenePackage、无变异/继承；replay buffer 与 Mexp 均限于单次训练寿命 | 见 C8 的切分线 |
| **C8** 给基因先验，不给知识语料 | **✗**（原样继承知识）/ **◐**（只继承算子） | **判定见下** | **必须切分**：可进基因 = **合成/重放算子与选择器参数**（结构性先验）；**不可进基因** = 蒸馏进 Mexp 的**外部环境知识**（来自 WebArena 排行榜高分 agent、WebShop 官方 repo 人类演示等外部语料，A.1–A.3 p15–16） |
| **C9** 不设评分函数，只有淘汰函数 | **✗**（RL 侧，明确违规）/ **◐**（选择侧，可改造） | RL 侧：outcome 奖励 `r∈{0,1}` + GRPO/PPO 直接更新策略（§4.1.1 p5、§3.2 p4）——**外部奖励函数**，教科书级违规。选择侧：`V_τ` 奖励熵**只用于挑种子任务，不给模型打分、不排序模型**（Eq.7 p6） | RL 侧**整段不采用**。选择侧**是 C9 合规的最小实现**：把 `V_τ` 用作 SSEA 的**情境/难度选择器**（挑「两臂有差异」的情境），**只判「有分辨力/无分辨力」，不打分、不排序个体** |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | Llama-3.1/3.2、Qwen-2.5、GRPO、PPO、SFT、CoT、BGE 类语义编码器全借用；创新在框架信息流（L2）与经验模型训练（L3） | — |

**C8 专项判定（本卡片的核心问题）——合成经验是「自造内部素材」还是「变相外部知识注入」？**

- **裁决：生成侧是「外部知识注入」，产物侧是「自造素材」——两者必须分开看。**
  1. **Mexp 的知识来源是外部的**：论文明确用公开 benchmark 的**离线真实轨迹**训练经验模型（WebShop 官方 repo 1,600 条人类演示 + 2,000 条 oracle/random；ALFWorld 3,200 专家 + 2,000；WebArena 4,800 条取自 IBM CUGA / ScribeAgent / Learn-by-Interact / AgentOccam 等排行榜高分 agent，A.1–A.3 p15–16）。**合成经验的「生成能力」来自外部语料蒸馏**——就 C8 而言，这是**变相外部知识注入**，不是凭空自造。
  2. **合成出的轨迹是新样本**（组合出未见过的状态序列），但**不是新知识来源**：它不产生环境之外的规律，只是把蒸馏到的动力学**外推/重排**。
  3. **对 SSEA 的切分线**：**可进 GenePackage = 合成算子 + 选择器参数**（「会做梦」是一种本能/结构先验，C8 允许）；**不可进 GenePackage = Mexp 学到的环境动力学内容**（后天知识，C8 禁止跨代）。
  4. **与 Agent0 的对照（关键）**：Agent0 主张「零数据」，其底座是**预训练语料压缩物**；DreamGym 连「零真实在线 rollout」都要求先有**离线真实轨迹**——在 C8 判定上，**DreamGym 的零数据主张比 Agent0 更弱**，但它是**更强的「合成素材工程范例」**。

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无（Llama/Qwen、GRPO/PPO、SFT、CoT 全借用） | 符合借用立场，零价值零风险 |
| **L2 信息流层** | **合成经验作为独立数据通道**；「抽象降维状态空间」的信息流设计；replay buffer 作为可检索通道；**Theorem 1 给出「保真度只需两项」的口径**；sim-to-real 的同一 mapping 对齐 | **最高**：SSEA 慢环「反事实素材生成器」的接口形状；`(εR, εP)` 是「合成素材是否真实可达」的**校验标准**；「抽象降维」是 C4 的正面参照 |
| **L3 学习层** | 经验模型 SFT 联合目标（推理 + 状态预测，Eq.5）；课程任务生成（Eq.6）；`V_τ` 选择 | **中高**：`V_τ` 可直接改造为「判据分辨力校准器」；但 Mexp 训练本身是 LLM 训练，不可搬 |
| **L4 演化层** | 无（无变异/继承/世代） | **中**：提供**反面界定**——合成器与知识库均不可遗传（C8 判据来源） |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **Mexp（合成/反事实生成器）** | **新增建议**：慢环「**反事实对照素材生成器**」，与 **Dream-RSI 的离线重放模拟器并列**（Dream-RSI 重放已有发现；Mexp 外推未见状态 → 双档：安全档重放 / 探索档合成）。**硬约束**：产物只进验证/对照面，**不进快环闭环** |
| **奖励熵 `V_τ`（Eq.7）** | **新增建议**：**判据分辨力校准器**。当危险回避率两臂均 **0.9814（饱和）** 时，`V_τ→0` 即「该情境无分辨率」——用 `V_τ` **先筛情境、再谈指标** |
| **四维经验评委（含 Hallucination & Failure Feedback）** | **债务 25/26/27/28**（判据形状错、**环境对无消费者通道报成功**、技能失效被判成成功）的现成判据维度——「无效动作应转移失败态并给 0 奖励」正是 SSEA 缺的**失败反馈通道** |
| **Theorem 1 `(εR, εP)`** | **合成素材校验标准**：只查**奖励准确度**与**域一致性**，**不查状态重建误差**——直接回答「合成素材是否真实可达」 |
| **抽象降维状态空间** | **C4** 的结构化信号参照；也是「`retrieve` 键收窄」的提示——降维要丢无关维度但**保住判别力** |
| **active replay buffer（offline 初始化 + 在线补充）** | 记忆库的一种形态；**冷启动靠外部语料**这一点是 C8 的反例教材 |
| **sim-to-real 状态空间对齐** | 四级验证门中「沙盒 → 环境实测」的状态映射接口 |
| **成本分解（合成轻 / 训练重；1/3–1/5）** | **睡眠期计算预算**的分解模板 |

### 3.4 债务与验收实验对应

- **判据饱和（危险回避率两臂均 0.9814）/ 指标全绿但行为没变**：本篇 `V_τ`（Eq.7 p6）是**直击此病灶**的零件——「两臂同一分数 ⇒ 方差 0 ⇒ 信息增益 0 ⇒ 该情境无效」。与 **GenEnv 的 α 带**（`p(1−p)` 在 p=1/2 最大）是同一数学事实的两个形式。
- **债务 25/26/27/28（判据形状错 / 环境对无消费者通道报成功 / 技能失效被判成成功）**：四维评委的 **Hallucination & Failure Feedback** 维度（附录 C.4 p27）给出「无效动作 → 失败态 + 0 奖励」的判据形状；`w/o Reasoning → hallucination↑`（Fig.4 p9）证明**推理缺失是幻觉主因**。
- **技能表示够不够 / 0/33**：本篇的「合成反事实」可提供对照素材——「**若技能生效，环境状态应如何变**」；若合成对照与实测无差异 → 说明该技能**没有可观测行为签名**，即表示不足（推断）。
- **睡眠期计算预算未定义**：提供**成本分解参照**（合成 rollout 轻 / RL 训练重；抽象状态空间降 token），并给「合成经验作暖启动」的成本—收益形状（1/3–1/5）。
- **Gene Manager 缺失 / C8**：给出「**算子可遗传、内容不可遗传**」的明确切分线（§3.1 C8 专项）。
- **可服务的验收实验（均为推断）**：实验 3（技能固化 0/33）——合成反事实对照重设判据形状；实验 2（记忆召回 0.5164）——`V_τ` 可作召回素材的**分辨力预筛**。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **「合成经验作反事实对照素材」协议**（"若采取 a，环境应如何回应"，含失败态） | 思想/协议 | 改造移植（去语言、产物只进验证面） | 慢环 · 反事实素材生成器（新增） | 真实经验稀缺/重复时缺有判别力的素材 | 中 |
| 2 | **奖励熵难度选择器** `V_τ = (1/n)Σ(r_i−r̄)²` | 算法 | 改造移植（**只选不训**） | 判据分辨力校准器（新增） | **判据饱和**（0.9814 两臂）、指标全绿但行为没变 | 高 |
| 3 | **四维经验评委**（尤其 **Hallucination & Failure Feedback**） | 协议/基准 | 改造移植（去 LLM 评委，改结构化判定） | 债务 25/26/27/28 判据 | 环境对无消费者通道报成功；合成素材引入幻觉捷径 | 高 |
| 4 | **Theorem 1 的两项误差口径 `(εR, εP)`** | 理论 | 直接引用 | 合成素材校验标准 | 「合成素材是否真实可达」的判据 | 中 |
| 5 | **抽象降维状态空间**（丢无关维度、保学习相关信号） | 思想 | 仅借思想 | C4 结构化信号 | 缓冲膨胀 / 键收窄 | 中 |
| 6 | **课程任务生成 + 「最具挑战但仍可行」选择 prompt** | 算法 | 改造移植 | 课程/情境供给 | 情境稀缺、探索停滞 | 中 |
| 7 | **active replay buffer**（offline 初始化 + 在线补充 + top-k 检索） | 工程/协议 | 改造移植 | 记忆库形态 | 冷启动与经验检索 | 中 |
| 8 | **sim-to-real 同一 mapping 对齐** | 工程 | 改造移植 | 四级验证门（沙盒→环境实测） | 沙盒与实环境状态不一致 | 中 |
| 9 | **「w/o Reasoning → hallucination↑」消融** | 证据 | 直接引用 | C2 论证 | 推理（≠语言）是幻觉的主要抑制项 | 中 |
| 10 | **训练开销降至 1/3–1/5** | 证据 | 直接引用 | 睡眠期预算 | 预算定义 | 中 |
| 11 | **成本分解：合成轻 / 训练重** | 思想 | 仅借思想 | 睡眠期预算草案 | 预算档位划分 | 中 |
| 12 | **`V_τ` 与 GenEnv α 带同源**（p≈0.5 处信息增益最大） | 证据/理论 | 直接引用 | 判据校准理论依据 | 为什么是「两臂各半」而非「全对/全错」 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 的 ✗/◐）：
  1. **C9（最严重）**：outcome 奖励 `r∈{0,1}` + GRPO/PPO 更新策略（§4.1.1 p5、§3.2 p4）——外部奖励函数，**整段不采用**。**注意**：本篇的 `V_τ` 与 RL 奖励是**两件事**，`V_τ` 只选任务（可搬），RL 奖励训策略（不可搬）；搬运时**必须切干净**。
  2. **C2**：语言是状态空间本体（抽象文本空间 + CoT），Mexp 本体不可搬——**抽象算子须自建**（与 EvolveR 同一瓶颈）。
  3. **C1**：任务域是 web/具身文本控制，不是生存控制；「成败」由任务完成判定，SSEA 只有淘汰/存活事实。
  4. **C4**：绝对资源 8×A100 nodes + 4×H100 nodes（未给 GPU-hours）；真实环境基线本身要 4 台 AWS server——**说明「真实 rollout 昂贵」这一动机对 SSEA 同样成立**。
  5. **C8**：Mexp 依赖**外部真实轨迹语料**（A.1–A.3 p15–16）——合成能力是外部知识蒸馏物，**不可当先验遗传**。
- **隐含假设与失效条件**：
  - 需要**可判定成败的 outcome 标签**；SSEA 生存环境反馈更稀疏，且个体死亡后不再产生轨迹 → **归因链更弱**。
  - 需要**离线真实轨迹冷启动**；SSEA 若无真实 trace，Mexp 无从蒸馏。
  - 需要**同域**；跨域过大即退化（web→ALFWorld，p8）。
  - 经验模型质量受基座约束（3B < 8B；低数据下 WebDreamer 反超）。
- **算力 / 带宽 / 工程代价**：
  - 重：Mexp 的 SFT（需外部语料 + LLM 标注推理轨迹）；agent policy 的 GRPO/PPO。
  - 轻：`V_τ` 计算（只需 rollout 奖励的方差）、四维评委（离线诊断）。
  - **结论**：可搬的零件全在「轻」侧（选择器 + 判据协议 + 理论口径）；「重」侧（合成器本体 + RL）恰是 SSEA 拿不到的两种能力。
- **搬运后的可能退化模式**：
  - **幻觉捷径**：若把 Mexp 的合成状态当**真值**用于验证 → 合成器「报成功」会掩盖真实失败。**这正是 SSEA 债务 26 的形态**（环境对无消费者通道报成功）。→ **硬规矩**：合成素材的判据**必须来自确定性代码/环境**（见 ScaleEnv / Agent-World），不能来自 LLM 推理。
  - **双重自我放大**：若同时用合成素材 + 内部评分（如 `V_τ` 排序个体）→ 重演 **RAGEN 的 Echo Trap**（方差塌缩 → 熵塌缩 → 崩溃）。→ `V_τ` **只选情境、不排序个体**。
  - **饱和迁移**：`V_τ` 若在 SSEA 现有情境上**全部≈0**（因为两臂本就同分），说明**瓶颈在情境难度而非素材来源**——须先换更难情境。
  - **C8 违规**：把 Mexp 学到的动力学内容纳入 GenePackage → 代际知识膨胀。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **互补（最紧）** | **GenEnv（难度对齐共演化）** | GenEnv 的 α-Curriculum Reward `R_env(p̂)=exp(−β(p̂−α)²)`（α=0.5）与本篇 `V_τ` 奖励熵是**同一件事的两个形式**——都对准 p≈0.5 的最大信息增益带（GenEnv Proposition 1：梯度信号 ∝ `p(1−p)`）。**关键区别**：GenEnv 用 `R_env` **训练**环境策略（C9 违规）；DreamGym 用 `V_τ` **只做种子选择**（**C9 合规的最小实现**）。→ **取 DreamGym 的「只选不训」版本，不取 GenEnv 的奖励训练版** |
| **互补** | **AutoEnv（跨环境度量）** | AutoEnv 给**判据健康度检查**（差分模型测试：弱模型≥强模型即判据近随机，丢弃；`Skin-Inverse` 控制消融）；DreamGym 给**反事实素材**。合起来 = 「**先证明判据有分辨力，再用合成素材施压**」——顺序不可颠倒 |
| **互补（双档）** | **Dream-RSI（重放模拟器）** | Dream-RSI 把**发现历史当重放模拟器**（只重放**已有**）；DreamGym 把**环境动力学蒸馏进经验模型**（可外推**未见**状态）。→ **安全档用 Dream-RSI（只重放），探索档用 DreamGym（合成）**；两者共用「离线零执行成本评估」的相位结构 |
| **同族对照（关键区分）** | **Agent0（零数据）** | Agent0 = 「零**标注**」，底座是预训练语料；DreamGym = 「零真实**在线** rollout」，但需**离线真实轨迹**。二者都非真「零外部知识」。**C8 判定**：DreamGym 的零数据主张**更弱**；但作为**合成素材工程范例**它**更强** |
| **同族对照** | **EvolveR（经验生命周期）** | EvolveR 蒸馏「**原则**」（语言抽象，供**策略检索**）；DreamGym 蒸馏「**环境动力学**」（供 **rollout 生成**）。两者都是「经验 → 抽象 → 复用」。**关键交叉**：EvolveR 的 **exp-absorb 负结果**（经验进权重反而退化 0.382→0.371）与 DreamGym 的 Mexp 进权重形成对照——**工具/算子进权重可接受，知识库内容进权重不可接受**（C3 的判据） |
| **前置依赖 / 警告** | **RAGEN（Echo Trap）** | DreamGym 用 GRPO 在**自合成经验 + 自造奖励**上训练 = Echo Trap **高危配置**（自生成数据 + 内部信号）。若 SSEA 启用任何权重侧更新，**必须先挂** RAGEN 的奖励 std / 熵 / 梯度范数监控 |
| **互补** | **Agent KB（跨域经验复用，2025-07-08，暂无专卡）** | Agent KB 做经验的**检索/复用**（跨域）；DreamGym 做经验的**生成**。合起来 = 经验的「**生成侧 + 检索侧**」 |
| **互补（判据来源，强烈推荐）** | **ScaleEnv / Agent-World（环境合成）** | 二者把环境做成**可执行代码 / 数据库状态**（判据 = 确定性代码对最终状态的检查）；DreamGym 把环境做成 **LLM 推理**（判据 = 概率生成）。**合成广度（DreamGym）+ 确定性判据（ScaleEnv/Agent-World）**是正解：**DreamGym 便宜但可能幻觉，ScaleEnv 确定但覆盖面窄**。SSEA 若用合成素材，**判据必须取自确定性代码侧** |
| **互补** | **Memento / MemRL** | replay buffer 的 top-k 语义检索精度有限（同病）；Memento 的**可学习 μ** 与 MemRL 的**两阶段检索**补检索键精度；本篇只贡献「**用相似经验降低幻觉**」的检索动机 |
| **互补** | **SEDM（记忆准入官）** | SEDM 管**准入**；DreamGym 的合成素材在入库前也须过准入（防止幻觉条目污染库） |
| **风险呼应** | **Misevolve（误演化威胁模型）** | DreamGym 的合成器若被误用为真值，会生成**看似合理实则虚假**的反馈——属 Misevolve 的「工具/环境路径」误演化，可互引 |
| **替代** | 无 | **不能替代**真实环境淘汰；合成素材只能**对照/校验**，不能当动力源 |

### 6.2 推荐组合方案

1. **判据分辨力组合（最高优先）：本篇 `V_τ` × GenEnv α 带 × AutoEnv 判据健康度**
   - **接口形态**：`V_τ` 做**情境预筛**（`V_τ≈0` 的情境直接标记「无分辨率」）；GenEnv 的 α=0.5 给**目标难度带**；AutoEnv 的差分模型测试给**判据可信度**终检。
   - **新增能力**：把「判据饱和（两臂均 0.9814）」从「结果」变成**可提前诊断的前置检查**。
   - **新增风险**：三套筛选串行后可用情境骤减；须先测「被筛掉的情境占比」这一分母。
2. **素材生成组合（双档）：本篇 Mexp 反事实 × Dream-RSI 重放模拟器**
   - **接口形态**：安全档 = Dream-RSI 重放已有发现；探索档 = Mexp 合成未见状态；**两档产物均只进验证面**。
   - **新增能力**：真实经验稀缺/重复时仍能造出有判别力的对照。
   - **新增风险**：探索档的幻觉；须由 ScaleEnv 式确定性判据兜底。
3. **校验组合：本篇四维评委 × ScaleEnv 确定性判据**
   - **接口形态**：四维评委（去 LLM 化）作**离线诊断**；ScaleEnv 的规则式判据作**准入终检**。
   - **新增能力**：合成素材「是否真实可达」有可执行判据（而非 LLM 说好就好）。
   - **新增风险**：规则式判据覆盖窄，可能拒掉合法合成素材。
4. **成本侧：本篇 × SSEA 睡眠期预算定义**
   - **接口形态**：按「合成轻 / 训练重」分解，只把轻侧纳入睡眠期草案。

### 6.3 本篇在组合中的典型角色

- **反事实对照素材生成器**（当真实经验稀缺/重复时提供对照）+ **难度/情境选择器**（奖励熵 `V_τ`）+ **幻觉捷径的验收协议提供者**（四维评委）+ **C8 的切分线标本**（算子可遗传 / 蒸馏知识不可）。
- 它**不是**主干：合成器本体是 LLM、动力源是 RL 奖励，两者均不可搬，因此定位 **B 零件采用**。主干仍由 **PSN（技能）** 与 **Memento（记忆）** 承担；本篇专司**判据分辨力**这一当前最紧的病灶。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 「真实经验稀缺/重复时如何获得有判别力的素材」正是 SSEA 当前最紧的问题（实测：`V_τ` 与四维评委机制完整，Eq.7 p6、附录 C.4 p27）；扣分项是任务域为 web/具身文本、控制对象为 LLM（实测），与生存架构无关 |
| 立场兼容性 | **2** | C1/C2/C9 三重明确冲突（实测：outcome 奖励 + GRPO/PPO、语言状态空间、web 任务域）；C8 依赖外部真实轨迹语料（实测：A.1–A.3 p15–16）。加分项：`V_τ` **只选不训**是 C9 合规的最小实现；Theorem 1 只要求 `(εR,εP)` 两项（推断） |
| 可搬运性 | **3** | `V_τ` 选择器、四维判据协议、`(εR,εP)` 口径在**协议层**可干净拆出（推断）；但**合成器本体是 LLM**（核心部件）不可搬——故封顶 3 |
| 证据强度 | **3** | 3 环境 × 3 backbone 主结果（Table 1 p7）+ 组件消融（Table 2 p9）+ 四维评委（Fig.4 p9，100 轨迹）+ 样本效率曲线（Fig.5 p10）+ 理论界（Theorem 1 p17）；**扣分**：全文**未报 seed/方差**，WebArena 自陈**评估函数会误判任务**（A.3 p16），且摘要「>30%」与 Table 1 数字口径不一致（见 §9） |
| 组合价值 | **5** | 与 GenEnv、AutoEnv、Dream-RSI、Agent0、EvolveR、RAGEN、Agent KB、ScaleEnv/Agent-World、Memento/MemRL/SEDM **九条线都能点名接上**（推断） |
| 落地成本 | **3** | 反向口径：`V_τ` 与判据协议**廉价**（只需 rollout 奖励方差、离线诊断）；但合成器本体需 LLM + 外部语料 + 训练，是**隐性高成本**（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用 ① **`V_τ` 奖励熵难度选择器**（**只选不训**，作判据分辨力校准器），② **四维经验评委**（去 LLM 化，尤其 Hallucination & Failure Feedback，作合成素材与失败反馈判据），③ **Theorem 1 的 `(εR,εP)` 校验口径**，④ **「合成经验作反事实对照素材」的能力形态**（产物只进验证面）。**不采用** outcome 奖励 + GRPO/PPO 回路（C9）、LLM 经验模型本体与语言状态空间（C1/C2）、把蒸馏进 Mexp 的外部环境知识当先验遗传（C8）。
- **优先级：P1** —— 不立即动手（P0），但**必须在「判据重设」与「慢环提案验证设计定稿前」强制参照**；是当前「判据饱和」病灶的最直接外部参照。

- **建议动作**
  1. **先做分辨力筛选器，不做合成器**：实现 `V_τ = (1/n)Σ(r_i−r̄)²` 作为**情境预筛**——对现有验收实验的每个情境算 `V_τ`，标出 `V_τ≈0` 的「无分辨率情境」（如危险回避率两臂均 0.9814 的场景）。**这一步不需要 LLM，可立刻做**。
  2. **装四维幻觉判据**：把 **Hallucination & Failure Feedback** 单列，专查「**无效/无消费者动作是否被环境报成功**」——直接对准债务 26/27。
  3. **写死 C8 切分线**：合成/重放**算子**与选择器参数可进 GenePackage；Mexp 学到的**动力学内容**与任何外部语料蒸馏物**不得**进 GenePackage。
  4. **立硬规矩**：合成素材的**判据必须来自确定性代码/环境**（ScaleEnv / Agent-World 式），**禁止**用 LLM 推理当判据（防幻觉捷径）。
  5. **建接口**：反事实素材生成器与 Dream-RSI 重放模拟器**并列双档**（安全档重放 / 探索档合成）。
  6. **建 issue**：「非语言合成算子」——与 EvolveR 的「非语言抽象算子」、0/33 的「技能表示够不够」合并处理。

- **最小验证实验（反事实素材双臂，服务实验 3 技能固化 0/33 与判据饱和）**
  - **双臂 / 消融设置**：A 臂 = 现状（仅真实 trace）；B 臂 = 真实 trace + **合成反事实对照素材**（对每个候选技能生成「若技能生效，环境状态应如何变」的对照，**产物只进验证面**）。两臂 ≥8 seed，任务与初始条件固定。
  - **判据（分档，先看分母）**：
    1. **机制计数（分母先查）**：合成素材条数、被引用次数、**`V_τ` 分布**、A/B 两臂各自的 `V_τ≈0` 情境占比；
    2. **行为差**：逐帧动作差、`retrieve` 命中率（对照 0.5164）；
    3. **淘汰结果**：危险回避率——**注意两臂现均为 0.9814（饱和），此项已无分辨率，须先换更高难度情境或换指标**，否则不得据此项下结论。
  - **预期与证伪**：预期 B 臂在饱和判据上**恢复非零方差**（`V_τ>0`），且技能固化的机制计数出现非零变化。**证伪条件**：若 B 臂的合成情境 `V_τ` 也**全部≈0**（合成素材同样无分辨力），说明瓶颈在**情境难度/合成器质量**而非素材来源，应转向「换更难情境」（动作 1）或重估合成器可行性；若 B 臂机制计数上升但行为差为零，说明合成素材**只是多了一堆被忽略的条目**，判据形状仍未修好（回债务 25）。

- **若 E 不采用**：不适用（确实有可搬零件：`V_τ` 选择器与四维判据协议无需大算力即可落地）。

---

## 9. 待确认问题

1. **非语言合成算子从哪来（最关键）**：Mexp 是一次 LLM 的 CoT 调用；SSEA 无 LLM，「合成反事实状态转移」用什么算子？论文的「抽象降维状态空间」思想可借，但**生成器本体**必须自建。
2. **`V_τ` 能否在无 outcome 奖励时计算**：`V_τ` 依赖 `{r_i}`（outcome 奖励）。SSEA 无外部奖励，只有淘汰/存活事实——**能否用「存活/死亡」的二值事实替代 `r`**？若能，`V_τ` 即变成 C9 合规的「**情境分辨力**」指标；若不能，则 `V_τ` 的搬运受阻（**这是本卡片最需要团队拍板的一点**）。
3. **合成素材的「真实可达性」如何校验**：Theorem 1 要求可测 `(εR, εP)`，但 SSEA 无 outcome 标签；需先定义「奖励准确度」与「域一致性」在非语言生存环境中的对应量。
4. **摘要「>30%」与 Table 1 口径不一致**：摘要称 WebArena 上「超所有基线 >30%」（p1），而 Table 1（p7）DreamGym 13.3 vs GRPO 传统 7.3（相对 +82%，绝对 +6.0 点）；**「>30%」的统计口径未在正文说明**——引用时须注明此缺口。
5. **全文无 seed/方差**：Table 1/2 的所有差值（如 13.3 vs 7.3、63.9 vs 59.2）**无法判断显著性**——引用本文数字时必须注明此口径缺口。
6. **WebArena 评估函数已知有误**：论文自陈某些任务被原始评估函数误判且「保留全部轨迹 as-is」（A.3 p16）——这直接影响「合成环境判据可信度」这一论点的强度。
7. **未给绝对 GPU-hours**：只说 8 nodes A100 + 4 nodes H100（A.1 p15），无法与 EvolveR 的 39.4h×8×A100 直接比较——**睡眠期预算锚点不如 EvolveR 精确**。
8. **需补查文献**：WebDreamer（Gu et al. 2024）、WebEvolver（Fang et al. 2025）、UI-Simulator（Wang et al. 2025b）——用于确认「LLM 当环境模拟器」这一族是否已有更早/更强的等价方案（本篇自陈 UI-Simulator 最接近）。
9. **需团队决策**：合成素材是否进入四级验证门的「**沙盒**」层？若进，其状态映射（sim-to-real 对齐，§4.3 p7）由谁维护？

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we introduce DreamGym, the first unified framework designed to **synthesize diverse experiences** with scalability in mind to enable effective online RL training for autonomous agents.” | p1 |
| “Rather than relying on expensive real-environment rollouts, DreamGym **distills environment dynamics into a reasoning-based experience model** that derives consistent state transitions and feedback signals through step-by-step reasoning.” | p1 |
| “On non-RL-ready tasks like WebArena, DreamGym outperforms all baselines by **over 30%**. And in RL-ready but costly settings, it matches GRPO and PPO performance using **only synthetic interactions**.” | p1 |
| “a unified and scalable RL framework that synthesize[s] …” + 四大障碍：“costly rollouts, limited task diversity, unreliable reward signals, and infrastructure complexity” | p1–2 |
| “the key insight is that **synthesizing transitions in this abstract state space can reduce irrelevant dimensions** and produce trajectories that are more informative and token-efficient than those derived from raw observations.” | p5 |
| 经验模型三件附加上下文：“(1) interaction history … (2) task instruction τ … (3) past experiences … top-k demonstrations … retrieved from the replay buffer based on semantic similarity” | p5 |
| **Eq.4**：`(s_{t+1}, r_{t+1}) = M_exp(R_t | {(s_i,a_i)}^t_{i=0}, {d_j}^k_{j=1}, τ)` | p5 |
| “if the action is invalid, it transitions to a **failure state** and assigns a **zero reward** to signal the error” | p5 |
| “we adopt an **outcome-based reward scheme**, assigning `r = 1` only at the final step when the task is successfully completed and `r = 0` in all other cases.” | p5 |
| **Eq.5**：`L_SFT = E[ −logP_θ(R*_t | s_t,a_t,H_t,D_k) − logP_θ(s_{t+1} | s_t,a_t,R*_t,H_t,D_k) ]` | p6 |
| **Eq.6**：`τ_t = M_task({τ^i_{t−1}}^m_{i=1})`（任务生成器与 Mexp 共享参数） | p6 |
| **Eq.7**：`V_τ = (1/n)Σ(r_i − r̄)²`；"a non-zero variance in G indicates that the agent observes both successes and failures … signaling that the task is **feasible yet challenging** … maximum entropy when successes and failures are **evenly balanced**" | p6 |
| “we introduce a hyperparameter **λ** that bounds the proportion of synthetic tasks sampled per iteration” | p6 |
| **Table 1**：WebArena（L3.2-3B）SFT 6.1 / DPO 5.5 / GRPO 传统 7.3 / PPO 传统 6.7 → **DreamGym 13.3**（0 real data）/ DreamGym-S2R 13.9（5K）；WebShop（0 real）59.3/63.9/68.3 vs GRPO 传统(80K) 62.1/65.0/66.1 | p7 |
| “Training efficiency … reducing training effort … to roughly **one-third or even one-fifth** of RL baselines in the real environment.” | p8 |
| “when the domain gap becomes too large, such as transferring from web-based environments to ALFWorld, the performance **drops significantly**” | p8 |
| **Table 2 消融**：DreamGym 63.9/13.3；w/o Exp. Replay 59.2/9.7；**w/o Exp. Reasoning 55.8/7.3**；**w/o Task Generation 57.3/7.3** | p9 |
| “Removing trajectory history … significantly reduces **consistency** … Removing reasoning … mainly hurts **informativeness** … and **increases hallucination**.” | p9 |
| **Fig.4**：四维评委（consistency / diversity / informativeness / hallucination），**100 条随机轨迹**，GPT-4o judge，每维 `{0,1,2}` | p9 |
| “the experience model is **highly data-efficient**. Even with a very limited number of offline samples (2k-10k), it already reaches competitive performance.” | p10 |
| “**Limitations**: Our work primarily investigates **single-environment learning** setups … build a universal world model … could pave the way toward scaling foundational agentic models with purely synthetic experiences” | p11 |
| **Theorem 1 (Eq.9)**：`J_M(π′)−J_M(π) ≥ 合成增益 − 4γVmaxδ/(1−γ)² − 2(εR/(1−γ) + 2γRmax·εP/(1−γ)²)` | p17 |
| **Lemma 1 (Eq.26)**：`|J_M(π)−J_M̂(π)| ≤ Δmodel := εR/(1−γ) + 2γRmax/(1−γ)²·εP`；“the gap … depends only on **reward accuracy and domain consistency errors**, rather than on strict fidelity metrics such as **state reconstruction error**” | p18 |
| **四维评委 rubrics**：1) Causal State Consistency 2) Diversity & State Variation 3) Informativeness 4) **Hallucination & Failure Feedback**（“does the state reflect an appropriate **failure/empty-result signal** instead of **hallucinating success**?”） | p27 |
| 离线语料：WebShop 1,600 人类演示 + 2,000 oracle/random；ALFWorld 3,200 专家 + 2,000；WebArena 4,800 条（IBM CUGA / ScribeAgent / Learn-by-Interact / AgentOccam） | p15–16 |
| 算力：“All experiments … are conducted on **8 nodes with A100 GPUs and 4 nodes with H100 GPUs**.” | p15–16 |
| WebArena 基线瓶颈：“we are able to operate only **four AWS servers**, enabling at most four parallel interaction sessions”；“some trajectories fail to execute properly and … certain tasks are **incorrectly judged by WebArena's original evaluation function** … we retain all collected trajectories and use them as-is” | p16 |
