# 论文分析卡片 · DSPy

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2023-10-05 DSPy Compiling Declarative Language Model Calls into Self-Improving.pdf` |
| 标题 | **DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines** |
| 作者 / 机构 | Omar Khattab、Arnav Singhvi、Paridhi Maheshwari、Zhiyuan Zhang、Keshav Santhanam、Sri Vardhamanan、Saiful Haq、Ashutosh Sharma、Thomas T. Joshi、Hanna Moazam、Heather Miller、Matei Zaharia、Christopher Potts；Stanford University、UC Berkeley、CMU、Amazon Alexa AI、IIT Bombay、Microsoft 等（p1） |
| 发表时间 / 出处 | Preprint，arXiv:2310.03714v1 [cs.CL]，2023-10-05（p1 页脚） |
| 论文链接 | arXiv:2310.03714 |
| 代码链接 | github.com/stanfordnlp/dspy（p1、§8 p11） |
| 标签 | 声明式模块 · 自然语言签名 · 编译器/teleprompter · 文本变换图 · 自举演示 · 度量驱动优化 · 程序即结构 |
| **应用裁决** | **B 零件采用**（L2「声明式模块 + 编译器」范式与「程序即结构、结构可版本化」参照；**编译目标 metric 是 C9 直接冲突，须换成环境侧淘汰事实**） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-29 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把 LM 流水线从「手写提示字符串」提升为**声明式程序**——用**自然语言签名**声明每个文本变换的输入/输出，用**参数化模块**（Predict / ChainOfThought / ReAct 等）替代提示技巧，再用**编译器（teleprompter）**在「程序 + 少量训练输入 + 验证度量」上自动生成与选择演示（并可选微调、集成），使同一条几行代码在 GPT-3.5 与 llama2-13b-chat 上从 4–20% 提升到 49–88%（p1、Table 1 p8）。
- **对 SSEA 的意义**：给出 **L2 信息流层的一个强同构范式**——**「把 prompt/流水线当作可编译、可版本化的程序」**，正对应 SSEA 慢环 SEL「把结构编译成新版本（ΔS/ΔM/ΔR/Δθ）再原子升版」；其「**程序即结构、结构可版本化**」是 GenePackage（C7）的载体参照。但它的编译目标是**最大化外部度量 metric**，与 C9「不设外部评分函数」正面冲突，须改造。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- 问题本身：LM 流水线中的多次 LM 调用通常以**硬编码的 prompt 模板**（长指令+演示字符串）实现，靠人工试错（p2）。该做法**脆弱且不可扩展**——「概念上类似手工调分类器权重」，一段字符串提示不能泛化到不同流水线/LM/领域/输入（p2）。
- 指出的既有方案缺陷：LangChain / LlamaIndex / Semantic Kernel 提供预打包 chain 与 agent，但内部仍靠**手写 prompt 模板**表达任务行为（§3 p3、Appendix B p17–18）；离散提示优化/RL 多针对**单个** LM 调用，未覆盖任意流水线（p3）。

### 2.2 核心思想（关键 insight）
1. **用编程取代提示工程**：借鉴神经网络抽象史（通用层可组合 + 权重由优化器训练而非手调），把 LM 调用做成**声明式模块**、把「如何提示」交给**编译器**（p2–3）。
2. **三个抽象**：**签名**（抽象模块的 I/O 行为）→ **模块**（替换手写提示技巧、可任意组合）→ **teleprompter**（优化整条流水线以最大化度量）（§3 p3）。
3. **参数化 = 可学习**：模块的「参数」包括用哪个 LM、字段前缀/指令、以及**演示**；论文主攻「自动生成并选择演示」（§3.2 p5、§4 p6）。
4. **程序是可编译的结构**：编译不改写任务逻辑，而是产出**新的、被优化的程序对象**（等价于一次版本升版）（§4 p6–7）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **签名（Signature）** | 字段名/元数据 → 自然语言类型化 I/O 声明（`question -> answer`） | 抽象提示与微调，不写字符串 | §3.1 p4 |
| **Predict 模块** | 签名 + 演示 → 调用 LM 并解析输出 | 最核心模块，compile 模式记录 I/O trace | §3.2 p4、App.D.1 p27 |
| **ChainOfThought / ReAct 等** | 签名 → 扩展签名的子模块 | 把提示技巧做成可复用模块 | §3.2 p4–5、App.D.2 p27 |
| **teleprompter（编译器）** | 程序 + 训练集 + 度量 → 优化后新程序 | 自动优化，三阶段 | §3.3 p5、§4 p6–7 |
| 阶段1 候选生成（BootstrapFewShot） | 教师程序 + 输入 → 通过度量的多阶段 trace 作演示 | 类拒绝采样自举演示 | §4 Stage1 p6–7、App.E.1 p28 |
| 阶段2 参数优化 | 候选演示集 → 选定（随机搜索/Optuna）或微调（BootstrapFinetune） | 离散/权重两种优化 | §4 Stage2 p7、App.E.2/E.3 p28–29 |
| 阶段3 高阶程序优化 | 程序 → 集成（并行多份+投票）或改控制流 | 改程序结构本身 | §4 Stage3 p7 |
| 组合（teacher 程序） | 大 LM 昂贵程序 → 监督小 LM 便宜程序 | 昂贵监督廉价、微调压缩 | §3.3 p6 |

### 2.4 关键表示与数据结构
- 签名 = 输入字段元组 + 输出字段元组 + 可选指令；字段 = 字段名 + 可选元数据（prefix/description/类型，类型为 WIP）（§3.1 p4、App.A p17）。
- 程序 = define-by-run 的**文本变换图**：先声明模块，再在 `forward` 中用任意 Python 控制流（if/for/异常）连接（§3.2 p5）。
- 编译产物 = 携带新演示/指令/（可选）新权重的**新程序对象**，可 `deepcopy`、可继续作为 teacher 再次编译（App.E.1 p28）。
- 模块参数：`self.lm`（用哪个 LM）+ `self.demonstrations`（演示列表）与签名分置（App.D.1 p27）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 / 出处 |
|---|---|---|---|
| GSM8K 数学（GPT-3.5） | vanilla/CoT/reflection × none/fewshot | reflection bootstrap dev 83.0、test 76.0；+ensemble dev 86.7（none 仅 65.0） | dev/test 准确率；200 训练、300 dev、1.3k test；随机采样取 3–5 次均值；Table 1 p8、§6 p8–9 |
| GSM8K（llama2-13b-chat） | 同上 | reflection +ensemble dev 49.0、test 46.9（none 仅 36.7） | 同上；Table 1 p8 |
| GSM8K 总体 | 字符串提示 | **不同 LM 从 4–20% 提升到 49–88%** | 表注；Table 1 标题 p8、§6 p9 |
| HotPotQA 多跳（GPT-3.5） | vanilla/CoT RAG/ReAct | multihop bootstrap dev 48.7 / Psg 47.0，test 39.6；ensemble dev 54.7、test 45.6（仅 50% test） | Ans EM / Psg；200 训练、300 dev、1000 验证；Table 2 p11 |
| HotPotQA（llama2-13b-chat） | 同上 | multihop bootstrap dev 42.0、test 36.4；ensemble dev 50.0 | 同上；Table 2 p11 |
| 小模型压缩（T5-Large 770M） | 专有大模型流水线 | dev 39.3% EM、46.0% passage，仅用 200 标注 + 800 无标注 | dev；§7 p10–11 |
| 编译开销 | — | 「分钟到数十分钟」，几千次程序运行（10–20 trials × 150–300 验证例） | §6 p9 |

### 2.6 论文自陈局限与边界条件
- **论文未设独立 Limitations 节**（v1 正文止于 §8 结论 p11）；以下为正文自陈边界：
- 假设依赖：存在可计算的**验证度量**（EM/F1 或另一个 DSPy 程序）与至少少量标注/输入（§3.3 p5–6、§5 p7）。
- 本迭代编译器**只主攻演示**（指令/字段描述/类型为 WIP），未系统优化指令文本（§4 Stage1 p6–7、App.A p17）。
- 编译成本高、属**离线重资产**；集成的 test 结果部分因成本只跑 50%（Table 2 注 p11）。
- 代码/框架为研究级；提示-only 之外的类型约束等尚不成熟（p4 脚注 4）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ✗/◐ | 控制环由 LM 调用构成（ReAct 循环，§7 p10），产物是 QA 系统 | 只保留「结构声明 + 编译」骨架；控制环改结构化信号，LM 退到观察面 |
| **C2** 自然语言只作观察员接口 | ✗ | 流水线核心即 LM 调用与自动生成的 prompt（§3–4） | 签名降级为**观察员接口**；控制流用代码（与 LLMasCode 拼） |
| **C3** 权重/记忆/技能三分离 | ✓/◐ | 模块把 `lm`（权重）、`demonstrations`（经验/记忆）、程序代码（结构）**分置为不同参数**（App.D.1 p27） | 严格三分：演示不得混入结构层 |
| **C4** 低算力低带宽 | ◐ | 编译离线昂贵（几千次运行）；但可编译到 770M T5，推理成本极低（§6 p9、§7 p10） | 编译只在**慢环离线**；快环读编译后廉价结构 |
| **C5** 精准回忆历史 | ◐ | 演示是自举的 I/O 样例、按 predictor 存；非情景记忆、无精准遗忘/合并 | 演示留在记忆层，不进基因 |
| **C6** 可自主修改自身 | ✓/◐ | 编译器自动改写程序的参数与（阶段3）控制流；但编译器自身固定 | 与 Gödel/Ouroboros 组合使编译器可自指 |
| **C7** 保存/恢复/变异/继承 | **✓/◐** | 编译产出**新程序对象**，可 deepcopy、可作 teacher 再编译（App.E.1 p28）；但无显式跨代继承机制 | **编译产出版本化结构 = GenePackage 载体参照** |
| **C8** 给基因先验，不给知识语料 | ◐ | 签名/模块组合是**结构先验**；但**演示携带任务知识**混入编译产物 | 基因只放结构（模块图/签名），演示/知识留记忆层 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（关键冲突）** | 编译器输入含 **validation metric**，目标即「**maximize a given metric**」；阶段2 按 score 选优（p1、§4 Stage2 p7） | **metric 换成环境侧淘汰事实**：编译只保留「通过淘汰（存活/任务成败）」的结构版本，**不排序、不打分** |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 贡献是编程模型（签名/模块/teleprompter），不引入新 L1 算子，LM 是借用 | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子，LM/检索器均借用 | 符合借用立场（C10 ✓） |
| **L2 信息流层** | **签名 + 模块 + 编译器：把流水线当可编译、可版本化的声明式程序** | **高**：与「慢环把结构编译成新版本」同构 |
| **L3 学习层** | BootstrapFewShot 自举演示、BootstrapFinetune 微调、集成 | 中：自举/自改进形状可借 |
| **L4 演化层** | 编译产出可保存/可再编译的新程序对象 | 中：GenePackage 版本化结构参照（无谱系/变异/继承） |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 签名（声明式 I/O） | 慢环发布**结构版本**的声明式接口层（新增建议） |
| 模块（Predict/CoT/ReAct） | 可组合的结构单元，类比慢环产出的 ΔS 技能/ΔR 规则模块 |
| teleprompter/编译器 | **慢环 SEL 的编译器**：把结构提案编译成新版本 |
| BootstrapFewShot | 慢环「重放/自举」把成功轨迹沉淀为结构（与 Dream-RSI 重放衔接） |
| 编译产出的程序对象 | **GenePackage（C7）的版本化结构载体参照** |
| validation metric | **须替换为环境侧淘汰事实**（C9，落点：四级验证门「只判合法性」） |

### 3.4 债务与验收实验对应
- 可回应的已知债务：**Gene Manager 缺失**（编译产出的版本化结构 = 基因库条目形态）；**睡眠期计算预算未定义**（DSPy 给出「10–20 trials × 150–300 验证例、分钟级」的可参考预算口径）；**技能表示够不够**（声明式模块 + 编译 = 技能/结构的一种表示候选）；**判据形状错（25/26/27/28）**（metric→淘汰事实的改造直接呼应「环境对无消费者通道报成功」「技能失效被判成功」）。
- 可服务的验收实验：**实验 4/5（架构变异与淘汰，缺 Gene Manager）**；技能固化实验（0/33）的「结构版本如何产生与判据」。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 「声明式模块 + 编译器」范式 | 思想/形式化 | 仅借思想 | L2 信息流层 | 把「结构」与「如何实现」解耦，结构可编译 | 高 |
| 2 | 签名（自然语言类型化声明） | 表示 | 改造移植 | 结构版本接口 | 结构声明的统一接口 | 中 |
| 3 | 三阶段编译器（候选生成/参数优化/高阶控制流） | 算法 | 改造移植 | 慢环编译 | 结构提案 → 新版本流水线 | 高 |
| 4 | BootstrapFewShot 自举演示 | 算法 | 改造移植 | 慢环自举 | 从成功轨迹沉淀结构 | 中 |
| 5 | 「程序即结构、结构可版本化」 | 思想/表示 | 改造移植 | GenePackage（C7） | 可保存/恢复的结构载体 | 高 |
| 6 | 度量驱动优化（metric） | 对照 | **仅作对照** | 四级验证门 | **反例**：C9 须改为淘汰事实 | 高 |
| 7 | 编译预算口径（trials × valset） | 工程 | 参考 | 睡眠期预算 | 定义慢环计算预算 | 中 |
| 8 | 开源实现（dspy） | 工程 | 参考 | 原型 | 加速编译骨架实现 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（对应 3.1 的 ✗/◐）**：
  1. **C9 硬冲突（最关键）**：编译目标即「maximize a given metric」，阶段2 按 score 排序选优——这是 SSEA 明令禁止的外部评分函数。**改造方向**：删去「最大化 metric」，编译只做**合法性验证**（格式→沙盒→回归→环境实测），保留「通过环境淘汰事实」的结构版本，**不排序、不打分**。
  2. **C2/C1 冲突**：流水线核心是 LM 调用与自动生成 prompt，语言进控制闭环。**改造**：控制流归代码（借 LLMasCode），签名降为观察员接口。
  3. **C8 冲突**：演示携带任务知识混入编译产物。**改造**：结构（模块图/签名）进 GenePackage，演示/知识留记忆层。
- **隐含假设与失效条件**：需存在可计算度量与少量标注；任务能被分解为可自举的多阶段调用；LM 对提示敏感。
- **算力 / 带宽 / 工程代价**：编译离线昂贵（几千次 LM 运行），须在慢环摊销；快环只读编译后结构，推理成本可低（770M T5）。
- **搬运后的可能退化模式**：若把 metric 换成淘汰事实后**信号太稀疏**（多数候选既非存活也非淘汰），编译会**失去方向**——退化为随机扰动；需补内在驱动/惊奇度信号（对应 SSEA 内在驱动层），并防「无消费者通道被误判成功」（债务 25/26/27/28 的坑）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 结构可声明化、可版本化；慢环编译器 | SSEA 部分具备（Gene Manager 缺失） |
| 互补（最紧） | **ADAS** | ADAS 在代码空间**搜索**智能体架构（种群/档案），DSPy 对**给定**流水线做**编译优化**：一搜一编，拼成「先搜架构、再编译实现」 |
| 互补 | **MaAS** | MaAS 超网按查询采样架构、带成本约束；DSPy 提供「编译给定架构」的落地层；两者共享「结构可参数化」 |
| 互补 | **LLMasCode** | LLMasCode 主张「控制流归代码」，DSPy 提供「声明式模块」接口：二者拼成 **C2 合规**的「代码控制流 + 声明式结构」 |
| 互补 | **Gödel Agent / Ouroboros** | Gödel 的自指可让**编译器自身**可改写；Ouroboros 的 reviewed commit = 结构版本的**受审升版**通道，正好承载 DSPy 的「编译产出新版本」 |
| 对照（方法学） | **HarnessEval** | DSPy 的 metric 优化必须过 HarnessEval 的**预算匹配基线 + 搜索/评测分离**检查，否则增益可能只是多试了几次 |
| 同题替代 / 对照 | **AFlow** | AFlow 把 workflow 生成视为**代码空间搜索**（MCTS），与 DSPy 的「编译器优化」是同一问题的两条路线（AFlow 论文池待建卡） |
| 分层 | **PSN / Voyager** | DSPy 编译出的程序版本可作技能载体，与 PSN 的技能网络、Voyager 的键/值技能库嵌套 |

### 6.2 推荐组合方案
- **组合**：DSPy × ADAS × LLMasCode
- **接口形态**：ADAS 搜出架构草图（L4）→ DSPy 用声明式模块把草图**编译**成可执行结构（L2）→ LLMasCode 保证**控制流归代码**、LM 只在叶调用（C2）→ 结构版本交 Ouroboros 式受审升版。
- **组合后新增能力**：得到一条「架构搜索 → 结构编译 → 控制流合规 → 受审升版」的慢环流水线。
- **新增风险**：metric 残留（C9）与演示携带知识（C8）会污染基因；须在编译入口强制「淘汰事实 + 结构/知识分离」。

### 6.3 本篇在组合中的典型角色
- **L2「结构编译器」/ 慢环编译范式**：管「如何把结构声明编译成新版本流水线」——是 GenePackage（C7）版本化结构载体的直接参照。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 「结构可编译、可版本化」直击慢环发布结构新版本（实测于原文范式，推断其同构） |
| 立场兼容性 | **2** | C9 硬冲突（metric 目标）+ C1/C2 语言闭环；C10 与 L2 定位对齐（实测+推断） |
| 可搬运性 | **3** | 范式可搬，但 metric→淘汰的改造大；代码是 Python LM 框架，需重写（推断） |
| 证据强度 | **4** | GSM8K/HotPotQA 多 LM 实测数字、含小模型压缩（实测） |
| 组合价值 | **4** | 与 ADAS/MaAS/LLMasCode/Gödel/Ouroboros/HarnessEval 多点互补（推断） |
| 落地成本 | **3** | 编译骨架中等；关键在 metric-free 改造与预算约束（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用「声明式模块 + 编译器」范式、签名/模块/teleprompter 三抽象、编译产出的**版本化结构载体**（GenePackage 参照）与自举/三阶段编译形状；**编译目标 metric 按 C9 改为环境侧淘汰事实**，删除排序/打分。
- **优先级：P1**。
- **建议动作**：
  1. 在慢环 SEL 定义「结构声明 → 编译 → 新版本」骨架（签名式接口 + 结构版本对象）；
  2. 编译入口强制 **metric-free**：只保留通过四级验证门（尤其环境实测）的结构版本，验证门**只判合法性、不排序**；
  3. Gene Manager 以「编译产出结构版本」为条目形态（不含演示/知识，符合 C8）；
  4. 用 DSPy 的「trials × valset」口径**定义睡眠期计算预算**；
  5. 与 LLMasCode 对齐：控制流归代码、签名降为观察员接口（C2）。
- **最小验证实验（实验 4 候选：结构编译与淘汰）**：
  - 双臂/消融：慢环编译器「按 metric 排序选结构版本」vs「按**环境淘汰事实**保留结构版本」；≥8 seed。
  - 判据（分档，先看分母）：机制计数（编译产出结构版本数 / 淘汰次数）→ 行为差（两臂技能固化率 0/33 是否改善）→ 淘汰结果（环境侧存活率）。
  - 预期与证伪：若「淘汰事实臂」存活率不低于「metric 臂」，则范式可搬；若淘汰信号过稀疏导致编译无方向（存活率≈随机），则证伪「直接照搬」，须补内在驱动/惊奇度信号。

---

## 9. 待确认问题

- 需作者 / 团队决策：SSEA 的「结构」哪些可编译（信息流？模块图？慢环规则？），哪些属宪法层不可编译？
- 需补查的文献或资料：AFlow（代码空间 workflow 搜索）建卡；DSPy 后续版本（GEPA/MIPROv2 等）是否已把「度量」抽象得更接近淘汰事实。
- 需人工核对的公式 / 实现：BootstrapFewShot 的 trace 过滤与 `metric` 接口签名（App.E.1 p28）在 metric-free 改造下的等价物；`dspy.Example(automated=True, ...)` 的演示存储是否会无界增长（C4 缓冲上界）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we introduce DSPy, a programming model that abstracts LM pipelines as **text transformation graphs** … where LMs are invoked through **declarative modules**” | p1 |
| “We design a compiler that will optimize any DSPy pipeline to **maximize a given metric**.” | p1 |
| “DSPy contributes three abstractions … **signatures, modules, and teleprompters**.” | §3 p3 |
| “a DSPy signature is a **natural-language typed declaration of a function**: a tuple of input fields and output fields (and an optional instruction)” | §3.1 p4 |
| 编译器三阶段：**Candidate Generation → Parameter Optimization → Higher-Order Program Optimization** | §4 p6–7 |
| “Compiling the correct modules, instead of string prompts, improves different LMs from **4–20% accuracy to 49–88%**” | Table 1 标题 p8 |
| GSM8K reflection bootstrap：GPT-3.5 dev 83.0 / test 76.0；+ensemble dev 86.7 | Table 1 p8 |
| HotPotQA multihop bootstrap：GPT-3.5 dev 48.7 / test 39.6；ensemble dev 54.7、test 45.6∗ | Table 2 p11 |
| T5-Large(770M) 编译后：dev 39.3% EM、46.0% passage，200 标注 + 800 无标注 | §7 p10–11 |
| “compiling generally runs on the order of **minutes** … a few thousand times (e.g., **10–20 trials over 150–300 validation examples**)” | §6 p9 |
