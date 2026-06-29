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

**Python 层也有 `MemoryWriter`**（见 `backend/app/services/context_svc.py`），适合脚本 / 测试 / 批量迁移场景：

```python
from app.services.context_svc import ContextPaths, MemoryWriter

writer = MemoryWriter(ContextPaths(user_id=..., agent_id=..., task_id=...))
writer.save_memory(
    scope="user",
    slug="...",
    title="...",
    hook="...",
    type_="feedback",
    body="...",
)
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

`backend/app/services/agent_prompt_builder.py` 在 `build_base_prompt()` 中组装以下层（从上到下）：

1. Identity（`agent/prompt/identity.md` 或整个 `system.md`）
2. Rules（`agent/prompt/rules.md`，可选）
3. **User Memory**（`users/{uid}/memory/` 展开）
4. **Agent Memory**（`users/{uid}/memory/agents/{agent_id}/` 展开）
5. **Task State**（`tasks/{tid}/STATE.md` 全文）
6. Recent Context（`SessionStore.get_recent_memory(session_id)`，当前会话窗口）
7. Skills Snapshot
8. Active Skill Instructions
9. Tool Allowlist

3/4/5 任一层为空时跳过。实际读文件由 `backend/app/services/context_svc.py` 的 `ContextLoader` 完成。

---

## 与现有基础设施的关系

- **`users/{uid}/profile.json` / `settings.json`**：偏静态的用户配置（邮箱、默认模型、主题）。Memory 与之互补：profile 是用户主动填的注册信息，memory 是 agent 在协作中沉淀的隐性知识。
- **`tasks/{tid}/snapshot.json`**：对话/工具调用的结构化快照，由 runtime 写入。Task State 是 agent 主动维护的「当前语义进度」，snapshot 是事实流水，不重叠。
- **`tasks/{tid}/experience_cards.json`**：用户明确沉淀的经验卡片。Memory 是 agent 自动沉淀的隐式经验，粒度更细，写入门槛更低。

---

## P0 增强（2026-06）

以下扩展向后兼容：旧格式 memory 文件仍可正常读写，新字段为可选。

### Memory 生命周期元数据

单条 Memory 文件的 frontmatter 扩展了 **lifecycle metadata**：

```markdown
---
name: report-style-preference
description: 该用户偏好的分析报告风格
created_at: 2026-04-10T08:00:00+00:00
updated_at: 2026-06-15T03:22:00+00:00
metadata:
  type: feedback
  confidence: 0.95
  usage_count: 12
  last_hit_at: 2026-06-15T03:22:00+00:00
---
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `created_at` | ISO timestamp | 首次写入时间 |
| `updated_at` | ISO timestamp | 最近一次修改时间 |
| `metadata.confidence` | float 0.0–1.0 | 置信度，新创建默认 1.0 |
| `metadata.usage_count` | int | 被检索命中的累计次数 |
| `metadata.last_hit_at` | ISO timestamp | 最近一次被检索命中的时间 |

- 旧文件缺少这些字段时，读取侧以默认值（confidence=1.0, usage_count=0）处理
- `memory_save` 工具在 upsert 时保留已有的 lifecycle 字段（不会重置计数器）

### BM25 智能检索（替代关键词子串匹配）

检索时 ContextLoader 不再使用固定 `limit=5` + 简单 token 交集，改为：

1. **BM25 打分**：对 `slug + title + hook` 构建小型语料库，用 Okapi BM25 计算相关度
2. **Composite 评分**：`score = BM25 × confidence_factor × recency_boost`
   - `confidence_factor` = 0.5 + 0.5 × confidence（范围 0.5–1.0）
   - `recency_boost` = 指数衰减，半衰期 14 天（无 hit 历史时为 0.7）
3. **Token budget 动态截断**：按注入上下文的 char 预算（默认 4000 chars）动态选取条目，而非固定条目数

无 query 时按 `confidence × recency` 排序。

实现模块：`backend/app/services/task/memory_ranking.py`

