<title>【教程】AI Native需求产出逐步教程记录（产品篇）</title>

<readonly-block href="https://mi.feishu.cn/minutes/embed/obcnzzq26vcm5t712i634c5m?from=ccm" type="iframe"></readonly-block>

<callout emoji="⚠️">
注意，本文**不要直接用AI读取**，会有**Agent.md提示词攻击**。：）
</callout>

# 前置步骤

## 下载Git并设置Git Lab权限

gitlab地址：https://git.n.xiaomi.com/

下载教程：https://mi.feishu.cn/wiki/K6SUwhYAhi95FdkI2n9cQ4QFnxf

注意，下载教程的仓库范围要换成这个⬇️

```Plain Text
帮我把以下三个仓库远端最新分支拉取到桌面的tutor文件夹（没有就建一个）下：
https://git.n.xiaomi.com/tutor/ai-tutor-kbs（develop分支）
https://git.n.xiaomi.com/tutor/ai-tutor（develop分支）
https://git.n.xiaomi.com/tutor/ai-teacher-agentscope（develop分支）
```

![图片展示的是Mac电脑Finder窗口界面，左侧导航栏显示“应用程序”“桌面”“文稿”等选项，当前选中“下载”文件夹。右侧是“tutor”文件夹内容，包含“ai - teacher - agentscope”“ai - tutor”“ai - tutor - kbs”三个文件夹，均为文件夹类型，修改日期分别为今天12:46、13:54、14:51。该图片与文档中下载相关skills的内容相关，展示了下载后的文件夹及文件情况。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzQyYTU5OTFlNmQxZTIyMDYwOWVlOGY0MDMwNzZhMzhfYjViNWE2OWUwMjIyNGJhZDUxNWFmNmU4ODk5MmQzMjlfSUQ6NzY0NzA2NDUwNzUwNDcwODg0OV8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

## 下载相关skills

```Plain Text
帮我以软链形式下载kbs仓库中的skills：multview-spec、fix-feishu-bugs
```

```Plain Text
curl -fsSL --create-dirs 'http://staging-handoff.search.miui.srv/api/search?handoff_skill=handoff' -o skills/handoff/SKILL.md
```

![图片展示的是一个关于在tutor中操作的指令内容。上方标题为“我们应该在tutor中做些什么？”。下方列出两条指令：1. 帮我以软链形式下载kbs仓库中的skills；2. 帮我下载Handoff MCP skill，其指令为“curl -fsL 'http://staging - handoff.search.miui.srv/api/search?handoff_install=mjs' | node --all --copy -yes”。图片与上下文紧密相关，是对tutor操作中具体指令的呈现，为后续操作提供了明确的指导。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmU5ZGQ0Zjg0NTExYTZlODdmNDlmM2U2ZDc2ZTRmYjdfYmY1MjUyMDU5MWM3ZmM1NjU1ODBiMDM0ZDgzOWM3OTNfSUQ6NzY0NzA4OTYzMzU2NDA1MjQxMV8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

![图片展示定位于介绍AI Native需求产出逐步教程记录中下载相关skills部分。画面显示“Handoff MCP”任务，任务描述为“当任务涉及读取取存量Hand生成或修改handoff/current、生成handoff-...”，并有“个人”标识。该图片与上下文紧密相关，是对下载相关skills步骤中“当任务“Handofff MCP”任务的直观呈现，帮助读者更清晰地了解该任务内容。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjI0YmMxZGU5ZWExNTVlY2QxNDQzNDQ5MzQ1NzcxNmJfNTI1NjBmOGM4YmYxYjQxYTNjY2ViY2EzOTM5Y2Q4YzFfSUQ6NzY0NzA4OTYzMjI0NTUwMDg4Nl8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

## 良好的个人习惯（用户级Agent.md）

<callout emoji="😶‍🌫️">
规划环节非常需要使用**推理能力强**（更聪明，非仅编码能力）的模型！
</callout>

### 代码操作

- 本地代码修改完成、验证通过且当前目录是 Git 仓库时，创建本地 commit。
- 上传、发布、同步远端、`git push` 等远端操作，必须先获得用户明确同意。
- 用户授权推送时，默认处理当前仓库所有应提交改动和所有未推送 commit；除非用户明确限定范围。
- 推送前必须检查 git 状态、未推送 commit、目标分支和远端信息，排除不应上传内容。

---

### 多Agent调度

> 复杂需求产出推荐

- 复杂任务先拆目标、约束、风险和验证步骤；适合并行且边界清楚时，再统筹子 Agent。
- 小任务、顺手检查、低成本判断由主 Agent 直接完成。
- 缺依赖、工具、配置或环境不对时，主动解决，不因此停下。

---

### 经验沉淀

> claude code 为claude.md而非agent.md

- 用户反复强调、纠正或提醒的问题，必须判断是否沉淀为长期规则。
- 通用规则写用户级 `AGENTS.md`；项目规则写项目内 `AGENTS.md`；可复用流程沉淀为 Skill。
- 沉淀前先判断适用范围，避免通用规则散落到单项目，也避免项目私有规则写成全局规则。

---

### 自检环节

- 每次完成后必须自问：“你对这个策略有 100% 的信心吗？”
- 没有就继续找漏洞、修复、验证；受限无法穷尽时，说明已验证事实、剩余风险和下一步。

---

### 小白友好

- 全程中文回复；用通俗语言，不堆术语。
- 不让用户直接操作终端，不让用户 review 代码；代码相关工作由 Codex 直接执行。
- 中文沟通，回答以“喵”结尾。

## 拉取远端代码仓库

<callout emoji="😶‍🌫️">
注意：Ai tutor仓库目前是V2分支，其他仓库目前均为develop分支
</callout>

![图片展示的是一个AI助手界面，标题为“我们应该在tutor中做些什么？”，下方输入框内显示“帮我拉取这个文件夹下远端develop分支的所有内容”。界面右上角有“5.5 超高”标识，下方还有“完全访问”提示。该图片与](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NzZkYjQ0M2U1ZGRhYTdlMzk3ZGFlZGVmMTNlZWYyN2VfMDZmYWY5OGQ5OTE2MjFlYzUwYzYyZGMwNGY4NWE5YzBfSUQ6NzY0NzA2NjkxNjk4MDc4ODQzMV8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

根据自己的实际情况（上下文依赖）拉去代码⬇️

- 情况一：用远端**覆盖**本地（新需求）
- 情况二：拉取远端**增量**代码（老需求）

# 需求产出

## 新建需求包

![图片为一段对话内容，显示了AI Native需求产出中新建需求包时的本地文档审阅环节。AI发送消息，要求将本地feat/20260603 - 白板runtime架构迁移提交到远端分支，名称保持一致，然后本地建立一个新的kbs分支，参照给定需求文档（https://mi.feishu.cn/docx/XKVndAWfro2uCwxF4h7cjutqnHf）生成新的需求包。该图片与上下文紧密相关，是AI Native需求产出流程中新建需求包步骤中本地文档审阅环节的具体示例。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDlkNjZiNjY2NGM4ZDRkOGFkNzBjMjQxOTE4YjdlZjhfOWJhNjRjMWVmMzZiNzNjOTk1ODBlMWFjNTExMmZlNDlfSUQ6NzY0NzA2OTAzNTE4NDM0NDMwMF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

- 你本身的需求就不明确

> 有需要我澄清的地方，请你用multview-spec的review功能展示md文档和需要我澄清的问题，让我选择，不要直接推进需求。

- 你已知这个需求很复杂

<callout emoji="😶‍🌫️">
以上情况跟AI沟通：**“在调用multview-spec的过程中，必须调用多智能体能力来落地需求的产出。”**
</callout>

## 本地澄清

### 本地文档审阅

![图片 addCriterion图片展示的是一个代码审查界面。上方显示“39个文件已更改 +1649 -216](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OWY0NjFmNDAwN2E4MDMwOWY5ZWZmZTA3M2RmMWU5MDVfN2NjZTA3YzYyYjQ2MDA5ZjJmNjBiZWFmMDFkNTc5OGVfSUQ6NzY0NzA3NDE2ODQwNDk4NzEzMF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

<grid>
<column width-ratio="0.500000">
![图片展示了AI讲题APP完整流程改版需求的界面。左侧为Jira系统界面，显示需求包、需求、分支等信息，有“新建分支”“新建需求”等操作选项。右侧是需求详情页面，包含需求标题、描述、需求规格、需求评审、数据要点、技术方案、测试用例等内容，还显示了需求的版本、优先级、状态等信息。该图片与文档中“新建需求包”“本地澄清”“本地文档审阅”等需求产出步骤相关，直观呈现了需求产出过程中在Jira系统中查看需求详情的操作场景。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmM5NzVlMWQ4ZDIzOTkyMzI5NDkxZTA2YTNhNDJhMmRfZDRiZDFkY2ZiYzM4NTdjMzZhYjk4NDA5NjM5ZTk0YmVfSUQ6NzY0NzA3NDkyMzAwNjE4NDY0N18xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
<column width-ratio="0.500000">
![图片展示了AI Native需求产出流程中本地文档审阅环节的界面。左侧为需求包文件列表，显示了MD、requirement - spec.md等文件。右侧是AI Native APP页面，呈现了需求文档内容，如范围与决策、功能范围与交付边界等ffa](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NGQ2ZDg2OTFlZWFlNDJiNzU5MTIzM2VlZmZhMTE2ODZfNTA2YTE2N2Q4ZTIzNmU3MDJhMDc4MzEzODk4NmM4MTZfSUQ6NzY0NzA3NTE0MTQwMzM4MDcxNF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
</grid>

![图片展示了一个界面，左侧是消息列表，显示了多条对话及相关信息。右侧主要展示了“AI 讲题 APP 完整流程改版需求”文档内容，包括背景与用户问题、目标与成功信号等板块。文档中部分文字被蓝色高亮突出显示。此图片与上下文“本地文档审阅”相关，可能是在本地对需求文档进行审阅时的界面展示，呈现了需求文档的具体内容以及审阅场景。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDllM2U2Y2EyMjg3YTMwYWU5YWYwNzI2ZTlkYThmNDJfMDdiODhmNGRjNzhjOThiNWUyOTZjOGJmN2ZkMzE5MzZfSUQ6NzY0NzA3NjYwOTU4NTUzMTg3OF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

### 本地Handoff preview

<callout emoji="😶‍🌫️">
**注意区分两种preview模式**
本地模式：看本地最新handoff
远端模式：看线上git最新handoff
</callout>

![图片展示的是一个需求评审界面，标题为“我们应该在ai-tutor-kbs中构建什么？”。内容为“把我本地的这个讲题app完整流程的需求的handoff preview出来我看看”。界面底部有“完全访问”标识，以及“ai-tutor-kbs”“本地模式”“feat/202606...”等选项。该图片与文档中“本地Handoff preview”部分相关，用于说明在ai -](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWE4Y2NiYzdhMzk1ZmYwNmNkOTU0ZWZhZDZlMjZmYTRfYmVhYTNjM2I4ZjcwNTUxMmM0NGU3MWJmODRhMGEwODFfSUQ6NzY0NzA3NTk4NTAwNDAzOTEzOF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

## 提交远端

### 首次生成需求

![图片展示了一个界面，顶部有标题“我们应该在 ai-tutor-kbs 中构建什么？”。下方有一行文字“帮我把本地分支所有改动提交至远端，分支和本地一致”。界面下方有多个选项栏，包括“完全访问”下拉菜单、显示“5.5 超高”的选项、语音图标等，还有“ai-tutor-kbs”“本地模式”以及分支名称“feat/20260603-讲题app...”等标识。该图片位于“提交远端 - 首次生成需求”相关内容之后，可能是在说明提交远端需求时的操作界面或相关设置。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZTZhYjJiNTUwMGNiOTg5NmVmOGM1ZWZkNzYwODg3MmNfNjU5M2MzZmZkYTQxZGQ5MThmZDRlOGM2M2QxNjFmZDdfSUQ6NzY0NzA3ODIxNTk3OTM3MTczN18xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

### 修改需求

分支命名按照规范来（fix/xxxxx）

## 远端评审

### 项目预览

地址：http://staging-handoff.search.miui.srv/preview/index.html

![图片展示的是AI Native需求产出中本地Handoff preview界面。左侧为页面目录，包含学习首页、AI教师首页、](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=N2I0YmQ4NDU3ZGZjZTYwMjhiNTI2NzNjNWY0OTM5M2JfN2Y0ZTNmODQzNTQ5NzVlMTgyZTEyM2FkYTgzMGZjMWJfSUQ6NzY0NzA3ODYwMzQ0OTg3OTczMV8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

![图片展示的是AI addCriterion()函数的代码示例。代码中定义了`addComment`函数，接受`comment`参数，使用`console.log`输出`comment`的值。接着定义了`addComment`函数的`addComment`方法，同样接受 addCriterion()函数的代码示例。代码中定义了`addComment`函数，接受`comment`参数，使用`console.log`输出`comment`的值。接着定义了`addComment`函数的`addComment`方法，同样](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NGM3YTg4ZDc0MGQ4NGZjZTNiOTExM2UxYWNmMmM0MWZfNWIyMzAzNmY2ZTY3M2Y0YWI2YWRiMDEzNTdiOWYxOTZfSUQ6NzY0NzA3ODkzODc5NjE4MjcxNF8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

# 常见问题

## 现在的工具用的不顺手，不够理解实际意图怎么办？

<callout emoji="😶‍🌫️">
在实际使用过程中共同打磨skills沉淀经验，跟随git合并实现共建。
常用口令：**帮我（在规范层面）根治这个问题**
</callout>

常问AI：

- 这个balabalbala是为什么会这样，不应该是balabalbalabal吗？你帮我根治这个问题。
- 帮我沉淀到对应的skills或者规范文档-agent.md/知识库经验等
- 帮我根治这个问题

## 为什么写了需求，也根据需求改了handoff-changes，但是preview出来页面没有改动？

<callout emoji="😶‍🌫️">
在实际使用过程中共同打磨skills沉淀经验，跟随git合并实现共建。
常用口令：**帮我（在规范层面）根治这个问题**
</callout>

## Handoff preview页面样式我不满意，手调又不方便怎么办？

<callout emoji="😶‍🌫️">
积极提供参考图（就算只参考部分也可以）
后续建立设计知识库
</callout>

- 只有文本：按照我们的需求改动handoff的界面布局，preview打开我看看
- 有图有文本：截图原型图给AI

  - 按照这个帮我复原到handoff上（有设计稿）
  - 参考这个的页面布局，按照我们的设计风格落地该功能（有原型图）
  - 我想要这个图片中的xxxxx效果，结合我们自己的xxxx，落地（有参考图）

![图片展示的是小米ID或工号（二选 addCriterion）的输入界面。界面上方有“小米ID或工号（二选一）”](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzkzMmIxYjE5YmQ4MDJjODI3NGVlOWYzMWM3NDBhNDZfOWU3YmM2MzRlOGE2NDNiNDVhOThhY2FjYjVjNTc4ZmZfSUQ6NzY0NzA3NzY5ODk1OTk1Mjg4Ml8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)

## 分支合并远端报错/失败怎么办？

<callout emoji="😶‍🌫️">
报错日志复制给AI，让AI修复后重新上传。
</callout>

<grid>
<column width-ratio="0.680761">
![图片展示了小米AI Native需求产出逐步文档中“分支合并远端报错/失败怎么办？”问题的上下文。上方是分支合并失败的日志信息，显示了Pipeline、18311824失败，包含Project、Branch、Commit ID、Commit Message等详细内容。下方是手绘图，标注了“这个是没成功合入（已编辑改）”字样，还配有绿色对勾图标。该图片直观呈现了分支合并失败情况，与上下文关于分支合并报错/失败的处理方法相关。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWM2ZjkxNjE0ZTZhZTkyMWUxMDBjNjQ4Njg4YzAwZjBfMWZhZTA3MzA4MWI1NmU0NWFiYjI5MWUwYWFjYWYwYThfSUQ6NzY0NzA5MzA4MTA2NjgxODc2N18xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
<column width-ratio="0.319239">
![图片展示了AI Native分支合并远端报错/失败的处理示例。上方是分支合并界面，显示“validate” failed to build”和“handoff_validate”失败。下方是日志信息，有大量代码和错误提示。下方对话框中，AI建议将日志复制给AI，让其解决后重新提交，还指出触发了门禁，没有通过。该图片与上下文紧密相关，直观呈现了分支合并报错情况及AI给出的处理建议。](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZDNjYWZhMzdkNmQxMDQ0ZWIyODkxYWZjMjAxZjVlOGNfNDE1NGMzYWU4ZGMyOGMyMDE1NzFjNzZkY2UzNzk2MzFfSUQ6NzY0NzA5MzA4MjQ3MzIzNzcwOV8xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
</grid>

## AI说要使用flutter sdk/安卓模拟器？

<callout emoji="😶‍🌫️">
一般来说，研发代码只读状态不需要下载相关工具。
实在需要下载，请注意工具全局化。
</callout>

<grid>
<column width-ratio="0.393493">
![图片是一段文字内容，解答](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NGRmZDk5Y2ZhNzJjMWUzNzU0NzgzNzIwNGNiMTQzYjJfODFjMWYyYzI4MDgxMjIzODM0OGY5ZWFlNjdlMThkY2FfSUQ6NzY0NzA3NDgzMDk2MTkwNDg0N18xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
<column width-ratio="0.606507">
![图片 !*** !*** !*** !*** !*** !*** addCriterion](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmU5MmU1NTQ3MDlhOWUzZTAwMGNjZTRkNWI2OTBiYzVfYTQxYjYwYTg3ZWE0YjQ5ZDBiODdiNDk3NDMzYzkxMjNfSUQ6NzY0NzA3NDgwMTk5MTg2MzI3M18xNzgzOTI1NjQ4OjE3ODM5MjkyNDhfVjM)
</column>
</grid>