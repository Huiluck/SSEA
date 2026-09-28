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
| [12-progress-report.md](12-progress-report.md) | 项目进度报告。07 §18 十二项完成标准逐条对账、§12 实验的实测数字与「机制数字 vs 对照组数字」的区分、Milestone 4/5 待办与执行顺序、25 项已知债务 | **进度快照（2026-09-27）** |
| [13-milestone4-plan.md](13-milestone4-plan.md) | Milestone 4 执行计划。依赖盘点、修正后的执行顺序、增量 1–3（Verification Gate / Experience Compiler / Plasticity Controller）的设计、验收与落地结果 | **执行计划（进行中）** |
| [14-overview-and-roadmap.md](14-overview-and-roadmap.md) | 项目总览与路线图。自足入口：项目是什么、架构现状、能力边界、证据现状、依赖图与关键路径 | **入口文档（2026-09-27）** |
| [15-glossary.md](15-glossary.md) | 名词表：术语 / 意义 / 出处。只回答「这个词在本项目里是什么意思、权威处在哪里」，不复述设计、不重抄公式 | **检索用（2026-09-28）** |
| [16-project-summary.md](16-project-summary.md) | 项目总结：本轮工作、现在的数字、证据现状（三档判据 / 两把尺）、债务现状、下一步与已否决项。**回答的是第四个问题**——不是「是什么」也不是「逐条算账」，而是「此刻站在哪、下一步做什么」 | **状态快照 / 交接（2026-09-28）** |
| [17-integrated-synthesis.md](17-integrated-synthesis.md) | 跨文档整合精读：把 01–16 重建为一条研究故事，给齐结论速览、项目全景、双环架构与机制、关键证据与七实验、两把坏尺、可信边界与复现风险、可复用洞察与行动顺序 | **整合报告（2026-09-28）** |

## 阅读顺序

**第一次接触这个项目，从仓库根目录的 [README.md](../README.md) 开始**——那是门面，
一页讲清「是什么、到哪了、怎么跑、下一步」，并给出本文档集的地图。

**想深入全貌再读 [14](14-overview-and-roadmap.md)**——它是自足的入口，
不预设你读过任何其他文档，比根 README 详细得多。想深入某一面时再按下面的顺序走。

01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 / 10 / 11。
01–04 是思考过程，05 是第一版正式任务书，06 是自我答辩，07 是修订后的当前版本，
**08 是对 07 的模糊地带补全**，**09–11 是 Milestone 0 的三份交付物**（互为支撑，建议连读）。
**12 是进度快照**，回答「现在到哪了、什么有效什么还没证据」，与上面十一篇是叙述关系而非递进关系。
**13 是 Milestone 4 的执行计划**，取代 12 §5.3 的排序（那份排序把价值判断当成了依赖判断）。
**14 是总览与路线图**：12 回答「到哪了」（向后看），14 回答「往哪走」（向前看）。
**15 是名词表**，不参与上面的顺序——它是检索用的：读到哪个词拿不准就查它，
它给的是「这个词在本项目里是什么意思 + 权威处在哪里」，不给设计也不给公式。
**16 是状态快照**，也不参与上面的顺序——回答第四个问题：「此刻站在哪、
下一步做什么、哪些话不能再按老说法讲」。**想知道「现在怎么样」就读它**，
它是唯一一份会把「别的文档里已经过时的数字」点出来的文档。
**17 是跨文档整合精读**，也不参与递进顺序——它把 01–16 重建为一条完整的
研究故事，一页给齐架构、证据、两把坏尺、可信边界与行动顺序；
**想一次看全整个项目、不想逐篇跳转就读它**。

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

全套件当前 **910 passed, 1 skipped**，且在 `pytest-randomly` 的 15 个随机
seed 下均为此结果（顺序不变性已有自动守卫，见
[requirements.txt](../requirements.txt)）。

## 下一步（Milestone 4 剩余）

