# SQL 查询

通过 Kyuubi HTTP API 执行交互式 SQL 查询，支持 Presto、Spark、Doris、Hologres 等引擎。

## 快速开始

```bash
# 基本查询（需指定 region）
datum query --region zjyprc --engine presto "SELECT 1 AS test"

# 表格输出
datum query --region zjyprc --engine presto -o table "SELECT * FROM catalog.db.table LIMIT 10"

# 指定 catalog 和 schema
datum query --region zjyprc --engine presto --catalog hive_zjyprc_hadoop --schema default \
  "SELECT * FROM my_table LIMIT 10"

# 使用 --sql 参数（适合多行 SQL）
datum query --region zjyprc --engine spark --sql "
  SELECT date, COUNT(*) AS cnt
  FROM catalog.db.events
  WHERE dateint >= 20240101
  GROUP BY date
  ORDER BY date
"
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `SQL`（位置参数）或 `--sql` | 是 | SQL 语句，二选一 |
| `--region` | 是 | Kyuubi 服务区域（见下表） |
| `--engine` | 否 | 引擎类型，默认 auto。可选：presto, spark, doris, hologres |
| `--catalog` | 否 | Catalog 名称。不指定则 SQL 中需用三级表名 |
| `--schema` | 否 | Schema/Database 名称 |
| `--tag` | 否 | 引擎分组标签 |
| `-o table` | 否 | 以 ASCII 表格格式输出结果 |

## 区域列表

| Region | 名称 | 支持引擎 |
|--------|------|---------|
| `zjyprc` | 中国北京 | presto/doris/spark/hologres |
| `tjwq` | 中国天津 | presto/doris/spark/hologres |
| `alsgprc` | 新加坡 | presto/doris/spark/hologres |
| `ksmosprc` | 俄罗斯莫斯科 | presto/doris/spark |
| `nlams` | 荷兰阿姆斯特丹 | presto/spark/doris |
| `nc4prc` | 中国上海 | presto/spark/doris |
| `nc4cloudprc` | 中国上海量产 | presto/spark/doris |
| `azpnprc` | 印度普纳 | presto/spark/doris |
| `tjv1autopilotprc` | 天津智驾合规区 | presto/spark/doris |
| `awsdeprc` | 德国法兰克福 | — |
| `vejhautopilotprc` | 马来西亚自驾合规区 | — |
| `staging` | 测试环境 | presto/doris/spark/hologres |

## 表名规范

- **不指定** `--catalog` 和 `--schema`：SQL 中必须使用三级表名 `{catalog}.{database}.{table}`
- **指定了** `--catalog` 或 `--schema`：SQL 中可用一级或二级表名，会自动补全
- **建议**：始终使用三级表名，避免歧义

```bash
# 三级表名（推荐）
datum query --region zjyprc --engine presto \
  "SELECT * FROM hive_zjyprc_hadoop.default.my_table LIMIT 10"

# 带有点号的表名需用反引号
datum query --region zjyprc --engine presto \
  "SELECT * FROM kudu_zjyprc_hadoop.default.\`migoc.some_table\` LIMIT 10"
```

## 输出格式

**JSON（默认）：**
```json
{"columns":[{"name":"id","type":"integer","comment":""},{"name":"name","type":"varchar","comment":""}],"rows":[[1,"Alice"],[2,"Bob"]]}
```

**Table（`-o table`）：**
```
id | name
---+------
1  | Alice
2  | Bob
(2 rows)
```

## 执行流程

`datum query` 内部执行异步查询流程：
1. **提交** SQL → 获得 queryId
2. **轮询** 状态（PENDING → RUNNING → FINISHED）
3. **拉取** 结果（每批 1000 行，自动翻页）
4. **关闭** 查询释放资源

进度信息输出到 stderr，查询结果输出到 stdout，可安全管道：

```bash
datum query --region zjyprc --engine presto -o table "SELECT ..." 2>/dev/null | head
```