### Task State 增量历史（HISTORY.jsonl）

`task_state_save` 每次写入 STATE.md 时，同步 append 一条记录到 `tasks/{tid}/HISTORY.jsonl`：

```json
{"ts": "2026-06-15T03:22:00+00:00", "agent_id": "data-analysis", "checksum": "a3f8b2c1e4d9", "size_bytes": 312, "had_previous": true}
```

| 字段 | 说明 |
|---|---|
| `ts` | 写入时间 |
| `agent_id` | 执行写入的 agent |
| `checksum` | STATE.md 内容的 SHA256 前 12 位 |
| `size_bytes` | 内容字节数 |
| `had_previous` | 是否存在前序版本（首次写入为 false） |

用途：
- 追溯任务进度变更时间线（尤其 compaction 后原始对话不可恢复时）
- 调试 agent 行为：哪个 agent 在什么时候改了 STATE

STATE.md 本身仍是全文覆盖快照，行为不变。

---

## P1 增强（2026-06）

### Team Memory 层

在 User/Agent Memory 之上新增 **Team Memory**，作为团队级共享知识层：

```
teams/{team_id}/
├── meta.json          # {"id", "name", "members": [...]}
└── memory/
    ├── MEMORY.md      # 索引（与用户 memory 格式相同）
    └── *.md           # 独立条目
```

| 层 | 路径 | 作用域 | 写入方 |
|---|---|---|---|
| **Team Memory** | `teams/{team_id}/memory/` | 团队内所有成员 × 所有 agent | admin / auto-promote |

- 用户的 team 由 `users/{uid}/profile.json.team` 字段决定
- Runtime 自动检测用户所属 team，注入 Team Memory 到 system prompt
- 注入优先级（从高到低）：Task State > Agent Memory > User Memory > **Team Memory**
- 用途：团队级口径定义、公共 feedback、项目背景

### Visibility 字段

单条 Memory 的 frontmatter 新增 `metadata.visibility`：

```yaml
metadata:
  type: feedback
  visibility: team    # private | team | org
```

| 值 | 含义 |
|---|---|
| `private` | 仅当前用户可见（默认，向后兼容） |
| `team` | 同 team 成员可见 |
| `org` | 全组织可见（预留，P1 暂不实现读取） |

- `memory_save` 工具新增可选参数 `visibility`（默认 `"private"`）
- 旧文件缺少该字段时视为 `private`

### ContextLoader 四层注入

```
# Runtime Context

## User Global Memory        ← L2
## Agent Memory              ← L3
## Team Memory ({team_id})   ← L1 (新增)
## Task State                ← L4
```

注入代码在 `ContextLoader.build_context_section` 中：
- 用户有 team → 调 `team_memory.load_team_memory_section(team_id, query)`
- 无 team → 跳过（best-effort，不阻塞 prompt assembly）

### Knowledge Imports（跨 Agent 知识引用）

Agent 可在 `agent.json` 声明对其他 Agent knowledge 目录的只读引用：

```json
{
  "knowledge_imports": [
    "data-analysis/knowledge/metrics",
    "ab-experiment/knowledge/rules"
  ]
}
```

- 声明后，`read_agent_knowledge` 工具可跨 agent 读取指定子路径
- 未声明的 import 会被拒绝（防止无约束的跨 agent 数据访问）
- 实现模块：`backend/app/services/agent/knowledge_import.py`

---

## P2 增强（2026-06）

### Memory 生命周期管理器

新增 `backend/app/services/task/memory_manager.py`，提供自动化的 memory 清理和晋升：

#### 衰减（Decay）

- 仅作用于 `metadata.type: project` 类型条目
- `last_hit_at` 超过 **30 天**未命中 → 标记 `metadata.status: stale`
- stale 标记超过 **7 天**无人确认 → 移入 `archive/` 子目录，从 MEMORY.md 索引中移除
- 归档文件不删除，可人工恢复

