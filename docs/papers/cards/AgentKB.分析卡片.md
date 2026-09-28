# 论文分析卡片 · Agent KB

> 纪律：任何结论若无法回溯到 C1–C10 裁判标准，即视为偏离 SSEA 立场，不予采纳。
> 论文未提及的内容一律标「未提及」，不得替论文主张。

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-07-08 Agent KB Leveraging Cross-Domain Experience for Agentic Problem Solving.pdf` |
| 标题 | **Agent KB: Leveraging Cross-Domain Experience for Agentic Problem Solving（AGENTKB）** |
| 作者 / 机构 | Xiangru Tang\*、Tianrui Qin\*、Tianhao Peng\*、Ziyang Zhou、Daniel Shao、Tingting Du、Xinming Wei、Peng Xia、Fang Wu、He Zhu、Ge Zhang、Jiaheng Liu、Xingyao Wang、Sirui Hong、Chenglin Wu、Hao Cheng、Chi Wang、Wangchunshu Zhou；Yale University、OPPO、UW-Madison、UNC Chapel Hill、Stanford University、ByteDance、Nanjing University、All Hands AI、DeepWisdom、Microsoft Research、Google DeepMind |
| 发表时间 / 出处 | arXiv:2507.06229；文件名前缀 2025-07-08（v1），PDF 版头为 **v5 [cs.CL] 27 Oct 2025**（32 页） |
| 论文链接 | arXiv:2507.06229 |
| 代码链接 | `github.com/OPPO-PersonalAI/Agent-KB`（摘要）；复现包 `https://anonymous.4open.science/r/Agent-KB/`（p11 Reproducibility） |
| 标签 | 跨框架共享记忆 · 跨域经验迁移 · 经验抽象 schema · 混合检索(BM25+语义) · disagreement gate · 两阶段 Reason-Retrieve-Refine · 集体智能 |
| **应用裁决** | **B 零件采用**（取「混合双通道检索 + disagreement gate + 经验 schema + 跨域不对称」四件；**不采用**其语言载体、LLM ranker/效用评分、外部 critic） |
| 优先级 | **P1**（直击 `retrieve` 键收窄与记忆门选择性两条活债；并提供 C8 的实证依据） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把 smolagents / OpenHands / OWL / SWE-Agent 等**异构框架**的轨迹，经 few-shot 抽象为统一 schema 的经验单元 `E=⟨π,γ,S,C⟩`，聚合成一个**跨框架、免重训、即插即用**的共享知识库，暴露轻量 REST API；推理时用两阶段 **Reason-Retrieve-Refine**（planning 阶段播种跨域 workflow、feedback 阶段注入针对性诊断修复），并以 **disagreement gate** 只放行与原始计划一致的修订，从而把「个体经验」变成「集体智能」——GAIA 上 smolagents+GPT-4.1 从 55.2% 升到 73.9%（pass@3），SWE-bench Lite 上 OpenHands+Claude-3.7 从 30.0% 升到 51.0%（p1、p6–7、Fig.1–2）。
- **对 SSEA 的意义**：它是**记忆检索侧**目前最直接的一篇——`E=⟨π,γ,S,C⟩` 给出 ΔM 的可移植 schema，**混合双通道检索（词法+语义）**直接补 SSEA `retrieve` 键收窄导致的召回精度上限，**disagreement gate** 是「只判合法性、不打分」的现成近似；更关键的是 **Fig.6 的跨域不对称**（reasoning 经验迁移到 SWE 后仍 37.0%，SWE 经验迁到 GAIA 只剩 56.4%）为 SSEA **C8「基因只给结构性先验」**提供了实证：**可迁移的是抽象后的 workflow/策略，不是具体经历**。代价是它整个载体是自然语言、且用效用评分与 LLM ranker 驱动库治理（C2/C9 冲突）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–2）：各智能体框架「operate in isolation」，重复解同一问题、重复犯同一错误；有价值的解题经验被困在单个系统内，无法涌现集体智能。现有记忆系统只强化**单个**智能体、或只合成**框架专用**的示范（Learn-by-Interact、A-Mem 仍限于单框架），无法跨架构迁移。
- **它指出的既有方案缺陷 / 三大挑战**（p1）：
  1. **Representation heterogeneity**：不同框架对经验的编码/抽象互不兼容，无法直接迁移复用；
  2. **Context mismatch**：某工具生态里有效的解，换一套 API/推理协议/执行环境后可能失效或不完整；
  3. **Knowledge interference**：朴素注入外部经验会扰乱智能体自身推理流，产生不连贯计划或错误叠加。

### 2.2 核心思想（关键 insight）
1. **经验应被抽象成统一 schema 的结构化单元再共享**：把异构轨迹蒸馏为 `E=⟨π,γ,S,C⟩`（任务嵌入 / 结构化目标谓词 / 动作-推理对 / 跨框架元数据），用 few-shot（每域 10–15 条人工范例）与跨框架**标准化动作词表**完成抽象（p4）。
2. **检索要双通道、注入要两阶段**：planning 阶段用任务描述做 Reason→Retrieve→Refine 生成可执行计划；feedback 阶段改用**执行轨迹**做同一循环产出修复——两阶段查询口径不同，互补（p5）。
3. **知识干扰须用一致性门而非质量分来防**：**disagreement gate** 只放行与原始计划语义一致（cos ≥ β）的修订，保证稳定性与安全（p1、p5）。
4. **抽象是收益的瓶颈，不是数据量**：库越大收益越稳，但高阶推理任务随规模**持平**——「quality of abstraction is bottlenecked, not the quantity」（p8–9）。
5. **自动抽取的经验可匹敌人工标注**：自动经验在 GAIA 上与 5 名 CS 研究生手工标注持平（75.15 vs 76.97），在 Level 3 反超（57.69 vs 53.85）（Table 4 p8）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）

| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **经验 schema `E=⟨π,γ,S,C⟩`** | 轨迹日志 → 结构化经验单元 | π=任务嵌入(all-MiniLM-L6-v2)、γ=结构化目标谓词、S={(aᵢ,rᵢ)} 动作-推理对、C=跨框架兼容元数据 | Eq.1 p4 |
| **human-guided 抽象** | 原始日志 → 经验 | few-shot（每域 10–15 人工范例）+ 标准化动作词表 | p4；App. F.1 |
| **Self-Evolving Memory** | 新增/去重/淘汰 | 库随多框架贡献增长（addition） | §3.2 p4 |
| **去重（τ=0.8 + LLM ranker）** | 高相似候选 → 保留更优条目 | `max cos(π,π′)>τ` 时由 **LLM ranker** 比 reasoning quality/completeness/transferability | §3.2 p4 |
| **效用淘汰** | `uⱼ ← uⱼ + η(rⱼ − uⱼ)` | 学习效用分（recency/frequency/transferability 权衡），低效用淘汰 | §3.2 p4 |
| **混合检索** | query → top-k 候选 | BM25 词法粗筛（域/工具兼容）+ 语义精排（all-MiniLM-L6-v2）；`σ_hyb=α·σ̃_text+(1−α)·σ̃_sem`，默认 α=0.5，top-k=3 | §3.3 p4 |
| **Reason 步（查询构造）** | 任务/轨迹 → 结构化多面查询 | 检索前的 query 展开：拆成可检索子查询 | §3.3 p5；App. F.2 |
| **Refine 步（跨框架适配）** | 候选经验 + C → 可执行计划 ρ | **entity mapping / tool substitution / step reordering**，把抽象动作对齐到当前可用工具 API | §3.3 p5 |
| **disagreement gate** | 原计划 ρ、修订 ρ′ → 放行/拒绝 | `G(ρ,ρ′)=1[cos(φ(ρ),φ(ρ′))≥β]`，β=0.8；仅放行一致修订 | §3.3 p5 |
| **两阶段 Reason-Retrieve-Refine** | 任务描述（planning）/执行轨迹（feedback）→ 计划/修复 | 推理被拦截在 planning 与 feedback 两个阶段，**基础 agent 不变** | §3.3 p5、Fig.2c |
| **REST 端点 + 标准化动作词表** | 提交/检索经验 | 免架构改动、免重训的跨框架接入 | §3.1 p3 |
| **80 条人工种子轨迹** | 5 名研究生手写（60 BrowseComp/HopRAG + 20 SWE-Gym） | **仅用于引导自动抽象，永不直接检索** | p5、App. B |

