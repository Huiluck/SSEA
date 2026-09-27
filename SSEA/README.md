# SSEA v0.3.1 —— Milestone 1 + 2 + 3：接口协议层 + 快环骨架 + 记忆与技能

**状态**：Milestone 1、2、3 完成。上一里程碑（Milestone 0：架构冻结）的三份文档见
[docs/09](docs/09-architecture-originality.md)、[docs/10](docs/10-boundary-definition-table.md)、
[docs/11](docs/11-phase1-not-doing-list.md)。

**实现依据**：[docs/07-ssea-v0.3.1-charter.md](docs/07-ssea-v0.3.1-charter.md) 第 8 节
（协议原文）+ [docs/08-dual-loop-interface-and-gap-closure.md](docs/08-dual-loop-interface-and-gap-closure.md)
第 5 节修订条款汇总表（19 条）。**凡 08 修订过的协议，以 08 为准，不以 07 原文为准。**

---

## 1. 目录结构

```
SSEA/
├── sse_protocols/                  ← Milestone 1：协议层（零 ML 依赖）
│   ├── action_constraints.py     8.3  约束 + 强制执行规则（双执行点共用）
│   ├── action_space.py           8.4  动作空间声明（已删 latent 块）
│   ├── action.py                 8.5  混合动作（已删 latent_action）
│   ├── body_state.py             8.2  身体状态
│   ├── observation.py            8.1  观测
│   ├── object_vector.py          8.6  感知对象向量
│   ├── event_vector.py           8.7  事件向量
│   ├── communication_signal.py   8.8  通信信号（第一阶段只预留）
│   ├── environment_summary.py    05 §7.3  环境摘要
│   ├── feedback.py               8.9  环境反馈
│   ├── memory.py                 8.10 记忆项 + 可继承性判定
│   ├── skill.py                  8.11 技能 + 内化判定
│   ├── self_modification.py      8.12 自我修改提案 + origin
│   ├── gene.py                   8.13 基因包
│   ├── structure_store.py        ★ 版本化结构仓库
│   ├── fast_loop_context.py      ★ 不可变快照
│   └── serialization.py          ★ JSON 往返
│
├── tensorize.py                   ← Milestone 2：协议 → 张量的唯一边界
├── surprise_estimator.py          ← Milestone 2：一阶持久化预测（Metabolic Monitor 子组件）
├── metabolic_monitor.py           ← Milestone 2：internal_drive_vector + 睡眠判定
├── perception_encoder.py          ← Milestone 2：观测 → perception_vector
├── state_core.py                  ← Milestone 2：GRU（L1 算子，不构成架构声明）
├── action_decoder.py              ← Milestone 2：intent_vector → Action
├── skill_runner.py                ← Milestone 2：第 11 模块，逐帧展开技能
├── environment.py                 ← Milestone 2：最小 2D 世界 + 淘汰函数
├── fast_loop.py                   ← Milestone 2：闭环装配 + 睡眠期状态机
├── memory_system.py               ← Milestone 3：外部记忆（写入/检索/淘汰/合并/可继承）
└── skill_library.py               ← Milestone 3：技能编译 / 提案 / 淘汰 / 继承

tests/
├── test_08_revisions.py          08 修订条款是否落地（55 项）
├── test_structure_store.py       结构注入面四条性质（31 项）
├── test_protocol_consistency.py  协议自洽性 / 无自然语言 / 无模型依赖（41 项）
├── test_serialization.py         Milestone 1 三条验收（59 项）
├── test_tensorize.py             协议↔张量边界（10 项）
├── test_surprise_estimator.py    prediction_error 生产者（16 项）
├── test_metabolic_monitor.py     驱动向量接线 + 睡眠判定（17 项）
├── test_perception_encoder.py    特征打包 + 对象选择（19 项）
├── test_state_core.py            GRU 形状 / 递归 / 确定性（17 项）
├── test_action_decoder.py        约束第一执行点 + 通道门控（29 项）
├── test_skill_runner.py          逐帧展开 + 三条中止条件（42 项）
├── test_environment.py           约束第二执行点 + 淘汰函数（62 项）
├── test_fast_loop.py             闭环 + 状态机 + 注入面（54 项）
├── test_memory_system.py         07 §6.4 五项 + 策略校验 + 可继承（87 项）
└── test_skill_library.py         编译判据 + 提案过门 + 端到端调用（57 项）
```

