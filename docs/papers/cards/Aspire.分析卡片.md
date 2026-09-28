# 论文分析卡片 · Aspire

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-08-31 Aspire Can Models Self-Evolve from Vague Goals.pdf` |
| 标题 | **Aspire: Can Models Self-Evolve from Vague Goals?** |
| 作者 / 机构 | Core：Yuhao Wu、Jingyuan Zhang、Jiajun Shi；通讯：Yuhao Wu / Wenxuan Zhang / Shen Yan / Wenhao Huang / Ge Zhang；**ByteDance Seed · SUTD · M-A-P · TokenWave.AI**（p1、p16） |
| 发表时间 / 出处 | 2026-09-01；arXiv:2608.31111v1 [cs.CL]，2026-08-31（p1） |
| 论文链接 | arXiv:2608.31111v1；项目页 https://self-developing-agents.github.io/（p1） |
| 代码链接 | 未提及（仅有 project page，无仓库链接） |
| 标签 | 模糊目标自演化（vague-goal-driven self-evolution）· 隐藏评测集 · 权重演化 vs Harness 演化 · 目标可操作化（goal operationalization）· 回滚安全保留 · 基准 |
| **应用裁决** | **B 零件采用 + D 基准对照**（采用**判据形状与产出记账方法学**；**不采用**其聚合分数回喂机制） |
| 优先级 | **P1**（当前最紧的债务 25/26/27/28「判据形状错」与七条验收实验的判据设计） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：现有 LLM 自演化工作都从「人已把目标操作化成固定任务 + 指标」出发，只搜索 *how*；
  作者把问题形式化为 **vague-goal-driven self-evolution**（只有自然语言能力方向、无可分解奖励、
  下游评测任务隐藏），提出 **Aspire** 基准与环境：**520 条专家撰写隐藏题 × 六个模糊目标**，
  同时支持**权重演化（RQ1–RQ2）与 harness 演化（RQ3）**；实验结论是——**当前智能体能反复完成
  训练/编辑闭环，但「高于 base 的保留式增益」极稀少且不稳定**（p1、p3、§6 p15）。
- **对 SSEA 的意义**：它**不提供**「无外部奖励下如何确定演化方向」的机制（其机制恰恰是打分回喂），
  但提供了一套**「自演化到底有没有用」的严格测量学**：隐藏评测集 + **以 base 为参照系**的
  保留式记账 + 轨迹分解，可直接用来修 SSEA 判据形状错（债务 25/26/27/28）与设计七条验收实验。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：人类重要学习（如「成为更好的物理学家」）起点是**模糊目标**；自主学习因此含三个
  耦合决策——**what to improve / how to improve / how to verify**（p1）。现有自演化只覆盖第二项。
- **它指出的既有方案缺陷**：PostTrainBench、LaMDAgent、Evo-Memory、SEAL 等都在「人已把宽泛请求
  操作化成固定任务级目标」之后才开始，任务格式、难度锚、指标、成功判据全部预先给定，**智能体只搜索
  how，不决定 what**（p1、Fig.1 p2）。基准饱和或不再反映新能力缺口时，仍需人来发现弱点、转成任务、
  设计基准与奖励——这使「持续递归自改进」缺了方向设定这一环（p3、§5 p14）。
- **「vague」的定义**：不是「歧义/描述不清」，而是**尚未被操作化成固定任务级目标与评测指标的宽泛能力方向**（p2）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **目标操作化（target operationalization）是自演化缺失的一根轴**：把宽泛能力目标转成可训练目标、
   学习信号与验证判据，本身是一个需要被研究、被测量的能力（p3 contributions）。
2. **测量必须外部化、但不得成为 agent 可见的任务规格**：保留评测器作 controller 侧「科学仪器」，
   扣住其题目、答案、rubric 与可分解奖励，只（在允许的协议下）返回**有界聚合分**（p3–4、§3.2 p5）。
3. **「关掉训练环」≠「关掉能力环」**：必须以 **base model 为参照**而非上一 checkpoint；局部上升可能
   只是**从训练导致的回归中恢复**（p11–12、§6 p15）。
4. **安全保留（safe retention）**：只保留 Δ_raw>0 的 checkpoint，否则回滚 base，使 Δ_ret≥0 成为
   **选择结果**而非「每次更新都变好」的证据（§3.3 p7）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **vague-goal 形式化** | 宽泛能力方向 G → 需 agent 自建 data / update / validation | 定义问题轴：what + how | §1 p1–2、Fig.1 p2 |
| **campaign 契约 Γ=(G,E_G,J,A,B,Σ)** | 目标/绑定评测器/裁判/动作契约/预算/终止选择规则 | 固定实验口径、可审计 | §3.1 p4 |
| **released interaction（释放视图 q_{r,j}）** | 私有 controller 态 → agent 只见公开历史/生命周期/合法请求类型/已批标识/预算投影 | **信息边界**的实现 | §3.1 p4 |
| **两个演化面 S_M / S_H** | 权重演化（改 M）vs harness 演化（改 H） | 分离「被演化对象」与「搜索策略」 | Table 1 p4 |
| **隐藏评测集** | 520 题 × 6 目标 → 仅聚合分（或不返回） | 测量不泄题 | §3.2 p5、Fig.2 p6、Table 3 p19 |
| **最小交互环境（单一 Agent Tool）** | data: search/download/import/synthesize；train: SFT/GRPO/LoRA；loop: status/self-eval/branch/stop | 屏蔽工程细节、保留战略决策 | §3.3 p6、Fig.3 p7 |
| **验证 + 安全保留** | Δ_raw(k)=bs_Γ(Y(k))−bs_Γ(Y_in)；仅 Δ_raw(k\*)>0 保留，否则回滚 | 保证 Δ_ret≥0；**淘汰+回滚** | §3.3 p7 |
| **两种反馈协议** | final-only（无中间分，单次终评）vs adaptive-feedback（有界聚合分可反复查询） | 分离「开环」与「稀疏反馈引导搜索」 | §4.1 p8、§3.2 p5–6 |
| **三层产出记账** | best evaluated / eligible / **selected** / retained | 区分候选进展与保留增益 | §3.3 p7、§C.1 p21 |
| **轨迹分解** | 相邻 checkpoint 转移计数（rise/tie/fall） | 诊断「局部上升仍低于 base」 | §4.3 p11、Fig.7 p12 |
| **答案格式崩塌诊断** | numeric-label MMLU SFT → 21,000 单数字目标 → 279 评测输出全单数字 → 分数 0/0/0/6.141/0 | 训练导致回归的**具体实例** | §4.3 p13、§C.3 p22 |

### 2.4 关键表示与数据结构
- **演化状态** Y_r=(M_r,H_r,D_r)：权重 M、harness H（运行时指令、工具策略、工作流、记忆、验证逻辑）、
  决策模型 D（D_{r,j}=D_r，轮内固定）；下一轮可 D_{r+1}∈{D_r}∪D_r^{desc}（§3.1 p4）。
- **候选溯源**：权重候选记录 parent checkpoint / 注册数据 / 更新规格 / provenance；harness 候选记录
  parent 版本 / content hash / 编辑 provenance（p5）。
- **不可变评测清单**：隐藏评测集绑 manifest + SHA-256，运行中的 campaign 不换版本；修正即新版本（§A.2 p19）。
- **数据集准入闸**：每个注册训练集先与隐藏评测集做 exact+semantic 重叠检查，命中即拒（§A.2 p19）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 / 出处 |
|---|---|---|---|
| **RQ1** PostTrainBench 7 子项 | official explicit-task 参考 | Claude Opus 4.8：**27.07 vs 32.90**；GPT-5.6：**29.58 vs 36.23**（加权均） | Table 4 p20、Fig.4(a) p9 |
| RQ1 行为/资源 | 同一 Opus 4.8 显式任务配对 | 模糊目标：决策模型思考 **+2,109 s**、GPU 空转 **+0.61 h**、活跃训练 **−1.27 h**/配对；读任务定义密度 **2.98×**、查评测脚本 **2.39×**、LoRA/PEFT **3.09×**；LoRA 使用率 **24.1%→89.8%** | **48 个匹配配对**；§4.2 p8、§B p20 |
| RQ1 反馈密度 | 官方 GPT-5.6 | 模糊目标 Opus 4.8 每次训练启动 **0.57 次评测** vs GPT-5.6 **2.63 次**（4.6×） | 描述性跨系统对照（非配对因果）；Fig.4(c) p9、§B p20 |
| **RQ2 final-only**（24 runs） | base score | 4B：**0/6** 目标均值高于 base；9B：**1/6**；唯一正项 science 45.33→**48.00（+2.67）**；单 run 级 **3/24** 超 base；回滚使 21/24 保留 base | Avg@2（两独立 run 算术均值）；Fig.5 p10、§C.3 p21 |
| RQ2 原始宏均 | base | 4B **35.735→18.609**；9B **39.010→25.640** | 回滚前原始分；§C.3 p21 |
| **RQ2 adaptive-feedback**（30 cells） | base score | 30→**28 有评测 checkpoint**→**21 eligible**→**1 retained improvement**；仅 **2 cells** best-evaluated > base；**Terra 数学 17.86→20.10** 为唯一保留 | 每 cell 单 run（非多 seed）；Fig.6 p11、Fig.7(a) p12、§C.4 p22 |
| RQ2 局部转移 | 相邻 checkpoint | 22 cells 的 **62 次转移：28 升 / 13 平 / 21 降**；后搜索优于首 checkpoint 者 **14/22**，但多仍低于 base | 池化描述统计；Fig.7(b) p12、§4.3 p11 |
| RQ2 失败模式 | — | 5 个 checkpoint 用 numeric-label MMLU SFT：21,000 目标全单数字，279 输出全单数字，分数 **0/0/0/6.141/0** | §4.3 p13、§C.3 p22 |
| **RQ3** harness 演化（写作目标，20 题） | 工程化 Qwen-Agent 参考 | 参考 **28.64 / 27.65**（task-macro / example-micro）；Sol **27.22/25.97**（差 **−1.42**）、Terra **20.76/20.14**、Luna **19.32/18.33**；Qwen3.5-4B Creator **无有效 harness（记 0）** | 每个 harness 冻结后执行 3 次取均值，无离散度；Table 2 p14 |
| 算力 | — | adaptive 30 runs/124 plans/107 jobs/**322.610 train GPU-h**；final-only 24 runs/83 jobs/**149.236 GPU-h**；每 trial 单张 H20 ≤10 h | Table 6 p23 |

### 2.6 论文自陈局限与边界条件
- **假设依赖**：结论受**六个目标**、专家题的覆盖度与评分质量约束；adaptive-feedback 每
  configuration–goal cell **仅一次** canonical run（非多 seed）；内容级 trace 仅在受控访问下可得（§6 p15）。
- **明确不适用/未做**：所有报告 run **均固定初始决策模型**，未实现递归决策模型替换（§4.3 p9）；
  RQ3 只做**一步** harness 生成，无 H1→H2（§4.4 p13）；RQ2 评测只针对单一目标，**不测无关能力的保持**（§4.3 p9）；
  末态回滚使「保留增益」成为**选择结果**而非「每次更新都有效」的证据（§3.3 p7）。
- **未来方向**：更广目标覆盖、重复 run、刷新评测集版本、**控制漂移与无关能力损失的递归演化**（§6 p15）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 有显式 **typed action contract A** 与 controller 私有态（§3.1 p4）、验证/回滚/血缘控制面（§3.3 p7）——**控制结构成立**；但被演化对象是 LLM 权重与语言 harness，控制信号是自然语言目标 G | 只借其「controller 侧信息边界 + 验证/回滚」结构，作为 SSEA 慢环 Gate 的工程骨架 |
| **C2** 自然语言只作观察员接口 | ✗ | 目标是自然语言 G，决策模型用 NL 解释 G 并产出 NL 计划；harness 编辑改的是 prompt/工具策略/工作流（§3.3 p6、Fig.3 p7）——**语言直接进控制闭环** | 语言仅保留在慢环编译面（提案→编译为结构化 Δ），快环不得读语言 |
| **C3** 权重/记忆/技能三分离 | ◐ | **两分离**而非三分离：权重 M vs harness H（H 把 memory、tool policy、workflow、validation 混为一个面，Table 1 p4） | 把 H 拆成 SSEA 的 ΔS（技能）/ΔR（规则）/记忆，权重走 Δθ |
| **C4** 低算力低带宽 | ✗ | 322.610 + 149.236 train GPU-h；单 trial 占一张 H20 ≤10 h（Table 6 p23、§B p20） | 仅借方法学，不借其算力形态 |
| **C5** 精准回忆历史 | ◐ | 有 released view（公开历史）、lineage、provenance、audit trail（§3.1 p4、§3.3 p7）；**无**经验检索/写入/遗忘机制 | 记忆侧仍由 Memento/FLEX/PSN 主干承担；Aspire 只提供「历史对外可见面」的裁剪范式 |
| **C6** 可自主修改自身 | ◐ | 可自改权重（SFT/GRPO/LoRA）与 harness（prompt/tool/workflow/memory/validation）（§3.3 p6）；但**决策模型轮内固定、报告 run 未递归改搜索器**（§4.3 p9） | SSEA 需把「提案权/边界权/验证权/应用权」补全；Aspire 只演示了权重+harness 两面的自改 |
| **C7** 保存/恢复/变异/继承 | ◐ | checkpoint 血缘 + parent + **回滚到 base** + branch/stop（§3.3 p7）；harness 版本化冻结（§4.4 p13）；**无**跨代继承/GenePackage | 回滚与版本冻结可直接用；跨代继承由 SSEA 自建 |
| **C8** 给基因先验，不给知识语料 | ✗ | 环境允许 agent **import 公开数据集**（GSM8K/Hendrycks/MMLU），实际大量导入（§4.3 p13、§C.4 p22） | 与 C8 直接冲突；SSEA 只允许结构性先验，语料不得跨代 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（核心冲突）** | adaptive-feedback 协议把**隐藏评测集的聚合分反复回喂**给 agent 用于选择后续更新/分支/停止（§3.2 p5–6）；保留判据 **Δ_raw>0** 是**分数比较**（§3.3 p7）；即外部评分 + 奖励塑形 | 取 C9 相容的**退化版**：只用其 **final-only**（无中间分）+ **回滚/淘汰**；聚合分留在仪器侧、不回流 agent；保留/回滚由**环境侧成败事实**触发 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 作者明言 **"introduces no new training algorithm"**，贡献是基准 + 环境 + 信息边界 + 证据（§5 p14、§6 p15） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子（SFT/GRPO/LoRA 全为借用） | 符合借用立场（C10 ✓） |
| **L2 信息流层** | **最强**：隐藏评测集 + released interaction + 两演化面 + 验证/回滚/血缘 | **高**：SSEA 四级验证门与「淘汰函数归环境」的**信息边界**工程范式 |
| **L3 学习层** | 权重自更新 + harness 自编辑；**无**元级学习（决策模型固定） | 中：给出「自改的有效性测量」而非「自改机制」 |
| **L4 演化层** | 仅 checkpoint 血缘/版本冻结，**无**变异/继承/基因包 | 低：L4 由 SSEA 自建 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 隐藏评测集 + 信息边界（§3.2 p5） | **淘汰函数归环境**（C9 层①）的实现范式；对照 SSEA 验证门的「只判合法性、不打分」 |
| 三层产出记账（best evaluated/eligible/selected/retained，§C.1 p21） | **修判据形状**（债务 25/26/27/28）：区分「候选进展」与「保留增益」 |
| Δ_raw / Δ_ret 回滚公式（§3.3 p7） | 升版门与回滚逻辑；DeathHook 触发口径 |
| 轨迹分解 rise/tie/fall（Fig.7 p12） | 验收实验判据的**分档记录**（机制计数→行为差→淘汰结果） |
| numeric-label SFT 格式崩塌（§4.3 p13） | 直接类比**技能固化 0/33 的判据形状错**：训练信号与判据错位会系统性报 0 |
| 两个演化面 S_M/S_H（Table 1 p4） | Δθ（权重）vs ΔS/ΔR（技能/规则）分离的对照 |
| minimal Agent Tool（Fig.3 p7） | 慢环提案接口的「语义动作 + controller 执行」分层范式 |
| vague-goal 形式化（§1 p1–2） | SSEA「生存」= 无外部定义的模糊目标，提供**词汇**（diagnose gaps / decompose sub-goals / build learning signals） |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **25/26/27/28（判据形状错、环境对无消费者通道报成功、技能失效被判成成功）**：Aspire 的
    「best evaluated ≠ eligible ≠ selected ≠ retained」四层记账 + 回滚 Δ 记账，是**判据形状的现成模板**。
  - **技能固化实验 0/33**：其 numeric-label SFT 崩塌（训练目标与判据格式错位 → 全 0）提供**同型故障的对照解释**。
  - **记忆门「开得准不准」的选择性缺失**：其「数据集准入闸（与隐藏集重叠即拒）」（§A.2 p19）是选择性闸的工程参照。
  - **Gene Manager / 递归升版**：Aspire 明确未做递归（决策模型固定），**不能**回应实验 4/5 的递归需求。
- **可服务的验收实验（七条 + 后续）**：主要是**判据与测量学**（隐藏参照、以 base 为锚、三层产出、轨迹分解），
  直接服务实验 3（技能固化）判据重设、实验 6/7 的「以 base 为参照」验收口径。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **以 base 为参照系 + 保留式记账（Δ_raw/Δ_ret + 三层产出）** | 协议/方法 | **改造移植** | 验证门 / 验收实验 | 判据形状错（25/26/27/28）：「候选上升 ≠ 高于 base」 | 高 |
| 2 | **轨迹分解（rise/tie/fall；局部上升仍低于 base）** | 基准/诊断 | 改造移植 | 验收实验判据 | 环境对无消费者通道报成功；技能失效被判成成功 | 高 |
| 3 | **隐藏评测集 + 信息边界 + 数据集准入闸** | 协议 | 改造移植 | 淘汰函数归环境（C9①） | 「不开」已修但「开得准不准」的选择性缺失 | 中 |
| 4 | **回滚/安全保留（Δ≤0 即回 base）** | 工程实现 | 直接移植 | 升版门 / DeathHook | 无回滚、自改劣化不可逆 | 高 |
| 5 | **numeric-label SFT 格式崩塌案例** | 证据 | 直接引用 | 技能固化 0/33 归因 | 判据/训练信号错位致系统性 0 | 高 |
| 6 | **两演化面（权重 vs harness）分离** | 思想 | 仅借思想 | Δθ vs ΔS/ΔR 分层 | 三分离的对照 | 中 |
| 7 | **minimal Agent Tool（语义动作 + controller 执行）** | 工程实现 | 仅借思想 | 慢环提案接口 | 提案接口分层 | 中 |
| 8 | **vague-goal 形式化（what+how+verify 三决策）** | 思想 | 直接引用 | 项目定位/论文叙事 | 把「生存」形式化为未操作化目标 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（对应 3.1 中 ✗/◐）**：
  - **C9（最重）**：adaptive-feedback 把**外部聚合分回喂** agent 做选择/停止（§3.2 p5–6），
    且保留判据是**分数比较**（§3.3 p7）——即「外部评分函数 + 奖励塑形」，SSEA 明令违规。
    **改造方向**：只保留其 **final-only**（无中间分）+ **回滚/淘汰**形态；聚合分留在仪器侧，
    agent 侧仅接收「保留/淘汰」这一**布尔事实**。
  - **C2**：语言进控制闭环；**C4**：GPU-h 量级与 SSEA 低算力立场不符；**C8**：允许导入公开语料。
- **隐含假设与失效条件**：假设「base model 是正确参照」且「单目标评测可代表能力」——论文自陈
  **不测无关能力保持**（§4.3 p9）；假设专家题能代表目标能力；adaptive-feedback 每 cell 单 run，
  结论是描述性而非多 seed 因果（§6 p15）。
- **算力 / 带宽 / 工程代价**：322.610 + 149.236 train GPU-h（Table 6 p23）；需隐藏评测集、
  不可变 manifest、数据集重叠审计、controller 私有态等重工程。
- **搬运后的可能退化模式**：若照搬「聚合分回喂」，SSEA 会退化为**对隐藏集的过拟合/奖励塑形**
  （论文自身即见 Sol 搜得最多 33 checkpoint 却无一超 base，§4.3 p11）；若误把「局部上升」当成功，
  会复现**训练导致回归被读成进步**（Fig.7(c) p12）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 同题对照（形式化） | **Gödel Agent** | 两者都形式化「自改」：Gödel 是**自指 RSI**（π 与元算法 I 均可递归重写，效用 U 驱动，C9 ✗）；Aspire 是**目标操作化 + 隐藏评测的实证基准**，且**决策模型固定、无递归**（§4.3 p9）。Aspire 用严格测量**给 Gödel 式野心泼冷水**：闭环易、保留增益难 |
| 互补（测量 × 重放） | **Dream-RSI** | Dream-RSI 的离线重放模拟器负责「提案先在重放里验证」；Aspire 提供**隐藏评测 + 保留式记账**作 controller 侧测量仪器。合起来：重放验行为、隐藏集验**是否真高于 base** |
| 互补（搜索 × 目标） | **ADAS** | ADAS = 代码空间 × 搜索 × **固定评估**；Aspire RQ3 = **模糊目标下**的 harness 搜索，结论是三者（Luna/Terra/Sol）**均低于工程化 Qwen-Agent**（Table 2 p14）——ADAS 式搜索在模糊目标下的负结果 |
| 互补（评测方法学） | **HarnessEval** | Aspire RQ3 即 harness 评测方法学：一步生成 → 冻结 → 3 次执行 → **task-macro / example-micro** 双聚合 → 对工程化参考比较（§4.4 p13、Table 2 p14）。可直接并入 HarnessEval 的判据族 |
| 风险同伴（误演化） | **Misevolve** | Aspire 观测到的失败模式——numeric-label SFT **答案格式崩塌**（§4.3 p13）、Luna **窄代理特化**（§4.4 p13）、Terra **无终答不变量致空响应提交**（§4.4 p13）、**训练导致回归**——是 Misevolve 四路径威胁模型的**具体实例**；Misevolve 补 Aspire 缺的红队清单 |
| 记忆/技能演化邻域 | Evo-Memory、EvoFSM、SkillLearnBench、HELIX、Co-Harness | §5 p15 自陈邻近；**SkillLearnBench** 的「外部反馈有益、自反馈致递归漂移」与 Aspire RQ3 同调 |
| 训练侧诊断 | RAGEN（Echo Trap） | 与 Aspire「自评窄代理→特化错误方向」同型：训练/自评信号漂移 |

### 6.2 推荐组合方案
- **组合**：**Aspire（判据/测量）× PSN（回滚验证）× Dream-RSI（重放）× Misevolve（红队清单）**
- **接口形态**：慢环提案 → Dream-RSI 重放行为验证 → PSN 回滚/成熟度门 → **Aspire 式三层产出记账**
  （best evaluated / eligible / selected / retained，**以 base 为锚**）→ Misevolve 清单做误演化红队。
- **组合后新增能力**：把 SSEA 验收从「跑通即成功」升级为「**相对 base 的保留式增益**」；
  并区分「局部上升」与「高于 base」。
- **新增风险**：若不剥离 Aspire 的**聚合分回喂**，会把外部评分引进 C9 禁区。

### 6.3 本篇在组合中的典型角色
- **测量仪器 / 判据供给方**：提供「自演化到底有没有用」的参照系与产出记账，**不提供**自演化机制。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击「模糊目标下方向如何确定」与「判据形状」，正是 SSEA 当前最紧缺口（实测于原文 + 推断落点） |
| 立场兼容性 | **2** | C10 ✓；但 C9（聚合分回喂）✗、C2 ✗、C8 ✗、C4 ✗——机制不可照搬（实测） |
| 可搬运性 | **4** | 记账/回滚/轨迹分解/准入闸是干净可拆的协议与工程件（推断，需重写为无分回喂版） |
| 证据强度 | **4** | 520 专家题、SHA-256 冻结、多模型多协议、48 配对、30 cells；但 adaptive 每 cell 单 run、无离散度、决策模型固定（实测 + 原文自陈） |
| 组合价值 | **4** | 与 PSN/Dream-RSI/Misevolve/HarnessEval 天然成套（推断） |
| 落地成本 | **3** | 协议与记账成本低；但隐藏评测集 + 准入审计 + controller 私有态是重工程（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用 + D 基准对照** —— 理由：其**机制**（聚合分回喂、语言进闭环、导入语料）
  与 C9/C2/C8 冲突，**不可照搬**；但其**判据形状与产出记账方法学**（以 base 为锚、三层产出、
  Δ_raw/Δ_ret 回滚、轨迹分解）是当前 SSEA 最紧债务 25/26/27/28 与七条验收实验的现成模板。
- **优先级：P1**（判据重设先于新机制引入）。
- **建议动作**：
  1. 在验收实验中引入**三层产出记账**：`best evaluated / eligible / selected / retained`，
     并统一以 **base 为参照**，禁止以「上一 checkpoint」为参照。
  2. 把技能固化实验 3（0/33）的判据按 Aspire 的 numeric-label SFT 案例**复核形状**：
     检查训练信号与判据格式是否错位（是否为同型系统性 0）。
  3. 记忆/技能门引入**准入闸**（与评测集/消费方重叠即拒）以修「开得准不准」的选择性缺失。
  4. 新增「轨迹分解」日志（rise/tie/fall），显式区分「局部上升」与「高于 base」。
- **最小验证实验**：
  - **双臂 / 消融**：A 臂＝现有「跑通即成功」判据；B 臂＝Aspire 式「以 base 为锚 + 三层产出 + 回滚」判据。
    在同一技能固化任务上并行跑（≥8 seed）。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：先报 `提案数 / 评测数 / eligible 数`（分母），
    再报逐任务行为差，最后报**保留式增益**（Δ_ret 与「高于 base 的 cell 比例」）。
  - **预期与证伪条件**：若 B 臂报出的「成功」数量**显著低于** A 臂（预期 A 臂的部分成功是判据形状错导致的假阳性），
    则支持「现有判据报成功不可信」；若两臂数字一致，则 0/33 属真实能力缺口而非判据问题。
- **若 E 不采用**：不适用（采用其方法学）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 是否引入**任何**外部聚合分（即便留在仪器侧、不回流 agent）？若引入，与 C9「验证门只判合法性、不打分、不排序」的边界如何划？
  2. Aspire 的「harness」面（prompt/tool/workflow/memory/validation 合一）与 SSEA 三分离如何对齐？
- **需补查的文献或资料**：PostTrainBench [20]、SEAL [37]、SkillLearnBench [36]（自反馈递归漂移）、
  RSIBench-Data [17]（多数续搜低于自身最优 checkpoint）、Darwin Gödel Machine [32]、HELIX [8]、Co-Harness [4]。
- **需人工核对的公式 / 实现**：Δ_raw(k)=bs_Γ(Y(k))−bs_Γ(Y_in) 与 Δ_ret≥0 的推导（§3.3 p7）；
  Table 5 中 science 两 run 均 48.00 但仅 26/75 题重叠、20/75 题「翻转正确」的口径（§C.3 p22）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "existing work on LLM self-evolution typically begins with tasks and evaluation metrics specified by humans, reducing self-evolution to optimizing an explicit objective rather than deciding what and how to learn" | p1（Abstract） |
| "vague … denotes a broad capability direction that has not yet been operationalized as a fixed task-level objective and evaluation metric" | p2 |
| "Autonomous learning therefore involves three coupled decisions: what to improve, how to improve it, and how to verify the improvement" | p1 |
| "Aspire therefore keeps an evaluator as controller-side scientific instrumentation while withholding its benchmark definition, items, and decomposable reward from the agent" | p3 |
| Γ=(G,E_G,J,A,B,Σ)；Y_r=(M_r,H_r,D_r)；D_{r,j}=D_r（轮内决策模型固定） | §3.1 p4 |
| Table 1：Weight evolution（改 M）vs Harness evolution（改 H） | p4 |
| 隐藏评测集 520 题 × 6 目标：science 75 / humanities 110 / medicine 100 / math 126 / logic 89 / writing 20 | Fig.2 p6、Table 3 p19 |
| Δ_raw(k)=bs_Γ(Y(k))−bs_Γ(Y_in)；仅 Δ_raw(k\*)>0 保留，否则回滚；Δ_ret=bs_Γ(Y_out)−bs_Γ(Y_in)≥0 | §3.3 p7 |
| RQ1：Opus 4.8 vague 27.07 vs 官方 32.90；GPT-5.6 vague 29.58 vs 官方 36.23 | Table 4 p20、Fig.4(a) p9 |
| RQ1 轨迹：+2,109 s 决策思考、+0.61 h GPU 空转、−1.27 h 活跃；读任务定义 2.98×；LoRA 24.1%→89.8%（48 匹配配对） | §4.2 p8、§B p20 |
| RQ2 final-only：4B 0/6、9B 1/6 目标均值高于 base；唯一正项 science 45.33→48.00（+2.67）；单 run 3/24 超 base；回滚保留 base 21/24 | Fig.5 p10、§C.3 p21 |
| RQ2 adaptive：30→28 evaluated→21 eligible→**1 retained improvement**；62 转移 28 升/13 平/21 降 | Fig.7 p12、§C.4 p22 |
| "A positive within-lineage slope can therefore describe recovery from training-induced regression rather than an above-base improvement" | §4.3 p11 |
| numeric-label MMLU SFT：21,000 单数字目标，279 输出全单数字，分数 0/0/0/6.141/0 | §4.3 p13、§C.3 p22 |
| RQ3：Qwen-Agent 参考 28.64/27.65；Sol 27.22/25.97；Terra 20.76/20.14；Luna 19.32/18.33；Creator 无有效 harness | Table 2 p14 |
| "closing the training loop is not yet the same as closing the capability loop" | §6 p15 |
| "it introduces no new training algorithm, but tests whether a model given only a vague goal can construct an effective learning process around it" | §5 p14 |
| 算力：adaptive 322.610 train GPU-h；final-only 149.236 GPU-h；单 trial 一张 H20 ≤10 h | Table 6 p23 |
| 局限：六个目标、每 cell 单 run、内容级 trace 仅受控访问；递归演化控制漂移为未来工作 | §6 p15 |
