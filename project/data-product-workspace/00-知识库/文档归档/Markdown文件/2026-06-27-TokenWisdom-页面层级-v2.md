# TokenWisdom 页面层级 v2

- 日期：2026-06-27
- 设计目标：清晰、高效、干净，先让用户理解“我在哪里、分身在做什么、下一步该点哪里”。
- 设计原则：主页面负责总览与分流，子页面承接具体任务；避免把所有能力堆在一个大 Dashboard。

## 0. 全局框架 App Shell

```text
TokenWisdom App Shell
├── 左侧主导航：Home / Missions / Mission Room / Agents / Knowledge / Approvals / Runtime / Audit
├── 顶部命令栏：Ask or assign to your Twin...
├── 当前分身状态：Safe Mode / Sovereign Mode / Local Runtime / Kill Switch
└── 页面内容区：根据导航切换子页面
```

## 1. 主页面：Home / Twin Overview

```text
Home / Twin Overview
├── Twin Summary
│   ├── 分身成熟度
│   ├── 当前授权等级
│   ├── 已连接 Agent 数量
│   └── 今日待确认事项
├── Today Focus
│   ├── 正在推进的 Mission
│   ├── 等待用户确认的动作
│   └── 分身建议的下一步
├── Quick Start
│   ├── 创建 Mission
│   ├── 添加 Agent
│   ├── 上传 / 连接文件
│   └── 打开 Mac Runtime
└── Four Hubs Preview
    ├── Dev Agent Hub
    ├── Knowledge Hub
    ├── AI Tool Hub
    └── Life Ops Hub
```

## 2. 子页面：Missions / 任务队列

```text
Missions
├── Mission List
│   ├── 进行中
│   ├── 待确认
│   ├── 已完成
│   └── 阻塞中
├── Mission Filters
│   ├── 工作域：Dev / Knowledge / AI Tools / Life Ops
│   ├── 状态：Running / Waiting / Blocked / Done
│   └── 权限风险：Low / Medium / High
└── Mission Card
    ├── 目标
    ├── 当前状态
    ├── 参与 Agent
    ├── 最近进展
    └── 下一步动作
```

## 3. 子页面：Mission Room / 单任务工作空间

```text
Mission Room
├── Mission Header
│   ├── 任务目标
│   ├── 状态
│   ├── 当前授权边界
│   └── 参与 Agent
├── Context Panel
│   ├── 相关文件
│   ├── 关联记忆
│   ├── 约束条件
│   └── 验收标准
├── Conversation
│   ├── 用户
│   ├── TokenWisdom Twin
│   ├── 外部 Agent
│   └── 工具返回
├── Execution Plan
│   ├── 步骤
│   ├── 依赖
│   ├── 风险
│   └── 是否需要审批
└── Timeline / Audit
    ├── 工具调用
    ├── 文件读写
    ├── Agent 输出
    └── 用户确认记录
```

## 4. 子页面：Agents / Agent Hub

```text
Agents / Agent Hub
├── My Agents
│   ├── Claude Code
│   ├── Codex
│   ├── Cursor
│   ├── Browser Agent
│   └── 文件知识 Agent
├── Agent Card
│   ├── 能力
│   ├── 适用任务
│   ├── 输入要求
│   ├── 输出特点
│   ├── 风险等级
│   └── 历史表现
├── Connector Setup
│   ├── CLI Connector
│   ├── Browser Connector
│   ├── API Connector
│   └── Manual Connector
└── Agent Test Room
    ├── 冷启动访谈
    ├── 能力测试
    └── 能力卡确认
```

## 5. 子页面：Knowledge / 文件与记忆

```text
Knowledge
├── Files
│   ├── 本地文件夹
│   ├── 上传文件
│   ├── 项目资料
│   └── 外部链接
├── Memory Center
│   ├── 全局用户记忆
│   ├── Workspace 记忆
│   ├── Agent 使用记忆
│   └── Mission 过程记忆
├── Memory Review Queue
│   ├── 待确认
│   ├── 待合并
│   ├── 可能过期
│   └── 可能冲突
└── Knowledge Map
    ├── 来源
    ├── 标签
    ├── 关联 Mission
    └── 关联 Agent
```

## 6. 子页面：Approvals / 审批中心

```text
Approvals
├── Pending Actions
│   ├── 文件读取
│   ├── 文件写入
│   ├── 命令执行
│   ├── 外部 Agent 调用
│   └── 记忆固化
├── Approval Detail
│   ├── 这次要做什么
│   ├── 为什么需要做
│   ├── 会影响哪些文件 / 平台
│   ├── 风险等级
│   └── 可选操作：允许 / 拒绝 / 修改范围
└── Approval History
    ├── 已允许
    ├── 已拒绝
    └── 自动通过规则
```

## 7. 子页面：Runtime / 本地执行

```text
Runtime
├── Device Status
│   ├── Mac App 在线状态
│   ├── Android 在线状态
│   └── Browser Extension 状态
├── Local Connectors
│   ├── Claude Code
│   ├── Codex
│   ├── Cursor
│   ├── Git
│   └── Shell
├── Permission Scope
│   ├── 可读目录
│   ├── 可写目录
│   ├── 禁止读取项
│   └── 高危动作规则
└── Runtime Logs
    ├── 心跳
    ├── 命令执行
    ├── 错误
    └── 版本更新
```

## 8. 子页面：Audit & Settings / 审计与设置

```text
Audit & Settings
├── Action Audit
│   ├── 读文件
│   ├── 写文件
│   ├── 跑命令
│   ├── 调 Agent
│   └── 上传上下文
├── Permission Policies
│   ├── Safe Mode
│   ├── Sovereign Mode
│   ├── 自动通过规则
│   └── 强制确认规则
├── Twin Profile
│   ├── 用户目标
│   ├── 沟通风格
│   ├── 工作偏好
│   └── 禁忌事项
└── Data & Privacy
    ├── 本地优先策略
    ├── 云端同步范围
    ├── 密钥边界
    └── 数据导出 / 删除
```

