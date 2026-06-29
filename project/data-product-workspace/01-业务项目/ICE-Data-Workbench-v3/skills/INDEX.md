# Skills Index

本文件是给 Agent 按需取用的 skill 索引。先读本文件判断是否命中，再调用：

```text
read_skill(skill_id="<skill_id>")
```

如 `SKILL.md` 指向同目录参考资料，再调用：

```text
read_skill(skill_id="<skill_id>", path="references/example.md")
```

任务内只能读取该任务已绑定并快照的 skill；如果 `read_skill` 返回 `SKILL_NOT_FOUND`，请提示用户在工作区右栏 Skills 面板添加。

## 选用原则

- **只读索引，不展开全文**：除非用户需求明确命中某个 skill，不要一次性读取多个 `SKILL.md`。
- **优先专用 skill**：飞书资源用 `feishu`，Kyuubi 查询用 `kyuubi`，DataWorks 查询用 `sql`，映射表 SQL 生成用 `nl-mapping-table-sql`。
- **外部服务需环境**：Mify、DataWorks、Tavily、飞书、datum 等需要对应 token / CLI / 网络权限。若执行失败，直接说明缺少配置，不要编造结果。
- **产物落工作区**：生成报告、SQL、CSV、HTML、PNG 等交付物时，用当前平台工具保存到任务工作区。

## 快速路由

| 用户需求 | 首选 skill | 何时使用 |
|---|---|---|
| 飞书文档、知识库、多维表格、权限、链接读取 | `feishu` | 出现 `*.feishu.cn` 链接或明确要操作飞书资源 |
| 小米 Kyuubi / Iceberg / Spark / Presto SQL | `kyuubi` | 平台内置 Kyuubi 查询场景 |
| DataWorks 数据工场 SQL | `sql` | 需要连接 DataWorks 执行 SQL |
| 内容生态映射表 SQL 生成 | `nl-mapping-table-sql` | 提到 dim / dm / ads / 映射表 / 维度枚举 / 中间表 |
| Python 统计、预测、拟合、变点、图表 | `nl-python` | SQL 之外的统计建模或可视化 |
| 完整数据分析报告 | `data.an` | 从查数到分析、图表、报告的端到端任务 |
| Mify 知识库管理 | `mify-knowledge-base` | 创建/上传/更新/搜索 Mify 知识库 |
| Mify 大模型网关 | `mify-model-gateway` | 查询模型、测试模型、配置 Mify/Claude 接入 |
| 飞书结构化写作 | `feishu-pyramid-writer` | 用金字塔原理写汇报、复盘、方案、分析报告 |
| 文本转图表 PNG | `text2html2png` | 画流程图、架构图、看板、漏斗、时间线等 |
| 每日新闻收集分发 | `daily-news-collector` | 新闻摘要、科技日报、行业 newsletter、定时新闻 |
| 都江堰内容池日报 | `djy-pool-analysis` | 上传 SQL 自动查数生成 AI 日报、内容池日报、CP 字段校验、消费分析、飞书推送 |
| 定时日报发送 | `schedule-send` | 设置日报定时并写入飞书多维表格 |
| datum 数据工场 CLI | `datum-cli` | 数据资产、DAG、Kestra、datum SQL / task 运维 |
| Word 文档 | `docx` | 新建、修改、批注、提取 `.docx` |
| PPT 演示文稿 | `pptx` | 新建、修改、分析 `.pptx` |
| PDF 处理 | `pdf` | 提取、合并、拆分、生成、填写 PDF |

## Skill 详情

### `daily-news-collector`

- **用途**：搭建每日科技新闻收集、筛选与分发流程。
- **触发**：每日新闻、新闻摘要、科技日报、行业新闻收集、自动 newsletter、新闻定时任务。
- **依赖**：通常需要 Tavily API / 可访问新闻源 / 定时任务能力。
- **读取**：`read_skill(skill_id="daily-news-collector")`

### `djy-pool-analysis`

- **用途**：上传 SQL 自动查数生成 AI 日报、都江堰内容池日报、CP 字段校验、DAU 消费分析和创作者审核链路校验。
- **触发**：上传 SQL 跑日报、自动查询生成日报、都江堰日报、内容池校验、CP 脏数据、日报推飞书、消费趋势、签约作者审核链路。
- **依赖**：Kyuubi/DataWorks 查询环境、飞书凭证、HTML/PNG 生成环境；推送前必须确认目标和权限。
- **读取**：`read_skill(skill_id="djy-pool-analysis")`

### `data.an`

- **用途**：基于 Hive / 数据仓库表或本地数据文件完成查数、分析报告、业务分析和可视化。
- **触发**：查数、做数据分析、生成分析报告、分析 CSV/Excel、业务复盘、数据可视化。
- **依赖**：可能依赖 `feishu`、`sql`、Python 分析环境和用户确认关卡。
- **读取**：`read_skill(skill_id="data.an")`

### `datum-cli`

- **用途**：通过 datum CLI 与数据工场交互，覆盖数据资产、SQL 查询、任务调度、DAG 运维、Kestra 开发、权限管理。
- **触发**：数据工场、datum、数据资产、DAG、Kestra、查表、跑 SQL 调度、任务运行、配权限。
- **依赖**：后端/运行环境需安装并登录 `datum` CLI。
- **读取**：`read_skill(skill_id="datum-cli")`

### `docx`

