# experiments/ —— 07 §12 的七个验收实验

这些脚本产出的**是证据，不是测试**。

| | 回答什么 | 判据 |
|---|---|---|
| `tests/` | 机制是否按设计工作 | 协议自洽、约束不被违反、注入面四条性质成立 |
| `experiments/` | 这个架构到底有没有用 | 12 §4.2 那张表的数字 |

751 项测试全绿只说明工程质量，不说明架构有效性。反过来，
`experiments/` 跑出来的数字再好也不能替代测试——**两者不能互相顶替**。

## 跑法

```bash
.venv/Scripts/python.exe -m experiments.run_all          # 一次跑完已就绪的
.venv/Scripts/python.exe -m experiments.exp1_nonverbal_loop
.venv/Scripts/python.exe -m experiments.exp7_sleep_compilation 400   # 指定帧数
```

## 七个实验的落地状态

编号与名称依 07 §12 原文（1–6），实验 7 是 08 新增的
（07 原文只有六条，见 12 §4.2 的注）。

| # | 实验 | 状态 | 脚本 |
|---|---|---|---|
| 1 | 非语言闭环 | 已跑 | [exp1_nonverbal_loop.py](exp1_nonverbal_loop.py) |
| 2 | 记忆召回 | 未落地 | — |
| 3 | 技能固化 | 未落地 | 依赖债务 6b（默认策略产生不了可编译的成功段） |
| 4 | 基因保存恢复 | 未落地 | 缺 Gene Manager |
| 5 | 变异 | 未落地 | 缺 Gene Manager |
| 6 | 安全自我修改 | 已跑 | [exp6_safe_self_modification.py](exp6_safe_self_modification.py) |
| 7 | 睡眠期编译 | 已跑 | [exp7_sleep_compilation.py](exp7_sleep_compilation.py) |

脚本不打全部七个的名字——**没跑的就不出现在输出里**。12 §4.2 长期写着
「一个都还没有」，理由是同一条：没有数字比假数字好。

**实验 2 / 3 仍未落地，而 2026-09-27 加的累计计数器并没有改变这一点。**
这两条是七实验里唯一带对照组的，而它们卡在**别处**：`危险回避率` 需要按
`source_id` 分辨危险源与资源（按类型的 dict **没有这个维度**——`OBJECT_FOUND`
对两者一视同仁），`能量消耗变化` 需要**按结构版本切开的窗口**而非全轮累计；
真约束则是行为层的「走不动」（`action_decoder.py:229` 的 `loco_dir` 是未训练
线性头，agent 近似直线行进，**不会转向就无从回避**）与世界层的「没有可学的
成功」。计数器是**必要不充分**的那个前置——它买到的是「脚本不会静默算错」，
不是这两列数字。详见 14 §6.3.4。

## 四个共用的设计选择

**一、量从 trace、累计计数器与审计日志取，不从环形缓冲取。**
`Environment.event_log()` / `event_notes()` 是 16 槽环形缓冲（12 §6 债务 10），
"跑完再遍历事件流"会**静默漏掉早期事件**。核对时它真的咬过一次：「跑完统计
`ENERGY_GAINED`」得到 0 次，而逐帧追踪显示第 10 帧确实 `grasp: +0.356 energy`。
所以有三个不丢的来源，**按问题选，互相顶替不了**：

| 来源 | 回答什么 | 不回答什么 |
|---|---|---|
| 逐帧 `Feedback` 增量 | 能量 / 伤害收支 | 事件类型分解 |
| `Environment.event_counts()` | 「这轮 grasp 成功了几次」 | 能量（`ENERGY_GAINED` 是**意图值**）；`source_id` 维度 |
| `StructureStore.audit_log()` | 提案与版本切换的明细 | 运行期的任何量 |

`event_counts()` 是 2026-09-27 加入的（只增不减、不截断），正是为补这个洞。
**但它与逐帧求和不是一回事**：它数的是**事件**，而 `push` / `pull` /
基础代谢的耗能**根本不发事件**（`ENERGY_LOST` 至今没有生产者），
所以"总能量支出"只数事件**一定漏**。要能量收支就用 trace 上的 `Feedback`。

**二、每个数字都必须能被人复跑。**
`run_episode` 的种子与帧数是显式参数，且 `torch.manual_seed` 在**构造任何对象
之前**调用——门控开不开由随机初始化决定（12 §4.3），种子的位置换一下就是
另一场抽奖。

**三、分母为 0 的指标必须主动造分母。**
自然运行下驳回率是 0，于是「失败回滚率」「被驳回提案对应的行为未改变率」
两个指标的分母是 0。0/0 最容易被写成 100% 然后当成机制有效的证据。
[`_injection.py`](_injection.py) 就是为这两列存在的。

**四、全轮累计归 `Environment`，窗口内的统计归 harness。**
两处都做会得到两个会漂移的真相，所以分工划死：