### 2.4 关键表示与数据结构
- **经验单元**：`E=⟨π,γ,S,C⟩`（Eq.1 p4）。π 用 `all-MiniLM-L6-v2` 嵌入；γ 为结构化目标谓词；S 为 `{(aᵢ,rᵢ)}` 动作-推理对；C 为跨框架元数据（工具/域兼容）。
- **JSON 落地形态**（App. E.2.3 p25、F.1）：`{question, true_answer, agent_plan, search_agent_plan, agent_experience[], search_agent_experience[]}`——planning 与 experience 均为**自然语言文本**（多智能体角色分别存 planning/experience）。
- **知识库规模**（App. A Table 5 p18）：BrowseComp 1,266 / MultiHopRAG 2,556 / HLE(text) ≈2,000 / WebWalkerQA 680 / RepoClassBench 1,000 / SWE-Gym-Raw 1,000 / RepoEval 1,000；合计 ≈7,802 任务 → **≈9,502 条经验**；正文口径「约 9k workflow summaries + 7k execution snippets」（p5）。
- **超参默认**：τ=0.8（去重）、α=0.5（混合权重）、β=0.8（gate）、top-k=3、temperature=1.0、base model=GPT-4.1（p5、p8）。
- **构建管线**：raw log → structured experience（App. E.2.2 p24 有完整样例）；对成功与失败运行**都**归一化为经验单元（p5）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| **GAIA**（165 题：L1 53 / L2 86 / L3 26） | 无记忆 baseline | smolagents+GPT-4.1：55.2%→**73.9%**（pass@3，+18.7，L2 +19.8）；Claude-3.7：58.8%→**75.2%**（L3 +19.2）；OWL+GPT-4o：43.6%→**63.6%**（+20.0） | Table 1 p6；单次运行，**未报 seed 与方差** |
| GAIA（对标 A-MEM） | A-Mem | A-Mem 把 GPT-4o smolagents 抬到 69.1%；AGENTKB 在同 planner 下达 73.9%（混合检索更优） | p6–7 |
| **SWE-bench Lite**（300 实例） | 无记忆 baseline | SWE-Agent+GPT-4.1：24.3%→**38.0%**（50 iter）/ **42.3%**（100 iter）；OpenHands+GPT-4.1：24.3%→28.3%（pass@1）；OpenHands+Claude-3.7：30.0%→**51.0%**（50 iter，+21.0） | Table 2a p6；50/100 iter |
| **HLE Bio/Chem**（149 实例） | OpenHands / Biomni | OpenHands 9.5%→**14.1%**（pass@3）；pass@2 12.1% 已超 Biomni 10.7% | Table 2c p6 |
| **GPQA**（198 实例） | OpenHands / Direct | OpenHands+GPT-4.1：62.6%→**72.7%**（pass@3，+10.1） | Table 2d p6 |
| **消融：模块**（GAIA，smolagents GPT-4.1） | 完整 AGENTKB 61.21 | **w/o Refine 最大跌幅 −6.06**（→55.15）；w/o Retrieve −3.63；w/o Reason −1.21；**w/ Raw Workflow 58.18** | Table 3 p7 |
| **消融：disagreement gate** | no-gate | gate 在 **β≈0.8** 最优 | Fig.5a p7–8 |
| **消融：检索策略** | text / semantic / hybrid | **hybrid 一致最优**；top-k 在 **k=3** 达峰（GAIA L1 83.0%） | Fig.5b p8 |
| **消融：库规模** | 100 / 500 / full | 100 条仍有增益；500 条稳步升；**高阶推理随规模持平**（抽象质量是瓶颈） | Fig.5c p8 |
| **自动 vs 人工经验** | HANDCRAFTED(5 名 CS 生) | GAIA 75.15 vs 76.97（持平）；**L3 57.69 vs 53.85（反超）**；SWE-bench 24.33→**51.00** | Table 4 p8 |
| **跨域迁移不对称** | reasoning KB / SWE KB | reasoning 经验：GAIA **73.9%**、迁到 SWE-bench 仍 **37.0%**；SWE 经验：SWE-bench **42.3%**、迁到 GAIA 只剩 **56.4%**（**SWE 知识不泛化到推理**） | Fig.6 p9 |
| **误差分析**（GAIA） | baseline vs +AGENTKB | GPT-4.1：共享错 49、baseline 独有 25、新增 15 → **净减 10**；Claude-3.7：共享 46、纠正 22、新增 11 → **净减 11**；六类：retrieval/planning/reasoning/format/perception/execution | Fig.7 p9–10 |
| **延迟与内存** | A-Mem / MemoryBank / ReadAgent | 查找延迟与内存占用**相当**（跨库规模） | Fig.4 p9 |
| **成本**（App. D） | — | GAIA：检索回路仅 **+$0.27**（占 $86.0 的 <0.4%）；SWE-bench：**<$0.004/issue**；一次性构建 **$10.88**（5.14M prompt + 0.77M completion tokens） | Table 6–7 p20 |

