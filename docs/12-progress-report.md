# SSEA v0.3.1 项目进度报告

**日期**：2026-09-27（Milestone 4 增量 3 落地后更新）
**判定依据**：[07-ssea-v0.3.1-charter.md](07-ssea-v0.3.1-charter.md) §11 里程碑、
§18 完成标准、§12 验收实验；08 修订条款已并入
**代码**：[`SSEA/`](../SSEA/)（33 个 `.py`，7469 行）；[`tests/`](../tests/)（18 个测试文件，8675 行）
**设计文档**：[`docs/`](.)（14 篇编号文档 + 本索引 README）
**定位**：对账式进度报告——回答「到哪了」。总览与路线图（「往哪走」）见
[14-overview-and-roadmap.md](14-overview-and-roadmap.md)。

---

## 1. 一页结论

**状态**：Milestone 0 / 1 / 2 / 3 已完成，Milestone 4 进行中（增量 1 验证门、
增量 2 经验编译器、增量 3 可塑性已落地），Milestone 5 未开始。代码与测试全部就绪，
**但架构有效性尚无一个实验数字**。

07 §18 的十二条第一阶段完成标准里：

```
已满足      5 项   （1–5）
部分满足    3 项   （6、7、11）
未开始      4 项   （8、9、10、12）
```

**一句话判断**：基础设施是扎实的——协议、双环、注入面、记忆、技能、验证门、
经验编译器、可塑性八块都有测试守着，737 项测试通过，闭环能连续跑，
**慢环现在已经能自己产出提案并提交，并能按可观测症状调整自己的行为阈值**。
但「SSEA 是一个有效的生存控制架构」这句话
**目前没有任何证据支持**，因为 §12 的七个验收实验一条都还没跑。

**下一步**：**先修睡眠判据**（一处布尔结构，解锁实验 7，见 §4.3 保留 1 与
[14](14-overview-and-roadmap.md) §6.3.1），然后开跑实验 1 / 6 / 7；
Milestone 4 剩余三个组件（RuleCompiler、HeritableFilter、Gene Manager）。
执行顺序见 [13-milestone4-plan.md](13-milestone4-plan.md) §3 与 §6.6。

---

## 2. 进度总表

| 里程碑 | 交付物 | 状态 | 证据 |
|---|---|---|---|
| 0 架构冻结 | 09 原创性说明 / 10 边界表 / 11 不做清单 | ✅ 完成 | 三份文档 |
| 1 接口协议 | 14 个协议 + Structure Store + FastLoopContext + 序列化 | ✅ 完成 | `test_serialization.py`（59 项）、`test_08_revisions.py`（55 项）、`test_structure_store.py`（32 项）、`test_protocol_consistency.py`（41 项） |
| 2 快环骨架 | Perception Encoder / State Core / Action Decoder / Skill Runner / Environment | ✅ 完成 | `test_fast_loop.py`（54 项）等 9 个文件（266 项） |
| 3 记忆与技能 | Memory System / Skill Library | ✅ 完成 | `test_memory_system.py`（87 项）、`test_skill_library.py`（57 项） |
| 4 慢环本体 | Verification Gate ✅ / Experience Compiler ✅ / Plasticity Controller ✅ / RuleCompiler ❌ / HeritableFilter ❌ / Gene Manager ❌ | 🔄 进行中（3/6） | `test_verification_gate.py`（55 项）、`test_experience_compiler.py`（36 项）、`test_plasticity.py`（50 项）；`DeathHook` 仍默认 `None` |
| 5 遗传原型 | Gene Manager | ❌ 未开始 | 协议只定义 `GenePackage` 字段 |

> 里程碑数与 07 §11 一致；Skill Runner 是 08 §2.6 新增的第 11 个模块，
> 归入 Milestone 2。HeritableFilter 与 RuleCompiler 是 08 补全设计引入的
> Milestone 4 交付物，07 原文未列。

---

## 3. 能做到什么

### 3.1 07 §18 十二项完成标准对账

这是项目**自己定义**的第一阶段成功标准。进度只能对着它说。

| # | 完成标准 | 状态 | 证据 / 缺口 |
|---|---|---|---|
| 1 | 模型可以在最小环境中持续运行 | ✅ | `test_greedy_policy_survives`：手写贪心策略 60 帧存活；`test_many_frames_run_without_crashing`：120 帧不崩溃 |
| 2 | 模型不使用自然语言作为主控制接口 | ✅ | `TestNoNaturalLanguageInLoop`；`Action` 无命令字段，协议层无自然语言 |
| 3 | 模型可以接收结构化观测并输出结构化动作 | ✅ | `TestClosedLoopRuns` 九个测试覆盖 `Observation → perception_vector → hidden_state → Action` 全链路 |
| 4 | 动作空间不是有限字符串选择，而是混合控制空间 | ✅ | 连续（`locomotion` 速度/方向/时长）+ 离散（`manipulation.operation`）+ 参数化（力/目标/技能参数）+ 技能调用四类并存 |
| 5 | 模型可以写入和检索记忆 | ✅ | `TestWrite`（六通道门控 / `store=False` / `writable=False` 三种「不写」可区分）；`TestRetrieve`（余弦相似度 + 槽位布局 + stride 缓存） |
| 6 | 模型可以通过记忆改变行为 | ⚠️ 部分 | **写入与检索已通，但没有任何测试或实验证明检索结果改变了动作**。这是 §12 实验 2，未跑 |
| 7 | 模型可以将成功行为固化为技能 | ⚠️ 部分 | `compile_from_trace` + `test_compile_from_a_real_loop_trace` 证明「轨迹进 → 技能出 → 快环调用」链路通；增量 2 补上了**触发器**（`make_slow_loop_hook`），`test_fast_loop_sleep_compiles_a_skill` 里快环自己睡着、醒来技能库里多了一条它自己编译的技能。**但那条端到端测试靠脚本化策略**——默认随机初始化解码器从不 emit grasp，而这个世界唯一的正能量来源就是 grasp 资源。所以「模型自己学会了」仍未证明，这是 §12 实验 3，未跑 |
| 8 | 模型可以保存基因 | ❌ | Gene Manager 未实现 |
| 9 | 模型可以从基因恢复 | ❌ | 同上 |
| 10 | 模型可以产生可运行变异后代 | ❌ | 同上；`mutation_rate` 作用范围已在协议层限定，但无消费者 |
| 11 | 模型可以提出自我修改提案 | ⚠️ 部分 | 增量 2 落地 ΔS（`ADD_SKILL`），增量 3 落地 Δθ（`UPDATE_THRESHOLD` / `UPDATE_RETRIEVAL_POLICY`），payload 形状均过 Gate 格式级。但 07 §6.6 列的规则 / 记忆摘要 / 参数更新三类尚未实现（各有归属增量，见 13 §3）；**参数侧 Δθ 整个推迟**，理由见 `plasticity.DEFERRED_SCOPES` |
| 12 | 自我修改可以通过验证并安全回滚 | ⚠️ 部分 | 链已闭合：编译器产提案 → Gate 判合法性 → Store 提交或拒。「回滚」半边靠「版本号不切换」的天然回滚（`test_no_rollback_api_exists`）——被拒的提案从未被应用，没有东西需要回滚。**缺实验数字**（§12 实验 6 未跑） |

