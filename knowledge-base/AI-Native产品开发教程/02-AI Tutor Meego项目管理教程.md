# 【教程】AI Tutor Meego项目管理教程

本文档是 AI Tutor 项目管理教程，也是其他项目接入 Meego + GitLab 自动同步的参考模板。日常协同看 Meego，上线前事实核查看 Handoff Review，需求正文和归档事实以 KBS 为准。

## 当前结论

AI Tutor 项目用 Meego 做项目管理主入口，用 GitLab 三仓做执行事实源，用 KBS / Handoff 做需求正文事实源。

固定三仓：

```text
tutor/ai-tutor-kbs              # 需求包、Handoff、技术方案、测试用例、验证事实
tutor/ai-tutor                  # App / server / agent 代码仓
tutor/ai-teacher-agentscope     # 讲题编排服务代码仓
```

当前最重要的口径：

- 需求 ID 使用 KBS `requirements/<requirement_id>/` 目录名，格式是 `YYYYMMDD-标题`，不是 `20YYYYMMDD-标题`。
- GitLab 分支、commit、MR 保留原始 `requirement_id`，不要求研发写 Meego 的 `m-xxx`。
- Meego 官方 GitLab 插件需要的 `m-<工作项ID>` 由 handoff-mcp 服务端 webhook 中继自动补充。
- Meego OpenAPI 必须通过已发布插件授权进入；没有独立绕过插件的 Meego 平台 API。
- AI Tutor 的 `需求状态` 是 Meego 工作流节点，不是普通字段；不能通过 `requirement_status` 字段更新。
- GitLab 任一远端事件触发后，同步服务都要对需求仓和代码仓做整仓轻量刷新，不只更新本次变动命中的一个需求。
- Meego 表格只展示项目管理需要的信息，GitLab 同步字段由系统写入并锁定人工编辑。
- 新需求必须扫描 GitLab 远端所有有效分支，不能只扫 `develop`。
- 新建 Meego 需求必须以 KBS 远端真实 `requirements/<requirement_id>/` 目录为准；分支名只能作为关联线索，不能因为分支名多了后缀就派生出一个新需求。
- 合入 `develop` 前，需求文档和需求原型链接指向远端需求分支；合入后切到 `develop`。
- `需求人员` 只取 KBS 需求包创建锚点文件的首次历史作者，不取后续测试用例、审计、验证或最新动态作者。

## 1. 怎么管理项目

### 1.1 系统分工

```text
KBS / 需求仓 = 需求正文、技术方案、测试用例、验证材料
GitLab = branch、commit、MR、pipeline 的执行事实源
Meego = 项目管理主入口、需求看板、缺陷、状态、人员、协同
飞书机器人 = 同步失败、阻断上线、关键状态变化提醒
Handoff Review / Preview = 需求文档和需求原型的固定访问入口
```

核心原则：

- 需求事实来自 GitLab 远端，不靠人手动维护 Meego 表格。
- Meego 展示项目状态，但不作为代码事实源。
- 需求 ID 是跨系统唯一主键，不能用 Meego 工作项 ID 代替。
- Meego OpenAPI 通过插件授权进入；插件必须创建、发布并授权后，服务端才能调用 OpenAPI。
- 需求状态优先用 Meego 工作流节点表达，不把 `需求状态` 当普通字段写。
- GitLab 任一远端事件触发后，同步服务应整仓轻量刷新需求状态，不只刷新当前 webhook 命中的需求。
- GitLab 中没有真实需求包或明确需求 ID 的代码变动，不自动生成 Meego 需求。
- KBS 分支名命中需求 ID 但分支树实际指向另一个 canonical `requirements/<requirement_id>/` 目录时，以目录 ID 为准；分支名后缀不允许创建伪需求。
- 缺陷可以人工创建，但修复轨迹仍然由 GitLab 自动回填。

Tutor 当前固定三仓：

```text
tutor/ai-tutor-kbs              # 需求包、Handoff、技术方案、测试用例、验证事实
tutor/ai-tutor                  # App / server / agent 代码仓
tutor/ai-teacher-agentscope     # 讲题编排服务代码仓
```

其他项目照抄时，把三仓替换成自己的项目仓库集合即可；原则是“一个需求仓 + N 个代码仓”。

### 1.2 Meego 对象定义

| Meego 对象 | 含义 | 来源 |
|-|-|-|
| 需求 | 一个真实业务需求，对应一个需求仓里的 `requirements/<requirement_id>/` | GitLab 同步服务自动创建 / 更新 |
| 任务 | 需求下的标准执行检查点，例如方案确认、测试用例确认、提测 | 需求创建后自动生成 |
| 缺陷 | 已发现的问题，需要修复和回归 | 人工创建，GitLab 修复轨迹自动回填 |

缺陷不是测试任务。

```text
测试任务 = 去验证某件事
缺陷 = 验证失败后记录的问题
```

### 1.3 ID 规则

需求 ID 使用需求仓目录名：

```text
requirements/<requirement_id>/
```

新需求建议：

```text
<yyyymmdd>-<short-slug>
```

示例：

```text
20260608-action-review-playback
20260608-sse-board-debug-guard
```

旧需求如果已经使用中文目录名，继续用真实目录名精确匹配，不迁移、不改名。

GitLab 分支、commit、MR 必须包含完整需求 ID：

```text
feat/<requirement_id>
fix/<requirement_id>-<bug_slug>

Requirement ID: <requirement_id>
Bug ID: <bug_id>
Change Type: requirement | bugfix | tech-debt | infra | refactor | chore
Repo Role: kbs | app | agent-service
```

禁止：

- 禁止使用 `m-123` / `f-123` 作为团队需求 ID。
- 禁止使用 Meego 工作项 ID 作为需求 ID。
- 禁止 KBS、GitLab、Meego 三边出现不同需求 ID。
- 禁止把 `feature/20260604-xxx-extra-suffix` 这类分支名后缀当成新的需求 ID；新建工作项只认远端真实 `requirements/<requirement_id>/` 目录。

