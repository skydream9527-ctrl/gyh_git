SELECT
    page,
    feed_channel,
    COUNT(DISTINCT uv_did) AS uv_7d,
    ROUND(SUM(dura_ms) / 60000.0, 0) AS total_dura_min_7d
FROM (
    SELECT
        properties['page'] AS page,
        COALESCE(properties['feed_channel'], '未知') AS feed_channel,
        CASE WHEN event_name IN ('page_expo_view_new', 'content_duration_new') THEN DISTINCT_ID ELSE NULL END AS uv_did,
        CASE WHEN event_name = 'content_duration_new' THEN CAST(properties['duration'] AS DOUBLE) ELSE 0 END AS dura_ms
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name IN ('page_expo_view_new', 'content_duration_new')
      AND properties['page'] IN (
        'feed_info_rec','feed_info_topnews','feed_info_hotList','feed_info_videos',
        'feed_info_skit','feed_info_novels','feed_info_shortVideo',
        'feed_content_detail','feed_video_immersion','lightapp_skit_detail',
        'feed_minivideo_continuously','feed_shortvideo_immerse'
      )
      AND COALESCE(DISTINCT_ID, '') != ''
) t
GROUP BY page, feed_channel
ORDER BY page, uv_7d DESC;
