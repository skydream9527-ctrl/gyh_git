# TokenWisdom 页面层级 v3：User → Twin Agent → Agents

- 日期：2026-06-27
- 核心模型：一个用户拥有一个分身 Agent；用户通过分身 Agent 与其他工具 / 应用 / 专业执行 Agent 协作。
- 核心交互：分身 Agent 始终常驻页面右上角；所有对外部 Agent 的对话，分身 Agent 都默认参与。
- 权限原则：分身 Agent 可以参与讨论、提出要求、整理上下文、草拟指令，但最终确认权属于用户。
- 设计方向：清晰、高效、干净；页面不是“作战大屏”，而是一个长期可用的个人 Agent 工作台。

## 页面层级总览

```text
TokenWisdom
├── Global Twin Dock（全局常驻，不随页面切换消失）
│   ├── User ↔ Twin 的长期对话
│   ├── Twin 当前参与的 Agent Rooms
│   └── Pending Confirmations
├── Home（主页面）
│   ├── User → Twin Agent → Agents 关系图
│   ├── Active Agent Rooms
│   └── Next Decisions
├── Agent Rooms（核心子页面）
│   ├── 对其他 Agent 的所有对话框
│   ├── Twin Agent 默认加入
│   └── User Final Confirm
├── Agents
│   ├── Twin Agent
│   └── Tool / App / Expert Agents
├── Permissions
│   ├── 角色权限矩阵
│   └── 动作等级 L0-L5
├── Knowledge
│   ├── 分身可用上下文
│   └── 对外部 Agent 的共享边界
├── Runtime
│   ├── Mac / Android / Browser / Backend
│   └── Local Agent Connectors
└── Audit
    ├── User ↔ Twin
    ├── Twin ↔ Agent
    └── Agent ↔ Agent
```

## 0. 产品核心关系

```text
User
└── Twin Agent（用户的长期分身）
    ├── 理解用户：目标、偏好、文件、历史决策、授权边界
    ├── 代表用户：向其他 Agent 提问、补充上下文、提出要求
    ├── 协调工作：组织 Agent-to-Agent 讨论、整理结论、生成执行建议
    └── 请求确认：任何执行、写入、发送、调用高风险工具前，都回到用户确认

Tool / App / Expert Agents
├── Claude Code / Codex / Cursor
├── Browser Agent / Web App Agent
├── Knowledge Agent / File Agent
├── Data Agent / SQL Agent
└── Life Ops Agent / Calendar / Mail / Todo
```

## 1. 全局 App Shell

```text
TokenWisdom App Shell
├── 左侧主导航
│   ├── Home
│   ├── Agent Rooms
│   ├── Agents
│   ├── Knowledge
│   ├── Permissions
│   ├── Runtime
│   └── Audit
├── 中间主工作区
│   └── 当前页面内容
└── 右上角常驻 Twin Dock
    ├── 分身 Agent 状态
    ├── 与用户的长期对话框
    ├── 待确认请求
    ├── 当前正在参与的 Agent Room
    └── 快捷授权 / 拒绝 / 修改范围
```

### 1.1 常驻 Twin Dock

```text
Twin Dock（始终显示）
├── Twin Identity
│   ├── 分身名称
│   ├── 当前权限等级
│   └── 在线状态
├── Persistent Conversation
│   ├── 用户直接对分身说话
│   ├── 分身同步当前页面上下文
│   └── 分身提示需要用户确认的事项
├── Pending Confirmations
│   ├── 允许 / 拒绝
│   ├── 修改范围
│   └── 先问清楚
└── Room Participation
    ├── 当前正在参与哪些 Agent 对话
    ├── 分身在每个 Room 的角色
    └── 是否有 Agent 等待用户裁决
```

## 2. 主页面：Home / Relationship Overview

```text
Home
├── Relationship Map
│   └── User → Twin Agent → Tool/App Agents
├── Twin Summary
│   ├── 分身懂你的程度
│   ├── 当前授权边界
│   ├── 今日参与的 Agent Room
│   └── 等待用户裁决事项
├── Active Agent Rooms
│   ├── Dev Room：Twin + Codex + Claude Code
│   ├── Knowledge Room：Twin + File Agent
│   ├── AI Tool Room：Twin + Browser Agent
│   └── Life Ops Room：Twin + Calendar / Mail Agent
└── Next Decisions
    ├── 是否允许执行
    ├── 是否采纳结论
    ├── 是否固化记忆
    └── 是否提升权限
```

## 3. 子页面：Agent Rooms / Agent-to-Agent 对话空间

Agent Rooms 是平台最核心的工作区域。它不是普通聊天列表，而是一个多方对话框架：用户给出目标，Twin Agent 带着目标、上下文和权限边界进入对话，外部 Agent 提供能力、方案和风险，最后由 Twin Agent 汇总成用户确认请求。

