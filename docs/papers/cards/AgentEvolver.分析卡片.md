# 论文分析卡片 · AgentEvolver

## 0. 卡片头（速览）

| 项 | 内容 |
|---|---|
| 文件名 | `2025-11-13 AgentEvolver Towards Efficient Self-Evolving Agent System.pdf` |
| 标题 | **AgentEvolver: Towards Efficient Self-Evolving Agent System** |
| 作者 / 机构 | Yunpeng Zhai\*, Shuchang Tao\*, Cheng Chen\*, Anni Zou\*, Ziqian Chen\*, Qingxu Fu\*, Shinji Mai\*, Li Yu, Jiaji Deng, Zouying Cao, Zhaoyang Liu†, Bolin Ding†, Jingren Zhou；Tongyi Lab, Alibaba Group（\*等贡献，†通讯） |
| 发表时间 / 出处 | arXiv:2511.10395v1 [cs.LG]，2025-11-13；预印本技术报告，29 页 |
| 论文链接 | arXiv:2511.10395 |
| 代码链接 | https://github.com/modelscope/AgentEvolver（p1）；经验构建/检索子模块另见 https://github.com/agentscope-ai/ReMe（p9 脚注） |
| 标签 | 自演化智能体 · 自问（任务生成）· 自导航（经验复用）· 自归因（细粒度信用分配）· GRPO/PPO · LLM-as-Judge · 上下文管理（LCT/TSR）· AppWorld/BFCL v3 |
| **应用裁决** | **B 零件采用**（采用三段式闭环**形状**、经验条目 schema、experience stripping、上下文管理模板、reference-replay 合法性门、以及一套**成本标尺**；**不采用**其多层外部奖励框架与 LLM 策略本体） |
| 优先级 | **P1**（慢环「前瞻预演/回顾编译」两通路对位的形状来源 + 睡眠期预算的成本标尺 + 记忆门选择性形状） |
| 评估日期 / 评估人 | 2026-09-28 / WorkBuddy |

---

## 1. 一句话定位

- **论文主张**：针对「手工造任务昂贵、RL 探索低效、样本利用率低」三瓶颈，提出 **AgentEvolver**——把训练主动权从人工流水线交给 LLM 自己，用三个协同机制构成自演化闭环：**self-questioning**（好奇心驱动自主出题）、**self-navigating**（经验复用 + 混合策略引导提高探索效率）、**self-attributing**（按贡献给轨迹各步分配差异化奖励提高样本效率）；在 AppWorld 与 BFCL v3 上，7B/14B 模型即超过参数大得多的基线（Fig.1, p1；Table 1, p19）。
- **对 SSEA 的意义**：它把 SSEA 慢环**「前瞻预演 + 回顾编译」两条通路**用一条可运行的三段式闭环具象化（出题≈前瞻、经验编译≈回顾、归因≈Δ 生成的信用分配），并罕见地给出**一组可作成本标尺的具体数字**（8×A100、batch 32、40 epochs/update、**100 条合成样本即达 40.3%**、Steps@.9 降 55%/67%），直接回应 SSEA「睡眠期计算预算未定义」这条硬门槛；同时它的 α 消融**反证了 C9**——过度依赖 LLM judge 的启发式标签会长期退化（p26）。

---

## 2. 问题 — 机制 — 证据

### 2.1 论文要解决的问题
- **问题本身**（p1–2）：LLM 智能体在**新环境**中的 RL 训练代价过高——(i) 为 RL 定制训练任务**极其昂贵**（工具功能未知、造多样化轨迹是重体力活）；(ii) 既有 RL 方法**样本效率极低**（长视野 + 工具增强使每次 rollout 都昂贵，intrinsic reward / UCB 之类探索技巧在长视野智能体上失效），主流仍是 PPO/GRPO 式「近似暴力探索 + 大量冗余 rollout」（p2）。
- **它指出的既有方案缺陷**：workflow 编排靠人写动作序列/工具规则，泛化差；学习式优化里 RL 是核心方向，但**任务供给与探索效率**两处卡死（p2）。
- **形式化立场**（p3）：把问题拆成 (1) **interaction sandbox** `E=(S,A,P)`——只有状态/动作/转移，**没有奖励 r、没有折扣 γ**（Eq.1）；(2) 未知的**目标任务分布** `p_target(g)`。核心挑战是让智能体在无奖励沙盒里开放式探索、自己估计 `p_target`，并**自造代理任务与代理奖励**（`Ftask:E→Δ(G)`，Eq.4；`Freward:E×G→(S×A→R)`，Eq.5；目标 `Jtrain`，Eq.6–7，p3–4）。

### 2.2 核心思想（关键 insight）
1. **把「出题 / 导航 / 归因」三段都交给 LLM 自己驱动**，形成 `环境→任务→轨迹→策略` 的闭环（Fig.2, p3）：self-questioning 造任务、self-navigating 造好轨迹、self-attributing 造密奖励——分别打掉任务稀缺、探索低效、样本浪费三个瓶颈（p2）。
2. **探索先于出题、参考答案当代理真值**（p7）：先探索得到轨迹，再由轨迹反推 query 与 **reference solution**；因问题是在探索之后生成的，答案「必在能力之外但已被探索发现」，故可作 proxy ground-truth 用于**可行性重放**与判分（p7）。
3. **注入的文本经验不应进入梯度**（experience stripping，p10–11）：经验只用来「引导 rollout」，算 policy loss 前把经验 token **剥掉**，让奖励只归因于模型自身的推理轨迹——即「语言经验做探索提示，不做学习信号」。
4. **两路奖励分开标准化再融合**（p13–14）：把过程质量（LLM 归因 GOOD/BAD）与结果有效性（终局 reward）**各自独立标准化**后加权融合（`r̂_t=α·r̂_attr+1_{t=T}·r̂_out`，Eq.20），避免一路尺度压倒另一路。
5. **对 LLM judge 启发式标签过度依赖会长期退化**（α 消融，p26）：α=0.30 早期快、末期掉到 43%（低于所有设置），α∈[0.10,0.20] 收敛约 59%（基线 55%）；论文自陈原因是"overfitting to the LLM judge's heuristic labels rather than true task objectives"。

