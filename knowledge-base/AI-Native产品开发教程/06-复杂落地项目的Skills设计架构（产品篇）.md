<title>【教程】复杂落地项目的Skills设计架构（产品篇）</title>

<callout emoji="😆">
**结论：好 Skill 不是“写得长”，而是能做到不偏移的“好架构”**
</callout>

很多人做 Skill，第一反应是写一段很像人的提示词，告诉 AI “请帮我生成 xxx”。这类 Skill 往往第一次看起来还行，一进入返修、协作、项目扩展、换人接手，就开始漂。

而成熟的 Skill 则很早就抓住了真正会让项目失控的地方：**上下游依赖、优先级、必要确认环节、统一规范、返修联动。**把 AI 当成一个需要被约束的执行者来设计系统。

可以通过分层定义的方式来优化自己的项目工作方式，如定义⬇️

- **项目级** 文档定义公共真相
- **IDE 级** 文档定义本地协作方式
- **Skills** 定义某类任务的推进路径
- 组件表、字段表、页面表负责稳定名词系统

> memory 只保存那些无法从项目当前状态直接推导出来、但跨轮又很重要的信息

一旦这几层分开，AI 就不容易既当项目经理、又当设计系统、又当个人秘书、又当工作流引擎，最后每一层都做得半吊子。

# 理论篇

## 先定义主链路，再定义每一步的成功标准

项目复杂起来时，希望 Skill 大跃进式地一步生成完整且完美的文档，通常是不现实的。原因不只是上下文长度不够，更重要的是：复杂项目不是单纯的写作问题，而是**分阶段决策**的问题。

很多关键信息只有在中间产物出现后才会暴露出来，比如页面结构是否成立、字段是否冲突、命名是否统一、上下游是否对齐。你没有先做出上一层，就不可能一次把下一层写到真正可执行。一步生成，往往只会得到一份“看起来完整”的草稿，而不是一份能持续迭代的工作产物。

所以，一个 Skill 只要涉及多阶段产物，就必须先把主链路定下来。

<callout emoji="📌">
我的 Skill 对应写法：明确逻辑依赖
</callout>

```Markdown
## 概述

本 Skill 包含三个环节，按用户需求调用：

1. **产品原型spec生成**：将产品构思/框架/思路转化为结构化的原型 Spec（Markdown）
2. **原型demo生成**：基于原型 Spec 生成按功能点拆分的可交互 HTML 原型
3. **产品prd生成**：基于确认后的原型 Demo 生成正式 PRD 文档

三个环节遵循严格的单向依赖：原型 Spec → HTML 原型 → PRD。
修改任何上游文件时，必须同步更新所有下游文件。
```

这件事看起来普通，其实很关键。因为一旦链路先被写清楚，后面的很多判断就自然成立：

- 为什么不能直接改 PRD 不管上游
- 为什么改 Spec 后要提醒 HTML 和 PRD
- 为什么 Demo 确认后才补正式 PRD

再往前一步，真正成熟的 Skill 还要给每一步写“成功标准”，也就是做到什么程度才算这一阶段完成。分步骤的目的，是把复杂度拆开；成功标准的目的，是把这一阶段真正冻结。

没有成功标准，就会出现几种典型问题：

- AI 以为已经做完，其实只是写了一版草稿
- 上游还没确认，就贸然进入下游
- 团队对“现在能不能进入下一步”理解不一致
- 后续返修时，不知道这一阶段当时到底确认了什么

<callout emoji="📌">
我的 Skill 对应写法：每个环节都有明确的触发条件和前置检查
</callout>

```Markdown
## 环节二：原型demo生成

### 触发条件
用户提供以下任一输入时触发：
- 要求基于原型 Spec 生成 HTML 原型
- 要求修改已有的 HTML 原型
- 要求为某个功能点生成新的状态帧

### 前置检查
1. **确认原型 Spec 存在**：如果版本目录中没有原型 Spec，拒绝生成并提醒用户先创建 Spec
2. **读取 _shared/ 资源前先读完全部 readme**
3. **识别 shared 的 workspace/versions 结构**
4. **读取版本级样式**
5. **读取 design-system 前先完成 readme 扫描**
```

<callout emoji="✅">
**总结**
1. 多阶段 Skill 先写依赖方向，再写规则。
2. 每个阶段都要有**触发时机**。
3. 每个阶段都要有**完成标准**。
4. 每个阶段只解决一类核心决策，**不要贪图一步到位**。
5. 没有成功标准的 Skill，后面一定会靠模型临场猜。
</callout>