### 2.6 论文自陈局限与边界条件
- **无独立 Limitations 节**（论文未单列）：限制散见于 Conclusion 与附录——未来工作指向「richer modalities and longer-horizon reasoning」（p10）。
- **自陈的瓶颈**（p8–9）：抽象质量而非数据量是高阶推理的瓶颈；更大库能稳步提升，但复杂任务需要「better structuring and retrieval」。
- **明确的不适用情形**（p9）：**SWE 经验不迁移到 reasoning**（Fig.6），说明域专用知识有明确边界。
- **伦理/部署边界**（p11）：记忆系统实际部署须考虑 data privacy、retrieved knowledge 的 bias、高风险域误用。
- **测试集口径**（p5 脚注 2）：HLE 的 bio/chem 子集被**特意从 HLE 中移除**作为独立测试集（149 题）。
- **假设依赖**：全程挂在前沿 LLM（GPT-4o/4.1、Claude-3.7、Qwen-3、DeepSeek-R1、o3-mini）之上；经验抽取、去重排序、Reason/Refine 均由 LLM 承担（App. G.1 p31）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 面向 QA/编码助手的语言智能体记忆层；无生存信号、无淘汰-繁衍闭环，反馈靠语言 critic（p5、p9） | 只搬记忆检索与抽象件，**不搬**其「agent 组织方式」；SSEA 控制环不接语言 |
| **C2** 自然语言只作观察员接口 | **✗（强冲突）** | 经验表示 `agent_plan`/`agent_experience` 全是英文文本（p24–25、App. F）；检索用文本嵌入（all-MiniLM-L6-v2）；注入是 prompt 拼接 | **必须换载体**：`E=⟨π,γ,S,C⟩` 的 γ/S/C 骨架可保留为结构化字段，语言 payload 改由非语言结构张量承载；语言只在慢环编译面 |
| **C3** 权重/记忆/技能三分离 | **◐** | 明确不重训、不动权重，纯**记忆侧**（=ΔM）；但**未区分**技能与记忆——workflow 经验既像记忆又像技能（p3–4） | 只作 ΔM 供应商；workflow 类经验须走 PSN 技能契约归 ΔS，避免与记忆混置 |
| **C4** 低算力低带宽 | **◐** | 检索开销极小（+$0.27/<0.4%；SWE <$0.004/issue，Table 6–7 p20），内存占用与 A-Mem 相当（Fig.4）；但**依赖前沿 LLM**，且基础 action loop 占 205k prompt tokens/task | 检索件可低成本移植；LLM 抽取/排序环节须换小模型或离线批处理；库增长须配淘汰（已有 u 淘汰，见 C9 改造） |
| **C5** 精准回忆历史 | **◐/✗（张力点）** | 有精确管理的一面（App. E.2.2 p24「Precision Management」学格式/精度要求）；但抽象**故意丢弃具体答案**（生成提示明令「without directly revealing the specific answer」p26）、去重 τ=0.8 合并相似条目、低效用条目被淘汰 → **有损** | **分库**：C5 要求精准 episodic store 与 C8 抽象层**物理分离**（SSEA 三分离已具备）；抽象层须保留**回指指针**（cf. EvolveR `Merge` 回指）到源经历，防「抽象取代精确」 |
| **C6** 可自主修改自身 | **◐** | 可自主修改**自身记忆**（add/dedup/evict，§3.2 p4），不改代码/权重；属 ΔM 自修改 | 映射为慢环 ΔM 提案；代码/权重自修改仍由 SSEA 四权框架管 |
| **C7** 可保存/恢复/变异/继承 | **◐** | KB 持久化并经 RPC **跨框架即时共享**（p5）——近似「跨个体继承」；但**同一 KB 实例共享**，无变异、无选择、无繁衍闭环 | 只取「共享通道」思想；GenePackage 的变异/选择/淘汰仍须自建（见 GEA 卡片方案） |
| **C8** 给基因先验，不给知识语料 | **◐（方向支持，非充分证明）** | **Fig.6**：抽象 workflow 经验部分跨域迁移（reasoning→SWE 37.0%），域专用经验不迁移（SWE→GAIA 跌到 56.4%）；**人工种子「永不直接检索」**，只塑造抽象函数（p5）——恰似「先验塑造结构、非注入语料」 | **判定**：SSEA 可继承/迁移的应是**结构性先验/技能（抽象 workflow/策略）**，**不是**具体经历。但本篇**未做**「结构性 vs 情节性」的内容消融，且其共享本身跨越了「个体边界」——**不足以单独证明 C8 的跨代条款**，只能作方向性支持 |
| **C9** 不设评分函数，只有淘汰函数 | **◐/✗（混合）** | **合规面**：评测**只用 ground-truth 任务完成度**（GAIA exact match / SWE test pass），明言「rather than LLM-generated evaluation scores」（App. G.2 p32）✓；disagreement gate 只判**一致性合法性**（cos≥β），非打分 ✓。**违规面**：去重用 **LLM ranker** 比质量/完整性/迁移性（排序，✗）；效用 `uⱼ←uⱼ+η(rⱼ−uⱼ)` 用 reward 驱动淘汰（评分，✗）；feedback 阶段用 **critic highlights**（外部评判，✗） | **降级**：u 只作**环境侧经验事实记录**（如 EvolveR 的 c_succ/c_use 计数），不参与任何选择排序；LLM ranker 换成**合法性/一致性门**或确定性去重；critic 换成**沿轨迹的成败事实**（cf. PSN REFLECT）；**保留** disagreement gate 与 ground-truth 评测 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子（BM25 + MiniLM + 现成 LLM）；创新在信息流（两阶段回路、混合检索、gate, L2）、库自演化（L3）、跨框架共享记忆（L4） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无新算子；BM25、all-MiniLM-L6-v2、现成 LLM 均为借用件 | 符合借用立场 |
| **L2 信息流层** | **两阶段 Reason-Retrieve-Refine**、混合双通道检索（α 融合）、disagreement gate、元数据 C 驱动的跨框架适配 | **高**：直接给「检索→适配→注入」的信息流骨架 |
| **L3 学习层** | 经验抽象（轨迹→schema）、库自演化（add/dedup/evict）、feedback 阶段的失败诊断回路 | **中高**：给慢环「回顾编译」的回路形状；评分件须降级 |
| **L4 演化层** | 跨框架**共享记忆**（免重训、RPC 即时可见）——近似跨个体继承 | **中**：提供「共享通道」参照，但无变异/选择/淘汰闭环 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| 经验 schema `E=⟨π,γ,S,C⟩` | ΔM 记忆条目 schema；γ 结构化谓词 → **Gate 合法性键**；C → 跨环境兼容元数据 |
| 混合检索（BM25 + 语义，α=0.5） | **`retrieve` 键收窄的直接修复**：单键 → 双通道融合 |
| Reason 步（结构化多面查询） | 检索前 **query expansion**，抬高召回精度上限 |
| Refine 步（entity mapping / tool substitution / step reordering） | 慢环 `ExperienceCompiler` 的「经验→可执行计划」适配器 |
| disagreement gate `G(ρ,ρ′)≥β` | 四级验证门的**一致性/合法性门**；与 SEDM A/B 准入互补（一个防干扰、一个验效用） |
| 去重 τ=0.8 + 效用淘汰（u 降级） | ΔM 的 merge / forget；**去掉 LLM ranker 与 reward 评分**，改事实计数 |
| 两阶段 Reason-Retrieve-Refine | 慢环「回顾编译」回路的**形状来源**（planning 播种 + feedback 修复） |
| feedback 阶段（轨迹派生查询 + 失败诊断） | 慢环故障定位（≈ PSN REFLECT 的语言版对照，SSEA 取非语言版） |
| 80 条人工种子（永不直接检索） | 抽象函数的 few-shot 先验范例；**不作为可检索语料**（合 C8 精神） |
| 成本台账（Table 6–7） | **睡眠期计算预算**标定的成本参照（token/$ 分模块口径） |

