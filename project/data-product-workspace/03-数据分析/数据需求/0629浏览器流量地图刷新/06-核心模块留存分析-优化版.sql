-- =====================================================
-- 0629 浏览器流量地图刷新 - Part4: 核心模块留存分析（优化版，单日计算，避免内存溢出）
-- 首日：2026-06-22，次日：2026-06-23
-- 两个口径：
--   1. 模块用户APP次日留存：访问模块的用户，次日是否回访APP
--   2. 模块用户模块次日留存：访问模块的用户，次日是否再次访问该模块
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- 第一步：先把首日模块访问和次日DAU/模块访问都预聚合好，再关联，减少数据量
WITH
-- 首日（2026-06-22）各模块访问用户
first_day_module AS (
    SELECT
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
        END AS module_level1,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date = 20260622
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
    GROUP BY 1, 2
),

-- 次日（2026-06-23）APP DAU
next_day_app_dau AS (
    SELECT DISTINCT did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date = 20260623
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
),

-- 次日（2026-06-23）各模块访问用户
next_day_module AS (
    SELECT
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
        END AS module_level1,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date = 20260623
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
    GROUP BY 1, 2
)

-- 最终结果
SELECT
    f.module_level1,
    COUNT(DISTINCT f.did) AS first_day_uv,
    COUNT(DISTINCT a.did) AS retained_app_uv,
    COUNT(DISTINCT m.did) AS retained_module_uv,
    ROUND(COUNT(DISTINCT a.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS app_next_day_retention,
    ROUND(COUNT(DISTINCT m.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS module_next_day_retention
FROM first_day_module f
LEFT JOIN next_day_app_dau a ON f.did = a.did
LEFT JOIN next_day_module m ON f.did = m.did AND f.module_level1 = m.module_level1
GROUP BY f.module_level1
ORDER BY first_day_uv DESC;