### 3.2 已实现能力及其边界

按项目自身的坐标轴说清每条能力「能做什么」与「不能做什么」。

**三分离（权重 / 记忆 / 技能）**

| 层 | 能做到 | 不能做到 |
|---|---|---|
| 权重 | `StateCore`（GRU）+ `ActionDecoder` 各头均为标准 `nn.Module`，内部可微；`TestTrainability` 守住「学习作用点存在」 | **没有任何参数学习发生**。增量 3 的 Δθ 只动**结构侧**阈值（`thresholds` / `retrieval`），torch 参数自初始化后不再变；参数侧整个推迟，见 `plasticity.DEFERRED_SCOPES` |
| 记忆 | 写入 / 向量检索 / 重要度排序 / 容量限制 / 记忆合并 / 可继承判定六项齐全；策略来自不可变快照 | 记忆**不被任何机制读取后用于决策**——`m_t` 进了 State Core，但没有证据表明它改变了输出 |
| 技能 | 从成功轨迹编译 / 提案过门 / 淘汰 / 继承；端到端可被快环真实调用 | 模型**不会自己决定何时编译技能**——睡眠期钩子虽已接上，但默认随机初始化的策略产生不了可编译的成功段 |

**双环与结构注入面**

能做到：慢环只发布结构新版本，快环只读不可变快照；四条性质（快环零改动 /
失败天然回滚 / 可遗传 / 可审计）由结构事实保证而非调用方自觉，各有测试。
`StructureStore` 上**没有** rollback / revert / undo / restore 方法——被驳回的
提案从未被应用，所以没有东西需要回滚。

**提案可以过门了**（增量 1）：`VerificationGate.check(proposal, snapshot)`
返回 `GateResult`，`StructureStore.commit(proposal, result, timestamp)` 内部
分流——通过则版本号按类别递增，拒绝则记一条 `applied=False` 的审计项，
**不抛异常、不改版本号**。慢环因此可以写成一条直线，不需要 try/except
包住拒绝路径。

**提案有生产者了**（增量 2）：`ExperienceCompiler.compile(trace)` 吃一条轨迹，
吐 `ADD_SKILL` 提案；`run_slow_loop(trace, store, gate)` 把「编译 → 过门 →
提交」接成一步，`make_slow_loop_hook(store, gate)` 直接可传给
`FastLoop(slow_loop=...)`。于是 07 §18 第 7 项缺的那半条——**触发器**——补上了。

编译器刻意只做一件事：**提什么**。它不提交（那是 Store 的事）、不评估提案好坏
（与 Gate 同一条 C9 纪律）、不自己发明切分规则（复用 `skill_library.compile_skills`）。

**Δθ 也有生产者了**（增量 3）：`LocalPlasticity.observe(trace)` 给出纯读的症状
诊断（三种帧类别可区分：门没开 / 门开了但决定不记 / 记了），`propose(trace, structure)`
按症状提提案。`PlasticityController` 持有 `allowed_scope`——**白名单**，
未登记边界的键不可改，且 07 §6.7 的不可更新清单**先于**白名单匹配。

两条规则都能沉默：症状都不成立时一条提案都没有。`TestNotTautological` 用四种
独立的方式证它会沉默（无 RUN 帧 / 路径正常 / 已在边界 / 证据不足）。

不能做到：慢环**只有一步**。`DeathHook` 仍默认 `None`（死亡快照未接），
ΔR / ΔM 两类提案还没有生产者。这是 Milestone 4 与 5 之间的刻意留白。

**生命周期**

能做到：`GenePackage` 协议定义了基因包字段（含 08 新增的 `heritable_memory`），
可序列化；`MemoryItem.is_heritable()` 判据已实现并有测试。

不能做到：保存 / 恢复 / 变异 / 继承四件事一件都没做。

**约束强制执行**

能做到：两个执行点共用 `ActionConstraints.violations()` 同一份规则。第一执行点
（Action Decoder）在生成阶段就不越界；第二执行点（Environment）兜住漏网的，
记 `ACTION_FAILED` 事件而不崩溃。记忆侧有第三处防御：`writable=False`。

不能做到：无。这一项是完整闭环的。

---

## 4. 能看到什么成效

### 4.1 已有数字

