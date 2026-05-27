# Search - 底表/宽表埋点指标参考

> **数据源（口径权威）**：[`reference/search/data_tables.yaml`](data_tables.yaml)
> **配套表结构**：[`reference/search/table-schema.md`](table-schema.md)
> **数据层级**：底表/宽表（dwd 层）
> **适用场景**：当中间表（`dm_search_pv_uv_di` / `ads_search_intent_*` / `dm_browser_search_core_indicators_2022_1d`）不支持所需事件维度时回退使用。

## 概述

搜索业务的 dwd 层埋点事件表有两张：

| Key | 真实表名 | 用途 |
|-----|---------|------|
| `search_event` | `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442` | 浏览器打点事件表（含搜索 sug/result/security 等事件） |
| `search_event_global` | `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418` | 全搜端内打点事件表（主动搜索数据来源） |

**UV 标准**：所有 UV 去重统一用顶层列 `distinct_id`，**不要**用 `properties[device_id]`（已在 `app_open` / `search_security` 上验证）。

---

## 指标说明

### 1. 搜索 SUG 页 UV（search_sugpage_uv）

**指标定义**: 搜索建议页面的用户访问数
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
**事件**: `search_sugpage_expose`

```sql
SELECT
    date,
    distinct_id AS did
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date = ${date-1}
    AND event_name = 'search_sugpage_expose'
GROUP BY 1, 2
;
```

---

### 2. 搜索 PV（search_pv） — dwd 442 浏览器打点

**指标定义**: 浏览器打点中的搜索行为次数
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
**事件**: `search_security`（已验证）

```sql
SELECT
    date,
    COUNT(1) AS search_pv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date = ${date-1}
    AND event_name = 'search_security'
GROUP BY 1
;
```

> **建议**：主动搜索类指标优先用 `dm_search_pv_uv_di` 聚合表（已内置渠道归属和版本覆盖率），本表用于需要 query / search_source / search_enter_way 等明细维度的场景。

---

### 3. 全搜端内主动搜索 PV（active_search_pv via dwd 418）

**指标定义**: 全搜端内的主动搜索行为次数（聚合表的兜底口径）
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418`
**事件**: `search`

```sql
SELECT
    date,
    COUNT(1) AS active_search_pv,
    COUNT(DISTINCT distinct_id) AS active_search_uv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418
WHERE
    date = ${date-1}
    AND event_name = 'search'
GROUP BY 1
;
```

---

### 4. 分搜索来源的搜索 PV（search_pv_by_source）

**指标定义**: 按 `properties[search_source]` 拆分的搜索次数（19 种值）
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`

```sql
SELECT
    date,
    properties['search_source'] AS search_source,
    COUNT(1) AS search_pv,
    COUNT(DISTINCT distinct_id) AS search_uv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date = ${date-1}
    AND event_name = 'search_security'
GROUP BY 1, 2
ORDER BY search_pv DESC
;
```

---

### 5. 分搜索引擎的搜索 PV（search_pv_by_engine）

**指标定义**: 按 `properties[searchengine_name]` 拆分（baidu / 360 / douyin）
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`

```sql
SELECT
    date,
    properties['searchengine_name'] AS search_engine,
    COUNT(1) AS search_pv,
    COUNT(DISTINCT distinct_id) AS search_uv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date = ${date-1}
    AND event_name = 'search_security'
GROUP BY 1, 2
ORDER BY search_pv DESC
;
```

---

### 6. 搜索结果页模块点击（search_resultpage_module_click）

**指标定义**: 用户在搜索结果页点击各模块的次数 / 用户数
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
**事件**: `search_resultpage_module_click`

```sql
SELECT
    date,
    COUNT(1) AS click_pv,
    COUNT(DISTINCT distinct_id) AS click_uv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date = ${date-1}
    AND event_name = 'search_resultpage_module_click'
GROUP BY 1
;
```

---

### 7. 搜索 CTR（粗口径，dwd 自查）

**指标定义**: `search_resultpage_module_click` PV / `search_security` PV
**数据源**: `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
**说明**: 严格的 CTR 需要 `search_result` 表（YAML `pending_alignment` 中），此为 dwd 层粗算口径

```sql
SELECT
    s.date,
    s.search_pv,
    c.click_pv,
    c.click_pv * 1.0 / s.search_pv AS ctr
FROM (
    SELECT date, COUNT(1) AS search_pv
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date = ${date-1} AND event_name = 'search_security'
    GROUP BY 1
) s
JOIN (
    SELECT date, COUNT(1) AS click_pv
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date = ${date-1} AND event_name = 'search_resultpage_module_click'
    GROUP BY 1
) c USING (date)
;
```

---

## 关键 properties 字段

`search_event`（dwd 442）的 `properties` MAP 内字段（访问写法 `properties['xxx']`）：

| 字段 | 取值范围 | 用途 |
|------|---------|------|
| `searchengine_name` | baidu / 360 / douyin | 搜索引擎拆解 |
| `search_source` | 19 种值（search_button / sug_word / search_keyboard / search_history / search_engine 等） | 搜索来源拆解 |
| `search_enter_way` | 8 种值 | 进入搜索方式拆解 |
| `search_way` | 9 种值 | 搜索方式拆解 |
| `from_page` | browser / search_result / … | 上级页面 |
| `page_type` | novel / djy_content / game | 页面类型 |
| `query` | 任意文本 | 搜索词 |
| `searchid` | 唯一 ID | 搜索唯一 ID（用于关联曝光/点击） |
| `device_id` | 设备 ID | **不用于 UV 去重；UV 一律用顶层列 `distinct_id`** |

---

## 注意事项

1. **UV 去重字段**：`distinct_id`（顶层列），**禁止**用 `properties['device_id']`。
2. **日期分区**：`date` 是 `INT YYYYMMDD`，过滤写 `date = 20260520`。
3. **优先级**：主动搜索 PV/UV、AI 搜索、留存等聚合指标 → 中间表（`dm_search_pv_uv_di` / `dm_browser_search_core_indicators_2022_1d`）；事件级、按 query/search_source/search_enter_way 拆解 → 本层 dwd 表。
4. **聚合范围**：单日埋点表查询前请加 `event_name` 过滤，避免扫全表。
