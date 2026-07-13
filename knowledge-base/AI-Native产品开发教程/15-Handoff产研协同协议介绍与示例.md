<title>【Handoff教程】Handoff产研协同协议介绍与示例</title>

<callout emoji="💡">
**Handoff** 是**产设研测接力用的协议文件**。它把团队**已经确认的需求结论**，存成一棵人和 AI 都能读懂的页面**语义树**，再把这棵树和接口、代码、测试等信息绑定起来。
- **可预览：**用于需求Demo评审预览器能把语义树渲染成可交互 Demo，大家直接看页面、状态和跳转，便于人审阅。
- **可存储：**用于项目知识库存储AI能把它当作结构化知识库读取，作为项目的统一上下文基准线，避免事实偏移。
- **可对齐：**需求迭代协作需求变更、接口字段、代码文件和测试口径等信息都可挂载在同一页面节点，便于接力工作。
</callout>

# 介绍：Handoff协议

## Handoff 协议解决什么问题

AI Native 协作里最浪费时间的环节，是同一个需求被反复解释。

产品和 AI 澄清过一次，设计再问一次；研发接手时再问一次；测试验收时再问一次。

换人、改需求、多人并行时，这种重复会继续放大。

<callout emoji="📝">
**Handoff 做三件事**
- 把产品、设计、研发、测试已经确认的结论放到同一份交接物里。（一份真正的全栈PRD）
- 让 AI 和下游同事能稳定读取、增量更新、追踪差异，不靠聊天记录猜上下文。
- 让 Demo、实现范围、接口字段、测试口径围绕同一个需求分支接力。
</callout>

<whiteboard token="KufYwypzNhZpXpbGD8scAA4wnbf"></whiteboard>

| 协作问题 | 没有 Handoff 时 | 有 Handoff 时 |
|-|-|-|
| 重复澄清 | 下游从群聊、截图、口头描述重新理解需求 | 下游读取同一份交接事实继续推进 |
| 事实偏移 | Demo、设计稿、代码和测试口径各写各的 | 页面、状态、动作、字段、接口同源维护 |
| AI 接力不稳 | 同一个页面或字段被叫成不同名字 | 语义名、状态名、动作名统一后，AI 能稳定续写 |
| 多人并行撞车 | 不知道谁负责哪一页、哪条链路 | 通过 claim/status 记录认领范围和进度 |

> 判断标准：如果信息只适合留在聊天里，它还是讨论；如果它会影响设计、研发或测试动作，就应该进入 Handoff。

## Handoff 是语义树

<callout emoji="⭐">
按当前 Handoff schema，它的核心结构就是**语义树**。
> **语义树的意思：**一页界面被拆成一个根节点和很多子节点。每个节点说明“我是什么”，再说明“我显示什么、什么时候显示、触发什么动作、用什么样式”。
参考 Claude Design 一类设计思路：页面不应只是截图，也不应只是 HTML 片段。页面应被表达成一棵模型能理解的组件树。此外，Handoff 在**语义树基础上继续补齐状态、接口、代码映射和测试依据**。
</callout>

一个页面节点通常包含这些信息：

| 字段 | 大白话解释 | 例子 |
|-|-|-|
| `id` | 节点唯一名字，方便定位和修改 | `wt_topbar_b1e2` |
| `semantic_role` | 这个节点在业务里的角色 | `summary_card`、`input_bar` |
| `$ref` | 复用哪个组件定义 | `definitions.TopBar` |
| `props/content` | 节点展示的文案、数据或参数 | `{topic_name}`、`按住说话` |
| `children` | 子节点，组成树结构 | 顶栏里有返回、标题、设置 |
| `visibility` | 什么状态下显示 | `current == paused` |
| `action` | 用户点了以后触发什么 | `toggle_audio`、`raise_hand` |

Handoff 会把页面拆成机器能消费的语义结构，例如：

```Plain Text
page
└── scaffold              页面整体骨架，决定这一页由哪些区域组成
    ├── top_bar           顶部导航区，比如返回、标题、设置、语音开关
    ├── query_bar         题目信息区，比如当前讲解的题目或用户输入
    ├── board_canvas      白板讲解区，承载 AI 板书、步骤推导和重点标注
    ├── summary_card      总结卡片区，展示课堂总结、知识点回顾或老师点评
    └── input_bar         底部输入区，支持拍照、输入、语音、追问等操作
```

## Handoff 和产品 Spec 的关系

产品 Spec 先回答“为什么做、为谁做、做什么、什么目标”。Handoff 再把确认后的需求翻译成“具体怎么做、怎么交给设计、研发、测试执行”。**Spec 是上游意图，Handoff 是下游执行协议。**

<callout emoji="⚠️">
**不要混用两个文件的职责**
- Product Spec 管业务目标、用户场景、规则边界、优先级。
- Handoff 管页面语义树、状态流转、接口契约、资源绑定、代码映射、测试依据。
</callout>

| 产物 | 主要回答 | 典型读者 | 变化时谁跟着动 |
|-|-|-|-|
| Product Spec | 为什么做、做什么、业务规则是什么 | AI、产品、业务 | Handoff 需要重新生成或增量更新 |
| Handoff | 页面怎么拆、状态怎么走、接口怎么接、代码怎么落 | AI、产品、设计、研发、测试 | 预览、代码、测试同步消费 |
| Code | 真实产品如何运行 | 研发、测试 | 反向通过 scan/gate 做对齐检查 |

例子：

```Plain Text
Spec 写：用户拍题后，AI 老师用白板一步步讲解，并允许中途追问。

Handoff 写：
- 页面：whiteboard_intro、whiteboard_teaching、class_summary
- 状态：intro、generating、teaching、paused、wait_confirm、summary
- 动作：upload_question、raise_hand、toggle_audio、navigate_back
- 接口：whiteboard_upload_question 返回 SSE command
- 代码映射：whiteboard_teaching 绑定 /blackboard 和 blackboard_screen.dart
```

