# 

> 来源：飞书文档，更新时间：2026-04-22T09:03:49.000Z

# Handoff Protocol — 亮点功能全景图

## 背景：我们遇到了什么问题

### 问题一：同一个结论要讲三遍

产品花了半天跟 AI 把一个页面的每个状态、每个跳转都捋清楚了，Demo 也跑通了。然后研发一上手——"这个按钮什么时候该灰掉？" 测试一写用例——"登录失败走哪条路？"

明明都澄清过了，但那些结论散在聊天记录里、会议纪要里、Demo 的某个角落里，下游捞不到，只能再问一遍。

### 问题二：改了一个地方，不知道还有哪里要跟着改

产品说"验证码倒计时从 60 秒改成 90 秒"。研发改了代码，但测试用例里还写着 60 秒。Demo 更新了，但文档没跟上。需求一变，谁该跟着改、改到哪里算完，全靠人记。

### 问题三：同一个东西，每个人的 AI 用不同的词表述

产品管一个东西叫"底部操作栏"，研发的 AI 叫它"safe-area"，测试的 AI 叫它"底部按钮区"。明明是同一个组件，三个名字，AI 以为是三个东西，各做各的，最后拼不起来。

## 解决思路：Handoff Protocol

针对上面三个问题，我们的思路是建立一层结构化的交接协议——产品澄清一次，结论落进一个文件，后面所有角色的 AI 都读这同一份文件继续工作。

| 问题 | 现状 | Handoff 怎么解决 |
|-|-|-|
| 反复解释 | 产品跟 AI 讲一遍，跟研发讲一遍，跟测试再讲一遍 | 结论写进 handoff，下游自己读，产品只需确认一次 |
| 变更失控 | Demo 改了文档没跟上，代码改了测试不知道 | 改了什么、影响哪些页面，跑个 `/diff` 全出来 |
| 命名不统一 | 同一个按钮三个名字，AI 当成三个组件 | 全局统一命名，AI 读得准、写得稳、改得对 |

具体来说，一个 handoff 文件包含四层视图，每个角色只维护自己那一层：

| 角色 | 负责的层 | 从 handoff 读什么 | 往 handoff 写什么 |
|-|-|-|-|
| 产品 | product | —（源头） | 布局、状态机、导航、验收标准 |
| 设计 | design | product 层的布局和交互 | Token、标注、审查结论 |
| 研发 | dev | product + design | 路由、组件路径、接口定义 |
| 测试 | test | product + dev | 测试矩阵、边界场景、验收结果 |

安装时每个人选自己的角色，脚本把对应的 AI 工作流装进 IDE。产品的 AI 知道怎么生成 handoff，研发的 AI 知道怎么消费 handoff 写代码，测试的 AI 知道怎么从 handoff 提取测试矩阵。每次修改都走 handoff 记录，`/diff` 一跑，谁改了什么一目了然。

| 指令 | 使用时机 | 作用 |
|-|-|-|
| `/validate` | 交出去之前 | 检查 handoff 是否有明显缺项，避免把半成品往下传 |
| `/diff` | 改完需求之后 | 告诉团队这次改了什么，不用所有人重读一遍 |
| `/claim` | 开始做之前 | 锁定负责范围，避免两个人同时改同一个页面 |
| `/complete` | 做完之后 | 交棒给下一个人，测试或产品知道可以开始验收 |
| `/preview` | 想看效果时 | handoff 直接渲染成手机页面，浏览器里就能看 |

---

### 存量项目接入：产品仓库扫描 + 研发仓库扫描

新项目从零开始用 Handoff 很自然，但存量项目怎么办？已经有一堆 HTML 原型、Spec 文件、组件库、Flutter 代码了，不可能全部重写。

`handoff scan` 就是解决这个问题的。它分两个方向扫描：

**产品仓库扫描**（扫描产品侧已有资产）

扫描产品 Git 仓库中的 HTML 原型、Spec 文件、共享组件表、页面命名表、字段命名表等，提取出：

- 已有页面清单（页面名、路由、对应的 Spec 文件路径）
- 已有共享组件（组件名、所在文件、被哪些页面引用）
- 已有字段定义（字段名、类型、语义描述）
- 已有 Design Token（CSS 变量名、值、使用范围）

这些信息会写入 handoff 的 product 层和 design 层，作为存量项目的冷启动基础。后续新增需求时，AI 知道哪些页面和组件已经存在，不会重复生成。

**研发仓库扫描**（扫描代码侧已有实现）

扫描研发 Git 仓库中的代码文件，自动检测技术栈（Flutter / React / Compose），提取出：

- 路由定义 → 写入 `page.dev.route`
- 组件文件 → 写入 `page.dev.components`，同时与 21 种内置节点类型匹配
- API 端点 → 写入 `page.dev.api`
- 数据模型 → 写入 models 索引

