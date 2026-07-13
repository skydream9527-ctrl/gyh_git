# Unsupported Dimensions - 不在dm表中的维度

## 说明

以下维度在需求文档中出现，但不在当前dm映射表中。如需查询这些维度，需要从dwm源表直接查询。以下SQL参照原有查询逻辑编写。

---

## 浏览器（Browser）

### Source Table

```sql
iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
```

### UD-B-001: 按实验组查询DAU

```sql
SELECT  date,
        exp_id,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, exp_id
ORDER BY dau DESC
```

### UD-B-002: 按三方调起包名查询DAU

```sql
SELECT  date,
        third_packagename,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
        AND third_packagename IS NOT NULL
        AND third_packagename != ''
GROUP BY date, third_packagename
ORDER BY dau DESC
LIMIT 50
```

### UD-B-003: 按冷启动标记查询DAU

```sql
SELECT  date,
        is_coldstart,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, is_coldstart
```

### UD-B-004: 按上划行为查询信息流DAU

```sql
SELECT  date,
        is_feed_sliding,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, is_feed_sliding
```

### UD-B-005: 按内容源查询曝光量

```sql
SELECT  date,
        source,
        SUM(expos_cnt) AS expose_pv,
        COUNT(DISTINCT did) AS expose_uv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, source
ORDER BY expose_pv DESC
```

---

## 浏览器信息流（Browser Feed）

### Source Table

```sql
iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
```

### UD-BF-001: 按实验组查询信息流DAU

```sql
SELECT  date,
        exp_id,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, exp_id
ORDER BY dau DESC
```

### UD-BF-002: 按三方调起包名查询信息流DAU

```sql
SELECT  date,
        third_packagename,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
        AND third_packagename IS NOT NULL
        AND third_packagename != ''
GROUP BY date, third_packagename
ORDER BY dau DESC
LIMIT 50
```

### UD-BF-003: 按冷启动标记查询信息流DAU

```sql
SELECT  date,
        is_coldstart,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, is_coldstart
```

### UD-BF-004: 按上划行为查询信息流DAU

```sql
SELECT  date,
        is_feed_sliding,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, is_feed_sliding
```

### UD-BF-005: 按内容源查询信息流曝光量

```sql
SELECT  date,
        source,
        SUM(expos_cnt) AS expose_pv,
        COUNT(DISTINCT did) AS expose_uv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, source
ORDER BY expose_pv DESC
```

---

## 内容中心（Content Center）

### Source Table

```sql
iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
```

### UD-C-001: 按实验组查询DAU

```sql
SELECT  date,
        exp_id,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, exp_id
ORDER BY dau DESC
```

### UD-C-002: 按三方调起包名查询DAU

```sql
SELECT  date,
        third_packagename,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
        AND third_packagename IS NOT NULL
        AND third_packagename != ''
GROUP BY date, third_packagename
ORDER BY dau DESC
LIMIT 50
```

### UD-C-003: 按冷启动标记查询DAU

```sql
SELECT  date,
        is_coldstart,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, is_coldstart
```

### UD-C-004: 按上划行为查询信息流DAU

```sql
SELECT  date,
        is_feed_sliding,
        COUNT(DISTINCT did) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_feed_dau = 1
GROUP BY date, is_feed_sliding
```

### UD-C-005: 按内容源查询曝光量

```sql
SELECT  date,
        source,
        SUM(expos_cnt) AS expose_pv,
        COUNT(DISTINCT did) AS expose_uv
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = '${DATE}'
        AND is_app_dau = 1
GROUP BY date, source
ORDER BY expose_pv DESC
```

---

## Unsupported Dimensions Summary

| Dimension | Field | Browser | Browser Feed | Content Center |
|-----------|-------|---------|-------------|----------------|
| 实验组 | exp_id | dwm_browser_event_aggregation_label_di | dwm_browser_event_aggregation_label_di | dwm_newhome_event_aggregation_label_di |
| 三方调起包名 | third_packagename | dwm_browser_event_aggregation_label_di | dwm_browser_event_aggregation_label_di | dwm_newhome_event_aggregation_label_di |
| 是否冷启 | is_coldstart | dwm_browser_event_aggregation_label_di | dwm_browser_event_aggregation_label_di | dwm_newhome_event_aggregation_label_di |
| 是否有上划行为 | is_feed_sliding | dwm_browser_event_aggregation_label_di | dwm_browser_event_aggregation_label_di | dwm_newhome_event_aggregation_label_di |
| 内容源 | source | dwm_browser_event_aggregation_label_di | dwm_browser_event_aggregation_label_di | dwm_newhome_event_aggregation_label_di |

---

## Notes

1. 以上SQL使用dwm源表，需要COUNT(DISTINCT did)来计算UV
2. dwm表的字段名与dm表不同（如dwm用`expos_cnt`，dm用`expose_pv`）
3. 如需将这些维度加入dm表，请联系数据开发团队补充
