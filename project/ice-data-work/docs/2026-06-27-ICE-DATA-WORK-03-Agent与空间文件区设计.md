# ICE-DATA-WORK 材料三 · Agent 设计方案 + 工作区/文件区设计方案

- 日期：2026-06-27
- 上级文档：`2026-06-27-ICE-DATA-WORK-设计方案-v1.md`（总纲）
- 关联：材料一（产品/交互）、材料二（技术/ToDo）
- 本文范围：统一 Agent 抽象、Agent/Twin 定义结构、agent.md 与记忆格式、记忆晋升流程、多参与者协作机制、四层空间文件区落地、空间访问控制、端到端实例、内置 Agent 种子
- 决策依据：总纲 D-05/D-06/D-07/D-08 + §4 空间与记忆模型

---

## 1. 统一 Agent 抽象

**Twin 与工具 Agent 是同一抽象的两种 `kind`（D-08）**，共用运行时、agent.md、记忆格式，区别只在归属与特权：

| 维度 | 工具 Agent（kind=tool） | Twin（kind=twin） |
|---|---|---|
| 归属 | 团队/平台共享 | 用户私有（1 user ↔ 1 twin） |
| 落盘 | `agents/{aid}/` | `users/{uid}/twin/` |
| 记忆 | 按用户分区 + 团队共享（D-06） | 用户长期记忆（偏好/决策/上下文） |
| 特权 | 无 | 编排其他 Agent、发起 Approval、读写用户空间 |
| 在对话里 | 一等发言者 | 一等发言者 + 编排者 |

> 好处：不引入第二套运行时，Twin 和工具 Agent 在同一 ReAct 循环、同一上下文里天然共存（复用 ICE `agent_runtime`）。

---

## 2. Agent 定义结构

### 2.1 工具 Agent：`agents/{agent_id}/agent.json`

```json
{
  "id": "data-analysis",
  "name": "数据分析 Agent",
  "kind": "tool",
  "category": "data",
  "owner": { "type": "platform" },
  "connector_type": "builtin",
  "capabilities": ["sql_query", "attribution", "report_draft"],
  "skills": ["kyuubi", "nl-python", "data.an"],
  "input_schema": { "goal": "string", "scope": "object" },
  "output_schema": { "report": "markdown", "findings": "array" },
  "risks": ["data_permission"],
  "default_permission_level": "L2",
  "prompt_version": 7
}
```

伴随文件：`agent.md`（操作手册）、`skills/`、`knowledge/`、`memory/by-user/{uid}/`、`memory/by-team/{tid}/`。

### 2.2 Twin：`users/{user_id}/twin/twin.json`

```json
{
  "id": "twin-u_8f3a",
  "kind": "twin",
  "user_id": "u_8f3a",
  "name": "云荷的分身",
  "profile": { "role": "数据产品", "domain": "增长分析" },
  "goals": ["推进 DAU 归因", "沉淀可复用分析口径"],
  "style": "先结论后细节；表格优先；避免炫酷大屏",
  "permission_level": "L3",
  "maturity_score": 0.42,
  "privileges": ["orchestrate_agents", "request_approval", "rw_user_space", "navigate_ui"]
}
```

> **导航感知与控制（D-12）**：Twin 拥有 `navigate_ui` 特权 + `navigate(page)` 工具。前端在左侧 tab/路由切换时向 Twin 推送 `page_changed` 事件（感知）；用户对 Twin 说"带我去看板"时，Twin 解析意图并调 `navigate("board")` 切换页面（控制）。`navigate` 为低风险纯 UI 动作，不需 Approval；但跨项目/跨空间跳转仍受成员资格约束。

伴随文件：`agent.md`（Twin 操作说明）、`memory/{preferences,decisions,project-context,pinned}.memory.md`。

---

## 3. agent.md 操作手册格式（始终注入）

统一模板（Twin 与工具 Agent 共用，Twin 多"编排与边界"两节）：

