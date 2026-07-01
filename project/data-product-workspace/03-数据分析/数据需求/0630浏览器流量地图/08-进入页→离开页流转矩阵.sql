-- =====================================================
-- 0630 浏览器流量地图 - Part08: 进入页→离开页 流转矩阵
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 数据源：神策事件明细表 dwd_ot_event_di_31000000442
-- 逻辑：通过 sessionId 关联 app_open（进入页）和 app_duration（离开页）事件
-- 模块映射：9类一级模块（与Part01一致）
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- 模块映射函数（9类，与Part01一致）
-- 1_首页 / 2_信息流 / 3_搜索 / 4_视频 / 5_小说 / 6_个人中心 / 7_书签历史 / 8_网页浏览 / 9_其他


-- ========== 查询1：进入页→离开页 流转矩阵（7天汇总） ==========
SELECT
    a.page AS page_open,
    b.page AS page_quit,
    COUNT(DISTINCT a.distinct_id) AS did_cnt
FROM
(
    -- 进入页：app_open 事件的 page
    SELECT
        date,
        DISTINCT_ID AS distinct_id,
        properties.sessionId AS sessionId,
        CASE
            WHEN properties.page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN properties.page LIKE 'feed_info_%'
              OR properties.page LIKE 'feed_content_detail%'
              OR properties.page LIKE 'immersion_news_detail%'
              OR properties.page LIKE 'feed_livestream%'
              OR properties.page LIKE 'author_profile%'
              OR properties.page LIKE 'topic_banner_detail%'
              OR properties.page = 'feed_minivideo_continuously_root'
              OR properties.page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN properties.page LIKE 'search_%' OR properties.page LIKE 'ai_search%' THEN '3_搜索'
            WHEN properties.page LIKE 'feed_video_immersion%'
              OR properties.page = 'feed_minivideo_continuously'
              OR properties.page LIKE 'feed_shortvideo_immerse%'
              OR properties.page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN properties.page LIKE '%novel%'
              OR properties.page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN properties.page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN properties.page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN properties.page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END AS page
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name = 'app_open'
      AND properties.page IS NOT NULL
    GROUP BY 1, 2, 3,
        CASE
            WHEN properties.page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN properties.page LIKE 'feed_info_%'
              OR properties.page LIKE 'feed_content_detail%'
              OR properties.page LIKE 'immersion_news_detail%'
              OR properties.page LIKE 'feed_livestream%'
              OR properties.page LIKE 'author_profile%'
              OR properties.page LIKE 'topic_banner_detail%'
              OR properties.page = 'feed_minivideo_continuously_root'
              OR properties.page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN properties.page LIKE 'search_%' OR properties.page LIKE 'ai_search%' THEN '3_搜索'
            WHEN properties.page LIKE 'feed_video_immersion%'
              OR properties.page = 'feed_minivideo_continuously'
              OR properties.page LIKE 'feed_shortvideo_immerse%'
              OR properties.page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN properties.page LIKE '%novel%'
              OR properties.page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN properties.page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN properties.page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN properties.page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END
) a
LEFT JOIN
(
    -- 离开页：app_duration 事件的 page
    SELECT
        date,
        DISTINCT_ID AS distinct_id,
        properties.sessionId AS sessionId,
        CASE
            WHEN properties.page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN properties.page LIKE 'feed_info_%'
              OR properties.page LIKE 'feed_content_detail%'
              OR properties.page LIKE 'immersion_news_detail%'
              OR properties.page LIKE 'feed_livestream%'
              OR properties.page LIKE 'author_profile%'
              OR properties.page LIKE 'topic_banner_detail%'
              OR properties.page = 'feed_minivideo_continuously_root'
              OR properties.page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN properties.page LIKE 'search_%' OR properties.page LIKE 'ai_search%' THEN '3_搜索'
            WHEN properties.page LIKE 'feed_video_immersion%'
              OR properties.page = 'feed_minivideo_continuously'
              OR properties.page LIKE 'feed_shortvideo_immerse%'
              OR properties.page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN properties.page LIKE '%novel%'
              OR properties.page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN properties.page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN properties.page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN properties.page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END AS page
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name = 'app_duration'
      AND properties.page IS NOT NULL
    GROUP BY 1, 2, 3,
        CASE
            WHEN properties.page IN ('home', 'home_concise', 'default') THEN '1_首页'
            WHEN properties.page LIKE 'feed_info_%'
              OR properties.page LIKE 'feed_content_detail%'
              OR properties.page LIKE 'immersion_news_detail%'
              OR properties.page LIKE 'feed_livestream%'
              OR properties.page LIKE 'author_profile%'
              OR properties.page LIKE 'topic_banner_detail%'
              OR properties.page = 'feed_minivideo_continuously_root'
              OR properties.page = 'home_hot_list_immersion'
                THEN '2_信息流'
            WHEN properties.page LIKE 'search_%' OR properties.page LIKE 'ai_search%' THEN '3_搜索'
            WHEN properties.page LIKE 'feed_video_immersion%'
              OR properties.page = 'feed_minivideo_continuously'
              OR properties.page LIKE 'feed_shortvideo_immerse%'
              OR properties.page LIKE 'lightapp_skit_detail%'
                THEN '4_视频'
            WHEN properties.page LIKE '%novel%'
              OR properties.page IN ('阅读页', '阅读扉页', 'duokan_sdk_reader_page', 'listen_page', 'listen_news_page')
                THEN '5_小说'
            WHEN properties.page IN ('me', 'mibrowser_dispatcher') THEN '6_个人中心'
            WHEN properties.page LIKE 'bookmark_%' THEN '7_书签历史'
            WHEN properties.page IN ('web_page', 'base_web_SimpleWebView', 'webapps_pwa') THEN '8_网页浏览'
            ELSE '9_其他'
        END
) b
ON a.distinct_id = b.distinct_id
   AND a.sessionId = b.sessionId
   AND a.date = b.date
GROUP BY a.page, b.page
ORDER BY did_cnt DESC;
