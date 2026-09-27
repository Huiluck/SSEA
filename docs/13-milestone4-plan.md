# Milestone 4 执行计划

**日期**：2026-09-27
**上游依据**：[07-ssea-v0.3.1-charter.md](07-ssea-v0.3.1-charter.md) §6.6–6.10、§11、
[08-dual-loop-interface-and-gap-closure.md](08-dual-loop-interface-and-gap-closure.md) §2.1/§4.2
**进度基线**：[12-progress-report.md](12-progress-report.md)
**状态**：增量 1（Verification Gate）与增量 2（Experience Compiler）已完成；
增量 3（Plasticity Controller）下一步

---

## 1. 先修正一处我自己的错误

[12-progress-report.md](12-progress-report.md) §5.3 建议的执行顺序把
Plasticity Controller 排在第一位。**那个排序是错的**，理由是混淆了两条不同的路径：

| 路径 | 上面的模块 | 性质 |
|---|---|---|
| **关键路径** | Verification Gate → Experience Compiler | 没有它，任何提案都无法提交，慢环根本不能闭环 |
| **价值路径** | Plasticity Controller → LocalPlasticity | 没有它，系统不学习，记忆门不开 |

关键路径应当先走。我在 12 里把「解门控不开这个问题最直接」当成了排序依据，
但那是价值判断，不是依赖判断。本文档取代 12 §5.3。

---

## 2. 依赖盘点：慢环缺的到底是什么

慢环公式（08 §4.2）：

```
触发: SLEEP | DEATH_SNAPSHOT
ΔM   = MemoryUpdate(trace, f_t)
ΔM_h = HeritableFilter(ΔM)
ΔS   = SkillCompiler(trace, f_t)
ΔR   = RuleCompiler(trace, f_t)
Δθ   = LocalPlasticity(trace, f_t, allowed_scope)
for p in ExperienceCompiler(ΔM, ΔS, ΔR, Δθ):
    VerificationGate(p) → pass ? StructureStore.commit(p, v+1) : reject
G' = GeneManager.mutate(G, ΔS, Δθ, ΔM_h)
```

**已经有的**（Milestone 1 留好的接口，不是我要建的）：

| 已有 | 位置 | 说明 |
|---|---|---|
| `StructureStore.commit()` | `sse_protocols/structure_store.py:140` | **已经消费 `GateResult` 并处理拒绝**——拒绝是正常路径，记 `applied=False` 的审计项，版本号不切换，不抛异常 |
| `GateResult` | 同文件 | `passed` / `reason` / `stage_failed` 三字段 |
| `PROPOSAL_KIND_MAP` | 同文件 | 8 种提案类型 → 5 种结构类别，一个提案只影响一个类别，版本号按类别独立递增 |
| `SelfModificationProposal` | `sse_protocols/self_modification.py` | 含 08 新增的 `origin` |
| `AuditRecord` | `sse_protocols/structure_store.py` | 每次提交记 `(proposal_id, kind, from_v, to_v, gate_result, timestamp)` |
| `SlowLoopHook` / `DeathHook` | `fast_loop.py` | 两个钩子，默认 `None` |
| `MemoryItem.is_heritable()` | `sse_protocols/memory.py` | 判据已实现并有测试，无消费者 |
| `SkillLibrary.compile_from_trace` | `skill_library.py` | 轨迹 → 技能的编译已实现（Milestone 3），但无触发器 |

**缺的**：`GateResult` 的**生产者**。这是关键路径的第一个断点——
`commit()` 在等一个 `GateResult`，而全项目除了测试常量没有任何东西产出它。

---

## 3. 执行顺序