Meego 官方 GitLab 插件内部仍然需要 `m-<Meego工作项ID>` 才能展示 `GitLab代码分支` 页签。这个 ID 不由人填写，也不写进仓库命名规则；由服务端 GitLab webhook 中继自动完成映射：

```text
GitLab 原始事件包含 <requirement_id>
-> 同步服务查询 Meego Requirement ID 字段
-> 找到对应 Meego 工作项 ID
-> 转发给 Meego 官方 GitLab 插件时补充 m-<工作项ID>
```

### 1.4 需求状态

Meego 需求状态只保留这 5 个：

```text
需求注册
需求评审
需求开发
需求验证
需求上线
```

不在这 5 个里的状态要删除或不展示。

状态由同步服务按 KBS / 代码仓远端快照计算：

| 状态 | 自动化事实源 | 进入条件 |
|-|-|-|
| 需求注册 | KBS / Meego | Meego 已有需求，但 KBS 远端快照还没有足够证据进入后续阶段 |
| 需求评审 | KBS 仓 | 远端存在包含该 `requirement_id` 的需求分支，但 KBS `develop` 还没有该 `requirement_id` |
| 需求开发 | KBS 仓 | KBS `develop` 已出现该 `requirement_id`，说明需求包进入开发基线，但代码落地证据还不完整 |
| 需求验证 | 代码仓 + KBS 文本 | 代码仓分支、当前 webhook、近期 `develop` commit、近期指向 `develop` 的 MR，或 KBS `package_final` 完成态能归因到该需求，说明已开始实际落地但未完成上线 |
| 需求上线 | KBS 仓 | KBS `main/master` 已出现该 `requirement_id`，表示需求包进入 KBS 上线基线；这不是业务代码生产发布证明 |

注意：

- 不能只扫 `develop`。未合入 `develop` 的新需求也必须展示。
- 同步服务必须扫描需求仓远端所有有效分支，并读取 KBS `develop` / `main` 快照；开发到验证阶段再读代码仓。
- 合入 `develop` 前，文档和原型链接指向该需求所在远端分支。
- 合入 `develop` 后，文档和原型链接切到 `develop`。
- 状态只能前进不能后退：旧 feature 分支继续提交时，不能把已验证或已上线需求改回开发。

### 1.4.1 Meego 更新触发时机

Meego 同步不是浏览器打开时刷新，也不是固定定时轮询；它是 GitLab webhook 驱动的准实时更新。只要配置内的需求仓或代码仓有远端事件到达 handoff-mcp 中继，就触发一次同步。

触发源：

| 触发源 | 典型事件 | 自动动作 |
|-|-|-|
| KBS / 需求仓 | push、MR open/update/merge | 识别 `requirement_id`，创建缺失 Meego 需求，刷新需求名称、日期、需求人员、需求文档链接、需求原型、最新动态，并把事件补充 `m-<工作项ID>` 后转发给 Meego 官方插件 |
| 代码仓 | push、MR open/update/merge、pipeline/build success/skipped | 用 branch、MR、commit、当前 webhook 文本识别需求落地证据，刷新最新动态和状态 |
| 任一配置内仓库事件 | 需求仓或代码仓任意有效 webhook | 触发整仓轻量刷新：扫描所有配置的 KBS 需求仓和代码仓，不只刷新当前 webhook 命中的需求 |
| 人工刷新 | 带合法 token 调用同步入口 | 本质上等同触发一次仓库快照刷新，用于部署后修正历史数据 |

整仓轻量刷新会做这些事：

```text
1. 扫描 KBS 远端所有有效需求分支。
2. 扫描 KBS develop 的 requirements 目录。
3. 扫描 KBS main/master 的 requirements 目录。
4. 扫描代码仓远端分支、develop 近期 commit、目标分支为 develop 的近期 MR。
5. 读取 KBS develop 里需求包的完成态文件和需求创建锚点作者。
6. 对 Meego 全量 Requirement ID 重新计算状态和同步字段。
```

不会触发更新的情况：

```text
非配置内 GitLab 项目事件
webhook token 校验失败
GitLab token 缺失导致无法读取远端快照
事件里没有 requirement_id，且无法通过路径、标题、描述、MR 或 commit 内容高置信归因
```

### 1.4.2 状态判定细则

状态按证据最高阶段计算，顺序是：

```text
需求注册 < 需求评审 < 需求开发 < 需求验证 < 需求上线
```

| 状态 | 自动进入条件 | 关键排除 |
|-|-|-|
| 需求注册 | Meego 已有需求，但整仓快照没有在 KBS 需求分支、KBS `develop`、KBS `main/master` 或代码落地证据中找到更高阶段 | 不代表需求被删除，只代表远端快照暂无足够证据 |
| 需求评审 | KBS 远端存在包含该 `requirement_id` 的非 `develop`、非 `main/master` 需求分支，且 KBS `develop` 还没有该需求 | `develop` 一旦出现该需求，评审阶段被开发阶段覆盖 |
| 需求开发 | KBS `develop` 的 `requirements/<requirement_id>` 已存在 | 仅说明需求包进入开发基线，不等于代码已落地 |
| 需求验证 | 已在整仓快照里的需求，命中任一代码落地证据：当前代码 webhook、代码仓分支、代码仓 `develop` 近期 commit、目标分支为 `develop` 的 opened/merged MR；或者 KBS `develop` 的需求包出现 `package_final` 完成态 | pipeline failed 不单独推进主状态；没有高置信归因时不能把代码事件强塞给某个需求 |
| 需求上线 | KBS `main/master` 的 `requirements/<requirement_id>` 已存在 | 这只表示 KBS 需求包进入上线基线，不是业务代码生产发布证明 |

防降级规则：

```text
如果当前 Meego 节点已经高于目标状态，同步服务不会回退节点。
例如已在 需求验证 / 需求上线 时，旧 feature 分支再次 push 不会改回 需求开发。
```

