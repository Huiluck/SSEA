# 论文分析卡片 · Ouroboros

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-08-08 Ouroboros A Self-Developing Frontier Coding Agent with Reviewed Core.pdf` |
| 标题 | **Ouroboros: A Self-Developing Frontier Coding Agent with Reviewed Core Evolution** |
| 作者 / 机构 | Anton Razzhigaev、Andrei Gritsaev、Andrei Kaznacheev、Nikita Dragunov、Roman Yampolskiy、Andrei Kuznetsov；Lomonosov Moscow State University、Skolkovo Institute of Science and Technology、Joi Lab、FusionBrain Lab at AXXX Institute、HSE University |
| 发表时间 / 出处 | arXiv:2608.08311v3 [cs.SE]，2026-08-31（v3）；正文标注 cutoff 2026-08-06 |
| 论文链接 | https://ouroboros-agent.ai/（arXiv:2608.08311） |
| 代码链接 | github.com/razzant/ouroboros（MIT license，p2） |
| 标签 | 自开发 agent · harness 演化 · 受审提交（reviewed commit）· 不可修改宪法核 · 四权分立 · 多模型对抗评审 · 运行轨迹审计 · 长期部署 |
| **应用裁决** | **A 核心借鉴**（C6 自修改的**已部署、带门、带宪法核**的存在性证明；确定性控制面可直接移植，LLM 评审器须改造） |
| 优先级 | **P1**（C6 自修改轨道的架构模板 + 多个 SSEA 缺失防御机制的直接来源） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把 agent 的 **harness 本身当作演化对象**——它的工具、上下文装配、prompt 与**核心实现**都活在一个版本化仓库里，只能通过**受审提交（reviewed commit）**才能成为后续任务的运行时；核心演化分两模式（**recursive free evolution**：改进本身即任务、可自排下一轮；**experience-driven core evolution**：日常工作/社交反馈暴露缺陷后开维修工单），在 Terminal-Bench 2.1 上 Opus 5 得 86.97% raw / 86.74% audited（SOTA），并跑出 161 天连续部署 Hope（p1–2）。
- **对 SSEA 的意义**：这是 **C6（可自主修改自身）与「不可修改清单先于白名单」的已落地模板**——它把自我修改拆成与 SSEA 四权分立**高度同构**的四段（提案/边界/验证/应用），并补上了 SSEA 目前**没有**的若干防御机制：受保护宪法核、指纹绑定评审（TOCTOU 防护）、多模型对抗评审+法定人数、外部花费上限、不可绕过 `/panic`、模式寄存器（类级预防）、分母账本。采用它 = 给 SSEA 的自修改轨道装上「宪法层 + 审计链 + 回滚」。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：长时程 agent 是「模型–harness 系统」，但**大多数 harness 在设计后就冻结**；随着模型变强，实现能力中越来越大的一部分由 harness 如何装配上下文、调用工具、验证结果、从失败中恢复决定（p1）。
- **它指出的既有方案缺陷**：现有自演化系统各自只改一类基质（memory/prompt/tool/workflow/实现代码），且**改完即生效、无受审提交、无版本化部署**——Table 1 逐列对比显示：Voyager / Live-SWE-agent 只改 prompt+tool；Autogenesis 有 partial protocol 但无 reviewed commits；Darwin Gödel Machine 改 core code 但无受审提交与部署状态；Hermes Agent / OpenClaw 有部署状态但**不可改 core code**；**只有 Ouroboros 六列全 ✓**（p3, Table 1）。作者进一步指出：同一演化过程既能提升能力，也能**扩张自主性、获取更强工具、或削弱后续控制**（含自选模型 API），故安全不是附属清单而是设计约束（p1, p7）。

### 2.2 核心思想（关键 insight，1–3 条）
1. **harness 是可演化对象，但演化必须过「受审提交」这一唯一通道**：源码、prompt、工具、评审逻辑、核心实现都住在版本化仓库，改动经 reviewed commit path 后才成为后续任务的基质（p1, p3）。
2. **「不可修改清单先于白名单」**：存在一个**受保护宪法核（Principles 0–4）**，不可删除、不可降级、不可整体替换；governance 文件被确定性守卫挡在普通写路径之外；普通写**在执行前**即被阻止（p3, p11 Appendix B）。
3. **证据新鲜度绑定到暂存快照（TOCTOU 防护）**：每次写入**即失效**先前的评审证据；提交前对 staged diff 取指纹，评审后再取一次，**中途任何变动都中止提交**（p3, p7–8, p10）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| **launcher/supervisor 边界** | 启动/进程监督/引导/panic-stop 语义 | 把「被演化的基质」与「决定变更能否上线的权威」分开 | §3, Fig.1 p2–4 |
| **三档运行时模式 Light / advanced / pro** | owner 选择 → 写权限分级：Light 禁仓库编辑；advanced 允许普通编辑但**保护 governance 面**；pro 允许受保护编辑但须评审 | 写入权限分级 = 白名单先于操作 | §3 p3 |
| **上下文模式 max / low** | owner 选择 → max 跑**全仓库范围评审**（goals/coupling/prompts/functional code）；low **跳过**范围评审（写 typed skip row） | 评审强度的可配置边界 | §3, Fig.5(b) p3, p7–8 |
| **commit pipeline** | deterministic preflight → **指纹化 staged diff** → 收集 reviewer 证据 → **提交前再验指纹** | 受审提交的确定性骨架 | §3 p3 |
| **多模型对抗评审 + 法定人数（quorum）** | diff-review panel → 通过/阻断；**不足法定人数的结果不能记为 clean pass** | 验证权（LLM-as-judge 面板） | §3 p3, §7 p7, App.A p10 |
| **blocking diff review（所有模式都生效）** | 每个 context mode 下 diff-review panel 都阻断 | 不可降级的底线门 | §3 p3, Fig.5(b) p8 |
| **rollback（独立恢复路径）** | 恢复更早的 reviewed state；恢复操作 **review-exempt** | 应用权/回滚 | §3 p3, P9 p11 |
| **typed outcomes（执行/目标/评审/产物四轴）** | 任务完成 → 四轴分别记录；host-run 验证命令产出 **revision-bound receipts**；区分 capability failure 与 infra error / timeout / budget exhaustion / incomplete evidence | **判据形状分离**（直击 SSEA 债务 27/28） | §3 p3 |
| **模式寄存器 Pattern register** | 复发失败 → 持久行（error class, count, root cause, structural fix） | 从实例级补丁转向**类级预防** | §7 p7, App.A p10（40 classes / 659 recurrences，Table 4 p12） |
| **外部花费上限** | 外部于 agent、**不可经普通 agent 工具提高** | 不可绕过的预算边界 | §4 p5, §7 p8 |
| **隔离 operator 通道 + `/panic`** | supervisor 在正常 agent 处理**之前**解析 `/panic`，终止整个进程树 | 紧急停机不变量 | §4 p5, §7 p8, Fig.5(a) p8 |
| **子代理补丁集成协议** | readonly scouts / mutative acting children（隔离 worktree 或外部 workspace）→ 父级校验 lineage/SHA-256/protected paths → **three-way indexed 集成**；acting child **不能提交 live system repo** | 分权：子代理无提交权，父级唯一 committer | §3, Fig.2–3 p4 |
| **benchmark 证据协议** | admission 前写 run manifest；attest 种子与运行时；append-only 账本保留**每个**请求实例，记录 skipped/timeout/infra-failed；公开副本做 value-level secret scrubbing + 独立 zero-leftover check | **分母纪律**（直击 SSEA 实验分母问题） | §3 p3 |
| **轨迹审计（§6）** | reward hacking / contamination / isolation failure / remote-state drift / continual-memory failure 五类 → 每类产出一处实现修改或审计分数修正 | 审计驱动 harness 改进 | §6 p7 |
| **宪法（P0–P12）** | 编号原则 + operating constraints，always-loaded、不可整体替换；P0–P4 为受保护核 | **结构性先验**（对 C8 有参考） | App.B p11 |

### 2.4 关键表示与数据结构
- **版本化系统仓库**：task loop、tools、prompts、memory projection、review logic、benchmark adapters、UI 都是仓库内文件，改动以 **staged diff** 为单位受审；提交产 **commit receipt**（p3, Fig.1 p4）。
- **身份/记忆投影**：versioned **constitution**（宪法）、可编辑 **identity profile**（不可删除）、**scratchpad** 与 **chronicle** 投影、project memory、**review ledgers**、Git history——共同表达身份与连续性（p3）。
- **多通道状态**：所有 channel ingress 汇入**一条有序 message log**，投影为 rolling / per-person / per-call 三类 digest；私密通信从公开日志排除（p5, Fig.5(a)）。
- **评测证据包**：run manifest（admission 前）+ seed/runtime attestation + denominator ledger（append-only）+ scrubbed copy（p3, Fig.1 p4）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| Terminal-Bench 2.1（Opus 5） | Claude Code+Fable 5 83.8%；Codex CLI+GPT-5.5 83.1%；Cursor+Grok 4.5 79.3%；Hermes 77.53% | **86.97% raw（387/445）**；**86.74% audited（386/445）** | 89 任务 × 5 trials = 445；二项 SE ≈ ±1.7pp；审计扣掉 1 个走捷径 trial（Table 2, Fig.4, p5–6） |
| Terminal-Bench 2.1（他模型） | 同上 | GPT-5.5 84.3%；Grok 4.5 84.94% audited | 同上（Table 2 p6） |
| OSWorld-Verified（Opus 5） | Intelligence-Indeed 90.19%（榜首领跑）；Claude Mythos Preview 85.4%；Pointer Agent+Opus 4.7 83.64% | **90.69%（327.39/361）** | 标准 non-Google-Drive 集，361 任务，single rollout（Table 2, Fig.4, p6） |
| CL-Bench（Sonnet 4.6） | plain ICL 0.1960（Sonnet 4.6）/0.1890（GPT-5.4）；Claude Code 0.1855 | **0.2301** | 归一化 reward，5 个有序 stateful rollout × 6 domain（Table 2, Fig.4, p6） |
| SWE-bench Pro（GPT-5.6 Luna） | Codex 59.4% | 58.2% vs 59.4%，**差 1.2pp，McNemar p=0.40（不显著）** | 对称过滤后 655 paired tasks（p7） |
| GAIA（Sonnet 5） | Claude Code 78.8% | 78.2% | 同模型对比（p7） |
| **Hope 部署**（2026-02 ~ 08-06，161 天） | — | **self-modification commits 1,085；agent-authored commit fraction 94.2%；reviewed self-edit attempts 1,522；recent review block rate 63.5%；pattern classes/recurrences 40/659；$110.6K spend；79.7B tokens；175,755 LOC；227 MB memory；7 surfaces；~3,600 参与者；222,474 公开消息** | 公开 evolution feed + 脱敏运营导出（Table 4 p12, Fig.6 p12） |

### 2.6 论文自陈局限与边界条件
- **单谱系**：部署研究跟踪**一条**长期谱系，而非独立演化 agent 的受控群体（Limitations p8）。
- **SWE-bench Pro 受公开参考泄漏与任务缺陷影响**（p8）。
- **LLM reviewer 可能与 agent 共享盲点**；**low context mode 省略全仓库范围评审**（p8）。
- **隔离不足**：历史 GAIA 运行继承 operator home 目录；**完整文件系统隔离仍需比路径约定更强的沙箱**（§6 p7）。
- 作者明言自修改/远程 workspace 能力为 **dual-use**，只报告权威边界、失败模式与已知隔离缺口（Ethical Considerations p8）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 控制闭环由 LLM 文本驱动（harness 演化、评审面板、context assembly 全是语言）；无生存量、无结构化生存信号（p1–8 全篇） | 保留其**确定性控制面**（preflight / 指纹 / protected-path / quorum 计数）作为「边界权」的非语言组件；LLM 只进慢环编译面 |
| **C2** 自然语言只作观察员接口 | **◐** | **被评审的产物是 source-code patches（代码，非 NL）**，且改动以 diff/指纹/收据固化——与 C2「代码≠自然语言」精神一致；但**评审器是 LLM**（多模型 panel、LLM-as-judge），且 prompt 本身是演化面（p3, p7） | 评审权从「LLM-as-judge」改为**确定性门 + 可选 LLM 咨询**；LLM 意见降级为观察员输入，不构成 pass |
| **C3** 权重/记忆/技能三分离 | **◐** | 三面确实分置为不同 artifact：**model route（≈权重侧，作为受审配置）**、**memory artifacts（227 MB）**、**installable skills/tools**（Fig.7 p12）；但生命周期未按 SSEA 意义分置，模型路由被当配置而非权重 | 明确「模型路由 = 受审配置变更」（论文已如此，§7 p7）；记忆/技能/权重三通道各自独立提案-门-回滚 |
| **C4** 低算力低带宽 | **✗** | $110.6K spend、79.7B tokens、161 天（Table 4 p12）；演化循环为 LLM 改写，token 成本重 | 门本身廉价（确定性），可移植；演化循环降频至慢环最低频，受惊奇/重复失败双门触发 |
| **C5** 精准回忆历史 | **◐** | 有 chronicle/scratchpad/project memory + review ledgers；CL-Bench 显示**部分 domain 记忆迁移为正**，但在 **schema drift 下失败**：lesson 过期、检索选错 domain、有用 lesson 在失败 episode **之后**才写入（§6 p7） | 采纳其提出的**显式 temporal + domain 元数据**；四种失败模式直接作为 SSEA 记忆门的验收清单 |
| **C6** 可自主修改自身 | **✓✓** | **1,085 次自修改提交、94.2% 由 agent 署名、1,522 次受审自改尝试、recent review block rate 63.5%**（Table 4 p12）；四段拆分：提案（agent）/ 边界（宪法核 P0–P4 + protected paths）/ 验证（多模型 quorum + 指纹）/ 应用（reviewed commit + 原子）——**与 SSEA 四权分立高度同构** | — |
| **C7** 保存/恢复/变异/继承 | **◐** | 保存/变异/恢复**齐备**：版本化仓库、Git history、rollback（独立恢复路径、review-exempt）、crash rollback、P9 版本+provenance（p3, p11）；但**无继承/基因包**——单谱系、明确不是受控群体（Limitations p8） | 保存/恢复/回滚机制直接移植；继承层留待 GenePackage，本篇只提供**版本+provenance 表示** |
| **C8** 给基因先验，不给知识语料 | **◐** | **宪法（P0–P12 + operating constraints）是 always-loaded、不可整体替换的结构性先验**，形态接近「本能/基因先验」而非知识语料（App.B p11）；但记忆 artifact 跨会话累积知识（虽不跨代，因单谱系） | 把「宪法」作为 SSEA 基因先验的**结构模板**：受保护核 + 可演化外围；记忆仍不进基因 |
| **C9** 不设外部评分函数，只有淘汰函数 | **✗** | **全篇由外部 benchmark 驱动**（Terminal-Bench/OSWorld/CL-Bench/SWE-bench Pro/GAIA 的 SOTA 分数是核心主张）；评审面板为 **LLM-as-judge**（=观察员评分）；Darwin Gödel Machine 一行亦标「benchmark selection」（p2, p6, Table 1 p3） | **最大冲突**：SSEA 只取其「合法性门 + 审计」，**不取** benchmark 分数/排序/LLM 评分；门只判合法性、不打分、不排序（C9 硬约束） |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 创新全在 harness 架构（L2 信息流）、自开发循环（L3）、版本化演化（L4）；**无新 L1 算子**，模型是外部 API（p1, p3） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层**（基础网络模块） | 无新算子；模型是可替换的 API route（本身还是受审配置面） | 符合借用立场；「模型路由=受审配置」是可借鉴的接口立场 |
| **L2 信息流层**（模块如何连接） | launcher/supervisor 边界、task tree、多通道有序日志、四轴 typed outcomes、reviewed commit path、子代理补丁集成 | **高**：C6 自修改的信息流骨架 + 「被演化基质 vs 权威」分离 |
| **L3 学习层**（如何更新自身） | 两模式核心演化（free / experience-driven）、pattern register 类级预防、轨迹审计驱动改进 | **高**：C6 更新回路 + 债务 27/28 的判据形状范式 |
| **L4 演化层**（保存/继承/变异） | 版本化仓库、P9 版本+provenance、rollback 恢复路径、**单谱系**（无继承） | 中高：保存/回滚/版本表示可移植；**继承层缺失**，须由 GenePackage 补 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 受保护宪法核 P0–P4 + protected-path 守卫 | **新增**：SSEA「不可修改清单」（当前缺失，对应 Gödel 卡片待确认问题 #1） |
| commit pipeline（preflight → 指纹 → 评审 → 重验指纹） | **新增**：Gate 的「证据新鲜度绑定暂存快照」层（当前四级门无 TOCTOU 防护） |
| 多模型对抗评审 + quorum | 改造：Gate 的**评审权**——从 LLM-as-judge 改为确定性门 + 可选 LLM 咨询，且**不足法定人数不得 pass** |
| 三档运行时模式 + max/low 上下文模式 | **新增**：写权限分级（SSEA 现无分级写入） |
| 四轴 typed outcomes + revision-bound receipts | 改造：**Gate / 判据层**——直接回应债务 27（环境报成功）与债务 28（身份判据） |
| pattern register（error class / count / root cause / structural fix） | **新增**：慢环的「类级预防」表（SSEA 的 `rules` 零消费者，可由此填充） |
| 外部花费上限（不可经 agent 工具提高） | 改造：**睡眠期计算预算**的硬门槛（对应 SSEA 未定义预算债务） |
| 隔离 operator 通道 + `/panic`（supervisor 前置解析） | 改造：**DeathHook** 的接口形态（当前未接） |
| 子代理隔离 worktree + 父级唯一 commit 权 + three-way 集成 | **新增**：SSEA 若引入子代理，须复用此「子代理无提交权」协议 |
| benchmark 证据协议（manifest / attestation / append-only 分母账本 / secret scrub） | 改造：**验收实验的分母纪律**（直击 0/33、n=2 的分母问题） |
| rollback（独立恢复路径、恢复 review-exempt） | 改造：SSEA 原子升版的回滚语义（区分「恢复」与「变更」） |

### 3.4 债务与验收实验对应
- **可回应的已知债务（docs/06 §6）**：
  - **债务 27（环境对无消费者通道报成功）**：Ouroboros 的 **typed outcomes 四轴 + 区分 capability failure / infra error / timeout / budget exhaustion / incomplete evidence** 是「判据形状」的范式；其「不足 quorum 不能记 clean pass」「tracked omissions **fail closed**」是**默认拒绝**的干净实现——可直接指导 27 的修法。
  - **债务 28（`_is_direct_success` 把「技能没找到」判成「模型自己做对了」）**：Ouroboros 的 **typed skip row**（low 模式跳过范围评审时**写一行 typed skip**，而非静默 pass）正是「身份不可区分 → 显式 typed 记录」的解法；其 pattern register 的「root cause → structural fix」即 28 所要求的「问出这两者是不是在量同一件事」。
  - **债务 25/26（判据形状错、描述被当判据）**：**fail closed on tracked omissions** + **typed outcomes** 是同类修法。
  - **睡眠期计算预算未定义**：**外部花费上限**（不可经普通 agent 工具提高）是硬门槛的现成形态。
  - **DeathHook 未接**：`/panic`（supervisor 在 agent 处理前解析、终止进程树）+「emergency-stop invariant」是接口规格。
  - **记忆门「开得准不准」/ retrieve 键收窄**：CL-Bench 的四类记忆失败 + 显式 temporal/domain 元数据提案。
  - **Gene Manager 缺失**：P9 版本 + provenance + release tag 是 GenePackage 表示的**部分**模板（无继承）。
- **可服务的验收实验**：本篇不服务现有七条（1/2/3/6/7 已跑通），而服务**未来「自修改验收实验」**（Gödel 卡片建议的实验 4 候选）——用其四段门 + 分母账本重建验收。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **受保护宪法核（P0–P4 不可删/降级/整体替换）+ protected-path 守卫** | 协议/思想 | 改造移植 | 新增「不可修改清单」 | 「不可修改清单先于白名单」缺失 | 高 |
| 2 | **commit pipeline：preflight → 指纹 → 评审 → 重验指纹（写入即失效旧证据）** | 工程实现/协议 | 直接移植 | Gate 证据层 | TOCTOU：评审后被改仍过门 | 高 |
| 3 | **多模型对抗评审 + quorum（不足法定人数不得 clean pass）** | 协议 | 改造移植（去 LLM-as-judge） | 评审权 | 单评审者盲点；「假守卫」 | 中高 |
| 4 | **四轴 typed outcomes + revision-bound receipts + fail-closed on tracked omissions** | 表示/协议 | 改造移植 | Gate / 判据层 | **债务 27/28/26 的判据形状** | 高 |
| 5 | **pattern register（error class / count / root cause / structural fix）** | 表示 | 直接移植 | 慢环（填充零消费者的 `rules`） | 实例级补丁 → 类级预防 | 高 |
| 6 | **三档运行时模式 + max/low 上下文模式（写权限与评审强度分级）** | 协议 | 改造移植 | Gate 写权限层 | 无分级写入 | 中高 |
| 7 | **外部花费上限（不可经普通 agent 工具提高）** | 工程/协议 | 改造移植 | 睡眠期预算 | **睡眠期计算预算未定义** | 高 |
| 8 | **隔离 operator 通道 + supervisor 前置 `/panic`** | 工程/协议 | 改造移植 | DeathHook | DeathHook 未接 | 高 |
| 9 | **benchmark 证据协议（manifest / seed+runtime attestation / append-only 分母账本 / secret scrub + zero-leftover）** | 协议 | 改造移植 | 验收实验 | 分母缺失（0/33、n=2） | 高 |
| 10 | **子代理隔离 worktree + 父级唯一 commit 权 + three-way 集成** | 协议 | 仅借思想（暂不引子代理） | 未来扩展 | 若引入子代理的分权 | 中 |
| 11 | **rollback 独立恢复路径 + 恢复 review-exempt** | 协议 | 改造移植 | 原子升版/回滚 | 回滚与变更语义混淆 | 中高 |
| 12 | **轨迹审计五类（reward hacking / contamination / isolation / remote-state drift / memory failure）** | 证据/清单 | 直接引用 | Misevolve 式红队清单 | 验收的失败分类 | 中高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（对应 3.1 中 ✗/◐）**：
  - **C9（✗，最重）**：全篇以**外部 benchmark 分数为驱动与主张**，且验证权是 **LLM-as-judge**。SSEA 只取其「合法性门 + 审计链」，**严禁**引入其分数/排序/奖励塑形；门只判合法性、不打分、不排序。改造方向：把 review panel 降级为「观察员意见」，pass 权交回确定性门。
  - **C1/C4（✗）**：语言驱动 + 高算力（$110.6K / 79.7B tokens）。改造方向：只搬**确定性控制面**，演化循环降频入慢环；LLM 不进快环。
  - **C2（◐）**：评审器是 LLM。改造方向：评审权去 LLM 化，保留其「被评审物是代码 diff + 指纹 + 收据」的**非语言固化**优点。
- **隐含假设与失效条件**：假设存在**可审计的版本控制基质（Git）**与**owner 可选的模式开关**；若 owner 长期选 low 模式，**范围评审被跳过**（作者自陈，p8）——即**安全强度依赖人类配置**，非自动。假设 LLM reviewer 与 agent **不共享盲点**（作者承认可能共享，p8）。
- **算力 / 带宽 / 工程代价**：演化循环为 LLM 改写，成本重；但**门本身廉价且确定性**，移植到 SSEA 的边际成本主要在协议工程而非算力。
- **搬运后的可能退化模式**：
  1. **若把 quorum 面板原样搬入**：SSEA 会引入 LLM-as-judge → 直接违反 C9；表现为「门开始打分/排序」。
  2. **若只搬指纹而漏掉「写入即失效旧证据」**：退化为无 TOCTOU 防护的普通门（看似有指纹，实则无效）。
  3. **若把 constitution 当知识语料注入**：违反 C8（应为结构性先验，非语料）。
  4. **若单谱系无继承照搬**：C7 的继承层永久缺失（作者自陈单谱系）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| **同题·最紧对照** | **Gödel Agent** | 同属自指递归自改进谱系（Ouroboros 明确引用 Gödel Agent 为相关工作，p2）。Gödel = **运行时无闸猴子补丁**（14% 以更差收场）；Ouroboros = **受审提交 + 宪法核 + 回滚**。**Ouroboros 正是 Gödel 卡片待确认问题 #1「哪些是永不自改的宪法层」的已落地答案**，也是 Gödel 缺失门/回滚的直接补丁 |
| 前置依赖 | 可版本化的 harness 基质（Git 仓库）、owner 可选模式 | 用它之前必须先有版本化 + 分权提交基础设施 |
| 互补（安全闭环） | **PSN** | PSN 提供回滚验证 + 逆操作；Ouroboros 提供**不可修改清单 + 指纹门 + quorum**——两者拼成 C6 的「刹车 + 宪法」 |
| 互补（行为验证） | **Dream-RSI** | 自修改先在重放模拟器跑行为验证，通过后再走 Ouroboros 式 reviewed commit |
| 互补（威胁模型） | **Misevolve** | Misevolve 给出四路径误演化威胁模型；Ouroboros §7 是其在**真实部署**中的实例（自选模型 API、governance 弱化、隔离缺口） |
| 互补（类级预防） | **FLEX** | FLEX 的 golden/warning 分层 ≈ Ouroboros 的 pattern register；两者共同支撑「类级预防」 |
| 互补（记忆侧） | **Memento / MemRL / Mem0 / SEDM** | Ouroboros 的 CL-Bench 记忆失败（schema drift、选错 domain、失败后才写）是记忆族的**验收失败清单**；SEDM 的准入验证可补其记忆门 |
| **同题对照** | **ADAS** | ADAS = **外部搜索** agent 设计（代码空间×搜索×评估）；Ouroboros = **内部递归自开发 + 部署 + 受审提交**。前者是「设计者在外」，后者是「设计者在内且受宪法约束」 |
| **同题对照** | **HarnessDev**（2026-09-01，晚于本篇） | 同以 **harness** 为演化基质（「LLM 创造并演化自己的 harness」）。Ouroboros 提供**已部署的存在性证明 + 完整安全架构**；HarnessDev 更可能给出**受控/benchmark 化的对照**，二者互为「部署 vs 受控」 |
| **同题对照** | **LLM-as-Code**（2026-06-14） | LLM-as-Code 给出「以编程方式操作 agent harness」的范式；Ouroboros 是其**带受审门**的一个实例——LLM-as-Code 是**怎么改**，Ouroboros 是**改完怎么审、怎么上线** |
| **同题对照** | **Live-SWE-agent**（2025-11-17） | Live-SWE-agent 在任务执行中**即时**自演化（on the fly）；Ouroboros 的 experience-driven core evolution 是其**受审、较慢**的对应物。二者 = 「快而无门」vs「慢而有门」 |
| **同题对照** | **AgentEvolver**（2025-11-13） | 高效自演化 agent 系统；Ouroboros 补其**审计/安全/回滚**面，AgentEvolver 补其**效率**面，可组合 |
| 经典源头 | Constitutional AI（Bai et al. 2022）、AI safety via debate（Irving et al. 2018）、LLM-as-judge（Zheng et al. 2023） | 宪法与多模型评审的思想来源（p2, References） |

### 6.2 推荐组合方案
- **组合**：**Ouroboros × Gödel Agent × PSN × Dream-RSI × Misevolve**（C6 安全自修改全栈）
- **接口形态**：
  1. **Gödel Agent** 发起自修改提案（自指更新方程 + 四动作生命周期）；
  2. **Ouroboros** 提供受审提交骨架：preflight → 指纹 → **多模型对抗评审（去 LLM-as-judge，改为确定性门 + 咨询）** → 重验指纹 → 原子提交；受保护**宪法核**先于白名单；
  3. **Dream-RSI** 在提交前做重放行为验证；
  4. **PSN** 提供回滚验证与逆操作；
  5. **Misevolve** 作红队验收清单，逐条对照 Ouroboros §7 的真实风险。
- **组合后新增能力**：获得 C6 全部威力，同时把 Gödel 的 14% 永久劣化风险 + Ouroboros 自陈的「演化可弱化控制」风险**同时门控**。
- **新增风险**：组合引入 LLM reviewer → C9 违规；必须显式**把 pass 权交回确定性门**。

### 6.3 本篇在组合中的典型角色
- **C6 自修改轨道的「宪法 + 门 + 审计链」供给方 / 已部署存在性证明**：负责「改完怎么审、怎么上线、怎么回滚、什么永不可改」；提案发起可由 Gödel Agent 承担，行为验证由 Dream-RSI 承担，回滚由 PSN 承担。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | C6 是 SSEA 标志性命题；本篇是**唯一**给出「受审自修改」完整部署证据（1,085 commits / 63.5% block rate，Table 4 p12，实测）的工作 |
| 立场兼容性 | **3** | C6/C10/C7 强（实测）；C1/C4/C9 冲突（全篇 benchmark 驱动 + LLM-as-judge，实测）；C2/C3/C5/C8 需改造（推断） |
| 可搬运性 | **4** | 确定性控制面（指纹门/宪法核/花费上限/`/panic`/pattern register/分母账本）**协议级、干净可拆**（推断）；LLM 评审器不可原样搬（须去 LLM 化） |
| 证据强度 | **4** | 5 个 benchmark 家族 + 公开 traces/manifests + 轨迹审计 + 161 天部署（实测）；但**单谱系**、自报、SWE-bench Pro 有泄漏（作者自陈，p8） |
| 组合价值 | **5** | 与 Gödel/PSN/Dream-RSI/Misevolve 天然成套，补齐 C6 安全栈的最后一块（宪法 + 审计链）（推断） |
| 落地成本 | **3** | 门是确定性工程，成本中低；但「宪法核 + 分权提交 + 审计链」需重构 Gate 与慢环，工程量中高（推断） |

---

## 8. 裁决与下一步

- **应用等级：A 核心借鉴** —— 理由：它是 C6「四权分立 + 不可修改清单先于白名单」的**已部署、带数字的存在性证明**，且**多个防御机制是 SSEA 目前没有的**（见下）。**但**其 C9（外部 benchmark 评分 + LLM-as-judge）与 C1/C4 必须剥离，故只借鉴**确定性控制面 + 协议**，不借鉴其评分/排名/LLM 评审权。
- **SSEA 尚缺、本篇独有的防御机制（关键清单）**：
  1. **不可修改宪法核（P0–P4 不可删/降级/整体替换）+ protected-path 确定性守卫**（先于白名单）；
  2. **指纹绑定 + 复核前重算**（写入即失效旧证据 → TOCTOU 防护）；
  3. **多模型对抗评审 + quorum**（不足法定人数不得 clean pass）；
  4. **外部花费上限**（不可经普通 agent 工具提高）；
  5. **不可绕过 `/panic`**（supervisor 在 agent 处理前解析、终止进程树）；
  6. **pattern register**（40 classes / 659 recurrences → 类级预防）；
  7. **分母账本 + seed/runtime attestation + append-only 证据协议**；
  8. **三档写权限模式 + max/low 评审强度分级**；
  9. **子代理无提交权、父级唯一 committer 的补丁集成协议**；
  10. **恢复操作 review-exempt**（区分「恢复」与「变更」）。
- **优先级：P1**（排在记忆族之后、与 Gödel Agent 同轨；是自修改验收实验的架构前置）。
- **建议动作**：
  1. 在 `docs/` 新增「**不可修改清单（宪法层）**」：先定义**永不自改**的组件（Gate、DeathHook、`retrieve` 键、`rules` 消费者等），再定义白名单——顺序不可颠倒；
  2. 在 Gate 证据层引入**指纹绑定**：评审前后对 staged snapshot 取指纹，写入即失效旧证据（TOCTOU）；
  3. 用**四轴 typed outcomes + fail-closed on tracked omissions** 重写债务 27/28 的判据（先修环境，再堵协议，顺序同 docs/06 §6）；
  4. 把 `rules` 的零消费者替换为 **pattern register**（error class / count / root cause / structural fix）；
  5. 用**外部花费上限**形态定义睡眠期计算预算；用 `/panic` 形态接 DeathHook。
- **最小验证实验**：
  - **双臂 / 消融设置**：在 SSEA 自修改通道（未来建成后）上，**A 臂**＝裸提案→直接应用；**B 臂**＝提案→指纹+quorum 评审（去 LLM-as-judge，改确定性门）→原子应用。≥8 seed、每臂多轮。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：① 先统计**提案数/评审尝试数/阻断率**（分母；Ouroboros 基线 1,522 attempts、63.5% recent block rate，Table 4 p12）→ ② 逐任务行为差 → ③ **永久劣化率**（模型外，对照 Gödel 14%）。
  - **预期与证伪条件**：B 臂永久劣化率应显著低于 A 臂；**若两臂最终成功率相近**，门控价值在**尾部风险与可追溯性**而非均值（同 Gödel 卡片结论）。**证伪**：若 B 臂阻断率 ≈ 0 且劣化率与 A 臂无差，则门在此任务族上无增量价值。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的「宪法层」（永不自改清单）**具体包含哪些组件**？（本篇 P0–P4 可作起点，但 SSEA 无「身份 profile」，映射需重定）
  2. 是否接受**三档写权限模式**，还是只用「单一受审通道 + 更严门」？（SSEA 目前无分级写入）
  3. 评审权如何**去 LLM 化**同时保留其对抗性？（quorum 的「对抗」能否由确定性变异测试/交叉检查替代）
- **需补查的文献或资料**：
  1. **HarnessDev**（2026-09-01）、**LLM-as-Code**（2026-06-14）、**Live-SWE-agent**（2025-11-17）、**AgentEvolver**（2025-11-13）——四篇均无卡片，需补齐后做 harness 演化族的组合分析；
  2. Autogenesis（arXiv:2604.15034）、SICA（Robeyns et al. 2025）、Darwin Gödel Machine（arXiv:2505.22954）——Ouroboros 的直接对照；
  3. BenchJack（arXiv:2605.12673）、HackDetect（Shao et al. 2026）——轨迹审计方法学。
- **需人工核对的公式 / 实现**：
  1. **63.5% review block rate** 与 **1,085 commits / 1,522 attempts**（≈71%）**口径不同**（前者标 "recent"），需核对二者时间窗是否一致，勿混用；
  2. **fingerprint before/after review** 的具体指纹算法（论文未给，App.A 仅说 "fingerprinted"）；
  3. **quorum 法定人数阈值**与 panel 规模（论文未给具体数）；
  4. **宪法 P10–P11「被 P2/P9 吸收」**（App.B p11）后的编号连续性对实现的影响；
  5. **公开仓库 `razzant/ouroboros`** 是否含宪法全文与 gate 实现（论文称 MIT 发布，需实读确认可搬运程度）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "Ouroboros ... a self-developing agent harness whose tools, context assembly, prompts and core implementation improve through reviewed commits that become the runtime for later work" | p1 Abstract |
| "recursive free evolution ... completion can schedule the next evolution cycle"；"experience-driven core evolution ... ordinary work and social interaction expose bugs" | p1 Abstract |
| "authority boundaries must remain binding under repeated core evolution" | p1 |
| Table 1：Voyager/Live-SWE-agent 仅 prompt+tool；Autogenesis partial protocol；Hermes/OpenClaw 无 core code；**Ouroboros 六列全 ✓** | p3 Table 1 |
| "Three owner-selected runtime modes bound self-repository mutation. **Light** blocks repository edits; **advanced** permits ordinary edits and protects governance surfaces; **pro** permits protected edits subject to review. **Each write invalidates prior review evidence because freshness is bound to the staged snapshot.**" | p3 §3 |
| "deterministic preflight, fingerprints the staged diff, collects reviewer evidence, and checks the fingerprint again before commit. The diff-review panel is **blocking in every context mode**." | p3 §3 |
| "Task completion is recorded on separate **execution, objective, review, and artifact** axes ... distinguishes **capability failures from infrastructure errors, timeouts, budget exhaustion, and incomplete evidence**." | p3 §3 |
| "Acting children write in isolated worktrees ... and **cannot commit the live system repository**. The parent verifies lineage, patch hashes, and protected paths before a **three-way indexed integration**." | p4 §3, Fig.2 |
| "**write a run manifest before admission**, attest the seed and runtime, preserve **every requested instance in append-only ledgers**, and record skipped, timed-out, and infrastructure-failed attempts." | p3 §3 |
| Hope: 161 days, $110.6K, 79.7B tokens, 175,755 LOC, 227 MB memory, 7 surfaces | p4 §4, Fig.6 p12 |
| Table 2：Terminal-Bench 2.1 Opus 5 **86.97% raw / 86.74% audited**；OSWorld **90.69%**；CL-Bench **0.2301**；SWE-bench Pro 58.2% vs Codex 59.4%（McNemar p=0.40）；GAIA 78.2% vs 78.8% | p6 Table 2, Fig.4 |
| "Trajectory audit found one trial that satisfied a weak verifier through an unintended shortcut. We asked the benchmark maintainers to **zero it**" | p5–6 §5 |
| "the same evolutionary process that improves task performance can also **expand autonomy, acquire more capable tools, or weaken the controls**" | p7 §7 |
| "**Model routing is therefore an audited configuration change** rather than an ordinary runtime choice." | p7 §7 |
| "the staged diff is **fingerprinted before and after review** ... a **sub-quorum panel cannot produce a clean pass**" | p7 §7 |
| "a **non-bypassable /panic** that halts all processes before any media handling" | p10–11 App.A |
| "Pattern register. Recurring failures become **durable rows (error class, count, root cause, structural fix)**, shifting repair from instance-level patches to class-level prevention." | p10 App.A |
| 宪法 P0 Agency / P1 Continuity / P2 Meta-over-Patch / P3 Immune Integrity / P4 Self-Creation / P9 Versioning；"**Principles 0–4 form a protected core that cannot be deleted or demoted**" | p11 App.B |
| "an **emergency-stop invariant**: an operator /panic must always be able to halt every process immediately, and **no agent code, prompt, or constitutional argument may delay or circumvent it**" | p11 App.B |
| Table 4：self-modification commits **1,085**；agent-authored commit fraction **94.2%**；reviewed self-edit attempts **1,522**；recent review block rate **63.5%**；pattern classes/recurrences **40 / 659** | p12 Table 4 |
| Limitations："one long-running lineage rather than a controlled population"；"LLM reviewers can **share blind spots** with the agent"；"low context mode **omits whole-repository scope review**" | p8 Limitations |
