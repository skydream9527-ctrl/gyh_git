# 🧠 这个仓库是什么 —— 我的思考与探索空间

> **一句话定位**：这是我的个人知识/思考工作台。**思考记录是主体，工程代码是参考副本。**
> ICE Workbench 的开发正本在 `https://git.n.xiaomi.com/gongyunhe/ice-workbench`，这里只保留一份快照供参考。

打开本仓库先看本文件，再按需跳转。

---

## 一、我在哪里记录什么（统一落点）

> 借助这个项目探索和思考时，按下表归类，避免散落。

| 我要记的东西 | 放哪里 | 命名约定 |
|---|---|---|
| 日常思考 / 心得 / 洞见 | [Wisdom&Decide/insights/](Wisdom&Decide/insights/) | `YYYY-MM-DD-主题.md` |
| 重要决策（有备选、有取舍） | [Wisdom&Decide/decisions/](Wisdom&Decide/decisions/) `YYYY-MM/` | `YYYY-MM-DD-决策主题.md` |
| 领域知识沉淀 | [project/](project/) 下对应领域目录 | 自由 |
| 学习笔记 | [Wisdom&Decide/notes/](Wisdom&Decide/notes/) | 自由 |
| 会议纪要 | `project/data-product-workspace/04-会议纪要/` | 自由 |
| 复盘 / 个人成长 | `project/data-product-workspace/05-个人成长/` | 自由 |
| Prompt 模板 | [prompts/](prompts/) | 场景名.md |

**日常思考的默认落点是 `Wisdom&Decide/insights/`，文件名一律 `YYYY-MM-DD-主题.md`。**

---

## 二、仓库三层结构

```
pm-workspace-starter/
├── 🧠 Wisdom&Decide/      # 思考中心（决策地图 + 全景导航 + SOP + insights + decisions + notes）
├── 📚 project/            # 知识沉淀（13 个领域目录，全 .md）+ 产品项目 + 工作区
│   └── ice-workbench-new/ # ICE Workbench 工程参考副本（唯一）
├── 📚 knowledge-base/     # 结构化知识库
├── 📄 prompts/ references/  # 模板 / 阅读参考 / 工具调研（engineering-ref 已归入 ice-workbench-new/）
├── 📄 USER.md MEMORY.md AGENTS.md CLAUDE.md  # AI 协作配置
└── 📄 THINKING.md         # 本文件（思考空间总入口）
```

1. **🧠 思考中心**：[Wisdom&Decide/](Wisdom&Decide/) — `00-我是谁与我的决策地图` / `01-我的项目全景导航` / `02-决策工作流SOP` 是核心三件套
2. **📚 知识沉淀**：[project/](project/) 下 13 个领域目录（ab-testing / agent-llm / ai-infra-knowledge / causal-inference / cybernetics / data-analysis / decision-frameworks / event-tracking / LLM_thinking / management-work / multica / product / understand-anything），全部 .md
3. **💻 工程参考**：[project/ice-workbench-new/](project/ice-workbench-new/) — ICE Workbench 唯一参考副本，**开发正本在 GitLab**，这里不改代码

---

## 三、工程代码（已去重）

ICE Workbench 的开发正本在 `https://git.n.xiaomi.com/gongyunhe/ice-workbench`。本仓库**只保留 1 份参考副本**：

| 位置 | 说明 |
|---|---|
| [project/ice-workbench-new/](project/ice-workbench-new/) | 2026-06-29 快照，最新最全；工程架构见其 [CLAUDE.md](project/ice-workbench-new/CLAUDE.md) / [design_decisions.md](project/ice-workbench-new/design_decisions.md) |

已清除的冗余副本（共 ~6900 文件）：根目录 `backend/frontend/agents/skills`、`cc-recovered-main/`、`project/ice-workbench/`、`project/data-product-workspace/01-业务项目/ICE-Data-Workbench-v3/`，以及根目录工程基建（Dockerfile / Makefile / deploy.sh / docker-compose.yml / .env.example / design_decisions.md / requirements / design）。

> 工程代码不在本仓库修改。看实现去 [project/ice-workbench-new/](project/ice-workbench-new/)，改代码去 GitLab 正本。

---

## 四、已整理 / 待整理

| 项 | 状态 |
|---|---|
| 根 `decisions/` 3 个研究参考文件 → [references/](references/) | ✅ 已归并，空目录已删 |
| `reference/` → engineering-ref/（区分阅读参考 vs 工程路由映射） | ✅ 已改名，后归入 [project/ice-workbench-new/engineering-ref/](project/ice-workbench-new/engineering-ref/) |
| 2026-07-05 知识体系重构（5 阶段，2038→1279 md，-37%） | ✅ 三层去重 + dpw 瘦身 + data-analysis 整合 + 导航更新 → [notes/2026-07-04-项目结构review](Wisdom&Decide/notes/2026-07-04-项目结构review与家目录git诊断.md) |
| 空 `memory/`（与 MEMORY.md 重叠）、空 `your-domain/`（未填模板） | ✅ 已删 |
| `Wisdom&Decide/feishu-part5~8.md` → [Wisdom&Decide/notes/](Wisdom&Decide/notes/) | ✅ 已归位 |
| 工程副本去重（3 份 + 混入 → 保留 1 份 ice-workbench-new） | ✅ 已完成 |
| [knowledge-base/](knowledge-base/) 与 `project/` 分工 | ✅ 已澄清：knowledge-base=实践记录/调优日志，project/=系统性原理，**互补不合并** → [knowledge-base/README.md](knowledge-base/README.md) |
| 根 [USER.md](USER.md) 画像 | ✅ 已用 data-product-workspace/MEMORY.md 补全（姓名/部门/核心项目/工具/偏好） |
| `project/data-product-workspace/` 自带 AGENTS/MEMORY/WORK-PLAN | ℹ️ 保留：子工作区自洽配置，不与根目录合并 |

---

## 五、AI 协作约定

- 我的画像 → [USER.md](USER.md)；AI 行为规则 → [AGENTS.md](AGENTS.md)；长期记忆 → [MEMORY.md](MEMORY.md)
- 每次对话 AI 先读这三个文件 + 本文件
- 日常思考统一落 [insights/](Wisdom&Decide/insights/)，命名 `YYYY-MM-DD-主题.md`
- 输出风格：先结论后细节、表格优于文字、数据标来源、无数据标「推断」

---

## 六、核心决策原则（反复提醒自己）

1. **AI 做执行，我做判断** —— 重复劳动交 AI，时间留给思考与决策
2. **先结论后细节** —— 任何输出先给结论
3. **表格优于文字** —— 对比、分析尽量用表格
4. **异常必想** —— 方案必须覆盖边界条件
5. **数据说话** —— 引用数据标来源，无数据标「推断」
6. **记录决策** —— 重要决策落地成文件，不靠脑子记
7. **完成比完美重要** —— 70 分就行动，快速迭代