```markdown
# <Agent 名称> · 操作手册

## 角色定位
一句话说明这个 Agent 是谁、为谁服务、不做什么。

## 适用任务
- 适合：……
- 不适合：……（引导路由到更合适的 Agent）

## 工作方式
分几步、调用哪些 skill、何时该停下来问用户。

## 输入要求
需要哪些上下文/文件/口径才能开工。

## 输出格式
产出物形态（报告/表格/代码/图表）+ 结构约定。

## 失败处理
常见失败与对应 error_code、可恢复性、建议下一步。

## 约束与边界
权限等级、禁止动作、需要确认的高风险动作。

## （仅 Twin）编排原则
如何选择工具 Agent、如何组合、如何把结果回报给用户。

## （仅 Twin）不可越权边界
绝不替用户最终确认的动作清单。
```

---

## 4. 记忆体系

### 4.1 记忆文件格式：`*.memory.md`

人类可读 + 机器可索引。每个文件是一组记忆条目，条目带元数据；pgvector 按条目 `id` 建向量索引（可重建，守 G3）。

```markdown
---
scope: user_preference
owner: user:u_8f3a
updated_at: 2026-06-27
---

## MEM-7c21  [confidence: high] [verified: 2026-06-27]
用户偏好：先结论后细节，表格优先，避免炫酷大屏。
- tags: [表达偏好, 输出格式]
- source: task:t_DAU0620 / turn:turn_42 / proposer:twin-u_8f3a

## MEM-9a04  [confidence: medium] [verified: 2026-06-20]
DAU 归因优先看：版本冷启动耗时、渠道新增、留存分层。
- tags: [分析口径, DAU]
- source: task:t_DAU0620
```

### 4.2 记忆候选：`tasks/{tid}/memory/candidates.jsonl`（每行一条）

```json
{"id":"cand_01","ts":"2026-06-27T10:12:00Z","proposed_scope":"user_preference","content":"用户偏好：先结论后细节，表格优先。","source":{"task":"t_DAU0620","turn":"turn_42","proposer":"twin-u_8f3a"},"status":"pending"}
{"id":"cand_02","ts":"2026-06-27T10:13:00Z","proposed_scope":"agent_team","content":"DAU 归因先查版本冷启动耗时，命中率高。","source":{"task":"t_DAU0620","proposer":"data-analysis"},"status":"pending"}
```

### 4.3 五种 scope 与落点（总纲 §4.4）

| proposed_scope | 落点 | 是否需审核 |
|---|---|---|
| `user_preference` | `users/{uid}/twin/memory/preferences.memory.md` | 用户本人确认 |
| `agent_user` | `agents/{aid}/memory/by-user/{uid}/usage.memory.md` | 低风险，本人分区 |
| `agent_team` ⭐ | `agents/{aid}/memory/by-team/{tid}/shared.memory.md` | "贡献给团队"，需审核（D-06） |
| `project` | `teams/{tid}/projects/{pid}/shared/memory/shared.memory.md` | 项目 owner/admin |
| `team` | `teams/{tid}/shared/memory/shared.memory.md` | 团队 owner/admin |

### 4.4 记忆晋升流程

```text
对话中 Agent/Twin 调 propose_memory(content, scope)
   → 追加到 tasks/{tid}/memory/candidates.jsonl (status=pending)
   → 镜像为审批项（Twin Dock 待确认 + /approvals）
用户/管理员审批
   → 通过：file_transaction 内 {读候选 → 写目标 *.memory.md(分配 MEM-id) → 写 pgvector → 更新 SQLite → 候选标 approved}
   → 拒绝：候选标 rejected（保留痕迹，可复盘）
```

- 全程原子：文件 + 向量 + 索引同事务（TDR-5）。
- `agent_team` 是**显式动作**：默认只进 `agent_user`，用户主动选"贡献给团队"且经审核才共享。

### 4.5 检索（pgvector，带访问边界）