### 2.3 关键机制 / 算法（可独立搬运的「零件」清单）
| 零件 | 输入 → 输出 | 作用 | 出处（节/式/图） |
|---|---|---|---|
| **无奖励交互沙盒** `E=(S,A,P)` | 环境 → 去奖励 MDP | 把「自造奖励」显式化 | Eq.1, p3 |
| **Environment Profile**（实体/属性/操作） | 环境 → 动作先验文本 | 探索时作初始状态 `s0` 的一部分，避免乱走 | §3.1, Fig.4, p5–6 |
| **两阶段探索**（广度 Nb → 深度 Nd，深度阶段只回看最近 Nd 步） | 高温策略 → 探索轨迹 τ | 覆盖 + 防早熟收敛 | Eq.8–9, p6；参数见 p19 |
| **自适应任务合成 Ψ** | 轨迹 × 用户偏好 → 任务 g | 难度/风格可控出题 | Eq.10, p7 |
| **参考答案抽取** | 简化轨迹 + 任务 → reference solution | 造代理真值 | §3.2, p7 |
| **多层任务过滤** | 候选任务 → 去重/可行任务 | 词面去重 + 语义去重 + **重放可行性**验证 | §3.3, p7 |
| **分布混合** `p_hybrid=(1−λ)p_target+λp_task` | 真/合成任务 → 混合分布 | 有真数据时保稳扩界 | Eq.12, p7 |
| **LLM Judge（Qwen3-235B-A22B）** | 轨迹 + 参考答案 → 分数 | 相关性/重复检查 + 连续打分 + 参考步骤覆盖校验 | §3.4, p8 |
| **经验条目**（When to use + Content） | 轨迹 → 自然语言经验 | 可检索、可解释的复用单元 | Fig.5, p8 |
| **经验池构建 + 检索**（余弦相似 + 重排/重写，TopK） | 任务 → 经验集 `EXP(g)` | 冷启动经验供给 | Eq.13–14, p9–10 |
| **经验混合 rollout**（η 比例：vanilla + 经验引导） | 任务 → 两类轨迹 T⁽ᵛ⁾∪T⁽ᵉ⁾ | 平衡探索/利用 | Eq.15–16, p10 |
| **Experience Stripping** | 经验引导样本 → 剥掉经验 token 的训练样本 | 防记忆外部文本、奖励只归因自身轨迹 | Fig.7, p11 |
| **Selective Boosting** | 正优势样本 → 放宽上裁剪界 `ε̂_high` | 救回被过度裁剪的经验引导梯度 | Eq.17, p11 |
| **逐步归因**（GOOD→+1 / BAD→−1） | 整条轨迹 → 每步 ±1 标签 | LLM 一次性整体判每步贡献 | §5.1–5.2, p11–12 |
| **轨迹级标准化** | 每步归因 → 标准化 `r̂_attr` | 让每条轨迹等权、防长轨迹主导统计 | Eq.18, p13 |
| **复合奖励 + 优势** | 双通道 → `r̂_t`、`A_t=Σ_{k=t}^T r̂_k` | 步级信用分配（γ=1） | Eq.20–21, p14 |
| **Context Manager（LCT + TSR）** | 多轮消息流 → 可变工作上下文 + 不可变快照 | 统一因果/非因果 rollout | §6.2, p16–17 |
| **四种上下文管理模板（CMT）** | LCT → 四种演化策略 | Basic Causal / Reasoning-Augmented / Sliding Window / **Self-Context-Managing** | Fig.11, p16–17 |
| **Gym 兼容环境服务 + Ray actor** | 环境 → 远程并发隔离实例 | 高并发、轻量隔离 | §6.3, p17–18 |

### 2.4 关键表示与数据结构
- **经验条目**：自然语言，两字段 `{When to use, Content}`；`When to use` 作检索触发（向量化嵌入匹配），`Content` 给策略/注意点（Fig.5, p8）。
- **上下文双结构**：`Live Context Timeline (LCT)`（可变工作上下文=短期可编辑记忆）+ `Timeline Snapshot Recorder (TSR)`（每次动作时冻结的不可变 token 级快照）；rollout 后 TSR 自动**时间线合并**（去冗余子序列、对齐重叠段的 loss mask）（p16–17）。
- **自管理操作集**：`a_context ∈ {α_keep, α_remove, α_compress}`——由策略 LLM 对每条消息选择保留/删除/压缩（p17）。
- **轨迹**：`τ=(s0,a0,…,sT)`；训练时轨迹**最多截断到 30 步**（p18）。
- **训练配置**：Qwen2.5-7B/14B-Instruct 作策略；GRPO 式；lr 1e-6、batch 32、**每轮策略更新 40 epochs**、KL 系数 0.001；**8×NVIDIA A100(80GB)**（p18）。
- **关键超参**：探索 `Nb=3, Nd=17`(AppWorld)/`Nd=27`(BFCL)，探索智能体 Qwen-Plus，温度 1；词面去重阈值 0.8；混合数据下 `p_train` 优势乘 0.5 衰减；`Npc=4`、`TopK k=5`、`η=0.5`、`ε_low=ε_high=0.28`、`ε̂_high=0.6`、`α` 默认 0.1（最优 [0.10,0.20]）、`β=1`（p18–19、p23、p26）。