### 3.4 债务与验收实验对应
- **`retrieve` 键收窄 → 召回精度上限低**：**直接回应**。混合双通道（BM25 词法 + 语义融合，α=0.5）+ Reason 步 query 展开 + k=3，为「单键收窄」提供现成的加宽方案。
- **记忆门「开得准不准」的选择性缺失**：disagreement gate（β 阈值）给出「只在一致时放行」的合法性判据模板；但须防其退化为相似度打分。
- **记忆检索命中率 0.5164**：hybrid 检索 + 多面查询有望抬升；须以双通道消融验证（见 §8）。
- **睡眠期计算预算未定义**：App. D 的分模块 token/$ 台账（Table 6–7 p20）给出**预算标定口径**。
- **技能表示够不够（0/33 后仍未答）**：本篇**不回应**——其经验停在 workflow/自然语言层，无技能契约；该债仍由 **PSN** 主答。
- **Gene Manager 缺失**：本篇是 ΔM 而非 GenePackage，**不直接回应**；但其「共享通道」与 **GEA** 互补。
- 服务**记忆检索侧实验**（命中率 + 记忆门选择性）的重设计。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | 经验 schema `E=⟨π,γ,S,C⟩`（含 γ 结构化谓词、C 元数据） | 表示 | 改造移植 | ΔM 条目 / Gate 键 | 经验可检查、可跨环境适配 | 高 |
| 2 | 混合双通道检索（BM25 + 语义 α 融合，k=3） | 算法 | 改造移植 | `retrieve` | 键收窄导致的召回上限 | 高 |
| 3 | Reason 步结构化多面查询（检索前展开） | 方法/提示设计 | 改造移植 | `retrieve` 前置 | 召回精度 | 中高 |
| 4 | disagreement gate `G(ρ,ρ′)=1[cos≥β]` | 协议 | 改造移植 | 验证门 / 共享准入 | 只判合法性、防知识干扰 | 高 |
| 5 | Refine 步跨框架适配（entity mapping / tool substitution / step reordering） | 算法 | 改造移植 | ExperienceCompiler | 抽象经验接地到当前环境 | 中 |
| 6 | 库治理：去重 τ=0.8 + 效用淘汰（**评分降级为事实计数**） | 工程 | 改造移植 | ΔM merge/forget | 库不无界增长、防冗余 | 中 |
| 7 | 两阶段 Reason-Retrieve-Refine 回路 | 思想 | 仅借思想 | 慢环回顾编译 | 慢环回路形状 | 中高 |
| 8 | **Fig.6 跨域迁移不对称**（抽象可迁、域专用不可迁） | 思想/证据 | 仅借思想 | C8 裁决依据 | 判定「可继承=结构/技能」 | 高 |
| 9 | 成本台账口径（Table 6–7） | 工程 | 直接引用 | 睡眠期预算 | 预算未定义 | 中 |
| 10 | GAIA / SWE-bench 评测口径（只用 ground-truth，不用 LLM 打分） | 基准/协议 | 直接引用 | 验收实验判据 | C9 合规的判据形状 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 的 ✗/◐）：
  - **C2 ✗（最硬）**：经验、检索、注入全走自然语言；SSEA 若直接搬，控制环会被语言污染。**改造方向**：只留结构化骨架（γ/S/C），语言 payload 换成非语言结构张量。
  - **C9 ✗（部分）**：LLM ranker 排序 + 效用 reward 评分 + critic 评判三重违规。**改造方向**：ranker→确定性去重/合法性门；u→环境侧事实计数；critic→轨迹成败事实。
  - **C1 ✗**：无生存语义。**改造方向**：仅作 ΔM 供应商，不改 SSEA 控制环组织。
  - **C5 ◐**：抽象**故意丢弃具体答案**（p26），与 C5「精准回忆」直接张力。**改造方向**：抽象层与 episodic store 分库 + 回指指针。
- **隐含假设与失效条件**：
  - 假设经验抽取/去重/Reason/Refine 的质量由**前沿 LLM** 保证（App. G.1 p31）——小模型下收益打折（cf. PSN 弱模型噪声证据）。
  - 假设「跨框架 = 跨个体」：KB 是**单一共享实例**，无谱系隔离、无变异选择；SSEA 的 C7/C8 命题（跨**代**）在此**未被检验**。
  - 假设抽象质量是瓶颈（p8–9）——若 SSEA 只能用小模型做抽象，可能先在此处失效。
- **算力 / 带宽 / 工程代价**：检索侧便宜（<0.4% 成本），但**一次性构建 $10.88 + 5.9M tokens**，且基础 action loop 才是大头（205k prompt tokens/task）；库 ≈9.5k 条目，需配淘汰防膨胀。REST + 标准化动作词表是额外工程面。
- **搬运后的可能退化模式**：
  - 把 disagreement gate 当**质量门**用 → 退化为相似度打分（违 C9），且高相似会**锁死**真正的改进（β=0.8 偏高）。
  - 抽象层直接顶替 C5 精确记忆 → 具体经历丢失，复现能力下降（「抽象取代精确」风险兑现）。
  - 双通道检索在**非语言键**上失效：BM25 无文本可索引，需重新设计词法通道的等价物。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可检索的经验库 + 失败轨迹 + ground-truth 评测 | SSEA 已有记忆库与验收框架雏形 |
