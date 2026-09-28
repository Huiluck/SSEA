# 论文分析卡片 · STaR

> 纪律：任何结论若无法回溯到 C1–C10 裁判标准，即视为偏离 SSEA 立场，不予采纳。
> 论文未提及的内容一律标「未提及」。所有关键数字带页码/表号/节号与统计口径。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2022 STaR Bootstrapping Reasoning With Reasoning.pdf` |
| 标题 | **STaR: Bootstrapping Reasoning With Reasoning**（正文亦称 **Self-Taught Reasoner**） |
| 作者 / 机构 | Eric Zelikman\*、Yuhuai Wu\*（共同一作）、Jesse Mu、Noah D. Goodman；Stanford University CS、Google Research（p1） |
| 发表时间 / 出处 | **NeurIPS 2022**（36th Conference on Neural Information Processing Systems，p1 页脚）；arXiv:2203.14465（2022-03-28，据公开索引；PDF 首页未印 arXiv 号）；**13 页（正文+参考文献，无附录正文）** |
| 论文链接 | arXiv:2203.14465 |
| 代码链接 | https://github.com/ezelikman/STaR（p1 脚注） |
| 标签 | **自举推理（bootstrapping reasoning）** · 链式思维 rationale · **生成—筛选—微调循环** · **rationalization（给答案反推理由）** · 自训练（self-training） · **二值正确性门** · GPT-J 6B |
| **应用裁决** | **B 零件采用**（采「**四判定自举回路原型**」＋「**二值正确性筛选门（全族中唯一对 C9 形态友好者）**」＋「**rationalization 反向提案**」＋「分母台账」；**不采用**语言 rationale SFT 训练栈、GPT-J 载体、预训练知识语料作为可继承物） |
| 优先级 | **P1**（自举推理族的**奠基工作**，是 R-Zero / Agent0 / TTCS / Aspire / EvolveR / EvoTest / Socratic-Zero 的**共同祖宗**；其筛选门直接回答「自举信号从哪来」，且**形态上可被 SSEA 淘汰函数直接充当**——与当前「`rules` 零消费者」「判据形状错」两项缺口同源） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：给定一个**预训练 LLM** 与一个**只有题目与最终答案、没有 rationale 的数据集**，用**极少（P=10）人类手写 rationale 示例**作提示，让模型自生成 rationale；**只按「最终答案是否答对」这一二值判据筛选**，对答错的题再**给出正确答案作 hint 让其反向生成 rationale（rationalization）**；把「答对生成的 rationale」与「rationalization 生成的 rationale」合并微调，**每次都从原始预训练模型重训**，循环至性能饱和——即可**从少量示例自举出大规模 rationale 数据集与更强推理能力**（摘要 p1、§3、Alg.1 p4）。CQA 上 STaR 达 **72.5%**，超过直接预测答案的 GPT-J（60.0%）与 137B LaMDA few-shot CoT（55.6%），逼近 **30× 大**的 GPT-3 微调（73.0%）（Table 1 p7）。
- **对 SSEA 的意义**：**正面（最大增量）**——STaR 的筛选信号是 `I(ŷ = y)` 这一**二值正确性门**，**不打分、不排序、无奖励塑形、无外部 judge**，是**全族中唯一在形态上对 C9 友好**的一件；因此 **SSEA 的淘汰函数（存活/死亡，模型碰不到、确定性、二值）可以直接充当这个筛选器**，把 `I(答对)` 换成 `I(存活到 T / 危险未致死)` 即得一条 **C9 合规的自举信号**——这正是「自举信号从哪来」这一原问题的**可执行答案原型**。**正面（其次）**——它的「四判定」（何时保留 / 何时回退 / 何时 hint / 何时用最终答案）是整族自举回路的**原始形状**，且其 rationalization（**给定结果反推中间结构**）天然给 SSEA 的 `rules`（当前**零消费者**）一个消费者原型。**反面**——能力底座仍是**预训练权重＝压缩的人类知识语料**（§6 p10 自陈「底座必须够大才有可自举的推理能力，GPT-2 不行」），整体 C8 ✗；且语言 rationale 既是训练目标又是筛选依据，C1/C2 ✗。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：诱导 LLM 生成 step-by-step rationale（CoT）**成本高、难扩展**——要么人工/模板构造大规模 rationale 数据集，要么用 few-shot 但精度大幅下降（p1）。
- **它指出的既有方案缺陷**（p1）：
  1. **人工标注 rationale**：昂贵，且「为每个感兴趣的问题都建一个数据集不可行」（"it is infeasible to construct such a dataset for each interesting problem"，p1）；
  2. **模板自动生成 rationale**：仅在**已知通解**（general solution）或可写硬编码启发式时可行（p1，引 [5]）；
  3. **few-shot CoT 推理**：比无 rationale 的直接提示好，但**通常显著弱于用更大数据集微调直接预测答案的模型**（p1）。

### 2.2 核心思想（关键 insight）
1. **自举循环：生成 → 按最终答案筛选 → 微调 → 用新模型重来**。关键点在于——**只查最终答案对不对，不单独检查 rationale 是否正确**："without needing to check new rationales' correctness"（贡献 1，p2；§3.1 p3）。论文假设「导出正确答案的 rationale 质量优于导不出正确答案的」（p3）。
2. **rationalization：给答案作 hint，让模型反向生成 rationale**。纯自举的致命缺陷是「对答错的题拿不到任何训练信号，改善在遇到新难题时终止」；rationalization 让模型**条件于答案**（从 `p(r|x)` 转向 `p(r|x,y)`）反推理由，且**训练时把 hint 从 prompt 中剥离**（"as if the model had come up with the rationale without the hint"，§3.2 p4）。论文视其为式(1)目标的 **off-policy 估计**（用 hint 增强的模型作提议分布，§5 p8）。
3. **每轮从原始预训练模型 M 重训，而非连续训练**："we train from the original pre-trained model M instead of continually training one model to avoid overfitting"（§3.1 p3）——**自举的产物是「数据集」，不是持续漂移的权重**。
4. **与 Expert Iteration (ExIt) 同源但更简**：筛选可视为「专家反馈」，但 STaR 的**专家是固定的**（ground truth），且**不训练独立价值函数**（§2 p3）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

**（a）STaR 循环的四个判定 —— 「自举信号从哪来」的原型**

| 判定 | 触发条件 | 动作 | 信号来源 | 出处 |
|---|---|---|---|---|
| **① 何时保留 rationale** | `ŷ_i = y_i`（最终答案**对**） | 收入 `D_n`，参与微调 | **二值正确性门**（与 ground-truth 标签比较） | §3.1 p3；Alg.1 L5 p4 |
| **② 何时回退到 rationalization** | `ŷ_i ≠ y_i`（生成**失败**） | 不丢弃，转交 rationalization | **失败本身**（模型侧可观测） | §3.2 p4；Alg.1 L4 p4 |
| **③ 何时给 hint** | **仅当** rationale generation 失败 | `add_hint(x_i, y_i)` 后重新生成 | **ground-truth 最终答案 y** | §3.2 p4；Alg.1 L4 p4 |
| **④ 何时用最终答案** | ①作**筛选判据**；②作 rationalization 的 **hint**；**从不**作训练目标或训练输入（hint 训练时被剥离） | — | ground-truth y | §3.1–3.2 p3–4 |

> **原型判词**：STaR 把「自举信号」锚在**一个固定的、模型碰不到的二值事实上**（最终答案对不对），并用它同时完成「筛选」（判定①）与「反向提案」（判定②③）；「最终答案」本身**绝不进入训练输入**（判定④）。这三条构成了后续所有自举工作（R-Zero/Agent0/TTCS…）改写的模板。

**（b）零件清单**

| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| rationale generation | 题 `x_i` + 10-shot rationale prompt → `(r̂_i, ŷ_i)` | 采样 rationale 与答案 | §3.1 p3；Alg.1 L3 p4 |
| **二值正确性门 `I(ŷ=y)`** | `(r̂_i, ŷ_i, y_i)` → 保留/丢弃 | **筛选**（本篇核心，C9 友好） | §3.1 p3；Alg.1 L5 p4 |
| **rationalization** | `add_hint(x_i, y_i)` → `(r̂^rat_i, ŷ^rat_i)` | 失败题**反向**生成 rationale | §3.2 p4；Alg.1 L4 p4 |
| **hint 剥离** | 训练时**去掉** hint 只留 rationale | 防泄漏、防依赖 hint | §3.2 p4 |
| 合并数据集 | `D_n ∪ D^rat_n` → 微调 `M_n` | 同时吃「答对」与「反向补上」的样本 | Alg.1 L7 p4 |
| **从原始 M 重训** | `M`（原始）+ 新数据 → `M_n` | 防过拟合、防权重漂移 | §3.1 p3 |
| 迭代外层循环 | 重复直到性能饱和 | 逐步自举 | Alg.1 L2–8 p4 |
| 内层步数调度 | 首轮 40 步、每轮 **+20%**（arithmetic 带 rationalization 首轮 300 步、每轮 +20 步） | 慢启动更优 | §4.1 p5、§4.3 p6 |
| **RL 视角（指示奖励）** | `J=Σ_i E[I(ŷ_i=y_i)]`；`∇J` 用 log-derivative trick | 把筛选解释为策略梯度的**筛选** | §3.1 式(1)(2) p4 |
| few-shot prompt 参与训练 | 采样时带 10-shot prompt | 减少 rationale「drift」、提升精度 | §4.4 p8、§5 p9 |
| 高温采样（反例） | 用高温多采样替代 rationalization | **适得其反**（错误推理配正确答案） | §5 p9、附录 H（未提取） |
| 多数投票伪标签（提及未采用） | 高温多采样取多数当 ground truth | 「significantly underperformed」，仅作 ablation | §5 p9、附录 H（未提取） |

### 2.4 关键表示与数据结构
- **数据**：`D = {(x_i, y_i)}`（题 + 正确答案）；**提示集** `P = {(x^p_i, r^p_i, y^p_i)}`，`P ≪ D`（如 `P = 10`）（§3.1 p3）。
- **每轮产出**：`D_n = {(x_i, r̂_i, y_i) | ŷ_i = y_i}`（生成正确）与 `D^rat_n = {(x_i, r̂^rat_i, y_i) | ŷ_i ≠ y_i ∧ ŷ^rat_i = y_i}`（rationalization 正确）（Alg.1 L5–6 p4）。
- **无记忆结构、无技能库、无外部知识库**：唯一「持久态」是**过滤后的 rationale 数据集**（每轮重新生成）与权重检查点（推断：全文未见 memory / skill library / retrieval 构件）。
- 超参（§4.1 p5、§4.3 p6）：底座 **GPT-J 6B**；100 步 learning-rate warmup 后恒定学习率；首轮 40 步、每轮 +20%；arithmetic 生成 **50,000** 题（数字位数均匀采样）、每轮采 **10,000**；CQA 训练 **9,741** 题；GSM8K 训练 **7,473** 题。rationale 提示：arithmetic 每个位数 10 个随机 few-shot；CQA 沿用 [6] 的 10 题（略作修正）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **算术**（1–5 位加法） | 无 rationale 微调（10,000 例、5,000 步） | **STaR 16 轮后 89.5%** vs 基线 **76.3%**；few-shot 2 位数 **<1%** | §4.3 p6、Fig 4 p6；单模型 GPT-J，无 seed/方差报告 |
| **算术（带 rationalization）** | 上一轮 | 2 位数 **<1% → 32%**（一次微调迭代内） | §4.3 p6、Fig 5 p6 |
| **CQA Dev**（Table 1） | GPT-J Direct Finetuned 60.0（100% 数据） | **STaR w/o rat 68.8（69.7% 数据）**；**STaR w/ rat 72.5（86.7% 数据；其中 8.5% 来自 rationalization）** | Table 1 p7；Dev 集 1,221 题 |
| CQA Dev 对照 | GPT-3 Direct Finetuned 73.0（100% 数据） | STaR 72.5 逼近 **30× 大**模型 | Table 1 p7 |
| CQA few-shot 对照 | Few-shot Direct GPT-J 20.9；Few-shot CoT GPT-J 36.6；Few-shot CoT **LaMDA 137B 55.6** | STaR 72.5 **超过 137B LaMDA few-shot** | Table 1 p7 |
| **GSM8K Test**（Table 2） | GPT-J Direct Finetuned 5.8（100% 数据） | **STaR w/o rat 10.1（25.0% 数据）**；**STaR w/ rat 10.7（30.3% 数据，1.2% 来自 rationalization）** | Table 2 p8；Test 集 1,319 题 |
| GSM8K few-shot | Few-shot Direct 3.0；Few-shot CoT 3.1 | STaR 10.7 | Table 2 p8 |
| **人工评估**（rationale 质量） | few-shot 与人类 rationale | STaR 被评「更能justify答案」比 few-shot 高 **30%**（p=.039）；比**人类**高 **74%**（p<.001） | §4.4 p7–8；**50 条 rationale**，**20 名 Prolific 众包**，每人随机 10 题、随机顺序 |
| 消融：few-shot prompt 参与训练 | 不参与 | 60.9%→**68.8%**（w/o rat）；69.9%→**72.5%**（w/ rat） | §4.4 p8 |
| 消融：rationalization 的作用 | 无 rationalization | 算术上「允许一次学会多个位数长度」；CQA +3.7；**GSM8K 几乎无增益**（10.1→10.7） | §4.3 p6、Table 1/2 p7–8 |
| 消融：高温采样替代 | rationalization | 更差（尤其算术，scratchpad 退化到无意义并停滞） | §5 p9、附录 H（未提取） |
| 计算步数一致性 | 人类 ground-truth 步数 | 模型步数与人类一致率 **53–57%**（不一致时模型通常更少步） | §4.5 p8、Fig 6 p8 |

### 2.6 论文自陈局限与边界条件
- **§6「Limitations and Impacts」自陈**（p9–10）：
  1. **Bias 放大**：STaR 会放大「对解数据集有用」的偏见，**rationalization 使其更糟**（把模型本不会到达的偏见答案「拉出来」）；
  2. **Faithfulness（忠实性）**：无法保证 rationale 反映模型内部过程——模型可能先选答案再编理由；「faithfulness」评估本身是开放难题；
  3. **Scale**：不保证泛化到更大模型；**小模型无法自举**——「for the first iteration of STaR to succeed, few-shot performance must be above chance… the initial model must be big enough to have some reasoning capabilities」（p10）；**GPT-2 连算术域都无法自举**；
  4. **高随机命中率场景失效**：二元决策等「chance performance 高」的设定会产生大量**坏 rationale**（答对但理由错），干扰 STaR。
- **§5 自陈**（p9）：
  5. **只查最终答案的门有漏洞**：**错误 rationale 配正确答案仍会被用于训练**；「如何超越最终答案检查来识别正确且可泛化的 rationale（如 token-level verifier）是有价值的未来方向」（p9）；
  6. **hint 机制不通用**：「the method to add the 'hint' does not follow immediately from the question and answer and in some contexts providing it may be nontrivial」（p9）；
  7. **温度**：更高温采样替代 rationalization **适得其反**；用多数投票当 ground truth **显著更差**（附录 H）。
- **隐含边界（推断）**：① 全篇依赖**数据集自带 ground-truth 答案**（筛选与 hint 都靠它）；② 三个域（算术 / CQA / GSM8K）均为**可被二值判定的语言推理任务**；③ 本 PDF 为 NeurIPS 版 **13 页，附录 A–J 未随附**（正文多处引用附录，本次未提取）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 目标是数学/常识题正确率；无生存压力、无不可逆后果；「环境」只是数据集标签（p1–3） | 只取「生成→筛选→重训」的**回路拓扑**与**二值门判据形状**，控制对象换成生存行为序列 |
| **C2** 自然语言只作观察员接口 | **✗** | rationale（自然语言）既是**训练目标**又是**筛选依据**；语言是动作空间本身（§3 p3） | SSEA 侧任何语言产物一律降级为日志；rationale 换成结构化行为轨迹 |
| **C3** 权重/记忆/技能三分离 | **✗/◐** | 只有权重一态（SFT 更新）；**无记忆、无技能库**（推断：全文未见相关构件）。**但**「每轮从原始 M 重训、产物是数据集」这一点，使**累积物在「数据」而非「权重」**——形态上比 R-Zero 更接近「结构可分离」 | 拆为 Δθ（可训练小网络）/ ΔM（外置记忆）/ ΔS（可执行技能）三通道后再谈搬运 |
| **C4** 低算力低带宽 | **✗** | GPT-J 6B；16–36 轮外层循环、每轮全数据集生成 + rationalization + **全量微调**；arithmetic 5 万题/轮采 1 万（§4.1 p5、§4.3 p6、§4.5 p8） | 只搬判据层零件（二值门、分母台账），不搬训练栈 |
| **C5** 精准回忆历史 | **—/◐** | 无记忆机制；`D_n` 每轮**重新生成**、非持久可检索记忆（未提及任何记忆结构） | — |
| **C6** 可自主修改自身 | **◐**（按四权拆） | **提案权** ✓：模型自生成 rationale（自我提案）；**边界权** ✗：架构/目标/prompt 全固定；**验证权** ✓：**二值正确性门**（唯一像样的验证权）；**应用权** ✓：SFT 更新权重 | 补边界权与四级验证门后再对标；当前可映射为「参数侧 Δθ 的受控应用」 |
| **C7** 可保存/恢复/变异/继承 | **◐** | **保存/恢复** ◐（每轮检查点，但从原始 M 重训，**无权重谱系**）；**继承** ◐（**数据集跨轮继承**，非权重）；**变异** ✗；**淘汰** ✓（**样本级**：不导出正确答案的 rationale 被丢弃——这是全族中少见的真实淘汰动作，但**非个体/种群级**） | 用 GenePackage 替换「数据集继承」；补个体级淘汰 |
| **C8** 给基因先验，不给知识语料 | **✗（整体）/ ✓（仅「自举信号不靠额外标注」层面）** ——**双层判定，见 §3.1-专项 B** | 起点是 **GPT-J 6B 预训练权重＝压缩的人类知识语料**（预训练于 The Pile 800GB [41]）；**明确自陈「利用 LLM 预存的推理能力」（p2）**；**明确自陈底座必须够大才有可自举先验（GPT-2 不行，§6 p10）**；few-shot rationale 人类手写（附录 B2，改自 Wei et al.） | **只搬循环拓扑与门形状，不搬载体**；SSEA 的基因先验应是结构性本能，不允许把预训练知识体作可继承物 |
| **C9** 不设评分函数，只有淘汰函数 | **◐（形态友好，全族最佳）/ 信号源须换** ——**详见 §3.1-专项 A** | 筛选是 **二值指示 `I(ŷ=y)`**：不打分、不排序、无奖励塑形、**无外部 judge**（对比 R-Zero 的连续 `r_uncertainty` + GPT-4o、Agent0 的沙盒）。**但**① 比较对象是**人类/模板给定的数据集标签**（外部标签 oracle），非环境侧生存事实；② 论文在 RL 视角（式 1–2 p4）把它称「reward」并驱动权重——**但它是 0/1 门而非塑形奖励**；③ 门**只查最终答案**，错误 rationale 配正确答案仍进训练（§5 p9） | **可直接对接**：把 `I(答对)` 换成 **SSEA 淘汰函数 `I(存活到 T / 危险未致死)`**（模型碰不到、确定性、二值）→ 得 C9 合规自举信号；门**只作准入、不打分不排序** |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子：GPT-J 骨干、SFT/Adam 均借用；创新在**自举回路拓扑**（L2）与 **rationalization 提议分布**（L3）；自陈为「首个让预训练 LLM 迭代用自身语言建模能力改进自身的技术」（贡献 4，p2） | — |

#### 3.1-专项 A：C9 裁决 —— 「最终答案对不对」是环境侧确定性事实，还是外部评分？

**裁决：是「二值正确性门」而非「外部评分函数」——形态上对 C9 友好（全族最佳），但信号源须从「数据集标签」换成「环境侧淘汰事实」才可直接落地。** 逐条严格核对：

| 核对项 | STaR 实况 | C9 判定 |
|---|---|---|
| 信号是「分数」还是「门」 | `I(ŷ_i = y_i)` ∈ {0,1}，确定性比较（Alg.1 L5 p4） | **门 ✓**（C9 禁「打分/排序」，不禁「合法性门」） |
| 有无奖励塑形 | 无（无连续项、无塑形项、无难度激励） | **✓**（对比 R-Zero `r_uncertainty`、GenEnv α 带、TTCS `R_cap`） |
| 有无外部 judge / 评分模型 | **无**（无 reward model、无 GPT-4o 判分） | **✓**（对比 R-Zero B.3 p15 的 GPT-4o） |
| 是否驱动权重 | 是——但通过 **0/1 门的筛选 + SFT**，而非把分数灌进优势项（§3.1 p3、式(1)(2) p4） | **◐**：门本身合规；「门 → 微调」属 C6 应用权范畴 |
| 信号是否「模型碰不到」 | **是**（标签预先给定，模型无法影响 `y_i`） | **✓**（形态等同 C9 层①「归环境、模型碰不到」） |
| 信号来源性质 | **人类/模板给定的数据集标签**（CQA 众包、GSM8K 人工、arithmetic 模板），**非**环境侧生存事实 | **须换**：SSEA 用**淘汰函数**（存活/死亡）替换 |
| 门的已知漏洞 | 只查最终答案，**错误 rationale 配正确答案仍被训练**（§5 p9 自陈） | 需在 SSEA 侧补「结构合法性/可执行」检查（PSN 式契约） |

> **一句话判词**：STaR 的筛选是**「对固定二值事实的确定性比较」**，不是「打分」——**C9 看的是「信号是不是打分、是否塑形、是否有外部评分者」，STaR 三项全过**。它比 R-Zero（内部自指连续奖励）与 Agent0（沙盒奖励 + 前沿带塑形）**在 C9 上干净一档**。
>
> **可执行结论（本篇给 SSEA 的最大增量）**：**SSEA 的淘汰函数可以直接充当这个筛选器**——把 `I(ŷ=y)` 替换为 `I(个体存活到 T / 危险未致死 / 资源未耗尽)`，即得一条**模型碰不到、确定性、二值、不打分、不排序**的自举信号，**无需任何外部评分**。这一步同时回答了三件事：①「自举信号从哪来」（来自环境淘汰事实）；②「`rules` 零消费者」（rationalization 给定结果反推规则，见 §3.3）；③「判据形状错」（门只判合法性、先看分母，见 §3.4）。

#### 3.1-专项 B：C8 裁决 —— 自举需要底座先验，底座先验从哪来？

**裁决：整体 ✗，与 R-Zero / Agent0 同口径——「预训练权重＝压缩的人类知识语料」。** 且 STaR **在这一点上自陈得最直白**，是全族的**证据来源**：

| 依赖层 | STaR 实况 | SSEA（C8 要求） |
|---|---|---|
| 种子题集 | **需要** `D={(x_i,y_i)}`（题 + **正确答案**）（§3.1 p3） | ✗ 不允许（题由环境/淘汰产生） |
| 人类标注 rationale | **不需要**（自生成）（贡献 1 p2） | ✓ 一致 |
| **人类手写 few-shot 先验** | **需要**（`P=10` 人类手写 rationale，附录 B2 改自 Wei et al.） | ✗ 不允许（语言先验不进基因） |
| **预训练知识语料** | **需要**——GPT-J 预训练于 **The Pile 800GB** [41]；**"leverage the LLM's pre-existing reasoning ability"（p2）**；**"the initial model must be big enough to have some reasoning capabilities"（§6 p10）**；**GPT-2 无法自举** | ✗ **不允许**（只给结构性先验） |
| 外部客观锚点 | 数据集 ground-truth 标签 | 环境淘汰函数 |

> **一句话判词**：STaR 证明的是「**少量 rationale 示例 + 大量无 rationale 数据可自举出推理能力**」，**没有**证明「不依赖知识语料」——它的能力底座就是**预训练权重，而预训练权重就是压缩的人类知识语料**；论文自己把这条边界写死了（GPT-2 太小、无法自举，§6 p10）。**这恰好是 SSEA 需要的反面标尺**：自举**必然**需要底座先验，因此 C8 的正确做法不是「零先验」，而是「**只给结构性先验（本能）、不给知识语料**」。STaR 的 `P=10` few-shot rationale 是「先验」的一个**极小样本形态**，可类比基因先验，但它携带的是**语言知识**而非**结构本能**，故不可直接搬进基因包。

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无（GPT-J 骨干、SFT/Adam 全部借用） | 符合 C10 借用立场，无搬运价值 |
| **L2 信息流层** | **生成→筛选→（rationalization）→微调的回路拓扑**；「hint 只作搜索工具、不进训练输入」的**接口纪律**；「每轮从原始 M 重训」的快照式训练 | **高**：这是**全族自举回路的原始形状**——R-Zero/Agent0/TTCS 的「Challenger/Synthesizer × Solver」双角色回路即由此演化 |
| **L3 学习层** | **rationalization**（条件于答案的 off-policy 提议分布 `p(r|x,y)`）；二值门筛选；步数调度 | **中–高**：rationalization 可直接对位 SSEA 慢环的「**给定结果反推结构**」提案（`rules` 消费者原型）；门筛选可对位慢环准入 |
| **L4 演化层** | **数据集跨轮继承** + **样本级淘汰**（不导出正确答案的 rationale 被丢弃） | **中**：全族中少见的**真实淘汰动作**（虽为样本级）；但无基因包、无种群、无个体级淘汰 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **二值正确性门 `I(ŷ=y)`** | `verification_gate.py`（**合法性层**）+ `experience_compiler.py`（准入）+ **淘汰函数**：**直接对接**——把判据换成环境侧存活/淘汰事实，即得 C9 合规自举门（回应 C9 与「判据形状错」债务 25/26/27/28） |
| **rationalization（给定结果反推中间结构）** | **`rules`（当前零消费者）**：把「给正确答案作 hint 反推 rationale」改造为「给**成功的行为结果/存活事实**作 hint，反推可复用**规则/行为序列**」→ 给 `rules` 一个**消费者原型**；亦作慢环 SEL 的**反向提案**通路 |
| hint 剥离（训练输入不含 hint） | 慢环提案纪律：**「用于搜索的先验」不得进入被固化的结构**（防泄漏、防依赖） |
| **从原始 M 重训（快照式）** | 呼应 SSEA「**快环只读不可变快照**」——自举产物是**数据/结构**，不是持续漂移的权重 |
| 二值门 + 分母台账（78.2% + 8.5% = 86.7%） | **判据纪律**：「先看分母（候选数/保留数）再报行为差」的现成模板（债务 25/26/28） |
| few-shot 先验 `P=10` | C8 基因先验的**极小样本形态**参照（但须换成结构本能，见 §3.1-专项 B） |
| 高温采样 / 多数投票（反例） | **反例证据**：自造信号若放宽到「高温多采样」，会「错误推理配正确答案」而退化——支持「门须严格、须确定性」 |
| 能力沉在权重 / 无技能库 | 反例证据：`skill_library.py` 的可执行、可检视、可继承形状正是 STaR 所缺 |

### 3.4 债务与验收实验对应
- **判据形状错 / 环境对无消费者通道报成功 / 技能失效被判成成功（债务 25/26/27/28）**：STaR 的**二值门 + 分母台账**是「门只判合法性、不打分、不排序」的**教科书模板**；「78.2% 生成 + 8.5% rationalization = 86.7% 训练数据」是「**先报分母再报行为差**」的现成范式。
- **`rules` 零消费者**：**rationalization 直接给出消费者原型**——「给定结果反推中间结构」正是规则应有的用途。
- **记忆二级门「开得准不准」的选择性缺失**：STaR 的「只保留导出正确结果的 rationale」＝记忆/经验准入的**最小形状**（选择性来自二值事实，不来自常量阈值）。
- **技能表示够不够（0/33 之后仍未回答）**：STaR 提供**反例**——能力沉在权重/rationale 文本里，不可检视、不可回滚、不可继承；坚持 `skill_library.py` 的可执行契约形状（与 PSN 互补）。
- **睡眠期计算预算未定义**：STaR 给量级参照——**每轮全数据集生成 + rationalization + 全量微调，循环 16–36 轮**（§4.3 p6、§4.5 p8）；「一轮自举」的成本形状可作预算标定（推断，不可直接照搬）。
- **可服务的验收实验**：实验 3（技能固化 0/33）的反例解释；实验 2（记忆召回）的准入改造；以及「自举信号来源」这一新问题的原型验证（见 §8）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **二值正确性门 `I(ŷ=y)` 作为自举筛选器**（不打分、不排序、无 judge） | 判据/协议 | **改造移植**（判据换成环境淘汰事实） | 淘汰函数、`verification_gate.py`、`experience_compiler.py` | C9 合规的自举信号；「判据形状错」债务 25/26/27/28 | 高 |
| 2 | **自举四判定原型**（保留/回退/hint/最终答案用途） | 思想/回路拓扑 | 仅借思想（结构版） | 慢环 SEL 提案回路 | 「自举信号从哪来」的原型答案 | 高 |
| 3 | **rationalization：给定结果反推中间结构** | 算法 | **改造移植**（hint 换成环境成功事实） | **`rules`（零消费者）**、慢环反向提案 | 给 `rules` 一个消费者；失败样本不浪费 | 中 |
| 4 | **hint 剥离纪律**（搜索用先验不进训练输入） | 协议 | 直接移植 | 慢环提案纪律 | 防泄漏、防依赖 hint | 高 |
| 5 | **从原始模型重训（快照式自举）** | 工程/设计原则 | 直接移植 | 慢环升版纪律 | 自举产物是数据/结构，非漂移权重 | 中 |
| 6 | **「候选→筛选→训练集」分母台账**（78.2%+8.5%=86.7%） | 方法论 | 直接移植 | 判据纪律 | 「先看分母」纪律（债务 25/26/28） | 中 |
| 7 | **「自举需要底座先验」的实证**（GPT-2 无法自举，§6 p10） | 证据/裁决依据 | 直接引用 | C8 判定与写卡纪律 | 给「零先验不可行、结构性先验可行」一个可援引的边界证据 | 高 |
| 8 | **高温采样/多数投票的退化反例**（§5 p9） | 证据/诊断 | 直接引用 | Misevolve 红队清单 / 门设计 | 自造信号必须严格、确定性，否则退化 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（逐条，对应 3.1 中 ✗/◐）：
  - **C1 ✗ / C2 ✗**：非生存控制架构；语言 rationale 既是训练目标又是筛选依据。
  - **C3 ✗/◐、C4 ✗、C5 —/◐、C7 ◐**：无记忆、无技能库；6B 模型 + 多轮全量微调；无权重谱系（但**有样本级淘汰**，全族中较好）。
  - **C8 ✗（整体）**：能力底座＝预训练知识语料（The Pile 800GB），论文自陈底座必须够大（§6 p10）。
  - **C9 ◐（形态友好）**：门本身合规，**唯一须改的是信号源**（数据集标签 → 环境淘汰事实）。
- **隐含假设与失效条件**：
  1. **必须有 ground-truth 最终答案**：筛选与 hint 都依赖它；无答案时退化为多数投票，**显著更差**（§5 p9）——对 SSEA，无「答案」但有「淘汰事实」，故须替换而非照搬。
  2. **底座必须够大**：小模型（GPT-2）无法自举（§6 p10）——**自举不是零门槛**。
  3. **高随机命中率场景失效**：二元决策等会产生大量「答对但理由错」的样本（§6 p10）。
  4. **门只查最终答案 → 污染训练集**：错误 rationale 配正确答案仍进训练（§5 p9 自陈）。
- **算力 / 带宽 / 工程代价**：GPT-J 6B × 16–36 轮 × 每轮全数据集生成 + rationalization + 全量微调；arithmetic 5 万题/轮采 1 万——与 C4 冲突；但**资产 1/2/4/6 都是判据/协议层**，可在现有代码廉价实现。
- **搬运后的可能退化模式**（若失败，会以什么形式失败）：
  1. 若把「门」实现成**打分/排序**，即退化为 C9 违规的奖励塑形——**必须保持二值、只作准入**；
  2. 若用**自洽性/高温多采样**代替确定性事实，会重演「错误推理配正确答案」的污染（§5 p9）；
  3. 若 rationalization 的 hint 用**语言答案**而非**结构事实**，会把语言知识混入被固化的结构（C2/C8 违规）；
  4. 若「每轮重训」改成「连续训练」，会丢失「自举产物是数据而非漂移权重」这一防护，趋向 R-Zero 式 model collapse。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **同族·直系后代（最紧）** | **R-Zero**（本库 **B/P1**） | 把 STaR 的**二值门**替换为**前沿带 `\|p̂−0.5\|≤δ` + 连续不确定性奖励**，并把「人工出题」变成**可 RL 的 Challenger**；代价是**从 C9 友好（二值门）退化为 C9 违规（自指连续奖励 + GPT-4o 判分）**。**STaR 是 R-Zero 的祖宗，且在 C9 上更干净**——R-Zero 卡片 §6.1 已把「前沿带」判为可搬资产；STaR 补上「**为什么门可以是二值的**」这一更原始的原型 |
| **同族·直系后代** | **Agent0**（本库 **B/P1**） | 同为「零数据 + 自洽性 `p̂` + 前沿带」，往环里插**外部 Python 沙盒**。**STaR 的 ground-truth 门 vs Agent0 的沙盒门**：两者都是「模型碰不到的确定性事实」，但 STaR 的门**不打分**（Agent0 的沙盒结果进前沿带奖励）；STaR 更原始、更 C9 友好 |
| **同族·课程合成** | **TTCS**（本库 **B/P1**） | 「无标签自洽性前沿带」＝判据分辨力校准器；把 STaR 的「固定 ground-truth 门」换成**在线 `\|s−0.5\|≤δ` 带**。**STaR 给「门的最简形状」，TTCS 给「无标签时如何保分辨力」**，两者互补：SSEA 生存域**有**淘汰事实（可用 STaR 式门），**无**ground-truth 标签（需 TTCS 式校准） |
| **同族·目标可操作化** | **Aspire**（本库 **B/P1**） | 模糊目标 → 可操作判据；STaR 的「最终答案对不对」是**最简的判据操作化**。Aspire 的「判据形状与产出记账方法学」与 STaR 的「分母台账」同源，可合并为 SSEA 判据设计清单 |
| **同族·经验生命周期** | **EvolveR**（本库 **B/P1**） | 「经验生命周期」回路形状与 STaR 的「生成→筛选→固化的循环」同构；EvolveR 的库治理四件套（去重/合并/计分/剪枝）可补 STaR **缺失的记忆治理**（STaR 的 `D_n` 无治理、每轮重生成） |
| **同族·无梯度整机演化** | **EvoTest**（本库 **B/P1**） | 成功/失败**双记忆** + 无梯度演化；STaR 的「保留正确 / rationalize 失败」正是**成功/失败双通道**的最简版本——EvoTest 的「失败记忆」可视为 STaR rationalization 的结构化后继 |
| **同族·外部模型辅助（未建卡）** | **Socratic-Zero** | 本库**未见卡片**（`cards/` 目录无此文件）。若按 R-Zero 卡片口径，Socratic-Zero 依赖**外部专有模型**做推理辅助，是 C9「外部评分/外部模型」的**显性化版本**——比 STaR 的「无外部 judge」更远 |
| **互补（技能侧，最紧）** | **PSN**（本库 **A/P1**） | STaR 的**最大空洞**：rationale 沉在权重/文本里，不可检视/回滚/继承（且门只查最终答案，坏 rationale 照样进训练）。PSN 的带契约可执行技能网络 + 成熟度门控 + 回滚验证正好补洞。合成：STaR 负责**造什么样的练习并筛选**，PSN 负责**把结果固化成可继承结构** |
| **互补（记忆侧）** | **Memento / FLEX / MemRL / LightMem** | STaR **无记忆结构**；其「二值门准入」若落地，落点是这些记忆系统的**准入门**（对照 Memento 冻结 LLM + 案例库、FLEX 分层经验库） |
| **互补（离线省算力）** | **Dream-RSI**（本库 **A/P1**） | STaR 每轮全数据集生成 + rationalization 很贵；Dream-RSI 的「发现历史即重放模拟器」可把生成/筛选搬进**睡眠期离线重放**，缓解 C4 冲突 |
| **风险验收** | **Misevolve**（本库 **A/P1**） | STaR 的结构＝自举回路 + 只查最终答案的门 + 偏置放大（§6 p9 自陈）；**bias 放大与 faithfulness 缺失**是其威胁模型条目；搬运前须过 Misevolve 红队清单 |
| **上游思想源** | **Expert Iteration (ExIt) [21] / Reflexion（本库 B/P2）** | STaR 自陈受 ExIt 启发（筛选＝专家反馈，但专家固定、无价值函数，§2 p3）；Reflexion 的「试错-评估-反思外环」是同一经典形状的对话版 |

### 6.2 推荐组合方案
1. **C9 合规自举门（STaR × SSEA 淘汰函数 × PSN）**
   - **接口形态**：`verification_gate.py` 增设**二值门**：`I(存活到 T) / I(危险未致死) / I(资源未耗尽)` → 只决定样本是否进入巩固，**不打分、不排序**；门内样本交 `experience_compiler.py` / `skill_library.py`（PSN 契约）固化。
   - **收益**：直接给出「自举信号从哪来」的 C9 合规答案；门保持二值即守住 C9。
2. **rationalization → `rules` 消费者（STaR × `rules` 零消费者 × EvolveR 库治理）**
   - **接口形态**：慢环对**失败个体**取「环境成功事实」作 hint，反推**可复用规则/行为序列**（不是语言理由）；产出经 EvolveR 式治理（去重/合并/剪枝）后写入 `rules`；hint 不进最终结构（资产 4）。
   - **收益**：给 `rules` 一个消费者；失败样本不再浪费；补 STaR 缺失的记忆治理。
3. **崩溃/污染监控（STaR 反例 × Misevolve × 慢环停机判据）**
   - **接口形态**：监控「门内样本的坏 rationale 比例」与「偏置放大」两条曲线（对标 §5 p9、§6 p9）；门只查最终答案 → 须补结构合法性检查（PSN 式）。
   - **收益**：防「错误推理配正确答案」污染自举回路。

### 6.3 本篇在组合中的典型角色
- **自举推理族的奠基原型 + C9 友好筛选门的最小范例 + 「自举信号从哪来」的原问题答案 + `rules` 消费者原型**。它不为 SSEA 提供可执行训练栈（那属于 R-Zero/Agent0），提供的是**最原始的回路形状、最干净的门判据、以及一条「底座先验不可省」的边界证据**。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 正面击中「自举信号从哪来」（四判定原型，实测 §3.1 p3–4）、C9 门判据（实测 Alg.1 p4）、`rules` 消费者（推断映射）与「先看分母」纪律（实测 Table 1/2 p7–8）；且是整族祖宗。扣分：目标域是语言推理，与生存具身控制相距很远（推断） |
| 立场兼容性 | **3** | C9 **形态友好（全族最佳，◐）** 是重要加分；但 C1/C2/C3/C4/C8 五条冲突（C8 论文自陈底座必须够大，实测 §6 p10）。比 R-Zero/Agent0 的兼容性高一档 |
| 可搬运性 | **4** | 判据/协议层零件（二值门、四判定、hint 剥离、分母台账）可**干净拆出**、不依赖训练栈；rationalization 需改 hint 语义（推断）。语言 rationale SFT 本体不可拆 |
| 证据强度 | **3** | 三域（算术/CQA/GSM8K）+ 多消融（rationalization、few-shot 训练、温度）+ **带 p 值的人工评估**（p=.039、p<.001，§4.4 p7–8）；**有独立 Limitations 章节**（加分）。但**单模型（GPT-J）**、**无 seed/方差**、报 best、GSM8K 绝对数很低（实测，§4.5 p8） |
| 组合价值 | **4** | 与 R-Zero / Agent0 / TTCS / Aspire / EvolveR / EvoTest / Socratic-Zero / PSN / Memento / FLEX / MemRL / LightMem / Dream-RSI / Misevolve / Reflexion / ExIt 均有明确、可命名的接口（推断） |
| 落地成本 | **4** | 采用判据/协议层零件几乎零新增算力，可在 `verification_gate.py` / `rules` / `experience_compiler.py` 上做；不搬训练栈则成本可控（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用四件：**二值正确性门（改造为环境淘汰门）**、**自举四判定原型**、**rationalization（改造为「给定结果反推结构」的 `rules` 消费者）**、**分母台账**；并采用两条**证据型资产**：**「自举需要底座先验」的边界证据（GPT-2 无法自举）**与**高温采样/多数投票的退化反例**。**不采用**：语言 rationale SFT 训练栈、GPT-J 载体、预训练知识语料作为可继承物、把门做成打分/排序。
- **优先级：P1** —— 理由有三：① 它是**自举推理族的奠基工作**，其「四判定」是 R-Zero/Agent0/TTCS… 改写的原始模板，「自举信号从哪来」这一坐标不能悬空；② 它的**二值门是全族中唯一对 C9 形态友好者**，**SSEA 淘汰函数可直接充当**——这是「C9 合规自举」的最短路径；③ 其 **rationalization** 恰好给当前**零消费者的 `rules`** 一个原型。**注**：其判据层增量**高于 R-Zero**（R-Zero 的门是自指连续奖励），与 Agent0 的沙盒门**同源但更简**。
- **建议动作**：
  1. 在 `verification_gate.py` 增设 **`binary_gate(outcome) -> bool`**：判据＝环境侧二值事实（存活到 T / 危险未致死），**只作准入、不打分不排序**；先做只读影子模式（记录会准入/会拒绝的样本，不改行为）。
  2. 在 `rules` 上落 **rationalization 通路**：对失败个体取环境成功事实作 hint，反推可复用规则/行为序列（hint 不进最终结构），给 `rules` 一个消费者。
  3. 记录**分母台账**：每轮「候选数 → 门内数 → 固化数」，写入判据纪律（债务 25/26/28）。
  4. 立项 **C8 专题（续 R-Zero 卡片 §8.4）**：把 STaR 的「GPT-2 无法自举」作为「零先验不可行」的边界证据，统一「零标注 / 零种子题 / 零知识语料 / **零底座先验**」四级标尺。
- **最小验证实验（二值淘汰门作为自举筛选器，服务实验 2/3 与债务 22/25/26/28）**：
  - **双臂 / 消融**：
    - **A 二值淘汰门臂**：准入判据＝`I(存活到 T)`（环境侧确定性二值事实），**不打分**；
    - **B 常量阈臂**（现状对照）：现有固定阈值二级门；
    - **C 打分臂**（STaR 的 RL 视角 / R-Zero 式）：把同一信号**做成连续分数**并用于排序——检验「打分是否比二值门更差」（C9 的反事实）。
    - ≥8 seed；慢环轮数固定。
  - **判据（分档，先看分母）**：
    1. **机制计数**：门内样本数、被拒样本数、`rules` 被实际调用次数（**先确认分母非零，尤其 `rules` 当前零消费者**）；
    2. **行为差**：记忆检索命中率（当前 0.5164）、逐帧动作差；
    3. **淘汰结果**：存活时长（**注意：危险回避率两臂均 0.9814 已饱和，不得作本实验判据**）。
  - **预期与证伪条件**：
    - 预期：A 在「命中率」与「`rules` 调用数」上优于 B，且**A ≥ C**——证明「**二值门不劣于打分**」，从而支持 C9「只判合法性、不打分」在 SSEA 域可行。
    - **证伪**：若 A < C（打分显著更好），说明 SSEA 当前环境事实的**二值化损失了信息**——此时应回查「淘汰事实的分辨力」（呼应「retrieve 键收窄→召回精度上限低」），而非改成打分（打分仍违反 C9）。
    - 另需监控 STaR 式污染：若门内样本的「结构非法/理由不可执行」比例升高，判为门过宽，须补 PSN 式结构检查（对标 §5 p9 自陈的「坏 rationale 配正确答案」）。
- 若 **E 不采用**：不适用（本卡片裁决为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 是否**正式采纳「淘汰函数即自举筛选器」**这一等价？若是，STaR 的裁决应从 B 升为 **A 核心借鉴**（它给出最短路径）；这决定资产 1 的落地形态。
  2. C8 的官方定义是否明确排除「以预训练权重形式携带的知识」？若是，STaR / R-Zero / Agent0 / Socratic-Zero 整族都应判为「零标注 / 零种子题，但非零知识、非零底座先验」。
- **需补查的文献或资料**：
  1. **Socratic-Zero**——本库 `cards/` **未见卡片**，本卡片 §6.1 仅按 R-Zero 卡片口径概述，**未核实全文**；若要纳入正式组合，需先补卡。
  2. **STaR 的附录 A–J**——本 PDF 为 NeurIPS 版 **13 页，附录正文未随附**（正文引用附录 A/B2/C/G/H/I/J，本次未提取）；涉及错误分析、few-shot 提示、超参、多数投票 ablation（附录 H）等，若需精确引用须补读 arXiv 全文版。
  3. **Self-Consistency [35]**——STaR §5 p9 提及用多数投票替代 ground truth 作 ground truth 的 ablation（附录 H），建议补读以厘清「自造标签」的退化程度。
- **需人工核对的公式 / 实现 / 数字**：
  1. **RL 视角的表述**：式(1)(2)（p4）把 `I(ŷ=y)` 称作「reward」并称 STaR 为「policy gradient objective 的近似」——**这是「门」还是「奖励」的措辞张力**，SSEA 引用时须注明「其数学形式是 0/1 指示门，非塑形奖励」（本卡片 §3.1-专项 A 已作此判定，属**推断**）。
  2. **「30× 更大」的基数**：摘要/CQA 处称 GPT-3 为 STaR 的 **30× 大**（p1、§4.4 p7）；GPT-3 参数量与 GPT-J 6B 的比值未在正文给出，需核对口径。
  3. **算术整体 89.5% 的位数口径**：§4.3 p6 称「16 iterations 后 overall accuracy 89.5%」，但 1–5 位各序列的加权方式未明确（推断为各位数平均或题量加权），需核对 Fig 4。
  4. **人工评估的统计口径**：50 条 rationale、20 名众包、每人 10 题（§4.4 p7）——「30% 更可能 / 74% 更可能」的具体度量（排名 vs 偏好）与样本量换算需核对原文。
  5. **训练数据占比**：Table 1 注称 STaR w/ rat 训练于「78.2%（生成）+ 8.5%（rationalization）= 86.7%」，但表中列 86.7；§4.3/§4.5 对 GSM8K 的 25.0%/30.3%/1.2% 口径需与 Table 2 逐项对齐。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "This technique, the 'Self-Taught Reasoner' (STaR), relies on a simple loop: generate rationales to answer many questions… if the generated answers are wrong, try again to generate a rationale given the correct answer; fine-tune on all the rationales that ultimately yielded correct answers; repeat." | p1（摘要） |
| "by leveraging the LLM's **pre-existing reasoning ability**, we iteratively bootstrap the ability to generate high-quality rationales" | p2（§1） |
| "we find this loop eventually fails to solve any new problems… because it receives no direct training signal for problems it fails to solve. To overcome this issue, we propose **rationalization**: for each problem that the model fails to answer correctly, we generate a new rationale by providing the model with the correct answer." | p2（§1） |
| "a bootstrapping mechanism to iteratively generate a rationale dataset from a few initial examples with rationales—**without needing to check new rationales' correctness**" | p2（贡献 1） |
| "the first technique to allow a pre-trained large language model to **iteratively use its language modeling capacity to improve itself**" | p2（贡献 4） |
| "We assume that rationales that lead to correct answers are of better quality than those that lead to incorrect answers. Therefore, we filter the generated rationales to include only the ones which result in the correct answer (ŷ_i = y_i)." | p3（§3.1） |
| "once we collect a new dataset, we train from the **original pre-trained model M** instead of continually training one model to avoid overfitting" | p3（§3.1） |
| `J(M,X,Y)=Σ_i E_{r̂,ŷ∼p_M(·\|x_i)} I(ŷ_i=y_i)`；"the indicator function discards the gradient for all sampled rationales that do not lead to the correct answer y_i: this is the filtering process in STaR" | p4（§3.1 式(1)(2)） |
| "we provide the answer as a hint to the model and ask it to generate rationales… **Given the answer, the model is able to reason backwards**… When adding a rationalization-generated rationale to our dataset, we **do not include the hint** in its corresponding prompt, as if the model had come up with the rationale without the hint." | p4（§3.2） |
| Alg.1：L3 rationale generation；L4 rationalization（`add_hint(x_i,y_i)`）；L5 `D_n={…\|ŷ_i=y_i}`；L6 `D^rat_n={…\|ŷ_i≠y_i ∧ ŷ^rat_i=y_i}`；L7 `M_n←train(M, D_n∪D^rat_n)` | p4（Algorithm 1） |
| Table 1（CQA Dev）：GPT-3 Direct Finetuned 73.0；Few-shot Direct GPT-J 20.9；Few-shot CoT GPT-J 36.6；Few-shot CoT LaMDA 137B 55.6；GPT-J Direct Finetuned 60.0；**STaR w/o rat 68.8（69.7%）**；**STaR w/ rat 72.5（86.7%，含 8.5% rationalization）** | p7 |
| Table 2（GSM8K Test）：Few-shot Direct 3.0；Few-shot CoT 3.1；GPT-J Direct Finetuned 5.8；**STaR w/o rat 10.1（25.0%）**；**STaR w/ rat 10.7（30.3%，含 1.2%）** | p8 |
| §4.3：算术 16 轮后 overall **89.5%**；无 rationale 基线（10,000 例、5,000 步）**76.3%**；few-shot 2 位数 **<1%**；带 rationalization 2 位数 **<1%→32%** | p6 |
| §4.4：人工评估——STaR rationale 比 few-shot 高 **30%**（p=.039）、比**人类**高 **74%**（p<.001）；few-shot prompt 参与训练：60.9%→68.8%（w/o rat）、69.9%→72.5%（w/ rat） | p7–8 |
| §5：**"One limitation of STaR is that undesirable rationales… paired with correct answers will still be used for training."**；"How to identify correct and generalizable rationales **beyond checking the final answer**… is a valuable direction" | p9 |
| §5：更高温采样替代 rationalization **counterproductive**；多数投票当 ground truth **significantly underperformed** | p9 |
| §6：**"in order for the first iteration of STaR to succeed, few-shot performance must be above chance… the initial model must be big enough to have some reasoning capabilities"**；**GPT-2 was not able to bootstrap**；高 chance-performance 场景产生大量坏 rationale | p10 |
| §6：Bias 会被放大，**rationalization 使其更糟**；Faithfulness 无法保证（模型可能先选答案再编理由） | p9–10 |
| 底座：GPT-J 6B（§4.1 p5）；预训练语料 The Pile 800GB（引 [41] p13） | p5、p13 |
| 代码：`https://github.com/ezelikman/STaR` | p1（脚注） |
