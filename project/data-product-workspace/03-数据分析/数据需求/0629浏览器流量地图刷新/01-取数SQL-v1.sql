-- =====================================================
-- 0629 浏览器流量地图刷新 取数SQL v1
-- 时间范围：2026-06-22 ~ 2026-06-28（最近7天）
-- 说明：基于2026-06-28探查结果更新，版本类型待确认
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================


-- =====================================================
-- Part 0: 启动方式分类映射（确认后放开注释）
-- =====================================================
-- 启动方式归类（四大类+其他）：
-- 1. 主启：点击icon、点击桌面书签
-- 2. 三方调起：第三方调起
-- 3. Push：点击push、subscribe_push
-- 4. 搜索：新全搜调起、newhome搜索框、newhome搜索调起、newhome搜索按钮、newhome信息流搜索light、newhome信息流搜索chose、全搜调起、桌面框调起
-- 5. 其他入口：负一屏、各类widget、calendar、其他等


-- =====================================================
-- Part 1: 分版本类型-整体数据（大盘，先不区分版本）
-- =====================================================

WITH app_base AS (
    SELECT
        date,
        did,
        SUM(app_open_cnt) AS app_open_cnt,
        SUM(app_dura) AS app_dur_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt + app_duration_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date, did
),

feed_base AS (
    SELECT
        date,
        did,
        SUM(CASE WHEN is_top = 0 THEN expos_cnt ELSE 0 END) AS nt_expose_cnt,
        SUM(CASE WHEN is_top = 0 THEN click_cnt ELSE 0 END) AS nt_click_cnt,
        SUM(CASE WHEN is_top = 0 THEN view_cnt ELSE 0 END) AS nt_view_cnt,
        SUM(CASE WHEN is_top = 0 THEN video_play_cnt ELSE 0 END) AS nt_play_cnt,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms,
        SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND feed_status IN ('true', 'false')
    GROUP BY date, did
)

SELECT
    a.date,
    '大盘' AS version_type,
    COUNT(DISTINCT a.did) AS dau,
    SUM(a.app_open_cnt) / COUNT(DISTINCT a.did) AS avg_open_cnt,
    ROUND(SUM(a.app_dur_ms) / COUNT(DISTINCT a.did) / 60000, 2) AS avg_app_duration_min,
    COUNT(DISTINCT CASE WHEN f.nt_expose_cnt > 0 OR f.nt_click_cnt > 0 THEN f.did END) AS feed_dau,
    ROUND(COUNT(DISTINCT CASE WHEN f.nt_expose_cnt > 0 OR f.nt_click_cnt > 0 THEN f.did END) * 100.0 / COUNT(DISTINCT a.did), 2) AS feed_penetration_rate,
    ROUND(SUM(COALESCE(f.total_vv, 0)) / COUNT(DISTINCT a.did), 2) AS avg_feed_vv,
    ROUND(SUM(COALESCE(f.feed_dura_ms, 0)) / COUNT(DISTINCT a.did) / 60000, 2) AS avg_feed_duration_min,
    ROUND(SUM(COALESCE(f.nt_click_cnt, 0) + COALESCE(f.nt_play_cnt, 0)) * 100.0 / NULLIF(SUM(COALESCE(f.nt_expose_cnt, 0)), 0), 2) AS feed_ctr
FROM app_base a
LEFT JOIN feed_base f
  ON a.date = f.date
 AND a.did = f.did
GROUP BY a.date
ORDER BY a.date;


-- =====================================================
-- Part 2: 分启动方式-规模&消费数据（按天）
-- =====================================================

WITH launch_base AS (
    SELECT
        date,
        did,
        app_launch_way,
        third_packagename,
        -- 启动方式归类
        CASE
            WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN '1_主启'
            WHEN app_launch_way IN ('第三方调起') THEN '2_三方调起'
            WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN '3_Push启动'
            WHEN app_launch_way IN ('新全搜调起', 'newhome搜索框', 'newhome搜索调起', 'newhome搜索按钮', 'newhome信息流搜索light', 'newhome信息流搜索chose', '全搜调起', '桌面框调起') THEN '4_搜索入口'
            ELSE '5_其他入口'
        END AS launch_type,
        SUM(app_open_cnt) AS launch_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date, did, app_launch_way, third_packagename
),

feed_base AS (
    SELECT
        date,
        did,
        SUM(CASE WHEN is_top = 0 THEN expos_cnt ELSE 0 END) AS nt_expose_cnt,
        SUM(CASE WHEN is_top = 0 THEN click_cnt ELSE 0 END) AS nt_click_cnt,
        SUM(CASE WHEN is_top = 0 THEN video_play_cnt ELSE 0 END) AS nt_play_cnt,
        SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND feed_status IN ('true', 'false')
    GROUP BY date, did
),

launch_feed AS (
    SELECT
        l.date,
        l.did,
        l.launch_type,
        l.app_launch_way,
        l.launch_cnt,
        COALESCE(f.total_vv, 0) AS feed_vv,
        COALESCE(f.feed_dura_ms, 0) AS feed_dura_ms,
        CASE WHEN COALESCE(f.total_vv, 0) > 0 THEN 1 ELSE 0 END AS is_feed_user
    FROM launch_base l
    LEFT JOIN feed_base f
      ON l.date = f.date
     AND l.did = f.did
),

-- 计算大盘DAU用于占比计算
daily_dau AS (
    SELECT date, COUNT(DISTINCT did) AS total_dau
    FROM launch_base
    GROUP BY date
)

