# [05-08] AI Native产品协作探索｜AI教育从Demo走向落地

> 来源: https://mi.feishu.cn/wiki/DmjiwwDSri7vwDkNAUIciYpenrc

<callout emoji="✨">
**李雪靖**
> 互联网业务部-内容生态部-AI应用中心-产品经理
- 原在校期间做宠物友好地图小程序的`创业者`
- 来到小米`第368天`的`设计背景``代码小白`产品25届校招生
- 负责AI搜索`AI相机`、`AI摘要`等系列功能、`AI教育`独立APP（暂未命名的AI Native产品）产品迭代
- 连续4周迭代AI Native产品，也连续4周`每天AI coding 18小时+`
</callout>

# **前言**

AI 能力的带来的**产能快速提升**正在从根本上改变产品工作的边界。

<table><colgroup><col/><col/><col/><col/><col/></colgroup><tbody><tr><td colspan="5" vertical-align="top"><b>对产品的挑战</b></td></tr><tr><td colspan="2" vertical-align="top"><b>Past</b></td><td vertical-align="middle"><b>AI的改变</b></td><td colspan="2" vertical-align="top"><b>Now</b></td></tr><tr><td rowspan="3" vertical-align="middle"><b>把需求说清楚</b></td><td vertical-align="top">文档不够详细</td><td rowspan="4" vertical-align="middle"><b>极大降低实现门槛</b></td><td rowspan="3" vertical-align="middle"><b>产品定位与协作模式</b></td><td vertical-align="top">需求边界</td></tr><tr><td vertical-align="top">设计稿不够具体</td><td vertical-align="top">机读标准</td></tr><tr><td vertical-align="top">边界考虑不清</td><td vertical-align="top">开发落地协作</td></tr><tr><td colspan="2" vertical-align="top"><b>核心能力：需求文档是否全面</b></td><td colspan="2" vertical-align="top"><b>核心能力：需求定义约束</b></td></tr></tbody></table>

目前项目已实现全员100% **AI Coding覆盖**，以**AI能力为核心**打造**AI Native产品**，并持续**以AI为中心重塑协作方式**。

# 第一章 理念层：AI Native 迭代模式下对产品的新要求

## 旧模式 vs 新模式：产品产出的新挑战

<callout emoji="🎯">
核心命题：  
研发提速倒逼产品**产出提速**，全员**以AI为媒介**进行协作。
</callout>

| 维度 | 旧模式 | 新模式 | 核心变化 |
|-|-|-|-|
| 流程 | 瀑布流（线性串行） | **全员并行** | 产品直接产出为 HTML/落地代码 Demo，设计与开发并行 |
| 决策 | 文档评审 | **Demo 演示** | 决策基于可交互原型，不靠想象，不靠文字描述 |
| 重心 | 写清楚文档 | **做明白判断** | 产品从繁琐文档中释放，重心回归用户洞察与业务逻辑 |
| 质量 | 确定性交付 | **不确定性量化** | AI 输出有模糊性，必须建立“定义→量化→迭代”闭环 |
| 协作 | 交付制 | **责任制** | 不是“谁交付什么给谁”，而是“谁对什么（某个维度的质量）负责” |

<grid>
<column width-ratio="0.500000">
**原PRD式（静态）交付方案**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzY5ZDhkNzEwOWFiYzJiNWZjYjlkM2NmOWFhOTQwY2NfNDAwM2NhMjI2ZjMzMDZlNTJiZjNlNDRmYThiODg2ZmVfSUQ6NzYzNzQwNTc1MTk3NTkyMjg4Nl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.500000">
**现Demo式（可交互）交付方案**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWNhNDhmOGM1NDEwMzE0Y2JjMGVlN2I2MjUxZTExZjVfYjA3ODRmMDU4ZDI3YzIyOGZkYTY0MDc0NWE0MGU4MTlfSUQ6NzYzNzQwNTc1MjYzODg4NTA1NV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZjU0YTk2NDM0OTUwOWExNDBkMzVmMmI3NGI2YjJkYjdfZjQwNTNmNGVkNDUxNTMxMzI5MTlkMWUyNTg5NzlhNDlfSUQ6NzYzNzQwNTc1MzA4MzQ5NzY5MF8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

当然，这样的方式解决了一些问题，也带来一些新的挑战：

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td colspan="2" vertical-align="top"><b>解决的问题</b></td><td vertical-align="top"><b>对产品产出物的要求</b></td></tr><tr><td vertical-align="middle"><b>快速生成需求清单</b><br/><b>提升</b>（初稿）<b>产出速度</b></td><td vertical-align="middle"><b>原：</b>有模式需求评审环节承担澄清环节，逐步补齐产品细节，但问题经常在提测后才系统暴露。<hr/><br/><br/><b>现：</b>从 Spec 到 Demo 再到代码的转化速度极快，大幅节省了需求产出从0→0.7的时间。</td><td vertical-align="middle">关键判断写清，如：页面职责、状态边界、字段来源、异常兜底、验收口径、回填路径都要尽量明确、闭环、可校验。</td></tr><tr><td vertical-align="middle"><b>挑战1</b></td><td colspan="2" vertical-align="middle"><b>任何没讲清的地方都会直接被放大，变成错误实现、错误预期或错误验收。</b></td></tr><tr><td vertical-align="middle"><b>快速生成可交互高保真原型</b><br/><b>前置交互细节澄清环节</b></td><td vertical-align="middle"><b>原：</b>写文档时逐步规划高保真原型和方案细节，耗时长；研发需要依据静态文字想象推演动态效果，无法推演的需要靠会议口头澄清。<hr/><br/><br/><b>现：</b>AI会直接把模糊SPEC描述变成可交互Demo，“先看一眼/体验一下再讨论”比“先想一轮再讨论”更有效。</td><td vertical-align="middle">交互结论前置，如：主链路、页面跳转、关键反馈、状态切换、边界分支都要尽量在 Demo 阶段看清、试清、定清。</td></tr><tr><td vertical-align="middle"><b>挑战2</b></td><td colspan="2" vertical-align="middle"><b>产品（或需求方）需直接在打磨Demo的环节做独立前置澄清。</b></td></tr><tr><td vertical-align="middle"><b>AI为细致稳定的协作媒介</b><br/><b>减少信息传递损耗</b></td><td vertical-align="middle"><b>原：</b>文档主要给人读，需求信息在产品、设计、研发、测试之间多轮传递，容易在转述中遗漏、变形或依赖人工脑补。<hr/><br/><br/><b>现：</b>AI读文档，不会信息遗漏，承担信息传递与转换的中间层。如果团队不同产物语义不一致，AI 就会把同一对象当成不同对象，容易出现错连、漏改等。</td><td vertical-align="middle">共享语义统一，如：页面名、模块名、组件名、字段名、状态名、动作名都要尽量唯一、稳定、可索引。</td></tr><tr><td vertical-align="middle"><b>挑战3</b></td><td colspan="2" vertical-align="middle"><b>产研需要共识一套统一、稳定、可索引的命名体系，让 AI 能准确读、准确写、准确传递。</b></td></tr></tbody></table>

<callout emoji="◽">
AI Native 带来的变化，表面看是“产能更高”，真正改变协作方式的其实是三件事：  
**定义错误暴露得更早、原型被推到决策前台、产出物从“人读标准”转向“机读标准”。**
</callout>

## AI 产品工作流：先规划，再生成

> Harness是一种思维习惯，努力让自己成为高级AI驯马师

<callout emoji="📌">
核心命题：  
AI 能显著加快写出来、做出来的速度，但不能替团队完成**需求定义、边界和取舍的判断**。
</callout>

### **Q：为什么一定要先规划，再生成？**

- **AI 擅长补全，不擅长替你决定。** 只要输入里缺边界，模型就会用最像样的方式把空白填满；产出看起来很完整，但很多关键判断其实是“它替你猜的”。
- **越靠后改，代价越高。** 在 Spec 里改一句约束，可能只要一分钟；等到 Demo、研发实现甚至测试用例都生长出来，再回头改，就会变成整条链路返工。

