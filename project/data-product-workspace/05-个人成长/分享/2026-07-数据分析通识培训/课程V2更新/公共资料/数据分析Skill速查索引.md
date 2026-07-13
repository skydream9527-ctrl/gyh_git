# 数据分析 Skill 速查索引

> **用途**：本课程涉及的 6 个数据类 Skill 的速查索引。既方便 AI 按需检索调用，也供学员了解"AI 辅助取数分析时，背后能调用哪些工具"。
> **来源目录**：`/Users/mi/Desktop/ice_workbench_new/skills/`
> **维护**：新增 / 变更 skill 时更新本文件。更完整的全量技能库见来源目录的 `INDEX.md`。

---

## 一、速查总表

| Skill | 一句话简介 | 核心入口 | 典型用途 |
|-------|-----------|----------|----------|
| **kyuubi** | Kyuubi 连 Spark SQL 引擎执行查询 | `python3 kyuubi_cli.py "<SQL>"` | 大数据量取数、SQL 验证、数据探查 |
| **sql** | 连小米数据工场（DataWorks）执行 SQL | `python sql_query_tool.py "<SQL>"` | 生成并执行 SQL、多机房取数 |
| **datum-cli** | 数据工场命令行（结构化 JSON 输出） | `datum <命令>` | 查表结构/分区、执行 SQL、任务调度、权限（进阶） |
| **bi** | 小米 BI 平台查询 | `bi_call(tool_name=..., arguments=...)` | 看现成看板/报表、查指标口径、复用报表 SQL |
| **data-platform-mcp** | 数据平台 MCP（指标/维度/表/元数据） | `data_platform_call(tool_name=..., arguments=...)` | 查指标口径、表元数据、**指标一致性检测** |
| **nl-mapping-table-sql** | 映射表驱动的自然语言转 SQL | 参考 `reference/` 映射表配置 | 复杂多表、口径一致的 SQL 生成 |

---

## 二、按用途分组

| 用途 | 用哪个 Skill |
|------|-------------|
| **执行 SQL 取数** | `kyuubi`、`sql`、`datum-cli` |
| **查指标口径 / 元数据** | `bi`、`data-platform-mcp` |
| **AI 把自然语言变成 SQL** | `nl-mapping-table-sql`（生成后交给 kyuubi/sql 执行） |
| **任务调度 / 自动化（进阶）** | `datum-cli` |

> 💡 一条典型的「AI 辅助取数」链路：**查口径（bi / data-platform-mcp）→ 生成 SQL（nl-mapping-table-sql）→ 执行验证（kyuubi / sql）→ 一致性检测（data-platform-mcp）**。

---

## 三、逐个详解

### 1. kyuubi —— SQL 执行引擎（最常用）
- **简介**：通过 Kyuubi JDBC 连接 Spark SQL 引擎执行查询，适合大数据量取数和 SQL 验证。就是课程里第1课申请权限后"在 Kyuubi 查询"的那个。
- **核心功能**：
  - 数据探查：`DESCRIBE 表名`、`SELECT * ... LIMIT 10` 看表结构和样例
  - 指标验证：跑 SQL 看结果是否符合预期（如 DAU 数量级）
  - 数据导出：大结果导出 CSV
- **核心用法**：
  ```bash
  python3 kyuubi_cli.py "SELECT COUNT(DISTINCT did) AS dau FROM <表> WHERE date=20260628 AND is_app_dau_2024=1"
  python3 kyuubi_cli.py "<SQL>" --format csv --output result.csv
  ```
  需配置环境变量 `KYUUBI_HOST/PORT/USER/PASSWORD`。
- **配合**：`nl-mapping-table-sql` / `sql` 生成 SQL 后，用它执行。
- **路径**：`ice_workbench_new/skills/kyuubi/`

### 2. sql —— DataWorks SQL 执行
- **简介**：连接小米数据工场（DataWorks）执行 SQL 并返回结果；模型可根据分析需求自动生成 SQL 再执行。
- **核心功能**：
  - 自动生成 + 执行 SQL
  - 多机房主机自动检测（zjyprc 北京、tjwq 天津、alsgprc 新加坡等）
  - 结果处理：小结果（≤15 行）表格返回；大结果自动存 CSV
- **核心用法**：
  ```bash
  python sql_query_tool.py "SELECT * FROM <表> LIMIT 10"
  python sql_query_tool.py --file query.sql
  python sql_query_tool.py --host zjyprc "<SQL>"
  ```
  需环境变量 `DATAWORKS_TOKEN_ID`。
- **路径**：`ice_workbench_new/skills/sql/`

### 3. datum-cli —— 数据工场命令行（进阶/自动化）
- **简介**：数据工场的命令行工具，帮 AI Agent 与数据工场交互，输出结构化 JSON。能力最全，偏工程和自动化。
- **核心功能**：
  - 数据资产查询：`catalog` `database` `table` `partition` `schema`（查表结构、字段、分区）
  - SQL 查询：`query`（支持 Presto / Spark / Doris）
  - 任务调度 / 运维：`job` `workflow` `dag`（创建/运行任务、看 DAG 状态）
  - 权限管理：`workspace` `token` `permission`