| # | 交付物 | 为什么在这个位置 | 验收 | 状态 |
|---|---|---|---|---|
| 1 | **Verification Gate** | 关键路径第一环；`GateResult` 的生产者；安全边界（07 风险 4） | 四类提案各自有「该拒的拒掉、该过的放过」的测试 | ✅ 完成 |
| 2 | **Experience Compiler** | 提案的生产者；吃 trace 吐四类 Δ；没有它 Gate 无输入 | 能从真实 trace 产出提案，且不产出恒真提案 | ✅ 完成 |
| 3 | **Plasticity Controller + LocalPlasticity** | 价值路径；解「门控不开」；`allowed_scope` 划定更新边界 | 记忆门在训练后开启率显著高于随机初始化 | ✅ 完成 |
| 4 | **RuleCompiler** | 与 3 并列，Gate 好了就能过门 | 能从 trace 产出 `RuleProposal` | ⬜ |
| 5 | **HeritableFilter** | 独立，`is_heritable()` 的消费者 | 瞬时记忆不进子代，可继承记忆进 | ⬜ |
| 6 | **Gene Manager** | 独立，可与 1–5 并行；Milestone 5 前置 | save / load / mutate 三件 | ⬜ |

**§12 实验的解锁点**：实验 2（记忆召回）在第 3 步之后可跑，不必等慢环完工。
它是验证 Plasticity 是否真的让记忆影响了行为的直接指标。实验 6（安全自我修改）
的前置已在第 1 步满足，等第 2 步产出提案即可开跑。

第 3 步落地后又多出一个解锁点：**实验 2 的对照组现在有了**。`ZeroMemoryRetriever`
是"把记忆关掉"那一格，而 Δθ 修好的"门本来就不开"是"记忆从未被打开"那一格——
两格的差别现在可测了。

---

## 4. 增量 1：Verification Gate

### 4.1 它是什么

`SSEA/verification_gate.py`。输入一个提案与当前结构，输出一个 `GateResult`。
四级检查，顺序不可换（08 §2.1）：

```
格式 → 沙盒 → 回归 → 小范围环境测试
```

任一级失败即停，`stage_failed` 记下失败的那一级。

| 级 | 查什么 | 典型拒绝理由 |
|---|---|---|
| 格式 | 提案类型合法；payload 键与结构类别匹配；引用 id 存在；无越权字段 | `提案类型无对应结构类别`、`payload 缺少必需键` |
| 沙盒 | 把提案应用到结构**副本**上，副本仍满足各类别的不变量 | `新技能动作序列违反约束`、`检索策略校验不过` |
| 回归 | 候选结构仍通过当前结构通过的全部不变量 | `memory_dim 不再被 top_k 整除`、`技能 id 重复` |
| 环境 | 用候选结构装配快环跑一小段，不崩溃、不立即死亡 | `闭环在候选结构下崩溃`、`N 帧内死亡` |

沙盒与回归的区别：沙盒查**这一个提案引入的**问题，回归查**它有没有弄坏别的**。
前者是「新东西合法吗」，后者是「旧东西还活着吗」。

### 4.2 它刻意不做什么

这一节比 4.1 重要。

**Gate 不评估提案好不好，只评估它能不能安全应用。**

SSEA 没有评分函数，只有淘汰函数（C9）。Gate 一旦开始给提案打分、按分数排序、
只放高分的过，它就变成了一个评分函数——而那正是 SSEA 立场要拒绝的东西。
Gate 的回答是二值的：合法 / 不合法。

推论：**两个提案一个让存活帧数翻倍、一个让存活帧数减半，只要两者都合法，
Gate 对它们一视同仁。** 选择权不在 Gate，在淘汰函数——活下来的那个自然被保留，
死掉的自然被淘汰。这是 07 §4.6「自我修改必须经过验证」与 C9 的接缝。

**Gate 不执行任意代码。** 08 §3.1 已把 ΔC 折叠进 ΔS，第一阶段没有代码执行。
所以「沙盒」不是代码沙盒，是**结构副本上的不变量检查**。若将来真的开放代码段，
这一级要重做，且必须先回答「谁有权执行」——那是 v0.4+ 的问题。