## 大项目里先统一定义（命名），再开始施工

很多团队做大项目时，最先出问题的不是页面，而是定义混乱。组件、字段、页面标题、文件名每个章节不一致、每个页面不一致、每个人不一致……最后设计、研发、测试、文档全都在各说各话。

我的 Skill 有一个很强的**基建意识**：它没有把“组件、字段、页面命名”当小事，而是把它们提升成协作基础设施。

<callout emoji="📌">
我的 Skill 对应写法：速查表同步规则
</callout>

```Markdown
## 速查表同步规则（写在项目级 readme 中）

1. `_shared/组件名称速查表.md`、`_shared/字段名称速查表.md` 和 `_shared/页面名称速查表.md`
   是项目级共享资产；凡是新增或返修需求、Spec、PRD、HTML 原型，结束前都必须检查并同步这三张表。
2. 本轮如果新增、重命名、废弃了组件、共享对象字段、`data-*` 绑定字段，
   必须把变更写回对应速查表；不能只改业务文件不改速查表。
3. 若本轮没有速查表增量，也要在执行结论中显式确认"本次无新增组件 / 字段 / 页面"。
```

<callout emoji="📌">
我的 Skill 对应写法：命名一致性规则
</callout>

```Markdown
## 命名一致性规则（写在项目级 readme 中）

1. 需求版本目录是唯一命名源：目录统一使用 `V{主版本}.{次版本}{功能名}`
2. 同目录下产物名必须一致：`【SPEC】`、`【PRD】`、`index.html`、各 `3.x页面名.html`
   的文件名、正文标题、目录卡标题、页头导航文案都必须复用同一套版本号与功能名
3. shared 版本与需求版本分开管理
4. 引用版本必须与路径一致
```

这套做法特别适合大项目，因为它等于在项目里提前定义了三种"唯一命名源"：

- 组件名来自组件速查表
- 字段名来自字段速查表
- 页面名和版本号来自版本目录与正文定义

<callout emoji="📌">
实际项目中的速查表长什么样
</callout>

以组件速查表为例，它不只是一张名称对照表，而是一个可执行的查找系统：

```Markdown
## 常用查找路径（组件速查表开头）

| 你想找什么 | 先搜什么 | 再看哪里 |
|------|------|------|
| 顶部切换 Tab | `.pg-segmented` / `createSegmentedTabs` | `bindSegmented`、`syncSegmented` |
| 输入框完整状态 | `.ds-shell-composer` / `.ds-input-shell` / `createComposer` | `initComposer` |
| 底部 Tab | `.pg-tabbar` / `createTabBar` | `syncTabs`、`bindTabBars` |
| 侧边栏 | `.pg-drawer` / `.sidebar-panel` / `createSidebar` | `bindDrawer`、`setDrawerOpen` |
```

字段速查表则把业务字段和 HTML `data-*` 属性一一对应：

```Markdown
## 任务共享字段（字段速查表节选）

| 字段名 | 中文语义 | 首次定义版本 | HTML / data-* 落点 |
|--------|----------|-------------|-------------------|
| `task_id` | 任务唯一标识 | V1.1 | 任务容器 `data-task-id` |
| `task_status` | 当前任务状态 | V1.1 | 状态标签 `data-task-status` |
| `task_stage` | 当前任务阶段 | V1.1 | 阶段条目 `data-task-stage` |
```

页面速查表按 APP 信息架构组织：

```Markdown
## 页面速查表（节选）

| 子页面 | 英文名 | 层级 | 说明 |
|--------|--------|------|------|
| 空态首页 | `page-chat-empty` | 一级视图 | 欢迎语 + 示例气泡 + 工具栏 + 输入区 |
| 会话页 | `page-chat-session` | 一级视图 | 用户消息 + AI回复 + 追问建议 |
| 侧边栏主面板 | `page-drawer` | 覆盖层 | 用户头像 + 新建对话 + 历史记录列表 |
```

<callout emoji="😆">
**总结**
抽象成通用经验，就是一句话：**大项目先统一定义，再开始施工。**
> 如果这一步不做，后面所有页面、原型、PRD、代码、埋点表都会慢慢长出自己的别名系统，最后返修成本会越来越高。
</callout>

## 规则一定要分层，别让一个 Skill 吞掉整个项目

真正的大项目，规则一定分层。不要把所有东西都塞进一个 Skill。一个 Skill 再强，也不应该同时承担：项目规则、个人偏好、IDE 自动化、业务工作流、权限策略、设计系统、命名词典……多种角色。

