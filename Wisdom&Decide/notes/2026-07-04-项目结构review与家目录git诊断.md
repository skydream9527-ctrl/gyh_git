# 项目结构 Review 与家目录 git 诊断

- 日期：2026-07-04
- 范围：`~/Desktop/trae-cn/gitlab/` 整体（ice-data-work + pm-workspace-starter + 家目录 git）
- 性质：现状盘点 + 重组建议（**用户决定暂不执行重组，仅记录现状**）

---

## 〇、一句话结论

`gitlab/` 不是 git 仓库，是装了两个独立 git 仓库的普通文件夹；家目录 `/Users/mi` 是一个 12GB 的在用 git 仓库，是 `git status` 噪音的根源。两个子项目定位互补：ice-data-work = 工程正本，pm-workspace-starter = 思考空间。

---

## Part 1 · 家目录 git 诊断

### 1.1 三个 git 仓库的真实关系

| 仓库 | 路径 | remote | 性质 |
|---|---|---|---|
| 家目录 git | `/Users/mi` | `gitlab`=gyh_gitlab(小米内网) · `origin`=browser_demo(github) | ⚠️ 工作区=整个家目录，无 `.gitignore` |
| ice-data-work | `gitlab/ice-data-work` | `origin`=ice-data-work(小米内网) | ✅ 工程正本，独立仓库 |
| pm-workspace-starter | `gitlab/pm-workspace-starter` | `gyh_git`(github) · `ice-workbench`(小米内网) · `origin`=gyh_gitlab(小米内网) | ⚠️ 三个 remote |

### 1.2 家目录 git 关键事实

| 项 | 数据 | 说明 |
|---|---|---|
| 仓库根 | `/Users/mi` | 整个家目录都是工作区 |
| 跟踪文件数 | 1446 | 几乎全在 `~/Desktop/` 下 |
| `.git` 大小 | 12 GB | 历史很重，推断含大量 `.DS_Store`/二进制 |
| `.gitignore` | 不存在 | 噪音的直接原因 |
| 当前分支 | `feat/task-workspace` | 活跃开发中（最新 `bec1b4c`） |
| 远端备份 | ✅ `origin/main` (github browser_demo) | 已推送，有备份 |
| 敏感文件泄露 | ✅ 无 | 命中的都是 `tokens.css`/`.env.example` 等误命中 |

### 1.3 跟踪文件分布

| 顶层目录 | 文件数 | 内容 |
|---|---|---|
| `Desktop/agents/` | 763 | data_analysis agent（含 nl-sql reference） |
| `Desktop/web_workspace/` | 568 | web 工作区 |
| `Desktop/game_demo/` | 104 | 游戏演示 |
| `Desktop/feishu-bot/` | 1 | 飞书 bot |
| 其他 | 10 | jump-game.html / README.md / .gitattributes |

> `~/Desktop/trae-cn/gitlab/` 下的两个子项目**没有**被家目录 git 跟踪（它们有自己的 `.git`）。家目录 git 跟踪的是 `Desktop/` 下另一批项目副本。

### 1.4 噪音根源

在 `gitlab/` 下执行 `git status` 时，git 向上找到的仓库根是 `/Users/mi`，于是把整个家目录当工作区扫描 → 看到 `../../../.claude/`、`../../../jump-game.html` 等全部未跟踪文件。**这不是子项目的问题，是家目录仓库的溢出。**

### 1.5 日常操作提示

在 `gitlab/` 下工作时，**显式指定子仓库**，避免误操作家目录仓库：

```bash
git -C ice-data-work status        # 操作 ice-data-work
git -C pm-workspace-starter status # 操作 pm-workspace-starter
# 裸 git status 会作用于 ~/，看到一堆噪音，不要据此 add/commit
```

### 1.6 待选清理方案（用户暂未采纳，留备后查）

| 方案 | 风险 | 效果 |
|---|---|---|
| A. 加 `~/.gitignore` 收窄（忽略非 Desktop 内容） | 低 | 消除噪音，保留仓库 |
| B. Desktop 下各项目独立 `git init`，退役家目录 git | 中 | 最干净，工作量大 |
| C. 备份 `.git` 后 `git filter-repo` 瘦身 12GB | 中 | 减体积，不改结构 |
| D. 不处理（当前选择） | 无 | 现状 |

---

## Part 2 · pm-workspace-starter 知识体系梳理

### 2.1 总览（2037 md，五层）

```
pm-workspace-starter/
├─ [L0] AI 协作配置   THINKING/USER/MEMORY/AGENTS/CLAUDE.md
├─ [L1] 思考决策中心  Wisdom&Decide/  (~10 md)
├─ [L2] 领域知识      project/ 13 领域 (~920 md) + ice-workbench-new(681 副本)
├─ [L3] 实践记录库    knowledge-base/  (46 md，多为占位)
└─ [L4] 自洽子工作区  data-product-workspace/  (1039 md，含 00-知识库 243 md)
```

### 2.2 13 领域卡片表