★ = 07 中不存在、由 08 §2.1 新增的组件。

## 2. 运行

```bash
python -m pytest tests/ -q
```

当前：**595 passed, 1 skipped**（skip 是 `StructureStore` 非 dataclass，
`test_annotations_resolve` 主动跳过，符合预期）。

**这个数字必须在任意测试顺序下都成立**。若干测试用 `torch.randn` 从全局 RNG
取数，而夹具是随机初始化的——顺序一变结论就翻。凡依赖随机门的断言（通道是否
开启、是否写入）一律按死门控或固定 seed，不断言抽奖结果。
`test_action_decoder.py::test_target_comes_from_candidates` 是这条纪律的一个
实例：它曾依赖夹具的随机初始化，顺序翻转时报"manipulation 通道从未开启，
测试无意义"。

**注意：`pytest-randomly` 当前未安装**（系统 Python 与 `.venv` 里都没有），
所以上述顺序不变性**没有被自动执行**。装上它即可回归验证：

```bash
pip install pytest-randomly
python -m pytest tests/ -q --randomly-seed=0
```

协议层**只依赖标准库**，不 import torch / numpy——这是 Milestone 1
验收第 2 条「所有接口不依赖具体模型实现」的直接保证，
由 `test_serialization.py::TestNoModelDependency` 守着。
模型层（`tensorize.py` 及以后）依赖 torch，由反向守卫
`test_model_layer_does_import_torch` 确认这条边界没被抹平。

---

## 3. 三个关键设计决策（Milestone 1）

### 3.1 协议用 frozen dataclass，不用裸 dict

07 第 8 节用 dict 记法描述协议。dict 无法阻止字段拼写错误，也无法执行
「动作必须可执行」（08 §2.4）这类明文约束。dataclass 让协议可被验证，
也让 Milestone 2 的模型代码有确定签名。

代价：字段增删要同步改 `EXPECTED_FIELDS`（test_protocol_consistency.py）。
这是故意的——协议变更应当是显式的、会被测试抓到的动作。

### 3.2 Structure Store / FastLoopContext 是双环之间的唯一接口

慢环不调用快环。慢环只发布结构的新版本，快环只读当前版本：

```
Verification Gate → Structure Store（版本化） → FastLoopContext（不可变） → 快环
```

四条性质是**结构事实**，不依赖调用方自觉：

| 性质 | 由什么保证 | 测试 |
|---|---|---|
| 快环零改动 | 快照与 Store 脱钩，快环只读快照 | `test_snapshot_does_not_change_after_later_commit` |
| 失败天然回滚 | Gate 不通过则版本号不切换；**不存在 rollback 方法** | `test_no_rollback_api_exists` |
| 可遗传 | 快照字段即 GenePackage 三字段来源 | `test_snapshot_fields_feed_gene_package` |
| 可审计 | 每次提交记 `(proposal_id, from_v, to_v, gate_result, timestamp)` | `test_audit_record_fields` |

「失败天然回滚」值得单独说：`StructureStore` 上**没有** rollback / revert /
undo / restore 方法，这不是遗漏。被驳回的提案从未被应用，所以没有东西需要回滚——
安全性来自架构形态（版本隔离），不来自外部事务（07 §4.6）。

### 3.3 序列化是类型导向的

`to_json_dict` 与 `from_json_dict` 使用同一份类型信息。原因是协议里有**无类型
容器**（`SelfModificationProposal.payload`、Structure Store 的 `rules` /
`retrieval`），里面可能装着 `Skill`。故：有类型标注处用简洁形式，无类型容器内
的 dataclass 带 `__dataclass__` 标记。顶层无标记，JSON 干净。

## 4. 与 07 的差异清单

全部来自 08 的修订条款，逐条对应 08 第 5 节汇总表：

| 协议 | 修订 |
|---|---|
| `Action` | 删 `latent_action`；新增「动作必须可执行」`is_executable()` |
| `ActionSpace` | 删 `latent` 块 |
| `ActionConstraints` | 新增 `violations()` / `permits()`，双执行点共用 |
| `Feedback` | `prediction_error` 生产者 = SurpriseEstimator（已实现） |
| `MemoryItem` | 新增 `is_heritable()` / `is_transient` |
| `Skill` | `precondition` 检查方 = Skill Runner；新增 `is_consolidatable()` |
| `SelfModificationProposal` | 新增 `origin`；代码段只走 `ADD_SKILL`/`UPDATE_SKILL` |
| `GenePackage` | 新增 `heritable_memory`；`memory_index` → `memory_store_ref`；`mutation_rate` 作用范围限定 |