- **用途**：读写、编辑和分析 Microsoft Word `.docx` 文档。
- **触发**：新建 Word、修改 docx、加批注、追踪修订、提取文本/表格。
- **依赖**：Python docx 处理库。
- **读取**：`read_skill(skill_id="docx")`

### `feishu`

- **用途**：通过飞书 CLI 操作文档、知识库、云盘、多维表格、表格、权限、日历、任务。
- **触发**：出现 `*.feishu.cn` 链接；读取/创建/修改飞书资源；飞书多维表格、wiki、docx、drive、sheet、perm。
- **依赖**：运行环境需有 `feishu` CLI 和登录/授权。
- **读取**：`read_skill(skill_id="feishu")`

### `feishu-pyramid-writer`

- **用途**：按金字塔原理结构化撰写飞书文档，支持 SCQA、MECE、结论先行和飞书排版。
- **触发**：写飞书文档、用金字塔原理写、结构化汇报、写复盘、写方案、写分析报告。
- **依赖**：通常与 `feishu` 配合发布。
- **读取**：`read_skill(skill_id="feishu-pyramid-writer")`

### `kyuubi`

- **用途**：通过 Kyuubi SQL 网关在小米内部 Iceberg / Spark / Presto 数据湖跑 SQL。
- **触发**：查一下、执行 SQL、跑查询、Kyuubi、Iceberg 表查询。
- **依赖**：本平台通常优先使用内置 `kyuubi_query` function tool；需要服务端连接上下文可用。
- **读取**：`read_skill(skill_id="kyuubi")`

### `mify-knowledge-base`

- **用途**：管理 Mify 知识库，包括列表、创建、上传文档、更新、搜索和飞书文档集成。
- **触发**：创建 Mify 知识库、上传文档到知识库、搜索知识库、更新知识库文档、同步飞书到 Mify。
- **依赖**：Mify API Key / profile 配置。
- **读取**：`read_skill(skill_id="mify-knowledge-base")`

### `mify-model-gateway`

- **用途**：查询和配置小米 Mify 大模型网关，支持安装 API Key、列出/测试模型、诊断模型 ID、推荐模型、配置 Claude 接入。
- **触发**：公司网关支持什么模型、Mify 有没有某模型、测试模型是否可调、配置 Claude Desktop 接公司网关。
- **依赖**：Mify 网关 token；注意模型调用需使用 `owned_by/id` 格式。
- **读取**：`read_skill(skill_id="mify-model-gateway")`

### `nl-mapping-table-sql`

- **用途**：把自然语言需求转成内容生态数仓 dim / dm / ads 映射表 SQL。
- **触发**：映射表、中间表、维度枚举、dim 表、dm 表、ads 表、关联查询、执行 nl-mapping-table-sql。
- **覆盖**：浏览器主端、浏览器信息流、内容中心；搜索/小说只支持有限 raw 参考，需按技能说明判断。
- **读取**：`read_skill(skill_id="nl-mapping-table-sql")`

### `nl-python`

- **用途**：生成沙箱可执行 Python，做 SQL 之外的统计、预测、拟合、变点检测、STL 分解、bootstrap、可视化。
- **触发**：预测、Prophet、ARIMA、拟合、变点、STL、cohort、KS test、需要 Python 图表。
- **依赖**：平台 `execute_python` function tool。
- **读取**：`read_skill(skill_id="nl-python")`

### `pdf`

- **用途**：PDF 读取、生成、合并、拆分、表单填写、文本/表格抽取。
- **触发**：处理 PDF、填 PDF 表单、抽取 PDF 文本/表格、合并/拆分 PDF。
- **依赖**：PDF 处理库。
- **读取**：`read_skill(skill_id="pdf")`

### `pptx`

- **用途**：创建、编辑、分析 PowerPoint `.pptx`，保留版式、占位符、母版样式。
- **触发**：做 PPT、修改 PPT、批量替换文字/图片、加备注、改版式。
- **依赖**：Python pptx 处理库。
- **读取**：`read_skill(skill_id="pptx")`

### `schedule-send`

- **用途**：设置定时日报发送流程，按指定时间生成项目日报并写入飞书多维表格。
- **触发**：定时发送、定时日报、设置日报定时、自动写入飞书多维表格。
- **注意**：当前说明包含特定 P3升X 项目示例，执行前必须与用户确认目标项目、表格、时间和权限。
- **读取**：`read_skill(skill_id="schedule-send")`

### `sql`

- **用途**：连接小米数据工场 DataWorks 执行 SQL 查询并返回结构化结果。
- **触发**：执行 SQL、查数据工场、查询 Hive 表、跑 SQL、查看表结构。
- **依赖**：`DATAWORKS_TOKEN_ID` 等环境变量；模板见 `scripts/.env.example`。
- **读取**：`read_skill(skill_id="sql")`

### `text2html2png`

- **用途**：把文字描述转换为 HTML 可视化图表，并截图输出 PNG。
- **触发**：画图、做成图、流程图、架构图、数据看板、甘特图、组织架构、转化漏斗、文字可视化。
- **依赖**：Node / Playwright / 技能内截图脚本。
- **读取**：`read_skill(skill_id="text2html2png")`

## 常见组合

- **数据分析报告**：`nl-mapping-table-sql` / `kyuubi` / `nl-python` / `feishu-pyramid-writer` / `feishu`
- **飞书知识沉淀**：`feishu` / `mify-knowledge-base`
- **模型网关排障**：`mify-model-gateway`
- **可视化交付**：`text2html2png` 或 `nl-python`
- **文档交付**：`docx` / `pptx` / `pdf` / `feishu`