- **`Environment.event_counts()`**——自构造或上次 `reset()` 以来的**全轮累计**，
  O(1)，免疫截断。注意它对 `reset()` **是归零的**（`FastLoop.__init__` 就会调
  `reset()`），所以 8-seed 循环里各轮总计**不同**才是对的；看到单调递增，
  就说明计数器活过了 `reset()`。
- **`count_events(trace, event_type)`**——**给定窗口内**的计数，按 `event_id`
  去重。去重治的是**重复计数**（观测里带的 `events` 是滚动窗口，同一个事件会
  连续出现在十几帧里），治不了**窗口外**——这正是它和上面那条的分界。
- **`energy_by_version_window(trace)`**——按 `StepRecord.context_fingerprint`
  切开的能量收支，**实验 3 的「能量消耗变化」必须用它，不能用全轮累计**：
  不切版本，固化**前**的消耗会永远留在分子里。切法照
  `plasticity._current_window`，那里记着不切窗口的实测代价（三轮睡眠把
  `memory_gate_threshold` 从 0.5 一路推到下界 0.15——「不是『收敛到合适的阈值』，
  是『撞到夹子』」）。**同一个错法在能量指标上会重演一遍。**

派生量挂在 `EpisodeResult` 上：`energy_gained` / `energy_spent` / `damage_taken`
（逐帧现加）、`event_totals`（尾部取一次）、`net_energy_change` /
`energy_spent_per_run_frame`（属性）。三条能量口径写在
[`_harness.py`](_harness.py) 的模块 docstring 一之二里，**别在各脚本里各定一套**：

1. 分母是 **RUN 帧数**，不是 `len(trace)`——睡眠帧每帧**涨** 0.01 能量，
   用总帧数归一化会让"睡得多的回合"显得**更省**。
2. `energy_spent` 是**毛支出**，睡眠期的恢复不抵消它；净额另给。
3. 取的是**夹取后的「实现增量」**，不是「请求增量」。由此有一条**已知偏低、
   不是 bug**：6 处 `max(0.0, ...)` 与 damage 的 `min(max_damage, ...)` 都在
   丢弃超调，而死亡帧恰是消耗峰值帧。报告里注明，别当测量误差去"修"。

## 本次实验发现的守卫缺口

这些不是违规，是**没人检查过**。「没人检查过」与「检查过没问题」是两件事，
所以记在这里。

### 一、`Action` 通道内部的 str 字段从未被静态检查

`tests/test_protocol_consistency.py::TestNoNaturalLanguageInLoop` 的白名单是
在 `Observation, Feedback, EventVector, MemoryItem` 上算的；
`test_action_has_no_string_command_field` 只查 `Action` 的**顶层**字段名
（六个通道名）。

于是 `Action` 六个通道**内部**的 str 字段从来没被检查过：

| 字段 | 所在通道 | 实际装的是 |
|---|---|---|
| `Manipulation.target_id` | manipulation | 对象 id——**名字** |
| `Manipulation.operation` | manipulation | 操作码——**名字，须取自闭集** |
| `Communication.target_id` | communication | 对象 id——**名字** |
| `SkillCall.skill_id` | skill_call | 技能 id——**名字** |
| `SelfModification.proposal_type` | self_modification | 提案类型——**名字，须取自闭集** |

实测它们确实都是名字，所以**不是违规**。`experiments/_harness.py` 的
`IDENTIFIER_FIELDS` 把这四个补进了白名单。

### 二、光有字段名白名单不够，操作码必须查闭词表

补完字段名之后仍然有一个口子：只按字段名放行的话，`operation` 就成了一个
**"可以往里写任何字符串"**的字段——而"可以往里面写任何字符串"正是正文的入口。

所以 `_harness.py` 的 `count_strs_deep` 加了一层：标识符允许出现，但取自
闭词表的那些（`operation` / `proposal_type`）**必须命中** `OPERATIONS` /
`ALLOWED_PROPOSAL_TYPES` 才算名字。

名字与正文的分界就在这里：**名字取自闭集，正文不是。**

第一次跑实验 1 时这条检查报了 670 次越界，全部来自上面五个字段。
补完字段名白名单 + 闭词表之后是 **0**。

### 三、Verification Gate 后三级的注入样本还是空的

`_injection.py` 的六条攻击打中的层是：

```text
plasticity.scope  ×3      gate.format  ×1
plasticity.clip   ×1      store.commit ×1
```

**`gate.sandbox` / `gate.regression` / `gate.env_test` 三级没有注入样本。**
实验 6 里 18 条自然提案全部四级通过，所以那三级在"自然 + 注入"两个来源上
都没有拒绝记录。它们的拒绝能力目前**只有测试覆盖，没有实验覆盖**——
补法见 12 §6 债务 6b 之后的待办。

## 相关文档

- `docs/12-progress-report.md` §4.2——七个实验的进度表（数字的归档处）
- `docs/13-milestone4-plan.md` §6.6——后续增量与顺序
- `docs/14-overview-and-roadmap.md` §6.3 / §6.4——各实验的前置与缺口
