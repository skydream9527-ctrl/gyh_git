# Browser Feed - Core Metrics Reference

## Source Tables

浏览器信息流复用浏览器整体的dm表，通过 `is_dau_feed_dapan_2024 = 1` 筛选信息流大盘DAU用户。

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_browser_multi_dimension_indicators_di | 多维指标聚合表 | iceberg_zjyprc_hadoop.browser |
| dm_browser_user_type_core_indicators_di | 用户类型核心指标表 | iceberg_zjyprc_hadoop.browser |
| dm_browser_multi_dimension_retain_indicators_di | 多维留存指标表 | iceberg_zjyprc_hadoop.browser |

---

## Atomic Metrics (不筛选维度)

### BF-001: 信息流DAU

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BF-002: 信息流时长(分钟)

```sql
SELECT  date,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BF-003: 信息流消费时长(分钟)

```sql
SELECT  date,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BF-004: 信息流内容曝光量

```sql
SELECT  date,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BF-005: 信息流内容点击量

```sql
SELECT  date,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BF-006: 信息流次日留存

```sql
SELECT  date,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BF-007: 信息流7日留存

```sql
SELECT  date,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BF-008: 信息流30日留存

```sql
SELECT  date,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BF-009: 信息流曝光-曝光次留

```sql
SELECT  date,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BF-010: 信息流曝光-有效次留

```sql
SELECT  date,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BF-011: 信息流有效-有效次留

```sql
SELECT  date,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

---

## Dimension-Filtered Metrics (按维度筛选)

### BF-DIM-001: 信息流DAU — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BF-DIM-002: 信息流DAU — 按体裁

```sql
SELECT  date,
        item_type,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
ORDER BY dau DESC
```

### BF-DIM-003: 信息流DAU — 按App版本

```sql
SELECT  date,
        app_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, app_version
ORDER BY dau DESC
LIMIT 50
```

### BF-DIM-004: 信息流DAU — 按系统版本

```sql
SELECT  date,
        os_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, os_version
ORDER BY dau DESC
LIMIT 50
```

### BF-DIM-005: 信息流DAU — 按机型

```sql
SELECT  date,
        phone_model,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, phone_model
ORDER BY dau DESC
LIMIT 50
```

### BF-DIM-006: 信息流DAU — 按频道

```sql
SELECT  date,
        feed_channel,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
ORDER BY dau DESC
```

### BF-DIM-007: 信息流时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BF-DIM-008: 信息流时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
ORDER BY feed_duration_min DESC
```

### BF-DIM-009: 信息流时长 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, app_version
ORDER BY feed_duration_min DESC
LIMIT 50
```

### BF-DIM-010: 信息流时长 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, os_version
ORDER BY feed_duration_min DESC
LIMIT 50
```

### BF-DIM-011: 信息流时长 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, phone_model
ORDER BY feed_duration_min DESC
LIMIT 50
```

### BF-DIM-012: 信息流时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
ORDER BY feed_duration_min DESC
```

### BF-DIM-013: 信息流消费时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BF-DIM-014: 信息流消费时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
ORDER BY consum_duration_min DESC
```

### BF-DIM-015: 信息流消费时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
ORDER BY consum_duration_min DESC
```

### BF-DIM-016: 信息流内容曝光量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BF-DIM-017: 信息流内容曝光量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
ORDER BY expose_pv DESC
```

### BF-DIM-018: 信息流内容曝光量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, app_version
ORDER BY expose_pv DESC
LIMIT 50
```

### BF-DIM-019: 信息流内容曝光量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, os_version
ORDER BY expose_pv DESC
LIMIT 50
```

### BF-DIM-020: 信息流内容曝光量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, phone_model
ORDER BY expose_pv DESC
LIMIT 50
```

### BF-DIM-021: 信息流内容曝光量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
ORDER BY expose_pv DESC
```

### BF-DIM-022: 信息流内容点击量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BF-DIM-023: 信息流内容点击量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
ORDER BY click_pv DESC
```

### BF-DIM-024: 信息流内容点击量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, app_version
ORDER BY click_pv DESC
LIMIT 50
```

### BF-DIM-025: 信息流内容点击量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, os_version
ORDER BY click_pv DESC
LIMIT 50
```

### BF-DIM-026: 信息流内容点击量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, phone_model
ORDER BY click_pv DESC
LIMIT 50
```

### BF-DIM-027: 信息流内容点击量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
ORDER BY click_pv DESC
```

### BF-DIM-028: 信息流次日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BF-DIM-029: 信息流次日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BF-DIM-030: 信息流次日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BF-DIM-031: 信息流次日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BF-DIM-032: 信息流次日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BF-DIM-033: 信息流次日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### BF-DIM-034: 信息流7日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BF-DIM-035: 信息流7日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BF-DIM-036: 信息流7日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BF-DIM-037: 信息流7日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BF-DIM-038: 信息流7日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BF-DIM-039: 信息流7日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### BF-DIM-040: 信息流30日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BF-DIM-041: 信息流30日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BF-DIM-042: 信息流30日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BF-DIM-043: 信息流30日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BF-DIM-044: 信息流30日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BF-DIM-045: 信息流30日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器信息流'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

---

## Calculated Metrics (不需要开发)

| Metric | Formula | Description |
|--------|---------|-------------|
| 人均信息流时长(分钟) | 信息流时长(秒)/60/信息流DAU | avg_feed_duration_min |
| 人均消费时长(分钟) | 消费时长(秒)/60/消费UV | avg_consum_duration_min |
| 次日留存率 | 次日留存/信息流DAU | retain_2d_rate |
| 7日留存率 | 7日留存/信息流DAU | retain_7d_rate |
| 30日留存率 | 30日留存/信息流DAU | retain_30d_rate |
