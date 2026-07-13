# 【教程】Multiview-spec使用说明书

## 1. 目标定位和视角分工

<callout emoji="💡">
**定位**：`multiview-spec` 是多视角 Spec 生成器。它把一个孵化需求拆给多个专业视角分别产出、审查和修订，避免一个 AI 从头写到尾。
</callout>

| **视角** | **负责回答的问题** | **主要产出** |
|-|-|-|
| **产品product** | 为什么做、解决什么问题、用户怎么用、哪些不做 | 背景、目标、Must/Should/Won't、页面/模块/组件清单、需求点、交互、预期用户结果、异常体验 |
| **技术tech** | 基于当前代码仓库怎么实现、哪些能力复用、哪些接口或模块要变 | 架构边界、模块影响、复用方案、API、配置、数据模型、风险与验证要求 |
| **数据data** | 成功如何衡量、指标和埋点怎么定义 | 北极星指标、过程指标、护栏指标、埋点事件表；指标口径要追溯到事件和参数条件，关键属性要逐项写明取值。 |
| **评测eval** | 如果需求涉及 AI，如何判断模型、Prompt、工具调用是否达标 | AI 质量目标、评测场景、阈值、降级策略 |
| **测试test** | 应该测哪些范围、哪些边界会阻断发布 | 测试范围、验收矩阵、边界覆盖、回归范围、自动化门禁、发布阻断项 |
| **运维ops** | 上线后如何监控、告警、发布、回滚 | 监控信号、告警阈值、发布计划、回滚方案、依赖检查、Runbook 要点 |

产品product 是入口。产品product 首次产出后，系统必须先进入 product-draft gate。只有出现两个以上可行方案且没有明显最优解的问题时，才生成 review.html 让人拍板；没有真实抉择时，状态机会自动通过该 gate。产品初稿 gate 通过后，才允许进入产品挑战；产品定稿 gate 通过前，下游技术、数据、测试、运维不能开始。

评测eval 只在需求被判断为 AI 相关时启用：

- 需求包含模型、Prompt、Agent、工具调用、生成、智能评测等内容时启用。
- 非 AI 需求默认跳过评测eval，不强行补空文档。

> 飞书正文中保留了用户粘贴的画板。同步时不能用会删除白板块的全量覆盖方式。

<grid><column width-ratio="0.346829"><whiteboard token="F1ZEwvtEShNDuUbM1bncZpk3nmb"></whiteboard></column><column width-ratio="0.643171"><table><colgroup><col/><col/><col/></colgroup><thead><tr><th>#</th><th>执行者与动作</th><th>输入 → 输出</th></tr></thead><tbody><tr><td>1</td><td>用户提供需求描述，包含一段话、飞书文档链接或会议纪要</td><td>原始需求 → 触发流程</td></tr><tr><td>2</td><td>产品product Agent 生成产品product 初稿</td><td>需求描述 + 共用规范 → 产品product 初稿</td></tr><tr><td>3</td><td>产品初稿 gate 检查：没有真实抉择自动通过，有真实抉择才让人选择方案</td><td>产品product 初稿 → 继续或反馈</td></tr><tr><td>4</td><td>产品挑战 Agent 审查产品初稿，指出需求遗漏、交互缺口和下游不可执行风险</td><td>产品product 初稿 → AI 审查意见</td></tr><tr><td>5</td><td>产品product Agent 根据人类反馈和挑战意见修订产品product</td><td>反馈 + 审查意见 → 产品product 修订稿</td></tr><tr><td>6</td><td>产品定稿 gate 检查：只处理 Agent 不能自行决策的问题</td><td>产品product 修订稿 → 产品product 定稿</td></tr><tr><td>7</td><td>技术 Agent 和数据 Agent 基于产品定稿并行产出</td><td>产品product 定稿 → 技术tech + 数据data</td></tr><tr><td>8</td><td>评测eval Agent 在 AI 需求中生成评测eval</td><td>技术tech + 数据data → 评测eval</td></tr><tr><td>9</td><td>测试test Agent 和运维ops Agent 生成质量与上线视角</td><td>前序视角 → 测试test + 运维ops</td></tr><tr><td>10</td><td>完整包 final gate：没有真实抉择自动归档，有真实抉择先返修</td><td>完整包 → 最终交接归档</td></tr></tbody></table></column></grid>

