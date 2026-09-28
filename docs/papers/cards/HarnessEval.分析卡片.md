# 论文分析卡片 · HarnessEval

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `Rethinking the Evaluation of Harness Evolution for Agents.pdf` |
| 标题 | **Rethinking the Evaluation of Harness Evolution for Agents** |
| 作者 / 机构 | Yike Wang\*、Huaisheng Zhu\*、Zhengyu Hu、Yige Yuan、Zhengyu Chen、Shakti Senthil、Hannaneh Hajishirzi、Yulia Tsvetkov、Pradeep Dasigi、Teng Xiao\*；Allen Institute for AI、University of Washington、Independent（\* 等贡献，p1） |
| 发表时间 / 出处 | arXiv:2607.12227v2 [cs.AI]，2026-08-27（Preprint，13 页；p1 页眉） |
| 论文链接 | arXiv:2607.12227 |
| 代码链接 | https://github.com/rethinking-harness-evolution（摘要 p1） |
| 标签 | harness 演化评测方法学 · 预算匹配基线 · test-time scaling 对照 · 搜索/评测集分离（held-out） · pass@1 vs pass@k · 归因与混杂 · 泛化/过拟合 · 判据饱和 |
| **应用裁决** | **A 核心借鉴**（评测方法学/验收协议：预算匹配基线、搜索-评测分离、pass@1/pass@k 判读、分母口径、归因纪律——直接改造成 SSEA 七条验收的**判据健康度检查表**） |
| 优先级 | **P0（立即）**（直击当前最紧的「判据饱和 / 指标全绿但行为没变 / 读数字读错 / 记录数字不复现」，且是协议级、零大算力；是「证明自演化真的有效」的方法论底座） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：现有「自动 harness 演化」用单元测试反馈**搜索** harness、又在**同一公开基准**上报最终性能，导致两个根本问题——(i) harness 演化本身就是迭代搜索过程，必须与**同等反馈/推理预算**下的简单 test-time scaling 基线（parallel sampling / sequential refinement）比较，才能判断增益来自**更好的设计**还是**额外的搜索**；(ii) 搜索集与评测集重叠，报出的增益有**过拟合**风险；作者在 Terminal-Bench 2.1（GPT-5.4 / Claude Opus 4.6 / GPT-5.4 mini）上实测：**自动 harness 演化并不稳定胜过简单 test-time scaling，且泛化有限**（摘要 p1、§4 p5–7、Table 1–3）。
- **对 SSEA 的意义**：它是 SSEA 反复踩的坑的**方法论镜子**——「判据饱和（危险回避率两臂均 0.9814）」「0/33」「指标全绿但行为没变」「读数字读错」「记录数字不复现（债务 25）」本质都是**评测有效性问题**；本文给出「预算匹配基线 + 搜索/评测分离 + pass@1/pass@k 分档 + 分母口径 + 归因纪律」五件可直接搬为 SSEA **判据健康度检查表**的协议。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：如何**公平地评测**「自动 harness 演化」——即自演化智能体对**外部 harness**（prompts / tools / memory / verification routines / control logic，p1）的自主改进，是否真带来**可泛化的设计改进**，还是只是**在评测任务上多试了几次**（摘要 p1、§1 p1–2）。
- **它指出的既有方案缺陷**（§1 p1–2、§2 p2–3）：
  1. **基线缺失**：harness 演化方法（Meta-Harness [Lee 2026]、Agentic Harness Engineering [Lin 2026]、AEVO [Zhang 2026]）用基准任务的 verifier 反馈搜索、又在**同一公开基准**上报成绩，从不与「把预算花在评测任务本身」的 test-time scaling 基线对照——增益可能纯属**重复采样**。
  2. **搜索集=评测集**：当搜索任务与评测任务重叠时，观察到的增益可能反映**对任务特定模式的适应**，而非可迁移的设计改进（§1 p2）。
  3. **混淆**：AHE 的 explore agent 会**从外部检索已为基准调好的 harness**，把「可复用演化」与「检索已拟合评测任务的解」混为一谈（§A.3 p11）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **harness 演化是一次搜索，必须付「搜索税」**：既然它反复用任务反馈评估、修订候选 harness，就应与**同等反馈与推理预算**的简单搜索基线比较；否则无法把「设计增益」从「搜索增益」里分离出来（摘要 p1、§1 p2）。
