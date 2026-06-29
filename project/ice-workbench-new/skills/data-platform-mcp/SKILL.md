---
name: data-platform-mcp
description: |-
  调用数据平台 MCP 工具，涵盖指标管理、维度管理、数据集管理、数据表管理、元数据配置、业务域管理、版本管理和指标一致性检测。

  触发条件（满足任一激活）：
  1. 提及指标 / 维度 / 数据集 / 数据表 / 业务域 / 元数据 / 版本管理 / 指标一致性；
  2. 提及数据平台 / data platform / 数据资产 / 指标检测 / 一致性检测；
  3. 要求查询/创建/更新指标、维度、数据集、数据表等数据平台资源。
version: 1.0.0
---

# data-platform-mcp Skill

通过内置 `data_platform_call` 工具调用数据平台 MCP 服务，覆盖 8 大模块、35 个工具。

**调用方式**：`data_platform_call(tool_name="<工具名>", arguments={<参数>})`

---

## 工具清单

### 一、指标一致性检测（consistency）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `consistency_overview` | 指标一致性全局概览 | `startDate`, `endDate` (int, yyyyMMdd) |
| `consistency_metric_list` | 分页获取指标一致性结果明细 | `startDate`, `endDate` |
| `consistency_metric_sql` | 获取指标一致性检测 SQL | `metricId` |
| `consistency_instance_list` | 分页获取指标检测实例 | `metricId` |
| `consistency_a1_date_summary` | A1 指标检测日期汇总 | `metricId` |
| `consistency_a1_dimension_detail` | A1 指标公共维度明细 | `metricId` |
| `consistency_distributed_detail` | 分布式指标检测明细 | `metricId` |

**通用可选参数**：`datasetId`, `tableId`, `techOwner`, `serviceStatus`, `myOwned`, `bizDomainId`, `keyword`, `pageNum`, `pageSize`

### 二、指标管理（metric）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `metric_list` | 分页查询指标列表 | — |
| `metric_detail` | 查询指标详情 | `id` |
| `metric_create` | 创建指标 | `name`, `bizDomainId`, `caliber` |
| `metric_update` | 更新指标 | `id` |
| `metric_offline` | 下线指标 | `id` |

**metric_list 可选参数**：`keyword`, `bizDomainId`, `level`, `serviceStatus`, `techOwner`, `pageNum`, `pageSize`

### 三、维度管理（dimension）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `dimension_list` | 分页查询维度列表 | — |
| `dimension_detail` | 查询维度详情 | `id` |
| `dimension_create` | 创建维度 | `name`, `bizDomainId` |
| `dimension_update` | 更新维度 | `id` |

**dimension_list 可选参数**：`keyword`, `bizDomainId`, `pageNum`, `pageSize`

### 四、数据集管理（dataset）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `dataset_list` | 分页查询数据集列表 | — |
| `dataset_detail` | 查询数据集详情 | `id` |
| `dataset_create` | 创建数据集 | `name`, `bizDomainId` |
| `dataset_update` | 更新数据集 | `id` |
| `dataset_fields` | 查询数据集字段列表 | `datasetId` |

**dataset_list 可选参数**：`keyword`, `bizDomainId`, `pageNum`, `pageSize`

### 五、数据表管理（table）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `table_list` | 分页查询数据表列表 | — |
| `table_detail` | 查询数据表详情 | `id` |
| `table_columns` | 查询数据表字段列表 | `tableId` |
| `table_data_preview` | 预览数据表明细 | `id` |
| `table_summary_preview` | 预览数据表统计区间 | `id` |
| `table_gen_newest_name` | 生成虚拟表名称 | `bizDomainId`, `guid` |

**table_list 可选参数**：`keyword`, `bizDomainIds`, `tableTypes`, `updateTypes`, `produceTypes`, `datasourceTypes`, `modelingTypes`, `owners`, `states`, `serviceStatus`, `startTime`, `endTime`, `page`, `pageSize`

### 六、元数据配置（metadata）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `metadata_config_list` | 查询元数据配置列表 | `type` |
| `metadata_config_detail` | 查询元数据配置详情 | `id` |
| `metadata_config_domain_detail` | 查询业务域配置详情 | `bizDomainId` |
| `common_config` | 查询前端公共枚举配置 | — |

**type 枚举**：`BUSINESS_DOMAIN`(业务域)、`DATA_DOMAIN`(数据域)、`BUSINESS_PROCESS`(业务过程)、`DERIVED_TERM`(派生词)、`MEASURE`(度量)、`TIME_PERIOD`(时间周期)、`UNIT`(单位)

### 七、业务域/数据域（domain）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `domain_tree` | 查询业务域/数据域树形结构 | — |

**可选参数**：`type` (1=维度, 2=指标), `bizDomainIds`, `keyword`, `includeBusinessProcess`

### 八、版本管理（version）

| 工具名 | 功能 | 必填参数 |
|--------|------|----------|
| `version_list` | 分页查询对象版本历史 | `objectType`, `objectId` |
| `version_list_all` | 查询对象全部版本历史 | `objectType`, `objectId` |
| `version_has_draft` | 判断对象是否存在待发布草稿 | `objectType`, `objectId` |

---

## 调用示例

### 查询业务域列表

```
data_platform_call(tool_name="metadata_config_list", arguments={"type": "BUSINESS_DOMAIN", "page": 1, "pageSize": 20})
```

### 查询指标列表

```
data_platform_call(tool_name="metric_list", arguments={"keyword": "DAU", "pageSize": 10})
```

### 查询指标一致性概览

```
data_platform_call(tool_name="consistency_overview", arguments={"startDate": 20260601, "endDate": 20260610})
```

### 查询数据表详情

```
data_platform_call(tool_name="table_detail", arguments={"id": 123})
```

### 查询业务域树形结构

```
data_platform_call(tool_name="domain_tree", arguments={"type": 2})
```

---

## 注意事项

- 所有日期参数格式为 `int`，yyyyMMdd 格式（如 `20260601`）
- 分页参数默认 `page=1`, `pageSize=10`
- 服务端点：`https://data-platform-mcp.mib.miui.com/mcp`（内网可达，无需额外鉴权）
- 如遇 `DATA_PLATFORM_UNREACHABLE` 错误，检查内网连接