-- 2.1 按启动大类聚合
SELECT
    l.date,
    l.launch_type,
    COUNT(DISTINCT l.did) AS launch_user_cnt,
    SUM(l.launch_cnt) AS total_launch_cnt,
    ROUND(COUNT(DISTINCT l.did) * 100.0 / d.total_dau, 2) AS launch_user_ratio,
    ROUND(SUM(l.launch_cnt) * 1.0 / COUNT(DISTINCT l.did), 2) AS avg_launch_per_user,
    ROUND(SUM(l.feed_vv) / COUNT(DISTINCT l.did), 2) AS avg_feed_vv,
    ROUND(SUM(l.feed_dura_ms) / COUNT(DISTINCT l.did) / 60000, 2) AS avg_feed_duration_min,
    ROUND(SUM(l.is_feed_user) * 100.0 / COUNT(DISTINCT l.did), 2) AS feed_user_penetration
FROM launch_feed l
JOIN daily_dau d ON l.date = d.date
GROUP BY l.date, l.launch_type, d.total_dau
ORDER BY l.date, launch_user_cnt DESC;


-- =====================================================
-- Part 2.2: 三方调起渠道Top20（最近7天汇总）
-- =====================================================

WITH third_party_base AS (
    SELECT
        date,
        did,
        third_packagename,
        SUM(app_open_cnt) AS launch_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_launch_way = '第三方调起'
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date, did, third_packagename
),

feed_base AS (
    SELECT
        date,
        did,
        SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND feed_status IN ('true', 'false')
    GROUP BY date, did
)

SELECT
    t.third_packagename,
    COUNT(DISTINCT t.did) AS user_cnt_7d,
    SUM(t.launch_cnt) AS launch_cnt_7d,
    ROUND(SUM(t.launch_cnt) * 1.0 / COUNT(DISTINCT t.did), 2) AS avg_launch_per_user,
    ROUND(SUM(COALESCE(f.total_vv, 0)) / COUNT(DISTINCT t.did), 2) AS avg_feed_vv,
    ROUND(SUM(COALESCE(f.feed_dura_ms, 0)) / COUNT(DISTINCT t.did) / 60000, 2) AS avg_feed_duration_min
FROM third_party_base t
LEFT JOIN feed_base f
  ON t.date = f.date
 AND t.did = f.did
WHERE t.third_packagename IS NOT NULL
  AND t.third_packagename != ''
  AND t.third_packagename NOT LIKE 'homeAppId%'
GROUP BY t.third_packagename
ORDER BY user_cnt_7d DESC
LIMIT 20;


-- =====================================================
-- Part 3: Push启动用户 vs 其他用户 价值对比（验证历史结论）
-- =====================================================

WITH user_launch_type AS (
    SELECT
        date,
        did,
        -- 标记用户是否有push启动（优先级：push > 其他）
        MAX(CASE WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN 1 ELSE 0 END) AS is_push_user,
        MAX(CASE WHEN app_launch_way = '第三方调起' THEN 1 ELSE 0 END) AS is_third_party_user,
        MAX(CASE WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN 1 ELSE 0 END) AS is_main_launch_user
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date, did
),

feed_base AS (
    SELECT
        date,
        did,
        SUM(app_open_cnt) AS app_open_cnt,
        SUM(app_dura) AS app_dur_ms,
        SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms,
        SUM(CASE WHEN is_top = 0 THEN expos_cnt ELSE 0 END) AS nt_expose_cnt,
        SUM(CASE WHEN is_top = 0 THEN click_cnt ELSE 0 END) AS nt_click_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND feed_status IN ('true', 'false')
    GROUP BY date, did
)

SELECT
    u.date,
    CASE
        WHEN u.is_push_user = 1 THEN 'Push启动用户'
        WHEN u.is_main_launch_user = 1 THEN '仅主启用户'
        WHEN u.is_third_party_user = 1 THEN '仅三方调起用户'
        ELSE '其他用户'
    END AS user_group,
    COUNT(DISTINCT u.did) AS user_cnt,
    ROUND(SUM(COALESCE(f.app_open_cnt, 0)) / COUNT(DISTINCT u.did), 2) AS avg_open_cnt,
    ROUND(SUM(COALESCE(f.app_dur_ms, 0)) / COUNT(DISTINCT u.did) / 60000, 2) AS avg_app_duration_min,
    ROUND(SUM(COALESCE(f.total_vv, 0)) / COUNT(DISTINCT u.did), 2) AS avg_feed_vv,
    ROUND(SUM(COALESCE(f.feed_dura_ms, 0)) / COUNT(DISTINCT u.did) / 60000, 2) AS avg_feed_duration_min,
    ROUND(SUM(COALESCE(f.nt_click_cnt, 0)) * 100.0 / NULLIF(SUM(COALESCE(f.nt_expose_cnt, 0)), 0), 2) AS feed_ctr
FROM user_launch_type u
LEFT JOIN feed_base f
  ON u.date = f.date
 AND u.did = f.did
GROUP BY u.date,
    CASE
        WHEN u.is_push_user = 1 THEN 'Push启动用户'
        WHEN u.is_main_launch_user = 1 THEN '仅主启用户'
        WHEN u.is_third_party_user = 1 THEN '仅三方调起用户'
        ELSE '其他用户'
    END
ORDER BY u.date, user_cnt DESC;