2. **优化反馈与最终测量必须分离**：搜索用一批任务、最终评测用**另一批不相交任务**，才能区分「真泛化的 harness 设计」与「对评测实例的过拟合」（摘要 p1、§4.4 p7）。
3. **增益若只在 pass@k（best-of）出现、不在 pass@1（单次）出现，就不是设计改进**：若 harness 修订真产出更好的 harness，改进应体现在 pass@1；只在能挑选多条轨迹时才出现的增益，说明它**只是多试了几次**（§4.3 p7）。
4. **多数编辑是「记答案」而非「提炼策略」**：meta agent 的编辑虽**理性、有据**，但大多把具体失败的知识**记进 prompt/memory**，而 agent 本可在单次 rollout 内自己重新发现；真正难的「硬核失败」不受影响，持久文本还带来**上下文膨胀**抵消增益（§5.1 p7–8）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图/页） |
|---|---|---|---|
| **统一预算评测视图** | 固定策略 + 任务分布 + 预算 K → 各方法「更新什么/观察什么反馈/预算花在哪」的显式化 | 把「设计增益」与「搜索增益」拆开 | §3 p3；Fig.2 p3 |
| **四种方法的形式化** | π_θ、任务 x、harness h → 轨迹 ŷ | Parallel Sampling / Sequential Refinement / Harness Evolution / Harness Scaling | §3.2–3.5 p3–5 |
| **预算匹配基线**（parallel sampling / sequential refinement） | 同等反馈与推理预算 → 基线成绩 | 检验 harness 演化是否**超出**「多试」 | §3.2–3.3 p3–4；Table 1–2 |
| **Harness Scaling（新基线）** | 单实例上迭代改 harness → 轨迹 | 「实例引导的 harness 适应」对照「数据集引导的 harness 演化」 | §3.5 p5 |
| **搜索/评测集分离（held-out）** | 45 训练 / 10 验证 / 34 留出 → 泛化 pass@1 | 检验演化出的 harness 是否**可迁移** | §4.4 p7；Table 3 |
| **pass@1 与 pass@k 双指标** | 多次 rollout → 单次均值 / 至少一次成功比例 | pass@k 上界 pass@1；**二者之差即方差** | §A.5 Eq.1–2 p11 |
| **分母口径：基础设施异常计为失败** | 沙箱崩溃/超时 → r=0（**不剔除**） | 防「读数字读错」 | §A.5 p11 |
| **explore agent 禁用** | 去掉外部检索 → 只保留 propose/refine 环 | 保证增益**可归因于演化**而非外部检索 | §A.3 p11 |
| **编辑归因分析**（改了什么层、留/回滚、治哪类失败） | 轨迹 → 编辑分类 | 定位增益/极限来源 | §5.1 p7–8 |
| **任务敏感度/headroom 条件** | 基准性质 → 是否适合评测 harness 演化 | 解释「为何无差」 | §5.2 p8 |

### 2.4 关键表示与数据结构
- **harness h**：定义 prompts、tools、memory、verification routines、control logic 的外部壳（p1）；**初始 harness h₁ 为最小配置**——只给一个 bash 工具，无 skills / middleware / 持久记忆（§A.1 p11）。
- **轨迹 y ∼ π_θ(·|x;h)**：状态、动作、观察的完整序列（§3.1 p3）。
- **结果 R(y,g) ∈ {0,1}**：有单元测试 g 时，轨迹解题则为 1（§3.1 p3）。
- **经验库 C_k = C_{k−1} ∪ {e_k}**，证据 e_k = (h_k, {y^{(i,j)}_k}, 可选 {R})（§3.4 p4）。
- **摘要映射 Φ**（同一底层模型实现）：把经验库压成下游可消费的形式（复现失败、冗余尝试、成本）（§3.1 p3、§A.2 p11，由 AHE 的 **Agent Debugger** 实现）。
- **统一预算**：K=5（各方法一致）、每任务每 harness 一次 rollout（m=1）；最大生成 128k token、高推理档；**所有结果取 2 次独立运行均值**（§4.1 p5）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 / 出处 |
|---|---|---|---|
| Terminal-Bench 2.1，**无单元测试** | direct sampling（初始 harness） | 平均：direct **68.2**；Parallel Sampling **72.3**；Sequential Refinement **69.3**；**Harness Evolution 67.4（低于 direct）**；Harness Scaling **71.8** | pass@1，3 模型平均、2 次运行；Table 1 p6 |
| ↑ 同上，最强模型反例 | — | GPT-5.4 从 **75.3 → 69.7**（Harness Evolution 反而伤强模型） | Table 1 p6 |
| Terminal-Bench 2.1，**有单元测试** | direct sampling | pass@1 平均：direct **72.9**；Parallel Sampling **86.0**；Sequential Refinement **84.3**；**Harness Evolution 75.8**；Harness Scaling **82.6**。pass@5 平均：Parallel **86.0**；Sequential **91.8**；Harness Evolution **86.2**；Harness Scaling **89.3** | pass@1/pass@5，2 模型平均、2 次运行；Table 2 p6–7 |
| **泛化（搜索/评测分离）** | 初始 harness 的 pass@1 | 45 训练/10 验证/34 留出：Harness Evolution **+1.2（Opus 4.6）**、**+0.0（GPT-5.4）**，平均 **+0.6** | pass@1 测试集；Table 3 p7 |
| 编辑归因（定性） | — | meta agent 的编辑**理性且有据**（prompt/middleware/tool 三层），但**硬核失败稳定核**不受影响；编辑多为**记忆修复**而非**策略提炼**；持久文本**上下文膨胀**抵消增益 | §5.1 p7–8；Fig.3 p13 案例 |