**Gate 不碰权重。** `UPDATE_ADAPTER` 提案改的是快照里的 adapter 配置，
不是 torch 参数本身。参数更新走 LocalPlasticity（增量 3），那条路有自己的
`allowed_scope` 限制（07 §6.7 的不可更新对象清单）。

**Gate 不做回滚。** `StructureStore` 上没有 rollback 方法——被拒的提案从未被应用，
没有东西需要回滚。Gate 的拒绝只是让 `commit()` 记一条 `applied=False`。

### 4.3 与 `StructureStore.commit()` 的接缝

已有代码已经把接缝定好了，Gate 只需遵守：

```python
result = gate.check(proposal, store.snapshot())   # → GateResult
record = store.commit(proposal, result, timestamp) # 内部自己分流 pass / reject
```

`commit()` 不抛异常、不要求调用方先判断 `passed`。慢环因此可以写成一条直线，
不需要 try/except 包住拒绝路径。

### 4.4 交付物与验收

- `SSEA/verification_gate.py`
- `tests/test_verification_gate.py`

验收（对齐 07 §11 Milestone 4 第三项「修改可以验证和回滚」中的**验证**半边）：

1. 四种提案类型各有至少一条「合法 → 放过」与一条「非法 → 拒绝」的测试
2. 四级检查的顺序可观测：一个同时触犯多级的提案，`stage_failed` 报的是**最早**那一级
3. Gate 不修改传入的结构（副本语义，可用 `store.versions()` 不变来验）
4. 拒绝路径不抛异常、不改版本号
5. Gate 不给提案打分——没有 `score` 字段，没有排序 API（这条由测试守住：
   断言 `GateResult` 的字段集合恰为三件套）

### 4.5 明确留给后续增量

- 提案的**内容**从哪来 → 增量 2（Experience Compiler）
- `UPDATE_ADAPTER` 的 adapter 到底是什么形状 → 增量 3（Plasticity Controller 定 `allowed_scope` 时一并定）
- 环境那一级跑多少帧、什么算「立即死亡」→ 实现时定一个默认值并写成可配置

### 4.6 增量 1 的落地结果与一个意外发现

**交付物**：`SSEA/verification_gate.py` + `tests/test_verification_gate.py`（53 项）。
五项验收逐条对上：

| 验收 | 落点 |
|---|---|
| 1. 四类提案各有放过与拒绝 | `TestEveryProposalType`，8 种类型 × {合法, 非法} 全覆盖 |
| 2. 顺序可观测，报最早那一级 | `TestStageOrder` |
| 3. 不修改传入的结构 | `TestNoMutation`（快照不变、版本号不变、三次查同一提案同结论） |
| 4. 拒绝不抛异常、不改版本号 | `TestWithStructureStore` |
| 5. 不打分 | `TestNoScoring`：`GateResult` 字段恰为三件套，Gate 上无 score/rank/sort/compare/best |

**意外发现：Gate 逼出了一个 Milestone 1 的潜伏 bug。**
第四级要把候选结构装配成快环真跑一遍，于是 `UPDATE_RETRIEVAL_POLICY`
无处躲藏——`StructureStore._apply` 写 `nxt[target] = policy`，而 `retrieval`
实际是**一份扁平策略**（键即策略字段名），不是 name→policy 的映射。提交后
`retrieval` 变成 `{"default": {"top_k": 8}}`，`MemorySystem` 把整个映射交给
`validate_retrieval_policy`，读到未知键 `"default"` 直接 `ValueError`——
**快环在下一个 `WAKE` 上崩**。

这个洞在 Milestone 1–3 全程不可见：`test_structure_store.py` 只断言版本号递增，
而构造 `MemorySystem` 的测试用手写的扁平 `retrieval`。**没有任何机制真的去读
提交后的 retrieval。**

