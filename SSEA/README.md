# SSEA v0.3.1 —— Milestone 1 + 2 + 3 + 4（增量 1–3）：接口协议 + 快环 + 记忆与技能 + 验证门 + 经验编译器 + 可塑性

**状态**：Milestone 1、2、3 完成；Milestone 4 进行中（增量 1 验证门、增量 2
经验编译器、增量 3 可塑性已落地，执行计划见
[docs/13-milestone4-plan.md](docs/13-milestone4-plan.md)）。
上一里程碑（Milestone 0：架构冻结）的三份文档见
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
├── action_decoder.py              ← Milestone 2：intent_vector → Action（门控阈值来自结构快照）
├── skill_runner.py                ← Milestone 2：第 11 模块，逐帧展开技能
├── environment.py                 ← Milestone 2：最小 2D 世界 + 淘汰函数
├── fast_loop.py                   ← Milestone 2：闭环装配 + 睡眠期状态机
├── memory_system.py               ← Milestone 3：外部记忆（写入/检索/淘汰/合并/可继承）
├── skill_library.py               ← Milestone 3：技能编译 / 提案 / 淘汰 / 继承
├── verification_gate.py           ← Milestone 4 增量 1：四级安全检查（格式→沙盒→回归→环境）
├── experience_compiler.py         ← Milestone 4 增量 2：trace → 提案（ΔS）+ 慢环一步
└── plasticity.py                  ← Milestone 4 增量 3：allowed_scope 边界 + Δθ 提案

tests/
├── test_08_revisions.py          08 修订条款是否落地（55 项）
├── test_structure_store.py       结构注入面四条性质（32 项）
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
├── test_skill_library.py         编译判据 + 提案过门 + 端到端调用（57 项）
├── test_verification_gate.py     四级检查 + 顺序可观测 + 「Gate 不打分」（55 项）
├── test_experience_compiler.py   提案生产者 + 「不恒真」五种沉默 + 睡眠端到端（36 项）
└── test_plasticity.py            allowed_scope 边界 + 沉默 + 收敛 + 开门率提升（50 项）
```

★ = 07 中不存在、由 08 §2.1 新增的组件。

## 2. 运行

```bash
.venv/Scripts/python.exe -m pytest tests/ -q        # Windows：完整环境在这里
python -m pytest tests/ -q                          # 系统 Python 也可跑，环境已补齐
```

当前：**751 passed, 1 skipped**（skip 是 `StructureStore` 非 dataclass，
`test_annotations_resolve` 主动跳过，符合预期）。

**这个数字必须在任意测试顺序下都成立**。若干测试用 `torch.randn` 从全局 RNG
取数，而夹具是随机初始化的——顺序一变结论就翻。凡依赖随机门的断言（通道是否
开启、是否写入）一律按死门控或固定 seed，不断言抽奖结果。
`test_action_decoder.py::test_target_comes_from_candidates` 是这条纪律的一个
实例：它曾依赖夹具的随机初始化，顺序翻转时报"manipulation 通道从未开启，
测试无意义"。

`pytest-randomly` 已装好（见 [requirements.txt](../requirements.txt)），
顺序不变性**已有自动守卫**。每次改动后不只跑默认顺序，还要复跑多个 seed：

```bash
for i in $(seq 0 14); do
  .venv/Scripts/python.exe -m pytest tests/ -q --randomly-seed=$i
