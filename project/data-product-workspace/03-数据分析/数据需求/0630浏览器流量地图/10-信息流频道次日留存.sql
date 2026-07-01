-- =====================================================
-- 0630 浏览器流量地图 - Part10: 信息流频道次日留存
-- 时间范围：首日 2026-06-22 ~ 2026-06-27（6天），次日 2026-06-23 ~ 2026-06-28
-- 留存口径：
--   1. APP次日留存：访问该频道的用户，次日是否回访APP
--   2. 频道次日留存：访问该频道的用户，次日是否再次访问该频道
-- 频道口径：直接使用 feed_channel 字段，与Part05一致
-- 仅展示7天UV >= 50万的核心频道
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：核心频道次日留存（6天平均，UV >= 50万） ==========
WITH
-- 首日访问各频道的用户
first_day_channel_users AS (
    SELECT
        date AS first_date,
        did,
        feed_channel
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260627
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND feed_channel IS NOT NULL AND feed_channel != ''
    GROUP BY 1, 2, 3
),

-- 次日回访APP的用户
next_day_app_dau AS (
    SELECT
        date - 1 AS first_date,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260623 AND 20260628
      AND app_open_cnt > 0
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
    GROUP BY 1, 2
),

-- 次日再次访问该频道的用户
next_day_channel_users AS (
    SELECT
        date - 1 AS first_date,
        did,
        feed_channel
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260623 AND 20260628
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND feed_channel IS NOT NULL AND feed_channel != ''
    GROUP BY 1, 2, 3
)

-- 6天平均次日留存（只看首日UV >= 50万的频道）
SELECT
    f.feed_channel,
    COUNT(DISTINCT f.did) AS first_day_uv,
    COUNT(DISTINCT n.did) AS next_day_app_uv,
    ROUND(COUNT(DISTINCT n.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS app_next_day_retain_rate,
    COUNT(DISTINCT nc.did) AS next_day_channel_uv,
    ROUND(COUNT(DISTINCT nc.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS channel_next_day_retain_rate
FROM first_day_channel_users f
LEFT JOIN next_day_app_dau n
    ON f.first_date = n.first_date AND f.did = n.did
LEFT JOIN next_day_channel_users nc
    ON f.first_date = nc.first_date AND f.did = nc.did AND f.feed_channel = nc.feed_channel
GROUP BY f.feed_channel
HAVING COUNT(DISTINCT f.did) >= 500000
ORDER BY channel_next_day_retain_rate DESC;
