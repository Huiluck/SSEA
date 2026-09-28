#!/usr/bin/env python3
"""Regenerate the card-set master table + stamped counts in cards/SSEA-应用图谱.md.

Usage (from repo root):
    ./.venv/Scripts/python.exe docs/papers/_tools/gen_card_index.py

Why this exists: the card set grows while being written (47 -> 61 in one session).
A hand-maintained index rots within minutes; this regenerates the table, stamps the
counts, and REPORTS any card that has no slot/grain mapping so the map cannot silently
drift out of date.
"""
import re, sys, pathlib, collections

ROOT = pathlib.Path(__file__).resolve().parents[3]          # repo root
CARDS = ROOT / "docs" / "papers" / "cards"
PAPERS = ROOT / "docs" / "papers"
DOC = CARDS / "SSEA-应用图谱.md"

# short name -> (slot, grain, landing)
MAP = {
 "A-MEM": ("S2 记忆组织", "G2", "类型化关联拓扑；retrieve 返回主记录 + 一步关联闭包"),
 "ACE": ("S2 记忆组织", "G1", "「慢环禁止整体重写」纪律 + 非 LLM 确定性 delta 合并 + 坍缩监控"),
 "ADAS": ("S9 L4演化", "G3", "档案/谱系/垫脚石形式化（Gene Manager 搜索侧模板）"),
 "Agent-World": ("S12 环境", "G1", "环境包契约 (D,F) + 通道消费者准入 + 可执行验证 V_code"),
 "Agent0": ("S1 判据健康", "G4", "前沿带选择规则 + C8 反例标本（零标注≠零知识语料）"),
 "AgentKB": ("S3 记忆检索", "G1", "混合双通道检索 + disagreement gate + 跨域不对称实证（C8 拼图）"),
 "ARISE": ("S8 技能构造", "G2", "两层 Cache/Reservoir 生命周期协议 + 只判合法性准入门 + 弃权门"),
 "Aspire": ("S1 判据健康", "G1", "三层产出记账（best/eligible/selected/retained）+ 以 base 为锚 + 轨迹分解"),
 "AutoEnv": ("S1 判据健康", "G1", "三层环境抽象 + 三阶段验证 + 差分可靠性检查 + Skin-Inverse 控制消融"),
 "AutoSkill": ("S8 技能构造", "G4", "技能卡 schema + 语义并集合并代数（反面：只有合并没有退休）"),
 "Dream-RSI": ("S11 睡眠期", "G3", "发现历史当可重放模拟器：零成本离线提案验证"),
 "DynamicCheatsheet": ("S2 记忆组织", "G4", "ΔM 产出物形态（反面：整体重写致 18,282→122 token 坍缩）"),
 "EvolveR": ("S2 记忆组织", "G2", "经验生命周期回路图 + 库治理四件套 + 成本锚点（8×A100×39.4h）"),
 "EvoRoute": ("S3 记忆检索", "G1", "三面析取检索（角色/工具/状态分档）+ 步级三维成本记账"),
 "EvoTest": ("S11 睡眠期", "G3", "无梯度整机演化 + 可量化预算账本（每周期 1 次前向 / 20–30 s）"),
 "ExperienceSynthesis": ("S1 判据健康", "G1", "奖励熵难度选择器 V_tau（只选不训）+ 四维评委（幻觉/失败反馈）"),
 "ExperienceToStrategy": ("S4 记忆内容", "G2", "三层抽象 Q→T→M：给 rules(ΔR) 装第一个消费者"),
 "FLEX": ("S2 记忆组织", "G1", "分层经验库 + 写入三分支 + logistic 增长曲线作睡眠期停机判据"),
 "G-Memory": ("S2 记忆组织", "G2", "三层图（洞察/索引/交互）+ 双向遍历 + 1-hop 检索纪律"),
 "GenEnv": ("S1 判据健康", "G1", "α 难度带 + Theorem 1 样本量界（同时也是 C9 头号反例）"),
 "Genie": ("S12 环境", "G3", "潜在动作模型 + ST-Transformer + FVD/ΔPSNR 可控性仪器"),
 "Gödel-Agent": ("S10 自修改", "G3", "自指更新方程 + 四动作生命周期 + 14% 永久劣化率风险先验"),
 "GroupEvolving": ("S9 L4演化", "G3", "群体共享拓扑 + 归档合法性门 + 祖先整合计数（Gene Manager 共享侧）"),
 "HarnessDev": ("S10 自修改", "G1", "诚实状态契约 + 评分路径隔离 + 「反馈涨 held-out 跌」退化清单"),
 "HarnessEval": ("S1 判据健康", "G1", "判据健康度检查表：预算匹配基线 + 搜索/评测分离 + pass@1/k 分档"),
 "InducingProgrammaticSkills": ("S8 技能构造", "G1", "入库三判据 + 尾随动作截断 + attempted/passed/reused 三档分母"),
 "LLMasCode": ("S15 控制流归属", "G1", "控制流=代码、语言退到叶（C2 最干净形式化）+ DAG 上下文作用域规则"),
 "LightMem": ("S2 记忆组织", "G1", "摄入压缩 + 双信号边界切块 + 阈值触发巩固 + 软更新（只合并不硬删）"),
 "MaAS": ("S9 L4演化", "G5", "架构超网分布 + 查询条件化早退（L4 连续路线对照 ADAS 离散种群）"),
 "Mem-alpha": ("S2 记忆组织", "G2", "ΔM 事务动作空间 + 三层记忆 + 写侧可学/读侧冻结解耦"),
 "Mem0": ("S2 记忆组织", "G2", "ADD/UPDATE/DELETE/NOOP 分类式 CRUD + 实体关系图 + 软冲突标记"),
 "Memento": ("S3 记忆检索", "G3", "可学习检索策略 mu（记忆增广 MDP）——治「门开得准不准」"),
 "MemEvolve": ("S9 L4演化", "G2", "记忆系统基因型 (E,U,R,G) + 可修改位点 + 诊断式提案"),
 "MemGen": ("S6 记忆动作", "G2", "定长潜张量注入面 + 可训练稀疏记忆门（含激活预算配额）"),
 "MemoryAsAction": ("S6 记忆动作", "G2", "按 id 精确裁剪——SSEA 缺的「忘」这一半动作"),
 "MemRL": ("S3 记忆检索", "G1", "两阶段检索（硬阈值召回→小池重排）+ 冻结库迁移验收协议 + 遗忘率 FR"),
 "MemSkill": ("S6 记忆动作", "G2", "「记忆技能」= 第四类元程序 + 睡眠期预算三元组 + 难例缓冲"),
 "Misevolve": ("S10 自修改", "G1", "模型/记忆/工具/工作流四路径误演化威胁模型与红队验收清单"),
 "OpenSkill": ("S5 记忆准入", "G1", "验证器品质仪器（假阳/假阴/一致率）+ 提案者/验证者进程级隔离"),
 "Ouroboros": ("S10 自修改", "G1", "宪法核 + 指纹绑定(TOCTOU) + quorum + 花费上限 + panic + pattern register"),
 "PSN": ("S7 技能主干", "G2", "技能契约网络 + REFLECT 故障定位 + 成熟度门控 + 回滚验证重构"),
 "RAGEN": ("S1 判据健康", "G1", "Echo Trap 诊断（方差悬崖→熵塌缩→梯度尖峰）+「方差先于均值」"),
 "ReasoningBank": ("S4 记忆内容", "G2", "推理单元 schema + 成功/失败双路抽取 + 注入条数预算律（k=1 最优）"),
 "RecordReplay": ("S7 技能主干", "G2", "多层经验粒度 + check function（技能该长什么样的粒度裁判）"),
 "Reflexion": ("S7 技能主干", "G5", "试错→评估→反思→入库外环经典形状（报告基线）"),
 "RetroAgent": ("S3 记忆检索", "G1", "SimUtil-UCB 探索项 + Phi_x 历史基线相对进展门（内驱第二层信号候选）"),
 "SEAL": ("S13 参数Δθ", "G4", "Δθ 代价标尺 + 灾难性遗忘实证（维持 DEFERRED 的判据来源）"),
 "SEDM": ("S5 记忆准入", "G1", "SCEC 自包含打包 + 配对 A/B 准入 + 抽象后跨域重验"),
 "ScaleEnv": ("S12 环境", "G1", "规则式状态判据（比对终局状态）+ Procedural Testing 通道准入"),
 "SelfConsolidation": ("S11 睡眠期", "G4", "teacher/student 蒸馏形状 + FIFO 有界遗忘（反面：产物落进权重）"),
 "SkillRL": ("S8 技能构造", "G1", "失败侧差分蒸馏 + 慢环回顾配额三元组（周期/条数/提案上限）"),
 "SkillWeaver": ("S8 技能构造", "G2", "提案-练习-合成-打磨流水线 + 强→弱 API 继承"),
 "SurveySelfEvolving": ("S14 综述", "G5", "坐标系索引；生存域在其坐标系中空白 → 独立赛道声明"),
 "TTCS": ("S1 判据健康", "G1", "无标签自洽性前沿带（s≈0.5）+ 在线过滤（偏离 0.5 超 δ 即弃）"),
 "Voyager": ("S8 技能构造", "G5", "自动课程（新颖性）+ 键/值技能库 + 独立 critic（PSN 前身）"),
 "WebRL": ("S8 技能构造", "G2", "失败→课程任务生成 + 演员置信过滤 + 四类失败分类法"),
 "Xolver": ("S3 记忆检索", "G2", "双记忆分层（长期 episodic × 单题工作记忆）+ 跨题经验积累回路"),
 "AgentEvolver": ("S11 睡眠期", "G1", "三段式闭环形状（自问/自导航/自归因）+ 成本标尺 + reference-replay 合法性门"),
 "MetaContextEngineering": ("S6 记忆动作", "G2", "元技能 ΔP 的双层形式化（元层技能演化 × 基座层上下文实例化）+ 双产物发布 + best-so-far 回滚"),
 "CoMAS": ("S1 判据健康", "G4", "「奖励来源=同伴」的 C9 边界裁决 + 自评回路两种失败模式 + 奖励-验证器一致性协议"),
 "SkillNet": ("S8 技能构造", "G2", "关系四类型（similar_to/belong_to/compose_with/depend_on）+ pre/post 场景契约 + 二值组合完备度"),
 "SkillsBench": ("S8 技能构造", "G5", "配对评测协议 + 确定性 verifier + 外部负结果（自生成技能低于无技能基线）"),
}