| 直接同族 | **Memento（A/P1）** | 同为「冻结 LLM + 案例库读写 + 可学习检索」；Memento 给记忆侧主干，Agent KB 给**跨框架/跨域共享**与**双通道检索**——Agent KB 是 Memento 的「多机共享」外延 |
| 互补（最紧·检索侧） | **FLEX（B/P1）** | FLEX 管**写入组织**（golden/warning 分层 + updater 三分支）；Agent KB 管**检索融合**（BM25+语义 + gate）。写入 × 检索 = 完整记忆管道 |
| 互补（最紧·准入侧） | **SEDM（B/P1）** | Agent KB 的 disagreement gate 防**干扰**，SEDM 的 A/B 准入验**效用**；两者合成「经验条目的双层准入」（GEA 卡片已点名此边） |
| 互补（技能侧） | **PSN（A/P1）** | Agent KB 停在 workflow/自然语言；PSN 给技能契约 + REFLECT + 成熟度门控 + 回滚。**workflow 经验成熟 → 经 PSN 结晶为带契约技能** |
| 互补（失败利用） | **ReasoningBank（B/P1）** | 二者都蒸馏成功+失败轨迹；ReasoningBank 给「少而精、k=1」的注入预算与双路抽取，Agent KB 给跨域共享与混合检索；可拼「跨域共享的推理记忆」 |
| 互补（跨域证据） | **CoPS（arXiv:2410.16670，本库未建卡）** | CoPS（Cross-Task Experience Sharing）用**分布匹配**选择跨任务经验并有理论保证；与 Agent KB 的 Fig.6 不对称互为佐证：**跨域迁移有可证边界** |
| 互补（抽象层级） | **From Experience to Strategy（arXiv:2511.07800，本库未建卡）** | 把轨迹抽象为**状态机决策路径 → 高层 strategic meta-cognition**；比 Agent KB 的 workflow 抽象更高一层，可作 Agent KB 抽象层的上游 |
| 替代 | 单键检索 / 平铺示范库（Synapse 一类） | 混合双通道 + 跨框架 schema 替代单键 RAG |
| 对照（共享一族） | **Group-Evolving Agents / GEA（B/P1）** | GEA 是**演化期结构共享**（跨个体 patch），Agent KB 是**推理期记忆共享**（跨框架 prompt）；**SSEA 只取 GEA 侧**（结构期合法），Agent KB 侧须改造为结构期 |
| 对照（共享一族） | **G-Memory（arXiv:2506.07398，本库未建卡）** | 三层图（insight/query/interaction）做多智能体记忆共享，**层级相反**：G-Memory 走图遍历高层洞见，Agent KB 走扁平 schema + 混合检索；同为推理期共享 |
| 对照（经验可迁移阵营） | **Xolver（arXiv:2506.14234，本库未建卡）** | 训练-free，给黑盒 LLM 配持久演化的整体经验记忆（外部/自检索、工具、协作、自评、迭代精化）；与 Agent KB 同属「经验可迁移」但 Agent KB 强调**跨框架** |
| 风险 | **Misevolve（A/P1）** | 跨框架共享是**新污染面**（一次注入影响全体）；须用四路径威胁模型与红队清单验收 |
| 风险 | **RAGEN（B/P1）** | 若未来以训练组件替代 LLM 抽取/排序，用 Echo Trap 诊断防坍缩 |

### 6.2 推荐组合方案
**方案 A（推荐，服务 `retrieve` 债）：双通道检索 + 一致性门 = 记忆检索升级**
- **组合**：Agent KB（混合检索 + Reason 查询展开 + disagreement gate）× **FLEX**（分层写入）× **Memento**（可学习检索 μ）
- **接口形态**：SSEA `retrieve` 从单键改为 **BM25-等价词法通道 + 语义通道 α 融合**；检索前加 Reason 式 query 展开；命中后过 disagreement gate（一致性）再注入；写入侧仍由 FLEX 分层。
- **组合后新增能力**：召回精度上限抬升 + 注入不再扰乱推理流（防 knowledge interference）。
- **新增风险**：非语言键上词法通道需重新设计；gate 阈值 β 在结构表示上需重标定。

**方案 B：workflow 经验 → 技能结晶（Agent KB × PSN × SEDM）**
- **组合**：Agent KB 的跨域 workflow 经验（抽象层）→ **PSN** CODEGEN 蒸馏为带契约技能 → **SEDM** A/B 准入验证
- **接口形态**：Agent KB 抽象层的 workflow 作为 PSN 的输入语料；成熟后固化为 ΔS；准入由 SEDM 把关。
- **组合后新增能力**：把「可迁移的抽象 workflow」正式升格为**可继承的结构性技能**（合 C8 判定）。
- **新增风险**：抽象 workflow 与技能契约的粒度对齐未验证。

**方案 C（C8 裁决实验）：结构共享 vs 情节共享（Agent KB × GEA）**
- 见 §8 最小验证实验。

