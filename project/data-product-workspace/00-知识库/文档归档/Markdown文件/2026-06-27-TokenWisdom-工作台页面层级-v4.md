# TokenWisdom 工作台页面层级 v4：Twin-Controlled Workbench

- 日期：2026-06-27
- 版本目标：把主页面从“关系说明页”改成真正的个人 AI 工作台。
- 核心模型：User → Twin Agent → Agents，但首页重点不再展示关系图，而是展示用户正在推进的工作、历史沉淀和可继续操作的资产。
- 全局规则：右侧始终常驻数字分身对话框；用户可以通过数字分身操纵工作台中的任务、文档、报告和外部 Agent。

## 0. 总体布局

```text
TokenWisdom App Shell
├── 左侧导航
│   ├── Workbench（首页）
│   ├── Tasks
│   ├── Artifacts
│   ├── Agents
│   ├── Reports
│   ├── Twin Manager
│   └── Audit / Runtime
├── 中间工作台
│   ├── 当前状态
│   ├── 工作区卡片
│   ├── 任务与资产列表
│   └── 点击进入具体工作页面
└── 右侧常驻数字分身 Dock
    ├── 长期对话框
    ├── 当前页面上下文
    ├── 待确认动作
    └── 操纵工作台的快捷指令
```

## 1. 首页：Workbench

首页是用户每天打开 TokenWisdom 后的默认落点，不再先解释产品概念，而是直接回答四个问题：现在在做什么、之前做过什么、沉淀了什么、下一步要确认什么。

```text
Workbench
├── Status Overview
│   ├── 今日运行任务数
│   ├── 等待确认事项
│   ├── 已连接 Agent 数
│   ├── 新增沉淀内容
│   └── API Token 消耗概览
├── Active Workspaces（点击进入具体工作页面）
│   ├── Code Development：Claude Code / Codex / Cursor
│   ├── Knowledge Management：File Agent / Knowledge Agent
│   ├── AI Tool Automation：Browser Agent / Web App Agent
│   └── Daily Ops：Mail / Calendar / Todo Agent
├── Running Tasks
│   ├── 任务名称
│   ├── 参与 Agent
│   ├── 当前状态
│   ├── 下一步动作
│   └── 是否需要用户确认
├── History Tasks
│   ├── 最近完成
│   ├── 最近暂停
│   ├── 可复用任务模板
│   └── 可继续推进任务
├── Used Tool Agents
│   ├── 最近使用
│   ├── 使用次数
│   ├── token 消耗
│   ├── 成功率 / 质量评分
│   └── 再次调用入口
├── Good Documents
│   ├── 用户确认过的好文档
│   ├── 从任务产出的方案 / PRD / 报告
│   ├── 可复用模板
│   └── 一键加入知识库
├── Summaries
│   ├── 日总结
│   ├── 项目总结
│   ├── Agent 协作总结
│   └── 用户待确认记忆
└── Reports / Other Outputs
    ├── 分析报告
    ├── 周报 / 月报
    ├── 导出文件
    └── 外部平台同步结果
```

## 2. 工作台卡片点击后的具体工作页面

每张工作台卡片都可以进入一个具体页面。页面里保留右侧数字分身 Dock，数字分身会带着当前工作页上下文继续对话。

```text
Workspace Detail
├── Work Brief
│   ├── 目标
│   ├── 进度
│   ├── 参与 Agent
│   └── 用户确认边界
├── Agent Room
│   ├── User
│   ├── Twin Agent
│   ├── Tool / Expert Agents
│   └── Agent-to-Agent 对话
├── Task Board
│   ├── To Confirm
│   ├── Running
│   ├── Review
│   └── Done
└── Outputs
    ├── 文档
    ├── 总结
    ├── 报告
    └── 可沉淀记录
```

## 3. 右侧常驻数字分身 Dock

右侧 Dock 是全平台最重要的操作入口。它不是普通客服聊天框，而是用户操纵工作台的自然语言控制层。

```text
Twin Dock
├── Identity
│   ├── 数字分身名称
│   ├── 当前权限等级
│   ├── 当前页面上下文
│   └── 参与中的 Agent Room
├── Conversation
│   ├── 用户直接下达目标
│   ├── 分身解释当前状态
│   ├── 分身整理任务下一步
│   └── 分身发起确认请求
├── Workbench Control
│   ├── 创建任务
│   ├── 继续任务
│   ├── 调用 Agent
│   ├── 总结结果
│   ├── 生成报告
│   └── 保存沉淀
└── Pending Confirmations
    ├── 文件写入确认
    ├── 外部 Agent 调用确认
    ├── API token 消耗确认
    ├── 发送 / 同步确认
    └── 长期记忆写入确认
```

## 4. 数字分身管理界面：Twin Manager

每个用户都有一个独立的数字分身管理界面。这里不是工作台的首页内容，而是管理分身长期能力、权限、消耗和知识沉淀的后台。

```text
Twin Manager
├── Twin Profile
│   ├── 名称 / 头像 / 角色描述
│   ├── 用户偏好
│   ├── 工作风格
│   ├── 代表用户说话的边界
│   └── 不能替用户确认的动作
├── Memory Files
│   ├── 用户偏好 memory.md
│   ├── 项目背景 memory.md
│   ├── 决策记录 memory.md
│   ├── 冲突记忆
│   └── 待确认记忆
├── Agent MD Files
│   ├── Claude Code 使用说明
│   ├── Codex 使用说明
│   ├── Cursor 使用说明
│   ├── Browser Agent 能力卡
│   └── 用户自定义 Agent 说明
├── API Token & Cost
│   ├── 按 Agent 统计 token 消耗
│   ├── 按任务统计 token 消耗
│   ├── 预算与预警
│   └── 高消耗操作回放
├── Saved Learnings
│   ├── 好文档
│   ├── 高质量 prompt
│   ├── Agent 协作经验
│   ├── 可复用工作流
│   └── 历史沉淀记录
└── Permissions
    ├── 默认权限等级
    ├── 白名单工具
    ├── 黑名单目录 / 平台
    ├── 高风险动作确认规则
    └── 一键暂停分身
```

## 5. 首页不需要承载的内容

首页只展示摘要、入口和下一步动作，不承载深层编辑和配置。

```text
首页不做
├── 不编辑 memory 原文
├── 不编辑 Agent MD 文件
├── 不做详细 token 账单分析
├── 不做权限规则深度配置
└── 不展示完整审计日志

这些内容进入 Twin Manager / Audit / Runtime 等子页面。
```

## 6. 页面设计重点

- 首页是“工作台”，不是营销页，也不是关系概念页。
- 每个模块都要能被点击进入具体工作页面。
- 数字分身 Dock 始终存在，并能操纵首页上的任务、文档、报告和 Agent。
- 首页展示任务、历史、Agent、好文档、总结、报告等内容，但只展示摘要和入口。
- 数字分身管理界面独立，用于管理分身本身、memory、Agent MD、token 消耗和沉淀记录。