> PRD生成是典型的一步式skill，容易受其影响。以输入框需求为例，效果如下：

<grid>
<column width-ratio="0.333333">
**A：直接根据模糊需求生成PRD**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=Y2ZiNTk5ODY3MGY3MjRmZmVhMTRjNTQ2Mjg4MTQ5YTlfNzNlMTk4ZTQ0N2ExNmYxMDdkM2FjODlmNWEwNjM3NDlfSUQ6NzYzNzQwNTc1NjU4NDk3MTQ3OV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**B：产品需求SPEC→生成PRD**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGIwNzcwZDExNzBkY2VlZDY2OTU3ZjI4OWNkNmM3NDBfN2NhMWUwNGY5YmVjMTg0ZTY4ZDQ3MDU4NmM3NzUzNTVfSUQ6NzYzNzQwNTc1NzkyMjc0MTQ0OV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**C：产品SPEC→Demo澄清→PRD**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZThjMzdhNWYzN2E0YzJhNjBjNzkzNWY5MzY4MTY1ODdfNTBhNmIyMmU4Mjk3OTZiZTljNmYzMTkyZmRiYmU0YjRfSUQ6NzYzNzQwNTc1NzA0NjQxMDQ0MV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

因此，更现实、也更适合 AI 的方式不是追求打磨一个完美的skill试图“一次性生成完美 PRD”，而是先规划，再快速生成，再围绕生成结果继续改微调规划本身，直至可闭环、可落地。

### **A：产品SPEC→Demo澄清→PRD流程**

1. **SPEC规划负责把判断前置原因：**需求不够具体时，AI 会忽略细节或者自行补足细节，容易把未确认的判断直接落地到Demo里。**任务：**明确需求边界做什么、不做什么、有哪些状态、什么算完成。**例如：**

   > 释义：SPEC 即 Specification，SPEC驱动即**规范驱动开发**，也可理解为**先思考实现计划，再落地。**

   ```Markdown
   ### 5.3 输入区
   
   #### 定位与目标
   输入区是 AI老师 页的统一任务入口，负责承接文本、语音、图片三类输入，并在同一组件内完成草稿编辑、补充与发送确认。目标是让用户始终围绕一个底部输入区完成操作，不因输入方式切换而跳出当前会话骨架。
   
   #### 结构布局
   - 输入区固定在页面底部，与工具栏、底部导航共同构成底部固定交互层。
   - 整体由两部分组成：主输入条、图片预览行。
   - 主输入条固定分为四段：左侧入口、输入主体、模式切换、右侧动作。
   - 图片预览行仅在用户已选图片但尚未发送时出现，位于主输入条上方。
   
   #### 组件划分
   - 左侧入口：承接拍照或加图。
   - 输入主体：承接文本输入框与按住说话区域。
   - 模式切换：负责文本输入与语音待命之间切换。
   - 右侧动作：根据状态切换为“更多操作”或“发送”。
   - 图片预览行：承接已选图片的预览、删除和继续补图。
   - 扩展层：图片选择面板与全屏相册浮层。
   
   #### 核心方案
   - 文本、语音、图片三类输入共用同一个输入组件，不拆成三套独立壳体。
   - 输入区通过统一状态机管理：键盘输入、语音待命、录音中、图片待发送。
   - 状态切换只改变组件内部显隐、文案和按钮样式，不改变输入区整体骨架和层级。
   
   #### 状态定义
   - `keyboard`：文本输入态，显示输入框。
   - `voice-ready`：语音待命态，显示“按住说话”按钮。
   - `recording`：语音录制态，显示录音反馈与取消提示。
   - `image-pending`：图片待发送态，显示图片预览行，允许补字、补图或删除。
   
   #### 数据与发送规则
   - 文本输入先进入当前草稿，不直接写入会话正文。
   - 语音识别结果不需回填输入框，转成文字后再发送。
   - 图片选择后先进入待发送态，不自动入会话。
   - 只有用户明确点击发送后，本轮文本、图片或语音转写结果才进入当前线程。
   
   #### 关键交互规则
   - 无文字、无图片时，右侧动作为“更多操作”。
   - 有文字或有图片时，右侧动作切换为“发送”。
   - 图片上传成功后保持在待发送态，不自动触发对话。
   - 语音结束后先回填文字，不直接触发对话。
   - 空态、输入中、待发送、失败重试时，输入区位置和骨架保持一致。
   
   #### 典型链路
   - 文本：输入文字 → 形成草稿 → 点击发送 → 进入会话。
   - 语音：切到语音待命 → 按住录音 → 松开转文字并发送。
   - 图片：拍照或选图 → 进入图片待发送态 → 补充文字 → 点击发送。
   
   #### 异常与边界
   - 发送失败时保留当前草稿和图片，支持直接重试。
   - 录音取消时丢弃本次识别结果，不污染现有草稿。
   - 拍照或选图取消时回到原状态，不新增图片。
   - 图片超上限时禁止继续添加，并给出数量限制提示。
   ```
2. **Demo生成负责把问题显化原因：**很多交互问题、信息层级问题、异常兜底问题，只有在“能点、能走、能看”的时候才会暴露。**任务：**根据 需求SPEC 快速展开为界面、流程和说明，并围绕演示结果补齐返修SPEC。**例如：**

   <figure view-type="Preview"><source href="https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDk2NDA0MGUwYzM5MzRkMTIwMDA4N2ViODgzZmQzMDJfMjkzNjliOGY5ZGI3ZmIzMDUwNWY5ZDkzNWNmOGU5ZDdfSUQ6NzYzNzQwNTc1NjY3ODA2NTMzOF8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM" mime="video/mp4" origin-height="790.000000" origin-width="364.000000" token="Sna0bsxU5oUhEMxbbiGcUASanXe"/></figure>

<callout emoji="📌">
这里真正必要的是 Spec 和 Demo，**顶层约束物SPEC反而比最终产出的Demo/PRD更重要**。
> PRD 只是在少数需要长期沉淀或对外同步时，才值得补的一份可选产物，而不是默认必经环节。
</callout>

## 顶层约束物：让团队从 Demo 走向落地的关键

实际推进时最容易出问题的，不是工具不熟练产出不够快，而是**「每个人都在按自己的方式产出」**。

### Q：没有顶层约束物，会出现什么问题

**场景1：原型图施工时（功能复用问题）**

无论是单人多需求迭代，还是多产品协作，都会遇到这样的问题：明明已经做过的页面和组件，换个页面、换个人又要重新生成一遍，而AI往往会产出相似但不一致的方案，导致已有功能难以复用，复用和联调成本随之持续上升。

<grid>
<column width-ratio="0.333333">
**上游功能原型图界面效果**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmQzZTMxZTljY2NhYTBiOTkyOGI4ZDA0ZDUzMWFkMjNfYTFhNDI4MmNjYjQzMDQyYWEyMTMzYTFjNzAyMGMyYWZfSUQ6NzYzNzQwNTc1NzY1NTI3MjYyNl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**A：下游功能共享约束前**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTY3MzBkNzJmYzQ2NDhhYzFiOWMzZjY3YzYzNzkyNzRfOGMwNjVlZGNmNDljYmJlMDMxODNlODJmNTc1NDc4MjJfSUQ6NzYzNzQwNTc2MDA3MDYxODMyNl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**B：下游功能共享约束后**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MGJlNjQ1MDNlYmIxZGY3NDNhMjg3OGYzYjY5ZDJjNDVfYWViZGU5ZGQ3MTlhOTJmNjg3MmUyYmEwOGEzZTdjNzdfSUQ6NzYzNzQwNTc2MDAwMzQ0MzkzNV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

**场景2：与研发协作时（定义/语义对齐问题）**

无论是产品与研发协作，还是双方借助 AI 共读需求，都会遇到这样的问题：上游字段标准、状态口径或设计规范一旦发生变化，下游实现很难快速同步，研发也难以判断哪些页面、接口和逻辑需要一起调整，最终只能逐页修改、逐处校对，返工和联调成本随之持续上升。