| 层级 | 主要解决什么 | 应该写什么 | 不该写什么 |
|-|-|-|-|
| Skill 级 | 某一类任务怎么做 | 工作流、触发条件、产物结构、同步规则 | 项目里所有命名和所有环境细节 |
| IDE 级 | 这个人在这个 IDE 里怎么和 AI 协作 | 权限、默认命令、hooks、个人沟通偏好、自动化 | 项目通用业务规则 |
| 项目级 | 这个仓库的公共约束是什么 | 目录、命名、设计系统、共享组件、字段协议、标准页 | 某个单任务的详细执行步骤 |

<callout emoji="📌">
我的 Skill 对应写法：项目级高于 Skill 级
</callout>

```Markdown
## 全局规则 → 项目启动前强制规则

执行具体项目时，若仓库根目录存在 `_shared/`，必须先读取其中全部 readme；
若存在 `_shared/AI_tutor_readme.md`，默认视为本轮工作的第一必读文件。
项目前置文件优先于通用 skill：`_shared/` 下 readme、设计规范、共享骨架
和项目指导文件都属于项目级硬约束；若与通用 skill 冲突，优先执行项目文件。
```

这就是非常成熟的“分层约束”意识。claude code 里也有相同思路，而且写成了系统级结构。它把能力来源按照policy / user / project 分层加载：

<callout emoji="🔗">
外部参考：`claude-code` 的 Skills 加载优先级
</callout>

```TypeScript
// claude-code/src/skills/loadSkillsDir.ts — getSkillsPath()
// 三层路径，优先级从低到高：

case 'policySettings':
  return join(getManagedFilePath(), '.claude', dir)   // 组织级策略
case 'userSettings':
  return join(getClaudeConfigHomeDir(), dir)           // 用户级偏好
case 'projectSettings':
  return `.claude/${dir}`                              // 项目级规则
```

```TypeScript
// claude-code/src/utils/claudemd.ts — Memory 文件加载顺序
// 1. Managed memory (eg. /etc/claude-code/CLAUDE.md) - 全局指令
// 2. User memory (~/.claude/CLAUDE.md) - 个人全局指令
// 3. Project memory (CLAUDE.md, .claude/CLAUDE.md, .claude/rules/*.md) - 项目指令
// 4. Local memory (CLAUDE.local.md) - 个人项目指令
// 文件按优先级反序加载，越后加载的优先级越高

```

<callout emoji="✅">
**总结**
1. Skill 负责“任务流程”。
2. IDE 负责“本地协作习惯和自动化”。
3. 项目文档负责“仓库级唯一真相”。
4. 真正稳定的系统，不是单层写得多，而是多层之间不抢职责。
</callout>

## 不把“客观事实”和“个人约束”混同

不是所有信息都该写进 Skill，也不是所有信息都该靠 memory。大项目里最重要的一条原则是：

**能从项目当前状态读出来的，就不要反复写进记忆层；必须跨轮保留、否则模型会忘的，才写进稳定文档层。**

<callout emoji="📌">
我的 Skill 对应写法：把事实指回权威源，而不是在 Skill 里重复定义
</callout>

```Markdown
## 生成约束（环节二）

31. **命名必须规范**：页面、组件、控件命名必须以 `_shared/design-system.md` 为准。
    共享原语用 `ds-`，页面级模块用 `pg-{page}-{block}`，
    状态用 `is-*` / `has-*`，脚本绑定优先使用 `data-*`

30. **生成前必读顺序固定**：每次生成前必须先扫描并读取 `_shared/` 目录下全部 readme 文件，
    再读取 `_shared/design-system.md`，最后读取目标页面当前引用的
    `_shared/versions/vX.Y.Z/` 下的 theme.css、components.css、shell.js

```

也就是说，组件语言、命名规则、目录结构，这些不是“聊天时顺便提一下」的信息，而是应该落在项目级文档和共享资源里的。Skill 只负责告诉 AI “去哪里读”，不负责把内容复制一遍。

<callout emoji="🔗">
外部参考：claude code 的 memory 类型设计明确排除了可推导信息
</callout>

```TypeScript
// claude-code/src/memdir/memoryTypes.ts — WHAT_NOT_TO_SAVE_SECTION
// 明确列出不该存入 memory 的信息类型：

export const WHAT_NOT_TO_SAVE_SECTION: readonly string[] = [
  '## What NOT to save in memory',
  '',
  '- Code patterns, conventions, architecture, file paths, or project structure'
  + ' — these can be derived by reading the current project state.',
  '- Git history, recent changes, or who-changed-what — `git log` / `git blame` are authoritative.',
  '- Debugging solutions or fix recipes — the fix is in the code; the commit message has the context.',
  '- Anything already documented in CLAUDE.md files.',
  '- Ephemeral task details: in-progress work, temporary state, current conversation context.',
]
```