```text
Agent Rooms
├── Room List
│   ├── Dev Agent Room
│   ├── Knowledge Agent Room
│   ├── AI Tool Agent Room
│   └── Life Ops Agent Room
├── Room Detail
│   ├── Participants
│   │   ├── User（最终确认者）
│   │   ├── Twin Agent（用户代表 / 协调者）
│   │   └── Tool/App Agents（专业执行者）
│   ├── Shared Context
│   │   ├── 用户目标
│   │   ├── 文件 / 记忆
│   │   ├── 约束条件
│   │   └── 权限边界
│   ├── Agent-to-Agent Conversation
│   │   ├── Twin Agent 向外部 Agent 提问
│   │   ├── 外部 Agent 回复能力 / 方案 / 风险
│   │   ├── Twin Agent 追问和压缩结论
│   │   └── User 最终确认
│   ├── Room Composer
│   │   ├── @Twin Agent always included
│   │   ├── @Target Tool Agent
│   │   ├── 自动携带用户目标
│   │   └── 自动标注权限边界
│   └── Decision Panel
│       ├── 分身建议
│       ├── 外部 Agent 输出
│       ├── 风险提示
│       └── 用户确认按钮
```

## 4. 子页面：Agents / Agent Network

```text
Agents
├── Twin Agent
│   ├── 用户画像
│   ├── 工作偏好
│   ├── 记忆范围
│   └── 可代表用户做什么
├── Tool / App Agents
│   ├── Coding Agents：Claude Code / Codex / Cursor
│   ├── Knowledge Agents：File / Knowledge Base / Search
│   ├── AI Tool Agents：Browser / MCP / Web App
│   └── Life Ops Agents：Calendar / Mail / Todo
├── Agent Card
│   ├── 能力
│   ├── 输入要求
│   ├── 输出质量
│   ├── 风险等级
│   ├── 是否可执行
│   └── 是否必须用户确认
└── Connector
    ├── CLI
    ├── Browser
    ├── API
    ├── MCP
    └── Manual
```

## 5. 子页面：Permissions / 权限结构

```text
Permissions
├── Role Permissions
│   ├── User：最终确认者，可授权、拒绝、撤销、修改范围
│   ├── Twin Agent：可讨论、可请求、可草拟、可协调，不可最终执行高风险动作
│   └── Tool/App Agent：只能在授权范围内执行或提供建议
├── Action Levels
│   ├── L0 Observe：观察 / 总结
│   ├── L1 Discuss：参与讨论 / 提问
│   ├── L2 Draft：草拟指令 / 执行计划
│   ├── L3 Request：向用户请求授权
│   ├── L4 Execute：用户确认后执行
│   └── L5 Autopilot：白名单内自动执行，仍保留审计与撤销
├── Non-negotiable Rules
│   ├── Twin Agent 永远不能替用户做最终确认
│   ├── Twin Agent 可以要求 Tool Agent 说明能力、风险、输入输出
│   ├── Twin Agent 可以草拟执行请求，但必须由用户点击确认
│   └── Tool/App Agent 只能在本次授权范围内行动
├── Confirmation Rules
│   ├── 写文件必须确认
│   ├── 发消息必须确认
│   ├── 调用付费工具必须确认
│   ├── 上传上下文必须确认
│   └── 固化长期记忆必须确认
└── Audit Guarantee
    ├── 谁提出
    ├── 谁执行
    ├── 用户是否确认
    └── 依据什么上下文
```

## 6. 子页面：Knowledge / 分身上下文

```text
Knowledge
├── User Memory
│   ├── 目标
│   ├── 偏好
│   ├── 表达风格
│   └── 判断标准
├── Room Context
│   ├── 每个 Agent Room 独立上下文
│   ├── 共享给外部 Agent 的内容
│   └── 不允许共享的内容
├── Files
│   ├── 用户上传
│   ├── 本地文件夹
│   ├── 项目资料
│   └── 外部链接
└── Memory Confirmation
    ├── 待确认记忆
    ├── 冲突记忆
    ├── 过期记忆
    └── 已确认记忆
```

## 7. 子页面：Runtime / 本地执行

```text
Runtime
├── Mac Local Runtime
│   ├── 本机在线状态
│   ├── 可访问目录
│   ├── 禁止读取目录
│   └── Kill Switch
├── Connectors
│   ├── Codex
│   ├── Claude Code
│   ├── Cursor
│   ├── Browser Extension
│   └── Android Approval App
└── Execution Boundary
    ├── 分身提出执行请求
    ├── 用户确认
    ├── Tool Agent 执行
    └── 结果回到 Room 和 Audit
```

## 8. 子页面：Audit / 审计

```text
Audit
├── Conversation Audit
│   ├── User ↔ Twin
│   ├── Twin ↔ Tool Agent
│   └── Agent ↔ Agent
├── Permission Audit
│   ├── 请求授权
│   ├── 用户确认
│   ├── 用户拒绝
│   └── 自动通过规则
├── Execution Audit
│   ├── 文件读写
│   ├── 命令执行
│   ├── 外部 Agent 调用
│   └── 上下文上传
└── Decision Audit
    ├── 采纳了什么建议
    ├── 拒绝了什么建议
    ├── 为什么这样决策
    └── 是否写入长期记忆
```
