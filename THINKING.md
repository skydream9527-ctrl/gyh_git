# 🧠 这个仓库是什么 —— 我的思考与探索空间

> **一句话定位**：这是我的个人知识/思考工作台。**思考记录是主体，工程代码是参考副本。**
> ICE Workbench 的开发正本在 `https://git.n.xiaomi.com/gongyunhe/ice-workbench`，这里只放快照供参考。

打开本仓库先看本文件，再按需跳转。

---

## 一、我在哪里记录什么（统一落点）

> 借助这个项目探索和思考时，按下表归类，避免散落。

| 我要记的东西 | 放哪里 | 命名约定 |
|---|---|---|
| 日常思考 / 心得 / 洞见 | [Wisdom&Decide/insights/](Wisdom&Decide/insights/) | `YYYY-MM-DD-主题.md` |
| 重要决策（有备选、有取舍） | [Wisdom&Decide/decisions/](Wisdom&Decide/decisions/) `YYYY-MM/` | `YYYY-MM-DD-决策主题.md` |
| 领域知识沉淀 | [project/](project/) 下对应领域目录 | 自由 |
| 学习笔记 | `Wisdom&Decide/notes/`（建议新建） | 自由 |
| 会议纪要 | `project/data-product-workspace/04-会议纪要/` | 自由 |
| 复盘 / 个人成长 | `project/data-product-workspace/05-个人成长/` | 自由 |
| Prompt 模板 | [prompts/](prompts/) | 场景名.md |

**日常思考的默认落点是 `Wisdom&Decide/insights/`，文件名一律 `YYYY-MM-DD-主题.md`。**

---

## 二、仓库三层结构

```
pm-workspace-starter/
├── 🧠 Wisdom&Decide/      # 思考中心（决策地图 + 全景导航 + SOP + insights + decisions）
├── 📚 project/            # 知识沉淀（13 个领域目录，全 .md）+ 产品项目 + 工作区
├── 💻 backend/ frontend/ agents/ skills/   # ICE Workbench 工程参考副本
├── 📄 USER.md MEMORY.md AGENTS.md CLAUDE.md  # AI 协作配置
└── 📄 THINKING.md         # 本文件（思考空间总入口）
```

1. **🧠 思考中心**：[Wisdom&Decide/](Wisdom&Decide/) — `00-我是谁与我的决策地图` / `01-我的项目全景导航` / `02-决策工作流SOP` 是核心三件套
2. **📚 知识沉淀**：[project/](project/) 下 13 个领域目录（ab-testing / agent-llm / ai-infra-knowledge / causal-inference / cybernetics / data-analysis / decision-frameworks / event-tracking / LLM_thinking / management-work / multica / product / understand-anything），全部 .md
3. **💻 工程参考**：根目录 `backend/frontend/agents/skills` + `project/ice-workbench*` — ICE Workbench 副本，**开发正本在 GitLab**，这里不改代码

---

## 三、工程代码副本说明（重要 —— 体量来源）

ICE Workbench 在本仓库有 **3 份参考副本**（同一套代码的多个时间快照，`design_decisions.md` 均为 2098 行）：

| 副本位置 | 快照时间 | 文件量 | 说明 |
|---|---|---|---|
| 根目录 `backend/frontend/agents/skills` | 2026-06-05 | ~260 | [README.md](README.md) / [CLAUDE.md](CLAUDE.md) 引用的"主工程" |
| [project/ice-workbench/](project/ice-workbench/) | 2026-05-27 | 609 | 有 [_NOTE.md](project/ice-workbench/_NOTE.md) 拷贝说明 |
| [project/ice-workbench-new/](project/ice-workbench-new/) | 2026-06-29 | 2890 | 最新最全快照 |

另：[project/data-product-workspace/](project/data-product-workspace/) 名为"工作区"，实混入约 2400 个 `.ts/.tsx/.py` 工程代码文件。

**这三份 + 混入代码 ≈ 仓库 80%+ 文件量**，是 402M / 10544 文件的主因。开发正本不在这里，副本只供阅读参考。

### 去重建议（待你确认，未执行）

- **保留 1 份**最新最全的参考副本 → 推荐 [project/ice-workbench-new/](project/ice-workbench-new/)（06-29）
- 根目录工程代码 + [project/ice-workbench/](project/ice-workbench/) + data-product-workspace 混入代码 → 删除，或统一移至 `archive/`
- 若删根目录工程，需同步把 [README.md](README.md) / [CLAUDE.md](CLAUDE.md) 的工程引用改指向保留的那份（或把工程 README/CLAUDE 移进保留副本，根目录只留思考层）

---

## 四、待整理清单（建议，待你确认，未执行）

| 项 | 现状 | 建议 |
|---|---|---|
| 根 [decisions/](decisions/) | 3 个文件（竞品分析 / 打分方法论 / 算法研究），实为研究参考，非决策 | 按主题归入 [references/](references/) 或 `project/` 对应领域；空目录删除。**不要**塞进 `Wisdom&Decide/decisions/`（那是决策归档） |
| [references/](references/) vs [reference/](reference/) | 名字易混：前者是阅读参考资料（6 个），后者是工程路由映射 `api-map`/`route-map`（2 个） | 保留两者；可把 `reference/` 改名 `engineering-ref/` 以区分（注意 [README.md](README.md) 里有链接需同步改） |
| [memory/](memory/) | 空（仅 `.gitkeep`），与根 [MEMORY.md](MEMORY.md) 职责重叠 | 删除 `memory/`，长期记忆统一走 `MEMORY.md` |
| [your-domain/](your-domain/) | 空占位（`context.md` + 空 decisions/reviews） | 删除，或明确用途 |
| [knowledge-base/](knowledge-base/) vs `project/` 知识类 | 主题重叠（都有 Agent / RAG / Skill 知识） | 长期目标是合并到 `project/` 对应领域；本轮不动，先靠 [01-我的项目全景导航.md](Wisdom&Decide/01-我的项目全景导航.md) 索引串联 |
| `Wisdom&Decide/feishu-part5~8.md` | 学习笔记散在思考中心根目录 | 归入新建的 `Wisdom&Decide/notes/` |

> 以上任何一项，你说"按建议执行"我就动手；不想动的保持原样。

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
