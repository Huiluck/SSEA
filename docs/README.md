# SSEA 设计文档索引

**项目**：SSEA — Survival-based Self-Evolving Agent Architecture（生存式自演化代理架构）

## 项目目标

设计一种新的模型架构，在减少算力与内存带宽消耗的同时不缩减智力：

- 低算力、低带宽
- 精准回忆历史（外部记忆，而非全部压入权重）
- 可自主修改自身代码与参数权重
- 可保存 / 恢复 / 变异 / 继承（具备生命周期）
- 可在一个近乎真实的生态系统中生存、竞争、合作、演化

核心立场：不是"更小的 Transformer"，而是把**语言生成架构**换成**生存控制架构** ——
感知 → 决策 → 行动 → 反馈 → 学习 → 遗传，自然语言只作为观察员接口，不进入控制闭环。

## 第一阶段目标

第一阶段**不构建生态系统**，只构建"能够进入生态系统的最小生命体"（SSEA v0.3.1）：

1. 非语言感知-行动闭环（快环 FSL 实时控制 + 慢环 SEL 经验编译与演化）
2. 权重 / 记忆 / 技能三分离
3. 混合动作空间（连续 + 离散 + 参数化 + 技能调用），`action_constraints` 只作约束；潜空间仅保留在通信向量中（见 08）
4. 局部学习：记忆写入、技能固化、规则生成、小型 adapter，不做全量权重训练
5. 基因包保存 / 恢复 / 变异 / 继承
6. 自我修改必须经验证门；失败天然回滚（版本号不切换，见 08）
7. 双环之间通过「结构注入面」交换：慢环发布结构新版本，快环读取不可变快照（见 08）

第一阶段明确**不做**：四季生态、自然灾害、多模型社会、自然语言主接口、高分辨率视觉、
复杂物理引擎、全量权重训练、人类知识库接入、自主联网、观察员评分系统。
完整 20 项清单及各项的失败模式见 [11-phase1-not-doing-list.md](11-phase1-not-doing-list.md)。

## 文档清单

| 文件 | 内容 | 性质 |
|---|---|---|
| [01-vision-and-open-questions.md](01-vision-and-open-questions.md) | 项目原始构想：目标、生态设想、9 篇论文初选型、三个核心问题（训练方式 / 逐词输出 / 权重连接）、传代、语言信息密度、架构与生态的边界 | 原始笔记 |
| [02-collaboration-scope.md](02-collaboration-scope.md) | 协研角色定位与六大协作维度，提出起步选项 A–D | 立项对话 |
| [03-architecture-feasibility-v0.1.md](03-architecture-feasibility-v0.1.md) | 对三个核心问题的可行性论证，提出 SSEA v0.1 八模块原型、三个 MVP、训练闭环 | 架构论证 |
| [04-phase1-plan-draft.md](04-phase1-plan-draft.md) | 第一阶段任务规划讨论稿：模块 A–E、五个里程碑、一周计划、五个待决策项、可复用成果表 | 规划讨论稿 |
| [05-ssea-v0.3-charter.md](05-ssea-v0.3-charter.md) | SSEA v0.3 第一阶段任务书：接口协议（Observation / BodyState / Action / Memory / GenePackage 等）、任务分解、里程碑、六个验收实验、技术选型、风险 | 正式任务书 v0.3 |
| [06-v0.3-rebuttal-and-revisions.md](06-v0.3-rebuttal-and-revisions.md) | 对 v0.3 的三点答辩：是否只是拿现有架构当大脑、如何强制非语言交互、`available_actions` 是否退化为有限菜单 | 答辩与修订意见 |
| [07-ssea-v0.3.1-charter.md](07-ssea-v0.3.1-charter.md) | SSEA v0.3.1 第一阶段任务书（当前有效版本）：双环架构、十个模块、修订后的接口协议、运行公式、里程碑、验收实验 | **当前有效任务书** |
| [08-dual-loop-interface-and-gap-closure.md](08-dual-loop-interface-and-gap-closure.md) | 对 v0.3.1 的 13 处模糊地带补全设计：双环结构注入面、Skill Runner 新模块、睡眠期一等公民状态、惊奇估计器、修订条款汇总表 | **补全设计 / 07 的修订依据** |
| [09-architecture-originality.md](09-architecture-originality.md) | Milestone 0：架构原创性说明。四层创新定位、六项可消融检验的架构主张、七项明确不声称的事、与九篇论文的对应关系 | Milestone 0 交付物 |
| [10-boundary-definition-table.md](10-boundary-definition-table.md) | Milestone 0：边界定义表。三条判定测试、17 要素的模型/接口/生态三分、平局裁决先例、后续阶段池 | Milestone 0 交付物 |
| [11-phase1-not-doing-list.md](11-phase1-not-doing-list.md) | Milestone 0：不做清单。20 项不做的具体理由与失败模式、7 类易误解项、突破清单的流程门槛 | Milestone 0 交付物 |
| [12-progress-report.md](12-progress-report.md) | 项目进度报告。07 §18 十二项完成标准逐条对账、已有数字与尚无数字的区分、Milestone 4/5 待办与执行顺序、六项已知债务 | **进度快照（2026-09-27）** |

