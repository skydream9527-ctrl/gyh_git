-- =====================================================
-- 0630 浏览器流量地图 - Part04: 信息流页面细分 UV/PV/时长
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 分析粒度：信息流模块按 page 字段细分
-- 时长口径：feed_dura（列表页时长）+ consum_dura（详情页消费时长），单位分钟
--           参考官方口径：https://mi.feishu.cn/wiki/C0J0w7MksizOJWkYQ3vcrWarn4g
-- 注意：本查询看全量信息流页面流量（不过滤is_top），有效消费口径见Part07
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：7天汇总（按page排序） ==========
SELECT
    page,
    COUNT(DISTINCT did) AS uv_7d,
    SUM(expos_cnt) AS pv_7d,
    ROUND(SUM(expos_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS pv_per_user,
    -- 信息流时长：列表页时长 + 详情页消费时长（官方口径）
    CAST(SUM(feed_dura) AS BIGINT) / 60000 AS feed_dura_min,
    CAST(SUM(consum_dura) AS BIGINT) / 60000 AS consum_dura_min,
    CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000 AS total_dura_min,
    ROUND(CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000.0 / COUNT(DISTINCT did), 2) AS dura_per_user_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND page IS NOT NULL AND page != ''
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
GROUP BY page
ORDER BY uv_7d DESC;


-- ========== 查询2：分天趋势 ==========
SELECT
    date,
    page,
    COUNT(DISTINCT did) AS uv,
    SUM(expos_cnt) AS pv,
    CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000 AS total_dura_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND page IS NOT NULL AND page != ''
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
GROUP BY date, page
ORDER BY date, uv DESC;
