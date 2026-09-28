# 论文分析卡片 · MemSkill

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-02-02 MemSkill Learning and Evolving Memory Skills for Self-Evolving Agents.pdf` |
| 标题 | **MemSkill: Learning and Evolving Memory Skills for Self-Evolving Agents** |
| 作者 / 机构 | Haozhen Zhang、Quanyu Long、Jianzhu Bao、Tao Feng、Weizhi Zhang、Haodong Yue、Wenya Wang；Nanyang Technological University、University of Illinois Urbana-Champaign、University of Illinois Chicago、Tsinghua University |
| 发表时间 / 出处 | arXiv:2602.02474v2 [cs.CL]，2026-05-24（稿脚 Preprint, May 26, 2026）；未注明是否已录用 |
| 论文链接 | arXiv:2602.02474 |
| 代码链接 | https://github.com/ViktorAxelsen/MemSkill |
| 标签 | 记忆技能(memory skills) · 写端程序化记忆 · controller(PPO)/executor(LLM)/designer(LLM) 三件套 · 难例缓冲 + 有界演化 + 快照回滚 · span-level 整合 · 自演化记忆 |
| **应用裁决** | **B 零件采用**（写端「记忆技能」这一**第四类对象**的定义权 + 难例驱动的有界演化回路 + span 预算旋钮；核心的奖励/LLM-judge 优化不可搬） |
| 优先级 | **P1**（前提：先把验证信号从评分换成淘汰式计数，否则不得进环） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把记忆系统的**操作本身**（抽取 / 巩固 / 剪枝）从「人写死的 add-update-delete-skip 流程」提升为一张**可学习、可演化的「记忆技能」库**（skill bank），由 RL 训练的 controller 为每个文本 span 选 Top-K 技能、冻结的 LLM executor 一次性执行、周期性的 LLM designer 从难例中精炼旧技能并提出新技能，形成「学用技能 ↔ 演化技能」的闭环（p1–5）。
- **对 SSEA 的意义**：它是第一篇把「**如何组织 / 检索 / 更新记忆**」当作独立的可复用程序对象来演化的工作——正好撞上 SSEA C3 三分离中**尚未定义的第四类东西**。它逼 SSEA 回答：这东西是 ΔM 的元层、ΔR 的规则、还是独立类别？同时它给出了**睡眠期预算的可测量形态**（周期 × 每周期提案上限 × 验证窗）和记忆门「开得准不准」的一条审计回路；但它的优化信号是**任务奖励 + LLM-judge 评分**，与 C9 硬冲突。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1）：多数 LLM agent 记忆系统依赖一小撮**静态、人工设计的操作原语**（add/update/delete/skip）与启发式模块（存什么、怎么改、何时剪），把人类先验硬编码进流程；在多样的交互模式下僵硬，且随历史变长而低效。
- 它指出的既有方案缺陷：
  1. 记忆行为被**硬编码进固定流程**，并与 LLM 抽取/修订**交错**（interleave），分布漂移下脆弱（p1）；
  2. 抽取粒度被绑死在**固定单元**（如逐 turn），长跨度上退化（p1）；
  3. 已有「学习化」尝试（Memory-R1、Mem-α）用 RL 优化记忆管理，但**操作集仍是固定的**——只学「怎么用」，不学「有哪些操作」（p3）。
- 论文给出理想记忆系统的三条性质（p1）：(i) 最小人类先验依赖；(ii) 支持更大的抽取粒度；(iii) **技能条件化、可组合**的一次生成式记忆构建。

### 2.2 核心思想（关键 insight）
1. **记忆构建 = 施加一小撮可复用「记忆技能」的结果**，而不是固定流水线的输出；技能是「何时、如何把交互轨迹转成记忆并随时间修订」的**结构化行为**（p1–2）。
2. **两个库必须分离**：memory bank 是 trace 专属、**每条 trace 重置**；skill bank 是**跨 trace 共享**的可复用记忆管理知识（§3.1, Fig.2 p4）。这是全文最关键的架构动作，也是它对 SSEA 最大的贡献。
3. **闭环是双层的**：learn to use（controller 选技能）+ improve the bank（designer 从难例演化技能），二者交替（§3.5 p5）。只学选择、或只精炼不加新，都不够（Table 2 p8）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| **记忆技能表示** s=(description, content)；content = Purpose / When to use / How to apply / Constraints / **Action type** | 结构化文本 → 可被选中、可被 LLM 执行、可被检索表示 | 既是「选择键」也是「执行规约」，还规定**写入条目的动作类型** | §3.2 p3；Appendix C p18–27 |
| **4 条初始原语** INSERT / UPDATE / DELETE / SKIP(NOOP) | — | 人类给的**结构性先验种子**（演化起点） | Appendix C.1 p18–19 |
| **span-level 处理**（按 token 数切固定长 span，非逐 turn） | 交互轨迹 → 连续 span 序列 | 一次 LLM 调用施加多个技能；降低调用数；粒度可调 | §3.3.1 p4；p5 |
| **controller 状态/技能编码 + 共享打分器** h_t=f_ctx([e(x_t); m̄_t])，u_i=f_skill(e(desc(s_i)))，z_{t,i}=f_score([h_t;u_i]) | 当前 span + 检索到的记忆 → 每个技能的 logit | **变长技能库兼容**（非固定维 action head），支持技能增删 | Eq.1–2 p4 |
| **Gumbel-Top-K 无放回选择 + Top-K 联合对数概率** π_θ(A_t\|h_t)=Π_j p(a_j)/(1−Σ_{ℓ<j}p(a_ℓ)) | 分布 → 有序 Top-K 技能集 | 让「选一组技能」这件事可被策略梯度优化 | Eq.3 p5；Eq.10–11 p16 |
| **episode 级奖励 = 下游任务分** R≜Eval(memory bank; training queries)（F1 / SR） | 建好的记忆库 → 标量奖励 | 把「记忆质量」接地到任务表现 | Eq.12 p17 |
| **难例缓冲（sliding hard-case buffer）** + 双过期规则（超最大训练步间隔 / 达容量上限） | 查询、检索到的记忆、预测、参考答案、奖励、失败计数 → 有界缓冲 | **不无界增长**地跟踪近期失败模式 | §3.4 p5；Appendix B.2 p14 |
| **难度分** d(q)=(1−r(q))·c(q) | 任务奖励 + 累计失败次数 → 排序分 | 低分且反复失败者优先 | Eq.4 p15 |
| **难例聚类 + 每簇取代表**（按查询语义相似度聚类，如 KMeans） | 难例集合 → 少量代表例 | 防止 designer 被单一高频错误模式垄断 | §3.4 p5；p15 |
| **两阶段技能演化**：① LLM 分析失败成因（storage / retrieval / memory-quality 三类归因）② 据此精炼旧技能 + 提出新技能 | 代表难例 → 技能库编辑 | designer 的核心；**归因先行**，避免把检索失败误修成写入失败 | §3.4 p5；Appendix D 分析 prompt p29 |
| **演化节流**：每 100 训练步触发一次，每轮**最多 3 次技能编辑** | — | 避免技能库突变 | §4.1 p6 |
| **快照 + 回滚 + 早停**：保存最优技能库快照；用**周期内后 1/4 步的平均奖励** r̄_tail 作周期分（Eq.8），未超过历史最优即回滚；连续若干周期无改进则早停 | 周期分 → 保留/回滚/停止 | 三重防劣化 | §3.4 p5；Eq.8 p15；Appendix A.4 p13 |
| **新技能探索激励**：给新技能 logit 加最小增益 δ_q，使 Σ_{i∈S_new} p(i) ≥ τ_q，τ_0=0.3，在 T_explore=50 步内线性衰减 | — | 让新技能被真正试用，否则演化白做 | Eq.5–7 p15 |
| **演化约束**：新技能只允许 action type = insert / update（delete 与 noop 不参与演化） | — | 防止演化出「删除记忆」的危险技能 | Appendix D p30 |

### 2.4 关键表示与数据结构
- **两个库的对立**（§3.1 p4）：`memory bank`——trace 专属、图 2 标注 **Reset Every Trace**；`skill bank`——**Shared Across Training**，跨 trace 累积。
- **技能 = description（短，供选择与编码）+ content（长，供执行）**；content 为四段式模板，末行硬性声明 `Action type: INSERT only / UPDATE only / DELETE only / NOOP only`（Appendix C p18–27）。「Action type」这一字段实质上把技能**绑定到写操作类型**，是它区别于一般 prompt 的地方。
- **演化出的技能规定了写入条目的 schema**，而非只规定「记不记」。典型：ALFWorld 的 `TRACK OBJECT LOCATION` 要求写出 **object–location–state 三元组**；LoCoMo 的 `CAPTURE TEMPORAL CONTEXT` 要求写出 start/end/duration/sequence 字段（Fig.4 p8；Appendix C.2/C.3 p20–27）。
- **按附录 C 列举**（论文未声明是否穷尽），最终技能库规模：LoCoMo **9 条**（p20–24）、ALFWorld **7 条**（p24–27），均由 4 条原语演化而来；designer 只允许 add new / refine existing / no change（Appendix D p30），**无任何技能退役（淘汰）机制**——技能库单调增长。
- 抽取器/设计器/检索器：embedding 用 Qwen3-Embedding-0.6B，**同时兼作记忆检索器**，取 top-20（§4.1 p6）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| LoCoMo（LLaMA-3.3-70B） | A-MEM / MemoryOS / CoN / Mem0 / LangMem / ReadAgent / MemoryBank | MemSkill **F1 44.21 / L-J 53.82**；次优 L-J 为 A-MEM 49.71、MemoryOS 48.64 | Table 1 p6；**未报 seed 数与方差** |
| LongMemEval（跨数据集迁移，LoCoMo 训练的技能直接搬，不训练） | 同上 | MemSkill **F1 31.12 / L-J 60.89**；A-MEM 38.04、MemoryOS 39.83 | Table 1 p6；测试集约 100 样本（约 1/5 分层抽样，p14） |
| ALFWorld 平均 SR（带 in-context 演示） | LightMem / AWM / Expel | LLaMA：MemSkill **80.36** vs LightMem 74.83（+5.53）；ALF-Unseen 83.58 vs 75.37，步数 20.69→16.63。Qwen（迁移）：81.29 vs Expel 73.68（+7.61） | Table 4 p11 |
| ALFWorld（**不带**演示，更纯粹的记忆贡献） | LightMem / A-MEM / CoN / MemoryOS 等 | LLaMA：MemSkill **57.71** vs LightMem 45.99（**+11.72**）；ALF-Unseen 59.70 vs 46.27；No-Memory 仅 18.65。Qwen：63.83（+8.03） | Table 5 p12 |
| AppWorld（工具使用，Appendix A.2） | Mem0 / LightMem / AWM / Expel / A-MEM | LLaMA Pass Rate avg **26.71**（Test-N 31.12 / Test-C 22.29）；Qwen **34.23** | Table 6 p13 |
| HotpotQA 分布漂移迁移（LoCoMo 训练 → 50/100/200 篇文档拼接） | MemoryOS / A-MEM | L-J：50 docs 67.57 vs 66.02/65.63；100 docs **71.48** vs 67.19/66.80；200 docs **67.97** vs 60.55/61.72（均为 K=7）。K 越大越好（K=7 > K=5 > K=3） | Fig.3 p7 |
| 消融（LoCoMo L-J） | w/o Ctrl（随机选技能）/ w/o Des（锁死 4 原语）/ Ref.-only（只精炼不加新） | LLaMA：完整 **53.82**、w/o Ctrl 48.43、w/o Des **46.50**、Ref.-only 47.45。Qwen：完整 54.14、w/o Ctrl 42.84、w/o Des **36.15**、Ref.-only 48.88 | Table 2 p8 |
| 小模型 Llama-3.1-8B | LightMem / A-MEM / MemoryOS / Mem0 | LoCoMo F1 20.59 / L-J 27.23；LongMemEval F1 18.13 / L-J 30.20；avg L-J 28.72 vs LightMem 28.13 | Table 7 p14 |
| 运行时成本（LoCoMo，LLaMA） | MemoryOS / A-MEM / LightMem | MemSkill SS=512：**L-J 53.82、输入 249K、输出 18K、调用 215 次**；MemoryOS 48.64 / 1013K / 165K / 1288 次；A-MEM 49.71 / 2850K / 362K / 1548 次；LightMem 51.95 / 789K / 209K / 685 次。SS=1024 降成本但掉到 48.11 | Table 3 p9 |

> 口径说明：全论文**未报告 seed 数、重复次数或误差棒**；表内数字为单次运行结果（推断）。训练侧总算力（演化轮数、墙钟、GPU 时）**未提及**；论文只说「preparation cost 在使用中摊销」（p8）。

### 2.6 论文自陈局限与边界条件
- **假设依赖**：executor 与 designer 都是 LLM（70B 级，经 API 调用）；controller 只是三个轻量 MLP；embedding 固定为 0.6B 模型并兼作检索器；训练需要**带参考答案的查询**作为奖励来源（Eq.12 p17）；LLM-judge 用 openai/gpt-oss-120b（p14）；训练在 NVIDIA A6000 上（p14）。
- **明确不适用的情形**（Appendix F, p32）：「本工作聚焦基准化的研究场景」，实际部署还需隐私、用户同意、访问控制、数据留存机制；明确声明不面向监控、欺骗、高风险决策（p33）。
- 论文**未自陈**但可从事实推出（推断）：奖励依赖 ground-truth 与 LLM-judge，因此**无法在无参考答案的开放式生存环境中使用**；designer 只看「难例」不看「技能库膨胀」，无退役机制。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗/◐** | 运行时是「给长上下文问答/ household 任务建记忆」，无生存压力、无死亡淘汰；ALFWorld 有 embodied 交互但与生存无关（Table 1 p6） | 只借「写端元程序」这一层；搬到 SSEA 必须改挂在生存相关信号上（危险/资源/失效） |
| **C2** 自然语言只作观察员接口 | **✗（冲突）** | 技能本身是**英文四段式文本模板**（Appendix C p18–27）；executor 是 LLM，记忆条目是自然语言句子；designer 是 LLM；embedding 编码文本。全系统唯一非语言的部件是 controller 的三个 MLP（§4.1 p6） | 技能表示必须**去语言化**：把 Purpose/When-to-use/How-to-apply 编译成「触发谓词 + 写入 schema + 字段槽」，executor 换成确定性的结构化写操作（对照 PSN 的 E^pre/E^post）；controller 若保留，输入必须是结构化状态张量而不是文本嵌入 |
| **C3** 权重/记忆/技能**三分离** | **✓（分离做得干净）/ ✗（但暴露了第四类）** | 三条更新通道彼此独立且生命周期不同：controller 权重用 PPO 训练（Eq.15 p17）；memory bank **每 trace 重置**（Fig.2 p4）；skill bank **跨 trace 共享累积**并**不训练**（§3.1 p4）。这是全文最扎实的一点 | 正面：**记忆技能既不是 ΔM 也不是 ΔS，是独立第四类**（详见 3.3）；SSEA 必须为其单独立槽，否则会被误塞进 ΔS 而重演实验 3 的判据形状错 |
| **C4** 低算力低带宽 | **◐** | 正面：难例缓冲**双过期规则、明确「不无界增长」**（§3.4 p5）；span-level 使运行时调用数 215 vs MemoryOS 1288（Table 3 p9）；controller 是轻量 MLP；演化节流（100 步 / ≤3 编辑）。负面：executor+designer 是 70B API LLM，训练在 A6000 上，**训练侧总算力未提及** | 搬的是「预算形状」而非「预算量级」：周期 × 提案上限 × 验证窗 + span 大小旋钮（Table 3 证明存在质量-成本前沿）。LLM 侧在 SSEA 全部替换为非语言编译 |
| **C5** 精准回忆历史 | **◐（偏 ✓）** | 记忆库支持显式 INSERT/UPDATE/DELETE/NOOP 四类写操作，DELETE 要求「证据明确才删，不确定优于不删」（Appendix C.1 p19）；**但检索是单一固定 embedding 的 top-20 语义相似**（§4.1 p6），无结构化键 | 真正可搬的是**写端 schema 化**：由技能规定条目字段（object–location–state 三元组、temporal 序列），使后续检索有窄字段可挂——这是它对 `retrieve` 键收窄的**间接**贡献，不是直接修键 |
| **C6** 可自主修改自身 | **✓（形状完整）** | 它修改的是**自己的记忆管理程序**。四权齐备：提案权=designer（LLM 提精炼/新增）；边界权=每轮 ≤3 编辑 + 新技能只允许 insert/update + DELETE/NOOP 不参与演化（p30）；验证权=周期分 r̄_tail（后 1/4 步均值）+ 未超历史最优即回滚 + 早停；应用权=技能库更新（Eq.8 p15） | 几乎可直接照抄四权分工；**验证信号必须换**（见 C9） |
| **C7** 可保存/恢复/变异/继承 | **◐（缺淘汰）** | 保存/恢复：最优技能库快照 + 回滚（p15）；变异：refine existing + add new。**继承**：技能库跨数据集（LoCoMo→LongMemEval→HotpotQA）与跨底座模型（LLaMA→Qwen→8B）直接复用（Table 1 p6、Table 7 p14）——是极强的横向可遗传性证据。**但无淘汰**：designer 只允许 add / refine / no change，技能库 4→9（LoCoMo）、4→7（ALFWorld）单调增长（Appendix C、D p30） | 这正是 SSEA 要补的一刀：给技能加**退役计数**（引入后 N 个睡眠周期内被选中次数低于阈值即退役，纯计数、不打分），使「淘汰+繁衍」构成达尔文闭环（C7 明文要求） |
| **C8** 给基因先验，不给知识语料 | **✓（强对齐）** | 种子只有 4 条**结构性原语** INSERT/UPDATE/DELETE/SKIP（Appendix C.1 p18–19），其余全部从交互数据演化；演化出的技能是**字段/结构约定**（「追踪物体位置-状态三元组」「捕获时间上下文」），**不是事实知识**（Fig.4 p8、Appendix C） | 直接支持「记忆技能属于可遗传本能段」的裁决；但须加硬约束：演化产物**不得携带具体事实内容**，否则违反 C8 的防膨胀条款 |
| **C9** 不设外部评分函数，只有淘汰函数 | **✗（硬冲突，两处）** | ① 奖励 = 下游任务分 F1 / SR（Eq.12 p17），并用于 PPO（Eq.15）；② 评估主指标之一是 **LLM-judge 评分**（gpt-oss-120b，p14），且难度分 d(q)=(1−r(q))·c(q) 直接用奖励排序（Eq.4 p15）。C9 明文「奖励塑形、观察员评分一律违规」。相对缓和的一点：ALFWorld 的 SR 由环境判定，性质上**接近**淘汰函数；F1 与 L-J 则是彻底的评分 | 分层改造：① F1 / L-J / 难度分**全部剔除**；② 保留 SR 一类**环境侧成败**作唯一信号；③ 难例的定义从「低分」改为**可计数的事实**：「决策时缺关键信息」「写入后从未被 retrieve 命中」「同一上下文矛盾更新次数」——三者都无需打分；④ 周期分 r̄_tail 改为**成敗率**（如最近 M 次交互的失效/死亡计数） |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | MLP / PPO / Gumbel-Top-K / KMeans / embedding 全是借用的现成件；创新在「记忆技能库」这一信息流抽象（L2）、难例驱动的演化与稳定化机制（L3）、技能库作为跨模型跨数据集可复用遗产（L4） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子。MLP、PPO、Gumbel-Top-K、Qwen3-Embedding-0.6B、冻结 LLM | 低（符合借用立场，无可搬算子） |
| **L2 信息流层** | **memory bank（trace 专属、每 trace 重置）与 skill bank（跨 trace 共享）的二元分离**；span-level 抽取粒度；「状态-技能对」共享打分器使技能库可变长 | **最高**：直接回答 C3 的第四类问题，并给出「写端元程序」的接口形状 |
| **L3 学习层** | 难例缓冲（有界）+ 难度分 + 聚类取代表 + 两阶段演化（归因→编辑）+ 节流 + 快照回滚 + 早停 + 新技能探索激励 | **高**：这是 SSEA 记忆门「开得准不准」缺失的那条审计回路的现成骨架（信号需换） |
| **L4 演化层** | 技能库作为跨数据集、跨底座模型的**可迁移遗产**；快照 = 可保存/恢复；refine+add = 变异；**无淘汰、无跨个体继承** | 中高：提供「本能段」候选对象的实例；缺淘汰与 GenePackage 语义，需 SSEA 自行补 |

### 3.3 模块映射（含第四类归属裁决）

#### ★ 裁决：记忆技能（Memory Skills）在 SSEA 归哪里？

**判定：独立第四类 —— 元程序 ΔP（meta-procedure）；发布通道并入 ΔR（规则），作为 ΔR 的「程序化子类 ΔR-proc」；绝不并入 ΔM，也绝不并入 ΔS。**

判定依据严格用 C3 自己给出的三条分判据（来源 / 生命周期 / 可遗传性）：

| 分判据 | ΔM（记忆） | ΔS（技能，PSN 式） | **记忆技能** |
|---|---|---|---|
| **来源** | 一次具体经历 | 任务流中蒸馏出的可执行程序 | **记忆系统自身失败案例的元层归纳**（designer 从 hard case 提炼，§3.4 p5）——不是经历，也不是环境动作 |
| **生命周期** | trace 内累积、**每 trace 重置**（Fig.2 p4） | 跨任务累积、可回滚 | **跨 trace 共享、持续累积、不重置**（§3.1 p4） |
| **可遗传性** | **不可遗传**（C8：后天知识不跨代） | 成熟后可遗传 | **天然可遗传且已实测**：跨数据集（LoCoMo→LongMemEval→HotpotQA）、跨底座模型（LLaMA→Qwen→8B）直接复用仍最优（Table 1 p6、Table 7 p14） |

三条全不同 → 它确实不是 ΔM、不是 ΔS、也不是 Δθ（它是符号结构不是权重）。**它是一个独立类别，这一点论文是对的。**

**为什么归入 ΔR 而不是单独开第五条通道**：SSEA 的 ΔR 本就是「约束结构如何被写入/整理与准入」的通道，记忆技能的本质正是**可枚举的写入/整理规则集**（When to use = 触发条件，Constraints = 边界，Action type = 允许的操作类型）。把它塞进 ΔR 有两个额外收益：① 给当前 **`rules` 零消费者** 的 ΔR 通道找到**第一个真实消费者**——记忆写入门；② 复用已有的四级验证门，不新增发布路径。代价是 ΔR 必须支持**带触发条件的程序化规则**（procedural），而非纯声明式约束。

**为什么不能并入 ΔM**：ΔM 按 C8 不可遗传，而记忆技能是 SSEA 里**最该遗传**的东西（它是不依赖具体经历的结构性先验）。若并入 ΔM，会被「后天知识不跨代」的防膨胀规则一并丢弃，或反过来污染 ΔM 使其膨胀——两者都是错误。

**为什么不能并入 ΔS**：ΔS（PSN 式）的契约是 E^pre/E^post **作用于环境状态**，其验证是环境成败；记忆技能的作用对象是记忆库，效果只能经「后续决策是否成功」**间接**观测。混进去会产生一类**无法用环境成败直接验证的伪技能**——这与实验 3「0/33 SKILL_FAILURE 判据形状错」是同一类风险。分开计数是防止再犯一次形状错的最省事办法。

**若团队坚持三分离不动**：唯一自洽的退路是把它算作 **ΔM 的元层（schema / metadata 段）**，并显式标记为「可遗传本能」，禁止把演化产物当作记忆内容去检索。此退路的缺点是 ΔM 的读写路径要额外承担「元层不可被普通 retrieve 命中」的隔离约束，工程上比并入 ΔR 更绕。**推荐 ΔR-proc。**

#### 构件落点

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| skill bank（跨 episode 共享的记忆技能库） | **新增 ΔR-proc 槽位**，由慢环 SEL 发布；与 `rules` 通道合并消费者（记忆写入门） |
| memory bank（per-trace、可重置） | 现有 `memory` 模块（ΔM）；**不变** |
| 4 条初始原语 INSERT/UPDATE/DELETE/SKIP | **GenePackage 的「本能段」**：给基因只给这 4 条写操作原语 + 字段约定，不给任何事实内容（C8 的标准范本） |
| 技能的 When-to-use / Constraints / Action-type 四段式 | 编译为 ΔR-proc 的**触发谓词 + 边界 + 允许操作类型**；触发谓词对接记忆二级门（当前常量阈值，债务 22） |
| 演化产物规定**写入条目 schema**（object–location–state 三元组、temporal 序列） | `memory` 写入条目增加**结构化字段槽**；为 `retrieve` 键收窄提供可挂字段（C5） |
| 难例缓冲（有界、双过期规则） | 慢环新增 `hard_case_buffer`：**按结构类型分桶**（缺关键信息 / 写了未命中 / 矛盾更新），不按分数排序 |
| 聚类取代表 | 慢环对难例分桶后**每桶抽样**，避免单一高频模式垄断（可直接用，无需评分） |
| 两阶段演化（归因 → 编辑） | 慢环 `ExperienceCompiler` 的**归因前置**步骤：先判定是「存储失败 / 检索失败 / 质量失败」，只把存储与质量失败转成 ΔR-proc 提案（避免像 designer 那样靠 LLM 自由发挥） |
| 演化节流（周期 + 每轮 ≤3 编辑） | **睡眠期预算的具体形态**：(触发周期 N, 每周期提案上限 k, 验证窗 M)。直接回应「睡眠期计算预算未定义」 |
| 周期分 r̄_tail（后 1/4 步均值）+ 快照回滚 + 早停 | 四级验证门的**第三级（回归）判据模板**：把「均值比较」换成**成败率比较**；快照回滚照搬（对齐 PSN 的逆操作/回滚） |
| 新技能探索激励（logit 增益 + 50 步线性衰减） | 对应 SSEA 的**可塑性窗口**：新 ΔR-proc 发布后给一个有限试用窗，之后回落到正常选择；衰减形状可直接借 |
| span-level 抽取 + span size 旋钮 | 睡眠期**批量整合的粒度旋钮**；Table 3 的质量-成本前沿是「预算定在哪」的实测依据（SS=512 最优，1024 掉质） |
| DELETE/NOOP 不参与演化 | 直接借作**边界权**：记忆技能可以新增/精炼「怎么写」，但**不允许演化出「怎么删」**，防止自演化削弱自身记忆 |
| 缺失：技能退役判据 | **SSEA 必须补**：引入后 N 个睡眠周期内被选中次数低于阈值即退役（纯计数） |

### 3.4 债务与验收实验对应

- **记忆门「开得准不准」的选择性缺失**（当前最紧缺口之一）：本论文的难例缓冲 + 分桶 + 两阶段归因 + 有界演化，正是「门开得准不准」的**审计回路**。可搬，但信号必须换：把「低分难例」换成三类可计数事实——(a) 决策时缺关键信息（该写没写）；(b) 写入后从未被 `retrieve` 命中（写了没用）；(c) 同一上下文矛盾更新次数。三者都不需要评分函数，C9 合规。
- **`retrieve` 键收窄 → 召回精度上限低**：本论文**不直接修键**（检索仍是单一固定 embedding top-20）。它给出的是**另一条杠杆**：改变**写入条目的 schema**，让条目自带可分辨字段（object–location–state、temporal start/end/duration）。对 SSEA 的含义：`retrieve` 命中率 0.5164 的天花板可能不全在键上，也在被检索内容的字段结构上——这是一条**此前没有评估过**的独立路径。
- **睡眠期计算预算未定义**（前瞻预演的硬门槛）：本论文给出预算的**三元组形态**（周期 N=100 步 / 每轮 ≤3 提案 / 验证窗=周期内后 1/4）与**粒度旋钮的实测前沿**（Table 3：SS=512 质量最优且调用 215 次；SS=1024 成本更低但 L-J 掉到 48.11）。这是目前卡片库里**唯一带数字的睡眠期预算参照**。
- **债务 22（记忆二级门用常量阈值，慢环不可调）**：本论文提供了「门规则本身可被慢环演化且带边界」的完整模板——触发条件、约束、允许操作类型三项都可发布。接线顺序：先把常量阈值换成可发布结构，再接 ΔR-proc。
- **`rules` 零消费者**：把记忆技能归 ΔR-proc，等于给 `rules` 通道装上**第一个消费者**（记忆写入/整理门）。这是本篇对 SSEA 结构最实用的一处贡献。
- **Gene Manager 缺失（实验 4/5 卡住）**：记忆技能是 GenePackage 本能段的**具体候选内容**，因此也成了 Gene Manager 需要管理的**一类新对象**——它扩大了 Gene Manager 的设计规格，而非缩小。
- **实验 3（技能固化）0/33 判据形状错**：本篇是**反面警示**——若把记忆技能计入 ΔS 的 SKILL_FAILURE 分母，会再产生一次形状错（记忆技能没有环境成败判据）。同时可借 PSN 的 SRR 思路为 ΔR-proc 设计独立指标：选用次数、命中贡献、退役数。
- **可服务的验收实验**：实验 2（记忆检索）、实验 3 的重设计（作为**排除项**）、实验 6/7 的记忆相关臂；不服务实验 4/5（那两个卡在 Gene Manager）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **「记忆技能 = 独立第四类元程序」的归类判据**（来源/生命周期/可遗传性三轴） | 表示 / 架构 | **直接移植（作为裁决）** | ΔR-proc 槽位 / GenePackage 本能段 | C3 三分离中第四类未定义；`rules` 零消费者 | 高 |
| 2 | **睡眠期预算三元组**（触发周期 N / 每周期提案上限 k / 验证窗 M）+ 粒度旋钮的质量-成本前沿（Table 3） | 协议 / 工程 | 改造移植（数值重标定） | 慢环 SEL 预算器 | **睡眠期计算预算未定义**（前瞻预演硬门槛） | 高 |
| 3 | **难例缓冲 + 分桶取代表 + 两阶段归因**（有界、双过期规则、先归因后编辑） | 算法 | 改造移植（信号换淘汰式计数） | 慢环 `hard_case_buffer` + `ExperienceCompiler` | 记忆门「开得准不准」的选择性缺失 | 高 |
| 4 | **快照 + 回滚 + 早停** 的三重防劣化（周期分成败率化） | 协议 | 改造移植 | 四级验证门第三级（回归） | 自修改安全；可恢复 | 高 |
| 5 | **写端 schema 化**：由技能规定条目字段（object–location–state 三元组 / temporal 序列 / 动作约束） | 表示 | 改造移植（去语言化） | `memory` 写入条目结构 | `retrieve` 键收窄导致召回精度上限低（间接路径） | 中 |
| 6 | **边界权清单**：新技能只允许 insert/update，DELETE/NOOP 不参与演化；每轮 ≤3 编辑 | 协议 | 直接移植 | 自修改四权之边界权 | 防止自演化削弱/清空自身记忆 | 高 |
| 7 | **新结构探索激励**（有限试用窗 + 线性衰减，50 步 / τ₀=0.3） | 算法 | 仅借思想（去 logit，改可塑性窗） | `plasticity` | 新 ΔR-proc 发布后无人用的冷启动问题 | 中 |
| 8 | **4 条初始原语作为基因先验种子** | 表示 | 直接移植 | GenePackage 本能段 | C8 的「给结构性先验」落地范本 | 高 |
| 9 | **技能退役计数（本篇缺失，SSEA 补）**：引入后 N 周期内被选中次数低于阈值即退役 | 指标 / 算法 | 新增（非搬运） | ΔR-proc 生命周期管理 | 技能库只增不减撞 C4；C7 要求「淘汰+繁衍」 | 中 |
| 10 | HotpotQA 跨分布迁移协议（50/100/200 文档拼接） | 基准 | 仅借思想 | 记忆迁移回归测试 | 检验记忆技能是否过拟合单一环境 | 低 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**：
  1. **C9（硬）**：奖励 = F1 / SR（Eq.12）驱动 PPO；LLM-judge（gpt-oss-120b）是观察员评分；难度分直接用 r(q) 排序（Eq.4）。三条全踩「奖励塑形、观察员评分一律违规」。**这是本篇最大的不可搬部分**，也是它只能拿 B 而非 A 的原因。
  2. **C2（硬）**：技能是英文文本模板、executor 与 designer 是 LLM、记忆条目是自然语句。整条链路的语言载体与 SSEA 相反。
  3. **C1（软）**：任务是长上下文 QA 与 household 操作，无生存压力；ALFWorld 的成功率不是生存淘汰。
  4. **C4（软）**：70B API LLM + A6000 训练；训练侧算力**未提及**，只有「摊销」的定性说法（p8）。
- **隐含假设与失效条件**：
  1. 必须有**带参考答案的查询**才能算奖励 → 无 ground truth 的开放式环境（SSEA 正是这种）**直接失效**。这是搬运的头号拦路石。
  2. 假设**记忆质量是瓶颈**。Table 5（无演示）显示增益变大（+11.72），说明它在「记忆真的被依赖」时才强；若 SSEA 的瓶颈在键或表征而非写入内容，收益归零。
  3. 假设技能库是**共享且稳定**的；若环境非平稳（SSEA 的生存域），「跨数据集复用」的证据会打折。
  4. 演化出的技能是**领域特化的**（LoCoMo 偏时间/活动，ALFWorld 偏物体位置/动作约束，Fig.4 p8）——意味着 SSEA 每个环境会长出不同技能集，跨环境继承未经验证。
- **算力 / 带宽 / 工程代价**：
  - 需要新建：ΔR-proc 槽位与表示、难例缓冲与分桶、归因步骤、快照/回滚/早停、探索窗、退役计数。**比 PSN 那套轻**（无契约网络、无重构搜索），但比单个零件重。
  - 慢环每睡眠期要跑「分桶 → 抽样 → 提案 → 验证窗」一遍，周期与上限必须**先定义**（这本身就是当前缺口），否则会无界。
  - 去语言化改造是主要一次性成本：把四段式模板编译成触发谓词 + 写入 schema，需要一个编译器（现有 `RuleCompiler` 缺失）。
- **搬运后的可能退化模式**（若失败，会以什么形式失败）：
  1. **技能库只增不减**（论文自带的缺陷）→ ΔR-proc 膨胀，慢环预算被吃掉，撞 C4「缓冲不无界增长」。
  2. **归因错误**：把「检索失败」误判为「存储失败」→ 加了一堆写入技能，命中率不动，只涨成本。论文靠 LLM 归因，SSEA 去掉 LLM 后这一环最脆弱。
  3. **技能漂移**：无评分但有演化，仍可能因难例抽样偏差而漂移；快照回滚会掩盖但未消除。
  4. **写入 schema 过窄**：字段被技能钉死，遇到新类型信息无处可写 → 表现为「该写没写」计数上升。
  5. **元层混入知识**：演化产物若被允许写具体事实，将违反 C8 并让 GenePackage 膨胀。

---

## 6. 组合分析

### 6.1 关系图谱（点名连接）
| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **镜像 / 最紧互补** | **PSN（Evolving Programmatic Skill Networks）** | PSN 的技能是**作用于环境状态**的可执行符号程序（E^pre/E^post 契约、REFLECT 定责、成熟度门控、20% 回滚）；MemSkill 的技能是**作用于记忆库**的元程序。**同一套「结构化可复用程序 + 契约 + 门控 + 回滚」形状，作用面差一层**。→ PSN 管 ΔS 的世界侧，MemSkill 管 ΔR 的记忆侧，二者构成 SSEA 程序化结构的完整两半。且 PSN 的**成熟度门控**正好补 MemSkill 缺的**退役/冻结**机制 |
| **同层互补（读侧 ↔ 写侧）** | **Memento** | Memento = 冻结 LLM + 案例库 + **可学习检索 μ**（读侧可学习）；MemSkill = 冻结 LLM + 技能库 + **可学习选择 controller**（写侧可学习）。**两者都是「小非语言模块 + 冻结大模型」的 C3 友好形状，且都因用奖励训练而踩 C9**。合起来才闭合记忆的读与写 |
| **替代 / 升级对象** | **Mem-α**、Memory-R1 | 同族：都用 RL 学记忆管理。关键差异：Mem-α 等**固定操作集只学策略**，MemSkill 让**操作集本身演化**（p3 论文自陈）。对 SSEA 的意义：只有 MemSkill 提供了「操作集从哪来」的答案 |
| **同层兄弟（同为「从经验蒸馏可复用 X」）** | **ReasoningBank** | ReasoningBank 蒸馏**推理策略**（≈ ΔS 侧），MemSkill 蒸馏**记忆操作**（≈ ΔR 侧）。论文 p3 自陈二者目标不同但同属自演化记忆一族。二者在 SSEA 里应各归其位，不可混计 |
| **架构级 vs 操作级** | **MemEvolve** | MemEvolve 做**记忆系统架构的元演化**（预定义架构上的搜索），MemSkill 做**记忆操作技能**的演化。MemSkill ≈ MemEvolve 的**内层**：先有架构，再有架构内的操作技能。若 SSEA 已引入 MemEvolve 的架构搜索，MemSkill 是它的下一层 |
| **相邻但不同层** | **MemGen** | MemGen 面向**推理用的潜在记忆**（latent memory），MemSkill 面向**显式记忆的构建操作**。不冲突，一隐式一显式；论文 p3 点名区分 |
| **可替换其验证环节** | **SEDM** | MemSkill 的验证是「周期分比较 + 回滚」（**分数量级**）；SEDM 的 SCEC 自包含打包 + **A/B 准入验证**是**成败式**。→ 用 SEDM 的 A/B 准入替换 MemSkill 的奖励快照比较，**正好消掉 C9 冲突**，得到「记忆技能的准入官」 |
| **写入侧主干的升级对象** | **FLEX** | FLEX 的 updater 是**人工设计的三分支写入**（golden/warning 分层经验库）；MemSkill 正是把这类「写入分支集」变成可演化对象。→ MemSkill = FLEX updater 的**可演化版**。另：FLEX 的 **logistic 增长曲线作慢环停机判据**可替换 MemSkill 的「连续若干周期无改进则早停」（后者依赖奖励，前者是基于增长饱和的形状判据） |
| **睡眠期同族** | **LightMem** | LightMem = 摄入压缩 + 主题分段 + **睡眠期离线巩固**，且在成本对照里被 MemSkill 以更少调用超过（L-J 51.95/685 次 vs 53.82/215 次，Table 3 p9）。→ 组合：LightMem 的**主题分段**定 span 边界，MemSkill 的 **span size** 定预算，二者共同定义睡眠期整合 |
| **被它超过的基线** | **A-MEM**、**Mem0** | A-MEM（Zettelkasten 链接拓扑 + 近邻回写）是**组织侧**方案，MemSkill 是**写入侧**方案，Table 1 中 MemSkill 的 avg L-J 57.36 vs A-MEM 43.88（LLaMA）。→ A-MEM 的链接拓扑可与 MemSkill 的写端 schema 并存：schema 决定条目长什么样，拓扑决定条目怎么连 |
| **威胁模型覆盖** | **Misevolve** | MemSkill 的 designer 是一个**会修改自身记忆管理程序**的自演化组件，正好落在 Misevolve 的**记忆路径误演化**象限。→ 引入本篇前，应先用 Misevolve 的红队验收清单过一遍（尤其是「演化削弱记忆」这一条，本篇只靠「DELETE/NOOP 不参与演化」防了一部分） |
| **训练稳定性诊断** | **RAGEN** | 若保留任何形式的 RL controller（即使信号已换成环境成败），RAGEN 的 **Echo Trap** 诊断与不确定性过滤是必需的稳定性仪器 |
| **验证场** | **Dream-RSI** | designer 的提案与回滚验证可放进重放模拟器离线跑，省真实交互——与 PSN × Dream-RSI 的组合同构 |
| **预算约束同类** | **MaAS** | MaAS 的成本约束 + 查询条件化早退，与 MemSkill 的 span size 质量-成本前沿同为「把预算写进结构」的思路，可互为参照 |
| **技能流水线同形** | **SkillWeaver** | SkillWeaver 的「提案-练习-合成-打磨」与 MemSkill 的「难例→归因→精炼/新增→探索窗」**同形**，但前者作用于 web 技能（ΔS），本篇是它的记忆侧版本 |
| **对照（非组合）** | Voyager / ADAS / Reflexion / MemRL / Gödel Agent | Voyager、ADAS 提供技能/架构搜索的形式化背景；Reflexion 式的口头反思正是 MemSkill 用「沿归因的结构化编辑」取代的东西；MemRL 的**遗忘率 FR** 可作为 ΔR-proc 退役指标的参考口径 |

### 6.2 推荐组合方案
1. **组合 A（首选）：MemSkill × PSN —— 程序化结构的两半**
   - 接口形态：PSN 的 ΔS 作用于环境（契约 E^pre/E^post、REFLECT 沿调用轨迹定责、20% 成败回滚）；MemSkill 的 ΔR-proc 作用于记忆库（触发谓词、写入 schema、允许操作类型）。**两者共用同一套「提案 → 边界 → 验证 → 应用」四权管线与同一套快照/回滚机制，但计数与指标完全分开。**
   - 组合后新增能力：SSEA 首次同时拥有「世界侧技能」与「记忆侧元程序」，且**不会**把记忆技能误计入技能固化分母（避免第二次实验 3 形状错）。PSN 的成熟度门控补上 MemSkill 缺失的冻结/退役。
   - 新增风险：两套程序库各自膨胀；须各设上限与退役计数。
2. **组合 B：MemSkill × SEDM —— 去掉 C9 冲突的准入官**
   - 接口形态：MemSkill 负责**提案与归因**（难例分桶 → 两阶段归因 → 精炼/新增提案），SEDM 负责**验证**：候选 ΔR-proc 打成 SCEC 自包含包，走 **A/B 成败准入**（通过/不通过），替换 MemSkill 的「周期分 r̄_tail 均值比较」。
   - 组合后新增能力：演化回路在不引入任何评分函数的前提下闭合——这正是 C9 要求的形态。
   - 新增风险：A/B 需要成对的对照运行，睡眠期预算翻倍；须先用组合 A 的 span 预算旋钮把总量压住。
3. **组合 C：MemSkill × FLEX × LightMem —— 睡眠期整合的预算与停机**
   - 接口形态：LightMem 的主题分段决定 **span 边界**，MemSkill 的 span size 决定 **每期处理预算**（参照 Table 3 的 SS=512 前沿），FLEX 的 **logistic 增长饱和**决定**何时停机**（替换「连续 N 周期无改进则早停」这一依赖奖励的判据）。
   - 组合后新增能力：**「睡眠期计算预算未定义」这一条被完整填上**——边界、预算、停机三者都有出处。
   - 新增风险：增长曲线在生存域的形状未验证；可能过早停机。

### 6.3 本篇在组合中的典型角色
- **记忆侧元程序的定义者与演化回路骨架**：不提供技能本体（那是 PSN 的事），也不提供验证判据（那是 SEDM 的事），而是回答「**管记忆的那些程序，是什么、从哪来、怎么长、怎么退**」。
- 次要角色：**睡眠期预算的度量模板**（周期 × 提案上限 × 验证窗 × 粒度旋钮，带一条实测质量-成本前沿）。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 正对三个当前缺口：第四类未定义、记忆门选择性、`retrieve` 键收窄；并给出睡眠期预算的实测前沿（Table 3 p9）。扣分因它是 LLM-NL、长上下文 QA 谱系，非生存控制环（实测：基准为 LoCoMo/LongMemEval/HotpotQA/ALFWorld/AppWorld） |
| 立场兼容性 | **2** | C9 硬冲突两处（F1/SR 奖励驱动 PPO Eq.12/15；LLM-judge 评分 p14）+ C2 硬冲突（技能为英文模板、executor/designer 为 LLM）；C1 软冲突。C8（4 条原语作本能种子）、C10、C6 四权、C3 通道分离是强加分项，但不足以抵两处硬冲突（实测 + 推断） |
| 可搬运性 | **3** | 可干净拆出：难例缓冲与分桶、两阶段归因、节流、快照/回滚/早停、探索窗、写端 schema、边界权清单。不可拆：controller 的 PPO、LLM executor、LLM designer、文本技能表示——即论文的核心优化回路整体不可搬（推断） |
| 证据强度 | **3** | 广度足：4 个主基准 + AppWorld + 3 个底座模型（70B×2 + 8B）+ 消融 + 跨分布迁移 + 成本分析（Table 1/2/3/4/5/6/7）。扣分：**全篇未报 seed 数与方差，表中无误差棒**；训练侧算力与演化轮数未提及；预印本未审稿（实测） |
| 组合价值 | **5** | 与 PSN / Memento / Mem-α / MemEvolve / MemGen / ReasoningBank / SEDM / FLEX / LightMem / A-MEM / Mem0 / Misevolve / RAGEN / Dream-RSI / MaAS / SkillWeaver 全部可点名连接；且占据卡片库中**此前空缺的「写端元程序」槽位**（推断） |
| 落地成本 | **2** | 反向口径（成本越低分越高）：需新建 ΔR-proc 表示与槽位、难例缓冲、归因步骤、快照/回滚、探索窗、退役计数，并**先**决定第四类归属与预算三元组；且去语言化改造依赖缺失的 RuleCompiler。中等偏重（推断） |

---

## 8. 裁决与下一步

- **应用等级：B（零件采用）** —— 理由：① 它提出并实证了「记忆技能」这一 SSEA 三分离中尚未定义的对象，并给出可操作的归类判据，这是**架构级贡献**；② 但它的核心优化回路（RL 奖励 + LLM-judge + LLM executor/designer + 文本技能）**同时踩 C9 与 C2 两条硬约束**，不可整体采用；③ 因此取零件：难例驱动的演化回路骨架 + 睡眠期预算三元组 + 快照回滚 + 写端 schema + 边界权清单。
- **优先级：P1** —— 但它**带门禁**：必须先把验证信号从「评分」换成「淘汰式计数」后才允许进环；在此之前只做离线原型，不接快环。
- **建议动作**：
  1. **先下裁决**：在架构文档中正式确认「记忆技能 = 独立第四类元程序 ΔP，发布通道并入 ΔR-proc，属 GenePackage 本能段；不并入 ΔM，不并入 ΔS」。这是本篇对 SSEA 的第一顺位产出，且**不依赖任何实现**。
  2. **给 `rules` 装第一个消费者**：把记忆写入门（INSERT/UPDATE/DELETE/SKIP + 触发谓词 + 允许操作类型）作为 ΔR-proc 的首个实例，顺带解决债务 22 的「常量阈值不可调」。
  3. **建难例缓冲（无评分版）**：三个桶——「决策时缺关键信息」「写入后从未被 retrieve 命中」「同上下文矛盾更新」；每桶抽样，先归因（存储 / 检索 / 质量），只把存储与质量桶转成提案。
  4. **定义睡眠期预算三元组**：(触发周期 N, 每期提案上限 k=3, 验证窗 M)，并在睡眠期整合中引入**粒度旋钮**，先照 Table 3 的形状扫一遍质量-成本前沿，找到 SSEA 自己的拐点。
  5. **补退役计数**：新 ΔR-proc 引入后 N 个周期内被选中次数低于阈值即退役（纯计数），与 PSN 的成熟度门控共用一套成熟度概念。
  6. **写死边界权**：DELETE / NOOP 类规则**不参与演化**，每期 ≤3 编辑，快照 + 回滚 + 早停照搬。
  7. **顺序依赖**：上述 3–6 依赖 RuleCompiler（缺失）。建议与 PSN 卡片的动作合并立项。
- **最小验证实验**：
  - **双臂 / 消融**（在现有记忆检索实验上做，不动快环）：
    - A 臂（对照）：固定 4 原语写端，条目字段自由（现状）。
    - B 臂：写端 schema 化——三类结构化字段（object–location–state / temporal 序列 / 动作约束），由 ΔR-proc 规定。
    - C 臂（消融，B 的对照）：B 的 schema，**但不允许慢环演化**（锁死初始 schema），用于分离「schema 本身的收益」与「演化带来的收益」。
  - **判据（分档，先看分母）**：
    1. **机制计数**：写入条目中带结构化字段的比例；写入后从未被 retrieve 命中的条目比例；每睡眠期提案数 / 回滚数 / 退役数；演化出的 ΔR-proc 总数（看是否只增不减）。
    2. **行为差**：`retrieve` 命中率是否脱离当前 **0.5164**；危险回避率是否已饱和（当前两臂均 **0.9814**，若饱和则该指标**不可用**，须换更难的臂）。
    3. **淘汰结果**：死亡率 / 存活时长（模型外，环境判定）。
  - **预期与证伪条件**：
    - 预期：B 臂「写后未命中条目比例」下降、`retrieve` 命中率上升；C 臂介于 A、B 之间（说明 schema 与演化各自都有贡献）。
    - **证伪**：若 B、C 两臂的命中率差异落在噪声内且「写后未命中比例」不变 → 说明瓶颈在 `retrieve` 的**键**而不在写端 schema，本篇路线应降级为 P3，转向键收窄。若 B 臂 ΔR-proc 数单调增长且预算被吃满 → 说明退役计数阈值设置失败。
- **若 E 不采用**：不适用（本篇至少贡献了第四类归属裁决与睡眠期预算形态，两者零成本）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **第四类归属**：接受「ΔR-proc（ΔR 的程序化子类）」还是走退路「ΔM 元层 + 显式可遗传标记」？这决定 Gene Manager 的数据模型。
  2. ΔR 是否愿意承载**带触发条件的程序化规则**（而非纯声明式约束）？若否，需新开第五条通道，请评估代价。
  3. 「记忆技能」作为 GenePackage 本能段，**演化产物是否允许跨代继承**？若允许，如何防止其携带事实知识而违反 C8 防膨胀？
  4. 记忆技能是否计入实验 3 的技能固化分母？（建议**明确不计**，并写入判据文档以防第二次形状错。）
- **需补查的文献或资料**：
  1. 论文未报 seed 数与方差——需向作者或代码仓库确认 LoCoMo 主结果的重复次数（github.com/ViktorAxelsen/MemSkill）。
  2. 训练侧总算力与**实际演化轮数**、最终技能库规模是否穷尽（附录 C 列举 9 / 7 条，未声明是否完整）。
  3. MemEvolve（Zhang et al., 2025b）与 Mem-α（Wang et al., 2025a）原文——本篇仅在 related work 中点名区分，卡片库尚无独立卡片，建议补卡以闭合「记忆自演化」一族。
  4. ReasoningBank（Ouyang et al., 2025）同上，本篇 p3 点名为同族不同焦点。
- **需人工核对的公式 / 实现**：
  1. Eq.10–11 的 Top-K 联合概率与 Eq.15 的 PPO 比值在 K>1 时是否与 Gumbel-Top-K 采样一致（论文自称兼容，需核对 B.4 的实现）。
  2. Eq.8 的周期分取「后 1/4 步均值」在周期长度 L=100 时只有 25 个样本，方差是否过大（论文未讨论）。
  3. Table 3 的「In (K)/Out (K)」是否为千 token 单位，以及是否含 LLM-judge 调用（论文称已排除 judge 调用，需核对）。
  4. 难度分 d(q)=(1−r(q))·c(q) 中 c(q) 是「buffer 窗口内的累计失败次数」还是全局累计（p15 表述为 within the buffer window，需与 §3.4 p5 的「number of failures observed so far」对齐）。
  5. SKIP/NOOP 在演化中是否真的完全不变（Appendix C.2 p23 的 NOOP 与 C.1 p19 的 SKIP 文本略有差异，需确认是否发生过精炼）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we present MemSkill, which reframes these operations as learnable and evolvable memory skills, structured and reusable routines for extracting, consolidating, and pruning information from interaction traces” | p1（Abstract） |
| 理想记忆系统三性质：(i) Minimal reliance on human priors (ii) Support for larger extraction granularity (iii) Skill-conditioned, compositional memory construction | p1 |
| “The memory bank is trace-specific… In contrast, the skill bank is shared across traces and contains reusable memory skills.”（图 2 标注 Memory Bank **Reset Every Trace**、Skill Bank **Shared Across Training**） | §3.1 / Fig.2, p4 |
| 技能 s∈S 含 (i) description（供表示与选择）(ii) content（指示 executor 抽取或修订） | §3.2, p3 |
| 状态与技能编码：h_t = f_ctx([e(x_t); m̄_t])，u_i = f_skill(e(desc(s_i)))，z_{t,i} = f_score([h_t; u_i])，p_θ(i\|h_t)=softmax(z_t)_i（**变长技能库兼容**） | Eq.1–2, p4 |
| Top-K 无放回联合概率：π_θ(A_t\|h_t)=Π_j p_θ(a_{t,j}\|h_t)/(1−Σ_{ℓ<j}p_θ(a_{t,ℓ}\|h_t)) | Eq.3 p5；Eq.10–11 p16 |
| 奖励定义：R ≜ Eval(memory bank; training queries) ∈ ℝ（F1 / success rate） | Eq.12, p17 |
| 难例缓冲双过期规则：“cases are removed if they become too old (exceeding a maximum training step gap) or if the buffer reaches its capacity limit, which tracks recent failure patterns **without growing unbounded**” | §3.4, p5 |
| 难度分：d(q) = (1−r(q))·c(q)，r(q) 为任务奖励、c(q) 为窗口内累计失败次数 | Eq.4, p15 |
| 两阶段演化：① LLM 分析失败、识别缺失/错配的记忆行为 ② 据此精炼现有技能并提出新技能；每 100 步触发、**每轮最多 3 次技能编辑** | §3.4 p5；§4.1 p6 |
| 稳定化周期分：r̄_tail = (1/(L/4)) Σ_{t=3L/4+1}^{L} r_t；未超过历史最优即回滚到最优快照；连续若干周期无改进则早停 | Eq.8, p15；Appendix A.4 p13 |
| 新技能探索激励：Σ_{i∈S_new} p_θ(i\|h_t) ≥ τ_q，δ_q 取最小值满足约束；T_explore=50，τ_0=0.3，线性衰减 | Eq.5–7, p15 |
| 演化边界：“delete and noop operations are not evolved at this time” / 只允许 update type “insert” or “update” | Appendix D, p30 |
| 初始 4 原语：INSERT / UPDATE / DELETE / SKIP(NOOP)，各自含 Purpose / When to use / How to apply / Constraints / **Action type** | Appendix C.1, p18–19 |
| 主结果（LLaMA-3.3-70B）：LoCoMo F1 44.21 / L-J 53.82；LongMemEval F1 31.12 / L-J 60.89；avg L-J 57.36（A-MEM 43.88、MemoryOS 44.24）；ALFWorld avg SR 80.36 | Table 1, p6 |
| ALFWorld **不带** in-context 演示：MemSkill avg SR 57.71 vs LightMem 45.99（**+11.72**）；ALF-Unseen 59.70 vs 46.27；No-Memory 18.65 | Table 5, p12 |
| 消融（LoCoMo L-J）：完整 53.82 / w/o Ctrl 48.43 / w/o Des 46.50 / Ref.-only 47.45（LLaMA）；Qwen：54.14 / 42.84 / 36.15 / 48.88 | Table 2, p8 |
| 跨分布迁移（LoCoMo → HotpotQA，L-J，K=7）：50 docs 67.57、100 docs 71.48、200 docs 67.97；MemoryOS 66.02 / 67.19 / 60.55 | Fig.3, p7 |
| 成本前沿（LoCoMo）：Ours SS=512 → L-J 53.82、输入 249K、输出 18K、**调用 215 次**；MemoryOS 48.64 / 1013K / 165K / **1288 次**；A-MEM 49.71 / 2850K / 362K / 1548 次；SS=1024 掉到 48.11 | Table 3, p9 |
| 演化出的技能规定**写入 schema**：TRACK OBJECT LOCATION 要求 “object-location-state triplet”；CAPTURE TEMPORAL CONTEXT 要求 start/end/duration/sequence | Fig.4 p8；Appendix C.2/C.3 p21、p26 |
| 附录 C 列举的最终技能库规模：LoCoMo 9 条（p20–24）、ALFWorld 7 条（p24–27），均由 4 条原语演化而来；designer 只允许 add new / refine existing / no change（**无退役**） | Appendix C、D, p20–27、p30 |
| 小模型（Llama-3.1-8B）：LoCoMo F1 20.59 / L-J 27.23；LongMemEval F1 18.13 / L-J 30.20（迁移） | Table 7, p14 |
| 设置：embedding = Qwen3-Embedding-0.6B（兼作检索器，top-20）；LLM judge = openai/gpt-oss-120b；训练于 NVIDIA A6000；训练时 K=3，评测 LoCoMo/LongMemEval K=7、ALFWorld K=5；span size 默认 512 | §4.1 p6；Appendix B.1 p14 |
| 自陈局限：“This work focuses on benchmarked research settings… may require additional mechanisms for privacy protection, user consent, access control, and data retention.” | Appendix F, p32 |
| LLM 使用声明：executor、designer、judge 均为 LLM；作者声明也可用 LLM 做语法润色与代码辅助 | Appendix E, p32 |