| 领域 | 定位 | 深度 | 主要重叠点 |
|---|---|---|---|
| agent-llm (75) | Agent/LLM 全栈 | 厚 | 与 knowledge-base/AI-Agent、RAG、dpw/00-知识库 三处重叠 |
| ice-workbench-new (681) | ICE Workbench 工程参考副本 | 厚 | 与 ice-data-work 概念继承；会过时 |
| ice-data-work (32) | 新工作台设计 + 代码副本 | 中 | 与"只保留一份副本"原则矛盾 |
| decision-frameworks (28) | SWOT/波特/RICE/贝叶斯 + 案例 | 厚 | 与 Wisdom&Decide/02-SOP 交叉；与 dpw/00-知识库 重叠 |
| data-analysis (16) | 漏斗/路径/留存/RFM/归因 | 中 | 与 Wisdom&Decide/data-analysis-handbook 高度重复 |
| cybernetics (12) | 控制论 + 钱学森 + AI 对接 | 中 | 独立，无重叠 |
| causal-inference (11) | 潜在结果/SCM/DID/DML/uplift | 中 | 与 dpw/00-知识库 重叠 |
| ab-testing (9) | 假设检验/CUPED/序贯/SRM | 中 | 与 dpw/00-知识库 重叠 |
| management-work (7) | 小米中基层管理指南 | 薄 | 独立 |
| ai-infra-knowledge (6) | 分布式训练/推理/MLOps/MoE | 薄 | 与 dpw/00-知识库 重叠 |
| event-tracking (6) | 埋点设计/参数模型/数据契约 | 薄 | 与 knowledge-base/数据埋点 功能重叠 |
| LLM_thinking (2) | 人-AI 协作思考 | 薄 | 两个近乎同名文件，是重复 |
| multica / product / understand-anything (各1) | 调研笔记 | 薄 | 单文件不该独立成"领域" |

### 2.3 最严重问题：三层知识库重叠

同一领域在**三处**各有独立目录和 README：

| 层 | 路径 | README 声明定位 | 实际状态 |
|---|---|---|---|
| L2 | `project/` | 系统性原理 | 内容实，是主载体 |
| L3 | `knowledge-base/` | 实践记录/调优日志 | 太薄，多为占位 |
| L4 | `data-product-workspace/00-知识库/` (243 md) | 无明确定位 | 实为 project/ 翻版，非补充 |

涉及重叠的 7 个领域：ab-testing / agent-llm / data-analysis / causal-inference / decision-frameworks / product / ai-infra。

### 2.4 其他结构问题

| # | 严重度 | 问题 |
|---|---|---|
| 2 | 中 | `Wisdom&Decide/data-analysis-handbook.md` (600+行) 与 `project/data-analysis/` 高度重复 |
| 3 | 中 | `Wisdom&Decide/decisions/` 空置，实际决策在 `data-product-workspace/DECISIONS.md`（8 条） |
| 4 | 低 | LLM_thinking/ 重复文件；multica/product/understand-anything 单文件不该独立成领域 |
| 5 | 低 | `engineering-ref/` 应归入 `ice-workbench-new/` |
| 6 | 低 | `project/ice-data-work/` 含代码副本，与"只保留一份副本"原则矛盾 |

### 2.5 重组建议（8 条，按优先级，**未执行**）

1. 消除三层知识库重叠：`data-product-workspace/00-知识库/` 7 个同名目录合并到外层 `project/`，子工作区只留链接 + 业务自有资产（预计减 100-150 重复 md）
2. 合并 `data-analysis-handbook.md` 与 `project/data-analysis/`，一处做主另一处链接互指
3. 激活 `decisions/`：把 `data-product-workspace/DECISIONS.md` 同步或链接过来
4. 清理 LLM_thinking 重复文件，移到 `insights/`，删空目录
5. 单文件调研笔记（multica/understand-anything）移到 `references/` 或 `agent-llm/` 下
6. `engineering-ref/` 归入 `ice-workbench-new/`
7. `knowledge-base/` 降级为索引层，或明确"跨项目通用实践 vs 业务特定实践"分工
8. 统一 `project/` 薄目录定位：`product/` 要么补内容要么合并到 `agent-llm/`

---

## Part 3 · 决策记录

- **2026-07-04** 家目录 git 仓库：**暂不处理，仅记录现状**（方案 D）。日常在 gitlab/ 下用 `git -C` 操作子仓库。
- **2026-07-04** pm-workspace-starter 知识体系重组：**暂不执行，先消化报告**。本文件即为重组前的现状基线，后续启动重组时以此为准。

---

## 附：ice-data-work 速览（工程正本，不在重组范围）

| 项 | 内容 |
|---|---|
| 定位 | User → Twin → Agents 团队数据工作台 |
| 技术栈 | FastAPI + SQLAlchemy + G3 文件优先 + SQLite + pgvector；React 18 + Vite + TS + Zustand |
| 代码体量 | 后端 41 service / 22 测试文件（pytest 415/415）；前端 16 页面 |
| 内置 Agent | code-runner / data-analysis / report-writer |
| 进度 | M0–M13 全部完成（v1 + v1.5 + 安全治理 + 自进化 + 外部集成 + LLM 预算硬上限） |
| 入口 | `ice-data-work/README.md` + `DEV_PLAN.md` + `PROGRESS.md` |