无法匹配内置类型的组件，自动创建 `customNodeTypes` 条目并写入 `node-type-registry.json`，标记 `source: "project-scan"`。这样研发侧已有的组件库就和 Handoff 的两个方向扫完之后，存量项目就有了一份完整的"现状快照"，后续的增量需求可以在这个基础上继续迭代。

---

以上是 Handoff 要解决的问题和基本用法。接下来展开看一下具体做了哪些能力——整体分成七层，从底层协议定义到上层外部集成，逐层往上搭。

## 一、核心协议层

| \\# | 功能 | 说明 |
|-|-|-|
| 1 | 单文件四层结构（v2） | 一个功能一个 `.handoff.jsonc`，内嵌 product / design / dev / test 四个视图。四个角色各取所需，消除信息孤岛。 |
| 2 | 21 种内置节点类型 + customNodeTypes | layoutTree 覆盖移动端常见 UI 组件（scaffold / app-bar / scroll-view / column / row / text / text-field / button / image / checkbox / rich-text / stack / grid / conditional 等）。遇到新类型时 AI 主动澄清并创建自定义类型定义，下游自动学习。 |
| 3 | 可执行状态机（stateMachine） | 不是画图，是可直接运行的状态转换定义。含 guards 守卫条件、meta 元数据（countdown / timeout）、UI 状态映射（disabled / enabled / loading / hidden），研发直接翻译为代码。 |
| 4 | Design Token 系统 | 颜色 / 字号 / 间距 / 圆角全部 `$token` 引用，支持 light / dark 双主题。含 `devToken` 字段直接映射到代码常量（如 `AppColorTokens.kBrand`）。 |
| 5 | \$ref 引用拆分 | 复杂页面可拆分为子 handoff 文件，resolveRefs 自动合并，支持循环引用检测和错误降级渲染。 |
| 6 | Confidence 三级标注 | confirmed（已确认）/ tentative（暂定）/ placeholder（占位）。研发按置信度分配投入，避免在"暂定"需求上过度开发。 |

## 二、智能引擎层

| \\# | 功能 | 说明 |
|-|-|-|
| 7 | Review Engine（审查引擎） | 五大类别自动审查：布局完整性、状态机完备性、导航覆盖、无障碍、协议字段。生成 gate 通过 / 不通过结论，阻止低质量交付物流入下游。 |
| 8 | Prompt Optimizer（提示词优化器） | 4 维度评分：结构 30% + 术语 25% + 清晰度 25% + 具体性 20%。3 种模式：analyze（分析）/ optimize（优化）/ evaluate（评估）。postToolUse hook 自动触发，分数低于 70 时建议优化。 |
| 9 | Diff Engine（差异引擎） | 对比两个版本的 handoff 文件，输出结构化差异报告。支持 layoutTree 树级 diff，精确到节点级别的增删改。 |
| 10 | Constraint Engine（约束引擎） | 内置约束规则集，验证 handoff 文件的结构正确性和完整性。支持自定义规则扩展。 |
| 11 | Quality Scorer（质量评分） | 对 handoff 文件整体质量打分，量化交付物质量，为持续改进提供数据基础。 |
| 12 | Decision Recorder（决策记录器） | 产品验收反馈时自动追加决策记录（topic / chosen / rejected / reason / decidedBy），保留设计决策的完整历史，避免重复讨论。 |

## 三、协作管理层

| \\# | 功能 | 说明 |
|-|-|-|
| 13 | Lock Manager（锁管理器） | 多人协作时的 scope 认领 / 完成 / 放弃机制，防止冲突。支持超时检测和同步标记。 |
| 14 | Knowledge Capture（知识沉淀） | 从 review 和回顾中提取知识条目，支持 Git 沉淀和飞书同步，团队经验不丢失。 |
| 15 | Shared Component Tracker（共享组件追踪） | 跨页面共享组件的影响分析。修改一个组件时自动列出所有受影响页面，防止遗漏。 |
| 16 | Asset Hash（资源哈希） | 图片等资源文件的变更检测，避免遗漏资源更新。 |
| 17 | Version Tracker（版本追踪） | 页面级别的演进历史记录，追踪每个页面从创建到当前的完整变更链。 |
| 18 | Telemetry（遥测） | 记录人工决策和 AI 建议的采纳率，为 Prompt Optimizer 提供反馈数据，驱动自优化。 |
| 19 | Language Profile（语言画像） | 记录团队的术语偏好和纠正历史，AI 自动适应团队用语习惯。 |

## 四、渲染与预览层