```TypeScript
// claude-code 只允许存四种 memory：
export const MEMORY_TYPES = ['user', 'feedback', 'project', 'reference'] as const

// user: 用户角色、偏好、知识背景
// feedback: 用户对 AI 行为的纠正和确认
// project: 项目进展、决策、截止日期（不可从代码推导的）
// reference: 外部系统的指针（Linear 项目、Grafana 看板等）
```

<callout emoji="✅">
**总结**
- 设计系统、目录结构、组件命名、字段协议 → **放项目级文档**
- 个人偏好和本地 IDE 协作习惯 → **放 IDE 级文档或本地 settings**
- 某类任务怎么推进 → **放 Skill**
> 不要把这些本来应该结构化保存的东西，全都堆在聊天上下文或 memory 里。一旦把这层分清楚，AI 在大项目里会稳定很多，因为它知道应该去哪里找“当前真相”。
</callout>

## 真正能长期使用的 Skill，一定会关注“失败场景”，注意返修环节

很多 Skill 只会第一次生成，真正进入 2 到 5 轮迭代以后就开始失真。因为它们默认“生成”是正常情况，“修改”是例外。**但失败总是常态，所以我把返修作为必要环节**，每个环节都有独立的“修改时的同步规则”章节。

另外，项目复杂后，我们各处文件都有一定关联，所以必要的联动机制也是必要的。

<callout emoji="📌">
我的 Skill 对应写法：三个环节各自的返修联动
</callout>

```Markdown
## 修改已有原型 Spec 时（环节一）：
1. 向用户确认即将修改的文件路径和变更摘要，获得同意后再写入 git 仓库
2. 检查是否存在对应的 HTML 原型文件，若存在则提醒用户需要同步更新
3. 检查是否存在对应的 PRD 文件，若存在则提醒用户需要同步更新
4. 如果用户确认同步，按依赖顺序执行：先更新 HTML 原型，再更新 PRD
```

```Markdown
## 修改已有 HTML 原型时（环节二）：
1. 向用户确认即将修改的文件路径和变更摘要
2. 检查修改是否源于原型 Spec 的变更（是→不需要反向更新 Spec；否→提醒同步）
3. 检查是否存在对应的 PRD
4. 如果存在飞书 PRD 文档：提醒用户飞书文档中的原型预览链接可能需要更新
```

```Markdown
## 修改已有 PRD 时（环节三）：
1. git 写入需用户确认
2. 同时更新 git 和飞书
3. 飞书更新前检查评论并归档
4. 检查上游一致性：如果涉及功能点变更，提醒原型 Spec 和 HTML 原型可能需要同步
```

```Markdown
## 修改联动检查清单（全局）

任何修改操作完成后，按以下清单检查：
- [ ] 原型 Spec 是否与 HTML 原型一致？
- [ ] HTML 原型是否与 PRD 第3章一致？
- [ ] PRD 的 git 版本是否与飞书版本一致？
- [ ] 飞书文档中的原型预览链接是否有效？
- [ ] 飞书文档的评论是否已归档？
只有全部一致时，才算修改完成。
```

<callout emoji="😆">
**总结**
如果 Skill 只会第一次生成，它只是 demo
如果它能稳定返修，**拥抱失败**，才是生产工具
</callout>

# 实战篇

## Skill 如何和大型项目的 shared 架构配合

<callout emoji="🌅"><p>成果篇：<cite doc-id="Qu42wsmjSiShAOkjreqccNI2nbe" file-type="wiki" title="【规范】协作V1：AI Native 产品迭代指导方针" type="doc"></cite></p></callout>

前面讲的都是方法论，这一节讲落地。一个 Skill 要在大项目里稳定工作，必须和项目的共享架构配合。以「小米智学」项目为例，`_shared/` 目录解决两个核心问题：**一致性问题**和**版本迭代管理**。

<callout emoji="📌">
我的项目架构：`_shared/` 的物理隔离版本体系
</callout>

```Markdown
## 版本目录结构（项目级 readme 中定义）

_shared/versions/vX.Y.Z/
├── theme.css                    ← 共用 Token 变量
├── tailwind-config.js           ← 共用 Tailwind 配置
├── phone-shell/                 ← 手机帧内部样式
│   ├── components.css           ← 手机帧内组件样式（唯一来源）
│   └── shell.js                 ← 手机帧交互 helper
└── prototype-gallery/           ← 原型展示外框样式
    ├── prototype-gallery.css    ← 外框布局、说明卡、步骤标题等
    ├── prototype-gallery.js     ← 外框交互（demo 切换等）
    └── prototype-shell-template.html  ← 标准页面模板

```

