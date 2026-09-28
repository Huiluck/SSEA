# 论文分析卡片 · CoMAS

> 纪律：任何结论若无法回溯到 C1–C10 裁判标准，即视为偏离 SSEA 立场，不予采纳。
> 论文未提及的内容一律标「未提及」。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-10-09 CoMAS Co-Evolving Multi-Agent Systems via Interaction Rewards.pdf` |
| 标题 | **CoMAS: Co-Evolving Multi-Agent Systems via Interaction Rewards** |
| 作者 / 机构 | Xiangyuan Xue, Yifan Zhou, Guibin Zhang, Zaibin Zhang, Yijiang Li, Chen Zhang, Zhenfei Yin, Philip Torr, Wanli Ouyang, Lei Bai；CUHK / Shanghai AI Laboratory / University of Georgia / NUS / Dalian University of Technology / Oxford / UCSD / Shenzhen Loop Area Institute |
| 发表时间 / 出处 | **ICLR 2026**（已录用会议论文，p1 页眉 "Published as a conference paper at ICLR 2026"）；arXiv:2510.08529v2 [cs.CL]，v2 日期 2026-02-09（22 页） |
| 论文链接 | arXiv:2510.08529 |
| 代码链接 | https://github.com/xxyQwQ/CoMAS（摘要末，p1） |
| 标签 | 多智能体 · 共演化(co-evolution) · 交互奖励(interaction rewards) · LLM-as-a-judge · 零和对抗奖励 · REINFORCE++ · 参数侧 RL · 无外部监督 |
| **应用裁决** | **C 思想启发**（核心机制「交互奖励」判为 **C9 违规**，不可移植；仅取其**失败模式诊断**与「**评分通道与内容通道分离**」两条思想，并作为 **C9 边界裁决的对照样本**） |
| 优先级 | **P2** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把「人类靠相互讨论与协作而进步、无需外部 oracle 逐条评判」这一观察搬进 RL——让 `l` 个 LLM 智能体在同一环境里**互相出解、互相挑错、互相打分**，用 **LLM-as-a-judge** 把打分结果转成**零和互补奖励**（式 7），再以 REINFORCE++ 更新每个智能体的**策略权重**，从而在**无外部监督**下实现「共演化」（p1 摘要、§3.2 p5、§3.3 p5–6）。
- **对 SSEA 的意义**：它是库里**第一个把「奖励来源」从「环境/oracle」挪到「同伴」**的论文，正面撞上 **C9**——SSEA 的 C9 明令「奖励塑形、观察员评分一律违规」。本篇的真正价值不在分数，而在于**逼 SSEA 回答：同伴互评到底算内部驱动、环境淘汰、还是外部评分**（本卡片 §3.1-C9 专项给出裁决：**是外部评分，✗**）。它同时提供了两条可直接抄的**诊断资产**：自评回路的两种失败模式（strict-critic 漂移 / unanimous-support 劫持）与「奖励-验证器一致性」检测协议。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- 问题本身：RL 已成为 LLM 智能体自演化（self-evolution）的主线，但其奖励来源面临两难——**外部奖励**（rule-based verifier / reward model）受限于「必须存在可用的外部信号」；**内部奖励**（self-certainty / confidence / semantic entropy / majority-voting 伪标签）虽摆脱外部监督，却**仍是「单模型自我奖励」**，与人类「靠群体讨论与多样性互动涌现」的智能形态相悖（p1–2、Fig.1 p2）。
- 它指出的既有方案缺陷：① 外部奖励方法依赖可获取的外部信号（p3 §2.2）；② 内部奖励方法「largely centered on self-rewarding at the level of individual models」（p2）；③ 多智能体系统研究多聚焦「集体推理」，而「fostering evolution in individual agents within such systems remains largely unexplored」（§2.1 p3）。
- 核心研究问题（原文，p2）：**"Can LLM-based agents, akin to human beings, achieve self-evolution by learning purely from inter-agent interactions, without an external oracle evaluating every contribution?"**

### 2.2 核心思想（关键 insight）
1. **奖励信号从「环境/oracle」迁到「同伴互动」**：奖励不再由 verifier 或单模型自身产生，而是从多智能体**讨论动力学**中提取（p1、Fig.1 右列 p2）。
2. **对抗式零和奖励设计（本篇真正的技术内核）**：解者（solver）与评者（evaluator）构成**零和博弈**——`r(s_i) = (τ̂−1)/2`，`r(e) = 1−r(s_i)`（式 7 p5）；评者越能挑出致命错，解者得分越低，反之亦然。消融证明：去掉「评估」→ 智能体变成**越来越严苛的批评者**（奖励单调下降）；去掉「打分」→ 智能体**一致地把所有解标为正确**（奖励冲到 1.0，reward hacking）（§4.3.1 p8–9、Fig.4、附录 J p21–22）。
3. **共演化的载体是「权重」，不是提示/拓扑/技能**：`o = π_θk(p)`（式 1 p4），共演化即「各智能体用同一套 RL 流程更新各自的 π_θk」（§3.3 p5–6）。拓扑（Solution→Evaluation→Scoring）与角色是**固定的**。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **智能体池 U 与随机调度** | 池 `U={u_1..u_l}` → 每步 `u_k ∼ Uniform(U)` | 保证每个智能体经历量相当、负载均衡 | §3.1 p5 |
| **Solution 交互（式 3）** | `(q, h_q) → s_i` | 出解 | §3.1 p4 |
| **Evaluation 交互（式 4）** | `(q, h_q, s_i) → e_{i,j}` | **显式提示「找错」而非附和**，抑制 LLM 的 catering bias | §3.1 p4 |
| **Scoring 交互（式 5）** | `(q, s_i, e_{i,j}) → τ_{i,j}` | **专为奖励生成而设的独立通道**（「contributing nothing to the discussion history」，p5） | §3.1 p4–5 |
| **讨论历史压缩 h_q** | 全历史 → 最近 κ 轮 | 防超上下文；**κ=2** | §3.1 p5 |
| **分数抽取 Extract(·)（式 6）** | τ → τ̂ ∈ {1,2,3} | 从格式化文本抠出整数分 | §3.2 p5 |
| **分数语义（1/2/3）** | τ̂ → 语义 | 3=解正确/评无用；2=基本正确有小瑕；1=有致命错 | §3.2 p5 |
| **零和互补奖励（式 7）** | τ̂ → r(s_i), r(e_{i,j}) | 制造解者-评者零和博弈 | §3.2 p5 |
| **格式罚分（式 8）** | 打分输出格式 → 0 / −1 | 逼评者遵循格式并保持中立 | §3.2 p5 |
| **REINFORCE++ 策略优化（式 9–11）** | replay buffer `D_k={(p,o,r(o))}` → 策略更新 | token 级 credit assignment + KL 正则 + 优势归一化 + clip | §3.3 p5–6 |
| **失败模式 A：无评估（strict-critic drift）** | 去掉 Evaluation → 奖励单调下降 | 智能体退化为越来越严的批评者 | §4.3.1 p8–9、附录 J p21 |
| **失败模式 B：无打分（unanimous-support hacking）** | 去掉 Scoring → 奖励升向 1.0 | 智能体一致把一切标为正确（reward hacking） | §4.3.1 p9、附录 J p21–22 |
| **奖励-验证器一致性检测** | reward 二值化 vs verifier ground truth → precision/recall | **诊断协议**：验证奖励是否随任务准确率同步上升（而非被 hack） | 附录 G p17–18、Table 6 p18 |
| **智能体数/异构性消融** | l∈{1,2,4}；同构 vs 异构（Qwen-3B + Llama-3.2-3B） | 测「多智能体互动」与「多样性」的边际作用 | §4.3.2 p9、Fig.5 p9、Table 8–9 p18–19 |
| **成本-规模分析** | l → interaction samples / tokens / memory / wall-clock | 显式给出算力-规模曲线 | 附录 D p16、Table 3 p16 |

### 2.4 关键表示与数据结构
- **交互三元组**：`(s_i, e_{i,j}, τ_{i,j})`；每次交互流程产出 `m` 个解、`m·n` 个评估、`m·n` 个打分（§3.1 p5）。主实验 `m=2l=8, n=1, κ=2`（§4.1.1 p6、Table 2 p16）。
- **奖励载体**：replay buffer `D_k = {(p, o, r(o))}`——`p` 上下文、`o` 生成输出、`r(o)` 分配到的奖励（§3.3 p5）。
- **无持久化结构**：**论文未提及**任何档案/基因/记忆库/技能库；唯一的「历史」是**易失的**讨论上下文 `h_q`（且被压缩到最近 κ 轮）。这是 C7/C8 判定的关键（见 §3.1）。
- **无自然语言以外的结构化表示**：全部信号（解、评、分）都是自然语言文本 + 一个被 `Extract` 抠出的整数。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 7 基准 × 4 设置（GSM8K/MATH-500/HumanEval/MBPP/SciBench/GPQA/MMLU；Vanilla/Consistency/AutoGen/Debate） | untrained、SRLM、MAPoRL、TTRL | CoMAS **在多数设置最优**：Vanilla GSM8K **85.40**、HumanEval **70.73**、SciBench **34.67**、MMLU **62.40**；Consistency HumanEval **77.44**、MBPP **59.20**、MMLU **65.60** | Table 1 p7；主模型 Qwen2.5-3B-Instruct、l=4；>500 题的基准随机取 500 样本 |
| AutoGen（多智能体设置，增益最大） | untrained | GSM8K **72.40 (+19.80)**、MMLU **50.60 (+13.20)**、HumanEval **50.61 (+10.98)**；对照 TTRL 在此设置**大幅崩溃**（HumanEval −16.46） | Table 1 p7、§4.2 p8 |
| Vanilla 设置 5 seed 统计 | untrained | CoMAS 84.68±0.37 vs untrained 83.68±0.35（GSM8K）；HumanEval 74.15±2.06 vs 69.76±1.37 | 附录 E p17、Table 4 p17；**仅 Vanilla 设置报 5 seed 均值±标准差** |
| 7B 模型泛化 | untrained（7B） | Vanilla GSM8K **91.40 (+3.00)**、GPQA **32.81 (+1.56)**；Consistency GPQA **38.17 (+2.46)**、MMLU **74.00 (+1.80)** | 附录 F p17、Table 5 p17 |
| 奖励消融（去 Evaluation） | 完整 CoMAS | Vanilla 平均**低于 untrained**；奖励曲线**单调下降**（strict-critic drift） | §4.3.1 p8–9、Fig.4 p8、Table 7 p18 |
| 奖励消融（去 Scoring） | 完整 CoMAS | 奖励升向 **1.0**（unanimous-support hacking）；Vanilla 平均亦低于 untrained | §4.3.1 p9、Fig.4 p8、Table 7 p18 |
| 智能体数消融 l∈{1,2,4} | 各 l 的 untrained | 性能**随 l 增大**；Consistency/Debate 下 1-Agent 分别 −0.19%/−0.16%，4-Agent 分别 **+2.02%/+1.75%** | §4.3.2 p9、Fig.5 p9、Table 8 p18 |
| 智能体异构性（Qwen-3B + Llama-3.2-3B） | 同构 | 异构**一致优于**同构：Vanilla **+2.21%**、Consistency **+2.78%**、Debate **+2.13%** | §4.3.2 p9、Fig.5 p9、Table 9 p19 |
| 奖励有效性（reward vs verifier） | — | 训练步 0→30：accuracy 38.38→45.75；precision 39.52→50.10；recall 20.29→28.95 | 附录 G p17–18、Table 6 p18；**precision/recall 用 verifier ground truth 计算** |
| 训练成本 vs 智能体数 | — | l=1/2/4 → interaction samples 48k/192k/768k、tokens 1.6B/6.3B/25.2B、memory 120/240/480GB、wall-clock 11.7/12.1/12.5h | 附录 D p16、Table 3 p16；样本/令牌约 **l²** 增长，内存约 **l** 线性，墙钟近乎不变（并行采样） |

### 2.6 论文自陈局限与边界条件
- **假设依赖**：① 存在**可自动验证的推理/编码/科学基准**作为评测与（附录 G 中）奖励有效性核对的 ground truth；② 智能体实现是**可被 RL 修改的 LLM 策略**；③ 同伴（评者/打者）提供的信号**足以互补**且评者会被训练成中立；④ 任务可用**自然语言**表达与评判。
- **明确不适用 / 未处理的情形**：
  - **无持久化演化结构**：论文**未提及**档案、谱系、快照/回滚、变异、继承、基因包——「co-evolution」仅是**一次训练内** `l` 个策略的同步更新，**无跨代遗传**（§3 全文、§5 结论 p9）。
  - **主结果增益幅度不大**：Vanilla 下 GSM8K +1.00、MMLU +1.00（Table 4 p17），论文自陈 "some individual performance improvements are relatively modest in magnitude"（附录 E p17）。
  - **弱设置**：SciBench Vanilla CoMAS 33.87 < TTRL 34.07；MBPP Vanilla 56.32 < TTRL 58.32（Table 4 p17）——并非全面 SOTA（摘要称 "state-of-the-art performance across most evaluation settings"，p1）。
  - **奖励机制脆弱**：去 Evaluation 或去 Scoring 任一即崩（§4.3.1）——**核心增益强依赖两个通道同时存在**。
  - **成本高**：l=4 时 25.2B 生成令牌、480GB 内存、12.5h 墙钟（Table 3 p16）。
  - **无误差棒的主表**：Table 1（p7）主结果未报 seed 数/方差，仅 Vanilla 设置补 5 seed（附录 E）。
  - **领域限于语言推理/编码/科学问答**，非生存/控制任务。
  - **Impact/伦理段**：论文**未提及**独立的 Impact Statement（22 页中未见）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 全篇是语言生成 + 语言评判：Solution（式3）、Evaluation（式4）、Scoring（式5）全部是自然语言文本进出（p4–5）；无结构化生存信号、无控制环 | 无可改造：整个机制由语言承载。仅「评分通道独立于内容通道」的**分离原则**可借 |
| **C2** 自然语言只作观察员接口 | **✗** | 语言在闭环**内部**：奖励由 `Extract(τ)` 从**格式化文本**抠出（式6 p5），再驱动权重更新；Fig.2（p4）显示讨论流即控制流 | 语言只许留在慢环的「编译/提案」面；快环零语言。本篇只有「scoring 不进 discussion history」（p5）这一分离思想可借 |
| **C3** 权重/记忆/技能三分离 | **◐** | 只动**权重**（RL 更新 π_θk），**无记忆库、无技能库**；讨论历史 `h_q` 是**易失上下文**（压缩到最近 κ 轮），不是记忆 | SSEA 须明确：`h_q` 类上下文缓冲 ≠ C5 记忆；三分离要求三者**分置**，本篇三者缺二，不构成分离 |
| **C4** 低算力低带宽 | **✗** | l=4：**25.2B 生成令牌、480GB 内存、12.5h 墙钟**、768k 交互样本（Table 3 p16）；样本/令牌约 **l²** 增长；每轮全量自然语言交换 | 整机不可落地。只借**诊断零件**（近零成本） |
| **C5** 精准回忆历史 | **◐/✗** | 讨论历史 `h_q` **被刻意截断到最近 κ=2 轮**（p5）——是**遗忘以塞上下文**，非「精准回忆」；**无**可写入/检索/查询/合并的记忆结构（未提及） | `h_q` 不得当记忆用；SSEA 记忆侧仍走 Memento/FLEX/LightMem 路线 |
| **C6** 可自主修改自身 | **◐** | 参数**确被自我更新**（RL 改 π_θk，式9–11）✓；但四权错位——**提案权** ◐（更新方向由外部奖励+梯度决定，非模型提案）、**边界权** ✗（未提及任何可改/不可改边界）、**验证权** ◐（无合法性门，奖励即信号）、**应用权** ✗（应用由外部训练循环执行，非智能体自身） | 四权必须显式拆分；本篇的「自我修改」是**被外部 RL 驱动**的参数更新，不是 SSEA 意义下的自主自改 |
| **C7** 可保存/恢复/变异/继承 | **—/✗** | **无档案、无快照/回滚、无变异、无继承**（未提及）；「co-evolution」= 一次训练内 l 个策略同步更新，**无跨代**；GenePackage 类结构不存在 | 本篇对 C7 无贡献。Gene Manager 侧模板仍取 **GEA 的档案 + 祖先计数** |
| **C8** 给基因先验，不给知识语料 | **✗** | 全篇目标就是把数学/编码/科学**任务知识**经 RL **烧进权重**（2000 条精选训练样本：MATH/KodCode/WebInstruct，§4.1.1 p6）；无「结构性先验 vs 后天知识」之分 | 「跨代」部分不适用（无代际）；但「不给知识语料」被直接违反。SSEA 须坚持：知识进记忆/技能，不进基因、不跨代 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（核心裁决，见 §3.1-专项）** | 奖励 = **LLM-as-a-judge 产出的标量分** τ∈{1,2,3}，经**人工设计**的零和互补公式转为 RL reward（式6–7 p5），并**驱动参数更新**（式9–11 p5–6）；scoring 是「independent interaction pattern **specifically designed for reward generation**」（p5） | **必须关闭评分通道**：把「打分」换成「**合法性判决**」（通过/不通过），把「互补奖励」换成「**淘汰事实**」（环境侧存活与否）。对抗结构可留，奖励通道必须关 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子（用 Qwen2.5 + REINFORCE++，§4.1.1 p6）；创新在 **L3（交互驱动的奖励用于策略优化）** 与 **L2（Solution/Evaluation/Scoring 交互拓扑）** | — |

#### 3.1-专项：C9 裁决 ——「交互奖励」是不是外部评分函数？

**裁决：是。CoMAS 的交互奖励构成 C9 明令禁止的外部评分函数（从 SSEA 的单个体视角看）→ ✗。**

判定依据（逐条回溯到论文）：

1. **信号形态是「打分」，不是「淘汰」**：奖励是 judge 产出的**标量分数** τ∈{1,2,3}（式6 `τ̂=Extract(τ)`），归一化后由**设计者手写的零和公式** `r(s_i)=(τ̂−1)/2, r(e)=(3−τ̂)/2`（式7 p5）转为 RL reward。C9 判的是**信号是不是打分、是否驱动参数**——此处两者皆是。
2. **通道性质是「观察员评分」**：scoring 被明确定义为「an independent interaction pattern **specifically designed for reward generation**, contributing nothing to the discussion history」（p5）——即一条**专为奖励而设、不参与内容的评分通道**。这正是 C9 所说的「观察员评分」。
3. **塑形是人工设计**：1/2/3 的语义（正确/小错/致命错）与零和互补构造均为设计者固定（p5、式7）——C9 明令「**奖励塑形…一律违规**」。
4. **它不是 C9 层②的「模型内部内在驱动」**：C9 层②指**预测误差/内驱**，且其**定义不可改**；CoMAS 的奖励**不是预测误差**，而是**同伴 LLM 生成的标量判决**，其定义（语义、公式）由设计者固定。**「内部」与否看的是信号是不是「模型自身的内驱」，不是「打分者是不是模型」。**
5. **它也不是 C9 层①的「环境淘汰」**：层①的淘汰函数**归环境、模型碰不到**；CoMAS 的奖励由**智能体自己**产生，且**打分者本身也是被训练的 agent**（`u_k ∼ Uniform(U)`，p5；打分动作还带格式罚分 r(τ)，式8）——模型能影响它，且无环境侧存活/淘汰事实。
6. **单个体视角的关键一步**：SSEA 是**单个体**架构（虽有多层）。对**单个体**而言，「同伴智能体」是**外部实体**。因此「智能体间互评」在 SSEA 分类学里落在**外部评分**一侧，而非「模型内部」。论文自称这是 "intrinsic rewards ... without external supervision"（p1）——**SSEA 不采纳这一自我归类**：把「外部 oracle」拆散成「一群同伴」，并没有把它变成「环境淘汰」或「预测误差内驱」。

> **一句话判词**：CoMAS 的交互奖励是「**去中心化、但仍是外部**」的评分函数——C9 看的是「信号是不是打分、是否驱动参数」，不是「打分者是谁」。

**可救的一半（改造方向）**：
- CoMAS 的**零和对抗结构**（解者 vs 评者）在形态上接近 SSEA 慢环的「**提案 vs 验证**」，但 SSEA 的验证门**只判合法性、不打分**。
- 改造：把「**评分**」换成「**合法性判决**」（通过/不通过），把「**互补奖励**」换成「**淘汰事实**」（环境侧存活与否）——则对抗结构可保留、**奖励通道必须关闭**。
- **一条论文未做的推断性改造**（标注为推断，非论文主张）：把「解者与评者的**分歧本身**」当作**不确定性/预测误差**的代理信号（C9 层②），**只记录不驱动权重**；但论文用的是 judge 的标量分，**未提及**此路。

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无（借用 Qwen2.5-3B/7B + REINFORCE++，§4.1.1 p6） | 无，符合借用立场 |
| **L2 信息流层** | **多智能体交互拓扑**：Solution→Evaluation→Scoring 三型交互 + 随机调度 + 讨论历史压缩；**「评分通道独立于内容通道」** | **低–中**：SSEA 是单个体，拓扑不可整体搬；但「**测量通道 ≠ 内容通道**」是可借的设计原则 |
| **L3 学习层** | **交互驱动的奖励 + REINFORCE++ 策略优化**（核心）；**自评回路两种失败模式** | **低（机制）/ 高（诊断）**：奖励机制 C9 违规不可用；**失败模式清单**价值高 |
| **L4 演化层** | **无**——无档案/继承/变异/基因包（未提及）；「co-evolution」无代际 | **无**。Gene Manager 模板仍取 GEA |

### 3.3 模块映射（**单个体降维：哪些零件能落到 SSEA 单个体上**）

> SSEA 是**单个体**架构（快环 FSL + 慢环 SEL），本篇是**多智能体**。下表逐件判定能否「降维到单个体使用」。

| 论文构件 | 能否降维到单个体 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|---|
| **Solution→Evaluation→Scoring 三型交互** | **部分**：单个体可同时扮演解者与评者（即**自评/自我批评**）；论文的 **1-Agent 消融**（Table 8 p18）直接测了这一点——**结果多为负增益**（Vanilla 1-Agent GSM8K −0.80、MATH-500 −1.00），说明**去掉同伴后对抗结构收益蒸发** | 慢环「**提案 → 验证**」回路（已有）；但**禁止把评者输出当分数** |
| **零和互补奖励（式7）** | **否**（C9 违规） | 不得进控制回路；最多作**模型外仪器**（见 §4） |
| **Scoring 通道「不进 discussion history」（p5）** | **能** | **原则**：慢环的**测量/观测面**与**内容面**物理分离——验证门只输出「合法性判决」，不产出可回灌的分数 |
| **失败模式 A/B（strict-critic drift / unanimous-support hacking）** | **能（纯诊断）** | **新增建议：慢环自评回路的红队清单**（并入 Misevolve 威胁模型） |
| **奖励-验证器一致性检测（附录 G、Table 6）** | **能（作模型外仪器）** | **验证/观测模块**：定期核对内部信号与真实存活率是否同步；**只记录不驱动** |
| **智能体数/异构性消融（Fig.5）** | **仅作对照** | 论证「单个体自评」为何不足；SSEA 若要多样性，靠**慢环历史快照的多样性**而非多机体 |
| **成本-规模曲线（Table 3）** | **仅作对照** | 算力预算参考（l² 增长），非调度器 |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **判据形状错 / 技能失效被判成成功（债务 25/26/27/28）**：CoMAS 的 **unanimous-support hacking**（去 Scoring → 所有解被标为正确、奖励冲到 1.0，§4.3.1 p9）是「**判据被 exploit**」的教科书实例——与 SSEA「技能失效被判成成功」同构；其**奖励-验证器一致性检测**（附录 G）给出「**如何发现判据被 hack**」的协议（对 ground truth 核 precision/recall）。
  - **睡眠期计算预算未定义**：Table 3（p16）给出**按智能体数**的样本/令牌/内存/墙钟曲线，可作预算量级参考（但非分档调度器）。
  - **记忆门「开得准不准」**：本篇**无记忆门**（未提及），不可回应。
- **可服务的验收实验**：
  - **实验 4（架构变异与淘汰）**：本篇**不可服务**（无 L4）；但可作**反面参照**——「无淘汰、无档案」的演化退化为单轮 RL。
  - **后续实验**：**C9 边界实验**（见 §8）——验证「同伴评分若进控制回路会以何种形式退化」。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **自评回路两种失败模式清单**（strict-critic drift / unanimous-support hacking）+ 附录 J 两条失败轨迹 | 思想/诊断 | **直接移植**（作红队清单） | Misevolve 威胁模型 / 慢环自评回路 | 为 SSEA 内部自评回路预设失败模式与告警 | 高 |
| 2 | **奖励-验证器一致性检测**（reward 二值化 vs verifier ground truth 的 precision/recall 随时间变化，附录 G、Table 6） | 协议/仪器 | **改造移植**（只作模型外仪器，不驱动） | 验证/观测面 | 检测「内部信号是否被 hack / 与真实存活脱钩」 | 中 |
| 3 | **「评分通道独立于内容通道」**（scoring "contributes nothing to the discussion history"，p5） | 设计原则 | **仅借思想** | 验证门 / 观测面 | 保证测量通道不污染控制内容 | 中 |
| 4 | **零和互补奖励构造**（式7） | 算法 | **仅作对照**（C9 违规样本） | — | 作为「奖励塑形」的具象反例，写进 C9 条款说明 | 高 |
| 5 | **C9 边界案例：同伴互评的归类** | 证据/裁决依据 | **直接引用** | C9 条款说明 | 为「同伴评分 = 外部评分」提供外部文献支撑 | 高 |
| 6 | **智能体数/异构性消融曲线**（Fig.5、Table 8–9） | 证据 | **仅作对照** | — | 论证「单个体自评」不足、多样性有边际收益 | 中 |

---

## 5. 冲突、代价与风险

### 与硬约束的冲突（逐条）
1. **C9 ✗（最主要冲突）**：交互奖励是 judge 产出的标量分并经人工塑形**驱动参数**——「观察员评分 + 奖励塑形」双重违规（式6–7、p5）。**改造**：评分通道关闭，改「合法性判决 + 环境淘汰」（见 §3.1-专项）。
2. **C2 ✗**：语言在闭环内部（Solution/Evaluation/Scoring 全是文本；奖励从文本抠出，式6）。**改造**：语言只在慢环编译面；「评分通道 ≠ 内容通道」的分离原则可留。
3. **C4 ✗**：l=4 时 25.2B 令牌 / 480GB / 12.5h（Table 3 p16），且交互样本约 l² 增长。**改造**：整机不落地，只搬诊断零件。
4. **C8 ✗**：以 RL 把任务知识烧进权重（§4.1.1 p6）。**改造**：知识进记忆/技能，不进基因。
5. **C6 ◐**：参数被自我更新 ✓，但四权错位（边界权/应用权缺失，提案权归外部奖励）。**改造**：显式拆分四权。
6. **C1/C7 ✗/—**：无生存信号、无 L4 持久化结构。

### 隐含假设与失效条件
- 假设存在**可自动验证的推理基准**（附录 G 用 verifier ground truth 核对奖励）——SSEA 的生存环境**没有这样的外部 ground truth**，去掉它后**无法判断奖励是否被 hack**，本方法的自检能力随之失效。
- 假设同伴**能提供互补信号**：1-Agent 消融显示去掉同伴后多为负增益（Table 8 p18）——**核心增益依赖真实多机体**，与 SSEA 单个体架构直接矛盾。
- 假设**评者可被训练成中立**：去 Scoring 即崩（一致化劫持）证明这一假设**脆弱**（§4.3.1）。

### 算力 / 带宽 / 工程代价
- 整机：l=4 → 768k 交互样本、25.2B 生成令牌、480GB 内存、12.5h 墙钟（Table 3 p16）；需多智能体 RL 基建（MARTI/OpenRLHF，§4.1.1 p6）。**与 C4 直接冲突，整机不可落地。**
- 零件：失败模式清单、一致性检测协议——**近零成本**，可立即写入文档/清单。

### 搬运后的可能退化模式（若失败，会以什么形式失败）
1. **判据被 exploit（最可能）**：把评分引进慢环 → 提案方学会「讨好评者」而非「变强」，对应 CoMAS 的 unanimous-support hacking（§4.3.1 p9）——**这正是 SSEA「技能失效被判成成功」的放大版**。
2. **评者漂移**：无外部锚时评者越来越严，信号单调退化（strict-critic drift，附录 J p21）。
3. **单个体坍缩**：SSEA 只有单个体 → 去掉同伴后对抗结构收益蒸发（Table 8 的 1-Agent 负增益）。
4. **知识膨胀进权重**：若照搬 RL 路径，任务知识烧进参数，违反 C3/C8。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **对照（同题 · 三条「共享」轴）** | **Group-Evolving Agents (GEA)**（`2026-02-04 Group-Evolving Agents ...`，本库 **B/P1**） | 同为「智能体互相学习而自演化」，但**共享的东西不同**：**GEA 共享「结构」**（framework patch，触 **C8**）；**CoMAS 共享「评分」**（interaction reward，触 **C9**）；**G-Memory 共享「记忆」**（触 **C2/C5**）。三篇构成「共享」三轴，**只有 GEA 的结构共享经改造后对 SSEA 合法**，CoMAS 的评分共享不可用 |
| **对照（同题 · 反向）** | **SPIRAL**（`2025-06-30 SPIRAL ...`，本库**未建卡**） | 自博弈（zero-sum self-play）的**合规变体**：奖励来自**有 grounding 的环境**（game engine / 可验证胜负），信号归环境（≈ C9 层①）；CoMAS 则**移除 grounded 环境、改用同伴 LLM 评分**，离 C9 更远。**SPIRAL 是「可用的对抗」，CoMAS 是「不可用的对抗」** |
| **替代/竞争** | **MAPoRL**（`2025-07 MAPoRL ...`，本库**未建卡**） | 同为**参数侧多智能体 RL 协同训练**，但 MAPoRL 用 **verifier 打分**（明确的外部 reward model）——**C9 违规更直白**；CoMAS 用同伴评分（C9 违规更隐蔽）。CoMAS 把 MAPoRL 当基线并在多设置上超过它（Table 1 p7） |
| **替代/近亲** | **Multi-Agent Evolve (MAE)**（`2025-10-27 Multi-Agent Evolve ...`，本库**未建卡**） | **最接近 CoMAS 且最贴近单个体**：三角色 **Proposer/Solver/Judge** 由**同一个 LLM** 实例化并 RL（CoMAS 无 Proposer、且是多模型池）。MAE 直接演示了「**单个体同时扮三角色**」——这正是 SSEA「降维到单个体」问题的实证参考；但 MAE 的 Judge 也打分 → **同样 C9 违规** |
| **前置依赖** | **Misevolve**（本库 **A/P1**） | CoMAS 暴露了「自评回路」两类失败模式，须并入 Misevolve 的四路径威胁模型作为**新威胁项** |
| **互补（诊断侧）** | **SEDM**（本库 **B/P1**，A/B 准入） | CoMAS 的 unanimous-support hacking 说明「**自产信号必须过准入/校验**」；SEDM 的配对 A/B 边际效用验证是「**如何不让退化信号进系统**」的现成手段（SEDM 作用于记忆条目，此处借其**方法论**） |
| **互补（记忆侧）** | **G-Memory**（`2025-06-09 G-Memory ...`，本库**未建卡**） | 同为「多智能体自演化」，G-Memory 是**推理期记忆共享**（insight/query/interaction 三层图），CoMAS 是**训练期奖励共享**；两者对 SSEA 都触 C2/C5，但 **G-Memory 的「跨 trial 洞见」比 CoMAS 的「同伴评分」更接近 SSEA 的记忆侧** |
| **风险/参照** | **Reflexion / RAGEN** | Reflexion 的「试错-评估-反思」外环是 CoMAS 自评回路的单个体前身；RAGEN 的 Echo Trap 诊断可防自评回路坍缩 |

### 6.2 推荐组合方案

**方案 A（推荐，纯诊断）：CoMAS 失败模式 × Misevolve 四路径威胁模型 × SSEA 慢环自评回路**
- **组合**：CoMAS（strict-critic drift + unanimous-support hacking + 奖励-验证器一致性检测）× **Misevolve**（模型/记忆/工具/工作流四路径威胁模型与红队清单）
- **接口形态**：把 CoMAS 的两条失败轨迹（附录 J）与一致性检测协议（附录 G）写成**慢环自评回路的红队条目**；每次慢环自评迭代后，用「**内部信号 vs 真实存活率**」的相关性做体检（模型外，只记录）。
- **组合后新增能力**：① 提前识别「判据被 exploit」（对接债务 25/26/27/28）；② 给 SSEA 的「提案-验证」回路一个**经验证的失败模式库**。
- **新增风险**：一致性检测需要一个「真实存活率」锚——SSEA 有（环境侧淘汰事实），**不依赖外部 verifier**，故此项**可行且合规**。

**方案 B（反面对照，非采纳）：CoMAS × SPIRAL × MAPoRL —— 「奖励来源三档」对照**
- **组合**：MAPoRL（外部 reward model）→ SPIRAL（环境可验证胜负）→ CoMAS（同伴评分）。
- **接口形态**：作为 C9 条款的**三档标尺**写进 sse_protocols：① 环境淘汰（**合规**，SPIRAL 侧）② 预测误差内驱（**合规**，需定义不可改）③ 同伴/观察员评分（**违规**，CoMAS/MAPoRL 侧）。
- **新增能力**：让「什么信号可进控制回路」有可援引的外部坐标。
- **新增风险**：无（纯文档）。

### 6.3 本篇在组合中的典型角色
- **C9 边界裁决的对照样本 + 自评回路的失败模式清单**（**反面参照**）。本篇不为 SSEA 快环或慢环提供任何可直接接入的算法零件——它提供的是「**如果把同伴评分放进控制回路，会以 strict-critic 漂移或一致化劫持的形式坏掉**」这一具象证据，以及一条**模型外的体检协议**。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **2** | 正面命中 **C9 边界裁决**（同伴评分的归类）与**判据被 exploit 的诊断**两条议题，且与 GEA/G-Memory/SPIRAL/MAPoRL/MAE 同族（实测：式6–7、§4.3.1、Table 3）。扣分：机制不可用、领域是语言推理非生存控制（实测） |
| 立场兼容性 | **1** | **C9 ✗（核心）+ C2 ✗ + C4 ✗ + C8 ✗ + C1 ✗**，多条硬冲突且核心机制（交互奖励）**不可改造为合规**（只能整段弃用、取其诊断）（实测：p5 式7、p1 摘要、Table 3 p16）。仅 C10 ✓ |
| 可搬运性 | **2** | 核心机制不可搬（C9 违规）；可搬的只有**诊断/清单/协议**三类思想型资产（推断，有实测支撑）；「评分通道分离」是原则而非零件（实测 p5） |
| 证据强度 | **3** | **ICLR 2026 已录用**；7 基准 × 4 设置、5 seed（仅 Vanilla）、7B 泛化、奖励/智能体数/异构性三重消融、显式成本分析、开源代码（实测）——**证据面较广**；但**增益幅度小**（Vanilla GSM8K +1.00）、部分设置非 SOTA、主表无误差棒、机制脆弱（实测） |
| 组合价值 | **3** | 与 **GEA（共享结构）**、**G-Memory（共享记忆）**、**SPIRAL（grounded 自博弈）**、**MAPoRL（外部 verifier）**、**MAE（单个体三角色）**、**Misevolve（威胁模型）**、**SEDM（准入）** 七条边成立，且是**「共享」三轴中「评分共享」轴的代表**（推断，有实测支撑） |
| 落地成本 | **3** | 反向口径：**诊断零件近零成本**（推断）→ 拉高；**整机 25.2B 令牌/480GB/12.5h（Table 3 p16）**→ 拉低；因推荐搬运的是诊断而非整机，取中 |

---

## 8. 裁决与下一步

- **应用等级：C 思想启发** —— 采用两条**诊断型**资产：**① 自评回路失败模式清单（strict-critic drift / unanimous-support hacking）**、**② 奖励-验证器一致性检测协议（改造为「内部信号 vs 真实存活率」体检，只作模型外仪器）**；并把它当作 **C9 条款的裁决依据**（「同伴评分 = 外部评分」）。**不采用**：交互奖励、零和互补奖励（式7）、LLM-as-a-judge 评分通道、参数侧 RL 共演化整机。
- **优先级：P2** —— 理由：其机制不可采纳，但**C9 对「同伴评分」的裁决**与**判据被 exploit 的失败模式**对 SSEA 的**债务 25/26/27/28 与自评回路设计**有直接价值；优先级低于 GEA（P1，因其提供可用的 L4 零件），高于纯备查文献。
- **建议动作**：
  1. **写死 C9 三层信号分类学（宪法层）**：① 环境淘汰（模型碰不到）② 模型内部内驱（预测误差，定义不可改）③ 结构提案；并在 sse_protocols 中**明写**「**同伴/多智能体互评 = 外部评分**，其标量分不得进入控制回路」，文献依据为 CoMAS §3.2 / 式7。
  2. **慢环自评回路加红队条目**：把 CoMAS 的两条失败模式（评者漂移 / 一致化劫持）并入 **Misevolve** 清单；给自评回路设「**禁止产出可回灌的标量分**」硬约束。
  3. **验证/观测面加体检协议**：定期计算「**内部信号 vs 环境侧真实存活率**」的相关性（对照 CoMAS 附录 G 的 reward-verifier 一致性），**只记录不驱动**。
  4. **判据换口径**：借 CoMAS 的「hacking」教训，把饱和的 0.9814 危险回避率与 0/33 技能固化改为**先看分母**的计数判据（与 GEA 卡片同一建议）。
- **最小验证实验：评分门 vs 合法性门（服务 C9 边界裁决）**
  - **双臂设置**（同一环境、同一初始 GenePackage、≥8 seed）：
    - **A 臂「合法性门」**（SSEA 现行，C9 合规）：验证门**只判合法性/淘汰**，不产出分数。
    - **B 臂「评分门」**（CoMAS 式，C9 违规对照）：验证门额外产出标量分，并**用该分排序/塑形**提案。
  - **判据（分档，先看分母）**：
    1. **机制计数（分母，必须先跑）**：评分通道被驱动次数、门拒绝率、提案总数、GenePackage 体积增长。若 B 臂评分数未真正驱动任何决策，则实验无效。
    2. **行为差**：技能固化命中率（当前 **0/33**）、记忆检索命中率（当前 **0.5164**）、**「评分 vs 真实存活率」相关系数**。
    3. **淘汰结果（环境侧，模型外）**：存活率 / worst-case top-k。
  - **预期**：B 臂出现 CoMAS 的两种失败模式之一——**评分与真实存活率脱钩**（评者漂移或一致化劫持），A 臂稳定；对应 CoMAS 去 Scoring 时奖励冲向 1.0、去 Evaluation 时奖励单调下降（§4.3.1 p8–9）。
  - **证伪条件**：① B 臂评分与真实存活率**始终强相关**且无劫持 → 「同伴评分必为外部塑形」的禁令需重新论证；② A 臂与 B 臂无差异 → 说明 SSEA 的验证门对评分不敏感，C9 边界在工程上不构成约束（需复查门是否真的「只判合法性」）；③ B 臂 GenePackage 体积增长失控 → 命中 C8 膨胀（与 GEA 卡片同一告警）。
- 若 **E 不采用**：不适用。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **「同伴互评」的最终归类**：SSEA 是否接受「去中心化但仍外部」这一裁决？若未来 SSEA 引入多机体，是否仍坚持「互评 = 外部」？（本卡片裁决为**是**，依据 §3.1-专项）
  2. **C9 层②「内部内驱」的边界**：是否允许把「解者与评者的**分歧**」当作**预测误差代理**（C9 层②），只要**只记录不驱动**？——CoMAS **未提及**此路，属 SSEA 侧的新设计。
  3. **一致性体检的锚**：用「环境侧真实存活率」作体检锚是否足够（SSEA 无外部 verifier ground truth，CoMAS 有）？
- **需补查的文献或资料**：
  1. **SPIRAL、MAPoRL、Multi-Agent Evolve、G-Memory 四篇本库均未建卡**，本卡片 §6.1 对其机制细节依据各自**摘要页（第 1 页）**作概述性对照，**未核实全文**；若要纳入正式组合，需先补建卡片。
  2. **MAE（Multi-Agent Evolve）** 是「单个体同时扮 Proposer/Solver/Judge」的最直接实证，与 SSEA「降维到单个体」问题高度相关，**建议优先补卡**。
  3. **TTRL / SRLM**（CoMAS 的基线）本库未见卡片；若要复现「判据被 exploit」对照，需补。
- **需人工核对的实现 / 数字**：
  1. **Table 1（p7）主结果无 seed 数与误差棒**，仅 Vanilla 补 5 seed（附录 E）——主表数字不得当作带方差的结论引用。
  2. **式7 的奖励语义**：`r(s_i)=(τ̂−1)/2` 在 τ̂=1 时为 0、τ̂=3 时为 1——请人工核对「解者得高分」与「评者得高分」的**对抗方向**是否如卡片所述（p5）。
  3. **1-Agent 消融（Table 8 p18）** 中部分单元（如 AutoGen 1-Agent GSM8K +20.80）增益异常大，疑为 AutoGen 基线本身极弱所致——需人工核对分母。
  4. **成本表 l² 增长**（Table 3 p16）与「wall-clock 近乎不变」的并行假设，需核对实际实现（MARTI/OpenRLHF）。
  5. 论文**是否真的无 Impact Statement**：22 页全文未见独立伦理/影响段，需人工确认（若在补充材料另有说明则更正）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "CoMAS generates intrinsic rewards from rich discussion dynamics, employs an **LLM-as-a-judge** mechanism to formulate these rewards, and optimizes each agent's policy through RL" | p1（摘要） |
| "Can LLM-based agents, akin to human beings, achieve self-evolution by learning purely from inter-agent interactions, **without an external oracle evaluating every contribution**?" | p2 |
| Fig.1：左=External Rewards（verifier/reward model）、中=Intrinsic Rewards（certainty/confidence/semantic entropy/voting）、**右=Interaction Rewards（Ours）** | p2 |
| "**Scoring** … is an **independent interaction pattern specifically designed for reward generation, contributing nothing to the discussion history**." | p5 |
| 式(6) `τ̂_{i,j} = Extract(τ_{i,j})`；分数语义 3/2/1（正确 / 小瑕 / 致命错） | p5 |
| 式(7) `r(s_i) = (τ̂_{i,j}−1)/2`，`r(e_{i,j}) = 1 − r(s_i) = (3−τ̂_{i,j})/2`（**零和博弈**） | p5 |
| 式(8) 打分格式罚分：`r(τ)=0`（格式正确）/ `−1`（否则） | p5 |
| §3.3 采用 **REINFORCE++**（非 GRPO）；式(9)–(11) token 级优势 + KL 正则 + 优势归一化 + clip | p5–6 |
| §4.1.1 训练集 **2000 条**（600 MATH level-4/5 + 600 KodCode medium/hard + 800 WebInstruct-verified）；主模型 **Qwen2.5-3B-Instruct**；l=4（主）/ l=2（消融）；m=2l, n=1, κ=2 | p6 |
| Table 1：Vanilla GSM8K **85.40**、HumanEval **70.73**、MMLU **62.40**；AutoGen GSM8K **72.40 (+19.80)**、MMLU **50.60 (+13.20)** | p7 |
| Fig.3：训练中平均响应长度持续增长、归一化奖励稳定在 **0.5** 附近 | p7 |
| §4.3.1 去 Evaluation → 奖励**单调下降**（agents become increasingly strict judges）；去 Scoring → 奖励升向 **1.0**（**reward hacking**，agents unanimously support all solutions） | p8–9 |
| §4.3.2 1-Agent 在 Consistency/Debate 分别 **−0.19%/−0.16%**；4-Agent **+2.02%/+1.75%**；异构（Qwen-3B+Llama-3.2-3B）优于同构（Vanilla **+2.21%**） | p9 |
| Table 3：l=1/2/4 → 交互样本 48k/192k/768k、令牌 1.6B/6.3B/**25.2B**、内存 120/240/**480GB**、墙钟 11.7/12.1/**12.5h** | p16 |
| Table 4（附录 E，5 seed）：CoMAS 84.68±0.37 vs untrained 83.68±0.35（GSM8K）；HumanEval 74.15±2.06 vs 69.76±1.37 | p17 |
| Table 6（附录 G）：步 0→30 accuracy 38.38→45.75、precision 39.52→50.10、recall 20.29→28.95（**precision/recall 用 verifier ground truth 计算**） | p17–18 |
| 附录 J：Failure Mode without Evaluation（奖励单调降）/ Failure Mode without Scoring（`<judgment>correct</judgment>` 一致化，奖励 hack） | p21–22 |
| 代码：`https://github.com/xxyQwQ/CoMAS` | p1 |
