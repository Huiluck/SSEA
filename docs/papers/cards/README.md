# 论文分析卡片集

对 `../`（`docs/papers/`）中论文逐篇做多维评估，决定**能否用于 SSEA**与**如何组合**。

- 空白模板与填写约定：[`../分析卡片-模板.md`](../分析卡片-模板.md)
- 卡片命名：`<论文短名>.分析卡片.md`，置于本目录
- 多维度评分以 1–5 分表格呈现（不生成雷达图）。
- 精读登记与候选名单：[`阅读统计.md`](阅读统计.md)

**当前进度：71 张卡片**（2026-09-29）。裁决分布：A 核心借鉴 **7** · B 零件采用 **58** · C 思想启发 **3** · D 基准对照 **3**。

---

## 卡片索引（按主题分组）

### 一、总纲与方法论（先读这三张）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [HarnessEval](HarnessEval.分析卡片.md) | **A 核心借鉴** | **P0** | 「如何证明自演化真的有效」的方法论底座：预算匹配基线 + 搜索/评测集分离 + 判据健康度 8 条检查表；直击判据饱和 / 0-33 / 读数字读错 / 债务 25。七条验收实验开跑前置 |
| [Misevolve](Misevolve.分析卡片.md) | **A 核心借鉴** | P1 | 模型/记忆/工具/工作流四路径误演化威胁模型与红队验收清单；自演化安全治理依据 |
| [SurveySelfEvolving](SurveySelfEvolving.分析卡片.md) | D 基准对照 | P2 | what/when/how/where 四维骨架作索引层；评测五维 + FGT/BWT/CPG 成本分类校准「睡眠期预算未定义」。**C9 反面教材**：把 reward-based 列为三大 How 之首，未区分「评分」与「环境淘汰」 |
| [SurveyComprehensive](SurveyComprehensive.分析卡片.md) | D 基准对照 | P2 | 独有价值在 Optimiser=(搜索空间 S, 算法 H) 形式化与领域分类学；与上篇重叠 60–70%，**先读 Gao（上篇）再选择性读本篇** |

### 二、C6 自修改 / C7 演化（四权分立与基因包）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [Ouroboros](Ouroboros.分析卡片.md) | **A 核心借鉴** | P1 | 受保护宪法核（P0–P4 不可删/降级）+ 指纹绑定提交（TOCTOU 防护）+ fail-closed：C6 四权分立唯一**已部署**的存在性证明（1,085 次自改、63.5% 阻断率）；另列「SSEA 尚缺十项防御」 |
| [Gödel Agent](Gödel-Agent.分析卡片.md) | B 零件采用 | P1 | 自指递归自改进的形式化北极星（π 与元算法 I 皆可改）；必须配门控与回滚 |
| [ADAS](ADAS.分析卡片.md) | B 零件采用 | P2 | 自动设计智能体的形式化（代码空间 × 搜索 × 评估）与档案/垫脚石；L4 模板，评估须改淘汰 |
| [MaAS](MaAS.分析卡片.md) | C 思想启发 | P2 | 架构超网分布 + 查询条件化早退 + 成本约束；L4 连续路线对照 ADAS |
| [SEAL](SEAL.分析卡片.md) | B 零件采用 | P2 | 自编辑数据改自身权重：给「不开 Δθ」提供**量化依据**（30–45 s/次评估、一轮 ≈6 h@2×H100、灾难性遗忘实证）；C3/C9 冲突 |
| [HarnessDev](HarnessDev.分析卡片.md) | B 零件采用 | P1 | 「诚实状态契约 + 自报状态永不计分」直治债务 26/27/28 的假成功；实测退化（+2.4 → held-out −10.32）是「淘汰事实取代评分」的最硬风险证据 |
| [LLMasCode](LLMasCode.分析卡片.md) | **A 核心借鉴** | P1 | 代码即控制流 + DAG 上下文作用域（输入 O(depth) 非 O(steps)）+ 提案→测试→commit as code；补 SSEA **回归门**的判据形状 |
| [EvoRoute](EvoRoute.分析卡片.md) | B 零件采用 | P1 | 步级自路由（多面检索→Pareto→Thompson）；三面检索治 `retrieve` 键收窄，双阶段给睡眠期预算模板 |
| [Aspire](Aspire.分析卡片.md) | B 零件采用 + D | P1 | 模糊目标下的**基座锚定留存记账**（best-evaluated/eligible/selected/retained 四档 + Δ_raw→Δ_ret 回滚式）直治 0/33 判据形状错 |
| [MetaContextEngineering](MetaContextEngineering.分析卡片.md) | B 零件采用 | P2 | ΔP→{ΔM 工件, ΔR-proc 检索程序} 双产物发布纪律；与 MemSkill 同族，建议并入其工作流 |

