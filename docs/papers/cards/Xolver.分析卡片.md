# 论文分析卡片 · Xolver

> 纪律：任何结论若无法回溯到 C1–C10 裁判标准，即视为偏离 SSEA 立场，不予采纳。
> 论文未提及的内容一律标「未提及」，不得替论文主张。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-06-17 Xolver Multi-Agent Reasoning with Holistic Experience Learning Just Like an.pdf` |
| 标题 | **Xolver: Multi-Agent Reasoning with Holistic Experience Learning Just Like an Olympiad Team** |
| 作者 / 机构 | Md Tanzib Hosain\*、Salman Rahman\*、Md Kishor Morol、Md Rizwan Parvez；American International University-Bangladesh、University of California Los Angeles、Cornell University、Qatar Computing Research Institute（\* 表示在 QCRI 远程 RA 期间完成） |
| 发表时间 / 出处 | arXiv:2506.14234v1 [cs.CL] 17 Jun 2025；Preprint，Under review（35 页） |
| 论文链接 | arXiv:2506.14234 |
| 代码链接 | 开源：`https://kagnlp.github.io/xolver.github.io/`（p1 Abstract 自陈「We open-source all code, and data」） |
| 标签 | 多智能体推理 · 整体经验学习(holistic experience) · 双记忆(episodic + intermediate shared) · 跨题经验累积 · 训练-free · BM25 检索 vs 自检索 · LLM Judge 打分 |
| **应用裁决** | **B 零件采用**（取「双记忆分层」「跨题经验累积回路」「整体经验维度清单」「外部>自检索>无检索证据」「消融优先级」五件；**不采用**其 LLM Judge 标量评分、TopK-by-score 选择、多智能体 LLM 组织方式、自然语言载体、self-judge） |
| 优先级 | **P2**（记忆侧资产与 Memento/FLEX/Agent KB/ReasoningBank 高度重叠；但「长期 episodic 库 × 单题工作记忆」的**双记忆分层**与「竞赛内跨题累积」是现有卡片未覆盖的净增量） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：给**黑盒 LLM（training-free，不改权重）**配一套「整体经验」——把 episodic 检索（外部语料 BM25 或模型自检索）、工具调用、多智能体协作、LLM Judge 评估、迭代精化，以及**竞赛中跨题累积**的 episodic 记忆缝成一个多智能体推理回路；在 GSM8K / AIME'24 / AIME'25 / Math-500 / LiveCodeBench 上一致超越基线智能体（OctoTools / CheatSheet / Search-o1），o3-mini-high 骨架达 98.1 / 94.4 / 93.7 / 99.8 / 91.6（p1 Abstract、Table 1 p7）。
- **对 SSEA 的意义**：它是**记忆侧**的一篇，但给了一个 SSEA 尚未明确的形式——**双记忆分层**：`D_E` 长期 episodic 库（跨题持久、可写）+ `D_S` 单题中间共享记忆（定长 `|D_S|=m`、按分数留 top-m）。其中 `D_E ← D_E ∪ (q,T,R)` 的**运行中增量写入**（Xolver(+) vs Xolver(−) 平均 +3.5 分、编码最大 +7.7 分，p7）直接对应 SSEA 慢环的**增量巩固**。**关键更正**：论文自陈 **training-free**（p1、p12），**未把经验写入权重**——所谓「双通道」实为「外部语料检索 vs **冻结参数**自检索」，因此它对 **C3 的挑战远弱于其标题给人的印象**：SSEA 只需把参数通道降为**只读冻结先验**、把外部通道作为**唯一可写经验通道**即可；真正硬冲突在 **C2（全自然语言）与 C9（Judge 标量评分 + TopK 选择）**。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–2）：当前 LLM 推理「operate in isolation」——每个问题被当作独立尝试，不累积、不整合经验性知识；而人类专家（Olympiad / 编程竞赛队）依赖**多模态经验**：教练指导、过往题目直觉、工具与库用法、同伴专长、试错精化、以及**竞赛中从相关题目学习**。
- **它指出的既有方案缺陷**（p2）：既有经验增强方法**各自停留在单一模态**——只检索相似题/上下文（RAG 一族）、只用外部工具、或只做多智能体协作——**无法跨经验维度综合**，因此学不到人类专家那种「互连的知识结构」。Related Work（p11–12）进一步点名：Reflexion / MemGPT 等「operate on isolated tasks, lack cross-problem experience accumulation, and employ single-agent architectures」；CheatSheet / Search-o1「remain confined to single-agent architectures」。