## 阅读顺序

01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 / 10 / 11。
01–04 是思考过程，05 是第一版正式任务书，06 是自我答辩，07 是修订后的当前版本，
**08 是对 07 的模糊地带补全**，**09–11 是 Milestone 0 的三份交付物**（互为支撑，建议连读）。
**12 是进度快照**，回答「现在到哪了、什么有效什么还没证据」，与上面十一篇是叙述关系而非递进关系。

> **注意**：07 仍是任务书本体，但 08 修订了它的第 5、6、8、9 节及运行公式。动手写 Milestone 1 的接口协议前，必须先读 08 的第 5 节修订条款汇总表。
>
> **Milestone 0 已完成**（09 / 10 / 11）。其验收标准"明确 SSEA 是新架构，而不是现有模型应用"由 09 第 4 节的消融检验表回答。

## 下一步

按 07 的推荐执行顺序，并按 08 的修订条款实现。

**已完成**：Milestone 0（09 / 10 / 11）、Milestone 1（接口协议）、
Milestone 2（快环骨架）、Milestone 3（记忆与技能），
代码见 [`SSEA/`](../SSEA/)，
说明见 [SSEA/README.md](../SSEA/README.md)。

**当前处于 Milestone 4（慢环本体）**：

```
接口协议 → [最小模型骨架] → 最小环境桩 → 运行闭环 →
记忆与技能学习 → 基因保存恢复 → 变异与自我修改 → 最小实验验收 → 进入 v0.4。
              ↑────────── 已完成 ──────────↑
```

Milestone 1 已按 08 第 7 节实现 `sse_protocols/`：八个既有协议文件加修订，
另新增 `structure_store.py` 与 `fast_loop_context.py`，并补 `serialization.py`
满足 07 §11「所有接口可序列化为 JSON」的验收。08 第 5 节 19 条修订条款已逐条核对落地。

Milestone 2 已按 08 §4.1 的快环公式实现：State Core 选 GRU（L1 算子选择，
不构成架构声明，见 09 第 2 节），Skill Runner 作为第 11 个模块插在
Action Decoder 与 Environment 之间，睡眠期实现为一等公民状态
（RUN → SLEEP → WAKE → RUN），死亡快照经 `on_death` 钩子触发。
07 §11 的验收「Observation → perception_vector → hidden_state → Action
闭环可运行」已由 `tests/test_fast_loop.py` 覆盖，全套件 **436 passed, 1 skipped**。

Milestone 3 已实现 `memory_system.py` 与 `skill_library.py`，替换掉两个占位：
`ZeroMemoryRetriever`（`m_t` 恒为零）换成真实的 `MemorySystem`，
`FastLoopContext.skills` 的空查表换成 `SkillLibrary`。

`m_t` 无命中时仍返回零向量——与占位实现**数值上不可区分**。这不是偷懒：
诚实的空在占位实现和真实实现上必须表现一致，否则「有记忆」与「没记忆」无法
分辨。`ZeroMemoryRetriever` 保留为消融对照组，不是默认值。

07 §11 的四条验收（写入 / 检索 / 保存技能 / 调用技能）已由
`tests/test_memory_system.py`（87 项）与 `tests/test_skill_library.py`（57 项）
覆盖，全套件 **595 passed, 1 skipped**。

## 下一步（Milestone 4）

慢环本体：Experience Compiler、RuleCompiler、Plasticity Controller、
Verification Gate、Gene Manager，以及 `MemoryItem.is_heritable()` 的消费者
HeritableFilter。Milestone 3 已把它们要消费的产物（trace、提案、可继承判据、
统计回写）全部备齐，缺的是把 `SLEEP` 末尾的钩子从 `None` 换成真的实现。