> 例：AI询问，PRD要求“App首页底部Tab提供拍照解入口”、当前App首页是quick-action chips设计。是要改为底部TabBar导航，还是保持现有布局?
> 
> 人的语义：底Tab
> 
> AI语义：quick-action chips

<grid>
<column width-ratio="0.333333">
**AI的疑惑**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MzE3NzIzMWIxYmZmNzdhZDNmZTE3OGJmYTM4NWI2NDdfYTQ4ZGU4NmIzM2E4ZTdhYmQ5NzFhMGRhYjdhODc2NmFfSUQ6NzYzNzQwNTc2MjM0MDIyODMxN18xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**A：被迁移功能页面布局**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OTYyNmJiMjQwZjkwM2E3YWFlNTUzNDc4ZjMxY2Q5NTVfOWJhYjYxM2Y1ZDcxNTZiNGVhNmE2ZTA0N2M2N2Q3ZDlfSUQ6NzYzNzQwNTc2MzA2OTIzNDM4M18xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**B：迁移后功能页面布局**  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZGQ3MmY0ODFlYTlmM2Y5MzE4YjhiNzI1M2VmZjhkYWZfZjE5ZTFlMjQ0YWYxNWFhMGM1ODkyZTBkYTI4ODg1NWVfSUQ6NzYzNzQwNTc1OTk0OTc4NjMxNV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

> 释义：
> 
> tab bar 在设计里是一级导航组件，负责在 App 的核心页面之间切换，属于信息架构层。它通常是全局常驻、层级稳定、切换后页面上下文会明显变化。
> 
> chips 这个词更偏 Material 体系里的轻量选择项/标签项/筛选项，强调“短、轻、可多场景复用的小颗粒控件”。你这张图里的这块是一个底部固定、强任务导向、围绕快门动作服务的模式切换器，语义比普通 chips 更重。

这样的问题层层积压，最后的结果就是**：页面越做越不一致，项目产物越积越乱，直至爆发。**

### A：顶层约束物要约束最上游的产品共识

对我们现在的项目来说，顶层约束物要收口的是那些**会被跨页面、跨产品、跨角色反复复用的基础定义**。

只有先把这些定义产、研、设、测对齐，AI介入后才能有四两拨千金的效果**（架构的意义）**。

| 约束维度 | 要收口的内容 | 主要解决的问题 |
|-|-|-|
| 原型图脚手架 | 页面骨架、目录结构、shared 引用方式、版本基线 | 避免不同人继续产出时各搭一套壳，已有页面和能力无法稳定复用 |
| 设计规范 | 视觉基线、布局规则、状态规范、交互规则 | 避免同一产品不同页面出现不一致的样式和交互表现 |
| 页面命名 | 页面中文名、英文名、路由名、页面索引 | 避免同一页面被不同角色用不同名字描述，协作和追踪困难 |
| 组件 / 控件 | 共享组件、控件形态、状态切换、复用边界 | 避免明明做过的功能，换个页面或换个人又重新生成一套 |
| 字段 | 字段名称、字段语义、状态枚举、data-\* 绑定 | 避免产品、研发和 AI 对同一对象理解不一致 |
| 接口 / 协议 | 事件名、指令名、返回结构、交接格式 | 避免研发落地或修改时找不到对应实现和修改范围 |

<callout emoji="◽">
顶层约束解决的问题：  
用**足够强的统一约束**，保证团队里的**每个人**都能尽量**摆脱模型自身偏好以及个人表述偏好的影响，产出方向一致、结构相近的结果**。
</callout>

# 第二章 个人能力升级：以 Skills 为切入点，进行AI提效

> **Challenge One**：研发速度提升了，产品还停留在框架，需求产出速度跟不上研发落地速度？

## 从替代日常高频工作的某一环节开始搭建SKill（Day1-2）

> skill：固定SOP流程or可复用的提示词，包含技能触发场景、执行步骤、约束条件和输出格式。

AI的冲击太过急促，但不意味着我们要一蹴而就。

更有效的做法，是先挑自己每天都在做、又最容易返工的一环开始做 Skill，先把一个点跑顺，再逐步连成线。

**例：在产出一个需求的时候，我会如何思考呢？**

1. 我会先思考需求目标和预期功能，形成初版 PRD 框架
2. 在此基础上，根据用户动线画出原型图主界面，补齐主要功能的设计
3. 最后在串联各个功能界面的过程中，继续把细节回填到 PRD 里。

抽象成Skill，这条链路大致就是：`产品框架 -> PRD`、`PRD -> HTML 原型`、`HTML 原型 -> PRD 反修`。

> 于是我就围绕这三个环节分别做了 3 个 Skills，把每一步单独打磨好，逐步加快自己从想法到 PRD 落地的速度，甚至可以直接产出可交互原型。这样交给 AI 的不再只是静态文档或静态原型，而是一份可运行的界面代码，可以补足很多静态原型图表达不出的交互细节。

这套方式最直接的价值有两点：

- 产品框架一旦演进，PRD 可以快速追进。

> 从需求idea到需求初稿的速度从 1 day -> 5 min

- 研发可以更早拿到明确的 HTML 原型和 CSS 标准，按原型直接落地，与设计并行推进，尽快上线验证。

<callout emoji="📌">
当前置环节的 Skill 已足够稳定、产出无需大范围返修时，就可以进一步串成多步骤 Skill。
> 💡 重要信号：你还会详细看前置环节skills的产出内容吗？
</callout>

## 复杂项目里的多步 Skill 怎么搭（Day3-5）

<blockquote><p>详见<cite doc-id="ALWTdGGEcorOyBxXuTccjtZbnzc" file-type="docx" title="【教程】复杂落地项目的Skills设计架构（产品篇）" type="doc"></cite></p></blockquote>

复杂项目里的多步 Skill，不只是把几个 prompt 串起来，而是把每一层到底在解决什么问题先写清。

以我的 skill `AI产品原型驱动` 为例，这套设计大致可以拆成下面三层：