### 2.2 核心思想（关键 insight）
1. **经验应被当作「整体（holistic）」而非单一模态**：把 episodic 检索、工具、协作、评估、精化、跨题传播**统一进一个回路**，而非各自为政（p1–2、Fig.2 p3）。
2. **记忆要分两层、生命周期不同**：`D_E` 是**跨题、持久、可增长**的长期 episodic 库；`D_S` 是**单题、定长、按质量替换**的中间工作记忆（`|D_S|=m`，每轮 `D_S ← TopK(D_S ∪ {新轨迹}, m; key=score)`，p5）——长短期分工。
3. **经验可以在「竞赛中」累积**（in-competition cross-problem experience）：解完一题即把 top-ranked `(q,T,R)` 写回 `D_E`，下一题即可检索到——Xolver(+) 相对静态版 Xolver(−) 平均 **+3.5 分**（p7）。
4. **外部经验优于模型自带的参数经验**：External Retrieval > Self-Retrieval > No Retrieval 在四个设置上**一致成立**（Fig.5 p8）——参数记忆可作后备但更弱。
5. **多智能体多样性 ≠ 迭代深度，二者互补**：预算受控实验中，固定「智能体数 × 迭代数」总量后，智能体数**超过 3 后仍有 >4% 的涌现增益**（p8）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **Planner Agent `P`** | 问题 `q` + 智能体数 `m` → 团队 `A`（`|A|=m`） | 先**过生成** `M>m` 个候选角色，再选出最有影响力的 `m` 个 | §2.1 p3–4；App. A.1 p19 |
| **Dynamic Reasoning Agents `A`** | 角色 + 检索范例 + 历史 + `D_S` → 思维链 `T` + 响应 `R` | 每轮 `C_i^j = {q} ∪ {T_{i-1}^j,R_{i-1}^j} ∪ D_S`（`i≥1`）；`i=0` 用 `{q} ∪ R(D_E)` | §2.1 p4（BUILD CONTEXT） |
| **Judge Agent `J`** | `(q,T,R)` → 反馈元组 `S=(T_S,s)` | `T_S` 为自然语言批判，`s` 为**标量质量分**：数学 `s∈[0,1]`（LLM 估计正确概率）；编码 `s∈{0..N_test}`（通过用例数） | §2.1 p4；App. A.3 p20 |
| **Verifier Agent `V`** | top-ranked `D_S` 条目 → 格式化最终答案 `y` | 数学抽 `\boxed{}`；编码调**外部调试器 LDB**（Python 运行时，迭代修 RTE） | §2.1 p4；App. A.4 p20 |
| **Tools `T`** | 需要时调 Python 执行 | 提升复杂计算准确率；提示词**工具无关**，当前仅 Python | §2.1 p4 |
| **Episodic Memory `D_E`** | 长期库 `{(q',T',R')}` | 两种形态：**外部语料** `D_E^ext`（BM25，k=5）或**内部参数记忆**（模型自采样自检索） | §2.2 p4–5 |
| **自检索回退 `R(D_E)∼LLM_j(q)`** | 无外部语料时 → 自采样相似题 | 无外部资源时的后备；Fig.5 显示劣于外部但优于无检索 | §2.2 p5；Fig.5 p8 |
| **中间共享记忆 `D_S`** | 候选池 → 定长 top-m | `D_S ← TopK(D_S ∪ {τ_i}, m; key=s(e))`，`|D_S|=m` | §2.2 p5（UPDATE SHARED MEMORY） |
| **运行中 episodic 写入** | 解完一题 → 追加 `(q,T,R)` | `D_E^ext ← D_E^ext ∪ (q,T,R)`；跨题经验累积 | §2.2 p5（UPDATE EPISODIC MEMORY） |
| **推理协议 Algorithm 1** | `(q,T,D_E,m,k,I)` → `y` | 三阶段：Planner 建队 → 迭代 `I` 轮（建上下文/跑智能体/更新 `D_S`/收敛检测）→ Verifier 出答案 + 写 `D_E` | §2.3 p5（Algorithm 1） |
| **收敛判据 `CONVERGED(D_S)`** | `D_S` 全满分为 1.0（数学）或全过用例（编码）→ 停机 | 迭代停机条件 | §3.1 p6 |
| **合成测试用例** | `AceCode-RM-32B` 生成 10 条 + 题面样例 | 编码任务判分依据 | §2.1 p4 |
| **CodeSim 式模拟执行** | LLM 提示模拟执行 → 判定用例通过 | 避免编译器交互延迟、保持符号可追溯 | §2.1 p4 |

