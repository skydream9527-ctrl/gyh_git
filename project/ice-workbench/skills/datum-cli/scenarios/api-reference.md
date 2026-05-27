# API 接口参考

当 CLI 命令报错（尤其是 `--from-file` 构造 JSON body 时），参考本文档排查。

## 完整 OpenAPI 文档

当本文档中的信息不足以解决问题（如多次调整参数仍报错、遇到本文未覆盖的接口），**拉取完整的 OpenAPI 接口文档**：

```
Fetch https://cnbj1-fds.api.xiaomi.net/datum-cli/OpenAPI.md
```

该文档包含所有接口的完整请求示例、参数表（含必填标记和枚举值）、响应结构。搜索接口路径（如 `/openapi/develop/jobs/op/sparksql`）即可定位到对应接口说明。

## 通用说明

- **认证**: 所有接口 Header 需 `Authorization: workspace-token/1.0 {token}`（CLI 自动处理）
- **jobType 自动注入**: CLI 的 `--type` 参数会自动映射为 API 的 `jobType` 枚举值并注入请求体，用户 JSON 中**无需手动填写** `jobType`
- **错误排查**: 使用 `--dry-run` 查看实际请求，使用 `-v` 查看完整 HTTP 请求/响应

## jobType 枚举映射

CLI `--type` 与 API `jobType` 对应关系（CLI 自动转换）：

| CLI --type | API jobType | 说明 |
|-----------|------------|------|
| spark-sql | SPARK_SQL | SparkSQL 作业 |
| spark-jar | SPARK_ALPHA | Spark Jar 作业 |
| flink-sql | FLINKSQL_STREAMING | FlinkSQL 实时 |
| flink-jar | FLINKJAR_STREAMING | Flink Jar 实时 |
| flink-sql-batch | FLINKSQL_BATCH | FlinkSQL 离线 |
| shell | SHELL | Shell 脚本 |
| hive2doris | HIVE2DORIS | Hive 导入 Doris |
| hdfs-sensor | HDFS_SENSOR | HDFS 感知 |
| hive-sensor | HIVE_SENSOR | Hive 感知 |
| iceberg-sensor | ICEBERG_SENSOR | Iceberg 感知 |
| hdfs-touch | HDFS_TOUCH | HDFS Touch |
| hook | HOOK | Hook 作业 |
| notebook | NOTEBOOK | Notebook |
| cloudml | CLOUD_ML | CloudML |
| data-push | DATA_PUSH | 数据推送 |
| serverlog | SERVLOG2TALOS | 日志采集 |
| copy | TABLE_CP | 离线拷贝 |
| integration | FLINKXQL_STREAMING | 集成作业 |

## 新建 SparkSQL 作业

`POST /openapi/develop/jobs/op/sparksql`

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| jobName | string | 作业名 |
| jobType | string | CLI 自动注入 `SPARK_SQL`，无需手动填 |
| description | string | 作业描述 |
| sql | string | SQL 语句 |
| sparkSQLVersion | string | SparkSQL 版本，如 `spark3` |
| driverMemory | string | Driver 内存，如 `2g` |
| executorMemory | string | Executor 内存，如 `4g` |
| dynamicAllocationEnabled | boolean | 是否动态调度 |
| retryTimes | integer | 重试次数 |
| noticeList | array | 告警配置，可传空数组 `[]` |
| mode | string | 见 mode 枚举 |

### mode 枚举

| 值 | 说明 |
|----|------|
| SAVE | 仅保存 |
| SAVE_AND_RUN | 保存并运行 |
| SAVE_AND_SCHEDULE | 保存并启用调度 |
| WORKFLOW_JOB_SAVE | 工作流作业保存 |

### schedulerType 枚举

| 值 | 说明 |
|----|------|
| scheduler | 调度模式 |
| user | 用户手动触发 |

### 最小示例