- **核心用法**：
  ```bash
  datum version           # 确认已安装
  datum config current    # 确认认证配置
  datum table ...         # 查表
  datum query ...         # 执行 SQL
  ```
  全局选项：`-o json/table/yaml`、`--dry-run`（破坏性操作前预览）、`-v`（调试）。
- **对新人**：了解即可——知道"取数、调度、自动化任务可以命令行搞定"。
- **路径**：`ice_workbench_new/skills/datum-cli/`

### 4. bi —— BI 平台查询（看现成的、核对口径）
- **简介**：查小米 BI 平台的看板、报表、指标数据，能直接拿现成看板数据、核对官方口径。
- **核心功能**：
  - 看板：`dashboard_list / detail / search`（找看板、看看板下的报表）
  - 报表：`report_detail / report_data / report_sql`（查报表数据、**拿底层 SQL 复用**）
  - 指标：`metric_search / metric_detail / metric_data`（**查指标官方口径定义**）
- **核心用法**：
  ```
  bi_call(tool_name="dashboard_search", arguments={"keyword": "信息流日报"})
  bi_call(tool_name="metric_detail", arguments={"metricId": 678})   # 查口径
  bi_call(tool_name="report_sql", arguments={"reportId": 12345})    # 复用报表SQL
  ```
- **对课程价值**：新人取数前先看有没有现成看板；"我算的和看板对不上"时，用 `metric_detail`/`report_sql` 核对官方口径。
- **路径**：`ice_workbench_new/skills/bi/`

### 5. data-platform-mcp —— 数据平台元数据与口径一致性
- **简介**：通过 `data_platform_call` 调数据平台 MCP 服务，覆盖 8 大模块（指标/维度/数据集/数据表/元数据/业务域/版本/一致性检测）。
- **核心功能**：
  - **指标一致性检测**：`consistency_overview`、`consistency_metric_sql`（检测同一指标在不同表算出来是否一致——直接对应课程"口径"痛点）
  - 指标管理：`metric_list / metric_detail`（查指标口径 caliber）
  - 数据表：`table_detail / table_columns / table_data_preview`（查表元数据、字段、预览）
  - 维度 / 数据集 / 业务域 / 版本管理
- **核心用法**：
  ```
  data_platform_call(tool_name="metric_list", arguments={"keyword": "DAU"})
  data_platform_call(tool_name="table_detail", arguments={"id": 123})
  data_platform_call(tool_name="consistency_overview", arguments={"startDate": 20260601, "endDate": 20260610})
  ```
- **对课程价值**：查指标标准口径、查表元数据、做口径一致性检测——是"指标口径与度量"主题的工具支撑。
- **路径**：`ice_workbench_new/skills/data-platform-mcp/`

### 6. nl-mapping-table-sql —— 映射表驱动的 AI 转 SQL
- **简介**：把「指标口径、维度定义、表结构」沉淀成**配置化映射表**，AI 依据映射表把自然语言问题转成口径一致的 SQL。核心解决 AI"幻觉字段、口径不一致"。
- **核心功能**：
  - 指标映射：`"CTR" → SUM(click_cnt)/SUM(expos_cnt)`
  - 维度映射：`"渠道" → channel 字段`
  - 表映射：`"信息流" → label_di 表`
  - 工作流：理解意图 → 查映射表 → 生成 SQL → 口径校验
- **核心用法**：加载 `reference/` 下的映射表配置，按映射表口径拼装 SQL（不自行发挥），生成后交 `kyuubi`/`sql` 执行。
- **对课程价值**：正是"AI 写 SQL、人校验"的工程化答案——口径写进映射表，AI 就不容易乱编。适合信息流/推送等复杂多表场景。
- **路径**：`ice_workbench_new/skills/nl-mapping-table-sql/`

---

## 四、与课程的对应关系

| 课程环节 | 可搭配的 Skill |
|----------|---------------|
| 找表 / 看字段 | `data-platform-mcp`（table_detail/columns）、`datum-cli`（table/schema）、`kyuubi`（DESCRIBE） |
| 写 SQL 取数 | `nl-mapping-table-sql`（生成）+ `kyuubi` / `sql`（执行验证） |
| 指标口径与度量（串讲 PPT） | `bi`（metric_detail 查口径）、`data-platform-mcp`（一致性检测） |
| 分析 / 看现成结论 | `bi`（看板报表数据） |
| 自动化（了解级） | `datum-cli`（任务调度 / DAG） |

---

## 五、给新人的一句话
> 这些 skill 的价值，是让"查口径、写 SQL、执行验证"这些活能借助 AI 和工具高效完成。但记住课程反复强调的一点：**工具/AI 负责"写作业"，你负责"检查作业"**——口径对不对、结果合不合理，最终要靠你判断。