def cell(s): return s.replace("|", "\\|")

def collect():
    rows = []
    for p in sorted(CARDS.glob("*.分析卡片.md")):
        t = p.read_text(encoding="utf-8")
        name = p.name.replace(".分析卡片.md", "")
        mv = re.search(r"\|\s*\*\*应用裁决\*\*\s*\|(.+)", t)
        mp = re.search(r"\|\s*优先级\s*\|(.+)", t)
        v = (mv.group(1) if mv else "?").replace("**", "").split("（")[0].split("(")[0].strip()
        pr = (mp.group(1).replace("**", "") if mp else "?")
        pr = re.split(r"[（(，,|]", pr)[0].strip()
        sc = dict(re.findall(r"\|\s*(项目相关性|立场兼容性)\s*\|\s*\*{0,2}(\d)\*{0,2}", t))
        slot, grain, land = MAP.get(name, ("?", "?", "（**未登记映射**：请在此脚本的 MAP 中补一行）"))
        rows.append((name, v, pr, sc.get("项目相关性", "-"), sc.get("立场兼容性", "-"), grain, slot, land))
    return rows

def main():
    rows = collect()
    n = len(rows)
    n_pdf = len(list(PAPERS.glob("*.pdf")))
    readme_rows = len([l for l in (CARDS / "README.md").read_text(encoding="utf-8").splitlines() if l.startswith("| [")])
    missing = n - readme_rows
    unmapped = [r[0] for r in rows if r[6] == "?" or r[5] == "?"]

    tbl = ["<!-- AUTO-TABLE-START -->",
           "| 短名 | 裁决 | 优先 | 相关性 | 兼容性 | 粒度 | 槽位 | 该拿什么 / 落到哪 |",
           "|---|---|---|---|---|---|---|---|"]
    for nm, v, pr, rl, cp, gr, sl, ld in rows:
        tbl.append("| [%s](%s.分析卡片.md) | %s | %s | %s | %s | %s | %s | %s |" % (nm, nm, cell(v), cell(pr), rl, cp, gr, cell(sl), cell(ld)))
    tbl.append("<!-- AUTO-TABLE-END -->")

    # `--stamp-only`：只重算 {N}/{NPDF}/{MISSING} 这些**计数**，不重写总表。
    # 卡片集由并发进程持续新增时，总表会有一批卡还没有槽位映射；这时重写会把
    # 它们全变成 `未登记映射`，把一张有用的表变成一张全是洞的表。
    # 所以：计数永远可以刷新，**表只在映射齐了的时候重写**。
    stamp_only = "--stamp-only" in sys.argv[1:]

    t = DOC.read_text(encoding="utf-8")
    if stamp_only:
        mapped = len([r for r in rows if r[5] != "?"])
        stamp_rows = len([ln for ln in t.splitlines() if re.match(r"^\| \[[A-Za-z]", ln)])
        t = t.replace(
            "<!-- AUTO-TABLE-START -->",
            "<!-- AUTO-TABLE-START -->\n"
            f"> **总表快照**：本表覆盖 **{stamp_rows}** 张已登记映射的卡；生成时卡片集共 **{n}** 张，\n"
            f"> 其中 **{n - mapped}** 张**尚未登记槽位映射**（生成器会点名它们）。重跑：\n"
            "> `./.venv/Scripts/python.exe docs/papers/_tools/gen_card_index.py`（不加 `--stamp-only`）。\n",
            1,
        )
    else:
        t = re.sub(r"<!-- AUTO-TABLE-START -->.*?<!-- AUTO-TABLE-END -->", "\n".join(tbl), t, flags=re.S)
    t = t.replace("{N}", str(n)).replace("{NPDF}", str(n_pdf))
    t = t.replace("{UNMAPPED}", str(n - mapped)) if stamp_only else t.replace(
        "{UNMAPPED}", "0"
    )
    t = t.replace("{STAMPED}", str(stamp_rows if stamp_only else n))
    t = t.replace("{MISSING}", str(missing)).replace("{README_ROWS}", str(readme_rows))
    DOC.write_text(t, encoding="utf-8")

    print("cards=%d  pdfs=%d  readme_index_rows=%d  missing_from_index=%d" % (n, n_pdf, readme_rows, missing))
    print("verdicts:", dict(collections.Counter(r[1] for r in rows)))
    print("prio:    ", dict(collections.Counter(r[2] for r in rows)))
    print("grain:   ", dict(collections.Counter(r[5] for r in rows)))
    print("compat:  ", dict(collections.Counter(r[4] for r in rows)))
    print("relev:   ", dict(collections.Counter(r[3] for r in rows)))
    print("slot:    ", dict(collections.Counter(r[6].split()[0] for r in rows)))
    if unmapped:
        print("!! UNMAPPED (add to MAP):", unmapped)
    return 1 if unmapped else 0

sys.exit(main())