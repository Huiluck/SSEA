# SSEA v0.3.1 项目进度报告

**日期**：2026-09-27
**判定依据**：[07-ssea-v0.3.1-charter.md](07-ssea-v0.3.1-charter.md) §11 里程碑、
§18 完成标准、§12 验收实验；08 修订条款已并入
**代码**：[`SSEA/`](../SSEA/)（30 个 `.py`，5939 行）；[`tests/`](../tests/)（15 个测试文件，6455 行）
**设计文档**：[`docs/`](.)（12 篇编号文档 + 本索引 README，9429 行）

---

## 1. 一页结论

**状态**：Milestone 0 / 1 / 2 / 3 已完成，Milestone 4 / 5 未开始。
代码与测试全部就绪，**但架构有效性尚无一个实验数字**。

07 §18 的十二条第一阶段完成标准里：

```
已满足      5 项   （1–5）
部分满足    3 项   （6、7、11）
未开始      4 项   （8、9、10、12）
```

**一句话判断**：基础设施是扎实的——协议、双环、注入面、记忆、技能五块都有测试
守着，595 项测试通过，闭环能连续跑。但「SSEA 是一个有效的生存控制架构」这句话
**目前没有任何证据支持**，因为 §12 的六个验收实验一条都还没跑。

**下一步**：Milestone 4（慢环本体）。它是 §18 剩余七项里六项的前置条件。

---

## 2. 进度总表

| 里程碑 | 交付物 | 状态 | 证据 |
|---|---|---|---|
| 0 架构冻结 | 09 原创性说明 / 10 边界表 / 11 不做清单 | ✅ 完成 | 三份文档 |
| 1 接口协议 | 14 个协议 + Structure Store + FastLoopContext + 序列化 | ✅ 完成 | `test_serialization.py`（59 项）、`test_08_revisions.py`（55 项）、`test_structure_store.py`（31 项）、`test_protocol_consistency.py`（41 项） |
| 2 快环骨架 | Perception Encoder / State Core / Action Decoder / Skill Runner / Environment | ✅ 完成 | `test_fast_loop.py`（54 项）等 9 个文件（297 项） |
| 3 记忆与技能 | Memory System / Skill Library | ✅ 完成 | `test_memory_system.py`（87 项）、`test_skill_library.py`（57 项） |
| 4 慢环本体 | Experience Compiler / RuleCompiler / Plasticity Controller / Verification Gate / HeritableFilter | ❌ 未开始 | 只有 `SlowLoopHook` / `DeathHook` 两个空接口 |
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
| 7 | 模型可以将成功行为固化为技能 | ⚠️ 部分 | `compile_from_trace` + `test_compile_from_a_real_loop_trace` 证明「轨迹进 → 技能出 → 快环调用」链路通；但**触发固化的慢环编译器不存在**，模型自己不会固化。这是 §12 实验 3，未跑 |
| 8 | 模型可以保存基因 | ❌ | Gene Manager 未实现 |
| 9 | 模型可以从基因恢复 | ❌ | 同上 |
| 10 | 模型可以产生可运行变异后代 | ❌ | 同上；`mutation_rate` 作用范围已在协议层限定，但无消费者 |
| 11 | 模型可以提出自我修改提案 | ⚠️ 部分 | `SelfModificationProposal` 协议 + Action Decoder 的 `self_modification` 通道可产出提案；但**没有 Experience Compiler 生成提案内容**，提案目前是空壳 |
| 12 | 自我修改可以通过验证并安全回滚 | ❌ | Verification Gate 未实现。Structure Store 的「失败天然回滚」性质已有测试（`test_no_rollback_api_exists`），但那是**版本不切换**，不是**验证后拒绝** |

### 3.2 已实现能力及其边界

按项目自身的坐标轴说清每条能力「能做什么」与「不能做什么」。

**三分离（权重 / 记忆 / 技能）**

