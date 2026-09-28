# SSEA 文档

**SSEA — Survival-based Self-Evolving Agent Architecture（生存式自演化代理架构）**

目标：设计一种新的模型架构，在**减少算力与内存带宽消耗的同时，保留语言之下那个
完整的认知基底**（多步规划、因果知觉、情景记忆、技能累积、非语言元认知、内在驱动），
并**明确放弃语言作为认知工具所提供的那部分能力**（精确离散符号运算、递归组合生成、
抽象概念的公共约定、显式自我叙述）。
核心立场：不是「更小的 Transformer」，而是把组织原则从**语言生成**换成**生存控制**；
自然语言只作观察员接口，不进控制闭环。

> **2026-09-28 三项裁决**：① 目标表述替换旧写法「不缩减智力」；② **C9 加「外部」
> 限定**并正式结盟自由能原理 / 主动推理；③ 睡眠期扩为「**回顾编译 + 前瞻预演**」
> 双通路。权威条款见 [03-architecture-spec.md](03-architecture-spec.md) §8，
> 论证依据见 [02-nonverbal-cognition.md](02-nonverbal-cognition.md)。

> 第一阶段（v0.3.1）**不建生态系统**，只建「能进入生态系统的最小生命体」。

## 文档地图（6 篇）

| 文件 | 回答的问题 |
|---|---|
| [01-philosophy.md](01-philosophy.md) | **为什么这样设计**：三个根本困境、范式革命、11 条思想支柱、生态系统构想（含繁衍与「偶然的美好」）、范式分界 |
| [02-nonverbal-cognition.md](02-nonverbal-cognition.md) | **去掉语言后高级认知如何可能**：神经科学与考古证据、六条可借用理论、A1 缺口解答、待裁决岔路口 |
| [03-architecture-spec.md](03-architecture-spec.md) | **动手写代码前的权威依据**：v0.3.1 任务书（Part I）＋双环接口与模糊地带补全（Part II）＋**§8 三项裁决落地**（冲突时以 Part II 为准，其中 §8 优先于 Part II 前七节） |
| [04-boundaries.md](04-boundaries.md) | **边界在哪**：架构原创性、模型/接口/生态边界定义表、第一阶段不做清单 |
| [05-glossary.md](05-glossary.md) | **术语什么意思**：统一名词口径与权威出处（检索用） |
| [06-status-roadmap.md](06-status-roadmap.md) | **此刻到哪、往哪走**：当前状态、实测数字、未结债务、里程碑路线图、M4 计划、复现方式 · **附 C 裁决 → 落地状态总表**（哪些裁决在代码里成立、哪些只是写在纸上）|
| [theory-design-plan.md](theory-design-plan.md) | **理论上的全弧设计**（**提案，不是承诺**）：生态系统、疾病、繁衍、跨代传递边界、地府、归属/爱/尊重、压力的定义、美好的肯定性机制、观察员、种群演化 · 分期**出口判据** · 开放问题登记表 |

## 推荐路径

- **第一次接触**：先读仓库根 [README.md](../README.md)（门面），再回到 [01](01-philosophy.md) 建立思想、[03](03-architecture-spec.md) 看规范、[06](06-status-roadmap.md) 看现状。
- **想理解理论根基**：[01](01-philosophy.md) → [02](02-nonverbal-cognition.md) → [03](03-architecture-spec.md) §8。
- **要写代码 / 复现**：[03](03-architecture-spec.md) → [04](04-boundaries.md) → [06](06-status-roadmap.md) 的复现一节；术语拿不准随时查 [05](05-glossary.md)。

## 代码与实验

- 生产代码：[`SSEA/`](../SSEA/)（含 `sse_protocols/` 协议层）
- 测试：[`tests/`](../tests/) ｜ 验收实验：[`experiments/`](../experiments/)
- 当前基线：**972 passed, 1 skipped**；七条验收实验跑通五条（详见 [06](06-status-roadmap.md)）。
- 技术栈与复现：[toolchain.md](toolchain.md)（运行环境 / 依赖 / 项目四层栈 / agent 工具链 / 复现命令）

