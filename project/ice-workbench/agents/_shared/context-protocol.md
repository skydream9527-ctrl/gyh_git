# Agent Context Protocol

> 参考 Claude Code 的 memory 机制，给 workbench 的所有 agent 提供一套**跨会话上下文**协议。

每个 agent 都遵守本协议；agent 自己的 `prompt/system.md` 只声明「本 agent 在各层 memory 里关心哪些字段」，不重复描述协议本身。

---

## 三层上下文

| 层 | 路径 | 作用域 | 生命周期 | 读写时机 |
|---|---|---|---|---|
| **User Global Memory** | `users/{uid}/memory/MEMORY.md` + 同目录 `*.md` | 当前用户，跨 agent、跨任务 | 持久 | 每次对话开头自动注入；用户说「记住…」/ 明显偏好时写入 |
| **Agent Memory** | `users/{uid}/memory/agents/{agent_id}/MEMORY.md` + 同目录 `*.md` | 当前用户 × 当前 agent | 持久 | 每次对话开头自动注入；agent 完成一次工作、识别到可复用领域经验时写入 |
| **Task State** | `tasks/{tid}/STATE.md` | 当前任务（单一对话上下文） | 临时（任务生命周期） | 每轮对话起始读、每个 Phase/Step 切换后刷新 |

三层都由 runtime 在 `PromptBuilder` 里自动注入进 system prompt，agent 不需要主动调 `read_file` 拉 memory 内容（但**写**仍由 agent 用 `write_file` 托管）。

---

## Memory 类型（User / Agent 层通用）

延用 Claude Code 的四类：

| 类型 | 用途 | 举例 |
|---|---|---|
| `user` | 用户身份 / 角色 / 技能背景 | "user 是 PM，主看 CC 业务线，汇报对象副总裁" |
| `feedback` | 用户纠偏 / 肯定的行为规则 | "报告不要把 SQL 放在正文，统一塞附录" |
| `project` | 当前项目 / 组织 / 进行中工作背景 | "Q2 主攻视频体裁，v7.2 灰度冲突中" |
| `reference` | 指向外部资源的指针 | "团队周报模板：`feishu://wiki/xxx`" |

**不要存**：
- SOP / 行为规则（固化在 `system.md`，不是 memory）
- 可当场从 kyuubi / 代码 / git 查出的事实
- 当前对话窗口内已讨论的细节
- 过期的 / 不再有效的规则

---

## MEMORY.md 索引格式

`users/{uid}/memory/MEMORY.md` 与 `users/{uid}/memory/agents/{agent_id}/MEMORY.md` 都是索引文件，一行一条，控制在 200 行以内：

```markdown
- [用户身份与角色](user_profile.md) — 资深 PM，主看内容中心，汇报对象副总裁
- [报告风格偏好](feedback_report_style.md) — 结论先行，SQL 进附录
- [Q2 主攻方向](project_q2_focus.md) — 视频体裁 + 深度 DAU
```

索引文件本身**没有 frontmatter**，只有链接列表。

---

## 单条 Memory 文件格式

每条 memory 独立存文件，带 YAML frontmatter：

```markdown
---
name: report-style-preference
description: 该用户偏好的分析报告风格
metadata:
  type: feedback
---

用户要求：分析报告正文保持结论先行，SQL / 口径细节统一塞入附录；PM 读者场景下附录默认折叠。

**Why**：2026-04 第一次合作时用户明确反馈"我不想在正文里看 SQL，有结论和数据就够了"。

**How to apply**：Phase 5 综合报告的角色自适应按此细化，不再每次问用户 SQL 放哪。

相关：[[reader-role-default]]
```

- `name`：kebab-case，与文件名同（不含 `.md`）
- `description`：一句话摘要，未来判断是否命中用
- `metadata.type`：四类之一
- 正文：`feedback` / `project` 类型建议带 **Why** + **How to apply** 两行
- 用 `[[slug]]` 关联其他 memory，slug 不存在也可写，表示待补

---

## Task State 格式（STATE.md）

`tasks/{tid}/STATE.md` 是单文件 markdown，半结构化。由 agent 维护，不带 frontmatter：

```markdown
# Task State

- **Agent**: data-analysis
- **Phase**: 4 (SQL 执行中)
- **Updated**: 2026-05-14T10:23:00+08:00

## 分析命题
定位 CC 消费 UV 近 14 天环比下跌 5% 的主因，用于是否回滚 v7.2 决策。

## 任务拆解
- [x] T1. 主指标复核
- [x] T2. 分频道拆解
- [ ] T3. 分体裁拆解（挂起，SQL 已生成未执行）
- [ ] T4. 新老用户拆解
- [ ] T5. 版本关联

## 挂起项
T3 SQL 已经让用户确认口径，等用户回「继续」再调 kyuubi。

## 关键决策
- 2026-05-14 用户选定读者=PM+分析师 混合
- 2026-05-14 业务线阈值套 CC 默认 8%，T2 触发追加下钻
```

每个 agent 在自己的 `system.md` 里声明**本 agent 关心的 STATE 字段**（不同 agent 字段不同）。

---

## 读写规则

### 读（对话开头自动注入）