```text
retrieve_memory(participant, query, k):
  candidates = 该 participant 在当前 (task,user,team) 边界内有权读的记忆条目
  return pgvector_topk(embed(query), candidates, k)   # v1 降级：关键词命中
```

边界由 §8 访问控制矩阵决定；检索**先过滤再排序**，从源头杜绝越权注入（TDR-3）。

---

## 5. 多参与者协作机制

### 5.1 参与者加入 / 退出

```text
邀请 Agent/Twin 进任务：
  → task.json#participants 追加 {ref_type, ref_id, role, permission_level, joined_at}
  → 建 tasks/{tid}/participants/{ref_id}/notes.md（任务级私有笔记）
  → 对话区广播系统消息"X 已加入，已带入其记忆"
  → 下一回合 ContextAssembler 自动纳入该参与者层
退出/任务结束：
  → notes.md 保留（任务级，归属任务）
  → 触发 propose_memory 汇总值得长期保留的认知
```

### 5.2 上下文组装：每个参与者注入什么

| 注入项 | 来源 | 注入策略 |
|---|---|---|
| agent.md | 该 Agent/Twin 定义 | 全量（始终） |
| pinned 记忆 | 其空间 `pinned.memory.md` | 全量 |
| 相关记忆切片 | 工具 Agent: by-user/{当前uid} + by-team/{当前tid}；Twin: 用户空间 | pgvector top-k |
| 任务级 notes | `tasks/{tid}/participants/{ref_id}/notes.md` | 全量（小） |

外加共享层：任务层（对话/working/文件索引）+ 用户层（操作者偏好）+ 项目/团队层（共享知识切片）。组装算法见材料二 §5。

### 5.3 轮次路由（v1：Twin 编排）

```text
用户发言
  → Twin 接管：判断本轮谁执行（自己回应 / 指派某工具 Agent）
  → 若用户 @某参与者，则强制定向
  → 被指派 Agent 执行（可多轮 Tool Calling，有界 20 轮）
  → 结果回流，Twin 汇总并决定是否请求确认 / 提议记忆
```

Squad 自动路由（leader 分发）留二期 P2-03。

### 5.4 speaker 与对话落盘

`conversation.jsonl` 每行一个 Turn，含 `speaker{type:user|twin|agent, id}`；WS 事件透传 speaker，前端按主体渲染头像/徽标/工具卡。

---

## 6. 四层空间文件区落地（完整目录树）

```text
# ① 用户空间（含 Twin）——私有
users/{uid}/
  profile.json
  twin/{twin.json, agent.md, memory/{preferences,decisions,project-context,pinned}.memory.md}
  memory/                      # 用户级跨任务记忆（与 Twin 记忆区分）
  artifacts/                   # 晋升为用户所有的产物
  bindings/                    # 用户对各工具 Agent 的连接/配置
  audit.jsonl

# ② Agent 空间——团队共享定义 + 分区记忆
agents/{aid}/
  agent.json  agent.md
  skills/  knowledge/
  memory/
    by-user/{uid}/usage.memory.md       # 默认隔离（D-06）
    by-team/{tid}/shared.memory.md       # "贡献给团队"后

# ③ 团队/项目空间——共享（D-07）
teams/{tid}/
  team.json
  shared/{files,knowledge,memory,artifacts}/        # 团队级
  projects/{pid}/
    project.json
    shared/{files,knowledge,memory,artifacts}/       # 项目级（公共文件按项目隔离）

# ④ 任务空间——参与者可读，不跨任务
tasks/{tid}/
  task.json                    # 含 project_id + participants[]
  conversation.jsonl  tool_calls.jsonl
  files/{input,output}/        # 任务独立文件区
  memory/{working.memory.md, candidates.jsonl}
  participants/{ref_id}/notes.md
  approvals.jsonl  audit.jsonl
  grants.jsonl                 # 二期 P2-02
```

每层职责与生命周期见总纲 §4.1；路径解析全部经 `core/storage/paths.py`（材料二 §4）。

---