> ⚠️ [03](03-architecture-spec.md) §8 的三项裁决是**设计层**修订，尚未落到代码；
> 当前基线仍是裁决前的实现。其中「前瞻预演」有**硬门槛**：必须先定义并实测
> 睡眠期计算预算，才可实现（理由见 §8.3）。

## 论文卡片

- 论文库：[`papers/`](papers/)（**266** 个 PDF）。
- 分析卡片：[`papers/cards/`](papers/cards/)（**62** 张卡，由并发进程持续新增）。逐篇裁决见 [papers/cards/README.md](papers/cards/README.md)——**注意该索引当前只登记 21 行，已过期**（原因与修复建议见应用图谱 §8）。
- **应用图谱**：[papers/cards/SSEA-应用图谱.md](papers/cards/SSEA-应用图谱.md) —— 按 SSEA **当前阶段**回答「哪些论文可用于、以什么形式用、和谁组合」：全量分级总表（62 篇 × 裁决/优先级/搬运粒度 G1–G5/功能槽位 S1–S15）＋ 15 个功能槽位 ＋ 7 个组合方案包 ＋ 5 处待裁决矛盾 ＋ 文献空白声明。
- 生成器：[papers/_tools/gen_card_index.py](papers/_tools/gen_card_index.py) —— 重算应用图谱的总表与计数；若出现没有槽位映射的新卡，**以非零退出码点名它**，使该表不会像卡片 README 索引那样静默过期。

## 历史档案

本篇幅由早期 22 份文档（原始构想、多版任务书、Milestone 0 交付物、进度报告、总览与
整合精读等）整合而成。被合并文档的完整原文保留在 git 历史中，需要时点的完整台账或
逐增量记录时，可用 `git log` / `git show` 取回（指引见 [06](06-status-roadmap.md) 附录 A）。

### 旧编号 → 现文档映射（**本表权威**）

**为什么需要这张表。** 整合只留下了 6 篇（01–06），但正文、代码 docstring 与 `tests/`
注释里仍在用**整合前的旧编号**（`07 §5.3`、`08 §2.1`、`14 §6.3.7` 之类）。实测指向旧编号的
引用共 **163 处**：**35 处**是 Markdown 链接（已经指向现文件，点得开），
**128 处是裸引用**（`14 §6.3.7` 这种，**没有任何跳转**，此前只能靠猜）。
最重的一处是 [05-glossary.md](05-glossary.md)（**62 处**）——而名词表的核心承诺正是
「**出处**：有分歧时以那里为准」，这条承诺此前对它的大部分条目是空头支票。

> 📌 **序号只给整合后的六篇设计文档。** 之后的文档（[theory-design-plan.md](theory-design-plan.md)、
> [Original Project Philosophy.md](Original%20Project%20Philosophy.md)、`Lineage/`）**一律不带序号**——
> 因为 `07`–`19` 已被旧编号占用，给新文件编号会让上面这类引用重新变得歧义。
> **新文件不抢旧号**，是这张表能成立的前提。

**先说清楚能解析到哪一级**——这一点比映射本身更重要：

| 级别 | 覆盖 | 怎么用 |
|---|---|---|
| ✅ **可解析到节** | `07` `08` | 二者分别**整篇**成为 [03](03-architecture-spec.md) 的 **Part I / Part II**，**节号原样保留**。`NN §x` → `[03](03-architecture-spec.md) Part I/II §x` |
| 🟡 **只能解析到文件** | `05` `12` `13` `14` `16` | 被**合并**进现文档，**节号不对应**。要节级原文只能走 git |
| ⚪ **不涉及** | `09` `10` `11` `15` `17` `18` | 现在只以链接出现，已经能定位 |

