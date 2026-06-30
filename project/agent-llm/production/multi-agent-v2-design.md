# Multi-Agent V2.0 设计参考：Sub-agent × Twin+A2A 三层融合

> 来源：ICE Workbench（`project/ice-workbench-new/`）+ ice-data-work（`gitlab/ice-data-work/`）现有实现分析
> 用途：ICE Workbench V2.0 multi-agent 架构设计参考
> 日期：2026-06-30
> 关联洞察：[Wisdom&Decide/insights/2026-06-30-nl-sql取数的协作式交互设计.md](../../../Wisdom&Decide/insights/2026-06-30-nl-sql取数的协作式交互设计.md)

---

## 一、背景：两个项目的两条路线

两个项目都实现了 multi-agent，但走了截然不同的两条路：

| | ICE Workbench | ice-data-work |
|---|---|---|
| 范式 | Hub-and-Spoke 派单（主 agent spawn 子 agent） | Twin(数字分身) Leader + 有界多跳 A2A |
| 对应模式 | Sub-agent（主调子，子跑独立 ReAct loop） | A2A handoff 接力（Twin 仲裁） |
| 底座 | 自身 | 沿用 ICE Workbench |

ice-data-work 底座沿用 ICE Workbench，所以 V2.0 应**融合而非二选一**。

---

## 二、方案一：ICE Workbench 的 Sub-agent（现状）

### 架构

```
用户 ──▶ general Agent (主编排, ReAct loop)
            │  LLM 决定: 自己干 / spawn_subagent / spawn_parallel
            ├──spawn_subagent──▶ data-analysis Agent (独立 ReAct loop)
            │                      │ 自包含 prompt + 工具白名单
            │                      ▼ 跑多轮 tool calling
            ◀──final_text + run_id─┘
            ├──spawn_subagent──▶ ab-experiment Agent ...
用户 ◀──汇总─── general
```

### 机制要点
- **主编排 agent = `general`**，`agent.json` 里 `spawn_targets: ["*"]`
- 主 agent 在 ReAct loop 中 LLM 决定调 `spawn_subagent` tool
- 子 agent 跑**独立 ReAct loop**（`agent_kernel.run`，主子共用同一内核）
- 深度限制 = 1（子 agent 不能再 spawn）

### 通信（函数调用 + 结构化包）
- 任务包（主→子）：`{agent_id, prompt, allowed_tools, model, max_tokens}`（prompt 必须自包含）
- 结果包（子→主）：`{final_text, run_id, tool_count, duration_ms}` + 失败 `{error_code, message}`
- 约束：子 agent **不共享主 agent 历史、无对话通道、不能再 spawn**

### 反馈学习
`subagent_feedback.py`：子 agent 完成后正则提取 `final_text` 结论段，以 `confidence=0.7` 存入父 agent Agent Memory。

### 关键代码
| 文件 | 职责 |
|---|---|
| `project/ice-workbench-new/backend/app/services/agent/agent_kernel.py:310` | 统一 ReAct loop `run()`，主子共用 |
| `project/ice-workbench-new/backend/app/services/agent/agent_runtime.py:45` | 子 agent 适配器 `run_agent_turn()` |
| `project/ice-workbench-new/backend/app/services/llm/tools/workflow.py:226-432` | `spawn_subagent` 工具实现 |
| `project/ice-workbench-new/backend/app/services/agent/agent_prompt_builder.py:129` | prompt 组装（含动态 spawn 目标表） |
| `project/ice-workbench-new/backend/app/services/agent/subagent_feedback.py` | 子 agent insight 提取 |

### 局限
- 子 agent 不能追问用户、不能彼此通信
- 无 HITL 确认机制、无计划编排
- 适合"主 agent 拆解 + 子 agent 深度执行"的派单场景

---

## 三、方案二：ice-data-work 的 Twin + A2A（现状）

### 架构（三层）