<table><colgroup><col/><col/><col/></colgroup><tbody><tr><td vertical-align="top"><b>描述维度</b></td><td vertical-align="top"><b>撰写内容</b></td><td vertical-align="top">对应示例</td></tr><tr><td vertical-align="top">关键动作内容</td><td vertical-align="top">先把主链路动作拆成几个稳定环节，讲明每一环写清触发时机、输入材料、输出产物和成功标准。</td><td vertical-align="top"><pre caption="&#xA;" lang="Plain Text"><code>本 Skill 包含三个环节，按用户需求调用：<br/>产品原型spec生成：将产品构思/框架/思路转化为结构化的原型 Spec（Markdown）<br/>原型demo生成：基于原型 Spec 生成按功能点拆分的可交互 HTML 原型<br/>产品prd生成：基于确认后的原型 Demo 生成正式 PRD 文档<br/>三个环节遵循严格的单向依赖：原型 Spec → HTML 原型 → PRD。修改任何上游文件时，必须同步更新所有下游文件。<br/>执行具体项目时，若仓库根目录存在 _shared/，必须先读取其中全部 readme；若存在 _shared/AI-Native产品迭代指导方针.md、_shared/design-system.md 等共享前置材料，也必须在 readme 之后按需继续读取，且项目级文件优先于通用 skill。<br/>……</code></pre></td></tr><tr><td vertical-align="top">动作衔接依赖</td><td vertical-align="top">再把环节之间的同步关系写死：上游改了，下游怎么追；哪些文件要一起更新；组件、字段、页面和飞书链接各回写到哪里。这样 Skill 才能持续迭代，而不是每改一次都靠人肉补漏。</td><td vertical-align="top"><pre caption="&#xA;" lang="Plain Text"><code>## 所有环节必须遵守以下同步规则<br/>1. **修改原型 Spec 时**：必须检查是否存在对应的 HTML 原型和 PRD，若存在则提醒用户需要同步更新<br/>2. **修改 HTML 原型时**：必须检查原型 Spec 是否需要反向更新（如果原型变更源于 Spec 变更则不需要），同时检查 PRD 是否需要同步<br/>3. **修改 PRD 时**：必须同时更新 git 仓库中的 Markdown 文件，并查阅 `_shared/飞书文档速查表.md` 获取对应飞书链接，自动同步变更到飞书文档；如果速查表中没有对应链接，提醒用户是否需要新建飞书文档<br/>4. **任何文件的修改**：都必须遵循"原型 Spec → HTML 原型 → PRD"的依赖方向，不允许只改下游不改上游<br/>5. **速查表必须同步**：每次新增或返修需求、Spec、PRD、HTML 原型时，都必须检查并同步 `_shared/组件名称速查表.md`、`_shared/字段名称速查表.md`、`_shared/页面名称速查表.md` 与 `_shared/飞书文档速查表.md`<br/>6. **字段与组件分开回写**：新增/重命名/废弃组件时更新组件速查表；新增/重命名/废弃共享字段、统计字段、结果字段或 `data-*` 绑定字段时更新字段速查表<br/>……</code></pre></td></tr><tr><td vertical-align="top">项目资产规则</td><td vertical-align="top">最后把进入项目后必须遵守的读写边界单独拎出来，包括先读哪些 shared 文件、项目级规则优先级、版本继承关系，以及写仓库前的确认规则。这样同一个 Skill 到不同项目里也能先对齐约束，再开始生成。</td><td vertical-align="top"><pre caption="&#xA;" lang="Plain Text"><code>## 所有环节必须遵守以下同步规则<br/>项目启动前强制规则<br/>开始任何分析、生成、返修、同步之前，必须先完成以下动作：<br/>1. **先扫项目级前置文件**：优先检查项目根目录是否存在 `_shared/`，并扫描其中全部 `README` / `README.md` / `readme.md` / `*_readme.md` 文件；只要存在，就必须先全部读完<br/>2. **`_shared/AI_tutor_readme.md` 默认最高优先级**：在 `AI_tutor` 项目里，如果存在该文件，默认视为本轮工作的第一必读文件；没读完前禁止继续分析、生成、返修或同步<br/>3. **项目前置文件优先于通用 skill**：`_shared/` 下 readme、设计规范、共享骨架和项目指导文件都属于项目级硬约束；若与通用 skill 冲突，优先执行项目文件<br/>4. **readme 之后再读 shared 真正资源**：读完 readme 后，按任务需要继续读取 `_shared/design-system.md`、页面引用的 `_shared/versions/vX.Y.Z/` 快照文件，以及仅在需要改组件时读取 `_shared/workspace/` 草稿文件<br/>5. **先判断页面引用的是哪个 shared 版本**：开始改页面前，先检查目标 HTML 当前引用的 `_shared/versions/vX.Y.Z/` 版本号；页面默认继续沿用该版本，除非用户明确要求升级 shared 组件版本<br/><br/>### Git 仓库写入规则<br/>任何对 git 仓库文件的创建、修改、删除操作，都必须先向用户确认：<br/>- 明确告知将要写入/修改的文件路径和变更内容摘要<br/>- 等待用户明确同意后再执行写入<br/>- 如果用户拒绝，保留变更内容在对话中供用户手动处理<br/>……</code></pre></td></tr></tbody></table>

此外，真正能长期使用的 Skill，一定会关注**“失败场景”。**

很多 Skill 只会第一次生成，真正进入 2 到 5 轮迭代以后就开始失真。因为它们默认“生成”是正常情况，“修改”是例外。**但失败总是常态，所以我把返修作为必要环节**，每个环节都有独立的“修改时的同步规则”章节。

```Markdown
## 修改联动检查清单（全局）
任何修改操作完成后，按以下清单检查：
- [ ] 原型 Spec 是否与 HTML 原型一致？
- [ ] HTML 原型是否与 PRD 一致？
- [ ] PRD 的 git 版本是否与飞书版本一致？
- [ ] 飞书文档中的原型预览链接是否有效？
- [ ] 飞书文档的评论是否已归档？
……
只有全部一致时，才算修改完成。
```

<callout emoji="📌">
多步骤 Skill 这三层写清后，才能**减少人工介入**，**提升首次产出的准确率**从而提升整体效率。  
同时，把握好项目规范后，即可**突破会话上下文限制，成为项目级资产**，奠定协作基础。
</callout>

## 学会向模型提问：大模型是好的「回答者」，但不是好的「提问者」（Day5+）

当你学会熟练跟AI打交道，那么就可以再往前走一步：让AI开始介入思路完全成形的时候**（头脑风暴）**。

在现在，我更常把它当成一个随时可聊的**全知全能的伙伴**，先一起把问题讲清楚。每天n问：

```Plain
我是一个不懂代码的可爱产品，我遇到了一些问题：xxxxxxx。
接下来我们来一起探讨一下这个问题。
我是这样想的，如果要解决这些问题，我有一个思路是这样的xxxxxxx。
但是我觉得可能这样解决有一些问题xxxxxx，还有一些地方我不明白行不行xxxxxxx。
你觉得怎么样，有什么好想法？
```

<callout emoji="📌">
**让AI全知全能的能力内化为你的能力的一部分，这是驾驭AI的起点。**
</callout>

# 第三章 产品工程体系建设：Vibe Coding 与 Vibe Design 的运用

> **Challenge Two**：如何规范存储这些产出物？在生成新内容的时候如何让AI与自己保证视野（上下文）同步？

## 产品 Git 仓库架构

<blockquote><p>Git仓库是一个代码管理平台，小白教程：<cite doc-id="PO2HdZXz8o4FcdxTzRvckAQQnef" file-type="docx" title="【教程】给产品小白的最短教程：Git使用" type="doc"></cite></p></blockquote>

<callout emoji="📌">
这个仓库现在主要解决两件事：一是**规范化存储**，二是**上下文统一**，三是**原型图演示**。
</callout>

- **规范化存储**

  - **规范内容：**统一存放 README、Design System、handoff 规范等项目级约束。
  - **原型共用内容：**统一存放样式版本、全局 CSS、组件库、飞书文档映射表等共享资产。
  - **开发对齐内容：**统一存放组件表、字段表、页面命名表等需要产研持续共读的事实。
- **上下文统一**

  - **保证规范一致：**每次使用仓库都按同一套说明和结构工作，不再依赖当次 prompt 或会话上下文限制。
  - **杜绝上下文腐坏：**在多轮反复修改中，会话里的上下文很容易失真；把文件作为唯一可信产出物，要求每一阶段都以上一阶段的文件作为输入，才能保证后续生成始终基于同一份事实（让 AI 直接读取仓库中的规范、组件和版本事实，再基于这些内容继续生成或者直接修改这些文件，逃离大模型幻觉）。

```
ai_tutor_prds/
├── index.html                              # 版本目录入口
├── _shared/                                # 项目共用资产库
│   ├── product-ai/
│   │   ├── AI_tutor_readme.md              # 仓库使用说明书（每次施工前必读）
│   │   └── design-system.md                # 视觉基线和 shared 组件规则
│   ├── lookups/
│   │   ├── 组件名称速查表.md               # 统一组件命名
│   │   ├── 字段名称速查表.md               # 统一字段 / data-* 命名
│   │   ├── 页面名称速查表.md               # 统一页面命名和原型落点
│   │   └── 飞书文档速查表.md               # 仓库文件和飞书文档对应关系
│   ├── dev-bridge/
│   │   ├── dev-handoff-spec.md             # handoff 规范
│   │   ├── dev-bridge.md                   # 产品到研发的桥接主文档
│   │   └── registry/                       # pages / components / protocols 等事实索引
│   ├── exports/
│   │   ├── mobile-shell/                   # mobile.html 当前 live runtime
│   │   └── ai-render-components/           # AI 渲染相关共享能力
│   ├── versions/
│   │   └── v1.0.0/                         # 版本页引用的 shared 冻结快照
│   └── route-registry.json                 # index.html 的唯一目录数据源
├── V1.0登陆与对话/                          # 独立版本目录：Spec / 原型 / 私有约束 / page.js / handoff
├── V1.1对话卡片/
├── V1.2任务页/
├── V2.0拍题与批改/
├── V2.1任务视图/                         
├── V3.0AI白板讲解/
├── asset/                                  # 资源保存（如字体、文件）
└── scripts/                                # 脚手架、lint、构建
```