### 2.5 实验证据
**基准**：AppWorld（TGC，官方定义）+ BFCL v3（**仅 multi-turn split**，官方多轮评测；force-terminated 记错）；指标 avg@8 / best@8（每实例 8 次独立 rollout）；轨迹截断 30 步（p18）。

| 任务 / 基准 | 对照基线 | 关键数字 | 统计口径 |
|---|---|---|---|
| AppWorld + BFCL v3 总评（Table 1, p19） | Qwen2.5-7B 基线 / Vanilla GRPO | 7B：avg@8 15.8%→**45.2%**（+29.4）；14B：29.8%→**57.6%**（+27.8）；best@8 7B +36.1 / 14B +30.3 | avg@8 / best@8，n=8 rollout/实例 |
| 分模块消融（Table 1, p19–20） | baseline → +Q → +Q&N → +Q&A → overall | 14B avg@8：29.8→52.3→54.1→56.4→**57.6**；**+Questioning 贡献最大**（7B 15.8→36.1） | 同上 |
| 合成 vs 原始 vs 混合（Table 2, p20） | 目标分布 `p_target` / 零样本 | 7B avg：zero-shot 15.8 / 原始 37.5 / 合成 36.1 / **混合 43.6**；14B：29.8 / 57.4 / 52.3 / **60.7** | avg@8 / best@8 |
| 数据量（Fig.12a, p21） | 100 / 200 / 500 条 | **100 条即 40.3%**；200→42.7；500→44.3（增益递减） | avg@8 |
| Judge 消融（Fig.12b, p21） | naive judge / +principle / +reference(ours) | 22.5 → 33.1 → **44.3**（**参考答案贡献最大**） | avg@8 |
| 跨域迁移（Table 3, p21） | AppWorld↔BFCL 交叉评 | 14B AppWorld→BFCL 仅掉 4.3% | avg@8 / best@8 |
| 自导航消融（Table 4, p22） | baseline / Navigating(w/o select) / ours | 14B avg@4：57.2 → 56.7（**去掉 selective boosting 掉到基线之下**）→ **65.0**（+7.9） | avg@4 / best@4，Qwen2.5-14B |
| 显式 vs 隐式经验（§7.4.2, p23） | ICL-only / 隐式(RL 内化) | 隐式比 ICL-only 高 **↑34.2% avg@4**，比 vanilla RL 高 ↑7.9% avg@4 | avg@4 |
| 自归因消融（Table 5, p24） | Qwen2.5 / w/o r_attr / w/o r_out / Attributing | 7B avg@8：16.4 / 41.3 / 35.7 / **47.6**；14B：29.8 / 57.4 / 53.0 / **62.0** | avg@8 / best@8，dev set |
| **样本效率（Table 6, p25）** | baseline | Steps@.9：AppWorld **40 vs 90（−55%）**；BFCL **20 vs 60（−67%）**；AUC 46.26 vs 41.03 / 61.02 vs 55.78 | Qwen2.5-14B |
| α 权衡（Fig.16, p26） | α∈{0.05,0.10,0.20,0.30} | α=0.30 早期 20 步达 45% 但末期掉到 43%（低于全部）；α∈[0.10,0.20] 收敛≈59%（基线 55%） | AppWorld，14B |
| ε̂_high 权衡（Fig.14, p23） | {0.4,0.6,0.8,1.0} | **0.6 最佳**：兼顾前期速度与长期稳健 | 训练 80 步 |
| 经验比例 η（Fig.13b, p23） | η 变化 | 高 η 利于推理即时表现，但训练长期被探索抑制；**η=0.5 最平衡** | — |
| 上下文模板 CMT（Table 7, p26） | 四种模板 | **SCMT 最优**：TGC@8 **0.720**、SGC@8 0.607；RAT 0.690；SWT 0.601；BCT 0.506 | Qwen3-14B，AppWorld |

### 2.6 论文自陈局限与边界条件
- **无独立的 Limitations 节**（全文仅在 §8 给出 "Next Steps"，p26–27）；摘要自陈为 **"Preliminary experiments"**（p1）。
- **边界条件**：仅两个工具增强基准（AppWorld、BFCL v3），未覆盖真实企业/安全关键长视野任务（§8 列为未来方向，p27）；未报告多 seed 方差（仅 avg@8/best@8 口径，p18）。
- **依赖 LLM Judge**：合成任务奖励完全依赖 LLM judge（Qwen3-235B-A22B 判任务、Qwen-Max 判归因，p19），作者未做「无 judge」消融。
- **规模**：主实验仅 Qwen2.5-7B/14B，更大模型「是否 scale」列为未来问题（§8, p27）；**未报告挂钟时间 / FLOPs / GPU-hours 等绝对成本**（仅相对样本效率）。
- **未来方向**（p27）：挑战型应用、扩展到更大模型并研究 **compute–data trade-off 与 cost-aware curriculum**、以及 **LLM-level self-evolving**（单模型内统一出题/导航/归因/推理）。

