-- =====================================================
-- 0630 浏览器流量地图 - Part01: 一级模块大盘 PV/UV/时长
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 模块分类：9类一级模块（沿用629版精细映射）
-- 时长口径：app_dura 为APP总时长，group by page后会重复累加，仅作群体画像参考
--           对比模块价值时，信息流时长请参考 Part04-06 的 feed_dura+consum_dura 口径
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：7天汇总（按模块排序） ==========
WITH page_module_mapping AS (
    SELECT
        did,
        page,
        expos_cnt,
        app_dura,
        CASE
            -- 1_首页
            WHEN page IN ('home', 'home_concise', 'default') THEN '1_首页'
            -- 2_信息流（核心模块）
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
        END AS module_level1
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
      AND page IS NOT NULL AND page != ''
),

total_dau_7d AS (
    SELECT COUNT(DISTINCT did) AS total_dau
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
)

SELECT
    m.module_level1,
    COUNT(DISTINCT m.did) AS uv_7d,
    SUM(m.expos_cnt) AS pv_7d,
    ROUND(SUM(m.expos_cnt) * 1.0 / COUNT(DISTINCT m.did), 2) AS pv_per_user_7d,
    ROUND(COUNT(DISTINCT m.did) * 100.0 / (SELECT total_dau FROM total_dau_7d), 2) AS uv_ratio_in_dau,
    -- 时长：访问该模块用户的APP总时长（注意：同一用户访问多模块会重复累加，仅作群体画像参考）
    CAST(SUM(CASE WHEN m.app_dura > 0 THEN m.app_dura END) AS BIGINT) / 60000 AS app_dura_sum_min,
    CASE WHEN COUNT(DISTINCT m.did) >= 500000 THEN '✅ 大模块' ELSE '' END AS is_large_module
FROM page_module_mapping m
GROUP BY m.module_level1
ORDER BY uv_7d DESC;


-- ========== 查询2：分天趋势（看波动） ==========
WITH page_module_mapping AS (
    SELECT
        date,
        did,
        page,
        expos_cnt,
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
),

daily_dau AS (
    SELECT date, COUNT(DISTINCT did) AS total_dau
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND app_open_cnt > 0
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
    GROUP BY date
),

module_daily AS (
    SELECT
        p.date,
        p.module_level1,
        COUNT(DISTINCT p.did) AS uv,
        SUM(p.expos_cnt) AS pv
    FROM page_module_mapping p
    GROUP BY p.date, p.module_level1
)

SELECT
    m.date,
    m.module_level1,
    m.uv,
    m.pv,
    ROUND(m.pv * 1.0 / m.uv, 2) AS pv_per_user,
    ROUND(m.uv * 100.0 / d.total_dau, 2) AS uv_ratio_in_dau,
    d.total_dau
FROM module_daily m
JOIN daily_dau d ON m.date = d.date
ORDER BY m.date, m.uv DESC;