### 6.3 本篇在组合中的典型角色
- **记忆检索侧的「双通道检索器 + 一致性门供应商」**：它不提供技能、不提供基因、不提供生存信号；它提供的是「**跨域/跨框架的经验该怎么被抽象成统一 schema、怎么被双通道召回、怎么在注入前用一致性门自保**」。抽象层上游接 From Experience to Strategy，下游结晶接 PSN，写入组织接 FLEX，准入接 SEDM。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 直击 `retrieve` 键收窄与记忆门选择性两条活债，并给 C8 跨域迁移实证（实测：Fig.5–6、Table 3）；扣 1：无生存语义、无技能/基因（实测） |
| 立场兼容性 | **2** | **C2 ✗ + C1 ✗ + C9 ✗（部分）** 三条硬冲突，且 C5 有张力（实测：p24–26、App. G.2）；但核心检索/门件改造路径明确，改造后可升至 4（推断） |
| 可搬运性 | **4** | 检索、gate、schema 均为架构级、与具体框架解耦（REST + 标准化动作词表）；语言载体是唯一需重写的面（实测/推断） |
| 证据强度 | **3** | 4 大基准、跨 6+ 模型家族、系统消融、误差分析、成本台账（实测）——广度强；但**单次运行、无 seed/方差、pass@k 非独立重复、无「结构 vs 情节」内容消融**（实测） |
| 组合价值 | **4** | 与 Memento / FLEX / SEDM / PSN / ReasoningBank / GEA / CoPS 多条边成立，且补上 GEA 卡片遗留的「Agent KB 未建卡」缺口（推断，有实测支撑） |
| 落地成本 | **4** | 反向口径：检索件近乎零成本（+0.27 美元/<0.4%）、内存与 A-Mem 相当（实测）；扣分在一次性构建 $10.88 与语言载体重写（实测/推断） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：记忆检索侧的**双通道检索 + 一致性门 + 经验 schema + 跨域不对称证据**四件干净可用，直接服务 `retrieve` 债与 C8 裁决；但**不采用**其语言载体（C2）、LLM ranker/效用评分/critic（C9）、以及其「跨框架共享即继承」的整体主张（C1/C7 无对应实体）。**不采用**整机（无生存、无基因）。
- **优先级：P1** —— 理由：`retrieve` 键收窄是当前活债（召回精度上限低），本篇是现有文献里对该债给得最直接的方案；且其 Fig.6 是 C8 裁决的实证拼图（与 GEA 并列）。
- **建议动作**：
  1. **`retrieve` 升级原型**：单键 → 双通道（词法等价物 + 语义通道）α 融合，检索前加 Reason 式多面查询；记录候选数（分母优先）。
  2. **实现 disagreement gate**（只判一致性合法性，不排序），接入四级验证门；β 在非语言表示上重标定。
  3. **ΔM schema 落地**：采用 `E=⟨π,γ,S,C⟩` 的结构骨架（γ→Gate 键、C→兼容元数据），语言 payload 换结构张量。
  4. **C9 降级**：去掉 LLM ranker 与 u 评分，改确定性去重 + 环境侧事实计数；critic 换轨迹成败事实。
  5. **写死 C8 分界线**：明确「可继承=抽象 workflow/技能（结构），不可继承=具体经历（episode）」，文献依据 = 本篇 Fig.6 + GEA Table 3。
  6. **抽象层与 C5 分库**：抽象层保留回指指针到 episodic store，防「抽象取代精确」。
- **最小验证实验（记忆检索侧，服务 `retrieve` 债 + 记忆门选择性）**：
  - **双臂 / 消融设置**（同一环境、同一记忆库、≥8 seed）：
    - **A 臂 单键检索**（现状）：单一 retrieve 键。
    - **B 臂 双通道 + 一致性门**：词法等价通道 + 语义通道 α 融合 + Reason 式 query 展开 + disagreement gate。
    - **C 臂（证伪对照）双通道但去掉 gate**：验证 gate 是否真防干扰。
  - **判据（分档，先看分母）**：
    1. **机制计数（分母）**：检索候选数 / gate 放行-拒绝数 / 记忆门「开」决策数 / 拒绝率。**若 B 臂 gate 拒绝率 >90%，说明 β 标定失效，后两档无意义。**
    2. **行为差**：记忆检索命中率（当前 **0.5164**）、记忆门误开率、任务完成率。
    3. **淘汰结果（环境侧，模型外）**：存活率 / 淘汰率 / 危险回避率（当前 0.9814，**已饱和**，不作主判据）。
  - **预期**：B 臂命中率显著高于 A（对照论文 hybrid 一致最优、k=3 达峰，Fig.5b）；C 臂在注入后出现计划不连贯（对照论文 knowledge interference 论据）。**若 B 臂 ≤ A 臂**，或 **C 臂 = B 臂**（gate 无贡献），则降级为 **C 思想启发**。
  - **C8 旁证实验（可选）**：在 SSEA 域内复刻 Fig.6——只共享抽象 workflow vs 共享具体经历，比较跨环境迁移增益；若具体经历不带来增益甚至有害，即支持 C8 防膨胀条款。
- 若 **E 不采用**：不适用。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. SSEA 的 `retrieve` 是**非语言结构键**，BM25 词法通道无文本可索引——词法通道的等价物是什么（符号/谓词精确匹配？）？
  2. disagreement gate 的 β=0.8 是在**文本嵌入**上标定的；换到 SSEA 的结构表示后，一致性度量与阈值如何定义？
  3. SSEA 是否具备「跨个体」实体（本篇的 cross-framework = 跨个体）？若无，共享通道的对象是谁（同机体多次慢环快照？多并行机体？）——与 GEA 卡片同题。
  4. 抽象层与 C5 episodic store 的**分库边界**画在哪：哪些字段进抽象层、哪些必须留在精确层？