## 7. 空间访问控制矩阵（读 / 写）

> 原则：**没有人直接写更高层空间**——跨层一律走"候选→审批→晋升"。读取在组装点强制过滤。

| 主体 | 任务空间 | 自己的 Twin/用户空间 | Agent by-user(自己) | Agent by-team(本团队) | 项目/团队共享 | 他人用户/Twin 空间 |
|---|---|---|---|---|---|---|
| **User（成员）** | 读写 | 读写 | 读 | 读 | 读写(按成员角色) | ❌ |
| **Twin（本人）** | 读写 | 读 / 写经审批 | — | — | 读 | ❌ |
| **工具 Agent** | 读写(notes/output) + 提候选 | ❌ | 读 / 写经审批 | 读 / 写经审批(贡献给团队) | 读 | ❌ |
| **他人 Twin（二期）** | 仅宿主任务、只读宿主 + 写任务空间 | ❌ | ❌ | 同团队可读 | 同团队可读 | 回流到其自己 owner 空间 |
| **管理员** | 审计可见 | 内容隔离 | 审计可见 | 管理 | 管理 | 内容隔离 |

写规则统一：任务空间可直接写（notes/output/working）；其余空间的"长期记忆/产物"只能经 `propose_memory`/"保存为产物(选层级)" + 审批晋升。

---

## 8. 端到端实例：DAU 下滑归因

**场景**：用户在 ProjectA 建任务，邀请 DataAgent + 自己的 Twin，协作产出报告并沉淀记忆。

### 8.1 任务创建后 `tasks/t_DAU0620/task.json`

```json
{
  "id": "t_DAU0620", "project_id": "p_growth", "type": "data",
  "title": "浏览器 6.20 DAU 下滑归因", "status": "doing",
  "assignee": {"type":"twin","id":"twin-u_8f3a"},
  "participants": [
    {"ref_type":"user","ref_id":"u_8f3a","role":"owner","permission_level":"L3"},
    {"ref_type":"twin","ref_id":"twin-u_8f3a","role":"collaborator","permission_level":"L3"},
    {"ref_type":"agent","ref_id":"data-analysis","role":"tool","permission_level":"L2"}
  ],
  "created_by": "u_8f3a"
}
```

### 8.2 一回合的上下文组装（注入清单）

```text
[任务层] task.json 摘要 + 近 N 轮对话 + working.memory + files/index
[参与者: data-analysis] agent.md + by-user/u_8f3a/usage(切片) + participants/data-analysis/notes
[参与者: twin-u_8f3a]  twin agent.md + pinned 全量 + 用户记忆(切片：MEM-7c21 表格优先 / MEM-9a04 归因口径) + twin notes
[用户层] 操作者偏好
[项目层] p_growth/shared/knowledge 相关切片
```

### 8.3 工具调用与落盘

```text
data-analysis 调 kyuubi_query(只读, 低风险) → 直接执行
  → tool_calls.jsonl 追加一条；结果写 files/output/dau_trend.csv
  → 报告写 files/output/analysis_report_v07.md（产出物面板渲染）
Twin 建议补查 ANR(新查询) → request_approval → approvals.jsonl(pending)
  → 用户确认 → 执行 → 报告更新
```

### 8.4 任务收尾：记忆候选与晋升

```text
candidates.jsonl:
  cand_01 user_preference "表格优先"           → 审批通过 → users/u_8f3a/twin/memory/preferences.memory.md (MEM-7c21)
  cand_02 agent_team     "DAU 先查冷启动耗时"   → 用户选"贡献给团队"+审核 → agents/data-analysis/memory/by-team/t_growthTeam/shared.memory.md
  cand_03 project        "6.20 渠道A口径"        → 项目 admin 通过 → teams/.../projects/p_growth/shared/memory/shared.memory.md
报告产物"保存为产物(项目级)" → teams/.../projects/p_growth/shared/artifacts/
```

### 8.5 结果文件树（新增/变更）