---

## 3. SSEA 立场对齐（核心维度）

### 3.1 C1–C10 映射
| 裁判标准 | 判定 | 依据（论文中的具体机制/数字） | 若冲突：改造方向 |
|---|---|---|---|
| **C1** 生存控制架构，非语言生成 | ✗ | 策略本体即 LLM（Qwen2.5-7B/14B），动作=工具调用/语言输出（p4、p18）；但 `E=(S,A,P)` 无奖励沙盒形式化（Eq.1, p3）是干净的结构抽象 | 只借「无奖励沙盒 + 自造任务/奖励」的**问题形式化**；控制对象换生存行为，策略换非语言网络 |
| **C2** 自然语言只作观察员接口 | ✗（有部分盟友） | 语言是载体：经验=自然语言条目（Fig.5, p8）、推理 token 入环、上下文管理由 LLM 决定（p17） | **experience stripping**（Fig.7, p11）可作「语言只做 rollout 提示、不进梯度」的现成协议模板；SSEA 侧把该协议推广为「语言只进日志面」 |
| **C3** 权重/记忆/技能三分离 | ◐ | **记忆与权重已分离**（经验池外置 vs GRPO 更新权重，p10、p14）；但**技能未独立**（经验条目兼作技能/策略），且权重被更新 | 权重更新限定白名单小网络（与 RAGEN 同）；把「经验条目」拆成记忆（经历）与技能（可执行契约，参见 PSN）两置 |
| **C4** 低算力低带宽 | ✗ | **8×A100(80GB)**、每轮策略更新 **40 epochs**、LLM judge 用 235B 模型、探索用高温度大模型（p18–19）；但**数据侧极省**（100 条样本→40.3%，p21） | 训练只在离线慢环/研究者侧；judge 与探索用大模型绝不进快环；把「100 样本够用」当数据预算标尺 |
| **C5** 精准回忆历史 | ◐ | 经验池外置、可检索（余弦 + 重排/重写，Eq.14）、有 LLM 校验（p9）；但经验是**抽象原则**而非具体经历，无显式**遗忘/合并/精准写入** | 借其「When to use 作检索键」的检索设计（对应 SSEA `retrieve` 键收窄问题）；补遗忘/合并（对照 MemRL 的 FR、A-MEM 的链接拓扑） |
| **C6** 可自主修改自身 | ◐ | 自生成任务 + 自归因驱动策略更新（自演化），但**不改代码**、无「四权」拆分（提案/边界/验证/应用） | 映射为参数侧 Δθ 的受控更新；把 reference-replay 可行性门当「验证权」零件 |
| **C7** 可保存/恢复/变异/继承 | ✗ | 无 GenePackage、无变异/继承；检查点隐含未提（p14、§8） | 不做架构级参照；仅「经验池可跨任务复用」（p9）作记忆继承的弱形态 |
| **C8** 给基因先验，不给知识语料 | ✗（环境画像可作结构先验） | 合成任务的「知识」来自 LLM 预训练 + LLM judge，非结构性先验；**Environment Profile（实体/属性/操作）**（Fig.4, p6）是唯一的**结构先验**形态 | 把 environment profile 当作「基因级结构先验」的候选表示；知识语料不进 GenePackage |
| **C9** 不设评分函数，只有淘汰函数 | **✗（但反向佐证强）** | 显式多层外部评分：LLM judge 打分 + 结果 reward + 归因 reward（±1）+ advantage + GRPO（Eq.18–21, p13–14）；**但 α 消融实证「过度依赖 judge 启发式标签→长期退化」**（p26），且 **reference-replay 只判可行性=只判合法性**（§3.3, p7） | 只保留 **reference-solution 可行性重放**（合法性门，不打分不排序，对齐 SSEA 四级验证门）；删除全部打分/奖励通道；α 消融作 C9 的引用证据 |
| **C10** 创新在 L2/L3/L4，不在 L1 算子 | ✓ | 创新全在闭环形状（L2）、经验内化/信用分配（L3）；算子用现成 GRPO/PPO/veRL，无新算子（p11、p14） | — |

### 3.2 L1–L4 层级定位
| 层次 | 论文在该层提供了什么 | 对 SSEA 的价值 |
|---|---|---|
| **L1 算子层**（基础网络模块） | 无新算子，直接用 Qwen2.5 + GRPO + veRL | 符合「L1 借用」立场 |
| **L2 信息流层**（模块如何连接） | 三段式闭环（出题→导航→归因）、经验混合 rollout、LCT/TSR 上下文双结构、四种 CMT | **高**：慢环两通路的形状模板 + 快照时间线设计 |
| **L3 学习层**（如何更新自身） | experience stripping、selective boosting、双通道分别标准化、步级信用分配 | **中高**：经验内化与稳定性零件（但奖励通道须剥离） |
| **L4 演化层**（保存/继承/变异） | 无（经验池跨任务复用是唯一弱形态） | 低 |