链接规则独立于状态：

```text
未合入 KBS develop -> 需求文档链接和需求原型指向需求分支
已合入 KBS develop -> 需求文档链接和需求原型指向 develop
已进入 KBS main/master -> 状态可到需求上线，但链接仍指向 develop
```

### 1.5 标准需求流转

```text
需求建立 -> 技术方案确认 -> 测试用例确认 -> 研发开工 -> 提测 -> 测试执行 -> 缺陷修复 -> 上线检查 -> 上线归档
```

标准任务：

| 顺序 | 任务 | 完成标准 | 自动化口径 |
|-|-|-|-|
| 1 | 技术方案确认 | 技术方案、影响仓库、风险、回滚方案确认 | 需求仓文档评审通过后自动完成 |
| 2 | 测试用例确认 | 主路径、异常路径、阻断用例确认 | 测试用例文档评审通过后自动完成 |
| 3 | 研发开工 | 至少一个相关代码仓出现需求分支或 MR | GitLab branch / MR 出现后自动完成 |
| 4 | 提测 | 代码仓 MR 合入 develop，且无阻断缺陷 | 代码仓 MR merged develop 后自动完成；pipeline failed 进入风险 |
| 5 | 测试执行 | 按用例验证，失败项已建缺陷 | 人工填写验证结果，系统同步缺陷摘要 |
| 6 | 缺陷修复 | 阻断缺陷都有 Fix MR 且回归通过 | Fix MR / pipeline 自动回填，关闭缺陷由人确认 |
| 7 | 上线检查 | 无阻断缺陷、无 `block:release`、验证结论完整 | 条件满足后自动进入可上线 |

自适应规则：

- 默认每个需求都有 1、2、3、4、5、7。
- 只有发现缺陷时才生成或激活“缺陷修复”。
- 某个代码仓没有 MR 不算异常，除非该需求显式声明这个仓必须交付。
- 不涉及代码的需求必须标明 `Change Type: non-code` 或写例外说明。

## 2. 人要做什么

### 2.1 需求负责人

- 在 KBS 创建真实需求包。
- 写需求概述、技术方案、测试用例。
- 推送远端分支并发起需求仓 MR。
- 确认 Meego 需求已自动创建，补充负责人、排期、验证结论和例外说明。

### 2.2 研发

- 分支名带完整需求 ID。
- commit message 带完整需求 ID 或缺陷 ID。
- MR 使用统一模板，填写 `Requirement ID`、`Change Type`、`Repo Role`、`Self Test`、`Risk`、`Validation`。
- 不手动维护 Meego 里的 MR、commit、branch 状态。

### 2.3 测试 / 验证负责人

- 确认测试用例。
- 提测后执行验证。
- 发现问题建 Meego 缺陷，并关联需求。
- 回归通过后关闭缺陷。

## 3. 系统自动做什么

- GitLab webhook 把 push、MR、pipeline 事件送到 handoff-mcp 中继。
- handoff-mcp 按 `requirement_id` 查 Meego 工作项，并转发给 Meego 官方 GitLab 插件。
- 分支名没有需求 ID 时，handoff-mcp 会继续从 MR 标题、MR 描述、commit message、GitLab push 的 `requirements/<requirement_id>/...` 文件路径兜底识别。
- handoff-mcp 每次收到远端事件都做整仓轻量刷新：KBS 分支决定 `需求评审`，KBS `develop` 决定 `需求开发`，代码仓分支 / 当前 webhook / 近期 `develop` commit / 近期指向 `develop` 的 MR / KBS `package_final` 完成态决定 `需求验证`，KBS `main/master` 决定 `需求上线`。
- push 事件转发给 Meego 官方插件时按 commit 粒度追加 `m-<工作项ID>`：同一批 webhook 识别到多个需求，也只能给命中该 commit 的需求追加对应 token，避免某个需求页签出现整批无关 commit。
- 整仓刷新会把 GitLab API 识别到的 MR 合成 Merge Request Hook 回放给 Meego 官方插件；Branch 不伪造官方 ref，真实分支写入自定义 `GitLab 分支` 字段。
- handoff-mcp 推进 Meego 状态时走工作流节点 `confirm`，不是写 `requirement_status` 字段。
- Meego GitLab 插件展示相关 branch、commit、MR、pipeline。
- 同步服务创建或更新 Meego 需求、标准任务、链接、人员和最新动态。
- `block:release` 和 pipeline failed 进入风险判断。
- Handoff Review 继续按 KBS 需求包聚合三仓事实。

归因优先级：

```text
1. label: requirement:<requirement_id>
2. MR body: Requirement ID
3. branch name 完整包含 requirement_id
4. MR title 完整包含 requirement_id
5. commit message 完整包含 requirement_id
6. 变更文件路径包含 requirements/<requirement_id>/
```

没有真实需求包的代码变动：

- 不创建 Meego 需求。
- 不进入需求视图。
- 可进入仓库动态或风险视图。
- 如果改变产品预期，必须补需求包或关联已有需求。

## 4. 怎么配置关联

### 4.1 Meego 字段

需求工作项至少配置以下字段。