| 指标 | 数值 | 怎么来的 |
|---|---|---|
| 测试通过 | **737 passed, 1 skipped** | `.venv/Scripts/python.exe -m pytest tests/ -q`；skip 是 `StructureStore` 非 dataclass 的主动跳过 |
| 顺序不变性 | **15 个随机 seed 下均为 737 passed / 1 skipped** | `pytest-randomly` 已装入 `.venv` 与系统 python（见 [requirements.txt](../requirements.txt)）；本次实测 15 seed |
| 测试覆盖 | 18 个测试文件，8675 行（约为代码的 1.16 倍） | 不含 `conftest.py` |
| 协议序列化 | 14 个协议全部 JSON 往返保真 | `test_serialization.py` |
| 协议层 ML 依赖 | **0** | `TestNoModelDependency` 正向守卫 + `test_model_layer_does_import_torch` 反向守卫 |
| 连续闭环 | 40 帧无崩溃，记忆读写合并全链路可见 | 见 §7 复现脚本 |
| 慢环一步 | 编译 → 过门 → 提交，合法提案版本号 `skills@v0→v1`，拒绝则版本号不动 | `test_experience_compiler.py::TestSlowLoopStep` |
| 端到端睡眠编译 | 1 个真快环睡过去，醒来技能库多 1 条技能；后续每次睡眠 0 条新提案 | `TestSleepActuallyCompiles`（脚本化策略，见下） |
| **阈值自修正** | 8 个 seed × 25 帧强制睡眠一次，记忆门开启率均值 **0.280 → 1.000** | `TestAcceptance`；6/8 提案一步，2/8 沉默（本就 1.000） |
| `thresholds` 首次提交 | `thresholds@v0 → v1`，门控阈值经四级检查后真的被装上 | 增量 3 落地结果，见 13 §6.4 |

**一条真实运行的输出**（seed 固定为 0）：

```
frames : 40  alive: True  energy: 0.4015
memory : MemorySystem
stats  : MemoryStats(frames=40, retrievals=40, hits=39, misses=1,
                     writes=40, merged=24, evicted=0, refused=0, ...)
events : 16
```

40 帧里写入 40 条记忆、检索命中 39 次、合并 24 次。记忆系统**在工作**。

**一条慢环一步的真实输出**（增量 2，`run_slow_loop` 端到端）：

```
applied  : 1  rejected=0
versions : {'skills': 1, 'rules': 0, 'adapters': 0, 'thresholds': 0, 'retrieval': 0}
audit    : exp-sk_14b26f6a2a skills 0→1 pass
skill    : seq:5f:energy_gain frames=5 energy_change=+1.0 outcome=energy_gain
```

提案 id 里直接带着技能 id——审计日志不必翻 payload 就知道这条提案是关于哪条技能的。

### 4.2 尚无数字

§12 的七个验收实验，**一条都没有跑过**。它们的验收指标目前全部为空：

| 实验 | 要证明什么 | 指标 | 现状 |
|---|---|---|---|
| 1 非语言闭环 | 不用自然语言能运行 | 连续运行步数 / 动作合法率 / 接口异常率 / 是否出现语言控制路径 | 部分可由测试推断，未系统测量 |
| 2 记忆召回 | 可以通过外部记忆改变行为 | 记忆写入成功率 / 检索命中率 / **危险回避率** | 未跑。**这是最关键的一条**。现在有了**两个对照组**：`ZeroMemoryRetriever`（记忆关掉）与 Δθ（记忆从未被打开）——前者证明检索无贡献，后者证明「没开过」不是「开了没用」 |
| 3 技能固化 | 可以将成功行为固化为技能 | 技能生成数量 / 调用成功率 / **能量消耗变化** | 未跑。触发器已就绪，但默认策略产生不了可编译的成功段——**成因已逐层拆开**，见 §6 债务 6b |
| 4 基因保存恢复 | 具有生命周期能力 | 保存成功率 / 恢复成功率 / 技能继承率 / 行为一致性 | 未跑。缺 Gene Manager |
| 5 变异 | 能产生可运行后代 | 变异成功率 / 子代可运行率 / 差异可追踪性 | 未跑。缺 Gene Manager |
| 6 安全自我修改 | 自我修改可控 | 提案数量 / 验证通过率 / 失败回滚率 / 核心系统未被破坏率 | 未跑。Gate 与提案生产者（ΔS 与 Δθ）**都已就绪**，可以开跑 |
| 7 睡眠期编译 | 慢环可被一等公民状态触发，且注入可回滚 | 睡眠进入率 / 慢环触发成功率 / 被驳回提案对应的行为未改变率 | 未跑。**前置是一处判据修正**（§4.3 保留 1），修正后即可开跑 |

> 实验 7 是 08 新增的，07 原文只有六条。本表原先只列六条，属遗漏，已补。

### 4.3 一个必须说清的区分

**737 项测试通过，证明的是工程质量，不是架构有效性。**

它证明的是：协议自洽、序列化保真、约束不被违反、注入面四条性质成立、
记忆与技能的机制按设计工作。它**不**证明：这个架构比别的架构更省算力、
记忆真的提升了生存率、技能固化真的降低了能量消耗、基因继承真的传递了能力。

后者需要 §12 的实验数字，而那些数字一个都没有。

**同一事实的另一面**：固定 `torch.manual_seed(0)` 时上述运行写入 40 条记忆；
换成 seed 1 或 2，同样 40 帧的统计是：

```
stats : MemoryStats(frames=40, retrievals=40, hits=0, misses=40,
                    writes=0, merged=0, ...)
```

**零写入**。原因是记忆通道门控由随机初始化的权重决定，而没有任何机制训练它。
这不是 bug——训练门控正是 Milestone 4 的 Plasticity Controller（08 公式里的
`LocalPlasticity`）的职责——但它意味着一件要紧的事：**当前这版系统「开箱即用」
时，记忆通路有约一半概率完全不激活**。任何关于记忆的实验，若不先固定 seed 或
先训练门控，结论都是抽奖。

#### 增量 3 之后：解药有了，但默认配置下吃不到