<whiteboard token="Vxt6wNBjNhvMuAb9CwycleJ1nDf"></whiteboard>

<grid>
<column width-ratio="0.333189">
![图片展示 addCriterion](https://feishu.cn/file/YfTub5bAhoV6nkxHhr1chjGpnsg)
</column>
<column width-ratio="0.333406">
![图片展示了多视图智能体生成项目spec的界面。左侧为项目导航栏，右侧是生成项目spec的界面。界面中显示了多视图智能体的描述、目标、任务、输入、输出等信息，还列出了相关文件，如多视图智能体使用说明书、多视图智能体项目spec等。界面底部有2个生成任务，分别是Chandrasekhar（worker）已完成和Goal（worker）已完成，均处于打开状态。该图片与文档中介绍多视图智能体自动化生成spec的内容相关，展示了生成项目spec的具体界面情况。](https://feishu.cn/file/LRuzbxDStobWfpxPNBfcdtHdnCg)
</column>
<column width-ratio="0.333406">
![图片展示了Multiview - spec使用说明书中的“生成流程”部分。左侧为多维视图界面，显示“multiview - spec - v1”项目，有“生成流程”“生成流程示例”等选项。中间是生成流程示例，包含“生成流程”“生成流程示例”“生成流程示例 - 1”等内容。右侧是“产品产品初稿待确认”界面，有“确认方式”“影响范围”“待确认事项”等选项，还显示了“确认通过”“不通过，按反馈修改”等确认方式。该图片与文档中介绍Multiview - spec使用流程的内容相关，直观呈现了生成流程示例及确认环节。](https://feishu.cn/file/Tyk4b0qNqo16PKxuZsKcAxNonzd)
</column>
</grid>

## 2. 存放位置和仓库联动方式

<callout emoji="💡">
**存放原则**：`multiview-spec` 跟业务代码仓库一起走。它只维护共用规范和过程 Spec，**最终交接归档** 不在这个文件夹里维护。
</callout>

推荐目录：

```text
your-code-repo/
├── app/ 或 src/                  # 业务代码，由业务仓库维护
├── 交接归档/                     # 最终交接归档，由业务仓库维护
└── multiview-spec/               # 多视角 Spec 工具目录，只维护规范和过程文件
```

| **对象** | **推荐位置** | **作用** |
|-|-|-|
| **业务代码** | 业务仓库原有目录，例如 `app/`、`src/`、`server/`、`client/` | 技术tech 读取现有模块、接口、组件和约束，判断能否复用 |
| **业务文档** | 业务仓库 `docs/` 或飞书链接 | 产品product、数据data、测试test 读取上下文、目标、历史决策 |
| **共用规范** | `multiview-spec/spec-system/` | 所有 Agent 每次执行前重新读取，不需要重新下载 skill |
| **过程 Spec** | `multiview-spec/需求过程/<run-id>/` | 保存本次孵化需求的生成、审阅、返修过程；最终归档后自动删除，目录为空时也会被清理 |
| **最终交接归档** | 业务仓库根目录 `交接归档/` | 最终 gate 通过后的权威交接物，研发交接和历史追溯以这里为准 |
| **可选交接协议** | 业务仓库里的 `handoff-protocol/` | 如果项目有该协议，最终交接归档可继续映射到 project/module/page/change |

> 如果项目没有 `handoff-protocol/`，也可以只使用业务仓库根目录的 `交接归档/`。

## 3. 如何和仓库一起使用

<callout emoji="💡">
**使用方式**：代码小白只需要用中文告诉 AI 要做什么。资深程序员可以直接用脚本控制 run、审批、返修和清理。
</callout>

不熟悉代码的人不用记命令。打开 IDE 后，直接对 AI 说“请帮我启用当前仓库里的多视角 Spec skill”，AI 应该找到 `multiview-spec/skill`，把它软链到 IDE 的 skills 目录，并提示重新打开 IDE 会话。

要生成新需求时，直接说“使用多视角 Spec，帮我为这个需求生成方案”，后面粘贴需求内容即可。AI 会读取仓库规范，创建过程 run，再按多视角流程推进。如果需求来自飞书，就把飞书链接一起给 AI，AI 应该用飞书 CLI 读取原文，把需求写入 `request.md`，再启动多视角流程。

如果过程 run 还没归档，生成后要调整时可以直接告诉 AI 哪些地方要改，例如“这个 Spec 里技术方案和埋点要调整”，AI 应该调用 `revise`，只重跑受影响视角和依赖链路。如果最终 gate 已经通过，过程 run 会被自动删除；后续继续修改同一个功能时，AI 必须读取业务仓库根目录 `交接归档/` 里的当前有效交接文档，再启动新的 run。

熟悉命令行的人可以直接使用脚本控制流程。`start` 用来创建新需求 run，`queue-gate` 用来检查当前 gate 是否存在真实抉择，`revise` 用来按反馈返修。只有 `review.html` 明确给出人工抉择内容时，才需要使用页面复制出的命令或反馈。

启用 Codex skill：

```bash
bash multiview-spec/scripts/install-codex-skill.sh
```

如果当前就在 `multiview-spec` 目录内：

```bash
bash scripts/install-codex-skill.sh
```

创建过程 run：

```bash
./skill/scripts/run-multiview-spec.sh start \
  --title "AI 学习规划" \
  --request-text "需要一个 AI 学习规划能力，包含产品product、技术tech、数据data、评测eval、测试test、运维ops"
```

查看过程 run 和业务仓库根目录的交接归档：

```bash
./skill/scripts/run-multiview-spec.sh list --kind all
```

处理人工抉择：

如果系统生成 `review.html`，打开页面后只处理页面列出的问题。每个问题都必须先选一个方案，或选择“这些选项都不对”并填写新方案。选完后点击复制图标，把复制内容发给 AI；没有真实抉择时不会要求确认。

最终 gate：

完整包完成后由 orchestrator 调用 `queue-gate --gate final`。没有真实抉择时会自动通过并归档；如果生成 `review.html`，按页面选择方案并复制给 AI 返修。

返修受影响视角：

```bash
./skill/scripts/run-multiview-spec.sh revise \
  --run-id <run-id> \
  --scope tech,data \
  --feedback-text "接口命名和埋点口径要一起调整"
```

> `start`、`approve`、`revise` 是脚本参数名。给 AI 的引导语必须优先使用中文。

## 4. 目录结构和文件分类

<callout emoji="💡">
**分类原则**：目录分为长期共用规范和孵化需求过程 Spec。最终交接归档在业务仓库根目录维护。
</callout>

```text
multiview-spec/
├── skill/                        # IDE 入口，只负责触发流程
│   ├── SKILL.md                  # skill 对 Codex 的入口说明
│   └── scripts/                  # skill 调用状态机的脚本
├── spec-system/                  # 共用规范，所有需求复用
│   ├── common/                   # 跨视角公共规范和最终归档约束
│   ├── views/                    # 六个视角规范，每个视角一个文件
│   ├── agents/                   # 各 Agent 的职责和读写边界
│   ├── pipeline/                 # 状态机、视角依赖和人工 gate
│   └── conflicts/                # 跨视角冲突裁决规则
├── 需求过程/                     # 孵化需求过程工作区，每个需求一个 run，归档后自动删除；为空时自动清理
└── scripts/                      # 本地状态机和辅助脚本
```

新需求的过程 run 使用扁平结构：

```text
需求过程/<run-id>/
├── README.md                     # 本次 run 的索引
├── request.md                    # 原始需求
├── state.yaml                    # 状态机
├── review.html                   # 当前人工抉择入口
├── review-product-draft.html     # 产品初稿人工抉择快照
├── review-product.html           # 产品定稿人工抉择快照
├── review-final.html             # 完整包人工抉择快照
├── multiview-spec.md             # 全部视角集中在同一个文档
├── product-challenge.md          # 产品挑战
├── issues.md                     # 冲突记录
├── feedback.md                   # 返修反馈
├── deliveries.yaml               # 角色交付记录
└── spec-package-summary.md       # 最终确认前的完整包摘要，不是后续交接协议文件
```

最终归档目录也保持扁平结构，不再有 `records/` 或 `spec/` 中转层：

```text
交接归档/<handoff-id>/
├── multiview-spec.md             # 最终多视角 Spec
├── spec-package-summary.md       # 完整包摘要
├── issues.md                     # 冲突和一致性结论
├── deliveries.yaml               # 角色交付记录
├── request.md                    # 原始需求
└── meta.yaml                     # 标题、target key、归档元信息
```

<table><colgroup><col/><col/><col/><col/></colgroup><thead><tr><th vertical-align="top"><b>文件类型</b></th><th vertical-align="top"><b>属于哪一类</b></th><th vertical-align="top"><b>是否长期维护</b></th><th vertical-align="top"><b>说明</b></th></tr></thead><tbody><tr><td vertical-align="top"><code>spec-system/common/*.md</code></td><td rowspan="4" vertical-align="top"><b>共用规范</b></td><td rowspan="4" vertical-align="top">是</td><td vertical-align="top">所有视角都必须读取</td></tr><tr><td vertical-align="top"><code>spec-system/views/&lt;role&gt;.md</code></td><td vertical-align="top">合并约束某个视角的写作规则、输出模板和自检标准</td></tr><tr><td vertical-align="top"><code>spec-system/agents/*.md</code></td><td vertical-align="top">约束 Agent 的读写边界</td></tr><tr><td vertical-align="top"><code>spec-system/pipeline/*.yaml</code></td><td vertical-align="top">约束流程顺序和人工 gate</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/request.md</code></td><td rowspan="9" vertical-align="top"><b>孵化需求过程文件</b></td><td rowspan="9" vertical-align="top">否</td><td vertical-align="top">本次需求的原始输入固化；最终归档后自动删除</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/multiview-spec.md</code></td><td vertical-align="top">本次需求的多视角过程 Spec，所有视角集中在同一个文档；归档后复制到最终事实源</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/review.html</code></td><td vertical-align="top">当前人工抉择入口，只包含真正需要拍板的问题；最终归档后自动删除</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/review-*.html</code></td><td vertical-align="top">三个人工抉择点的历史快照；最终归档后自动删除</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/product-challenge.md</code></td><td vertical-align="top">本次需求的产品挑战意见；最终归档后自动删除</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/issues.md</code></td><td vertical-align="top">本次需求的冲突记录和裁决；归档后复制到最终事实源</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/feedback.md</code></td><td vertical-align="top">本次需求的人工返修意见；最终归档后自动删除</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/deliveries.yaml</code></td><td vertical-align="top">本次需求的角色交付记录；归档后复制到最终事实源</td></tr><tr><td vertical-align="top"><code>需求过程/&lt;run-id&gt;/spec-package-summary.md</code></td><td vertical-align="top">完整包进入最终确认前自动生成的摘要；归档后复制到最终事实源</td></tr><tr><td vertical-align="top">业务仓库根目录 <code>交接归档/</code></td><td vertical-align="top"><b>最终事实源</b></td><td vertical-align="top">是</td><td vertical-align="top">不在 <code>multiview-spec/</code> 内维护</td></tr></tbody></table>

## 5. 需求如何流转成多视角 Spec

<callout emoji="💡">
**流转顺序**：先固化需求，再产出产品product。首次产品product 产出后必须先进入产品初稿 gate，再进入挑战、修订、产品定稿、下游视角、冲突裁决和最终 gate。只有真实抉择才会生成 `review.html`；没有真实抉择时 gate 自动通过。页面会预览要复制给 AI 的内容，并提供复制图标；不能用历史授权或默认同意跳过正在等待人工抉择的 gate。
</callout>

| **步骤** | **动作** | **产物** | **审查方式** |
|-|-|-|-|
| 1 | 创建过程 run | `request.md`、`state.yaml`、`multiview-spec.md` 视角占位章节 | 自动 |
| 2 | 产品product 首次产出 | `multiview-spec.md` 的 `## 产品product` | 自动 |
| 3 | 产品初稿 gate | `review.html` 或自动通过记录 | 有真实抉择才人工抉择 |
| 4 | 产品挑战 | `product-challenge.md` | AI 审查 |
| 5 | 产品修订 | 更新 `## 产品product` | 自动 |
| 6 | 产品定稿 gate | `review.html` 或自动通过记录 | 有真实抉择才人工抉择 |
| 7 | 下游视角产出 | `multiview-spec.md` 中各自章节 | 自动 |
| 8 | 冲突裁决 | `issues.md` | AI 裁决，必要时人类判断 |
| 9 | 完整包一致性验收 | `issues.md` 的 `## 一致性结论` | AI 审查，必须无冲突 |
| 10 | 完整包校验 | 校验结果 | 自动 |
| 11 | 最终 gate | `review.html`、`spec-package-summary.md` 或自动通过记录 | 有真实抉择才人工抉择 |
| 12 | 归档 | 业务仓库根目录 `交接归档/` | 自动 |

每个视角的章节所有权：

| **视角** | **只能写入** | **不能做什么** |
|-|-|-|
| **产品product** | `multiview-spec.md` 的 `## 产品product` | 不能修改状态机、技术tech、数据data |
| **产品挑战product-challenger** | `product-challenge.md` | 不能直接改产品正文 |
| **技术tech** | `multiview-spec.md` 的 `## 技术tech` | 不能凭空新增架构，不覆盖产品结论 |
| **数据data** | `multiview-spec.md` 的 `## 数据data` | 不能发明技术实现细节 |
| **评测eval** | `multiview-spec.md` 的 `## 评测eval` | 非 AI 需求不能强行生成 |
| **测试test** | `multiview-spec.md` 的 `## 测试test` | 默认不写详细测试用例 |
| **运维ops** | `multiview-spec.md` 的 `## 运维ops` | 不替技术tech 写实现方案 |
| **冲突裁决arbiter** | `issues.md` | 不能直接修改任何视角正文 |

## 6. 如何避免一个 AI 从头写到尾

<callout emoji="💡">
**控制维度**：角色隔离、流程门禁、证据留痕、冲突裁决。任何一类失效，都不能进入下一个人工 gate。
</callout>

### 角色隔离

- 主 Agent 只做编排，不能直接写 `multiview-spec.md` 里的任何视角章节。
- 每个视角 Agent 只能写自己拥有的章节。
- 产品、技术、数据、评测、测试、运维、冲突裁决分别由不同职责完成。

### 流程门禁

- 产品product 首次产出后，必须先进入 `product-draft` gate；没有真实抉择时自动通过，有真实抉择时生成 `review.html`。
- 只有进入 `waiting_human` 的 gate 才需要人工抉择。每个人工抉择点必须使用当前 `review.html` 复制图标生成的内容，不能用“之前都同意”自动批准。
- 需要抉择的问题不会预选方案；选定方案后复制的是返修指令，让对应视角改正文并删除待确认标记。
- 产品定稿 gate 未通过前，下游视角不能开始。
- 完整包 final gate 未通过前，不能生成最终事实源。

### 证据留痕

- 每个视角完成后都要记录交付来源。
- 过程 Spec 只在 `需求过程/<run-id>/` 里临时存在，最终归档后自动删除。
- 最终交接归档只写入业务仓库根目录，不放在 `multiview-spec/` 内。

### 冲突裁决

- 跨视角冲突必须写入 `issues.md`。
- `arbiter` 只能记录和裁决冲突，不能直接改视角正文。
- 裁决后必须由对应 owner agent 回写自己的视角章节。
- 完整包进入最终 gate 前，arbiter 必须做一次整体一致性验收。
- `issues.md` 的 `## 一致性结论` 必须写明 `可实现完整功能：是`、`未解决冲突：0` 和 `阻塞待确认：0`。
- 如果任一视角之间仍有冲突、阻塞待确认或占位内容，最终 gate 会失败，不能进入人工抉择。

## 7. 审查入口和人工抉择重点

<callout emoji="💡">
**审查入口**：AI 审查、工具校验、人类审查三类入口共同控制质量。所有需要人介入的澄清都按同一规则处理，不只产品环节。人类只处理真正需要拍板的抉择；没有抉择点时，状态机自动放行。
</callout>

| **审查入口** | **谁审** | **触发时机** | **审查重点** | **是否阻断** |
|-|-|-|-|-|
| 产品初稿 gate | 人类或自动 | 产品product 首次产出后 | 只处理两个以上可行方案且没有明显最优解的问题；没有真实抉择时自动通过 | 阻断产品挑战 |
| 产品挑战 | AI | 产品初稿后 | 需求点、交互、预期用户结果、异常体验、下游可执行性、产品是否越界 | 不直接放行 |
| 产品定稿 gate | 人类或自动 | 产品挑战和修订后 | 只处理未能由 Agent 自行决策的产品抉择；没有真实抉择时自动通过 | 阻断下游 |
| 冲突裁决 | AI 或人类 | 视角之间出现不一致时 | 冲突是否记录、优先级是否合理、是否需要人判断 | 视冲突级别决定 |
| 完整包一致性验收 | AI | 全部视角完成后、最终 gate 前 | 是否能合成一个可实现、可测试、可上线、可回滚的完整功能；是否满足 `未解决冲突：0`、`视角越界：0`、`清理状态：已完成` | 阻断最终 gate |
| 状态机校验 | 工具 | 每个人工 gate 前 | 依赖、交付记录、占位内容、开放冲突、一致性结论是否满足要求 | 阻断 gate |
| 最终 gate | 人类或自动 | 全部视角完成且一致性通过后 | 只处理最终归档前仍需人拍板的抉择；没有真实抉择时自动归档 | 阻断归档 |

## 8. 规范和审查流程如何维护

<callout emoji="💡">
**维护入口**：要改输出质量，优先改 `spec-system/`。不要把规则只写进 skill 本体，也不要单独维护外部参考清单。
</callout>

| **想改什么** | **修改位置** | **生效方式** |
|-|-|-|
| 所有视角共同标准 | `spec-system/common/spec-writing-standard.md` | 下次使用 skill 时所有 Agent 重新读取 |
| 某个视角怎么写 | `spec-system/views/<role>.md` | 影响对应视角 Agent 的写作边界、输出结构和内部检查规则 |
| Agent 职责边界 | `spec-system/agents/<agent>.md` | 影响哪个 Agent 能读写哪些文件 |
| 流程顺序和依赖 | `spec-system/pipeline/multiview-spec.yaml` | 影响视角启动顺序和人工 gate |
| 冲突优先级 | `spec-system/conflicts/resolution-policy.md` | 影响 `arbiter` 如何写入 `issues.md` 并裁决冲突 |
| 最终归档约束 | `spec-system/common/archive-contract.md` | 影响最终交接物如何写入业务仓库 |

维护规则：

- **数据指标与埋点**：最终 Spec 必须包含北极星指标、过程指标、护栏指标和埋点事件表；北极星要表达用户持续价值或使用意愿，链路成功率只能作为过程指标。
- **指标口径**：过程指标要写清分子、分母、去重口径和判断窗口，并能追溯到具体埋点事件与参数条件。
- **护栏指标**：只保留 1-3 个会阻断发布或造成明显业务误判的风险，不为了全面堆列表。
- **埋点事件表**：事件表要拆出新增/复用、事件名、触发位置、触发动作或接口、关键属性与取值、关联指标；关键属性必须一行一个 `属性=具体取值或取值枚举`，不用顿号或逗号揉在一起。
- **视角命名**：写视角名称时用 `产品product` 这种短名称，不新增中英文名称列。
- **飞书表头样式**：表头必须是灰色底，文字必须是黑色加粗。
- **表格标题精炼**：表格标题和表头只写短词或短句，不写长段说明，也不插入高亮块。补充解释放在表格正文或表格外的普通正文里。
- **飞书表格宽度**：表格总宽度必须等于列宽总和。
- **合并重复单元格**：同一列连续出现相同内容时，必须合并单元格。合并后只保留一次文字，清空被合并区域内的重复文字。
- **浅色高亮块**：高亮块只能用浅色填充，不能使用深色填充。如果有描边，描边必须和填充色属于同一色系。
- **并列表达**：用顿号或列表表达并列项，不用分号串长句。
- **重点加粗**：只加粗真正重要的信息。
- **局部加粗**：不能整段加粗，只加粗关键词、结论词、风险词或门禁词。

> 次要说明使用引用块，不放进正文主线。

- **中文引导**：面向用户的引导语使用中文。
- **中文正文**：所有 Spec 正文使用中文。只有字段名、API、事件名、代码标识等必须进入系统的名称可以保留英文。
- **人工抉择**：只有真实抉择才会生成页面。用户选择方案后复制给 AI，AI 按选择返修并重新进入 gate；没有真实抉择时不需要用户确认。
- 如果要沉淀外部经验，必须改写进共用规范或视角规则，不能新增单独的外部参考文档。