| \\# | 功能 | 说明 |
|-|-|-|
| 20 | Demo Renderer（H5 预览渲染器） | handoff → 单文件 HTML。iPhone 模拟器外壳（375×812 + Dynamic Island + iOS 状态栏），产品无需 Figma 即可验收 UI。 |
| 21 | Token → CSS 变量自动映射 | design.tokens 自动生成 `:root` CSS 变量，支持 light / dark 主题切换，\$token 引用自动替换为 `var(--name)`。 |
| 22 | 状态机交互面板 | 右侧面板可点击事件触发状态转换，Guard 条件勾选框，转换历史记录，当前状态高亮。 |
| 23 | Happy Path 自动播放 | 一键演示完整用户流程，每步 1 秒间隔，Guard 未满足时自动暂停并提示。 |
| 24 | SVG 图标内置映射 | 8 种常用图标（arrow-left / arrow-right / close / check / menu / search / more / share）自动渲染为 SVG，无需外部图标库。 |
| 25 | Node Type Registry（节点类型注册表） | 存量项目扫描已有组件库，自动建立组件 → 节点类型映射，固化到 `node-type-registry.json`，新老项目无缝衔接。 |

## 五、CLI 工具链

| \\# | 命令 | 说明 |
|-|-|-|
| 26 | handoff start | 交互式技术栈选择，搜索 handoff 文件，生成 PROMPT.md（含 layoutTree / stateMachine / navigation 摘要 + P0-P4 优先级规则）。 |
| 27 | handoff preview | 渲染 handoff 为 H5 并在浏览器打开。支持 `--watch` 热重载（WebSocket），文件变更后 500ms 内自动刷新。 |
| 28 | handoff scan | 扫描代码仓库，自动检测技术栈（Flutter / React / Compose），生成组件清单和 node-type-registry。 |
| 29 | handoff validate / check / diff / review | 验证文件结构、检查约束、对比差异、执行审查 — 完整的质量保障工具链。 |
| 30 | handoff claim / complete / abandon | 协作生命周期管理：认领 scope → 完成实现 → 放弃认领，配合 Lock Manager 防冲突。 |
| 31 | handoff optimize-prompt | CLI 版提示词优化，分析当前 handoff 文件的 prompt 质量并给出优化建议。 |

## 六、多 IDE 适配层

| \\# | IDE | 适配方式 | 特色 |
|-|-|-|-|
| 32 | Kiro | steering + hooks + agents | 4 个角色 Agent + 7 个自动化 Hook + 3 个 Steering 文件 |
| 33 | Cursor | rules + commands | .cursorrules + 4 个角色 workflow + 6 个命令 |
| 34 | Claude Code | skills + commands + CLAUDE.md | 4 个角色 skill + 6 个命令 |
| 35 | Codex | skills + commands + AGENTS.md | 4 个角色 skill + 6 个命令 |
| 36 | OpenCode | modes + commands + AGENTS.md | 5 个模式（含 review）+ 6 个命令 |

<callout emoji="📦">
所有 5 个 IDE 适配器均提供一键安装脚本（`install.sh`），交互式角色选择（产品 / 设计 / 研发 / 测试），自动安装对应配置文件。所有 dev-workflow 内置 P0-P4 优先级处理规则。
</callout>

## 七、外部集成层

| \\# | 功能 | 说明 |
|-|-|-|
| 37 | 飞书 Handoff Bridge  <br/>（正在急速施工中） | GitLab Webhook → 飞书卡片通知，飞书回调 → 认领 / 完成操作，用户映射，超时检查。支持私有化部署（FEISHU\\\_BASE\\\_URL 可配置）。 |
| 38 | GitLab CI 集成 | CI pipeline 中自动验证 handoff 文件，MR 合并前确保交付物质量达标。 |

## 核心差异化总结

<grid>
<column width-ratio="0.500000">
### 相比传统交接方式
- ❌ 口头沟通 → ✅ 结构化协议
- ❌ 截图标注 → ✅ 可执行状态机
- ❌ Figma 链接 → ✅ H5 即时预览
- ❌ 会议对齐 → ✅ AI 自动审查
- ❌ 人工跟踪 → ✅ 锁管理 + 超时检测
</column>
<column width-ratio="0.500000">
### 我们做到了什么
- ✅ 四层结构覆盖产品、设计、研发、测试
- ✅ 5 个 IDE 适配，不绑定单一工具
- ✅ 状态机可执行，不只是静态布局描述
- ✅ Confidence 标注，研发按置信度分配投入
- ✅ 知识沉淀 + 语言画像，团队越用越顺
</column>
</grid>

## 相关文档

- [端到端演示 — 从用户输入到 H5 预览](https://www.feishu.cn/docx/XW50dRaqjo4D6nxBO5xc9kAJnuq)
- [团队分享 — AI 时代的跨角色协同框架](https://www.feishu.cn/docx/DiOldPYaoobzxAxGyYtcHCScnhe)
- [安装指南 + 基础教程](https://www.feishu.cn/docx/D1rrdF8PioYeL1xXKQecfct6nwC)
- [命令参考手册](https://www.feishu.cn/docx/ERh6dITjKoaOZqxfw59cGkDrn4f)