> **口径提示（读数字先看分母）**：pass@1 是**所有 rollout 的平均**，基础设施异常（沙箱崩溃/API 超时）**计为 0 而非剔除**（§A.5 p11）；pass@5 = 至少一次成功，是 pass@1 的**上界**，二者之差即**跨次方差**（§A.5 p11）。「2 次独立运行」是本文的方差控制手段。

### 2.6 论文自陈局限与边界条件
- **假设依赖**：评测对象是**语言模型智能体 + 外部 harness**（π_θ 为 LLM，动作经 harness 落到 bash/终端，§3.1 p3、§A.1 p11）；结论依赖 Terminal-Bench 这一**终端任务**分布（§4.1 p5）。
- **明确不适用 / 需重验的情形**（§5.2 p8）：
  1. agent 在 Terminal-Bench 上**已得高分**，剩余失败可能来自**底层模型**而非 harness；
  2. Terminal-Bench **对 harness 设计可能不敏感**——「一个 shell 工具 + 基本 prompt」已足够解多数可解题，瓶颈在模型推理而非脚手架；因此 harness 编辑只带来**边际增益**。
- **作者给出的适用条件**（§5.2 p8）：未来应研究满足两条件的基准——(1) 任务**足够难**、当前 agent 有**显著 headroom**；(2) 性能**高度依赖 harness**（专用工具/技能/工作流关键）。
- **未提及**：无「淘汰函数 vs 评分函数」的显式区分（全文以 pass@1/pass@k 等**外部评分**为度量，未讨论免评分的淘汰式评测）；未涉及权重/记忆/技能三分离；未涉及遗传继承；未涉及生存控制环。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 形式化对象是 LLM 智能体 + harness 的**语言控制环**（π_θ 为 LLM，§3.1 p3）；但其「**统一预算视图**」把「更新什么/观察什么反馈/预算花在哪」显式化，是**架构中立的评测框架** | 只搬**评测框架**（预算/反馈/更新面三元显式化），被测对象换成 FSL/SEL 双环 |
| **C2** 自然语言只作观察员接口 | ✗/◐ | 全篇对象即语言智能体；harness 含 prompts、memory，语言**直接进控制环**（p1、§A.1 p11） | 评测纪律可搬；「harness」在 SSEA 侧对应**结构化控制面**（ΔS/ΔM/ΔR/Δθ），语言不得入环 |
| **C3** 权重/记忆/技能三分离 | ◐ | harness 含 prompts / tools / memory / verification / control logic（p1），可**按组件分面**（§5.1 按 prompt/middleware/tool 层归因）；但无三分离语义 | 把 harness 五面映射为 ΔS/ΔM/ΔR/Δθ，按**分面消融**（每类 Δ 单独开/关） |
| **C4** 低算力低带宽 | ◐ | 评测协议本身廉价（K=5、2 次运行、协议级）；但被测/元 agent 用 GPT-5.4/Opus 4.6，单次上下文 200k、生成 128k（Table 4 p12），算力重 | 只作**离线**验收协议；SSEA 在线侧不引入前沿 LLM |
| **C5** 精准回忆历史 | — | 未提及（harness 的 memory 面存在，但无检索/遗忘机制讨论） | — |
| **C6** 可自主修改自身 | ◐ | harness 演化=自主改进外部壳（§3.4 p4）；但**四权不分**（提案=meta agent、验证=基准跑分、应用=选最优 harness） | 借「propose/refine」形状，但验证权交验证门、应用权交淘汰函数 |
| **C7** 可保存/恢复/变异/继承 | ◐ | 经验库 C_k 跨轮保存 harness 版本、按验证性能选最优（§3.4 p4）；**但演化产物泛化差**（Table 3：+0.6），恰是**继承准入必须查 held-out** 的实证 | 直接支撑 GenePackage/HeritableFilter 的**留出验收**：演化出的结构必须在未参与搜索的条件下实测 |
| **C8** 给基因先验，不给知识语料 | ✓/◐ | 发现「编辑多为**记忆修复**而非**策略提炼**」（§5.1 p8）——把任务特定知识写进持久 prompt 是**反模式**，恰证 C8「不给知识语料」的必要 | 基因只放**结构性先验**；把「记答案」式编辑判为不合格 |
| **C9** 不设评分函数，只有淘汰函数 | **◐（方法论警示，非支持）** | 全文以 pass@1/pass@k 等**外部评分**为度量（§A.5 p11），**未**提出淘汰式评测；但其核心批判「增益来自重复采样而非设计」正是**评分式评测会骗人**的实证 | **改造方向**：把「held-out pass@1」改成**淘汰式**——演化结构须在**未参与搜索的条件**下**存活**（环境侧通过/死亡），而非拿一个留出分数；「预算匹配基线」改为「**同等预算下的简单策略**是否也存活」 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 全篇为**评测方法学/基础设施**，无新 L1 算子 | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子（用 GPT-5.4/Opus 4.6 + bash） | 符合借用立场 |
| **L2 信息流层** | **统一预算视图**：显式化「更新什么 / 观察什么反馈 / 预算花在哪」 | **高**：可作 SSEA 验收实验的**设计模板**（每臂声明 Δ 面 + 反馈面 + 预算） |
| **L3 学习层** | 批判「harness 演化作为搜索」：编辑**记答案**而非**提炼策略**（§5.1） | **高**：直接对应实验 3「技能固化」——技能是**记忆修复**还是**策略提炼** |
| **L4 演化层** | **泛化/过拟合**实证：演化产物在 held-out 上增益≈0（Table 3） | **高**：为 GenePackage 继承准入提供「留出实测」的硬要求 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 统一预算视图（更新面/反馈面/预算） | **验收实验设计契约**：每臂显式声明改了哪类 Δ、观察什么反馈、多少预算 |
| 预算匹配基线（parallel / sequential） | **新增：验收实验的「简单基线」臂**——「多试几次 / 重置」是否也达标？ |
| 搜索/评测集分离（held-out） | **GenePackage / HeritableFilter 准入**：演化结构必须在**未参与慢环搜索**的 seed/任务上实测 |
| pass@1 vs pass@k 判读 | **判据分档**：单次行为（pass@1）vs best-of（pass@k）——回应「指标全绿但行为没变」 |
| 基础设施异常计为失败（分母口径） | **统计纪律**：记录脚本须把异常计入分母，回应债务 25（记录数字不复现） |
| explore agent 禁用（不得预拟合） | **纪律**：技能/记忆入库前不得对验收任务预拟合 |
| 编辑归因（改了什么层、留/回滚） | **实验 3 归因**：技能固化是「记忆修复」还是「策略提炼」 |
| 任务敏感度/headroom 条件 | **验收任务选择**：先验「该条件是否对被测 Δ 敏感」，回应判据饱和 |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **债务 25（记录数字不复现）**：本文的「基础设施异常计为失败 + 2 次运行取均值 + 显式记录口径」给出**记录-实测不脱钩**的纪律（§A.5 p11）。
  - **债务 26（判据形状错）**：本文「pass@1 才反映设计改进、pass@k 只是多试」提示——**0/33 与『41 帧成功』是两个判据**，须先确认判据测的是「设计」还是「搜索」。
  - **债务 27/28（环境对无消费者通道报成功 / 技能失效被判成功）**：属**假阳性**；本文「搜索集=评测集即过拟合」+「explore agent 禁用」给出**归因纪律**——报成功前先问「是不是在评测任务上多试出来的」。
  - **判据饱和（危险回避率两臂均 0.9814）**：本文「agent 已高分 ⇒ 剩余失败来自模型而非 harness」+「基准对 harness 不敏感」正是**饱和的机制解释**（§5.2 p8）。
  - **「指标全绿但行为没变」**：本文 pass@1 vs pass@k 给出**可直接落地的分档判据**。