## Handoff 如何承接技术方案

Handoff 不替代技术方案。技术方案仍然要决定架构、选型、性能、安全、灰度、异常处理。Handoff 负责把会影响多人协作的技术结论固定下来。

<callout emoji="💡">
**Handoff 记录技术方案里会被下游消费的部分**
- 页面和路由：这个页面由哪个 route 承载。
- 组件和文件：这个语义节点落到哪个组件或文件。
- 接口和数据：请求字段、响应字段、事件流、mock 序列。
- 状态和动作：按钮触发什么动作，失败态怎么处理。
- 资源和 token：图标、颜色、字号、间距用哪个语义名。
</callout>

以白板 Demo 为例：

| 技术结论 | Handoff 里怎么表达 |
|-|-|
| 白板讲解走 Flutter `/blackboard` 路由 | `manifest.json` 和 `code-skill-request.json` |
| 题目上传后用 SSE 返回板书指令 | `apis.json` 的 `whiteboard_upload_question` |
| 顶栏、输入栏、板书卡片要复用组件 | `definitions/components.json` |
| 讲解中、暂停、等待确认是页面状态 | `interaction.json` |
| 绿色高亮、圆角、间距要统一 | `tokens/semantics.json` 和 `style.json` |

技术方案决定“怎么实现才可靠”，Handoff 固化“哪些结论必须被下游一致消费”。

## 新增需求和存量Handoff关系

<callout emoji="🤟">
新增需求不是从0重新生成一份新的 Handoff，而是**生长在存量 Handoff 上**。
具体做法是：先从现有 Handoff 里找到它影响的页面、状态、动作、接口和代码映射，然后只在这些位置做增量补充。
</callout>

例：比如白板已经有 `whiteboard_teaching` 页面，新增“讲解中插入随堂测”时，不需要重写整套白板 Handoff，只需要在已有页面里增加：

```Plain Text
一个新状态：quiz_active
一个新组件：随堂测弹层或 QuizSheet
一个新动作：submit_quiz_answer
一段新接口或事件：SSE 推送 quiz 指令
一条测试口径：讲解中收到 quiz 后能展示、提交、回到讲解
```

这样做的好处是，新增需求会继承原来的页面结构、组件、token、接口约定和代码映射。团队不用重新理解整套需求，只要看这次 diff：新增了什么、改了什么、影响哪里。

所以 Handoff 在需求迭代里的角色更像“活的产品实现契约”。它不是一次性文档，而是随着需求变化持续增量生长的协议树。

## Handoff 和代码的关系

代码是最终实现，Handoff 是实现前后的对齐协议。

<callout emoji="✅">
**两种落地模式**
- 存量项目知识构建：Handoff 不重写实现，只把页面、状态和真实 Flutter 文件建立映射。
- 新增项目或需求：AI 读取 Handoff，把页面语义树、状态和接口转成代码草案或测试草案。
</callout>

```Java
{
  "input_handoff": "../handoff",
  "target": {
    "platform": "android",
    "artifact": "../apk/ai-tutor-whiteboard-demo-dev-debug.apk",
    "build_command": "flutter build apk --flavor dev --debug"
  },
  "required_pages": [
    "whiteboard_intro",
    "whiteboard_teaching",
    "dictation_mode",
    "recitation_mode",
    "class_summary",
    "homework_review"
  ]
}
```

| Handoff 页面 | Flutter 路由 | 关键文件 |
|-|-|-|
| `whiteboard_intro` | `/blackboard` | `blackboard_screen.dart`、`blackboard_input_bar.dart`、`blackboard_top_bar.dart` |
| `whiteboard_teaching` | `/blackboard` | `blackboard_screen.dart`、`blackboard_notifier.dart`、`board_webview.dart` |
| `dictation_mode` | `/dictation` | `dictation_screen.dart`、`blackboard_screen.dart` |
| `recitation_mode` | `/recitation` | `recitation_screen.dart`、`blackboard_screen.dart` |

研发拿到 Handoff 后，按固定顺序消费，不再重新猜页面：

- 读 `manifest`：确认页面和路由。
- 读 `pages` 三件套：确认结构、样式、交互。
- 读 `apis`：确认字段和事件流。
- 读 `code-skill` 映射：确认要改哪些文件。
- 编码实现后，运行构建、测试和截图对齐检查。

## 团队怎么使用 Handoff

<blockquote><p><cite doc-id="RFN8wX3V2ibWL4ket5LcXwLtnRb" file-type="wiki" title="【Handoff教程】从产品 Spec 到 H5 Preview 与客户端 APK全链路交付说明" type="doc"></cite></p></blockquote>

### 首次生成需求

自然语言需求 → Product Spec → **Handoff** → **Handoff** **H5 Preview** → 设计/产品确认 → **Code Skill** → 测试验收

下面几张图来自 `whiteboard-handoff-demo` 和项目基线截图。

**H5 Renderer 总览**

左侧选择页面，中间是手机预览，右侧是状态和 code skill 映射。它证明同一份 Handoff 可以被预览器消费。

