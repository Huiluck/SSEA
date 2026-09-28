# 论文分析卡片 · ALFWorld

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2020-10-08 ALFWorld Aligning Text and Embodied Environments for Interactive Learning.pdf` |
| 标题 | **ALFWorld: Aligning Text and Embodied Environments for Interactive Learning** |
| 作者 / 机构 | Mohit Shridhar†、Xingdi Yuan♡、Marc-Alexandre Côté♡、Yonatan Bisk‡、Adam Trischler♡、Matthew Hausknecht♣；†University of Washington、♡Microsoft Research Montréal、‡Carnegie Mellon University、♣Microsoft Research |
| 发表时间 / 出处 | ICLR 2021（arXiv:2010.03768v2 [cs.CL]，2021-03-14）；21 页（正文 9 页 + 附录 A–K） |
| 论文链接 | arXiv:2010.03768；项目页 ALFWorld.github.io |
| 代码链接 | 项目页 ALFWorld.github.io（正文未给 GitHub 仓库名；代码/数据发布状态未在正文明确） |
| 标签 | 文本化具身环境 · TextWorld · ALFRED · THOR · PDDL 规划域 · 上下文敏感文法观测 · 高层文本动作 vs 低层物理动作 · BUTLER 智能体 · 模仿学习 DAgger · 跨模态零样本迁移 |
| **应用裁决** | **D 基准对照**（兼 B：判据形状 + 动作通道消费者设计可搬；其语言入环架构不搬） |
| 优先级 | **P1**（是 MemRL/SkillRL/RAGEN/Memento/Agent0 五卡的评测环境，且直接指向债务 27 的第四扫描面） |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把 ALFRED（THOR 仿真中的视觉具身家务任务）与 TextWorld（程序化文本游戏引擎）**对齐**为同一底层世界的两种视图——用 PDDL 描述场景、TextWorld 生成等价文本游戏（高层文本动作），THOR 渲染等价视觉场景（低层物理动作）——从而让智能体先在**抽象文本环境**里用 DAgger 学会高层策略，再**零样本迁移**到具身环境执行；作者给出 BUTLER 三件套（Brain/Vision/Body）证明「先文本后具身」不仅 7× 快，且泛化更好（Table 2–3，p5–7）。
- **对 SSEA 的意义**：它是 SSEA **环境侧**最干净的一份对照参照——①「任务成功」由**环境侧确定性判据**（PDDL 目标谓词是否满足、Fast Downward 规划器维护状态）判定，天然落在 C9 第一层「淘汰函数归环境」；②它的**动作空间是封闭的**：每个高层文本动作都在 PDDL 域里有对应的产生式规则消费者（Table 6，p18），这正是 SSEA 债务 27「`skill` 通道无消费者却被报成功」的**反面标本**；③它是 MemRL/SkillRL/RAGEN/Memento/Agent0 这五张卡所缺的**评测场**（确定成功判据 + seen/unseen 泛化协议）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1）：人类仅凭一句抽象请求（*Put a washed apple in the kitchen fridge*）就能在纯抽象层面推演动作序列、评估成功率/原型性/效率，**不动一根肌肉**；看到真实厨房后再更新抽象计划。具身智能体需要同样的能力，但既有基础设施**不能同时支持「抽象推理」与「具体执行」**。
- **它指出的既有方案缺陷**（p2）：
  1. **指令跟随类工作**（MacMahon 2006；Anderson 2018a）用**静态跨模态专家演示语料**——只有演示，没有可交互的语言反馈；
  2. **机器人控制类工作**用 MuJoCo 等仿真器提供无限交互数据，但**没有任何机制**（除非请人 7×24 值守）为具身智能体提供**语言反馈与标注**；
  3. 纯视觉状态的智能体（如 Zhu 2017）因状态表示受视觉所限，**只能泛化到很小一撮任务**（p9 Related Work）。

### 2.2 核心思想（关键 insight）
1. **两个视图共享一个潜在结构**（p3）：ALFWorld 用 **PDDL** 描述每个 ALFRED 场景，并据此用 TextWorld 引擎构造等价文本游戏；对象与交互在两种模态间**一一对应**，因此可在任一模态训练、在任一模态评测（*train in either the language or embodied world*）。
2. **先在抽象语言空间学策略，再迁移到具身执行**（p2）：语言环境让智能体**不必处理物理约束导致的执行失败/专家失败**，从而更快学到任务引导的启发式（如「翻遍厨房所有抽屉找刀」），且这些启发式**更能泛化到具身世界**。
3. **高层文本动作 = 可分解为若干低层物理动作的抽象**（p3）：`goto/take/put/open/close/toggle/clean/heat/cool` 是高层动作；`heat/cool/clean/goto` 各自对应多个低层具身动作（由 BUTLER::BODY 的 A*/API 展开）。
4. **交互式语言 vs 静态语料的区别是泛化来源**（§4.1，p5）：DAgger 在线交互使智能体能**从错误中恢复**，而 Seq2Seq 仅从等量演示做行为克隆，泛化明显更差。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **PDDL 潜在状态** | ALFRED 场景 → 谓词集合（`at/in/closed/openable`…），线性逻辑乘法合取 ⊗ | 两模态共享的符号状态；状态可被动作产生式规则改写 | §C p16 |
| **TextWorld 引擎（planner）** | PDDL 域 + 当前状态 → Fast Downward 经典规划器维护/更新状态 | 确定性状态转移与目标可满足性检查 | §C p16 |
| **TextWorld 引擎（text generator）** | 当前状态 + 上一动作 → 上下文敏感文法采样模板 → 文本观测 | 观测文本化（观测模板 Table 6，p18） | §C p16–18 |
| **高层文本动作集**（9 类） | `goto{take,put,open,close,toggle,clean,heat,cool}` + `examine/inventory` | 文本侧动作空间；每类有对应观测模板 | p3、Table 6 p18 |
| **低层物理动作集** | `MoveAhead/RotateLeft,Right/LookUp,Down/Pickup/Put/Open/Close/ToggleOn,Off` | 具身侧动作空间（THOR 渲染+物理） | p2 |
| **BUTLER::BRAIN** | `o0, ot, g` → 动作句 `at`（token-by-token） | 文本策略；Transformer Seq2Seq + pointer softmax + BERT 嵌入 + GRU 聚合器 + 观测队列 | §3.1 p4、§A p14–15 |
| **观测队列 + 循环聚合器** | 最近 k 个不重复观测 + 固定保留 `o0` → 历史感知表示 | 部分可观测下的历史；k 消融见 Fig.4 | §3.1 p4、§A.1 p14 |
| **BUTLER::VISION** | 视觉帧 `vt` → 文本描述 `ot`（Mask R-CNN 检测 + 模板） | 状态估计（captioning）；73 类对象 | §3.2 p4–5、§D p17 |
| **BUTLER::BODY** | 高层动作 `at` → 低层动作序列 `{â1..âL}`（A* + ALFRED API） | 控制器；A* 走预建栅格图 | §3.3 p5 |
| **目标谓词成功判据** | 终态 → 目标条件是否满足（"You won!"） | 环境侧确定性成功判定 | §K p21 示例 |
| **Goal-condition success** | 部分完成度（如 3 个目标条件满足 1 个 = 0.33） | 部分得分度量（来自 ALFRED） | §4.1 脚注 3 p5 |
| **seen/unseen 划分协议** | 训练实例（已知 {task-type, object, receptacle, room}）vs 新实例（必在未见房间） | 分布内/外泛化度量 | §2 p3 |
| **规则专家 + DAgger** | 任务 → 子目标序列 → 监督信号 | 模仿学习监督；专家比 ALFRED 的 PDDL 规划器更稳 | §E p17 |

### 2.4 关键表示与数据结构
- **状态**：谓词集合 + 线性逻辑乘法合取 ⊗，如
  `st = at(player, microwave) ⊗ in(mug, microwave) ⊗ closed(microwave) ⊗ openable(microwave)`（§C p16）；
  动作 = 产生式规则，如 `open microwave` 把 `closed(microwave)` 替换为 `open(microwave)`。
- **观测**：上下文敏感文法生成的文本模板（Table 6，p18）；失败/无状态变化一律回 `Nothing happens`（p5、p18）。
- **动作（文本侧）**：高层动作句；对象带实例 ID（如 `tomato 1`）。
- **动作（具身侧）**：低层原语；A* 输出位移序列。
- **任务规格**：模板化目标（Table 7，p19，每类 2 个模板等概率采样）或人类标注目标（含 66 个未见动词、189 个未见名词，§H.2 p19）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 / 出处 |
|---|---|---|---|
| 零样本域迁移（All Tasks） | TextWorld-only / Seq2Seq / BUTLER / BUTLER-ORACLE / Human Goals | 见 / 未见成功率：TW-only **40/35**；Seq2Seq **6 (15)/5 (14)**；BUTLER **19 (31)/10 (20)**；ORACLE **37 (46)/26 (37)**；Human Goals **8 (17)/3 (12)**（括号为 goal-condition 率） | 成功率 3 次评测均值；每类取 8 seed 中 TextWorld 最佳 checkpoint；Table 2 p6 |
| 训练策略（All Tasks，ORACLE，50K eps） | EMBODIED-ONLY / TW-ONLY / HYBRID | train/seen/unseen：21.6/33.6/23.1（0.9 eps/s）；23.1/27.1/**34.3**（**6.1 eps/s**）；11.9/21.4/23.1（0.7 eps/s） | 取各 split 峰值；TextWorld 快 **7×**；Table 3 p7 |
| TextWorld 内泛化 | BUTLER / BUTLER_g（无 beam search）/ Seq2Seq | All Tasks tn/sn/un：**16/40/37**；16/19/22；9/10/9 | 8 seed；Table 4 p8 |
| 单模态基线（All Tasks，50K eps，具身评测） | BUTLER / VISION-ResNet18 / VISION-MCNN-FPN / ACTION-ONLY | seen/unseen：**18.8/10.1**；10.0/6.0；11.4/4.5；**0.0/0.0** | 取各 split 峰值；Table 5 p8 |
| 模型消融（All Tasks，8 seed） | 观测队列长度 k、是否保留 `o0`、是否循环、训练游戏数 | 保留 `o0` 助未见任务生成容器词；循环组件助已知环境；训练游戏越多泛化越好 | Fig.4 p8–9 |
| RL 尝试失败 | token-by-token RL | 随机撞到语法正确且上下文合法动作的概率 **7.02e-44**（序列长 10） | §5.1 p7 |

### 2.6 论文自陈局限与边界条件
- **域隙（domain gap）**（§4.2，p6）：TextWorld 允许任意「小容器放大物体」，具身世界受物理尺寸约束（如大锅放不进微波炉）；即使 ORACLE 也观察到从 TextWorld 到具身的显著性能下降。
- **强先验假设**（§3.3，p5）：导航依赖**预建栅格图**（每个容器实例带交互视点 x,y,θ,φ）——作者自陈是「strong prior assumption」。
- **模板化观测**（§3.2，p5）：状态估计器是模板式，作者称「preliminary results」，未来可用图像/视频描述或场景图解析器替代。
- **RL 不成功**（§5.1，p7）：token 级动作空间太大，RL 无法取得有意义进展，最终改用 DAgger。
- **任务子集**（p3 脚注 2）：训练/评测**排除**切片类任务与便携容器（如碗）。
- **发布状态未提及**：正文未明确代码/数据发布；`ALFWorld.github.io` 为项目页。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 环境侧是**结构化控制世界**（PDDL 谓词状态 + 产生式规则，§C p16），但**接口是自然语言**，智能体 BUTLER 本身是 NLG 式文本生成器（§3.1 p4） | 只取 PDDL 潜在状态作 SSEA 结构化状态通道；文本仅作观察员/教师面 |
| **C2** 自然语言只作观察员接口，不进控制闭环 | **✗** | 全篇核心即「文本动作进入控制闭环」：观测是文本、动作是文本句（p2–4） | 改造：把 TextWorld 的**符号状态与产生式规则**当控制环通道，文本降级为日志/解释；这正是 SSEA 与 ALFWorld 的结构性分界 |
| **C3** 权重/记忆/技能三分离 | ◐ | BUTLER 是模块分解（Brain/Vision/Body，§3），非三分离；无独立记忆/技能库 | 可把观测队列视作「记忆雏形」，但需按 SSEA 三分离重建 |
| **C4** 低算力低带宽 | ◐/✓（环境侧） | TextWorld **CPU-only、7× 快**（6.1 vs 0.9 eps/s，Table 3 p7）；但具身侧渲染 100MB×batch GPU（p7 脚注 4），智能体侧 BERT+Transformer | 环境侧用文本视图服务 C4；具身视图仅作抽检 |
| **C5** 精准回忆历史 | ◐ | 环境**完全确定、可重放**（PDDL + 规划器）；但无外置可检索记忆，仅观测队列 k（§A.1） | 环境确定性利于 SSEA 记忆的精准落库与重放，可作 C5 验证场 |
| **C6** 可自主修改自身 | — | 不涉及（BUTLER 不改自身代码/权重结构） | — |
| **C7** 保存/恢复/变异/继承 | — | 不涉及（无基因包/继承机制） | — |
| **C8** 给基因先验，不给知识语料 | ◐/✓ | PDDL 域 = **结构性先验**（对象可供性 affordance、前置条件 precondition，p1），非知识语料；文法模板固定 | 可将 PDDL 域类比为 SSEA 的「结构性本能先验」，但注意它仍含对象语义先验 |
| **C9** 不设评分函数，只有淘汰函数 | **✓** | 成功由**环境侧确定性判据**判定（目标谓词满足 / "You won!"，§K p21；Fast Downward 维护状态，§C p16）；环境无奖励塑形、无 LLM 评委；goal-condition 率是环境计算的部分完成度，非学习评分器（§4.1 脚注 3 p5） | — （本篇对 C9 是正面标本；但 BUTLER 训练用规则专家+DAgger 属监督通道，须与 SSEA 的淘汰函数区分） |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 是环境/基础设施（L2 信息流 + 演化训练场），无新智能体算子；L1 用现成 Transformer/BERT/GRU | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子：Transformer Seq2Seq + pointer softmax + BERT 嵌入 + GRU（§A p14–15） | 符合「L1 借用可替换」立场 |
| **L2 信息流层** | **双模态对齐信息流**：PDDL 潜在状态 → {文本视图 / 具身视图}；观测队列 + 循环聚合器 | **高**——SSEA 环境侧「结构化状态通道」与「快环历史」的直接对照 |
| **L3 学习层** | DAgger 模仿学习 + beam search 失败恢复（§3.1、§5.1） | 中——「从错误中恢复」的机制可借思想 |
| **L4 演化层** | 环境作为训练/验证场；**seen/unseen 泛化协议**；环境规格可打包（PDDL 域 + 文法） | 中-高——服务 L4 的记忆/技能跨环境迁移验收 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| PDDL 潜在状态 + 产生式规则 | **环境侧结构化状态通道**（替代文本观测），服务 C1/C2 |
| 高层文本动作集（9 类） | **Action 六通道的消费者设计参照**：`goto`→locomotion，`take/put/open/close/toggle/clean/heat/cool`→manipulation；证明「每个通道都应有环境分支」 |
| 目标谓词成功判据 | **C9 淘汰函数形状**（环境侧确定性终态检查） |
| goal-condition success（部分完成度） | 分档判据参照（注意它是**观察员度量**，不可进控制环） |
| seen/unseen 划分 | L4 泛化验收协议（记忆/技能跨环境迁移） |
| 观测队列 + 循环聚合器 | 快环历史机制；与 SSEA 记忆二级门对照（k 消融 Fig.4） |
| 规则专家 + DAgger | 慢环技能提案/技能固化的**监督通道对照**；可作 SkillRunner 验收臂 |
| TextWorld 引擎（CPU-only、7× 快） | **廉价验证场**（C4）；可作技能/记忆固化实验的低成本判据场 |
| 单模态基线（VISION / ACTION-ONLY） | 消融设计模板（ACTION-ONLY=0.0 证明「背动作序列」不可行） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **债务 27（环境把无消费者通道报成功）**：ALFWorld 是**反面标本**——它的动作空间**封闭**，每个高层文本动作在 PDDL 域里有对应产生式规则消费者（Table 6 p18），且失败一律回 `Nothing happens`（p5）。SSEA 第四扫描面「Action 每个通道在环境侧都有消费者」可直接以「ALFWorld 式：无分支即不合法/回失败」为参照。
  - **债务 25/26/28（判据形状错 / 代理指标冒充目标）**：ALFWorld 的成功是**终态谓词检查**（不是「动作成功」这类代理指标），为 SSEA 修复「技能失效被判成成功」提供正确形状。
  - **债务 22（记忆二级门用常量阈值，慢环不可调）**：ALFWorld 无记忆门，但其观测队列长度 k 的消融（Fig.4 第一列）给出「历史量—性能」曲线，可作二级门阈值标定的外部参照。
  - **技能表示够不够（0/33 之后）**：ALFWorld 的**高层动作 = 子目标序列**（规则专家分解，§E p17）正是「技能即压缩行为先验」的现成标注。
- **可服务的验收实验**：
  - **实验 3（技能固化）**：可把 ALFWorld 文本视图作为**判据干净的复测场**——成功由环境终态判定，排除债务 27/28 的污染。
  - **L4 记忆/技能迁移**：seen/unseen 协议可直接复用于 GenePackage 的跨环境泛化验收。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | PDDL 潜在状态 + 产生式规则（结构化环境规格） | 表示/协议 | 改造移植 | 环境侧状态通道 | C1/C2 结构化控制环 | 高 |
| 2 | 高层文本动作集（9 类）+ 每动作对应观测模板 | 协议 | 改造移植 | Action 六通道消费者 | 债务 27 第四扫描面 | 高 |
| 3 | 目标谓词成功判据（环境侧确定性终态检查） | 思想/协议 | 直接移植 | C9 淘汰函数 | 判据形状错（25/26/28） | 高 |
| 4 | seen/unseen 泛化划分协议 | 协议 | 直接移植 | L4 泛化验收 | 记忆/技能迁移验收 | 高 |
| 5 | TextWorld 引擎（CPU-only、7× 快） | 工程实现 | 仅作对照 | 廉价验证场 | C4 低算力评测 | 中 |
| 6 | goal-condition success（部分完成度分档） | 方法 | 仅作对照 | 观察员度量（不进控制环） | 分档判据设计 | 中 |
| 7 | 观测队列 + 循环聚合器（历史机制） | 算法 | 仅借思想 | 快环历史 / 记忆门标定 | 二级门阈值参照 | 中 |
| 8 | 规则专家分解（任务→子目标序列） | 工程实现 | 仅作对照 | SkillRunner 验收臂 | 技能表示/固化 | 中 |
| 9 | 单模态基线设计（VISION / ACTION-ONLY） | 方法 | 直接引用 | 消融模板 | 消融设计 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C2（硬冲突）**：ALFWorld 的**全部价值**建立在「自然语言进入控制闭环」之上；SSEA 若照搬其接口，等于把语言抬进控制环。**必须以 PDDL 符号状态替代文本观测**后才可接入。
  - **C1（◐）**：BUTLER 是语言生成智能体，不是生存控制架构；只借环境侧。
  - **C4（◐）**：具身视图（THOR 渲染 + 物理）算力重；文本视图便宜，但仅文本视图时又依赖「文本动作」这一 C2 冲突通道。
- **隐含假设与失效条件**：
  - 导航依赖**预建栅格图**（强先验），在 SSEA 无地图场景会失效；
  - PDDL 域是**手工/领域专家构造**，迁移到生存域需重写域与文法；
  - 观测模板是 preliminary，对象误检会污染状态估计。
- **算力 / 带宽 / 工程代价**：文本视图 CPU-only 便宜（7× 快）；具身视图需 GPU 渲染（100MB×batch）。自建 TextWorld 式引擎需 PDDL 域 + 文法 + 规划器，工程量中等。
- **搬运后的可能退化模式**：若把文本动作直接当 SSEA 动作，会重演债务 27——出现「通道无环境消费者却报成功」；若把 goal-condition 率当控制信号，会违反 C9（观察员评分入环）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **评测环境（最紧）** | **MemRL、SkillRL、RAGEN、Memento、Agent0** | 这五卡都缺一个「成功由环境确定性判定、且有 seen/unseen 泛化协议」的交互环境；ALFWorld 正好提供。MemRL/Memento 的记忆检索、SkillRL 的技能库、RAGEN 的 Echo Trap 诊断、Agent0 的课程-执行回路，都可在 ALFWorld 文本视图上取得**无代理指标污染**的读数 |
| **前置依赖** | TextWorld 引擎、PDDL 域、ALFRED/THOR | 用它之前必须先有环境规格（PDDL）+ 引擎；SSEA 可只搬规格与判据形状 |
| **互补（环境侧）** | **Genie** | Genie = **生成式视觉世界模型**（无监督、潜在动作、视觉状态）；ALFWorld = **符号化文本世界**（PDDL、确定性、可规划）。ALFWorld §7 自陈未来要学「**textual dynamics models**，analogous to vision-based world models」——正与 Genie 的视觉世界模型对称，构成「文本动力学 vs 视觉动力学」两极 |
| **互补（判据形状）** | **ScaleEnv** | ScaleEnv 把成功定义成「环境侧确定性代码对最终状态的检查」（`s^env_T` vs `s^env_gt`）——与 ALFWorld 的**终态谓词检查**同形；两者可互为「合成环境 vs 真实环境」的判据对照 |
| **互补（环境规模/契约）** | **Agent-World** | Agent-World 的环境 = `(数据库 D, 工具集 F)`，强调「每个 Action 通道都有消费者」；ALFWorld 是这一契约在**真实具身域**的现成实例（文本动作→PDDL 产生式规则），可作 Agent-World 环境包契约的**参照实现** |
| **替代** | 无（ALFWorld 是评测环境，不替代 SSEA 组件） | — |

### 6.2 推荐组合方案
- **组合 A：ALFWorld（环境）+ MemRL/Memento（记忆）+ SkillRL（技能库）**
  - **接口形态**：ALFWorld 文本视图作环境；SSEA 把文本观测换成 PDDL 符号状态，把六通道中的 locomotion/manipulation 映射到高层文本动作；记忆侧用 MemRL 两阶段检索、技能侧用 SkillRL 技能库。
  - **组合后新增能力**：在**判据干净**（环境终态判定）的具身任务上测「记忆/技能是否真提升泛化」。
  - **新增风险**：语言通道若未被替换成符号通道，C2 冲突复发。
- **组合 B：ALFWorld（判据形状）+ ScaleEnv/Agent-World（环境合成）**
  - **接口形态**：以 ALFWorld 的「终态谓词检查」为模板，给 ScaleEnv/Agent-World 的合成环境设计 C9 友好判据。
  - **组合后新增能力**：合成环境族获得**确定性淘汰函数**参照，规避「LLM 评委 / 被测者表现定难度」的 C9 冲突。
- **组合 C：ALFWorld（文本动力学）+ Genie（视觉动力学）**
  - **接口形态**：ALFWorld 提供「符号世界模型」范式（PDDL 规划器 = 文本引擎）；Genie 提供视觉世界模型。
  - **组合后新增能力**：SSEA 的 Dream-RSI「查无延续时生成未来」可有**两种引擎**——符号引擎（确定、可规划）与视觉引擎（生成、可想象）。

### 6.3 本篇在组合中的典型角色
- **判据样板 + 评测场 + 通道消费者参照**：管「任务成功的确定性判据长什么样」「每个动作通道如何都有消费者」「记忆/技能/参数方法如何在干净环境上取得无污染读数」。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 是五张已读方法卡（MemRL/SkillRL/RAGEN/Memento/Agent0）的评测环境，且直接指向债务 27 第四扫描面（实测于论文 + 项目文档） |
| 立场兼容性 | **2** | C2 硬冲突（语言入控制环，p2–4）；但环境侧 C9/C8 友好（实测） |
| 可搬运性 | **3** | PDDL 域 + 文法 + 规划器可自建（中工程量）；THOR/ALFRED 视觉侧重（实测 + 推断） |
| 证据强度 | **4** | Table 2–5 系统实验（8 seed、3 次评测均值）+ 消融 Fig.4 + 7× 加速（实测） |
| 组合价值 | **5** | 与记忆/技能/参数/环境合成四族都能接；是「评测场」这一稀缺角色（推断） |
| 落地成本 | **3** | 文本视图 CPU-only 便宜；具身视图 GPU 重；自建引擎中等（实测 + 推断） |

---

## 8. 裁决与下一步

- **应用等级：D 基准对照** —— 理由：ALFWorld 的**接口（语言入控制环）与 SSEA 架构冲突**，不作为组件整体采用；但它是 SSEA 环境侧最干净的**对照参照**：①任务成功是**环境侧确定性判据**（C9 友好）；②动作空间**封闭、每通道有消费者**（债务 27 反面标本）；③提供 seen/unseen 泛化协议与廉价（7× 快）验证场。其中**判据形状**与**通道消费者设计**按 **B 零件采用**处理。
- **优先级：P1**（是五张方法卡的评测环境 + 债务 27 的第四扫描面参照）。
- **建议动作**：
  1. 以 ALFWorld 的「终态谓词检查」为模板，重写 SSEA 环境侧成功判据（治债务 25/26/28）；
  2. 参照「每个动作有 PDDL 产生式规则消费者」，补 `test_consumer_surface.py` **第四个面**：Action 每个通道在环境侧都有消费者（债务 27）；
  3. 建一个 **ALFWorld 文本视图适配层**：把文本观测替换为 PDDL 符号状态，六通道只映射 locomotion/manipulation；
  4. 复用 seen/unseen 协议作 L4 记忆/技能迁移验收。
- **最小验证实验**：
  - **双臂 / 消融设置**：SSEA 在 ALFWorld 文本视图上跑同一策略，A 臂 `skill` 通道有消费者（SkillRunner 展开为高层动作序列），B 臂 `skill` 通道禁用；其余五通道固定。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：①机制计数——`skill` 调用次数、**被环境消费次数**（分母必须 > 0，否则仍空转）；②行为差——两臂在 seen/unseen 任务上的成功率差；③淘汰结果——两臂的 energy/生存指标。
  - **预期与证伪条件**：若 A 臂成功率与能量效率**显著优于** B 臂，则「skill 通道有消费者」有效；若两臂无差异（或 `skill` 被消费次数=0），则说明 skill 通道仍空转——债务 27 未修。
- **若 E 不采用：不适用**（裁决为 D）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：SSEA 是否引入 PDDL 式符号环境规格（域 + 文法）作为环境侧标准，还是只在 ALFWorld 上做临时适配？
- **需补查的文献或资料**：ALFWorld 代码/数据是否实际开源（正文未明确）；TextWorld 引擎（Côté 2018）与本卡环境的依赖关系；ALFRED（Shridhar 2020）goal-condition 率的精确定义。
- **需人工核对的公式 / 实现**：pointer softmax 的 switch 公式（Eq.6–7，p15）；Fast Downward 状态更新与「You won!」判定的实现细节。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "a simulator that enables agents to learn abstract, text-based policies in TextWorld and then execute goals from the ALFRED benchmark in a rich visual environment" | 摘要 p1 |
| "ALFWorld uses PDDL to describe each scene from ALFRED and to construct an equivalent text game using the TextWorld engine." | §2 p3 |
| 高层文本动作：`goto / take / put / open / close / toggle / clean / heat / cool` | §2 p3 |
| 具身低层动作：`MoveAhead/RotateLeft,Right/LookUp,Down/Pickup/Put/Open/Close/ToggleOn,Off` | §2 p2 |
| "A state is represented by a set of predicates which define the relations between the entities"；`st = at(player, microwave) ⊗ in(mug, microwave) ⊗ closed(microwave) ⊗ openable(microwave)` | §C p16 |
| "Failed actions and actions without any state-changes result in `Nothing happens`." | §G p18 |
| 任务类型与规模：All 3,553 train / 140 seen / 134 unseen（六类） | Table 1 p2 |
| 零样本迁移 All Tasks：TW-only 40/35；Seq2Seq 6/5；BUTLER 19/10；ORACLE 37/26；Human 8/3 | Table 2 p6 |
| 训练策略：TW-ONLY unseen 34.3、6.1 eps/s；EMBODIED-ONLY seen 33.6、0.9 eps/s；TextWorld 快 7× | Table 3 p7 |
| 单模态基线：ACTION-ONLY 0.0/0.0；VISION 10.0–11.4 / 4.5–6.0 | Table 5 p8 |
| "the pre-built grid-map of receptacle locations is a strong prior assumption" | §3.3 p5 |
| 未来工作："learn 'textual dynamics models' through environment interactions, akin to vision-based world models" | §7 p9 |
| RL 失败：随机撞到合法动作概率 7.02e-44（序列长 10） | §5.1 p7 |
| 文本游戏示例以 "You won!" 结束（环境侧终态判定） | §K p21 |