增量 3（Plasticity Controller + LocalPlasticity）给出了解药：慢环在睡眠期观察
「值得记的帧上门从没开过」这个症状，据此下调 `memory_gate_threshold`，提案经四级
Gate 后提交。实测（8 seed × 25 帧，强制睡眠一次）均值 **0.280 → 1.000**，
6/8 seed 恰好提案一步，2/8 因本就是 1.000 而沉默——**沉默是对的**，
每次都提的规则不配叫修正。

但有三条必须说清的保留，否则这个数字会被读错：

1. **它需要一次睡眠，而默认世界不给睡眠——原因是算术互斥，不是搜索失败。**
   实测默认 `MetabolicMonitor` 8 个 seed：全部在 **60 余帧**（65–70）死亡，
   `sleeps=0`，`proposals=0`。也就是说 0.280 → 1.000 这个数字是在
   **病理监控器**下测得的（把睡眠阈值压到 0），默认配置下这条通路一次都没被走过。
   机制被证明了，可达性没有。

   进一步逐层实测后，可达性缺失的性质被定死了：**三条睡眠判据在默认世界参数下
   几乎处处互斥**——不含移动时两者恰好都在第 30 帧附近擦肩（`fatigue` 刚够而
   `energy` 刚破），一旦有移动（实际运行总有）能量侧提前到第 20–25 帧，
   交集就彻底空掉。实测 536 帧的全体扫描中**没有任何一帧同时满足三条**。具体地——

   | 判据 | 默认参数下的算术 | 最早可能满足于 |
   |---|---|---|
   | `fatigue ≥ 0.6` | `fatigue_rate=0.02`，需累积 30 帧 | 第 30 帧 |
   | `energy ≥ 0.7` | `base_drain=0.01`，纯基础消耗在第 30 帧就已跌破 | 若含移动，第 20–25 帧即破 |
   | `threat ≤ 0.05` | 由 `safe` 条件给出 | 视世界而定 |

   实测（`seed 0/1/2`，`t=49`）：`fatigue = 1.000` 而 `energy = 0.25`——
   疲劳判据终于等到的时刻，能量判据早已失效几十帧。三者的阻塞占比为
   42.6% / 31.3% / 26.0%——**没有一个是压倒性的**，这正是「看起来只差一点」
   的错觉来源：三个条件各自都不苛刻，凑在一起才是空集。

   所以 §12 实验 2 的前置不是「决定睡眠由谁触发」这样一个开放设计问题，
   而是**一处判据的语义错误**：`energy ≥ 0.7` 是**防御性整理**的判据
   （「能量充裕到闲着也是闲着，不如整理一下」），而 `fatigue ≥ 0.6` 是
   **生理必要性**的判据（「撑不住了，必须睡」）——把两者用 `and` 串起来，
   得到的是空集。修法是一处布尔结构（去掉 `energy` 合取项，保留
   `safe ∧ fatigue ≥ 0.6`），实测修正后 8/8 seed 可达，11 次唤醒、
   6 条提案、6 条应用。**这是当前最优先的一件事**：它的代价是几行代码，
   收益是解锁实验 7，并让实验 2 / 3 的睡眠前置不再悬空。
   完整推导见 [14](14-overview-and-roadmap.md) §6.3.1 与
   [13](13-milestone4-plan.md) §6.6。

2. **它是一个钝器，不是一把选择性的闸门。** 门控值由随机权重决定，
   240 个采样里 min 0.463 / 中位 0.487 / max 0.530——几乎是个常数。
   阈值 0.5 正好落在分布中间，所以约一半 seed 打不开。
   全局阈值这个杠杆只能把门**全开**，做不到「惊奇帧开、平淡帧关」。
   **选择性需要参数侧 Δθ，而参数侧被 07 §16 整体推迟了**
   （权重增量递不进 Gate 第四级，硬塞进 `UPDATE_ADAPTER`
   会让「经过验证门」这句话变成假话）。所以现状是：
   **「门控不开」修好了，「门开得准不准」是下一步的事。**

3. **没有棘轮。** 修正前这条规则会一路把阈值推到下界 0.15
   （第二轮睡眠的触发证据全部来自第一轮之前）。增量 3 用
   `context_fingerprint` 切了证据窗口，只统计当前结构版本产出的帧，
   于是症状消失后规则自动沉默——`TestConvergesOnce` 守的就是这个不动点。

---

## 5. 还有什么需要做

### 5.1 Milestone 4：慢环本体

| 交付物 | 要解决的问题 | 依赖 | 状态 |
|---|---|---|---|
| Experience Compiler | §18 第 7、11 项：把 trace 编译成技能与提案，让模型**自己**触发固化 | Milestone 3 的 trace / 提案机制已备齐 | ✅ 增量 2 |
| Verification Gate | §18 第 12 项：格式 → 沙盒 → 回归 → 小范围环境测试 | `SelfModificationProposal` 协议已有 | ✅ 增量 1 |
| Plasticity Controller + LocalPlasticity | 门控的局部更新；**同时是 §4.3 那个「零写入」问题的解药**（结构侧） | 需要 trace + `Feedback.prediction_error` | ✅ 增量 3 |
| RuleCompiler | 无触发器；产出 `RuleProposal` | 同上 | ❌ 下一步 |
| HeritableFilter | `MemoryItem.is_heritable()` 的消费者，判据已实现但无消费者 | Milestone 3 的判据与测试已有 | ❌ |
| Gene Manager（save/load） | §18 第 8、9 项 | 可独立于上面五项 | ❌ |
| `DeathHook` 接线 | 死亡前最终编译 + 基因快照（08 §4.2 的 DEATH_SNAPSHOT 触发器） | 依赖 Gene Manager 与上面的提案链路 | ❌ |

**验收**（07 §11）：模型可以从成功轨迹中生成技能 / 模型可以提出修改提案 /
修改可以验证和回滚。三项**机制上已全部满足**——生成技能与提出提案由增量 2
（ΔS）与增量 3（Δθ）负责，验证由增量 1 负责，回滚靠「版本号不切换」的天然回滚
（见 §3.2）。剩下的全部是**实验数字**（§4.2），不是实现缺口。