```text
tasks/t_DAU0620/
  task.json  conversation.jsonl  tool_calls.jsonl  approvals.jsonl
  files/output/{dau_trend.csv, analysis_report_v07.md}
  memory/{working.memory.md, candidates.jsonl}
  participants/{data-analysis/notes.md, twin-u_8f3a/notes.md}
users/u_8f3a/twin/memory/preferences.memory.md            (+MEM-7c21)
agents/data-analysis/memory/by-team/t_growthTeam/shared.memory.md  (+1)
teams/t_growthTeam/projects/p_growth/shared/{memory,artifacts}/    (+1,+1)
```

> 隔离体现：DataAgent 这次的"冷启动口径"经验默认只进 `by-user/u_8f3a`；只有用户显式"贡献给团队"才进 `by-team`，B 用户用同一个 DataAgent 才能受益。Twin 记忆只进用户自己空间，别的用户读不到。

---

## 9. 内置 Agent 种子（复用 ICE）+ Twin 模板

### 9.1 工具 Agent 种子（来自 ICE `agents/`）

| Agent | 类别 | 能力 | 默认权限 |
|---|---|---|---|
| data-analysis | 数据 | SQL/归因/报告草稿 | L2 只读 |
| ab-experiment / volcano-abtest | 数据 | AB 实验分析 | L2 |
| wave-attribution | 数据 | 波动归因 | L2 |
| biz-insight | 数据 | 经营洞察 | L2 |
| general | 通用 | 文档/方案/资料 | L1 |
| （二期）codex / claude-code / cursor | 编码 | 本机项目修改 | L3，本机 daemon |

### 9.2 Twin 模板（新用户冷启动种子）

```text
twin.json: name=<用户名>的分身, permission_level=L1(初始), maturity=0
agent.md: 通用编排手册 + 空的"不可越权边界"(引导用户填)
memory/pinned.memory.md: 空，等待冷启动采访填入初始偏好
```

随使用，记忆累积、maturity 上升、用户逐步放权到 L2/L3。

---

## 10. 二期预览：跨用户 Twin 的文件/记忆机制（P2-02）

```text
访客 Twin 进入宿主任务：
  → grants.jsonl 记录 scoped grant（visitor_twin, host_task, 可读范围, 有效期）
  → 访客 Twin 上下文 = 宿主任务空间(只读宿主文件) + 它自己 owner 允许其带入的记忆切片
  → 访客只能写 tasks/{host_tid}/participants/{visitor_twin}/notes.md（带来源标注）
  → 访客产生的长期记忆 → 回流到它自己 owner 空间的 candidates，受其 owner 审批
  → 全程双方审计可见；grant 可随时撤销
```

不破坏 v1 隔离：访客对宿主的用户/Agent 空间零写权限，只在任务空间留痕。

---

## 附：与材料一/二的衔接

- 产品交互（邀请参与者、记忆候选卡、贡献给团队开关、空间标识）见**材料一 §6/§8**。
- ContextAssembler 伪码、memory_svc、三轴权限、paths 扩展、开发 ToDo 见**材料二 §4/§5/§7/§8/§13**。
- 本文聚焦"Agent 与空间"的落地格式与文件级机制，是上述两者的实现底稿。

---

## 11. 用户贡献的 Skill 与 Agent 自更新（D-13）

Skill 与记忆同构：**个人草稿优先（by-user）+ 显式"贡献给团队"才共享（by-team），版本化可回滚**。本节给出文件级落地。

### 11.1 Skill 文件布局

```text
skills/{skill_id}/                       # 团队/平台共享 Skill（已晋升）
  skill.json                             # name/desc/runtime/input_schema/owner_scope/current_version
  versions/{n}/code.(sql|py)             # 版本化代码（目录不可变）
  versions/{n}/meta.json                 # author/source_task/test_status/created_at
  tests/cases.json                       # 沙盒 test-run 样例入参

users/{uid}/skills/{skill_id}/           # 用户私有草稿 Skill（by-user，立即可用，仅本人）
  skill.json  versions/{n}/...

agents/{agent_id}/
  agent.json                             # #skills: 团队绑定的 skill_id 列表
  knowledge/skill-usage.md               # 何时用某 Skill（团队级）
  bindings/by-user/{uid}/skills.json     # 该用户私有给本 Agent 加的 Skill 绑定 + knowledge
```