![图片展示了Handoff H5 Renderer的三个关键部分。左侧是白板Handoff HS Renderer，包含白板入口、白板讲师中、写习模式、背诵模式、课堂总结、作业回、作业回题等信息。中间是AI面书，有AI面书训练、提问模式、背诵模式、课堂总结、作业回题等。右侧是白板入口，有主路径、失败态、中途追问、返回回灌等信息。该图与文档中产品输入需求时需说明的入口、页面、状态、动作和数据来源等内容相关，直观呈现了相关输入项。](https://feishu.cn/file/LwEBbq8txo5E1qx9jqTceiYfnxe)

<grid>
<column width-ratio="0.333333">
![图片展示的是AI板书界面，上方显示“AI板书 内容由AI生成”。中间部分是“AI板书·边讲边写”板块，介绍拍照或输入题目，AI老师会在板书上为你一步一步讲解。下方有两条试一试示例，分别是“试一试：默写《静夜思》，讲一下诗句的意思”和“试一试：一个长方形长9厘米宽4厘米，求周长和面积”。底部有“按住说话”按钮，以及拍照、手写输入和添加图片的图标。该图片与文档中介绍AI板书功能的内容相关，直观呈现了其使用示例。](https://feishu.cn/file/X31lbdgr1oVqbsxijJtcS7q4nqh)
</column>
<column width-ratio="0.333333">
![图片展示的是AI板书界面，上方显示“AI板书”及“内容由AI生成”，下方有“图片”](https://feishu.cn/file/TNsTblJtsoFeN3xdPc2c3j0enIc)
</column>
<column width-ratio="0.333333">
![图片展示的是AI板书界面，上方显示“AI板书 内容由AI生成”。中间是“一个长方形的长是8cm，宽是5cm，求这个长方形...”的题目，下方是“第三步：求面积”的解答，包括面积公式及代入数值计算结果。下方有“这节课学得很扎实，继续保持”等鼓励语，以及课堂总结、知识点回顾、老师点评等内容。底部有“按住说话”按钮等操作选项。该图片与文档中产品输入需求时需说明数据来源的上下文相关，展示了AI板书的示例内容。](https://feishu.cn/file/OhVGbGxNkojFK4xvC7ccODBynWf)
</column>
</grid>

<whiteboard token="QR8JwtOxbh15RqbOKmQcyNG2nnh"></whiteboard>

产品输入需求时，重点说清楚入口、页面、状态、动作和数据来源。

| **拆解对象** | **白板讲题示例** |
|-|-|
| 页面 | `whiteboard_intro`、`whiteboard_teaching`、`class_summary`、`homework_review` |
| 状态 | `intro`、`generating`、`teaching`、`paused`、`summary` |
| 动作 | `upload_question`、`raise_hand`、`toggle_audio`、`enter_homework_review` |
| 数据 | 题目文本、题目图片、SSE command、课堂统计 |
| 验收口径 | 主路径、失败态、中途追问、返回回灌 |

### 开发过程中修改需求

需求变化时，不要只在群里说“顺手改一下”。先改 Handoff，再让下游继续。

| **常见动作** | **什么时候用** | **解决什么问题** |
|-|-|-|
| `/validate` | 交给下游前 | 检查交接物是否达到可交接状态 |
| `/diff` | 需求变更后 | 告诉团队这次改了页面、状态、字段还是接口 |
| `/claim` | 研发开始前 | 锁定谁负责哪块，避免并行撞车 |
| `/complete` | 研发完成后 | 把交接权传给测试或产品 |
| `/status` | 多人并行时 | 看当前谁在做什么、做到哪 |

**变更纪律**

当 Handoff、Demo、实现范围三者没有重新对齐时，不要继续下游开发。否则推进越快，返工越快。

# 示例：白板Handoff完整架构

这份文档只解释 `whiteboard-handoff-demo` 的生成物架构。它不是一份新的规范，也不改动任何代码。

Handoff 的核心是把白板需求存成一棵页面语义树，再把页面语义树和流程、接口、组件、样式、代码映射、预览产物连接起来。

---

## 1. 总体架构

```text
whiteboard-handoff-demo/
├── README.md                                包说明，告诉读者这个 demo 怎么看、怎么构建
├── package-manifest.json                    产物清单，记录这次 demo 输出了哪些文件
├── handoff/                                 Handoff 协议主体，产品、设计、研发、测试主要读取这里
│   ├── manifest.json                        协议入口，声明项目名、版本、页面列表和页面 route
│   ├── flows.json                           跨页面流程，说明从入口到讲解、总结、作业回顾怎么流转
│   ├── apis.json                            数据协议，说明接口路径、请求字段、响应字段和 SSE 事件
│   ├── board_templates.json                 白板模板，说明板书标题、正文、公式、高亮等内容怎么渲染
│   ├── definitions/                         可复用组件定义目录
│   │   └── components.json                  组件库，定义 TopBar、InputBar、BoardCard、DockCard 等组件
│   ├── tokens/                              设计变量目录
│   │   ├── primitives.json                  原始设计值，比如颜色值、字号、间距、圆角
│   │   └── semantics.json                   语义设计值，比如 primary、surface、card radius
│   ├── resources/                           资源注册目录
│   │   └── icon_registry.json               图标白名单，声明页面里允许使用哪些图标名
│   └── pages/                               页面目录，每个页面都有结构、样式、交互三件套
│       ├── whiteboard_intro/                白板入口页，用户进入课堂前看到的首屏
│       │   ├── structure.json               页面有什么：顶部栏、引导区、输入栏、设置面板
│       │   ├── style.json                   页面长什么样：布局、间距、卡片、颜色 token
│       │   └── interaction.json             页面怎么动：intro、generating、error 等状态
│       ├── whiteboard_teaching/             白板讲解中，AI 老师逐步板书讲解的核心页
│       │   ├── structure.json               页面有什么：题目条、白板、字幕、追问、测验、输入栏
│       │   ├── style.json                   页面长什么样：白板区、浮层、输入栏等视觉规则
│       │   └── interaction.json             页面怎么动：讲解、暂停、测验、等待确认、追问等状态
│       ├── dictation_mode/                  听写模式页
│       │   ├── structure.json               页面有什么：听写题、进度、提示、操作按钮
│       │   ├── style.json                   页面长什么样：听写卡片、进度区、按钮样式
│       │   └── interaction.json             页面怎么动：dictating、between_words、completed
│       ├── recitation_mode/                 背诵模式页
│       │   ├── structure.json               页面有什么：课文、录音入口、录音态、批改态
│       │   ├── style.json                   页面长什么样：背诵卡片、录音浮层、输入栏
│       │   └── interaction.json             页面怎么动：ready、recording、reviewing
│       ├── class_summary/                   课堂总结页
│       │   ├── structure.json               页面有什么：课堂统计、知识点回顾、老师点评、追问入口
│       │   ├── style.json                   页面长什么样：总结卡片、统计区、点评区
│       │   └── interaction.json             页面怎么动：summary、replaying、returning
│       └── homework_review/                 作业回顾页
│           ├── structure.json               页面有什么：总结回顾、上传作业、图片预览、批改入口
│           ├── style.json                   页面长什么样：作业上传浮层、图片预览卡片
│           └── interaction.json             页面怎么动：post_class、upload_prepare、image_preview、sending_review
├── h5/                                      H5 预览层，用来证明 Handoff 可以被浏览器读取并展示
│   └── index.html                          静态预览器，左侧页面列表、中间手机预览、右侧状态和代码映射
├── code-skill/                              代码映射层，用来把 Handoff 绑定到真实 Flutter 工程
│   ├── code-skill-request.json             code skill 输入，声明目标平台、构建命令、必需页面
│   ├── handoff-to-code-map.json            页面到 Flutter route / 文件的映射表
│   ├── validate_code_skill_request.mjs      校验脚本，检查页面三件套和 Flutter 文件是否存在
│   └── build_android_apk.sh                 构建脚本，校验通过后执行 Flutter APK 构建
└── apk/                                     Android 演示产物目录
    └── ai-tutor-whiteboard-demo-dev-debug.apk  已构建的白板 demo APK
```

这一套产物可以分成四层：

| 层级 | 文件 | 作用 |
|-|-|-|
| 协议层 | `handoff/*` | 保存页面、流程、接口、组件、样式、资源和状态机 |
| 预览层 | `h5/index.html` | 读取 Handoff JSON，渲染出可看的 H5 Demo |
| 代码映射层 | `code-skill/*` | 把 Handoff 页面绑定到 Flutter route 和文件 |
| 演示产物层 | `apk/*` | 已构建的 Android 演示包 |

---

## 2. Handoff 的主入口

`handoff/manifest.json` 是白板 Handoff 的目录入口。它告诉下游：这个包叫什么、版本是什么、有哪些页面、每个页面对应什么业务路由。

当前 demo 里有 6 个页面：

| 页面 ID | 页面名 | Handoff route | 说明 |
|-|-|-|-|
| `whiteboard_intro` | 白板入口 | `/whiteboard/intro` | 用户进入白板课堂前看到的首屏 |
| `whiteboard_teaching` | 白板讲解中 | `/whiteboard/teaching` | AI 老师逐步板书讲解的主状态 |
| `dictation_mode` | 听写模式 | `/dictation` | 词句听写课堂 |
| `recitation_mode` | 背诵模式 | `/recitation` | 课文背诵课堂 |
| `class_summary` | 课堂总结 | `/whiteboard/class_summary` | 课堂结束后的总结页 |
| `homework_review` | 作业回顾 | `/whiteboard/homework_review` | 课堂后继续拍作业、追问和批改 |

#### 代码示例：handoff/manifest.json

```json
{
  "schema_version": "0.1.3",
  "name": "AI Tutor 白板专项 Handoff",
  "version": "0.1.3-sim",
  "pages": [
    {
      "id": "whiteboard_intro",
      "name": "白板入口",
      "route": "/whiteboard/intro",
      "readiness": "ready"
    },
    {
      "id": "homework_review",
      "name": "作业回顾",
      "route": "/whiteboard/homework_review",
      "render_scope": "in_session_state",
      "consumes_flutter_route": "/blackboard"
    }
  ]
}
```

---

## 3. 页面语义树是什么

页面语义树就是把页面拆成稳定的业务节点。每个节点都说明自己是什么、展示什么、什么时候出现、触发什么动作。

下面是白板页面的简化结构：

```text
page
└── scaffold              页面整体骨架，决定这一页由哪些区域组成
    ├── top_bar           顶部导航区，比如返回、标题、设置、语音开关
    ├── query_bar         题目信息区，比如当前讲解的题目或用户输入
    ├── board_canvas      白板讲解区，承载 AI 板书、步骤推导和重点标注
    ├── summary_card      总结卡片区，展示课堂总结、知识点回顾或老师点评
    └── input_bar         底部输入区，支持拍照、输入、语音、追问等操作
```

真实文件里，每个页面都拆成三件套：

| 文件 | 回答的问题 | 产品/研发怎么看 |
|-|-|-|
| `structure.json` | 页面有什么 | 页面节点、文案、组件引用、数据绑定 |
| `style.json` | 页面长什么样 | 布局、间距、颜色、圆角、token 使用 |
| `interaction.json` | 页面怎么动 | 状态机、动作、事件、接口调用 |

---

## 4. 页面完整结构

### 4.1 白板入口：whiteboard_intro

白板入口是用户进入课堂前的首屏。它承载示例题、输入栏、拍照/相册入口和生成中状态。

```text
whiteboard_intro
└── wi_root_1000 scaffold
    ├── wi_topbar_1100        definitions.TopBar
    ├── wi_scroll_1200        scrollable
    ├── wi_inputbar_1300      definitions.InputBar，正常输入态
    ├── wi_inputbar_1301      definitions.InputBar，生成中禁用态
    └── wi_settings_1400      definitions.SettingsPanel
```

状态机：

```text
intro -> guidance_hidden -> generating -> whiteboard_teaching
                    └────-> error
```

#### 代码示例：pages/whiteboard_intro/structure.json

```json
{
  "page_id": "whiteboard_intro",
  "name": "白板入口",
  "route": "/whiteboard/intro",
  "root": {
    "id": "wi_root_1000",
    "type": "scaffold",
    "children": [
      {
        "id": "wi_topbar_1100",
        "$ref": "definitions.TopBar",
        "props": {
          "title": "{topic_name}",
          "show_audio_btn": false,
          "show_speed_btn": false
        }
      },
      {
        "id": "wi_inputbar_1300",
        "$ref": "definitions.InputBar",
        "visibility": {
          "condition": "$state:current != 'generating' && !is_generating"
        }
      }
    ]
  }
}
```

#### 代码示例：pages/whiteboard_intro/style.json

```json
{
  "$schema": "handoff/page-style@1.0",
  "page_id": "whiteboard_intro",
  "nodes": {
    "wi_root_1000": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "cross_axis": "stretch"
      }
    },
    "wi_onboarding_1210": {
      "padding": { "all": "$token:spacing.lg" },
      "background_color": "$token:color.surface",
      "border_radius": "$token:radius.card"
    }
  }
}
```

#### 代码示例：pages/whiteboard_intro/interaction.json

```json
{
  "$schema": "handoff/page-interaction@1.0",
  "page_id": "whiteboard_intro",
  "state_machine": {
    "initial": "intro",
    "states": {
      "intro": {
        "transitions": {
          "question_submit": { "target": "generating" }
        }
      },
      "generating": {
        "transitions": {
          "sse_first_command": {
            "target": null,
            "action": {
              "type": "navigate",
              "route": "/whiteboard/teaching"
            }
          }
        }
      }
    }
  }
}
```

### 4.2 白板讲解中：whiteboard_teaching

白板讲解中是核心课堂页。它包含板书、字幕、随堂测、等待确认、举手追问、上传作业、总结嵌入和设置面板。

```text
whiteboard_teaching
└── wt_root_a0f1 scaffold
    ├── wt_topbar_b1e2            definitions.TopBar
    ├── wt_querybar_c2d3          definitions.QueryBar
    ├── wt_scroll_d3e4            scrollable
    ├── wt_quiz_dock_qa10         definitions.DockCard
    ├── wt_wait_dock_wa10         definitions.DockCard
    ├── wt_wait_inputbar_wa20     definitions.InputBar
    ├── wt_followup_dock_fu10     definitions.DockCard
    ├── wt_upload_dock_up10       definitions.DockCard
    ├── wt_summary_dock_sm10      definitions.DockCard
    ├── wt_subtitle_c8d9          definitions.SubtitleBar
    ├── wt_inputbar_d9e0          definitions.InputBar
    └── wt_settings_panel_sp10    definitions.SettingsPanel
```

状态机：

```text
teaching
├── paused
├── quiz_active
├── wait_confirm
├── followup_streaming
├── upload_homework_prepare
└── summary_inline
```

#### 代码示例：pages/whiteboard_teaching/structure.json

```json
{
  "page_id": "whiteboard_teaching",
  "name": "白板讲解中",
  "root": {
    "id": "wt_root_a0f1",
    "type": "scaffold",
    "children": [
      { "id": "wt_topbar_b1e2", "$ref": "definitions.TopBar" },
      { "id": "wt_querybar_c2d3", "$ref": "definitions.QueryBar" },
      { "id": "wt_scroll_d3e4", "type": "scrollable" },
      {
        "id": "wt_quiz_dock_qa10",
        "$ref": "definitions.DockCard",
        "visibility": {
          "condition": "$state:current == 'quiz_active'"
        }
      }
    ]
  }
}
```

#### 代码示例：pages/whiteboard_teaching/style.json

```json
{
  "$schema": "handoff/page-style@1.0",
  "page_id": "whiteboard_teaching",
  "nodes": {
    "wt_root_a0f1": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "cross_axis": "stretch"
      }
    },
    "wt_scroll_d3e4": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "gap": "$token:spacing.md"
      }
    }
  }
}
```

#### 代码示例：pages/whiteboard_teaching/interaction.json

```json
{
  "page_id": "whiteboard_teaching",
  "state_machine": {
    "initial": "teaching",
    "states": {
      "teaching": {
        "transitions": {
          "pause": { "target": "paused" },
          "quiz": { "target": "quiz_active" },
          "wait": { "target": "wait_confirm" }
        }
      }
    }
  },
  "actions": {
    "raise_hand": {
      "steps": [
        { "type": "emit", "event": "wait" }
      ]
    }
  }
}
```

### 4.3 听写模式：dictation_mode

听写模式用于词句听写，重点是当前题、进度、重复播放、完成总结。

```text
dictation_mode
└── dm_root_2000 scaffold
    ├── dm_topbar_2100      definitions.TopBar
    ├── dm_querybar_2200    definitions.QueryBar
    └── dm_content_2300     scrollable
```

状态机：

```text
dictating -> between_words -> completed
```

#### 代码示例：pages/dictation_mode/structure.json

```json
{
  "page_id": "dictation_mode",
  "name": "听写模式",
  "route": "/dictation",
  "root": {
    "id": "dm_root_2000",
    "type": "scaffold",
    "children": [
      { "id": "dm_topbar_2100", "$ref": "definitions.TopBar" },
      { "id": "dm_querybar_2200", "$ref": "definitions.QueryBar" },
      {
        "id": "dm_content_2300",
        "type": "scrollable",
        "semantic_role": "scroll_container"
      }
    ]
  }
}
```

#### 代码示例：pages/dictation_mode/style.json

```json
{
  "page_id": "dictation_mode",
  "nodes": {
    "dm_content_2300": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "cross_axis": "stretch",
        "gap": "$token:spacing.md"
      }
    }
  }
}
```

#### 代码示例：pages/dictation_mode/interaction.json

```json
{
  "page_id": "dictation_mode",
  "state_machine": {
    "initial": "dictating",
    "states": {
      "dictating": {
        "transitions": {
          "word_done": { "target": "between_words" },
          "all_done": { "target": "completed" }
        }
      }
    }
  },
  "actions": {
    "repeat_current": {
      "steps": [
        { "type": "platform_capability", "capability": "tts_replay" }
      ]
    }
  }
}
```

### 4.4 背诵模式：recitation_mode

背诵模式用于课文背诵，重点是准备态、录音态、批改态。

```text
recitation_mode
└── rm_root_3000 scaffold
    ├── rm_topbar_3100             definitions.TopBar
    ├── rm_querybar_3200           definitions.QueryBar
    ├── rm_content_3300            scrollable
    ├── rm_ready_dock_3400         definitions.DockCard
    ├── rm_ready_inputbar_3500     definitions.InputBar
    ├── rm_recording_dock_3410     definitions.DockCard
    └── rm_recording_inputbar_3510 definitions.InputBar
```

状态机：

```text
ready -> recording -> reviewing
```

#### 代码示例：pages/recitation_mode/structure.json

```json
{
  "page_id": "recitation_mode",
  "root": {
    "id": "rm_root_3000",
    "type": "scaffold",
    "children": [
      { "id": "rm_topbar_3100", "$ref": "definitions.TopBar" },
      { "id": "rm_querybar_3200", "$ref": "definitions.QueryBar" },
      { "id": "rm_content_3300", "type": "scrollable" },
      {
        "id": "rm_ready_inputbar_3500",
        "$ref": "definitions.InputBar",
        "props": {
          "mode": "slide_to_record",
          "complete_action": "start_recording"
        }
      }
    ]
  }
}
```

#### 代码示例：pages/recitation_mode/style.json

```json
{
  "page_id": "recitation_mode",
  "nodes": {
    "rm_ready_dock_3400": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "gap": "$token:spacing.sm"
      }
    }
  }
}
```

#### 代码示例：pages/recitation_mode/interaction.json

```json
{
  "page_id": "recitation_mode",
  "state_machine": {
    "initial": "ready",
    "states": {
      "ready": {
        "transitions": {
          "start_recording": { "target": "recording" }
        }
      },
      "recording": {
        "transitions": {
          "stop_recording": { "target": "reviewing" }
        }
      }
    }
  }
}
```

### 4.5 课堂总结：class_summary

课堂总结用于展示讲解结束后的结果：课堂时长、互动次数、随堂测结果、知识点回顾和老师点评。

```text
class_summary
└── cs_root_4000 scaffold
    ├── cs_topbar_4100      definitions.TopBar
    ├── cs_querybar_4200    definitions.QueryBar
    ├── cs_content_4300     scrollable
    └── cs_inputbar_4500    definitions.InputBar
```

状态机：

```text
summary -> replaying -> returning
```

#### 代码示例：pages/class_summary/structure.json

```json
{
  "page_id": "class_summary",
  "name": "课堂总结",
  "root": {
    "id": "cs_root_4000",
    "type": "scaffold",
    "children": [
      { "id": "cs_topbar_4100", "$ref": "definitions.TopBar" },
      { "id": "cs_querybar_4200", "$ref": "definitions.QueryBar" },
      {
        "id": "cs_content_4300",
        "type": "scrollable",
        "semantic_role": "scroll_container"
      },
      { "id": "cs_inputbar_4500", "$ref": "definitions.InputBar" }
    ]
  }
}
```

#### 代码示例：pages/class_summary/style.json

```json
{
  "page_id": "class_summary",
  "nodes": {
    "cs_summary_card": {
      "layout": {
        "type": "flex",
        "direction": "column",
        "gap": "$token:spacing.md"
      },
      "background_color": "$token:color.surface",
      "border_radius": "$token:radius.card"
    }
  }
}
```

#### 代码示例：pages/class_summary/interaction.json

```json
{
  "page_id": "class_summary",
  "state_machine": {
    "initial": "summary",
    "states": {
      "summary": {
        "transitions": {
          "replay": { "target": "replaying" },
          "sync_result": { "target": "returning" }
        }
      }
    }
  },
  "actions": {
    "go_homework_review": {
      "steps": [
        { "type": "navigate", "route": "/whiteboard/homework_review" }
      ]
    }
  }
}
```

### 4.6 作业回顾：homework_review

作业回顾用于课堂后的继续互动：上传作业图片、补充说明、发送批改、回到课堂总结。

```text
homework_review
└── hr_root_5000 scaffold
    ├── hr_topbar_5100         definitions.TopBar
    ├── hr_querybar_5200       definitions.QueryBar
    ├── hr_content_5300        scrollable
    ├── hr_upload_dock_5400    definitions.DockCard
    ├── hr_inputbar_post_5500  definitions.InputBar
    └── hr_inputbar_image_5510 definitions.InputBar
```

状态机：

```text
post_class -> upload_prepare -> image_preview -> sending_review
```

#### 代码示例：pages/homework_review/structure.json

```json
{
  "page_id": "homework_review",
  "name": "作业回顾",
  "root": {
    "id": "hr_root_5000",
    "type": "scaffold",
    "children": [
      { "id": "hr_topbar_5100", "$ref": "definitions.TopBar" },
      { "id": "hr_querybar_5200", "$ref": "definitions.QueryBar" },
      {
        "id": "hr_upload_dock_5400",
        "$ref": "definitions.DockCard",
        "visibility": {
          "condition": "$state:current == 'upload_prepare'"
        }
      }
    ]
  }
}
```

#### 代码示例：pages/homework_review/style.json

```json
{
  "page_id": "homework_review",
  "nodes": {
    "hr_preview_5330": {
      "padding": { "all": "$token:spacing.lg" },
      "background_color": "$token:color.surface",
      "border_radius": "$token:radius.card"
    }
  }
}
```

#### 代码示例：pages/homework_review/interaction.json

```json
{
  "page_id": "homework_review",
  "state_machine": {
    "initial": "post_class",
    "states": {
      "post_class": {
        "transitions": {
          "open_upload_dock": { "target": "upload_prepare" },
          "image_selected": { "target": "image_preview" }
        }
      },
      "image_preview": {
        "transitions": {
          "send": { "target": "sending_review" }
        }
      }
    }
  }
}
```

---

## 5. 跨页面流程

`handoff/flows.json` 记录页面之间怎么跳。它不是某个单页内部的状态机，而是整个白板课堂的用户旅程。

```text
$external
  └── whiteboard_intro
      ├── whiteboard_teaching   讲题模式
      ├── dictation_mode        听写模式
      └── recitation_mode       背诵模式

whiteboard_teaching
  └── class_summary
      └── homework_review
          └── $back
```

#### 代码示例：handoff/flows.json

```json
{
  "navigation": {
    "transitions": [
      {
        "id": "flow_entry",
        "from": "$external",
        "to": "whiteboard_intro",
        "trigger": "tool_call_whiteboard"
      },
      {
        "id": "flow_intro_to_teaching",
        "from": "whiteboard_intro",
        "to": "whiteboard_teaching",
        "trigger": "generation_complete",
        "guard": {
          "$expr": "$global:class_type == 'explain'"
        }
      }
    ]
  }
}
```

---

## 6. 数据协议

`handoff/apis.json` 记录接口契约。它把页面动作和后端数据连接起来。

当前 demo 的接口包括：

| API | 作用 |
|-|-|
| `whiteboard_upload_question` | 上传题目，创建白板课堂，返回 SSE 板书流 |
| `whiteboard_wait_followup` | 等待确认或举手追问后的继续讲解 |
| `tts_stream` | 文本转语音播放 |
| `voice_recognize` | 语音识别 |
| `submit_recitation` | 提交背诵结果 |
| `session_analytics` | 课堂统计 |

#### 代码示例：handoff/apis.json

```json
{
  "whiteboard_upload_question": {
    "method": "POST",
    "path": "/api/edu-agentscope/question/upload",
    "description": "发起讲题/听写/背书课堂",
    "request": {
      "content_type": "application/json",
      "body": {
        "question": {
          "type": "string",
          "required": true
        },
        "mode": {
          "type": "string",
          "required": true,
          "enum": ["explain", "dictate", "recite"]
        }
      }
    }
  }
}
```

---

## 7. 白板模板

`handoff/board_templates.json` 记录白板 canvas 内部怎么渲染。SSE 返回的板书指令会按模板类型展示，比如步骤标题、步骤正文、公式、高亮、测验反馈。

#### 代码示例：handoff/board_templates.json

```json
{
  "templates": {
    "step_title": {
      "description": "板书步骤标题，如「第一步 · 审题」",
      "semantic_role": "heading",
      "content_schema": {
        "type": "object",
        "properties": {
          "text": {
            "type": "string",
            "required": true
          }
        }
      },
      "typography": "$token:typography.section_title",
      "text_color": "$token:color.on_background"
    }
  }
}
```

---

## 8. 组件定义

`handoff/definitions/components.json` 是组件库。页面里的节点可以用 `$ref` 复用这些组件，不需要每一页重复写一遍。

当前 demo 里有 36 个组件定义，白板核心组件包括：

| 组件 | 作用 |
|-|-|
| `TopBar` | 顶部导航栏 |
| `StatusBar` | 手机状态栏 |
| `InputBar` | 底部输入栏 |
| `SubtitleBar` | 讲解字幕 |
| `QueryBar` | 题目条 |
| `BoardCard` | 白板内容卡片 |
| `DockCard` | 底部浮层卡片 |
| `QuizSheet` | 随堂测 |
| `ContinueConfirmSheet` | 等待确认 |
| `SettingsPanel` | 设置面板 |

#### 代码示例：handoff/definitions/components.json

```json
{
  "TopBar": {
    "semantic_role": "nav_bar",
    "description": "白板顶栏",
    "dev_bridge": {
      "flutter_widget": "BlackboardTopBar",
      "file": "features/blackboard/widgets/blackboard_top_bar.dart",
      "status": "mapped"
    },
    "params": {
      "title": {
        "type": "string",
        "required": true
      },
      "show_audio_btn": {
        "type": "boolean",
        "default": true
      }
    }
  }
}
```

---

## 9. 设计 Token

Token 是设计变量。它把“绿色”“圆角”“间距”这类视觉值变成稳定名字，避免每个页面手写不同数字。

### 9.1 primitives.json

`primitives.json` 保存最底层的原始值，比如颜色值、字号、圆角、阴影。

#### 代码示例：handoff/tokens/primitives.json

```json
{
  "colors": {
    "brand_500": "#00D1B2",
    "gray_900": "#1A1A2E",
    "white": "#FFFFFF"
  },
  "spacing": {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16
  },
  "radii": {
    "md": 8,
    "lg": 12,
    "xl": 16
  }
}
```

### 9.2 semantics.json

`semantics.json` 把原始值变成业务语义名。页面不直接关心 `#00D1B2`，只关心 `$token:color.primary`。

#### 代码示例：handoff/tokens/semantics.json

```json
{
  "color": {
    "primary": "$primitive:colors.brand_500",
    "background": "$primitive:colors.white",
    "surface": "$primitive:colors.gray_50",
    "on_background": "$primitive:colors.gray_900"
  },
  "spacing": {
    "sm": "$primitive:spacing.sm",
    "md": "$primitive:spacing.md",
    "lg": "$primitive:spacing.lg"
  }
}
```

---

## 10. 资源注册

`handoff/resources/icon_registry.json` 是图标白名单。Handoff 里出现的图标名应该先在这里登记，预览器和代码才能稳定消费。

#### 代码示例：handoff/resources/icon_registry.json

```json
{
  "schema_version": "handoff.icon_registry@0.1.0",
  "policy": "Preview may render icons with its own adapter, but icon names and allowed semantics must be declared by Handoff.",
  "icons": {
    "arrow_left": {
      "semantic": "back_navigation",
      "source": "definitions.TopBar"
    },
    "camera": {
      "semantic": "camera_picker",
      "source": "definitions.InputBar"
    }
  }
}
```

---

## 11. H5 预览器

`h5/index.html` 是一个静态 H5 预览器。它直接内嵌并读取 Handoff JSON，左侧切页面，中间显示手机预览，右侧显示状态和 code skill 映射。

它证明这份 Handoff 能被浏览器读取和渲染。

#### 代码示例：h5/index.html

```html
<script>
  const HANDOFF = { "manifest": { "name": "AI Tutor 白板专项 Handoff" } };
  const pageIds = ["whiteboard_intro", "whiteboard_teaching"];
  let currentPage = pageIds[0];

  function render() {
    const page = HANDOFF.pages[currentPage];
    const structure = page.structure;
    app.innerHTML =
      '<main class="app">' +
      '<aside class="panel">页面列表</aside>' +
      '<section class="phone-shell">' + renderNode(structure.root) + '</section>' +
      '<aside class="panel">状态和 code skill 映射</aside>' +
      '</main>';
  }
</script>
```

---

## 12. Code Skill 映射

code-skill 层负责告诉代码工具：Handoff 里的页面对应哪个 Flutter route、哪些 Flutter 文件、构建目标是什么。

### 12.1 code-skill-request.json

这个文件是 code skill 的输入。它说明 Handoff 在哪里，目标平台是什么，需要消费哪些页面，最终 APK 放在哪里。

#### 代码示例：code-skill/code-skill-request.json

```json
{
  "schema_version": "code-skill-request@1.0",
  "input_handoff": "../handoff",
  "target": {
    "platform": "android",
    "artifact": "../apk/ai-tutor-whiteboard-demo-dev-debug.apk",
    "build_command": "flutter build apk --flavor dev --debug"
  },
  "required_pages": [
    "whiteboard_intro",
    "whiteboard_teaching",
    "dictation_mode",
    "recitation_mode",
    "class_summary",
    "homework_review"
  ]
}
```

### 12.2 handoff-to-code-map.json

这个文件是页面到代码的映射表。它不描述界面长什么样，只描述 Handoff 页面应该落到哪些 Flutter 文件。

#### 代码示例：code-skill/handoff-to-code-map.json

```json
{
  "code_bindings": [
    {
      "page_id": "whiteboard_teaching",
      "flutter_route": "/blackboard",
      "flutter_files": [
        "client/lib/features/blackboard/screens/blackboard_screen.dart",
        "client/lib/features/blackboard/providers/blackboard_notifier.dart",
        "client/lib/features/blackboard/widgets/board_webview.dart"
      ],
      "status": "implemented_code_route"
    }
  ]
}
```

### 12.3 validate_code_skill_request.mjs

这个脚本检查 code skill 输入是否完整：页面三件套是否存在，映射到的 Flutter 文件是否存在。

#### 代码示例：code-skill/validate_code_skill_request.mjs

```js
for (const pageId of request.required_pages) {
  for (const name of ['structure.json', 'style.json', 'interaction.json']) {
    const file = path.join(handoffRoot, 'pages', pageId, name);
    if (!fs.existsSync(file)) missing.push(file);
  }
}

for (const binding of request.code_bindings) {
  for (const file of binding.flutter_files) {
    const abs = path.join(workspaceRoot, 'flutter-client-simulation', file);
    if (!fs.existsSync(abs)) missing.push(abs);
  }
}
```

### 12.4 build_android_apk.sh

这个脚本先校验 code skill 输入，再进入 Flutter 工程构建 APK，最后把 APK 复制到 demo 包。

#### 代码示例：code-skill/build_android_apk.sh

```bash
#!/usr/bin/env bash
set -euo pipefail

node "$SCRIPT_DIR/validate_code_skill_request.mjs" "$REQUEST" "$WORKSPACE_ROOT"

cd "$CLIENT_ROOT"
flutter build apk --flavor dev --debug

mkdir -p "$(dirname "$APK_DST")"
cp "$APK_SRC" "$APK_DST"
```

---

## 13. APK 演示包

`apk/ai-tutor-whiteboard-demo-dev-debug.apk` 是构建后的 Android 演示包。

这里要注意：APK 不是运行时动态解释 Handoff JSON。它运行的是已有 Flutter 白板实现。Handoff 的作用是约束和对齐页面、状态、交互、资源和代码映射。

#### 代码示例：package-manifest.json 里的 APK 输出声明

```json
{
  "status": "whiteboard_handoff_demo_ready",
  "outputs": [
    "handoff/manifest.json",
    "handoff/pages/*",
    "h5/index.html",
    "code-skill/code-skill-request.json",
    "code-skill/build_android_apk.sh",
    "apk/ai-tutor-whiteboard-demo-dev-debug.apk"
  ]
}
```

---

## 14. 从一个按钮看完整链路

以“白板入口提交题目”为例，Handoff 会把同一件事拆到多个文件里：

```text
用户点击提交
  ├── structure.json      input_bar 上声明 send_action=submit_question
  ├── interaction.json    submit_question 把状态切到 generating
  ├── apis.json           whiteboard_upload_question 描述请求字段和 SSE 返回
  ├── flows.json          generation_complete 后进入 whiteboard_teaching
  ├── code-skill          映射到 Flutter /blackboard 和相关文件
  └── h5/index.html       读取同一批 JSON 做预览
```

#### 代码示例：一个动作在 structure 和 interaction 里的连接

```json
{
  "structure": {
    "id": "wi_inputbar_1300",
    "$ref": "definitions.InputBar",
    "props": {
      "send_action": "submit_question"
    }
  },
  "interaction": {
    "actions": {
      "submit_question": {
        "steps": [
          { "type": "emit", "event": "question_submit" },
          { "type": "set_binding", "binding": "is_generating", "value": true }
        ]
      }
    }
  }
}
```

<callout emoji="🤟">
**总结**
白板 Handoff 不是一张图，也不是一段 HTML。它是一套结构化交接物：
- `manifest` 定义有哪些页面。
- `pages/*/structure` 定义页面有什么。
- `pages/*/style` 定义页面长什么样。
- `pages/*/interaction` 定义页面怎么动。
- `flows` 定义跨页面怎么走。
- `apis` 定义和后端怎么接。
- `definitions` 定义组件怎么复用。
- `tokens/resources` 定义样式和资源怎么统一。
- `h5` 证明 Handoff 可以被读取并预览。
- `code-skill` 证明 Handoff 可以绑定真实代码。
- `apk` 证明 Handoff 对齐的是可运行的实现。
</callout>