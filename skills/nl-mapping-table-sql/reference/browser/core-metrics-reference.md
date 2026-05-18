# Browser - Core Metrics Reference

## Source Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_browser_multi_dimension_indicators_di | 多维指标聚合表 | iceberg_zjyprc_hadoop.browser |
| dm_browser_user_type_core_indicators_di | 用户类型核心指标表 | iceberg_zjyprc_hadoop.browser |
| dm_browser_multi_dimension_retain_indicators_di | 多维留存指标表 | iceberg_zjyprc_hadoop.browser |

---

## Atomic Metrics (不筛选维度)

### BM-001: DAU

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### BM-002: 应用使用时长(分钟)

```sql
SELECT  date,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### BM-003: 信息流时长(分钟)

```sql
SELECT  date,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BM-004: 消费时长(分钟)

```sql
SELECT  date,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### BM-005: 内容曝光量

```sql
SELECT  date,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### BM-006: 内容点击量

```sql
SELECT  date,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### BM-007: 次日留存

```sql
SELECT  date,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BM-008: 7日留存

```sql
SELECT  date,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BM-009: 30日留存

```sql
SELECT  date,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BM-010: 曝光-曝光次留

```sql
SELECT  date,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BM-011: 曝光-有效次留

```sql
SELECT  date,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### BM-012: 有效-有效次留

```sql
SELECT  date,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
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

### BM-DIM-001: DAU — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-002: DAU — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
ORDER BY dau DESC
```

### BM-DIM-003: DAU — 按体裁

```sql
SELECT  date,
        item_type,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
ORDER BY dau DESC
```

### BM-DIM-004: DAU — 按App版本

```sql
SELECT  date,
        app_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY dau DESC
LIMIT 50
```

### BM-DIM-005: DAU — 按系统版本

```sql
SELECT  date,
        os_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY dau DESC
LIMIT 50
```

### BM-DIM-006: DAU — 按机型

```sql
SELECT  date,
        phone_model,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY dau DESC
LIMIT 50
```

### BM-DIM-007: DAU — 按频道

```sql
SELECT  date,
        feed_channel,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
ORDER BY dau DESC
```

### BM-DIM-008: 应用使用时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-009: 应用使用时长 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
ORDER BY app_duration_min DESC
```

### BM-DIM-010: 应用使用时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
ORDER BY app_duration_min DESC
```

### BM-DIM-011: 应用使用时长 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY app_duration_min DESC
LIMIT 50
```

### BM-DIM-012: 应用使用时长 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY app_duration_min DESC
LIMIT 50
```

### BM-DIM-013: 应用使用时长 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY app_duration_min DESC
LIMIT 50
```

### BM-DIM-014: 应用使用时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
ORDER BY app_duration_min DESC
```

### BM-DIM-015: 信息流时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-016: 信息流时长 — 按体裁

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

### BM-DIM-017: 信息流时长 — 按频道

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

### BM-DIM-018: 信息流时长 — 按App版本

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

### BM-DIM-019: 信息流时长 — 按系统版本

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

### BM-DIM-020: 信息流时长 — 按机型

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

### BM-DIM-021: 消费时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-022: 消费时长 — 按体裁

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

### BM-DIM-023: 消费时长 — 按频道

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

### BM-DIM-024: 内容曝光量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-025: 内容曝光量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
ORDER BY expose_pv DESC
```

### BM-DIM-026: 内容曝光量 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
ORDER BY expose_pv DESC
```

### BM-DIM-027: 内容曝光量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY expose_pv DESC
LIMIT 50
```

### BM-DIM-028: 内容曝光量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY expose_pv DESC
LIMIT 50
```

### BM-DIM-029: 内容曝光量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY expose_pv DESC
LIMIT 50
```

### BM-DIM-030: 内容曝光量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
ORDER BY expose_pv DESC
```

### BM-DIM-031: 内容点击量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### BM-DIM-032: 内容点击量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
ORDER BY click_pv DESC
```

### BM-DIM-033: 内容点击量 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
ORDER BY click_pv DESC
```

### BM-DIM-034: 内容点击量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY click_pv DESC
LIMIT 50
```

### BM-DIM-035: 内容点击量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY click_pv DESC
LIMIT 50
```

### BM-DIM-036: 内容点击量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY click_pv DESC
LIMIT 50
```

### BM-DIM-037: 内容点击量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
ORDER BY click_pv DESC
```

### BM-DIM-038: 次日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BM-DIM-039: 次日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BM-DIM-040: 次日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BM-DIM-041: 次日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BM-DIM-042: 次日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BM-DIM-043: 次日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### BM-DIM-044: 7日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BM-DIM-045: 7日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BM-DIM-046: 7日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BM-DIM-047: 7日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BM-DIM-048: 7日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BM-DIM-049: 7日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### BM-DIM-050: 30日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### BM-DIM-051: 30日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### BM-DIM-052: 30日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### BM-DIM-053: 30日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### BM-DIM-054: 30日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### BM-DIM-055: 30日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '浏览器'
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
| 人均使用时长(分钟) | 应用使用时长(秒)/60/DAU | avg_duration_min |
| 人均信息流时长(分钟) | 信息流时长(秒)/60/DAU | avg_feed_duration_min |
| 人均消费时长(分钟) | 消费时长(秒)/60/消费UV | avg_consum_duration_min |
| 次日留存率 | 次日留存/DAU | retain_2d_rate |
| 7日留存率 | 7日留存/DAU | retain_7d_rate |
| 30日留存率 | 30日留存/DAU | retain_30d_rate |