### 3.3 模块映射
| 论文构件 | SSEA 落点（现有模块 / 缺失组件 / 新增建议） |
|---|---|
| self-questioning（出题 + reference solution） | 慢环**前瞻预演**通路；新增「任务/假设生成器」，Environment Profile 作结构先验 |
| self-navigating（经验池 + 检索） | 慢环**回顾编译**通路 + 记忆侧；「When to use + Content」schema 落记忆条目 |
| experience stripping | 记忆→快环注入面协议：**注入提示不进学习信号**（C2 的执行细则） |
| reference-solution 可行性重放 | 四级验证门的**沙盒层**（只判合法性，不打分）——对应 SSEA 验证门纪律 |
| Self-Context-Managing 模板（keep/remove/compress） | **记忆二级门选择性**（债务 22 + 「门开得准不准」）：把常量阈值换成三操作决策 |
| LCT / TSR 双结构 | 快环不可变快照 + 慢环时间线合并的工程参照 |
| Steps@.9 / AUC / 100 样本→40.3% | **睡眠期计算预算的成本标尺**（数据量、收敛步数、硬件口径） |
| LLM judge / 归因 reward / α | **不落点**（C9 冲突件）；仅 α 消融作反证证据引用 |

### 3.4 债务与验收实验对应
- **睡眠期计算预算未定义**（前瞻预演硬门槛）：本篇给出**成本标尺**——数据侧「100 条合成样本即 40.3%」、收敛侧「Steps@.9 降 55%/67%」、硬件侧「8×A100 80GB、batch 32、40 epochs/update、30 步截断」（p18–21、p25）。**未给**绝对挂钟/FLOPs 与睡眠期式预算，仍属「相对标尺」。
- **债务 22（记忆二级门常量阈值，慢环不可调）**：Self-Context-Managing 模板的 `{keep, remove, compress}` 三操作决策可作慢环可调门的形状来源（p17）——但需去 LLM 化。
- **记忆门「开得准不准」选择性缺失**：judge 的「相关性/重复检查：无关或幻觉步**立即零分**」是一种**准入式**（非打分）过滤形状（§3.4, p8）。
- **债务 25/26/27/28（判据形状错）**：分阶段消融（baseline→+Q→+Q&N→+Q&A→overall，Table 1）是「逐步归因、先看分母」的判据形状；Steps@.9/AUC 是效率判据模板（p19、p25）。
- **未回应**：Gene Manager 缺失、DeathHook 未接、`rules` 零消费者、技能表示够不够（其经验≠可执行技能）。

---

## 4. 可借鉴资产清单

| # | 资产 | 类型 | 搬运方式 | 落点模块 | 预期解决的问题 | 置信度 |
|---|---|---|---|---|---|---|
| 1 | **三段式闭环形状**（出题→导航→归因） | 思想 | 仅借思想 | 慢环两通路对位（前瞻预演 + 回顾编译） | 慢环结构缺一张总图 | 高 |
| 2 | **成本标尺**（8×A100、batch 32、40 epochs/update、100 样本→40.3%、Steps@.9 −55%/−67%、30 步截断） | 证据/标尺 | 直接引用 | 睡眠期计算预算标定 | 睡眠期预算未定义 | 高 |
| 3 | **Experience Stripping**（算梯度前剥掉经验 token） | 协议 | 改造移植 | 语言→控制环的注入面协议 | C2「语言不进控制闭环」的执行细则 | 高 |
| 4 | **Reference-solution 可行性重放** | 协议 | 改造移植 | 四级验证门·沙盒层 | 验证门「只判合法性不打分」的现成实现 | 高 |
| 5 | **「When to use + Content」经验条目 schema** | 表示 | 改造移植 | 记忆条目 / 检索键 | `retrieve` 键收窄、召回精度上限低 | 高 |
| 6 | **Self-Context-Managing 三操作（keep/remove/compress）** | 协议 | 改造移植 | 记忆二级门选择性 | 债务 22 + 门「开得准不准」 | 高 |
| 7 | **LCT/TSR 双结构 + 时间线合并** | 表示 | 改造移植 | 快照不可变 + 慢环时间线合并 | 快照/回滚工程参照 | 中 |
| 8 | **双通道分别标准化再融合**（Eq.18–19） | 算法/统计 | 仅借思想（作统计卫生，不作奖励） | Δ 提案的度量归一 | 多信号尺度互压 | 中 |
| 9 | **α 消融：过度依赖 judge 标签→长期退化** | 证据 | 直接引用 | C9 论证 | 为「不设评分函数」提供实证 | 高 |
| 10 | **Environment Profile（实体/属性/操作）** | 表示 | 改造移植 | 基因级结构先验 | C8 的「结构先验」表示候选 | 中 |
| 11 | **Selective Boosting**（正优势样本放宽上裁剪界） | 算法 | 仅作对照（参数侧启用时） | 未来 Δθ 训练 | off-policy 引导样本的梯度救回 | 中 |
| 12 | **Judge 消融：naive 22.5 < principle 33.1 < reference 44.3** | 证据 | 直接引用 | 验证门设计 | 客观锚点比评委启发式更重要 | 高 |

---

## 5. 冲突、代价与风险

- **与硬约束的冲突**（对应 3.1 中 ✗/◐）：
  1. **C9（最重）**：多层外部评分（judge + 结果 + 归因 + advantage + GRPO）。但本篇是**少见的「自我反证」案例**——α 消融直接说明「依赖 judge 启发式标签会退化」，且 reference-replay 可行性门本质是**合法性检查**，与 SSEA 验证门同形。改造：只留可行性门，删全部打分。
  2. **C2**：语言是载体。改造：借 experience stripping 的「提示不进梯度」协议，但 SSEA 控制环须非语言。
  3. **C3**：权重被更新。改造：仅白名单小网络；记忆/技能必须再拆。
  4. **C4**：8×A100 + 235B judge。改造：只在离线慢环；judge 不进快环。
  5. **C1/C7/C8**：LLM 策略、无基因包、知识来自预训练。改造：仅借形式化与结构先验。
