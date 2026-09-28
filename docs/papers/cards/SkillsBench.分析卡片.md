# 论文分析卡片 · SkillsBench

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-02-13 SkillsBench Benchmarking How Well Agent Skills Work Across Diverse Tasks.pdf` |
| 标题 | **SkillsBench: Benchmarking How Well Agent Skills Work Across Diverse Tasks** |
| 作者 / 机构 | Xiangyi Li、Yimin Liu、Wenbo Chen、Bingran You、Zonglin Di 等 60+ 人；BenchFlow / OSU / UC Berkeley / Stanford / CMU / 字节 / Amazon / Anyscale 等 36 家机构（p1 脚注） |
| 发表时间 / 出处 | arXiv:2602.12670v4 [cs.AI]，2026-06-14（v1 2026-02-13） |
| 论文链接 | arXiv:2602.12670；AgentBeats 在线版 `agentbeats.dev/Yiminnn/skillsbench-agentbeats`（p18 脚注 1） |
| 代码链接 | `github.com/benchflow-ai/benchflow`（BenchFlow 框架，p10 参考）；benchmark/轨迹公开（p1、p8） |
| 标签 | 基准 / 配对评测(paired evaluation) / Agent Skills 包 / 确定性 verifier / 技能有效性 / 负结果 |
| **应用裁决** | **D 基准对照**（它测的是「LLM 智能体 + 自然语言 SKILL.md」的技能增益，非 SSEA 式非语言结构技能；价值在**评测协议与负结果**，不在机制） |
| 优先级 | **P1**（直接服务于实验 3 判据重设计与「技能表示够不够」的外部证据） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：Agent Skills（`SKILL.md` + 资源文件的文件系统级程序性知识包）此前无人系统测量；本文构建 **87 任务 / 8 领域 / 18 个 model–harness 配置**的配对基准（同任务、同容器，只差「有没有挂载 Skills」），实测策展 Skills 把平均通过率从 **33.9%→50.5%（+16.6 pp，归一化增益 25.5%）**，但同时给出**大量负结果**——自生成 Skills 反而**低于**无 Skills 基线，技能数量/篇幅过量会掉增益（p1、p6–8、p22）。
- **对 SSEA 的意义**：它是 SSEA 判断「**技能表示够不够**」（0/33 之后仍未回答）最直接的**外部证据源**：以「配对对照 + 确定性 verifier + 负结果如实报告」的方式，划出了技能**有用 / 无用 / 有害**的条件边界；其 `SKILL.md` schema、任务分类、配对协议、失败模式分类是可直接改造成 SSEA 验收仪器的**基准对照件**，而不是可搬运的机制。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p2）：Agent Skills 生态已膨胀到 **2,014,000 个**（构建快照，p1、p3 Figure 2），但**没有任何基准系统回答**：「Skills 到底帮了多少？什么时候会失效？」（原文：“how much do Skills actually help, and when do they fail?”）。
- **它指出的既有方案缺陷**（p2）：既有智能体基准（Terminal-Bench、SWE-bench、AgentBench、WebArena、OSWorld 等）只测**孤立原始能力**，把 model、harness、augmentation 三类效应**折叠进一个通过率**，回答不了部署问题：「给我这个智能体加这个 Skill，在这类任务上到底涨多少？」

### 2.2 核心思想（关键 insight）
1. **配对评测（paired evaluation）**：同一任务、同一容器、同一 verifier，唯一变量是「Skills 是否挂载」，故 Δ 是 `(配置,任务)` 级配对差而非无配对池差（p4 Figure 3、p5、p42）。这是全篇方法论内核。
2. **技能=可移植的程序性知识包，而非答案**：Skill 必须对**一类**任务给程序性指导（SOP/惯例/启发式），**绝不**编码单实例答案；任务指令**从不点名**用哪个 Skill，智能体须自主发现（渐进式披露）（p3、p36 M.1、p37 M.4）。
3. **确定性 verifier 消灭 LLM-as-judge 方差**：全部 87 任务只用 `test-script` 策略（pytest + CTRF，reward∈{0,1}），不用 llm-judge/reward-kit/agent-judge（p16、p20 Table 4）。
4. **技能有效性是「具体 agent 栈的经验属性」，不是普适常数**：增益在配置间从 +4.1 到 +25.7 pp，且受 harness 中介（p5–6 Finding 1/3）。
5. **负结果优先**：自生成技能、过量技能、冗长文档三处均报告**增益极小或为负**，并给出轨迹审计的机制归因（p7–8、p22–23、p28）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
> 本篇是基准论文，可搬运件集中在**技能定义/schema、任务分类、评测协议**三处。

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **Skill 四条操作判据** | artifact → 是否算 Skill | procedural content / task-class applicability / structured components / portability；显式排除 system prompt、few-shot、RAG、tool docs | §M.1 p36 |
| **`SKILL.md` schema** | YAML frontmatter(name+一行 description) + body 程序性指导 | 目录=一个 Skill：`SKILL.md` 必需 + 可选 `scripts/ references/ assets/ examples` | §2 p2、§D.5 p21、§M.1 p36 |
| **`task.md` 任务标准** | YAML frontmatter(配置) + Markdown body(指令) | 单文档可移植任务包；严格顶层 schema，`network_mode∈{no-network,public,allowlist}` | §C p18–20 |
| **任务四件套** | instruction / environment(Dockerfile+`skills/`) / oracle(须 100% 过) / verifier(确定性 pytest) | 自包含可复现单元 | §M.2 p36–37、§B.1 p15–16 |
| **配对三臂协议** | 同任务三条件：A 无 Skills / B 策展 Skills / C 自生成 Skills → r_A,r_B,r_C | Δ_curated=r_B−r_A；Δ_self=r_C−r_A（同一基线） | Figure 3 p4 |
| **自生成条件双会话协议** | creator 会话（挂 `skill-creator`，只造包不解题）→ solver 会话（干净上下文，只挂生成包） | 隔离「造技能」与「用技能」，测自产技能可替代性 | §D.6 p21–22 |
| **确定性 verifier + reward.txt** | `test.sh`→pytest→`/logs/verifier/reward.txt`∈{0,1} | 无 LLM 判分，可复现 | §B.3 p16 |
| **task-macro pass rate** | 每任务 3 trials 平均 → 跨 87 任务宏平均 | 主指标（对齐 Terminal-Bench） | §N.4 p42 |
| **归一化增益 g** | g=(pass_skill−pass_vanilla)/(1−pass_vanilla) | 度量「剩余空间的填补比例」，须与绝对 Δ 联读 | Eq.1 p5、p42 |
| **Skill Invocation Rate** | 轨迹中读取/调用 task-bundled Skill 的 trial 占比 | 分离「发现」与「使用」瓶颈 | §K p33、Figure 5 p6 |
| **失败模式三分类（负增益归因）** | 配对轨迹 → A 重管道挤走简路径 / B 技能压制更强原生策略 / C 技能指向不可调试的 solver | 技能**有害**时的机制诊断 | §F.3 p28 |
| **复杂度契约（提案）** | `SKILL.md` frontmatter 增：预期工具/令牌成本、适用边界、**必配轻量回退路径** | 治负增益根因（单一「正确」管道无边界无回退） | §6 p8 |
| **泄漏审计** | CI agent 查 task-specific 文件名/路径/魔数/逐字命令/期望输出 | 防止 Skill 变成隐藏答案键 | §M.7 p38、§B.7 p17 |

### 2.4 关键表示与数据结构
- **Skill** = 目录：`<skill-name>/SKILL.md`（YAML frontmatter：`name` + 一行 `description`，供发现匹配）+ 可选 `scripts/ references/ assets/ examples`（p21 §D.5）。生态实测：`SKILL.md` 中位 **~1.2k tokens**，整包中位 **~1.8k tokens**（n=767,425，p14 Figure 7）——高度偏瘦，但尾部可超 1.6 GB。
- **Task** = `tasks/<id>/`：`task.md`（frontmatter + 指令体）、`environment/`（`Dockerfile` + `skills/`）、`oracle/solve.sh`、`verifier/test.sh` + `test_outputs.py`（p15–16）。
- **结果记录**：每次 trial 记 token 数、wall-clock、cost（部分）、`error/error_category`；reward 写入 `reward.txt`（p16、p34 Table 17）。
- **聚合口径**：固定 **87×3** 帧（每 (配置,任务,条件) 取 3 个健康 trial）；失败回填仅用 timeout 行（p42 §N.3）。

### 2.5 实验证据（**重点：测出了什么结论**）
> 本篇价值在于「技能何时有用、何时无用/有害」。全部为论文实测数字。

**A. 总量与异质性**
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 87 任务 × 18 配置 | no-Skills vs curated-Skills | **33.9%→50.5%（+16.6 pp；归一化 25.5%）**；配置级 +4.1~+25.7 pp | 9,396 trial（Table 2 p6、Table 10 p29） |
| 同上 | 18/18 配置 | **每个配置都涨**，但最弱者仅 +4.1 pp（OH+Gemini 3.1 Flash Lite）；最大 +25.7 pp（OH+GLM 5.1） | p5 Finding 1 |
| 同上 | 最强系统≠最大受益 | 最高 with-Skills 67.3%（OH+GPT-5.5）；高基线（41.1%）配置只 +7.1 pp | p5 Finding 2 |

**B. 技能「在什么条件下有用」（正向边界）**
| 结论 | 关键数字 | 出处 |
|---|---|---|
| 领域异质性大 | Natural Science **+28.8**、Media **+24.1**、Cyber **+18.9**、Industrial +15.7、Finance +14.2、Office +12.6、SW Eng **+11.6**、Math/OR **+9.7**（全为正） | Table 3 p7 |
| 强预训练领域受益最小 | 需「预训练里稀缺的专业程序知识」的域（科学信号处理/安全分析/多媒体）涨最多 | p7 Finding 5 |
| 技能数量：**越少越好** | 1 个 Skill **+18.0**、2–3 个 **+19.0**、**≥4 个仅 +10.1** | Table 8 p28 |
| 技能篇幅：**聚焦胜过详尽** | Compact +19.0、Standard +21.5、Detailed +14.5、**Comprehensive 仅 +0.7** | Table 9 p28 |
| 小模型+技能≈大模型无技能 | MiniMax M2.7+Skills 34.9% > OH+GLM 5.1 无技能 32.7% | p8 Finding 6 |
| 发现通常不是瓶颈 | Skill Invocation Rate 46.4%~99.2%（Codex+GPT-5.5 最高 99.2%），高调用不保证高通过 | Table 14 p33、p6 Finding 4 |
| 顶 10 受益任务 | 平均 **+67.0 pp**（如 llm-prefix-cache-replay 1.9%→94.4%，dapt-intrusion-detection 0%→81.5%） | Table 13 p33 |

**C. 技能「在什么条件下无用/有害」（负结果——对 SSEA 极重要）**
| 结论 | 关键数字 | 出处 |
|---|---|---|
| **自生成技能 < 无技能基线** | **−8.1 pp**(CC+Opus4.7)、**−11.3 pp**(Codex+GPT-5.5)、**−11.5 pp**(Gemini CLI+3.1 Pro)；同配置策展技能却 +18.2~+24.8 pp | Table 6 p22、Figure 10 p23 |
| 自生成失败机制 | ①生成包**常被 solver 完全无视**（12 条审计轨迹中 10 条事件流 0 次出现“skill”）②造技能**挤占解题**③被用的包**锁死自信错误**（3d-scan-calc 单位假设错，量级差 10³）④唯一胜例其实是**泄漏**（把 data-testid 写进包） | §D.6.1 p23 |
| **13/87 任务出现负增益** | 最大跌幅：exam-block-sequencing **−7.4 pp**、suricata-custom-exfil −7.4、adaptive-cruise-control/r2r-mpc-control/mars-clouds-clustering/econ-detrending-correlation 各 −5.6 | p7、Figure 13 p27、§F.3 p28 |
| 负增益三模式 | A 重管道挤走简路径；B 技能压制更强原生策略；C 技能指向不可调试 solver。**共同根因：单一「正确」管道，无适用边界、无轻量回退** | §F.3 p28、§6 p8 |
| harness 中介技能效果 | 同模型换 harness 差 5~10 pp（Gemini 3.1 Pro：CLI 60.8% vs OH 52.8%）；结构化接口会引入**格式漂移**长程失效 | p6 Finding 3、p8 Discussion |
| 失败分布 | 无技能失败率 66.1%→有技能 49.5%；失败中 **~90% 是 Verification 类**（非 timeout/execution） | Table 11 p30 |
| **因果归因警告** | Skills 注入**增加上下文长度**，增益可能部分只是「更多上下文」而非程序结构；作者明确**尚缺长度匹配基线**（随机/无关文本、仅检索文档） | §6.1 p8 |

### 2.6 论文自陈局限与边界条件
- **覆盖/泛化**：仅限**终端、容器化**任务；不直接迁移到 GUI agent、多智能体协作、超长程工作流（p8 §6.1）。
- **生态 vs 基准落差**：基准 Skills 取自**质量前 25%**（≥9/12；基准均值 10.1/12），生态均值仅 **6.2/12**；真实世界 Skill 质量更低、匹配更差，故本文是**乐观场景**（p15 A.4）。
- **因果归因**：自生成条件缺陷**混合**了内容质量、技能发现、creator/solver 干扰三种效应（p8 §6.1）。
- **确定性与污染**：容器隔离≠完美确定性，也非免训练集泄漏；用多 run + 泄漏审计 + 配对缓解，但未消除（p8 §6.1）。
- **模型侧**：Claude 系列被训练过 Agent Skills 规范，可能对 Skill 格式有先天优势（p21 §D.2）；harness 版本会随时间变（p8）。
- 预印本，2026-06 修订至 v4。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据 | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 全篇是 LLM 终端 agent；Skill 本体即自然语言 `SKILL.md`，直接进上下文参与控制（p2、p21） | 作为**外部对照基准**采用，不采用其架构；SSEA 只借「配对对照」方法 |
| **C2** 自然语言只作观察员接口 | **✗** | 技能=自然语言程序性指导，注入即影响决策闭环（p2）；本文正测「语言技能对语言 agent 的增益」 | 反面教材：SSEA 的技能须**非语言结构化**；本基准恰好暴露「语言技能」的边界 |
| **C3** 权重/记忆/技能三分离 | **✓** | Skills 是文件系统件，**不改权重**、跨模型可移植（Table 1 p3）；与 SSEA 三分离同构 | 直接借「技能=独立文件件、不动权重」的分离立场 |
| **C4** 低算力低带宽 | **◐（偏 ✗）** | 8K 滑窗；Skills 常**增加** token（如 OH+Gemini 3.1 Pro 1.82M→4.02M，p35）；成本跨两个数量级 | 只取「聚焦技能更省」的结论（Table 9）；SSEA 须避免语言上下文膨胀 |
| **C5** 精准回忆历史 | **—** | 未涉及记忆检索/遗忘；不测 memory store（p8 把 memory stores 列为可复用同一协议的**其他** artifact） | 无 |
| **C6** 可自主修改自身 | **◐（偏 ✗）** | 有「自生成技能」条件，但**作者自己造包**、非慢环受控自修改；且自生成**低于基线**（p22） | 借其**负结果**警示：SSEA 慢环自产技能必须过验证门 |
| **C7** 可保存/恢复/变异/继承 | **—** | 未涉及继承/变异/GenePackage | 无 |
| **C8** 给基因先验，不给知识语料 | **✗** | 本文 Skills **正是**人类策展的**领域知识语料**（SOP/惯例/公式），明确以「注入专家知识」为增益来源（p7、p31–32 案例） | 关键分界：SkillsBench 技能=**后天知识**，SSEA 禁其跨代；SSEA 只让此类知识留在 L3 个体内 |
| **C9** 不设评分函数，只有淘汰函数 | **◐** | verifier 是**确定性 pass/fail**（无 LLM-judge，合 C9 精神）；但归一化增益 g、pass rate 是**外部评分函数**用于分析（p42） | g/pass rate **仅作基准对照的分析量**，绝不进 SSEA 控制环；reward∈{0,1} 更接近淘汰函数，可参照 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子，创新在**评测方法论**（配对协议）与技能表示/schema | 符合「不声明 L1 创新」；其协议属 L2/L3 验收工具层 |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无；LLM/harness 均为现成件 | 符合借用立场（C10） |
| **L2 信息流层** | 「技能→harness 注入→上下文」的信息流，及**配对隔离**设计 | 中：借「技能与执行解耦、只换技能件」的对照思路 |
| **L3 学习层** | 无学习；技能是**静态注入**，不更新 | 低：反衬 SSEA 的 L3 是「技能会演化」，本文技能不会 |
| **L4 演化层** | 无 | 无 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| Skill 四条操作判据 + `SKILL.md` schema | 技能表示校验（`skill_library.py`）的**外部对照**：SSEA 技能须可被「发现+对类适用」，此判据暴露 0/33 的表示缺口 |
| 配对三臂协议（A/B/C） | **实验 3 重设计**的对照设计模板（见第 4 节） |
| 确定性 verifier（reward∈{0,1}） | 与 C9 淘汰函数同形；可作 SSEA 环境侧判据形状参照（债务 26/27/28） |
| 失败模式三分类（A/B/C） | 慢环技能**回滚/失效判定**的归因分类（对应「技能失效被判成成功」债务 28） |
| 复杂度契约提案 | 技能元数据建议：预期成本 + 适用边界 + **必配回退路径** |
| Skill Invocation Rate | 新增仪器：SSEA 技能「是否被快环真正调用」的分母指标 |
| 自生成技能负结果 | **Gene Manager / 慢环自产技能的准入红线**证据 |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **「技能表示够不够」（0/33 之后未答）**：本文给出**外部判据形状**——技能须满足「对类适用 + 可被发现 + 可验证」；SSEA 若技能既不可被快环发现、又不带适用边界，则等价于本文「生成包无人用/锁死错误」的失败模式。
  - **债务 26/27/28（判据形状错、环境对无消费者通道报成功、技能失效被判成成功）**：本文的**负增益识别 + 失败模式三分类 + 配对对照**是修正判据形状的直接模板。
  - **缺失组件 Gene Manager**：自生成技能「低于基线」的实证，为 Gene Manager 的**技能准入验证**提供必要性论证。
- **可服务的验收实验**：
  - **实验 3（技能固化）重设计**：引入配对 A/B/C 臂 + 负增益显式计数（先看分母）。
  - 后续：SSEA 技能库的「发现率 / 使用率 / 负增益任务占比」仪器化。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **配对评测协议**（同任务同容器，只切「技能有无」；A 无/B 策展/C 自生成三臂；Δ=r_B−r_A） | 协议 | 改造移植 | 实验 3 重设计 / 验收框架 | 把「技能是否真的有用」从折叠通过率中解耦 | 高 |
| 2 | **确定性 verifier + reward∈{0,1} + 失败回填规则** | 协议/工程 | 改造移植 | 四级验证门 / 环境判据 | 消除 LLM-judge 方差，判据形状对齐 C9 | 高 |
| 3 | **Skill 四条操作判据 + `SKILL.md` schema（frontmatter 描述 + 资源目录）** | 表示/规范 | 仅借思想 | skill_library 技能规格 | 技能「可发现 + 对类适用」的最小表示要求 | 高 |
| 4 | **任务分类学（8 领域 + Core/Extended/Extreme 难度 + 5 能力轴）** | 分类法 | 改造移植 | 技能回归任务集设计 | 技能评测的覆盖与难度分层 | 中 |
| 5 | **失败模式三分类（重管道/压制原生/不可调试 solver）+ 复杂度契约** | 方法 | 直接引用 | 慢环技能回滚/失效归因 | 负增益归因与回退路径强制 | 高 |
| 6 | **Skill Invocation Rate 指标** | 指标 | 改造移植 | 实验仪器 | 区分「发现」与「使用」瓶颈（债务 26） | 中 |
| 7 | **归一化增益 g 及其「须与绝对 Δ 联读」的告诫** | 指标 | 仅借思想 | 结果汇报规范 | 防止近天花板处 g 高估 | 中 |
| 8 | **泄漏审计清单（禁 task-specific 文件名/路径/魔数/逐字命令/期望输出）** | 工程/清单 | 直接引用 | 技能交付前质控（RuleCompiler/verifier） | 防技能退化为答案键 | 高 |
| 9 | **自生成技能负结果 + 轨迹审计方法** | 证据/方法 | 直接引用 | Gene Manager 准入 / 慢环自产验证 | 为「自产技能须验证」提供实证红线 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 ✗/◐）：
  - **C1/C2 ✗**：全篇是语言 agent + 自然语言技能，架构层面**不可采用**；只能作外部对照。
  - **C8 ✗**：其技能=人类知识语料，与 SSEA「基因只放结构先验、知识不跨代」直接对立。若误把 SkillsBench 式知识包当 SSEA 基因，则违反 C8。
  - **C4 ◐**：技能注入常增大上下文/成本，与低算力低带宽相悖。
  - **C9 ◐**：g / pass rate 是评分函数——**仅限基准对照分析**，不得进控制环。
- **隐含假设与失效条件**：
  - 假设「技能可表示为文件系统件并被 harness 发现」——SSEA 的非语言结构技能**未必能表达为 `SKILL.md`**，存在**表示层不可搬运**的根本风险。
  - 假设「Δ 归因于技能的程序结构」——作者自认**未排除「更多上下文」混淆**（§6.1），故不能直接宣称「结构化技能本身有效」。
- **算力 / 带宽 / 工程代价**：成本跨两个数量级（$0.15~$22.70/trial，p35）；9,396 trial 的规模对 SSEA 过重，须缩样。
- **搬运后的可能退化模式**：
  - 若 SSEA 照搬「自然语言技能包」→ 违反 C1/C2/C8，且重演「生成包无人用/锁死错误」失败。
  - 若只搬 pass rate 当内部奖励 → 违反 C9。
  - 若不做长度匹配对照 → 无法区分「结构」与「上下文量」贡献，实验 3 仍会得到**形状错**的判据。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | —（自带协议与任务集） | 它是**外部度量层**，不依赖 SSEA 现有模块即可跑 |
| 直接对照/互补 | **PSN**（技能侧主干，已有卡 A/P1） | PSN 提供「技能**如何被维护/演化/回滚**」；SkillsBench 提供「技能**到底有没有用**」的外部裁决。**两者接口**：PSN 演化出的技能库应作为 SkillsBench 式的**被测件**，跑配对对照 |
| 互补 | **Voyager**（已有卡 B/P2，技能库前身） | Voyager 的键/值技能库 = SkillsBench 里「task-class 技能包」的原始形态；SkillsBench 正是量化 Voyager 式技能迁移增益的仪器 |
| 互补 | **SkillWeaver**（已有卡 B/P1，提案-练习-合成-打磨） | SkillWeaver 造技能、SkillsBench 验技能——**供给侧 × 裁决侧**配对 |
| 互补（须新建卡） | **SkillRL / AutoSkill / ARISE / MemSkill / SkillNet** | 均为「技能获取/表示/强化」方法族（**本仓库尚未建卡**，见第 9 节）：它们与 SkillsBench 构成「造→测」闭环。SkillsBench 的负结果（自生成低于基线、≥4 技能掉增益）对它们的**自动技能合成**是直接的反证条件 |
| 替代 | — | 不可替代 SSEA 任何模块；它**替换的是「凭直觉声称技能有用」的评估方式** |

### 6.2 推荐组合方案
- **组合**：**SkillsBench（裁决侧）× PSN（技能侧主干）× Memento/FLEX（记忆侧主干）**
- **接口形态**：SSEA 技能库（PSN 式契约技能）与案例库（Memento μ 检索 / FLEX 分层经验）作为**被测件**，投入 SkillsBench 式**配对对照**：A=无技能基线、B=SSEA 技能、C=SSEA 慢环自产技能。
- **组合后新增能力**：把 SSEA 的「技能表示够不够 / 自产技能能不能用」从**内部主观**变为**外部可裁决**；并用失败模式三分类直接生成**回滚/失效**信号。
- **新增风险**：SSEA 技能非语言、非文件系统件，**可能无法装入该基准**；须先解决「表示映射」，否则对照跑不起来（这本身即是对实验 3 的暴露）。

### 6.3 本篇在组合中的典型角色
- **外部裁决场 / 判据形状标尺**：它不供给技能，供给**「技能有没有用、何时有害」的可复现判据**——正是 SSEA「0/33 未答问题」所需的第三方裁判视角。

### 6.4 「若把 SSEA 的技能放进这个基准」的预期（对实验 3 的直接推演）
1. **预期增益接近零或为负**：SSEA 现有技能（0/33）既非 `SKILL.md` 式可发现件，又缺**对类适用**与**适用边界**——按本文失败模式，等价于「生成包无人用」（发现失败）或「锁死错误」（表示不匹配）。**暴露判据**：Skill Invocation Rate（发现率）与负增益任务占比。
2. **自产技能红线被直接命中**：本文自生成技能 **−8.1~−11.5 pp**；SSEA 慢环自产技能若无验证门，预期同样跌破基线。**暴露判据**：Δ_self 是否 < 0。
3. **「结构 vs 上下文量」混淆会被暴露**：SSEA 若声称「非语言结构技能有效」，必须过本文要求的**长度匹配基线**（随机/无关文本、仅检索文档），否则增益不可归因于结构。
4. **会暴露的判据形状**：pass rate 只给 0/1 末端信号，**看不到「技能被调用但用错」的中间态**——这正是 SSEA 债务 26「判据形状错」的同构问题；须补 Skill Invocation Rate 与失败模式分类。

---

## 7. 多维度评分（1–5）

| 维度    | 分值    | 评分理由（含证据性质：实测 / 推断）                                            |
| ----- | ----- | -------------------------------------------------------------- |
| 项目相关性 | **4** | 直击 SSEA「技能表示够不够 / 实验 3 判据形状」这一**最紧缺口**（实测：0/33 背景 + 本文负结果）     |
| 立场兼容性 | **2** | C3/C10 对齐，但 C1/C2/C8 直接冲突（语言 agent + 知识语料）；作为 D 对照可接受（实测 + 推断） |
| 可搬运性  | **3** | **协议与判据可搬**（配对设计、确定性 verifier、失败分类、schema）；**机制/技能本体不可搬**（实测）  |
| 证据强度  | **5** | 87 任务 × 18 配置 × 9,396 trial；确定性 verifier；如实报告负结果与混淆（实测）        |
| 组合价值  | **4** | 与 PSN/Voyager/SkillWeaver 及未建卡技能族构成「造→测」闭环（推断）                 |
| 落地成本  | **3** | 协议本身廉价；但需自建任务集/容器/verifier，且要先解决 SSEA 技能→基准的**表示映射**（推断）       |

---

## 8. 裁决与下一步

- **应用等级：D 基准对照** —— 理由：它是**语言 agent + 自然语言技能**的度量基准（C1/C2/C8 冲突），不提供可搬机制；但其**配对协议、技能判据、失败模式分类与负结果**正是 SSEA 修正实验 3 判据、回答「技能表示够不够」的外部标尺。
- **优先级：P1**。
- **建议动作**：
  1. 采用**配对三臂协议**（A 无技能 / B SSEA 技能 / C 慢环自产技能）重设计实验 3；
  2. 引入**Skill Invocation Rate**（技能发现率）与**负增益任务计数**作为新分母指标（补债务 26）；
  3. 把**失败模式三分类**（重管道/压制原生/不可调试 solver）写入慢环技能**回滚判定**；
  4. 为技能元数据加**复杂度契约**（预期成本 + 适用边界 + 必配回退路径）；
  5. 以**长度匹配基线**（随机/无关文本、仅检索文档）检验「结构 vs 上下文量」归因；
  6. 抽取 **10~20 个 SSEA 生存/技能任务**（缩样），套用其 `task.md`+确定性 verifier 形状，先跑通协议。
- **最小验证实验**：
  - **双臂/消融**：同一技能演化流上，A 无技能 / B 结构技能 / C 慢环自产技能；**另加长度匹配对照臂**（等 token 的无关文本）。≥8 seed。
  - **判据（分档）**：机制计数（**先看分母**：技能被调用次数、任务总数）→ 行为差（逐任务 Δ 通过率，**显式列负增益任务**）→ 淘汰结果（模型外，环境成败）。
  - **预期与证伪**：
    - 预期：B 相对 A 有正 Δ 且**负增益任务占比 < 15%**（对齐本文 13/87≈15% 量级）；C 若不设验证门则 Δ_self < 0（复现本文负结果）。
    - **证伪条件**：若 B 的 Δ 在长度匹配对照下消失 → 增益来自上下文量而非结构，SSEA「结构化技能有效」被证伪；若 C 未跌破基线 → 自产技能安全，Gene Manager 准入门可放宽。
- 若 **E 不采用**：不适用（本篇作 D 对照采用）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的**非语言结构技能**如何映射到 `SKILL.md` 式「可发现 + 对类适用」的判据？若无法映射，实验 3 是否改为**内部配对协议**而非套用本基准？
  2. 实验 3 是否采用「A/B/C 三臂 + 长度匹配对照」四臂设计？
- **需补查的文献或资料**：
  3. **SkillRL、AutoSkill、ARISE、MemSkill、SkillNet**（用户点名但**本仓库尚无卡片**）——需先建卡，再与本篇连成「技能合成→技能裁决」闭环。
  4. Terminal-Bench（arXiv:2601.11868，本文指标来源）与 BenchFlow 框架，评估能否直接复用其容器/verifier 栈。
- **需人工核对的公式 / 实现**：
  5. 归一化增益 g 在 SSEA 生存任务（近天花板/近地板）是否仍可解释；是否改用绝对 Δ + 负增益占比。
  6. `reward∈{0,1}` 的确定性 verifier 与 SSEA 四级验证门的**合法性判定（不打分）**如何对齐，避免引入评分函数（C9）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “Curated Skills raise the average pass rate from 33.9% to 50.5% (+16.6 percentage points; 25.5% normalized gain), with configuration-level gains ranging from +4.1 to +25.7 pp.” | p1 Abstract |
| “how much do Skills actually help, and when do they fail?”（本文要回答的核心问题） | p2 §1 |
| Skill 四条操作判据：procedural content / task-class applicability / structured components / portability；显式排除 system prompts、few-shot、RAG、tool docs | p36 §M.1 |
| 配对三臂：A no skills（r_A）/ B curated（r_B）/ C self-generated（r_C）；Δ_curated=r_B−r_A | p4 Figure 3 |
| g=(pass_skill−pass_vanilla)/(1−pass_vanilla)（Eq.1） | p5 §4、p42 §N.4 |
| “Self-generated Skills land below the no-Skills baseline on all three configurations (−8.1 pp … −11.3 pp … −11.5 pp)” | p7 §5.1.1、p22 Table 6 |
| 自生成失败机制：生成包常无人用（12 条审计轨迹中 10 条 0 次出现“skill”）、造技能挤占解题、锁死自信错误、唯一胜例是泄漏 | p23 §D.6.1 |
| “13 of 87 tasks show negative Skills deltas” | p7 §5.1.3 |
| 失败三模式 A/B/C；根因“a single ‘correct’ pipeline without applicability boundaries or lightweight fallbacks” | p28 §F.3、p8 §6 |
| Skill 数量：1→+18.0、2–3→+19.0、≥4→+10.1 pp | p28 Table 8 |
| Skill 篇幅：Compact +19.0 / Standard +21.5 / Detailed +14.5 / Comprehensive +0.7 pp | p28 Table 9 |
| 领域增益：Natural Science +28.8 … Math/OR +9.7 pp（全为正） | p7 Table 3 |
| Skill Invocation Rate 46.4%~99.2%（Codex+GPT-5.5 = 99.2%） | p33 Table 14 |
| “Skills injection increases context length, so observed gains could partly reflect ‘more context’ rather than procedural structure.” | p8 §6.1 |
| 生态均值 6.2/12 vs 基准均值 10.1/12；“optimistic scenario” | p15 §A.4 |
| 复杂度契约提案：expected tool and token cost、applicability boundaries、required lightweight fallback path | p8 §6 |