```
用户 ──▶ Twin(数字分身, leader)
            │  resolve_speaker 路由
            │  (a) 单跳: Twin/Agent 单次 LLM
            │  (b) 有界多跳 A2A: Agent 输出 [[handoff:X|理由]]
            │      → orchestrator.parse_directive → Twin arbitrate_handoff
            │      → 下一个 Agent 接力 (单轮≤3跳, 硬顶6)
            │  (c) autostep: 回合后 Twin 自动推进 plan.json 下一步
            ├──[[handoff:data-analysis|需查SQL]]──▶ data-analysis Agent
            │   [[handoff:report-writer|出报告]]──▶ report-writer Agent
            │   [[ask:code-runner|跑个脚本]]──────▶ code-runner (问完回)
            │  高风险动作 → request_approval → 用户确认 (L2)
用户 ◀──Twin 汇总───
```

### 机制要点
- **Twin = 数字分身 leader**，用户只对 Twin 说话
- **有界多跳**：Agent 输出末尾发转交指令 → Twin 仲裁 → 接力（单轮≤3跳，硬顶6）
- **计划编排**：`decompose_goal` 把目标拆成有序步骤存 `plan.json`，回合后推进
- **自驱**：Twin 自动推进计划下一步，受 `proactivity_svc` 护栏（每日上限/静默/暂停），超限转 proposal

### 通信（文本指令 + Twin 仲裁 + 上下文注入）
- 转交指令：`[[handoff:<agent_id>|<理由>]]`（接力）/ `[[ask:<agent_id>|<问题>]]`（咨询，问完回发起方）
- 也可通过 `handoff_to_agent` / `ask_agent` 工具（等价）
- 仲裁规则（`arbitrate_handoff`）：自转交拒、目标不存在拒、超预算拒、A↔B 乒乓拒、重复转交拒
- 上下文注入（`context_assembler_svc._a2a_system`）：为接手方注入"谁因何转交 + 前序产出摘要"，五层组装

### HITL / 治理
- 工具带 `risk` 字段（`high` 需确认），`request_approval` 工具
- 三轴权限 + 一键暂停 + 主动性护栏 + 审计
- 这是"L2 辅助驾驶"的落地

### 关键代码
| 文件 | 职责 |
|---|---|
| `gitlab/ice-data-work/backend/app/services/agent_runtime.py:142-197` | 主循环：多跳 while + parse_directive + arbitrate_handoff |
| `gitlab/ice-data-work/backend/app/services/orchestrator_svc.py:87-126` | `arbitrate_handoff` 仲裁 + HopState 防环 |
| `gitlab/ice-data-work/backend/app/services/plan_svc.py` | 计划编排（decompose_goal / start_next / plan_advance_after_turn） |
| `gitlab/ice-data-work/backend/app/services/context_assembler_svc.py:109` | 五层上下文 + A2A 前序注入 |
| `gitlab/ice-data-work/backend/app/services/squad_svc.py` | Agent 小队（leader + members + policy） |
| `gitlab/ice-data-work/backend/app/services/proactivity_svc.py` | 自驱护栏 |

### 局限
- Agent 无独立 ReAct loop（每次"跳"是单次 LLM + 可选工具，被动被调度）
- 关键特性默认关（`IDW_A2A_ENABLED` / `IDW_AUTOSTEP_ENABLED` / `IDW_SQUADS_ENABLED` / `IDW_TRIGGERS_ENABLED`）
- 适合"多专业 Agent 协作 + 人机分级授权"的团队场景

---

## 四、对比

| 维度 | ICE Workbench (Sub-agent) | ice-data-work (Twin+A2A) |
|---|---|---|
| 主 agent | general（spawn 派单） | Twin（数字分身 leader） |
| 子 agent 自治 | ✅ 独立 ReAct loop（多轮工具） | ❌ 单跳，被动被调度 |
| Agent 间通信 | ❌ 无（只回 final_text） | ✅ handoff/ask 指令 + 仲裁 |
| 多跳深度 | 1（子不能再 spawn） | ≤3 跳/轮（硬顶 6） |
| 计划编排 | todo_write（agent 内） | plan.json（步骤级） |
| 主动性 | ❌ 被动响应 | ✅ autostep 自驱 + proposal |
| HITL 确认 | ❌ 无 | ✅ risk + request_approval |
| 上下文共享 | ❌ prompt 自包含 | ✅ 五层组装 + A2A 注入 |
| 反馈学习 | ✅ subagent_feedback | propose_memory |
| 通信复杂度 | 低（函数调用） | 中（指令解析+仲裁） |