| 字段名 | 类型 | 建议别名 | 来源 | 是否允许人工编辑 |
|-|-|-|-|-|
| 需求名称 | 标题 | 系统字段 | GitLab 需求包标题 / 概述 | 否 |
| Requirement ID | 文本 | `requirement_id` | GitLab 需求包目录名 | 否 |
| 需求日期 | 日期 | `requirement_date` | `requirement_id` 里的日期 | 否 |
| 需求状态 | 工作流节点 | Meego 节点状态 | KBS / 代码仓快照计算后由 OpenAPI 节点确认推进 | 否 |
| 需求文档链接 | 链接 | `requirement_document` | 固定 URL 自动生成 | 否 |
| 需求原型 | 链接 | `requirement_preview` | 固定 URL 自动生成 | 否 |
| GitLab 分支 | 多行文本 | `requirement_git_branch` | 三仓远端分支按 Requirement ID 归因后的摘要 | 否 |
| 需求人员 | 人员 | `requirement_people` | KBS 需求包创建锚点文件的首次 GitLab 作者 | 否 |
| 需求最新动态 | 文本 | `requirement_latest_activity` | 最新 branch / commit / MR 摘要 | 否 |
| 最新动态作者 | 人员 | `requirement_latest_activity_author` | 最新 GitLab 动态作者 | 否 |
| 最新动态更新时间 | 日期时间 | `requirement_latest_activity_updated_at` | 最新 GitLab 动态时间 | 否 |
| GitLab Projects | 文本 | `gitlab_projects` | 关联仓库列表 | 否 |
| GitLab MRs | 链接 / 文本 | `gitlab_mrs` | 关联 MR 列表 | 否 |
| Block Release | 布尔 / 单选 | `block_release` | `block:release` 标签或阻断缺陷 | 否 |
| Validation Result | 文本 / 单选 | `validation_result` | 验证结论 | 可由验证负责人编辑 |

重要配置：

- `需求文档链接` 必须是自定义链接字段，不要用 Meego 系统内置的 `需求文档` 字段。
- 系统内置 `需求文档` 字段无法稳定锁定编辑权限，视图里隐藏。
- `需求状态` 优先使用 Meego 工作流节点，不创建 `requirement_status` 这类普通状态字段。AI Tutor 线上实测普通字段更新会返回 `30009 Field Not Found`。
- Meego 内置 `GitLab代码分支` 页签不是普通字段，只展示官方 GitLab 插件识别到的关联记录。
- 官方页签的数据由服务端 webhook 中继自动补 `m-<工作项ID>` 后写入，不要求仓库 branch / commit / MR 改成 Meego ID。
- 项目表格里的 `GitLab 分支` 使用自定义只读字段，展示跨仓聚合摘要；详情页 `GitLab代码分支` 页签展示官方插件的 MR / commit / branch / pipeline 明细。
- 所有 GitLab 同步字段必须锁定人工编辑权限。
- 锁定权限对所有普通成员生效；只有同步插件 / 同步服务可以通过 OpenAPI 写入。

缺陷媒体预览配置：

| 字段名 | 类型 | 建议别名 | 用途 |
|-|-|-|-|
| 媒体预览 | 附件 / 图片视频 | `media_preview_attachment` | 写入所有可预览图片 / 视频附件，Meego 表格显示缩略图 |
| 媒体预览链接 | URL 链接 | `media_preview_url` | 写第一条可直接打开的图片、视频或动作回放链接，作为兜底打开入口 |
| 证据链接 | 多行文本 / 链接 | `evidence_links` | 保留全部截图、视频、动作回放、日志等原始 URL |

配置要求：

- `MEEGO_DEFECT_MEDIA_ATTACHMENT_FIELD_KEY` 指向 `media_preview_attachment`，该字段必须是附件 / 图片视频类字段。
- `MEEGO_DEFECT_MEDIA_PREVIEW_FIELD_KEY` 指向 `media_preview_url`，该字段必须是 URL 链接字段，只做兜底。
- 同步器会把同一缺陷里的多个图片 / 视频逐个上传到附件字段，不能只保留第一条媒体。
- HTML 动作回放不当作缩略图附件上传，只进入 `媒体预览链接` 和 `证据链接`。

当前 Tutor 已验证的关键字段类型：

```text
需求人员: user
最新动态作者: user
需求文档链接: link
需求原型: link
GitLab 分支: text
需求日期: date
需求最新动态: text
最新动态更新时间: date
```

### 4.2 字段说明和悬浮注释

除 `需求日期`、`需求状态`、链接字段外，GitLab 同步字段都要加字段说明，说明数据口径。

建议说明：

| 字段 | 说明 |
|-|-|
| 需求人员 | KBS 需求包创建锚点文件的首次历史 commit 作者；优先回看 `planning/process/request.md`、`planning/process/requirement-overview.txt`、`planning/requirement-spec.md`、`internal/meta.yaml`、`internal/state.yaml`、`review.html`，只有这些锚点都没有历史时才兜底回看整个 `requirements/<requirement_id>` 目录；后续测试用例、审计、验证、最新动态作者、webhook 触发人或服务账号都不能覆盖；同步服务用 GitLab 作者邮箱动态匹配 Meego 空间人员。 |
| 需求最新动态 | 当前需求最近一次 GitLab 动态，优先取 MR 更新，其次取 commit，再取 branch。 |
| 最新动态作者 | 需求最新 GitLab 动态的作者；同步服务用 GitLab 作者邮箱动态匹配 Meego 空间人员。 |
| 最新动态更新时间 | 需求最新 GitLab 动态发生时间。 |
| GitLab 分支 | 需求仓和代码仓中按 Requirement ID、标题、需求文本、MR 描述或 MR commit 归因到该需求的真实远端分支摘要；Branch 官方页签不通过伪造 ref 回填。 |
| Requirement ID | 需求仓 `requirements/<requirement_id>/` 的目录名，是跨系统唯一主键。 |
| GitLab MRs | 按 Requirement ID 归因到该需求的 MR 集合。 |

### 4.3 Meego 视图

所有需求相关视图都使用同一套表格列。

固定列：

```text
需求名称
需求日期
需求状态
需求文档链接
需求原型
GitLab 分支
需求人员
需求最新动态
最新动态作者
最新动态更新时间
```

可选列只放在详情页，不放表格主视图：

```text
Requirement ID
GitLab Projects
GitLab MRs
Block Release
Validation Result
```

Tutor 当前视图：

| 视图 | 筛选 |
|-|-|
| 需求总览 | 全部需求，按需求状态分组 |
| 开发中需求 | `需求状态 = 需求开发` |
| 需求测试中管理 | `需求状态 = 需求验证` |
| 需求落地前管理 | `需求状态 = 需求注册 / 需求评审 / 需求上线` |