### 11.2 Skill 定义格式 `skill.json`

```json
{
  "id": "biz-xx-dau",
  "name": "XX 业务 DAU 查询",
  "desc": "按业务线/渠道/日期查询 XX 业务 DAU",
  "runtime": "sql",
  "owner_scope": "user:u_8f3a",
  "input_schema": { "date_range": "string", "channel": "string?" },
  "current_version": 1,
  "source_task": "t_DAU0620"
}
```

### 11.3 Agent 自更新机制

「让 Data Agent 学会」= 一次 `file_transaction`：

1. 写/更新 Skill 版本（`skills/` 或 `users/{uid}/skills/`）。
2. 在 Agent 绑定该 Skill：团队 → `agent.json#skills`；个人 → `bindings/by-user/{uid}/skills.json`。
3. 写 knowledge："对于 XX 业务，使用 Skill `biz-xx-dau`"（团队 → `knowledge/skill-usage.md`；个人 → by-user 绑定内）。
4. Agent 版本 +1（复用 ICE Agent 快照/版本/回滚）。
5. 更新 SQLite/索引；写审计。

下次 ContextAssembler 注入该 Agent 时，把"可见 Skill 清单 + knowledge"一并注入（团队绑定 + 本用户 by-user 绑定），Agent 即"知道何时调用"。

### 11.4 贡献生命周期

```text
run_user_code（沙盒跑通）
  → propose_skill → tasks/{tid}/skill_candidates.jsonl (status=pending, proposed_scope, bind_agent)
  → 审批：
      · 个人草稿(user) → 低风险，确认即晋升到 users/{uid}/skills/ + by-user 绑定该 Agent → 立即可用
      · 贡献团队(team) → 沙盒 test-run 通过 + owner/admin 审核 → skills/ + agent.json#skills + 团队 knowledge → Agent 版本+1
  → 全程审计；可回滚（指 current_version 或新版本）
```

### 11.5 端到端实例（延伸 §8 的 DAU 场景）

用户发现 Data Agent 不会查"XX 新业务 DAU"，于是贡献 SQL：

```text
对话：用户粘贴 XX 业务的 SQL → Data Agent 调 run_user_code(sql, kyuubi 只读)
  → tasks/t_DAU0620/tool_calls.jsonl 记录；结果回填报告
  → 跑通 → propose_skill 生成候选：
     skill_candidates.jsonl: {name:"XX 业务 DAU 查询", runtime:"sql",
       input_schema:{date_range,channel}, proposed_scope:"user", bind_agent:"data-analysis"}
  → 用户选「个人草稿 + 绑定 Data Agent」→ 确认
     · 写 users/u_8f3a/skills/biz-xx-dau/{skill.json, versions/1/code.sql}
     · 写 agents/data-analysis/bindings/by-user/u_8f3a/skills.json（+biz-xx-dau + knowledge）
  → 下次：用户问"查 XX 业务 DAU" → Data Agent 上下文已含该 Skill → 直接调用，无需再贴代码
  → 若有用 → 用户点"贡献给团队" → 沙盒 test-run + admin 审核 → 晋升到 skills/ + agent.json#skills
     → 全团队的 Data Agent 都学会了
```

### 11.6 隔离 / 复用（与 §7 访问矩阵一致）

- 个人草稿 Skill 仅本人任务可用、不进他人上下文；Agent 的 by-user 绑定同理。
- 团队 Skill 经审核后全团队共享；按 Team 隔离（呼应 D-06/D-07）。
- 用户贡献代码一律沙盒执行，团队晋升双门（test-run + 审核）。