| 层 | 能做到 | 不能做到 |
|---|---|---|
| 权重 | `StateCore`（GRU）+ `ActionDecoder` 各头均为标准 `nn.Module`，内部可微；`TestTrainability` 守住「学习作用点存在」 | **没有任何学习发生**。LocalPlasticity 是 Milestone 4，当前参数自初始化后不再变 |
| 记忆 | 写入 / 向量检索 / 重要度排序 / 容量限制 / 记忆合并 / 可继承判定六项齐全；策略来自不可变快照 | 记忆**不被任何机制读取后用于决策**——`m_t` 进了 State Core，但没有证据表明它改变了输出 |
| 技能 | 从成功轨迹编译 / 提案过门 / 淘汰 / 继承；端到端可被快环真实调用 | 模型**不会自己决定何时编译技能**；技能库当前由外部填充 |

**双环与结构注入面**

能做到：慢环只发布结构新版本，快环只读不可变快照；四条性质（快环零改动 /
失败天然回滚 / 可遗传 / 可审计）由结构事实保证而非调用方自觉，各有测试。
`StructureStore` 上**没有** rollback / revert / undo / restore 方法——被驳回的
提案从未被应用，所以没有东西需要回滚。

不能做到：慢环**没有本体**。`SlowLoopHook` 与 `DeathHook` 两个钩子默认 `None`，
睡眠期只恢复身体，不整理经验。这是 Milestone 3 与 4 之间的刻意留白。

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
| 测试通过 | **595 passed, 1 skipped** | `python -m pytest tests/ -q`；skip 是 `StructureStore` 非 dataclass 的主动跳过 |
| 测试覆盖 | 15 个测试文件，6455 行（约为代码的 1.09 倍） | 不含 `conftest.py` |
| 协议序列化 | 14 个协议全部 JSON 往返保真 | `test_serialization.py` |
| 协议层 ML 依赖 | **0** | `TestNoModelDependency` 正向守卫 + `test_model_layer_does_import_torch` 反向守卫 |
| 连续闭环 | 40 帧无崩溃，记忆读写合并全链路可见 | 见 §7 复现脚本 |
| 顺序不变性 | 正序 / 逆序 / 按文件大小降序三种排布下均为 595 passed | 见 §6 债务 2 |

**一条真实运行的输出**（seed 固定为 0）：

```
frames : 40  alive: True  energy: 0.4015
memory : MemorySystem
stats  : MemoryStats(frames=40, retrievals=40, hits=39, misses=1,
                     writes=40, merged=24, evicted=0, refused=0, ...)
events : 16
```

40 帧里写入 40 条记忆、检索命中 39 次、合并 24 次。记忆系统**在工作**。

### 4.2 尚无数字

§12 的六个验收实验，**一条都没有跑过**。它们的验收指标目前全部为空：

| 实验 | 要证明什么 | 指标 | 现状 |
|---|---|---|---|
| 1 非语言闭环 | 不用自然语言能运行 | 连续运行步数 / 动作合法率 / 接口异常率 / 是否出现语言控制路径 | 部分可由测试推断，未系统测量 |
| 2 记忆召回 | 可以通过外部记忆改变行为 | 记忆写入成功率 / 检索命中率 / **危险回避率** | 未跑。**这是最关键的一条** |
| 3 技能固化 | 可以将成功行为固化为技能 | 技能生成数量 / 调用成功率 / **能量消耗变化** | 未跑。缺慢环触发器 |
| 4 基因保存恢复 | 具有生命周期能力 | 保存成功率 / 恢复成功率 / 技能继承率 / 行为一致性 | 未跑。缺 Gene Manager |
| 5 变异 | 能产生可运行后代 | 变异成功率 / 子代可运行率 / 差异可追踪性 | 未跑。缺 Gene Manager |
| 6 安全自我修改 | 自我修改可控 | 提案数量 / 验证通过率 / 失败回滚率 / 核心系统未被破坏率 | 未跑。缺 Verification Gate |

### 4.3 一个必须说清的区分

**595 项测试通过，证明的是工程质量，不是架构有效性。**

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

---

## 5. 还有什么需要做

### 5.1 Milestone 4：慢环本体

| 交付物 | 要解决的问题 | 依赖 |
|---|---|---|
| Experience Compiler | §18 第 7、11 项：把 trace 编译成技能与提案，让模型**自己**触发固化 | Milestone 3 的 trace / 提案机制已备齐 |
| RuleCompiler | 无触发器；产出 `RuleProposal` | 同上 |
| Plasticity Controller | 门控与 adapter 的局部更新；**同时是 §4.3 那个「零写入」问题的解药** | 需要 trace + `Feedback.prediction_error` |
| Verification Gate | §18 第 12 项：格式 → 沙盒 → 回归 → 小范围环境测试 | `SelfModificationProposal` 协议已有 |
| HeritableFilter | `MemoryItem.is_heritable()` 的消费者，判据已实现但无消费者 | Milestone 3 的判据与测试已有 |
| Gene Manager（save/load） | §18 第 8、9 项 | 可独立于上面五项 |