**核心判断**：两者互补——ICE Workbench 强在单 agent 深度自治，ice-data-work 强在多 agent 协作 + HITL。

---

## 五、V2.0 融合架构：Twin + plan.json + sub-agent 三层

### 设计思路
- L1 Twin（来自 ice-data-work）：意图理解、目标拆解、HITL 决策点、handoff 仲裁
- L2 plan.json（来自 ice-data-work）：步骤级任务包，编排执行顺序
- L3 sub-agent（来自 ICE Workbench）：每步派给专家 Agent，跑独立 ReAct loop，可再 spawn

**关键创新**：L3 的专家 Agent 有独立 ReAct loop（补 ice-data-work 的"单跳被动"短板），但被 L2 plan.json 编排、L1 Twin 仲裁约束（补 ICE Workbench 的"无计划、无 HITL"短板）。

### 架构图

```
                          ┌──────────────┐
                          │     用户      │
                          └──────┬───────┘
                                 │ 自然语言目标
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│  L1: Twin（数字分身 leader）                                  │
│  ─ 意图理解 + 消歧                                            │
│  ─ decompose_goal → plan.json                                │
│  ─ handoff/ask 仲裁（orchestrator_svc.arbitrate_handoff）     │
│  ─ HITL 决策点判断（pending_questions / high risk → 确认）    │
│  ─ autostep 自驱推进（proactivity_svc 护栏）                  │
└──────────────────────┬───────────────────────────────────────┘
                       │ ① decompose_goal
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  L2: plan.json（计划编排）                                    │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                          │
│  │step1│→│step2│→│step3│→│step4│  (deps 控制顺序/并行)       │
│  └──┬──┘  └─────┘  └─────┘  └─────┘                          │
│     │ ② start_next → 取 step1                                │
│     │ {step_id, goal, agent_id, deps, risk, status}          │
└─────┼────────────────────────────────────────────────────────┘
      │ ③ handoff to expert（TaskPackage）
      ▼
┌──────────────────────────────────────────────────────────────┐
│  L3: sub-agent（深度执行，ICE Workbench 内核）                │
│  专家 Agent 跑独立 ReAct loop（agent_kernel.run）             │
│  ─ 多轮 tool calling（kyuubi_query / data_viz / MCP…）        │
│  ─ 可再 spawn 子 agent（深度1，如 data-analysis→wave-attribution）│
│  ─ 落盘产物到 tasks/{tid}/files/output/                      │
│  ◀── TaskPackage        ──▶ ResultPackage ──▶                │
│      {step_id,goal,        {final_text,artifacts,             │
│       context,constraints,  confidence,pending_questions,     │
│       allowed_tools,        insights}                         │
│       return_req,max_rounds}                                 │
└──────────────────────┬───────────────────────────────────────┘
                       │ ④ ResultPackage 回 Twin
                       ▼
              ⑤ Twin 判断:
                 ├─ 有 pending_questions / high risk → ⑥ ApprovalRequest → 用户(L2)
                 │      用户确认 → 修正 step 或推进
                 ├─ step 完成 → plan_advance → 下一步
                 └─ 全部完成 → 汇总 → 用户
```

### 一次完整调用的数据流

1. 用户 → Twin：自然语言目标（"查上周浏览器推荐流人均消费时长"）
2. Twin `decompose_goal` → `plan.json`（多个 PlanStep）
3. Twin `plan_advance` → `start_next` 取 step1
4. Twin `handoff` → 专家 Agent（携带 **TaskPackage**）
5. 专家 Agent 跑 ReAct loop（可 `spawn_subagent` 深度执行）
6. 专家 Agent → **ResultPackage**（含 `pending_questions`、`insights`）
7. Twin 判断：`pending_questions` 或 high risk → **ApprovalRequest** → 用户（L2 决策点）
8. 用户确认 → Twin 回 step 修正或推进
9. `plan_advance` → step2 … 循环
10. 全部完成 → Twin 汇总 → 用户

