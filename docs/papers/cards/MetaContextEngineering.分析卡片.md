# 论文分析卡片 · Meta Context Engineering（MCE）

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-01-29 Meta Context Engineering via Agentic Skill Evolution.pdf` |
| 标题 | **Meta Context Engineering via Agentic Skill Evolution（MCE）** |
| 作者 / 机构 | Haoran Ye、Xuning He、Vincent Arak、Haonan Dong、Guojie Song；北京大学 通用人工智能国家重点实验室 / 智能科学与技术学院、电子工程与计算机科学学院 |
| 发表时间 / 出处 | arXiv:2601.21557v2 [cs.AI]，2026-02-11（稿面标注 Date: January 27, 2026）；Preprint，未注明录用 |
| 论文链接 | arXiv:2601.21557 |
| 代码链接 | https://github.com/metaevo-ai/meta-context-engineering |
| 标签 | 元上下文工程 · 双层优化 · 智能体技能演化 · agentic crossover · (1+1)-ES · 上下文即文件与代码 · 检索函数演化 · 上下文迁移 |
| **应用裁决** | **B 零件采用**（「元技能 = 独立第四类 ΔP」的**双层形式化** + 演化回路形状 + best-so-far 回滚可拆；核心的 LLM-agent 回路与 J_val 评分选择不可搬） |
| 优先级 | **P2**（与 MemSkill 同族且**高度重叠**，建议并入 MemSkill 工作流一并处理；若团队决定给 ΔP 一个正式双层模板，可升 P1） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把「上下文工程（CE）」从**人工写死的 harness**（固定的生成-反思-整理流程 + 预定义 context schema）提升为一个**双层优化问题**——元层 agent 用 **agentic crossover** 在「技能历史 + 执行轨迹 + 评估指标」上做审议式搜索，持续演化**CE 技能**（可执行的指令与代码）；基座层 agent 执行该技能，把上下文实例化为**任意文件与代码**并从训练 rollout 中学习；技能与上下文**共同演化**（p1、§3、Fig.2）。五个领域上比 SOTA agentic CE 方法相对提升 5.6–53.8%（均值 16.9%），且上下文长度自适应（1.5K–86K token）、训练快 13.6×、rollout 少 4.8×（p1、§4.2）。
- **对 SSEA 的意义**：它是**「如何给智能体准备上下文」这一元层技能**的最完整形式化——正好撞上 SSEA C3 三分离中**尚未定义的第四类对象**（与 MemSkill 同族）。它把 MemSkill 的「写端记忆技能」推广为**整个上下文函数**（= 静态知识库 ρ + 动态检索/组合算子 F），因此它的 ΔP 有**两个产物**（ΔM 上下文工件 + ΔR-proc 检索/组织程序）。同时它给出 C6 四权分立的**双层版对照**，但它的验证/选择**整体建立在 J_val 评分上**，与 C9 硬冲突，且**天然语言中心**，与 C2 硬冲突。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–2）：LLM 的效用取决于推理时上下文的组织。当前 CE 方法依赖**人工设计的 agentic harness**，带来两类结构偏置：
  1. **表示层偏置**：case-based 轨迹有情景但缺泛化；itemized 列表有抽象但扁平无结构；graph 层级灵活但高延迟且不一定胜过朴素检索（p1、§2.1 p3）。
  2. **优化层偏置**：prompt-rewriting（GEPA 式）偏**简洁**，在需要细粒度领域知识的任务上失败；additive-curation（ACE/DC 式）偏**冗长**，产生噪声更新、开销过大、上下文膨胀（p1–2）。
- **它指出的既有方案缺陷**：这些启发式把 CE 限制在一个狭窄设计空间，**无法发现人类直觉之外的、任务最优的策略**（p2）。论文主张「**没有单一 agentic harness 普遍最优**」（§2.1 p3）。

### 2.2 核心思想（关键 insight）
1. **双层解耦：把「怎么表示与学习上下文」（skill）与「学到了什么上下文」（artifact）分开**（§3.1 p5）。类比 ML 中「模型架构/训练算法」与「已学参数」的分离，但 MCE 的 LLM 已训练且冻结。
2. **技能是新的、整合的演化抽象层级**：既非 solution/function/program level，而是把指令、脚本、资源封进统一表示（§2.2 p3–4），使**不同解层可无缝共演化**，并让遗传算子更 agentic（可检查并选择性重组祖先技能目录的组件）。
3. **上下文即文件与代码**：基座 agent 有 coding toolkit 与文件系统，把上下文实例化为**任意文件与可执行检索函数**，不受预定义 schema 约束（§2.1 p3、§3.3 p5–6）。
4. **演化算子不是固定重组规则，而是审议式过程**：agentic crossover 让 agent 自由检视 workspace、识别成败模式、组合出更好的技能（§3.2 p5）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **上下文函数表示** c(x)=(F_k∘···∘F_1)(x;ρ) | 查询 x → 上下文；ρ=静态组件（system prompt/知识库/代码库）、F=动态算子（retrieval/selection/filtering/formatting/composition） | 把「上下文工程」形式化为可优化的函数族 | Eq.1 p4 |
| **双层目标** s*=argmax_s J_val(c*_s) s.t. c*_s=argmax_cs J_train(cs;s) | 内层：给定技能求最优上下文函数；外层：求使验证性能最高的技能 | **解耦 what 与 how**；外层是**评分驱动的选择** | Eq.2–3 p4–5 |
| **技能数据库** H_{k−1}={(s_i,c_i,J^train_i,J^val_i)} | 历次技能 + 其上下文函数 + 训练/验证指标 → 文件夹 | 元层的**历史账本** | §3.2 p5 |
| **Agentic Crossover** s_k=CROSSOVER(τ,H_{k−1}) | 任务规格 τ + 技能历史 → 新技能 s_k | 审议式演化算子（非固定重组） | Eq.4 p5 |
| **技能表示 = 工作区文件夹** | 含 (1) methodology（自然语言学习程序）(2) 可执行脚本（Python）(3) 结构化上下文模板 (4) 验证协议 (5) 动态上下文算子（如检索函数） | 统一封装「怎么做 CE」 | §3.2 p5；§C p26–30 |
| **基座执行** c_k=ENGINEER(τ,s_k;c*_{k−1},R_k) | 技能 + 上一轮最优上下文（warm-start）+ 训练 rollout R_k={(x_i,ŷ_i,eval_i)} → 新上下文函数 | 从 rollout 反馈学习、**在已有上下文上精修而非重建** | Eq.5 p5–6 |
| **(1+1)-ES 编排** | 每轮生成**一个**子代上下文 c_k，与当前最优 c*_{k−1} 比较，保留更优者 | 简单历史知情演化策略；**best-so-far 选择** | Algorithm 1 p6 |
| **工具集** T={Read,Write,Edit,Bash,Glob,Grep,TodoWrite} | agent 通过操纵文件系统工作 | 通用 agent harness；读写权限**按角色与当前迭代严格限定** | §3.4 p6 |
| **callable 接口校验** | 基座 agent 须实现预定义输入-输出签名的可调用接口，**每次执行完成时校验** | 让上下文函数可在 rollout/eval 中被程序化调用 | §3.4 p6 |
| **显式停机判据（案例 D.3）** | 技能自学会「何时停止精炼」：验证模式 <3 / 训练准确率 >90% / 估计 train-val gap >1.5% / 不可约错误 >40% | 元层「知道何时停」本身作为习得技能 | §D.3 p36 |

### 2.4 关键表示与数据结构
- **上下文函数 c = (ρ,F)**：ρ 静态组件（知识库/决策规则/示例），F 动态算子（检索/过滤/组合）。在基座层实例化为**指定目录下的文件集合**（如 `context/*.md` + `retrieve_context.py`）（§3.3 p5–6）。
- **技能 s = 工作区文件夹**：`CE/SKILL.md`（methodology）+ 可执行脚本 + 上下文模板 + 验证协议 + 动态算子（§3.2 p5；§B p21–22 的 `learning-context/SKILL.md` 路径）。
- **技能数据库 H_k**：`meta_agent/` 下按迭代存档 `skills/iterK/SKILL.md` 与 `evaluations.json`（train_acc/val_acc）（§B p22）。
- **载体**：methodology 与上下文工件**全部是自然语言 markdown**；算子与脚本是 LLM 生成的 Python（§C p26–30 的 learned skill 是英文 8 阶段方法 + Python 代码块 + markdown 模板）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| 五领域总览（offline） | ICL / MIPROv2 / GEPA / ACE | **MCE 平均相对增益 89.1%**，ACE 70.7%、GEPA 61.5%、MIPROv2 48.6%、ICL 32.1% | Table 1 p8；DeepSeek-V3.1 生成器 |
| 五领域总览（online） | DC / ACE | **MCE 74.1%** vs ACE 41.1%、DC 35.8%；MCE(w/o skills) 71.3% | Table 1 p8 |
| FiNER（金融 NER，acc） | Base 58.0 / ACE 71.0 / GEPA 66.0 | **MCE 75.0 (+17.0)** | Table 1 p8 |
| USPTO-50k（化学，acc） | Base 6.0 / ACE 18.0 / GEPA 15.0 | **MCE 20.0 (+14.0)** | Table 1 p8 |
| Symptom2Disease（医学，acc） | Base 63.7 / ACE 79.2 / ICL 84.4 | **MCE 89.2 (+25.5)** | Table 1 p8 |
| LawBench（法律，micro-F1） | Base 0.36 / ACE 0.65 / GEPA 0.69 | **MCE 0.70 (+.34)**；论文称超过法律专用模型 0.56 | Table 1 p8、Obs.❹ |
| Aegis2.0（AI 安全，F1） | Base 0.54 / GEPA 0.76 / ACE 0.68 | **MCE 0.80 (+.26)**；论文称超过 Llama Guard 3 8B (0.72) | Table 1 p8、Obs.❹；生成器 Qwen3-8B |
| 强弱模型上下文迁移 | ACE 对照 | MCE 平均相对退化 **23.6/17.1/43.4**（Llama3.3-70B/Qwen3-8B/Gemma3-4B）vs ACE 28.1/23.6/48.3 | Table 2 p8 |
| 上下文效率（FiNER，Fig.3） | ACE | MCE-S **73% @ ~1.5K token** vs ACE 65%；MCE-L **75% @ 20K** vs ACE 70% @ 79K | Fig.3 p9 |
| 训练效率（FiNER，Fig.4） | ACE | **13.6× 加速**（1.9h vs 25.8h）；**4.8× 更少 rollout**（450 vs 2169，达 95% 训练准确率） | Fig.4 p9 |
| 消融：双层设计（FiNER offline） | w/o skills / fixed skill / ACE | full **75** > w/o skills 73 > fixed skill 71 > ACE 71；w/o skills 在线 67 > ACE 64 | Table 3 p10 |
| 排除模型混淆 | ACE + MiniMax M2.1 vs ACE + DeepSeek | 换 MiniMax 后 ACE **反而变差**（67 vs 70；playbook 114K vs 79K token） | Table 4 p10 |

> 口径说明：全篇**未报告 seed 数、重复次数或误差棒**（多篇卡片共性问题）；部分任务用**数据子集**（FiNER 200/100/100、USPTO 50/30/100、LawBench 200/50/100、Aegis 400 训练），论文自陈因算力预算限制（§4.1 p6、§A）。表内数字按单次运行理解（推断）。

### 2.6 论文自陈局限与边界条件
- **优势场景**：以**领域知识获取与模式匹配**为中心的任务，可学习技能能捕捉数据特征、组织领域结构（§5 p10）。
- **不适用 / 弱项**（§5 p10–11）：
  1. **推理密集型任务**未必获益——人工 harness（迭代试错、纠错、系统反思）已很适合这类问题；
  2. **rollout 轨迹很长很复杂**时吃力，因为需要细粒度 credit assignment 与轨迹分析，批量式全 agentic CE 可能做不好；
  3. 论文将第 2 点归因于**底层 agent 模型能力**而非框架本身，预期随 agentic 模型变强而消解。
- **Future work 自陈**（§5 p11）：技能演化可推广到 CE 之外；当前生成器用 one-shot 推理，未来可让生成器直接与工件交互并**共演化「上下文利用技能」**；**技能跨任务迁移**与技能组合的涌现行为仍是开放问题。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 任务是五个**分类/预测 benchmark**（金融 NER、逆合成、症状诊断、罪名预测、安全分类），目标是外部 accuracy/F1，无生存压力、无死亡、无淘汰环境（Table 1 p8） | 只借「元层技能」这一抽象；搬到 SSEA 必须把信号挂到生存事件（危险/资源/失效），而非 benchmark 指标 |
| **C2** 自然语言只作观察员接口 | **✗（最硬冲突）** | 上下文工件是**自然语言 markdown**（`context_*.md`）；methodology 是英文 8 阶段方法；动态算子是 LLM 生成的 Python；元/基座 agent 都是 LLM（§C p26–30、§B p21–22）。**「上下文工程」天然语言中心**，此处判定从严 | 完全去语言化：把 methodology 编译成**触发谓词 + 写入/检索 schema + 参数槽**；上下文工件改结构化张量/符号表；retrieve 函数保留但输入须为非语言状态 |
| **C3** 权重/记忆/技能**三分离** | **✓（分离干净）/ ✗（暴露第四类）** | 不微调任何权重（改输入不改权重，p2）；上下文函数=文件（≈ΔM）；技能=独立文件夹（≠ΔM、≠ΔS）；三者生命周期不同：上下文 warm-start 逐轮精修，技能跨迭代累积（§3.2–3.3） | 正面：**CE 技能既非 ΔM 也非 ΔS，是独立第四类 ΔP**（详见 3.3）；须单独立槽，否则重演实验 3 判据形状错 |
| **C4** 低算力低带宽 | **◐/✗** | 正面：比 ACE 快 13.6×、rollout 少 4.8×；上下文可短到 1.5K token（Fig.3–4 p9）。负面：上下文可达 86K token；基座 agent 处理「大批量 rollout」；元+基座双 LLM 回路，全靠 API（MiniMax M2.1 + DeepSeek V3.1，§4.1 p7）；**无低带宽控制环** | 搬「预算形状」（技能历史账本、批量处理、warm-start 精修），量级换成非语言结构化；LLM 回路整体不进 SSEA |
| **C5** 精准回忆历史** | ◐ | 正面：技能数据库按迭代存档；上下文函数是带检索算子的文件集合，可程序化调用（§3.4 p6）。负面：存的是**蒸馏后的通用知识/决策规则**，非可精准寻址的具体经历；检索是 LLM 生成的**路由函数**（如 symptom 任务 1,440 行规则），非结构化键 | 借「检索算子可被演化」这一点；条目层挂到 SSEA 可寻址 episode 索引；retrieve 键结构化 |
| **C6** 可自主修改自身 | **◐** | 它修改的是**自己的上下文函数与检索程序**（retrieve_context.py 会被执行，属自身推理管线）。四权对照见 3.3：提案权=meta-agent CROSSOVER ✓；应用权=best-so-far 替换 ✓；**边界权弱**（仅「读写权限按角色限定」，无编辑数上限、无「不许改什么」硬约束）；**验证权=J_val 评分选择，非门**（Algorithm 1 p6） | 补边界权（编辑上限 + 危险操作白名单）；把 J_val 评分选择换成**四级验证门**（格式→沙盒→回归→环境实测），门只判合法性、不打分 |
| **C7** 可保存/恢复/变异/继承 | **◐（缺淘汰）** | 保存/恢复：技能数据库 + warm-start 上下文 + **best-so-far 回滚**（劣则弃、保留旧最优）；变异：agentic crossover 组合祖先技能组件。**继承未验证**（跨任务技能迁移是 future work，§5 p11）；**无技能淘汰**：H_k=H_{k-1}∪{…} 单调累积（Algorithm 1 p6） | 补技能退役计数（同 MemSkill 建议）；把 best-so-far 回滚从「评分比较」改为「环境成败淘汰」 |
| **C8** 给基因先验，不给知识语料 | **✗** | 上下文工件恰恰是**领域知识语料**（决策规则、示例、消歧规则、anti-patterns，§C p26–30）；论文核心主张就是积累领域知识并**跨模型迁移**（Table 2 p8） | 只把**结构**（技能组织方式、演化回路、算子形状）当先验入包；知识内容一律不跨代 |
| **C9** 不设评分函数，只有淘汰函数 | **✗（硬冲突，核心）** | 外层选择直接是 `s*=argmax_s J_val(c*_s)`、`c*_k=argmax J_val`（Eq.3 p5、Algorithm 1 p6）；J(c) 是外部任务指标（accuracy/F1）。**验证门=按分数排序选择**，正是 C9 明文禁止的「打分、排序」 | 分层改造：① 剔除 J_val 驱动的 argmax；② 改为**成败式淘汰**（新上下文在近期环境事件上未更差即保留，劣化即回滚，参照 PSN 的 20% 阈值与 SEDM 的 A/B 准入）；③ 历史账本只记**事实计数**（尝试次数/成败次数），不记分数 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子；LLM、embedding、ES 全是借用件；创新在双层信息流（L2）、技能演化与 best-so-far 稳定化（L3）、技能作为可迁移遗产（L4） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子。DeepSeek V3.1 / MiniMax M2.1 / Qwen3-8B 可即插即换（§4.1 p7） | 低（符合借用立场） |
| **L2 信息流层** | **主贡献层**：双层结构（元层技能演化 / 基座层上下文优化）；上下文函数 c=(ρ,F) 的静态/动态分解；技能=文件夹的整合表示；技能数据库账本 | **最高**：直接回答 C3 第四类问题，并给出「元层 → 基座层 → 工件」的信息流模板 |
| **L3 学习层** | agentic crossover（审议式演化）；(1+1)-ES + best-so-far 回滚；warm-start 精修（不重建）；技能自学的停机判据 | **高**：元层演化回路骨架（信号需换） |
| **L4 演化层** | 技能作为可迁移遗产（论文把跨任务技能迁移列为 open question）；技能数据库累积；**无淘汰、无跨个体继承** | 中：提供 ΔP 对象的实例；缺淘汰与 GenePackage 语义 |

### 3.3 模块映射（含第四类归属裁决）

#### ★ 裁决：MCE 的「CE 技能」在 SSEA 归哪里？与 MemSkill 是同一类还是不同类？

**判定：与 MemSkill 的「记忆技能」是同一类 —— 独立第四类 ΔP（元程序 meta-procedure），发布通道并入 ΔR-proc；但 MCE 的 ΔP 是 MemSkill 的「上位/推广版」，作用面更大。**

判定依据严格用 C3 的三条分判据（来源 / 生命周期 / 可遗传性），并与 MemSkill 并列：

| 分判据 | ΔM（记忆） | ΔS（技能，PSN 式） | **MemSkill 记忆技能** | **MCE 的 CE 技能** |
|---|---|---|---|---|
| **来源** | 一次具体经历 | 任务流中蒸馏的可执行程序（作用于环境） | 记忆系统自身失败案例的元层归纳 | **技能历史 + 执行轨迹 + 评估指标的元层归纳**（CROSSOVER，Eq.4 p5）——同样不是经历、不是环境动作 |
| **生命周期** | trace 内、每 trace 重置 | 跨任务累积、可回滚 | 跨 trace 共享、持续累积、不重置 | **跨迭代累积**（技能数据库 H_k，Algorithm 1 p6），上下文工件 warm-start 逐轮精修 |
| **可遗传性** | 不可遗传 | 成熟后可遗传 | 已实测跨数据集/跨模型复用 | **未验证**（跨任务技能迁移=open question，§5 p11）；但**上下文工件**已实测跨强弱模型迁移（Table 2 p8） |

三条来源与生命周期全同于 MemSkill → **同一类**。差异在**作用面**：

- **MemSkill 的技能**只作用于**记忆库的写入/整理**（一个面）；
- **MCE 的技能**作用于**整个上下文函数 c=(ρ,F)**——它同时产出 ① **静态上下文工件（≈ΔM：知识库/决策规则/示例）** 与 ② **动态检索/组合算子（≈ΔR-proc：路由规则、过滤逻辑）**。也就是说 **MCE 的 ΔP 有两个消费者**，MemSkill 的 ΔP 只有一个。

**结论：MCE 与 MemSkill 同一类（ΔP），MCE 是更一般的形式（ΔP → {ΔM, ΔR-proc}），MemSkill 是它的记忆侧特例。**

**为什么仍并入 ΔR-proc 而非新开通道**：与 MemSkill 同一理由——CE 技能的本质是**可枚举的「如何准备/组织/检索上下文」的程序化规则集**，正是 ΔR 通道的「程序化子类」；并入后可复用既有四级验证门，并给 `rules` 零消费者的 ΔR 装上消费者。MCE 相对 MemSkill 的**新增落点**是：它明确把 **retrieve 函数**也纳入可演化对象（ΔR-proc 的检索侧），这正对 SSEA 的 `retrieve` 键收窄问题。

**为什么不能并入 ΔM**：ΔM 按 C8 不可遗传，而 ΔP 是 SSEA 最该遗传的结构性先验（不依赖具体经历）。并入会把二者一并丢弃或污染 ΔM。

**为什么不能并入 ΔS**：ΔS 的契约作用于**环境状态**、验证靠环境成败；ΔP 的作用对象是**上下文/记忆**，效果只能经「后续决策是否成功」间接观测。混入会产生无法用环境成败验证的伪技能（=实验 3 形状错的同一风险）。

**附带裁决（MCE 特有的分裂问题）**：MCE 的 ΔP 同时产出 ΔM 与 ΔR-proc，因此 SSEA 若采用它，必须**在发布通道上再分一次**——技能产物中的**知识内容**走 ΔM（且受 C8 约束、不进基因包），**检索/组织程序**走 ΔR-proc。这是 MCE 比 MemSkill 多出的一条工程纪律。

#### 构件落点

| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| CE 技能（工作区文件夹） | **新增 ΔP 槽位**，经 ΔR-proc 发布；与 MemSkill 的 ΔR-proc 共用同一槽 |
| 技能数据库 H_k={(s_i,c_i,J^train_i,J^val_i)} | 慢环**历史账本**：去掉 J 分数列，改存事实计数（尝试/成败次数） |
| 上下文函数 c=(ρ,F) | ΔM（静态工件）+ ΔR-proc（动态算子）**双落点** |
| 动态算子 F（retrieve/filter/compose） | ΔR-proc 的**检索侧**——直接对应 `retrieve` 键收窄的改造面 |
| Agentic Crossover（Eq.4） | 慢环**提案算子**：去 LLM 后改为「结构化组件重组 + 规则化搜索」 |
| (1+1)-ES + best-so-far（Algorithm 1） | 慢环**演化+回滚**骨架：选择判据由 J_val 换为**环境成败淘汰** |
| 技能内的 validation protocols | 四级验证门的**模板**（但须去评分、改判合法性） |
| 技能自学的停机判据（§D.3 p36） | 慢环**停机/预算法则**候选（与 FLEX logistic、ACE 阈值不敏感并列） |
| callable 接口校验（§3.4 p6） | 上下文函数**交付前接口检查**（对齐 PSN 的三层噪声防御） |
| warm-start 精修（不重建） | 慢环**增量纪律**（对齐 ACE「禁止整体重写」） |

### 3.4 债务与验收实验对应
- **技能表示够不够（0/33 之后仍未答）**：MCE 给出一种**文件夹式技能表示**（methodology + 脚本 + 模板 + 验证协议 + 算子），但它是**语言承载**的，不能直接作 SSEA 的技能表示；其**结构性贡献**是「技能应包含验证协议与算子，而非纯文本」这一形状，可并入 PSN/AutoSkill 的表示讨论。
- **`retrieve` 键收窄 → 召回精度上限低**：MCE **正面命中**——它把 retrieve 函数列为**可演化对象**（F 算子），并展示了演化出的路由函数（symptom 1,440 行、LawBench 177 行、Aegis 995 行，§D.3–D.5 p36–43）。对 SSEA 的含义：检索策略本身可被慢环演化，是一条**此前未评估的独立路径**（MemSkill 只给写端 schema，MCE 给检索端程序）。
- **记忆门「开得准不准」的选择性缺失**：MCE 的**上下文函数演化**含「何时检索哪一段」的判别逻辑（early safe return、优先级级联，§D.5 p42–43），是「门开得准不准」的**检索侧审计形态**；信号须换（见 C9）。
- **睡眠期计算预算未定义**：MCE 给出**迭代数 K=5**、每轮**一个子代**（(1+1)-ES）、基座 agent 可**批量处理 rollout** 的形状；Fig.4 给出 rollout 账（450 vs 2169）。可作预算形态的**第二参照**（MemSkill 给周期×提案上限×验证窗，MCE 给迭代数×单子代×批量）。
- **`rules` 零消费者**：同 MemSkill——把 CE 技能的检索/组织程序归 ΔR-proc，给 `rules` 装上消费者（**检索门**）。
- **Gene Manager 缺失（实验 4/5 卡住）**：MCE 的 ΔP 是两个 GenePackage 本能段候选（MemSkill 记忆技能 + MCE CE 技能）中的**更一般者**；扩大 Gene Manager 规格。
- **实验 3（技能固化）0/33 判据形状错**：MCE 是**反面警示**——它的技能验证**完全依赖 J_val 评分**，若照搬会把 SSEA 拉回评分选择；其可借处是「**best-so-far 回滚**」这一成败形状（改判据后可并入实验 3 重设计）。
- **可服务的验收实验**：实验 2（记忆检索）——检索算子演化；实验 3 的重设计（作为**排除项** + best-so-far 回滚形状）；不服务实验 4/5（卡在 Gene Manager）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **双层解耦（skill=how / artifact=what）与「元技能=ΔP」的判据** | 表示/架构 | **直接移植（作为裁决）** | ΔP 槽位 / GenePackage 本能段 | C3 第四类未定义；与 MemSkill 的归类统一 | 高 |
| 2 | **ΔP → {ΔM, ΔR-proc} 的双产物发布纪律** | 协议 | **直接移植** | 发布通道 | MCE 特有：防止知识内容与程序混装（重演 ACE 的 C3 混装） | 高 |
| 3 | **(1+1)-ES + best-so-far 回滚** | 算法/协议 | **改造移植**（J_val → 环境成败淘汰） | 慢环演化回路 | 自修改安全、可恢复；C9 合规改造 | 高 |
| 4 | **warm-start 精修（不重建）** | 协议 | **直接移植** | 慢环所有改写路径 | 防「整体重写」导致的信息损失 | 高 |
| 5 | **动态算子 F 可演化（检索/过滤/组合程序）** | 表示/算法 | **改造移植**（去语言化） | `retrieve` / ΔR-proc 检索侧 | `retrieve` 键收窄、召回精度上限低 | 中高 |
| 6 | **技能=文件夹（含验证协议与算子）的整合表示** | 表示 | 仅借思想（结构形状） | 技能表示讨论 | 「技能表示够不够」 | 中 |
| 7 | **Agentic Crossover 的「历史知情审议式重组」形状** | 算法 | 仅借思想（去 LLM） | 慢环提案算子 | 比固定重组更灵活的技能合成 | 中 |
| 8 | **技能自学的停机判据（§D.3 p36）** | 判据 | 仅借思想 | 慢环停机/预算 | 睡眠期计算预算未定义 | 中 |
| 9 | **callable 接口交付前校验** | 工程/协议 | 直接引用 | 交付前质控清单 | 编译产物可靠性 | 中 |
| 10 | **上下文效率/迁移/训练效率三套指标口径**（Fig.3–4、Table 2） | 仪器 | 仅借思想 | 实验仪器 | 上下文成本-质量前沿的度量模板 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（逐条）**：
  1. **C2（最硬）**：上下文工件是 NL markdown、methodology 是英文、算子与脚本由 LLM 生成、双层都是 LLM agent。**「上下文工程」天然语言中心**，SSEA 控制环不能进 NL。→ 必须整体做**载体替换**，否则本篇只能停在观察员面。
  2. **C9（硬）**：外层选择 `argmax_s J_val`、`c*_k=argmax J_val` 是**评分驱动的排序选择**，正是 C9 禁止项；验证门退化为「按分数择优」。→ 必须换成环境成败淘汰 + 事实计数。
  3. **C1（硬）**：目标是 benchmark accuracy/F1，无生存、无淘汰环境。→ 信号整体换到生存事件。
  4. **C8（硬）**：上下文工件是领域知识语料，且论文主张跨模型迁移。→ 只有结构可入基因包，知识内容不跨代。
  5. **C6（软）**：边界权弱（仅读写权限按角色限定，无编辑上限）、验证权=评分选择而非门。→ 补边界权与四级门。
  6. **C4（软）**：86K token 上下文、双 LLM 回路、全靠 API。→ 只搬形状不搬量级。
- **隐含假设与失效条件**：
  1. 假设**有可用的验证集与外部指标 J_val**——SSEA 无外部评分，**这条假设直接失效**，是搬运头号拦路石（与 MemSkill 同）。
  2. 假设**agentic 模型能操作编程环境并产出合法文件/代码**（论文自陈这是 MCE 增益的必要条件，§4.3 p10）。SSEA 若不用 agentic LLM，整条回路失效。
  3. 假设任务是**知识获取/模式匹配型**；论文自陈**推理密集型任务未必获益**（§5 p10）——SSEA 的生存决策更像推理/控制型，收益存疑。
  4. 假设轨迹**短而可批量分析**；长复杂轨迹下批量式 CE 会失效（§5 p10）——生存轨迹长且关键帧稀疏，风险高。
- **算力 / 带宽 / 工程代价**：
  - 元层每迭代一次 LLM agent 搜索；基座层每次执行可跑「批量 rollout 分析 + 写码」；论文用 MiniMax M2.1 + DeepSeek V3.1 + Qwen3-8B（§4.1 p7）。**训练侧总算力未提及**（只有 1.9h vs 25.8h 的相对量）。
  - 需要新建：ΔP 槽位与表示、双产物发布纪律、慢环提案/回滚、warm-start 精修、检索算子演化面。**与 MemSkill 工作流高度重叠**，重复建设风险高。
  - 去语言化是主要一次性成本：把文件夹式技能（NL 方法 + Python）编译成「触发谓词 + 写入/检索 schema + 参数槽」，依赖缺失的 RuleCompiler。
- **搬运后的可能退化模式**：
  1. **评分回潮**：J_val 被换名保留（如「回归窗成功率」实为分数）→ C9 名义合规、实质违规。→ 判据须是**计数/成败**而非阈值比较。
  2. **ΔP 双产物混装**：知识内容与检索程序混在一个 ΔP 里发布 → 重演 ACE 的 C3 混装与实验 3 形状错。
  3. **技能库只增不减**（论文自带缺陷）→ ΔP 膨胀吃掉慢环预算，撞 C4。
  4. **检索算子过拟合训练集**：MCE 的 retrieve 函数（如 1,440 行规则）是在训练错误上长出来的，换环境即失效；论文的迁移证据是**上下文工件**迁移，不是**算子**迁移。
  5. **agent 模型依赖**：换成弱模型（SSEA 低算力侧）时，论文自陈增益依赖 agentic 能力，可能大幅缩水（Table 4 反证了「换模型不解决 ACE 问题」，但也说明 agent 模型能力是门槛）。

---

## 6. 组合分析

### 6.1 关系图谱（点名连接）
| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **同类（最紧）** | **MemSkill** | **同一类 ΔP（元程序）**。MemSkill = 记忆**写端**元程序（难例→归因→精修/新增，作用面=记忆库）；MCE = **整个上下文函数**的元程序（作用面=上下文工件 + 检索算子）。**MCE ⊃ MemSkill**：MCE 的 ΔP 有两个产物（ΔM 工件 + ΔR-proc 算子），MemSkill 只有一个。**合并建议**：两篇共用一套 ΔP/ΔR-proc 槽与四权管线；MCE 补 MemSkill 缺的**检索侧演化**，MemSkill 补 MCE 缺的**难例缓冲/归因/边界权清单** |
| **被它取代的对象** | **ACE（Agentic Context Engineering）** | MCE **明确把自己定位为 ACE 的元层升级**：ACE 的 generation-reflection-curation 是「可能 CE 技能空间中的**一个点**」（p2），MCE 用技能演化去**搜索这个空间**。ACE 是**固定 harness**，MCE 是**可演化 harness**。→ 对 SSEA：ACE 卡给的是「防坍缩的写入协议」，MCE 给的是「harness 本身可演化」；二者叠加 = 可演化的防坍缩写入协议 |
| **同形不同面** | **PSN（Evolving Programmatic Skill Networks）** | PSN 的技能是**作用于环境状态**的可执行符号程序（E^pre/E^post 契约、REFLECT 定责、成熟度门控、20% 回滚）→ ΔS；MCE 的 CE 技能是**作用于上下文**的元程序 → ΔP。**同一套「程序 + 契约/验证 + 门控 + 回滚」形状，作用面差一层**。PSN 的**成熟度门控**可补 MCE 缺的**技能淘汰/冻结** |
| **同族（技能演化）** | **SkillRL** | SkillRL 用教师模型把轨迹蒸馏为技能 + GRPO 训练策略（技能侧训练化）；MCE 演化的是**CE 元技能本身**（不训练权重）。**层级差**：SkillRL ≈ ΔS 的固化，MCE ≈ ΔP 的演化。二者在 SSEA 各归其位，不可混计 |
| **同族（技能自演化）** | **AutoSkill** | AutoSkill = NL `SKILL.md` + add/merge/**discard** 准入（有淘汰）；MCE = 可执行文件夹 + agentic crossover（无淘汰）。**互补**：AutoSkill 的 **discard 准入**正好补 MCE 缺的淘汰；MCE 的**可执行算子**补 AutoSkill 纯文本的表示弱项。二者合并可作 ΔP 表示的**双分支**（文本卡 / 可执行文件夹） |
| **元层同族（待确认）** | **Meta Context** | 仓库中**无**名为「Meta Context」的 PDF 或卡片；按语义最接近的 in-repo 元层工作是 **MemEvolve（Meta-Evolution of Agent Memory Systems，2025-12-21）**：MemEvolve 做**记忆系统架构的元演化**，MCE 做**上下文工程技能的元演化**。二者同属「元层搜索」，**MCE ≈ MemEvolve 的上下文侧对应物**。**注**：此条为解释性连接，见 §9 待确认 |
| **弱化子集** | **Gödel Agent** | Gödel Agent 是**自指递归自改进**（连元算法都可重写，改自身代码）；MCE 只改**上下文函数与检索程序**，元层 agent 的代码固定、不递归自指。→ MCE = Gödel 理想的**可计算、弱化、非自指**子集（同 ACE 卡对 Gödel 的定位，但 MCE 比 ACE 多改了「检索程序」这一层） |
| **前置依赖** | 可记录完整 rollout（含 eval 标签）、可判定成败 | SSEA 具备（快环事件流）；**但缺非 LLM 的提案/归因器** |
| **可替换其验证环节** | **SEDM** | MCE 的验证是「J_val 择优」（分数量级）；SEDM 的 SCEC 打包 + **A/B 准入**是**成败式**。→ 用 SEDM 的 A/B 准入替换 MCE 的 best-so-far 评分比较，**正好消掉 C9 冲突**（与 MemSkill × SEDM 同构） |
| **验证场** | **Dream-RSI** | MCE 的候选上下文/技能可在重放模拟器上离线验证，省真实交互（与 PSN×Dream-RSI、MemSkill×Dream-RSI 同构） |
| **威胁模型覆盖** | **Misevolve** | MCE 的元 agent 会**写任意代码**（含检索程序），落在 Misevolve 的**工作流/工具路径误演化**象限。→ 引入前应过 Misevolve 红队清单 |
| **写入/巩固侧互补** | **FLEX** | FLEX 的人工三分支写入 + logistic 停机判据，可与 MCE 的「技能自学的停机判据」交叉验证；FLEX 的 updater 正是 MCE 的可演化对象之一 |
| **记忆组织侧** | **LightMem / A-MEM / Mem0** | LightMem 的主题分段可作 MCE 基座 agent 的**批量处理边界**；A-MEM 的链接拓扑 / Mem0 的事实 CRUD 可作 MCE 上下文工件的**组织层**（MCE 不管条目怎么连，只管函数怎么演化） |
| **训练稳定性** | **RAGEN** | 若保留任何形式的可学习选择器，RAGEN 的 Echo Trap 诊断是必需仪器 |
| **对照（非组合）** | Voyager / ADAS / Reflexion / Gödel Agent | Voyager/ADAS 提供技能/架构搜索背景（MCE ≈ 在 CE 技能层的 ADAS）；Reflexion 式口头反思是 MCE 用「结构化技能演化」取代的东西 |

### 6.2 推荐组合方案
1. **组合 A（首选）：MCE × MemSkill —— ΔP 的统一双层表示（并入同一工作流）**
   - 接口形态：**共用一套 ΔP 槽 + ΔR-proc 发布通道 + 四权管线**。MemSkill 提供 ΔP 的**写端**（难例缓冲、归因、边界权、退役计数、快照回滚）；MCE 提供 ΔP 的**整体上下文函数视角**（检索算子演化、双层解耦、warm-start 精修、best-so-far 回滚）。ΔP 的两个产物分别走 ΔM（工件，受 C8 约束）与 ΔR-proc（检索/组织程序）。
   - 组合后新增能力：SSEA 首次拥有**统一的「上下文准备元技能」对象**，覆盖写端（MemSkill）与检索端（MCE），且不重演实验 3 形状错。
   - 新增风险：两篇的回路高度重叠，若分别实现会重复建设；必须先合并立项。
2. **组合 B：MCE × SEDM —— 去掉 C9 的准入官**
   - 接口形态：MCE 负责**提案与演化**（agentic crossover + warm-start 精修），SEDM 负责**验证**：候选上下文/技能打成 SCEC 包，走 **A/B 成败准入**，替换 MCE 的 `argmax J_val`。
   - 组合后新增能力：演化回路在**零评分函数**下闭合（C9 合规）。
   - 新增风险：A/B 需成对运行，睡眠期预算翻倍。
3. **组合 C：MCE × PSN —— 程序化结构的两面**
   - 接口形态：PSN 管 ΔS（环境侧技能网络，契约+门控+回滚）；MCE 管 ΔP（上下文侧元技能，检索算子+双层演化）。**共用四权管线与快照/回滚，但计数与指标完全分开。**
   - 组合后新增能力：SSEA 同时拥有「世界侧技能」与「上下文侧元技能」两套程序化结构。

### 6.3 本篇在组合中的典型角色
- **元技能（ΔP）的双层形式化者 / 检索侧演化供给者**：不提供验证判据（那是 SEDM），也不提供写端回路细节（那是 MemSkill），而是回答「**给智能体准备上下文这件事本身，如何被形式化为一个可演化对象**」，并把**检索策略**纳入可演化范围。
- 次要角色：**warm-start 精修 + best-so-far 回滚**的增量演化模板；**停机判据**的又一候选。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 正面命中 C3 第四类问题（元技能归属）与 `retrieve` 键收窄（检索算子可演化）；给出双层形式化与演化回路。扣分：任务是 NL 分类 benchmark，非生存控制环（实测：五领域 Table 1） |
| 立场兼容性 | **2** | **C2 硬冲突（全 NL 载体）、C9 硬冲突（J_val 评分选择）、C1 硬冲突（无生存）、C8 硬冲突（知识语料）**；C3/C6 四权形状/C10 是加分项，但不足以抵四处硬冲突（实测 + 推断） |
| 可搬运性 | **3** | 可干净拆出：双层解耦、双产物发布纪律、best-so-far 回滚、warm-start 精修、检索算子演化面、停机判据。不可拆：agentic crossover 的 LLM 搜索、文件夹式技能的 NL 载体、J_val 选择——即核心回路不可搬（推断） |
| 证据强度 | **4** | 广度足：5 领域 × 4 LLM × offline/online + 双层消融 + 模型混淆排除 + 迁移/效率分析（Table 1–4、Fig.3–4）。扣分：**全篇未报 seed 数与方差**；用数据子集；预印本未审稿（实测） |
| 组合价值 | **4** | 与 MemSkill / ACE / PSN / SkillRL / AutoSkill / Gödel Agent / MemEvolve / SEDM / Dream-RSI / Misevolve / FLEX / LightMem / A-MEM / Mem0 / RAGEN 均可点名连接；但**与 MemSkill 重叠度高**，边际组合价值低于其单独价值（推断） |
| 落地成本 | **2** | 反向口径（成本越低分越高）：需新建 ΔP 表示与槽位、双产物发布纪律、慢环提案/回滚、检索算子演化面、warm-start 精修，并**先**决定 ΔP 归属与「与 MemSkill 合并还是分建」；去语言化依赖缺失的 RuleCompiler。与 MemSkill 重复建设风险高（推断） |

---

## 8. 裁决与下一步

- **应用等级：B（零件采用）** —— 理由：① 它把 MemSkill 的「记忆技能」**推广为整个上下文函数的元技能**，并给出**双层形式化**，正面回答 C3 第四类问题（架构级贡献）；② 但它的核心回路**同时踩 C2 与 C9 两条硬约束**（NL 载体 + J_val 评分选择），且 C1/C8 亦冲突，不可整体采用；③ 取零件：双层解耦判据、ΔP→{ΔM,ΔR-proc} 双产物纪律、best-so-far 回滚、warm-start 精修、检索算子演化面、停机判据。
- **优先级：P2** —— **与 MemSkill 同族且高度重叠**，建议**并入 MemSkill 工作流一并处理**，避免重复建设；若团队决定给 ΔP 一个正式双层模板，可升 P1。
- **建议动作**：
  1. **先下裁决（与 MemSkill 合并）**：在架构文档中正式确认「MemSkill 记忆技能 + MCE CE 技能 = 同一第四类 ΔP，发布通道并入 ΔR-proc，属 GenePackage 本能段；MCE 是 ΔP 的一般形式，其产物分走 ΔM（知识工件，不进基因包）与 ΔR-proc（检索/组织程序）」。**这是零成本的第一顺位产出。**
  2. **给 `retrieve` 装演化面**：把检索策略作为 ΔR-proc 的可演化对象（对齐 MCE 的 F 算子），先做**非 LLM 的结构化检索规则**（触发谓词 → 段选择），再谈演化。
  3. **立「warm-start 精修」纪律**：慢环任何改写上下文的路径**禁止整体重建**，一律在上一版最优上精修（与 ACE「禁止整体重写」同源）。
  4. **实现 best-so-far 回滚（成败版）**：新上下文/技能在近期环境事件上**未更差即保留、劣化即回滚**，判据用成败计数而非 J_val 分数。
  5. **补边界权**：给 ΔP 演化加编辑上限 + 危险操作白名单（对齐 MemSkill 的「DELETE/NOOP 不参与演化」）。
  6. **顺序依赖**：动作 2–5 依赖 RuleCompiler（缺失），建议与 PSN/MemSkill 卡片动作合并立项。
- **最小验证实验（检索算子演化，服务实验 2）**：
  - **双臂 / 消融**（在现有记忆检索实验上做，不动快环）：A 臂（对照）= 固定 retrieve 键（现状）；B 臂 = ΔR-proc 式**结构化检索规则**（触发谓词 → 段选择），但**锁死不演化**；C 臂 = B + 慢环演化检索规则（best-so-far 成败回滚）。≥8 seed。
  - **判据（分档，先看分母）**：① 机制计数：检索规则条数、命中段数、每睡眠期提案/回滚数、规则是否只增不减；② 行为差：`retrieve` 命中率是否脱离 **0.5164**（注意危险回避率两臂已饱和于 **0.9814**，不可作判据）；③ 淘汰结果：死亡率/存活时长（环境判定）。
  - **预期与证伪条件**：预期 B 臂命中率高于 A，C 臂高于 B。**证伪**：若 B、C 差异落在噪声内且命中率不动 → 说明瓶颈在**检索键/表征**而非检索策略程序，本篇路线降级 P3；若 C 臂检索规则单调增长且过拟合训练错误（换环境即失效）→ 说明「演化检索算子」在非平稳生存域不可行，须回到固定键收窄。
- 若 **E 不采用**：不适用（本篇至少贡献了 ΔP 双层形式化与双产物发布纪律，零成本）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **ΔP 归属与合并**：接受「MCE CE 技能与 MemSkill 记忆技能 = 同一 ΔP」吗？若接受，两篇的回路是**合并实现**还是分建？
  2. **ΔP 双产物发布纪律**：ΔP 同时产出 ΔM（知识工件）与 ΔR-proc（检索程序）——是否接受「同一 ΔP 需在发布通道上再分一次」这一新增工程纪律？
  3. **检索算子是否入演化范围**：MCE 把 retrieve 函数列为可演化对象，SSEA 是否采纳？（这直接改变 `retrieve` 键收窄的解法方向。）
  4. **验证信号**：MCE 的 J_val 选择必须换成什么？建议 SEDM 式 A/B 成败准入 + 事实计数，需团队确认。
- **需补查的文献或资料**：
  1. **「Meta Context」指向哪一篇**：仓库中**无**名为「Meta Context」的 PDF 或卡片。本卡暂按「元层上下文优化一族」解释，并以 **MemEvolve（Meta-Evolution of Agent Memory Systems，2025-12-21）** 作最接近的 in-repo 对应物。**请团队确认该名称的确切所指**，若为独立论文应补卡。
  2. 论文未报 seed 数与方差——需向作者/代码仓库确认主结果重复次数（github.com/metaevo-ai/meta-context-engineering）。
  3. 完整 learned skills 集合（论文称放在仓库 assets，正文只给 FiNER 一例，§C p26）。
  4. Dynamic Cheatsheet / GEPA 原文（本卡对二者的描述转引自 MCE 的 §2.1，未读原文）。
- **需人工核对的公式 / 实现**：
  1. Algorithm 1 的 `c*_k ← argmax_{c∈{c*_{k−1}, c_k}} J_val(c)` 中，技能 s_k 是否也参与「保留/淘汰」（算法只对 context 做 argmax，技能库 H_k 无条件累积）——需核对技能是否真的从不被淘汰。
  2. §4.2 摘要称「5.6–53.8% 相对提升（均值 16.9%）」，而 Table 1 的 Avg. Rel. Gain 为 89.1%（相对 base）——两处口径不同（前者对 SOTA、后者对 base），需在引用时区分。
  3. §4.1 称「MCE base-agents are allowed to invoke DeepSeek V3.1 during its execution」，而 §E p43 的 utility 注释 `model=os.getenv("SANDBOX_MODEL")` 固定 DeepSeek V3.1——需确认基座 agent 可调用的模型范围。
  4. Table 1 的 MCE online 未列 full 版（因单次处理无法迭代演化，Table 3 注），online 的 74.1% 来自哪一变体需核对（Table 1 的 online MCE 为 68.0/20.0/76.4/0.66/0.63）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “we introduce Meta Context Engineering (MCE), a bi-level framework that supersedes static CE heuristics by co-evolving CE skills and context artifacts… achieving 5.6–53.8% relative improvement over state-of-the-art agentic CE methods (mean of 16.9%)” | p1（Abstract） |
| “At the meta-level, we propose agentic skill evolution… driven by agentic crossover, an evolutionary operator that synthesizes superior skills by reasoning across task specifications, historical CE trajectories, and performance metrics.” | p2 |
| “MCE decouples what to learn (the context function c_s) from how to represent and learn it (the skill s).” | §3.1 p5 |
| 上下文函数：c(x)=(F_k∘···∘F_1)(x;ρ)，ρ 静态组件、F 动态算子 | Eq.1 p4 |
| 双层目标：s*=argmax_s J_val(c*_s) s.t. c*_s=argmax_cs J_train(cs;s) | Eq.2–3 p4–5 |
| 技能数据库：H_{k−1}={(s_i,c_i,J^train_i,J^val_i)}；agentic crossover：s_k=CROSSOVER(τ,H_{k−1}) | §3.2 p5；Eq.4 p5 |
| 技能=文件夹，含 (1) methodology (2) executable scripts (3) structured context templates (4) validation protocols (5) dynamic context operators | §3.2 p5 |
| 基座执行：c_k=ENGINEER(τ,s_k;c*_{k−1},R_k)；上下文函数=目录下文件集合（静态 ρ + 动态算子 F） | Eq.5 p5–6 |
| Algorithm 1：三阶段（skill evolution / context optimization / evaluation）；“a single offspring context c_k is generated and compared against the current best c*_{k−1}, with the better one retained”；“history-informed (1 + 1)-ES”；H_k←H_{k−1}∪{(s_k,c_k,J^train_k,J^val_k)} | §3.4 p6 |
| 工具集 T={Read,Write,Edit,Bash,Glob,Grep,TodoWrite}；“read/write permissions of both agents are strictly scoped according to their respective roles and the current iteration” | §3.4 p6 |
| Table 1：offline MCE 89.1% / ACE 70.7% / GEPA 61.5%；online MCE 74.1% / ACE 41.1%；MCE 75.0/20.0/89.2/0.70/0.80 | p8 |
| Table 2：强弱模型迁移，MCE 平均相对退化 23.6/17.1/43.4 vs ACE 28.1/23.6/48.3 | p8 |
| Fig.3 上下文效率：MCE-S 73% @ ~1.5K token vs ACE 65%；MCE-L 75% @ 20K vs ACE 70% @ 79K | p9 |
| Fig.4 训练效率：13.6× 加速（1.9h vs 25.8h）；450 rollout 达 95% vs ACE 2169 rollout 达 94% | p9 |
| Table 3 消融（FiNER offline）：full 75 / w/o skills 73 / fixed skill 71 / ACE 71 | p10 |
| Table 4 模型混淆排除：MiniMax M2.1 使 ACE 变差（67 vs 70，playbook 114K vs 79K token） | p10 |
| §5 局限：“MCE may not offer advantages on reasoning-intensive tasks… MCE may struggle in scenarios where rollouts involve very long and complex trajectories.” | p10–11 |
| §5 Future work：“Investigating skill transfer across tasks… are interesting open questions.” | p11 |
| §C learned skill：FiNER 最优技能 = 8 阶段系统化方法 + 三文件上下文（reasoning-chains.md / semantic-principles.md / tag-reference.md）+ 三次 LLM 调用工作流 | §C p26–30 |
| §D.3 技能自学的停机判据：验证模式 <3 / 训练准确率 >90% / 估计 train-val gap >1.5% / 不可约错误 >40% | §D.3 p36 |
| §D.3–D.5 演化出的检索函数：symptom2disease 1,440 行 / LawBench 177 行 / Aegis 995 行 | §D.3–D.5 p36–43 |
