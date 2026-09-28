# 论文分析卡片 · HarnessDev

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-09-01 HarnessDev Can LLMs Create and Evolve Their Own Agent Harness.pdf` |
| 标题 | **HarnessDev: Can LLMs Create and Evolve Their Own Agent Harness?** |
| 作者 / 机构 | Yuhao Wu、Jingyuan Zhang、Jiajun Shi（Core Contributors）等；ByteDance Seed、SUTD、Georgia Institute of Technology、M-A-P、TokenWave.AI；通讯 Yuhao Wu / Shen Yan / Wenhao Huang / Ge Zhang / Wenxuan Zhang（p17） |
| 发表时间 / 出处 | 2026-09-02，arXiv:2609.01437v1 [cs.SE]（p1） |
| 论文链接 | arXiv:2609.01437；项目页 https://self-developing-agents.github.io/（p1） |
| 代码链接 | **未提及独立代码仓库**；论文称 benchmark release 会固定候选系统的角色/版本/许可（p6） |
| 标签 | Agent harness（外壳）· 自演化 · 基准/评测协议 · creator–executor 分离 · held-out 泛化 · 执行成本 · 失败模式 |
| **应用裁决** | **B 零件采用**（并含强 **D 基准对照** 角色：自改退化的实测证据源） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把智能体评测的**单位从「任务输出」换成「可运行的执行基础设施」**——提出
  HarnessDev 基准：**Creation** 阶段让 creator LLM 从「弱但可运行」的 seed 造出完整 harness，
  **Evolution** 阶段让它用下游执行反馈迭代修改**自己造的 harness**；评测同时看**能力**
  （held-out benchmark 成功率）与**效率**（执行 token 成本）。结论：六个前沿模型都能造出可运行
  harness，但在 code / search / research 上仍显著落后人类工程系统（writing、MLE 上追平或反超）；
  Evolution 能产生**局部增益，但不稳定**、只能部分迁移到 held-out 任务，且**强烈依赖执行模型**（p1、p3、p15）。
- **对 SSEA 的意义**：这篇把 SSEA 最核心的疑问——「**SSEA 自己是不是一个可被自身演化的 harness**」——
  变成了一个**有实测数据的问题**。它给出 ①harness 的六模块分解 `H=<E,T,C,S,L,V>`（直接对标快环执行环
  的结构定义）；②一套**「反馈集涨、held-out 跌」的实测退化模式**（C6/C7 自改的风险证据，比 Misevolve 的
  理论威胁模型更硬）；③两条与 C9 同向的工程纪律——**评分路径与 harness 隔离、harness 自报状态永不计分**
  （p7），可直接搬去修债务 25–28 的「假成功」问题。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题

- **问题本身**：agent 能力越来越取决于**模型权重之外的执行基础设施**（harness：执行环、工具、上下文、
  失败恢复、结果验证）；同等权重下 GPT-5 在 Terminus 2 里解 35.2% Terminal-Bench 2.1，在 Codex CLI 里
  解 49.6%（p1）。既然如此，**LLM 能否自己造、并持续改进 harness**？
- **它指出的既有方案缺陷**：①主流 agent 基准（SWE-bench / GAIA / WebArena / τ-bench / AgentBench）
  把 harness **当作实验配置固定下来**，只报任务分数，harness 本身不是被测对象（p2、p14）；②已有工作
  开始研究 harness 表示与自动设计，但**「能否同时创造并持续改进可运行、持久化的 harness」仍未被系统评测**；
  ③要把这件事测清楚，必须**分离「造 harness 的模型」与「跑任务的模型」**，并同时记录开发环境、下游表现、
  跨 executor 迁移、与人类系统的距离、回归与成本（p2）。论文用 **FDE（forward-deployed engineer）**
  这一角色类比：真实部署中「能力强的模型 ≠ 能用的系统」，缺口现在由人补（p3）。

### 2.2 核心思想（关键 insight）

1. **把 harness 形式化为可评测对象**：`(L_C, D) → H`，`(H, L_E, x) → y`，`J` 打分（式 1，p4）。
   `D`（开发环境）用于造 `H`，`L_E`（executor）只在 `H` 冻结后使用——**creator 与 executor 必须分离**，
   否则分不清增益来自「改好了系统」还是「换了个更强的模型」（p2、p4）。
2. **弱 seed 剥离样板负担、但不给解法**：`H_seed` 是可运行的**兼容层**，只解析输入、暴露**被动**低层原语、
   写审计产物；**没有** agent loop、任务分解、工具策略、上下文管理、持久状态、验证器、重试/恢复、停机规则；
   未修改时在所有下游基准上**得 0 分**——任何非零 Creation 分数必来自 creator 加的**执行逻辑**（p4、Fig.2 p5）。
3. **harness = 六模块控制面**：`H = <E 执行环, T 工具, C 上下文, S 状态, L 生命周期, V 验证>`
   （RQ2 系统提示词明确定义，p29；Fig.3 p5）——「责任可放在任何模块，关键是最终系统**真的执行**它们」。
4. **反馈集 ≠ 泛化**：Evolution 中反复评测的任务构成 **feedback set**，只在演化后评、结果不回传给
   creator 的任务构成 **held-out set**；二者**分开报告**，避免把「适应反馈」误当「能力提升」（p6、p11）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **HarnessDev 两阶段** | Creation（RQ1）+ Evolution（RQ2） | 基准形式化：造 vs 改 | §3.1、Table 1 p4 |
| **弱 seed `H_seed`** | 统一契约 + 被动原语 → 可运行但 0 分 | 剥离样板、不泄解法 | §3.2 p4、Fig.2 p5 |
| **creator–executor 分离** | `L_C` 造 `H`；`L_E` 冻结后跑 | 把「系统质量」与「模型能力」解耦 | 式 1 p4 |
| **Self-Eval / Unified-Eval** | `L_E=L_C` / 固定 `L_E=Gemini` | 分离 harness 设计、executor 能力与二者兼容性 | §3.4 p6、Table 3–4 p8 |
| **harness 六模块 `H=<E,T,C,S,L,V>`** | 控制面 → 统一审计产物 | 结构分解与「机制须真进入执行路径」口径 | RQ2 提示词 p29、Fig.3 p5 |
| **诚实状态契约** | run → `result.json` 的 `success/partial/failed` | 禁止把 plan/模板/空产物当完成 | 提示词 p27、p30 |
| **评分路径隔离** | harness 自报状态 → **永不计分** | 只能靠真实 repo diff / 最终环境状态得分 | §3.4 p7 |
| **pair 预算 + probe 配额** | 10 对全量评估；每轮 ≤2 个固定子集探针 | 稀缺远程信号 + 廉价方向信号 | §3.2 p6、提示词 p29 |
| **版本冻结 + ledger + declare-final** | git commit 快照 → 版本 + 最终声明 | 版本化、回滚、选版本 | 提示词 p29–30、Fig.7 p13 |
| **held-out 分离评测** | 每个官方版本 → 630 题 SWE-Pro（不回传） | 把「适应」与「泛化」分开 | §3.2 p6、§4.3 p11 |
| **约束合规审计** | 交付源码 + 执行产物 → 事后审计 | 约束「可检查」而非「建议」 | §3.4 p7（null result） |

### 2.4 关键表示与数据结构

- **harness 作为产物**：一个可运行的 `python -m harness ...` 包（`agent.py`/`tools.py`/`schemas.py`/
  `taskspec.py`/`prompts.py`/`runner.py`/`model.py` 等，p35），含执行环、工具注册、上下文管理、状态、
  生命周期、验证；RQ2 提示词明确要求**保留三种调用形式与别名**（p27）。
- **统一审计契约**：`result.json`（含诚实 `status`、artifact 路径、指标、错误）、`trajectory.jsonl`
  （每行一个结构化事件）、`response.md`、`stdout.log`/`stderr.log` + 域特定最终产物（`patch.diff` 等）（p27、Fig.3 p5）。
- **域最终产物**：Code→repo 状态 + patch；Data/MLE→submission + metrics；Writing→最终文本；
  Search→答案 + 引用证据（Fig.3 p5）。
- **版本与事件流**：git commit 冻结为不可变快照；`feedback/events.jsonl` 为 append-only、带单调 `seq`；
  `evals/<id>/` 存 `meta.json`、`cases.json`、`feedback_index.jsonl`（p30）。
- **三层信号语义**（p30）：① 任务正确性 `score`（平台固定 verifier 产出，`null` 既不算成功也不算失败）；
  ② 运行诊断 `adapter_status` / `harness_run_diagnostic`；③ 行为产物 `made_edit`/非空 patch/文件数。
  **关键**：`adapter_status=success` 仍可能 `score=0`，非空 patch 也可能全错。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| Creation · 覆盖 | — | 6 个 creator LLM × 4 域 × 5 benchmark，共 **2,207** 个下游实例 | 隐藏评测集不参与开发（p1、Table 2 p6） |
| Creation · Self-Eval 总分 | 人类工程参考 86.2 | Opus 4.8 最高 **67.8**（仍低于人类） | 每 creator×benchmark 独立造 3 个 harness，报 **avg@3**（Table 3 p8） |
| Creation · 域差 | 人类参考 | Writing 追平、**MLE 反超**（Opus/Gemini medal 32.9/32.4 vs 人类 24.0）；**Search 差距最大**、Code 仍落后 | Self-Eval avg@3（Table 3、Fig.4 p8–9） |
| Creation · 失败归因 | — | **77.8%** 的 Data 失败任务归因于 **harness 缺陷** | p7 |
| Creation · 成本 | — | MLE-bench token 用量相差约 **19 倍**，高成本**不**可靠地换来高分 | Fig.9、p8 |
| Creation · 状态/记忆缺口 | — | 18 个 Code 产物中 11/18 定义 State 类，仅 **1** 暴露保存接口、仅 **1** 实现周期性 checkpoint；**26,679** 条轨迹中**无** checkpoint 事件 | p8 |
| Creation · 死机制 | — | 108 个组件实例：72 真触发、18 部分、**18 从未触发（全是 state/memory）**；Writing 587 特征中 **124 为死代码** | p9 |
| Creation · 自测相关性 | — | 自测数量与下游分数的 Spearman **0.13–0.26（不显著）**；revision 调用达 **0.57（p≤.0005）** | p9 |
| Creation · 跨 executor | Self-Eval | Qwen 换 Gemini 后 BrowseComp **+17.6**、MLE **+12.9**；Opus SWE **69.3→33.0**、Writing **84.6→74.2**；Opus Search 重复查询率 **10.1%→88.2%** | avg@3（Fig.6、p10） |
| Evolution · 规模 | — | 9 条 lineage，**73** 个官方版本、**64** 次相邻切换 | 5 self-runtime + 4 fixed-Gemini（p11、Fig.7 p13） |
| Evolution · 增益与泛化 | H0 | self-runtime 5 个声明版本 held-out 全升，**+1.43~+4.44（均值 +3.11）**；fixed-Gemini 仅 Opus 升，其余 **3 条回归**（GPT-5.5：反馈 +2.4 → held-out **−10.32**，final gap 16.51） | Table 6 p12 |
| Evolution · 稳定性 | — | 64 次切换：**8 双基准回归、16 单基准回归、3 交叉权衡、7 无变化、27 落在噪声带内、2 明确正向、1 无代码改动**；同一 commit 波动约 **±4.75** pair 分 | p13 |
| Evolution · 死代码 | — | 169 个新函数/类：113 可达、**31 仅死代码可达、25 无调用者** | p13 |
| Evolution · 反馈可靠性 | — | 反馈与 held-out 同向仅 **34/64（53.1%）**；仅 **2/9** 声明版本是 held-out 最优；Opus 案例：99/100 报 success 但仅 48 通过 | p12–13 |
| Evolution · 诊断薄弱 | — | 专用轨迹接口仅被调用 **2 次**；显式检查的案例仅覆盖 189 个反馈任务的 **0.5%–40.2%**；某 GPT-5.5 候选过 5/5 Terminal 探针但全量仅 **0.584** | p12 |
| 约束合规 | — | 审计全部运行，**无** harness 通过禁止路径得分（null result） | §3.4 p7 |

### 2.6 论文自陈局限与边界条件

- 四类域**覆盖许多但非全部**真实部署；**人类基线不齐且不保证最优**（p15）。
- Unified-Eval **减弱但无法完全消除** executor 差异（harness–模型交互复杂）（p15）。
- Evolution **每个 creator–runtime 单元只有一条轨迹**、且有一个未完成的主 runtime 单元，held-out 只覆盖
  SWE-Pro——**不支持不确定性估计或群体级比较**（p15）。
- 开发环境 `D` 在**两阶段都固定**；**「演化出的 harness 能否自己充当进一步演化的开发环境」留作未来工作**（p15）——
  这一句几乎就是 SSEA 的立题。
- 明确声明：HarnessDev 测的是 **model-external learning**，**不主张**启发式学习能替代参数训练（p16）。
- 伦理：自动构造 harness 有**放大不安全工具使用**的风险；容器边界是**为可复现而非为隔离**，
  使用者应把生成的 harness 当作**不可信代码**更严格隔离（p16）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 优化目标是任务成功（SWE/QA/MLE/writing/search），无生存信号、无淘汰；harness 是「解题系统」非「生存系统」（p4、Table 2 p6） | 把 `<E>` 执行环换成生存控制环（FSL），`J` 从任务评分换成环境淘汰事实 |
| **C2** 自然语言只作观察员接口 | **◐** | harness **本身是代码**（符合「代码非自然语言」）；但产物运行时**在线调用 runtime LLM** 做语义决策，creator 也用 LLM 改代码（p7、p30） | 快环非语言化；creator（慢环）可用语言，但产物运行时不得把语言放进控制闭环 |
| **C3** 权重/记忆/技能三分离 | **◐** | 论文明确「**model-external learning**」、不动模型权重，harness 与权重分离（p16）；但无「记忆/技能/权重」三者显式分置；`S`(state) 与 memory 反而被自陈为最大缺口（p8） | harness 代码归 **ΔS 技能侧**；权重冻结；记忆另立 `ΔM` 并补 S/memory 缺口 |
| **C4** 低算力低带宽 | **✗/◐** | 一次 pair = 100+89 全量评估、端到端约 1–2 小时；10 对预算；MLE token 差 19 倍（p8、p29） | 用**重放/本地免费运行 + 探针配额**做廉价预筛；控制环信息结构化 |
| **C5** 精准回忆历史 | **◐** | paper 自陈 S/memory 是最弱环：仅 1/18 有保存接口、1/18 周期 checkpoint、26,679 轨迹无 checkpoint（p8） | 这正是 SSEA 记忆侧（Memento 检索 μ / FLEX 分层经验库 / LightMem 巩固）要补的 |
| **C6** 可自主修改自身代码与参数 | **✓** | 核心命题：creator **修改自己的 harness 代码**（执行环/工具/上下文/生命周期/验证）；四权拆解清晰——提案权=creator、边界权=约束条款+审计、验证权=平台 verifier+probe+full pair、**应用权=creator 自己 declare-final**（controller 不 accept/reject/rollback，p30） | 直接可对位 SSEA 自改四权；补「边界权」与「验证权」的外部锚 |
| **C7** 保存/恢复/变异/继承 | **✓/◐** | 版本冻结（frozen commits）、git 持久化、**rollback**（T4 revert、Opus 撤 setsid/killpg）、declare-final 选版本（p13、p38–41）；但**无 GenePackage、无跨会话继承、无种群**（单 lineage 单轨迹） | commit/ledger → 结构库版本；declare-final → 淘汰后存活版本；补种群与可遗传打包 |
| **C8** 给基因先验，不给知识语料 | **◐** | `H_seed` 是「弱但可运行、**policy-free**」的兼容层，接近结构先验（p4）；但成品 harness 含大量工具/提示（任务知识） | seed 只留结构先验（本能），后天知识不跨代 |
| **C9** 不设评分函数，只有淘汰函数 | **✗**（含 ◐ 亮点） | 演化由**外部 benchmark 分数**显式驱动，是评分搜索（p11、式 2）；但两处同向：**(a) 评分路径与 harness 隔离，自报状态永不计分（p7）；(b) telemetry 明示非评分目标、禁写装饰代码（p28）** | 分数→淘汰事实；保留「自报状态不计分」「装饰代码不得分」两条纪律 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 创新全在 harness 层（模块组合/信息流/版本），不动模型权重与算子；明说 external learning ≠ parameter training（p16） | — |

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子，直接用现成前沿 LLM | 符合借用立场 |
| **L2 信息流层** | **`H=<E,T,C,S,L,V>` 六模块控制面分解**（p29、Fig.3 p5） | **高**：给 SSEA 快环执行环与结构库提供模块边界语言 |
| **L3 学习层** | creator 从失败诊断改 harness 代码（非改参数）；反馈→编辑→重评→选版 | 中：harness 代码即「技能」载体的学习环 |
| **L4 演化层** | 版本冻结、rollback、declare-final、held-out 泛化、失败模式 | **高**：GenePackage 版本化与淘汰后存活版本的实测对照 |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| `H=<E,T,C,S,L,V>` | 快环 FSL 执行环 + 结构库的**模块边界定义** |
| creator（造/改）vs executor（跑） | **慢环 SEL（creator）vs 快环 FSL（executor）** 的分离证据 |
| probe / full pair / held-out 三层 | **四级验证门**（格式→沙盒→回归→环境实测）的对照与配额设计 |
| 评分路径隔离 / 自报状态不计分 | 验证门「**只判合法性、不打分**」的工程实现（直接修债务 25–28） |
| 诚实状态 `success/partial/failed` | 反「**假成功**」判据（债务 26/27/28） |
| git commit + ledger + declare-final | **Gene Manager（缺失组件）** 的版本管理雏形 |
| 死代码统计（可达/死码/无调用者） | 「机制是否真进入主路径」的**技能/机制有效性口径** |
| 「演化出的 harness 能否当进一步演化的开发环境」 | **SSEA 立题的对照陈述**：SSEA 主张 D 也可被自演化 |

### 3.4 债务与验收实验对应

- **可回应的已知债务**：
  - **债务 25/26/27/28（判据形状错、环境对无消费者通道报成功、技能失效被判成功）** ← 论文的
    「诚实状态契约」+「自报状态永不计分」+「`adapter_status=success` 仍可 `score=0`」（p7、p30）是**直接对症的工程口径**。
  - **「技能表示够不够」（0/33 之后仍未回答）** ← 论文「声明机制 ≠ 触发机制」的统计（108 实例中 18 从未触发、
    169 新函数中 25 无调用者，p9、p13）提供**「技能是否真被执行」的判定维度**。
  - **「睡眠期计算预算未定义」** ← 论文的 **pair 预算 / probe 配额 / 12 小时 liveness guard**（p29–30）是现成的预算/配额模板。
  - **Gene Manager 缺失、`rules` 零消费者** ← commit + ledger + declare-final + 死代码审计是**最小版本管理雏形**。
  - **记忆门「开得准不准」的选择性缺失** ← 论文 `S`/memory 缺口（p8）与「机制证据密度」分析（Fig.5 p10）可作记忆门**选择性**的外部参照。
- **可服务的验收实验**：服务**实验 4/5（架构变异与淘汰、基因继承）**的协议设计与**失败判据**；
  其「反馈集 vs held-out 方向一致率」可作 SSEA 慢环升版的**独立判据**。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | `H=<E,T,C,S,L,V>` harness 六模块分解 | 表示/形式化 | 改造移植 | 快环结构定义 / 结构库 | 执行环与结构库的模块边界 | 高 |
| 2 | creator–executor 分离 + Self/Unified-Eval | 协议 | 改造移植 | 慢环/快环分离 | 分清「改好系统」与「换强模型」 | 高 |
| 3 | 诚实状态契约（`success/partial/failed`；禁 plan/空产物充完成） | 协议 | **直接移植** | 验证门 / 判据 | 债务 26/27/28「假成功」 | 高 |
| 4 | 评分路径隔离（自报状态**永不计分**，只认环境最终状态） | 协议 | **直接移植** | 验证门 / C9 改造 | 「环境对无消费者通道报成功」 | 高 |
| 5 | 版本冻结 + ledger + declare-final + rollback | 工程/协议 | 改造移植 | Gene Manager（缺失） | 版本化、回滚、选版本 | 高 |
| 6 | probe / full-pair / held-out 三层信号 + 配额 | 协议 | 改造移植 | 验证门 / 睡眠期预算 | 廉价方向信号 + 稀缺实测预算 | 中 |
| 7 | 失败模式清单（回归/过拟合/executor 适配/死代码/并发冲突） | 证据 | 仅借思想 | 风险验收 / Misevolve 红队 | C6/C7 自改风险判据 | 高 |
| 8 | 「机制可达性」统计（可达 / 死码 / 无调用者） | 度量 | 改造移植 | 技能有效性审计 | 「技能表示够不够」 | 高 |
| 9 | 弱 seed 设计（可运行、policy-free、未改得 0 分） | 思想 | 仅借思想 | 基因先验 / 冷启动 | C8 结构先验边界 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C9 硬冲突**：Evolution 由**外部 benchmark 分数**驱动，是显式评分搜索；SSEA 只允许淘汰函数。
    → 改造方向：把「分数」换成环境侧淘汰事实；但**保留**「自报状态不计分」「装饰代码不得分」两条纪律。
  - **C1 冲突**：目标是任务成功而非生存。→ 执行环换生存控制环。
  - **C4 冲突**：全量 pair 评估昂贵（1–2 小时 / 对，10 对预算）。→ 重放/本地免费运行 + 探针预筛。
- **隐含假设与失效条件**：① 存在**可靠且不可被 harness 触及的外部 verifier**（论文的 verifier 由平台固定，
  p7）；② 能**把 held-out 与 feedback 干净分离**；③ 有 git/容器等可持久化载体。若这三条不成立，
  整篇的「能力/泛化」区分即失效。
- **算力 / 带宽 / 工程代价**：Creation 需 6 模型 × 4 域 × 3 复现；Evolution 需 10 对全量评估 +
  探针配额；复现门槛高。但**协议与判据本身**（诚实状态、score 隔离、held-out 分离）成本极低。
- **搬运后的可能退化模式**（论文**实测**，非推断）：
  1. **反馈集涨、held-out 跌**——GPT-5.5 在 fixed-Gemini 下反馈 +2.4 而 held-out **−10.32**（Table 6 p12）；
  2. **重复优化噪声分 → 过拟合**——同 commit 波动 **±4.75**，反馈与 held-out 同向仅 **53.1%**（p13）；
  3. **executor 适配陷阱**——Opus harness 换 executor 后 SWE **69.3→33.0**、重复查询率 **10.1%→88.2%**（p10）；
  4. **死代码膨胀**——169 新函数中 **31 仅死码可达、25 无调用者**（p13）；
  5. **并发会话冲突**——Opus I 两个 session 对同一文件做**相反编辑**，最终 commit 只改了 ledger（p41）；
  6. **creator 从不修自己的缺陷**——GPT-5.5 H **54% 工具调用被拒**却始终未修（p39）。

---

## 6. 组合分析

### 6.1 关系图谱

| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可运行 harness 代码载体、外部 verifier、held-out 分离 | 无这三样，能力/泛化不可分 |
| **互补（最紧）** | **Misevolve**（已有卡片 A/P1） | Misevolve 给「模型/记忆/工具/工作流四路径误演化」**威胁模型**；HarnessDev 给**实测失败数据**（回归、过拟合、executor 适配、死代码）——威胁模型 × 实测证据互锁 |
| 互补 | **Dream-RSI**（A/P1） | 用重放模拟器对 harness 变体做**廉价预筛**，再占真实 pair 预算（直接缓解 C4 成本） |
| 互补 | **PSN**（A/P1） | PSN 的技能契约/成熟度门控/回滚验证，与 HarnessDev 的**版本冻结 + rollback + 验证门**同构；HarnessDev 提供跨版本实测判据 |
| 互补 | **ADAS**（B/P2） | ADAS 的「代码搜索空间 + 档案/谱系/垫脚石」是**种群式**架构搜索；HarnessDev 是**单 lineage 反馈驱动**的对照——两者合起来覆盖「种群」与「梯度式」两条 L4 路线 |
| 互补 | **Memento / FLEX**（A/P1、B/P1） | 补 HarnessDev 自陈的最大缺口 `S`/memory（仅 1/18 有保存接口，p8） |
| 互补 | **SEDM**（B/P1） | A/B 准入验证可作 HarnessDev「版本是否进官方轨迹」的准入官 |
| 自指对照 | **Gödel Agent**（B/P1） | Gödel 给「自指递归自改进」的形式化；HarnessDev 说明**当前前沿模型的自改在真实 benchmark 上并不稳定**——是对 Gödel 式北极星的**现实校验** |
| 同题对照（同期基准） | **HarnessOpt-Bench**（arXiv:2608.06301）、**Evo-Bench**（2608.09096）、**Meta-Agent Challenge**（2606.04455） | HarnessOpt 聚焦「优化给定 harness」、Evo-Bench 聚焦「跨域最终版本质量」、Meta-Agent 聚焦「Creation」；HarnessDev 把它们**串成 Creation→Evolution 并加 held-out**（p14–15） |
| 风险对照（同目录另一篇） | **Rethinking the Evaluation of Harness Evolution for Agents**（arXiv:2607.12227，ref [50]） | matched-budget 研究发现 harness 演化**可能过拟合搜索基准、甚至不如更简单的搜索基线**；HarnessDev 的 Table 6/p13 与之**互为佐证**——两篇一起构成「自演化会退化」的独立证据 |
| 方法族对照 | **Self-Harness**（2606.09498）、**HarnessFix**（2606.06324）、**Harness-R1**（2608.02276）、**HarnessCompass**（2608.01918）、**VeRO**（2602.22480）、**Meta-Harness**（2603.28052）、**HarnessBank**（2607.13683）、**Recursive harness self-improvement**（2607.15524）、**Continual harness**（2605.09998） | 这些**提出方法**（派生编辑 + 回归测试 / 溯源修复 / 训练 harness 工程师 / 抗过拟合 / 版本快照 / 编码 agent 提案 / 语义基因库门控）；HarnessDev **不提出方法，只做统一协议下的评测**（p15） |
| 方法族对照 | **LLM-as-Code**、**Live-SWE-agent**、**Ouroboros**、**AgentEvolver** | 均为「让 LLM 写/改代码即自我改进」的同族主张；HarnessDev 的实测退化模式（held-out 跌、executor 适配、死代码）是**对整族的统一风险证据**，可作它们的验收反例集 |
| 上位/替代 | **Harness-Bench**（2605.27922） | 只测「harness 选择如何改变模型表现」；HarnessDev 进一步把 harness 当**被开发对象** |

### 6.2 推荐组合方案

1. **自演化风险红队（HarnessDev × Misevolve）**
   - 形态：用 Misevolve 的四路径威胁模型造**违规/退化场景**，用 HarnessDev 的判据（反馈 vs held-out 方向一致率、
     死代码率、executor 适配差、噪声带宽度）做**量化验收**。
   - 新增能力：把「自改是否安全」从定性清单变成**可打分/可淘汰的验收门**。
   - 新增风险：两套判据可能口径冲突，需先统一「成功」定义。
2. **廉价预筛演化（HarnessDev × Dream-RSI）**
   - 形态：harness 变体先进重放/本地免费运行 + 探针配额，通过后再占 10 对全量预算。
   - 新增能力：在**低算力约束（C4）**下保住 held-out 泛化评测的独立性。
   - 新增风险：重放与真实分布偏移会引入新噪声。
3. **版本管理与门控（HarnessDev × PSN / SEDM）**
   - 形态：commit 冻结 → 结构库版本；rollback 与成熟度门控由 PSN 提供；SEDM 做 A/B 准入。
   - 新增能力：Gene Manager 的最小可用形态。
   - 新增风险：过度门控会压低探索（与 C7「淘汰+繁衍」的多样性张力）。

### 6.3 本篇在组合中的典型角色

- **自演化失败模式的实测证据源 + harness 工程验收基准 + 版本管理/验证门协议供给**：
  管「**改 harness 这件事本身会不会退化、怎么判、怎么回滚、怎么分开适应与泛化**」。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 直击 SSEA 最核心的「SSEA 是否是可自演化的 harness」与 C6/C7（实测于论文设定） |
| 立场兼容性 | **2** | C1（生存）、C4（算力）、C9（外部评分）三项冲突；但 C2/C10（代码载体、创新在 L2/L4）与「score 隔离/自报状态不计分」高度对齐（实测+推断） |
| 可搬运性 | **4** | 协议与表示（六模块、诚实状态、score 隔离、配额）可干净拆出；benchmark 复现门槛高（推断） |
| 证据强度 | **5** | 6 creator × 9 lineage × 73 版本 × 64 切换 × 2,207 实例 + 630 held-out；失败模式均有具体数字（实测） |
| 组合价值 | **4** | 与 Misevolve/Dream-RSI/PSN/ADAS/Memento/FLEX 多点互补（推断） |
| 落地成本 | **3** | 协议/判据落地极低；复现完整 benchmark 昂贵（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用**（并承担强 **D 基准对照**角色）——理由：不采纳其外部评分驱动的演化目标（违 C9）
  与任务导向目标（违 C1）；但**采纳** ①`H=<E,T,C,S,L,V>` 六模块分解；②creator–executor 分离；
  ③**诚实状态契约 + 评分路径隔离**（直接修债务 25–28）；④版本冻结/ledger/rollback/declare-final；
  ⑤把其**实测失败模式清单**收编为 C6/C7 的风险验收判据。
- **优先级：P1**——债务 25–28 与「技能表示够不够」正在卡关，本文的判据可立即用。
- **建议动作**：
  1. 把「诚实状态契约 + 自报状态不计分」写入 SSEA 验证门规范，逐条对照债务 26/27/28 做回归；
  2. 在 `sse_protocols` 用 `H=<E,T,C,S,L,V>` 重述快环执行环 + 结构库的模块边界；
  3. Gene Manager 以 commit 冻结 + ledger + declare-final 为最小形态落地，补回滚；
  4. 引入「机制可达性」审计（可达 / 死码 / 无调用者），回答「技能表示够不够」；
  5. 把论文的**退化模式清单**（反馈涨/held-out 跌、噪声带、executor 适配、并发冲突）固化为慢环升版的**证伪清单**。
- **最小验证实验**：
  - **双臂 / 消融设置**：SSEA 慢环对 harness/结构库产出变体——A 臂用「外部分数排序选版本」（论文做法），
    B 臂用「**淘汰事实 + 诚实状态门 + held-out 分离**」（SSEA 做法）；同 creator、同算力预算，≥8 seed。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：
    ①机制计数：新机制进入主路径比例、死代码率（分母=新增函数/机制数）；
    ②行为差：**反馈集与 held-out 的方向一致率**（论文基线 53.1%）、噪声带宽度（论文 ±4.75）；
    ③淘汰结果：存活版本在 held-out 上的增益（论文 self-runtime 均值 +3.11）。
  - **预期与证伪条件**：预期 A 臂复现论文的**过拟合退化**（held-out 增益低于反馈增益、方向一致率≈50%），
    B 臂 held-out 增益更稳；**若 B 臂相对 A 臂在 held-out 上无差异**，则论文的过拟合结论在 SSEA 低算力场景**不成立**，
    需重新评估是否引入外部信号。
- 若 **E 不采用**：不适用（本篇采纳为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的「淘汰函数」如何替代本文的 benchmark 分数，同时保住 held-out 泛化评测的独立性？
  2. `H=<E,T,C,S,L,V>` 与 SSEA「快环 FSL + 结构库」的精确边界如何划分？哪些属宪法层不可变？
- **需补查的文献或资料**：
  3. 论文未给独立代码仓库——benchmark release / 复现资产是否公开？
  4. 同目录 **Rethinking the Evaluation of Harness Evolution for Agents**（2607.12227）的 matched-budget 结论细节，
     与本文 Table 6 的过拟合证据如何合并成一份 SSEA 验收清单；
  5. HarnessOpt-Bench（2608.06301）、Evo-Bench（2608.09096）是否提供可直接复用的 held-out 切分。
- **需人工核对的公式 / 实现**：
  6. 式 1、式 2（pair score 定义）在 SSEA 中的对应；「pair 预算 / probe 配额」与 SSEA 睡眠期预算的换算；
  7. 「评分路径隔离」在无外部 verifier 的 SSEA 环境里如何落地（谁持有最终环境状态的判定权）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “HarnessDev, a benchmark that shifts the unit of evaluation from task outputs to runnable infrastructure.” | p1 |
| “generated harnesses remain substantially behind mature human-engineered references on code and on search and research, while matching or exceeding … on writing and machine-learning experimentation” | p1 |
| “Evolution produces some performance gains, but they are unstable and transfer only partially to held-out tasks.” | p1 |
| “GPT-5 solves 35.2% of Terminal-Bench 2.1 inside Terminus 2 but 49.6% inside Codex CLI” | p1 |
| 式(1)：`(L_C,D)→H, (H,L_E,x)→y, J→score` | p4 |
| “Weak seed … a runnable compatibility layer, not a task-solving agent … scores zero on every downstream benchmark.” | p4 |
| “a harness can be abstracted as `H = <E, T, C, S, L, V>`” | p29 |
| “The score path is isolated from the harness: a harness’s self-reported status is never a scoring input … no harness can earn score by asserting success.” | p7 |
| “no harness obtained score through a prohibited route … we report the outcome as a null result.” | p7 |
| Table 3：Opus 4.8 Self-Eval Avg **67.8** vs 人类参考 **86.2**；MLE medal 32.9/32.4 vs 人类 24.0 | p8 |
| “77.8% of failed Data tasks are attributed to harness defects” | p7 |
| “11/18 artifacts define a State class, but only one exposes a state-saving interface and only one implements periodic checkpointing. No checkpoint event appears in 26,679 recorded task trajectories.” | p8 |
| “of 108 component instances in Code, 72 trigger in real runs … 18 are never observed; all unobserved instances concern state and memory” | p9 |
| “self-test … Spearman correlation … only 0.13–0.26 and is not significant, whereas revision calls reach 0.57 (p≤.0005)” | p9 |
| “Opus … SWE-Pro score falls from 69.3 to 33.0 under Gemini … duplicate-query rate rises from 10.1% to 88.2%” | p10 |
| Table 6：Fixed Gemini / GPT-5.5 反馈 **+2.4** → held-out **−10.32**，final gap **16.51** | p12 |
| “of the 64 official switches, eight regress on both benchmarks, 16 show a single-benchmark regression … 27 report gains that remain inside the repeated-run noise band … two have clear positive evidence” | p13 |
| “The same commit can vary by about ±4.75 pair-score points” | p13 |
| “of 169 new functions or classes, 113 are reachable from the entry point, 31 are reachable only through dead code, and 25 have no caller.” | p13 |
| “feedback and held-out scores move in the same direction only 34 times (53.1%), and only 2/9 declared versions are held-out optimal” | p13 |
| “the dedicated trajectory interface is called only twice, and explicitly inspected cases cover just 0.5%–40.2% of the 189 feedback tasks” | p12 |
| “one GPT-5.5 candidate passes all five Terminal probes but scores only 0.584 on the full set” | p12 |
| “The controller performs no accept/reject, no best-version selection, no rollback, no failure attribution, and no feedback summarization.” | p30 |
| “whether an evolved harness can itself serve as the development environment for further evolution is left to future work.” | p15 |
| “HarnessDev measures model-external learning and does not claim heuristic learning can replace parameter training.” | p16 |
| 案例 Opus I：两个并发 session 对同一文件做相反编辑，最终 commit 只改 LEDGER.md | p41 |
| 案例 GPT-5.5 H：“The creator never repaired its own 54% tool-call rejection.” | p39 |