- **原型图演示：通过GitLab Pages直接部署内网可见**的产品仓库的网址，便于需求评审或Demo体验。

> AI老师原型图地址：[http://ai-tutor-prds-6af886.pages.n.xiaomi.com/](http://ai-tutor-prds-6af886.pages.n.xiaomi.com/)
> 
> ⚠️ 内部项目，受限访问。需有仓库访问权限才可查看哦～

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YzJlN2M4YzAwZGQ0ZDAwZmFiMjhhMWRlNmM1ODQzMDVfZjE5ZDBmMDQ4OGVlNjI3ODViYWIyMmYyNjM3NTllM2NfSUQ6NzYzNzQwNTc2NDg2MTg1Njk0Nl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)

<callout emoji="📌">
给研发的交付方式：**以Git仓库链接为交付物和上下文，AI以Vx.x的单位去控制开发需求范围。**
</callout>

## 仓库需求孵化与合入流程

这部分真正要看清的是两条线：

- **第一：需求孵化与合入逻辑（版本的叠加逻辑）**版本关系不是分别完全独立，而是沿着同一条业务主线继续加功能，以保证能复用组件及原有逻辑：

  > 例如：
  > 
  > V1.0 = V1.0  
  > V1.1 = V1.0 + V1.1 分支新增的对话卡片部分   --V1.1和V1.2并行开发  
  > V1.2 = V1.0 + V1.2 分支新增的任务 Tab 部分   --V1.1和V1.2并行开发  
  > V2.0 = V1.0 + V1.1 + V1.2 + V2.0 分支新增的拍题与批改部分  
  > ……

<callout emoji="📌">
需求的孵化逻辑：  
仓库里的 `Vx.x` 目录（即孵化/开发分支）是同一个产品**在不同阶段新增的能力分支**。  
新功能先在自己的分支里孵化，验证清楚后，再统一合并进入主分支（即线上分支）。
> 💡 重要信号：此时你应该发现，需求的孵化逻辑已经高度雷同于开发代码管理逻辑
</callout>

- **第二：需求的孵化过程（AI 先产出 Spec，人工集中澄清）**

  1. **AI 产出需求 Spec** ：AI 在产出 Spec 时不是直接一口气往下写，而是应该先确定核心功能，再判断应该拆成哪些页面、组件、字段、状态等，Demo需要展示哪些关键Pages（关键帧），最后再做关键说明补齐。
  2. **AI根据需求Spec生成Demo**：AI根据关键Pages（关键帧）生成可供评审的原型图，进行**人工澄清**或**Demo体验**。相关修改意见再同步到Demo，并回写到Spec和shared文件中。

<callout emoji="📌">
**人工介入原则**  
AI 生成内容多、速度快，人工不可能逐项审阅。因此，在上层规范明确的前提下，应尽量把人工介入集中在**结果可视、效果直观、便于快速判断的关键环节**。
</callout>

## 高品质产品原型的落地：Design Token 构造

<blockquote><p>详见教程：<cite doc-id="G9kodVzTJoupO0xdSJzc2Yqinrc" file-type="docx" title="【教程】 高品质产品原型的落地：Design Token构造" type="doc"></cite></p></blockquote>

<callout>
AI 越强大，约束体系越重要，是用更精确的约束让 AI 的输出稳定可控。  
**设计从「执行层」前移到了「规则层」**：定义的 Token 和规范，决定了 AI 生成的每一个页面的视觉品质。
</callout>

在我的shared文件夹中，有这样一些文件⬇️

```Shell
design-system.md
  -> theme.css                          # Design Token定义
  -> shell / app-shell                  # Demo演示脚手架引用样式（Token消费）
  -> components.css / views.css         # 共享组件与共享页面样式（Token消费）
  -> _shared/exports/mobile-shell       # 主分支界面引用样式（Token消费）
  -> _shared/versions/v1.0.0            # 孵化分支界面引用样式（Token消费）
```

- **Design system（即Design.md）：Design Token的值的主基调、生成标准及引用标准**定义共享视觉语言和实现边界，往往会影响组件边界、页面模板、共享层/版本层分工、交付规范。
- **Design token：颜色、字号、间距、圆角、阴影、尺寸这些值是什么**定义最基础的设计变量，实际上就是把设计决策编译为一串CSS变量，定义了整个产品的视觉基因。这些 token 会被上层样式消费，形成共享组件和共享页面样式。例如：

```CSS
:root {
  /* 背景：冷白雾面基底，不是纯白 */
  --c-bg: #F9FAF9;
  
  /* 品牌主色：青绿，用于 CTA、链接、强调 */
  --c-brand: #00D1B2;
  
  /* 文字：三级灰度递减，冷绿灰色调 */
  --c-text:   #1A3C34;   /* 一级：标题、正文 */
  --c-text-2: #3D5A52;   /* 二级：副标题 */
  --c-text-3: #5A7A70;   /* 三级：占位符、注释 */
  
  /* 间距：严格 4px 栅格 */
  --sp-4:  8px;   --sp-8:  16px;   --sp-10: 24px;
  
  /* 圆角：克制的圆润感 */
  --r-md: 12px;   --r-xl: 20px;   --r-full: 9999px;
  
  /* 阴影：品牌色调阴影，不是黑色 */
  --sh-sm: 0 0 16px rgba(0, 150, 137, 0.07);
}
```

<grid>
<column width-ratio="0.333333">
**无设计规范**  
（语言描述橙色温馨风格）  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MWJmNzM3MzJjYmNlOGViYmU5OWFjYmExNmI0ZmYyNGVfOGRlOTBmNDc5ZTE4ZTQwNGQzMzY1YmQyZmEyZjQwNDBfSUQ6NzYzNzQwNTc2Njc2Njg1NzQyMV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**模糊的设计规范**  
（控制色调、圆角、图标方案等）  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWFmZTBlYmUxNDhhYzk4ZjE4NTVjMmViMTVmOTViNTRfNDQ4MjJhOWU4ODg0OWQ4YjkxMDlkNzU5ZWJhYjk1MDZfSUQ6NzYzNzQwNTc2NzQxNTQ4MzYxMl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
**层级清晰的设计规范**  
（原型界面脚手架架构+详细设计规范）  
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MjNhYmRkMDdmYTJhZWVhMDg2ZjllYTA4MGI1OWZlMWVfZGNjMmE0NjA4MzhlMTRmNDg0ZDYyOGE3ODM0YjYwYjBfSUQ6NzYzNzQwNTc2NzUyNDU1MTg4MV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

它主要解决效率和一致性的问题：

- **提升首次产出原型的界面效果**原型图也可基础按照顶层设计文件生成，保证初始原型的高保真效果。新需求不必反复重定颜色、间距、字号这些基础规则，能直接复用。

  > 场景1：设计在此基础生成的原型上微调，比从0生成再微调的流程要快
  > 
  > 场景2：视觉改动较小的小需求直接使用Token标准生成，无需设计介入
- **跨产物一致性**避免原型、设计稿、研发实现各做各的，产品、设计、研发可以围绕同一套语义化变量沟通，而不是靠截图和感觉反复对齐，保证跨产物对齐。

  > 场景1：视觉风格色调改了，可以快速修改顶层文件，达到全局色调刷新
  > 
  > 场景2：保证产品组件-设计token-研发控件组件一致性，保证语义一致性、产出一致性

<callout emoji="👌">
Design Token 对业务的核心价值，是把重复且容易漂移的设计决策沉淀成统一底层参数，让团队在高频迭代里还能**保持一致、可复用、可扩展**。
</callout>

**设计在 AI Native 流程中的 4 个介入点**

| 介入点 | 设计要定义什么 | 对 AI 产出的作用 |
|-|-|-|
| Design System | 定义品牌形象、视觉语言、页面骨架和组件边界 | 决定 AI 生成结果的整体风格与质量上限 |
| Design Token | 定义颜色、字号、间距、圆角等底层变量，以及调用、覆写、冻结规则 | 保证生成结果稳定、一致、可复用 |
| 组件 / 页面组合标准 | 把 Token 组合成符合视觉交付标准的组件和页面（澄清） | 让 AI 直接生成更接近可交付的界面 |
| 设计直达代码 | 设计借助 AI 直接修改原型或代码中的视觉效果 | 缩短从视觉决策到真实效果落地的链路 |