### 2.4 关键表示与数据结构
- **`D_E`（长期 episodic 库）**：`D_E^ext = {(q',T',R')}`——过去题目 `q'`、思维链 `T'`（可选）、解答 `R'`。检索算子 `R(D_E)` 返回 K 个相关范例；外部时 `Retrieve_j(q, D_E^ext)`（BM25），无外部时 `∼LLM_j(q)`（自检索）（§2.2 p4–5）。
- **`D_S`（中间共享记忆）**：定长集合 `|D_S|=m`；条目 `τ_j^i = (T_j^i, R_j^i, S_j^i, a_j)`（思维/响应/反馈/智能体身份）；初始 `D_S←∅`；每轮按 `s(e)` 留 top-m（§2.2 p5）。
- **反馈元组 `S=(T_S,s)`**：`T_S` 自然语言解释、`s` 标量分（§2.1 p4）。
- **提示词全部 0-shot**，全文见 App. A（p19–20）；**输出格式**：数学 `\boxed{}`，编码 ```` ```python ```` 块。
- **超参默认**：`temperature=0.2`、`m=3`（智能体数）、`I=2`（最大迭代数）、检索 `k=5`（§3.1 p6）。
- **外部语料**：编码 = 从 GitHub（cp-algorithms）采集的 **9M-token** 算法题 + C++ 解答（App. C p33 另有 156 篇细粒度教程，分 10 类）；数学 = **OpenMathReason** 数据集（§3.1 p6）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **GSM8K** | o3-mini-medium LongCoT 95.2 / QWQ-32B 96.1 | Xolver(+)：**97.1** / **98.0**；o3-mini-high Xolver(+) **98.1** | Table 1 p7；**单次贪心解码** |
| **AIME'24** | o3-mini-medium 75.8 / QWQ-32B 78.1 | Xolver(−) 87.2 / 89.9；Xolver(+) **93.8** / **93.6**；o3-mini-high Xolver(+) **94.4** | Table 1 p7；**16 runs** |
| **AIME'25** | o3-mini-medium 70.4 / QWQ-32B 65.8 | Xolver(−) 85.1 / 79.5；Xolver(+) **89.4** / **82.7**；o3-mini-high Xolver(+) **93.7** | Table 1 p7；**32 runs** |
| **Math-500** | o3-mini-medium 97.3 / QWQ-32B 83.2 | Xolver(−) 97.7 / 93.1；Xolver(+) **99.2** / **95.5**；o3-mini-high Xolver(+) **99.8** | Table 1 p7；**单次贪心** |
| **LiveCodeBench (v5)** | o3-mini-medium 66.3 / QWQ-32B 63.4 | Xolver(−) 79.6 / 76.2；Xolver(+) **87.3** / **79.2**；o3-mini-high Xolver(+) **91.6** | Table 1 p7；**32 runs**；pass@1 |
| **超越基线智能体** | Search-o1 / OctoTools / CheatSheet | o3-mini-medium 下 Xolver(+) 领先最佳基线 **+12.7**（AIME'25）、**+13.5**（LCB） | p6（§3.2） |
| **episodic 记忆增益**（Xolver(+) vs (−)） | 静态记忆 | 平均 **+3.5 分**；最大 **+7.7**（o3-mini-medium，LiveCodeBench） | p7（§3.2） |
| **检索策略消融** | No / Self / External | AIME'25(o3-m-m)：73.8→80.2→**91.6**；QWQ-32B：71.5→76.3→**81.4**；LCB(o3-m-m)：72.4→79.1→**90.6**；QWQ-32B：68.7→76.2→**84.2** | Fig.5 p8；**External > Self > No** 一致 |
| **组件消融**（Math Avg / LCB 掉分） | 完整 Xolver | **Multi-iteration 与 Multi-Agent 掉分最大**，其次 Judge Agent，再次 External Retrieval；Verifier 对数学关键、不可去 | Fig.3 p8；**读图，具体数值须人工核对** |
| **智能体数 × 迭代数** | 预算受控 | 迭代深度重要；智能体数**超过 3** 后仍有 **>4%** 涌现增益 | p8（Fig.4） |
| **self-judge vs Judge Agent** | 外部 Judge | self-judge 偏袒自身：编码 **−9.9%**、数学 **−3.88%** | p9（§4） |
| **成本** | Search-o1 | Xolver token 用量约 **1.5×** Search-o1；token 复杂度 `O(mI)`，**运行时长复杂度 `O(I)`**（智能体并行）；约 **25%** token 用于真正推理 | p9–10（Fig.8、§4） |
| **方差** | 多轮 | AIME'24(16 runs)/AIME'25(32)/LCB(32)：STD **≈1%**（Table 4 p35）；打乱题目顺序 5 runs STD **≈1**（Table 5 p35） | App. D.2–D.3 p34–35 |
| **细粒度** | CheatSheet / CodeSim | Math-500 QWQ-32B 各子类 **+7.5~+11.0**；LCB Hard(o3-m-m) **+32.3** | Fig.6 p9、Fig.7 p9 |
| **误差分析** | — | 总错率 AIME'25：o3-m-m 8.4% / QWQ-32B 18.6%；LCB：9.4% / 15.8%；失败含 wrong reasoning/calc、TLE、RTE、syntax | Fig.9 p10 |
| **推理模式动态** | OpenCodeReasoning | Xolver 随难度**提升 self-evaluation 与 new approach**；失败时增加 subgoal setup / rephrasing（t 检验 p<0.05） | Table 2 p10–11、Table 3 p34 |

### 2.6 论文自陈局限与边界条件
- **计算效率**（Conclusion p12）：「faces limitations in computational efficiency, with substantially higher token consumption than traditional approaches」——约 1.5× Search-o1（p10）。
- **依赖骨架质量**（p12）：「remains dependent on the quality of backbone LLMs」——性能随骨架强弱**单调变化**（p7）。
- **评测口径的软肋**（§3.1 p6）：
  - **GSM8K 与 MATH-500 用单次贪心解码**，无多次重复；只有 AIME'24/25 与 LiveCodeBench 做 16/32 runs。
  - **数学准确率用 GPT-4o 判定**；**编码用例通过由 LLM 模拟执行（CodeSim）判定**，而非真实编译器。
- **假设依赖**：全程挂在**前沿 LLM**（o3-mini medium/high、QWQ-32B）之上；Planner/Judge/Verifier/自检索/模式标注全由 LLM 承担（App. A p19–20）。
- **明确不适用的情形**：**未提及**任何生存、物理、非语言域；仅数学与编码两个符号域（p12 未来工作才提「diverse reasoning domains beyond mathematics and programming」）。
- **无独立 Limitations 节**：限制散见于 Conclusion 与各消融段落。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 面向数学/编码 QA 的多智能体推理框架；无生存信号、无淘汰-繁衍闭环；控制回路全是 LLM 提示与自然语言反馈（p3–4、Fig.2） | 只搬「双记忆分层」与「跨题累积回路」，**不搬**其多智能体组织与 Judge 回路；SSEA 控制环不接语言 |
| **C2** 自然语言只作观察员接口 | **✗（强冲突）** | 经验表示 `(q',T',R')`、反馈 `T_S`、角色提示、答案抽取全是英文文本；检索用 BM25 文本匹配或 LLM 自采样；注入即 prompt 拼接（§2.2 p4–5、App. A p19–20） | **必须换载体**：`D_E/D_S` 的字段骨架可保留为结构化槽位，语言 payload 换非语言结构张量；语言只在慢环编译/日志面 |
| **C3** 权重/记忆/技能三分离 | **◐（挑战被标题夸大）** | 论文自陈 **training-free**（p1、p12），**未把经验写入权重**——所谓「内部参数记忆」是**冻结的预训练权重**，经自采样访问（§2.2 p5）。故**不存在「经验同时进权重与外部库」**；但接口上把权重当记忆源，**模糊了「来源/生命周期」**（`R(D_E)` 一个算子内合并外部语料与参数采样）；**技能**完全未分离（经验停在 workflow 文本） | **SSEA 应只保留外部通道为唯一可写通道**；参数通道降为**只读冻结 L1 先验**（合 C8）；`R(D_E)` 拆成两个算子（外部检索 / 冻结先验读取），不合并；workflow 经验须走 PSN 契约归 ΔS |
| **C4** 低算力低带宽 | **◐** | token 复杂度 `O(mI)`、用量 ≈**1.5×** Search-o1、`m=3,I=2`；多智能体 + 多迭代**越加越贵**（Fig.4 p8）；但**运行时长 `O(I)`**（并行），且优于 self-consistency 的 32–64 次生成、优于 CheatSheet 的 `O(n²)` 记忆更新（p9–10） | 检索/累积件可低配移植；多智能体并行与 Judge 回路须换小模型或离线批处理；`D_S` 定长 `|D_S|=m` 已是防膨胀的正面样本 |
| **C5** 精准回忆历史 | **◐** | `D_E` 是**可写、可检索、跨题持久**的精确经历库（`D_E ← D_E ∪ (q,T,R)`，p5）——合 C5；但 `D_S` **定长 top-m、按分数替换**，旧条目被覆盖（有损）；且无显式遗忘/合并/回指机制 | 取 `D_E` 的「精确经历外置」形态作 ΔM 主库；`D_S` 的定长替换须改为**合法性门 + 回指指针**，防「工作记忆覆盖精确经历」 |
| **C6** 可自主修改自身 | **◐** | 可自主修改**自身记忆**（`D_E` 追加、`D_S` top-m 替换，§2.2 p5），**不改代码/权重**；属 ΔM 自修改 | 映射为慢环 ΔM 提案；代码/权重自修改仍由 SSEA 四权框架管 |
| **C7** 可保存/恢复/变异/继承 | **◐** | `D_E` 持久并可**运行中增量增长**（近似「同一机体跨任务累积」）；但**无变异、无选择、无繁衍闭环**，亦无跨个体继承 | 只取「增量累积 + 持久」思想；GenePackage 的变异/选择/淘汰仍须自建（见 GEA 卡片方案） |
| **C8** 给基因先验，不给知识语料 | **◐（方向支持）** | **Fig.5**：冻结参数记忆（self-retrieval）本身携带**可迁移的解题结构**（AIME'25 73.8→80.2、LCB 72.4→79.1），但**弱于外部经验**（→91.6/90.6）——恰证「参数里放的是**结构性先验**，具体知识应放外部」 | **判定**：SSEA 可让权重承载**结构性先验**（自检索通道），但**可写经验只进外部库**；本篇未做「结构 vs 情节」内容消融，**不足以单独证明 C8 跨代条款**，仅方向性支持 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（部分·最硬）** | **合规面**：编码的 `s∈{0..N_test}` 是**环境事实**（用例通过数）✓；Verifier 只做答案抽取/格式，不打分 ✓。**违规面**：数学 `s∈[0,1]` 是 **LLM 估计的正确概率（外部评分）✗**；`D_S ← TopK(..., key=score)` 是**按分数排序选择 ✗**；Judge Agent 是**外部 critic**（self-judge 更差，−9.9%/−3.88%，p9）✗ | **降级**：`s` 只保留**环境侧事实**（编码用例通过数、数学→改为环境淘汰结果）；`D_S` 的 top-m 改为**合法性/一致性门**（cf. Agent KB disagreement gate）而非分数排序；Judge 的自然语言批判换成**沿轨迹的成败事实**（cf. PSN REFLECT） |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子（BM25、冻结 LLM、Python 均借用）；创新在信息流（双记忆、多智能体回路，L2）、经验累积（L3）、跨题持久库（L4） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；BM25、冻结 LLM、Python 解释器、LDB 调试器均为借用件 | 符合借用立场 |
| **L2 信息流层** | **双记忆架构**（`D_E` 长期 + `D_S` 单题定长）、`BUILD CONTEXT` 的两级上下文构造、Judge 反馈回路、Planner 过生成-选择 | **高**：直接给「长期库 + 工作记忆 + 反馈」的信息流骨架 |
| **L3 学习层** | **运行中跨题 episodic 写入**（Xolver(+) +3.5/+7.7）、迭代精化、收敛判据、失败后 rephrasing/subgoal 恢复 | **中高**：给慢环「增量巩固」的回路形状；评分件须降级 |
| **L4 演化层** | `D_E` 持久并跨题增长——近似「同一机体跨任务累积」；**无变异/选择/繁衍** | **中低**：提供「累积」参照，非演化闭环 |

### 3.3 模块映射（含**多智能体→单个体 + 多层**的降维方案）
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **Planner Agent `P`（过生成 M>m 角色再选 m）** | **降维**：SSEA 无多智能体——「角色」映射为**慢环的评审视角/模块提案**（如不同 ΔM/ΔS 提案者），「过生成-选择」映射为慢环**提案多、留少**的候选生成（选择须改合法性门，去 C9 排序） |
| **Dynamic Agents `A`（m 个专家角色）** | **降维**：映射为 SSEA **单个体内的多层结构**——不同 L2 子模块/头部（如感知层 vs 规划层）在同一快照上并行产生候选，取代「多智能体」；**不引入多 LLM 实例** |
| **`D_S` 中间共享记忆（定长 top-m）** | SSEA 慢环**单题工作记忆/候选池**（现有 `retrieve` 的候选集）；定长 `|D_S|=m` → 睡眠期**有界缓冲**（合 C4）；**top-m-by-score → 合法性门**（去 C9） |
| **`D_E` 长期 episodic 库** | SSEA **ΔM 记忆库**（现有外部存储）；`{(q',T',R')}` schema 骨架可借，语言 payload 换结构张量 |
| **运行中 episodic 写入 `D_E ← D_E ∪ (q,T,R)`** | SSEA **慢环增量巩固**（睡眠期把本轮经历写入 ΔM）；直接服务「记忆检索命中率 0.5164」的存量积累 |
| **自检索 `∼LLM_j(q)`（冻结参数）** | SSEA **只读冻结 L1 先验通道**（不做可写记忆）；对应 C8「结构性先验在权重」 |
| **Judge Agent `J`（标量 `s`）** | **不采用**（C9）；只取「需独立于自评的第三方信号」这一**结构洞察**（self-judge 更差，p9）——SSEA 用**环境淘汰信号**充当该第三方 |
| **Verifier Agent `V`（答案抽取/格式 + LDB 调试）** | 映射为 SSEA 慢环**产物校验/格式门**（四级验证门第一级）与**沙盒执行反馈** |
| **Tools `T`（Python）** | SSEA 沙盒工具面（若引入）；注意论文自陈**工具与推理解耦**（p10）——SSEA 应把工具绑定进控制环而非旁挂 |
| **收敛判据 `CONVERGED`（全满分/全过用例）** | 慢环**停机判据**参照；但须换成**合法性/淘汰口径**而非满分（去 C9） |
| **成本台账（Fig.8 `O(mI)`/`O(I)`、1.5×）** | **睡眠期计算预算**标定的成本参照 |
| **推理模式动态（Table 2：self-eval 随难度升、失败后 rephrasing）** | 慢环**自评信号设计**的观察依据（非语言化后作内在驱动形状） |

### 3.4 债务与验收实验对应
- **记忆检索命中率 0.5164**：**间接回应**。「运行中增量巩固」+「长期库 × 工作记忆分层」为命中率提供**经验积累侧**的改进方向（与 Agent KB 的检索融合侧互补）。
- **记忆门「开得准不准」的选择性缺失**：本篇的 Judge 打分**恰是反例**（C9 违规）——只能借其「独立于自评的第三方信号」洞察，不能借其打分；该债仍由 Agent KB disagreement gate 主答。
- **`retrieve` 键收窄**：本篇只用**单路 BM25**（或自检索回退），**弱于** Agent KB 的混合双通道；**不回应**，该债仍由 Agent KB 主答。
- **睡眠期计算预算未定义**：**部分回应**——Fig.8 给出 `O(mI)`/`O(I)` 复杂度与 ≈1.5× Search-o1 的 token 口径，可作预算标定参照。
- **技能表示够不够（0/33 后仍未答）**：**不回应**——经验停在自然语言 workflow 层，无技能契约；该债仍由 **PSN** 主答。
- **Gene Manager 缺失**：本篇是 ΔM 而非 GenePackage，**不直接回应**；其「累积库」与 **GEA** 互补。
- 服务**记忆累积侧 / 慢环增量巩固**实验（命中率 + 睡眠期写入）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **双记忆分层**：长期 episodic 库 `D_E` × 单题定长工作记忆 `D_S` | 思想/表示 | 改造移植 | ΔM 库 + 慢环工作记忆 | 长短期经验生命周期混置；缓冲无界增长 | 高 |
| 2 | **运行中跨题 episodic 写入**（Xolver(+) vs (−) 平均 +3.5、编码 +7.7） | 算法/协议 | 改造移植 | 慢环增量巩固 | 记忆检索命中率 0.5164（存量不足） | 高 |
| 3 | **整体经验维度清单**（检索/共享记忆/工具/协作/自评精化/验证/跨题传播，7 项） | 思想 | 仅借思想 | 经验来源分类 | 经验维度遗漏（SSEA 目前偏记忆/技能） | 中高 |
| 4 | **External > Self > No Retrieval** 的一致证据（Fig.5） | 证据 | 仅借思想 | C3/C8 裁决依据 | 判定「可写经验只进外部库，参数只读」 | 高 |
| 5 | **组件消融优先级**（Multi-iteration/Multi-Agent 最大，Judge 次之，Verifier 数学关键） | 证据/工程 | 直接引用 | 慢环资源分配 | 睡眠期预算优先级 | 中（读图，须核对） |
| 6 | **定长工作记忆 `|D_S|=m` 的 top-m 替换** | 表示 | 改造移植（**去 score 排序**） | 慢环候选池 | 缓冲不无界增长（合 C4） | 中高 |
| 7 | **智能体多样性 × 迭代深度互补**（>3 后仍有 >4% 涌现增益） | 证据/思想 | 仅借思想 | 单个体多层结构设计 | 「多层结构是否值得」的设计依据 | 中 |
| 8 | **成本台账**（`O(mI)`/`O(I)`、≈1.5× Search-o1、25% 用于推理） | 工程 | 直接引用 | 睡眠期预算 | 预算未定义 | 中 |
| 9 | **推理模式动态**（self-eval 随难度升、失败后 rephrasing/subgoal 恢复） | 观察/证据 | 仅借思想 | 慢环自评信号设计 | 自评信号的形状 | 中 |
| 10 | **多轮方差 + 打乱顺序统计**（STD≈1%，Table 4–5） | 基准/协议 | 直接引用 | 验收实验判据形状 | 判据需报方差与顺序鲁棒性 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 的 ✗/◐）：
  - **C2 ✗（最硬）**：经验/反馈/检索/注入全走自然语言。**改造方向**：只留结构化骨架（`(q',T',R')`→结构化槽位），语言 payload 换非语言结构张量。
  - **C9 ✗（部分·最硬）**：数学 `s∈[0,1]` 为 LLM 评分、`D_S` top-m 按 score 排序、Judge 为外部 critic。**改造方向**：`s` 只留环境事实；top-m→合法性门；critic→轨迹成败事实。
  - **C1 ✗**：无生存语义。**改造方向**：仅作 ΔM/慢环供应商，不改 SSEA 控制环组织。
  - **C3 ◐**：`R(D_E)` 在**一个算子内合并**外部语料与参数采样，模糊来源边界。**改造方向**：拆成两个算子，参数通道**只读**。
  - **C4 ◐**：`O(mI)` token 与多智能体工程面偏重。**改造方向**：降维到单个体多层、离线批处理。
- **隐含假设与失效条件**：
  - 假设**经验抽取/判定/自检索的质量由前沿 LLM 保证**——小模型下收益打折（cf. PSN 弱模型噪声证据）。
  - 假设**数学答案可由 GPT-4o 可靠判分**、**编码用例可由 LLM 模拟执行判定**（CodeSim）——两者都是**LLM 代理的评估**，非真实环境；SSEA 的淘汰信号归环境，**口径不可直接照搬**。
  - 假设「跨题累积 = 同一机体跨任务」——`D_E` 是**单一共享实例**，无谱系隔离、无变异选择；SSEA 的 C7/C8 命题（跨**代**）在此**未被检验**。
- **算力 / 带宽 / 工程代价**：token ≈1.5× Search-o1，`m=3,I=2`；多智能体 + Judge + Verifier + 外部调试器（LDB）是显著工程面；9M-token 外部语料的一次性构建成本未单列（**未提及**精确 $ 值）。
- **搬运后的可能退化模式**：
  - 把 Judge 标量分当**质量门**用 → 退化为外部评分（违 C9），且自评偏袒（−9.9%）会**锁死**改进。
  - `D_S` 定长 top-m 替换**覆盖** `D_E` 精确经历 → 复现能力下降（「工作记忆取代精确」风险）。
  - 双记忆分层若**不拆算子**，参数通道被当可写记忆 → 越过 C3/C8 边界，经验进权重（膨胀）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可检索经验库 + 冻结骨架模型 + 环境淘汰信号 | SSEA 已有记忆库与验收框架雏形；本篇的 Judge 打分须先换淘汰信号 |
| 直接同族 | **Memento（A/P1）** | 同为「冻结 LLM + 案例库读写 + 可学习检索 μ」；Memento 给记忆侧主干（可学习检索），Xolver 给**双记忆分层 + 跨题累积**——Xolver 是 Memento 的「多智能体 + 工作记忆」外延 |
| 直接同族 | **Agent KB（B/P1）** | **Agent KB 卡片 §6.1 已把 Xolver 列为「经验可迁移阵营」对照**。Agent KB 走**跨框架扁平 schema + 混合双通道检索 + disagreement gate**；Xolver 走**多智能体 + 双记忆 + BM25/自检索**。二者同属记忆侧但**检索侧相反**：Agent KB 强在融合检索，Xolver 强在**分层记忆与跨题累积** |
| 互补（最紧·累积侧） | **FLEX（B/P1）** | FLEX 管**写入组织**（golden/warning 分层 + updater 三分支）；Xolver 给**双记忆分层 + 运行中跨题写入**。写入组织 × 增量累积 = 完整记忆生命周期 |
| 互补（最紧·工作记忆侧） | **LightMem（B/P1）** | LightMem 给摄入压缩 + 主题分段 + **睡眠期离线巩固**；Xolver 的「运行中跨题写入」可作其**在线版**对照——两者合成「在线累积 × 离线巩固」 |
| 互补（失败利用） | **ReasoningBank（B/P1）** | 二者都从经验中提炼可复用件；ReasoningBank 蒸馏**成功+失败**轨迹为推理记忆、给「少而精、k=1」注入预算；Xolver 给**成功轨迹的双记忆分层与跨题累积**。可拼「分层累积 + 双路蒸馏」 |
| 互补（技能侧） | **PSN（A/P1）** | Xolver 停在自然语言 workflow；PSN 给技能契约 + REFLECT + 成熟度门控 + 回滚。**Xolver 的 workflow 经验成熟 → 经 PSN 结晶为带契约技能** |
| 对照（共享一族·推理期） | **G-Memory（arXiv:2506.07398，本库未建卡）** | G-Memory 用**三层图**（insight/query/interaction）做多智能体记忆共享，走**图遍历高层洞见**；Xolver 走**扁平 episodic 库 + 定长工作记忆**。层级相反，同为推理期共享 |
| 对照（演化期共享） | **Group-Evolving Agents / GEA（B/P1）** | GEA 是**演化期结构共享**（跨个体 patch）；Xolver 是**推理期经验共享**（同机体跨题）。**SSEA 只取 GEA 侧**（结构期合法），Xolver 侧须改造为慢环增量巩固 |
| 对照（协同演化一族） | **CoMAS（本库未建卡，机制细节未核实）** | CoMAS 走**多智能体协同演化**（据其摘要页为经交互奖励共演）；Xolver 为 **training-free、不改权重**。二者都做多智能体经验，但 CoMAS 的交互奖励属**外部评分**（C9 冲突更重），Xolver 的 training-free 反使其**未越 C3 写权重边界**——**须先补建卡片核实机制** |
| 替代 | 单层平铺示范库 / 单题工作记忆 | 双记忆分层（长期库 × 定长工作记忆）替代单层记忆 |
| 风险 | **Misevolve（A/P1）** | 「运行中自动写库」是**新污染面**（错误经验即时入库、跨题扩散）；须用四路径威胁模型与红队清单验收 |
| 风险 | **RAGEN（B/P1）** | 若未来以训练组件替代 LLM Judge/自检索，用 Echo Trap 诊断防坍缩 |

### 6.2 推荐组合方案
**方案 A（推荐，服务「记忆累积侧 + 睡眠期预算」）：双记忆分层 + 增量巩固**
- **组合**：Xolver（双记忆分层 + 运行中跨题写入）× **FLEX**（分层写入）× **LightMem**（睡眠期离线巩固）
- **接口形态**：SSEA ΔM 采用「长期库 `D_E` × 慢环工作记忆 `D_S`」两层；`D_S` 定长（合 C4），替换条件由 **score 排序改为合法性门**；慢环睡眠期把 `D_S` 中经门控的经历写回 `D_E`（在线累积）并由 LightMem 做离线压缩巩固。
- **组合后新增能力**：记忆既有**在线增量**（提命中率）又有**离线巩固**（防膨胀），长短期生命周期分离。
- **新增风险**：`D_S` 覆盖精确经历；错误经验即时入库（须 Misevolve 红队验收）。

**方案 B：workflow 经验 → 技能结晶（Xolver × PSN × SEDM）**
- **组合**：Xolver 的 `D_E` workflow 经验 → **PSN** CODEGEN 蒸馏为带契约技能 → **SEDM** A/B 准入验证
- **接口形态**：`D_E` 的 `(q',T',R')` 作 PSN 输入语料；成熟后固化为 ΔS；准入由 SEDM 把关。
- **组合后新增能力**：把「可迁移的抽象 workflow」升格为**可继承的结构性技能**（合 C8 判定）。
- **新增风险**：workflow 与技能契约的粒度对齐未验证。

**方案 C（C3 边界实验）：外部通道 vs 参数通道（Xolver × Agent KB）**
- 见 §8 最小验证实验的「C3 边界」旁证。

### 6.3 本篇在组合中的典型角色
- **记忆累积侧的「双记忆分层器 + 跨题增量写入供应商」**：它不提供技能、不提供基因、不提供生存信号；它提供的是「**经验库该怎么按生命周期分成长期库与工作记忆、经验该怎么在运行中增量累积、哪些经验维度不能遗漏**」。检索融合接 Agent KB，写入组织接 FLEX，离线巩固接 LightMem，技能结晶接 PSN，准入接 SEDM，演化共享接 GEA。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击「记忆命中率 / 睡眠期预算」两条活债，并给 C3 边界与 C8 方向的实证（实测：Fig.5、Fig.8、Table 1）；扣 1：无生存语义、无技能/基因（实测） |
| 立场兼容性 | **2** | **C1 ✗ + C2 ✗ + C9 ✗（部分）** 三条硬冲突，C3/C4/C5 有张力（实测：p4–5、p9–10、App. A）；但核心「双记忆分层/累积」改造路径明确，改造后可升至 4（推断） |
| 可搬运性 | **3** | 双记忆、累积回路为架构级、与具体框架解耦；但**多智能体须降维到单个体多层**、语言载体须重写、评分件须降级（实测/推断） |
| 证据强度 | **3** | 5 基准、跨 3+ 骨架、系统消融、误差分析、多轮方差（实测）——广度强；但 **GSM8K/Math-500 单次贪心**、**编码用 LLM 模拟执行判分**、数学用 GPT-4o 判分（实测） |
| 组合价值 | **4** | 与 Memento / Agent KB / FLEX / LightMem / ReasoningBank / PSN / GEA / G-Memory / CoMAS 多条边成立，并补上 Agent KB 卡片遗留的「Xolver 未建卡」缺口（推断，有实测支撑） |
| 落地成本 | **3** | 反向口径：**training-free 无训练成本**（实测）；扣分在 token ≈1.5×、多智能体 + Judge + Verifier + LDB 工程面、语言载体重写（实测/推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：**双记忆分层 + 运行中跨题写入 + 整体经验维度清单 + 外部>自检索证据 + 消融优先级**五件干净可用，服务记忆累积侧与 C3 边界裁决；但**不采用**其 LLM Judge 标量评分与 TopK 排序（C9）、自然语言载体（C2）、多智能体 LLM 组织与 self-judge（C1/C9）。**不采用**整机（无生存、无基因、无技能）。
- **优先级：P2** —— 理由：记忆侧资产与 Memento / FLEX / Agent KB / ReasoningBank **高度重叠**，其检索侧还弱于 Agent KB；净增量只在**双记忆分层**与**运行中跨题累积**两点，故排队于 P1 的记忆/技能主干之后。若「记忆命中率」实验需要在线累积件，可临时提至 P1。
- **建议动作**：
  1. **ΔM 双层结构落地**：`D_E`（长期、可写、跨任务）× `D_S`（慢环工作记忆、定长、有界）。
  2. **`D_S` 替换条件去 C9**：`TopK-by-score` → **合法性门**（可复用 Agent KB disagreement gate）；`D_S` 保留回指指针到 `D_E` 源经历。
  3. **慢环增量巩固**：睡眠期把经门控的 `D_S` 经历写回 `D_E`，观测检索命中率（当前 0.5164）。
  4. **C3 边界写死**：**外部通道 = 唯一可写经验通道**；参数通道 = **只读冻结 L1 先验**；`R(D_E)` 拆成「外部检索」与「先验读取」两个算子。
  5. **预算标定**：用 Fig.8 的 `O(mI)`/`O(I)` 与 ≈1.5× 口径给睡眠期预算定档。
  6. **降维说明入档**：把「多智能体角色 → 单个体多层结构」的映射写进设计文档，防后人误引多智能体组织。
- **最小验证实验（记忆累积侧 + C3 边界）**：
  - **双臂 / 消融设置**（同一环境、同一 ΔM、≥8 seed）：
    - **A 臂 静态记忆**（现状）：慢环内不写回，`D_E` 冻结（≈ Xolver(−)）。
    - **B 臂 增量巩固**：慢环内把经合法性门的经历写回 `D_E`（≈ Xolver(+)），`D_S` 定长。
    - **C 臂（证伪对照）无门直写**：写回不加合法性门（验证门是否真防污染）。
  - **判据（分档，先看分母）**：
    1. **机制计数（分母）**：`D_E` 写入数 / `D_S` 替换数 / 合法性门放行-拒绝数。**若 C 臂门控缺失导致 `D_E` 污染率激增，说明门必需；若 B 臂写入数 ≈0，说明门过严、后两档无意义。**
    2. **行为差**：记忆检索命中率（当前 **0.5164**）、任务完成率、睡眠期 token 消耗。
    3. **淘汰结果（环境侧，模型外）**：存活率 / 淘汰率（危险回避率 0.9814 **已饱和**，不作主判据）。
  - **预期**：B 臂命中率 > A 臂（对照 Xolver(+) 平均 +3.5、编码 +7.7，p7）；C 臂出现错误经验扩散、命中率虚高但淘汰率恶化。**若 B ≤ A**，或 **C = B**（门无贡献），则降级为 **C 思想启发**。
  - **C3 边界旁证（可选）**：对同一经验集，比较「只写外部库（只读参数）」vs「外部库 + 参数通道」，若后者无增益甚至有害，即支持「SSEA 只保留外部可写通道」。
- 若 **E 不采用**：不适用。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的 `D_S`（慢环工作记忆）**定长 `|D_S|=m` 的 m 取多少**？以何为界（候选数 / 内存预算 / 时延）？
  2. 合法性门在**非语言结构表示**上的判据与阈值如何定义（`D_S` 替换与 `D_E` 写回共用一门还是两门）？
  3. SSEA 是否具备「跨个体」实体（本篇 cross-problem = 同机体跨任务）？若无，`D_E` 累积的对象是谁——与 GEA 卡片同题。
- **需补查的文献或资料**：
  1. **CoMAS、G-Memory（arXiv:2506.07398）本库均未建卡**，§6.1 对其描述依据各自摘要页 / 二手索引，**机制细节未核实**；若要纳入正式组合，须先补建卡片。
  2. 本篇引用的 **CheatSheet（Suzgun et al. 2025）、CodeSim（Islam et al. 2025）** 为直接对照基线，其机制与判分口径需核对。
- **需人工核对的公式 / 实现**：
  1. **Fig.3（p8）组件消融的各柱数值**（如 7.25 / 23.70 / 7.58 / 16.40 …）在 PDF 文本层中**与组件名对应关系不可靠**，本卡片仅记定性结论「Multi-iteration 与 Multi-Agent 掉分最大，Judge 次之，Verifier 数学关键」；引用具体值须人工看图。
  2. **Fig.5（p8）四组检索对比数值**（73.8/80.2/91.6 等）为人工读图，须核对是否与正文口径一致。
  3. 主结果中 **GSM8K / Math-500 为单次贪心解码**、**数学准确率由 GPT-4o 判定**、**编码用例由 LLM 模拟执行（CodeSim）判定**——引用时须注明口径，不得当独立重复实验。
  4. `D_S` 的 `TopK` 键 `key(e)=s(e)` 与收敛判据「全满分/全过用例」的**实现细节**须核对（Algorithm 1 伪码较简）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we introduce Xolver—a **training-free, multi-agent reasoning framework** that equips a black-box LLM with a persistent, evolving memory of holistic experience.” | p1（Abstract） |
| “Xolver integrates diverse experience modalities, including **external and self-retrieval, tool use, collaborative agent interactions, agent-driven evaluation, and iterative reasoning refinement**.” | p1（Abstract） |
| 问题陈述：“current large language models (LLMs) typically operate **in isolation**—treating each problem as an independent attempt, without accumulating or integrating experiential knowledge.” | p1（Abstract） |
| 双记忆：`D_E`（episodic long-term，存 past problems/solutions/traces）与 `D_S`（intermediate dynamic shared memory，推理中演化、保留高质量轨迹） | p3（§2） |
| 两级上下文：`C_0^j = {q} ∪ R(D_E)`；`C_i^j = {q} ∪ {T_{i-1}^j, R_{i-1}^j} ∪ D_S`（i≥1） | p4（§2.1，BUILD CONTEXT） |
| Judge 输出：`S=(T_S,s)`，`T_S` 自然语言解释、`s` 标量分；数学 `s∈[0,1]`（LLM 估计正确概率）、编码 `s∈{0..N_test}` | p4（§2.1） |
| “To avoid compiler interaction latency … test case outcomes are determined by **simulating execution through LLM prompting** within the judge agent `J`, following the **CodeSim protocol**.” | p4（§2.1） |
| 两种 episodic 记忆：外部语料 `D_E^ext={(q',T',R')}` 与**内部参数记忆**（“the internal parametric memory encoded in the **weights** of the agent-specific language model `LLM_j`”） | p4（§2.2） |
| 检索：外部 `R(D_E)={(q'_k,T'_k,R'_k)} ← Retrieve_j(q, D_E^ext)`（BM25）；否则回退自检索 `∼ LLM_j(q)` | p5（§2.2） |
| 写回：`D_E^ext ← D_E^ext ∪ (q,T,R)`，取 `D_S` 中 top-ranked `(T,R,S,a)` | p5（§2.2，UPDATE EPISODIC MEMORY） |
| 共享记忆定长：`|D_S|=m`；`D_S ← TopK(D_S ∪ {τ_i}, m; key(e)=s(e))` | p5（§2.2，UPDATE SHARED MEMORY） |
| Algorithm 1：三阶段（Planner 建队 → I 轮迭代 + 收敛检测 → Verifier 出答案 + 写 `D_E`） | p5（§2.3） |
| 默认超参：`temperature=0.2`、`m=3` 智能体、`I=2` 迭代；检索 `k=5`；收敛=全满分/全过用例 | p6（§3.1） |
| 评测：GSM8K/MATH-500 **单次贪心**；AIME'24 **16 runs**、AIME'25 与 LiveCodeBench **32 runs**，STD≈1% | p6（§3.1） |
| 主结果 o3-mini-high Xolver(+): GSM8K **98.1**、AIME'24 **94.4**、AIME'25 **93.7**、Math-500 **99.8**、LiveCodeBench **91.6** | Table 1 p7 |
| o3-mini-medium：LongCoT 75.8→Xolver(+) **93.8**（AIME'24）；66.3→**87.3**（LCB） | Table 1 p7、p6（§3.2） |
| “the cross-problem variant Xolver (+) consistently outperforms … On average, episodic memory integration yields a **+3.5 point** improvement … largest gain is **+7.7 points** with o3-mini-medium on coding.” | p7（§3.2） |
| 消融（Fig.3）：“most significant degradation observed when removing **Multi-iteration and Multi-Agent** followed by **Judge Agent** … Verifier is critical for math tasks and cannot be removed.” | p8（§4） |
| 检索消融（Fig.5）：**External > Self > No Retrieval** 在 AIME'25 与 LiveCodeBench、两种骨架上一致；AIME'25(o3-m-m) 73.8→80.2→**91.6** | p8（§4，Fig.5） |
| 预算受控：固定「智能体数 × 迭代数」后，智能体数**超过 3** 仍有 **>4%** 涌现增益 | p8（§4，Fig.4） |
| self-judge 更差：“**9.9% decrease in coding** tasks and **3.88% decrease in math** tasks, on average.” | p9（§4） |
| 成本：token 复杂度 `O(mI)`、运行时长 `O(I)`；“approximately **1.5×** that of Search-o1”；约 **25%** token 用于真正推理 | p9–10（§4，Fig.8） |
| 工具解耦：“such calculation errors often occur when agents choose **not to invoke these tools**—highlighting that **tool usage remains decoupled from the model’s core reasoning process**.” | p10（§4） |
| 推理模式：Xolver 随难度**提升 self-evaluation 与 new approach**；失败解增加 subgoal setup / rephrasing（p<0.05） | Table 2 p10–11、Table 3 p34 |
| 自陈局限：“Xolver faces limitations in **computational efficiency, with substantially higher token consumption** than traditional approaches, and **remains dependent on the quality of backbone LLMs**.” | p12（Conclusion） |
| 外部语料：编码 = GitHub（cp-algorithms）**9M-token** C++ 题解；数学 = OpenMathReason 数据集 | p6（§3.1）、App. C p33 |
| 方差：AIME'24(16 runs) 87.2±1.2 / 93.8±0.3；AIME'25(32) 85.1±1.3 / 89.4±0.7；LCB(32) 79.6±1.0 / 87.3±0.4（o3-mini-medium） | Table 4 p35 |
| 打乱顺序：5 runs、STD≈1（“a strong sign on the robustness of the framework”） | Table 5 p35 |