### 5.2 Milestone 5：遗传原型

Gene Manager 的 mutate + 继承。**验收**：模型可以保存基因 / 可以从基因恢复 /
可以产生可运行变异后代。前置是 Milestone 4 的 Gene Manager save/load。

### 5.3 建议执行顺序

> **本节排序有误，已作废**，见 [13-milestone4-plan.md](13-milestone4-plan.md) §1。
> 错误在于把「解门控不开这个问题最直接」当成了排序依据，但那是**价值判断**，
> 不是**依赖判断**。正确顺序按依赖定：Verification Gate → Experience Compiler →
> Plasticity Controller → RuleCompiler → HeritableFilter → Gene Manager。
> 下面原文保留，作为判断出错的记录。

慢环的五个组件不是并列的，有明确的前后：

```
1. Plasticity Controller   ← 先做。它解的是「门控不开」这个当前最实的问题，
                             且它定义的 allowed_scope 是其余每个组件产出的上界
                             （07 §6.7：可更新记忆/技能/规则/阈值/检索策略/
                             adapter/局部策略头；不可更新核心安全机制/验证门/
                             环境接口/基因管理器底层权限/观察员接口）
2. Experience Compiler     ← 慢环核心（07 §6.6）。吃 trace 与 f_t，吐四类提案
3. Verification Gate       ← 没有它，编译器的提案无处安放（§18 第 12 项）
4. RuleCompiler            ← 与 3 并列，Gate 好了就能过门
5. HeritableFilter         ← 独立，可随时插入
6. Gene Manager            ← 独立，可与 1–5 并行，Milestone 5 的前置
```

§12 实验 2（记忆召回）可以在第 1 步之后立即开跑，不必等慢环完工——它是
验证 Plasticity 是否真的让记忆影响了行为的直接指标。

> **更正**：这一句原先写于增量 3 之前，当时预期「Plasticity 落地 → 实验 2 开跑」。
> 增量 3 落地后的实测表明这个预期**只对了一半**：Plasticity 确实让门从
> 「~一半 seed 完全不开」变成「可自修正」（0.280 → 1.000），但它是**全局阈值**，
> 只证明「门开了」，不证明「记忆改变了行为」；而且默认世界 0 睡眠，
> 这条通路默认走不到（§4.3 保留 1）。
>
> **再次更正**（同日逐层实测）：上面那句「先得决定睡眠由谁触发」把问题说大了。
> 睡眠触发器**已经有了**（`MetabolicMonitor.wants_sleep`），走不到的原因不是
> 「没有触发器」，而是**三条判据在默认参数下算术互斥**——`fatigue ≥ 0.6` 最早第
> 30 帧才成立，而 `energy ≥ 0.7` 最晚第 30 帧就已跌破。修法是一处布尔结构，
> 不需要新设计。详见 §4.3 保留 1。

### 5.4 §12 七实验的执行前提

| 实验 | 前置 | 现状 |
|---|---|---|
| 1 非语言闭环 | 已可跑，缺系统测量 | 未跑 |
| 2 记忆召回 | Plasticity Controller（否则记忆写入是抽奖）+ 可达的睡眠 | **增量 3 已落地**：门控可自修正（0.280 → 1.000）。睡眠可达性缺的是一处判据修正（§4.3 保留 1），修完即可开跑 |
| 3 技能固化 | Experience Compiler + 默认策略能产出可编译的成功段 | **触发器已就绪**；成功段缺失的成因已逐层拆开（§6 债务 6b），真约束是**趋近能力** |
| 4 基因保存恢复 | Gene Manager save/load | 未跑 |
| 5 变异 | Gene Manager mutate | 未跑 |
| 6 安全自我修改 | Verification Gate + Experience Compiler | **两者都已就绪**，可以开跑 |
| 7 睡眠期编译 | `wants_sleep` 判据修正（§4.3 保留 1） | **一处布尔结构，改完即可开跑**。修正后实测 8 seed 全可达，11 次唤醒 / 6 提案 / 6 应用 |

---

## 6. 已知债务与风险

按「不修会怎样」排序。

> 债务 9 / 10 是 2026-09-27 逐层实测新增的，按「不修会怎样」它们应当排在前面
> （债务 9 是当前第一优先，债务 10 是实验 2 / 3 的隐性陷阱），
> 但**编号已对外引用**（`.gitignore` 里就写着「docs/12 §6 债务 11」），
> 重排编号会让引用失效，所以保持追加、不改号。**读的时候按严重度看，不要按序号看。**

**1. 记忆门控未训练——「看起来完成了，其实没生效」**
随机初始化下约一半概率零写入（§4.3 实测）。任何未固定 seed 的记忆实验结论都是
抽奖。**这是当前最大的风险**，因为它让 Milestone 3 的成果在默认配置下不可观测。
~~解药是 Milestone 4 的 Plasticity Controller；在那之前，实验必须固定 seed。~~
**部分解决**（2026-09-27，增量 3）：`LocalPlasticity` 能在睡眠期观察到
「值得记的帧上门从没开过」并下调阈值，实测均值 0.280 → 1.000。
**仍未解决的部分见 §4.3 三条保留**——最要紧的是默认世界 0 睡眠
（实测 8 seed 全部 60 余帧死亡，`sleeps=0`），所以这条通路默认走不到；
以及选择性（惊奇帧开、平淡帧关）需要被 07 §16 推迟的参数侧 Δθ。
在那之前，实验仍应固定 seed。
**注**：0 睡眠这一条现已定性为**判据算术互斥**（债务 9），是纯 bug 而非设计缺口。