runtime 按 `users/{uid}/memory/MEMORY.md` → 索引引用的文件 → `users/{uid}/memory/agents/{agent_id}/MEMORY.md` → 其子文件 → `tasks/{tid}/STATE.md` 的顺序，拼成 system prompt 的 Context 段。Agent 不需要主动读；读到的内容**视作上下文已知**。

### 写 User Global Memory（`users/{uid}/memory/`）

**触发**：
- 用户明确说「记住 X」「以后都 Y」
- 用户纠正 agent 的某条行为（feedback）
- 用户肯定一个非显而易见的选择（也存 feedback，避免下次误退）

**写入方式：调 `memory_save` 工具**（RuntimeFacade 默认注册给每个 agent，LLM 直接 tool-call）：

```json
{
  "tool": "memory_save",
  "arguments": {
    "scope": "user",
    "slug": "report-style-preference",
    "title": "报告风格偏好",
    "hook": "结论先行，SQL 进附录",
    "type": "feedback",
    "body": "用户要求：正文只放结论和数据，SQL 全进附录。\n**Why**: ...\n**How to apply**: ..."
  }
}
```

一次调用等价于：
1. 原子写 `users/{uid}/memory/{slug}.md`（frontmatter + 正文）
2. 原子 upsert `users/{uid}/memory/MEMORY.md`（slug 已存在则更新，否则追加）

删除用 `memory_delete` 工具（参数 `scope` + `slug`），会同步从索引里清除。

**Python 层也有 `MemoryWriter`**（见 `context.py`），适合脚本 / 测试 / 批量迁移场景：

```python
from agents._shared.context import ContextPaths, MemoryWriter

writer = MemoryWriter(ContextPaths(workspace_root=..., user_id=..., agent_id=..., task_id=...))
writer.save_user_memory(slug="...", title="...", hook="...", type_="feedback", body="...")
```

**手动 `write_file` 两次也允许**（极少数特殊情况），但写入者自己要保证：
- frontmatter 的 `name` 与文件 slug 一致
- MEMORY.md 索引行格式是 `- [{title}]({slug}.md) — {hook}`
- 不在 MEMORY.md 里直接写 memory 正文内容

### 写 Agent Memory（`users/{uid}/memory/agents/{agent_id}/`）

**触发**：
- 完成一次工作后识别到**领域专属**可复用信息（不是通用偏好）
- 例：ab-experiment 记「该用户常看的实验 ID 空间」，data-analysis 记「常用对比窗口习惯 7/14 天」

API 与 User Global Memory 对称：
- Tool 调用：`memory_save` 传 `scope: "agent"` 即可
- Python：`writer.save_agent_memory(...)` / `writer.delete_agent_memory(slug)`

落地目录换为 `users/{uid}/memory/agents/{agent_id}/`。

### 写 Task State（`tasks/{tid}/STATE.md`）

**触发**：
- 每次 Phase / Step 转换
- 用户做出关键决策（业务线、读者角色、拆解清单变更等）
- 挂起项变化（agent 跳转、等用户回复、异常门卡住）

**写入方式**：
- Tool 调用：`task_state_save(content)`
- Python：`writer.save_task_state(content)`

全文覆盖，不做增量追加。单文件保持 100 行以内。

### 写入前规则

- **不存已固化的规则**：`system.md` 里已写的 SOP / 约束，不要再抄到 memory
- **不存过期信息**：发现 memory 过时先更新或删除，不要新增冲突条目
- **不存敏感数据**：密码、API key、用户私人信息等绝不写入

---

## 访问前验证

Memory 是「写入时」的快照，读取时可能已过期。使用前验证：

- memory 指向某个具体 wiki/doc/实验 ID → 使用前 `feishu fetch` 或 kyuubi 查一下仍然有效
- memory 总结「当前状态」（如「v7.2 灰度中」）→ 时间久了要回头查 git / kyuubi / 飞书最新状态
- 与当前 kyuubi 查询结果冲突 → 以查询结果为准，顺手更新或删除 stale memory

---

## Runtime 注入点

`agents/_shared/prompt_builder.py` 在 `build()` 中组装以下层（从上到下）：

1. Identity（`agent/prompt/identity.md` 或整个 `system.md`）
2. Rules（`agent/prompt/rules.md`，可选）
3. **User Memory**（`users/{uid}/memory/` 展开）
4. **Agent Memory**（`users/{uid}/memory/agents/{agent_id}/` 展开）
5. **Task State**（`tasks/{tid}/STATE.md` 全文）
6. Recent Context（`SessionStore.get_recent_memory(session_id)`，当前会话窗口）
7. Skills Snapshot
8. Active Skill Instructions
9. Tool Allowlist

3/4/5 任一层为空时跳过。实际读文件由 `agents/_shared/context.py` 的 `ContextLoader` 完成。

---

## 与现有基础设施的关系

- **`users/{uid}/profile.json` / `settings.json`**：偏静态的用户配置（邮箱、默认模型、主题）。Memory 与之互补：profile 是用户主动填的注册信息，memory 是 agent 在协作中沉淀的隐性知识。
- **`tasks/{tid}/snapshot.json`**：对话/工具调用的结构化快照，由 runtime 写入。Task State 是 agent 主动维护的「当前语义进度」，snapshot 是事实流水，不重叠。
- **`tasks/{tid}/experience_cards.json`**：用户明确沉淀的经验卡片。Memory 是 agent 自动沉淀的隐式经验，粒度更细，写入门槛更低。