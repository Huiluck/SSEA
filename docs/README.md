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
| [13-milestone4-plan.md](13-milestone4-plan.md) | Milestone 4 执行计划。依赖盘点、修正后的执行顺序、增量 1–3（Verification Gate / Experience Compiler / Plasticity Controller）的设计、验收与落地结果 | **执行计划（进行中）** |
| [14-overview-and-roadmap.md](14-overview-and-roadmap.md) | 项目总览与路线图。自足入口：项目是什么、架构现状、能力边界、证据现状、依赖图与关键路径 | **入口文档（2026-09-27）** |

## 阅读顺序

**第一次接触这个项目，从 [14](14-overview-and-roadmap.md) 开始**——它是自足的入口，
不预设你读过任何其他文档。想深入某一面时再按下面的顺序走。

01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 / 10 / 11。
01–04 是思考过程，05 是第一版正式任务书，06 是自我答辩，07 是修订后的当前版本，
**08 是对 07 的模糊地带补全**，**09–11 是 Milestone 0 的三份交付物**（互为支撑，建议连读）。
**12 是进度快照**，回答「现在到哪了、什么有效什么还没证据」，与上面十一篇是叙述关系而非递进关系。
**13 是 Milestone 4 的执行计划**，取代 12 §5.3 的排序（那份排序把价值判断当成了依赖判断）。
**14 是总览与路线图**：12 回答「到哪了」（向后看），14 回答「往哪走」（向前看）。

> **注意**：07 仍是任务书本体，但 08 修订了它的第 5、6、8、9 节及运行公式。动手写 Milestone 1 的接口协议前，必须先读 08 的第 5 节修订条款汇总表。
>
> **Milestone 0 已完成**（09 / 10 / 11）。其验收标准"明确 SSEA 是新架构，而不是现有模型应用"由 09 第 4 节的消融检验表回答。

## 下一步

按 07 的推荐执行顺序，并按 08 的修订条款实现。

**已完成**：Milestone 0（09 / 10 / 11）、Milestone 1（接口协议）、
Milestone 2（快环骨架）、Milestone 3（记忆与技能）、
Milestone 4 增量 1–3（Verification Gate / Experience Compiler / Plasticity Controller），
代码见 [`SSEA/`](../SSEA/)，
说明见 [SSEA/README.md](../SSEA/README.md)。
**总览与路线图见 [14](14-overview-and-roadmap.md)**。

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
闭环可运行」已由 `tests/test_fast_loop.py` 覆盖。

Milestone 3 已实现 `memory_system.py` 与 `skill_library.py`，替换掉两个占位：
`ZeroMemoryRetriever`（`m_t` 恒为零）换成真实的 `MemorySystem`，
`FastLoopContext.skills` 的空查表换成 `SkillLibrary`。

`m_t` 无命中时仍返回零向量——与占位实现**数值上不可区分**。这不是偷懒：
诚实的空在占位实现和真实实现上必须表现一致，否则「有记忆」与「没记忆」无法
分辨。`ZeroMemoryRetriever` 保留为消融对照组，不是默认值。

07 §11 的四条验收（写入 / 检索 / 保存技能 / 调用技能）已由
`tests/test_memory_system.py`（87 项）与 `tests/test_skill_library.py`（57 项）覆盖。

Milestone 4 增量 1–3 已实现 `verification_gate.py`、`experience_compiler.py`
与 `plasticity.py`。Gate 做四级检查（格式 → 沙盒 → 回归 → 小范围环境测试），
产出 `GateResult` 交给 `StructureStore.commit()` 内部分流。Gate **不打分**——
SSEA 只有淘汰函数（C9），两个提案一个让存活翻倍一个减半，只要都合法，
Gate 一视同仁。编译器吃 trace 吐提案，**不提交、不评估、不自己发明切分规则**；
`make_slow_loop_hook` 把它接成 `SLEEP` 末尾的钩子，于是睡眠期真的整理经验了。

增量 3（可塑性）把 07 §6.7 的两张清单变成可执行的边界：`PlasticityController`
回答"这个能不能改"（**白名单**，且不可更新清单**先于**白名单匹配），
`LocalPlasticity` 按**可观测症状**提 Δθ——"值得记的帧上门从没开过"就降低
`memory_gate_threshold`，"写进去了却读不回来"就降低 `min_similarity`，
两者皆非则沉默。第一阶段的 Δθ 是**结构侧**阈值，参数侧整个推迟：
权重增量递进 Gate 的第四级它看不见，硬塞进 `UPDATE_ADAPTER` 会让
"经过验证门"这句话变成假话。

这一级修了两处断点：`FastLoopContext.get_threshold()` 原本是个**没有消费者的
声明**（改结构阈值对行为毫无影响，而提案、Gate、Store 一路都是绿的）；
`thresholds` 这个结构类别原先**永远无法被初始化**（格式级要求 target 已存在，
而没有任何提案类型能建第一个键）。完整记录见
[13-milestone4-plan.md](13-milestone4-plan.md) §4.6、§5 与 §6。

全套件当前 **737 passed, 1 skipped**，且在 `pytest-randomly` 的 15 个随机
seed 下均为此结果（顺序不变性已有自动守卫，见
[requirements.txt](../requirements.txt)）。

## 下一步（Milestone 4 剩余）

慢环本体剩余：RuleCompiler、HeritableFilter、Gene Manager，
以及 `DeathHook` 的接线。执行顺序见
[13-milestone4-plan.md](13-milestone4-plan.md) §3。

**但补组件本身不产生有效性证据。** 详见 [14](14-overview-and-roadmap.md) §6：

- **§12 实验 6（安全自我修改）的前置已全部就绪**——Gate 与提案生产者（ΔS + Δθ）都在，
  它是七个验收实验里第一个可以开跑的。
- **实验 1（非语言闭环）** 缺的只是一个测量脚本，不是实现。
- **真正的瓶颈是「世界里没有可学的成功」**——默认随机初始化解码器从不 emit grasp，
  而 grasp 是唯一正能量来源。它挡住实验 2 / 3 / 7 三个，是性价比最高的一处修改。