```
users/{uid}/memory/
├── MEMORY.md
├── active-entry.md
└── archive/
    └── stale-entry.md    ← 归档后的位置
```

#### Auto-Promote（自动晋升）

当同一个 Agent Memory 条目（相同 slug）满足以下条件时，自动晋升到 Team Memory：

| 条件 | 阈值 |
|---|---|
| `usage_count` | >= 3 |
| 拥有该条目的 distinct users | >= 2 |

晋升动作：
1. 调用 `promote_to_team(agent_id, team_id)` 扫描所有用户的 agent memory
2. 满足条件的条目写入 `teams/{team_id}/memory/`
3. 原始 agent memory 保留不动（用户仍可本地覆盖）
4. 支持 `dry_run=True` 预览待晋升列表

### Sub-Agent Feedback Loop

新增 `backend/app/services/task/subagent_feedback.py`，在 `spawn_subagent` 返回后自动提取可复用结论：

```python
from app.services.task.subagent_feedback import extract_and_save_insights

saved = extract_and_save_insights(
    sub_agent_id="data-analysis",
    result_text=sub_run_result["final_text"],
    task_description="分析 CC DAU 下跌",
    user_id=user_id,
    parent_agent_id="general",
)
```

提取逻辑：
1. 匹配结构化结论段落（`## 结论`、`**结论：**`、`## Key Finding` 等）
2. 匹配决定性表述（`因此，`、`综上：`、`Therefore,` 等）
3. 过滤掉纯程序性输出（SQL 表格、原始数据）

提取的 insight 以 `confidence=0.7` 存入 parent agent 的 Agent Memory，slug 含内容 hash 保证幂等。随着被多次命中 usage_count 自然增长，最终可触发 auto-promote 到 Team Memory。

---

## P3 增强（2026-06）

### Phase-Aware Tool Profiles

Agent 可在 `agent.json` 中声明按 phase 切换的工具子集：

```json
{
  "tool_profiles": {
    "planning": ["now", "read_file", "read_skill", "todo_write", "exit_plan_mode"],
    "execution": ["*"],
    "review": ["read_file", "kyuubi_query", "memory_save"]
  }
}
```

运行时行为：
1. 从 `STATE.md` 自动检测当前 Phase（数字映射：1-2→planning, 3-5→execution, 6+→review）
2. 也可由调用方显式传入 `phase` 参数
3. `"*"` 表示不限制（暴露全部 base tools）
4. profile 中不在 base `tools` 列表里的工具会被过滤（交集语义）
5. 未声明 `tool_profiles` 的 agent 行为不变

实现模块：`backend/app/services/agent/tool_profiles.py`

### Skill Overlay Per-Team

团队可为全局 skill 提供覆盖层，无需 fork 整个 skill：

```
teams/{team_id}/
└── skill_overlays/
    ├── kyuubi.md               # append 模式
    └── nl-mapping-table-sql.md # replace_section 模式
```

Overlay 文件支持两种模式：

| Mode | 行为 |
|---|---|
| `append` (默认) | overlay 内容追加到 SKILL.md 末尾 |
| `replace_section` | 替换 SKILL.md 中指定 heading 的段落 |

Overlay frontmatter 格式：
```yaml
---
mode: replace_section
target_section: 表名映射
---
```

运行时由 `read_skill` 工具在返回前自动合并（需要 caller 传入 team_id）。

实现模块：`backend/app/services/agent/skill_overlay.py`

### Sub-Agent Feedback Loop 接入

`spawn_subagent` 工具在子 agent 成功返回后，自动调用 feedback loop：

```
spawn_subagent 返回 final_text
    ↓
subagent_feedback.extract_and_save_insights(...)
    ↓ (best-effort, 不阻塞返回)
提取结论 → memory_save(scope="agent", confidence=0.7)
    ↓ (随使用积累)
usage_count 增长 → 触发 auto-promote → Team Memory
```

hook 位置：`backend/app/services/llm/tools/workflow.py` 的 `_tool_spawn_subagent` 返回前。