- **可服务的验收实验（七条）**：
  - **实验 1（非语言闭环）/ 6（安全自修改）/ 7（睡眠期编译）**：本文的**分母口径 + 2 次运行 + held-out** 可作记录纪律（回应债务 25）。
  - **实验 2（记忆召回，检索命中率 0.5164，危险回避率两臂 0.9814 饱和）**：本文的**预算匹配基线 + pass@1/pass@k 分档**可诊断「饱和是判据问题还是真实能力」。
  - **实验 3（技能固化 0/33）**：本文「记忆修复 vs 策略提炼」直接命中其核心问题——**技能表示够不够**。
  - **实验 4/5（基因保存恢复/变异）**：本文的 **held-out 泛化**是 GenePackage **继承准入**的硬要求（虽不解锁 Gene Manager 缺口）。
  - 七条验收的**判据健康度检查表**（见 §4 资产 4）可**前置**应用于全部七条。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **预算匹配基线协议**（同等反馈/推理预算下与简单搜索基线比较） | 协议 | 改造移植 | 验收实验设计 | 「增益来自设计还是搜索」 | 高 |
| 2 | **搜索/评测集分离（held-out 泛化）** | 协议 | 改造移植 | GenePackage / HeritableFilter 准入 | 过拟合、继承准入 | 高 |
| 3 | **pass@1 vs pass@k 判读**（设计改进应体现在 pass@1） | 方法/判据 | 直接引用 | 判据分档 | 「指标全绿但行为没变」 | 高 |
| 4 | **评测缺陷清单 → 判据健康度检查表**（8 条，见下） | 检查表 | 改造移植 | 七条验收的前置检查 | 判据饱和/形状错/读错 | 高 |
| 5 | **分母口径：异常计为失败、口径显式记录** | 口径 | 直接引用 | 记录/统计脚本 | 债务 25 记录不复现 | 高 |
| 6 | **explore agent 禁用（不得预拟合评测任务）** | 纪律 | 直接引用 | 技能/记忆入库 | 归因混杂 | 高 |
| 7 | **编辑归因分析**（改了什么层 / 留或回滚 / 治哪类失败） | 方法 | 改造移植 | 实验 3 技能表示归因 | 0/33 归因 | 中 |
| 8 | **记忆修复 vs 策略提炼** 诊断概念 | 思想 | 仅借思想 | 技能固化/记忆组织 | 技能表示够不够 | 中 |
| 9 | **任务敏感度 / headroom 适用条件** | 思想 | 仅借思想 | 验收任务选择 | 判据饱和 | 中 |