**一处结构偏差需记录**：08 §7 的文件清单把 `ActionConstraints` 的实现列在
`body_state.py` 下；实际拆为独立的 `action_constraints.py`，因为 07 §8.3
本就是独立一节，且强制执行规则应由定义约束的协议自己持有。
`body_state.py` 通过 import 使用它，行为一致。

**一处公式偏差需记录**：08 §4.1 的检索公式写
`MemorySystem.retrieve(p_t, h_{t-1})`，实现**收窄为 `retrieve(p_t)`**——
`h_{t-1}` 不进检索键，但仍进 State Core。理由是可继承性（C7）：

> 可继承记忆（RULE / SKILL）要复制进子代，而子代的 hidden 分布与父代不同。
> 用 hidden 做键，继承来的记忆永远命中不了——那等于把一个永远为空的
> 死字段传给了下一代。

这与 08 §2.4 从 `Action` 里删掉 `latent_action` 是同一条理由。完整推导见
`memory_system.py` 模块 docstring 第 3 条。

---

## 5. Milestone 2 的四个关键设计决策

### 5.1 协议 → 张量的转换只发生在一个地方

`tensorize.py::as_vector` 是唯一的协议↔张量边界。它**只做类型转换**：
不收归一化、不裁剪、不 detach。

不收归一化是立场：`internal_drive` 里的 `energy_deficit` 是有量纲的
生存信号，压到 [0,1] 会让「能量差 0.1」和「损伤差 0.1」变得不可比。
裁剪是 Action Decoder 的职责（第一执行点），不是边界的职责。
不 detach 是功能需要：`StateCore` 与 `ActionDecoder` 的内部头必须可微，
局部可塑性的作用点在那里。

### 5.2 Action 边界刻意不可微

两件事合起来的结果，不是疏漏：

1. **协议约定 2**：`Action` 的向量是 `tuple[float, ...]`，不是 torch 张量
2. **通道门控是硬阈值比较**（`sigmoid >= threshold`），不是可微稀疏化

故 `ActionDecoder.forward` 返回的 Action 不携带计算图。SSEA **不走
「反向传播穿过动作」这条路**——那需要一个可微环境，而 SSEA 的环境是
淘汰函数，不是损失函数（C9）。学习发生在慢环的 LocalPlasticity 与
基因变异上（08 §4.2 的 `Δθ`）。

**内部头仍然可微**：`trunk` / `gates` / 各通道头都是标准 `nn.Module`。
`test_action_decoder.py::TestTrainability` 守住的正是这条——若有人把某个头
改成纯 Python 运算，局部可塑性就失去了作用点，而这件事不会在任何运行时
报错里显现。

### 5.3 约束强制执行有两个执行点，共用同一份规则

| 执行点 | 位置 | 职责 |
|---|---|---|
| 第一 | Action Decoder（模型内） | 生成阶段就不越界：连续量按上限缩放，离散量从候选 argmax，布尔门读 `can_*` |
| 第二 | Environment（防御性） | 兜住漏网的：记 `ACTION_FAILED` 事件 + `action_success=False`，**不崩溃** |

两处共用 `ActionConstraints.violations()` 定义的同一份规则。

第二执行点必须存在的理由：Skill Runner 吐出的子动作序列跨越多个步长，
期间 `action_constraints` 可能变化（如 `energy_budget` 随能量下降而收缩）。
第一执行点裁剪的是**它当时看到的**约束。且兜住的方式是记事件而非抛异常——
崩溃会让 episode 中断，而 episode 中断在生存式架构里等于一次真实的死亡，
代价不对等。

`Feedback.action_success` 与 `ACTION_FAILED` 事件必须是同一个判断：前者是
Skill Runner 的中止判据（`ABORT_ENV`），后者是慢环的检索依据。两者若各说各话，
一个技能会在「明明抓空了」的情况下跑完整个 `action_sequence`。
`test_environment.py::test_action_success_agrees_with_event_log` 守着这条。

### 5.4 淘汰函数的判定权在环境，模型物理上碰不到它