- **隐含假设与失效条件**：整套闭环**假设有一个可执行沙盒 + 可靠 judge**；无奖励沙盒形式化（Eq.1）虽漂亮，但落地靠 judge 补奖励——judge 一旦不可靠，闭环失效（论文未做无 judge 消融）。
- **算力 / 带宽 / 工程代价**：训练侧 8×A100 级；探索/judge 每次调用大模型（Qwen-Plus / Qwen3-235B-A22B / Qwen-Max）——这是**训练期**成本；SSEA 若要搬，必须全部留在离线慢环，且需另造无 judge 的替代。
- **搬运后的可能退化模式**：
  1. 若照搬 judge，会重现**奖励放大→长期退化**（α 消融已示警，与 RAGEN 的 Echo Trap 同族）；
  2. 若照搬「经验=自然语言技能」，会破坏 C3 三分离与 C2，且经验条目**不可执行**，无法过沙盒门；
  3. 「efficient」是**相对**主张（对基线），无绝对成本数字，误当作绝对效率证据会高估收益。

---

## 6. 组合分析

### 6.1 关系图谱
| 关系 | 对象（点名论文或方法族） | 说明 |
|---|---|---|
| 前置依赖 | 可执行沙盒 + 环境画像 + 判分/可行性门 | SSEA 已有环境与四级验证门骨架 |
| 互补（最紧） | **FLEX** | 同为「经验库」组织/写入/检索侧主干；FLEX 冻结权重、AgentEvolver 更新权重。**关键分歧**：AgentEvolver 的 Table 4 实证「隐式内化（RL）> 显式 ICL-only（↑34.2% avg@4）」，直指纯 ICL 经验库有天花板——SSEA 须回答「记忆能否只靠 ICL 承载改进」 |
| 互补 | **EvolveR** | 几乎同形（在线交互→离线自蒸馏→GRPO）；EvolveR 有库治理四件套（去重/合并/计分/剪枝），AgentEvolver 有 experience stripping + selective boosting——两者互为缺口。**反向**：EvolveR 实证「经验吸收进权重反而退化」，AgentEvolver 实证「隐式内化更好」——同一问题的相反结论，须并列核对 |
| 互补 | **RAGEN** | RAGEN 是受控诊断仪（Echo Trap：奖励方差悬崖→熵塌→梯度尖峰）；AgentEvolver 是真实训练族成员。本篇 α=0.30 的「早期快、末期退化」正是 Echo Trap 的软形态，可用 RAGEN 指标仪器化预警 |
| 互补 | **WebRL** | 同族「自演化课程」；WebRL 从**失败**造任务 + ORM + 回放缓冲，AgentEvolver 从**探索**造任务 + LLM judge + 经验池。任务供给两条路线可对照 |
| 互补 | **Agent0** | 同为「零标注自演化」；Agent0 用 Python 沙盒作**外部客观锚点**、前沿带过滤；AgentEvolver 用 **reference solution 可行性重放**作锚点。本篇 judge 消融（reference 贡献最大 22.5→44.3）**正面支持** Agent0 的「必须插外部客观锚点」原则 |
| 互补 | **EvoRoute** | 都是「步级/任务级经验 → 检索 → 引导执行」形状；EvoRoute 检索后**路由模型**（性能/成本/时延 Pareto），AgentEvolver 检索后**注入提示**。可组合成「检索→（路由 或 注入）」双出口 |
| 互补 | **Agent-World** | Agent-World 造**环境**（数据库 D + 工具集 F），AgentEvolver 在环境内造**任务与经验**——上下游互补：Agent-World 供环境族，AgentEvolver 供环境内的出题/经验闭环 |
| 互补 | **Memento** | Memento 冻结 LLM + 案例库 + 可学习检索 μ；AgentEvolver 的经验池 = 无学习检索版，二者可拼「可学习检索 + 三操作门」 |
| 互补 | **PSN（Evolving Programmatic Skill Networks）** | AgentEvolver 的「经验」是自然语言、不可执行；PSN 的技能是带契约的可执行网络——**正好补 AgentEvolver 缺的技能侧**，把「经验条目」升级为可过沙盒门的技能 |
| 同宗 | **Agent0 / WebRL / EvolveR / R-Zero / RAGEN** | 真实世界自演化训练族 |
| 替代 | 无监控的裸 GRPO 训练、纯 ICL 经验库（就探索效率而言） | 以「出题 + 经验引导 + 细粒度信用」替换 |
| 风险参照 | **Misevolve** | 本篇的「judge 标签过拟合」「经验过度利用压制探索（高 η）」正是误演化清单里的条目 |

### 6.2 推荐组合方案
- **组合 A（慢环形状包）**：本篇（三段式形状 + 成本标尺）× **FLEX**（经验库组织/写入）× **EvolveR**（库治理四件套）
  - **接口形态**：`环境画像 → 出题(前瞻预演) → 轨迹 → 经验编译(回顾编译) → {keep/remove/compress} 门 → 记忆库`
  - **组合后新增能力**：SSEA 慢环首次同时具备「出题—编译—治理—预算标尺」四件。
  - **新增风险**：三者都靠外部奖励/judge 收尾，须统一替换为 SSEA 淘汰函数与合法性门。