> **资产 4 · 判据健康度检查表（由本文缺陷清单改造，可直接挂到七条验收）**：
> 1. **搜索集 ≠ 评测集？**（held-out 是否分离；否则过拟合，§4.4 p7）
> 2. **有预算匹配的简单基线吗？**（「多试 K 次 / 重置」是否也达标，§4.2–4.3）
> 3. **增益在 pass@1（单次行为）还是只在 pass@k（best-of）？**（后者=多试，非设计，§4.3 p7）
> 4. **跨次/跨 seed 方差报了吗？**（本文 2 次运行；SSEA 现为 5/8 seed，§3.2 债务 25）
> 5. **消融：改了哪一类 Δ？**（prompt/middleware/tool ↔ ΔS/ΔM/ΔR/Δθ，§5.1）
> 6. **分母口径**：异常/失败是否**计入**分母？（§A.5 p11）
> 7. **被测条件对被测变量敏感吗？**（是否已饱和、是否 headroom 不足，§5.2 p8）
> 8. **增益可归因吗？**（有无外部检索/预拟合污染，§A.3 p11）

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  - **C9（最关键）**：本文**未**提出淘汰式评测，全文以 **pass@1/pass@k 外部评分**为度量（§A.5 p11）。其补救（held-out 打分）**仍是外部评分**。→ SSEA 须把「held-out pass@1」**改造为淘汰式**：演化结构在未参与搜索的条件下**存活/死亡**，而非拿留出分数。
  - **C1/C2**：对象是语言智能体 + 含 prompt/memory 的 harness，语言进控制环（p1、§A.1 p11）。→ 只搬评测框架，被测对象与 Δ 面全部换为 SSEA 结构化控制面。
  - **C4**：评测用前沿 LLM（200k 上下文、128k 生成，Table 4 p12），算力重。→ 仅作离线验收协议。
- **隐含假设与失效条件**：假定「有可靠的外部正确性信号（单元测试）」是演化的前提——作者明言**无单元测试时 harness 演化甚至伤强模型**（GPT-5.4 75.3→69.7，Table 1 p6）；SSEA 无外部评分信号，此前提**不成立**，须另找「环境侧事实」作反馈。
- **算力 / 带宽 / 工程代价**：协议级搬运**成本低**（K=5、2 次运行、无权重依赖）；真正成本在**重跑 held-out 与匹配基线**，但相较「因判据无效而误判」的代价可忽略。
- **搬运后的可能退化模式**：
  - 若照搬「held-out 打分」，SSEA 会引入**新的外部评分系统**（C9 违规），且「指标全绿但行为没变」**依旧存在**；
  - 若只加基线不加**淘汰语义**，检查表会退化成「又一套跑分」；
  - 若把「预算匹配基线」理解成「多跑几条 rollout」，会与 SSEA 的**单次行为**口径（pass@1）冲突，反而掩盖问题。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可记录轨迹/反馈、可开/关组件、可重放、可分离搜索与评测集 | SSEA 已具备（七条实验骨架 + 重放） |
