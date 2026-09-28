# 论文分析卡片 · ACE

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-10-06 Agentic Context Engineering Evolving Contexts for Self-Improving Language.pdf` |
| 标题 | **Agentic Context Engineering (ACE): Evolving Contexts for Self-Improving Language Models** |
| 作者 / 机构 | Qizheng Zhang\*、Changran Hu\*、Shubhangi Upasani、Boyuan Ma、Fenglu Hong、Vamsidhar Kamanuru、Jay Rainton、Chen Wu、Mengmeng Ji、Hanchen Li、Urmish Thakker、James Zou、Kunle Olukotun；1Stanford University、2SambaNova Systems, Inc.、3UC Berkeley（\*等贡献） |
| 发表时间 / 出处 | ICLR 2026 会议论文；arXiv:2510.04618v3 [cs.LG]，PDF 页眉标注 2026-03-29（文件日期前缀 2025-10-06，为初版时间） |
| 论文链接 | arXiv:2510.04618 |
| 代码链接 | github.com/ace-agent/ace（§Reproducibility Statement p11） |
| 标签 | 上下文适应（context adaptation）· 不更新权重 · 生成者/反思者/整理者三角色 · 增量 delta 更新 · grow-and-refine · 简洁偏置（brevity bias）· 上下文坍缩（context collapse）· playbook |
| **应用裁决** | **B 零件采用**（itemized bullet + 元数据计数器 + 非 LLM 确定性 delta 合并 + grow-and-refine 去重/剪枝触发器；**不采用**其 NL playbook 载体与「整理者直接应用、无验证门」的写入路径） |
| 优先级 | **P1** |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：不做权重更新，只把**上下文**当作会演化的 playbook 来积累/精炼/组织策略——用 Generator（产生轨迹）、Reflector（从成败中蒸馏洞察）、Curator（合成结构化 delta）三角色分工，配**增量 delta 更新**（局部编辑替代整体重写）与 **grow-and-refine**（追加新条目、原地更新旧条目、语义嵌入去重、超长触发剪枝），从而同时治住「简洁偏置」与「上下文坍缩」；AppWorld 平均 +10.6%、金融 +8.6%，且**无需标注监督、只靠自然执行反馈**即可适应（摘要、§3、§4）。
- **对 SSEA 的意义**：它给出了「**记忆库防坍缩 + 防膨胀**」的一套可拆零件——条目化 + ID + helpful/harmful 计数器 + **非 LLM 的确定性合并** + 去重/剪枝触发器，正好补 SSEA 慢环**记忆巩固**缺的写入侧协议；同时它把「上下文到底算记忆还是技能」这个 C3 归属问题逼到了台面上（ACE 把二者混装在一个 playbook 里），并提供了一个 **C9 较干净的信号源**（执行成败而非外部评分）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- 问题本身：LLM 应用（agent、领域推理）越来越依赖 **context adaptation**——改输入而不改权重。但既有方法有两大缺陷（§2.2 p3）：
  1. **Brevity bias（简洁偏置）**：prompt 优化器偏爱「简洁可套用的指令」，这会丢掉领域启发式、工具用法、常见失败模式。论文点名 GEPA 把 brevity 当优点（p2）；Gao et al. 记录到迭代优化反复收敛到近乎相同的短指令（§2.2 p3）。
  2. **Context collapse（上下文坍缩）**：让 LLM **整体重写**累积上下文时，上下文越长越被压成更短的摘要，细节被抹掉、性能骤降。
- 它指出的既有方案缺陷：GEPA 式的「整段 prompt 变体 + 验证集筛选」是端到端重写；Dynamic Cheatsheet（DC）的 DC-CU/DC-RS 也是整体重写 cheatsheet（§C.2 p22–23）。二者都踩坍缩风险。

### 2.2 核心思想（关键 insight）
1. **上下文应是「详尽的、结构化的 playbook」，不是简洁摘要**。论文明确论证方向与人相反：人类受益于简洁概括，LLM 在**长而详尽**的上下文下更有效，且能自己在推理时挑出相关部分（p2，引 Jiang et al. 2025、Liu et al. 2025b、Suzgun et al. 2025）。
2. **分工解耦：评估/洞察抽取 与 整理/合并 必须分开**。Reflector 只管「从成败里提炼教训」，Curator 只管「把它变成 delta 并合入」；合并本身是**轻量、非 LLM 的确定性逻辑**（§3 p4）。这既是质量来源，也是成本来源（局部编辑替代全文重写）。
3. **增长要有，但冗余要控**：grow-and-refine——新条目追加、旧条目原地更新（如计数器 +1）、语义嵌入比对去重、可主动做也可**懒惰做（仅当超出上下文窗口时）**（§3.2 p5）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **三角色流水线** | Query + Playbook → Trajectory（Generator）→ Insights（Reflector）→ Delta Context Items（Curator）→ 合入 Playbook | 职责解耦，避免单模型过载；灵感来自 Dynamic Cheatsheet | §3 Fig.4 p4–5 |
| **Itemized bullet 表示** | 一条知识 → {metadata: 唯一 ID + helpful/harmful 计数器；content: 可复用策略 / 领域概念 / 常见失败模式} | 局部化更新、细粒度检索、可增量合并/剪枝/去重 | §3.1 p5 |
| **增量 delta 更新** | Reflector 蒸馏 + Curator 合成的小批候选 bullet → 由**非 LLM 的确定性逻辑**合并进既有上下文 | 避免整体重写的信息损失与算力/延迟开销；多条 delta 可并行合并、支持批处理 | §3.1 p5、§4.7 p9 |
| **Generator 反标** | 解题时 Generator 标出哪些 bullet 有用/误导 → 反馈给 Reflector | 让「哪条记忆真的起作用」可记账（**环境侧可用性信号**） | §3.1 p5 |
| **Grow-and-refine** | 新 ID 追加；已有条目**原地更新**（计数器递增）；语义嵌入比对去重 | 兼得扩展与冗余控制 | §3.2 p5 |
| **惰性 / 主动精炼双模式** | 触发条件：每条 delta 后（主动）或 仅当超出上下文窗口（惰性） | 按延迟/精度需求切换 | §3.2 p5 |
| **多轮反思 + 多 epoch 适应** | Reflector 最多 5 轮精炼；离线适应最多 5 个 epoch；batch size = 1 | 逐步强化上下文 | §4.2 p7、§A.6 p21 |
| **剪枝触发器（最大上下文长度）** | 超阈值 → 合并/剪掉陈旧或低效用条目 | 防无界增长 | §A.6 Table 21 p21 |
| **噪声防御（第一道防线）** | grow-and-refine 合并去重 + 可依 metadata 过滤被标 harmful 的条目 | 抗上下文噪声 | §A.4 p20 |
| **离线 warmup → 在线适应** | 先离线把上下文初始化，再在线增量 | 在线起点更好 | §4.6 Table 3 p9 |

### 2.4 关键表示与数据结构
- **Playbook**：结构化的**条目化 bullet 集合**，不是单块 prompt。每 bullet = 元数据（唯一标识符 + helpful/harmful 计数器）+ 内容（可复用策略 / 领域概念 / 常见失败模式）。论文明确指出 bullet 概念「类似于 Dynamic Cheatsheet 与 A-MEM 中的 memory entry」，但在其上加了计数器与本地化更新（§3.1 p5）。
- **Delta context**：Reflector 蒸馏、Curator 合成的小批候选 bullet，由确定性逻辑合并（§3.1 p5）。
- **信号来源**：执行反馈（代码执行成功/失败）、单元测试报告、以及**可选的** ground-truth 标签（Reflector 可见与否在实验中作为变量「GT Labels ✓/✗」被显式对照，Table 1/2 p7–8）。
- **载体**：全部为**自然语言**文本（附录 F 的完整 prompt 均为 NL 指令 + JSON schema，p24–32）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| AppWorld（agent，离线） | ReAct 42.4、+ICL 46.0、+GEPA 46.4 | **ReAct+ACE 59.4（+17.0）**；无 GT 标签仍 57.2（+14.8）；TGC 76.2 / SGC 64.3（test-normal） | Table 1 p7，TGC/SGC 平均，DeepSeek-V3.1-671B，官方 ReAct 实现；未见 seed 数说明 |
| AppWorld（在线） | ReAct 42.4、DC(CU) 51.9 | **ACE 59.5（+17.1）**，无 GT；test-challenge TGC 66.0 / SGC 48.9 | Table 1 p7 |
| AppWorld 榜单对照 | 榜首 IBM CUGA 60.3%（GPT-4.1） | ACE 离线 59.4% **持平**；在线在 test-challenge 上 TGC +8.4、SGC +0.7 **超过** CUGA，且用更小的开源模型 | p8，2025-09-20 快照；脚注声明 CUGA 仅作量级参照、非方法基线 |
| 金融 FiNER / Formula（离线，有 GT） | Base 69.1、ICL 69.6、MIPROv2 70.9、GEPA 72.5 | **ACE 81.9（+12.8）**：FiNER 78.3、Formula 85.5 | Table 2 p8，accuracy（精确匹配） |
| 金融（在线，无 GT） | Base 69.1、DC(CU) 65.4（**退化** −3.7） | ACE 72.9（+3.8）；但 FiNER 单科 67.3（**−3.4，低于 base 70.7**） | Table 2 p8 |
| 跨 LLM 泛化 | 各模型自身 base | DeepSeek-V3.1 / GPT-OSS-120B / GPT-5.1 / Llama-3.3-70B 全部有增益；论文称常见 5–12 点；Llama-3.3-70B 增益较小 | §4.5 p9、§A.1 Table 5–9 p16–18 |
| 医疗 DDXPlus | GEPA 76.4（+1.2） | **ACE 90.2（+15.0）** | Table 10 p18，离线，1000 训练样本 |
| BIRD-SQL | GEPA 52.2（+4.4） | ACE 52.9（+5.1），Simple 子集 53.5（+7.1） | Table 11 p18；用 GPT-4o-mini 作 LLM-as-a-judge |
| 消融：Reflector / 多 epoch | 全量离线 ACE 59.4 | 去掉 Reflector 且去多 epoch → 55.1（+12.7）；只去多 epoch → 56.8（+14.4） | Table 3 p9 |
| 消融：离线 warmup | 在线 ACE 56.1 | +warmup → 59.5（+17.1） | Table 3 p9 |
| **消融：增量 delta 更新** | 有增量：TGC 76.2 / SGC 64.3 / 平均 70.3（test-normal） | **无增量：67.3 / 46.4 / 56.9** | Table 18 p20。**核心消融**：delta 更新贡献最大份额 |
| 成本：离线 vs GEPA | 延迟 53898 s、rollouts 1434 | **9517 s（−82.3%）、357 rollouts（−75.1%）** | Table 4(a) p10 |
| 成本：在线 FiNER vs DC | 延迟 65104 s、$17.7 | **5503 s（−91.5%）、$2.9（−83.6%）** | Table 4(b) p10 |
| 细粒度 token 账 | GEPA 适应期输入 204.1M / 输出 1.87M | ACE 39.3M（−80.8%）/ 0.31M（−83.6%）；rollouts +42.6%；**评估期输入 token +117.4%**、输出 +7.6% | Table 12–15 p18–19 |
| KV cache 摊销 | 按原始 token 计费 | GPT-5.1 + OpenAI prompt caching：**91.8% 输入 token 命中缓存**，billed 输入成本 **−82.6%** | §4.7 p10、§A.3 p18–19 |
| 反思质量鲁棒性（弱反思者） | FiNER base 70.7 | 反思者换 GPT-OSS-120B → 76.6（+5.9）；DeepSeek-V3.1 → 78.3（+7.6）；GPT-5.1 → 78.5（+7.8） | Table 16 p19 |
| 有害反思注入压力测试 | 无注入 78.3 | 每 1 步注入 → **66.7（−4.0，低于 base）**；每 5 步 76.1；每 10 步 77.0；每 25 步 77.8；每 50/100 步 78.2 | Table 17 p19–20，FiNER 离线 |
| 超参敏感性 | base（无 ACE）53.3 | 反思轮次 1→61.3、3→65.8、**5→67.6**、10→65.2（过多反而降）；去重阈值 50%/70%/90% → 77.0/73.9/78.6；最大长度 10K/50K/100K → 78.6/78.4/78.3 | Table 19–21 p21，AppWorld test-normal 平均 / FiNER accuracy |

### 2.6 论文自陈局限与边界条件
- **假设依赖**（§5 p10）：
  1. 依赖一个**足够强的 Reflector**——若反思者从轨迹中抽不出有意义洞察，构造出的上下文会变噪声甚至有害；在「任何模型都抽不出洞察」的领域任务里，上下文自然就没有这些内容（论文承认与 DC 同类依赖）。
  2. 依赖**可靠的反馈信号质量**。无 GT 且无可靠执行信号时，ACE 与 DC **都会退化**——金融在线无 GT 的 FiNER 为 67.3，低于 base 70.7（Table 2 p8）。论文自陈：此时上下文会被 spurious/misleading 信号污染，是推理时自适应的**潜在局限**。
  3. 有害反思**每一步都注入**的极端对抗条件下，性能会跌破 base（Table 17 p19）。
- **明确不适用的情形**（§5 p10）：并非所有应用都需要rich context——
  - HotPotQA 一类更适合**简洁高层指令**（如「如何检索与综合证据」）；
  - Game of 24 一类固定策略游戏只需**一条可复用规则**，多余上下文是冗余。
  - 结论性边界：ACE 只在「需要细致领域知识、复杂工具使用、环境特定策略」的场景最有益。
- 其他边界：评估在公开 benchmark 上做，未涉及人类受试者或隐私数据（Ethics Statement p11）；论文未声明 seed 数与多次运行的方差（**未提及**）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ◐ | 主战场是 AppWorld agent（多轮工具调用、API、代码执行）与金融推理，是**交互式闭环**而非纯文本生成；但目标函数是被外部 benchmark 定义的任务完成度，不是生存 | 把「执行反馈」换成**环境侧存活/危险事件**；playbook 内容改为结构化信号而非解题话术 |
| **C2** 自然语言只作观察员接口 | **✗/◐** | playbook、Reflector/Curator 洞察、Generator 标注全部是**自然语言**（附录 F p24–32 全 NL prompt + JSON）；三角色都是 LLM | **核心冲突点**。改造：把 bullet content 换成**结构化条目**（条件-动作-预期、参数槽位），NL 只留在慢环日志/解释面；快环只读结构化快照，运行时零语言 |
| **C3** 权重/记忆/技能三分离 | ◐（**权重侧 ✓，记忆/技能侧 ✗**） | ① **权重侧强支持**：明确「改输入而非改权重」，且论证改上下文比改权重便宜（§5 p10）；② **记忆/技能侧混装**：一个 playbook 里同时装「可复用策略 / 领域概念 / 常见失败模式」（§3.1 p5），§C.1 更明说 agent 场景要保留「step-by-step procedures 与 tool-use rules」——**这是技能（ΔS）**，而「领域概念、事实证据」是**记忆（ΔM）**，ACE 未做区分 | **必须拆书**：playbook 拆成 ΔM 子册（事实/领域概念/失败模式）与 ΔS 子册（程序/工具规则/契约）；两者生命周期、验证门、可遗传性不同（ΔS 可入 GenePackage，ΔM 不可跨代） |
| **C4** 低算力低带宽 | ◐（**适应期 ✓，运行期 ✗**） | 适应期：delta 更新 + 非 LLM 合并使输入 token **−80.8%**、输出 **−83.6%**、延迟 **−82.3%**（Table 12/4(a)）；惰性原则可只在超窗时才付出整理成本。**但**：评估期原始输入 token **+117.4%**（Table 14 p18）；三角色每样本 3 次 LLM 调用、反思最多 5 轮、离线 5 epoch；rollouts +42.6% | 只搬**非 LLM 的确定性合并/去重/剪枝**部分（零 LLM 成本）；LLM 三角色不进 SSEA。长上下文靠 KV cache 摊销的论证（91.8% 命中）**对 SSEA 不适用**——快环无 LLM、无 KV cache |
| **C5** 精准回忆历史 | ◐ | 支持侧：itemized bullet + 唯一 ID + 计数器 → 局部化更新、**细粒度检索**、可增量合并/剪枝/去重（§3.1 p5）。冲突侧：bullet 存的是**蒸馏后的通用洞察**，不是可精准寻址的具体经历；去重靠**语义嵌入比对**（有损合并）；无「按具体 episode 精确写入/检索/遗忘」的机制 | 保留 ID + 计数器 + 局部更新的**记账骨架**，但内容层挂到 SSEA 已有的可精准寻址 episode 索引上；**去重只做「链接」不做「覆盖」**（同 LightMem 软更新），关键帧不合并 |
| **C6** 可自主修改自身 | **✗** | 只改上下文，**不改代码、不改参数权重**（摘要、§3）。更严重的是**权限结构缺失**：Curator 产出 delta 后由确定性逻辑**直接合并**，论文中**没有验证门**——即「提案权 + 应用权」在手，「边界权 + 验证权」缺位。§A.4 的自陈缓解措施（去重、按 metadata 过滤 harmful）只是过滤器，不是门 | 改造成四权分离：delta 提案（慢环）→ **四级验证门（格式→沙盒→回归→环境实测）** → 原子升版；把 §A.4 的「harmful 过滤」降级为门前的**预筛**，不等于门 |
| **C7** 保存/恢复/变异/继承 | ◐ | 支持侧：上下文可**跨模型/跨模块共享**（p2 引 Khot et al. 2023），条目带 ID、计数器、版本式原地更新，具备可打包的雏形；论文还点出可支持 **selective unlearning**（§5 p10，因上下文人类可读）。缺失：无变异、无继承、无 GenePackage 式跨代机制 | playbook 可作为 **GenePackage 的候选内容源**，但必须经 HeritableFilter 过滤（只留结构性先验）+ 跨域重验；`helpful/harmful` 计数器可作为**淘汰证据**随包携带 |
| **C8** 给基因先验，不给知识语料 | **✗（若直接继承）** | ACE 的核心主张恰恰是**积累后天知识**（领域概念、XBRL 规则、工具用法、失败模式），且越详尽越好（p2、§3）。这正命中 C8 要防的「知识语料跨代膨胀」 | 只把**结构**（条目组织方式、合并/去重/剪枝规则、计数器协议）当先验入包；**内容一律不跨代**。与 C8「知识不跨代」硬对齐 |
| **C9** 不设评分函数，只有淘汰函数 | ◐（**本篇最值得记的一点**） | 支持侧：① 明确可在**无标注监督**下工作，信号来自**自然执行反馈**（代码执行成败、单元测试报告）——Table 1 无 GT 仍 +14.8；② Reflector 的 helpful/harmful 标签是**锚定在执行结果上**的归因，不是自由打分。冲突侧：① 离线变体使用 **GT 标签**作反馈（Table 1/2 的 ✓ 列）；② 评估口径本身是 benchmark accuracy 外部评分；③ BIRD-SQL 用 **GPT-4o-mini 作 LLM-as-a-judge**（§4.1 p6）；④ GEPA 对照臂依赖验证集上的 prompt-validation 循环 | **可用部分**：把「执行成败 → 条目计数器」这条链完整搬过来，它是**环境侧淘汰证据**而非评分。**剔除部分**：GT 标签、benchmark accuracy、LLM-as-a-judge 一律不入 SSEA。注意 §5 自陈——反馈信号不可靠时 ACE 会**退化甚至低于 base**（FiNER 在线无 GT 67.3 < base 70.7），这正好反证 C9「信号质量决定一切」的立场 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 无任何新算子；创新全在三角色**信息流**（L2）、增量 delta 合并与 grow-and-refine（L2/L3）；L1 纯借用（DeepSeek-V3.1 / GPT-5.1 / Llama-3.3 可换，算法与 prompt 不变，§4.5 p9） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无。四个 LLM 家族可即插即换（§4.5 p9） | 无（符合借用立场） |
| **L2 信息流层** | **主贡献层**：Generator/Reflector/Curator 三角色流水线；itemized bullet（ID + 计数器 + 内容）；delta 由**非 LLM 确定性逻辑**合并；grow-and-refine（追加 / 原地更新 / 语义去重 / 阈值剪枝）；惰性 vs 主动精炼 | **高**：直接是 SSEA 慢环**记忆巩固写入侧**的骨架，且合并侧零 LLM 成本 |
| **L3 学习层** | 自改进闭环（轨迹→洞察→delta→合并→再解题）；多轮反思、多 epoch；噪声/有害更新的鲁棒性边界（Table 17） | **中高**：提供了「自改进在**不改权重**前提下能做到什么程度」的经验上界，以及噪声容忍的量化边界 |
| **L4 演化层** | 无变异、无继承、无基因包；仅有「上下文可跨模型/模块共享」与 selective unlearning 的**提法**（p2、§5 p10），未实现 | **低（直接）／中（间接）**：playbook 可作为 GenePackage 内容候选，但必须先过 C8 过滤与 HeritableFilter 重验 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| Playbook（条目化 + ID + 计数器） | **记忆库条目 schema 升级**：现有 `retrieve` 键收窄 → 召回精度上限低，可用「细粒度检索 + 条目级计数器」补 |
| 增量 delta 更新（非 LLM 确定性合并） | **慢环巩固器（Consolidator）写入算子**：对应 SSEA 慢环「发布结构新版本 ΔM」，合并逻辑可确定性实现、无需模型 |
| grow-and-refine（追加 / 原地更新 / 去重） | **记忆库防膨胀策略**：回应「记忆库长期膨胀与信息损失」 |
| 剪枝触发器（最大上下文长度） | **慢环停机判据候选**：Table 21 显示 10K/50K/100K 三者性能几乎不变（78.6/78.4/78.3），说明**阈值不必精调**——这可直接支撑「睡眠期预算」的粗粒度设定 |
| helpful/harmful 计数器 | **记忆门（二级门）的环境侧证据源**：回应「记忆门开得准不准的选择性缺失」；同时是**债务 22 常量阈值**的一个可调输入候选（**注意**：ACE 自身的去重阈值/最大长度同样是常量，只是它证明了不敏感） |
| Reflector（洞察蒸馏） | 慢环**离线**组件；在 SSEA 中须换成非 LLM 的确定性抽取器，或置于观察员面 |
| 惰性精炼（超窗才整理） | LightMem 式「阈值触发巩固」的同类触发策略，可与睡眠期节律对接 |
| 成本台账（Table 12–15 口径） | **睡眠期计算预算的记账模板**（输入/输出 token、rollouts、延迟分项）——直接服务「睡眠期计算预算未定义」 |
| 上下文坍缩检测（18,282 → 122 token） | **记忆库健康度监控指标**：把「条目数 / 平均条目长度突降」做成告警，防 SSEA 记忆库静默丢信息 |

### 3.4 债务与验收实验对应
- **可回应的已知债务**：
  - 「**记忆库长期膨胀与信息损失**」——本篇最直接对应：grow-and-refine + 去重 + 剪枝触发器 + 坍缩检测指标。
  - 「**睡眠期计算预算未定义**」——Table 12–15 的分项成本台账是可照抄的记账模板；Table 4 的延迟/rollout 削减比例给出「增量 vs 全量重写」的代价对比基准。
  - 「**记忆门开得准不准的选择性缺失**」——helpful/harmful 计数器（锚定执行成败）可作为门的环境侧证据，而非评分。
  - 「**债务 22：记忆二级门用常量阈值，慢环不可调**」——部分回应：ACE 的阈值也是常量，但 Table 20/21 证明**对阈值不敏感**，可作为「先固定、后可调」的过渡依据；彻底解决仍需慢环可调参数。
  - 「**技能表示够不够（技能固化 0/33）**」——间接：§C.1 明确 agent 场景要保留「step-by-step procedures 与 tool-use rules」，这与 PSN 的技能契约化是同一主张；但 ACE 用 NL 承载，表示层问题仍归 PSN。
  - 「**`retrieve` 键收窄 → 召回精度上限低**」——itemized + 细粒度检索是检索侧的补充方向。
- **可服务的验收实验**：
  - 实验 2（记忆检索命中率 0.5164）：条目化 + 计数器 + 去重应直接作用于此指标。
  - 实验 4/5（Gene Manager 缺失而卡住）：playbook → GenePackage 的过滤链路可作为 HeritableFilter 的输入侧设计参照。
  - 危险回避率两臂均 **0.9814 已饱和** → **本篇不可用该指标做判据**，须换指标（见 §8）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **Itemized bullet 表示**（唯一 ID + helpful/harmful 计数器 + 单条内容单元） | 表示/数据结构 | **改造移植**（内容改结构化） | 记忆库条目 schema、ΔM 发布格式 | `retrieve` 键收窄、召回精度上限低；条目级可追溯 | 高 |
| 2 | **非 LLM 的确定性 delta 合并** | 算法/工程 | **直接移植** | 慢环巩固器（Consolidator） | 慢环合并零 LLM 成本、可并行、可批处理 | 高 |
| 3 | **增量更新替代整体重写**（防上下文坍缩） | 思想/协议 | **直接移植**（作为硬纪律） | 慢环所有「改写记忆库」路径 | **记忆库长期信息损失**（静默坍缩） | 高 |
| 4 | **grow-and-refine**（追加 / 原地更新 / 语义去重 / 阈值剪枝，可惰性触发） | 算法 | 改造移植 | 记忆库生命周期管理 | 记忆库无界膨胀 | 高 |
| 5 | **剪枝触发器 + 「阈值不敏感」实证**（10K/50K/100K → 78.6/78.4/78.3） | 工程/判据 | 直接引用 | 慢环停机判据、睡眠期预算 | 睡眠期计算预算未定义 | 中高 |
| 6 | **helpful/harmful 计数器（锚定执行成败）** | 协议 | 改造移植（改为环境侧事实计数） | 记忆二级门 / HeritableFilter 证据 | 记忆门选择性缺失；债务 22 | 中 |
| 7 | **分项成本台账口径**（适应期 vs 评估期，输入/输出 token、rollouts、延迟分项） | 工程/仪器 | **直接移植** | 睡眠期预算记账 | 睡眠期计算预算未定义（C4 仪器） | 高 |
| 8 | **坍缩检测指标**（条目数 / 平均长度突降，对照 18,282→122 token 事件） | 监控/协议 | 改造移植 | 记忆库健康度监控 | 信息损失不可见 | 中高 |
| 9 | **噪声容忍边界**（Table 17：每步注入有害更新才跌破 base） | 基准/思想 | 仅借思想 | Misevolve 红队清单 | 记忆路径误演化的容忍度量 | 中 |
| 10 | **自然执行反馈作为唯一适应信号**（无 GT 仍 +14.8） | 协议 | **直接移植** | 慢环信号源 | C9 合规的自改进信号来源 | 高 |
| 11 | **「详尽的 playbook 优于简洁摘要」的主张 + 反例边界** | 思想/对照 | 仅作对照 | — | 提示 SSEA：简洁压缩未必安全；但也提示存在**反例**（HotPotQA/Game-of-24 更适合简洁） | 中 |
| 12 | **离线 warmup → 在线增量**的两阶段节奏 | 协议 | 仅借思想 | 慢环预热 / 快环增量 | 冷启动起点质量 | 中 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（逐条）**：
  1. **C2（最硬）**：整条流水线以自然语言为载体、以 LLM 为三角色。SSEA 控制环不能进 NL。→ 必须做**载体替换**：bullet content 改为结构化条目；若无法替换，本篇只能停在观察员面。
  2. **C3（记忆/技能混装）**：一个 playbook 同时装策略（ΔS）与概念/失败模式（ΔM）。→ 必须**拆书**，两册走不同的验证门与生命周期。
  3. **C6（无验证门）**：Curator 产出即合并，缺边界权与验证权。→ 必须插入 SSEA 四级验证门；不可把「去重/harmful 过滤」误当作门。
  4. **C8（知识跨代）**：若 playbook 内容直接进入 GenePackage 即违规。→ 只传结构不传内容。
  5. **C9（评分件）**：GT 标签、benchmark accuracy、BIRD-SQL 的 LLM-as-a-judge 均为评分件。→ 剔除；只保留「执行成败 → 计数器」这条环境侧链。
  6. **C4（运行期成本）**：评估期原始输入 token **+117.4%**（Table 14），且 KV-cache 摊销论证对无 LLM 的快环不成立。→ 增量合并只许在慢环执行；快环只读不可变快照。
- **隐含假设与失效条件**：
  - 假设「存在可提取洞察的强反思者」。SSEA 若换掉 LLM 反思者，**这条假设直接失效**——这是搬运后最大的不确定性。
  - 假设「反馈信号可靠」。论文自陈不可靠时 ACE 会**退化到 base 以下**（FiNER 在线无 GT：67.3 < 70.7）。SSEA 的生存域若反馈稀疏/延迟，同样风险。
  - 假设任务**需要详尽上下文**。论文自陈 HotPotQA、Game of 24 一类更适合简洁指令——**SSEA 快环（毫秒级、低带宽）恰恰更像这类场景**，因此「详尽 playbook」不能在快环生效，只能在慢环作为知识库形态存在。
- **算力 / 带宽 / 工程代价**：
  - 每样本 3 次 LLM 调用（Generator/Reflector/Curator），Reflector 最多 5 轮，离线 5 epoch；AppWorld 离线适应 rollouts **+42.6%**（Table 12）。
  - 惰性精炼可把整理成本推迟到超窗时，是与「睡眠期」对接的关键。
  - 可搬的最贵零件其实是**便宜的**：确定性合并 + 去重 + 剪枝，零 LLM。**最贵且最不可搬的是 Reflector**。
- **搬运后的可能退化模式（若失败，以什么形式失败）**：
  1. **静默坍缩**：若某处仍走了「整体重写」，表现为条目数/平均长度突降而**指标短期不降**（对照 18,282→122 token 事件），等到某天突然掉。→ 用资产 8 的监控指标兜住。
  2. **噪声固化**：Reflector 换成弱抽取器后，噪声 bullet 被计数器反复确认，反而**加固错误条目**（Table 17 中「每 5 步注入有害」仍 +5.4，说明中等噪声被系统吸收而非清除）。
  3. **记忆库膨胀换了个形式**：去重阈值不当（Table 20：70% → 73.9，明显低于 50% 的 77.0）说明**去重激进度会真伤性能**，不是免费午餐。
  4. **C3 混装复发**：ΔM/ΔS 同册后，技能条目被当成记忆条目去重合并掉 → 技能失效被判成成功（对应债务 25/26/27/28 的形状）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名） | 说明 |
|---|---|---|
| **前置依赖** | 可记录完整执行轨迹、可判定执行成败 | SSEA 具备（快环事件流）；**但缺「非 LLM 的洞察抽取器」**——这是采用本篇的硬前置 |
| **互补（最紧）** | **SEDM** | 二者同在「记忆条目怎么进库」这条路上，但**职责正好互补且互纠**：SEDM 是**准入官**（SCEC 打包 + 配对 A/B 验证 + 抽象后重验，判「这条该不该进、能不能搬走」）；ACE 是**增量写入官**（delta 合并 + 计数器 + 去重剪枝，判「进了之后怎么长、怎么不坍缩」）。**接口**：SEDM 的 A/B 结论 → 写入 bullet 的计数器初值；ACE 的 grow-and-refine → SEDM 的合并巩固执行者。**互纠点**：ACE 的 Curator 无门直接合并，正需要 SEDM 的 A/B 准入来补 C6 缺失的验证权 |
| **互补** | **LightMem** | 同为「睡眠期离线整理」。LightMem 管**摄入压缩**（感觉记忆过滤 + 主题分段 + 阈值触发巩固 + 软更新「合并不删除」）；ACE 管**条目级增量合并与去重剪枝**。**接口**：LightMem 压缩后的主题段 → ACE 的 delta bullet → 睡眠期合并去重。**关键增益**：ACE 的 Table 21（10K/50K/100K 性能几乎不变）为 LightMem 的「缓冲达阈值才触发」提供了**阈值不敏感**的实证支撑 |
| **互补** | **Mem0** | Mem0 是**事实抽取 + CRUD 分类 + 实体关系图**；ACE 无实体图、无 CRUD 分类，只有扁平 bullet + 计数器。**分工**：Mem0 管事实类条目（ΔM 的事实子册），ACE 管策略/教训类条目的增量合并与去冗余。ACE 的 ID + 计数器可给 Mem0 的 CRUD 补上「效用记账」 |
| **替代 / 反模式对照** | **Dynamic Cheatsheet（DC）** | ACE **直接以 DC 为灵感来源并点名修它的病**（§3 p4、§C.2 p22–23）。DC-CU 每步整体重写 cheatsheet → **context collapse**（step 60: 18,282 token/66.7 → 122 token/57.1，低于无适应基线 63.7，Fig.2 p3）；ACE 用 delta 更新修之（Table 1 在线 59.5 vs DC 51.9）。**对 SSEA 的价值**：DC 是「记忆库整体重写」这一做法的**已量化反例**，ACE 是修法；SSEA 应把「禁止整体重写」写进慢环纪律 |
| **互补 / 冲突** | **ReasoningBank** | 二者都把轨迹蒸馏成可复用单元。RB 给出「**双路抽取**（成功给策略、失败给护栏）+ **k=1 少而精注入**」；ACE 给「**详尽 playbook 全量注入 + delta 合并 + 计数器**」。**冲突**：注入策略相反（少而精 vs 详尽）——SSEA 快环低带宽更像 RB 的 k=1，慢环知识库更像 ACE 的详尽。**互补**：RB 的**失败轨迹利用**是 ACE 缺的（ACE 只在 agent 场景靠执行成败，无显式双路 schema）；ACE 的计数器是 RB 缺的。**C9 关键差异**：RB 用 LLM-as-a-Judge + BoN 评分（硬冲突），ACE 可在无标注下靠执行反馈工作（较干净）——**ACE 是更合规的信号源** |
| **互补** | **Memento** | Memento 是「冻结 LLM + 案例库读写 + **可学习检索 μ**」，强在**检索侧**；ACE **完全不学检索**（仅在去重时用语义嵌入），强在**写入/合并侧**。二者拼起来才是完整的记忆闭环：μ 决定选什么、delta 合并决定库怎么长 |
| **对照 / 定位** | **Gödel Agent** | Gödel Agent 是**自指递归自改进的形式化北极星**；ACE 只改上下文、**不改自身代码与权重**（摘要、§3）。因此 ACE 是 Gödel 理想的一个**弱化但可计算的子集**：有自改进闭环、无自指。**价值**：给 SSEA 一个「自改进可以先在**不改自身**的层面做到什么程度」的实测下界（agent +17.0、金融 +12.8） |
| 互补 | **A-MEM** | 论文 §3.1 明确「bullet 概念类似 A-MEM 的 memory entry」。A-MEM 给**链接拓扑 + 近邻回写**，ACE 给**计数器 + 确定性合并**。链接骨架 + 效用记账可叠加 |
| 互补（技能侧） | **PSN** | §C.1 明确 agent 场景要保留「step-by-step procedures 与 tool-use rules」——**这就是技能**。ACE 用 NL 承载，PSN 用**带契约的可执行网络**承载。二者指向同一需求：**ACE 的 ΔS 子册应交给 PSN 表示** |
| 风险治理 | **Misevolve** | ACE 的「Curator 无门直接合并」+「中等噪声被系统吸收」（Table 17）正是**记忆路径误演化**的典型面。应过 Misevolve 的记忆路径红队清单 |
| 互补（写入侧） | **FLEX** | FLEX 的 updater 三分支写入 + logistic 增长曲线作慢环停机判据；ACE 的剪枝触发器与「阈值不敏感」实证可作为 FLEX 判据的**替代品或交叉验证** |
| 对照 | **Reflexion / GEPA** | Reflexion 是「试错-评估-反思」外环的**经典形状**，ACE 的三角色是它的**增量版**；GEPA 是 ACE 的主要对手基线（离线 AppWorld 46.4 vs 59.4），且 ACE 的 §C.1 给了二者清晰的适用边界（GEPA 适合单块指令优化，ACE 适合需保留大量细粒度洞察的场景） |

### 6.2 推荐组合方案
1. **「防坍缩记忆巩固」主干（ACE × SEDM × LightMem）** —— 推荐作为首选落地路径
   - **组合**：LightMem（摄入压缩 → 主题分段 → 睡眠期阈值触发）+ SEDM（SCEC 打包 → A/B 准入 → 抽象后重验）+ ACE（条目化 → delta 确定性合并 → grow-and-refine → 计数器 → 阈值剪枝）。
   - **接口形态**：LightMem 输出**主题化候选段** → SEDM 判「该不该进」并给出**环境侧事实证据** → ACE 的 Curator 产 **delta bullet**（ID + 计数器初值来自 A/B 结论）→ **非 LLM 确定性合并**入 ΔM 库 → 超阈值触发去重/剪枝。**全链路禁止整体重写**。
   - **组合后新增能力**：记忆库既能**控膨胀**（LightMem 压缩 + ACE 去重剪枝）又能**不丢信息**（ACE 增量 delta），且**每条入库有环境侧证据**（SEDM）。
   - **新增风险**：三段流水线的触发时序复杂化；SEDM 的 A/B 双跑与 ACE 的多轮反思都在睡眠期争抢**同一份未定义的预算**——这正是「睡眠期计算预算未定义」债务会最先爆的地方。
2. **「ΔM/ΔS 拆书」（ACE × PSN × ReasoningBank）**
   - **组合**：ACE 的 playbook **拆两册**——ΔS 子册（程序/工具规则）交给 **PSN** 的带契约可执行网络表示；ΔM 子册（概念/失败模式/经历）用 **ReasoningBank 的双路抽取**（成功→策略、失败→护栏）+ ACE 的条目化与计数器。
   - **接口形态**：一条轨迹同时产出两个 delta（ΔS-delta / ΔM-delta），走**不同的验证门**（ΔS 过契约与回归，ΔM 过一致性与检索可用性）。
   - **组合后新增能力**：正面回应 C3 归属问题，并给「技能固化 0/33」的表示层提供一个**中间形态**（先 ΔS bullet，再升格为 PSN 契约技能）。
   - **新增风险**：双 delta 的一致性问题——同一条经验在两册里可能演化出冲突版本。
3. **「C9 合规自改进信号链」（ACE × Memento）**
   - **组合**：Memento 的**可学习检索 μ** 选条目，ACE 的**执行成败 → helpful/harmful 计数器**回写条目；**全程无评分函数**，只有环境侧事实计数。
   - **接口形态**：`retrieve` 用 μ 排序（不打分、只排序），回写只递增/递减环境事实计数器。
   - **组合后新增能力**：在不引入外部评分的前提下获得「哪条记忆有用」的可学习信号。
   - **新增风险**：计数器本身若被当作排序分使用，就**退化成评分函数**（C9 违规）——必须限定其只作用于**淘汰/剪枝判定**，不作用于在线排序。

### 6.3 本篇在组合中的典型角色
- **记忆巩固写入官 / 防坍缩守门人**：管「库怎么长、怎么不因为整理而丢东西、怎么不无限膨胀」。
- 与 SEDM 的区别要记牢：**SEDM 管「进不进」，ACE 管「进了之后怎么长」**。二者不是替代关系，是同一条入库流水线的**前后两段**。
- 附带角色：**「整体重写」这一做法的反例提供者**（通过 DC 的 18,282→122 token 事故），可写进 SSEA 慢环的工程纪律。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质） |
|---|---|---|
| 项目相关性 | **4** | 正面命中「记忆库长期膨胀与信息损失」「睡眠期计算预算未定义」两条最紧缺口；也回应记忆门选择性缺失（实测于原文 Table 20/21 的阈值不敏感证据、Table 12–15 成本台账） |
| 立场兼容性 | **3** | C3 权重侧 ✓、C10 ✓、C9 ◐（执行反馈信号干净）；但 **C2 载体冲突（全 NL + 三角色 LLM）、C3 记忆/技能混装、C6 无验证门、C8 知识跨代** 四处硬冲突（实测+推断） |
| 可搬运性 | **4** | 最值钱的零件（条目化、确定性 delta 合并、去重剪枝、成本台账）**与 LLM 解耦**，可干净拆出接入；最不可搬的是 Reflector（推断） |
| 证据强度 | **5** | ICLR 2026；2 类场景 × 5 基准 × 4 个 LLM 家族；含**核心消融**（Table 18 delta 更新）、三角色消融（Table 3）、噪声压力测试（Table 17）、超参敏感性（Table 19–21）、分项成本台账（Table 12–15）、并**自陈失效条件**（§5）。本篇是已读卡片中证据最完整者之一（实测） |
| 组合价值 | **4** | 与 SEDM/LightMem/Mem0/ReasoningBank/Memento/PSN/Misevolve 均有明确点名接口，且能同时补「写入侧」与「防坍缩纪律」两个空位（推断） |
| 落地成本 | **3** | 合并/去重/剪枝侧成本低；但需先造**非 LLM 洞察抽取器**替换 Reflector（否则 C2 违规），且三个方案都要先解决「睡眠期预算未定义」才能落地（推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用**条目化 bullet 表示（ID + 环境事实计数器）、非 LLM 的确定性 delta 合并、grow-and-refine（追加/原地更新/去重/阈值剪枝）、「禁止整体重写」纪律、分项成本台账口径、坍缩检测指标**；**不采用** NL playbook 载体、LLM 三角色、GT 标签/LLM-as-a-judge 等评分件、以及「Curator 直接应用」的无门写入路径。
- **优先级：P1**（排在 Gene Manager 与债务 25–28 之后；但「禁止整体重写」这条纪律建议**立即**写入慢环规范，成本为零）。
- **建议动作**：
  1. **立纪律**：慢环任何改写记忆库的路径，**禁止整体重写**，一律走 delta；同时在记忆库上加**坍缩监控**（条目总数、平均条目长度、单日删除量的突降告警）。
  2. **加 schema**：记忆条目升级为 `{id, kind: ΔM|ΔS, content, env_hit_count, env_miss_count, provenance, version}`；拆 ΔM/ΔS 两册（C3 归属落地）。
  3. **造合并器**：实现**非 LLM 的确定性 delta 合并算子**（追加新 ID / 原地更新计数器 / 语义近邻**只链接不覆盖** / 超阈值触发剪枝），作为慢环 Consolidator。
  4. **接门**：delta 过 **SSEA 四级验证门**后才原子升版；把 ACE 的「harmful 过滤」降级为门前**预筛**，不得替代门（补 C6 缺的验证权）。
  5. **建预算台账**：照 Table 12–15 口径，为睡眠期建立「适应期/评估期 × 输入/输出 × rollouts × 延迟」的分项记账，并用 Table 21 的「阈值不敏感」结论先粗设、后可调。
  6. **补前置**：评估「非 LLM 洞察抽取器」可行性——这是本篇能否真正落地的**单点瓶颈**（Reflector 假设）。
- **最小验证实验（增量 delta 合并 vs 整体重写，服务实验 2）**：
  - **双臂 / 消融设置**：同一记忆库、同一轨迹流、≥8 seed。臂 A = 睡眠期**整体重写**记忆库（DC-CU 式）；臂 B = **增量 delta 合并 + grow-and-refine**（ACE 式）；可选臂 C = 臂 B + SEDM 式准入（验证「有门 vs 无门」）。
  - **判据（分档，先看分母）**：
    - 档 1 机制计数：条目总数增长曲线、去重链接命中数、剪枝触发次数、计数器非零条目占比、**坍缩事件数**（条目数/平均长度突降次数）——**先看这些分母是否真的发生了**；
    - 档 2 行为差：记忆检索命中率（基线 **0.5164**）是否提升、睡眠期耗时与调用数（预算台账）；
    - 档 3 淘汰结果：后续任务上的少走弯路率 / 生存时长差（**注意：危险回避率两臂已饱和于 0.9814，不可作判据**）。
  - **预期与证伪条件**：
    - 预期：臂 B 的坍缩事件数 = 0，记忆检索命中率 > 0.5164，且睡眠期增量成本低于全量重写（对应 Table 4 的 −82.3% 延迟量级，但无 LLM 场景预计差距更小）。
    - **证伪**：若臂 B 与臂 A 的检索命中率无差异且坍缩事件数同为 0，说明 SSEA 当前记忆库规模**尚未进入坍缩区**，本篇应**降级为 P2/备查**，待库规模增长后再评估；若臂 B 反而出现条目被错误合并导致技能条目失效，说明 **C3 混装风险已发生**，须先完成拆书（对应债务 25/26/27/28 的形状）。
- 若 **E 不采用**：不适用。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. **C3 归属裁定**：上下文/playbook 在 SSEA 里到底算 ΔM 还是 ΔS？本卡建议**拆两册**，需团队确认这是否是 SSEA 的正式立场。
  2. **Reflector 谁来当**：SSEA 不用 LLM 进控制环，那么「从轨迹蒸馏洞察」这一步由什么执行？（确定性模板抽取？慢环小模型但置于观察员面？还是干脆跳过、只保留合并与去重？）**这是本篇能否落地的单点瓶颈**。
  3. **计数器是否算评分**：helpful/harmful 计数器若用于**在线排序**即触 C9；若只用于**淘汰/剪枝判定**则可接受。需团队给出明确边界。
- **需补查的文献或资料**：
  1. **Dynamic Cheatsheet 原文**（arXiv:2504.07952）——本卡对 DC 的描述全部转引自 ACE 的 §2.2 与 §C.2，未读原文；若 DC 需单独建卡应补。
  2. GEPA（arXiv:2507.19457）——ACE 的主要对手基线，且其「prompt evolution + Pareto 前沿」对 SSEA 的结构搜索另有价值。
  3. §B.1 点名的 AgentFly、AWM、Agentic Plan Caching——均未建卡，其中 AWM 的「workflow 注入」与技能侧相关度可能不低。
- **需人工核对的公式 / 实现**：
  1. **Table 18 与 §C.2 数值不一致**：Table 18 给出「无增量更新 vs 有增量更新」在 test-normal 上为 TGC 67.3 vs **76.2**、SGC 46.4 vs **64.3**（差 8.9 / 17.9）；而 §C.2 正文称「去掉 delta 更新导致 TGC −11.7%、SGC −27.8%」。二者对不上，疑似不同实验配置或笔误。**本卡一律以 Table 18 为准**，需核对。
  2. 原文**未声明 seed 数与方差**（全篇未见多次运行/误差棒的说明），Table 1/2 的差值应视为单次运行结果。
  3. §2.1 末段有约 828 字节在文本提取中被截断（涉及 context adaptation 范式的收尾句），本卡未据此作任何主张。
  4. 论文 arXiv 版本号与日期：PDF 页眉为 `arXiv:2510.04618v3 [cs.LG] 29 Mar 2026`，与文件名前缀 2025-10-06 不一致，本卡按「初版 2025-10、ICLR 2026 收录」处理。

---

## 附：关键摘录与出处

| 摘录（原句 / 要点） | 页码 |
|---|---|
| “modifying inputs with instructions, strategies, or evidence, rather than weight updates” — context adaptation 定义 | 摘要 p1 |
| “brevity bias, which drops domain insights for concise summaries, and from context collapse, where iterative rewriting erodes details over time” | 摘要 p1 |
| “treats contexts as evolving playbooks that accumulate, refine, and organize strategies through a modular process of generation, reflection, and curation” | 摘要 p1 |
| “+10.6% on agents and +8.6% on finance… without labeled supervision and instead by leveraging natural execution feedback” | 摘要 p1 |
| “contexts should function not as concise summaries, but as comprehensive, structured playbooks… Unlike humans… LLMs are more effective when provided with long, detailed contexts” | p2 |
| **Context Collapse 事故**：AppWorld，step 60 上下文 18,282 token / accuracy 66.7 → 下一步骤 **122 token / 57.1**，低于无适应基线 63.7（以 Dynamic Cheatsheet 为例） | Fig.2 p3 |
| “the Generator, which produces reasoning trajectories; the Reflector, which distills concrete insights from successes and errors; and the Curator, which integrates these insights into structured context updates” | §3 p4 |
| 三大创新：dedicated Reflector / incremental delta updates / grow-and-refine | §3 p4 |
| “merged deterministically into the existing context by lightweight, non-LLM logic” —— **可搬零件的原句出处** | §3 p4 |
| bullet = “(1) metadata, including a unique identifier and counters tracking how often it was marked helpful or harmful; and (2) content… a reusable strategy, domain concept, or common failure mode”；概念类似 Dynamic Cheatsheet 与 A-MEM 的 memory entry | §3.1 p5 |
| 三性质：localization / fine-grained retrieval / incremental adaptation | §3.1 p5 |
| grow-and-refine：新 ID 追加、已有条目原地更新（计数器递增）、语义嵌入去重；可主动或**惰性（仅当超出上下文窗口）** | §3.2 p5 |
| 配置：Reflector 最多 5 轮精炼、离线最多 5 epoch、batch size = 1；三角色用同一 LLM（DeepSeek-V3.1 非思考模式）以防知识迁移 | §4.2 p7 |
| Table 1：AppWorld 离线 ACE 59.4（+17.0）/ 无 GT 57.2（+14.8）；在线 ACE 59.5 vs DC 51.9；ReAct 基线 42.4 | p7 |
| AppWorld 榜单（2025-09-20）：ACE 59.4% 持平榜首 IBM CUGA 60.3%；在线在 test-challenge 上 TGC +8.4、SGC +0.7 超过 | p8 |
| Table 2：金融离线 ACE 81.9（+12.8）；**在线无 GT 时 FiNER 67.3 低于 base 70.7（−3.4）** | p8 |
| “when ground-truth supervision or reliable execution signals are absent, both ACE and DC may degrade… the constructed context can be polluted by spurious or misleading signals” | p8–9 |
| Table 3 消融：去 Reflector+多 epoch → 55.1；去多 epoch → 56.8；全量 → 59.4；在线无 warmup → 56.1，有 warmup → 59.5 | p9 |
| Table 4：离线 vs GEPA 延迟 −82.3%、rollouts −75.1%；在线 FiNER vs DC 延迟 −91.5%、token 成本 −83.6% | p10 |
| KV cache：GPT-5.1 + OpenAI prompt caching，**91.8% 输入 token 命中缓存**，billed 输入成本 **−82.6%** | p10 / §A.3 p18–19 |
| Table 12：适应期输入 token 204.1M→39.3M（−80.8%）、输出 1.87M→0.31M（−83.6%）、rollouts +42.6%；Table 14：评估期输入 **+117.4%**、输出 +7.6% | p18–19 |
| **§5 局限**：依赖足够强的 Reflector；反馈不可靠时退化；“not all applications require rich or detailed contexts”（HotPotQA 适合简洁指令、Game of 24 只需一条规则） | p10 |
| Table 16：弱反思者 GPT-OSS-120B 76.6 / DeepSeek-V3.1 78.3 / GPT-5.1 78.5，base 70.7 | p19 |
| Table 17：有害反思每 1 步注入 → **66.7（低于 base 70.7）**；每 5 步 76.1；每 10 步 77.0；每 25 步 77.8；每 50/100 步 78.2 | p19–20 |
| “ACE’s bullet-point analyzer (grow-and-refine), which merges and deduplicates semantically similar bullets and can filter entries flagged as potentially harmful via metadata, serves as a first line of defense” | §A.4 p20 |
| **Table 18（核心消融）**：无增量更新 67.3/46.4/56.9 vs 有增量更新 76.2/64.3/70.3（test-normal TGC/SGC/平均） | p20 |
| Table 19–21：反思轮次 1/3/5/10 → 61.3/65.8/**67.6**/65.2；去重阈值 50%/70%/90% → 77.0/73.9/78.6；最大长度 10K/50K/100K → 78.6/78.4/78.3 | p21 |
| §C.1 vs GEPA：“ACE instead represents context as a structured, itemized Playbook and applies incremental delta updates… merged… with simple deterministic logic” | p22 |
| §C.2 vs DC：DC “rewriting the cheatsheet as a whole… can cause context collapse”；ACE “avoids full rewrites by using incremental delta updates” | p22–23 |
| §B.1 相关记忆工作点名：AgentFly、AWM（Agent Workflow Memory）、A-MEM、Agentic Plan Caching | p22 |
| 代码开源：github.com/ace-agent/ace | Reproducibility p11 |