死亡 = `energy <= 0` 或 `damage >= max_damage`，由 `Environment` 判定。
若判定权在模型侧，模型就能通过修改自身参数来避免死亡——那 SSEA 的
「生存压力」就退化成一个可被 hack 的评分函数（违背 C9）。

放在环境里之后，安全约束「模型不可修改淘汰函数」**天然成立**：它在模型
之外。`Environment.step` 在 `alive=False` 时抛 `RuntimeError`，淘汰是终态，
唯一出路是 `reset()` 开新 episode。

---

## 6. Milestone 3 的三个关键设计决策

### 6.1 记忆只按感知键检索，不按 hidden 键

见第 4 节的公式偏差记录。这条决策的直接后果是 `MemorySystem` **不需要**
State Core 的句柄——它可以被单独测试、被不同架构的 State Core 使用，
也让子代继承记忆时不改一行代码。

代价：检索键的信息量比 `(p_t, h_{t-1})` 小，召回精度上限更低。这是
**可继承性换来的精度**，不是疏漏。Milestone 4 若发现需要更强的检索，
正确的扩展方向是换更强的键函数，而不是把 hidden 加回去。

### 6.2 写入通道有第二执行点，且三种「不写」的原因可区分

| 原因 | 位置 | 测试 |
|---|---|---|
| 门控没开 | Action Decoder | `test_fast_loop.py`（`Action.memory is None`） |
| 约束禁止 | `constraints.can_store_memory` | `test_action_decoder.py::test_disabled_constraint_blocks_channel` |
| 系统不可写 | `MemorySystem.writable=False` | `test_memory_system.py::TestWrite` |

第三种是记忆自己的防御点。若 `MemorySystem` 只提供 `write()` 而不可拒绝，
一个被环境判为「此刻不可写」的记忆系统就没有表达方式——只能靠调用方自觉，
而自觉不是架构保证。

三种情况在 `stats` 里分开计数，不相加：`writes` 只记**成功写入**，
`refused` 只记 `writable=False` 的拒绝，门控没开则两者都不动（那一次调用
根本没发生）。所以「没写」与「写了没读到」不会混为一谈——后者是
`stats.misses` 的领域，只计检索未命中。

### 6.3 技能的 `energy_cost` 是每帧毛成本，不是净收益

编译只收净收益为正的段（`_is_direct_success`）。若此时把 `energy_cost`
取成净收益，每条编译出来的技能成本都恒为 0——一个永远为 0 的字段就是
死字段。Skill Runner 的中止判据要的是"这条技能每帧烧多少"，所以取
**各帧能量损失的均值**（净收益为正的帧计 0）。见
`skill_library.py::_gross_per_frame_cost`。

---

## 7. 快环运行公式（08 §4.1，逐行对应 `fast_loop.py::_step_run`）

```
p_t = PerceptionEncoder(o_t, b_t)
m_t = MemorySystem.retrieve(p_t)                   # 受 retrieval_policy 约束，非每步全量检索
h_t = StateCore(p_t, m_t, b_t, d_t, h_{t-1})       # d_t = internal_drive_vector
a_t = ActionDecoder(h_t, b_t.action_constraints, d_t)
u_t = SkillRunner(a_t, ctx.skills)                 # 技能执行中为子动作
o_{t+1}, f_t = Environment.step(u_t)
f_t.prediction_error = SurpriseEstimator.update(...)
MemorySystem.write(a_t.memory, p_t, o_{t+1}, f_t)  # Milestone 3 新增
```

状态机（08 §2.2 睡眠期是一等公民状态）：

```
RUN ──代谢判定──► SLEEP ──满 min_sleep_frames──► WAKE ──应用新快照──► RUN
 │                                                                    ▲
 └──────────────── 环境判定死亡 ──► DEAD（终态，不可撤销）
```

`m_t` 现在是 `MemorySystem.retrieve()` 的真实产物。无命中时它返回零向量——
与 `ZeroMemoryRetriever` 的输出**数值上不可区分**。这不是偷懒：诚实的空在
占位实现和真实实现上必须表现一致，否则「有记忆」与「没记忆」无法分辨。
`ZeroMemoryRetriever` 保留为消融对照组，不是默认值。

---

## 8. 明确不在本里程碑的内容

按 [docs/11](docs/11-phase1-not-doing-list.md) 的执行机制，以下各项**未实现**：