- **组合 B（合法性门 + 技能）**：本篇（reference-replay 可行性门）× **PSN**（可执行技能契约）× **Agent-World**（环境契约）
  - **接口形态**：`任务 → reference solution → 沙盒重放（合法性）→ 通过则入库为技能`
  - **组合后新增能力**：把「自然语言经验」升级为「可执行、可验证的技能」，补 C3 技能侧。
  - **新增风险**：重放本身需要环境可执行与状态可校验（Agent-World 的 `V_code` 思路）。
- **组合 C（训练稳定化）**：本篇 × **RAGEN**（Echo Trap 仪器）
  - **接口形态**：任何带引导的离线训练挂 std/熵/梯度范数监控。
  - **新增风险**：阈值需重标定。

### 6.3 本篇在组合中的典型角色
- **慢环「两通路形状 + 成本标尺」的供给方**：给出前瞻预演（出题）与回顾编译（经验）的完整回路图，并附一套可作预算标定的成本数字；同时是 **C9 的自我反证标本**（judge 标签过拟合→退化）。

---

## 7. 多维度评分（1–5）

| 维度 | 分值 | 评分理由（含证据性质：实测 / 推断） |
|---|---|---|
| 项目相关性 | **5** | 直击慢环两通路、记忆门选择性、睡眠期预算三条最紧缺口（实测：三段式闭环与成本数字；推断：映射到 SSEA 模块） |
| 立场兼容性 | **2** | C1/C2/C3/C4/C9 多处 ✗，C7/C8 ✗；但 C9 有强反向佐证（α 消融 + reference-replay 合法性门），C10 ✓（实测 + 推断） |
| 可搬运性 | **4** | 闭环形状、经验 schema、stripping、CMT、成本标尺均可干净拆出（推断）；奖励框架不可搬 |
| 证据强度 | **3** | 两基准 + 分模块/分参数消融较系统，但**自陈 preliminary**、**无 Limitations 节**、**无多 seed 方差**、**无绝对成本**（实测） |
| 组合价值 | **4** | 与 FLEX/EvolveR/PSN/Memento/Agent0/Agent-World/EvoRoute/RAGEN 广泛互补（推断） |
| 落地成本 | **3** | 搬形状/标尺/schema 廉价；跑其完整 RL 闭环需 8×A100 + 大模型 judge（实测） |

---

## 8. 裁决与下一步

- **应用等级：B 零件采用** —— 采用①三段式闭环形状（慢环两通路对位）、②成本标尺、③Experience Stripping、④Reference-replay 合法性门、⑤「When to use + Content」经验 schema、⑥Self-Context-Managing 三操作门、⑦α 消融证据；**不采用**其 LLM judge / 归因 reward / GRPO 奖励框架与 LLM 策略本体。
- **优先级：P1**（慢环形状与睡眠期预算标定的直接参照；与 EvolveR/FLEX 同批对齐）。
- **建议动作**：
  1. 在 `docs/` 慢环设计文档中把「前瞻预演=出题」与「回顾编译=经验编译」两通路对位到本篇三段式，注明可搬与不可搬边界；
  2. 为「睡眠期计算预算」补一张标尺表：以本篇数字（8×A100 / batch 32 / 40 epochs/update / 100 样本→40.3% / Steps@.9 −55%/−67% / 30 步截断）为**上界参照**，实测 SSEA 慢环的对应量级；
  3. 记忆二级门（债务 22）原型引入 `{keep, remove, compress}` 三操作，但**决策不用 LLM**，改用环境事实 + 惊奇；
  4. 把 reference-replay 可行性门作为四级验证门「沙盒层」的实现参考；
  5. 新建 issue：核对 AgentEvolver（隐式内化更优）与 EvolveR（经验吸收进权重退化）的相反结论，作为 C3「记忆/权重是否必须分离」的判据实验。
- **最小验证实验**：
  - **双臂设置**：A 臂=现行记忆二级门（常量阈值）；B 臂=三操作门（keep/remove/compress，决策信号只用环境事实/惊奇，无评分、无 LLM）。两臂同批、同初始状态、≥8 seed。
  - **判据（分档，先看分母）**：① 机制计数（门触发次数、keep/remove/compress 分布、分母样本数）→ ② 逐帧动作差 → ③ 淘汰结果（危险回避率/任务完成率，注意 0.9814 已饱和）。
  - **预期与证伪**：若 B 臂三操作分布退化（全为 keep），说明该形状不可搬运（证伪）；若两臂**均值无差但门决策分布与逐帧动作有差**，则旧判据会误判「无差异」——须先修尺子。另设**成本标尺实验**：测 SSEA 慢环单轮成本（A100-等效 GPU-hours + 样本数 + 收敛步数），与本篇标尺比；预期 SSEA 低 1–2 个数量级，否则说明预算定错。
- 若 **E 不采用**：不适用（取 B）。

---

## 9. 待确认问题

- **需作者 / 团队决策**：
  1. 「efficient」是相对主张还是绝对主张？论文**未报告挂钟时间 / FLOPs / GPU-hours**，SSEA 若引用其成本标尺，只能作**相对上界**，需明确口径。
  2. 是否做**无 LLM judge** 的消融？整个闭环的奖励完全依赖 judge，若去掉 judge 结论是否成立（对 C9 判定关键）。
- **需补查的文献或资料**：
  1. ReMe 仓库（github.com/agentscope-ai/ReMe）中经验构建/检索的实现细节（论文仅给脚注，p9）；
  2. 与 EvolveR「经验吸收进权重退化」的相反结论做并列核对；
  3. 与 Agent0「外部客观锚点」原则的一致性验证。
