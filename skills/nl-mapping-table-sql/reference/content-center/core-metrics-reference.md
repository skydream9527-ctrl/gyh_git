# Content Center - Core Metrics Reference

## Source Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| dm_newhome_multi_dimension_indicators_di | 多维指标聚合表 | iceberg_zjyprc_hadoop.newhome |
| dm_newhome_user_type_core_indicators_di | 用户类型核心指标表 | iceberg_zjyprc_hadoop.newhome |
| dm_newhome_multi_dimension_retain_indicators_di | 多维留存指标表 | iceberg_zjyprc_hadoop.newhome |

---

## Atomic Metrics (不筛选维度)

### CM-001: DAU

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### CM-002: 应用使用时长(分钟)

```sql
SELECT  date,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### CM-003: 信息流时长(分钟)

```sql
SELECT  date,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### CM-004: 消费时长(分钟)

```sql
SELECT  date,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### CM-005: 内容曝光量

```sql
SELECT  date,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### CM-006: 内容点击量

```sql
SELECT  date,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date
```

### CM-007: 次日留存

```sql
SELECT  date,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### CM-008: 7日留存

```sql
SELECT  date,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### CM-009: 30日留存

```sql
SELECT  date,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### CM-010: 曝光-曝光次留

```sql
SELECT  date,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### CM-011: 曝光-有效次留

```sql
SELECT  date,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date
```

### CM-012: 有效-有效次留

```sql
SELECT  date,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
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

### CM-DIM-001: DAU — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-002: DAU — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
```

### CM-DIM-003: DAU — 按体裁

```sql
SELECT  date,
        item_type,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-004: DAU — 按App版本

```sql
SELECT  date,
        app_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY dau DESC
LIMIT 50
```

### CM-DIM-005: DAU — 按系统版本

```sql
SELECT  date,
        os_version,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY dau DESC
LIMIT 50
```

### CM-DIM-006: DAU — 按机型

```sql
SELECT  date,
        phone_model,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY dau DESC
LIMIT 50
```

### CM-DIM-007: DAU — 按频道

```sql
SELECT  date,
        feed_channel,
        COUNT(DISTINCT CASE WHEN da_pv > 0 THEN did END) AS dau
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-008: 应用使用时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-009: 应用使用时长 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
```

### CM-DIM-010: 应用使用时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-011: 应用使用时长 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY app_duration_min DESC
LIMIT 50
```

### CM-DIM-012: 应用使用时长 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY app_duration_min DESC
LIMIT 50
```

### CM-DIM-013: 应用使用时长 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY app_duration_min DESC
LIMIT 50
```

### CM-DIM-014: 应用使用时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(app_duration_s)/60 AS app_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-015: 信息流时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-016: 信息流时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-017: 信息流时长 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, app_version
ORDER BY feed_duration_min DESC
LIMIT 50
```

### CM-DIM-018: 信息流时长 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, os_version
ORDER BY feed_duration_min DESC
LIMIT 50
```

### CM-DIM-019: 信息流时长 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, phone_model
ORDER BY feed_duration_min DESC
LIMIT 50
```

### CM-DIM-020: 信息流时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(feed_duration_s)/60 AS feed_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-021: 消费时长 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-022: 消费时长 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-023: 消费时长 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(consum_duration_s)/60 AS consum_duration_min
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-024: 内容曝光量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-025: 内容曝光量 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
```

### CM-DIM-026: 内容曝光量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-027: 内容曝光量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY expose_pv DESC
LIMIT 50
```

### CM-DIM-028: 内容曝光量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY expose_pv DESC
LIMIT 50
```

### CM-DIM-029: 内容曝光量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY expose_pv DESC
LIMIT 50
```

### CM-DIM-030: 内容曝光量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(expose_pv) AS expose_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-031: 内容点击量 — 按新老用户

```sql
SELECT  date,
        is_new_2024,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, is_new_2024
```

### CM-DIM-032: 内容点击量 — 按启动方式

```sql
SELECT  date,
        app_launch_way,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_launch_way
```

### CM-DIM-033: 内容点击量 — 按体裁

```sql
SELECT  date,
        item_type,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, item_type
```

### CM-DIM-034: 内容点击量 — 按App版本

```sql
SELECT  date,
        app_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, app_version
ORDER BY click_pv DESC
LIMIT 50
```

### CM-DIM-035: 内容点击量 — 按系统版本

```sql
SELECT  date,
        os_version,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, os_version
ORDER BY click_pv DESC
LIMIT 50
```

### CM-DIM-036: 内容点击量 — 按机型

```sql
SELECT  date,
        phone_model,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, phone_model
ORDER BY click_pv DESC
LIMIT 50
```

### CM-DIM-037: 内容点击量 — 按频道

```sql
SELECT  date,
        feed_channel,
        SUM(click_pv) AS click_pv
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_indicators_di
WHERE   date = '${DATE}'
        AND is_app_dau_2024 = 1
GROUP BY date, feed_channel
```

### CM-DIM-038: 次日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-039: 次日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-040: 次日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-041: 次日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-042: 次日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-043: 次日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_2d) AS retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### CM-DIM-044: 7日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-045: 7日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-046: 7日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-047: 7日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-048: 7日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-049: 7日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_7d) AS retain_7d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### CM-DIM-050: 30日留存 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-051: 30日留存 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-052: 30日留存 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-053: 30日留存 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-054: 30日留存 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-055: 30日留存 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(retain_30d) AS retain_30d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### CM-DIM-056: 曝光-曝光次留 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-057: 曝光-曝光次留 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-058: 曝光-曝光次留 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-059: 曝光-曝光次留 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-060: 曝光-曝光次留 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-061: 曝光-曝光次留 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(e2e_retain_2d) AS e2e_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### CM-DIM-062: 曝光-有效次留 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-063: 曝光-有效次留 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-064: 曝光-有效次留 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-065: 曝光-有效次留 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-066: 曝光-有效次留 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-067: 曝光-有效次留 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(e2v_retain_2d) AS e2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
GROUP BY date, browser_valid_user_type
```

### CM-DIM-068: 有效-有效次留 — 按用户类型

```sql
SELECT  date,
        history_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, history_user_type
```

### CM-DIM-069: 有效-有效次留 — 按活跃类型

```sql
SELECT  date,
        active_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, active_user_type
```

### CM-DIM-070: 有效-有效次留 — 按信息流有效类型

```sql
SELECT  date,
        feed_valid_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, feed_valid_user_type
```

### CM-DIM-071: 有效-有效次留 — 按消费类型

```sql
SELECT  date,
        consume_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND duration_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, consume_user_type
```

### CM-DIM-072: 有效-有效次留 — 按时长类型

```sql
SELECT  date,
        duration_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
        AND history_user_type = '整体(ALL)'
        AND active_user_type = '整体(ALL)'
        AND feed_valid_user_type = '整体(ALL)'
        AND consume_user_type = '整体(ALL)'
        AND browser_valid_user_type = '整体(ALL)'
GROUP BY date, duration_user_type
```

### CM-DIM-073: 有效-有效次留 — 按浏览器有效类型

```sql
SELECT  date,
        browser_valid_user_type,
        SUM(v2v_retain_2d) AS v2v_retain_2d
FROM    iceberg_zjyprc_hadoop.newhome.dm_newhome_multi_dimension_retain_indicators_di
WHERE   date = '${DATE}'
        AND app_port = '内容中心'
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
