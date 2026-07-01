-- =====================================================
-- 0630 浏览器流量地图 - Part05: 信息流频道细分 UV/PV/时长
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 分析粒度：信息流模块按 feed_channel 字段细分
-- 时长口径：feed_dura + consum_dura（官方口径），单位分钟
-- 注意：本查询看全量信息流频道流量（不过滤is_top），有效消费口径见Part07
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：7天汇总（按频道排序） ==========
SELECT
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
  AND feed_channel IS NOT NULL AND feed_channel != ''
GROUP BY feed_channel
ORDER BY uv_7d DESC;


-- ========== 查询2：分天趋势 ==========
SELECT
    date,
    feed_channel,
    COUNT(DISTINCT did) AS uv,
    SUM(expos_cnt) AS pv,
    CAST(SUM(feed_dura) + SUM(consum_dura) AS BIGINT) / 60000 AS total_dura_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND feed_channel IS NOT NULL AND feed_channel != ''
GROUP BY date, feed_channel
ORDER BY date, uv DESC;