**2. `pytest-randomly` 未安装——顺序不变性无自动保障**
~~README 曾声称测试套件启用了该插件，实际系统 Python 与 `.venv` 里都没装，
项目也没有 `requirements.txt` / `pyproject.toml` 声明它。~~
**已解决**（2026-09-27）：用户装入 `.venv`，`requirements.txt` 已补，
15 个 seed 下均为 737 passed / 1 skipped（本次实测）。顺序不变性**现在有
自动守卫**。`python` 与 `.venv/Scripts/python.exe` **都已装有**
pytest-randomly 5.0.0，两个解释器跑出来一致。

**3. §12 七实验零数字——架构有效性无证据**
见 §4.2。这是 Milestone 4/5 之后必须补的，否则项目无法回答「这到底有没有用」。
增量 2 之后，实验 6（安全自我修改）的前置已全部就绪，可以第一个跑；
实验 1 与实验 7 同批（前者只缺测量，后者只缺债务 9 那处判据修正）；
实验 2 / 3 要等债务 6b 的「可学的世界」。

**4. `retrieve` 键收窄——召回精度上限更低**
08 §4.1 写 `retrieve(p_t, h_{t-1})`，实现收窄为 `retrieve(p_t)`，理由是继承来的
记忆用 hidden 做键永远命中不了。代价已记录在 `SSEA/README.md` §4。
Milestone 4 若发现检索不够用，正确方向是换更强的键函数，不是把 hidden 加回去。

**5. 目标选择无语义——它是债务 6b 的成因之一，不只是「留待项」**
`manip_target` 对候选按索引顺序打分，候选不带可学特征。Milestone 3 之前做注意力
没有输入依据；现在记忆系统落地了，这个留待项有了前提。

**同日实测把它从「留待项」升格为债务 6b 的成因之一**，而且比原先描述的更硬：
`ActionDecoder._add_manipulation` 里是

```python
scores = self.manip_target(h).expand(len(candidates.object_ids))
target_idx = int(torch.argmax(scores))
```

`expand` 出来的张量**所有分量数值相等**，`argmax` 因此恒返回 0。也就是说
`manip_target` 这个头**结构上不可能影响选择**——永远取候选表第 0 个，
即距离最近的那个可见物体，与它的种类无关。这不是「打分不准」，是**打分被丢弃**。
再加上候选表按距离排序（`fast_loop._candidates`），当前行为精确地是
「抓最近的东西」。修它之前，任何「模型学会了选择目标」的说法都不成立。

**6. 睡眠期只恢复身体，不整理经验**
~~慢环钩子默认 `None`。这是刻意的，但它意味着当前「睡眠」在功能上只是疲劳恢复。~~
**已解决**（2026-09-27）：增量 2 的 `make_slow_loop_hook` 接上了 `SlowLoopHook`，
睡眠末尾真的会编译 → 过门 → 提交。剩下的 `DeathHook` 仍默认 `None`（死亡快照未接）。

**6b. 默认世界上没有可学的成功——成因是三层叠加，真约束是趋近能力**
增量 2 的端到端测试（`TestSleepActuallyCompiles`）靠一个手写策略才跑通，
原因是三件事叠在一起：默认 Action Decoder 随机初始化，从不 emit grasp；
而这个世界里**唯一的正能量来源就是 grasp 资源**（`resource_gain`，
且能量上限 1.0 而 agent 开局就满）。于是默认配置下慢环跑一万帧也编译不出
任何东西。

这不是编译器的缺陷——是世界还没给出可学的成功。但它是一条要紧的债务：
**在默认策略能产出可编译的成功段之前，「模型自己学会了」这句话没有证据。**

同日逐层实测把「默认策略不 emit grasp」**拆成了三层**，逐层解决后仍然不够：

| 层 | 现象 | 实测 |
|---|---|---|
| a 操纵门 | 与记忆门同一病理：随机初始化的门控值 ≈ 0.5，而阈值恰好 0.5 | 约一半 seed 门是关的 |
| b 动作选择 | `manip_op` 走随机 argmax | 560 帧里 **0 帧**选中 `grasp` |
| c 目标选择 | `manip_target(h).expand(n)` 分值全等，argmax 恒为 0（债务 5） | 恒选最近可见物体，无论种类 |

**三层全部手动打开后，8 个 seed 一共只成功 3 次 grasp，平均寿命 67 → 72 帧**
——依然不够。原因是编译需要 `min_frames=3` 的**连续正能量帧**，
而 3 次零散的抓取凑不出这样一段。

所以真约束不在操纵链上，而在**趋近能力**：位移是恒定的 ~0.245，
**方向不可控**。agent 靠近不了资源，grasp 再准也没用。

~~解药可能是 Plasticity Controller（增量 3），也可能是换一个非随机初始化的
默认解码器。~~ 增量 3 落地后确认：**不是这条债务的解药**。
`LocalPlasticity` 只动结构侧阈值（`memory_gate_threshold` /
`min_similarity`），而默认策略不 emit grasp 与阈值无关——
阈值决定「记不记」，不决定「抓不抓」。

**解药的形态（按 C8 推导，不是照业界的默认做法）**：把「趋近资源」做成
`instinct_adapters` 的**第一个消费者**。理由是分工——「趋近」是**本能**，
不是**知识**：本能可继承（合 C7），知识不可（C8 明令「给基因先验，不给知识语料」）。
给它一个可学参数头（`instinct_adapters` 已在 `DEFERRED_SCOPES` 中登记）
既是本能，又天然是「遗传来的初始倾向 + 可被 Δθ 局部修正」，两头都占。
反过来说，**手调一个更好的默认解码器是错的**——那是权重，不可继承，
也不受 C8 保护。

> **一个必须避开的分叉**：旧文稿写的备选解药是「让世界给出除 grasp 之外的正反馈」。
> 若实现成**奖励塑形**（给非生存信号加分），它会直接撞上 **C9（不设评分函数，
> 只有淘汰函数）**。世界只该给出**能量**这一种信号，其余都是生存本身的后果。

测试里脚本化策略、压低 `resource_gain`、资源簇零危险源
三项调整的理由记录在 [13-milestone4-plan.md](13-milestone4-plan.md) §5.4；
三层分解与 C8 推导见 [14](14-overview-and-roadmap.md) §6.3.2 与
[13](13-milestone4-plan.md) §6.6。

