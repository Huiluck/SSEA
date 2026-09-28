# 论文分析卡片 · AgentGym

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2024-06-06 AgentGym Evolving Large Language Model-based Agents across Diverse.pdf` |
| 标题 | **AgentGym: Evolving Large Language Model-based Agents across Diverse Environments** |
| 作者 / 机构 | Zhiheng Xi, Yiwen Ding, Wenxiang Chen, Boyang Hong, Honglin Guo, Junzhe Wang, Dingwen Yang, Chenyang Liao, Xin Guo, Wei He, Songyang Gao, Lu Chen, Rui Zheng, Yicheng Zou, Tao Gui, Qi Zhang, Xipeng Qiu, Xuanjing Huang, Zuxuan Wu, Yu-Gang Jiang；Fudan NLP Lab & Fudan Vision and Learning Lab（p1） |
| 发表时间 / 出处 | arXiv:2406.04151v1 [cs.AI]，2024-06-06；45 页 |
| 论文链接 | arXiv:2406.04151；项目页 https://agentgym.github.io |
| 代码链接 | https://github.com/WooooDyy/AgentGym（摘要 p1） |
| 标签 | 异构环境平台 · 统一环境接口(HTTP/EnvClient/AgentController) · 轨迹集(AgentTraj/-L) · 基准(AgentEval) · 自演化(BC→探索→加权 SFT) · 多环境进化 |
| **应用裁决** | **B 零件采用**（搬**环境接口标准化协议**——HTTP 服务 + EnvClient + AgentController 统一 observation/action/step 接口，及**轨迹收集流水线**；**不搬**外部奖励驱动的 AGENT EVOL、语言 ReAct 控制环、BC 知识语料） |
| 优先级 | **P1**（环境接口标准化是 SSEA「6 个 Action 通道 / `skill` 通道无消费者、债务 27」的前置；协议级、无模型权重依赖；不解决 Gene Manager 缺口） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：构建跨环境自演化的通用 LLM 智能体需要三件套——**多样环境 + 轨迹集 + 可扩展演化方法**；作者提出 **AgentGym**（14 环境 / 89 任务 / 20509 指令，每个环境部署为 HTTP 服务并提供统一接口）与 **AgentEvol**（先 BC 得基座，再在**未见指令**上探索、按奖励加权 SFT 迭代），实证演化后智能体在 WebShop/ALFWorld/BabyAI 上超过 BC 上界与 SOTA（摘要 p1、Table 3 p8）。
- **对 SSEA 的意义**：它是**环境侧接口最工程化**的标本——把异构环境统一成 `observation / available_actions / step / reset` 单一接口，并用 AgentController 做「评估 + 采样 + 训练」中枢。SSEA 环境通道目前封闭（6 Action 通道、`skill` 无消费者、债务 27），**环境接口标准化正是补这个洞的前置**；其探索→学习回路可作慢环 SEL 提案空间的形状参照（信号须换，见 C9）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：如何构建**跨多样环境自我演化**的通用智能体，从「模仿」走向「交互式学习」（p1–2）。
- **它指出的既有方案缺陷**（p2、§6 p9）：① 人类监督 BC 需熟练标注员与经费，难扩展、探索不足；② 隔离环境自改进只得**专才**，泛化差；③ 标准 RL 在多环境下采样空间大、长期任务，计算复杂度高、训练不稳定（§4.2 p5）。

### 2.2 核心思想（关键 insight）
1. **环境即 HTTP 服务 + 统一接口**：14 环境各部署独立服务（防依赖冲突），对外暴露统一 API，客户端封装为函数，控制器做中枢——「异构环境 → 单一可训练/可评测接口」的解耦（§3 p4；Appendix D p19–20）。
2. **自演化 = 模仿起步 + 跨环境探索 + 奖励加权回归**：把 RL 写成概率推断，导出「探索步（`q_{m+1}∝r·π`）+ 学习步（奖励加权 NLL）」的**离线（off-policy）**回路，规避 on-policy RL 的不稳定（§4.2 Eq.5–8 p5–7）。
3. **未见指令上的演化**：探索用指令集 `Q^e` 大于 BC 用的 `D_s`，检验「面对未见任务能否自我演化」（§4.2 p7；§5.1 p7）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图/页） |
|---|---|---|---|
| **统一环境接口（HTTP）** | 环境动作 → 观察/可用动作/奖励 | `/createEnv`、`/observation`、`/available_actions`、`/step`、`/reset` | Appendix D p19 |
| **EnvClient** | HTTP 服务 → 可调用函数 | 把环境封装成统一函数接口 | Appendix D p19–20 |
| **AgentController** | 智能体 + 环境 → 评估/采样/训练 | 连接智能体与环境的中枢 | §3 p4；Appendix D p20 |
| **ReAct 轨迹表示** | `(h_t,a_t,o_t)` 序列 | 统一 thought+action+observation 格式 | §2 Eq.1–2 p3–4 |
| **BC 目标 `J_BC`** | AgentTraj → 基座智能体 | 模仿起步，给基础指令跟随与先验 | §4.1 Eq.3 p5 |
| **AGENT EVOL 探索步** | 指令 `Q^e` + 策略 `π_m` → `D_m` | 采样未见指令轨迹并算奖励 | §4.2 p6–7；Algorithm 1 p6 |
| **AGENT EVOL 学习步** | `D_m`（含 `D_s`）→ `π_{m+1}` | 奖励加权 NLL，离线更新 | §4.2 Eq.8 p7 |
| **数据合并 Strategy 1** | 当前轨迹 + 初始轨迹 → 训练集 | 比「与上一轮轨迹合并」更稳定 | §5.3 图 3 p8 |

### 2.4 关键表示与数据结构
- **环境形式化**：每个环境 `e` 的任务是 POMDP `(U,S,A,O,T,r)`，含指令空间 `U`、状态/动作/观察空间、确定性转移 `T:S×A→S`、奖励 `r:S×A→R`（§2 p3）。
- **轨迹** `τ=(h_1,a_1,o_1,…,h_T,a_T)∼π_θ(τ|e,u)`，最终奖励 `r(e,u,τ)∈[0,1]`（§2 Eq.1 p4）。
- **接口端点**：`/createEnv`、`/observation`、`/available_actions`、`/step`、`/reset`（Appendix D p19）。
- **数据集**：AgentTraj（6130）/ AgentTraj-L（14485）；AgentEval（1160 指令）；指令总数 20509（Table 2 p4）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 / 出处 |
|---|---|---|---|
| 11 环境主实验（Llama-2-Chat-7B） | BCbase / BClarge / SOTA | WS 66.5→73.5→**76.5**；ALF 77.5→83→**88**；Baby 69.3→74.19→**82.7**；TC 44→60→**64** | 成功率/奖励，Table 3 p8 |
| 与闭源/开源模型对比 | GPT-4-Turbo、Claude-3、AgentLM | AgentEvol 在 WS/ALF/Baby 超 GPT-4-Turbo（15.5/67.5/72.83） | 同上，Table 3 p8 |
| 数据合并策略与迭代 M | Strategy 1 vs 2 | 与**初始**轨迹合并更稳定；M 增大先升后收敛，取 **M=4** | 4 任务，图 3 p8 |
| 采样数 K | K=1/2/3 | K=1 77.0/88.0/82.9/65.0 → K=3 78.5/89.0/83.6/68.0（增益不显著），取 **K=1** | 4 任务，Table 4 p9 |
| 探索范围消融 | 有限 vs 更广 | 有限范围也提升但不显著（WS 70.0 vs 77.0）⇒ 有效演化需**更广环境** | Table 4 p9 |
| 不同骨干 | Llama-2-13B、DeepSeek-Coder-1.3B | AgentEvol 均 ≥ BClarge（如 13B ALF 85→89.5） | Table 5 p9 |
| 成功+失败轨迹（DPO） | AgentEvol | DPO 75.0/86.5/78.3/58.0 < AgentEvol 77.0/88.0/82.9/65.0 | Table 6 p9 |
| 交互轮数 | 各模型 | AgentEvol 轮数最少且性能最好（ALF 14.0、Baby 4.3） | Table 7 p21 |

### 2.6 论文自陈局限与边界条件
- **明确自陈（Appendix A p16）**：① 每轮只采样一次（K=1），未探索更多采样的上界；② 仅在三个模型（Llama2-Chat-7B/13B、DeepSeek-Coder-1.3B）验证，未在更强更大基座验证。
- **假设依赖**：环境可文本化、智能体为 LLM（ReAct）；奖励有效且跨环境可比（§5.1 p7）。
- **不适用**：不涉及权重/记忆/技能三分离，不涉及遗传继承，不涉及生存控制环。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 控制环是 LLM 的 ReAct 文本环：`h_{t+1}∼π_θ` 先出 thought 再出 action（§2 p4），全篇为语言生成架构 | **只搬环境接口层**（POMDP 元组 + HTTP 统一接口），控制环换成 FSL/SEL；被测对象改为非语言控制器 |
| **C2** 自然语言只作观察员接口 | **◐** | 环境侧有**结构化** observation/action space（§2 p3）；但**在线闭环把语言 thought 直接喂进控制环**（ReAct，p4）；**离线合成侧**用 GPT-4 扩指令、SOTA 标注轨迹（§3 p4–5） | **语言角色区分**：离线合成侧（指令扩写、轨迹标注）可留语言；在线闭环侧只取结构化 `observation/available_actions`，语言仅入日志/解释面 |
| **C3** 权重/记忆/技能三分离 | **—** | 仅更新策略权重 `θ`（BC/加权 NLL），无记忆/技能独立通道（§4 p5–7） | — |
| **C4** 低算力低带宽 | **✗** | 8×A100-80GB；Llama-2-7B 四轮演化约 **20 小时** + 测试 1 小时（Appendix E p20） | 仅借**接口协议**（纯工程、无权重依赖）；在线侧不引入 LLM |
| **C5** 精准回忆历史 | **—** | 未提及（上下文仅交互历史 `c_{t-1}`，Eq.2 p4） | — |
| **C6** 可自主修改自身 | **◐** | 策略参数经奖励加权 NLL 自更新（Eq.8 p7），属**参数级**自修改；但**四权不分**（提案=探索采样、验证=奖励、应用=训练），无代码自改 | 借「探索→更新」形状，但**验证权交回四级验证门**（只判合法性），应用权交淘汰函数 |
| **C7** 可保存/恢复/变异/继承 | **◐** | 跨迭代保留策略版本 `π_{θ_m}`（Algorithm 1 p6），release checkpoints；但**无 GenePackage / 遗传继承** | 仅借「版本化策略」；继承机制另寻（GenePackage） |
| **C8** 给基因先验，不给知识语料 | **✗** | AgentTraj 是**专家轨迹知识语料**，用于 BC 注入后天能力（§4.1 p5）——正是「给知识语料」的反面 | 若搬到 SSEA，AgentTraj 只能作**评测/对照**，**不入基因**；环境接口的**结构契约**（available_actions/step 形状）才可作结构先验 |
| **C9** 不设评分函数，只有淘汰函数 | **✗** | 奖励 `r(e,u,τ)∈[0,1]`（或二值）**直接驱动**学习：`J_Evol=E[r·log π]`（Eq.8 p7）；主指标为成功率/奖励（Table 3 p8）——**纯外部评分** | **只搬淘汰式件**：环境接口的**合法性检查**（action 是否在 available_actions 内、step 是否可执行）；**丢弃**奖励加权训练与成功率选优 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 全篇为平台/接口/演化算法，无新 L1 算子（骨干用 Llama-2 / DeepSeek） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子（Llama-2-Chat / DeepSeek-Coder 骨干） | 符合「借用」立场 |
| **L2 信息流层** | **环境接口标准化**：HTTP 服务 + EnvClient + AgentController，统一 observation/action/step/reset；环境与其余部分解耦（Appendix D p19–20） | **高**：正是 SSEA 环境层缺的「统一接口契约」，可作 FSL 读结构化信号的接口骨架 |
| **L3 学习层** | AGENT EVOL 的「探索→奖励加权回归」离线回路（§4.2 Eq.8） | 中：可作 SEL 提案空间的组织参照，但其信号来自外部奖励（须换） |
| **L4 演化层** | 多环境（14 环境 / 89 任务）作跨环境选择压力 | 中：为「环境即淘汰函数」提供「异构环境族」的工程形状；但无继承/变异 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| **HTTP 统一接口**（`/createEnv`/`/observation`/`/available_actions`/`/step`/`/reset`） | **新增：SSEA 环境层接口契约**——每个 Action 通道须声明可用动作与执行反馈，回应债务 27（通道无消费者仍报成功） |
| **EnvClient / AgentController** | 新增：环境客户端 + 控制器（评估/采样/训练中枢），对应环境侧「通道消费者」接线 |
| **AgentTraj / AgentTraj-L** | 仅作**评测/对照**（C8 冲突，不入基因） |
| **AGENT EVOL（探索 + 加权 SFT）** | 慢环 SEL 提案空间的**形状参照**（仅借思想；信号须换成淘汰式） |
| **AgentEval / 交互轮数指标** | 验收实验的**评测口径**参照（成功率 + 轮数） |
| **BC 基座** | 对照（C8 冲突：后天知识不跨代） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **环境对无消费者通道报成功（债务 27）、`skill` 通道无消费者**：AgentGym 要求每个环境**显式声明 `available_actions`** 并实现 `/step` 执行反馈——正是「通道必须有消费者」的接口形状（Appendix D p19）。**环境接口标准化是补这个洞的前置**。
  - **6 个 Action 通道封闭**：其「环境 = HTTP 服务 + EnvClient」解耦范式，可作 SSEA 把异构通道统一成单一可训练/可评测接口的模板。
- **可服务的验收实验**：不解决 Gene Manager 缺口（实验 4/5 仍卡）；但可作**实验 3（技能固化 0/33）**与危险回避率饱和项的**接口契约前置检查**——先确保「每通道有消费者、action 可被 step 消费」。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **统一环境接口（HTTP `/createEnv`/`/observation`/`/available_actions`/`/step`/`/reset`）** | 协议 | 改造移植 | SSEA 环境层契约 | 通道封闭、债务 27 | 高 |
| 2 | **EnvClient + AgentController 中枢**（评估/采样/训练） | 工程实现 | 改造移植 | 环境客户端 + 控制器 | 通道消费者接线 | 高 |
| 3 | **ReAct 轨迹统一格式**（`h_t,a_t,o_t`） | 表示 | 改造移植 | 轨迹/日志格式 | 统一观察/动作记录 | 中高 |
| 4 | **AGENT EVOL 探索→学习回路**（离线、避免 on-policy 不稳定） | 思想 | 仅借思想 | SEL 提案空间 | 提案组织 | 中 |
| 5 | **数据合并 Strategy 1**（当前轨迹 + 初始轨迹） | 算法 | 仅借思想 | 慢环停机/合并判据 | 防过拟合与漂移 | 中 |
| 6 | **奖励加权 NLL / 成功率选优** | 算法 | **仅作对照** | — | C9 反面标本 | 中（负例价值高） |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**：**C9（最重，✗）** 奖励 `r∈[0,1]` 直接驱动 `J_Evol=E[r·log π]`（Eq.8 p7）→ 只取接口合法性件，丢弃奖励训练与选优；**C2（◐）** 在线闭环用 ReAct 语言 thought（p4）→ 在线侧只用结构化 observation/action；**C1（✗）** 整体语言智能体 → 只搬环境接口层；**C4（✗）** 8×A100/20h（p20）→ 仅离线协议搬运；**C8（✗）** AgentTraj 是知识语料（p5）→ 不入基因，只作对照。
- **隐含假设与失效条件**：假定环境可文本化、被测对象是 LLM；假定奖励跨环境一致且有效（§5.1 p7）。若奖励不一致（论文自陈多环境 reward consistency 是问题，§6 p9），加权学习失效。
- **算力 / 带宽 / 工程代价**：协议层搬运成本低（HTTP 接口、无权重依赖）；学习回路成本极高（20h / 8×A100）。
- **搬运后的可能退化模式**：若照搬「奖励加权 SFT + 成功率选优」，SSEA 会退化成**语言智能体自演化环**（违反 C1/C2/C9）；若只用接口契约而无**通道消费者准入**，债务 27 的「无消费者报成功」依旧存在。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 环境服务化 + EnvClient + 统一 observation/action 接口 | 用它之前需先有「环境可独立部署 + 统一接口」 |
| 直接前身 | **AgentBench**（Table 1 p4：8 环境、仅评测、无轨迹、无演化） | AgentGym 在其上加「训练 + 轨迹集 + 多环境演化」（14 环境、Eval&Train、Traj、Multi-Env Evol） |
| 互补（环境契约侧） | **AutoEnv**（`BaseEnv/ObsEnv/SkinEnv` 三层抽象 + 三阶段验证） | AutoEnv 给「规则/观察解耦 + 判据校验」；AgentGym 给「统一接口 + 轨迹流水线」，拼成完整环境层 |
| 互补（规模化工厂） | **ScaleEnv**、**Agent-World**（`(D,F)` 环境包 + 通道消费者准入 + 可执行验证 `V_code`） | Agent-World 的「通道消费者准入」正补 AgentGym 缺的「无消费者检测」 |
| 互补（同族环境集） | **GEM（A Gym for Agentic LLMs）**、**REASONING GYM**（均同批/同族） | 均为「环境集合作训练/评测场」；AgentGym 独有「HTTP 统一接口 + 多环境演化回路」 |
| 替代/被替代 | **ALFWorld**、**WebShop**（单一环境） | AgentGym 把 ALFWorld/WebShop 等**收编为子环境**，用异构族替代单域集 |
| 组合 | **PSN / SkillWeaver**（技能侧）、**Misevolve**（误演化红队） | AgentGym 的接口契约可作技能通道的「消费者准入」形状；Misevolve 红队清单可与之互证 |
| 反例/警示 | **AutoEnv**（外部奖励 + 上界不可信） | 两者都触碰 C9；AgentGym 是「奖励直接驱动学习」的反面标本 |

### 6.2 推荐组合方案
- **组合**：本篇 + **Agent-World**（+ 抽象侧 **AutoEnv**）
- **接口形态**：AgentGym 提供**统一环境接口**（`/observation`、`/available_actions`、`/step`、`/reset`）与**轨迹流水线**；Agent-World 提供**通道消费者准入**与可执行验证 `V_code`；AutoEnv 提供三层抽象与判据健康度检查。三者组成 **SSEA 环境层「接口标准化 → 消费者准入 → 判据校验」** 的补洞链。
- **组合后新增能力**：SSEA 的 6 个 Action 通道在**接线前**即可体检：先统一接口（AgentGym）→ 再验每通道有消费者（Agent-World）→ 再验判据有区分度（AutoEnv）。
- **新增风险**：若不加约束，三套外部度量会合流成新的「外部评分系统」（C9 违规）；须硬性规定接口只输出**合法/非法、通过/拒绝**，不输出分数、不排序。

### 6.3 本篇在组合中的典型角色
- **环境接口标准化器 / 通道消费者准入的前置**：管「异构环境如何统一成单一可训练/可评测接口」，是 SSEA 环境侧补洞的**第一步**。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击环境接口标准化（债务 27 前置），SSEA 环境侧是当前最紧缺口之一（实测：14 环境/统一接口 p4、p19–20） |
| 立场兼容性 | **2** | C1/C4/C8/C9 硬冲突（语言控制环 p4、8×A100 p20、知识语料 p5、奖励驱动 Eq.8 p7）；C2 部分冲突；仅接口层可净化为兼容 |
| 可搬运性 | **4** | 接口协议与端点清晰（p19），无模型权重依赖；轨迹/平台有代码仓库（实测） |
| 证据强度 | **4** | 14 环境/89 任务/11 环境主实验/多骨干/多消融（Table 2–6 p4–9）；扣分项：K=1、仅 3 模型验证（自陈 p16） |
| 组合价值 | **4** | 与 AgentBench/AutoEnv/ScaleEnv/Agent-World/GEM/REASONING GYM/ALFWorld/WebShop 天然同族（推断为主） |
| 落地成本 | **3** | 接口协议搬运成本低；若照搬其学习回路成本极高（20h/8×A100，实测 p20） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：其**环境接口标准化协议**（HTTP 服务 + EnvClient + AgentController 统一 observation/action/step）与**轨迹收集流水线**可干净拆出，正面回应 SSEA 环境侧通道封闭（债务 27）的前置需求；但**语言控制环 + 外部奖励学习**与 C1/C2/C9 硬冲突，整体框架不采用。
- **优先级：P1** —— 环境接口标准化是补「通道无消费者」洞的前置，当前最紧。
- **建议动作**：① 把**统一环境接口**抽为 SSEA 环境层契约，要求**每通道显式声明可用动作与执行反馈**，回应债务 27；② 引入 **Agent-World 式通道消费者准入**（无消费者通道拒绝注册，而非报成功）；③ 明确语言角色分界（语言只在离线合成侧与观察员接口，禁入在线控制环）；④ 建 issue：`环境接口标准化（AgentGym 协议）`，挂债务 27 与实验 3。
- **最小验证实验**：
  - **双臂/消融**：取封闭的 **`skill` 通道**（无消费者）。**臂 A**＝现接口（`skill` 送动作后报成功）；**臂 B**＝现接口 + AgentGym 式契约（该通道须声明 `available_actions`，`/step` 返回执行反馈；无消费者时**拒绝**）。
  - **判据分档**：① 机制计数（通道数、有消费者通道数、无消费者通道是否被拒）→ ② 行为差（同一 `skill` action 在臂 A/臂 B 的返回值：成功 vs 拒绝）→ ③ 淘汰结果（是否判该通道非法并接线）。
  - **预期与证伪**：预期臂 B 下 `skill` 通道调用返回**「无消费者/非法」**而非成功 ⇒ 债务 27 可被接口契约暴露。**证伪**：若臂 B 仍报成功，则仅靠接口契约不足，须引入 Agent-World 式**消费者注册表**。
- 若 **E 不采用**：不适用（裁决为 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：① SSEA 环境接口统一为「HTTP 服务 + EnvClient」还是进程内直调（后者更合 C4 低带宽）？② 接口契约是否作为**通道注册前置**（默认必过）？
- **需补查的文献或资料**：③ **ScaleEnv（2026-02-06）、Agent-World、GEM（2025-10-01）、REASONING GYM（2025-05-30）** 尚**无卡片**，需补读完成环境族图谱。④ 项目 `docs/06` 债务 27 原文定义，以对齐「无消费者通道报成功」措辞。
- **需人工核对的公式 / 实现**：⑤ AGENT EVOL 的奖励加权 NLL（Eq.8 p7）改用**淘汰式信号**后，如何保持「探索→更新」回路形状而不引入打分？⑥ 环境接口的 `available_actions` 在 SSEA 生存域（连续/结构化信号）如何泛化，论文例均为文本动作（Appendix C p16–19）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “We identify a trinity of ingredients: 1) diverse environments … 2) a trajectory set … 3) an effective and scalable evolution method.” | 摘要 p1 |
| “AGENT GYM offers convenient APIs through HTTP services, standardizing task specifications, environment settings, and the observation/action spaces for agents.” | §1 p2 |
| “we have implemented a unified interface for multi-round interactions and real-time feedback across different environments to support online evaluation, trajectory sampling, and interactive training.” | §1 p2 |
| 环境形式化 POMDP `(U,S,A,O,T,r)_e`；轨迹 `τ=(h_1,a_1,o_1,…,h_T,a_T)∼π_θ(τ|e,u)`，奖励 `r(e,u,τ)∈[0,1]` | §2 Eq.1–2 p3–4 |
| Table 1 对比：AgentBench 8 环境/Eval/No Traj/No Evol；**AgentGym 14 环境/Eval & Train/Traj/Multi-Env Evol** | Table 1 p4 |
| Table 2 统计：14 环境、89 任务、20509 指令、1160 评测、6130 AgentTraj、14485 AgentTraj-L | Table 2 p4 |
| “AGENT GYM deploys separate services for each environment … The clients can communicate with environments using HTTP protocol. At the core of this architecture is the controller.” | §3 p4 |
| “the agent generates the thought h_{t+1} … first and the subsequent action a_{t+1}”（ReAct 文本控制环） | §2 p4 |
| AGENT EVOL 学习步：`θ_{m+1}:=arg max_θ E[r(e,u,τ) log π_θ(τ|e,u)]`（奖励加权 NLL） | §4.2 Eq.8 p7 |
| 主结果：WS 66.5→73.5→**76.5**；ALF 77.5→83→**88**；Baby 69.3→74.19→**82.7**；TC 44→60→**64** | Table 3 p8 |
| “merging with the initial data provides more stable improvements … we choose M = 4” | §5.3 p8 |
| “performance increases with higher K, but the improvement is not significant. So we select K = 1” | §5.3 p9；Table 4 p9 |
| 接口端点：`/createEnv`、`/observation`、`/available_actions`、`/step`、`/reset`；“developers can easily develop new environments and add them to AGENT GYM by encapsulating the aforementioned interfaces.” | Appendix D p19 |
| “the complete evolution process based on Llama-2-Chat-7B (four iterations) takes approximately twenty hours” | Appendix E p20 |
| 自陈局限：“we do not perform multiple samplings in each iteration”；仅在三个模型验证（Llama2-Chat-7B/13B、DeepSeek-Coder-1.3B） | Appendix A p16 |
