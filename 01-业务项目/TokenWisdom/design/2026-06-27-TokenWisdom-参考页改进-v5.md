# TokenWisdom 工作台 v5：参考页改进说明

- 日期：2026-06-27
- 输入参考：Multica 类三栏 Agent 管理页面截图
- 结论：参考页适合作为“Agent 配置后台”的局部参考，但不能作为 TokenWisdom 首页。TokenWisdom 首页应该是“用户工作推进台”，而不是“Agent 列表 + 配置表单”。

## 1. 参考页值得借鉴的点

```text
可借鉴
├── 左侧稳定导航：用户知道自己处在哪个模块
├── 中间对象列表：Agent / Project / Task 可以快速切换
├── 右侧详情编辑：适合配置 Instructions / Skills / Memory
├── 极简视觉：低干扰，适合长时间使用
└── 标签页结构：Instructions / Skills / Tasks / Memory 适合管理 Agent
```

## 2. 参考页不适合 TokenWisdom 的点

```text
问题
├── 它是 Agent 管理页，不是个人工作台
├── 中央大面积是配置文本，没有体现“当前工作状态”
├── 缺少用户目标、任务进度、历史沉淀和下一步确认
├── 没有数字分身常驻对话框
├── 没有 User → Twin Agent → Agents 的协作关系
├── 没有 Agent-to-Agent 对话空间
├── 没有 token 消耗、好文档、报告、总结这些个人工作资产
└── 页面让用户“配置 Agent”，而不是“通过分身推进工作”
```

## 3. v5 设计方向

v5 采用“操作型三栏 + 常驻分身”的结构：保留参考页的清晰分栏，但把中心从 Agent 配置改成工作台。

```text
TokenWisdom v5
├── 左侧 Global Nav
│   ├── Workbench
│   ├── Work Rooms
│   ├── Tasks
│   ├── Agents
│   ├── Artifacts
│   ├── Reports
│   └── Twin Manager
├── 左中 Context List
│   ├── 当前工作区
│   ├── 运行任务
│   ├── 最近文档
│   └── 最近使用 Agent
├── 中间 Work Surface
│   ├── 今日状态总览
│   ├── 重点工作卡片
│   ├── 任务推进流
│   ├── Agent-to-Agent Room 摘要
│   └── 产出与沉淀
└── 右侧 Persistent Twin Dock
    ├── 数字分身长期对话框
    ├── 当前页面上下文
    ├── 待确认请求
    ├── 快捷操纵工作台
    └── 进入 Twin Manager
```

## 4. 首页应该显示什么

```text
Workbench Home
├── 当前状态
│   ├── 运行任务数
│   ├── 待确认动作
│   ├── 今日 token 消耗
│   ├── 本周沉淀文档
│   └── 已连接 Agent
├── 工作区入口
│   ├── Code Development
│   ├── Knowledge Management
│   ├── AI Tool Automation
│   └── Daily Ops
├── 在运行的任务
├── 历史任务
├── 已用工具类 Agent
├── 好文档 / 沉淀内容
├── 总结
└── 报告 / 其他输出
```

## 5. Twin Manager 应该独立

数字分身管理不是首页主体，而是独立界面。首页只给出入口和摘要。

```text
Twin Manager
├── Twin Profile
│   ├── 分身名称
│   ├── 工作风格
│   ├── 用户偏好
│   └── 不可越权边界
├── Memory Files
│   ├── user-preferences.memory.md
│   ├── project-context.memory.md
│   ├── decisions.memory.md
│   └── pending-memory.md
├── Agent MD Files
│   ├── codex-agent.md
│   ├── claude-code-agent.md
│   ├── cursor-agent.md
│   └── browser-agent.md
├── Token & Cost
│   ├── 按 Agent 统计
│   ├── 按任务统计
│   ├── 预算告警
│   └── 高消耗回放
└── Saved Learnings
    ├── 好文档
    ├── 高质量 prompt
    ├── 可复用工作流
    └── Agent 使用经验
```

## 6. v5 页面原则

- 首页是工作台，不是配置台。
- 左中栏像参考页一样提供快速切换，但对象应是“工作”，不是只有 Agent。
- 中央区域展示状态、任务、产出和下一步动作。
- 右侧永远是数字分身，不被任何详情页替代。
- Agent 配置、Memory 文件、Token 消耗进入 Twin Manager。
- 每个工作项都能进入具体工作页，并让数字分身带上下文继续操作。