### 三、技能侧（ΔS：固化 / 表示 / 组合 / 评测）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [PSN](PSN.分析卡片.md) | **A 核心借鉴** | P1 | 技能即带契约的可执行网络：故障定位/成熟度门控/回滚验证重构，**技能侧主干** |
| [SkillRL](SkillRL.分析卡片.md) | B 零件采用 | P1 | 慢环回顾编译的**预算配额三元组**（间隔 5 / 失败 ≤10 / 新增 ≤3）+ 失败轨迹差分蒸馏 + 技能必带 when-to-apply |
| [Voyager](Voyager.分析卡片.md) | B 零件采用 | P2 | 自动课程（新颖性）+ 键/值技能库 + 独立 critic；技能库奠基原型，PSN 为其升级 |
| [SkillWeaver](SkillWeaver.分析卡片.md) | B 零件采用 | P1 | 技能提案-练习-合成-打磨流水线 + 强→弱 API 继承；网页版技能构造 |
| [InducingProgrammaticSkills](InducingProgrammaticSkills.分析卡片.md) | B 零件采用 | P1 | 入库三判据（重放成功 × 确曾调用 × 调用必须造成环境变化）+ 尾随动作截断；attempted/passed/reused 三档分母拆解 0/33 的三种病因 |
| [AutoSkill](AutoSkill.分析卡片.md) | B 零件采用 | P2 | SKILL.md 技能卡 schema + 语义并集合并代数 + 前台只读快照/后台异步演化；**反面样本**：库膨胀无退休机制 |
| [OpenSkill](OpenSkill.分析卡片.md) | B 零件采用 | P2 | 开放世界自演化；落点在第二阶段环境侧，技能主干已由 PSN 占据 |
| [ARISE](ARISE.分析卡片.md) | B 零件采用 | P1 | 两层 Cache(10)/Reservoir(100) + 五操作固定序 + 四阶段只判合法性的准入门 + 置信门弃权；「Intrinsic」是**伪友** |
| [SkillNet](SkillNet.分析卡片.md) | B 零件采用 | P2 | pre/post 场景契约 + post→pre 结构匹配 = 图可达性检查（**睡眠期离线试组合**缺的低算力形状）+ 二值组合完备度指标 |
| [SkillsBench](SkillsBench.分析卡片.md) | D 基准对照 | P1 | 配对三臂协议（无/策展/自生成技能）+ 确定性 verifier；**关键负结果**：自生成技能低于无技能基线（−8.1~−11.5 pp），≥4 技能与详尽文档增益塌陷 |
| [MemSkill](MemSkill.分析卡片.md) | B 零件采用 | P1 | 记忆技能 = 独立第四类 ΔP（并入 ΔR-proc）；难例缓冲 + 两阶段归因 + 睡眠期预算三元组（Table 3 唯一带数字的预算前沿） |