---

## 六、关键接口定义

### 6.1 PlanStep（plan.json 元素，来自 ice-data-work plan_svc）

```python
{
  "step_id": "s1",
  "goal": "查上周浏览器推荐流人均消费时长",
  "agent_id": "data-analysis",       # 执行专家
  "deps": [],                         # 前置 step_id 列表（控制顺序/并行）
  "risk": "medium",                   # low/medium/high → 决定是否 HITL
  "status": "pending",                # pending/running/done/blocked/failed
  "result": null                      # 完成后填 ResultPackage
}
```

### 6.2 TaskPackage（Twin → 专家 Agent，融合 spawn_subagent + plan step）

```python
{
  "step_id": "s1",                    # 来自 plan.json
  "agent_id": "data-analysis",
  "goal": "查上周浏览器推荐流人均消费时长",
  "context": {                        # 五层上下文摘要（context_assembler_svc）
    "user": {...}, "task": {...},
    "a2a_prior": "Twin 因用户提问转交，前序无产出"
  },
  "constraints": {                    # 消歧后的口径约束
    "口径": "有效时长",
    "时间": "自然周 6/23-6/29"
  },
  "allowed_tools": ["kyuubi_query", "data_viz", "csv_export"],
  "return_requirements": ["数字", "SQL", "口径说明", "置信度"],
  "max_rounds": 8,                    # ReAct loop 上限
  "can_spawn": true                   # 是否允许再 spawn 子 agent（深度1）
}
```

### 6.3 ResultPackage（专家 Agent → Twin，融合 spawn_subagent 返回 + subagent_feedback）

```python
{
  "step_id": "s1",
  "final_text": "人均 12.4 分钟（自然周 6/23-6/29，有效时长口径）",
  "artifacts": ["tasks/{tid}/files/output/s1_report.md"],  # 落盘产物路径
  "tool_count": 3,
  "duration_ms": 8200,
  "confidence": "high",               # high/medium/low
  "pending_questions": [              # 待用户确认的歧义点（L2 决策点来源）
    {"q": "推荐流是否含二级频道？", "options": ["含二级", "仅首页"]}
  ],
  "insights": [                       # 提取的可复用 insight → 存 Agent Memory
    {"text": "推荐流人均有效时长口径=前台时长-后台时长", "confidence": 0.7}
  ],
  "error": null                       # {error_code, message} 失败时
}
```

### 6.4 HandoffDirective（Twin 仲裁的转交，来自 ice-data-work orchestrator_svc）

```python
# 文本指令（嵌入 Agent LLM 输出末尾）:
#   [[handoff:<agent_id>|<理由>]]   接力：控制权交给另一 Agent
#   [[ask:<agent_id>|<问题>]]       咨询：问完控制权回发起方

# parse_directive 解析后:
{"action": "handoff"|"ask", "to": "data-analysis", "reason": "需查SQL"}

# arbitrate_handoff 仲裁规则（违反即拒）:
#   - 自转交拒（A→A）
#   - 目标不存在拒
#   - 超预算拒（HopState 单轮≤3，硬顶6）
#   - A↔B 乒乓拒
#   - 重复转交拒
```

### 6.5 ApprovalRequest（HITL，L2 决策点，来自 request_approval + risk）

```python
{
  "step_id": "s1",
  "trigger": "high_risk_tool"|"ambiguous_oracle"|"step_boundary",
  "question": "推荐流是否含二级频道？",
  "options": ["含二级", "仅首页推荐"],
  "default": "仅首页推荐",           # 用户不响应时的兜底
  "block": true                       # 是否阻塞执行等用户
}
```

