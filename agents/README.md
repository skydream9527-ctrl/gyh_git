# agents/ — 内置 Agent 目录

本目录存放 ICE Workbench 的内置 Agent 定义。当前运行时以 `agent.json`
声明能力边界，以 `prompt/` 下的 markdown 作为系统提示词来源。

## 当前 Agent

| 目录 | Agent 名 | 状态 | 用途 |
|---|---|---|---|
| `general/` | 通用 Agent | published | 开放任务入口与跨 Agent 编排 |
| `data-analysis/` | 数据分析 Agent | published | BM/BF/CC 数据分析、NL→SQL、Python 分析、报告 |
| `ab-experiment/` | 实验分析 Agent | published | AB 显著性、下钻、放量决策 |
| `gray-release/` | 灰度版本 Agent | published | APP 版本灰度发布分析与决策 |
| `know/` | 知识库 Agent | published | 飞书知识空间使用、维护、归档 |
| `volcano-abtest/` | 火山实验分析 | published | 火山 ABtest 查询与报告 |
| `zijian-data-analysis/` | 自建数据分析 | published | 都江堰自建信息流分析 |
| `biz-insight/` | 经营洞察 Agent | coming_soon | 经营报告与洞察 |
| `wave-attribution/` | 波动归因 Agent | coming_soon | 指标异动归因 |

## 目录约定

每个 Agent 至少包含：

```text
agents/{agent_id}/
├── agent.json          # 运行时声明：工具白名单 / spawn 目标 / feature flags / 展示信息
├── prompt/             # system.md 或 v3 的 identity.md + sop.md
├── knowledge/          # Agent 私有知识库，供 read_agent_knowledge 读取（可选）
├── skills/             # Agent 私有说明型 skill（可选）
└── README.md           # Agent 使用说明（可选）
```

## agent.json 关键字段

- `tools`: 该 Agent 可见的 function tools。缺失时运行时会按兼容逻辑暴露全部内置工具，新 Agent 应显式声明。
- `features`: 细粒度开关，例如 `todo_write`、`exit_plan_mode`、`spawn_subagent`、`run_background`。
- `spawn_targets`: 可派单的子 Agent 白名单。`["*"]` 表示所有已发布 Agent；空数组表示不可派单。
- `skills`: 推荐的说明型 skill id，仅作为提示词 hint；真正可读取的 skill 仍由任务绑定的 skill 快照决定。
- `prompt_layout: "v3"`: 使用 `identity.md` / `sop.md` + `_shared/_partials/` 组装运行时提示词。

## 共享运行时片段

`agents/_shared/_partials/` 下的片段由 `agent_prompt_builder` 注入：

- `tool_contract.md`: 通用工具契约
- `context_protocol.md`: 上下文协议
- `spawn_routing.md`: 子 Agent 派单规则，仅对启用 `spawn_subagent` 的 v3 Agent 注入
- `plan_mode.md`: Plan Mode 规则，仅对启用 `exit_plan_mode` 的 v3 Agent 注入