配置空视图时的做法：

```text
1. 如果视图当前没有数据，临时把筛选放宽到有数据的状态。
2. 配置表格列。
3. 恢复原筛选。
4. 保存视图，确认对所有浏览者可见。
```

废弃字段不要出现在任何视图：

```text
需求人员_文本废弃
最新动态作者_文本废弃
当前负责人
优先级
业务线
需求类型
所属空间
提出时间
创建者
系统内置 需求文档
```

### 4.4 文档和原型固定 URL

同步服务必须自动写入 `需求文档链接` 和 `需求原型`，不能人工填。

Preview 固定 URL：

```text
/preview/project/<catalog_id>/branch/<branch>/requirements/<requirement_id>
```

Tutor 示例：

```text
/preview/project/ai-tutor-kbs/branch/<branch>/requirements/<requirement_id>
```

Reviewer 文档固定 URL：

```text
/reviewer/project/<encoded_gitlab_project_path>/branch/<branch>/requirements/<requirement_id>/docs/<doc_key>
```

Tutor 示例：

```text
/reviewer/project/tutor%2Fai-tutor-kbs/branch/<branch>/requirements/<requirement_id>/docs/spec
```

`doc_key` 固定枚举：

```text
spec
evalSpec
tracking
techPlan
testCases
```

表格里的 `需求文档链接` 默认写 `docs/spec`；详情页需要时再展示其他文档入口。

分支选择规则：

```text
如果需求已合入 develop -> branch = develop
如果未合入 develop -> branch = 最新包含该 requirement_id 的远端需求分支
如果需求已进入 main/master -> 只作为需求上线状态证据，文档和原型链接仍保持 develop
如果找不到 explicit branch -> 不写固定链接，并记录同步异常
```

无效链接：

```text
/preview/project/<catalog_id>
/preview/project/<catalog_id>/branch/develop
缺 requirement_id 的 reviewer / preview 地址
```

### 4.5 Meego GitLab 插件

插件用途：

- 授权 Meego 访问 GitLab。
- 授权同步服务调用 Meego OpenAPI。
- 接收 GitLab webhook。
- 在工作项详情展示 MR / commit / branch / pipeline。
- 提供 OpenAPI 入口，让同步服务按远端快照推进工作流节点。

插件不是需求 ID 规则的来源。

原因：

- Meego 原生插件识别 `m-<工作项ID>`。
- 团队仓库继续只使用 KBS `requirement_id`。
- 两者通过服务端 webhook 中继做映射，不让人手动维护两套 ID。

配置方式：

````text
1. Meego 空间安装并授权 GitLab 插件。
2. 在 Meego GitLab 插件里保留工作项 ID 前缀规则：m-[0-9]+。
3. 创建、发布并授权 OpenAPI 插件；同步服务通过插件凭据换取 plugin token。
4. GitLab 三仓 webhook 不直接指向 Meego 官方 URL，而是指向同步服务中继 URL。
5. 同步服务转发事件到 Meego 官方 GitLab 插件 URL。

AI Tutor 当前节点映射：

```text
started  -> 需求注册
state_0  -> 需求评审
doing    -> 需求开发
state_1  -> 需求验证
end      -> 需求上线
````

````

### 4.6 服务端 GitLab webhook 中继

必须部署成共享服务，不能依赖某个人本地脚本。

部署形态：

```text
GitLab Webhook -> 同步服务中继 -> Meego OpenAPI 查询 requirement_id
                              -> 补充 m-<Meego工作项ID>
                              -> Meego 官方 GitLab 插件 webhook
                              -> 飞书机器人
````

中继职责：

- 接收三仓或多仓 GitLab webhook。
- 从 branch / commit / MR 中提取原始 `requirement_id`。
- 如果分支名没有需求 ID，继续从 MR 标题、MR 描述、commit message、GitLab push 的 `requirements/<requirement_id>/...` 文件路径兜底识别。
- 通过 Meego OpenAPI 查询 `Requirement ID` 字段，找到对应工作项 ID。
- 转发给 Meego 官方 GitLab 插件前补充 `m-<工作项ID>`。
- 保持 GitLab 原始分支名、commit message、MR 标题不被改写。
- 对没有需求 ID 的 GitLab 事件直接转发，不扫描 Meego，也不创建伪需求。
- 每次远端事件触发后整仓轻量刷新状态：KBS 分支决定 `需求评审`，KBS `develop` 决定 `需求开发`，代码仓落地证据或 KBS `package_final` 完成态决定 `需求验证`，KBS `main/master` 决定 `需求上线`。
- 推进 Meego `需求状态` 时读取 `current_nodes`，再调用工作流节点 `confirm`；不要把 `需求状态` 当普通字段写。
- Meego API 短暂失败时优先使用服务端缓存，避免 webhook 瞬时失败。
- webhook token 校验失败时拒绝请求。

同步服务职责：

- 接收三仓或多仓 GitLab webhook。
- 定时补偿扫描 GitLab 远端 branch / MR / pipeline。
- 按 Requirement ID 归因需求。
- 创建 / 更新 Meego 需求。
- 创建 / 更新标准任务。
- 回填文档链接、原型链接、人员、最新动态、更新时间。
- 计算需求状态。
- 同步缺陷修复 MR 和阻断状态。
- 写同步失败日志，并用飞书机器人通知。

归因优先级：

```text
1. label: requirement:<requirement_id>
2. MR body: Requirement ID
3. branch name 完整包含 requirement_id
4. MR title 完整包含 requirement_id
5. commit message 完整包含 requirement_id
6. 变更文件路径包含 requirements/<requirement_id>/
```

没有真实需求包的代码变动：

- 不创建 Meego 需求。
- 可以进入仓库动态或技术债视图。
- 高风险时打 `risk:high`。
- 阻断上线时打 `block:release`。

### 4.7 动态人员映射

人员映射不能写死。

每次同步都要动态读取 Meego 字段和当前空间人员，再把 GitLab 作者映射到 Meego 人员字段。