done
```

15 个 seed 下均为 751 passed / 1 skipped（Milestone 4 增量 3 落地时实测；
增量 2 收尾时 684，增量 1 收尾时 649）。这条纪律由
[docs/13-milestone4-plan.md](docs/13-milestone4-plan.md) §7 定下：
**此后每次改动都必须在这 15 个 seed 下复跑**，不只是默认顺序。

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

**一处形状偏差需记录（Milestone 4 增量 1 修正）**：`retrieval` 是**一份扁平
策略**——键就是策略字段名（`top_k` / `stride` / `types` / ...），不是
name→policy 的映射。因此 `UPDATE_RETRIEVAL_POLICY` 的 `target` 是策略键名、
`policy` 是它的新值，与 `UPDATE_THRESHOLD` 同形。

原先 `StructureStore._apply` 写的是 `nxt[target] = policy`（把整份策略塞进
`retrieval[target]`），于是提交后 `retrieval` 变成 `{"default": {"top_k": 8}}`，
而 `MemorySystem` 把整个映射交给 `validate_retrieval_policy`，读到未知键
`"default"` 直接 `ValueError`——**快环在下一个 `WAKE` 上崩**。

这条路是 Verification Gate 逼出来的：没有门的时候，没有任何机制会发现
「一条过审的提案会让闭环炸掉」。修正见 `structure_store.py::_apply`，
回归钉子见 `test_verification_gate.py::test_committed_retrieval_policy_is_readable_by_memory_system`
与 `test_structure_store.py::test_committed_retrieval_policy_is_readable_downstream`。

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
a_t = ActionDecoder(h_t, b_t.action_constraints, d_t, ctx.thresholds)   # 增量 3 新增末参数
u_t = SkillRunner(a_t, ctx.skills)                 # 技能执行中为子动作
o_{t+1}, f_t = Environment.step(u_t)
f_t.prediction_error = SurpriseEstimator.update(...)
MemorySystem.write(a_t.memory, p_t, o_{t+1}, f_t)  # Milestone 3 新增
```

`ctx.thresholds` 那一项是增量 3 落的地：门控阈值**住在结构快照里**，
于是改它要走「提案 → 验证门 → Structure Store → WAKE 换版」整条路，
而不必让慢环直接写 torch 参数（07 §16：模型不可绕过验证器应用修改）。
在此之前 `FastLoopContext.get_threshold()` 是一个**没有消费者的声明**——
改结构里的阈值对行为没有任何影响，而提案、Gate、Store 一路都是绿的。

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
| Experience Compiler | Milestone 4 | ~~无触发器。Gate 已就绪，等它产提案~~ **已实现**（增量 2，见 §11），但只覆盖 ΔS 一类 |
| Plasticity Controller / LocalPlasticity | Milestone 4 | 无 `allowed_scope` 的消费者 |
| RuleCompiler | Milestone 4 | 无触发器 |
| HeritableFilter | Milestone 4 | `MemoryItem.is_heritable()` 判据已实现并有测试，消费者未接线 |
| Gene Manager（save/load/mutate） | Milestone 4 | 协议只定义 `GenePackage` 字段 |
| 多智能体 / 语言指令 / 奖励函数 | v0.4+ | `Communication` 只回环，无接收方 |
| 结构演化（NEAT 式） | v0.4+ | `mutation_rate` 只作用于 adapter / 阈值 / 技能参数 |

**睡眠期现在真的整理经验了**（增量 2）：`SlowLoopHook` 由
`make_slow_loop_hook(store, gate)` 提供，睡眠末尾编译 → 过门 → 提交，
有应用则 `WAKE` 时换新快照，无应用则快环继续用旧的。
`DeathHook` 仍默认 `None`（死亡快照未接）。

**Verification Gate 已落地**（增量 1，见 §12）。它只回答「能不能安全应用」，
不回答「好不好」——后者是淘汰函数的职权。

**一条要紧的限制**：默认 Action Decoder 随机初始化，从不 emit grasp，
而这个世界里唯一的正能量来源就是 grasp 资源。所以**默认配置下慢环跑一万帧
也编译不出任何东西**——这不是编译器的缺陷，是世界还没给出可学的成功。
增量 2 的端到端测试因此脚本化了策略，理由记录在
[docs/13-milestone4-plan.md](docs/13-milestone4-plan.md) §5.4。

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

### Milestone 4（07 §11，进行中）

- [x] **修改可以验证** —— 增量 1，`test_verification_gate.py` 53 项
- [x] **模型可以从成功轨迹中生成技能** —— 增量 2，`TestCompilesRealTraces`；
      端到端见 `TestSleepActuallyCompiles`
