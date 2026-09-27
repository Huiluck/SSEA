# experiments/ —— 07 §12 的七个验收实验

这些脚本产出的**是证据，不是测试**。

| | 回答什么 | 判据 |
|---|---|---|
| `tests/` | 机制是否按设计工作 | 协议自洽、约束不被违反、注入面四条性质成立 |
| `experiments/` | 这个架构到底有没有用 | 12 §4.2 那张表的数字 |

739 项测试全绿只说明工程质量，不说明架构有效性。反过来，
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

## 三个共用的设计选择

**一、量从 trace 与审计日志取，不从事件流取。**
`Environment._event_notes` 是 16 槽环形缓冲（12 §6 债务 10），"跑完再统计
事件流"会**静默漏掉早期事件**。核对时它真的咬过一次：「跑完统计
`ENERGY_GAINED`」得到 0 次，而逐帧追踪显示第 10 帧确实 `grasp: +0.356 energy`。
所以 `_harness.py` 的累计量一律逐帧现加，或者直接读 `StructureStore.audit_log()`
（append-only，不丢）。

**二、每个数字都必须能被人复跑。**
`run_episode` 的种子与帧数是显式参数，且 `torch.manual_seed` 在**构造任何对象
之前**调用——门控开不开由随机初始化决定（12 §4.3），种子的位置换一下就是
另一场抽奖。

**三、分母为 0 的指标必须主动造分母。**
自然运行下驳回率是 0，于是「失败回滚率」「被驳回提案对应的行为未改变率」
两个指标的分母是 0。0/0 最容易被写成 100% 然后当成机制有效的证据。
[`_injection.py`](_injection.py) 就是为这两列存在的。

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