Skill 怎么和这套架构配合？关键是 Skill 里写了“先读什么、再读什么、引用哪个版本”的完整链路：

```Markdown
## 前置检查（环节二 · 原型demo生成）

1. 确认原型 Spec 存在
2. 读取 _shared/ 资源前先读完全部 readme
3. 识别 shared 的 workspace/versions 结构：
   先确定目标页面当前引用的版本号，以及本轮是只改页面，还是需要升级共享组件版本
4. 读取版本级样式
5. 读取 design-system 前先完成 readme 扫描
6. 同版本页面必须先锁定已确认标准页
```

```Markdown
## 组件版本冻结规则（项目级 readme 中定义）

当需要修改组件样式时，必须按以下步骤执行：
1. 在 `_shared/workspace/` 的对应文件上修改
2. 修改完成并确认无误后，读取 `_shared/versions/` 目录，找到当前最大版本号，递增
3. 创建新版本目录，按版本目录结构组织文件
4. 需要使用新组件的页面，将引用路径改为新版本
5. 不需要更新的页面保持原有版本引用不动

禁止任何页面直接引用 `_shared/workspace/` 下的文件。
```

<callout emoji="😆">
**总结**
Skill 定义工作流，项目文档定义约束，shared 快照定义物理隔离，三者各司其职
</callout>

## 我建议你在任何大项目里都建立这四类文件

#### 项目级 README

用途：定义这个仓库的公共真相。

```Markdown
# 项目级说明

## 1. 项目里哪些文件是唯一真相
## 2. 目录和版本命名规则
## 3. 设计系统与共享组件入口
## 4. 组件名称、字段名称、页面名称定义
## 5. 哪些修改需要同步上下游
## 6. 哪些动作必须先征得用户确认
## 7. 标准验证方式和发布前检查

```

#### IDE 级 settings / steering

用途：定义“这个人在这个环境（IDE工具）里怎么和 AI 协作”。

```Markdown
# IDE 级协作说明

## 1. 默认沟通风格
## 2. 默认验证动作
## 3. 高风险动作确认规则
## 4. 常用命令与 hooks
## 5. 本地自动化与权限边界
```

#### Skill 级 SKILL.md

用途：定义某类任务应该怎么做。

```Markdown
---
name: <skill 名称>
description: <这类任务解决什么问题>
---

# <skill 名称>

## 概述
## 全局规则
### 项目启动前强制规则
### 文件同步规则
### 写作基调

## 环节一
### 触发条件
### 输入处理
### 输出结构
### 修改时的同步规则

## 环节二
### 触发条件
### 前置检查
### 生成方法
### 生成约束
### 修改时的同步规则

## 环节三
...

## 环节调度逻辑
## 本轮返修经验补充

```

<callout emoji="🔗">
外部参考：`claude-code` 的 Skill 加载机制
</callout>

```TypeScript
// claude-code/src/skills/loadSkillsDir.ts
// Skill 只支持目录格式：skill-name/SKILL.md
// 支持 frontmatter 字段：name, description, when_to_use, allowed-tools,
//   user-invocable, model, paths, hooks, context, agent, effort, shell

// claude-code/src/skills/bundledSkills.ts
// 内置 Skill 的注册接口：
type BundledSkillDefinition = {
  name: string
  description: string
  whenToUse?: string        // 什么时候自动触发
  allowedTools?: string[]   // 允许使用的工具白名单
  hooks?: HooksSettings     // 关联的 hooks
  context?: 'inline' | 'fork'  // 执行上下文
  files?: Record<string, string>  // 附带的参考文件
  getPromptForCommand: (args, context) => Promise<ContentBlockParam[]>
}

```

#### 词典级文件

这是很多团队最容易漏掉的一层，但一旦项目做大，它们的价值会非常高。

我的项目中目前包括：

- `组件名称速查表.md` — 组件中文名 ↔ CSS 类名 ↔ 使用页面
- `字段名称速查表.md` — 业务字段 ↔ data-\* 属性 ↔ 首次定义版本
- `页面名称速查表.md` — 页面名称 ↔ 英文名 ↔ 层级 ↔ 说明

根据你的项目性质，你可以对其进行删减或拓展，适应真实业务场景。