# Browser Feed - SQL Templates

## Table Schema

浏览器信息流复用浏览器整体的dm表，通过 `is_dau_feed_dapan_2024 = 1` 筛选信息流大盘DAU用户。

### Main Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_browser_multi_dimension_indicators_di | 多维指标聚合表 | iceberg_zjyprc_hadoop.browser |
| dm_browser_multi_dimension_retain_indicators_di | 留存计算用did粒度指标表 | iceberg_zjyprc_hadoop.browser |
| ads_browser_user_type_core_indicators_di | 用户类型核心指标表 | iceberg_zjyprc_hadoop.browser |
| ads_browser_item_type_core_indicators_di | 内容转化主题核心指标表 | iceberg_zjyprc_hadoop.browser |
| ads_browser_page_indicators_di | 小场景指标表 | iceberg_zjyprc_hadoop.browser |
| ads_browser_finance_core_indicators_di | 财收核心指标表 | doris_c3prc_xiaomi.browser |

---

## SQL Templates by Query Type

### BF-DIM-001: 多维指标聚合表 — 启动方式枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: app_launch_way

```sql
SELECT
    app_launch_way,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY app_launch_way
ORDER BY dau DESC;
```

---

### BF-DIM-002: 多维指标聚合表 — 体裁枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: item_type

```sql
SELECT
    item_type,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY item_type
ORDER BY dau DESC;
```

---

### BF-DIM-003: 多维指标聚合表 — App版本枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: app_version

```sql
SELECT
    app_version,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY app_version
ORDER BY dau DESC
LIMIT 50;
```

---

### BF-DIM-004: 多维指标聚合表 — 系统版本枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: os_version

```sql
SELECT
    os_version,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY os_version
ORDER BY dau DESC
LIMIT 50;
```

---

### BF-DIM-005: 多维指标聚合表 — 机型枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: phone_model

```sql
SELECT
    phone_model,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY phone_model
ORDER BY dau DESC
LIMIT 50;
```

---

### BF-DIM-006: 多维指标聚合表 — 频道枚举值

**Table**: dm_browser_multi_dimension_indicators_di
**Field**: feed_channel

```sql
SELECT
    feed_channel,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY feed_channel
ORDER BY dau DESC;
```

---

### BF-DIM-007: 用户类型核心指标表 — 用户类型枚举值

**Table**: ads_browser_user_type_core_indicators_di
**Field**: user_type

```sql
SELECT
    user_type,
    dau
FROM iceberg_zjyprc_hadoop.browser.ads_browser_user_type_core_indicators_di
WHERE date = '${DATE}'
ORDER BY dau DESC;
```

---

### BF-DIM-008: 内容转化主题核心指标表 — 体裁枚举值

**Table**: ads_browser_item_type_core_indicators_di
**Field**: item_type

```sql
SELECT
    item_type,
    expose_pv,
    click_pv,
    view_pv
FROM iceberg_zjyprc_hadoop.browser.ads_browser_item_type_core_indicators_di
WHERE date = '${DATE}'
ORDER BY expose_pv DESC;
```

---

### BF-DIM-009: 小场景指标表 — 页面枚举值

**Table**: ads_browser_page_indicators_di
**Field**: page

```sql
SELECT
    page,
    expose_uv,
    expose_pv
FROM iceberg_zjyprc_hadoop.browser.ads_browser_page_indicators_di
WHERE date = '${DATE}'
ORDER BY expose_uv DESC;
```

---

### BF-DIM-010: 留存计算用did粒度指标表 — 启动方式枚举值

**Table**: dm_browser_multi_dimension_retain_indicators_di
**Field**: app_launch_way

```sql
SELECT
    app_launch_way,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY app_launch_way
ORDER BY dau DESC;
```

---

### BF-DIM-011: 留存计算用did粒度指标表 — 体裁枚举值