### 四、记忆侧（ΔM：写入 / 检索 / 巩固 / 组织）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [Memento](Memento.分析卡片.md) | **A 核心借鉴** | P1 | 冻结 LLM、以案例库读写与可学习检索 μ 实现适应；μ 治记忆门「取之准」；**记忆侧主干** |
| [A-MEM](A-MEM.分析卡片.md) | B 零件采用 | P1 | Zettelkasten 自组织记忆：链接拓扑 + 近邻回写演化 + 关联闭包检索；补联想结构 |
| [MemRL](MemRL.分析卡片.md) | B 零件采用 | P2 | 两阶段检索 + 冻结库迁移验收 + 遗忘率 FR；Memento 的保守简化版与验证补丁 |
| [SEDM](SEDM.分析卡片.md) | B 零件采用 | P1 | SCEC 自包含打包 + A/B 准入验证 + 跨域抽象重验；记忆准入官 |
| [LightMem](LightMem.分析卡片.md) | B 零件采用 | P1 | 摄入压缩 + 主题分段 + 睡眠期离线巩固 + 软更新；记忆效率工程与 C4 记账模板 |
| [Mem0](Mem0.分析卡片.md) | B 零件采用 | P1 | 事实抽取 + ADD/UPDATE/DELETE/NOOP 分类 CRUD + 实体关系图；生产级记忆参照 |
| [MemGen](MemGen.分析卡片.md) | B 零件采用 | P1 | 定长潜张量注入面（与快环向量通道形状契合）+ 可训练稀疏记忆门 + 激活预算；记忆内容写在 LoRA 里，故只能当读出口 |
| [Mem-alpha](Mem-alpha.分析卡片.md) | B 零件采用 | P1 | 离散写入动作空间 {insert,update,delete} + 类型化参数 + 三层记忆（core/semantic/episodic）→ 直对位慢环 ΔM 编译器 |
| [MemEvolve](MemEvolve.分析卡片.md) | B 零件采用 | P1 | **记忆基因型 Ω=(E,U,R,G) + 可修改位点白名单**（跨框架/跨 LLM 继承实证）；内环每代重置为空 → 跨代只继承架构不继承内容，正是 C8 要的形状 |
| [G-Memory](G-Memory.分析卡片.md) | B 零件采用 | P1 | 三层图记忆（insight/query/interaction）+ 双向遍历 + 1-hop/k∈{1,2} 纪律；消融实测**原始层贡献大于抽象层**，是 C5/C8 可共存的直接证据 |
| [CAM](CAM.分析卡片.md) | B 零件采用 | P1 | 增量重叠聚类（免全局重建）+ Prune-and-Grow 检索；**建构主义会损害精准**，须严格两层（事实层 append-only / 建构层可丢弃视图） |
| [GeneralAgenticMemory](GeneralAgenticMemory.分析卡片.md) | B 零件采用 | P1 | 无损 page-store + 有损 memo 索引双层分离（有损只压索引不压事实源）+ InfoCheck 二值门 |
| [ReasoningBank](ReasoningBank.分析卡片.md) | B 零件采用 | P1 | 推理单元 schema + 成功/失败双路抽取（≤3 条、去重、去语境化）+ 两级检索粒度；把记忆门从「开不开」升级为「开几条」 |
| [MemoryAsAction](MemoryAsAction.分析卡片.md) | B 零件采用 | P2 | 把上下文裁剪建模为策略动作（Prune&Write + ID 可寻址）；**前置：债务 27**；另钉出 `environment.memory_requests` 无界 append |
| [DynamicCheatsheet](DynamicCheatsheet.分析卡片.md) | B 零件采用 | P2 | 条目 schema（含溯源标签 + 中性计数 + version）+ 有界活文档 + 策展三分支（新增/修订/淘汰）；DC-∅ 空记忆对照臂可剥离脚手架增益 |
| [ACE](ACE.分析卡片.md) | B 零件采用 | P1 | 非 LLM 的确定性 delta 合并 + grow-and-refine（适应期输入 token −80.8%）+ 阈值不敏感实证；「慢环禁止整体重写」建议立即入规范 |
| [FLEX](FLEX.分析卡片.md) | B 零件采用 | P1 | 经验库三维拓扑（三层粒度 × golden/warning 双区）+ 写入三分支 + **经验增长 logistic 曲线作睡眠期停机判据**；权重全冻结 |
| [Xolver](Xolver.分析卡片.md) | B 零件采用 | P2 | 双记忆分层（长期 episodic 库 × 定长工作记忆）+ 运行中增量写回（+3.5/+7.7）；自陈 training-free，**未把经验写进权重** |
| [ThinkInMemory](ThinkInMemory.分析卡片.md) | C 思想启发 | P3 | 2023 年「写入时思考」的奠基表述，**具体机制已被 A-MEM/Mem0/LightMem/Memento/G-Memory 全面取代**；残留价值仅为术语与「偏置思想」诊断，作 C5 反例臂 |
| [MemEvolve / MemGen / Mem-α / MemSkill 族](MemSkill.分析卡片.md) | — | — | 见上；四篇合起来构成「记忆写入策略 vs 记忆注入面 vs 记忆元演化 vs 记忆技能」四分野 |

