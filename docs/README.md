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
| [06-status-roadmap.md](06-status-roadmap.md) | **此刻到哪、往哪走**：当前状态、实测数字、未结债务、里程碑路线图、M4 计划、复现方式 |

## 推荐路径

- **第一次接触**：先读仓库根 [README.md](../README.md)（门面），再回到 [01](01-philosophy.md) 建立思想、[03](03-architecture-spec.md) 看规范、[06](06-status-roadmap.md) 看现状。
- **想理解理论根基**：[01](01-philosophy.md) → [02](02-nonverbal-cognition.md) → [03](03-architecture-spec.md) §8。
- **要写代码 / 复现**：[03](03-architecture-spec.md) → [04](04-boundaries.md) → [06](06-status-roadmap.md) 的复现一节；术语拿不准随时查 [05](05-glossary.md)。

## 代码与实验

- 生产代码：[`SSEA/`](../SSEA/)（含 `sse_protocols/` 协议层）
- 测试：[`tests/`](../tests/) ｜ 验收实验：[`experiments/`](../experiments/)
- 当前基线：**910 passed, 1 skipped**；七条验收实验跑通五条（详见 [06](06-status-roadmap.md)）。

> ⚠️ [03](03-architecture-spec.md) §8 的三项裁决是**设计层**修订，尚未落到代码；
> 当前基线仍是裁决前的实现。其中「前瞻预演」有**硬门槛**：必须先定义并实测
> 睡眠期计算预算，才可实现（理由见 §8.3）。

## 历史档案

本篇幅由早期 22 份文档（原始构想、多版任务书、Milestone 0 交付物、进度报告、总览与
整合精读等）整合而成。被合并文档的完整原文保留在 git 历史中，需要时点的完整台账或
逐增量记录时，可用 `git log` / `git show` 取回（指引见 [06](06-status-roadmap.md) 附录 A）。