已修：`_apply` 改为 `nxt[target] = policy`，与 `UPDATE_THRESHOLD` 同形
（`target` 是策略键名，`policy` 是它的新值）。Gate 侧同步改了四处——
格式级改为校验「target 是不是合法策略键」，沙盒/回归级改为校验**整份扁平映射**。

回归钉子两条，堵在不同层：
`test_verification_gate.py::test_committed_retrieval_policy_is_readable_by_memory_system`
与 `test_structure_store.py::test_committed_retrieval_policy_is_readable_downstream`。

**这条教训对后续增量直接有用**：Store 只管版本号与审计，**不保证下游读得懂**。
每个新增的提案类型，都必须配一条「提交后消费方真的能用」的测试，
否则又会造出一个只有 Gate 能发现的洞。

**环境参数定值**（§4.5 里说「实现时定」的那项）：
`env_frames=20`（够长到能暴露崩溃，又短到 gate 可频繁调用）、
`env_sudden_death_frames=3`、`env_seed=0`、`decoder_seed=0`。
固定 seed 是为了让 Gate 的结论**可复现**——同一个提案在同一个结构上
必须得到同一个答案，否则「能不能安全应用」这句话没有意义。

---

## 5. 增量 2：Experience Compiler

### 5.1 它是什么，以及它刻意不做的三件事

`SSEA/experience_compiler.py`。输入一条 trace，输出一组
`SelfModificationProposal`。它是慢环公式（08 §4.2）里
`ExperienceCompiler(ΔM, ΔS, ΔR, Δθ)` 那一项的第一段可执行形式。

07 §6.6 列了四类输出（技能 / 规则 / 记忆摘要 / 局部参数更新），
本增量**只实现 ΔS**。理由不是懒，是另外三类各有归属增量且都不能用空壳敷衍：

| Δ | 归属 | 为什么现在不做 |
|---|---|---|
| ΔS 技能提案 | 本增量 | `SkillLibrary.compile_from_trace` 自 Milestone 3 就在，缺的是触发器 |
| ΔR 规则提案 | 增量 4 | 从 trace 提规则的判据尚未设计 |
| ΔM 记忆摘要 | 增量 5 | `is_heritable()` 已实现但无消费者 |
| Δθ 参数更新 | 增量 3 | `LocalPlasticity.allowed_scope` 是它的上界，先有上界再谈更新 |

未实现的 Δ 以 `DEFERRED_DELTAS` 常量声明，**不写返回空 tuple 的占位方法**——
一个永远为空的函数就是死代码，而「协议不容无消费者的通道」这条纪律对函数
同样成立。`TestDeferredDeltas` 守着这个集合：增量落地时必须同步改常量与
docstring，否则那条测试失败。

三件刻意不做的事：

**不提交任何东西。** 编译、验证、应用是三个不同的问题：

```
编译器决定「提什么」 → Gate 决定「能不能安全应用」 → Store 决定「应用不应用」
```

把三者捏在一起，就没法单独回答「提得对不对」——而那正是慢环最该被测的部分。
`compile()` 只返回提案；提交是调用方的事（`run_slow_loop`）。

**不评估提案好不好。** 与 Gate 同一条纪律（C9）。编译器按**世界计价物**
（净能量）决定提不提，不按任何内部偏好排序。

**不自己发明 Δ。** ΔS 复用 `skill_library.compile_skills` 那一份切分规则。
两份规则必然漂移，而漂移的表现是「同一条轨迹编译出两条语义相同的技能」——
那种不一致在运行时报错里看不见，只会在审计日志里表现为重复提案。
为此把 `compile_skills` 提成了模块级纯函数（Milestone 3 的
`compile_from_trace` 现在是它的一个委托）。

### 5.2 「不恒真」是验收的另一半

一个恒真的编译器——不管 trace 是什么都提同样的提案——能让整条慢环链看起来
在工作，而实际上什么也没学到：它只是把一个常数搬过了验证门。
所以测试用四种独立的方式证它**会沉默**：

