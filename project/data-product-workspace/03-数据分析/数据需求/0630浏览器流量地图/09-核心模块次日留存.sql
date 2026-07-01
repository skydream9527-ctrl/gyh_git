-- =====================================================
-- 0630 浏览器流量地图 - Part09: 核心模块次日留存
-- 时间范围：首日 2026-06-22 ~ 2026-06-27（6天），次日 2026-06-23 ~ 2026-06-28
-- 留存口径：
--   1. APP次日留存：访问该模块的用户，次日是否回访APP
--   2. 模块次日留存：访问该模块的用户，次日是否再次访问该模块
-- 信息流模块留存：使用官方有效用户口径（见Part07）
-- 其他模块留存：按page映射的9类模块口径
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：各模块次日留存（6天平均，非信息流模块用page映射口径） ==========
-- 注意：信息流模块的有效用户留存见查询2

WITH
-- 首日访问各模块的用户
first_day_module_users AS (
    SELECT
        date AS first_date,
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
    WHERE date BETWEEN 20260622 AND 20260627
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
    GROUP BY 1, 2, 3
),

-- 次日回访APP的用户（次日是否打开APP）
next_day_app_dau AS (
    SELECT
        date - 1 AS first_date,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260623 AND 20260628
      AND app_open_cnt > 0
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
    GROUP BY 1, 2
),

-- 次日再次访问该模块的用户
next_day_module_users AS (
    SELECT
        date - 1 AS first_date,
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
    WHERE date BETWEEN 20260623 AND 20260628
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
      AND page IS NOT NULL AND page != ''
    GROUP BY 1, 2, 3
)

-- 6天平均次日留存
SELECT
    f.module_level1,
    COUNT(DISTINCT f.did) AS first_day_uv,
    -- APP次日留存
    COUNT(DISTINCT n.did) AS next_day_app_uv,
    ROUND(COUNT(DISTINCT n.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS app_next_day_retain_rate,
    -- 模块次日留存
    COUNT(DISTINCT nm.did) AS next_day_module_uv,
    ROUND(COUNT(DISTINCT nm.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS module_next_day_retain_rate
FROM first_day_module_users f
LEFT JOIN next_day_app_dau n
    ON f.first_date = n.first_date AND f.did = n.did
LEFT JOIN next_day_module_users nm
    ON f.first_date = nm.first_date AND f.did = nm.did AND f.module_level1 = nm.module_level1
GROUP BY f.module_level1
ORDER BY app_next_day_retain_rate DESC;


-- ========== 查询2：信息流有效用户次日留存（官方口径） ==========
-- 信息流有效用户定义见Part07，这里计算有效用户的APP次日留存

WITH
-- 首日信息流有效用户
first_day_feed_valid AS (
    SELECT
        date AS first_date,
        did
    FROM (
        SELECT
            date,
            did,
            MAX(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true', 1, 0)) AS is_slide,
            SUM(IF(
                COALESCE(item_type,'') NOT IN ('novel','shortstory')
                OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                    AND (
                        (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                        OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                    )
                ),
                consum_cnt_v2, 0
            )) AS consum_cnt_v2,
            SUM(IF(
                feed_channel IN ('热点','推荐','profile','profile_djy','push')
                OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566672|1960891|2316339|2316341|1643918') AND item_docid RLIKE 'djy')
                OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566673|1960892|2316340|1960893|1643917') AND item_docid RLIKE 'toutiao'),
                expos_cnt, 0
            )) AS expose_cnt
        FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
        WHERE date BETWEEN 20260622 AND 20260627
          AND is_app_dau_2024 = 1
          AND is_top = 0
          AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
        GROUP BY 1, 2
    ) a
    WHERE consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)
),

-- 次日回访APP的用户
next_day_app_dau AS (
    SELECT
        date - 1 AS first_date,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260623 AND 20260628
      AND app_open_cnt > 0
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
    GROUP BY 1, 2
),

-- 次日仍是信息流有效用户的
next_day_feed_valid AS (
    SELECT
        date - 1 AS first_date,
        did
    FROM (
        SELECT
            date,
            did,
            MAX(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true', 1, 0)) AS is_slide,
            SUM(IF(
                COALESCE(item_type,'') NOT IN ('novel','shortstory')
                OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                    AND (
                        (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                        OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                    )
                ),
                consum_cnt_v2, 0
            )) AS consum_cnt_v2,
            SUM(IF(
                feed_channel IN ('热点','推荐','profile','profile_djy','push')
                OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566672|1960891|2316339|2316341|1643918') AND item_docid RLIKE 'djy')
                OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566673|1960892|2316340|1960893|1643917') AND item_docid RLIKE 'toutiao'),
                expos_cnt, 0
            )) AS expose_cnt
        FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
        WHERE date BETWEEN 20260623 AND 20260628
          AND is_app_dau_2024 = 1
          AND is_top = 0
          AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
        GROUP BY 1, 2
    ) a
    WHERE consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)
)

-- 6天平均次日留存
SELECT
    '信息流有效用户' AS module,
    COUNT(DISTINCT f.did) AS first_day_uv,
    -- APP次日留存
    COUNT(DISTINCT n.did) AS next_day_app_uv,
    ROUND(COUNT(DISTINCT n.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS app_next_day_retain_rate,
    -- 信息流有效用户次日留存
    COUNT(DISTINCT nf.did) AS next_day_feed_valid_uv,
    ROUND(COUNT(DISTINCT nf.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS feed_valid_next_day_retain_rate
FROM first_day_feed_valid f
LEFT JOIN next_day_app_dau n
    ON f.first_date = n.first_date AND f.did = n.did
LEFT JOIN next_day_feed_valid nf
    ON f.first_date = nf.first_date AND f.did = nf.did;
