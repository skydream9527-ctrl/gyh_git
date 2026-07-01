-- =====================================================
-- 0629 浏览器流量地图刷新 - Part4: 核心模块留存分析
-- 两个口径：
--   1. 模块用户APP次日留存：访问模块的用户，次日是否回访APP
--   2. 模块用户模块次日留存：访问模块的用户，次日是否再次访问该模块
-- 时间：首日取2026-06-22~2026-06-27共6天，次日对应2026-06-23~2026-06-28，取多日平均更稳定
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

WITH
-- 模块映射
page_module_mapping AS (
    SELECT
        date,
        did,
        CASE
            WHEN page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN page LIKE 'feed_info_rec%' 
              OR page LIKE 'feed_info_topnews%'
              OR page LIKE 'feed_info_hotList%'
              OR page LIKE 'feed_content_detail%'
              OR page LIKE 'immersion_news_detail%'
              OR page LIKE 'feed_info_videos%'
              OR page LIKE 'feed_info_shortVideo%'
              OR page LIKE 'feed_info_novels%'
              OR page LIKE 'feed_info_broworldcup%'
              OR page LIKE 'feed_info_location%'
              OR page LIKE 'feed_info_skit%'
              OR page LIKE 'feed_info_sport%'
              OR page LIKE 'feed_info_%'
              OR page LIKE 'feed_livestream%'
              OR page LIKE 'author_profile%'
              OR page LIKE 'topic_banner_detail%'
              OR page = 'feed_minivideo_continuously_root'
              OR page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN page LIKE 'search_%' OR page LIKE 'ai_search%' THEN '3_搜索'
            WHEN page LIKE 'feed_video_immersion%'
              OR page = 'feed_minivideo_continuously'
              OR page LIKE 'feed_shortvideo_immerse%'
              OR page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN page LIKE '%novel%' 
              OR page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END AS module_level1
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
    GROUP BY date, did, 
        CASE
            WHEN page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN page LIKE 'feed_info_rec%' 
              OR page LIKE 'feed_info_topnews%'
              OR page LIKE 'feed_info_hotList%'
              OR page LIKE 'feed_content_detail%'
              OR page LIKE 'immersion_news_detail%'
              OR page LIKE 'feed_info_videos%'
              OR page LIKE 'feed_info_shortVideo%'
              OR page LIKE 'feed_info_novels%'
              OR page LIKE 'feed_info_broworldcup%'
              OR page LIKE 'feed_info_location%'
              OR page LIKE 'feed_info_skit%'
              OR page LIKE 'feed_info_sport%'
              OR page LIKE 'feed_info_%'
              OR page LIKE 'feed_livestream%'
              OR page LIKE 'author_profile%'
              OR page LIKE 'topic_banner_detail%'
              OR page = 'feed_minivideo_continuously_root'
              OR page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN page LIKE 'search_%' OR page LIKE 'ai_search%' THEN '3_搜索'
            WHEN page LIKE 'feed_video_immersion%'
              OR page = 'feed_minivideo_continuously'
              OR page LIKE 'feed_shortvideo_immerse%'
              OR page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN page LIKE '%novel%' 
              OR page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END
),

-- APP DAU列表（用于判断次日是否回访APP）
app_dau AS (
    SELECT DISTINCT date, did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260623 AND 20260628
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
),

-- 首日访问模块的用户（2026-06-22 ~ 2026-06-27，共6天）
first_day_users AS (
    SELECT
        d.module_level1,
        d.date AS first_date,
        d.did
    FROM page_module_mapping d
    WHERE d.date BETWEEN 20260622 AND 20260627
),

-- 关联次日APP回访
retention_app AS (
    SELECT
        f.module_level1,
        COUNT(DISTINCT f.did) AS first_day_uv,
        COUNT(DISTINCT CASE WHEN a.did IS NOT NULL THEN f.did END) AS retained_app_uv
    FROM first_day_users f
    LEFT JOIN app_dau a
      ON f.did = a.did
     AND a.date = f.first_date + 1
    GROUP BY f.module_level1
),

-- 关联次日模块回访
retention_module AS (
    SELECT
        f.module_level1,
        COUNT(DISTINCT f.did) AS first_day_uv,
        COUNT(DISTINCT CASE WHEN m.did IS NOT NULL THEN f.did END) AS retained_module_uv
    FROM first_day_users f
    LEFT JOIN page_module_mapping m
      ON f.did = m.did
     AND m.date = f.first_date + 1
     AND f.module_level1 = m.module_level1
    GROUP BY f.module_level1
)

-- 最终结果
SELECT
    a.module_level1,
    a.first_day_uv / 6 AS avg_daily_uv, -- 日均UV
    ROUND(a.retained_app_uv * 100.0 / a.first_day_uv, 2) AS app_next_day_retention,
    ROUND(m.retained_module_uv * 100.0 / m.first_day_uv, 2) AS module_next_day_retention
FROM retention_app a
JOIN retention_module m ON a.module_level1 = m.module_level1
ORDER BY avg_daily_uv DESC;
