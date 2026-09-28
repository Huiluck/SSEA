# 论文分析卡片 · SkillNet

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-02-26 SkillNet Create, Evaluate, and Connect AI Skills.pdf` |
| 标题 | **SkillNet: Create, Evaluate, and Connect AI Skills** |
| 作者 / 机构 | Yuan Liang、Ruobin Zhong、Haoming Xu、Chen Jiang（共同一作）等；通讯 Ningyu Zhang、Huajun Chen 等。浙江大学 + 同济、东南、Alibaba、Ant Group、Tencent、OPPO、HomologyAI、UCLA、UCSD、Edinburgh、Monash、NUS、NTU、Honor 等（p1） |
| 发表时间 / 出处 | arXiv:2603.04448v3 [cs.AI]，2026-08-23（v1 2026-02，预印本，34 页） |
| 论文链接 | arXiv:2603.04448；官网 http://skillnet.openkg.cn |
| 代码链接 | https://github.com/zjunlp/SkillNet |
| 标签 | 技能基础设施 · 技能本体（taxonomy/relation graph/package）· 多维质量评估 · 技能路由 · 组合基准 |
| **应用裁决** | **B 零件采用**（关系四类型 + pre/post 场景契约 + 二值组合完备度指标可干净拆出；但语言载体、500k 知识语料、LLM 评分评估三项与 C2/C8/C9 硬冲突，且其组合机制自身是 LLM 高算力管线，不能作主干） |
| 优先级 | **P2**（依赖 PSN 先落地技能契约；本片补 PSN 未覆盖的「连接/组合」环） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：技能不应是散落脚本，而应被组织为**统一本体下的技能网络**——三个动作
  **Create**（从轨迹/仓库/文档/提示四类异构源用 LLM 生成 SKILL.md 技能）、**Evaluate**
  （Safety/Completeness/Executability/Maintainability/Cost-awareness 五维 LLM 评分准入）、
  **Connect**（similar_to / belong_to / compose_with / depend_on 四类关系 + pre/post 场景
  匹配构成的技能 DAG），在 60 万候选、50 万精选技能上运转，使 agent 在 ALFWorld/WebShop/
  ScienceWorld 上平均奖励 +40%、交互步数 −30%（p1、p3、p5、p8、p9–10）。
- **对 SSEA 的意义**：SSEA 技能侧只答了 **Create**（经验编译器产 ΔS）与 **Evaluate**（验证门，
  但成熟度门控缺失），**Connect 整环空缺**——技能库里没有任何技能间关系。SkillNet 提供
  「连接」的**最小形状**：把技能表示成 **pre/post 场景契约**，把「能不能组合」降为
  **post→pre 的结构匹配**（不需要环境 rollout）。这正是 SSEA 悬置的「睡眠期离线试组合」
  所需的低算力形状候选——但 SkillNet 自己的实现是 LLM 管线，**形状可搬、实现不可搬**。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–3）：agent 缺「把情景经验固化为可迁移技能」的统一机制，导致反复
  「reinvent the wheel」；技能散落在 prompt、脚本、孤立 workflow 里，质量/可靠性/可复用性
  从不被系统评估。
- **它指出的既有方案缺陷**（p3、p24–25）：
  1. 无统一机制**获取并巩固**技能——专家经验虽存在于开源仓库/论文/执行轨迹中，但
     「largely unstructured and disconnected」；
  2. 无原则性框架**验证并维护**大规模技能质量——既有仓库只靠社区指标（stars）或下游任务
     成功率间接评估，导致仓库「pollution」与技术债；
  3. 既有平台（ClawHub/SkillsMP/SkillHub/Skills.sh）是**静态包管理器或市场**：手工策展、
     无自动生成、技能被当作孤立实体 → 冗余、脆弱、可组合性差（Table 8，p25）。

### 2.2 核心思想（关键 insight）
1. **技能是统一知识表示**，桥接「非结构化语言理解」与「结构化、机器可执行的逻辑」；
   载体是自文档化的结构化文件夹（核心 `SKILL.md`），渐进三步使用：Discovery（只载元数据）
   → Activation（读全文指令）→ Execution（执行捆绑代码/资产）（p3–4）。
2. **技能必须被「连接」才有价值**：孤立技能无用，价值在**关系**。四类关系
   `similar_to`（可互换/冗余检测）、`belong_to`（子步骤/层级）、`compose_with`（常共现、
   前者的输出被后者消费）、`depend_on`（无前置则不能执行）（p8）。
3. **组合可行性 = 场景对接**：为每条技能抽 **pre-scenario**（适用前状态）与
   **post-scenario**（成功执行后状态），把 `post_A` 与 `pre_B` 做匹配 + LLM 裁决，
   匹配成功即建 `compose_with` 边 → 技能图成为**技能中心的 DAG**（p11–12、p33）。
4. **可用性 ≠ 成形**：路由分两阶段——扩大候选集 `𝒮_q` 只提高**可用性**；最终集合
   `𝒴_q` 由 Explorer 在 Wiki 上比较成形。候选过多反而使成形变差（全池 FinalFullCoverage
   38.22% < L=10,000 时 57.78%）（p17、p22）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **技能本体三层** | taxonomy（category/tag）→ relation graph → package library | 功能分类 + 关系 + 物理打包的骨架 | §3.2 p5、Fig.3 |
| **四类关系** `similar_to`/`belong_to`/`compose_with`/`depend_on` | 技能对 → 类型化有向边 | 连接环的关系词汇表 | §3.5 p8 |
| **pre/post 场景契约** | 技能规格 → （pre-scenario, post-scenario） | 把技能变成可对接的「端口」 | §5.2 p11、§C.1 p33 |
| **post→pre 匹配建边** | `post_A` 嵌入 → 检索 `pre_B` 候选 → LLM 裁决 | 组合可行性判定，**无需环境 rollout** | §5.2 p11–12 |
| **技能契约（Fabric）** | 技能源 → 契约 `𝒞`（能力/使用条件/输入/输出，字段锚回源行） | 检索与关系构建的紧凑表示 | §6.3 p17–18 |
| **两阶段路由** | 任务 q → 混合种子检索（BM25+dense+RRF）→ 关系扩展 → 任务 Wiki → Explorer 成形 `𝒴_q` | 可用性/成形解耦 | §6.4–6.5 p18–19、Eq.1–4 |
| **组合模式采样** | 技能 DAG → 子图（chain/fan-out/fan-in/diamond，2–5 技能） | 自动合成组合任务 | §5.3 p12 |
| **二值组合完备度指标** | 检索/编排结果 → Skill Retrieval / Orchestration Completeness | 「先看分母」的判据形状 | §5.6 p13 |
| **五维评估** | 技能 → Good/Average/Poor ×{Safety,Completeness,Executability,Maintainability,Cost-awareness} | 准入过滤（**评分性，C9 冲突**） | §3.4 p6–7 |
| **失败分类法** | 坏例 → Knowledge Bias（59.6%）/ Instruction Override（40.4%） | 技能注入反效果的归因 | §5.9 p15–16、Fig.8 |

### 2.4 关键表示与数据结构
- **Skill**：结构化文件夹，核心 `SKILL.md` = 元数据（name、description、使用条件）+
  分步指令；可选脚本/模板/文档，构成自包含能力包（p3–4）。
- **SkillOntology**：三层——Skill Taxonomy（10 功能类 × 细粒度 tag）、Skill Relation Graph
  （节点=技能实体，边=四类关系）、Skill Package Library（`packaged_in` 打包）（p5–6、Fig.3）。
- **Skill Contract（Fabric）**：`stated capability / use conditions / inputs / outputs`，
  字段**锚回源行**（source-grounded），供检索与关系构建（p17–18）。
- **Skill DAG**：技能中心有向图；边存 source/target、supporting scenarios、alignment types、
  confidence/retrieval scores、scenario-level evidence（p33）。
- **Routing space**：`ℛ_q=(𝒮_q,ℰ_q)`，`𝒴_q=π(q,ℛ_q;K)`（Eq.1，p17）。
- ⚠️ 表示与 SSEA 的关键差异：SkillNet 的**技能体是自然语言指令**（SKILL.md），
  SSEA 的 `Skill` 是 `precondition`（option 的 initiation set 谓词）+ `action_sequence`
  （policy，绝对动作序列）——**无语言**（`SSEA/skill_library.py:41-49`）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| ALFWorld/WebShop/ScienceWorld（R↑/S↓） | ReAct / Expel / Few-Shot | SkillNet 平均奖励 **+40%**、交互步数 **−30%**；o4 Mini +15.7 R、Gemini 2.5 Pro +28.5 R；Claude Sonnet 4.6 ALFWorld Seen 95.71 | 4 backbone × seen/unseen；Table 1 p9、p10 |
| 评估器可靠性 | 3 名 PhD 标注员盲评 | 200 随机技能，MAE **<0.03**、QWK **>0.90**（五维） | n=200，Fig.4(b) p7 |
| 技能质量分布 | — | Safety/Maintainability「Good」占比高；**Executability 偏 Average** | Fig.4(a) p7 |
| SkillNet-Gym（技能检索/编排） | No Skill / Official Skill / Skill-Creator / Retrieve / Orchestration | 8 模型 × 2 harness × Easy(77)/Hard(82)，159 任务；**Hard 任务检索分常高于 Easy，但编排分大幅下滑** | Avg@k，k=3；Table 3 p13–14 |
| 组合基线 | SkillRouter/SkillRet/AgentSkillOS | 专用组合基线**强于 agent**：SkillRet Complete Recall 59.12、SkillRouter w/ Reranker 44.03 vs Agent 18.83 | Table 4 p15 |
| 失败类型 | 人工+AI 归因 | Knowledge Bias **59.6%** / Instruction Override **40.4%** | Fig.8 p15 |
| 域依赖 | — | Geospatial **+50.0 pp**、Information Extraction +33.3 pp；Academic Research **−6.2 pp**、Business Compliance −4.2 pp | Fig.9(a) p16 |
| 拓扑依赖 | — | **单技能任务几乎无增益**；Chain/Fan-out/Fan-in 增益最大；Diamond 方差最大 | Fig.9(b) p16 |
| Fabric 路由（SkillRouter Hard） | BM25/BGE/Qwen3/SkillRouter | 79,141 候选；K=5 Recall **67.91%**/FullCoverage 49.33%；K=10 **74.80%**/60.00%（较官方 SkillRouter +5.38/+9.33 pt） | 75 任务，macro；Table 5 p18–20 |
| Fabric 下游 | SkillRouter/SkillsVote/Golden/Full Pool | SkillsBench 87 任务：**46.08%**（GPT-5.4 mini）/ **66.67%**（GPT-5.6 Terra）；AgentSkillOS Pool Mean 64.21/83.00 | 95% CI；Table 6 p20 |
| Wiki 组件消融 | 去 graph expansion / relation evidence / contract cards / complete sources | 完整 Wiki BT **65.51**，每项消融 ≥−11.36；token 用量与质量**非单调** | 30 任务、500 技能池；Table 7 p21 |
| 可用性 vs 成形 | L∈{10…10000, 全池} | CandidateFullCoverage 44%→100%；FinalFullCoverage@10 峰值 57.78%（L=10,000）后**降至 38.22%（全池）** | 75 任务 × 3 Explorer；Fig.14 p22 |

### 2.6 论文自陈局限与边界条件
- **假设依赖**：技能以自然语言 `SKILL.md` 为载体，执行者与评估者均为 LLM（Claude Code /
  Codex CLI harness）；评估为 LLM 评分，安全评估「不替代部署级安全验证」（p7、p26）。
- **明确不适用/未解决**（§10 p26）：
  1. 技能覆盖**必然不完整**——私有/专业域、低频或**抗拒语言显式描述的隐性能力**难以捕获；
  2. 自建技能质量**不能完全保证**；恶意「poisoned/adversarial」技能，Safety 评估**只能检出部分、
     无法完全缓解**；
  3. **尚未建立**「自然语言需求 → 完全实例化 agent」的端到端管线。
- 预印本；核心实验全在文本模拟环境（ALFWorld/WebShop/ScienceWorld + 自建 SkillNet-Gym），
  **无生存/具身控制域**实验。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 面向语言 agent 的技能基础设施；运行时由 LLM 读指令执行（Discovery→Activation→Execution，p4），无控制环、无生存信号 | 只借**离线**关系/契约层；运行时技能必须是非语言程序 |
| **C2** 自然语言只作观察员接口 | **✗（最硬冲突）** | **语言就是技能体**：`SKILL.md` 全文指令在 Activation 阶段进入执行闭环（p4）；评估/关系/路由全由 LLM 承担 | 把 LLM 严格限制在**慢环编译面**（生成 pre/post 契约与关系），快环零语言 |
| **C3** 权重/记忆/技能三分离 | **◐** | 明确不微调权重；技能外置为文件（分离 ✓）；但「memory」非其核心，仅 §9 提「workflows/memory/skills 三约束」（p25） | 采纳「技能外置、独立于权重」；记忆侧仍由 Memento/FLEX 承担 |
| **C4** 低算力低带宽 | **✗/◐** | 60 万候选/50 万精选；每条技能 LLM 评分；关系由 LLM 推理；Wiki Explorer 每任务 27.8K token，扫描至 200–800K（Fig.13a、14c p21–22） | **只搬形状**：post→pre 匹配用结构化谓词 + 嵌入近邻，不用 LLM 裁决 |
| **C5** 精准回忆历史 | **◐** | 非核心；轨迹是创建输入，技能是固化产物；无外置可检索的情景记忆机制 | 记忆侧交 Memento/FLEX/MemRL |
| **C6** 可自主修改自身 | **◐** | 「self-evolving skill ecosystem」（p6）；OpenClaw 集成中任务后自动 `skillnet create` 入库（p24）——但这是策展管线，无提案/边界/验证/应用四权分离 | 映射为「慢环提案 → 四级验证门」的受控自修改 |
| **C7** 可保存/恢复/变异/继承 | **◐** | 技能文件化、版本可控、可跨 agent 复用（保存 ✓）；「digital persona 可 inherit/share」（§9 未来工作，p25–26）——**无变异/继承机制实现** | 成熟技能作 GenePackage 候选；继承仍需 HeritableFilter |
| **C8** 给基因先验，不给知识语料 | **✗** | 整个前提是**50 万+ 技能知识语料**从互联网/文档/仓库策展而来（p1、p9）；这是知识语料而非结构先验 | 只把**契约 schema**（pre/post 字段形状）当结构先验；语料不入基因 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（第二硬冲突）** | 五维 LLM-rubric 评分 + Good/Average/Poor 三档 + 对准人类标注的 QWK 验证（p6–7）；SkillsBench 用 verifier reward、AgentSkillOS 用 Bradley–Terry 分（p20） | **只保留二值合法性**：Executability 沙盒 pass/fail、组合完备度布尔（Complete Recall/FullCoverage）；**删掉一切分档评分与排序** |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **◐/✓** | 无新算子；创新在技能本体、关系图、路由（偏 **L2 信息流/组织**）；L3 自修改与 L4 演化**几乎不涉及** | 采纳 L2 组织层；L3/L4 仍需 PSN/Misevolve |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；LLM 为现成件 | 符合借用立场 |
| **L2 信息流层** | 技能本体、四类关系、pre/post 契约、两阶段路由、Wiki | **高**：SSEA 缺的「连接环」的 L2 形状 |
| **L3 学习层** | 技能创建/巩固管线、质量准入（弱，无自修改回路） | 中：Create 侧与评估准入的形状 |
| **L4 演化层** | 无（仅 §9 展望继承） | 低：演化需另找（Misevolve/PSN） |

### 3.3 模块映射
| 论文构件 | SSEA 落点 |
|---|---|
| 四类关系 `similar_to`/`belong_to`/`compose_with`/`depend_on` | **新增 `SkillRelationGraph`**（`skill_library` 之上）：技能库首次有技能间边 |
| pre/post 场景契约 | `Skill.precondition`/`expected_outcome` 升级为显式 **pre/post 契约**（与 PSN 契约同构） |
| post→pre 匹配建边 | **慢环「离线试组合」**：候选组合由「图可达性检查」生成，无需快环/环境步进 |
| 两阶段路由（可用性 vs 成形） | `retrieve` 键收窄问题：瓶颈不止候选可用性，**比较/成形阶段**也限精度 |
| 二值组合完备度指标 | 实验 3 / 债务 26 的判据形状（先看分母：可检索技能数、可成形组合数） |
| 五维评估（评分） | **改造为二值合法性门**（只留 Executability 沙盒 pass/fail 与组合完备布尔） |
| 失败分类法（Knowledge Bias/Instruction Override） | 技能失效归因（债务 26「技能失效被判成成功」的对照词汇） |
| SkillNet-Gym 组合任务合成 | 技能组合基准的构建形状（离线合成、不依赖真实环境） |
| 技能网络健康指标（库规模、关系密度、拓扑） | 债务 26 的结构性指标补充 |

### 3.4 债务与验收实验对应
- **「技能表示够不够」（0/33 之后仍未回答）**：SkillNet 直接回答——平铺的
  `action_sequence` 不够，需 **pre/post 契约 + 关系边**；且**单技能任务几乎无增益、
  组合任务才有增益**（Fig.9b p16）印证「表达力上限」是真问题。
- **「睡眠期计算预算未定义」（前瞻预演硬门槛）**：SkillNet 提供**低算力形状**——
  组合可行性用 **post→pre 结构匹配**判定，**不需 rollout**；但论文自身用 LLM 裁决，
  故只能借「形状」并**另行定义预算**（结构化匹配的次数/深度上限）。
- **「`retrieve` 键收窄 → 召回精度上限低」**：Fig.14 说明瓶颈在**两处**——候选可用性
  与成形阶段；单纯放宽键不够，需两阶段设计。
- **债务 26（判据形状）**：二值组合完备度 + 失败分类法提供可计数、可看分母的判据形状。
- **实验 3（技能固化）**：技能组合任务（chain/fan-out/fan-in）可作新判据的载体。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 四类技能关系词汇表（similar/belong/compose/depend） | 表示/协议 | 改造移植 | 新增 SkillRelationGraph | 连接环空白、技能库无技能间边 | 高 |
| 2 | **pre/post 场景契约 + post→pre 匹配建边** | 算法/表示 | 改造移植（去 LLM） | 慢环「离线试组合」 | **睡眠期试组合的低算力形状** | 高 |
| 3 | 两阶段路由（可用性 vs 成形） | 方法 | 仅借思想 | retrieve / 慢环规划 | `retrieve` 键收窄、召回精度上限 | 中 |
| 4 | 二值组合完备度指标（Complete Recall / FullCoverage） | 指标 | 改造移植 | 实验仪器、债务 26 | 实验 3 判据形状 | 高 |
| 5 | 失败分类法（Knowledge Bias / Instruction Override） | 概念 | 仅借思想 | 技能失效归因 | 债务 26「失效被判成功」 | 中 |
| 6 | 技能契约（能力/条件/输入/输出，锚回源行） | 表示 | 改造移植 | Skill 规格升级（与 PSN 契约合并） | 技能可检查、可对接 | 中 |
| 7 | SkillNet-Gym 组合任务自动合成（DAG 子图采样） | 基准 | 仅借思想 | 技能组合回归基准 | 组合能力的廉价评测 | 中 |
| 8 | 五维评估**中的 Executability 沙盒执行** | 工程 | 直接引用（仅二值部分） | 验证门（沙盒级） | 编译产物交付前运行正确性 | 中 |
| 9 | 技能网络健康指标（库规模/关系密度/拓扑） | 指标 | 改造移植 | 观察员、债务 26 | 库健康度可观测 | 中 |
| 10 | 500k 技能库 + skillnet-ai 工具链 | 工程 | 仅作对照 | 技能供给（若需外部技能源） | 技能覆盖广度（但语料不可入基因） | 低 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C2（最硬）**：语言是技能体且进入执行闭环。SkillNet 的整个 Create/Evaluate/Connect
    都由 LLM 读自然语言完成——搬到 SSEA 会把语言塞进控制环。改造方向：**只搬结构层**
    （契约字段、关系类型、匹配算法），把生成这些结构的 LLM 关在慢环编译面。
  - **C8**：50 万技能=知识语料。若整库继承即违反「不给知识语料」。改造：只继承契约
    **schema**（结构性先验），技能本体不跨代。
  - **C9（第二硬）**：五维评分 + QWK 对齐人类 + Bradley–Terry/verifier reward 是
    典型**外部评分函数**。改造：只保留二值判定（沙盒 pass/fail、完备度布尔），
    **禁止任何 Good/Average/Poor 分档、禁止排序**。
  - **C4**：LLM 评分 ×50 万技能、LLM 关系推理、27.8K–800K token/任务的 Wiki 探索，
    与低算力低带宽直接冲突。改造：结构化匹配 + 嵌入近邻替代 LLM 裁决。
- **隐含假设与失效条件**：
  - 假设技能可被语言显式描述（§10 自陈隐性能力「resist explicit linguistic description」）——
    SSEA 的生存技能正是**动作序列**，很多无法语言化。
  - 假设有充足 LLM 预算做评估/关系/路由——SSEA 睡眠期预算未定义。
  - 假设任务可分解为有向技能 DAG——生存任务多为闭环、并发、非 DAG 结构。
- **算力 / 带宽 / 工程代价**：关系图构建（嵌入 + LLM 裁决）、契约抽取、Wiki 路由
  三层均需工程与算力；若照搬 LLM 管线，睡眠期预算必然超支。
- **搬运后的可能退化模式**：
  - 若把 post→pre 匹配照搬为 LLM 裁决 → 慢环成本爆炸，试组合退回「不得进入代码」。
  - 若把五维评分接入验证门 → **验证门从「只判合法性」退化为「打分排序」**，
    直接违反 C9（这是最危险的退化）。
  - 若把 pre/post 场景当自然语言 → 语言渗入技能表示，违反 C2。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | **PSN**（A/P1，技能侧主干） | SkillNet 的 post→pre 匹配**必须先有 pre/post 契约**；PSN 已提供可执行契约（`E^pre/E^post`）——**先 PSN 后 SkillNet** |
| 互补（最紧） | **PSN** | PSN 管「技能何时改、怎么改、改坏怎么退」（维护侧）；SkillNet 管「技能之间怎么连、怎么组合」（连接侧）——两片拼成完整技能环 |
| 互补 | **SkillWeaver**（B/P1，提案-练习-合成-打磨） | SkillWeaver 造技能，SkillNet 连技能；其轻量前置契约与 SkillNet 的 pre/post 同源 |
| 互补 | **AutoSkill**（B/P2，表示与合并代数） | AutoSkill 的合并代数给 SkillNet 的 `compose_with` 提供代数形状；两者都需去评分化 |
| 互补 | **ARISE**（B/P2，两层库 + 只判合法性的准入门 + 弃权门） | ARISE 的「只判合法性准入门」正是 SkillNet 五维评分应被替换成的形状 |
| 互补 | **SkillRL**（B/P2，蒸馏形状 + 慢环回顾配额） | SkillRL 的「慢环回顾配额」是「试组合」的预算旋钮候选 |
| 互补 | **MemSkill**（B/P2，第四类对象定义权 + span 预算旋钮） | 与 SkillNet 的「技能即对象」呼应；MemSkill 的**预算旋钮**可作试组合预算 |
| 互补 | **Memento / FLEX**（记忆侧主干） | 情景（Memento 案例）→ 成熟后结晶为 SkillNet 技能；`compose_with` 边可源于 FLEX 的共现统计 |
| 互补 | **Dream-RSI**（A/P1，重放模拟器） | 「离线试组合」若需行为验证，交重放模拟器；结构匹配先筛掉明显不可行的组合 |
| 对照 / 基准 | **SkillsBench**（Li et al., 87 任务，本片 §8.2 引用） | 关键对照：**策展技能 +16.2pp，而自生成技能无增益**——直接质疑 SSEA「经验编译器产 ΔS」的收益假设（p24） |
| 对照 | **Voyager**（B/P2，PSN 前身） | SkillNet 的技能库=带关系的 Voyager 技能库；Voyager 的键/值表示是 SkillNet 契约的粗糙前身 |
| 替代 | 平铺技能库 / 无关系技能集合 | 用关系图 + 组合完备度指标替代「只有技能、没有连接」 |
| 反例警示 | **Reflexion**（B/P2） | SkillNet 失败分类显示语言反思类方法对组合无效；组合需结构，不需再反思 |

### 6.2 推荐组合方案
1. **技能连接环（PSN × SkillNet × Dream-RSI）**
   - 形态：PSN 提供技能契约（`E^pre/E^post`）；SkillNet 的四类关系 + post→pre 匹配
     在**慢环**为技能库建 `SkillRelationGraph`；组合候选先过**结构匹配**（零 rollout），
     少数高置信候选再交 Dream-RSI 重放模拟器做行为验证。
   - 接口形态：`(skill_A.E^post, skill_B.E^pre) → 结构化谓词可满足性 + 嵌入近邻 → compose_with 边`。
   - 组合后新增能力：**技能库首次有组合表达力**，且「试组合」是**图上检查**而非环境 rollout。
   - 新增风险：谓词设计过松→假阳性组合；过严→假阴性。需以「先看分母」的二值指标校准。
2. **实验 3 判据重设（SkillNet × PSN × ARISE）**
   - 形态：以 **Complete Recall / FullCoverage（二值）** 替代 SKILL_FAILURE 计数；
     准入用 ARISE 的「只判合法性门」，**删掉 SkillNet 的五维评分**。
3. **技能库健康观测（SkillNet × MemSkill）**
   - 形态：库规模、关系密度、拓扑（chain/fan-in）作观察员指标；用 MemSkill 的预算旋钮
     给「试组合」定次数上限。

### 6.3 本篇在组合中的典型角色
- **技能连接环的「形状供给者」**：管「技能之间怎么连、怎么判能不能组合」——补 PSN
  未覆盖的 Connect 环；其评估机制**只取二值部分**作对照，不取评分部分。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 三个动词精确对应 SSEA 技能侧三件事，且直接回答「Connect 空缺」与「表达力上限」（实测于原文结构）；但域为语言 agent/文本环境，非生存（推断） |
| 立场兼容性 | **2** | C2/C8/C9 三项硬冲突（语言载体、知识语料、外部评分），仅 C3/C6 部分对齐（实测：SKILL.md 载体 p4、五维评分 p6–7） |
| 可搬运性 | **3** | 关系词汇表、pre/post 契约、二值指标是架构级、语言无关、可干净拆出（推断）；但实现全是 LLM 管线且绑 SKILL.md/Claude 生态（实测） |
| 证据强度 | **3** | 规模大、基准多、CI 与消融齐（实测）；但**「Connect」机制本身无独立消融**，40%/30% 头条来自技能注入而非连接机制，且预印本未审稿（实测+推断） |
| 组合价值 | **4** | 补齐 PSN/SkillWeaver/AutoSkill/ARISE/SkillRL/MemSkill 共用的「连接」缺环（推断） |
| 落地成本 | **2** | 关系图 + 契约 + 路由三层工程重；若照搬 LLM 管线，睡眠期预算必超（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：Connect 环的**形状**（四类关系 + pre/post 契约 +
  post→pre 匹配 + 二值完备度）是 SSEA 明确缺失且高价值的零件；但语言载体（C2）、
  知识语料（C8）、外部评分（C9）、高算力 LLM 管线（C4）四项使**不能作主干**，
  其评估机制只取二值部分。
- **优先级：P2** —— 理由：其 post→pre 匹配**依赖 PSN 先落地技能契约**（PSN=A/P1）；
  在 PSN 之后排队，避免重复建设契约层。
- **建议动作**：
  1. 在 `Skill` 规格（`SSEA/skill_library.py`）上把 `precondition`/`expected_outcome`
     升级为**显式 pre/post 契约**（与 PSN 契约合并，非语言谓词）；
  2. 新增 `SkillRelationGraph`，只实现 `compose_with`/`depend_on` 两类（其余两类留白）；
  3. 「离线试组合」用**结构化谓词可满足性 + 嵌入近邻**实现，**禁用 LLM 裁决**，
     并给出次数/深度上限（预算旋钮）；
  4. 实验 3 判据改为二值 Complete Recall / FullCoverage；准入沿用「只判合法性门」，
     **不得接入五维评分**；
  5. 记录失败分类（Knowledge Bias / Instruction Override）作技能失效归因词汇。
- **最小验证实验**：
  - **双臂 / 消融设置**：同一技能演化流上对比 ①平铺技能库（无关系）②仅加
    `compose_with` 边（结构化匹配，零 rollout）③结构化匹配 + Dream-RSI 重放验证；
    ≥8 seed；另设消融：把结构化匹配换成 LLM 裁决，测算力代价。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：先报**分母**
    （可检索技能数、检出组合边数、候选组合数）；再看**行为差**（组合任务
    chain/fan-in 的成功率与步数差）；最后看**淘汰结果**（哪些技能因组合失败被下线，
    模型不可见）。
  - **预期与证伪条件**：预期 ②显著优于 ①且算力增量小；③在少数高置信候选上再提升。
    **证伪**：若 ②相对 ① 无行为差，或 ②的算力已接近 LLM 裁决，则「低算力试组合」
    形状不成立，Connect 环应另寻（回到 PSN 的成熟度门控内部）。
- 若 **E 不采用**：不适用（Connect 形状价值明确）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 技能契约的 pre/post 在**非语言状态张量**上如何表达（谓词形式？嵌入？
     字段来源）——SkillNet 用自然语言场景，SSEA 必须另设；
  2. 「试组合」的结构化匹配**次数/深度上限**定多少（SkillNet 未给，仅 Fabric 有 L/K 旋钮）；
  3. 五维评估中，哪些能降级为二值合法性、哪些必须整体弃用（Safety 的语义评分不可搬）。
- **需补查的文献或资料**：
  1. **SkillsBench**（arXiv:2602.12670）——「自生成技能无增益」对 SSEA 经验编译器的直接威胁，
     需专卡评估；
  2. SkillRouter / SkillRet / AgentSkillOS（组合基线强于 agent）——SSEA 组合能力的对照；
  3. CoEvoSkills（自演化+协同验证）、SkillsVote（生命周期治理）——与 Connect 环相邻。
- **需人工核对的公式 / 实现**：
  1. post→pre 匹配的「alignment confidence / retrieval similarity / scenario alignments」
     三分数如何合成边权（§5.3 p12）——是否隐含评分（C9）；
  2. SkillNet-Fabric 的 Explorer token 口径（27.8K/task）与 SSEA 睡眠期预算的换算；
  3. 技能图 `compose_with` 边的 LLM 裁决 prompt 是否可替换为确定性谓词匹配。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we introduce SkillNet, an open infrastructure for creating, evaluating, and organizing AI skills at scale … 600,000 skills … 40% higher average rewards and 30% fewer execution steps” | p1 |
| “a skill serves as a unified knowledge representation that integrates entities, relationships, workflows, and executable code” | p4 |
| 三步使用：Discovery（只载元数据）→ Activation（读 SKILL.md 全文）→ Execution（执行代码/资产） | p4 |
| 本体三层：Skill Taxonomy / Skill Relation Graph / Skill Package Library（Fig.3） | p5 |
| 四类关系：`similar_to`、`belong_to`、`compose_with`、`depend_on`（定义原文） | p8 |
| 五维评估：Safety / Completeness / Executability / Maintainability / Cost-awareness，三档 Good/Average/Poor | p6–7 |
| “200 randomly sampled skills … MAE remains below 0.03 … QWK … above 0.90” | p7 |
| Table 1：Claude Sonnet 4.6 + SkillNet ALFWorld Seen 95.71；o4 Mini +15.7 R；Gemini 2.5 Pro +28.5 R | p9–10 |
| “an LLM extracts each skill’s pre and post scenarios … matching embedded post-scenarios to pre-scenarios … LLM to verify whether each match constitutes a valid workflow handoff” | p11 |
| Table 3/§5.8：Hard 任务检索分常高于 Easy，但编排分下滑；“One-Shot Skill Construction May Introduce Information Loss” | p13–14 |
| Fig.8：Knowledge Bias 59.6% / Instruction Override 40.4% | p15 |
| Fig.9(b)：“Single skill tasks receive almost no benefit … Chain, Fan-out, and especially Fan-in topologies … largest gains” | p16 |
| Skill Contract：能力/使用条件/输入/输出，字段锚回源行（source grounded） | p17–18 |
| Table 5：SkillNet-Fabric K=10 Recall 74.80 / FullCoverage 60.00（79,141 候选） | p18–20 |
| Table 7：完整 Wiki BT 65.51，各项消融 ≥−11.36；token 与质量非单调 | p21 |
| Fig.14：FinalFullCoverage@10 峰值 57.78%（L=10,000）→ 全池降至 38.22% | p22 |
| §8.2 引 SkillsBench：“curated agent Skills significantly boost … while self-generated Skills offer no gain” | p24 |
| §10 Limitations：覆盖不完整；自建技能质量不能保证；poisoned 技能无法完全缓解；无端到端管线 | p26 |
