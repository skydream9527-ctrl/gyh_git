-- =====================================================
-- 0629 浏览器流量地图刷新 - Part3: 各模块下启动方式拆分
-- 目标：看每个模块的用户中，各种启动方式的占比构成
-- 时间范围：2026-06-22 ~ 2026-06-28（最近7天）
-- 说明：用户一天内可能有多种启动方式，标签非互斥，占比之和>100%为正常
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

WITH -- 第一步：给每个用户每天标记启动方式标签
user_launch_label AS (
    SELECT
        date,
        did,
        -- 是否有push启动
        MAX(CASE WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN 1 ELSE 0 END) AS is_push,
        -- 是否有三方调起
        MAX(CASE WHEN app_launch_way = '第三方调起' THEN 1 ELSE 0 END) AS is_third_party,
        -- 是否有搜索入口启动
        MAX(CASE WHEN app_launch_way IN ('新全搜调起', 'newhome搜索框', 'newhome搜索调起', 'newhome搜索按钮', 'newhome信息流搜索light', 'newhome信息流搜索chose', '全搜调起', '桌面框调起') THEN 1 ELSE 0 END) AS is_search_launch,
        -- 是否有主启
        MAX(CASE WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN 1 ELSE 0 END) AS is_main_launch,
        -- 计算该用户当天总启动次数，用于确定主要启动方式
        SUM(app_open_cnt) AS total_open_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date, did
),

-- 第二步：用户主要启动方式（互斥分类，用于计算占比，优先级：push > 三方 > 搜索 > 主启 > 其他）
user_primary_launch AS (
    SELECT
        date,
        did,
        CASE
            WHEN is_push = 1 THEN '3_Push启动'
            WHEN is_third_party = 1 THEN '2_三方调起'
            WHEN is_search_launch = 1 THEN '4_搜索入口'
            WHEN is_main_launch = 1 THEN '1_主启'
            ELSE '5_其他入口'
        END AS primary_launch_type,
        is_push,
        is_third_party,
        is_search_launch,
        is_main_launch
    FROM user_launch_label
),

-- 第三步：用户模块访问映射
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
      AND is_app_dau_2024 = 1
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

-- 关联用户启动方式和模块访问
module_launch AS (
    SELECT
        m.date,
        m.did,
        m.module_level1,
        l.primary_launch_type,
        l.is_push,
        l.is_third_party,
        l.is_search_launch,
        l.is_main_launch
    FROM page_module_mapping m
    JOIN user_primary_launch l
      ON m.date = l.date
     AND m.did = l.did
)

-- =====================================================
-- 结果1：按主要启动方式拆分，每个模块中各启动方式用户占比（互斥，占比和=100%）
-- =====================================================
SELECT
    module_level1,
    primary_launch_type,
    COUNT(DISTINCT did) AS uv,
    ROUND(COUNT(DISTINCT did) * 100.0 / SUM(COUNT(DISTINCT did)) OVER (PARTITION BY module_level1), 2) AS ratio_in_module
FROM module_launch
GROUP BY module_level1, primary_launch_type
ORDER BY module_level1, uv DESC;


-- =====================================================
-- 结果2：非互斥标签，看每个模块中，有多少比例的用户是push/三方/搜索/主启动用户（占比可超100%）
-- =====================================================
-- SELECT
--     module_level1,
--     COUNT(DISTINCT did) AS total_uv,
--     ROUND(SUM(is_push) * 100.0 / COUNT(DISTINCT did), 2) AS push_user_ratio,
--     ROUND(SUM(is_third_party) * 100.0 / COUNT(DISTINCT did), 2) AS third_party_user_ratio,
--     ROUND(SUM(is_search_launch) * 100.0 / COUNT(DISTINCT did), 2) AS search_user_ratio,
--     ROUND(SUM(is_main_launch) * 100.0 / COUNT(DISTINCT did), 2) AS main_launch_user_ratio
-- FROM module_launch
-- GROUP BY module_level1
-- ORDER BY total_uv DESC;