### 五、L3 学习 / 经验编译（ΔS/ΔM/ΔR 的产出侧）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [EvolveR](EvolveR.分析卡片.md) | B 零件采用 | P1 | 经验生命周期五段式回路（产生→抽象→两级去重合并→逐条计数→周期剪枝）+ `Merge` 抽象保留回指指针；**exp-absorb 反退化实证（0.382→0.371）** |
| [RetroAgent](RetroAgent.分析卡片.md) | B 零件采用 | P1 | UCB 探索项 `κ√(ln N/max(n,1))`（纯计数、无评分，直接移植，治记忆门选择性）+ `Φ_x` 相对增益信号；与 EvolveR 的 exp-absorb 结论**正面矛盾** |
| [EvoTest](EvoTest.分析卡片.md) | B 零件采用 | P1 | 确认**无梯度**（backbone 冻结，只改外部结构）→ 强证据支持 C3 与「Δθ 继续不做」；成本台账 Eq.8（20–30 s / 1 次 LLM 调用 vs GRPO 5–10 min@4×H100） |
| [SelfConsolidation](SelfConsolidation.分析卡片.md) | B 零件采用 | P1 | teacher(全历史)/student(少上下文) 蒸馏形状 + **重建式巩固判据 L_consolid**（纯行为、不含打分）可直接替换实验 3 那个形状错的判据 |
| [ExperienceToStrategy](ExperienceToStrategy.分析卡片.md) | B 零件采用 | P1 | 三层抽象「经验(Q)→FSM 规范化路径(T)→策略原则(M)」；**M 层是 `rules`(ΔR) 零消费者的首个落点**，T 层回应技能表示 |
| [AgentKB](AgentKB.分析卡片.md) | B 零件采用 | P1 | 混合双通道检索（BM25+语义 α 融合，k=3）+ Reason 式查询展开直修 `retrieve` 键收窄；disagreement gate 补记忆门选择性；**Fig.6 跨域不对称支持「可继承=抽象 workflow，非具体经历」**（仅方向性证据） |
| [ExperienceSynthesis](ExperienceSynthesis.分析卡片.md) | B 零件采用 | P1 | `V_τ=(1/n)Σ(r_i−r̄)²` 奖励熵**难度选择器**（只选情境、不训个体，C9 合规最小实现，`V_τ≈0` 即无分辨率）+ 幻觉失败反馈维度 |
| [EarlyExperience](EarlyExperience.分析卡片.md) | B 零件采用 | P1 | `L_IWM=−Σ log p_θ(s'|s,a)`：把「预测误差」落成 reward-free 的下一状态预测目标 → SSEA `prediction_error`（C9 第二层）最直接外部参照 |
| [RecordReplay](RecordReplay.分析卡片.md) | B 零件采用 | P2 | 多层经验分类：低层=带变量的**参数化**动作序列（非逐帧照做）、高层=抽象 policy；check function 四类 → 映射四级验证门。**判决：0/33 的失败形态很可能是技能被写成定长动作串** |
| [Reflexion](Reflexion.分析卡片.md) | B 零件采用 | P2 | 试错-评估-反思外环经典形状 + 自写测试启发式；语言通道待去语言化 |
| [RAGEN](RAGEN.分析卡片.md) | B 零件采用 | P1 | Echo Trap 诊断 + 不确定性过滤 + rollout 塑造；参数侧训练的诊断仪与稳定化手册 |
| [WebRL](WebRL.分析卡片.md) | B 零件采用 | P2 | 从失败造训练任务的自演化课程 + 置信过滤 + 错误分类法；权重 RL 不进模型 |

### 六、L4 演化 / 群体与继承

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [GroupEvolving](GroupEvolving.分析卡片.md) | B 零件采用 | P1 | 归档合法性准入门（只判合法性不打分）+ 祖先整合计数 + 能力项二态追踪 → Gene Manager 共享侧观测指标；**C8 张力**：可共享结构性先验，禁共享具体经历 |
| [CoMAS](CoMAS.分析卡片.md) | C 思想启发 | P2 | **C9 专项裁决 ✗**：交互奖励 = LLM-judge 标量分经零和塑形驱动参数——C9 看的是「信号是不是打分、是否驱动参数」，不是「打分者是谁」；只取自评回路失败模式诊断 |
| [AgentEvolver](AgentEvolver.分析卡片.md) | B 零件采用 | P1 | **成本标尺**（8×A100、100 条样本→40.3%、Steps@.9 −55%/−67%）直答睡眠期预算 + Experience Stripping + reference-replay 可行性门 |
| [Agent0](Agent0.分析卡片.md) | B 零件采用 | P1 | 前沿带选择 `|p̂−0.5|≤δ`（去奖励化后作惊奇分位带硬门，直击债务 22）+ 「外部客观锚点打破自演化天花板」原则 |
| [R-Zero](R-Zero.分析卡片.md) | B 零件采用 | P1 | 零数据自演化族旗舰基线；**C8 严格度标尺** + 自合成数据崩溃诊断（伪标签 79%→63%，达峰后掉头）；C9 五重违规 |
| [TTCS](TTCS.分析卡片.md) | B 零件采用 | P1 | 无标签自洽性前沿带 `R_cap=(4s(1−s))^γ`：**绕过 SSEA「生存域无 ground-truth」这道最硬门槛**；须与 GenEnv 合并使用 |
| [GenEnv](GenEnv.分析卡片.md) | B 零件采用 | P1 | α-难度带 + Theorem 1 样本量界 → **判据分辨力校准器与实验样本量计算器**；直接回应「判据饱和」 |
| [ExpSeek](ExpSeek.分析卡片.md) | B 零件采用 | P1 | **内生不确定性自触发门**（token 熵决定何时求助）+ 阈值区间 + 三区概率门 + 一步静默 → 直替债务 22 常量阈值；警告：过程步 AUC 仅 0.6223，须先修信号 |
| [MemEvolve](MemEvolve.分析卡片.md) | B 零件采用 | P1 | 见「记忆侧」；同时是 L4 记忆元演化的主参照 |