| 输入 | 期望 |
|---|---|
| 空 trace | 0 条 |
| 净能量为负的 trace | 0 条（把失败固化下来不是学习） |
| 技能执行中的子动作帧 | 0 条（抄一条已有技能是复制不是学习） |
| 同一条 trace 第二次 | 0 条（技能已在结构里） |
| 不同 trace | **不同**提案 |

最后一条是对偶：恒真编译器坏在输出与输入无关。两条合起来才说明
提案是 trace 的函数。

沉默必须**留原因**。`CompileResult` 把 `proposals` 与 `skipped` 分开：
审计日志要能回答「我们看到了一条可编译的成功轨迹，为什么没提案」。
只有 proposals 的话，那次沉默与「什么都没看到」在日志里不可区分。

### 5.3 proposal_id 由内容导出，不由调用次数导出

实现过程中自己踩的一个坑：第一版 `proposal_id` 用自增计数器
（`exp-000001`、`exp-000002`）。它能让 id 唯一，但代价是
`compile()` 不再是纯函数——同一条 trace 两次编译得到两个不同的 id。
三个后果：

- 「同样的输入同样的输出」无法断言；
- 审计日志里同一条技能出现两行不同 id 的记录，「这是重复提案」要一次集合运算才能回答；
- Gate 的可复现性（见 `GateConfig.env_seed` 的注释）缺了上游一半。

改为 `f"{prefix}-{skill_id}"`：目标即 id，内容相同则 id 相同。
重复提案现在**看起来就是重复的**，审计日志里也一眼能看出这条提案是关于
哪条技能的，不必翻 payload。

### 5.4 端到端：睡眠期真的整理经验

07 §18 第 7 项「模型可以将成功行为固化为技能」在 Milestone 3 只备齐了
编译判据，**没有触发器**——`FastLoop.slow_loop` 默认 `None`。
`make_slow_loop_hook` 就是那个触发器。

`TestSleepActuallyCompiles` 跑一个真快环（状态机、Skill Runner、
Environment、Gate、Store 全是真的），让它睡过去，断言醒来时技能库里多了
一条它自己编译出来的技能，且后续每一次睡眠都沉默。

**这个测试为什么长这样，需要记录**，否则结论会被误读：

| 做法 | 原因 |
|---|---|
| 脚本化策略 | 默认 Action Decoder 随机初始化，从不 emit grasp；而这个世界里唯一的正能量来源就是 grasp 资源。默认配置下跑一万帧也编译不出任何东西——**这不是编译器的缺陷，是世界还没给出可学的成功** |
| 「攒满 n 帧才准睡」的代谢包装 | 若睡眠阈值全放宽（第一帧就睡），trace 里永远只有 1 帧 RUN，短于 `min_frames=3`，编译器无事可做 |
| `resource_gain=0.2` | 能量上限 1.0 而 agent 开局就满。增益太大则第一抓吃满头寸，后续各抓的 `energy_change` 全是 0.0，连续正收益段拼不起来 |
| 资源簇 + 0 危险源 | 让策略只管抓，不用躲，减少与「能不能抓到」无关的变量 |

三条都是**环境与策略的现实约束**，不是编译器的性质。诚实的说法是：
**慢环的闭环已经打通，但当前默认世界上还没有可学的东西。**
增量 3（Plasticity）之后、或换一个默认解码器不是随机初始化的配置，
这条端到端才可能不靠脚本化策略跑通。

### 5.5 交付物与验收

- `SSEA/experience_compiler.py`
- `tests/test_experience_compiler.py`（35 项）
- `SSEA/skill_library.py`：`compile_skills` 提为模块级纯函数，`compile_from_trace` 委托给它

