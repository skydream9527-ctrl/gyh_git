SELECT
    feed_channel,
    COUNT(DISTINCT uv_did) AS uv_7d,
    ROUND(SUM(dura_ms) / 60000.0, 0) AS total_dura_min_7d,
    ROUND(SUM(dura_ms) / COUNT(DISTINCT uv_did) / 60000.0, 2) AS dura_per_user_min
FROM (
    SELECT
        COALESCE(properties['feed_channel'], '未知') AS feed_channel,
        CASE WHEN event_name IN ('page_expo_view_new', 'content_duration_new') THEN DISTINCT_ID ELSE NULL END AS uv_did,
        CASE WHEN event_name = 'content_duration_new' THEN CAST(properties['duration'] AS DOUBLE) ELSE 0 END AS dura_ms
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name IN ('page_expo_view_new', 'content_duration_new')
      AND properties['page'] IN (
        'feed_info_rec','feed_info_topnews','feed_info_hotList','feed_info_broworldcup',
        'feed_info_videos','feed_info_skit','feed_info_novels','feed_info_shortVideo',
        'feed_minivideo_continuously','feed_info_location','feed_info_sport','feed_info_gaokaov2',
        'feed_info_game','feed_info_science','feed_info_entertainment','feed_info_emotion',
        'feed_info_car','feed_info_property','feed_info_international','feed_info_military',
        'feed_info_finance','feed_info_education','feed_info_society','feed_info_culture',
        'feed_info_history','feed_info_household','feed_info_tourism','feed_info_food',
        'feed_info_fashion','feed_info_parenting','feed_info_health','feed_info_constellations',
        'feed_info_newera','feed_content_detail','feed_video_immersion','lightapp_skit_detail',
        'feed_shortvideo_immerse','duokan_sdk_reader_page','novel_home_tab_page'
      )
      AND COALESCE(DISTINCT_ID, '') != ''
      AND NOT (properties['page'] = 'feed_minivideo_continuously' AND properties['feed_channel'] = '视频底tab小视频')
) t
GROUP BY feed_channel
ORDER BY uv_7d DESC;
