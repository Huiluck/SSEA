# 论文分析卡片 · AutoSkill

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2026-03-01 AutoSkill Experience-Driven Lifelong Learning via Skill Self-Evolution.pdf` |
| 标题 | **AutoSkill: Experience-Driven Lifelong Learning via Skill Self-Evolution** |
| 作者 / 机构 | Yutao Yang、Junsong Li、Qianjun Pan、Bihao Zhan、Yuxuan Cai、Lin Du、Jie Zhou、Kai Chen、Qin Chen、Xin Li、Bo Zhang、Liang He；华东师范大学计算机科学与技术学院（ICALK@ECNU）+ 上海人工智能实验室 |
| 发表时间 / 出处 | arXiv:2603.01145v2 [cs.AI]，2026-03-05（Preprint，v2） |
| 论文链接 | arXiv:2603.01145 |
| 代码链接 | github.com/ECNU-ICALK/AutoSkill（论文首页给出；本卡未核对仓库实现） |
| 标签 | 技能自演化 · 经验驱动终身学习 · SKILL.md 技能工件 · add/merge/discard 准入 · 版本化语义合并 · 前后台双环 · training-free |
| **应用裁决** | **B 零件采用**（表示与合并代数、准入三值判定、双环解耦可直接拆件；但四项硬约束冲突且证据弱，不能作主干） |
| 优先级 | **P2**（若实验 3 重设计采纳「文本化技能卡」作为第二表示分支，可升 P1） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：把用户在对话中反复表达的稳定偏好/流程约束，不当作「待检索的记忆文本」，而当作**技能形成的原料**——经抽取（只用**用户侧 query** 作证据）→ 与最近邻已有技能比较 → LLM 判定 **add / merge / discard** → 合并时**保留技能身份 + 语义并集 + 版本递增**，结晶为结构化的 **SKILL.md** 工件，再在推理时经「查询重写 → 稠密+BM25 混合检索 → Top-K 阈值过滤 → 注入上下文」回灌给生成模型；全程 **training-free**，不碰权重（§3 p3–8，§4 p8–11）。
- **对 SSEA 的意义**：它提供了三件 SSEA 目前缺的东西——① 一份**可 inspect / 可 diff / 可合并的技能卡 schema + 明确的合并代数**（正面回应「技能表示够不够」这条未答债务）；② 一个与 FSL/SEL **同构的前台只读快照 + 后台异步演化**的工程样例；③ 一个关于**技能库膨胀**的**反面样本**：只有「合并防重复」、没有「退休/淘汰」、没有增长曲线与遗忘指标，正好反证 C8/C4 必须自建淘汰函数。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（§1 p1–2）：真实 LLM 应用中用户会跨 session 反复陈述稳定偏好（少幻觉、遵循机构写作规范、避免术语堆砌），但这类**交互经验极少被固化为可复用知识**，导致 agent 每开新会话都要重新建立习惯与任务预期。
- **它指出的既有方案缺陷**（§1 p1、§2 p2–3）：
  1. **参数更新 / 自演化路线**（SELF、self-improve、RISE、SEC、UPO）：成本高、在需要细粒度频繁个性化时难控；
  2. **记忆路线**（RAG、MemoryBank、MemGPT、Mem0、A-MEM、MemInsight）：把过去交互当作「待检索的文本」，而不是「可被操作化的行为」；
  3. **agent / 技能学习路线**（ReAct、Toolformer、ART、Gorilla、Voyager、Reflexion）：技能**停留在 prompt、轨迹或隐式策略里**，缺少统一的 inspect / edit / transfer / 长期维护机制。

### 2.2 核心思想（关键 insight）
1. **积累单元从「记忆记录」换成「显式行为知识」**：记忆是文本，技能是可执行的行为单元；检索要复活的是「怎么做」，不是「说过什么」（§1 p2、§2.3 p3）。
2. **技能库靠「精炼」而非「复制」增长**：后来的反馈应更新**同一个**工件，而不是产生一堆重叠的 prompt 片段——这是它对抗库膨胀的唯一手段（§4.3 p9、§4.1 p8「Continuous but controlled evolution」）。
3. **判定只在局部近邻上做，不在全库上做**：候选先检索 TopM 邻居，judge 只比较 candidate 与其 argmax 邻居，**决策成本与库规模解耦**（§3.4.2 p7）。
4. **学习信号只取环境/用户侧**：抽取阶段只吃 user query，**不用模型自己的回复**作证据，避免把自我生成内容当成监督（§3.1 p4、§3.4.1 p6）。
5. **训练免费即部署可行**：全部模块为 prompt 实例化的通用 LLM + embedding 模型，换 backbone 不需重训框架（§3.2 p4–5、§3.5 p8）。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处 |
|---|---|---|---|
| **技能表示** s=(n,d,p,τ,γ,ξ,v) | name / description / prompt(可执行指令) / triggers / tags / examples / version | 标准化、可检索、可共享的技能单元 | §3.1 p4 |
| **候选表示** z_t=(n,d,p,τ,γ,ξ,c) | 同上 + **confidence c** | 抽取产物（c 的后续用法论文未说明） | §3.4.1 p6 |
| **SKILL.md 工件** | 中心文件 + 可选 scripts/ references/ assets/ | 把学到的行为变成**一等系统对象**，可 inspect/edit/import/export | §4.2 p9、§4.5 p10 |
| **Prompt 内部结构** | `# Goal` `# Constraints & Style` `# Workflow(可选)`；卡片实体还有 Anti-Patterns / Output Format / Role & Objective | 约束与反例显式化，便于检查与合并 | §3.4.1 p6、§3.4.3 p8、附录 p13–15、19–22 |
| **查询重写 M_rw** | (q_t, h_t) → 独立检索查询 q̃_t | 消解指代、判断「延续 vs 话题切换」、保留 topic anchor、只留检索相关约束 | §3.3 p5 |
| **混合检索** Rel(q_t,s)=λ·d̂+(1−λ)·b̂ | 稠密 sim + BM25，各自归一化到 [0,1] 加权 | 语义匹配 + 字面精确匹配双通道 | §3.3.1 p5 |
| **Top-K + 阈值 η 注入** | H_t={s∈TopK | Rel≥η}；C_t=Render(H_t) | 限制注入量；无命中则不增强 | §3.3.1–3.3.2 p5 |
| **技能抽取 M_ext** | 近期 user query 窗 → 候选 z_t（含 principles：只抽 durable/reusable，不抽一次性请求、不臆造步骤、去掉实例级实体） | 经验 → 技能抽象 | §3.4.1 p6 |
| **检索辅助的近邻判定** | Rel_m(z_t,s)=α·d̂+(1−α)·b̂ → N_t=TopM → s*_t=argmax | 管理决策只针对最相关邻居，可扩展 | §3.4.2 p7 |
| **管理判定 M_judge → a_t∈{add, merge, discard}** | (z_t, s*_t) → {action, target_skill_id, reason} | **准入官**：五步流程（话题/能力族连续性 → discard gate → 四轴比较 → merge/add 判据） | §3.4.2 p7 |
| **discard gate** | 拒绝 generic / low-signal / non-portable / library-covered 候选 | 入口侧噪声过滤（**注意：只过滤新候选，不淘汰已有技能**） | §3.4.2 p7 |
| **四轴比较** | job-to-be-done / deliverable type / hard constraints & success criteria / required tools & workflow | merge 与 add 的判据 | §3.4.2 p7 |
| **版本化合并 M_merge** | (s*_t, z_t) → s'_t；v(s'_t)=Bump(v(s*_t)) | 保留身份 + **语义并集**（非拼接）+ 8 条合并规则（不臆造、不携带陈旧约束、去重、语言一致等） | §3.4.3 p7–8 |
| **库更新规则** | add：B∪{z}；merge：(B\{s*})∪{s'}；discard：B 不变 | 形式化的技能库演化方程 | §3.4.3 p7 |
| **四阶段生命周期** | 经验摄入 → 技能抽取 → 维护与版本化 → 复用 | 终身学习的流程骨架 | §4.3 p9 |
| **前台/后台解耦** | 关键路径 retrieve-then-generate；抽取与维护**异步后台**执行，不阻塞用户可见延迟 | 延迟与学习分离 | §4.4 p9–10 |
| **存储布局** | `SkillBank/Users/<uid>/<slug>/SKILL.md`、`Common/`（共享）、`vectors/`（*.meta.json/*.ids.txt/*.vecs.f32） | 个人知识与共享知识**目录级分离**；持久化向量索引 | §4.5 p10 |
| **三种部署形态** | Python SDK（ingest/search/render_context）、Web UI、OpenAI 兼容反向代理（/v1/chat/completions 等） | 低摩擦接入既有 LLM 栈 | §4.2 p9、§4.6 p10 |
| **离线冷启动** | 历史 OpenAI 格式对话 / 文档 / agent 轨迹 → 预填 SkillBank | 上线即非空库 | §4.6 p10 |

### 2.4 关键表示与数据结构
- **技能 = 七元组 + Markdown 工件**：s=(n,d,p,τ,γ,ξ,v)。其中 **τ trigger set 是检索键的显式化**（把「什么情况下用」从语义里单独拎出来），**γ tag set 用于统计与归类**，**p 是自然语言的可执行指令体**（§3.1 p4）。
- **prompt 体的固定小节**：`# Goal` / `# Constraints & Style` / `# Workflow`（仅当显式多步流程时）；实际卡片还稳定出现 **Anti-Patterns**（显式负约束）、Output Format、Role & Objective（§3.4.1 p6、附录 p13–15、19–22）。
- **版本 = 单点递增**（Bump，论文举例为 patch 级），论文**只展示版本号，未提及保留历史版本正文**（§3.4.3 p7）。
- **索引**：稠密向量 + BM25 双通道，向量缓存独立于工件存储（§4.5 p10）。
- **raw 经验不做长期留存**：近期对话窗 h_t 只在生成期可见；原始交互被抽象后**未提及**保留可检索的情景记录（§3.1 p4、§3.3 p5）。

### 2.5 实验证据
| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| WildChat-1M 四子集 SkillBank 规模（Table 1） | **无基线** | 中/GPT-3.5：5912 对话、134670 消息、均值 22.78 msg/对话、**400 技能**；英/GPT-3.5：10243、267681、26.13、**631**；中/GPT-4：1145、36834、32.17、**224**；英/GPT-4：5211、157508、30.23、**603** | 一次性流水线扫描四个子集下的 SKILL.md；保留 >8 轮的对话；**无 seed、无重复运行、无下游指标**（§5.1–5.2 p11–12） |
| 技能类别分布（Fig 2，N=1858） | — | 编程与软件开发 **482**、写作与内容创作 **363**、数据与 AI/ML **354**、通用/混合 **356**、系统/DevOps/配置 194、研究与教育 72、运营与市场 23、其他特定领域 14 | 绝对频数（本人按 Fig 2 读数；四类合计 400+631+224+603=1858，与 N 一致） |
| 高频标签（Table 2） | — | python 98、javascript 38、excel 36、c++ 35、creative writing 35、formatting 35、pandas 30、education 29、translation 28、matlab 24 | YAML tags 字段，拉丁标签大小写不敏感归一（§5.2 p12） |
| 平台提及（Fig 3） | — | Twitter/X 27、Instagram 24、YouTube 13、Douyin/TikTok 6、WeChat OA 4、LinkedIn 4、Xiaohongshu 3、Weibo 1 | 名字/描述/标签/触发词中出现平台关键词即计数（§5.2 p12） |
| 版本化证据（案例） | — | `professional_text_rewrite` **v0.1.34**（论文解读为 34 轮增量优化）；`顶级心理咨询师` **v0.1.0** | **两个个案**，论文自陈为 "qualitative evidence"（§5.3 p13） |
| 技能抽取产出率（本人计算，非论文数字） | — | 四子集合计 22511 对话 → 1858 技能 ≈ **8.3%（约每 12 通对话 1 个技能）**；分子集 6.8% / 6.2% / 19.6% / 11.6% | 由 Table 1 数值相除得出，**属推断**，非论文主张 |
| **下游任务增益 / 消融 / 遗忘 / 库增长曲线** | — | **全部未提及** | §5 全为描述性统计 + 2 个案例（§5 p11–15） |

### 2.6 论文自陈局限与边界条件
- **论文未设独立的 Limitations 小节**：§6 p15 为「结论与未来工作」，只讲贡献与方向，**未列举局限**。以下边界条件为正文可确证者：
- 假设依赖：
  1. 假设**用户会反复表达稳定偏好/约束**——用户不表达则无可抽之物（§1 p1）；
  2. 假设技能可被**自然语言 prompt** 完整表达（p 字段即指令体），故适用场景偏向**风格、格式、流程、写作、代码生成**类（Fig 2 分布与此一致）；
  3. 依赖通用 LLM 与 embedding 模型的质量（可插拔但不可替，§4.7 p10）。
- 明确不适用 / 未覆盖的情形（**本卡判断，非论文自陈**）：
  - 无具身 / 生存场景，无环境反馈闭环，无失败-死亡信号；
  - 无技能**退休**、无容量上限、无灾难性遗忘测量；
  - 无合并后的**验证与回滚**（改坏不可逆，见 §5 冲突节）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | **✗** | 场景是对话助手个性化（写作风格、格式、角色扮演、Selenium 脚本生成），**无生存/具身控制环**；技能本身就是注入生成模型的自然语言指令（§3.3.2 p5） | 只搬「外置技能库 + 后台演化」的信息流形状；控制环换回结构化信号；把 SKILL.md 字段**编译**成非语言门控谓词（triggers→键，Anti-Patterns→禁止谓词） |
| **C2** 自然语言只作观察员接口 | **✗** | 技能的**载体即自然语言 prompt**（p 字段），注入 C_t 后直接改变输出；抽取/判定/合并三模块全部由 LLM prompt 承担（§3.2 p4、§3.4 p6–8）。语言既在生成回路内，又是自我修改的执行者 | 把语言使用**退回慢环编译面**（RuleCompiler 角色），运行时零语言；快环只读结构化技能快照 |
| **C3** 权重/记忆/技能三分离 | **◐** | 权重/技能分离明确 ✓：training-free，全部改进来自外部技能（§3.5 p8）；**记忆/技能未分离 ✗**：原始对话只在近期窗 h_t 可见，经验被抽象成技能后**未提及**保留可检索情景记录，论文且以「从记忆文本提升到行为单元」自居（§2.3 p3） | 在 SkillBank 旁保留**独立 episodic 层**（对应 SSEA ΔM），技能层只存可移植规则，二者生命周期不同 |
| **C4** 低算力低带宽 | **◐** | 正面：Top-K + 阈值 η 限注入量（§3.3.1 p5）；判定只在 TopM 邻居上做、与库规模解耦（§3.4.2 p7）；演化走后台异步不占前台延迟（§4.4 p9–10）。负面：**技能库无容量上限、无已有技能退休机制**（全文未提及），长期只增不减；抽取/检索/判定每轮常驻调用 | 加容量上限与淘汰函数；把抽取判定**降频**到慢环节律；前台只读快照 |
| **C5** 精准回忆历史 | **◐** | 技能级可精确写入/编辑/合并/版本化 ✓（工件可 inspect/edit/import/export，§4.2 p9、§4.7 p10）；**情景级 ✗**：具体经历不留档，版本只记号码、**未提及**保留旧版本正文，无法精准回忆某次具体经历 | 情景层自建（ΔM）；技能层保留版本链 + 逆操作日志（PSN 给模板） |
| **C6** 可自主修改自身 | **◐** | 提案权 ✓（M_ext 提出候选）；边界权 ◐（discard gate + 四轴比较 + 8 条合并规则，**但由 LLM 判定而非法式边界**，§3.4.2 p7）；**验证权 ✗（全文未提及任何沙盒/回归/回滚验证）**；应用权 ✓（后台写入 §4.4 p10） | 必须外接 SSEA **四级验证门 + 逆操作日志**；否则不满足 C6 的验证权要求 |
| **C7** 可保存/恢复/变异/继承 | **◐** | 保存 ✓（本地文件 + 向量索引，可 import/export）；**恢复 ✗**（无回滚、无历史版本）；变异 ◐（merge = 语义并集，是受限的内容变异，但只增不减）；继承/共享 ✓（明确主张跨 agent/user/task 共享迁移，§1 p1、§4.5 p10 Common/）——此项即 C8 冲突源 | 恢复能力自建；共享范围按 C8 收窄 |
| **C8** 给基因先验，不给知识语料 | **✗** | 技能**全部从交互经验抽取**（后天知识），且明确设计为**跨 agent / user / task 共享与迁移**（abstract p1、§1 p1、Common/ 共享库 §4.5 p10），即后天知识跨代 | **照抄 Users/ vs Common/ 二分，但反转语义**：`Common/` 只放结构性先验（字段模板、门控谓词形式、表示规范）= GenePackage；`Users/` 放个体后天技能，个体死亡即消失、不进基因包 |
| **C9** 不设评分函数，只有淘汰函数 | **✗** | 四处评分：① Rel=λd̂+(1−λ)b̂ 检索**打分排序** + Top-K + 阈值 η（§3.3.1 p5）；② 管理期 Rel_m 打分取 argmax 邻居（§3.4.2 p7）；③ 候选自带 **confidence c**（§3.4.1 p6）；④ judge 由 LLM 按四轴判 add/merge/discard，本质是**观察员评分**（§3.4.2 p7） | 剥离方案见下：检索打分降级为**布尔可达性**（命中 trigger 键即入候选，**不排序**）；删除 c；judge 改为**合法性三问**（与已有技能重复→merge；在许可边界内→add；违反构造规则→discard），只判合法性不打分；淘汰权交环境侧 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | **✓** | 无新算子，全部为现成 LLM + embedding，明确 training-free（§3.2 p4–5、§3.5 p8）；创新在表示与生命周期（L3）、双环与存储/服务解耦（L2）、跨个体共享（L4） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层** | 无。LLM / embedding 均为借用件，可插拔替换（§4.7 p10） | 符合借用立场，无价值也无风险 |
| **L2 信息流层** | 前台 retrieve-then-generate 关键路径 + **后台异步演化**双环；查询重写；混合检索→Top-K+阈值→Render 注入；`Users/Common/vectors` 存储布局；三种部署接口 | **高**：与 SSEA FSL/SEL 双环**工程同构**（前台只读快照、后台不阻塞），是罕见的同构样例；阈值化的注入量控制呼应 C4；Users/Common 二分是 GenePackage 的目录级模板 |
| **L3 学习层** | 四阶段生命周期、add/merge/discard 准入、**语义并集**合并代数与 8 条合并规则、版本递增、「只用 user 侧 query 作证据」 | **高**：给 SSEA 慢环补上缺的「技能 ΔS 的**准入官 + 合并算子**」；证据来源约束值得照抄 |
| **L4 演化层** | 跨 user/agent 的共享技能库与标准化表示、离线冷启动、import/export | **中（须按 C8 改造）**：共享与冷启动在 SSEA 必须让位给「基因只给先验、后天知识不跨代」 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| SKILL.md 技能卡 schema（n/d/p/τ/γ/ξ/v + Goal/Constraints&Style/Workflow/Anti-Patterns） | `skill_library.py` 技能规格的**第二候选表示**（当前实验 3 固化表示之外的对照分支）；τ triggers → Gate 的**合法性键**，Anti-Patterns → 禁止谓词 |
| 语义并集合并算子 M_merge + 8 条合并规则 | **新增 SkillMerger**（慢环）：当前 SSEA 只有技能写入，无合并代数 |
| add / merge / discard 判定 + discard gate + 四轴比较 | **新增技能准入官**（与 SEDM 在记忆侧的准入官对称）；判据改为合法性三问后接四级验证门 |
| 抽取只以 user 侧 query 为证据 | `ExperienceCompiler` 的**证据来源约束**：环境/外部信号优先，禁用自生成内容作监督 |
| 查询重写 M_rw（指代消解 + topic anchor + 保留检索相关约束） | **新增 retrieve 键归一化前置**（针对「`retrieve` 键收窄 → 召回精度上限低」债务）；非语言侧实现为键的结构化规范化 |
| 混合检索 dense+BM25 + Top-K + η | 检索面双通道（结构化键精确匹配 + 软匹配）；**η 必须做成慢环可调**（勿重蹈债务 22） |
| 前台只读快照 / 后台异步演化 | FSL/SEL 解耦的工程参照；睡眠期预算的**每轮上界**可借鉴「1 次抽取 + TopM 局部判定」的固定小预算 |
| TopM 近邻局部判定 | 慢环计算预算约束（呼应「睡眠期计算预算未定义」缺口） |
| 版本号（0.1.34 vs 0.1.0） | 低成本的**技能成熟度/可塑性可观测量**（PSN 用 V(s)，此处用版本计数即可） |
| `Users/` vs `Common/` 二分 | GenePackage（结构先验）vs 个体技能库（后天、不跨代）的目录级分离模板 |
| SkillBank 目录布局 + SDK(ingest/search/render_context) | 若 SSEA 需要一个可 inspect 的技能仓库，布局可直接照抄 |

### 3.4 债务与验收实验对应
- **「技能表示够不够」（0/33 之后仍未回答）**：本篇给出**唯一一份带合并代数的完整技能卡 schema**，可作为实验 3 的**第二表示分支**（文本化结构化卡）与 PSN 的代码契约表示做 A/B。
- **「`retrieve` 键收窄 → 召回精度上限低」**：查询重写 + triggers 显式键 + 双通道检索，是三条可抽出的修复线索。
- **债务 22（记忆二级门用常量阈值、慢环不可调）**：AutoSkill 的 η / λ / α / TopK / TopM **同样是常量且取值未给出**（§3.3.1 p5、§3.4.2 p7）——作**反面参照**：搬它时不得再引入一个常量阈值，须让慢环可调。
- **债务 25/26/27/28（判据形状错、无消费者通道报成功、技能失效被判成功）**：add/merge/discard 三值 + 版本递增 + 合并规则违反计数，是**可数的机制指标**（先看分母），可替代 SKILL_FAILURE 的 0/33 形状。
- **技能库容量 / 膨胀与灾难性遗忘**：本篇**未提供解法**（无退休、无增长曲线、无遗忘指标），只能作为**要补什么的清单**；解法仍需 PSN（回滚验证）+ SSEA 自有的淘汰函数 + C8。
- **睡眠期计算预算未定义**：TopM 局部判定提供「固定小预算」的设定范式（**推断**）。
- **服务的验收实验**：实验 3（技能固化）**重设计**（三臂表示 A/B）；间接服务实验 6/7（记忆/检索侧）的键归一化部分；**不服务**实验 4/5（缺 Gene Manager，本篇反而与 C8 冲突）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | SKILL.md 技能卡 schema（n/d/p/τ/γ/ξ/v + Goal/Constraints&Style/Workflow/**Anti-Patterns**） | 表示 | 改造移植 | skill_library / Gate | 「技能表示够不够」；让技能可 inspect、可 diff、合法性有键、负约束可检查 | 高 |
| 2 | **语义并集合并代数** + 8 条合并规则（保身份、非拼接、不臆造、不带陈旧约束、去重、语言一致） | 算法/协议 | 改造移植 | 新增 SkillMerger（慢环） | 技能库的「精炼而非复制」，直接压重复 | 高 |
| 3 | **add / merge / discard 准入三值判定** + discard gate + 四轴比较 | 协议 | 改造移植（去掉打分，改合法性三问） | 新增技能准入官 | 技能 ΔS 的入口噪声过滤与重复识别 | 中 |
| 4 | **前台只读快照 + 后台异步演化**的双环工程形态 | 工程实现 | 直接移植（思想级） | FSL/SEL 解耦、serving 层 | 快环不被慢环阻塞；给「快照只读」一个工业佐证 | 高 |
| 5 | **TopM 近邻局部判定**（决策成本与库规模解耦） | 算法 | 直接移植 | 慢环准入官 / 预算控制 | 库变大后准入不爆炸；给睡眠期预算定上界 | 高 |
| 6 | **只用环境/用户侧信号作抽取证据**（不用模型自身输出） | 思想 | 直接移植 | ExperienceCompiler | 规避自我蒸馏漂移 / Echo Trap；对齐 C9「淘汰权归环境」 | 中 |
| 7 | 查询重写（指代消解 + topic anchor + 保留检索相关约束） | 提示设计/算法 | 仅借思想 | retrieve 前置归一化 | `retrieve` 键收窄导致召回上限低 | 中 |
| 8 | 版本号作为**成熟度/可塑性可观测量**（0.1.34 vs 0.1.0） | 指标 | 改造移植 | plasticity / HeritableFilter | 比 PSN 的 V(s) 更廉价的成熟度代理信号 | 中 |
| 9 | `Users/` vs `Common/` 目录级二分 | 工程实现 | 改造移植（**语义按 C8 反转**） | GenePackage vs 个体技能库 | 让「基因只给先验、后天不跨代」有落盘形状 | 中 |
| 10 | 混合检索（稠密 + BM25）+ Top-K + 阈值 | 算法 | 仅借思想（打分改布尔可达） | 检索面 | 结构化键精确匹配 + 软匹配互补 | 中 |
| 11 | **反面样本**：只有合并、没有退休 → 库膨胀无解 | 对照 | 仅作对照 | C8/C4 设计复核 | 提醒 SSEA 必须自建淘汰函数与容量上限 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突（对应 3.1 的 ✗/◐）**
  1. **C9（四处评分）**：Rel 检索打分排序、Rel_m 邻居打分、候选 confidence c、LLM judge 四轴评分。剥离方案（可操作）：检索改为**布尔可达**（命中 τ 键即入候选，不排序不截断）；**删除 c**；judge 改为**合法性三问**（重复→merge / 在边界内→add / 违反构造规则→discard），只判合法性不打分不排序；技能成败由**环境侧**记录，模型不给自己打分。
  2. **C1/C2（语言作控制器）**：技能载体即自然语言 prompt 且注入生成回路。剥离方案：语言只在慢环编译面出现，SKILL.md 的语义被**编译**为结构化谓词/参数化策略后再进快环；运行时零语言。
  3. **C8（跨代知识共享）**：Common/ 共享库与「跨 agent/user/task 迁移」是明确主张。剥离方案：保留目录二分、反转语义（Common/ = 结构先验 = GenePackage；Users/ = 个体后天、不跨代、随个体死亡消失）。
  4. **C6 验证权缺失**：合并直接覆盖旧版本、无沙盒/回归/回滚。剥离方案：外接 PSN 式「近期任务窗验证 + 逆操作回滚」，以及 SSEA 四级验证门。
  5. **C4 缓冲无界**：库无容量上限、无退休。
  6. **C3 记忆/技能未分离**：episodic 层缺失。
- **隐含假设与失效条件**：① 用户必须反复表达约束（生存域里没有「用户」这回事，环境不会用自然语言陈述偏好 → **抽取器在 SSEA 无直接对应物**，须换成对**环境侧重复出现的结构**的检测）；② 假设技能可用自然语言完整表达（非语言域需重做表示）；③ 判定/合并由 LLM 执行，质量随 backbone 强弱漂移，且**无 ground truth 校验**（PSN 有静态检查与环境再验证，本篇没有，§2.6 已注）。
- **算力 / 带宽 / 工程代价**：每轮抽取 + 检索 + 判定是**常驻 LLM 成本**（仅靠「后台异步」掩盖延迟，不减少总算力）；技能全文入 prompt 使上下文随 |H_t| 线性增长（Top-K 有上限但 K 值未给）；向量索引需常驻；对 SSEA 的低算力侧，若用小模型充当抽取器/判定器，论文**未给出**任何弱模型鲁棒性数据（PSN 有 Fig.8 跨模型对比，本篇无）。
- **搬运后的可能退化模式**：
  1. **只合并不退休** → 库单调膨胀、检索噪声上升、阈值 η 逐渐失效（且 η 是常量，无人调）；
  2. **坏合并不可逆** → 一次糟糕的语义并集永久污染技能（无回滚、无历史版本）→ 表现为「技能越改越差且查不出何时变坏」；
  3. **把 Rel 打分搬进来** → 违反 C9 并引入事实上的奖励塑形，表现为「高分技能被反复选中、低分技能永不复用」；
  4. **语言注入** → 快环出现语言依赖，违背 C1/C2，表现为「无语言通道时技能不可用」；
  5. **Common/ 共享** → 后天知识跨代，违背 C8，表现为代际技能库体积逐代累加（正是 C8 要防的膨胀）。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可序列化的交互/事件轨迹、环境侧结果信号、可向量化索引、LLM/embedding 后端 | SSEA 已有 SkillLibrary 雏形与经验流；**缺 RuleCompiler**（抽取器在非语言侧的实例化载体） |
| 直接前身（谱系） | **Voyager** | 本篇 §2.4 p3 明确引用 Voyager 作为「组合式技能库持续探索复用」的代表；AutoSkill 相当于把 Voyager 的**代码技能库换成 SKILL.md 文本技能库**，并把「只加」升级为「加/合/弃」三值——**但丢掉了 Voyager 的环境验证环节** |
| 互补（最紧） | **PSN（Evolving Programmatic Skill Networks）** | 分工极清晰：PSN 给「可执行契约 + REFLECT 沿轨迹定责 + 成熟度门控 + **回滚验证**」；AutoSkill 给「技能卡 schema + 语义并集合并代数 + 版本递增 + 准入三值」。**PSN 缺轻量表示与合并代数，AutoSkill 缺验证与回滚**——二者缺口正好互补 |
| 互补 | **SkillWeaver** | 其「提案→练习→合成→打磨」流水线对应 AutoSkill 的「抽取→判定→合并→复用」；SkillWeaver 的**练习/环境验证**环节正好补 AutoSkill 缺失的**验证权（C6）** |
| 互补 | **SEDM（记忆准入官）** | AutoSkill 的 add/merge/discard 是**技能侧的准入官**；可与 SEDM 的记忆侧准入官共用同一协议骨架「候选 → 近邻检索 → 局部判定 → 自包含打包（SCEC）→ A/B 准入验证」；SEDM 的 A/B 验证补 AutoSkill 的验证洞 |
| 互补 | **Memento / MemRL / A-MEM** | AutoSkill 主张把「记忆文本」提升为「行为单元」；SSEA 应**保留两层而非替换**：Memento/MemRL 的案例层（μ 检索、冻结库迁移、遗忘率 FR）+ AutoSkill 的技能层，技能由累积案例**结晶**而成；A-MEM 的链接拓扑与近邻回写可补 AutoSkill 的「技能间关系」缺失（本篇技能之间**无拓扑**，只有检索相似度） |
| 互补 | **LightMem** | 同为「摄入压缩 + 睡眠期离线巩固」形状；LightMem 给**压缩**，AutoSkill 给**结晶**，可串成一条睡眠期管线 |
| 互补 | **Dream-RSI** | 把 AutoSkill 的合并结果放进**重放模拟器**验证，用离线廉价淘汰替代它缺失的验证权 |
| 互补 | **RAGEN** | AutoSkill「只用 user 侧 query、不用模型自身回复作抽取证据」（§3.1 p4、§3.4.1 p6）是规避 **Echo Trap** 的一条实证线索（论文未用此术语，属**推断**） |
| 替代 / 被替代 | **Voyager 式平铺技能库**、**Reflexion 口头反思** | 用结构化技能更新替代口头反思（Reflexion 于 §2.4 p3 被引用）；若 SSEA 选文本表示路线，AutoSkill 替代平铺库；若选代码契约路线，则被 **PSN** 整体替代 |
| 替代（反向） | **PSN** 在「库膨胀」议题上**优于**本篇 | PSN 实测库规模**平台于 ~20–25**、有 SRR 保持率曲线（86/83/67/50% vs Voyager 57/38/29/0%）；AutoSkill 只有静态计数、无增长曲线、无遗忘指标、无退休 |
| **反面参照** | （本篇自身） | 在「终身学习下的**灾难性遗忘 / 技能库膨胀**」这一 SSEA C8 议题上，AutoSkill 是**负面样本**：论文声称「keeps the repository compact」（§4.1 p8），但**无任何证据**支撑——无库规模随轮次曲线、无容量上限、无已有技能退休机制 |
| 未建卡邻居（待回填） | **SkillRL、OpenSkill** | 本篇**未引用**二者（参考文献 [1]–[44] 全文无）；SSEA 卡片体系中二者**尚无独立卡片**（SkillRL 仅在 PSN 卡片 §6.1 的互补行被点名，OpenSkill 未见）。故本卡**不对二者作实质比较**，仅登记为「技能族待建卡邻居」；待其建卡后按四轴回填：**技能表示 / 准入判据 / 是否有淘汰与容量上限 / 是否跨代** |

### 6.2 推荐组合方案
1. **技能准入官（AutoSkill × SEDM × PSN）——首选**
   - 接口形态：候选 ΔS → **近邻检索 TopM** → **合法性三问**（去掉 Rel 打分与 confidence c）→ **语义并集合并 + 版本递增** → **自包含打包**（借 SEDM 的 SCEC）→ 进 **PSN 式验证门**（近期任务窗 + 逆操作回滚，劣化超阈值即撤）。
   - 组合后新增能力：SSEA 第一次拥有「技能**准入 + 合并 + 可回滚**」的完整闭环；AutoSkill 补表示与合并，SEDM 补打包与准入协议，PSN 补验证与回滚。
   - 新增风险：合并由 LLM 执行时的内容漂移（需静态检查 + 环境再验证兜底，可借 PSN 三层噪声防御清单）。
2. **双环工程参照（AutoSkill × LightMem × Dream-RSI）**
   - 接口形态：前台只读快照 → retrieve → 渲染注入；睡眠期做摄入压缩、抽取结晶、合并、重放验证；每轮预算上界 = 1 次抽取 + TopM 局部判定 + 一次重放窗验证。
   - 新增能力：给「**睡眠期计算预算未定义**」一个可落地的预算设定范式（**推断**）。
3. **表示 A/B（AutoSkill vs PSN vs 现状）——直击未答债务**
   - 三臂在同一技能演化流上对照：现状表示 / AutoSkill 文本结构化卡 / PSN 代码契约；判据见 §8。

### 6.3 本篇在组合中的典型角色
- **技能卡表示与合并代数的供给者** + **前后台双环解耦的工程样例** + **「只有合并没有退休」的反面警示牌**。
- 不是主干（证据弱 + 四项硬冲突），是**零件与对照**。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **4** | 正面命中三条当前缺口：技能表示（未答债务）、`retrieve` 键收窄、慢环准入/预算；双环与 FSL/SEL 同构。**实测**：schema/合并/准入在原文 §3–4 完整给出。**推断**：领域是对话助手而非生存，实际搬运需重做表示，故未给 5 |
| 立场兼容性 | **2** | C1 ✗、C2 ✗、C8 ✗、C9 ✗ 四项硬冲突，C3/C4/C5/C6/C7 五项 ◐。**实测**：冲突点均可回溯到 §3.3.1、§3.1、§3.4.2、abstract/§4.5。四项冲突均需改造，扣分重 |
| 可搬运性 | **4** | schema、合并规则、准入三值、双环形态、TopM 局部判定均为**与领域无关的架构件**，可干净拆出；仓库开源。**推断**：语言绑定需重编译为非语言谓词，抽取器在生存域无对应物 |
| 证据强度 | **2** | **实测**：§5 全为描述性统计（Table 1、Table 2、Fig 2–3）+ 2 个案例 + 附录卡片；**无任何基线对照、无消融、无下游任务指标、无 seed/重复运行、无遗忘或库增长曲线**；版本证据论文自陈为 qualitative。**推断**：主张「库保持紧凑」完全未验证 |
| 组合价值 | **4** | 与 PSN（互补缺口）、SEDM（准入官对称）、SkillWeaver（验证）、Memento/MemRL/A-MEM（双层）、LightMem/Dream-RSI（睡眠期）、Voyager（前身）、RAGEN（Echo Trap）均有具体接口；**推断**：作为「反面样本」本身也有设计复核价值 |
| 落地成本 | **3** | schema + 目录布局 + 双环解耦原型成本低（Markdown + 向量索引即可）；**推断**：但抽取/判定/合并需常驻 LLM 调用，SSEA 低算力侧代价高；非语言侧需重做表示与抽取器；且必须外接验证门才算完整 |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 理由：能拆出**可直接用的零件**（技能卡 schema + 语义并集合并代数 + 准入三值 + 双环解耦 + TopM 局部判定），且正面回应「技能表示够不够」这条未答债务；但 **C1/C2/C8/C9 四项硬冲突**必须改造，且**证据强度仅 2**（无基线、无消融、无下游指标），不足以支撑 A 级「核心借鉴」。
- **优先级：P2**。若实验 3 重设计决定把「文本化结构化技能卡」作为第二表示分支纳入 A/B，则升 **P1**。
- **建议动作**：
  1. 把 SKILL.md schema 抽象为**与载体无关的技能卡规格**（n/d/body/τ/γ/ξ/v + Anti-Patterns），τ triggers 映射为 Gate 的合法性键；作为 `skill_library` 的第二表示分支原型；
  2. 实现 **SkillMerger**：语义并集 + 8 条合并规则 + 版本递增，并**强制记录逆操作**（本篇没有，必须自建）；
  3. 实现**技能准入官**：候选 → TopM 近邻 → **合法性三问**（不打分、不排序）→ 打包 → 四级验证门；与 SEDM 的记忆准入官共用协议骨架；
  4. 抽取证据**只取环境侧信号**，禁止用 agent 自身输出作监督（写入 ExperienceCompiler 的纪律）；
  5. 采用 `Users/` vs `Common/` 的目录二分，但**按 C8 反转语义**：Common/ = 结构先验（GenePackage），Users/ = 个体后天技能、不跨代；
  6. **不要**搬运 Rel 打分、confidence c、LLM judge 的评分性用法；η/λ/α 若引入，必须做成**慢环可调**（债务 22 的反面教训）。
- **最小验证实验（技能表示 A/B + 库膨胀探针，服务实验 3 重设计）**：
  - **三臂 / 消融**：同一技能演化流上，A=现状表示（平铺）／B=AutoSkill 文本结构化卡 + 语义并集合并／C=PSN 代码契约 + 回滚验证；再加 **B′=B 去掉退休机制**（即本篇原样）作为膨胀对照；≥8 seed。
  - **判据（分档，先看分母）**：
    1. **机制计数**：候选抽取数、add/merge/discard 三值分布、**merge 率**（精炼率）、版本递增分布、合并规则违反计数、Gate 命中/拒绝数；
    2. **行为差**：技能复用率、逐任务动作序列与基线的差异、技能触发命中率；
    3. **淘汰结果（模型外，环境侧）**：任务成功率/生存时长；
    4. **膨胀与遗忘探针（本篇缺失，SSEA 必须补）**：|B| 随任务数增长曲线（是否平台化）、**陈旧技能重触发保持率**（N 轮后重新触发早期技能，测是否遗忘）、容量上限触发次数。
  - **预期与证伪**：预期 B/C 的 merge 率显著高于 A、|B| 增速更慢；C 因有回滚而保持率最高。**证伪条件**：若 B′（无退休）的 |B| 呈单调增长且无平台、且下游成功率无增益，则证明「只合并防重复」不足以对抗膨胀，**必须为 SSEA 自建退休/淘汰函数与容量上限**（即本篇只能作对照，不能作方案）。
- **若 E 不采用**：不适用（本篇有可拆零件，非 E）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. 候选的 **confidence c** 究竟用在哪？论文仅在 §3.4.1 p6 的候选 schema 中出现，后续 Rel_m、judge、合并规则均未使用——是否有阈值门？需核对仓库实现。
  2. **λ、α、η、Top-K、TopM 的具体取值全文未给出**（§3.3.1 p5、§3.4.2 p7），不可复现；它们是常量还是可调？可否由慢环调节？
  3. **版本递增是否保留历史版本正文？** 若只覆盖，则坏合并不可逆——需确认 SkillBank 是否存历史版本。
  4. **已有技能的退休 / 归档 / 容量上限是否存在？** 全文未提及；是否有后续版本补充？
  5. 跨 user/agent 共享（`Common/`）时如何做冲突消解与污染隔离？未提及。
- **需补查的文献或资料**：
  6. 同组前作 **ELL / StuLife**（arXiv:2508.19005，参考文献 [22]）——AutoSkill 只在其基准上定位自己、未在其上评测；StuLife 是否提供「长程遗忘/库膨胀」指标可供借用？
  7. **SkillRL、OpenSkill** 与 AutoSkill 的实际差异（表示 / 准入判据 / 淘汰与容量上限 / 是否跨代）——二者在 SSEA 卡片体系中**尚未建卡**，待建卡后回填本卡 §6.1。
  8. 是否有技术报告/后续版本给出下游任务增益与消融（§5 目前只有描述性统计）。
- **需人工核对的公式 / 实现**：
  9. §3.4.2 的 `N_t = TopM(B^u_t; Rel_m(z_t,s))` 与 `s*_t = argmax` 的**实际 M 取值**与「邻居为空时」的行为（此时是否直接 add？论文未明说）。
  10. 非语言（SSEA）环境下，SKILL.md 的 **p 字段应编译为何种结构**（谓词集合 / 程序 / 参数化策略）、**τ triggers 如何变成可判定的结构化键**——这是搬运成败的关键，需原型验证。
  11. Fig 2 / Fig 3 的数值为本人按图读数，建议对照原图复核（Table 1 / Table 2 为正文表格数值，可直接引用）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| “AutoSkill abstracts skills from user experience, supports their continual self-evolution, and dynamically injects relevant skills into future requests without retraining the underlying model… a standardized skill representation for sharing and transfer across agents, users, and tasks.” | p1（abstract） |
| “treat repeated interaction experience not merely as memory, but as a source of skill formation… crystallizes them into explicit skill artifacts” | p2（§1） |
| 既有三路线缺陷：参数更新「costly or difficult to control」；记忆路线「treat past interaction as text to be retrieved rather than behavior to be operationalized」；技能路线「skills remain implicit in prompts, trajectories, or policies」 | p1、p3（§1、§2.4） |
| 技能表示 s=(n,d,p,τ,γ,ξ,v)：name / description / executable instruction prompt / trigger set / tag set / example set / version | p4（§3.1） |
| “the skill extraction stage only uses user queries rather than model responses… it learns from {q1,…,qt} but does not use r_t as extraction evidence” | p4（§3.1） |
| 五模块提示集 P={P_rw, P_chat, P_ext, P_judge, P_merge} + M_emb；「modular inference-time composition」 | p4（§3.2） |
| 混合检索：Rel(q_t,s)=λ·d̂(q_t,s)+(1−λ)·b̂(q_t,s)，归一化后加权；H_t={s∈TopK(B^u_t) \| Rel≥η} | p5（§3.3.1） |
| 抽取原则：“Extract only when there are durable, reusable constraints, policies, workflows, or templates… Do not extract one-shot requests… Remove case-specific entities and preserve only portable rules. Do not invent workflow steps unless the user explicitly specified them.” | p6（§3.4.1） |
| 候选 z_t=(n,d,p,τ,γ,ξ,c)，**c 为 confidence score**；输出 schema {"skills": [...]} | p6（§3.4.1） |
| 管理期检索：Rel_m(z_t,s)=α·d̂+(1−α)·b̂；N_t=TopM；s*_t=argmax；a_t=M_judge(P_judge,z_t,s*_t)∈{add,merge,discard} | p7（§3.4.2） |
| P_judge 判定流程：① 话题连续性与能力族 ② **discard gate**（拒绝 generic / low-signal / non-portable / library-covered）③ 四轴比较（job-to-be-done、deliverable type、hard constraints & success criteria、required tools/workflow）④ merge 仅当「same capability after removing instance details」⑤ add 仅当「distinct durable capability」 | p7（§3.4.2） |
| 合并与库更新：v(s'_t)=Bump(v(s*_t))；B^{t+1}=B∪{z}（add）/ (B\{s*})∪{s'}（merge）/ B（discard） | p7（§3.4.3） |
| 合并规则：“Preserve the original capability identity. Perform **semantic union rather than raw concatenation**. Import only reusable, non-conflicting additions… Do not carry over stale or unrelated topic constraints… Do not invent any new standards or details… Deduplicate sections, bullets, triggers, tags, and examples.” | p8（§3.4.3） |
| “no model parameters are optimized throughout this process… a training-free, prompt-driven, explicit-skill lifelong learning framework” | p8（§3.5） |
| 设计原则三条：Explicit skill representation / **Continuous but controlled evolution**（“keeps the repository compact”）/ Low-friction deployment | p8（§4.1） |
| 四阶段生命周期：Experience ingestion → Skill extraction → Skill maintenance and versioning → Skill reuse；“evolves by **refinement** rather than **duplication**” | p9（§4.3） |
| 前台 retrieve-then-generate 为关键路径，抽取与维护“concurrently as asynchronous background operations” | p9–10（§4.4） |
| 存储布局：`SkillBank/Users/<user_id>/<skill-slug>/SKILL.md`（+ scripts/ references/ assets/）、`SkillBank/Common/`（共享）、`SkillBank/vectors/`（*.meta.json / *.ids.txt / *.vecs.f32） | p10（§4.5） |
| 三种接口：Python SDK（ingest / search / render_context）、Web UI、OpenAI 兼容反向代理（/v1/chat/completions 等）；支持离线冷启动灌库 | p9–10（§4.2、§4.6） |
| Table 1：四子集规模（5912/134670/22.78/400；10243/267681/26.13/631；1145/36834/32.17/224；5211/157508/30.23/603）；筛选 >8 轮对话 | p11（§5.1–5.2） |
| Table 2 高频标签：python 98、javascript 38、excel 36、c++ 35、creative writing 35、formatting 35、pandas 30… | p11（§5.2） |
| Fig 2 类别分布（N=1858）：Programming & Software Dev 482、Writing & Content Creation 363、Data & AI/ML 354、General/Mixed 356、Systems/DevOps/Config 194、Research & Education 72、Operations & Marketing 23、Other Domain-Specific 14 | p12（§5.2） |
| Fig 3 平台提及：Twitter/X 27、Instagram 24、YouTube 13、Douyin/TikTok 6、WeChat OA 4、LinkedIn 4、Xiaohongshu 3、Weibo 1 | p12（§5.2） |
| 版本证据：`professional_text_rewrite` **v0.1.34**（论文解读为 34 轮增量优化）vs `顶级心理咨询师` **v0.1.0**；论文自陈此为 “qualitative evidence” | p13（§5.3） |
| 案例卡片字段实样：Role & Objective / Communication & Style Preferences / Operational Rules & Constraints / **Anti-Patterns** / Interaction Workflow / Core Workflow / Output Format | p13–15、p19–22 |
| §6 结论与未来工作：**未列 limitations**；仅有贡献总结与「personal digital surrogates」方向 | p15（§6） |