```json
{
  "jobName": "my_spark_job",
  "description": "描述",
  "sql": "SELECT 1",
  "sparkSQLVersion": "spark3",
  "driverMemory": "2g",
  "executorMemory": "4g",
  "numExecutors": 2,
  "dynamicAllocationEnabled": false,
  "retryTimes": 0,
  "noticeList": [],
  "mode": "SAVE"
}
```

## 新建 Shell 作业

`POST /openapi/develop/jobs/op/shell`

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| jobName | string | 作业名 |
| jobType | string | CLI 自动注入 `SHELL`，无需手动填 |
| description | string | 描述 |
| command | string | Shell 命令（即 dockerCommand） |
| dockerCommand | string | Docker 执行命令 |
| retryTimes | integer | 重试次数 |
| noticeList | array | 告警配置 |
| mode | string | 见 mode 枚举 |

### 最小示例

```json
{
  "jobName": "my_shell_job",
  "description": "描述",
  "command": "echo hello",
  "dockerCommand": "echo hello",
  "retryTimes": 0,
  "noticeList": [],
  "mode": "SAVE"
}
```

## 新建 FlinkSQL 实时作业

`POST /openapi/develop/jobs/op/flinksql`

### 必填字段

| 字段 | 类型 | 说明 |
|------|------|------|
| jobName | string | 作业名 |
| jobType | string | CLI 自动注入 `FLINKSQL_STREAMING` |
| description | string | 描述 |
| sql | string | FlinkSQL 语句 |
| flinkVersion | string | Flink 版本 |
| parallelism | integer | 并行度 |
| retryTimes | integer | 重试次数 |
| noticeList | array | 告警配置 |
| mode | string | 见 mode 枚举 |

## 新建工作流

`POST /openapi/develop/workflow`

### 请求体

```json
{
  "workflowName": "我的工作流",
  "description": "描述"
}
```

仅需 workflowName 和 description，工作流内的作业通过 `datum job create` 用 `WORKFLOW_JOB_SAVE` mode 添加。

## 创建表

`POST /openapi/resource/table/create`（`datum table create --from-file`）

### 请求体结构

```json
{
  "tableParams": {
    "baseParams": {
      "catalogName": "hive_zjyprc_hadoop",
      "databaseName": "default",
      "tableName": "my_table",
      "description": "表描述",
      "columns": [
        {
          "pos": 0,
          "name": "id",
          "type": "bigint",
          "comment": "主键"
        },
        {
          "pos": 1,
          "name": "name",
          "type": "string",
          "comment": "名称"
        }
      ],
      "ttl": 0,
      "owner": "username"
    },
    "specificParams": {}
  }
}
```

> **提示**: 参考 `datum table get --catalog <c> --db <d> --table <t>` 获取现有表的完整结构作为模板。

## 常见 API 错误排查

| 错误信息 | 原因 | 解决 |
|---------|------|------|
| `不支持的类型: UNKNOWN` | 请求体缺少 jobType | 升级 CLI（已自动注入）或手动在 JSON 中添加 jobType |
| `Cannot deserialize value of type java.lang.Long from String` | 服务端校验失败的嵌套错误，实际是缺少必填字段 | 对照上方必填字段表检查 JSON body |
| `SchedulerType: not one of [scheduler, user]` | schedulerType 值不对 | 只能用 `scheduler` 或 `user` |
| `Validation failed` | 多个必填字段缺失 | 使用 `--dry-run` 检查请求体，对照必填字段补全 |
| `404 Not Found` | API 路径错误或对象不存在 | 检查 --type 拼写，用 list 确认对象存在 |

## 调试技巧

```bash
# 查看实际请求（不执行）
datum job create --type spark-sql --from-file ./spec.json --dry-run

# 查看完整 HTTP 请求/响应
datum job create --type spark-sql --from-file ./spec.json -v

# 参考现有对象结构
datum job get --job-id <id>          # 查看现有作业的完整 JSON 结构
datum table get --catalog <c> --db <d> --table <t>  # 查看现有表结构
datum workflow get --id <id>         # 查看现有工作流结构
```