### 七、环境 / 世界（第二阶段生态与淘汰压力来源）

| 论文 | 裁决 | 优先级 | 一句话结论 |
|---|---|---|---|
| [Agent-World](Agent-World.分析卡片.md) | B 零件采用 | P1 | 环境包契约 `(D,F)` + **通道消费者准入** + 可执行验证脚本 + 难度三旋钮；不搬 LLM 策略与失败驱动共演化 |
| [ScaleEnv](ScaleEnv.分析卡片.md) | B 零件采用 | P1 | 规则式终局判据三档（Exempt/Hard/Semantic，明确拒绝 LLM-judge）+ Procedural Testing 通道准入 → 直接解债务 25/26/27/28；**不检测判别力**，须配 GenEnv 校准器 |
| [AutoEnv](AutoEnv.分析卡片.md) | B 零件采用 | P1 | **判据健康度双件套**（差分模型可靠性检查：弱臂≥强臂即判据饱和；Skin-Inverse 控制消融）+ 三层环境抽象 BaseEnv/ObsEnv/SkinEnv（结构化观察 vs 语言皮肤分离，服务 C2） |
| [EndlessTerminals](EndlessTerminals.分析卡片.md) | B 零件采用 | P1 | 四阶段无人工合成流水线 + **隐藏特权真值 + 环境侧确定性终局测试**（最干净的 C9 层①形状）；难度锚定前沿模型是天花板缺陷 |
| [AutoForge](AutoForge.分析卡片.md) | B 零件采用 | P2 | DAPO 动态采样（剔除全对/全错）= 把判据饱和操作化为样本级判别力门；`E=(S,F)` 环境包可版本化 |
| [Genie](Genie.分析卡片.md) | B 零件采用 | P2 | 无监督生成可玩世界：潜在动作 + ST-Transformer + MaskGIT；Dream-RSI 的生成延续件 |
| [Dream-RSI](Dream-RSI.分析卡片.md) | **A 核心借鉴** | P1 | 发现历史即重放模拟器，为慢环提供「做梦式」廉价离线提案验证；C9/C2 两处需改造 |

### 八、综述与索引层

见「一、总纲与方法论」中的两张综述。

---

## 裁决等级

- **A 核心借鉴**：思想或机制构成 SSEA 某模块骨架
- **B 零件采用**：具体算法/表示可直接用于某模块
- **C 思想启发**：思路有启发，需重新设计
- **D 基准对照**：作为基线、数据集或评测参照
- **E 不采用**：与立场冲突或无关

## 交叉索引：按 SSEA 缺口找卡片

| SSEA 缺口 | 首选卡片 |
|---|---|
| 判据饱和 / 判据形状错 / 读数字读错（债务 25–28） | **HarnessEval(P0)** · AutoEnv · Aspire · ScaleEnv · Agent-World |
| **Gene Manager 缺失**（实验 4/5 卡住） | **MemEvolve**（记忆基因型 + 位点白名单）· GroupEvolving · ScaleEnv/AutoForge（环境包） |
| 记忆门「开得准不准」 | ExpSeek · MemGen · MemRL · ReasoningBank · MemSkill · RetroAgent(UCB) |
| `retrieve` 键收窄 → 召回精度上限低 | EvoRoute（三面检索）· G-Memory · AgentKB · CAM · GeneralAgenticMemory |
| **睡眠期计算预算未定义** | EvoTest · AgentEvolver · MemSkill · FLEX · SkillRL · AgentEvolver · SEAL（反面标尺） |
| 技能表示够不够（0/33 未答） | **SkillsBench**（外部负结果）· InducingProgrammaticSkills · SkillNet · RecordReplay · ExperienceToStrategy |
| `rules` 零消费者 | ExperienceToStrategy（M 层）· MemSkill（ΔR-proc） |
| 环境对无消费者通道报成功（债务 27） | ScaleEnv · Agent-World · EndlessTerminals · AutoEnv · MemoryAsAction |
| 自修改防御机制不足 | **Ouroboros**（十项缺失清单）· HarnessDev · LLMasCode |
| 自演化安全 / 误演化 | Misevolve · CoMAS（自评回路失效）· HarnessDev（实测退化） |
