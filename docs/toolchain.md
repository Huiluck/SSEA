# 技术栈报告（当前工作所用的栈）

> **目的**：说清「现在这套东西是在什么栈上做出来的」，供复现与交接。
> **口径**：分三层报告——① **项目声明的栈**（`requirements.txt`）② **实际跑起来的栈**（本机实测）③ **做这份工作的 agent 用的工具链**。三者不是一回事，混在一起会让「为什么能复现」变成玄学。
> **快照时点**：2026-09-29，基线 **972 passed, 1 skipped**。

---

## 一、运行环境（本机实测）

| 项 | 值 |
|---|---|
| OS | Microsoft Windows 11 专业版 |
| Shell | PowerShell **7.6.6**（`pwsh`） |
| Python | **3.12.10**（项目内 `.venv`，全路径 `.venv/Scripts/python.exe`） |
| VCS | git **2.50.1.windows.1** |
| 换行符 | 全仓 LF，**唯一例外** `SSEA/fast_loop.py`（CRLF） |

> ⚠️ git 在本机配置了 `core.autocrlf`，于是新建 / 修改 `.md` 与 `.py` 时会打印「LF will be replaced by CRLF」。**这是提示不是错误**，不影响内容与测试。

---

## 二、依赖

### 2.1 项目声明的（`requirements.txt`）

依赖面极小，**这是架构立场的一部分**：

| 包 | 归属 | 为什么 |
|---|---|---|
| `torch` | **唯一的生产依赖** | 模型层（`perception_encoder` / `state_core` / `action_decoder` / `tensorize`） |
| `pytest` | 测试 | |
| `pytest-randomly` | 测试 | **顺序不变性的自动守卫**——项目里有多处夹具依赖全局 RNG，不随机化就发现不了顺序依赖（曾有一条测试在顺序翻转时报「通道从未开启」） |

**明确不需要**（`requirements.txt` 里逐条写明理由）：`numpy`（由 torch 带进来，本项目不直接 import）、`torchvision`（无视觉输入）、任何 LLM / 向量库 / 训练框架。

### 2.2 实际装了的（本机实测）

```
python           3.12.10
torch            2.14.0+cu132
torchvision      0.29.0+cu132     <- 装了但不用（torch 依赖链带进来）
numpy            2.5.3            <- 装了但项目不直接 import
pypdf            6.19.0           <- 卡片工具用（读 PDF 全文）
pytest           9.1.1
pytest-randomly  5.0.0
```

---

## 三、项目自身的技术栈：四层，且「栈的选择」就是立场

| 层 | 技术 | 硬约束 |
|---|---|---|
| **协议层** `SSEA/sse_protocols/` | **纯 stdlib**（frozen dataclass + tuple，无 numpy / torch） | 由 `tests/test_serialization.py` **双向守卫**（正向：协议层不得 import torch；反向：模型层必须 import） |
| **模型层** `SSEA/*.py` | **torch**，CPU 可跑 | 不训练权重；`torch.manual_seed(seed)` 保证确定性 |
| **实验层** `experiments/` | 纯 Python 编排 + torch 确定性种子 | 每个 `(臂, seed)` 一份新 store；不引入额外依赖 |
| **测试层** `tests/` | pytest + pytest-randomly | 每增量收尾跑**全套件 + 15 个随机序种子** |

**为什么协议层不用 numpy / torch**：协议是**接口**，必须可序列化、可 diff、可跨进程；张量化发生在模型边界，不发生在协议层（`sse_protocols/__init__.py` 的设计约定 2）。

**为什么没有 LLM / 向量库**：C2 禁止自然语言进控制闭环；卡片库里 99 篇论文的机制也都**不可整机搬**（见 [SSEA-应用图谱.md](papers/cards/SSEA-应用图谱.md) §1.2）。

---

## 四、做这份工作的 agent 用的工具链

### 4.1 执行环境

| 项 | 值 |
|---|---|
| 框架 | DeepSeek Harness（DSH） |
| 角色 / 模型 | `lead` / `deepseek-flash` |
| 唯一可直接调用的工具 | **`run_code`**（一段 async TypeScript 程序；其它工具都要从程序里 `await tools.x(...)` 调） |
| 每次 `run_code` 的进程 | **全新 Node 进程**，不与上一次共享内存 |
| 工作目录 | `C:\MyDocs\AGI\SSEA` |

### 4.2 实际用到的工具