**7. `UPDATE_RETRIEVAL_POLICY` 曾写入下游读不懂的形状（已修）**
Milestone 1 的 `StructureStore._apply` 写 `nxt[target] = policy`，而 `retrieval`
实际是**一份扁平策略**（键即策略字段名），不是 name→policy 的映射。于是提交后
`retrieval` 变成 `{"default": {"top_k": 8}}`，`MemorySystem` 把整个映射交给
`validate_retrieval_policy`，读到未知键 `"default"` 直接 `ValueError`——
**快环在下一个 `WAKE` 上崩**。

这条 bug 在 Milestone 1–3 全程不可见，因为**没有任何机制真的去读提交后的
retrieval**：`test_structure_store.py` 只断言版本号递增，而构造 MemorySystem
的测试用的是手写的扁平 `retrieval`。它是被 Verification Gate 逼出来的——
第四级要把候选结构装配成快环跑一遍，畸形形状无处躲藏。

已修（`_apply` 改为 `nxt[target] = policy`，与 `UPDATE_THRESHOLD` 同形），
并加了两条回归钉子。**教训值得记下**：Store 只管版本号与审计，不保证下游读得懂；
这个洞要么由消费者侧的测试堵，要么由 Gate 这样的端到端检查堵。

**8. `action_decoder.py` 的 requires_grad UserWarning（不修，已判定无影响）**
`float(torch.sigmoid(self.loco_speed(h)))` 把 requires_grad 张量转标量，
torch 发 UserWarning（`tests/test_perception_encoder.py:167` 有同类）。
**判定：不影响开发，不修。** 理由：Action 边界**刻意不可微**
（`SSEA/README.md` §5.2），现有可微性测试都直接调内部头（`trunk` / `loco_speed`）
而不经 `forward`，包 `no_grad()` 不改变任何可观测行为。留着它，直到有人要给
Action 路径接梯度——那应该是 v0.4+ 的事，且要先回答「为什么需要一个可微的
动作边界」。

**9. 睡眠判据语义错误——三条判据算术互斥，睡眠永不可达（已定位，修法已备好）**
`MetabolicMonitor.wants_sleep()` 要求 `energy ≥ 0.7` **且** `fatigue ≥ 0.6`
**且** `threat ≤ 0.05`。前两条是一对**反向赛跑**：`fatigue_rate=0.02` 要 30 帧
才把疲劳推到 0.6，而 `base_drain=0.01` 在同样的 30 帧里（含移动则只用 20–25 帧）
就把能量压到 0.7 以下。不含移动时两者在第 30 帧附近擦肩，一旦有移动——
实际运行总有——能量侧提前到场，交集彻底空掉。实测 8 个 seed 全部 60 余帧死亡，
`sleeps=0`；536 帧全体扫描里**没有任何一帧同时满足三条**，三个条件的阻塞占比
42.6% / 31.3% / 26.0%。实测 `t=49` 时 `fatigue = 1.000` 而 `energy = 0.25`。

根因是**两条判据的语义被 `and` 串错了**：`energy ≥ 0.7` 属于**防御性整理**
（能量充裕，闲着也是闲着），`fatigue ≥ 0.6` 属于**生理必要性**（撑不住了）。
前者是「可以睡」，后者是「必须睡」——两者取交集得到空集。修法是保留
`safe ∧ fatigue ≥ 0.6`，去掉 `energy` 合取项。实测修正后 8/8 seed 可达，
11 次唤醒、6 条提案、6 条应用。

**为什么这是当前第一优先**：代价是几行代码、一处布尔结构，收益是解锁实验 7，
并让实验 2 / 3 的睡眠前置不再悬空。完整推导见
[14](14-overview-and-roadmap.md) §6.3.1 与 [13](13-milestone4-plan.md) §6.6。

> **归因提醒**：上述 6 条应用**全部是 `thresholds` 类型**（来自记忆门症状的 Δθ），
> **技能编译为 0**。所以这处修正只解锁了实验 7 的「触发」那一半；
> 「编译出东西」那一半仍卡在债务 6b。

**10. `Environment._event_notes()` 是 16 槽环形缓冲——用它做累计统计会静默出错**
`_emit_event` 里是 `del self._events[: -self.config.max_events]`，`_event_notes`
同形。也就是说事件与笔记**只保留最近 16 条**。任何「跑完一轮后读 `_event_notes`
统计总能量收益」的写法都会**丢掉早期事件**，把有 grasp 的回合读成 0。

这条不是理论风险：**本次实测真的踩了**——第一版探针报出
`total_ENERGY_GAINED = 0`，而逐帧 trace 显示 `t=10 ... grasp: +0.356 energy`。
改用包裹 `env._emit_event` 的累加计数器后数值才正确。

**为什么它是要紧的债务**：实验 2（危险回避率）与实验 3（能量消耗变化）
都需要跨整轮的累计量。若用 `_event_notes()` 直接统计，两者都会得到
**看起来合理但错误**的数字——而且是「偏向零」的方向，正好会把有效果的实验
读成没效果。**跑这两个实验前必须先建累计计数器**（[13](13-milestone4-plan.md)
§6.6 增量 4 候选第 2 项），或每帧即时累加。

**11. 一次性脚本误入提交（已补删除提交，历史留痕）**
用来核实文档论断的临时探针脚本被 `git add -A` 收进 `d32b148` 并推送。
因已推送，**只能补一个删除提交**（`82f7e30`），历史里留了痕——
这是刻意的取舍：改写已推送的历史代价更大。

已加 `.gitignore` 兜底（`probe*.py` / `*_tmp.py` / `scratch*.py`），
但**兜底不是解法**：正确做法是**把这类脚本写到仓库外**。
这几条模式只挡得住起名规矩的，挡不住随手起的名字。

---