| **互补（最紧·同族评测）** | **Misevolve**（自演化风险/红队验收清单） | Misevolve 回答「**该测什么风险**」（模型/记忆/工具/工作流四路径），本篇回答「**怎么测得公平**」（预算匹配基线 + 搜索/评测分离）；二者拼成「演化验收的两半」——一个管威胁面，一个管混杂与归因 |
| **互补（判据健康度）** | **AutoEnv**（判据健康度：差分可靠性检查 + Skin-Inverse 控制消融） | AutoEnv 管「判据**是否饱和/是否对目标变量敏感**」；本篇管「增益**是否来自搜索而非设计**」；二者合为完整**判据健康度套件** |
| **互补（训练诊断）** | **RAGEN**（Echo Trap：「方差先于均值」） | RAGEN 管「**训练动力学**是否崩」（std→熵→梯度）；本篇管「**评测口径**是否骗人」（pass@k vs pass@1）；两者都是「**尺子在说谎**」的诊断，合起来覆盖「训前训后」 |
| **被评对象** | **HarnessDev**（*Can LLMs Create and Evolve Their Own Agent Harness*，2026-09-01）、**Ouroboros**（*Self-Developing Frontier Coding Agent with Reviewed Core*，2026-08-08）、Meta-Harness [Lee 2026]、AHE [Lin 2026]、AEVO [Zhang 2026] | 这些正是本篇**批判的「harness 演化」方法族**——它们的评测协议都需按本篇清单体检（搜索/评测是否同集、有无预算匹配基线） |
| **治理对象** | **ADAS**（自动设计智能体：代码空间 × 搜索 × 评估） | ADAS 的「搜索后在同一基准报成绩」正是本篇点名的**过拟合范式**；ADAS 须配本篇的 held-out + 预算匹配验收 |
| **技能/结构侧** | **PSN**（契约/成熟度门/回滚验证） | PSN 给「技能即带契约的可执行网络」的工程形状；本篇给「演化产物必须 held-out 存活」的验收纪律——PSN 的门控可作为 held-out 淘汰的执行点 |
| **重放侧** | **Dream-RSI**（历史即重放模拟器） | 提供「搜索集」与「评测集」分离的廉价验证场；本篇的 held-out 泛化可在重放中先跑 |
| **替代** | 「搜索集=评测集」的旧评测协议 | 以「预算匹配基线 + 搜索/评测分离」替换 |
| **反例/警示** | 一切「自演化，报涨点」的自评报告（含 SSEA 自身历史） | 本篇是「**别信自评涨点**」的方法论反例集 |

### 6.2 推荐组合方案
- **组合**：本篇 **× Misevolve × AutoEnv**（+ 执行侧 PSN / Dream-RSI）
- **接口形态**：
  - **Misevolve** 提供「该测哪些风险/路径」（威胁清单）；
  - **本篇** 提供「怎么测才公平」（预算匹配基线 + 搜索/评测分离 + pass@1/pass@k + 分母口径 + 归因）；
  - **AutoEnv** 提供「判据本身健不健康」（差分可靠性 + Skin-Inverse 敏感度）；
  - **PSN** 提供门控/回滚的执行点；**Dream-RSI** 提供廉价重放验证场。
  三者组成 **SSEA 验收实验的「三前置」**：先验威胁面（Misevolve）→ 再验判据健康（AutoEnv）→ 再验增益归因（本篇）→ 最后按 held-out 淘汰。
- **组合后新增能力**：SSEA 的七条验收在**开跑前**即可被体检，避免「0/33 才发现判据形状错」「两臂 0.9814 才发现饱和」「报涨点却只是多试了几次」。
- **新增风险**：三套度量若不加约束会合流成新的**外部评分系统**（C9 违规）；须硬性规定三者**只输出通过/拒绝/存活（淘汰式），不输出分数、不排序**。