字段发现：

```text
1. 调 Meego 字段元数据接口。
2. 找到 alias = requirement_people 的字段。
3. 确认字段类型是 user。
4. 找到 alias = requirement_latest_activity_author 的字段。
5. 确认字段类型是 user。
```

人员匹配顺序：

```text
1. GitLab author_email 精确匹配 Meego 用户邮箱。
2. GitLab username + 公司邮箱域名推导后匹配。
3. GitLab author_email 的本地部分匹配，例如 `yuanbin@xiaomi.com` 先尝试 `yuanbin`。
4. GitLab display name 匹配 Meego 用户名。
5. 仍然找不到则留空，并记录同步异常。
```

要求：

- 新增 Meego 成员后，不需要改配置；下一次同步自动识别。
- GitLab display name 可能是历史 alias，例如 `eastwing <yuanbin@xiaomi.com>`，不能让 alias 映射覆盖邮箱或邮箱本地部分身份。
- 不允许把人员写成普通文本。
- 不允许出现同一个人有时中文、有时英文的展示问题。
- 写入 Meego 时必须写人员字段支持的用户标识，不能写显示名字符串。

### 4.8 GitLab 配置

每个仓库配置 webhook：

```text
URL: https://<handoff-mcp-host>/integrations/meego/gitlab/webhook
Secret Token: 与 MEEGO_GITLAB_RELAY_SECRET 一致
Push events
Merge request events
Pipeline events
Tag push events（如果上线用 tag）
```

不要把仓库 webhook 直接指向 Meego 官方插件 URL；否则官方插件只能识别仓库里手写的 `m-<工作项ID>`，无法自动识别团队的 `requirement_id`。

推荐 label：

```text
requirement:<requirement_id>
release:<release_key>
repo:kbs
repo:app
repo:agent-service
type:requirement
type:bugfix
type:tech-debt
type:infra
type:refactor
type:chore
block:release
risk:high
```

MR 模板：

```text
Requirement ID:
Bug ID:
KBS Link:
Change Type: requirement | bugfix | tech-debt | infra | refactor | chore
Repo Role: kbs | app | agent-service
Scope:
Self Test:
Risk:
Validation:
```

分支保护：

- `develop` / `main` / `master` / release 分支按项目实际配置。
- 禁止 force push。
- MR 合入前 pipeline 必须通过。
- MR 合入前必须解决 discussion。
- 高风险或阻断需求必须带 `risk:high` / `block:release`。

### 4.9 依赖接口

Meego OpenAPI 需要：

```text
插件 token 获取
字段元数据查询
工作项查询
工作项创建
工作项更新
工作流详情查询
工作流节点完成 / 回滚
人员字段写入
评论读写
视图 / 空间信息读取
```

已验证的关键接口：

```text
POST /open_api/:project_key/work_item/:work_item_type_key/:work_item_id/workflow/query
POST /open_api/:project_key/workflow/:work_item_type_key/:work_item_id/node/:node_id/operate
PUT  /open_api/:project_key/work_item/:work_item_type_key/:work_item_id
```

`PUT work_item` 只写普通字段；状态节点用 `node/:node_id/operate {"action":"confirm"}`。

当前可用文档入口：

```text
OpenAPI 总览: https://project.feishu.cn/b/kahelpcenter/2hsn1l8c/1tew6uao
空间详情: https://project.feishu.cn/b/kahelpcenter/2hsn1l8c/5t7b61ek
工作流详情: https://project.feishu.cn/b/kahelpcenter/2hsn1l8c/5hcmcl04
节点完成 / 回滚: https://project.feishu.cn/b/kahelpcenter/2hsn1l8c/7gix3380
插件管理: https://project.f.mioffice.cn/openapp/list
集成管理: https://project.f.mioffice.cn/ai-tutor/setting/integrationManagement
```

旧文档里出现的 `5ur6k502` 当前会打开“快速了解插件能力”，不要按它找工作流详情。

GitLab API 需要：

```text
Group projects
Repository branches
Merge requests
Commits
Pipelines
Labels
Milestones / Tags
Webhooks
Users
```

飞书机器人需要：

```text
同步失败通知
阻断上线通知
字段映射失败通知
GitLab / Meego 鉴权失败通知
```

鉴权要求：

- Meego 使用企业插件或自研插件授权获取 OpenAPI token。
- GitLab 使用项目或组级 token，只给同步需要的最小权限。
- token 存在服务端密钥系统，不能放本地电脑、脚本或仓库。

Handoff MCP 同步服务需要的环境变量：

不需要为 Meego/GitLab 同步单独开发后端；handoff-mcp 的 HTTP 网关已经内置中继入口：

```text
/integrations/meego/gitlab/webhook
```

三仓 GitLab webhook 指向这个入口，handoff-mcp 再转发到 Meego 官方 GitLab 插件 webhook。

