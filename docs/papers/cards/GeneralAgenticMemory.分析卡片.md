# 论文分析卡片 · General Agentic Memory（GAM）

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-11-23 General Agentic Memory Via Deep Research.pdf` |
| 标题 | **General Agentic Memory Via Deep Research** |
| 作者 / 机构 | B.Y. Yan, Chaofan Li, Hongjin Qian, Shuqi Lu, Zheng Liu（北京智源研究院 BAAI、中国人民大学、北京大学、香港理工大学） |
| 发表时间 / 出处 | arXiv:2511.18423v1 [cs.CL]，2025-11-23（Preprint，17 页） |
| 论文链接 | arXiv:2511.18423 |
| 代码链接 | https://github.com/VectorSpaceLab/general-agentic-memory |
| 标签 | 智能体记忆 · JIT 编译（对比 AOT） · 深度研究式记忆构造 · Memorizer/Researcher 双智能体 · 无损 page-store + 轻量 memo 索引 · RL 端到端优化 |
| **应用裁决** | **B 零件采用**（采纳「无损页库 + 有损索引」双层分离与「主动研究式取用」协议；RL 奖励 Γ 与语言载体为冲突件） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：现有记忆系统按 **AOT（Ahead-of-Time）编译**——离线把原始上下文压成轻量记忆、在线只读这份预算好的记忆，必然**信息有损**且结构**静态**、依赖领域启发式；GAM 改按 **JIT（Just-in-Time）编译**——离线只留「简单但有用」的轻量记忆（memo）作**检索导航**，同时把**完整历史无损**存进 page-store，在线由 Researcher 针对请求执行**深度研究**（规划→并行检索→整合→反思）现场合成定制上下文（p1–2）。
- **对 SSEA 的意义**：若采用，SSEA 的记忆轨道从「离线压成一份东西、在线只读」改为「**无损底座 + 有损索引 + 取用时研究**」——直接冲击 SSEA 当前「`retrieve` 键收窄 → 召回精度上限低」与「记忆二级门只有常量阈值」两条缺口，并给出 C5「精准回忆」的一种**可操作解法**：把有损只压到索引、不压到事实源。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**：LLM 智能体的历史（多会话、多步推理与工具调用）快速增长，带来上下文溢出、算力成本与性能退化；记忆系统需在**最小上下文尺寸**下**最大化下游任务完成度**（Def. 2.1：`c*←Memory(task,history)`，`argmin|c|` 同时 `argmax Agent(task,context)`，p3）。
- **它指出的既有方案缺陷**（p1–2，三条）：
  1. **记忆即压缩，必然有损**：预算记忆是原始数据的压缩表示，无法满足细粒度信息需求；
  2. **结构静态**：难以适配临时/未预见的请求；
  3. **依赖领域专长与手工启发式**：跨域泛化受限。
- 论文核心反转：**「搜索是记忆的核心，记忆化只是为了让搜索更有效」**（"Search is made as the core of memory, while memorization is conducted to enable effective search"，p2）。

### 2.2 核心思想（关键 insight）
1. **无损只能来自对完整历史库的搜索**：预计算记忆只用于**支持搜索**，不用于替代事实源（p2）。
2. **JIT 双智能体**：Memorizer 离线做「记忆化 + 分页」，Researcher 在线做「深度研究」，两者皆为 LLM 智能体、各带定制提示（p3–4）。
3. **记忆构造本身就是一次主动研究过程**：离线 memorizing/paging 是「抽取显著信息 + 生成上下文头」的研究式构造；在线 researcher 则是「按信息需求规划检索、反思结果是否完备」的迭代研究（p2–4）。
4. **端到端可优化**：Memorizer 与 Researcher 可用 RL 联合优化，client 不参与学习（Eq.6–7，p4）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **Memorizer.memorize** | 新会话 sᵢ + 现有记忆 mᵢ → memo µᵢ；mᵢ+{µᵢ}→mᵢ₊₁ | 增量生成「简洁且结构化」的关键信息快照 | Eq.1，p3 |
| **Memorizer.page** | sᵢ + mᵢ → 页头 hᵢ；{header:hᵢ, content:sᵢ}→pᵢ；p.append(pᵢ) | 生成页头并装饰会话成页，存入 page-store，保**完整历史** | Eq.2，p3 |
| 页头生成（上下文检索） | 前序轨迹 → 关键上下文头 | 保页面语义一致性、可被准确检索（同 BGE landmark retrieval / Anthropic contextual retrieval） | §2.2.1，p3 |
| **Researcher.plan** | 请求 r + 记忆 mᵢ + 工具集 T → {tool:t, param:ρₜ} | CoT 分析信息需求、生成检索计划（工具：embedding 向量检索 / BM25 关键词 / ID 直读页） | Eq.3，p3 |
| **Researcher.search+integrate** | 并行执行 t(ρₜ)→页 pₜ；整合 ∪pₜ、上一轮整合 I、r → 新 I | 并行检索并增量整合证据 | Eq.4，p4 |
| **Researcher.reflect** | I, r → 二值指示 y, 新请求 r′ | 判定信息是否**已完备**；不完备则生成 r′ 开启下一轮（最大反思深度 3） | Eq.5，p4 |
| **InfoCheck 门（提示级）** | 请求 + 当前整合结果 → `enough` 布尔 | 判断「是否已收集足够信息」，**只判完备性、不答问**（附录 Prompt，p16） | 附录 p16 |
| 后续请求生成（提示级） | 请求 + 结果 → ≤5 条新检索问句 | 定位缺口、生成并排序补检索问句 | 附录 p17 |
| **RL 端到端优化** | D={(task,hist)} → 期望奖励 R=E[Γ(ans)]；对 θm/θr 做策略梯度 | 联合优化 memorizer/researcher（client 排除） | Eq.6–7，p4 |

### 2.4 关键表示与数据结构
- **page-store**：完整历史的容器；每页 = `{header, content}`，content 为原始会话，header 为跨轨迹上下文头（Eq.2，p3）。
- **memory（memo 序列 m）**：轻量、增量更新的结构化高亮，仅作检索导航（Eq.1，p3）。
- **会话切分**：输入按 **2048 token** 分页做流式处理（§3.1，p5）。
- **研究态**：整合结果 I + 反思指示 y + 后续请求 r′（Eq.4–5，p4）。
- **输出格式三档**：integration only / integration with page / integration with extraction（Table 4，p8）。

### 2.5 实验证据

| 任务 / 基准 | 对照基线 | 关键数字（GPT-4o-mini 骨干，除注明） | 出处 |
|---|---|---|---|
| LoCoMo（单跳/多跳/时序/开放） | long-LLM、RAG、A-Mem、Mem0、MemoryOS、LightMem | GAM F1：单跳 **57.75**、多跳 **42.29**、时序 **59.45**、开放 **33.30**，全项第一 | Table 1a，p6 |
| HotpotQA（56K/224K/448K） | 同上 | GAM F1 **63.22 / 64.56 / 59.81**；长-LLM 56.56/54.29/53.92；A-Mem 33.90/30.22/31.37 | Table 1b，p6 |
| RULER 128K（Retri./MT/AGG./QA） | 同上 | GAM Acc **97.70 / 93.20 / 42.50 / 72.50**；RAG 在 MT 为 **0.00** | Table 1b，p6 |
| NarrativeQA（随机 300 问，均 87K） | 同上 | GAM F1 **36.86**；LightMem 17.51 | Table 1b，p6 |
| 模型规模影响（Memorizer） | Qwen2.5 0.5B→32B | Memorizer 缩到 0.5B 仍具竞争力（avg F1 48.83 vs 14B 53.18） | Table 2a，p7 |
| 模型规模影响（Researcher） | 同上 | Researcher 降到 7B 及以下显著退化（0.5B avg **9.08**；14B **53.18**） | Table 2b，p7 |
| 测试时算力（反思深度 1→5） | — | 深度增大持续提升、边际递减；系统**自主决定**实际反思步数 | §3.4 Fig.2a，p6–7 |
| 测试时算力（检索页数 3→20） | — | 页数增大持续提升 | §3.4 Fig.2b，p7 |
| 工具消融 | 单工具 / 两工具组合 | 三工具联合最佳（avg F1 53.18）；单工具最差仅 page-id 28.96 | Table 3，p8 |
| 模块消融 | research w/o memory / memory w/o research | 去记忆 48.27；**去研究 27.50**（记忆单用更差） | Table 3，p8 |
| 输出格式 | integration / +page / +extraction | F1 53.18 / **55.71** / 54.47；token 105.9 / **2379.8** / 230.8 | Table 4，p8 |
| 效率（HotpotQA 56K） | A-mem/Mem0/MemoryOS/LightMem | GAM 在线 **12.43s**（基线 0.15–0.52s）；总时 69.32s（A-mem 210.26s） | Table 5，p9 |

> 统计口径：主表未报告 seed 数与方差，均为单次运行的点估计；LoCoMo 用 F1/BLEU-1，RULER 用 Acc，HotpotQA/NarrativeQA 用 F1。

### 2.6 论文自陈局限与边界条件
- **论文未设独立的 Limitations 章节**（全文 17 页，第 4 节结论后即参考文献与附录，无专门局限段）。
- 从正文可推断的边界：**在线服务延迟显著高于基线**（12–18s vs 0.2–0.5s，Table 5 p9）——JIT 的代价是把算力搬到在线；**反思/检索边际收益递减**（§3.4 p6–7）；**性能强烈依赖 Researcher 的模型规模**（Table 2b p7）；域全部为 **QA / 对话 / 长上下文理解**，无生存、无具身、无工具执行环境。
- 假设依赖：假定历史可完整留存于 page-store 且可被检索；假定 client 可给出奖励信号 Γ 供 RL 训练（p4）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射

| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 记忆机制本身与生存无关；全域为 QA/对话（Table 1 p6） | 把「页」从会话文本改为生存事件的**结构化状态页**；研究环只服务生存 |
| **C2** 自然语言只作观察员接口 | **✗** | memo、page header、检索查询、整合结果 I **全部是自然语言**（Eq.1–5、附录 Prompt p11–17）——语言是记忆的**载体与控制物质** | 生存域记忆用结构化向量/事件页；语言仅留在慢环离线研究面，不进快环 |
| **C3** 权重/记忆/技能三分离 | ◐ | 是纯记忆框架，但 RL 同时更新 memorizer/researcher **权重**（Eq.7 p4），记忆与权重未做生命周期分离 | 权重（策略）/记忆（页库）/技能分置；RL 只作离线策略更新 |
| **C4** 低算力低带宽 | **✗** | JIT 把算力搬到**在线**：在线 12.43s→18.49s（基线 0.15–0.55s，Table 5 p9）；page-store 随完整历史**无界增长**；测试时算力可扩（§3.4） | 把研究环移入**慢环离线**（与 SSEA 双环一致）；页库设上限/分级冷热；在线只取缓存结果 |
| **C5** 精准回忆历史 | **✓** | 完整历史**无损**存 page-store，仅把有损压到 memo 索引；论文断言 "lossless memory can only be realized via searching over a database of the complete history"（p2） | —（见 §5 的精度边界说明） |
| **C6** 可自主修改自身 | ◐ | RL 更新自身参数（Eq.7 p4），但无代码自改、无四权拆分 | 提案/边界/验证/应用四权分离 |
| **C7** 可保存/恢复/变异/继承 | ◐ | 记忆增量持久化（Eq.1–2 p3），但**无变异/继承机制** | page-store + memo 可作 GenePackage 的**记忆材料**；页/索引需可版本化打包 |
| **C8** 给基因先验，不给知识语料 | **✓** | 记忆是**client 私有**（由其自身 history 构造，Def. 2.1 p3），论文**未主张跨个体复用记忆**；跨 client 共享的只有 RL 学到的 memorizer/researcher **策略**（= 结构性先验「如何记忆/如何研究」），非知识语料 | —（GAM 未越 C8 边界；见 §5） |
| **C9** 不设评分函数，只有淘汰函数 | **✗/◐** | 显式奖励函数 **Γ(ans)** 用于 RL（Eq.6–7 p4）= 外部评分；InfoCheck 是 LLM **judge**，但只输出二值 `enough`（完备性/合法性门，不打分不排序） | Γ 换**环境侧淘汰信号**（存活/危险回避）；InfoCheck 保留为「合法性门」，严禁其输出分数 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子（BGE-M3 检索器借用，p5）；创新在 JIT 记忆信息流（L2）与端到端 RL（L3） | — |

### 3.2 L1–L4 层级定位

| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；BGE-M3 作稠密检索器（p5） | 符合借用立场 |
| **L2 信息流层** | **JIT 双环记忆流**：离线 memorize+page → 无损页库；在线 plan→并行 search→integrate→reflect | **高**：可作 SSEA 记忆存取骨架 |
| **L3 学习层** | RL 端到端优化 memorizer/researcher（Eq.7 p4） | 中：思想可用，但 Γ 与 C9 冲突 |
| **L4 演化层** | **无**：记忆不跨代、不继承 | 低；但页库/索引可作基因包材料 |

### 3.3 模块映射

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| page-store（无损完整历史） | **记忆存储层新增**：作 retrieve 的**无损事实源**，解「召回精度上限」 |
| memo（轻量索引 m） | 慢环 ΔM 的**导航索引**；只导不载事实 |
| Memorizer.memorize/page | 慢环 SEL 的**记忆构造器**（离线写入路径） |
| page header（上下文头） | retrieve 的**键增强**（对照 BGE landmark / Anthropic contextual retrieval，p3） |
| Researcher.plan/search/integrate/reflect | 慢环**离线研究/预演**（与 Dream-RSI 重放树结合）；快环不调用 |
| InfoCheck 二值门 | **记忆二级门**（替代债务 22 的常量阈值；提供「不开」的判据形状） |
| 多工具并行检索 | retrieve 的**多路召回**（向量 + 关键词 + 直读） |
| RL 奖励 Γ | **仅作模型外仪器**（C9）；模型内不出现 |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - **`retrieve` 键收窄 → 召回精度上限低**：page header（上下文检索）扩键 + 无损页库抬升召回天花板。
  - **债务 22（记忆二级门用常量阈值、慢环不可调）**：InfoCheck 二值完备性门可由慢环生成，替代常量阈值。
  - **记忆门「开得准不准」的选择性缺失**：InfoCheck 的 `enough=false` 分支给出「不开」的显式判据形状。
  - **睡眠期计算预算未定义**：GAM 把预算花在在线（JIT），SSEA 相反（慢环离线）——提供一份「研究成本 = 反思深度 × 检索页数」的**可换算预算模型**（§3.4 p6–7）。
- **可服务的验收实验**：七条中的记忆/检索相关项（实验 2/3/6 中的记忆与技能固化部分）；GenePackage 记忆材料打包（服务实验 4/5 的 Gene Manager 缺口）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **无损 page-store + 有损 memo 索引**双层分离 | 表示/架构 | 改造移植 | 记忆存储 / retrieve | 召回精度上限、C5 精准回忆 | 高 |
| 2 | Memorizer/Researcher 研究协议（plan→并行 search→integrate→reflect） | 协议 | 改造移植 | 慢环记忆构造 / 预演 | 「主动研究式构造记忆」 | 高 |
| 3 | page header（上下文检索 / landmark 式扩键） | 表示 | 改造移植 | retrieve 键 | `retrieve` 键收窄 | 中 |
| 4 | InfoCheck 二值完备性门 | 协议 | 改造移植（去 LLM、去打分） | 记忆二级门 | 债务 22、门的选择性 | 中 |
| 5 | 多工具并行检索（向量 + BM25 + ID 直读） | 算法 | 改造移植 | retrieve | 召回覆盖不足 | 中 |
| 6 | 输出格式 token/F1 权衡（integration / +page / +extraction） | 工程 | 仅借思想 | 注入面预算 | 上下文预算分配 | 中 |
| 7 | 反思深度 / 检索页数作**可调算力旋钮** | 思想 | 仅借思想 | 睡眠期预算 | 预算未定义 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 的 ✗/◐）：
  - **C2 ✗**：记忆载体与检索介质**全是自然语言**——与「语言只作观察员接口」正面冲突。这是本篇与 SSEA 最根本的错位。
  - **C4 ✗**：JIT 把重算搬到在线（在线 12–18s vs 基线 0.2–0.5s，Table 5 p9），且 page-store 随历史**无界增长**。SSEA 的算力预算在**慢环离线**，两者方向相反。
  - **C9 ✗/◐**：RL 奖励 **Γ(ans)** 是显式外部评分（Eq.6–7 p4）。InfoCheck 虽是 LLM judge，但只输出二值合法性判定，**未打分、未排序**，属可接受的合法性门。
- **关于 C5 的精度边界（本篇核心判定）**：主动研究式构造**仍能保证精准**，但机制是**分离**而非「研究本身精准」——GAM 把有损只压到 **memo 索引**（只影响导航、不影响可召回性），把事实源**无损**留在 page-store（p2）。因此召回精度的**上界由页库决定、不由研究决定**；研究只决定「能否把上界兑现」。**风险点**：在线交付的是**整合结果 I**（一次有损再推导），其精度强烈依赖 Researcher 规模（Table 2b：7B 以下崩溃，p7）——即「精准」在**交付环节**重新被引入损失。
- **关于 C8 的边界判定（明确结论）**：**GAM 未越 C8 边界**。记忆是 client 私有的（Def. 2.1 明确 `Memory(task,history)`，p3），论文**未主张记忆跨个体复用**；跨 client 复用的只有 RL 学到的 memorizer/researcher **策略**，那是「如何记忆/如何研究」的**结构性先验**，恰是 C8 允许进基因包的东西，而非知识语料。若未来把 page-store/memo **直接跨个体搬运**，才会触线（SSEA 需在 HeritableFilter 明确拦截）。
- **隐含假设与失效条件**：假定完整历史可留存且可检索；假定可取得奖励 Γ；假定检索器能覆盖页库语义。
- **算力 / 带宽 / 工程代价**：在线研究双跑成本高；页库存储无上界；离线建库时间随长度线性增长（56K 56.89s → 448K 557.16s，Table 5 p9）。
- **搬运后的可能退化模式**：若把研究环直接搬进 SSEA 快环——延迟爆表、预算失控（C4 失败）；若把 memo 当事实源用——退回有损 AOT，C5 优势归零；若把 Γ 直接接进训练——C9 违规。

---

## 6. 组合分析

### 6.1 关系图谱（以下均为本卡推断，论文未点名这些工作）

| 关系 | 对象（点名） | 说明 |
|---|---|---|
| 前置依赖 | 可留存完整历史 + 可检索底座 + 可注入请求 | SSEA 记忆存储层部分具备 |
| 互补（最紧） | **SEDM** | SEDM 管**准入**（SCEC 打包 + A/B 边际验证），GAM 管**存取**（无损页库 + 主动研究）；SCEC 可作 GAM 的 page 容器，A/B 准入插在 researcher 之前 |
| 互补 | **Memento** | Memento 冻结 LLM + 案例库 + 可学习检索 μ 决定「选什么」，GAM 的 researcher 决定「怎么研究」；μ 作导航先验、researcher 作检索执行 |
| 互补 | **Dream-RSI** | Dream-RSI 提供重放模拟器，GAM 的 plan/search/reflect 在睡眠期对重放树执行 → **离线主动研究式记忆构造** |
| 互补 | **LightMem** | LightMem 摄入压缩 + 主题分段 + 睡眠期巩固，GAM 提供无损底座与取用研究；压缩与无损各管一层 |
| 互补 | **FLEX** | FLEX 分层经验库（golden/warning）+ updater 写入三分支，可决定 GAM memo 的**分层归属** |
| 对照（范式相反） | **Mem0** | Mem0 是典型 AOT（事实抽取 + CRUD + 实体图）；GAM 反其道——**不抽取、只在取时研究**。二者是 AOT vs JIT 的镜像对照 |
| 对照 / 互补 | **A-MEM** | A-MEM 用 Zettelkasten 链接拓扑组织；GAM 用页头保上下文。A-MEM 缺无损底座，GAM 缺链接拓扑 |
| 对照 / 互补 | **G-Memory** | G-Memory 层级图记忆强在图导航，GAM 强在无损召回；可「图上导航 → 页库取事实」 |
| 互补 | **MemRL** | MemRL 两阶段检索 + 冻结库迁移验收 + 遗忘率 FR；GAM 的 page-store 是天然**冻结库**候选，MemRL 的迁移验收可复用于 GAM 记忆跨域 |
| 互补 | **MemEvolve** | MemEvolve 提供记忆系统的演化框架与威胁模型；GAM 的 RL 优化是「记忆策略演化」的一例，但须去 Γ（C9） |
| 互补 | **ReasoningBank** | ReasoningBank 把成功推理抽成可复用条目（高层策略），GAM 保留原始历史（底层事实）；一抽一存，互补 |
| 对照 / 互补 | **DeepDive**（知识图谱 + 多轮检索） | 与 GAM 同属「多轮检索式研究」范式：DeepDive 用 KG 结构化导航，GAM 用非结构化页库；**可组合为「KG 导航 + 页库取事实」** |

### 6.2 推荐组合方案

- **组合 1：GAM × SEDM —— 无损记忆存取（慢环主干）**
  - **接口形态**：SCEC 作 page 格式（自包含 + 哈希 + 种子），page-store 作无损底座，memo 作导航索引；候选记忆入库前跑 SEDM 的 A/B 准入；InfoCheck 作二级门。
  - **新增能力**：既有 SEDM 的「准入防噪」，又有 GAM 的「无损可召回」。
  - **新增风险**：页库膨胀（需 SEDM 的合并/软删约束）。
- **组合 2：GAM × Dream-RSI —— 睡眠期主动研究式记忆构造**
  - **接口形态**：researcher 的 plan/search/reflect 在睡眠期对 Dream-RSI 的重放树执行；产出的 memo/page 作为 ΔM 提案，过四级验证门后升版。
  - **新增能力**：把「主动研究」搬进慢环离线，规避 C4 在线重算冲突。
  - **新增风险**：睡眠期预算需按「反思深度 × 检索页数」建模（对应 SSEA「预算未定义」缺口）。
- **组合 3：GAM × Memento —— 导航先验 + 研究执行**
  - **接口形态**：Memento 的可学习检索 μ 作 researcher 的规划先验；researcher 作检索/整合执行。
  - **新增能力**：μ 学「选哪些」，researcher 学「怎么取」，检索从「一次命中」升级为「迭代补齐」。

### 6.3 本篇在组合中的典型角色
- **记忆存取骨架 / 主动研究式记忆构造器**：管「事实源怎么无损留存、取用时怎么现场研究补齐」；与 SEDM（准入官）分工为「准入 vs 存取」。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击 C5 与「retrieve 键收窄」「记忆二级门」两缺口（实测于原文机制，推断其可迁移性） |
| 立场兼容性 | **2** | C5/C8/C10 对齐，但 C2（语言载体）、C4（JIT 在线重算）、C9（RL 奖励 Γ）三重冲突（实测） |
| 可搬运性 | **4** | 双层分离与研究协议清晰、与底座解耦，可拆为独立零件（推断） |
| 证据强度 | **4** | 4 基准、6 基线、工具/模块消融、效率表、模型规模表（实测；但无 seed/方差报告） |
| 组合价值 | **4** | 与 SEDM/Memento/Dream-RSI/LightMem/A-MEM/G-Memory/DeepDive 广互补（推断） |
| 落地成本 | **2** | 反向口径：JIT 在线重算昂贵、页库无界；但离线化后可降（实测 + 推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采纳「无损 page-store + 有损 memo 索引」双层分离、「主动研究式取用」协议、page header 扩键与 InfoCheck 二值门；**不采纳**语言载体与在线 JIT 重算，**RL 奖励 Γ 仅作模型外仪器**。
- **优先级：P1**（记忆轨道紧邻 SEDM/Memento，服务当前 retrieve 与记忆门缺口）。
- **建议动作**：
  1. 记忆存储层引入「**无损事实页 + 轻量导航索引**」双层，页头由慢环生成以扩 `retrieve` 键；
  2. 把 researcher 的 plan→search→integrate→reflect 作为**慢环离线研究**接入 Dream-RSI 重放树，产出 ΔM 提案；
  3. 用 InfoCheck 形态的二值完备性门替换债务 22 的常量阈值（门只判合法性、不打分）；
  4. 明确记忆为 **client 私有**，禁止跨个体直接搬运页库（守 C8）。
- **最小验证实验**（服务记忆/检索验收）：
  - **双臂 / 消融**：AOT 臂（离线压成 memo、在线只读）vs JIT 臂（无损页库 + 慢环研究取用），同一生存轨迹数据集，≥8 seed；第三臂消融「去研究只留页库」。
  - **判据（分档：机制计数 → 行为差 → 淘汰结果；先看分母）**：
    - 机制计数：页库完整率、memo 对页库的覆盖/召回率、每请求反思轮数；
    - 行为差：后续任务少走弯路的步数差、危险回避率（当前 0.9814 已饱和，需换判据）；
    - 淘汰结果：存活时长 / 任务成败。
  - **预期与证伪**：预期 JIT 臂召回精度高于 AOT 臂（无损底座抬上界），但慢环预算显著更高。**证伪条件**：若 JIT 臂召回精度不高于 AOT 臂，则「无损底座抬升精度上界」假设不成立（可能因研究能力不足或页库不可检索）；若 JIT 臂预算超慢环上限，则须退回分级/冷热方案。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. 生存域「完整历史」的粒度是什么（原始传感帧 / 结构化事件）？无损页库在生存域可能体量巨大，是否可承受？
  2. 若 researcher 只在**慢环离线**运行，page-store 与 memo 的更新时间线如何与 ΔM 升版（四级验证门）对齐？
- **需补查的文献或资料**：
  3. BGE landmark retrieval [14] 与 Anthropic contextual retrieval [15]（p3）的具体扩键做法，用于生存域页头设计。
  4. MemAgent [7]（HotpotQA 记忆评测数据集来源，p4）的评测构造，判断其是否可用于 SSEA 记忆验收。
- **需人工核对的公式 / 实现**：
  5. InfoCheck 的阈值由谁定（慢环模型 / 规则），如何确保它**不**退化为评分件（C9）？
  6. RL 奖励 Γ(ans) 在 SSEA 中换用什么环境侧信号（存活时长 / 危险回避 / 任务成败）？
  7. 无语言生存域中，page header（本依赖 LLM 生成自然语言上下文头）如何生成？

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "the widely-adopted static memory … is inevitably subject to severe information loss"（AOT 之弊） | p1 摘要 |
| "Search is made as the core of memory, while memorization is conducted to enable effective search" | p2 |
| "lossless memory can only be realized via searching over a database of the complete history, where the pre-computed memory is introduced to support such a search process" | p2 |
| Def. 2.1：`c*←Memory(task,history)`，`argmin|c|` 且 `argmax Agent(task,context)` | p3 |
| Eq.1 Memorizer.memorize：`sᵢ,mᵢ→µᵢ; mᵢ+{µᵢ}→mᵢ₊₁` | p3 |
| Eq.2 Memorizer.page：`{header:hᵢ, content:sᵢ}→pᵢ`（保完整历史） | p3 |
| Eq.3–5 Researcher：plan→search/integrate→reflect（二值 y，不完备则 r′） | p3–4 |
| Eq.6–7 RL 优化：`R=E[Γ(ans)]`，memorizer/researcher 策略梯度，client 排除 | p4 |
| Table 1：LoCoMo 时序 F1 59.45；HotpotQA 63.22/64.56/59.81；RULER MT 93.20、RAG MT 0.00 | Table 1 p6 |
| Table 2b：Researcher 0.5B→avg 9.08，14B→53.18（研究模块对规模敏感） | Table 2 p7 |
| Table 3：去研究 27.50 < 去记忆 48.27（记忆不可单用） | Table 3 p8 |
| Table 4：integration only 53.18 F1 @105.9 token；+page 55.71 @2379.8 token | Table 4 p8 |
| Table 5：GAM 在线服务 12.43s→18.49s（基线 0.15–0.55s） | Table 5 p9 |
| 附录 Prompt：InfoCheck 只输出 `enough` 布尔，不答问、不打分 | p16 |
| 附录 Prompt：FollowUpRequestAgent 生成 ≤5 条补检索问句并排序 | p17 |
| 全文无独立 Related Work / Limitations 章节（结论后即参考文献与附录） | p9–17 |
