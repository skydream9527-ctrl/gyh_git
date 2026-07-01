SELECT 
    event_name,
    properties['page'] AS page,
    properties['feed_channel'] AS feed_channel,
    properties['duration'] AS duration,
    COUNT(*) AS cnt
FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE date = 20260628
  AND pkg = 'com.android.browser'
  AND event_name IN ('page_expo_view_new', 'content_duration_new')
  AND COALESCE(DISTINCT_ID, '') != ''
GROUP BY 1, 2, 3, 4
ORDER BY cnt DESC
LIMIT 100;