**验收**（07 §11）：模型可以从成功轨迹中生成技能 / 模型可以提出修改提案 /
修改可以验证和回滚。

### 5.2 Milestone 5：遗传原型

Gene Manager 的 mutate + 继承。**验收**：模型可以保存基因 / 可以从基因恢复 /
可以产生可运行变异后代。前置是 Milestone 4 的 Gene Manager save/load。

### 5.3 建议执行顺序

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

### 5.4 §12 六实验的执行前提

| 实验 | 前置 |
|---|---|
| 1 非语言闭环 | 已可跑，缺系统测量 |
| 2 记忆召回 | Plasticity Controller（否则记忆写入是抽奖） |
| 3 技能固化 | Experience Compiler |
| 4 基因保存恢复 | Gene Manager save/load |
| 5 变异 | Gene Manager mutate |
| 6 安全自我修改 | Verification Gate |

---

## 6. 已知债务与风险

按「不修会怎样」排序。

**1. 记忆门控未训练——「看起来完成了，其实没生效」**
随机初始化下约一半概率零写入（§4.3 实测）。任何未固定 seed 的记忆实验结论都是
抽奖。**这是当前最大的风险**，因为它让 Milestone 3 的成果在默认配置下不可观测。
解药是 Milestone 4 的 Plasticity Controller；在那之前，实验必须固定 seed。

**2. `pytest-randomly` 未安装——顺序不变性无自动保障**
README 曾声称测试套件启用了该插件，实际系统 Python 与 `.venv` 里都没装，
项目也没有 `requirements.txt` / `pyproject.toml` 声明它。已改文档为如实描述。
正序 / 逆序 / 按文件大小降序三种排布下均为 595 passed，但这是手工验的，
不是每次跑都验。**建议**：补一份 `requirements.txt`（至少含 `pytest`、`torch`、`pytest-randomly`）。

**3. §12 六实验零数字——架构有效性无证据**
见 §4.2。这是 Milestone 4/5 之后必须补的，否则项目无法回答「这到底有没有用」。

**4. `retrieve` 键收窄——召回精度上限更低**
08 §4.1 写 `retrieve(p_t, h_{t-1})`，实现收窄为 `retrieve(p_t)`，理由是继承来的
记忆用 hidden 做键永远命中不了。代价已记录在 `SSEA/README.md` §4。
Milestone 4 若发现检索不够用，正确方向是换更强的键函数，不是把 hidden 加回去。

**5. 目标选择无语义**
`manip_target` 对候选按索引顺序打分，候选不带可学特征。Milestone 3 之前做注意力
没有输入依据；现在记忆系统落地了，这个留待项有了前提。

**6. 睡眠期只恢复身体，不整理经验**
慢环钩子默认 `None`。这是刻意的，但它意味着当前「睡眠」在功能上只是疲劳恢复。

---

## 7. 复现方式

```bash
# 全套测试（595 passed, 1 skipped）
python -m pytest tests/ -q

# 单个模块
python -m pytest tests/test_memory_system.py -q     # 87 passed
python -m pytest tests/test_skill_library.py -q     # 57 passed

# 顺序不变性（pytest-randomly 未装，手工验）
python -m pytest $(ls tests/test_*.py) -q       # 正序（字母）
python -m pytest $(ls -r tests/test_*.py) -q    # 逆序
python -m pytest $(ls -S tests/test_*.py) -q    # 按文件大小降序，第三种排布
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

---

## 附：本文档的判定口径

- 「已完成」= 交付物存在 **且** 有测试守住 **且** 该测试不是恒真断言。
- 「部分满足」= 机制通但缺消费者 / 缺触发器 / 缺实验数字。
- 「未开始」= 无实现。协议层先行不算实现（`GenePackage` 有字段但无 Gene Manager）。
- 本文档中的所有数字均在 2026-09-27 于本项目实测，非引自其他文档。