- **需补查的文献或资料**：
  1. **Xolver（arXiv:2506.14234）、G-Memory（arXiv:2506.07398）、CoPS（arXiv:2410.16670）、From Experience to Strategy（arXiv:2511.07800）本库均未建卡**，§6.1 对其描述依据各自摘要页 / 二手索引，**机制细节未核实**；若要纳入正式组合，须先补建卡片。
  2. 本篇**引用的 A-Mem / MemoryBank / ReadAgent** 延迟对比（Fig.4）为二手数字（取自 Xu et al. 2025），需核对口径。
- **需人工核对的公式 / 实现**：
  1. **Fig.5a 的 β 扫描图（p7–8）在 PDF 文本层中提取的数值与柱状对应关系不可靠**（文本抽取只留零散数字），本卡片仅记定性结论「β≈0.8 最优」，如需引用具体值须人工看图。
  2. **Fig.6（p9）跨域迁移的两个百分比**（reasoning→SWE 37.0%、SWE→GAIA 56.4%）为人工读图，须核对是否与正文口径一致。
  3. **Fig.7 误差分析**（净减 10 / 11）为单次运行、无 seed；不得当带误差棒的结论引用。
  4. 主结果 **pass@k 是同一 KB 的多次检索**（p5），属 test-time scaling，**非独立重复实验**——引用时须注明口径。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “AGENTKB aggregates trajectories into a structured knowledge base and serves lightweight APIs … hybrid retrieval operates through two stages: planning seeds agents with cross-domain workflows, while feedback applies targeted diagnostic fixes.” | p1（Abstract） |
| 三大挑战：Representation heterogeneity / Context mismatch / Knowledge interference | p1 |
| `E=⟨π,γ,S,C⟩`（Eq.1）：π=task embedding(all-MiniLM-L6-v2)、γ=structured predicates、S={(aᵢ,rᵢ)} action–reasoning pairs、C=metadata for cross-framework compatibility | p4（§3.2） |
| 去重：`max_{π′∈E} cos(π,π′)>τ`（τ=0.8），由 **LLM ranker** 比 reasoning quality/completeness/transferability | p4 |
| 效用淘汰：`uⱼ ← uⱼ + η(rⱼ − uⱼ)`，rⱼ 为 reward signal（retrieval success 或 execution gain） | p4 |
| 混合融合：`σ_hyb_i ← α·σ̃_text_i + (1−α)·σ̃_sem_i`，α=0.5；BM25 粗筛 + 语义精排 | p4（§3.3） |
| disagreement gate：`G(ρ,ρ′)=1[cos(ϕ(ρ),ϕ(ρ′))≥β]`，β=0.8；仅放行 G=1 的修订 | p5 |
| Refine 适配：entity mapping、tool substitution、step reordering | p5 |
| 80 条人工种子「are never retrieved directly; instead they guide automatic rollouts」 | p5（§4.1） |
| smolagents+GPT-4.1：55.2% → **73.9%**（pass@3，+18.7）；L2 53.5%→73.3% | Table 1 p6 |
| SWE-bench Lite：OpenHands+Claude-3.7 30.0% → **51.0%**（50 iter，+21.0） | Table 2a p6 |
| 消融：w/o Refine 最大跌幅 −6.06（61.21→55.15）；w/o Retrieve −3.63；w/ Raw Workflow 58.18 | Table 3 p7 |
| “hybrid strategy consistently achieves the highest accuracy”；top-k 在 **k=3** 达峰（GAIA L1 83.0%） | Fig.5b p8 |
| “Advanced reasoning tasks remain flat, suggesting that the quality of abstraction is bottlenecked, not the quantity.” | p8–9 |
| 自动 vs 人工：GAIA 75.15 vs 76.97（持平）、**L3 57.69 vs 53.85（反超）** | Table 4 p8 |
| **跨域不对称**：reasoning 经验 GAIA 73.9% / SWE-bench 37.0%；SWE 经验 SWE-bench 42.3% / GAIA 56.4%——“SWE knowledge does not generalize to reasoning tasks” | Fig.6 p9 |
| 误差分析：GPT-4.1 净减 10（25 baseline-only / 15 new）、Claude-3.7 净减 11 | Fig.7 p9–10 |
| “Performance assessment relies solely on ground-truth task completion metrics … rather than LLM-generated evaluation scores.” | App. G.2 p32 |
| 成本：GAIA 检索回路 +$0.27（<0.4% of $86.0）；SWE <$0.004/issue；一次性构建 $10.88（5.14M prompt + 0.77M completion tokens） | Table 6–7 p20 |
| 生成提示明令经验「without directly revealing the specific answer to the question」 | App. F.1.1 p26 |
| 库规模：≈7,802 任务 → **≈9,502 条经验**（BrowseComp 1,266 / MultiHopRAG 2,556 / HLE≈2,000 / WebWalkerQA 680 / RepoClassBench 1,000 / SWE-Gym-Raw 1,000 / RepoEval 1,000） | Table 5 p18 |
