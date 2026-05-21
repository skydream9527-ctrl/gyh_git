# PM 工作区模板 — 5 分钟快速开始

## 第一步：克隆仓库

```bash
git clone {仓库地址}
```

用 Trae IDE 打开这个文件夹。

## 第二步：填写你的画像（2 分钟）

打开 `USER.md`，填好你的角色、业务、偏好。只需要填一次，以后每次对话 AI 都会记住。

把 `your-domain/` 文件夹重命名为你的业务名，例如 `ecommerce/`、`search/`、`content/`。这个文件夹用来放你的业务文档。

## 第三步：开始工作

在 Trae IDE 对话框中，直接说你想做什么：

| 你说的话 | AI 会做什么 |
|---------|------------|
| 「帮我写一份 PRD，功能是 XX」 | 自动读取 `prompts/prd-write.md` 模板生成 PRD |
| 「分析一下 XX 竞品最近更新」 | 自动读取 `prompts/competitor-analysis.md` 生成竞品分析 |
| 「整理这份用户反馈，提炼核心痛点」 | 自动读取 `prompts/user-insight.md` 提炼洞察 |
| 「把这个功能拆成用户故事」 | 自动读取 `prompts/user-story.md` 拆解 |
| 「整理今天的会议纪要」 | 自动读取 `prompts/meeting-notes.md` 生成纪要 |
| 「把这周的工作写成周报」 | 自动读取 `prompts/weekly-report.md` 生成周报 |
| 「帮我查一下 XX 数据」 | 自动读取 `prompts/data-analysis.md` 写 SQL 并解读 |

> **不用每次都说「读取 prompts/xxx」**，AI 会根据你的请求自动匹配对应模板。

---

## 你的文件夹怎么用

```
├── AGENTS.md       ← AI 的大脑，记录行为规则和踩坑（自动更新，别删）
├── MEMORY.md       ← AI 的记忆索引（自动更新，别删）
├── USER.md         ← 你的画像（填一次就行）
├── prompts/        ← Prompt 模板库，拿来就用，也可以自己加
├── memory/         ← 每日对话记录（自动生成）
├── decisions/      ← 重要决策放这里
├── your-domain/    ← 重命名为你的业务名，例如 ecommerce/、search/
└── .ai/            ← AI 内部配置，不用管
```

---

## 越用越好用的秘密

每次对话结束后，AI 会自动：

1. 把你的新偏好写进 `AGENTS.md`（下次就不会忘了）
2. 把你做的决策写进 `MEMORY.md`（下次对话 AI 会参考）
3. 把对话摘要写进 `memory/YYYY-MM-DD.md`（需要时可回溯）

> 用得越多，AI 越懂你。这不是一次性工具，是和你一起成长的工作伙伴。

---

## 进阶

### 创建你的专属 Prompt 模板

打开 `prompts/` 文件夹，参考已有模板的格式，创建你自己的场景模板。

模板格式：

```
背景 → 目标 → 约束 → 输出要求
```

用 `{ }` 标记需要替换的参数。

### 飞书 MCP 配置

本模板自带飞书文档写入能力。在 Trae IDE 中配置飞书 MCP 后，可以直接让 AI 帮你写飞书文档。

---

## 常见问题

**Q: 和 GM 的工作区什么关系？**

A: GM 的工作区是「战略指挥中心」，这个模板是「个人生产力座舱」。你不需要学 GM 那套复杂的 Agent 系统。

**Q: AGENTS.md 和 MEMORY.md 我能删吗？**

A: 别删。它们是 AI 长期记住你的关键。删了就是让 AI 失忆。

**Q: Prompt 模板不够用怎么办？**

A: 在 `prompts/` 下创建新的 `.md` 文件，用「背景→目标→约束→输出要求」格式即可。

**Q: 需要学 Skill / Workflow / Role 这些概念吗？**

A: 不需要。你只需要理解三个文件：AGENTS.md、MEMORY.md、USER.md。