**那把尺已经换上了（2026-09-28），所以最高优先级移到了下一处。**
本节的上一版写的是「给实验 2 换一把有分辨率的尺」——第三档判据
`action_divergence`（逐帧解码后动作差）已落地在 `experiments/_harness.py`，
判读顺序定为**从细到粗**（细档说「一样」才是真的没动）。
~~换尺之后的当前最高优先级是「查实验 3 的重放判据与编译判据是不是同一把尺」~~
**已查完（2026-09-28）**：**不是同一把尺，而且互不蕴含**——编译判据是窗口内
`energy_change` 的**积分** > 0（从不看水平），重放闸 1 是某一帧的**绝对水平**
对比一个冻结的数（从不看窗口总量）。**所以 0/33 不是「技能表示丢了信息」的证据**，
是**判据的形状错**。见 [16](16-project-summary.md) §3.3 与 12 §6 债务 26。

下面是换尺前后都成立的读数。实验 2 / 3 的脚本本体已于 2026-09-28 写完并跑出数字，
它们给的是**第一组对照数字**：

- 记忆落库 458 条、检索 844 次；两臂的**粗粒度签名（5 个整数）在 7/8 个
  seed 上相同**——但那 5 个整数是阈值化后的投影，**两臂动作在 5/8 个 seed
  上不同**（这些 seed 内部 56–99% 的帧不同，中位幅度 3.5e-4 ~ 1.8e-3）。
  **整数指标相同 ≠ 行为相同**。
- 技能固化出 2 条，**调用 33 次全部失败**（成功率 0.0000）。这一条是**真缺陷**，
  成因已复核（**两条，但被闸序串起来而非并列**，见 12 §6 债务 26）。
- `危险回避率` 两臂都是 0.9814——**饱和**，不能作证据。

这排除了「机制没接上」，也排除了「扰动传不到行为」——**问题出在尺子上**。数字见
[12](12-progress-report.md) §4.2，读法与三种坏数字见
[14](14-overview-and-roadmap.md) §5.2 与 [experiments/README.md](../experiments/README.md)。

- ~~真正的瓶颈「世界里没有可学的成功」~~ **已解除（2026-09-27）**：给趋近与
  操纵链各补一份基因先验后，默认世界第一次出现可编译的成功段
  （0 → 2，`ENERGY_GAINED` 0 → 9）。见 [14](14-overview-and-roadmap.md) §6.3.6。
  **但前置解除只说明「能测」，不说明「测出来是好的」**——上面那三条就是测出来的结果。
- **§12 实验 1 / 6 / 7 已跑**，全是「机制通了」的数字；**实验 2 / 3 已跑**，
  是仅有的对照数字，而它们暴露的是**判据的分辨率不够**。
- ~~08 §2.4「不允许存在无消费者的通道」只活在 docstring 里~~ **已修（2026-09-28）**：
  `tests/test_consumer_surface.py` 扫三个面（结构类别 / 读取访问器 / Action 六通道），
  十条变异实测全部能红。它抓出两处：`rules` 零消费者（**仍登记着**，等 RuleCompiler），
  四个访问器零调用方（**已全部删除**，并加断言守着它们不回来）。
  顺带把快照的「约定只读」变成了结构事实（`MappingProxyType`），
  这一改撞出 `serialization` 里一句永不成立的类型判断（见 12 §6 债务 19）。
- **§12 实验 2 / 3 已落地**（2026-09-28）：脚本本体写完并跑出第一组对照数字，
  而**它暴露的是判据太粗**——记忆两臂的粗粒度签名（5 个整数）7/8 个 seed
  相同，**而动作在 5/8 个 seed 上不同**；技能调用 33 次全部失败（真缺陷，
  成因已复核，且**已定性为判据问题**）。这排除了「机制没接上」，
  也排除了「扰动传不到行为」。
  见 §4.2 与 12 §6 债务 3、21。
  顺带撞出 `FastLoop.__init__` 用一个假值判空（`MemorySystem` 有 `__len__`，
  刚构造的实例是假值，传进去的检索器被静默换掉，见 12 §6 债务 20）。
  全部见 [14](14-overview-and-roadmap.md) §6.3.7 与 §6.4 线 D。

慢环本体剩余：RuleCompiler、HeritableFilter、Gene Manager，
以及 `DeathHook` 的接线。执行顺序见
[13-milestone4-plan.md](13-milestone4-plan.md) §3。
