# 论文分析卡片 · RecordReplay（AgentRR）

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-05-23 Get Experience from Practice LLM Agents with Record & Replay.pdf` |
| 标题 | **Get Experience from Practice: LLM Agents with Record & Replay（AgentRR）** |
| 作者 / 机构 | Erhu Feng、Wenbo Zhou、Zibin Liu、Le Chen、Yunpeng Dong、Cheng Zhang、Yisheng Zhao、Dong Du、Zhichao Hua、Yubin Xia、Haibo Chen；上海交通大学 IPADS |
| 发表时间 / 出处 | arXiv:2505.17716v1，2025-05-23（v1 标注 May 26, 2025；Preprint, cs.LG） |
| 论文链接 | arXiv:2505.17716 |
| 代码链接 | 未提及（正文无代码仓库；仅引用 Chrome Recorder / Playwright Codegen 作为录制工具） |
| 标签 | 录制-重放(Record & Replay) · 多层经验抽象 · check function(TCB) · 经验商店 · bounded intelligence · 有界可靠性 |
| **应用裁决** | **B 零件采用**（多层经验 + check function 直接回答「技能该长什么样」；评分/排序部分须按 C9 剥离） |
| 优先级 | **P2** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

> 定位说明：本篇是**立场/愿景论文（position paper）**，不是完整实验论文——全文无定量实验，仅 §5 一个定性案例（在线表单填写）。因此「可搬运」的是**概念、表示与协议**，不是可复现的算法实现。若只取分类学而不取 schema，等级应降为 C。

---

## 1. 一句话定位

- **论文主张**：把系统领域成熟的**录制-重放（Record & Replay, R&R）**引入 LLM 智能体，形成三阶段流水线 **Record（录轨迹）→ Summary（抽象成多层经验）→ Replay（按经验引导执行）**；用**多层经验**（低层=精确动作序列、高层=泛化过程知识）在「可靠性↔泛化」之间取舍，用 **check function** 作为可信计算基（TCB）划出安全边界，从而同时降低 LLM 调用成本、提升可靠性与执行性能（p1、p3–4）。
- **对 SSEA 的意义**：它把「重放」与「技能」的边界讲得最清楚——**低层经验 = 带变量与约束的参数化动作序列（非逐帧照做）**，**高层经验 = 需模型落地的抽象策略**。这正好是 SSEA 技能定义（action_sequence / option 的 policy）缺的那层「粒度选择」，直接指向实验 3（技能固化 **0/33**）的根因判断；其 check function 四类恰是 SSEA「四级验证门 + 前置条件=合法性键」的对照物。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p2）：LLM 智能体走向自主后，决策不透明、不可预测，妨碍规模化落地；归纳为四挑战——**可靠性**（幻觉）、**隐私**（云端处理敏感数据）、**成本**（Manus 单复杂任务约 $2 API 费）、**性能**（比人慢）。
- **它指出的既有方案缺陷**：
  - 模型对齐（RLHF 等）只能减少显式错误，**无法消除幻觉**（p2、p6）；
  - 工作流约束 / 提示工程 / 多智能体互检：要么牺牲泛化，要么**每步仍依赖昂贵模型调用**（p6–7）；
  - 传统 R&R 工具（Playwright 等）可靠且快，但**逐帧照做、零泛化**，环境一变即失败（p8、Table 2）；
  - 既有「经验抽象」工作（如 MobileGPT、UFO2）**只关注成功率**，未回答经验如何同时提升**执行效率与可靠性**（p10）。

### 2.2 核心思想（关键 insight）
1. **有界智能（bounded intelligence）**：把智能体智能**约束在已被验证成功的安全经验之内**——用经验护栏把「模型泛化」与「确定性执行」解耦，既不放弃泛化，又阻止进入不可恢复的错误态（p3、Fig.1）。
2. **多层经验消解「可靠性↔泛化」张力**：低层经验精确但泛化弱（要求 UI 布局不变），高层经验泛化强但需模型落地；**执行时动态选层**——环境高度相似→选低层（快、稳），环境变化→选高层（活、需强模型）（p3、p10、Fig.2）。
3. **经验必须配 check function**：经验不是具体轨迹，需本地模型翻译成动作，故必须由 check function（TCB）验证**执行流完整性 / 状态前置条件 / 数据参数约束 / 安全不变量**，把泛化边界显式化（p4、p11）。
4. **智能与执行解耦**：谁录制、谁重放可以自由组合（Table 1），从而「大模型录、小模型放」「不可信模型录、可信环境放」等，把探索与可信执行分离（p5–6）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **三阶段流水线** Record→Summary→Replay | 用户/智能体交互 → 动作轨迹 → 多层经验 → 受控执行 | 整体骨架 | §3.2、§4、Fig.3 p4、12–14 |
| **多层经验（multi-level experience）** | 一条或多条相似轨迹 → 低层（精确动作序列）+ 高层（泛化计划） | 在可靠性/泛化间取舍，执行时选层 | §3.2.1、Fig.2 p10 |
| **低层经验参数化** | trace 日志 → 识别**变量 + 描述 + 约束**，可脚本/API 直接执行 | 泛化的关键：不是逐帧照做，而是**变量化** | §5 p16 |
| **check function（4 类）** | 经验 + 执行动作 → 合法/非法（二值） | TCB 安全边界，划泛化边界 | §3.2.2 p11 |
| ├ 执行流完整性 | 动作序列 → 是否进入未定义状态 | 阻止越权（如未确认即支付） | p11 |
| ├ 状态前置条件 | 当前状态 → 前置字段是否满足 | 依赖顺序约束（表单字段） | p11 |
| ├ 数据/参数约束 | 运行参数 → 是否与任务/经验约束一致 | 变体不得越界 | p11 |
| └ 安全不变量 | 循环/变量部分 → 是否破坏安全 | 变体不损安全 | p11 |
| **状态转移图形式化** S/A/→/轨迹 | 环境状态 + 动作 → 合法轨迹集合 | 把「经验」形式化为轨迹子集，缩小搜索空间 | §3.4 p12 |
| **元操作集**（meta-operations） | click(obj)/type(field,text)/call_api(endpoint,params) | 限制状态转移复杂度 | §3.4 p12、§4.1 p13 |
| **Summary 共性/差异分离** | 多条相似轨迹 → 共性入经验、差异留给 Replay | 一次总结覆盖一类任务 | §4.2 p13–14 |
| **Replay 选层 + 自优化** | 当前任务/环境 → 选「仍保持最高成功率的最低层经验」；持续抽象出更低层经验 | 常用任务越用越快 | §4.3 p14 |
| **Experience Store** | 经验 + 元数据 → 可检索/上传/下载/评分/审计 | 经验复用与共享生态 | §3.3 p11–12 |
| **录制角色矩阵**（Table 1，8 种组合） | (录制者, 重放者) → 用例 | 解耦智能与执行 | Table 1 p6 |

### 2.4 关键表示与数据结构
- **状态转移图**：状态 S（环境快照：当前应用/窗口、UI 元素内容、文件系统，或抽象态如 "Logged In"）；动作 A（边）；转移 S —A→ S′；**轨迹** S0—A1→S1—A2→…→Sn 为一次完整执行（p12）。
- **经验 = 相似任务轨迹的总结集合**，即状态转移图中的一个**小轨迹集**，用以缩小模型动作选择搜索空间（p12）。
- **多层**：多个低层状态可聚合成一个高层状态；高层经验由**合并多个低层经验的状态**得到（p12、§4.2 p14）。
- **录制格式**：每步记录环境状态 + 动作；GUI 页布局粗录、交互元素细录；动作经元操作集规范化（JSON，例见 Fig.3：`action_type:CLICK`、`target_element.resource_id` 等）（§4.1 p13）。
- **Experience Store**：以 JSON 或图数据库存储，附元数据（task description / creator / version / ratings / audit status / usage statistics）（§3.3 p11–12）。
- **check function**：可为精确校验代码（如禁止点击安全敏感元素），或「自然语言描述 + 校验模型」；**必须显著小于智能体模型**以缩小 TCB（§4.2 p14）。

### 2.5 实验证据
> 本篇为立场论文，**无定量实验**；§5 仅一个定性案例。

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 在线表单填写（Fig.4 案例） | OpenAI CUA、Chrome Recorder | CUA **约 3 分钟**仍未完成；Chrome Recorder 每次需**人工填参**、无泛化；AgentRR 由用户 NL 描述任务、LLM 依经验自动填表 | 单例、定性、**无 n、无 seed、无均值**（§5 p14–16） |
| 三范式对比（Table 2） | Pure LLM Agent / Traditional R&R | AgentRR：效率 High（超人类）、准确 High、泛化 High（重复任务）；纯 LLM 效率/准确 Low；传统 R&R 泛化 Low | **定性评级表，非测量**（Table 2 p9） |
| 录制↔重放组合（Table 1） | — | 8 种 (Recorder, Replayer) 组合及其用例（含「同模型录放=确定性执行与技能固化」） | 概念矩阵，**无实验**（Table 1 p6） |

### 2.6 论文自陈局限与边界条件
- **假设依赖**：任务**边界清晰、执行流跨请求相似**（重复性任务，如填表、订酒店、网购）；原型刻意采取**保守泛化**（§6 p17）。
- **明确不适用 / 未解**：
  - **Summary 复杂度**：多层经验的**层级定义仍不清晰**，存在总结不完整、生成可执行脚本失败（p16）；
  - **状态空间**：状态定义随任务而异（UI vs CLI/API）（p16–17）；
  - **泛化↔安全**张力未根治：过度泛化会破坏由具体人类轨迹导出的安全保证（p17）；
  - **录制保真**：动态 HTML、弹窗、分辨率差异使 **100% 可靠重放不可达**（p17）；
  - **用户负担**：录制需人工投入，经验商店的共享经验还需审计/评分机制（p17）。
- 全文**无算力预算数字、无失败率统计、无消融**；不涉及生存、无进化/继承。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 目标是 GUI/web 任务的可靠性/隐私/成本/性能，**无生存原则**；边界是「任务成功」而非「存活」（p2、§6 p17） | 把「任务安全边界」替换为「生存约束边界」；check function 的 4 类换成生存不变量（能量/危险/死亡态） |
| **C2** 自然语言只作观察员接口 | **◐** | 低层经验运行时为 API/脚本（非语言）；但**高层经验是自然语言计划**，Replay 时由本地模型现场落地 → 语言进入控制闭环（p10、p16） | 快环只允许**低层参数化动作序列**（非语言）；NL 仅限离线 Summary/解释面 |
| **C3** 权重/记忆/技能三分离 | **◐** | 不微调，经验独立于权重（✓）；但**记忆与技能被合并进同一个「experience」存储**，未分置（§3.3 p11–12） | 拆分经验：低层动作序列→ΔS（技能）；高层计划/上下文→ΔM（记忆） |
| **C4** 低算力低带宽 | **✓/◐** | 核心动机即**大幅减少 LLM 调用**、支持边缘设备本地重放（p4–5、p7）；但经验商店的评分/审计/合并是持续维护开销 | 去掉评分/审计开销；只保留结构性匹配；慢环预算仍待 SSEA 自定 |
| **C5** 精准回忆历史 | **◐** | 逐帧记录状态+动作、重放验证可复现性（§4.1 p13、§5 p16）；但经验是**抽象**而非精确情节，选择靠 task similarity/ratings/success rate 而非精准检索 | 检索键改为结构化状态匹配；低层经验保留精确轨迹以支撑精准召回 |
| **C6** 可自主修改自身 | **◐** | Replay 期自优化：持续抽象出更低层经验、合并他人经验（§4.3 p14）；但改的是**经验库**，非代码/参数；**无四权（提案/边界/验证/应用）框架** | 把经验库更新纳入 Δ 提案→四级验证门管线；补回滚 |
| **C7** 可保存/恢复/变异/继承 | **◐** | Experience Store 支持上传/下载/版本/合并（=保存/共享/变异）（§3.3 p11–12）；**无跨个体遗传、无淘汰** | 经验作 L3 个体资产；可继承者仅限「多层经验 schema + check function 类型」等结构先验 |
| **C8** 给基因先验，不给知识语料 | **✗** | 经验商店的核心卖点是**跨用户/设备/应用共享经验**，即把后天知识跨个体搬运（p5、§3.3） | 严禁经验进 GenePackage；跨代只传结构先验，后天经验留个体（L3） |
| **C9** 不设评分函数，只有淘汰函数 | **✗** | Experience Store 明确支持**rate 质量与可靠性**、按 **success rate** 检索、用 **ranking mechanism 选最优经验**（§3.3 p11–12、§4.3 p14） | 删除 rating/success-rate/ranking；选择仅用**结构合法性（check function 通过=不淘汰）** + 任务结构匹配；check function 本身是二值合法性门，**保留** |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子；创新在多层经验的信息流（L2）与经验库更新（L3） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无；LLM 为现成件 | 符合借用立场 |
| **L2 信息流层** | **多层经验 + check function 边界 + 状态转移图**；Record/Summary/Replay 数据流 | **高**：直接对应「技能表示 + 门」的信息流设计 |
| **L3 学习层** | Summary 泛化 + Replay 自优化（抽象出更低层经验、合并经验） | 中：技能固化/泛化的粒度机制 |
| **L4 演化层** | Experience Store 共享（无选择/淘汰/继承） | 低/—：只有「共享」，无达尔文闭环 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 多层经验（低层/高层） | `skill_library.py` **技能规格升级**：技能须显式标注粒度——低层=参数化 action_sequence，高层=抽象 policy（需模型落地）。**这是实验 3 的核心答案** |
| 低层经验「变量+描述+约束」参数化 | 技能参数化机制：技能不是定长动作串，而是**带变量与约束的动作模板** |
| check function 四类 | **Gate / 四级验证门**：执行流完整性→格式门；状态前置条件→合法性键；参数约束→沙盒门；安全不变量→回归门 |
| 状态转移图（S/A/轨迹） | 技能执行轨迹表示 + **技能成功判据**：轨迹合法性（直接回应债务 25/26/27/28「判据形状错」） |
| Record 阶段 | 快环日志 / 经验采集（对应「精准回忆历史」采集侧） |
| Summary 阶段 | 慢环 `ExperienceCompiler`（泛化/抽象） |
| Replay 阶段 | 快环技能执行 + 选层（对应 option 的 policy 落地） |
| Experience Store（去评分后） | 记忆/技能库的元数据 schema（version/audit/usage） |
| Bounded intelligence | 生存边界设计哲学（替换为生存不变量） |
| Table 1 录制/重放角色矩阵 | Gene Manager / 慢环角色设计（谁提案、谁验证） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **实验 3 技能固化 0/33**：本篇给出「技能该长什么样」的判决——**技能应是带变量的参数化动作序列（低层）+ 抽象策略（高层），而非逐帧定长动作串**。0/33 的形状问题很可能源于技能表示**过于具体、无参数化 → 无法泛化 → 无法固化**。
  - **债务 25/26/27/28 判据形状错**：用「轨迹合法性 + check function 二值通过」替代错误的布尔成功判据。
  - **`retrieve` 键收窄**：低层经验保留精确状态（S 快照），可拓宽结构化检索键。
- **不能回应**：
  - **债务 22 记忆二级门常量阈值**：check function 是**静态边界**，非慢环可调阈值，不解决。
  - **睡眠期计算预算未定义**：全文**无算力预算数字**，无法回答 C4 预算缺口。
- **可服务的验收实验**：实验 3（技能固化，重设计）；实验 2（经验/记忆复用，选层机制）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 多层经验分类（低层参数化动作序列 / 高层抽象策略） | 表示 | 改造移植 | skill_library | **技能表示（实验 3，0/33）** | 高 |
| 2 | 低层经验「变量识别 + 描述 + 约束」参数化 | 算法/思想 | 改造移植 | skill 参数化 | 技能泛化、可重放 | 高 |
| 3 | check function 四类（流完整性/前置/参数/不变量） | 协议 | 改造移植 | Gate / 验证门 | 判据形状（债务 25/26/27/28） | 高 |
| 4 | 状态转移图形式化（S/A/轨迹） | 表示 | 改造移植 | 技能执行轨迹 | 技能成功判据 | 高 |
| 5 | Record→Summary→Replay 三段流水线 | 工程/协议 | 改造移植 | 快环日志 + 慢环 ExperienceCompiler | 经验采集-抽象-应用闭环 | 中 |
| 6 | Experience Store 元数据 schema（version/audit/usage） | 表示 | 改造移植（**去评分**） | memory/skill 库 | 库治理与版本 | 中 |
| 7 | Table 1 录制/重放角色矩阵 | 思想 | 仅作对照 | Gene Manager / 慢环角色 | 解耦提案与验证 | 中 |
| 8 | bounded intelligence 设计哲学 | 思想 | 仅借思想 | 生存边界设计 | 有界可靠性 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C9（最重）**：Experience Store 的 **rating / success rate / ranking** 是典型**外部评分函数**——必须整体删除；选择只保留「check function 二值合法性 + 任务结构匹配」。**check function 是淘汰式合法性门，保留**（与 PSN 的成败式回滚同性质）。
  - **C8**：跨用户经验共享 = 后天知识跨个体搬运，违反「不给知识语料」——经验须留在个体 L3，禁入 GenePackage。
  - **C2**：高层经验需模型在 Replay 现场落地 → 语言进入控制闭环；SSEA 只应搬**低层非语言参数化动作序列**。
  - **C3**：记忆与技能被合并为单一「experience」存储，须按三分离拆开。
  - **C1**：无生存原则，任务成功 ≠ 存活。
- **隐含假设与失效条件**：假设任务**重复且执行流相似**；一旦任务开放/长程，低层经验失效、高层经验退化回普通 LLM 智能体，收益消失。
- **算力 / 带宽 / 工程代价**：**无预算数字**；但录制保真（动态 HTML/分辨率）、Summary 生成可执行脚本失败、经验商店审计，都是实际工程成本。
- **搬运后的可能退化模式**：若把 SSEA 技能写成**逐帧定长动作串**（照抄低层经验而不参数化），环境轻微扰动即重放失败——很可能就是实验 3「0/33」的失败形态；若照抄 rating/ranking，则直接违反 C9 并引入误演化攻击面（参 Misevolve）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **概念同构·须区分** | **Dream-RSI** | Dream-RSI 重放的是**发现树（历史探索决策+结果）**，用于**慢环离线 off-policy 评估**（做梦）；本篇重放的是**成功轨迹→经验**，用于**快环在线执行引导**。**同构点**：都把「历史」变成可重放的模拟器/模板；**边界**：Dream-RSI=验证场，本篇=执行向导。二者互补而非替代 |
| **概念同构·须区分** | **PSN** | PSN 技能=带**契约（前置/后置/子技能）**的可执行程序；本篇低层经验=**参数化 API/脚本 + check function**。**check function ≈ PSN 契约前置条件**。差异：PSN 用 REFLECT **持续演化网络**，本篇只做**一次性 Summary**（无修复/重构）→ PSN 是技能维护侧主干，本篇是技能**来源/表示**侧 |
| **前身 / 上位** | **Voyager** | Voyager 的 key/value 技能库是本篇 Experience Store 的前身；本篇增加了**多层粒度 + 元数据 + 共享** |
| 互补（跨域复用） | **Agent KB** | Agent KB 跨域经验检索复用 ≈ Experience Store 的跨用户共享版（用检索替代 rating）；二者都需**去评分化**才合 C9 |
| 互补（触发条件） | **ExpSeek** | ExpSeek 回答「**何时**该去寻求经验」（自触发）；本篇默认「总是重放经验」，**缺重放触发条件**——ExpSeek 正好补这一环 |
| 互补（经验来源） | **Scaling Agent Learning via Experience Synthesis** | 该文**合成**经验，本篇**录制**经验；合成可补本篇「录制需人工、用户负担重」的短板 |
| 互补（失败经验） | **FLEX** | FLEX 有 golden/warning 两层经验库 + updater 三分支；本篇只录**成功**经验（≈golden），**缺 warning 侧**——FLEX 补齐失败经验与写入分支 |
| 互补（检索） | **Memento** | Memento 的 μ 可学习检索 = Experience Store 检索机制的升级（替代 rating 排序） |
| 互补（准入） | **SEDM** | SEDM 的 SCEC 自包含打包 + A/B 准入 = Experience Store「审计/准入」的可搬实现 |
| 互补（技能族） | ReasoningBank / EvolveR / AutoSkill / OpenSkill / SkillRL | 「经验→技能」族同伴；本篇提供「成功轨迹→多层经验」的来源侧 |
| 替代 | 纯 Playwright 式逐帧 R&R、纯 prompt 记忆 | 参数化低层经验替代逐帧照做；多层经验替代平铺轨迹 |
| 风险参照 | **Misevolve** | Experience Store 的 rating/audit/共享是新的误演化攻击面 |

### 6.2 推荐组合方案
1. **成功轨迹→多层技能（本篇 × PSN × FLEX）**
   - 形态：本篇录制成功轨迹并总结出**参数化低层动作序列 + 抽象高层计划**；PSN 给其加**契约与网络化维护**（REFLECT/成熟度/回滚）；FLEX 补 warning 层失败经验。
   - 新增能力：技能既有**来源（录制）**又有**结构（契约）**又有**负例（warning）**。
   - 纪律：删除 Experience Store 的 rating/ranking；选择只用合法性门。
2. **离线验证重放（本篇 × Dream-RSI）**
   - 形态：本篇的 check function 与候选技能，先在 Dream-RSI 的重放模拟器里做**合法性淘汰**，通过后再进真实环境。
   - 新增能力：自修改验证从「真实环境试错」变「离线廉价淘汰」。
3. **重放触发条件（本篇 × ExpSeek）**：ExpSeek 决定「何时检索/重放经验」，补本篇缺失的触发环。

### 6.3 本篇在组合中的典型角色
- **技能表示的「粒度裁判」+ 经验来源侧**：回答「技能该长什么样」（多层、参数化、带 check function 边界），并给出「成功轨迹→经验」的总结流水线；不做技能演化维护（那是 PSN 的角色）。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 直接命中「技能表示 + 重放」两命题；但域为 GUI/web，非生存（实测于原文） |
| 立场兼容性 | **2** | C9 ✗（rating/ranking/success-rate）、C8 ✗（跨用户共享）、C2/C3 ◐、C1 ✗——冲突多，须大幅改造（实测+推断） |
| 可搬运性 | **4** | 机制语言无关、概念清晰、schema 可直接写；**无代码**（推断） |
| 证据强度 | **2** | **立场论文，无定量实验**，仅一个定性案例（CUA 约 3 分钟）；Table 2 为定性评级（实测） |
| 组合价值 | **4** | 与 Dream-RSI/PSN/Voyager/Agent KB/ExpSeek/FLEX 直接互补，是技能表示的关键拼图（推断） |
| 落地成本 | **4** | 搬运的是概念与 schema，实现成本低；但多层经验的层级定义仍需 SSEA 自定（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：多层经验分类、低层参数化、check function 四类、状态转移图形式化四件套**可直接写入 SSEA 技能规格**，正面回答「技能该长什么样」（实验 3）；但其**评分/排序/共享机制违反 C9/C8，必须整体剥离**，且**无定量证据**，故不达 A。若只取分类学不取 schema，则降为 C。
- **优先级：P2**（技能表示修正可随实验 3 重设计一起做，非最紧）。
- **建议动作**：
  1. 在 SkillLibrary 技能规格中引入**双粒度标注**：低层=带变量/约束的 action_sequence（非语言、可重放），高层=抽象 policy（仅慢环/需模型落地）；
  2. 实现**低层经验参数化**（变量识别 + 约束绑定），这是实验 3 的核心修复点；
  3. 把 check function 四类映射到四级验证门，并用「**轨迹合法性**」作技能成功判据，替换错误的布尔判据（债务 25/26/27/28）；
  4. Experience Store 仅保留**元数据 schema（version/audit/usage）**，删除 rating/ranking/success-rate；选择交合法性门 + 结构匹配。
- **最小验证实验（技能表示双臂）**：
  - **双臂/消融**：同一技能固化流，A 臂=**逐帧定长动作序列**（照抄本篇低层经验但不参数化）vs B 臂=**参数化动作序列 + 约束（check function）**；≥8 seed。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：① 机制计数——参数化变量数、约束数、重放成功次数（先报分母）；② 行为差——同一技能在**扰动环境**（UI 位移/字段顺序变）下的动作序列差异；③ 淘汰结果——环境实测存活/任务完成（模型外）。
  - **预期与证伪**：预期 B 臂在扰动环境下重放成功率**显著高于** A 臂；**若 B 臂仍为 0/33**，则证明「技能表示」不是 0/33 的根因（问题在 Gate 判据形状或重放触发条件），须转向其他假设。
- 若 **E 不采用**：不适用（保留其表示与边界思想）。

---

## 9. 待确认问题

1. **重放 vs 技能的边界（最紧）**：SSEA 技能应是「低层参数化动作序列」还是「高层抽象 policy」？抑或**双粒度并存**（技能带 level 字段，运行时选层）？本篇主张多层，但**层级定义论文自陈不清晰**——SSEA 需自定切分标准（按状态抽象度？按参数化程度？）。
2. **重放触发条件**：本篇默认「总是重放」，未定义**何时该重放、何时该从零规划**；SSEA 需自定（可参 ExpSeek）。
3. **check function 与四级验证门**：四类 check function 是否 1:1 映射到格式/沙盒/回归/环境实测？生存域的安全不变量如何表达（非语言状态张量）？
4. **去评分化后的选择**：删掉 rating/success-rate/ranking 后，多个同层经验如何选？仅靠「结构合法性 + 任务结构匹配」是否足够？
5. **经验与三分离**：低层经验（技能）与高层经验（记忆/计划）如何按 C3 拆到 ΔS/ΔM？拆后 check function 归属哪一侧？
6. **睡眠期预算**：本篇无任何算力数字，SSEA 睡眠期预算仍须另行定义。
7. 需补查：**Agent KB、ExpSeek、Scaling Agent Learning via Experience Synthesis** 三篇尚无卡片，其与本篇的互补关系需读原文确认。

---

## 附：关键摘录与出处

| 摘录（原句 / 图表要点） | 页码 |
|---|---|
| “The core idea is to: ① record an agent's interaction trace… ② summarize this trace into a structured 'experience'… ③ replay these experiences in subsequent similar tasks” | p1（Abstract） |
| “Low-level experiences capture precise, concrete action sequences… high-level experiences provide more generalized procedural knowledge, allowing the agent to adapt… by leveraging the LLM's reasoning ability to instantiate concrete actions from abstract plans.” | p4（§1）、p10（§3.2.1） |
| “the record phase… the aim is not bit-perfect replay. Instead, the summary phase introduces generalization, creating an abstract 'Experience' that represents a class of safe executions.” | p8（§2.3） |
| check function 四类：“Execution Flow Integrity / State Preconditions / Data/Parameter Constraints / Safety Invariants” | p11（§3.2.2） |
| “To achieve generalization capabilities, low-Level experience identifies variables within traces, along with their descriptions and associated constraints (e.g., check function).” | p16（§5） |
| 状态转移图：“nodes correspond to environment states, and edges correspond to actions… Experience is defined as a summarized collection of trajectories from similar tasks, effectively representing a small set of trajectories.” | p12（§3.4） |
| Experience Store：“rate the quality and reliability of Experiences… select the most appropriate Experience… based on criteria like task similarity, user ratings, success rate, etc.”（**C9 冲突来源**） | p11–12（§3.3） |
| Table 2：Pure LLM Agent（Low/Low/High）、Traditional R&R（High/High/Low）、AgentRR（High/High/High） | p9（Table 2） |
| 案例：CUA “approximately three minutes… while still falling short”；Chrome Recorder “lack generalization capabilities, requiring manual parameter input” | p14–16（§5） |
| 局限自陈：“there is still a lack of clear definitions for different levels of experiences”“achieving 100% reliable replay remains elusive”“over-generalization can compromise the safety guarantees” | p16–17（§6） |
| “AgentRR is guided by the design philosophy of bounded intelligence: constraining agent intelligence within safe, successful experiences.” | p3（§1） |
