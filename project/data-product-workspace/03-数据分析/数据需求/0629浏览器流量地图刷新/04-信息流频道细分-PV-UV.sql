-- =====================================================
-- 0629 浏览器流量地图刷新 - Part2: 信息流频道细分（支撑频道重构）
-- 时间范围：2026-06-22 ~ 2026-06-28（最近7天）
-- 指标：UV、PV（曝光）、人均PV、占信息流总流量比例、人均消费时长
-- 目标：找出长尾低流量频道，支撑频道收束重构
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

WITH feed_channel_base AS (
    SELECT
        date,
        did,
        feed_channel,
        SUM(expos_cnt) AS expos_cnt,
        SUM(click_cnt) AS click_cnt,
        SUM(CASE WHEN feed_status = 'true' THEN feed_dura ELSE 0 END) AS feed_dura_ms
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND COALESCE(did, '') != ''
      AND is_app_dau_2024 = 1
      AND feed_channel IS NOT NULL AND feed_channel != ''
      AND feed_channel != '未知' -- 过滤未知
      AND is_top = 0 -- 非置顶内容，自然流量
    GROUP BY date, did, feed_channel
),

-- 信息流总流量（用于计算占比）
feed_total AS (
    SELECT
        COUNT(DISTINCT did) AS feed_dau_7d,
        SUM(expos_cnt) AS total_expos_7d
    FROM feed_channel_base
)

-- 7天各频道汇总，按UV排序
SELECT
    c.feed_channel,
    COUNT(DISTINCT c.did) AS uv_7d,
    SUM(c.expos_cnt) AS pv_expos_7d,
    SUM(c.click_cnt) AS click_7d,
    ROUND(SUM(c.feed_dura_ms) / COUNT(DISTINCT c.did) / 60000, 2) AS avg_duration_min_per_user,
    ROUND(SUM(c.expos_cnt) * 1.0 / COUNT(DISTINCT c.did), 2) AS pv_per_user,
    ROUND(SUM(c.click_cnt) * 100.0 / NULLIF(SUM(c.expos_cnt), 0), 2) AS ctr,
    ROUND(COUNT(DISTINCT c.did) * 100.0 / (SELECT feed_dau_7d FROM feed_total), 2) AS uv_ratio_in_feed,
    ROUND(SUM(c.expos_cnt) * 100.0 / (SELECT total_expos_7d FROM feed_total), 2) AS pv_ratio_in_feed,
    CASE
        WHEN COUNT(DISTINCT c.did) >= 1000000 THEN '🔴 核心频道（≥1000万UV）'
        WHEN COUNT(DISTINCT c.did) >= 1000000 THEN '🟠 重要频道（100-1000万UV）'
        WHEN COUNT(DISTINCT c.did) >= 100000 THEN '🟡 腰部频道（10-100万UV）'
        ELSE '🟢 长尾频道（<10万UV）'
    END AS channel_tier
FROM feed_channel_base c
GROUP BY c.feed_channel
ORDER BY uv_7d DESC;


-- =====================================================
-- 补充：分天趋势，看各频道稳定性
-- =====================================================
SELECT
    date,
    feed_channel,
    COUNT(DISTINCT did) AS uv,
    SUM(expos_cnt) AS pv_expos
FROM feed_channel_base
WHERE feed_channel IN ('推荐', '热点', '视频', 'push', '发现', '热榜', '文章详情页相关推荐') -- 先看头部频道天级趋势
GROUP BY date, feed_channel
ORDER BY date, uv DESC;
