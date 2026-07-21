SELECT
    page,
    COUNT(DISTINCT uv_did) AS uv_7d,
    ROUND(SUM(dura_ms) / 60000.0, 0) AS total_dura_min_7d,
    ROUND(SUM(dura_ms) / COUNT(DISTINCT uv_did) / 60000.0, 2) AS dura_per_user_min
FROM (
    SELECT
        properties['page'] AS page,
        CASE WHEN event_name IN ('page_expo_view_new', 'content_duration_new') THEN DISTINCT_ID ELSE NULL END AS uv_did,
        CASE WHEN event_name = 'content_duration_new' THEN CAST(properties['duration'] AS DOUBLE) ELSE 0 END AS dura_ms
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name IN ('page_expo_view_new', 'content_duration_new')
      AND properties['page'] IS NOT NULL
      AND COALESCE(DISTINCT_ID, '') != ''
) t
GROUP BY page
ORDER BY uv_7d DESC;