```bash
MEEGO_GITLAB_RELAY_ENABLED=1
MEEGO_GITLAB_RELAY_TARGET_URL=<Meego 官方 GitLab 插件 webhook URL>
MEEGO_GITLAB_RELAY_SECRET=<GitLab webhook secret>
MEEGO_BASE_URL=https://project.f.mioffice.cn
MEEGO_PROJECT_KEY=<meego_project_key>
MEEGO_WORK_ITEM_TYPE_KEYS=story
MEEGO_REQUIREMENT_FIELD_KEYS=requirement_id,Requirement ID,需求ID
MEEGO_REQUIREMENT_PROJECTS=tutor/ai-tutor-kbs
MEEGO_CODE_PROJECTS=tutor/ai-tutor
MEEGO_REPOSITORY_STATUS_REFRESH_ENABLED=1
MEEGO_GITLAB_RELAY_BRANCH_SCAN_LIMIT=200
MEEGO_CODE_COMMIT_SCAN_LIMIT=80
MEEGO_CODE_MR_SCAN_LIMIT=80
MEEGO_CODE_MR_COMMIT_SCAN_LIMIT=20
MEEGO_GITLAB_ASSOCIATION_BACKFILL_ENABLED=1
MEEGO_GITLAB_ASSOCIATION_BACKFILL_TTL_MS=21600000
MEEGO_REQUIREMENT_OWNER_COMMIT_SCAN_LIMIT=200
MEEGO_REQUIREMENT_MATCH_FILE_PATHS=planning/requirement-spec.md,implementation/technical-plan.md,internal/state.yaml
MEEGO_STATUS_SYNC_ENABLED=1
MEEGO_STATUS_SYNC_MODE=node
MEEGO_STATUS_VALUES=registered=需求注册,review=需求评审,development=需求开发,verification=需求验证,online=需求上线
MEEGO_PLUGIN_ID=<Meego OpenAPI plugin id>
MEEGO_PLUGIN_SECRET=<Meego OpenAPI plugin secret>
MEEGO_PLUGIN_TOKEN_TYPE=0
MEEGO_USER_KEY=<Meego service user key>
MEEGO_GITLAB_BASE_URL=https://git.n.xiaomi.com
MEEGO_GITLAB_TOKEN=<GitLab read_api token>
MEEGO_GITLAB_BRANCH_FIELD_KEY=<GitLab 分支字段 key>
```

`MEEGO_STATUS_SYNC_MODE=node` 用于 Meego 工作流节点空间。只有旧空间确实把状态做成普通字段时，才用 `field`；默认 `auto` 用于迁移兼容。

`MEEGO_REQUIREMENT_OWNER_COMMIT_SCAN_LIMIT` 控制需求人员历史回看窗口，服务端会强制保留至少 50 条窗口，避免线上误配过小后把最近维护者当成首次需求包作者。

## 5. 后续怎么使用

### 5.1 新建需求

人做：

```text
1. 在需求仓创建 requirements/<requirement_id>/。
2. 写需求概述、技术方案、测试用例。
3. 推送远端分支。
4. 开需求仓 MR。
```

系统自动做：

```text
1. 扫到远端分支上的新需求包。
2. 创建或更新 Meego 需求。
3. 写需求名称、需求日期、需求人员、需求文档链接、需求原型；需求人员只取 KBS 需求包创建锚点文件的首次历史作者。
4. 根据当前 GitLab 状态计算需求状态。
5. 创建标准任务。
```

### 5.2 开发需求

人做：

```text
1. 创建 feat/<requirement_id> 分支。
2. commit message 带完整 requirement_id。
3. MR 标题或描述带完整 Requirement ID。
4. MR 模板字段填完整。
```

系统自动做：

```text
1. 归因 branch / commit / MR 到 Meego 需求。
2. 更新需求最新动态、最新动态作者、最新动态更新时间。
3. 回填 GitLab MRs。
4. KBS `develop` 出现该需求后进入需求开发。
5. 代码仓分支、当前 webhook、近期 `develop` commit、近期指向 `develop` 的 MR 或 KBS `package_final` 完成态能归因到该需求后进入需求验证；pipeline failed 只进入风险，不单独决定主状态。
```

### 5.3 查看文档和原型

Meego 表格里直接点：

```text
需求文档链接 -> Reviewer docs/spec
需求原型 -> Preview requirement page
```

链接跟随 GitLab 状态自动变化：

```text
合入 develop 前 -> 远端需求分支
合入 develop 后 -> develop
进入 main/master 后 -> 状态可到需求上线，链接仍打开 develop 中该需求的 Reviewer / Preview
```

不能手动维护链接。

### 5.4 处理缺陷

人做：

```text
1. 在 Meego 创建缺陷。
2. 关联 Requirement ID。
3. 写复现步骤、期望结果、实际结果、严重等级、是否阻断上线。
4. 修复 MR 填 Bug ID、Requirement ID、Change Type: bugfix。
5. 回归通过后关闭缺陷。
```

系统自动做：

```text
1. 把 Fix MR / pipeline 回填到缺陷。
2. 同步 block:release 到需求阻断状态。
3. 阻断缺陷关闭前，不允许需求进入上线状态。
```

### 5.5 非需求代码变动

允许存在非需求代码变动：

```text
type:tech-debt
type:infra
type:refactor
type:chore
```

规则：

- 不创建 Meego 需求。
- 不进入需求视图。
- 可进入仓库动态或风险视图。
- 如果改变产品预期，必须补需求包或关联已有需求。

### 5.6 上线检查

上线必须满足：

```text
需求包存在且已评审
相关 MR 已合入目标基线
pipeline 通过
无 block:release
阻断缺陷清零
验证结论完整
需求文档和需求原型链接有效
```

日常协同看 Meego；上线前事实核查看 Handoff Review。

## 6. 其他项目接入步骤

### Step 1：确定项目事实源

填写项目配置：

```yaml
project:
  meego_space: <space_key>
  gitlab_host: <gitlab_host>
  gitlab_group: <group_path>
  requirement_repo:
    project_path: <group>/<requirement_repo>
    catalog_id: <preview_catalog_id>
    default_branch: develop
  code_repositories:
    - project_path: <group>/<repo_a>
      repo_role: app
    - project_path: <group>/<repo_b>
      repo_role: service
```

### Step 2：配置 Meego

```text
1. 创建需求工作项类型。
2. 创建缺陷工作项类型。
3. 创建本文档 4.1 中的字段。
4. 把需求状态限制为：需求注册、需求评审、需求开发、需求验证、需求上线。
5. 锁定所有 GitLab 同步字段的人工编辑权限。
6. 隐藏系统内置“需求文档”和所有废弃字段。
7. 配置所有需求视图的固定列。
8. 安装并授权 Meego GitLab 插件，保留 m-[0-9]+ 工作项识别规则。
9. 发布并授权 OpenAPI 插件；状态节点由同步服务调用工作流 OpenAPI 推进。
```

### Step 3：配置 GitLab