| 旧编号 | 旧文件名（`64c8921`） | 现文档 | 节级 |
|---|---|---|---|
| **07** | `07-ssea-v0.3.1-charter.md` | [03-architecture-spec.md](03-architecture-spec.md) **Part I** | ✅ 节号保留 |
| **08** | `08-dual-loop-interface-and-gap-closure.md` | [03-architecture-spec.md](03-architecture-spec.md) **Part II** | ✅ 节号保留 |
| 05 | `05-ssea-v0.3-charter.md` | 已被 v0.3.1 任务书取代；其答辩修订并入 [03](03-architecture-spec.md) Part I 的修订背景 | ⚪ |
| 09 | `09-architecture-originality.md` | [04-boundaries.md](04-boundaries.md) **Part A** | 🟡 |
| 10 | `10-boundary-definition-table.md` | [04-boundaries.md](04-boundaries.md) **Part B** | 🟡 |
| 11 | `11-phase1-not-doing-list.md` | [04-boundaries.md](04-boundaries.md) **Part C** | 🟡 |
| 12 | `12-progress-report.md` | [06-status-roadmap.md](06-status-roadmap.md) | 🟡 合并 |
| 13 | `13-milestone4-plan.md` | [06-status-roadmap.md](06-status-roadmap.md) **Part III** | 🟡 约等于，节号未保留 |
| 14 | `14-overview-and-roadmap.md` | [06-status-roadmap.md](06-status-roadmap.md) | 🟡 合并 |
| 15 | `15-glossary.md` | [05-glossary.md](05-glossary.md) | 🟡 表已重排 |
| 16 | `16-project-summary.md` | [06-status-roadmap.md](06-status-roadmap.md) | 🟡 合并 |
| 17 | `17-integrated-synthesis.md` | [06-status-roadmap.md](06-status-roadmap.md) | 🟡 合并 |
| 18 | `18-architectural-philosophy.md` | [01-philosophy.md](01-philosophy.md) | 🟡 |
| 19 | `19-nonverbal-cognition-foundation.md` | [02-nonverbal-cognition.md](02-nonverbal-cognition.md)（另含旧文件 `docs/思想层面的待完善处.md` → 本篇**附录**） | 🟡 未被引用，按标题推断 |
| 01–04 · 06 | `01-vision` / `02-collaboration-scope` / `03-feasibility-v0.1` / `04-phase1-plan-draft` / `06-v0.3-rebuttal` | v0.3.1 **之前**的一代，内容并入 01 / 03 / 04，**几乎不再被引用**（仅 1 处） | ⚪ |

**已逐条核实的节级对应**（只有这四条是查过的，其余不要照推）：

| 旧引用 | 现位置 | 依据 |
|---|---|---|
| `12 §6`（债务台账） | [06](06-status-roadmap.md) **§4 债务现状** | 本篇 §4 自己写着「见旧进度报告 §6」 |
| `14 §5.2`（三种坏数字） | [06](06-status-roadmap.md) **§3.4 读数字的纪律** | 三档标题与内容逐条对应 |
| `16 §3.3`（描述被当判据 / options） | [02](02-nonverbal-cognition.md) **§3.3** | 理论论证整段搬入 |
| `08 §2.1`（结构注入面） | [03](03-architecture-spec.md) **Part II §2.1** | 节号即原号 |

其余节级原文用 git 取回：

```bash
git show 64c8921:docs/14-overview-and-roadmap.md    # 旧编号换成文件名即可
```

> ⚠️ **维护纪律（双向）**：**新增引用一律用现编号**（写成 `[03](03-architecture-spec.md) §8.3`），
> 不要再写旧编号。本表是**用来清零旧账的，不是永久别名表**——它若只增不减，就变成了
> 第二套编号系统，比没有更糟。（同一条纪律的另一个实例见
> [`tests/test_consumer_surface.py`](../tests/test_consumer_surface.py) 的 `NO_CONSUMER_YET`：
> 登记表必须**双向**断言，长了消费者就要移出，否则清单会烂掉。）
