# Browser - Commerce Metrics Reference

## Source Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_browser_finance_core_indicators_di | 财收核心指标表 | iceberg_zjyprc_hadoop.browser |

---

## Atomic Metrics (不筛选维度)

### BM-ADV-001: 财收(元)

```sql
SELECT  date,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-002: 流水(元)

```sql
SELECT  date,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-003: 计费曝光

```sql
SELECT  date,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-004: 计费点击

```sql
SELECT  date,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-005: 广告下载量

```sql
SELECT  date,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-006: 广告请求次数

```sql
SELECT  date,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### BM-ADV-007: 广告填充次数

```sql
SELECT  date,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

---

## Dimension-Filtered Metrics (按维度筛选)

### BM-ADV-DIM-001: 财收 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY revenue DESC
```

### BM-ADV-DIM-002: 财收 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY revenue DESC
```

### BM-ADV-DIM-003: 财收 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY revenue DESC
LIMIT 50
```

### BM-ADV-DIM-004: 财收 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY revenue DESC
```

### BM-ADV-DIM-005: 财收 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY revenue DESC
```

### BM-ADV-DIM-006: 财收 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY revenue DESC
```

### BM-ADV-DIM-007: 财收 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY revenue DESC
```

### BM-ADV-DIM-008: 财收 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY revenue DESC
```

### BM-ADV-DIM-009: 财收 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY revenue DESC
```

### BM-ADV-DIM-010: 财收 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(revenue) AS revenue
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY revenue DESC
```

### BM-ADV-DIM-011: 流水 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY gmv DESC
```

### BM-ADV-DIM-012: 流水 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY gmv DESC
```

### BM-ADV-DIM-013: 流水 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY gmv DESC
LIMIT 50
```

### BM-ADV-DIM-014: 流水 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY gmv DESC
```

### BM-ADV-DIM-015: 流水 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY gmv DESC
```

### BM-ADV-DIM-016: 流水 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY gmv DESC
```

### BM-ADV-DIM-017: 流水 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY gmv DESC
```

### BM-ADV-DIM-018: 流水 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY gmv DESC
```

### BM-ADV-DIM-019: 流水 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY gmv DESC
```

### BM-ADV-DIM-020: 流水 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(gmv) AS gmv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY gmv DESC
```

### BM-ADV-DIM-021: 计费曝光 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-022: 计费曝光 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-023: 计费曝光 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY expose_cnt DESC
LIMIT 50
```

### BM-ADV-DIM-024: 计费曝光 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-025: 计费曝光 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-026: 计费曝光 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-027: 计费曝光 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-028: 计费曝光 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-029: 计费曝光 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-030: 计费曝光 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(expose_cnt) AS expose_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY expose_cnt DESC
```

### BM-ADV-DIM-031: 计费点击 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-032: 计费点击 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-033: 计费点击 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY click_cnt DESC
LIMIT 50
```

### BM-ADV-DIM-034: 计费点击 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-035: 计费点击 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-036: 计费点击 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-037: 计费点击 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-038: 计费点击 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-039: 计费点击 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-040: 计费点击 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(click_cnt) AS click_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY click_cnt DESC
```

### BM-ADV-DIM-041: 广告下载量 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-042: 广告下载量 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-043: 广告下载量 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY download_cnt DESC
LIMIT 50
```

### BM-ADV-DIM-044: 广告下载量 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-045: 广告下载量 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-046: 广告下载量 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-047: 广告下载量 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-048: 广告下载量 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-049: 广告下载量 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-050: 广告下载量 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(download_cnt) AS download_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY download_cnt DESC
```

### BM-ADV-DIM-051: 广告请求次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-052: 广告请求次数 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-053: 广告请求次数 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY ad_request_cnt DESC
LIMIT 50
```

### BM-ADV-DIM-054: 广告请求次数 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-055: 广告请求次数 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-056: 广告请求次数 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-057: 广告请求次数 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-058: 广告请求次数 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-059: 广告请求次数 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-060: 广告请求次数 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_status
ORDER BY ad_request_cnt DESC
```

### BM-ADV-DIM-061: 广告填充次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-062: 广告填充次数 — 按广告位类型

```sql
SELECT  date,
        ad_position_type,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_type
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-063: 广告填充次数 — 按广告位ID

```sql
SELECT  date,
        ad_position_id,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_id
ORDER BY ad_response_cnt DESC
LIMIT 50
```

### BM-ADV-DIM-064: 广告填充次数 — 按广告位来源

```sql
SELECT  date,
        ad_position_source,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_source
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-065: 广告填充次数 — 按广告位状态

```sql
SELECT  date,
        ad_position_status,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_status
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-066: 广告填充次数 — 按广告位标签

```sql
SELECT  date,
        ad_position_label,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_label
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-067: 广告填充次数 — 按广告位子标签

```sql
SELECT  date,
        ad_position_sub_label,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_label
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-068: 广告填充次数 — 按广告位子类型

```sql
SELECT  date,
        ad_position_sub_type,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_type
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-069: 广告填充次数 — 按广告位子来源

```sql
SELECT  date,
        ad_position_sub_source,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_sub_source
ORDER BY ad_response_cnt DESC
```

### BM-ADV-DIM-070: 广告填充次数 — 按广告位子状态

```sql
SELECT  date,
        ad_position_sub_status,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_finance_core_indicators_di
WHERE   date = '${DATE}'
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