| 未实现 | 属于 | 现状 |
|---|---|---|
| Experience Compiler / Plasticity Controller / Verification Gate | Milestone 4 | 只有 `SlowLoopHook` / `DeathHook` 两个接口 |
| RuleCompiler | Milestone 4 | 无触发器 |
| HeritableFilter | Milestone 4 | `MemoryItem.is_heritable()` 判据已实现并有测试，消费者未接线 |
| Gene Manager（save/load/mutate） | Milestone 4 | 协议只定义 `GenePackage` 字段 |
| 多智能体 / 语言指令 / 奖励函数 | v0.4+ | `Communication` 只回环，无接收方 |
| 结构演化（NEAT 式） | v0.4+ | `mutation_rate` 只作用于 adapter / 阈值 / 技能参数 |

**睡眠期当前只恢复身体，不整理经验**——慢环钩子存在但默认 `None`。
这是 Milestone 3 与 Milestone 4 之间的刻意留白，不是遗漏。

---

## 9. 里程碑验收对照

### Milestone 1（07 §11）

- [x] **所有接口可序列化为 JSON** —— `test_serialization.py`，14 个协议全部往返保真
- [x] **所有接口不依赖具体模型实现** —— `TestNoModelDependency`，协议层零 ML 库导入
- [x] **环境不接受自然语言命令** —— `TestNoNaturalLanguageInLoop` + `Action` 无命令字段

### Milestone 2（07 §11）

- [x] **`Observation → perception_vector → hidden_state → Action` 闭环可运行**
  —— `test_fast_loop.py::TestClosedLoopRuns`，含 120 帧连续运行不崩溃
- [x] **睡眠期状态机** —— `RUN → SLEEP → WAKE → RUN` 四态，`TestSleepStateMachine`
- [x] **死亡快照触发器** —— `TestDeathSnapshot`，`on_death` 钩子收到终帧 trace 与末帧观测
- [x] **约束双执行点** —— 第一执行点 `TestOutputAlwaysLegal`，第二执行点 `TestSecondEnforcementPoint`
- [x] **`prediction_error` 有生产者** —— `SurpriseEstimator`，`TestPredictionErrorProducer`
      并确认**环境不生产它**（默认 0.0）
- [x] **技能可执行** —— Skill Runner 逐帧展开，三条中止条件可区分
- [x] **世界可生存** —— `test_greedy_policy_survives`：手写贪心策略在 60 帧内存活。
      这条不是性能指标，是**下界证明**——若连贪心策略都活不下来，Milestone 4
      的学习就没有可学的东西。

### Milestone 3（07 §11）

- [x] **模型可以写入记忆** —— `test_memory_system.py::TestWrite`，六条通道门控 /
      `store=False` / `writable=False` 三种「不写」的原因在 `stats` 里分开计数
- [x] **模型可以检索记忆** —— `TestRetrieve`，余弦相似度 + 槽位布局 + stride 缓存；
      无命中时是诚实的空
- [x] **模型可以保存技能** —— `test_skill_library.py::TestEndToEnd`，轨迹进 → 提案 →
      过门 → 新快照出 → 快环真的调用它
- [x] **模型可以调用技能** —— Milestone 2 的 Skill Runner（`test_fast_loop.py::
      TestSkillIntegration`）；Milestone 3 补上「调用的技能从哪来」

另覆盖 07 §6.4 / §6.5 的五项 + 来源：

| 07 要求 | 落点 |
|---|---|
| 记忆：写入 / 向量检索 / 重要度排序 / 容量限制 / 记忆合并 | `TestWrite` / `TestRetrieve` / `TestOrdering` / `TestCapacity` / `TestMerge` |
| 技能四来源：成功轨迹 / 模型生成代码 / 慢环编译 / 遗传继承 | 成功轨迹 → `compile_from_trace`；代码 → `ADD_SKILL`（08 §3.1，ΔC 折叠）；遗传 → `TestAdopt` |

---

## 10. 下一步（Milestone 4）

慢环本体：Experience Compiler、RuleCompiler、Plasticity Controller、
Verification Gate、Gene Manager，以及 `MemoryItem.is_heritable()` 的消费者
HeritableFilter。Milestone 3 已把它们要消费的产物（trace、提案、可继承判据、
统计回写）全部备齐，缺的是把 `SLEEP` 末尾的钩子从 `None` 换成真的实现。
