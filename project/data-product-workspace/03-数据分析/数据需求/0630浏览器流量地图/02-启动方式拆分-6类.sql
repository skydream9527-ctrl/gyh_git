-- =====================================================
-- 0630 浏览器流量地图 - Part02: 启动方式拆分（6类，含内容中心）
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 启动方式分类：点击icon / 第三方调起 / 点击push / 新全搜调起 / 内容中心(newhome) / 其他
-- 时长口径：app_dura（APP总时长，注意重复累加问题）
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- ========== 查询1：7天汇总（按启动方式排序） ==========
SELECT
    CASE
        WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
        WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
        ELSE '其他'
    END AS launch_way,
    COUNT(DISTINCT did) AS uv_7d,
    CAST(SUM(CASE WHEN app_dura > 0 THEN app_dura END) AS BIGINT) / 60000 AS app_dura_sum_min,
    ROUND(COUNT(DISTINCT did) * 100.0 / SUM(COUNT(DISTINCT did)) OVER (), 2) AS uv_ratio
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND app_launch_way IS NOT NULL AND app_launch_way != ''
GROUP BY
    CASE
        WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
        WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
        ELSE '其他'
    END
ORDER BY uv_7d DESC;


-- ========== 查询2：分天趋势 ==========
SELECT
    date,
    CASE
        WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
        WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
        ELSE '其他'
    END AS launch_way,
    COUNT(DISTINCT did) AS uv,
    CAST(SUM(CASE WHEN app_dura > 0 THEN app_dura END) AS BIGINT) / 60000 AS app_dura_sum_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260622 AND 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
  AND app_launch_way IS NOT NULL AND app_launch_way != ''
GROUP BY date,
    CASE
        WHEN app_launch_way LIKE '%newhome%' THEN '内容中心'
        WHEN app_launch_way IN ('点击icon', '第三方调起', '点击push', '新全搜调起') THEN app_launch_way
        ELSE '其他'
    END
ORDER BY date, uv DESC;
