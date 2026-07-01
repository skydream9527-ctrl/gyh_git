-- =====================================================
-- 0629 浏览器流量地图刷新 取数SQL
-- 时间范围：待确认（建议2026-06-22 ~ 2026-06-28，最近7天）
-- 说明：部分字段待确认，SQL中用⚠️标注
-- =====================================================


-- =====================================================
-- Part 1: 分版本类型-整体数据
-- =====================================================

-- 1.1 APP整体规模与使用数据
WITH app_base AS (
    SELECT
        date,
        did,
        app_ver,
        -- ⚠️ 待确认：版本类型映射逻辑
        -- CASE 
        --     WHEN app_ver LIKE '20.11.101%' THEN '默认版'
        --     WHEN app_ver LIKE '20.11.201%' THEN '简洁版'
        --     WHEN app_ver LIKE '20.11.301%' THEN '高端版'
        --     ELSE '其他'
        -- END AS version_type,
        SUM(app_open_cnt) AS app_open_cnt,
        SUM(app_dura) AS app_dur_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN '${start_date}' AND '${end_date}'  -- 待确认日期
      AND app_open_cnt + app_duration_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
      -- AND package_name = 'com.android.browser'  -- 如有需要
    GROUP BY date, did, app_ver
),

-- 1.2 信息流消费数据
feed_base AS (
    SELECT
        date,
        did,
        SUM(CASE WHEN is_top = 0 THEN expos_cnt ELSE 0 END) AS nt_expose_cnt,
        SUM(CASE WHEN is_top = 0 THEN click_cnt ELSE 0 END) AS nt_click_cnt,
        SUM(CASE WHEN is_top = 0 THEN view_cnt ELSE 0 END) AS nt_view_cnt,
        SUM(CASE WHEN is_top = 0 THEN video_play_cnt ELSE 0 END) AS nt_play_cnt,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN '${start_date}' AND '${end_date}'  -- 待确认日期
      AND feed_status IN ('true', 'false')
    GROUP BY date, did
)

-- 1.3 分版本类型聚合结果
SELECT
    a.date,
    -- a.version_type,  -- 待确认版本类型映射后打开
    '大盘' AS version_type,  -- 临时先看大盘
    COUNT(DISTINCT a.did) AS dau,
    SUM(a.app_open_cnt) / COUNT(DISTINCT a.did) AS avg_open_cnt,
    SUM(a.app_dur_ms) / COUNT(DISTINCT a.did) / 60000 AS avg_app_duration_min,
    COUNT(DISTINCT CASE WHEN f.nt_expose_cnt > 0 OR f.nt_click_cnt > 0 THEN f.did END) AS feed_dau,
    ROUND(COUNT(DISTINCT CASE WHEN f.nt_expose_cnt > 0 OR f.nt_click_cnt > 0 THEN f.did END) * 100.0 / COUNT(DISTINCT a.did), 2) AS feed_penetration_rate,
    SUM(COALESCE(f.nt_click_cnt, 0) + COALESCE(f.nt_play_cnt, 0)) / COUNT(DISTINCT a.did) AS avg_feed_vv,
    SUM(COALESCE(f.feed_dura_ms, 0)) / COUNT(DISTINCT a.did) / 60000 AS avg_feed_duration_min
    -- ⚠️ 待补充：ARPU等商业化指标
FROM app_base a
LEFT JOIN feed_base f
  ON a.date = f.date
 AND a.did = f.did
GROUP BY a.date
ORDER BY a.date;


-- =====================================================
-- Part 2: 分版本类型-分启动方式-规模&消费数据
-- =====================================================

WITH launch_base AS (
    SELECT
        date,
        did,
        app_launch_way,
        -- ⚠️ 待确认：三方调起渠道字段（如from_package, caller_app等）
        -- from_package_name AS third_party_channel,
        SUM(app_open_cnt) AS launch_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN '${start_date}' AND '${end_date}'
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
    GROUP BY date, did, app_launch_way
),

feed_launch_base AS (
    SELECT
        l.date,
        l.did,
        l.app_launch_way,
        l.launch_cnt,
        -- l.third_party_channel,
        COALESCE(f.nt_click_cnt, 0) + COALESCE(f.nt_play_cnt, 0) AS feed_vv,
        COALESCE(f.feed_dura_ms, 0) AS feed_dura_ms
    FROM launch_base l
    LEFT JOIN feed_base f
      ON l.date = f.date
     AND l.did = f.did
)

-- 2.1 分启动方式汇总（不区分版本）
SELECT
    date,
    app_launch_way,
    COUNT(DISTINCT did) AS launch_user_cnt,
    SUM(launch_cnt) AS total_launch_cnt,
    ROUND(COUNT(DISTINCT did) * 100.0 / SUM(COUNT(DISTINCT did)) OVER (PARTITION BY date), 2) AS launch_user_ratio,
    SUM(feed_vv) / COUNT(DISTINCT did) AS avg_feed_vv,
    SUM(feed_dura_ms) / COUNT(DISTINCT did) / 60000 AS avg_feed_duration_min,
    ROUND(SUM(CASE WHEN feed_vv > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(DISTINCT did), 2) AS feed_user_rate
    -- ⚠️ 待补充：ARPU
FROM feed_launch_base
GROUP BY date, app_launch_way
ORDER BY date, launch_user_cnt DESC;


-- 2.2 三方调起渠道Top10（仅三方调起用户）
-- ⚠️ 待确认三方调起对应的app_launch_way枚举值后放开过滤
SELECT
    date,
    -- third_party_channel,
    '待确认渠道字段' AS third_party_channel,
    COUNT(DISTINCT did) AS user_cnt,
    SUM(launch_cnt) AS launch_cnt,
    SUM(feed_vv) / COUNT(DISTINCT did) AS avg_feed_vv,
    SUM(feed_dura_ms) / COUNT(DISTINCT did) / 60000 AS avg_feed_duration_min
FROM feed_launch_base
-- WHERE app_launch_way = '三方调起'  -- 待确认枚举值
GROUP BY date
ORDER BY date, user_cnt DESC
LIMIT 10;


-- =====================================================
-- Part 3: 辅助查询 - 先看下有哪些启动方式枚举值
-- =====================================================

-- 3.1 探查app_launch_way枚举值分布
SELECT
    app_launch_way,
    COUNT(DISTINCT did) AS user_cnt,
    SUM(app_open_cnt) AS open_cnt
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN '${start_date}' AND '${end_date}'
  AND app_open_cnt > 0
GROUP BY app_launch_way
ORDER BY user_cnt DESC;

-- 3.2 探查版本号分布（确认版本类型映射）
SELECT
    app_ver,
    COUNT(DISTINCT did) AS user_cnt
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN '${start_date}' AND '${end_date}'
  AND app_open_cnt > 0
GROUP BY app_ver
ORDER BY user_cnt DESC
LIMIT 50;

-- 3.3 探查三方调起相关字段（先查看表结构或抽样）
-- DESC iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di;
-- SELECT * FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
-- WHERE date = '${start_date}' AND app_open_cnt > 0 LIMIT 10;