| 验收（§3 增量 2） | 落点 |
|---|---|
| 能从真实 trace 产出提案 | `TestCompilesRealTraces`：7 项，含「payload 的键是 Gate 格式级认的那一个」与「提案真能过门」 |
| 不产出恒真提案 | `TestNotTautological`：10 项，五种沉默方式全覆盖 |
| 慢环一步可执行 | `TestSlowLoopStep`：编译 → 过门 → 提交，含「Gate 每条提案看到的是新快照」 |
| 端到端触发器 | `TestSleepActuallyCompiles`：4 项，含「编译出来的技能 Skill Runner 真能展开」 |

全套件 **684 passed / 1 skipped**，且在 `pytest-randomly` 的 15 个 seed 下
结果一致（顺序不变性）。

---

## 6. 增量 3：Plasticity Controller + LocalPlasticity

### 6.1 它是什么

`SSEA/plasticity.py`。两个类，分工与增量 1 / 2 同构：

| 类 | 回答什么问题 | 依据 |
|---|---|---|
| `PlasticityController` | 这个更新在不在 `allowed_scope` 里 | 07 §6.7 两张清单的可执行形式 |
| `LocalPlasticity` | 从这条 trace 提什么 Δθ | 08 §4.2 慢环公式的 `Δθ` |

**第一阶段的 Δθ 是结构侧的行为阈值**，住在 `FastLoopContext.thresholds` 与
`FastLoopContext.retrieval` 里。于是改它必须走「提案 → 验证门 → Structure Store →
WAKE 换版」——每一次变动都是一次可审计的版本切换。**不是 torch 参数**，理由见 6.2。

两条规则，各自对应一个**可观测的症状**，且都能沉默：

```
症状 1  值得记的帧上门从没开过     → 降低 memory_gate_threshold
症状 2  写进去了却从来读不回来     → 降低 min_similarity
两者皆非                        → 不提案
```

"值得记的帧"由**惊奇**判定（`Feedback.prediction_error`，SurpriseEstimator 的产物，
doc 03 点名的 SSEA 核心学习信号），不由任何内部偏好判定。这与增量 2 是同一条纪律：
编译器按世界计价物决定提不提，不按内部排序。

注意症状 1 的措辞是"门从没开过"，不是"门开得不够多"。通道门开着而模型选择
`store=False` 是**一个决定**，不是缺失——那个决定属于 `mem_store` 头，是参数侧的
职权。第一阶段只修"连决定都没得做"。

### 6.2 它刻意不做什么

**不动 torch 参数。** `ActionDecoder` 的门控头（`gates.memory` 等）确实可微，
但第一阶段整个不动它，理由不是排不下，是现在做会造出一个**假的安全保证**：

1. 07 §16「模型不可绕过验证器应用修改」。参数更新要么不过门（违背此条），要么过门。
2. 而过门这条路在第一阶段是**空的**：`VerificationGate` 的四级检查全部在
   `FastLoopContext` 上进行，第四级环境测试装配的是一个**全新的** ActionDecoder——
   一个权重增量递进去，环境测试看不见它，于是"四级检查全部通过"这句话在参数上
   什么也没检验。
3. 把权重增量塞进 `UPDATE_ADAPTER` 的 bytes 里能让它"看起来过了门"。
   `_check_adapters` 只查"是非空 bytes"。**那比不过门更糟**：它让文档可以写
   「自我修改经过验证门」，而实际上验证了什么并不知道。

所以参数侧整个声明为未实现（`DEFERRED_SCOPES`），由
`tests/test_plasticity.py::TestScopeBoundary::test_deferred_scopes_are_declared_not_stubbed`
守着。真正的落地顺序是三步可见的工程：先让 `adapters` 有模型侧消费者（现在它是个
写得进、过得门、传得下、**却没有消费者**的类别），再让 Gate 的第四级能装上候选权重，
然后才谈参数侧 Δθ。

**不评估提案好不好。** 与 Gate 和编译器同一条纪律（C9：只有淘汰函数，没有评分函数）。
`PlasticityObservation` 里没有任何"这轮学得好不好"的字段——只有症状计数。