**trigger 判定**（对应 L2 辅助驾驶的"关键决策点"）：
- `high_risk_tool`：工具 risk=high（如写操作、删除、外发）
- `ambiguous_oracle`：ResultPackage.confidence=low 或有 pending_questions
- `step_boundary`：计划关键节点（如首个步骤、最后一步）

---

## 七、实现路径（从两个现有项目融合）

| 阶段 | 动作 | 来源 |
|---|---|---|
| 1. 底座 | 用 ICE Workbench（`agent_kernel` + `spawn_subagent` + `subagent_feedback` 已成熟） | ICE Workbench |
| 2. 移植编排 | 移植 `orchestrator_svc`（handoff 仲裁）+ `plan_svc`（计划编排）+ `proactivity_svc`（自驱护栏）+ `request_approval`（HITL） | ice-data-work → ICE Workbench |
| 3. 统一接口 | 定义 PlanStep / TaskPackage / ResultPackage / HandoffDirective / ApprovalRequest（见第六节） | 新建 |
| 4. Twin 升级 | 把 `general` agent 升级为 Twin（加 plan + handoff + HITL 能力） | 改造 |
| 5. 专家 Agent 适配 | 现有 `data-analysis` 等专家 Agent：接受 TaskPackage、返回 ResultPackage（保留独立 ReAct loop） | 改造 |
| 6. 灰度 | 沿用 ice-data-work 的开关模式：`IDW_A2A_ENABLED` / `IDW_AUTOSTEP_ENABLED` 默认关 | ice-data-work |

### 关键改造点
- **Twin = general + plan + handoff**：general 的 `spawn_subagent` 改为 `handoff`（经 plan.json 编排 + Twin 仲裁），保留"子 agent 独立 ReAct loop"
- **专家 Agent 入参出参**：从 `{prompt}` → `{TaskPackage}`，从 `{final_text}` → `{ResultPackage}`
- **L2 决策点**：Twin 在 step 完成后判断 `pending_questions` / `risk` → `ApprovalRequest`，这是"协作式取数"insight 的落地

---

## 八、参考代码索引

### ICE Workbench（`project/ice-workbench-new/`，本仓库内）
- `backend/app/services/agent/agent_kernel.py:310` — 统一 ReAct loop
- `backend/app/services/agent/agent_runtime.py:45` — 子 agent 适配器
- `backend/app/services/llm/tools/workflow.py:226-432` — spawn_subagent 实现
- `backend/app/services/agent/agent_prompt_builder.py:129` — prompt 组装
- `backend/app/services/agent/subagent_feedback.py` — insight 提取
- `agents/general/agent.json` — 主编排 agent（spawn_targets:["*"]）
- `agents/_shared/_partials/spawn_routing.md` — 派单指南

### ice-data-work（`gitlab/ice-data-work/`，独立 clone）
- `backend/app/services/agent_runtime.py:142-197` — 多跳主循环
- `backend/app/services/orchestrator_svc.py:87-126` — handoff 仲裁 + HopState
- `backend/app/services/plan_svc.py` — 计划编排
- `backend/app/services/context_assembler_svc.py:109` — 五层上下文 + A2A 注入
- `backend/app/services/squad_svc.py` — Agent 小队
- `backend/app/services/proactivity_svc.py` — 自驱护栏
- `backend/app/services/tools/registry.py` — ToolSpec（含 risk 字段）

---

## 九、与既有思考的关联

- [协作式取数五步](../../../Wisdom&Decide/insights/2026-06-30-nl-sql取数的协作式交互设计.md)：plan.json 的步骤 = 协作式取数的"澄清→确认→生成→自检→沉淀"
- L2 决策点（ApprovalRequest）= "不要二元反馈，要具体指向"的落地
- ResultPackage.insights + pending_questions = "口径沉淀是准确率杠杆"的载体
- Twin = 会议纪要里的"数字分身 Agent 作为用户与工具 Agent 中介"
- plan.json + 范式库：每个 PlanStep 的 goal 可绑定范式库范式，这是 nl-sql 90% 准确率的工程路径