**Table**: dm_browser_multi_dimension_retain_indicators_di
**Field**: item_type

```sql
SELECT
    item_type,
    COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE date = '${DATE}'
    AND is_dau_feed_dapan_2024 = 1
GROUP BY item_type
ORDER BY dau DESC;
```

---

### BF-DIM-012: 财收核心指标表 — 广告位场景枚举值

**Table**: ads_browser_finance_core_indicators_di
**Field**: ad_position_scene

```sql
SELECT
    ad_position_scene,
    SUM(revenue) AS total_revenue
FROM doris_c3prc_xiaomi.browser.ads_browser_finance_core_indicators_di
WHERE date = '${DATE}'
    AND tag_id IN (
        '1.13.c.1', '1.13.c.2', '1.13.c.3', '1.13.c.4', '1.13.c.5',
        '1.13.c.7', '1.13.c.8', '1.13.c.9', '1.13.c.10', '1.13.c.11',
        '1.13.c.12', '1.13.c.13', '1.13.c.16', '1.13.c.17', '1.13.c.19',
        '1.13.c.20', '1.13.c.22', '1.13.c.23', '1.13.c.24', '1.13.c.25',
        '1.13.c.26', '1.13.c.27', '1.13.c.28', '1.13.c.30',
        '1.13.f.13', '1.13.f.20',
        '1.13.g.4', '1.13.g.5', '1.13.g.6', '1.13.g.7', '1.13.g.9',
        '1.13.g.18', '1.13.g.23', '1.13.g.24', '1.13.g.25', '1.13.g.29',
        '1.13.g.30',
        '1.13.1.3', '1.13.1.4', '1.13.1.6', '1.13.1.9'
    )
GROUP BY ad_position_scene
ORDER BY total_revenue DESC;
```

---

### BF-DIM-013: 财收核心指标表 — 广告位枚举值

**Table**: ads_browser_finance_core_indicators_di
**Field**: tag_id

```sql
SELECT
    tag_id,
    SUM(revenue) AS total_revenue
FROM doris_c3prc_xiaomi.browser.ads_browser_finance_core_indicators_di
WHERE date = '${DATE}'
    AND tag_id IN (
        '1.13.c.1', '1.13.c.2', '1.13.c.3', '1.13.c.4', '1.13.c.5',
        '1.13.c.7', '1.13.c.8', '1.13.c.9', '1.13.c.10', '1.13.c.11',
        '1.13.c.12', '1.13.c.13', '1.13.c.16', '1.13.c.17', '1.13.c.19',
        '1.13.c.20', '1.13.c.22', '1.13.c.23', '1.13.c.24', '1.13.c.25',
        '1.13.c.26', '1.13.c.27', '1.13.c.28', '1.13.c.30',
        '1.13.f.13', '1.13.f.20',
        '1.13.g.4', '1.13.g.5', '1.13.g.6', '1.13.g.7', '1.13.g.9',
        '1.13.g.18', '1.13.g.23', '1.13.g.24', '1.13.g.25', '1.13.g.29',
        '1.13.g.30',
        '1.13.1.3', '1.13.1.4', '1.13.1.6', '1.13.1.9'
    )
GROUP BY tag_id
ORDER BY total_revenue DESC;
```

---

## Usage Notes

1. **Date Format**: Always use `'YYYYMMDD'` format (e.g., `'20260330'`)
2. **Partition Filter**: Always include `date` in WHERE clause to avoid full table scan
3. **Feed Filter**: Use `is_dau_feed_dapan_2024 = 1` for browser feed data
4. **High Cardinality Fields**: app_version, os_version, phone_model use `LIMIT 50`
5. **Revenue Fields**: Revenue is stored in 分 (cents), divide by 100000 for 元 (yuan) if needed
6. **Duration Fields**: Duration fields in dm tables are in seconds (not milliseconds)
7. **DAU Aggregation**: dm表中无dau字段，使用COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END)计算DAU