### 6.3 本篇在组合中的典型角色
- **评测方法学守门人 / 归因审计官**：管「这次自演化声称的改进，到底是**设计变好了**，还是**多试了几次**、**过拟合了评测集**、**只是记了答案**」。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 直击 SSEA 当前最紧的**评测有效性**问题（判据饱和 0.9814、0/33、指标全绿但行为没变、债务 25 记录不复现）（项目现状实测；论文机制对应为实测 Table 1–3） |
| 立场兼容性 | **3** | 评测框架**架构中立**、方法论可净化；但 C9 冲突（全文外部评分，未提淘汰式，实测 §A.5）、C1/C2 域冲突（实测 p1） |
| 可搬运性 | **5** | 纯**协议/判据**级，无模型权重依赖，五件资产可直接改造成检查表（实测 §3–§5） |
| 证据强度 | **4** | 3 模型 × 2 设定 × 泛化设定、2 次运行、预算统一、含最强模型反例（实测 Table 1–3）；扣分：仅 1 个基准（Terminal-Bench）、2 次运行方差控制偏弱、无显著性检验（实测 §4.1 p5、§A.5 p11） |
| 组合价值 | **5** | 与 Misevolve（威胁）、AutoEnv（判据健康）、RAGEN（诊断）、HarnessDev/Ouroboros/ADAS（被评对象）天然咬合（推断为主） |
| 落地成本 | **5** | 协议级、零大算力；主要是**重跑 held-out 与匹配基线**的工作量（实测/推断） |

---

## 8. 裁决与下一步

- **应用等级：A 核心借鉴** —— 理由：它不提供可插拔的算法零件，但提供 SSEA 当前**最缺的评测方法学**——「如何证明自演化真的有效」。其**预算匹配基线、搜索/评测分离、pass@1/pass@k 判读、分母口径、归因纪律**五件是可直接改造成「判据健康度检查表」的**协议级资产**，且与 Misevolve（威胁清单）形成「演化验收的两半」。
- **优先级：P0（立即）** —— 理由：判据饱和、0/33、指标全绿但行为没变、债务 25 记录不复现是当前**最高优先级的阻塞项**；本检查表**开跑前置、零大算力**，可在下一轮七条验收前落地。⚠️ 与既有 P1（AutoEnv/Misevolve）形成**张力**：本篇更贴「如何证明有效」的总问题，故定为 P0；若团队认为须先补齐组件（Gene Manager），可降为 P1，但检查表应即刻挂上。
- **建议动作**（具体到原型 / issue / 实验）：
  1. 在 `sse_protocols` 写入**判据健康度检查表（8 条，见 §4 资产 4）**，作为七条验收的**前置**；
  2. 为每条验收实验加一个**预算匹配的简单基线臂**（「多试 K 次 / 重置」），并**显式声明**每臂的 Δ 面 + 反馈面 + 预算（统一预算视图）；
  3. 把实验 2/3 的**搜索条件与评测条件分离**（held-out seed/任务），对演化产物做**留出实测**；
  4. 记录脚本统一**分母口径**（异常计为失败）并**显式留档口径**，回应债务 25；
  5. 建立 issue：`判据健康度检查表（HarnessEval 协议）`，挂到实验 2（饱和）、实验 3（0/33）、实验 4/5（继承准入）。
- **最小验证实验**：
  - **双臂 / 消融设置**：以**实验 3 技能固化（0/33）**为对象。**臂 A**＝现验收（同一条件搜索+评测）；**臂 B**＝现验收 + HarnessEval 健康检查——(i) 加**预算匹配基线**（不加技能、只多跑 K 次）；(ii) 搜索/评测**分离**（技能在 seed 集 A 上编译，在**未参与编译**的 seed 集 B 上测调用）；(iii) 同时报 **pass@1（单次调用成功）与 pass@k（best-of）**。
  - **判据分档（先看分母）**：① 机制计数（分母：多少 seed / 多少调用 / 多少 held-out 条件）→ ② 行为差（pass@1 单次行为 vs pass@k best-of 之差；held-out 与 in-sample 之差）→ ③ 淘汰结果（该技能是否在 held-out 上**存活**，或该判据是否被判**不可信并弃用**）。
  - **预期与证伪条件**：
    - **预期**：held-out 上 pass@1 无显著提升、仅 pass@k 有差 ⇒ 增益来自**多次尝试**而非**技能设计**，0/33 与「饱和」同源，判据应改造。
    - **证伪条件**：若在**未参与编译**的 seed 集 B 上，技能调用的 pass@1 显著提升（如 ≥ 基线 + 明显幅度）⇒ 说明技能**真带来可泛化的设计增益**，则「技能表示不够」被推翻，应保留判据并另找 0/33 的成因。
- 若 **E 不采用**：不适用（裁决为 A）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的「判据健康度检查表」是否作为七条验收的**开跑前置**（默认必过）还是**可选诊断**？若前置，是否会拖慢七条验收实验？
  2. 「预算匹配基线」在 SSEA 侧如何定义？SSEA 无外部评分，基线的「达标」口径应是**环境侧淘汰结果**（存活/死亡）而非分数——这一定义需团队确认。
  3. 把「held-out pass@1」改造为淘汰式时，「留出」应以什么单位切分（seed / 任务 / 环境实例）？切分会不会削弱样本量（SSEA 现为 5–8 seed）？