**不提交任何东西。** 编译 / 判定 / 验证 / 应用是四个问题：
编译器决定「提什么」（ΔS）、本模块决定「Δθ 提什么」、Controller 决定「在不在边界内」、
Gate 决定「能不能安全应用」、Store 决定「应用不应用」。捏在一起，
「提了一个越界的更新」与「边界定错了」在日志里不可区分。

### 6.3 三处设计决定

**一、白名单而非黑名单。** `DEFAULT_BOUNDS` 是一张显式的「键名 → (下界, 上界)」表，
不在表里的键不可改。一个忘了登记的键应当**提不出提案**，而不是悄悄改掉某个机制。
键名从语义所有者取（`action_decoder.GATE_THRESHOLD_KEYS`、
`memory_system.DEFAULT_RETRIEVAL_POLICY`），不在本模块另列一份——两份清单必然漂移。
下界不取 0：阈值为 0 时门控恒开，那不再是"倾向于开门"，是"门控不存在了"。

**二、证据只看当前版本。** 慢环拿到的 trace 是**整条 episode**，横跨多个结构版本。
Δθ 的判定因此只取末帧 `context_fingerprint` 那段（`_current_window`）——
换版前那些帧上的"门没开"是**旧策略的账**。

不切这一刀的后果实测过（seed 2）：三轮睡眠把 `memory_gate_threshold` 从 0.5 推到
0.4 → 0.3 → 0.15（下界），而第二、三轮的触发证据全部来自第一轮之前。
**那不是收敛到合适的阈值，是撞到夹子。** 切了窗口之后同一轨迹只提一次，且换版后
新窗口里 `missed_surprise == 0`，于是沉默。

**三、关系断言要证据下限。** 两条症状对证据量的要求刻意不同：症状 1 是逐帧性质
（"这一帧上门没开"在单帧上就是真的），症状 2 是**关系**断言（"写了却读不回"要写入
与读取双方都有机会发生）。`min_evidence_frames` 因此只约束症状 2。不设这个下限的
后果也实测过：短窗口下规则每轮都触发，把 `min_similarity` 一路推到下界 0.01，
而 0.01 意味着恒命中——机制被关掉而不是被调好。

### 6.4 落地结果：修了两个断点，一处诚实保留

**断点一：`FastLoopContext.get_threshold()` 是一个没有消费者的声明。**
它的文档写"Action Decoder 的决策阈值来源"，而 `ActionDecoder` 读的是
`self.config.gate_threshold`。不接上这一线，Δθ 提的每一条提案都能过门、都能提交、
都能换版，而**行为一点都不会变**。接法是在 `forward` 加第五个参数
`gate_thresholds`，默认 `None` = 退回配置值，老调用点一行不用改。
由 `TestThresholdIsObservable` 钉住：同一个 hidden、同一个门控值，
阈值从刚好高于它降到刚好低于它，记忆通道从闭到开。

**断点二：`thresholds` 这个结构类别永远无法被初始化。**
Gate 格式级曾要求 `UPDATE_THRESHOLD` 的 target 必须**已存在**——而 Store 刚建起来时
`thresholds` 是空的，且 `ALLOWED_PROPOSAL_TYPES` 里**没有** `ADD_THRESHOLD`
（07 §8.12「未增删」只增删技能与规则）。于是 UPDATE 只能改已有的键，而没有任何提案
能建第一个键：这个类别是死的。

修法是扩展 `UPDATE_RETRIEVAL_POLICY` 已有的那条特例（它当初的注释已经把同样的
理由写在 `retrieval` 上了）——两个类别都是**一份扁平策略**（键即策略字段名），
target 该按"是不是一个合法的策略键名"判，而那要从语义所有者取。
回归钉子在 `tests/test_verification_gate.py::TestFormatStage::test_flat_policy_can_be_initialized`。

**一处诚实保留：这个提升很大，但不是因为规则很聪明。**
8 个 seed、各 25 帧、睡一次、再看 25 帧：

