-- 浏览器DAU查询
-- 指标ID: BM001
-- 时间范围: 20260407 ~ 20260413 (最近7天)
-- 生成时间: 2026-04-14 14:58:00

SELECT
    date,
    COUNT(DISTINCT did) AS uv
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date >= 20260407
    AND date <= 20260413
    AND is_app_dau_2024 = 1
GROUP BY
    date
ORDER BY
    date
;