# 第四章 团队协作：AI Native 团队协作体系

> 参见教程：https://mi.feishu.cn/wiki/O5RZwLV6PijIUBkmwzLci5Rsn5g

<callout emoji="❓">
以上内容已经足够完成基础的项目闭环，但是在实际落地过程中，我们还发现一些问题：
1. **重复劳动**
- 产品在产出Demo时已经做了长时间澄清，但Html代码转Flutter时有转译损失，产品的澄清结论没有100%带入到研发侧，导致研发老师需要再澄清一次已有内容。
- 有些需求不经过产品孵化，直接在落地代码中修改。这导致产品在这个需求基础上进行迭代时，需要用Html再复现一次已有功能，再进行开发。
1. **事实偏移**
- 目前仍非全栈模式，则研发侧需求落地时极大概率会对需求模式进行变更和补充。长此以往，实际代码会与产品仓库存在严重偏移，上下文失真。
- 或者有些需求不经过产品孵化，直接在落地代码中修改，产品仓库上下文会有缺失。
1. **没有脱离瀑布流模式**
- 虚假的Spen驱动：产品Spec→产品产出物→研发Spec→研发产出物→测试Spec→测试产出物，仍有上下游环节卡点阻塞需求快速迭代。
1. **上下文膨胀**
- 随着功能增多，每次用 AI 工作时上下文很快占满，缺乏高效的索引机制。  
……
</callout>

<callout emoji="📌">
**自己的视角无法解决这个问题，就站在其他人的视角解决这个问题。**  
所以，良好的协作关系需要团队的每个人都深度参与进来。
</callout>

---

⚠️注意：以下部分仍在小范围实验中，未实现全员闭环，仅做思路参考。

## 能力与架构托举的“全员全栈”能力

<blockquote><p>详细内容可见<cite doc-id="GSIOdf91ZoWCp2xXcKscF1Hhnyb" file-type="docx" title="【规范】协作V2：AI Coding 全员全栈并行协作团队共识" type="doc"></cite></p></blockquote>

<callout emoji="🚀">
核心理念：**能力与架构分离** — 架构是产物的组织方式，能力是赋予每个人的 AI 工具集。  
**每个团队成员 = 人（经验、审美、架构思维、产品思维、市场判断）+ AI 能力 = 全栈工程师**
</callout>

我们都知道未来的结局是全栈（产设研测运一体）工程师主导，但走向这个理想态的过程并不是一蹴而就的。

**“一个人”使用这些能力（团队共识规范+AI知识边界）**，在统一架构上完成一个需求从提出到落地的全流程。

<grid>
<column width-ratio="0.500000">
<callout emoji="◽">
**架构（静态基础设施）**  
代码和产物的组织方式：
- 多仓库 + 权限隔离
- 孵化分支增量开发
- 事实库分层索引
</callout>
</column>
<column width-ratio="0.500000">
<callout emoji="◽">
**能力（动态生产力）**  
赋予每个人的 AI 工具集：
- 需求产出
- 设计能力
- 代码生成能力
- 测试能力
- 数据分析能力
</callout>
</column>
</grid>

## 多视角 Spec 方案

因为一个人或一组人可能要完成多工种的交叉工作，Spec也不应各自为政，而是一个包含**6个视角**的综合规格文档：

| 视角 | 核心内容 | 立场 |
|-|-|-|
| **产品视角** | 需求范围、功能定义、功能点、交互效果、数据逻辑 | 业务标准、用户体验 |
| **测试视角** | 用例设计大纲、代码质量、功能测试、覆盖率要求、边界条件清单、回归范围 | 功能完善程度与代码质量 |
| **数据视角** | 埋点需求、指标定义、数据分析计划、实验设计 | 业务指标定义与观测 |
| **评测视角** | 提示词设计、工具调用、模型参数、AI 输出质量评测标准、降级策略 | AI 产出质量 |
| **技术视角** | 架构设计、接口定义、组件设计、数据模型、性能、安全 | 功能实现路径 |
| **运维视角** | 监控方案、回滚方案、依赖服务 SLA | 服务稳定性 |

<grid>
<column width-ratio="0.500000"></column>
<column width-ratio="0.500000">
| # | 执行者与动作 | 输入 → 输出 |
|-|-|-|
| 1 | 用户提供需求描述（一段话、飞书文档链接、会议纪要等） | 原始需求 → 触发流程 |
| 2 | **产品 Agent** 生成产品视角 Spec（设计目标、用户画像、页面清单、组件清单、边界场景） | 需求描述 + 事实库规范 → 产品视角初稿 |
| 3 | **测试 Agent** 审阅产品视角，挑出遗漏的边界场景、模糊的验收标准。**不产出测试用例**，只输出修改建议 | 产品视角初稿 → 修改建议列表 |
| 4 | **产品 Agent** 根据测试反馈修订产品视角（可能多轮迭代） | 修改建议 → 产品视角修订稿 |
| 5 | **人审阅确认**产品视角（唯一的人工介入点） | 产品视角修订稿 → 产品视角定稿 |
| 6 | **技术 Agent** 基于产品定稿生成技术视角（架构、接口、数据模型、伪代码） | 产品视角定稿 + 事实库注册表 → 技术视角 |
| 7 | **数据 Agent** 基于产品定稿生成数据视角（埋点、指标、看板、实验设计） | 产品视角定稿 → 数据视角 |
| 8 | **评测 Agent** 基于技术视角和数据视角生成评测视角（仅涉及 AI 功能时触发） | 技术视角 + 数据视角 → 评测视角 |
| 9 | **测试 Agent** 基于所有前序视角生成完整测试视角（影响分析、用例、质量门禁） | 全部前序视角 → 测试视角 |
| 10 | **运维 Agent** 基于技术视角生成运维视角（监控、告警、回滚、灰度） | 技术视角 → 运维视角 |
</column>
</grid>

> 粗显理解，在过渡时期，多视角Spec的意义如下：
> 
> 1. 产品在产出需求Spec方案时可以考虑其他老师视角，考虑更周全，替代部分需求评审补全环节
> 2. 研发需求涉及产品方案改造时，可以先通过多视角Spec完成方案补全，避免卡在产品需求转换
> 3. ……
> 
> 远期来看，这是我们每个人走向全栈的基础，在这个过程中配合AI**锻炼个人的全局视角能力**。

<grid>
<column width-ratio="0.333333">
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=YWFiYjM5YjliMjYwMTQ1MGNmNGFiODJmMGVhNDI5ZDFfNzE3MTk0ZDM0OGQ5MmNiZDU2NDhkZjU5MjRmNGI3MWFfSUQ6NzYzNzQwNTc3MjY4NDIwMTE0OV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZWQ4MGUzZjBkZjRlODY3ZjQ3MWJjZjNmMmY3NjFiODVfNjE5N2M0N2JhYjgxYmNlMmQ4NzRlN2U4ZjJkMGJhMTNfSUQ6NzYzNzQwNTc3MzIyODM2Mjk3Nl8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.333333">
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NmUxY2JiZThlYTNhZjY5NThlMGRhNTRhM2ZiNTdhYTZfY2VhZWU5ODVmYmFmNjk2NzI1OWM4YzQ2NTY2MDIyNzdfSUQ6NzYzNzQwNTc3Mjk1Nzk5NDE2Ml8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

## Git 仓库框架：事实库 + 需求仓库 + 服务仓库

团队统一采用“多仓库 + 权限隔离 + 同仓库双分支”的组织方式：

> 产研在 `develop` 分支内完成 Spec、Demo、评审和增量实现；合并到 `online` 后，再把当次确认版本的 Spec、Demo 快照和评审结论沉淀到事实库。

