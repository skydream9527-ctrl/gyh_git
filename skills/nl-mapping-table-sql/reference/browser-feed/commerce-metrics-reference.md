# Browser Feed - Commerce Metrics Reference

## Source Tables

浏览器信息流复用浏览器整体的财收表，通过 `app_port = '浏览器信息流'` 筛选信息流数据。

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_browser_finance_core_indicators_di | 财收核心指标表 | iceberg_zjyprc_hadoop.browser |

---

## Atomic Metrics (不筛选维度)

### BF-ADV-001: 信息流财收(元)

```sql
SELECT  date,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-002: 信息流流水(元)

```sql
SELECT  date,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-003: 信息流计费曝光

```sql
SELECT  date,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-004: 信息流计费点击

```sql
SELECT  date,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-005: 信息流广告下载量

```sql
SELECT  date,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-006: 信息流广告请求次数

```sql
SELECT  date,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

### BF-ADV-007: 信息流广告填充次数

```sql
SELECT  date,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date
```

---

## Dimension-Filtered Metrics (按维度筛选)

### BF-ADV-DIM-001: 信息流财收 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY revenue DESC
```

### BF-ADV-DIM-002: 信息流财收 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY revenue DESC
```

### BF-ADV-DIM-003: 信息流财收 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY revenue DESC
LIMIT 50
```

### BF-ADV-DIM-004: 信息流财收 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY revenue DESC
```

### BF-ADV-DIM-005: 信息流财收 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY revenue DESC
```

### BF-ADV-DIM-006: 信息流财收 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY revenue DESC
```

### BF-ADV-DIM-007: 信息流财收 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY revenue DESC
```

### BF-ADV-DIM-008: 信息流财收 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY revenue DESC
```

### BF-ADV-DIM-009: 信息流财收 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY revenue DESC
```

### BF-ADV-DIM-010: 信息流财收 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY revenue DESC
```

### BF-ADV-DIM-011: 信息流流水 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY gmv DESC
```

### BF-ADV-DIM-012: 信息流流水 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY gmv DESC
```

### BF-ADV-DIM-013: 信息流流水 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY gmv DESC
LIMIT 50
```

### BF-ADV-DIM-014: 信息流流水 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY gmv DESC
```

### BF-ADV-DIM-015: 信息流流水 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY gmv DESC
```

### BF-ADV-DIM-016: 信息流流水 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY gmv DESC
```

### BF-ADV-DIM-017: 信息流流水 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY gmv DESC
```

### BF-ADV-DIM-018: 信息流流水 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY gmv DESC
```

### BF-ADV-DIM-019: 信息流流水 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY gmv DESC
```

### BF-ADV-DIM-020: 信息流流水 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY gmv DESC
```

### BF-ADV-DIM-021: 信息流计费曝光 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-022: 信息流计费曝光 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-023: 信息流计费曝光 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY expose_cnt DESC
LIMIT 50
```

### BF-ADV-DIM-024: 信息流计费曝光 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-025: 信息流计费曝光 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-026: 信息流计费曝光 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-027: 信息流计费曝光 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-028: 信息流计费曝光 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-029: 信息流计费曝光 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-030: 信息流计费曝光 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY expose_cnt DESC
```

### BF-ADV-DIM-031: 信息流计费点击 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-032: 信息流计费点击 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-033: 信息流计费点击 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY click_cnt DESC
LIMIT 50
```

### BF-ADV-DIM-034: 信息流计费点击 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-035: 信息流计费点击 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-036: 信息流计费点击 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-037: 信息流计费点击 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-038: 信息流计费点击 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-039: 信息流计费点击 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-040: 信息流计费点击 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY click_cnt DESC
```

### BF-ADV-DIM-041: 信息流广告下载量 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-042: 信息流广告下载量 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-043: 信息流广告下载量 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY download_cnt DESC
LIMIT 50
```

### BF-ADV-DIM-044: 信息流广告下载量 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-045: 信息流广告下载量 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-046: 信息流广告下载量 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-047: 信息流广告下载量 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-048: 信息流广告下载量 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-049: 信息流广告下载量 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-050: 信息流广告下载量 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY download_cnt DESC
```

### BF-ADV-DIM-051: 信息流广告请求次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-052: 信息流广告请求次数 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-053: 信息流广告请求次数 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY ad_request_cnt DESC
LIMIT 50
```

### BF-ADV-DIM-054: 信息流广告请求次数 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-055: 信息流广告请求次数 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-056: 信息流广告请求次数 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-057: 信息流广告请求次数 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-058: 信息流广告请求次数 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-059: 信息流广告请求次数 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-060: 信息流广告请求次数 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY ad_request_cnt DESC
```

### BF-ADV-DIM-061: 信息流广告填充次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_scene
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-062: 信息流广告填充次数 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_type
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-063: 信息流广告填充次数 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_id
ORDER BY ad_response_cnt DESC
LIMIT 50
```

### BF-ADV-DIM-064: 信息流广告填充次数 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_source
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-065: 信息流广告填充次数 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_status
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-066: 信息流广告填充次数 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_label
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-067: 信息流广告填充次数 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_label
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-068: 信息流广告填充次数 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_type
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-069: 信息流广告填充次数 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_source
ORDER BY ad_response_cnt DESC
```

### BF-ADV-DIM-070: 信息流广告填充次数 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
GROUP BY date, ad_position_sub_status
ORDER BY ad_response_cnt DESC
```

---

## Calculated Metrics (不需要开发)

| Metric | Formula | Description |
|--------|---------|-------------|
| eCPM | 财收/计费曝光*1000 | 每千次曝光收入 |
| CTR | 计费点击/计费曝光 | 广告点击率 |
| CVR | 广告下载/计费点击 | 广告转化率 |
| CPC | 财收/计费点击 | 每次点击成本 |
| 填充率 | 广告填充/广告请求 | 广告填充率 |
