# 论文分析卡片 · ExpSeek

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-01-13 ExpSeek Self-Triggered Experience Seeking for Web Agents.pdf` |
| 标题 | **ExpSeek: Self-Triggered Experience Seeking for Web Agents** |
| 作者 / 机构 | Wenyuan Zhang, Xinghua Zhang, Haiyang Yu, Shuaiyi Nie, Bingli Wu, Juwei Yue, Tingwen Liu, Yongbin Li；中科院信息工程研究所（IIE CAS）、UCAS 网安学院、**Tongyi Lab / Alibaba Group** |
| 发表时间 / 出处 | arXiv:2601.08605v2 [cs.CL]，v2 标注 2026-04-15（文件命名 2026-01-13，应为 v1） |
| 论文链接 | arXiv:2601.08605 |
| 代码链接 | github.com/WYRipple/ExpSeek |
| 标签 | Web Agent · 经验干预 · 步级熵触发 · 内在不确定性信号 · 经验三元组 · 无梯度自演化 · 选择性门控 |
| **应用裁决** | **B 零件采用**（可搬的是「自触发门 + 阈值区间」这一零件；框架本体是语言 web agent，须大改） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把「经验干预」从**任务前全局注入**改为**步级主动寻求**——用模型**自身的步级 token 熵**判断「何时该求助」，用「成功/失败轨迹对」蒸馏的**经验三元组（行为-错误-指导）**决定「求什么」，在四个 web agent 基准上较 vanilla ReAct 平均绝对提升 **9.3%（Qwen3-8B）/ 7.5%（Qwen3-32B）**（Table 2, p6）。
- **对 SSEA 的意义**：它给出了「**门开得准不准**」这一 SSEA 当前最紧缺口的一个**训练免费（training-free）样板**——用一个**模型内在不确定性信号**做选择性门控，而非每步都检索。这正是 Memento 的 μ 想做、但用外部奖励 Q 做的事；ExpSeek 证明「**内在信号 + 离线标定的阈值区间**」也能当门，且代价低一个量级（Table 3, p7）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–2）：web agent 与开放网络多轮交互时，**上下文观测持续变化**；现有经验方法把经验**被动地作为全局上下文注入在任务执行前**（Fig.1-A），无法对齐动态变化的步级决策，导致次优甚至错位决策。原文设问：*"why not empower the agent to proactively seek experience during its interaction with the environment?"*（p2）。
- **它指出的既有方案缺陷**（p2–3、§B.2 p15）：
  - **离线经验**（如 Training-Free GRPO、RaDA、ExpeTrans）与**在线自演化**（如 ReasoningBank、ExpeL）**两类都把经验做成静态全局上下文**，「difficult to align with step decisions」；
  - 经验**获取与真实推理脱节**：重加工后的抽象经验，agent「可能根本看不懂」；
  - 经验**难以被利用**：在超长上下文里要求模型精确定位几条短经验并据此纠偏，本身极难（p15）。

### 2.2 核心思想（关键 insight）
1. **「何时求助」比「求什么」更缺**：最优求助时机 = 「agent 困惑、真正需要指导时」。作者用**步级熵**把「困惑」操作化为一个可计算的内生信号（p2、p4）。
2. **熵是有效的自触发信号，但对过程步/答案步强弱不同**：正确步熵系统性低于错误步（KS=0.1998 过程 / 0.3809 答案，p<0.001），但**过程步可分性弱（AUC=0.6223）**、**答案步可分性可接受（AUC=0.7187）**（p4）。故**分步型各设一条阈值**。
3. **指导要「生成」而非「检索」**：以检索最相似经验直接复用，准确率显著低于生成式指导（Table 3, p7），说明**上下文条件化的生成**才使经验与当前推理对齐。
4. **机制效应是「先发散后收敛」**：指导**抬高过程步熵**（逃离局部决策、扩大探索），**压低答案步熵并锐化峰**（更自信地收敛到正确答案）（Fig.4, §6.1 p7）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **步级熵 H̄_t** | 响应 R_t 的逐 token 分布 → 平均 token 熵 | 把「困惑/低置信」操作化为内生标量 | Eq.2, p3 |
| **正确/错误步分布可分性诊断** | 步集合 S⁺/S⁻ → KS / AUC | **先量尺子再接线**：判断熵是否可当门信号 | §4.2.1 Eq.3, p4 |
| **阈值区间估计（logistic + bootstrap）** | (H̄_t, 正确性标签 y_t) → [θ_lower, θ_upper] | 用 95% 置信区间替代单点常量阈值 | Eq.4–5, Alg.1, p4–5、p14 |
| **概率化干预 p_intervene** | H̄_t 与阈值区间 → [0,1] 干预概率 | **三区门**：安全区（不开）/ 缓冲带（概率开）/ 干预区（必开） | Eq.6, p5 |
| **一步静默（refractory）** | 上一步是否干预 → 本步禁用 | 防过度干预，给 agent 消化时间 | p5、Fig.6 p8 |
| **经验三元组（Behavior/Mistake/Guidance）** | 成功-失败轨迹对 → 结构化经验 | 可复用、按 topic 分组的经验表示 | §4.1, p3；Table 6, p17 |
| **topic 归纳** | 三元组流 → 主题标签（复用/新建/修改） | 经验库压缩、可检索 | Table 13, p25 |
| **经验模型 Me（topic 选择 + 指导生成）** | 历史上下文 h_t + 候选 topic → 3 个 topic → 步级指导 e_t | 生成式、上下文对齐的指导 | §4.3, p5；Table 14/15, p26–27 |
| **分步型注入协议** | 过程步：e_t 拼到 O_t；答案步：把 e_t 当作 O_T 续跑第 T+1 步 | 让答案步也能被拉回继续求证 | p5 |
| **模型式触发对照（RM）** | 全历史 → Claude-4 判 yes/no | 触发机制消融对照（证明熵触发更省） | Table 3, p7；Table 17, p29 |

### 2.4 关键表示与数据结构
- **轨迹** τ=(q,R₁,O₁,…,R_T)：过程步 Sᵗ_p=(R_t,O_t)、答案步 Sᵃ_T=R_T（Eq.1, p3）。
- **经验库**：按 topic 分组的三元组集合，过程步库 E_p 与答案步库 E_a **分开建**。实测规模（p6）：8B → |E_p|=196（17 topic）、|E_a|=190（11 topic）；32B → |E_p|=276（18 topic）、|E_a|=143（23 topic）。
- **阈值表**（Table 1, p5）：

  | 模型 | θᵖ_low | θᵖ_high | θᵃ_low | θᵃ_high |
  |---|---|---|---|---|
  | Qwen3-8B | 0.314 | 0.413 | 0.225 | 0.257 |
  | Qwen3-32B | 0.877 | 1.384 | 0.714 | 0.820 |

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 4 基准总评（8B） | vanilla ReAct / Training-Free GRPO / ReasoningBank+ | ExpSeek 均值 **41.50（+9.3）**；两基线增益 <3% 甚至为负 | Table 2, p6；**5 次独立运行均值** |
| 4 基准总评（32B） | 同上 | ExpSeek 均值 **45.32（+7.5）** | 同上 |
| 逐基准（8B，ExpSeek/基线） | — | WebWalkerQA **51.00**、GAIA **48.25**、SEAL **30.16**、xbench **37.20** | Table 2, p6 |
| 逐基准（32B） | — | WebWalkerQA 54.33、GAIA 51.09、SEAL 32.76、xbench 42.00 | Table 2, p6 |
| 消融：只导过程步 / 只导答案步 | 全量干预 | 8B 全量 41.50 vs 36.59（-4.91）/ 39.06（-2.44）；32B 45.32 vs 40.81（-4.51）/ 41.20（-4.12） | Table 2, p6；**只导答案步更接近全量** |
| Pass@3（Table 5, p16） | vanilla | 8B 均值 **61.89（+12.9）**、32B **64.96（+8.8）** | Pass@3，优于平均准确率增益 |
| 触发机制对照（8B/GAIA） | Rule+Me / Claude-4+Me / Entropy+emb | Entropy+Me：36.89 acc，**Rej 67.8%**，5.75 步，**127.57s**；Rule+Me 9.52 步 329.71s；Claude-4+Me 8.55 步 370.82s；Entropy+emb 30.92 acc | Table 3, p7；Step/Time 为**每题均值**，Rej=触发检查中未干预占比 |
| 触发机制对照（8B/xbench） | 同上 | Entropy+Me 37.20 acc，Rej 42.2%，5.73 步，143.81s；Rule+Me 8.52 步 300.09s | Table 3, p7 |
| 经验模型缩放（Fig.5, p7） | 4B / 30B / 235B 作 Me | **4B 指导模型仍把 32B agent 提升 5.2% / 9.7%** | GAIA / xbench |
| 经验库互换（Table 4, p8） | E-8B / E-32B | 8B agent：36.89 / 35.60；32B agent：43.88 / 40.33 | GAIA；有模型依赖但**有迁移价值** |
| 经验库规模（Fig.7, p8） | 1/1 → 1/2 → 1/4 → 1 topic/exp → 清空 | **每 topic 仅 1 条经验仍保持高准确率**；清空后性能下降但仍有收益 | Qwen3-8B |
| 干预强度扫描（Fig.6, p8–9） | 间隔 {0,1,2} × 阈值 ±0.05，共 21 组 | **~2 次干预即达 43.01%**，>6 次几乎不再提升 | GAIA |

### 2.6 论文自陈局限与边界条件（Limitations, p9）
- **阈值估计依赖训练集与 tool model 对步质量的评估**，更精确的策略待研究（第 1 条）——即**阈值是外部标定的**。
- **是否可扩展到非 web 域、更多工具，未探索**（第 2 条）。
- **能否作为 Agentic RL 的 rollout 增强，未研究**（第 3 条）。
- 隐含依赖：需要**任务级 ground truth**（成功/失败标签）来配对轨迹、拟合阈值；需要**强 tool model（235B）**来抽取三元组与生成指导；ReAct + 语言工具（Search/Visit）范式。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 全篇是 ReAct **语言生成回路**（thought/tool_call/answer 标签，Table 11 p23），经验以自然语言注入 | 只借「内生信号触发门」的形状；把信号改到结构化动作分布上，回路换为 FSL |
| **C2** 自然语言只作观察员接口 | **✗** | 核心动作是**生成自然语言 `<guidance>` 并注入上下文**（§4.3 p5、Table 15 p27）——语言在控制闭环内 | 保留「门」；把「指导内容」换成结构化 ΔM/ΔR 注入面，或整体降级为慢环离线产物 |
| **C3** 权重/记忆/技能三分离 | **◐** | agent 权重冻结（无微调），经验库为外置记忆；但无「技能层」概念，Me 是第二个 LLM（近工具） | 经验库归 ΔM；把 Me 的「指导生成」改造成技能/规则侧的结构化供给 |
| **C4** 低算力低带宽 | **✓** | **熵触发近乎免费**（logits 已算），把干预压到稀疏：Rej 67.8%（GAIA）/42.2%（xbench）；同精度下 Entropy+Me 127.57s vs Rule+Me 329.71s（**2.6× 时间差**）（Table 3, p7） | 直接借「便宜门挡住昂贵检索」这一结构；注意 Me=235B 触发时仍贵（GAIA 66.94s→127.57s） |
| **C5** 精准回忆历史 | **◐** | 经验库按 topic 组织、三元组结构化（Table 6, p17）；但取回是**topic 选择 + 生成式改写**，非精确情景回放 | 落库精确、取回可选择性；把「生成」与「精确取回」职责分离（呼应 Memento §4） |
| **C6** 可自主修改自身 | **—** | 无代码/权重自修改；经验库离线构建，在线只「求助」 | 若搬，仅映射为**门控参数（阈值）的慢环更新**，非在线自改 |
| **C7** 可保存/恢复/变异/继承 | **◐** | 经验库/topic 可序列化、可互换（Table 4, p8）；**无跨个体继承、无变异** | 经验库作 GenePackage **素材**，继承需另设筛选（且受 C8 约束） |
| **C8** 给基因先验，不给知识语料 | **◐** | 轨迹由 agent 自采样，但**三元组由 235B tool model 蒸馏**、标签来自 ground truth——部分是**强模型蒸馏知识**，非纯自生成 | 经验库只能留个体记忆（L3）；**禁止进基因包**（否则违反「知识不跨代」） |
| **C9** 不设评分函数，只有淘汰函数 | **◐** | **触发信号=模型自身 token 熵（内在不确定性）→ 合法，正是 C9 第二层「内在驱动」形态**；但**阈值由 (熵, ground-truth 正确性) 的 logistic 回归标定**，且局限自陈依赖「tool model 的步质量评估」（p9）——**边界来自外部监督** | 信号保留；**阈值改由内在量（运行期熵统计/预测误差分布）或慢环用环境淘汰结果标定**，绝不引入步级评分/奖励；删掉 tool model 判步质量这一路 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 创新在「何时注入」的信息流机制（L2）与阈值估计方法（L3），无新算子（p5–7） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；Qwen3-8B/32B/235B 均现成件 | 符合「借用」立场 |
| **L2 信息流层** | **步级内生信号 → 门 → 按需注入**的信息流范式（Fig.1-B, p1）；分步型注入协议 | **最高**：直接对应 SSEA「记忆门选择性」缺口 |
| **L3 学习层** | 阈值区间估计（logistic+bootstrap）、topic 归纳、经验模型缩放 | 中高：门控参数的离线标定规程 |
| **L4 演化层** | 经验库可序列化/互换（无继承变异） | 中：基因包内容参照 |

### 3.3 模块映射
| 论文构件 | SSEA 落点 |
|---|---|
| **步级熵 H̄_t** | `surprise_estimator.py`：在**结构化动作分布**上定义同构量（动作熵 / 世界模型预测误差），替代语言 token 熵 |
| **阈值区间 [θ_low, θ_high] + 概率化干预** | **记忆二级门（债务 22）**：以「区间 + 三区概率门」替换常量阈值，对接 `plasticity.py` |
| **可分性诊断（KS/AUC）** | 新增「尺子质检」步骤：接线前先量 SSEA 惊奇信号能否区分正/错帧 |
| **一步静默（refractory）** | 记忆门节流器：防过度召回，保 C4 |
| **经验三元组 + topic 库** | `memory_system.py`：经验/教训落库格式（对照 FLEX golden/warning） |
| **经验模型 Me** | 慢环「指导供给器」的对照物；**SSEA 版应换成结构化 ΔM/ΔR 生成，非语言** |
| **Pass@3 / 干预强度扫描（Fig.6）** | 记忆门验收的**分档判据**参照（机制计数→行为差→结果） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **债务 22（记忆二级门用常量阈值、慢环不可调）**：→ 阈值**区间** + 概率门 + 慢环可标定，直接给出替代形状。
  - **「门开得准不准」选择性缺失**：→ **本卡片的核心贡献**。ExpSeek 提供「内在信号门」的最简可跑形态。
  - **`retrieve` 键收窄 → 召回精度上限低**：→ topic 分层 + 生成式对齐可作键函数改造参照。
- **可服务的验收实验**：**实验 2（记忆召回）增强**——加一条「选择性门」臂；以及记忆门选择性的**独立验收**（见 §8）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **内生不确定性自触发门**（模型自决「何时求助」） | 思想/机制 | **改造移植** | `surprise_estimator` + 记忆门 | 「门开得准不准」的选择性缺失 | 高 |
| 2 | **阈值区间 + 三区概率化干预**（Eq.5–6） | 算法 | **改造移植** | 记忆二级门（债务 22） | 常量阈值不可调、无缓冲带 | 高 |
| 3 | **接线前的可分性诊断（KS/AUC）** | 方法/协议 | 直接移植 | 慢环验证门 / 仪器侧 | 防止「用无区分度的信号当门」 | 高 |
| 4 | **一步静默 / 干预间隔扫描** | 工程实现 | 直接移植 | 记忆门节流 | 过度召回、C4 预算 | 高 |
| 5 | **经验三元组（行为-错误-指导）+ topic 分组** | 表示 | 改造移植 | `memory_system` 落库格式 | 教训型记忆的结构化 | 中 |
| 6 | **「先发散后收敛」机制证据** | 证据 | 直接引用 | 慢环/快环设计 | 门的作用方向可预期 | 中 |
| 7 | **经验模型缩放律（4B 指导 32B）** | 证据 | 直接引用 | 慢环指导供给 | 弱→强指导可行性 | 中 |
| 8 | **经验库互换的迁移性证据（Table 4）** | 证据 | 直接引用 | GenePackage 素材 | 记忆跨个体迁移边界 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 的 ✗/◐）：
  1. **C1/C2 硬冲突**：整个框架是**语言生成回路 + 自然语言指导注入**（`<guidance>`）。SSEA 控制环不能收语言。→ 只搬「门的形状」，指导内容须换成结构化 ΔM/ΔR。
  2. **C9 半冲突**：触发信号（熵）合法，但**阈值由 (熵, ground-truth 正确性) 的 logistic 回归标定**，且自陈依赖「tool model 判步质量」（p9）——**外部监督定义了门的边界**。→ 阈值改由内在量或慢环用**环境淘汰结果**标定，删除 tool model 判步质量一路。
  3. **C8 张力**：三元组由 235B **强模型蒸馏**，非纯自生成 → 经验库**只能留 L3 个体记忆，禁止进基因包**。
- **隐含假设与失效条件**：
  - 需要**任务级 ground truth**（配对成功/失败轨迹、拟合阈值）——无标签环境直接失效；
  - 需要**强 tool model** 抽取三元组与生成指导；
  - **熵是「不确定性」的代理**：论文自陈**过程步 AUC 仅 0.6223（弱区分）**（p4）——信号本身不够锐利，门可能开错；SSEA 若信号 AUC≈0.5，搬门无用。
- **算力 / 带宽 / 工程代价**：
  - **触发侧极廉**（logits 已算），这是最大卖点；
  - **干预侧贵**：Me=235B 生成指导，GAIA 66.94s→127.57s（≈1.9×）（Table 3, p7）；
  - 离线阈值估计「秒级」（§A.1 p14）可忽略。
- **搬运后的可能退化模式**：
  1. 信号无区分度 → 门退化为**随机开**（论文 32B 过程步黄区大，正是「高不确定下随机化」p15）；
  2. 阈值外部标定被删后 → **门失去校准**，开得太频（退回 Rule）或太疏（漏召回）；
  3. 语言指导换结构化注入 → **信息量骤降**，收益消失（论文已证检索式复用显著差于生成式，Table 3）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 内生不确定性信号、离线标定数据、可序列化经验库 | SSEA 已有 `surprise_estimator`、慢环、记忆落库 |
| **互补（最紧）** | **Memento** | Memento 的 μ 是**可学习**的门（需奖励 Q，C9 冲突）；ExpSeek 是**训练免费**的内生信号门（C9 半合规）。**同一问题的两条路线**：可先用 ExpSeek 门做零成本基线，再让 Memento 的 μ 只在 ExpSeek「缓冲带」内学习 |
| 互补 | **MemRL**（两阶段检索） | ExpSeek 门 = **阶段 0 触发器**：门开 → 进入 MemRL 的粗→精两阶段检索，省掉无谓的两阶段开销 |
| 互补 | **AgentFold**（主动上下文管理） | 二者都主张「主动」：AgentFold 主动**折叠内部上下文**，ExpSeek 主动**索取外部经验**；拼起来=「内折外取」双主动 |
| 互补/同族 | **Memory as Action**、**DynamicCheatsheet**、**RecordReplay** | Memory as Action 把记忆操作当动作（ExpSeek 的「求助」本质是一次主动记忆动作）；DynamicCheatsheet 是运行时自适应备忘（ExpSeek 经验库是其同族）；RecordReplay 录-放轨迹（ExpSeek 三元组构建的输入正是成功/失败轨迹对）。**三者均未在 §3 已有卡片中，需补卡** |
| **直接对照/被超越** | **ReasoningBank** | **本篇的被动注入基线**：ReasoningBank 把经验检索进 system prompt（全局静态），ExpSeek 超越其 6.7%/6.0%（p2）。SSEA 若曾参照 ReasoningBank 的「检索即注入」，应以 ExpSeek 为升级方向 |
| 互补 | **FLEX** | FLEX 管**写入侧**（golden/warning + logistic 停机）；ExpSeek 管**取用侧**（何时取）。二者拼成「写-取」完整闭环 |
| 互补 | **Dream-RSI** | Dream-RSI 重放=可评估世界；ExpSeek 门=决定「何时在重放中调取经验」。慢环离线标定阈值可在重放上做 |
| 替代 | 常量阈值门、每步检索、Rule 式连续干预 | 以「内生信号门 + 阈值区间」替换钝器与暴力触发（Table 3 已证效率差 2.6×） |
| 待防 | **Misevolve** | 门失效（开错/开乱）属「记忆路径误演化」，应纳入 Misevolve 红队清单 |
| 训练侧 | **RAGEN** | 若后续把阈值门升级为可学习门，RAGEN 的 Echo Trap/稳定性手册适用 |

### 6.2 推荐组合方案
1. **零成本选择性门（ExpSeek × SSEA 记忆门）**
   - 形态：在 `retrieve` 前插一道**内生信号门**（区间 + 三区概率 + 一步静默），替换常量阈值。
   - 新增能力：**选择性召回**——「惊帧开、平帧关」，且不引入任何学习/评分。
   - 纪律：阈值只准由**内在量或慢环环境淘汰结果**标定（C9）。
2. **门 + 两阶段检索（ExpSeek × MemRL）**
   - 形态：门开 → MemRL 粗筛→精排；门关 → 不检索。
   - 新增能力：把 MemRL 的成本压到只在「需要」时发生（C4）。
3. **写-取闭环（ExpSeek × FLEX）**
   - FLEX 负责写入/组织（golden/warning、logistic 停机），ExpSeek 负责取用时机。
   - 新增能力：经验「进得来、出得准」。
4. **可学习门的起点（ExpSeek → Memento）**
   - 先用 ExpSeek 门建基线；再在缓冲带内用 Memento μ（信号改惊奇驱动）细化，形成「廉价先验门 + 可学习精调」。

### 6.3 本篇在组合中的典型角色
- **选择性门控器 / 触发时机供给方**：一端读模型内在不确定性，一端决定「这一刻要不要动用昂贵的外部经验/检索」。它是 SSEA 记忆链上**最缺的那道「准不准」的闸**。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 主张即 SSEA 当前最紧缺口「记忆门选择性」。**实测**（Table 2/3） |
| 立场兼容性 | **2** | C4/C10 强对齐；C1/C2 硬冲突（语言回路+语言注入）、C9 半冲突（阈值外部标定）、C8 张力（强模型蒸馏）。**推断** |
| 可搬运性 | **4** | 门机制（区间+三区概率+静默）干净可拆；但熵定义在**语言词表**上，需在结构化动作分布上重建。**推断** |
| 证据强度 | **4** | 4 基准 × 2 骨干 × 5 seed，含 Pass@3、触发消融、缩放律、库互换、强度扫描；**无生存域证据**。**实测** |
| 组合价值 | **5** | 与 Memento/MemRL/AgentFold/FLEX/Dream-RSI 天然互补，且是 ReasoningBank 的直接升级。**推断** |
| 落地成本 | **4** | 触发侧近零成本；主要成本是「把语言熵换成结构化信号熵」与「阈值改内在标定」。**推断** |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：**可搬的是「自触发门 + 阈值区间 + 可分性诊断」这一零件**，它精确命中 SSEA 记忆门选择性缺口；但**框架本体（ReAct 语言回路 + 自然语言指导注入 + 外部标定阈值）与 C1/C2/C9 冲突**，不能整篇照搬。
- **优先级：P1**（与 Memento 同档；两者是同一缺口的「训练免费 vs 可学习」两条腿）。
- **建议动作**：
  1. 在 `surprise_estimator` 上定义**结构化内生信号**（动作分布熵 / 世界模型预测误差），先跑 **KS/AUC 诊断**——信号 AUC 不显著优于 0.5 就**先修信号，别接线**；
  2. 以「**阈值区间 + 三区概率门 + 一步静默**」替换记忆二级门常量阈值（债务 22），阈值由**内在统计或慢环环境淘汰结果**标定；
  3. 落库采用「行为-错误-指导」式三元组 + topic 分组（对照 FLEX golden/warning），**禁止进基因包**（C8）；
  4. 把「指导内容」从自然语言换成**结构化 ΔM/ΔR 注入**，删掉外部 tool model 判步质量一路（C9）；
  5. 门失效场景纳入 **Misevolve** 红队清单。
- **最小验证实验**：
  - **双臂/消融**：① 常量阈值门（现状）② 内生信号区间概率门（ExpSeek 式）③（可选）常开门；≥8 固定 seed；
  - **判据（分档）**：**先看分母**（触发率 / 未干预率 Rej）→ 逐帧动作差（被取回内容是否改变动作）→ 淘汰结果（模型外）；
  - **预期与证伪**：若内生信号 AUC 显著 >0.5 且门使**部分 seed 改变动作**→ 门有效；若 AUC≈0.5（过程步式弱信号）或动作无差异 → **先怀疑尺子/信号，而非门**；若「开得少但结果不变」→ 说明当前环境对召回不敏感（与 Memento 库饱和互证）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. 阈值能否**去掉 ground-truth 标签**，改用内在量（运行期熵分位/预测误差）标定？其性能损失多大？（C9 改造的核心问号）
  2. 「熵」若换成 SSEA 的**结构化动作分布熵**，是否保留可分性？（论文只在语言词表上验证）
- **需补查的文献或资料**：
  3. **Memory as Action / RecordReplay / DynamicCheatsheet / AgentFold** 尚无 SSEA 卡片，需补卡以闭合 §6 关系图谱；
  4. ReasoningBank 原文，以明确「被动注入」基线的确切形态。
- **需人工核对的公式 / 实现**：
  5. Table 2 数字排版混乱（每值后附「- 0.0」占位），已按列语义还原，**建议对表核对**；
  6. Alg.1 阈值 θ=-b/w 与 Eq.6 三区映射的边界一致性（θ_low 处 p=0、θ_high 处 p=1）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "shifts experience toward step-level proactive seeking … estimating step-level entropy thresholds to determine intervention timing using the model's intrinsic signals" | p1（摘要） |
| "why not empower the agent to proactively seek experience during its interaction with the environment for more precise guidance?" | p2 |
| Eq.2 步级熵 H̄_t = (1/\|R_t\|) Σ H(x)，H(x_i)=−Σ P(v\|h_i)logP(v\|h_i) | p3 |
| "process steps: KS=0.1998, p<0.001 … AUC=0.6223（weak）; answer steps: KS=0.3809 … AUC=0.7187（acceptable）" | p4 |
| Eq.4 logistic P(y_t=0\|H̄_t)；Eq.5 bootstrap 95% CI；θ_lower=Q₀.₀₂₅, θ_upper=Q₀.₉₇₅ | p4–5 |
| Table 1 阈值区间：8B [0.314,0.413]/[0.225,0.257]；32B [0.877,1.384]/[0.714,0.820] | p5 |
| Eq.6 概率化干预 p_intervene（0 / 线性 / 1 三区）；"we disable intervention at step t+1 after any intervention at step t" | p5 |
| "average absolute improvements of 9.3% and 7.5% over vanilla ReAct on Qwen3-8B and 32B" | p6 |
| Table 3 "Rule-based triggers result in 1.7× step and 2.6× time overhead … compared to entropy-based triggering"；Entropy+Me 127.57s vs Rule 329.71s | p7 |
| "guidance increases entropy in process steps … conversely, the entropy distribution of answer steps shifts toward lower values with a sharper peak"（先发散后收敛） | p7 |
| "the 4B guidance model improves the 32B agent by 5.2% and 9.7% points … weak-to-strong guidance" | p7 |
| "even with just one experience per topic, Me still identifies key intervention points"；"removing the repository entirely degrades performance" | p8 |
| "With ~2 interventions, accuracy reaches 43.01%; beyond 6 interventions, performance barely improves" | p9 |
| Limitations: "threshold estimation relies on the training set and the tool model's assessment of step quality" | p9 |
| "estimating thresholds for one step type completes within seconds … offline computation time is negligible" | p14 |
| Table 5 Pass@3："absolute improvements in pass@3 are 12.9% and 8.8%, exceeding the improvement margins in average accuracy" | p15 |
| Table 6 经验三元组 demo（Behavior / Mistake / Guidance） | p17 |