- **需人工核对的公式 / 实现**：
  1. Eq.17 selective boosting 的 `ε̂_high` 与 Eq.20 的 `α` 是否存在耦合（p11、p14、p23、p26 分别调参）；
  2. 「轨迹级标准化」（Eq.18）与「步级标准化」（§7.1.3 称 step-level normalization within group）表述不一致（p13 vs p19），需核对实现；
  3. Self-Context-Managing 的 `{keep,remove,compress}` 是否真由策略 LLM 决定、还是阈值触发后 LLM 只做标注（p17）。

---

## 附：关键摘录与出处

| 摘录（原句 / 公式 / 图表要点） | 页码 |
|---|---|
| "AgentEvolver introduces three synergistic mechanisms: (i) **self-questioning**… (ii) **self-navigating**… (iii) **self-attributing**…" | p1（Abstract） |
| "**Preliminary experiments** indicate that AgentEvolver achieves more efficient exploration, better sample utilization, and faster adaptation" | p1 |
| "we define an **interaction sandbox**… `E=(S,A,P)`… **excludes the reward function r as well as the discount factor γ**"（Eq.1） | p3 |
| `Ftask:E→Δ(G)`（Eq.4）；`Freward:E×G→(S×A→R)`（Eq.5）；`Jtrain(θ)=E_{g∼Ftask(E)}[V̂πθ(s0,g)]`（Eq.6） | p3–4 |
| 两阶段探索：breadth-first `Nb` → depth-first `Nd`；AppWorld `Nb=3,Nd=17`，BFCL `Nb=3,Nd=27` | p6、p19 |
| 任务过滤：词面去重阈值 **0.8** + 语义去重 + **重放可行性**验证（"identifying real execution failures… where the reference solution is likely hallucinatory"） | p7、p19 |
| Judge 原则：i) **Relevance and Repetition Check**（无关/幻觉步"receive zero scores immediately"）；ii) Continuous Scoring；并做 **Reference-based Correctness Check** | p8 |
| 经验条目 = `{When to use, Content}`；"Representing experiences entirely in natural language"（Fig.5） | p8 |
| 经验池：`Npc=4`、检索 `TopK k=5`、余弦相似 + 重排/重写（Eq.13–14） | p9–10、p19 |
| 经验混合 rollout：`Ne=⌊η·N⌋`，**η=0.5**（Eq.15）；优势 `Â(τ)=(R(τ)−µR)/(σR+ε)`（Eq.16） | p10、p19 |
| **Experience Stripping**："prior to policy gradient computation, retrieved experience tokens are **removed**… optimization is driven exclusively by the generated trajectory"（Fig.7） | p11 |
| Selective Boosting（Eq.17）：`εj=ε̂high if Âj(e)>0 else εhigh`；`εlow=εhigh=0.28`、`ε̂high=0.6` | p11、p19 |
| 归因：GOOD→**+1**、BAD→**−1**；"evaluate each trajectory holistically in a single pass"（Fig.8–9） | p12 |
| 轨迹级标准化（Eq.18）："we adopt **trajectory-level standardization**… each trajectory is treated as an equally important trial" | p13 |
| 复合奖励（Eq.20）：`r̂t=α·r̂attr_t + 1_{t=T}·r̂out`；优势（Eq.21）：`At=Σ_{k=t}^T r̂k`（γ=1） | p14 |
| 训练配置：lr **1e-6**、batch **32**、**40 epochs per policy update**、KL **0.001**、**8×NVIDIA A100 (80GB)** | p18 |
| 轨迹"truncated at a maximum of **30 steps**"；指标 avg@8 / best@8 | p18 |
| Table 1：7B avg@8 **15.8→45.2**（+29.4）；14B **29.8→57.6**（+27.8） | p19 |
| Table 2：7B 原始 37.5 / 合成 36.1 / **混合 43.6**；14B 57.4 / 52.3 / **60.7** | p20 |
| Fig.12a：**100 条样本即 40.3%**，200→42.7，500→44.3 | p21 |
| Fig.12b：naive judge **22.5** → +principle **33.1** → +reference(ours) **44.3** | p21 |
| Table 3：14B AppWorld→BFCL 迁移仅掉 **4.3%** | p21 |
| Table 4：baseline 57.2 → w/o select **56.7** → Navigating(ours) **65.0**（+7.9 avg@4） | p22 |
| 隐式 vs 显式经验："implicit learning consistently surpasses… ICL-only (**↑34.2%** in avg@4)" | p23 |
| **η=0.5** 最平衡；`ε̂high=0.6` 最平衡（Fig.13b/14） | p23 |
| Table 5：7B 16.4 / 41.3 / 35.7 / **47.6**；14B 29.8 / 57.4 / 53.0 / **62.0**（avg@8） | p24 |
| **Table 6 样本效率**：Steps@.9 AppWorld **40 vs 90（−55%）**、BFCL **20 vs 60（−67%）**；AUC 46.26/41.03、61.02/55.78 | p25 |
| α 分析："may cause **overfitting to the LLM judge's heuristic labels** rather than true task objectives"；α=0.30 末期 43%（低于全部）；最优 α∈[**0.10,0.20**] | p26 |
| Table 7 CMT：SCMT 最优 TGC@8 **0.720**、SGC@8 0.607；RAT 0.690 / SWT 0.601 / BCT 0.506 | p26 |
| 未来方向："examine **compute–data trade-offs** and develop **cost-aware curricula**"；"**LLM-level self-evolving**" | p27 |