| 仓库类型 | 允许存在的内容 | 不允许存在的内容 |
|-|-|-|
| 事实仓库 | 索引、规范、归档、经验、注册表、知识抽取工具 | 无 |
| 需求工作仓库 `develop` | Spec、Demo、评审记录、handoff、增量实现、测试脚本 | 事实库真源、副本规范、长期分叉的共享注册表 |
| 需求工作仓库 `online` | 正式代码、运行时配置、最小运行说明、必要合同 | 工作稿 Spec / Demo、评审过程文档、长期沉积的规范副本 |
| 服务仓库 | 运行时代码、工具 / 技能源码、工作区身份文件、服务专属文档 | 团队级规范、跨仓协作规范副本 |
| 工具仓库 | 评测代码、分析脚本、工具专属文档、工具技能资产 | 项目级需求 / 设计 / 任务规范副本 |

## 全栈协同 Handoff协议

<blockquote><p>本章节方案来源<cite type="user" user-id="ou_f44a52a241ee80c31b1d07ab94b1fec9" user-name="孙天"></cite>老师</p><p><cite doc-id="Nl85dhjcyoYQUmxIvaDcHmrYn5c" file-type="docx" title="Handoff Protocol — 亮点功能全景图" type="doc"></cite></p><p><cite doc-id="M2JbdMHJYonaoSxewOccefcKnFf" file-type="docx" title="Handoff Protocol — AI 时代跨角色协同框架设计文档" type="doc"></cite></p></blockquote>

**Q：Handoff 协议解决什么问题？**

<callout emoji="👌">
Handoff 协议，就是把某一需求在产、设、研、测等视角下**已经确认的执行结论**整理成**结构化交接物**，稳定地**交给下游**同事或 Skills 继续推进。
</callout>

在 AI Native 协作里，真正贵的是“重复解释”，如果没有 Handoff，同一个需求至少会被讲N遍。

Handoff 的作用，就是把这部分重复澄清环节前置，并沉淀下来。

> 场景1：需求原定由A开发，最后落地由B开发，换人后又要再澄清一次
> 
> 场景2：产品在Demo澄清和AI讲一次，和其他人拉通再讲一次，甚至其他人在与AI澄清时再讲N次
> 
> ……

| 维度 | 没有 Handoff 时 | 有 Handoff 时 |
|-|-|-|
| 重复劳动 | 下游需要从群聊、截图、口头描述里重新理解需求，产品已经澄清过的内容还要再澄清一次 | 下游直接读取同一份交接事实继续工作，产品已经确认过的结论不会在传递里丢失 |
| 事实偏移 | Demo、设计稿、代码和测试口径容易各写各的，需求一改就不知道谁该跟着改 | 大家围绕同一个需求变更包回写，同一个结论只维护一份真源 |
| AI 接力 | 同一个页面、状态、字段可能被叫成不同名字，AI 容易误读、错连、漏改 | 页面名、状态名、动作名、字段名统一后，AI 才能稳定读取和稳定续写 |

<callout emoji="👌"><p>Handoff核心就三件事</p><ul><li>📄 <b>一个文件说清楚一个需求的落地方案</b>（产品要什么 + 设计长什么样 + 研发怎么做 + 测试怎么验）</li><li>🤖 <b>AI 能直接读、直接写、直接验证</b>（AI Friendly式内容读取）</li><li>📱 <b>Handoff支持实时预览</b>（避免Demo到落地代码的转译损失）<blockquote><p>预览见教程<cite doc-id="XW50dRaqjo4D6nxBO5xc9kAJnuq" file-type="docx" title="Handoff Protocol 端到端演示 — 从用户输入到 H5 预览" type="doc"></cite></p></blockquote></li></ul></callout>

**Q：个人怎么使用 Handoff Protocol 工具？**

一个需求的迭代过程中，从第一次澄清开始都应使用Handoff工具。

**场景1：首次生成一个需求时**

1. 自然语言输入需求，生成 Spec 文档
2. 使用 Spec 文档生成 Handoff 文件

> Handoff可根据存量知识库内容组织Demo的页面、组件等等

1. 使用Handoff preview渲染可预览交互的页面（Demo）

![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmZhOGIzZGRkZTAzYzVjZjgwNmE3YmNlOWYyMmMzZjZfMmNlNTU0Yjc4OTZhNzg2MGU3YzExZWEwZDEyYmI1OTdfSUQ6NzYzNzQwNTc3NDQzNjc2NDg2MV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)

**场景2：开发过程中修改需求时**

1. 用 Handoff diff 告诉团队“这次到底改了什么”：是多了一个状态、改了一条跳转，还是新增了一个字段

   > 如果改动影响研发认领范围，就重新同步认领范围；如果影响验收口径，就同步测试范围和回归项
2. 当 Handoff、Demo、实现范围三者重新对齐后，下游才继续往前做。**否则速度越快，返工越快。**

| 常见动作 | 什么时候用 | 它解决什么问题 |
|-|-|-|
| `/validate` | 交给下游前 | 先看这份交接物是否达到可交接状态，避免把明显缺项的内容往下传 |
| `/diff` | 需求变更后 | 快速告诉团队“这次改了什么”，避免所有人重读整份文档 |
| `/claim` | 研发开始做前 | 锁定谁负责哪一块，避免两个人同时改同一页、同一条链路 |
| `/complete` | 研发完成后 | 把交接权明确传给测试或产品，让后续验收有明确起点 |
| `/status` | 多人并行时 | 看当前谁在做什么、做到哪，避免撞车和遗漏 |

> 一个简单判断标准：
> 
> 如果这条信息只适合留在聊天里，说明它还是讨论；
> 
> 如果它已经足以影响设计、研发或测试动作，就应该进入 handoff。

**Q：Handoff Protocol 是如何串联团队同伴及项目的？**

1. **安装：作为每个团队成员的共用工具**

Handoff Protocol 按角色安装，分为产品、设计、研发、测试四类。

安装时脚本会先让你选择角色，再把对应工作流放进当前项目。

> 虚拟角色⬇️
> 
> - 产品经理：负责维护 `page.product`，把需求范围、交互规则、状态流转和验收标准写清楚。
> - UI 设计师：负责维护 `page.design`，补齐 token、标注、动效和设计审查结论。
> - 研发工程师：负责维护 `page.dev`，认领开发范围并回填路由、组件、接口映射。
> - 测试工程师：负责维护 `page.test`，补齐测试矩阵、边界场景和验收结果。
> 
> 如果已经是全栈工程师，也可以选择SOLO模式，一个人控制所有角色的技能（⚠️高风险）

团队如有多角色在同一需求协作，可以分别运行安装脚本，把不同角色的工作流都补齐到同一个分支文件中。

1. **操作：以Handoff为媒介，多人在同一需求中协作**

<blockquote><p>Handoff使用示例：<cite doc-id="XW50dRaqjo4D6nxBO5xc9kAJnuq" file-type="docx" title="Handoff Protocol 端到端演示 — 从用户输入到 H5 预览" type="doc"></cite></p></blockquote>

每一次澄清都需要Handoff先自动介入再修改，保证所有需求澄清都可以被Handoff记录

团队始终围绕同一需求分支的Handoff接力，每个角色只修改自己负责的那一层并向下游传递

> 上下游传递：自动化通知相关人员决策

<callout emoji="◽">
Handoff 是团队在 AI Native 时代的一层**“公共翻译器”。**  
这样团队才能真的从以人为媒介的“口口相传”，逐步走向以AI为媒介的**“高速协作”**。
</callout>

## 更进一步：Issue驱动的项目管理方案

<blockquote><p>本章节方案来源<cite type="user" user-id="ou_5e900b83dcf112cffc88facce624f418" user-name="冯海涛"></cite>老师</p><p><cite doc-id="Es5kdeVFGoxUSzxzOVbcx3bQnGc" file-type="docx" title="Issue驱动的Managed Agent实践探索" type="doc"></cite></p><p>showcase链接：http://staging-multica-ai.search.miui.srv/</p><p>平台注册setup：<cite doc-id="PvAndFhXsoSuwBxC5t9cnW1qntp" file-type="docx" title="本地cli守护进程&amp;注册 setup" type="doc"></cite> (极简版，一路点点点即可)</p><p><cite doc-id="FL9vdLIpUoGK61xSK3YcSBIPnqd" file-type="docx" title="Fork我们的工作流：Agent &amp; Skills 使用指南" type="doc"></cite></p></blockquote>

