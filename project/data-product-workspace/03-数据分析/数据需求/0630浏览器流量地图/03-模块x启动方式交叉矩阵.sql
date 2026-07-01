-- =====================================================
-- 0630 浏览器流量地图 - Part03: 模块 × 启动方式 交叉矩阵
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 模块：9类一级模块
-- 启动方式：6类（含内容中心）
-- 指标：UV（去重用户数）
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

WITH module_launch AS (
    SELECT
        did,
        CASE
            -- 1_首页
            WHEN page IN ('home', 'home_concise', 'default') THEN '1_首页'
            -- 2_信息流
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
            -- 3_搜索
            WHEN page LIKE 'search_%' OR page LIKE 'ai_search%' THEN '3_搜索'
            -- 4_视频
            WHEN page LIKE 'feed_video_immersion%'
              OR page = 'feed_minivideo_continuously'
              OR page LIKE 'feed_shortvideo_immerse%'
              OR page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            -- 5_小说
            WHEN page LIKE '%novel%'
              OR page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            -- 6_个人中心
            WHEN page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            -- 7_书签历史
            WHEN page LIKE 'bookmark_%' THEN '7_书签历史'
            -- 8_网页浏览
            WHEN page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END AS module_level1,
        CASE
            WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
            WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
            ELSE '其他'
        END AS launch_way
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
      AND app_launch_way IS NOT NULL AND app_launch_way != ''
)

-- 交叉矩阵：模块（行） × 启动方式（列）
SELECT
    module_level1,
    COUNT(DISTINCT did) AS uv_total,
    COUNT(DISTINCT CASE WHEN launch_way = '点击icon' THEN did END) AS "uv_点击icon",
    COUNT(DISTINCT CASE WHEN launch_way = '第三方调起' THEN did END) AS "uv_第三方调起",
    COUNT(DISTINCT CASE WHEN launch_way = '点击push' THEN did END) AS "uv_点击push",
    COUNT(DISTINCT CASE WHEN launch_way = '新全搜调起' THEN did END) AS "uv_新全搜调起",
    COUNT(DISTINCT CASE WHEN launch_way = '内容中心' THEN did END) AS "uv_内容中心",
    COUNT(DISTINCT CASE WHEN launch_way = '其他' THEN did END) AS "uv_其他"
FROM module_launch
GROUP BY module_level1
ORDER BY uv_total DESC;


-- ========== 补充：各模块内启动方式占比（横向看流量来源结构） ==========
WITH module_launch AS (
    SELECT
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
        END AS module_level1,
        CASE
            WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
            WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
            ELSE '其他'
        END AS launch_way
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
      AND app_launch_way IS NOT NULL AND app_launch_way != ''
)

SELECT
    module_level1,
    launch_way,
    COUNT(DISTINCT did) AS uv,
    ROUND(COUNT(DISTINCT did) * 100.0 / SUM(COUNT(DISTINCT did)) OVER (PARTITION BY module_level1), 2) AS launch_way_ratio_in_module
FROM module_launch
GROUP BY module_level1, launch_way
ORDER BY module_level1, uv DESC;