- **需补查的文献或资料**：
  4. **HarnessDev**（2026-09-01）与 **Ouroboros**（2026-08-08）**尚无卡片**，需补读——它们是本篇批判的「harness 演化」被评对象，须逐篇对照其评测协议是否踩本篇清单的坑。
  5. 本篇引用的 Meta-Harness [Lee 2026]、AHE [Lin 2026]、AEVO [Zhang 2026] 均无卡片，需补查以完成「harness 演化方法族」图谱。
  6. 项目 `docs/06` 中债务 25–28 的原文定义，以精确对齐「判据形状/记录不复现」措辞。
- **需人工核对的公式 / 实现**：
  7. pass@1 口径中「基础设施异常计为 r=0 而非剔除」（§A.5 p11）——SSEA 现有记录脚本是否同样处理？须核对 `experiments/` 的统计实现。
  8. 「2 次独立运行」的方差控制是否足够（作者未做显著性检验，§4.1 p5）？SSEA 需要多少 seed 才能对 1e-3 量级效应（实验 2 第三档 action_divergence）下结论？
  9. Fig.3 的编辑案例（p13）中「agent 试图削弱测试（weaken tests）」一例——SSEA 的 Gate 是否已能拦截同类「为通过而改判据」的行为？

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “Existing harness evolution methods use unit test cases to search for harness configurations and then report final performance on the same public benchmark.” | 摘要 p1 |
| “it should therefore be compared with simple task-level search baselines under matched feedback and inference budgets to determine whether its gains arise from improved harness design or from additional search alone.” | 摘要 p1 |
| “the reported gains risk overfitting to that specific task set.” | 摘要 p1 |
| “automatic harness evolution does not consistently outperform simple test-time scaling methods and exhibits limited generalization.” | 摘要 p1 |
| 统一预算视图：比较 four methods——parallel sampling / sequential refinement / harness evolution / harness scaling | §3 p3；Fig.2 p3 |
| “Each method is specified by what it updates and what feedback it observes.” | §3 p3 |
| Harness Evolution 形式化：h_k = M(Φ(C_{k−1}))；ĥ = arg max_k R̄(h_k) | §3.4 p4 |
| Harness Scaling = instance-guided harness adaptation vs dataset-guided harness evolution | §3.5 p5 |
| 无单元测试：Harness Evolution 平均 **67.4** < direct **68.2** < Parallel Sampling **72.3**；GPT-5.4 **75.3 → 69.7** | Table 1 p6 |
| “iterative harness revision can actively hurt a strong model when the revision process is guided only by the agent’s own judgment.” | §4.2 p6 |
| 有单元测试：pass@1 Parallel **86.0** > Sequential **84.3** > Harness Scaling **82.6** > **Harness Evolution 75.8**；pass@5 Sequential **91.8** > Harness Evolution **86.2** | Table 2 p6–7 |
| “If harness revision genuinely produced better harnesses, we would expect the improvement to be reflected in pass@1. Instead, the benefit only materializes when we can select among multiple trajectories.” | §4.3 p7 |
| 泛化：45 train / 10 val / 34 test；Harness Evolution **+1.2（Opus）**、**+0.0（GPT-5.4）**，平均 **+0.6** | Table 3 p7 |
| “the revisions discovered during evolution encode task-specific shortcuts rather than genuinely better harness design principles.” | §4.4 p7 |
| “the meta agent makes rational, well motivated edits … a stable core of hard tasks remains unaffected” | §5.1 p7–8 |
| “most edits memorize fixes rather than distilling strategies … the growing volume of persistent prompt text introduces context bloat that can offset the remaining gains.” | §5.1 p8 |
| “agents already achieve relatively high scores on Terminal-Bench … performance is bottlenecked by the model’s reasoning rather than by the surrounding scaffolding.” | §5.2 p8 |
| 适用条件：任务须 (1) 有显著 headroom、(2) 高度依赖 harness | §5.2 p8 |
| 初始 harness：单一 bash 工具，无 skills/middleware/memory | §A.1 p11 |
| explore agent 被禁用：“so that every reported gain is attributable to evolution over the feedback signal rather than to externally sourced, benchmark-specific harnesses.” | §A.3 p11 |
| pass@1 = 所有 rollout 平均；**基础设施异常计为 r=0 不剔除**；pass@k ≥ pass@1，差值反映跨次方差 | §A.5 Eq.1–2 p11 |
| 配置：K=5、m=1、128k 生成、2 次独立运行；Agent/Meta Agent 用 GPT-5.4/Opus 4.6（Table 4） | §4.1 p5；Table 4 p12 |
| Fig.3 案例：agent 曾「试图削弱测试（agent weakened tests）」 | Fig.3 p13 |