<callout emoji="🤟">
仓库框架和 Handoff 协议解决了怎么产出和怎么交接，但还没确认怎么**落地执行**。  
Issue驱动的项目管理方案确定执行阶段怎么分工、接力和推进，支撑人和 AI 一起协作把任务持续做下去。  
--不只是**人与人**的协作，还有**人与AI**的协作。
</callout>

| **维度** | **传统项目管理工具（如 Meego）** | **AI Native 的 issue 驱动** |
|-|-|-|
| 协作对象 | 主要是人与人的分工 | **同时承接人、AI、Agent 的协作** |
| 任务产生 | 多靠人手动创建和拆分 | **需求变更、巡检异常、Review 结论都能自动生成 issue 或子 issue** |
| 执行记录 | 状态和结果主要靠人手动同步 | **分析、执行、Review、验证结果持续回写到同一条 issue** |
| 管理重点 | 管理任务列表和负责人 | **管理分工、接力、阻塞、进度和自动化推进** |

<grid>
<column width-ratio="0.500000">
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NGNhM2MxMDhmMGZiY2Q0ZTU0YzYyNDMxNTU2NzA5NzlfNzcyZGNmMWQ4OTZkZGJjZWQxZGZkYzkyODMyMWU5M2VfSUQ6NzYzNzQwNTc4MTIwNjE5MTMyMV8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
<column width-ratio="0.500000">
![](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=OGZhMGFhN2ViMWVhNmI0MDBhMjY0NDY5NGFhZTA1M2VfZWM2MWIyNWNmYmZjN2I4ZjE3ODE5MmM1MTMwMjg3ZTZfSUQ6NzYzNzQwNTc4MTM1NzU2MzA5MF8xNzc5ODcxNDg1OjE3Nzk4NzUwODVfVjM)
</column>
</grid>

**主要协作场景**

- 不同需求、不同人并行：一个需求对应一个主 issue，各自独立推进。
- 同一需求、不同人分工：在主 issue 下按页面、模块或角色拆子 issue，各自负责各自的交付范围。
- 同一需求、不同人接力：产品澄清后交研发，研发完成后交测试，状态和结论都回在同一条 issue 上。
- 同一需求、人和 Agent 协作：人负责分诊和关键判断，Agent 负责分析、执行、Review、验证。

**核心工作流**

**Agent管理能力**

| 能力 | 具体内容 | 在项目里的价值 |
|-|-|-|
| Agent 角色化 | 可按 Monitor、Clarifier、Executor、Reviewer、QA 等角色拆分职责 | 让 Agent 不只是一个通用助手，而是团队里的具体工种 |
| Agent 配置化 | 每个 Agent 都可独立配置 Instructions、Skills、Memory、环境变量和运行参数 | 让不同 Agent 能稳定承担不同类型任务 |
| 任务队列与状态 | 支持 queued、running、completed、failed 等任务状态，以及 idle、working、blocked、error 等运行状态 | 让 Agent 的执行可分配、可观察、可追踪 |
| 过程透明化 | 支持实时工作面板、执行历史、工具调用和 Token 用量统计 | 让人能看见 Agent 做了什么，而不是只看到结果 |
| 双运行时与自动运行 | 支持 Local / Cloud 两种运行方式，以及定时任务、Webhook、API 触发 | 让 Agent 既能处理本地私有任务，也能承接持续自动化工作 |

**Issue状态管理与核心功能**

| 功能 | 在项目里怎么用 | 主要解决的问题 |
|-|-|-|
| Issue 管理 | 用主 issue 承接一个需求或问题，再按页面、模块、角色拆子 issue；支持状态流转、评论、附件、时间线 | 让任务不散在聊天、代码和口头同步里 |
| 人机统一分配 | 同一套 assignee 机制里既能分给人，也能分给 Agent | 让人和 Agent 进入同一条推进链路 |
| Inbox 通知 | 创建、评论、状态变更、Agent 执行结果都能主动提醒 | 让关键节点不靠人反复追问 |
| Projects 项目层 | 把多个 issue 聚合到项目里，看优先级、状态、进度和负责人 | 让并行需求有统一视角，而不是一条条单看 |
| 实时协作 | issue、评论、Agent 状态、任务进度即时同步 | 让多人和多 Agent 协作时，进展始终是同一份现场 |

<callout emoji="🤟">
以 Issue 为单位落地协作链路，把握好AI Native协作落地的最后一公里。
</callout>

---

<blockquote><p>更多教程：<cite doc-id="MORGdA0UHoO5Adxrr0uckXsRn7Q" file-type="docx" title="AI PM 教程汇总" type="doc"></cite>  更多教程AI实时更新中～</p></blockquote>

# 结语

全员 AI coding 并不是项目启动之初的硬性要求，但大家却不约而同地拥抱了这一新范式，这本身就说明，我们团队对AI方向的判断和共识是高度一致的。

从零开始蹚出一条路注定不会轻松，这四周以来，每个人都踩过不少坑，但大家始终抱着迎接挑战的心态，努力接纳新事物、适应新变化，也愿意包容队友层出不穷的新花样和新尝试（还有我闯的祸），这一点特别让人感动。

虽然今天是我作为产品代表进行分享，但从各位老师身上学到的东西早潜移默化地影响了我。

特别致谢各位：

<blockquote><p><cite type="user" user-id="ou_134c445ca15c13d764cfcb7e4f905da1" user-name="袁彬"></cite><cite type="user" user-id="ou_62db52ec75841569b28083c21121de2a" user-name="陈晟康"></cite><cite type="user" user-id="ou_1029a8804b763c3b8737bafa6dbf3927" user-name="李静"></cite>敢想敢干，追着先进方案往前走，也总推着大家“再想一步”。</p><p><cite type="user" user-id="ou_ff175eb94772f7f5c89cd1c528940cbc" user-name="陶梁"></cite><cite type="user" user-id="ou_f44a52a241ee80c31b1d07ab94b1fec9" user-name="孙天"></cite>像 AI 时代原生长出来的人，同样的模型总能发挥出更聪明的效果，令人<del>嫉妒</del>羡慕</p><p><cite type="user" user-id="ou_5e900b83dcf112cffc88facce624f418" user-name="冯海涛"></cite><cite type="user" user-id="ou_fc68e3011a84b8adb3c2f8fba93c4f48" user-name="贺洋洋"></cite><cite type="user" user-id="ou_8652f3e5c8933810dce6481d20e8d2a0" user-name="王宝仓"></cite>为产品架构搭建协助提供框架思路与工具选型建议，支撑整体方案落地</p><p><cite type="user" user-id="ou_1210112ed39ac135412e812d7c8869ab" user-name="王帅琦"></cite><cite type="user" user-id="ou_c602e19debe6299bad18bfc9b78b1a6a" user-name="琚川"></cite><cite type="user" user-id="ou_abdaecb3c7c199e33a89019766ef8bc6" user-name="陈光涛"></cite>包容各种天马行空的想法，也总能在理解的基础上把方案再往前推一步</p><p><cite type="user" user-id="ou_60f1524095b46195bdce1bf9e3ef956f" user-name="Bo5 Wang 汪博"></cite><cite type="user" user-id="ou_4b22579cf1a16843b92cb5dccd469bb1" user-name="李高媛"></cite>拥抱 AI，也始终站在产品视角保持清醒，敢在关键时刻踩刹车</p><p><cite type="user" user-id="ou_991e1dd1a42ee14de48faea9fde30ad1" user-name="李博"></cite><cite type="user" user-id="ou_175ae989080e9c2c027f46f5d3d53bb9" user-name="许志恒"></cite><cite type="user" user-id="ou_0debd188a69ab0b0d9b4b88425a8f065" user-name="娄辛辉"></cite>敢于尝试新方案，而且真的把新方案落成了协作方式</p><p>还有其他参与项目攻坚的小伙伴们……相信我们终会走出艰难的起步期，迎来真正的起飞：）</p></blockquote>