- [x] **模型可以提出修改提案** —— 增量 2 的 ΔS（`ADD_SKILL`）+ 增量 3 的 Δθ
      （`UPDATE_THRESHOLD` / `UPDATE_RETRIEVAL_POLICY`）。四类 Δ 里 ΔR / ΔM
      尚未实现（各有归属增量，见 13 §3）
- [x] **修改可以回滚** —— 天然回滚：`test_no_rollback_api_exists`。被拒的提案
      从未被应用，没有东西需要回滚
- [x] **参数可以在边界内被修改** —— 增量 3，`allowed_scope` 是白名单；
      07 §6.7 不可更新清单先于它匹配。**仅结构侧**，参数侧整个推迟
      （见 `plasticity.DEFERRED_SCOPES`）
- [ ] 基因保存 / 恢复 / 变异 —— Gene Manager，未开始

---

## 10. 下一步（Milestone 4）

慢环本体剩余：RuleCompiler、HeritableFilter、Gene Manager，
以及 `DeathHook` 的接线（死亡快照）。Milestone 3 已把它们要消费的产物（trace、
提案、可继承判据、统计回写）全部备齐。

执行顺序见 [docs/13-milestone4-plan.md](docs/13-milestone4-plan.md) §3：
Verification Gate（✅ 增量 1）→ Experience Compiler（✅ 增量 2）→
Plasticity Controller + LocalPlasticity（✅ 增量 3）→ RuleCompiler →
HeritableFilter → Gene Manager。

**§12 实验 6（安全自我修改）的前置现已全部就绪**——Gate 产 `GateResult`，
编译器与可塑性产提案，Store 提交或拒。它是六个实验里第一个可以开跑的。

**§12 实验 2（记忆召回）现在有了第二个对照组**：`ZeroMemoryRetriever` 是
"把记忆关掉"那一格，而增量 3 修好的"门本来就不开"是"记忆从未被打开"那一格。
两格的差别现在可测。

---

## 11. Milestone 4 增量 2 的三个关键设计决策

### 11.1 编译、验证、应用是三个不同的问题，所以分在三个类里

```
编译器决定「提什么」 → Gate 决定「能不能安全应用」 → Store 决定「应用不应用」
```

`ExperienceCompiler.compile()` 只返回提案，不碰 Store、不碰 Gate。
把三者捏在一起，就没法单独回答「提得对不对」——而那正是慢环最该被测的部分。
`run_slow_loop` 把三者接成一步，`make_slow_loop_hook` 再把它包成快环的钩子。

**不评估提案好不好**：与 Gate 同一条 C9 纪律。编译器按**世界计价物**
（净能量）决定提不提，不按任何内部偏好排序。07 §6.6 把「成功/失败结果」
列为输入，而 SSEA 里成功的判据只有一个：净能量收益为正。不用奖励函数。

**不自己发明 Δ**：ΔS 复用 `skill_library.compile_skills` 那一份切分规则
（为此把它提成了模块级纯函数）。两份规则必然漂移，而漂移的表现是「同一条轨迹
编译出两条语义相同的技能」——那种不一致在运行时报错里看不见，
只会在审计日志里表现为重复提案。

### 11.2 「不恒真」与沉默必须留原因

一个恒真的编译器——不管 trace 是什么都提同样的提案——能让整条慢环链看起来
在工作，而实际上什么也没学到：它只是把一个常数搬过了验证门。
测试用五种独立的方式证它会沉默（空 trace / 负收益 trace / 子动作帧 /
同一条 trace 第二次 / 不同 trace 必须给不同提案）。

沉默必须**可观测**：`CompileResult` 把 `proposals` 与 `skipped` 分开，
后者形如 `(skill_id, 原因)`。审计日志要能回答「我们看到了一条可编译的成功
轨迹，为什么没提案」——只有 proposals 的话，那次沉默与「什么都没看到」
在日志里不可区分。

07 §6.6 列的四类 Δ 只实现 ΔS。其余三类各有归属增量，以 `DEFERRED_DELTAS`
常量声明并由 `TestDeferredDeltas` 守着，**不写返回空 tuple 的占位方法**——
一个永远为空的函数就是死代码，「协议不容无消费者的通道」这条纪律对函数同样成立。

