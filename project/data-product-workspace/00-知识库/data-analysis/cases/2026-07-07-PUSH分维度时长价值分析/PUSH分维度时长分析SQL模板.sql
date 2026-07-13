-- =====================================================
-- PUSH分维度时长分析SQL模板（可复用）
-- 适用场景：评估PUSH不同内容类型、不同后续行为的用户价值
-- 时间范围：按需修改日期参数
-- -----------------------------------------------------
-- 包含两个核心分析维度：
-- 1. 分图文/视频PUSH：对比两类PUSH带来的信息流时长、浏览器时长
-- 2. 分返回/下滑行为：对比看完直接返回vs下滑沉浸vs跳出三类用户的时长差异
-- 执行引擎：presto
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- 口径校验：必须包含from_page = ''的空值场景，避免漏统计
-- =====================================================


-- ==============================================
-- 查询1：分图文/视频PUSH的时长对比
-- 口径说明：
-- - 图文PUSH：落地页为feed_content_detail（图文详情页）
-- - 视频PUSH：落地页为feed_video_immersion/feed_minivideo_continuously（视频页/小视频连续播放）
-- - 其他：落地页为其他类型，单独统计低价值流量
-- - 时长统计：取用户点击PUSH当天的整体浏览器时长/信息流时长（人均）
-- ==============================================
WITH push_launch AS (
    SELECT
        date,
        distinct_id AS did,
        properties['sessionId'] AS session_id,
        CASE
            WHEN properties['page'] = 'feed_content_detail' THEN '图文'
            WHEN properties['page'] IN ('feed_video_immersion', 'feed_minivideo_continuously') THEN '视频'
            ELSE '其他'
        END AS content_type,
        ROW_NUMBER() OVER(PARTITION BY date, distinct_id, properties['sessionId'] ORDER BY e_ts) AS rn
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN ${start_date} AND ${end_date}
      AND event_name = 'content_duration_new'
      AND properties['app_launch_way'] = '点击push'
      AND properties['feed_channel'] = 'push'
      AND (properties['from_page'] = 'feed_info_rec' OR properties['from_page'] = '') -- 关键口径：必须包含空值
),
push_user_content AS (
    SELECT
        date,
        did,
        content_type,
        COUNT(DISTINCT session_id) AS push_pv
    FROM push_launch
    WHERE rn = 1
    GROUP BY 1, 2, 3
)
SELECT
    p.date,
    p.content_type,
    COUNT(DISTINCT p.did) AS push_uv,
    SUM(p.push_pv) AS push_pv,
    SUM(CASE WHEN w.is_app_dau_2024 = 1 THEN w.app_dura ELSE 0 END) / 60000 / 10000 AS total_browser_dura_wan_min,
    SUM(CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN w.feed_dura ELSE 0 END) / 60000 / 10000 AS total_feed_dura_wan_min,
    SUM(CASE WHEN w.is_app_dau_2024 = 1 THEN w.app_dura ELSE 0 END) / 60000
        / NULLIF(COUNT(DISTINCT p.did), 0) AS avg_browser_dura_min,
    SUM(CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN w.feed_dura ELSE 0 END) / 60000
        / NULLIF(COUNT(DISTINCT CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN p.did END), 0) AS avg_feed_dura_min
FROM push_user_content p
LEFT JOIN iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di w
    ON p.date = w.date AND p.did = w.did
GROUP BY 1, 2
ORDER BY 1, 2;


-- ==============================================
-- 查询2：分返回/下滑行为的时长对比
-- 口径说明：
-- - pull(下滑)：PUSH落地后首个行为是下滑进入视频沉浸页，持续消费
-- - back(返回)：PUSH落地后首个行为是返回推荐信息流列表
-- - bounce(跳出)：无后续行为，直接退出APP（单独统计）
-- - 时长统计：取用户点击PUSH当天的整体浏览器时长/信息流时长（人均）
-- ==============================================
WITH push_session AS (
    SELECT
        date,
        distinct_id AS did,
        properties['sessionId'] AS session_id
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN ${start_date} AND ${end_date}
      AND event_name = 'app_open'
      AND properties['app_launch_way'] = '点击push'
    GROUP BY 1, 2, 3
),
session_action AS (
    SELECT
        date,
        distinct_id AS did,
        properties['sessionId'] AS session_id,
        e_ts,
        'pull' AS action_type
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN ${start_date} AND ${end_date}
      AND event_name = 'content_duration_video_play_new'
      AND properties['app_launch_way'] = '点击push'
      AND properties['feed_channel'] = 'push'
      AND properties['from_page'] IN ('feed_content_detail', 'home', '') -- 注意空值场景
      AND properties['page'] = 'feed_video_immersion'
      AND properties['item_position'] = '0'

    UNION ALL

    SELECT
        date,
        distinct_id AS did,
        properties['sessionId'] AS session_id,
        e_ts,
        'back' AS action_type
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN ${start_date} AND ${end_date}
      AND event_name = 'content_item_expose_enter'
      AND properties['app_launch_way'] = '点击push'
      AND properties['feed_channel'] = '推荐'
      AND properties['from_page'] IN ('feed_content_detail', 'feed_video_immersion', '') -- 注意空值场景
      AND properties['page'] = 'feed_info_rec'
),
session_label AS (
    SELECT
        s.date,
        s.did,
        s.session_id,
        COALESCE(a.action_type, 'bounce(跳出)') AS action_type,
        ROW_NUMBER() OVER(PARTITION BY s.date, s.did, s.session_id ORDER BY a.e_ts ASC) AS rn
    FROM push_session s
    LEFT JOIN session_action a
        ON s.date = a.date AND s.did = a.did AND s.session_id = a.session_id
),
user_action AS (
    SELECT
        date,
        did,
        action_type,
        COUNT(DISTINCT session_id) AS push_pv
    FROM session_label
    WHERE rn = 1
    GROUP BY 1, 2, 3
)
SELECT
    u.date,
    u.action_type,
    COUNT(DISTINCT u.did) AS push_uv,
    SUM(u.push_pv) AS push_pv,
    SUM(CASE WHEN w.is_app_dau_2024 = 1 THEN w.app_dura ELSE 0 END) / 60000 / 10000 AS total_browser_dura_wan_min,
    SUM(CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN w.feed_dura ELSE 0 END) / 60000 / 10000 AS total_feed_dura_wan_min,
    SUM(CASE WHEN w.is_app_dau_2024 = 1 THEN w.app_dura ELSE 0 END) / 60000
        / NULLIF(COUNT(DISTINCT u.did), 0) AS avg_browser_dura_min,
    SUM(CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN w.feed_dura ELSE 0 END) / 60000
        / NULLIF(COUNT(DISTINCT CASE WHEN w.is_dau_feed_dapan_2024 = 1 AND w.feed_dura > 0 THEN u.did END), 0) AS avg_feed_dura_min
FROM user_action u
LEFT JOIN iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di w
    ON u.date = w.date AND u.did = w.did
GROUP BY 1, 2
ORDER BY 1, 2;
