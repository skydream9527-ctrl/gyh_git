# Understand Anything

> 把任何 codebase / 知识库 / 文档变成一张可探索、可搜索、可问答的**交互式知识图谱**。
>
> 上游：[github.com/Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything) · [官网](https://understand-anything.com) · [Live Demo](https://understand-anything.com/demo/) · MIT License

---

## 一、它解决什么

> "你刚加入一个新团队。代码库 20 万行。**从哪开始？**"

Understand Anything 是一个 **Claude Code Plugin**（同时也支持 Codex / Cursor / Copilot / Gemini CLI / OpenCode / Hermes / Cline / KIMI / Trae 等十几种 AI 编码工具）。它做一件事：

```
用 multi-agent pipeline 扫描你的项目，
把每个 file / function / class / dependency 都建成知识图谱节点，
然后给你一个交互式 dashboard 去 pan / zoom / search / click
```

→ **目标不是"画出复杂图让你 wow"，而是"安静地教会你每一块怎么拼接到一起"**。

---

## 二、核心特性

| 特性 | 干什么 |
|---|---|
| **结构图（Structural Graph）** | 每个文件 / 函数 / 类都是节点，可点击、搜索；选中节点看自然语言摘要、关系、Guided Tour |
| **业务域视图（Domain View）** | `/understand-domain` 切到横向图：domains → flows → steps，看代码怎么映射到业务流程 |
| **知识库分析（Karpathy LLM Wiki）** | `/understand-knowledge` 把 Karpathy 风格的 wiki（`index.md` + wikilinks + categories）变成 force-directed 图谱 + community clustering |
| **Guided Tours** | 自动生成 walkthrough，按依赖顺序教你读代码 |
| **Fuzzy & Semantic Search** | "哪些部分处理 auth?" → 语义搜索跨图返回相关结果 |
| **Diff Impact Analysis** | `/understand-diff` 在 commit 前看变更的涟漪范围 |
| **Persona-Adaptive UI** | 根据角色（junior / PM / power user）调整 dashboard 详细程度 |
| **Layer Visualization** | 自动按 API / Service / Data / UI / Utility 分组并配色 |
| **Language Concepts** | 12 种编程模式（generics / closures / decorators 等）出现在哪都标出来 |

---

## 三、原理 / 实现机制

### 3.1 Tree-sitter + LLM 混合

**核心设计**：把"结构事实"和"语义解读"分开干，每件事用最擅长的工具：

```
Tree-sitter（确定性）        LLM（语义性）
──────────────────────        ──────────────────────
解析源码 → CST                读源码 + 结构 → 自然语言摘要
提取 imports / exports       生成 tags
function / class 定义        分配 architectural layer
call sites / 继承            mapping 业务域
fingerprint 用于增量更新     Guided Tour 内容
（同输入 → 同输出）           Language Concept 标注

→ 结构边永远可复现           → 意图侧捕捉"这个文件是干嘛的"
```

这种分工让图谱**结构面是 reproducible 的**（同代码 → 同边），**语义面是 emergent 的**（捕获 intent 而不只是 imports）。

### 3.2 Multi-Agent Pipeline

`/understand` 命令编排了 5 个专用 Agent，`/understand-domain` 加第 6 个，`/understand-knowledge` 加第 7 个：

| Agent | 职责 |
|---|---|
| `project-scanner` | 发现文件、检测语言和框架 |
| `file-analyzer` | 抽 functions / classes / imports；产出图节点和边 |
| `architecture-analyzer` | 识别架构 layers |
| `tour-builder` | 生成 Guided Tour |
| `graph-reviewer` | 校验图完整性 + 引用一致性（默认内联跑；`--review` 跑完整 LLM review） |
| `domain-analyzer` | 抽业务域 / flows / 步骤（被 `/understand-domain` 调用） |
| `article-analyzer` | 从 wiki 文章里抽实体 / claims / 隐式关系（被 `/understand-knowledge` 调用） |

**并行 + 增量**：
- file-analyzer 最多 5 个并发，每批 20-30 个文件
- 默认增量——只重分析变更的文件（fingerprint 比对）
- `--auto-update` 装一个 post-commit hook，每次 commit 自动 patch 图谱

### 3.3 数据持久化

```
.understand-anything/
├── knowledge-graph.json       ← 主图（提交进 git）
├── intermediate/              ← 本地 scratch（gitignore）
└── diff-overlay.json          ← 本地 scratch（gitignore）
```

**团队共享**：把 `knowledge-graph.json` commit 进仓库，新人 onboarding 时直接用，不用再跑 pipeline。10 MB+ 的图建议用 git-lfs。

---

## 四、关键命令速查

```bash
# 一次性分析
/understand
/understand --language zh         # 输出节点描述 + dashboard UI 用中文（en/zh/zh-TW/ja/ko/ru）
/understand src/frontend          # 限定子目录（大型 monorepo）
/understand --auto-update         # 装 post-commit hook

# 探索
/understand-dashboard             # 起 web dashboard
/understand-chat How does the payment flow work?
/understand-explain src/auth/login.ts
/understand-onboard               # 新人指南
/understand-domain                # 业务域视图
/understand-diff                  # 当前改动影响分析
/understand-knowledge ~/path/to/wiki   # 分析 Karpathy 风格 LLM wiki
```

---

## 五、跨平台安装

### Claude Code（原生）

```bash
/plugin marketplace add Lum1104/Understand-Anything
/plugin install understand-anything
```

### 其他平台一键脚本

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.sh | bash
# 跳过提示：
curl -fsSL https://raw.githubusercontent.com/Lum1104/Understand-Anything/main/install.sh | bash -s codex
```

支持的 `<platform>`：`gemini`、`codex`、`opencode`、`pi`、`openclaw`、`antigravity`、`vibe`、`vscode`、`hermes`、`cline`、`kimi`、`trae`

更新：`./install.sh --update`；卸载：`./install.sh --uninstall <platform>`。

### Cursor / VS Code + Copilot

仓库带 `.cursor-plugin/plugin.json` 和 `.copilot-plugin/plugin.json`，**克隆即被自动发现**，无需手动装。

### Copilot CLI

```bash
copilot plugin install Lum1104/Understand-Anything:understand-anything-plugin
```

---

## 六、和本工作区的关系

### 6.1 在 [`pm-workspace-starter/`](../) 整体定位

这个工作区里已经有几条相关线索：

| 模块 | 用途 |
|---|---|
| [`agent-llm/`](../agent-llm/) | Agent / LLM 原理与范式（ReAct、ToT、Memory） |
| [`agent-llm/agents/openviking-vs-hindsight.md`](../agent-llm/agents/openviking-vs-hindsight.md) | 长期**记忆** Provider 对比（语义召回） |
| **本目录（understand-anything）** | 长期**知识图谱** Provider（结构 + 语义） |
| [`ice-workbench/`](../ice-workbench/) | AI 数据工作流工作台（生产级 Agent 应用） |

**Understand Anything 在四件事上独特**：
1. 是**结构性的**：节点和边来自 tree-sitter，不像向量库可能"召回不可控"
2. 是**层级的**：file ↔ class ↔ function 自带层级，可以浏览
3. 是**可视化的**：dashboard 比对话窗口更适合理解一个项目的整体形状
4. 是**多 Agent pipeline 的范本**：5 个 Agent 协作的开源实现，可以拆开学

### 6.2 在 [`ice-workbench/`](../ice-workbench/) 里怎么用

#### 用法 A — 给 ice-workbench 自身造图

```bash
cd pm-workspace-starter/project/ice-workbench
/understand --language zh
/understand-dashboard
```

→ 一份给 PM / 新加入工程师的"导览"，比读 [`design_decisions.md`](../ice-workbench/design_decisions.md)（133 决策）更直观。

ice-workbench 的 [`backend/app/services/`](../ice-workbench/backend/app/services/) 有 30+ service 文件，前端 [`frontend/src/pages/`](../ice-workbench/frontend/src/) 24 路由——**典型靠人读读不完**的规模。Understand Anything 的 Guided Tour 按依赖顺序排，恰好覆盖这种学习场景。

#### 用法 B — 给 ice-workbench 的 Agent 接入"代码库知识"

ice-workbench 当前的知识来源是飞书 wiki（[`backend/app/services/kb_svc.py`](../ice-workbench/backend/app/services/kb_svc.py)）。Understand Anything 产出的 `knowledge-graph.json` 也可以作为知识源：

```python
# backend/app/services/codebase_kb_svc.py（新增）
def get_node(node_id: str) -> dict: ...
def search_nodes(query: str) -> list: ...

# 注册成 builtin tool（参考 tool_runner.py 已有 kyuubi_query 模式）
{
  "name": "codebase_search",
  "description": "搜索本仓库的代码知识图谱（function/class/file 级），返回节点摘要 + 关系。",
  ...
}
```

→ Agent 在做"找业务逻辑在哪"类问题时，先查图谱比扫文件高效。

#### 用法 C — Diff Impact 集成进 PR Review

`/understand-diff` 输出的"涟漪范围"可以直接喂给 ice-workbench 的 [`pr-feedback-loop`](../../CLAUDE.md) 流程，让 review 之前先看到"这次改动**理论上**影响哪些下游"。

### 6.3 和 Agent 范式的对应（[`agent-llm/`](../agent-llm/)）

Understand Anything 是 [`react-and-variants.md`](../agent-llm/agents/react-and-variants.md) 里 **"Multi-Agent + Plan-and-Execute" 的混合实例**：

```
Plan-and-Execute 外层：
  project-scanner（先扫一遍）
    ↓
  按 file 分发
    ↓
Multi-Agent 内层：
  file-analyzer × N（并行）
    ↓
  architecture-analyzer
    ↓
  tour-builder + graph-reviewer
```

这是把 [react-and-variants.md §10 "把这些范式拼起来用"](../agent-llm/agents/react-and-variants.md) 落到一个具体可读源码的范例——值得拆开看每个 Agent 的 prompt 怎么写、每个 Agent 怎么协作。

---

## 七、典型使用流（PM 视角）

```
□ 1. clone Understand Anything 进任意 Claude Code 工作区
□ 2. /understand --language zh 在自己关心的代码库（比如 ice-workbench）跑一次
□ 3. /understand-dashboard 打开看整体形状
□ 4. /understand-onboard 生成新人指南（PM 也是新人——读这份比读 README 快）
□ 5. /understand-domain 切到业务域视图，对照 PRD 看代码是不是按 PRD 切的
□ 6. /understand-chat "<问任何业务问题>" → 直接问图
□ 7. 把 .understand-anything/knowledge-graph.json commit 进团队仓库，新人复用
□ 8. 启 /understand --auto-update，post-commit hook 让图随代码同步
```

---

## 八、相关链接

- 项目：[github.com/Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything)
- 官网：[understand-anything.com](https://understand-anything.com)
- Live Demo：[understand-anything.com/demo/](https://understand-anything.com/demo/)
- 团队共享样例：[Lum1104/microservices-demo](https://github.com/Lum1104/microservices-demo)（Go / Java / Python / Node 多语言项目，已 commit 图）
- 社区视频（Better Stack）：[YouTube 演示](https://www.youtube.com/watch?v=VmIUXVlt7_I)
- Karpathy LLM Wiki 模式（被 `/understand-knowledge` 支持）：[gist 原文](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

### 在本工作区的衔接

- 多 Agent 范式：[`../agent-llm/agents/react-and-variants.md`](../agent-llm/agents/react-and-variants.md)
- 知识检索 vs 知识图谱：[`../agent-llm/agents/openviking-vs-hindsight.md`](../agent-llm/agents/openviking-vs-hindsight.md)
- 应用对象：[`../ice-workbench/`](../ice-workbench/)