```text
1. 给每个仓库配置 webhook，URL 指向同步服务中继。
2. 配置组级 / 仓库级 label。
3. 配置 MR 模板。
4. 配置分支保护。
5. 配置同步服务读取 GitLab API 的 token。
```

### Step 4：部署同步服务

同步服务最少需要这些配置：

```bash
MEEGO_GITLAB_RELAY_ENABLED=1
MEEGO_GITLAB_RELAY_TARGET_URL=<Meego 官方 GitLab 插件 webhook URL>
MEEGO_GITLAB_RELAY_SECRET=<GitLab webhook secret>
MEEGO_BASE_URL=https://project.f.mioffice.cn
MEEGO_PROJECT_KEY=<meego_project_key>
MEEGO_WORK_ITEM_TYPE_KEYS=story
MEEGO_REQUIREMENT_FIELD_KEYS=requirement_id,Requirement ID,需求ID
MEEGO_REQUIREMENT_PROJECTS=tutor/ai-tutor-kbs
MEEGO_CODE_PROJECTS=tutor/ai-tutor
MEEGO_REPOSITORY_STATUS_REFRESH_ENABLED=1
MEEGO_GITLAB_RELAY_BRANCH_SCAN_LIMIT=200
MEEGO_CODE_COMMIT_SCAN_LIMIT=80
MEEGO_CODE_MR_SCAN_LIMIT=80
MEEGO_CODE_MR_COMMIT_SCAN_LIMIT=20
MEEGO_GITLAB_ASSOCIATION_BACKFILL_ENABLED=1
MEEGO_GITLAB_ASSOCIATION_BACKFILL_TTL_MS=21600000
MEEGO_STATUS_SYNC_ENABLED=1
MEEGO_STATUS_SYNC_MODE=node
MEEGO_STATUS_VALUES=registered=需求注册,review=需求评审,development=需求开发,verification=需求验证,online=需求上线
MEEGO_PLUGIN_ID=<Meego OpenAPI plugin id>
MEEGO_PLUGIN_SECRET=<Meego OpenAPI plugin secret>
MEEGO_USER_KEY=<Meego service user key>
MEEGO_GITLAB_TOKEN=<GitLab read_api token>
MEEGO_KBS_BASE_URL=<KBS pages base URL>
MEEGO_KBS_LINK_FIELD_KEY=<需求文档链接字段 key>
MEEGO_REQUIREMENT_PREVIEW_FIELD_KEY=<需求原型字段 key>
MEEGO_GITLAB_BRANCH_FIELD_KEY=<GitLab 分支字段 key>
```

AI Tutor 当前已验证字段配置：

```bash
MEEGO_KBS_BASE_URL=http://staging-handoff.search.miui.srv
MEEGO_KBS_LINK_FIELD_KEY=field_qjt8gr,requirement_document
MEEGO_REQUIREMENT_PREVIEW_FIELD_KEY=field_fc8ae7,requirement_preview
```

注意：`requirement_document` 和 `requirement_preview` 只是语义别名。AI Tutor 线上 OpenAPI 写入必须把真实 Meego 字段 key 放在第一位，否则会返回 Field Not Found，导致对应链接无法刷新。

### Step 5：验收

必须通过这些用例：

| 用例 | 期望 |
|-|-|
| 新需求只在远端分支，未合入 develop | Meego 出现需求，链接指向远端分支 |
| 需求合入 develop | Meego 文档 / 原型链接切到 develop |
| 代码仓新建需求 branch 或 KBS `package_final` 完成态 | Meego 状态进入需求验证，详情页 `GitLab代码分支` 页签展示 branch / commit / MR；只有 KBS 完成态时不伪造代码动态 |
| 代码仓 MR merged develop | Meego 保持 / 进入需求验证，并刷新最新动态 |
| MR 带 `block:release` | Meego 显示阻断上线 |
| GitLab 作者是新加入 Meego 的人 | 人员字段自动显示 Meego 人员头像和姓名 |
| GitLab 作者无法匹配 | 人员字段留空，飞书机器人提示映射失败 |
| 非需求 MR | 不创建 Meego 需求 |
| 人工尝试编辑 GitLab 同步字段 | 普通成员不能编辑 |
| 缺陷关联需求并有 Fix MR | 缺陷展示修复 MR，需求阻断状态可计算 |

## 7. Tutor 当前配置摘要

Tutor 当前项目配置：

```text
Meego 空间: AI Tutor
GitLab group: tutor
需求仓: tutor/ai-tutor-kbs
代码仓: tutor/ai-tutor
代码仓: tutor/ai-teacher-agentscope
Preview catalog id: ai-tutor-kbs
Reviewer project path: tutor%2Fai-tutor-kbs
默认开发基线: develop
```

Tutor 当前 Meego 固定视图：

```text
需求总览
开发中需求
需求测试中管理
需求落地前管理
```

Tutor 当前固定表格列：

```text
需求名称
需求日期
需求状态
需求文档链接
需求原型
GitLab 分支
需求人员
需求最新动态
最新动态作者
最新动态更新时间
```

Tutor 已确认的关键口径：

- `需求文档链接` 是自定义 link 字段，不用系统内置 `需求文档`。
- `需求文档链接` 当前字段 key 是 `field_qjt8gr`；`需求原型` 当前字段 key 是 `field_fc8ae7`。
- `需求人员` 和 `最新动态作者` 是 Meego user 字段。
- `需求人员` 锚定 KBS 需求包创建文件的首次历史作者，不能被后续测试用例、审计、验证或最新动态作者覆盖。
- 人员映射动态读取 Meego 当前空间人员，不维护固定名单。
- 新需求扫描 GitLab 远端所有有效分支，不只扫 `develop`。
- 合入 `develop` 前链接指向远端需求分支；合入后链接指向 `develop`。
- GitLab 同步字段对普通成员只读，由同步服务写入。
- GitLab 仓库继续写 KBS `requirement_id`，`m-<Meego工作项ID>` 只由服务端 webhook 中继在转发给官方插件时自动补充。