| seed | 换版前开门率 | 换版后开门率 | 提案数 |
|---|---|---|---|
| 0 | 1.000 | 1.000 | 0 |
| 1 | 1.000 | 1.000 | 0 |
| 2–6 | 0.000 | 1.000 | 1 |
| 7 | 0.240 | 1.000 | 1 |
| **均值** | **0.280** | **1.000** | 6/8 提案，2/8 沉默 |

提升是真的，且**该沉默的种子保持沉默**（0 和 1 本来就能开门，一条提案都没有）。
但 0.28 → 1.00 这么大，主要是因为随机初始化的门控值几乎恒定在 0.5 附近
（240 个采样：min 0.463、中位数 0.487、max 0.530），阈值 0.5 恰好切在正中间，
于是大约一半的种子门恒闭。**一个全局阈值是钝器。**

更强的断言——**选择性**（惊奇帧开门、平淡帧关门）——没有做到，且用一个全局阈值
**做不到**。那需要参数侧 Δθ，也就是 6.2 里被整个推迟的那一半。
所以本增量的正确说法是：**「门控不开」这个故障被修好了，而「门开得准不准」
是下一步的事。** 这句话写在这里，免得后来的人把 1.00 读成学会了选择性。

### 6.5 交付物与验收

- `SSEA/plasticity.py`（新增）
- `tests/test_plasticity.py`（新增，50 项）
- `SSEA/action_decoder.py`：`GATE_THRESHOLD_KEYS` + `forward` 第五参数 `gate_thresholds`
- `SSEA/fast_loop.py`：解码调用传入 `dict(self.context.thresholds)`
- `SSEA/verification_gate.py`：修 `thresholds` 类别无法初始化的缺陷
- `SSEA/experience_compiler.py`：Δθ 接进慢环一步；Δ 的三态账本补 `DELEGATED_DELTAS`

| 验收（§3 增量 3） | 落点 |
|---|---|
| 记忆门开启率显著高于随机初始化 | `TestAcceptance`：5 项，含「均值至少翻倍」「本来正常的种子保持沉默」「提交的值真的装进了新快照」 |
| `allowed_scope` 划定更新边界 | `TestScopeBoundary`：10 项，含「禁止清单先于白名单」「未登记边界的键不可改」 |
| 不产出恒真提案 | `TestNotTautological`：7 项，四种沉默方式（无 RUN 帧 / 路径正常 / 已在边界 / 证据不足） |
| 阈值改动看得见 | `TestThresholdIsObservable`：2 项，行为真的随阈值翻转 |
| 收敛而不是撞夹子 | `TestConvergesOnce`：2 项 + `TestEvidenceWindow`：4 项 |
| 三种帧类别可区分 | `TestObservation`：8 项，含事件按 id 去重（滚动窗口）、一帧滞后 |

全套件 **737 passed / 1 skipped**，且在 `pytest-randomly` 的 15 个 seed 下
结果一致（顺序不变性）。

---

## 7. 环境

已按本次会话补 [`requirements.txt`](../requirements.txt)：生产代码只依赖 `torch`，
测试加 `pytest` 与 `pytest-randomly`。`numpy` / `torchvision` 不需要（前者由 torch
自带，本项目不直接 import；后者无视觉输入）。

`pytest-randomly` 已装入环境。顺序不变性现已有自动守卫，本次会话已用 15 个
随机 seed 验证全套件均为 737 passed / 1 skipped（增量 1 收尾时 649，增量 2 收尾时
684，增量 3 收尾时 737）。**此后每次改动都必须在这 15 个 seed 下复跑**，
不只是默认顺序。

> 注：`python` 与 `.venv/Scripts/python.exe` 现在都装了完整环境
> （`pytest-randomly` 5.0.0），两者跑出来一致。此前 `python` 指向的系统解释器
> 缺少该插件，那条限制已解除。