### 11.3 proposal_id 由内容导出，不由调用次数导出

`proposal_id = f"{prefix}-{skill_id}"`。计数器式的 id（`exp-000001`）也能唯一，
但代价是 `compile()` 不再是纯函数——同一条 trace 两次编译得到两个不同的 id，
于是「这是重复提案」要一次集合运算才能回答，且 Gate 的可复现性缺了上游一半。

内容导出的 id 让重复提案**看起来就是重复的**，审计日志里也一眼能看出
这条提案是关于哪条技能的，不必翻 payload。

---

## 12. Milestone 4 增量 1 的三个关键设计决策

### 12.1 Gate 不打分，只判合法性

SSEA 没有评分函数，只有淘汰函数（C9）。Gate 一旦开始给提案打分、按分数排序、
只放高分的过，它就变成了一个评分函数——而那正是 SSEA 立场要拒绝的东西。
Gate 的回答是二值的：合法 / 不合法。

推论：**两个提案一个让存活帧数翻倍、一个让存活帧数减半，只要两者都合法，
Gate 对它们一视同仁。** 选择权不在 Gate，在淘汰函数——活下来的那个自然被保留，
死掉的自然被淘汰。这是 07 §4.6「自我修改必须经过验证」与 C9 的接缝。

这条纪律由 `test_verification_gate.py::TestNoScoring` 守着：断言
`GateResult` 的字段集合恰为 `("passed", "reason", "stage_failed")`，
且 `VerificationGate` 上没有 score / rank / sort / compare / best 任何公开成员。

### 12.2 四级检查的顺序是代价递增，不可换

```
格式 → 沙盒 → 回归 → 小范围环境测试
```

格式错是纸面错误，沙盒错会污染结构，回归错会弄坏别的类别，环境错要跑闭环。
先做便宜的。任一级失败即停，`stage_failed` 记下失败的那一级——
**同时触犯多级时报最早那一级**，这条由 `TestStageOrder` 守着。

沙盒与回归的分工：沙盒查**这一个提案引入的**问题（「新东西合法吗」），
回归查**它有没有弄坏别的**（「旧东西还活着吗」）。后者逐个类别复查，
代价是 O(类别数)，可以忽略。

### 12.3 Gate 不碰权重、不执行代码、不做回滚

**不碰权重**：`UPDATE_ADAPTER` 改的是快照里的 adapter 配置（第一阶段是
`bytes` 权重片段），不是 torch 参数。参数更新走 LocalPlasticity（增量 3），
那条路有 07 §6.7 的不可更新对象清单管着。

**不执行任意代码**：08 §3.1 已把 ΔC 折叠进 ΔS，第一阶段没有代码执行。
所以「沙盒」不是代码沙盒，是**结构副本上的不变量检查**。若将来真的开放代码段，
这一级要重做，且必须先回答「谁有权执行」——那是 v0.4+ 的问题。

**不做回滚**：`StructureStore` 上没有 rollback 方法——被拒的提案从未被应用，
没有东西需要回滚。Gate 的拒绝只是让 `commit()` 记一条 `applied=False`。

---

## 13. Milestone 4 增量 3 的四个关键设计决策

### 13.1 边界是白名单，且禁止清单先于它匹配

07 §6.7 只给了两张清单——可更新对象与不可更新对象——没有说"谁来判定越界"。
`PlasticityController.allows(kind, target)` 把两张清单变成一次判定，
且**先查 `NON_UPDATABLE` 再查 `kinds` / `bounds`**。

顺序是刻意的：若先查白名单，将来有人把一个禁止项登记进 `bounds`
（`{"core_weights": (0,1)}` 这种），禁止清单会被白名单悄悄盖掉——而那正好是
07 §16 要防的事。`TestScopeBoundary` 用一个"类别合法、键名恰好是禁止项"的
scope 钉住这个顺序。