| 工具 | 用途 |
|---|---|
| `run_code` | 唯一入口；所有编排、测量、校验都在里面 |
| `read` / `edit` / `write` | 读写源码与文档（**edit 前必须先 read**，且有版本守卫） |
| `grep` / `glob` | 找内容 / 找文件（**不**用 shell 的 `find` / `grep`） |
| `pwsh` | 跑 Python、pytest、git；长任务用 `run_in_background` 拿 job id，再 `job_output` 收 |
| `todo_write` | 多步任务的进度盘 |

**本次未用到**（列出以说明覆盖面）：`web_search` / `web_fetch`（未查外网）、`subagent` / `spawn_teammate`（未开并行代理）、`present`、`skill`、`ask_user_question`。

### 4.3 临时探针的纪律

诊断脚本写在 **`%TEMP%`**（`C:\Users\Lhui\AppData\Local\Temp\*.py`），**不进仓**；需要长期留存的一律做成 `experiments/` 下的仪器并登记。

已落地的仪器：`experiments/measure_instinct.py`、`experiments/measure_judgement_health.py`、`docs/papers/_tools/gen_card_index.py`、`docs/papers/_tools/extract_text.py`。

---

## 五、本次增量新增的东西各自的技术栈归属

| 新增 | 层 | 技术 |
|---|---|---|
| `SSEA/sse_protocols/judgement_health.py` | 协议层 | 纯 stdlib；八条子句，H1–H4 算、H5–H8 声明 |
| `SSEA/sse_protocols/induction_funnel.py` | 协议层 | 纯 stdlib；漏斗六段 + 慢环闸 + 单调性守卫 |
| `experiments/measure_judgement_health.py` | 实验层 | 跑 exp2 / exp3 既有臂，喂给协议层；**只体检不改行为** |
| `experiments/_harness.py` 的 `BudgetMatchedRetriever` | 实验层 | 包装 `FastLoop` 造好的记忆实例，抹掉注入向量 |
| `docs/papers/_tools/gen_card_index.py` | 文档工具 | 纯 stdlib；从卡片正文抽表 + 盖章计数 + **未映射即非零退出** |
| 本轮全部诊断探针 | 无（临时） | `%TEMP%`，用完即删 |

---

## 六、复现命令（可直接拷）

```powershell
cd C:\MyDocs\AGI\SSEA

# 1. 全套件
.\.venv\Scripts\python.exe -m pytest tests/ -q

# 2. 顺序不变性：15 个随机序种子
1..15 | ForEach-Object { .\.venv\Scripts\python.exe -m pytest tests/ -q -p randomly --randomly-seed=$_ }

# 3. 判据体检（八条子句 + 逐情境 V_tau）
.\.venv\Scripts\python.exe -m experiments.measure_judgement_health 200

# 4. 三臂验收实验（固化关 / 固化开 / 预算匹配）
.\.venv\Scripts\python.exe -m experiments.exp2_memory_recall 200
.\.venv\Scripts\python.exe -m experiments.exp3_skill_consolidation 200

# 5. 卡片的分析与总表
.\.venv\Scripts\python.exe docs\papers\_tools\gen_card_index.py --stamp-only
```

> **临时探针跑法**：在 `pwsh` 里先设 `$env:PYTHONPATH` 为仓库根，否则 `import experiments` 会失败——这是本机唯一一个「不写下来就会重复踩」的坑。

---

## 七、边界与局限

1. **CUDA 构建未锁版本**：`torch 2.14.0+cu132` 与本机显卡相关；换机需按 pytorch.org 选装。项目本身 CPU 可跑。
2. **本报告是快照**：依赖与版本会漂。`requirements.txt` 头部那行「已验证环境」现写着 2026-09-27 / 595 passed，**已过期**，应随之更新。
3. **agent 工具链不可复现**：第四节描述的是「这份工作怎么被做出来的」，不是项目的一部分。**能复现的是第六节的命令**，不是我的编辑器。
4. **无 GPU 训练**：本项目不做参数侧 Δθ（`plasticity.DEFERRED_SCOPES`），所有实验都是 CPU 上的确定性 rollout。

---

## 附：一句话

**这份项目的栈是「纯 stdlib 协议层 + torch 模型层 + 确定性实验层 + 随机序测试层」，生产依赖只有一个；做它的 agent 工具链是 DSH 的 `run_code` 单入口 + 读写 / 搜索 / 后台作业——前者要复现，后者只需要知道。**
