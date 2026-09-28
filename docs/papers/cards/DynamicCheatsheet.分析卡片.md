# 论文分析卡片 · Dynamic Cheatsheet（DC）

> 纪律：任何结论若无法回溯到 C1–C10 即视为偏离 SSEA 立场。论文未提及的内容一律标
> 「未提及」。关键数字带出处（表号/图号/节号/页码），区分「实测」与「推断」。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-04-10 Dynamic Cheatsheet Test-Time Learning with Adaptive Memory.pdf`（22 页） |
| 标题 | **Dynamic Cheatsheet: Test-Time Learning with Adaptive Memory** |
| 作者 / 机构 | Mirac Suzgun, Mert Yuksekgonul, Federico Bianchi, Dan Jurafsky, James Zou；Stanford University + Together AI（p1） |
| 发表时间 / 出处 | arXiv:2504.07952v1 [cs.LG]，2025-04-10 |
| 论文链接 | arXiv:2504.07952 |
| 代码链接 | https://github.com/suzgunmirac/dynamic-cheatsheet（p1 脚注） |
| 标签 | 测试时学习 / 在线学习 · 参数无关适应（non-parametric memory）· 记忆策展（curation）· black-box LLM · 策略与代码片段复用 |
| **应用裁决** | **B 零件采用**（不搬框架，只搬「备忘单的条目 schema + 有界活文档 + 保留/修订/淘汰三分支 + 溯源与使用计数」） |
| 优先级 | **P2**（条件性升 P1：当「慢环 ΔM 产出物形态 / 睡眠期预算」立项时） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：给黑盒 LLM 配一块**持久、自我策展、随推理演化的外部文本记忆（cheatsheet）**，
  只存简洁可迁移的策略 / 代码片段 / 元级洞见而非整份对话，从而在**完全不动权重、不需要
  真值标签或人类反馈**的前提下实现测试时学习——GPT-4o 在 Game of 24 上由 10% 升到 99%，
  Claude 3.5 Sonnet 在 AIME 2024 上由 23.3% 升到 50.0%（Table 1, p6；摘要 p1）。
- **对 SSEA 的意义**：它是「**C3（不动权重也能改行为）+ C5（精准回忆）**」的最干净同类物，
  且**与 Memento/MemRL 相比更接近 C9**（明确不使用 ground-truth 与人类反馈）。但 SSEA 的
  `experience_compiler.py` + `memory_system.py`（合并 / 淘汰 / 检索计数）**已是其结构等价物**；
  DC 的净增量只在「备忘单 = 一份有界、带溯源与使用计数、可修订替换的活文档」这一**产出物形态**
  上，而这一形态恰恰是纯语言的（C2 冲突最重）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题

- **问题本身**（p2）：LLM 部署后是固定的，推理时不保留过去的问题、成功与失败，每次都
  *de novo* 重来——「重新推导同一洞见、重犯同一错误」。
- **指出的既有方案缺陷**（p2、p14–15）：
  - **参数化路线**（dynamic evaluation / domain adaptation / test-time training）：要改权重，
    对 GPT-3、Claude 这类黑盒 API「困难乃至完全不可行」（p14）；
  - **传统 RAG**：检索语料在推理前固定、不随经验演化，且**不能从错误中学习、不在先前解法上
    累积**（p15）；
  - **Reflexion / Self-Refine / Self-RAG / TextGrad 一族**：用反馈回路或验证机制纠正**单次**
    解法，而 DC 存的是**跨任务可复用**的启发式 / 代码 / 元级洞见，且不需要为每个 batch 或
    scenario 新建训练循环（p14）；
  - **朴素全历史追加（FH）**：上下文膨胀、稀释关键洞见、拖垮检索（p6、p9）。

### 2.2 核心思想（关键 insight）

1. **把「学习」搬出权重，搬进一块会自我策展的外部记忆**：记忆是 non-parametric 的，与推理
   过程同步演化；不要求梯度、兼容黑盒 API（p3 §2 开头）。
2. **两个角色分离：Generator 与 Curator**（p3）：`ỹi = Gen(xi, Mi)`（Eq.1）与
   `Mi+1 = Cur(Mi, xi, ỹi)`（Eq.2）。二者可用同一个模型、以任务无关的不同 prompt 扮演，
   也可分开（p3）。
3. **策展本身就是学习，且策展者拿不到真值**：*Cur does not have access to ground-truth
   labels; so, it has to assess the correctness and efficiency of the solutions by itself*
   （p3）。因此「对/错」不是外部反馈，而是模型自评——这是本篇与 C9 关系的关键事实。
4. **只留「够用且可迁移」的，不留原始流水**：显式抵制 naive in-context 全量追加，防止
   context ballooning（p2、p15）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| # | 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|---|
| 1 | **外部非参数记忆 M_i** | — | 持久、随推理演化的记忆载体；不动模型权重 | §2, p3 |
| 2 | **Generator（Gen）** | (xi, Mi) → ỹi | 记忆条件化生成 | Eq.1, p3 |
| 3 | **Curator（Cur）** | (Mi, xi, ỹi) → Mi+1 | 记忆更新＝学习发生的地方 | Eq.2, p3 |
| 4 | **Cur 的三条判据** | 新答案 → 保留/修订/删除决定 | (i) 有用性与可泛化性：正确或有洞见则**蒸馏**入库；(ii) 已有条目若错误或被更高效策略取代则**修订或删除**；(iii) 全库**合并压缩**、保持清晰紧凑 | §2.1.2 (i)(ii)(iii), p3 |
| 5 | **无真值自评** | 自身输出 → 正确性/效率判断 | 使整条链路不依赖外部评分 | p3 |
| 6 | **Retriever（Retr）** | (xi, 历史输入-输出对, k) → Ri | 按 query 嵌入的**余弦相似**取 top-k；k=3（试过 5/7 增益不显著）；嵌入模型 text-embedding-3-small | Eq.3, p4 及脚注 1/2 |
| 7 | **DC-RS 的时序：先检索 → 先策展 → 再生成** | Ri=Retr(...)；Mi=Cur(Mi−1, xi, Ri)；ỹi=Gen(xi, Mi) | 让当前 query 的洞见在作答前就进入记忆；DC-Cu 无检索、作答后才策展 | Eq.3–5, p4 |
| 8 | **备忘单条目 schema** | — | `<memory_item>` = `<description>`（问题上下文/目的/关键要素，**含溯源 Reference: Q1, Q2, Q6**）+ `<example>`（代码 / 完整解法 / 高效策略）+ `** Count:`（使用次数） | Fig.14 curator prompt, p21 |
| 9 | **四节组织结构** | — | Reusable Code Snippets and Solution Strategies / General Problem-Solving Heuristics / Optimization Techniques & Edge Cases / Specialized Knowledge & Theorems | p21 |
| 10 | **溯源标签（Q14、Q22 等）** | 题目编号 → 条目 | 条目可回溯到产生它的具体经验 | p21 |
| 11 | **使用计数器（Usage Counter）** | 每次「成功使用」→ +1 | 以使用频次排序，高频策略优先于低频策略 | p21 |
| 12 | **写入准入规则** | 候选内容 → 存/不存 | 只保留高价值、可泛化的策略/代码/洞见；**丢弃冗余、琐碎、过于题目特定的细节** | p21 |
| 13 | **替换规则** | 新旧策略 → 保留其一 | *If a better approach than a previously recorded one is found, replace the old version.* | p21 |
| 14 | **有界长度 + 版本号** | — | 备忘单约 **2000–2500 词**，含 `Version:` 字段；显式抵制无界增长 | p21（Cheatsheet Template） |
| 15 | **全量重写语义（双刃）** | 旧备忘单 → 新备忘单 | *once the cheatsheet is updated, any previous content not directly included will be lost*——必须显式拷贝要保留的内容 | p21 N.B. |
| 16 | **空记忆对照臂 DC-∅** | 同一 generator prompt，记忆占位符填 "(empty cheatsheet)" | 隔离「结构化指令」与「记忆本身」的归因（强基线） | §2.3(2), p4 |
| 17 | **另两个对照臂 FH / DR** | 全历史原始追加 / 只检索不策展 | 分别证伪「全量追加」与「只检索不策展」 | §2.3(3)(4), p4 |

### 2.4 关键表示与数据结构

- **记忆＝纯自然语言文本**（非向量、非结构化表）：一份 ~2000–2500 词、带版本号、分四节的
  「活文档」（p21）。
- **条目＝`description + example + Count` 三元组 + 溯源标签**（p21；实例见 Fig.5 p7 的
  `Count: 99`、Fig.6 p7 的 `Count: 20 / 15`，标签如 `Reference: Q1-Q20`）。
- **检索键**：原始 query 经 text-embedding-3-small 映射为向量，余弦相似，top-3（p4 脚注）。
- **更新方式**：Cur 整份重写（不是增量 patch），旧内容不显式复制即丢失（p21）→ 与 SSEA
  `memory_system.replace()` 产副本换旧项的做法**相反**，是一个明确的风险对照。
- **记忆内容演化可度量**：以 word-level LCS 相似度衡量相邻两次记忆的相似度（Fig.11, p18）。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| Game of 24（100 例） | BL 10.0 / DC-∅ 19.0 / DR 6.0 / DC-Cu 93.0 | **DC-RS 99.0** | GPT-4o，准确率（Table 1, p6） |
| Game of 24 | BL 12.0 → DC-Cu 14.0 / DC-RS 14.0 | Claude 3.5 Sonnet 几乎无增益（未内化通用解法） | 同上 |
| AIME 2024（30 题） | BL 23.3 / DC-∅ 36.7 / DR 43.3 | **DC-Cu 50.0**（DC-RS 46.7），+26.7 点 | Claude 3.5 Sonnet（Table 1, p6） |
| AIME 2025（30 题） | BL 6.7 / DC-∅ 23.3 | **DC-Cu 36.7**（+30.0） | 同上 |
| AIME 2020–24（133 题） | BL 6.7 | **DC-RS 40.6** | 同上 |
| AIME 2024 / 2025（GPT-4o） | BL 20.0 / 6.7 | DC-RS 40.0 / 20.0 | 同上 |
| GPQA-Diamond（198 题） | BL 59.6 / DC-∅ 60.1 / DR 63.6 | **DC-RS 68.7（+9.1）**；GPT-4o 仅 57.1→58.1 | Claude（Table 1, p6；§4.2 p6） |
| Math Equation Balancer（250 题） | BL 44.8 / 50.0 | **DC-Cu 100.0（Claude）/ 100.0（GPT-4o）**；DC-RS 97.8 / 99.2 | 同上 |
| MMLU-Pro Physics（采样 250） | BL 74.0 | **DC-RS 82.0（+8.0）**；MMLU-Pro Eng. 61.2→67.6 | Claude（Table 1, p6） |
| 全历史追加对照（AIME 2024/2025） | BL 23.3/6.7（Claude），20.0/6.7（GPT-4o） | **FH 26.7/6.7（Claude），13.3/3.3（GPT-4o，低于基线）** vs DC-Cu 50.0/36.7、DC-RS 40.0/20.0 | Table 2, p7 |
| 多数投票对照（AIME） | BL 23.3 / 6.7 | **MV(BL) 23.3 / 6.7 无增益**；MV(DC-∅) 33.3 vs DC-Cu **50.0 / 36.7** | Claude，Table 4, p9 |
| 小模型：Claude 3.5 Haiku | AIME 2024 BL 10.0 | DC-Cu 36.7；AIME 2025 仅 13.3；GPQA 43.4→49.0 | Table 3, p8 |
| 小模型：GPT-4o-mini | AIME 2024 BL 16.7 | **DC-Cu/DC-RS 均 13.3（低于基线）**；GPQA 34.3→32.3（下降） | Table 3, p8 |
| 推理专用模型 | DeepSeek R1 / o1 | 「minimal or inconsistent improvements」；解法过于冗长 | §5, p9 |
| 推理开销（AIME 2024，Claude） | BL 平均 **370 tokens** | DC-∅ 494 / **DC-RS 1035 / DC-Cu 1831** | 平均生成 token 数，脚注 13, p9 |
| 记忆内容演化 | 相邻记忆的 word-level LCS 相似度 | 前几次迭代后**高度稳定**；DC-Cu 后半段波动略大 | Fig.11, p18 |

> 口径提示（推断）：论文**未声明 seed 数 / 是否多次运行 / 方差**；AIME 子集仅 30 题；
> 测试样本为**顺序序列**且论文自陈收益依赖样本结构相似与排序（§4.6, p8）。上述数字应视为
> 单轮、小样本、顺序敏感的实测值。

### 2.6 论文自陈局限与边界条件

- **假设依赖**：
  - 基座模型必须有足够生成能力——*DC demands a capable foundation model to seed and refine
    the curated knowledge*（p9）；小模型与 R1/ o1 类模型收益极小甚至下降（Table 3, p8；p9）。
  - 收益依赖**测试样本间的结构相似性**与排序（§4.6, p8）。
  - 每个 query 都访问同一块记忆，故**序列结构不利于大规模并行 / batch 推理**（p9）。
- **明确不适用 / 已观察到的失效**：
  - **错误启发式会扩散**：正确与错误回答在嵌入空间聚成簇，*faulty heuristics that slip into
    memory can be equally amplified*（Fig.10, p17；§5, p9）。
  - **长文生成弱于长文理解**：模型常以 “Previous content [...] preserved” 简写代替重写，
    *truncated memory updates can reduce the quality of stored heuristics over time*（p9）；
    论文自提解药是「维护一个结构化的外部数据库，让 LM 引用而不必每次重生成大段文本」（p9）。
  - **检索噪声**：检索质量差时会引入混淆（GPT-4o 在 GPQA 上的偶发下降，p6、p9）。
  - **跨模型迁移记忆**：把大模型的记忆传给小模型，结果**混合**（p9）。
  - 论文自陈工具范围只限于 Python 解释器（§4.4, p7）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | Gen→Cur→M 是**对记忆状态的迭代控制回路**（Eq.1–2, p3），而非一次性生成；但目标函数为答题准确率，无生存/具身/能量 | 把回路对象从「下一题」换为「下一帧的存活」；Cur 的触发改由慢环周期驱动 |
| **C2** 自然语言只作观察员接口 | **✗** | 记忆是**纯文本备忘单**（p21）；Gen 与 Cur 都是 LLM 的 prompt（Fig.13 p20、Fig.14 p21）；备忘单**直接进 prompt 并决定行动**——语言在控制闭环内，且是机制的唯一载体 | **去语言化方案**：条目改为结构化 `{signature, content_ref, provenance[], use_count, version}`，`content_ref` 指向可执行片段/参数指针而非文本；Cur 换成**确定性 updater**（保留/修订/淘汰三分支 + 合并去重），只在观察员侧把结构渲染成文本给人看。**若去语言后「综合泛化」收益消失 → 判定为不可搬运，本篇降为 C（仅思想）** |
| **C3** 权重/记忆/技能三分离 | ◐（权重侧 ✓✓，库内 ✗） | 权重侧强对齐：*without modifying their underlying parameters*（摘要 p1）、*no gradient-based updates are required*（p3）；但**技能（可复用代码片段）与记忆（洞见）混在同一份备忘单**（Fig.5 p7 的 Python solver 与 Fig.6 p7 的启发式同库） | ΔS 与 ΔM 分开编译与存储（SSEA `experience_compiler` 已按 ΔM/ΔS/ΔR/Δθ 分置，保持即可） |
| **C4** 低算力低带宽 | ◐ | 正面：显式长度上限 ~2000–2500 词、**缓冲不无界增长**（p21）；负面：每步全量重读重写，DC-Cu 平均 1831 tokens vs BL 370（≈5×），DC-RS 1035（脚注 13, p9）；且需调用嵌入模型做检索 | 只在**慢环睡眠期**做策展（快环只读不可变快照）；检索键复用 SSEA 已有向量，不新增嵌入调用；条目数硬上限按 C4 预算换算 |
| **C5** 精准回忆历史 | ✓ | 写入可精准（结构化条目 + 溯源标签 Q14/Q22 + 版本号，p21）、可**修订**、可**淘汰**（错误或被取代则 remove，p3/p21）、可**合并**（consolidate duplicate entries，p3/p21）、可取回（top-k=3 检索，p4） | 落点为 ΔM 的条目 schema 与策展规则；检索键精度问题由 Memento 的 μ 解决，本篇不解决 |
| **C6** 可自主修改自身 | ◐ | 在线修改自身记忆内容（Eq.2, p3）；不改自身代码、不改权重。附注：会**生成并存代码**（可调用 Python，p7），近似「造工具」 | 映射为慢环 ΔM/ΔS 提案权；应用权仍在 VerificationGate，本篇不提供边界权/验证权 |
| **C7** 可保存/恢复/变异/继承 | ◐ | 记忆持久、可序列化（备忘单即文本）；**跨个体迁移被实测过**（大模型记忆传给小模型，**结果混合**，p9）——这是难得的「记忆继承」反证；无变异、无选择、无繁衍 | 「记忆能否进 GenePackage」的**警示证据**：迁移后会退化 → 默认 ΔM 不跨代（呼应 C8） |
| **C8** 给基因先验，不给知识语料 | ✓ | 备忘单 100% 由模型自生成经验填充，无人类语料注入（p2、p15） | 与 C7 合并判：**后天经验不进基因包**，DC 提供了实证理由 |
| **C9** 不设外部评分函数，只有淘汰函数 | ◐（本族中最接近 C9 的一篇） | **正面**：明确*without needing explicit ground-truth labels or human feedback*（摘要 p1、p2）；*Cur does not have access to ground-truth labels*（p3）——**没有外部评分器**，优于 Memento（环境奖励 r）与 MemRL（RL 信号）。**负面**：Cur 的判据是**自评**「correct / useful / generalizable」（p3），`Count` 只在「**成功**使用」时 +1（p21）→ 是一个**模型内部的价值判断** | **剥离方案**：① 删掉 Cur 的「正确性自评」与「有用性排序」，只保留**结构操作**（是否新增 / 是否与已有条目同签名而替换 / 是否超出上限而淘汰 / 是否合并）；② 「成功」的定义外置为**环境侧事实**（净能量收益为正、存活/淘汰），与 `experience_compiler.py` 现有纪律一致（「按世界计价物决定提不提，不用奖励函数」）；③ `Count` 改为「被取回次数」等中性计数，**不作为好坏排序键**（排序改由环境侧事实键承担） |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ◐ | 无新算子（LM 与嵌入模型均为现成件）；创新在 Gen/Cur 双角色回路（L2）与策展式在线学习（L3）。**扣分点**：机制全部写在 prompt 里（提示设计，p20–22），去语言化后是否仍成立**论文未验证** | 只承认「回路形状 + 策展三分支 + 条目 schema」为可搬资产，prompt 文本本身不搬 |

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；基座 LM + text-embedding-3-small 均为借用件 | 符合借用立场，无价值 |
| **L2 信息流层** | Gen / Cur / Retr 三角色及其时序（DC-Cu：先生成后策展；DC-RS：先检索→先策展→后生成，Eq.1–5, p3–4）；记忆作为生成的一等输入 | **中高**：与 SSEA 快环只读快照 / 慢环离线编译的分工可对照；「先策展后作答」是慢环-快环时序的一个参照 |
| **L3 学习层** | 策展即学习：写入 / 修订替换 / 淘汰修剪 / 合并去重 / 有界压缩 / 使用计数 | **高（本篇主要价值）**：直接对应 ΔM 的产出物形态与更新规则 |
| **L4 演化层** | 记忆持久化 + 跨模型迁移的**混合结果**（p9）；无变异、无选择 | **中**：为「ΔM 不进基因包」提供实证理由；为 Gene Manager 的准入规则提供一条输入 |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| Curator（Eq.2, p3） | **已有等价物**：`SSEA/experience_compiler.py`（慢环 `ExperienceCompiler(ΔM, ΔS, ΔR, Δθ)`，且已按 C9 纪律「不评估提案好不好、按世界计价物决定提不提」）→ **不搬 Cur 的评价职能，只搬其策展动作集合** |
| 备忘单 M_i（有界 + 版本号，p21） | **部分已有**：`memory_system.py` 有 `merge_threshold=0.95` 合并、`retrieval_count`、`importance` 排序、`replace()` 产副本换旧项。**缺**：条目级**溯源标签**（provenance: 来自哪些 trace）与**条目数/字节硬上限 + 版本号**的「活文档」语义 → 建议加在 ΔM 快照层 |
| 条目 schema（description + example + Count + 溯源标签，p21） | 建议：`memory_system.MemoryItem` 增 `provenance: tuple[trace_id, ...]` 与显式的 `use_count`；`skill_library` 技能条目可同构（回应「技能表示够不够」） |
| 三分支策展（保留 / 修订替换 / 淘汰）+ 合并去重（p3、p21） | `experience_compiler` 的 ΔM 规则建议显式写成三分支而非单一 merge；`_try_merge`（memory_system.py:607）是「合并」一半，「修订替换」与「因被取代而淘汰」未见对应 |
| 使用计数 Count（p21） | 对应 `retrieval_count`（已存在）；**但 DC 的 Count 由「成功使用」驱动**——搬到 SSEA 时必须改为中性计数（见 C9 剥离方案） |
| Retriever（top-k=3 余弦，p4） | 现有 `retrieve()` 受 `retrieval_policy`（types / top_k）约束且**键已收窄** → DC 的检索比 SSEA 更弱，**仅作下界对照**，不作为升级目标（升级目标仍是 Memento 的 μ） |
| 空记忆对照臂 DC-∅（p4） | **方法学资产**：七条验收实验应增设「同构脚手架但记忆为空」的对照臂，用于把「结构化指令」从「记忆增益」里剥离 |
| LCS 记忆内容稳定度（Fig.11, p18） | 候选**慢环停机/预算判据**（研究者侧仪器，不进模型）：ΔM 内容变化率趋近 0 即停止本轮整理 |
| 「错误启发式扩散」（Fig.10, p17） | 记忆写入准入 + 回归门的**设计依据**（呼应 Misevolve 的误演化威胁模型） |
| 全量重写的丢失风险（p21 N.B.） | 反面对照：确认 SSEA `replace()` 产副本的做法是对的，不要改成整份重写 |

### 3.4 债务与验收实验对应

- **「睡眠期计算预算未定义」**：DC 提供两个候选判据——备忘单**有界**（~2000–2500 词，p21）
  与**内容变化趋稳**（LCS 高稳定，Fig.11 p18）。这是本篇对当前最紧缺口之一的最直接贡献。
- **「技能表示够不够」（0/33）**：DC 的「可复用代码片段 + 溯源 + 使用计数」是**技能条目形态**
  的一个具体候选 schema，可与 PSN 的契约式技能对照做选型实验。
- **记忆门选择性 / `retrieve` 键收窄**：DC **不解决**（其检索更弱）；但 DC-∅ 对照臂可用作
  归因方法，帮助判断现有 0.5164 命中率里有多少来自「结构化检索」而非「记忆本身」。
- **债务 22（记忆二级门常量阈值，慢环不可调）**：DC 的 `Count` 是「非阈值型选择信号」的一个
  候选，但须先过 C9 审查（见 3.1）。
- **Gene Manager 缺失 / C7**：「跨模型迁移记忆结果混合」（p9）→ 支持默认**ΔM 不进基因包**。
- **服务验收实验 2（记忆召回）的增强**：以「条目 schema + 三分支策展」作为增强臂。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 备忘单**条目 schema**：description + example + 溯源标签 + Count + 版本号 | 表示 | **改造移植**（结构化化） | `memory_system.MemoryItem` / ΔM 快照 | 记忆条目可追溯、可审计、可回滚 | 高 |
| 2 | **有界活文档**：条目数/长度硬上限 + 版本号 + 原子换版 | 协议 | 改造移植 | 慢环 ΔM 快照（快环只读不可变快照） | 缓冲不无界增长（C4）；给睡眠期一个天然预算边界 | 高 |
| 3 | **策展三分支**：新增 / 修订替换（被更优者取代）/ 淘汰修剪（错误或失效）+ 合并去重 | 算法 | 改造移植（确定性化） | `experience_compiler` 的 ΔM 规则 | 现有只有 merge 一半，缺「修订替换」与「因被取代而淘汰」 | 高 |
| 4 | **溯源标签（Q14、Q22）** | 表示 | 直接移植 | 记忆与技能条目 | 慢环提案可回溯到具体轨迹；支撑四级门的回归验证 | 高 |
| 5 | **空记忆对照臂 DC-∅**（同一脚手架、记忆置空） | 基准 / 协议 | 直接移植 | 七条验收实验的归因设计 | 剥离「脚手架」与「记忆」的贡献（当前多处判据饱和，正需要这种对照） | 高 |
| 6 | **「错误启发式会扩散」**（Fig.10, p17）+ 需 careful pruning | 证据 | 直接引用 | 记忆写入准入 / 回归门 | 防止误演化在记忆侧自我放大（与 Misevolve 相接） | 高 |
| 7 | **「弱基座下记忆机制无效甚至有害」**（GPT-4o-mini AIME 16.7→13.3、GPQA 34.3→32.3，Table 3 p8；R1/o1 亦无增益 p9） | 证据 | 直接引用 | 快环设计（C4） | **支持「快环不做 curator、策展只在慢环」这一架构决定** | 高 |
| 8 | **LCS 记忆内容稳定度**作收敛/停机判据（Fig.11, p18） | 证据 / 仪器 | 仅借思想 | 慢环睡眠期预算 | 「整理到什么程度可以停」的可观测指标 | 中 |
| 9 | **全量重写的丢失风险**（p21 N.B. + p9 的 “[…] preserved” 简写塌缩） | 工程教训 | 直接引用 | ΔM 更新实现 | 反向确认：坚持 `replace()` 产副本，禁止整份重写 | 中 |
| 10 | **分层 / 模块化记忆**建议（按域分子记忆，p9） | 思想 | 仅借思想 | 记忆组织 | 错误隔离在域内（与 FLEX 的 golden/warning 分层同向） | 中 |
| 11 | Curator prompt 全文（Fig.14, p21） | 提示设计 | **仅作对照**（不搬，C2） | — | 作为「语言化策展」的对照基准，用于说明去语言化的必要性 | 低 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（逐条）**：
  1. **C2 ✗（最重）**：记忆是文本、机制写在 prompt 里、备忘单直接决定行动 → 语言在控制闭环内。
     剥离方案见 3.1；**若剥离后增益消失则整篇降为 C**。
  2. **C9 ◐**：无外部评分器（✓）但 Cur 自评「正确/有用」、Count 由「成功」驱动（✗）。
     剥离方案：删自评与好坏排序，只留结构操作，「成功」改由环境侧事实定义。
  3. **C3 库内 ✗**：技能与记忆同库混存。SSEA 侧已分离，保持即可——**这是从 DC 学到的一条
     反向纪律**（混存会导致「同一条经验既当技能又当记忆」的重复提案）。
  4. **C4 ◐**：DC-Cu 平均 1831 tokens vs BL 370（≈5×，脚注 13 p9），每步全量读写；
     与低带宽冲突 → 只允许在慢环做、快环读快照。
  5. **C10 ◐**：机制载体是 prompt，去语言化后成立性未被论文验证。
- **隐含假设与失效条件**：① 基座有足够生成能力（p9）——SSEA 快环是小模型，**DC 式策展在快环
  不可用**；② 测试样本结构相似且顺序有利（§4.6 p8）——SSEA 若危险事件随机出现，该前提不成立；
  ③ 序列依赖，无法并行（p9）。
- **算力 / 带宽 / 工程代价**：真正的低代价部分是**条目 schema 与三分支规则**（纯数据结构 +
  确定性规则，几乎零算力）；高代价部分是任何形式的「生成式综合」（重写整份备忘单、嵌入检索）。
  建议只取前者。
- **搬运后的可能退化模式**：
  1. **内容塌缩**：updater 简写/漏拷 → 记忆质量逐轮下降（论文已观察，p9）；
  2. **错误策略扩散**：一条错误启发式入库后在同类情境被反复放大（Fig.10, p17）；
  3. **早收敛**：备忘单在前几次迭代后就稳定不变（Fig.11, p18），此后**不再产生任何行为差**——
     这与 SSEA 实测「记忆增益小、危险回避率两臂均 0.9814（饱和）」是同一现象的两个观测面；
  4. **计数污染**：若把 Count 当作好坏排序键，等于在记忆侧长出评分函数（C9 违规）。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名论文 / 方法族） | 说明 |
|---|---|---|
| 同族·互补（最紧） | **Memento**（A/P1） | 同为「冻结主干 + 外部经验库 + 写读循环」。差异在**学习信号**：Memento 用环境奖励 r 学检索分布 μ（Eq.7，其卡片记为 C9 ✗），DC **明确不用任何外部标签**（p3）。分工：**Memento 决定「取回哪条」，DC 决定「留下什么、怎么组织」**；DC 的 curator 可视为 Memento `Retain` 步骤的具体化 |
| 同族·互补 | **MemRL**（B/P2） | MemRL 两阶段检索 + 冻结库迁移验收 + **遗忘率 FR**；DC 没有 FR 指标，但给出「基于被取代/失效而淘汰」的具体规则 → **DC 补 MemRL 的淘汰规则细节，MemRL 补 DC 的遗忘度量** |
| 后代 / 替代候选 | **ReasoningBank**（`2025-09-29 ReasoningBank Scaling Agent Self-Evolving with Reasoning Memory.pdf`，**本项目暂无卡片**） | 同族（从经验中蒸馏推理记忆 + 记忆感知的 test-time scaling）。**关键差异（推断，需补查其卡片确认）**：DC 的策展偏向「正确/有用」，失败只触发「修订或剪除错误启发式」（p3）；而 ReasoningBank 从标题看更强调**从成功与失败两侧显式蒸馏**——这与 SSEA「只有淘汰信号」更契合。**不替其主张，细节列入 §9 待确认** |
| 被本篇明确定位为「不同」 | **Reflexion**（B/P2） | DC 原文（p14）自陈差异：Reflexion 用反馈回路纠正**单次**解法，DC 存**跨任务可复用**的启发式/代码/元洞见，且不需为每个 batch 新建训练循环。对 SSEA：Reflexion 的「口头反思」进不了控制环（C2）；DC 的进步在于把反思**固化成可复用条目**——但仍是文本，故仍是 ✗ |
| 同槽位竞争 | **Self-Consolidation**（`2026-02-02 Self-Consolidation for Self-Evolving Agents.pdf`，**本项目暂无卡片**） | 同属「测试时把自身产出再加工成可用结构」一族；DC 是**跨 query 累积**，Self-Consolidation 从标题看是**自演化智能体的自我整合**。二者可能争夺同一个「慢环编译器」槽位 → 需补查后二选一或分工（**不替其主张**） |
| 同槽位竞争·演化版 | **EvoTest**（`2025-10-15 EvoTest Evolutionary Test-Time Learning for Self-Improving Agentic Systems.pdf`，**本项目暂无卡片**） | 同为 test-time learning 的「演化」版本；DC 的 curator 是**单点改写**，EvoTest 从标题看引入**演化式搜索** → 与 C7 的变异/选择更接近。**排序建议：先补查 EvoTest，再决定「非语言 curator」走确定性规则（DC/FLEX）还是演化搜索（EvoTest）**（**不替其主张**） |
| 替代（本篇被替代） | **FLEX**（B/P1，记忆组织/写入侧主干） | FLEX 的**分层经验库（golden/warning）+ updater 三分支写入** 就是 DC curator 的**非语言化版本**。判定：**在记忆组织/写入侧 FLEX 优先于 DC**；DC 只在「条目 schema + 有界活文档 + 溯源/计数 + 空记忆对照臂」上补 FLEX |
| 互补（下游） | **PSN**（A/P1，技能侧主干） | DC 的「可复用代码片段 + 使用计数 + 溯源」是技能条目的雏形，但**无契约、无成熟度门控、无回滚**——PSN 正好补上。组合：DC 式计数达阈值 → 提交 PSN 成熟度门控 → 固化技能（直接回应「技能表示够不够 / 0/33」） |
| 互补（对照方法） | **LightMem / SEDM / A-MEM / Mem0** | 睡眠期巩固、准入验证、链接拓扑、CRUD 分类：都与 DC 的「策展」在同一层，DC 的独特件是**有界单页活文档**这一形态 |
| 互补（诊断） | **RAGEN**（B/P1） | 若日后为策展器引入任何可训练组件，RAGEN 的 Echo Trap / 不确定性过滤是稳定化手册（DC 无可训练组件，暂不需要） |
| 替代（本篇实证证伪） | 全历史追加（FH）、只检索不策展（DR）、多数投票（MV） | FH 在 AIME 上低于基线（GPT-4o 20.0→13.3，Table 2 p7）；MV 完全无增益（Table 4 p9）；DR 显著弱于 DC（Table 1 p6）→ **可直接引用为「不要做 FH/MV」的实证依据** |

### 6.2 推荐组合方案

- **组合**：**FLEX（写入三分支 + 分层库）+ 本篇（条目 schema + 有界活文档 + 溯源/计数）+ PSN（成熟度门控 → 技能固化）**。
- **接口形态**：ΔM 条目统一为
  `{signature, content_ref, provenance:[trace_id, ...], use_count, version}`；
  慢环每轮对条目执行三分支：新增 / 修订替换（同 `signature` 且被更优者取代）/ 淘汰（超出上限
  或被环境侧事实判为失效）；条目数硬上限由睡眠期预算给定。
- **组合后新增能力**：记忆条目**可追溯、可审计、可回滚**，且慢环有了**天然的停机判据**
  （内容变化率趋 0 或条目数触顶）——直接回应「睡眠期计算预算未定义」。
- **新增风险**：① `use_count` 若被当作用途排序的好坏键 → C9 违规（改为中性计数）；
  ② 有界上限过小 → 早收敛后不再产生行为差（Fig.11 p18 已预示）；
  ③ 「修订替换」会覆盖旧版本 → 必须有 `version` 与副本（对照 p21 的丢失风险）。

### 6.3 本篇在组合中的典型角色

- **ΔM 产出物的「形态学样本」与对照基准**：不提供检索、不提供学习信号、不提供验证门；
  只提供「一份被整理过的记忆**长什么样**、按什么规则增删改」。
- 兼作**反面样本**：证明「把策展做成 prompt 里的文本重写」这条路的三个失效模式
  （内容塌缩 p9、错误扩散 p17、弱基座失效 p8），从而支撑 SSEA 走确定性 updater 路线。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 主张即 C3/C5 的同类物（实测：不动权重、外部持久记忆，摘要 p1、p3）；但 SSEA 已有 `experience_compiler` + `memory_system` 作结构等价物，增量窄 |
| 立场兼容性 | **2** | C2 ✗（记忆与机制双重语言化）、C9 ◐（自评 + 成功计数）、C3 库内混存 ✗、C4 ◐（5× token）、C10 ◐；仅 C5/C8 干净 ✓（推断为主，依据为原文机制） |
| 可搬运性 | **3** | 条目 schema、有界上限、三分支规则**可干净搬**（纯数据结构 + 确定性规则）；但「综合泛化」这一价值来源依赖 LLM 生成，去语言化后需重做且论文未验证 |
| 证据强度 | **3** | 5 类任务 × 5 模型 × 4 个对照臂（DC-∅/DR/FH/MV，实测）；但**单轮、无 seed 方差、AIME 子集仅 30 题、顺序敏感**（§4.6 p8），且无具身/生存域证据 |
| 组合价值 | **4** | 与 Memento（取回）、FLEX（写入）、PSN（技能固化）、MemRL（遗忘度量）、ReasoningBank/EvoTest（槽位竞争）均有点名接口 |
| 落地成本 | **4** | 反向口径：schema + 计数 + 溯源 + 上限几乎零成本；真正的成本只在若坚持做生成式 curator（高成本且 C2 冲突） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用**。理由：① 形态与纪律高度对口（C3/C5/C8），且是本族中**最不依赖
  外部评分**的一篇（C9 半兼容）；② 但 SSEA **已有等价物**（`experience_compiler.py` 的 ΔM/ΔS/ΔR/Δθ
  提案 + `memory_system.py` 的合并/淘汰/计数），DC 的净增量只在「产出物形态」；③ 而该形态
  是纯语言的，与 C2 直接冲突——故只搬**数据结构与规则**，不搬框架、不搬 prompt、不搬 curator 的评价职能。
- **优先级：P2**（条件性升 P1：当「慢环 ΔM 产出物形态 / 睡眠期计算预算」立项时，本篇即升为该议题的
  首要参照）。
- **建议动作**：
  1. 给 `MemoryItem` 加 `provenance: tuple[trace_id, ...]` 与显式 `use_count`（**中性计数**，
     不由「成功」驱动），ΔM 快照加 `version` 与条目数硬上限；
  2. 把 `experience_compiler` 的 ΔM 规则显式写成**三分支**：新增 / 修订替换（同 signature
     且被更优者取代）/ 淘汰（超上限或被环境侧事实判失效），补齐现有只有 `_try_merge` 的缺口；
  3. 在七条验收实验中**增设 DC-∅ 式空记忆对照臂**（同脚手架、记忆置空），把「脚手架增益」
     从「记忆增益」里剥离；
  4. 把「ΔM 内容变化率（LCS 类）」登记为**研究者侧的慢环停机判据候选**（不进模型）；
  5. 将「错误启发式扩散」（Fig.10 p17）写入记忆写入准入与回归门的验收清单（与 Misevolve 相接）；
  6. **不**把 Count 用作好坏排序键；**不**在快环引入任何策展（弱基座证据 Table 3 p8）。
- **最小验证实验（增强实验 2 · 记忆召回）**：
  - **三臂**：A 臂现状（`merge_threshold=0.95` + `importance` 排序）；
    B 臂 A + **DC 式条目 schema（溯源 + 中性计数 + version）+ 三分支策展 + 条目数上限**；
    C 臂 **DC-∅ 式空记忆对照**（同脚手架）。≥8 固定 seed。
  - **判据（分档，先看分母）**：
    ① 机制计数：写入数 / merged 数 / **修订替换数** / **淘汰数** / 条目数 / 备忘单内容变化率；
    ② 行为差：**逐帧动作差**（第三档，避免 0.9814 饱和判据的钝化）；
    ③ 淘汰结果留在模型外（环境侧）。
  - **预期与证伪**：预期 B 臂改变写入/淘汰的分布（尤其出现非零的「修订替换」计数），并在部分
    seed 上改变动作。若三臂行为无差异——**先怀疑尺子**（当前危险回避率已饱和），而非判定机制无效。
    **证伪条件**：若 B 臂条目数很快触顶、内容变化率→0，且行为差为 0 → 判「备忘单形态不产生
    行为差」，本篇降为 **C 思想启发**。
- **若 E 不采用**：不适用（判为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. Cur 的「正确性自评」能否整体删除而只保留结构操作？删掉后 DC 的增益是否随之消失？
     （论文**无此消融**，需 SSEA 自测。）
  2. `use_count` 由「成功使用」驱动是否即构成内部评分（C9）？可否改为「被取回次数」等中性键？
  3. ΔM 是否允许进 GenePackage？DC 的「跨模型迁移记忆结果混合」（p9）是否足以支撑「默认不进」？
- **需补查的文献或资料**：
  4. **ReasoningBank**（2025-09-29，本项目暂无卡片）：其「从失败中蒸馏」的机制细节与
     memory-aware test-time scaling 的具体形态；与本篇的槽位关系（互补还是替代）。
  5. **Self-Consolidation**（2026-02-02，暂无卡片）与 **EvoTest**（2025-10-15，暂无卡片）：
     二者与 DC 共享「测试时自我改进」槽位，需补查后决定「非语言策展器」走确定性规则
     （DC / FLEX）还是演化搜索（EvoTest）。**本卡片未替其主张，仅按标题与 DC 原文定位。**
- **需人工核对的公式 / 实现**：
  6. 主要数字为**单轮、无方差、小样本**（AIME 子集 30 题）且顺序敏感（§4.6 p8）——能否复现、
     能否迁移到随机危险事件的 SSEA 环境，需自测。
  7. 「2000–2500 词」的硬上限换算到 SSEA 应是多少条目 / 字节？与 C4 的睡眠期预算如何对齐？
  8. Fig.14（p21）的 curator prompt 中四节结构与 Count 机制，若改为结构化 updater，
     哪几条规则可保留、哪几条必然失效？

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “a lightweight framework that endows a black-box LM with a persistent, evolving memory … without needing explicit ground-truth labels or human feedback” | p1（摘要） |
| 摘要数字：Claude 在 AIME 上 accuracy more than doubled；GPT-4o Game of 24 10%→99%；GPQA-Diamond +9%；MMLU-Pro 工程与物理 +8% | p1 |
| “DC’s memory is self-curated, focusing on concise, transferable snippets rather than entire transcripts, thereby facilitating meta-learning and avoiding context ballooning” | p1 |
| “DC, in its core, includes an external, non-parametric memory that evolves in tandem with the LLM’s inference process.” | p3 |
| Eq.1：`ỹi = Gen(xi, Mi)`；Eq.2：`Mi+1 = Cur(Mi, xi, ỹi)` | p3 |
| Cur 三条判据：(i) 有用性与可泛化性 (ii) 修订或删除已有条目 (iii) 全库清晰与紧凑（consolidated） | p3 |
| “Cur does not have access to ground-truth labels; so, it has to assess the correctness and efficiency of the solutions by itself” | p3 |
| Eq.3–5（DC-RS）：`Ri = Retr(xi, {(xj, ỹj)}_{j<i}, k)`；`Mi = Cur(Mi−1, xi, Ri)`；`ỹi = Gen(xi, Mi)`；k=3，text-embedding-3-small + 余弦相似 | p4 |
| 基线定义：BL / DC-∅（空记忆，强基线）/ FH（全历史追加）/ DR（只检索不策展） | p4 |
| Table 1：AIME 2024 Claude 23.3→50.0（DC-Cu）；Game of 24 GPT-4o 10.0→99.0（DC-RS）；GPQA-Diamond Claude 59.6→68.7；Math Eqn Balancer 44.8→100 | p6 |
| Table 2：FH 反而低于基线（GPT-4o AIME 2024：BL 20.0 → FH 13.3），DC-Cu/DC-RS 40.0 | p7 |
| Fig.5：GPT-4o 记忆条目实例，含 `Count: 99` 的 Game 24 brute-force Python 解法 | p7 |
| Table 3：GPT-4o-mini AIME 2024 BL 16.7 → DC-Cu/DC-RS 各 13.3；GPQA 34.3→32.3（下降） | p8 |
| §4.6：DC 在测试样本结构相似与有利排序下收益被放大（curriculum-style） | p8 |
| Table 4：多数投票完全无增益（MV(BL) 23.3 = BL 23.3），DC-Cu 50.0 | p9 |
| 脚注 13：AIME 2024 上 Claude 平均 token 数 BL 370 / DC-∅ 494 / DC-RS 1035 / DC-Cu 1831 | p9 |
| “faulty heuristics that slip into memory can be equally amplified” + 长文生成弱导致 “[…] preserved” 式简写塌缩 | p9 |
| “DC demands a capable foundation model to seed and refine the curated knowledge”（R1/o1 收益 minimal or inconsistent） | p9 |
| 记忆跨模型迁移「mixed results」；顺序结构不利于并行 | p9 |
| 附录 A.1：与 Reflexion/Self-Refine/TextGrad 的差异——DC 存**跨任务可复用**的启发式，不纠正单次解法 | p14 |
| 附录 A.3：传统 RAG 语料固定、不随经验演化，不能从错误中学习 | p15 |
| Fig.10：t-SNE 显示 GPQA-Diamond 上正确与错误回答在嵌入空间聚簇 | p17 |
| Fig.11：以 word-level LCS 相似度衡量记忆演化，前几次迭代后高度稳定 | p18 |
| Fig.14（curator prompt）：四节结构；`<memory_item>` = description（含 Reference: Q1, Q2, Q6）+ example + `** Count:`；“If a better approach … replace the old version”；“Implement a Usage Counter … Increase the count every time a strategy is successfully used”；备忘单 ~2000–2500 词、含 Version | p21 |
| “once the cheatsheet is updated, any previous content not directly included will be lost” | p21（N.B.） |