键名不在本模块另列一份：门控阈值取自 `action_decoder.GATE_THRESHOLD_KEYS`
（语义所有者），检索策略取自 `memory_system.DEFAULT_RETRIEVAL_POLICY`。
两份清单必然漂移，而漂移会让一个拼错的键名通过格式级、在运行时才炸。

**下界不取 0**：阈值为 0 时门控恒开，`min_similarity` 为 0 时恒命中。
两个都是"机制被关掉"而不是"机制取默认值"。

### 13.2 参数侧 Δθ 整个推迟，因为它会造出一个假的安全保证

第一阶段的 Δθ 是**结构侧**阈值：`thresholds` 与 `retrieval` 里的若干键。
它们住在 `FastLoopContext` 里，于是改它必须走「提案 → 验证门 → Structure Store →
WAKE 换版」——每一次变动都是一次可审计的版本切换。

torch 参数侧整个不动，三条理由（完整版见 `plasticity.py` 模块 docstring）：

1. 07 §16「模型不可绕过验证器应用修改」——不过门违背此条；
2. 过门这条路在第一阶段是**空的**：Gate 四级检查全在 `FastLoopContext` 上，
   第四级装配的是一个**全新的** ActionDecoder，权重增量递进去它看不见，
   于是"四级检查全部通过"在参数上什么也没检验；
3. 把权重增量塞进 `UPDATE_ADAPTER` 的 bytes 能让它"看起来过了门"，
   而 `_check_adapters` 只查"是非空 bytes"——**那比不过门更糟**，
   它让文档可以写「自我修改经过验证门」，而实际上验证了什么并不知道。

所以参数侧以 `DEFERRED_SCOPES` 常量声明并由测试守着，**不写返回空 tuple 的
占位方法**。落地顺序是三步可见的工程：先给 `adapters` 补模型侧消费者
（现在它写得进、过得门、传得下、**却没有消费者**），再让 Gate 第四级能装候选权重，
然后才谈参数侧 Δθ。

### 13.3 证据只看当前版本，否则规则会撞到夹子

慢环拿到的 trace 是**整条 episode**，横跨多个结构版本。Δθ 的判定因此只取末帧
`context_fingerprint` 那段（`_current_window`）——换版前那些帧上的"门没开"是
**旧策略的账**。

不切这一刀的后果实测过（seed 2）：三轮睡眠把 `memory_gate_threshold` 从 0.5 推到
0.4 → 0.3 → 0.15（下界），而第二、三轮的触发证据全部来自第一轮之前。
**那不是收敛到合适的阈值，是撞到夹子。** 切了窗口之后同一轨迹只提一次，
且换版后新窗口里 `missed_surprise == 0`，于是沉默。

`context_fingerprint` 的文档原本只写"行为改变的归因依据"——这里是它的第一个
消费者。指纹为空（`versions={}`）时退化成整条 trace：没有版本信息就没有归因
可言，此时的行为与不切窗口一致，而不是抛异常。

### 13.4 提升是真的，但别把 1.00 读成学会了选择性

8 个 seed、各 25 帧、睡一次、再看 25 帧：

| | 换版前开门率 | 换版后开门率 | 提案数 |
|---|---|---|---|
| 均值 | 0.280 | 1.000 | 6/8 提案，2/8 沉默 |

**该沉默的种子保持沉默**（seed 0、1 本来就能开门，一条提案都没有）——
这条比提升本身更重要：若它红，说明规则恒真，那么提升可能只是乱改撞对了。

但 0.28 → 1.00 这么大，主要是因为随机初始化的门控值几乎恒定在 0.5 附近
（240 个采样：min 0.463、中位数 0.487、max 0.530），阈值 0.5 恰好切在正中间，
于是大约一半的种子门恒闭。**一个全局阈值是钝器。**

更强的断言——**选择性**（惊奇帧开门、平淡帧关门）——没有做到，且用一个全局阈值
**做不到**。那需要参数侧 Δθ，也就是 13.2 里被整个推迟的那一半。
所以本增量的正确说法是：**「门控不开」这个故障被修好了，而「门开得准不准」
是下一步的事。**