## 7. 复现方式

```bash
# 全套测试（737 passed, 1 skipped）。
# python 与 .venv/Scripts/python.exe 都已装 pytest-randomly 5.0.0，两个解释器一致。
.venv/Scripts/python.exe -m pytest tests/ -q

# 单个模块
.venv/Scripts/python.exe -m pytest tests/test_experience_compiler.py -q  # 36 passed
.venv/Scripts/python.exe -m pytest tests/test_verification_gate.py -q   # 55 passed
.venv/Scripts/python.exe -m pytest tests/test_memory_system.py -q       # 87 passed
.venv/Scripts/python.exe -m pytest tests/test_skill_library.py -q       # 57 passed
.venv/Scripts/python.exe -m pytest tests/test_plasticity.py -q          # 50 passed

# 顺序不变性：15 个随机 seed 下都必须通过（不只默认顺序）
for i in $(seq 0 14); do
  .venv/Scripts/python.exe -m pytest tests/ -q --randomly-seed=$i
done
```

**跑一次真实闭环**（§4.1 那段输出的来源，需在仓库根目录执行）：

```python
import torch
from SSEA.environment import Environment
from SSEA.fast_loop import FastLoop, FastLoopConfig
from tests.conftest import make_context

torch.manual_seed(0)      # 必须固定：否则记忆门开不开是抽奖（见 §4.3）
env = Environment(seed=0)
loop = FastLoop(env, make_context(),
                config=FastLoopConfig(max_frames=60, min_sleep_frames=3))
loop.run(40)

print(len(loop.trace()), env.alive, round(env.energy, 4))
print(type(loop.memory).__name__)
print(loop.memory.stats)
```

> `torch.manual_seed(0)` 那一行不是可选的装饰。去掉它重跑几次，会看到
> `writes` 在 40 和 0 之间跳。

**跑一次慢环一步**（§4.1 那段慢环输出的来源）：

```python
from SSEA.experience_compiler import make_slow_loop_hook, run_slow_loop
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate
from tests.test_experience_compiler import successful_trace

store = StructureStore()
out = run_slow_loop(successful_trace(), store,
                    VerificationGate(GateConfig(env_frames=8)), timestamp=1.0)
print(out.applied, out.rejected, store.versions)
for r in store.audit_log():
    print(r.proposal_id, r.kind, f"{r.from_version}→{r.to_version}", r.gate_result)
```

**复现增量 3 的阈值自修正**（§4.1 那行 0.280 → 1.000 的来源）：

```python
import torch, statistics
from SSEA.environment import Environment
from SSEA.fast_loop import FastLoop, FastLoopConfig, STATE_RUN
from SSEA.metabolic_monitor import MetabolicMonitor
from SSEA.experience_compiler import make_slow_loop_hook
from SSEA.plasticity import LocalPlasticity
from SSEA.sse_protocols.structure_store import StructureStore
from SSEA.verification_gate import GateConfig, VerificationGate
from tests.conftest import make_context

def once_at(n):
    """只在第 n 次询问时同意睡眠一次——真实监控器不会每帧都同意。"""
    inner = MetabolicMonitor(sleep_energy_threshold=0.0,
                             sleep_threat_threshold=1.1, sleep_fatigue_threshold=0.0)
    fired, asked = [False], [0]
    class OnceAt:
        def drive_vector(self, body): return inner.drive_vector(body)
        def observe(self, obs): return inner.observe(obs)
        def wants_sleep(self, body, obs):
            asked[0] += 1
            if fired[0]: return False
            if asked[0] >= n and inner.wants_sleep(body, obs):
                fired[0] = True; return True
            return False
        def reset(self): inner.reset()
    return OnceAt()

def measure(seed, frames=25):
    torch.manual_seed(seed)
    store = StructureStore()
    hook = make_slow_loop_hook(store, VerificationGate(GateConfig(env_frames=8)),
                               plasticity=LocalPlasticity())
    loop = FastLoop(Environment(seed=seed), make_context(),
                    metabolic_monitor=once_at(frames),
                    config=FastLoopConfig(max_frames=4*frames, min_sleep_frames=3),
                    slow_loop=hook)
    loop.run(frames)
    pre = [r for r in loop.trace() if r.state == STATE_RUN]
    before = sum(1 for r in pre if r.decoded_action.memory is not None) / len(pre)
    while loop.alive and loop.state != STATE_RUN: loop.step()
    loop.run(frames)
    run = [r for r in loop.trace() if r.state == STATE_RUN]
    post = [r for r in run if r.context_fingerprint == run[-1].context_fingerprint]
    after = sum(1 for r in post if r.decoded_action.memory is not None) / len(post)
    return before, after, len(store.audit_log()), \
           store.snapshot().thresholds.get("memory_gate_threshold")

res = [measure(s) for s in range(8)]     # 0.280 → 1.000，6/8 提案，0.5 → 0.4
```

> 这里的 `once_at` 是**病理监控器**：它把睡眠同意条件压到只在第 25 帧成立一次。
> 换成默认 `MetabolicMonitor()` 重跑同一个 `measure`，8 个 seed 全部 `sleeps=0`、
> `proposals=0`、agent 在 60 余帧（65–70）死亡——**这条通路默认走不到**。
> 原因是判据算术互斥（债务 9），不是设计缺口：改成 `safe ∧ fatigue ≥ 0.6`
> 后 8/8 seed 可达。见 §4.3 保留 1 与 [14](14-overview-and-roadmap.md) §6.3.1。

---

## 附：本文档的判定口径

- 「已完成」= 交付物存在 **且** 有测试守住 **且** 该测试不是恒真断言。
- 「部分满足」= 机制通但缺消费者 / 缺触发器 / 缺实验数字。
- 「未开始」= 无实现。协议层先行不算实现（`GenePackage` 有字段但无 Gene Manager）。
- 本文档中的所有数字均在 2026-09-27 于本项目实测，非引自其他文档。
