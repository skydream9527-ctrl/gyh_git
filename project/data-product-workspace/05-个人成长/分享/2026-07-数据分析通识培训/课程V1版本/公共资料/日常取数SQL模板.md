# 日常取数SQL模板
> 直接复制修改日期范围即可使用

---

## 模板1：APP核心指标日报
```sql
-- APP每日DAU、人均时长、人均启动次数
SELECT
    date,
    COUNT(DISTINCT did) AS app_dau,
    SUM(app_open_cnt) AS total_open_cnt,
    ROUND(SUM(app_open_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_open_cnt,
    ROUND(SUM(app_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_app_duration_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN ${start_date} AND ${end_date}  -- 替换成日期，如20260601
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
GROUP BY date
ORDER BY date
```

---

## 模板2：信息流核心指标日报
```sql
-- 信息流每日DAU、CTR、人均时长、VV
SELECT
    date,
    COUNT(DISTINCT did) AS feed_dau,
    SUM(expos_cnt) AS total_expose,
    SUM(click_cnt) AS total_click,
    ROUND(SUM(click_cnt) * 1.0 / SUM(expos_cnt), 4) AS ctr,
    ROUND(SUM(expos_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_expose_per_user,
    ROUND(SUM(click_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_click_per_user,
    ROUND(SUM(feed_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_feed_duration_min,
    SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN ${start_date} AND ${end_date}
  AND is_dau_feed_dapan_2024 = 1
  AND COALESCE(did, '') != ''
  AND is_top = 0  -- 自然流量打开，算全量就注释掉
GROUP BY date
ORDER BY date
```

---

## 模板3：新老用户分群指标
```sql
-- 新老用户DAU、时长对比
SELECT
    date,
    CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END AS user_type,
    COUNT(DISTINCT did) AS dau,
    ROUND(SUM(app_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_duration_min,
    ROUND(SUM(app_open_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_open_cnt
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN ${start_date} AND ${end_date}
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
GROUP BY date, CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END
ORDER BY date, user_type
```

---

## 模板4：启动方式拆分DAU
```sql
-- 按启动方式拆分DAU和占比
SELECT
    date,
    CASE
        WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN '1-主启'
        WHEN app_launch_way = '第三方调起' THEN '2-三方调起'
        WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN '3-Push启动'
        WHEN app_launch_way LIKE '%搜索%' THEN '4-搜索入口'
        ELSE '5-其他入口'
    END AS launch_type,
    COUNT(DISTINCT did) AS dau
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN ${start_date} AND ${end_date}
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
GROUP BY date,
    CASE
        WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN '1-主启'
        WHEN app_launch_way = '第三方调起' THEN '2-三方调起'
        WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN '3-Push启动'
        WHEN app_launch_way LIKE '%搜索%' THEN '4-搜索入口'
        ELSE '5-其他入口'
    END
ORDER BY date, dau DESC
```
