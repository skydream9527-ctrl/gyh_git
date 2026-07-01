-- =====================================================
-- 0630 浏览器流量地图 - Part06: 信息流 page × feed_channel 双层下钻
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 分析粒度：信息流模块按 page × feed_channel 双层矩阵
-- 时长口径：feed_dura + consum_dura（官方口径），单位分钟
-- 注意：本查询看全量信息流流量（不过滤is_top），有效消费口径见Part07
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：7天汇总（page × channel 矩阵） ==========
SELECT
    page,
    feed_channel,
    COUNT(DISTINCT did) AS uv_7d,
    SUM(expos_cnt) AS pv_7d,
    ROUND(SUM(expos_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS pv_per_user,
    CAST(SUM(feed_dura) AS BIGINT) / 60000 AS feed_dura_min,
    CAST(SUM(consum_dura) AS BIGINT) / 60000 AS consum_dura_min,
    CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000 AS total_dura_min,
    ROUND(CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000.0 / COUNT(DISTINCT did), 2) AS dura_per_user_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND page IS NOT NULL AND page != ''
  AND feed_channel IS NOT NULL AND feed_channel != ''
  -- 信息流页面过滤
  AND (
      page LIKE 'feed_info_%'
      OR page LIKE 'feed_content_detail%'
      OR page LIKE 'immersion_news_detail%'
      OR page LIKE 'feed_livestream%'
      OR page LIKE 'author_profile%'
      OR page LIKE 'topic_banner_detail%'
      OR page = 'feed_minivideo_continuously_root'
      OR page = 'home_hot_list_immersion'
  )
GROUP BY page, feed_channel
ORDER BY uv_7d DESC;


-- ========== 查询2：以page为行、channel为列的UV透视表 ==========
SELECT
    page,
    COUNT(DISTINCT did) AS uv_total,
    COUNT(DISTINCT CASE WHEN feed_channel = '推荐' THEN did END) AS "uv_推荐",
    COUNT(DISTINCT CASE WHEN feed_channel = '热点' THEN did END) AS "uv_热点",
    COUNT(DISTINCT CASE WHEN feed_channel = '视频' THEN did END) AS "uv_视频",
    COUNT(DISTINCT CASE WHEN feed_channel = 'push' THEN did END) AS uv_push,
    COUNT(DISTINCT CASE WHEN feed_channel = '发现' THEN did END) AS "uv_发现",
    COUNT(DISTINCT CASE WHEN feed_channel = '热榜' THEN did END) AS "uv_热榜",
    COUNT(DISTINCT CASE WHEN feed_channel = '文章详情页相关推荐' THEN did END) AS "uv_文章详情页相关推荐",
    COUNT(DISTINCT CASE WHEN feed_channel NOT IN ('推荐','热点','视频','push','发现','热榜','文章详情页相关推荐') THEN did END) AS "uv_其他频道"
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND page IS NOT NULL AND page != ''
  AND feed_channel IS NOT NULL AND feed_channel != ''
  AND (
      page LIKE 'feed_info_%'
      OR page LIKE 'feed_content_detail%'
      OR page LIKE 'immersion_news_detail%'
      OR page LIKE 'feed_livestream%'
      OR page LIKE 'author_profile%'
      OR page LIKE 'topic_banner_detail%'
      OR page = 'feed_minivideo_continuously_root'
      OR page = 'home_hot_list_immersion'
  )
GROUP BY page
ORDER BY uv_total DESC;


-- ========== 查询3：以channel为行、page为列的UV透视表 ==========
SELECT
    feed_channel,
    COUNT(DISTINCT did) AS uv_total,
    COUNT(DISTINCT CASE WHEN page = 'feed_info_rec' THEN did END) AS uv_feed_info_rec,
    COUNT(DISTINCT CASE WHEN page = 'feed_info_topnews' THEN did END) AS uv_feed_info_topnews,
    COUNT(DISTINCT CASE WHEN page = 'feed_content_detail' THEN did END) AS uv_feed_content_detail,
    COUNT(DISTINCT CASE WHEN page = 'immersion_news_detail' THEN did END) AS uv_immersion_news_detail,
    COUNT(DISTINCT CASE WHEN page = 'feed_info_videos' THEN did END) AS uv_feed_info_videos,
    COUNT(DISTINCT CASE WHEN page = 'feed_info_hotList' THEN did END) AS uv_feed_info_hotList,
    COUNT(DISTINCT CASE WHEN page NOT IN ('feed_info_rec','feed_info_topnews','feed_content_detail','immersion_news_detail','feed_info_videos','feed_info_hotList') THEN did END) AS "uv_其他page"
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND page IS NOT NULL AND page != ''
  AND feed_channel IS NOT NULL AND feed_channel != ''
  AND (
      page LIKE 'feed_info_%'
      OR page LIKE 'feed_content_detail%'
      OR page LIKE 'immersion_news_detail%'
      OR page LIKE 'feed_livestream%'
      OR page LIKE 'author_profile%'
      OR page LIKE 'topic_banner_detail%'
      OR page = 'feed_minivideo_continuously_root'
      OR page = 'home_hot_list_immersion'
  )
GROUP BY feed_channel
ORDER BY uv_total DESC;
