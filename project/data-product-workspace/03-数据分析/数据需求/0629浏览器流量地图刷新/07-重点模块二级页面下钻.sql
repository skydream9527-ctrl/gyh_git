-- =====================================================
-- 0629 浏览器流量地图刷新 - Part5: 重点模块二级页面下钻
-- 覆盖模块：信息流、搜索、视频、小说
-- 时间范围：2026-06-22 ~ 2026-06-28（最近7天）
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

WITH page_base AS (
    SELECT
        page,
        did,
        SUM(expos_cnt) AS expos_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
      AND page IS NOT NULL AND page != ''
    GROUP BY page, did
),

-- 先标记一级模块和二级页面
page_classify AS (
    SELECT
        page,
        did,
        expos_cnt,
        -- 一级模块
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
            ELSE '其他'
        END AS module_level1,
        -- 二级页面分类
        CASE
            -- ========== 信息流二级 ==========
            WHEN page = 'feed_info_rec' THEN '2-1_推荐主feed'
            WHEN page LIKE 'feed_info_topnews%' THEN '2-2_热点feed'
            WHEN page LIKE 'feed_content_detail%' OR page = 'immersion_news_detail' THEN '2-3_内容详情/沉浸阅读'
            WHEN page LIKE 'feed_info_hotList%' OR page = 'home_hot_list_immersion' THEN '2-4_热榜'
            WHEN page LIKE 'feed_info_videos%' OR page LIKE 'feed_info_shortVideo%' OR page = 'feed_minivideo_continuously_root' THEN '2-5_信息流内视频/小视频'
            WHEN page LIKE 'feed_info_novels%' THEN '2-6_信息流内小说tab'
            WHEN page LIKE 'feed_info_skit%' OR page LIKE 'lightapp_skit_detail%' THEN '2-7_短剧'
            WHEN page LIKE 'feed_info_sport%' OR page LIKE 'feed_info_broworldcup%' OR page LIKE 'feed_info_location%' THEN '2-8_垂类频道(体育/本地/世界杯等)'
            WHEN page LIKE 'author_profile%' THEN '2-9_作者主页'
            WHEN page LIKE 'topic_banner_detail%' THEN '2-10_专题页'
            WHEN page LIKE 'feed_livestream%' THEN '2-11_直播'
            WHEN page LIKE 'feed_info_%' THEN '2-12_其他信息流频道'

            -- ========== 搜索二级 ==========
            WHEN page = 'search_home' THEN '3-1_搜索主页/入口'
            WHEN page LIKE 'search_result%' THEN '3-2_搜索结果页'
            WHEN page LIKE 'search_sug%' THEN '3-3_搜索建议/联想'
            WHEN page LIKE 'ai_search%' THEN '3-4_AI搜索'
            WHEN page LIKE 'search_history%' THEN '3-5_搜索历史'
            WHEN page LIKE 'search_%' THEN '3-6_其他搜索页面'

            -- ========== 视频二级 ==========
            WHEN page LIKE 'feed_video_immersion%' THEN '4-1_沉浸式视频播放'
            WHEN page = 'feed_minivideo_continuously' OR page LIKE 'feed_shortvideo_immerse%' THEN '4-2_小视频/短视频沉浸式流'
            WHEN page LIKE 'lightapp_skit_detail%' THEN '4-3_短剧播放页'
            WHEN page LIKE 'video%' OR page LIKE '%video%' THEN '4-4_其他视频页面'

            -- ========== 小说二级 ==========
            WHEN page LIKE '%novel_home%' OR page LIKE '%novel_shelf%' OR page LIKE '%novel%' AND NOT (page LIKE '%reader%' OR page LIKE '%listen%') THEN '5-1_小说主页/书架'
            WHEN page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page') OR page LIKE '%novel_reader%' THEN '5-2_小说阅读页'
            WHEN page IN ('listen_page', 'listen_news_page') OR page LIKE '%listen%' THEN '5-3_听书/听新闻页'
            WHEN page LIKE '%novel%' THEN '5-4_其他小说页面'

            ELSE '其他'
        END AS page_level2
    FROM page_base
)

-- 最终统计：按一级模块→二级页面聚合UV、PV
SELECT
    module_level1,
    page_level2,
    COUNT(DISTINCT did) AS uv_7d,
    SUM(expos_cnt) AS pv_expos_7d,
    ROUND(SUM(expos_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS pv_per_user,
    ROUND(COUNT(DISTINCT did) * 100.0 / SUM(COUNT(DISTINCT did)) OVER (PARTITION BY module_level1), 2) AS uv_ratio_in_module
FROM page_classify
WHERE module_level1 IN ('2_信息流', '3_搜索', '4_视频', '5_小说')
GROUP BY module_level1, page_level2
ORDER BY module_level1, uv_7d DESC;
