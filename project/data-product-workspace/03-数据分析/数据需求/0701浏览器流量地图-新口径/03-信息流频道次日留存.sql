WITH
first_day_channel_users AS (
    SELECT
        date AS first_date,
        DISTINCT_ID AS did,
        COALESCE(properties['feed_channel'], '未知') AS feed_channel
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260622 AND 20260627
      AND pkg = 'com.android.browser'
      AND event_name = 'page_expo_view_new'
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
    GROUP BY 1, 2, 3
),
next_day_app_open AS (
    SELECT
        date - 1 AS first_date,
        DISTINCT_ID AS did
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260623 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name = 'app_open'
      AND COALESCE(DISTINCT_ID, '') != ''
    GROUP BY 1, 2
),
next_day_channel_users AS (
    SELECT
        date - 1 AS first_date,
        DISTINCT_ID AS did,
        COALESCE(properties['feed_channel'], '未知') AS feed_channel
    FROM iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
    WHERE date BETWEEN 20260623 AND 20260628
      AND pkg = 'com.android.browser'
      AND event_name = 'page_expo_view_new'
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
    GROUP BY 1, 2, 3
)
SELECT
    f.feed_channel,
    COUNT(DISTINCT f.did) AS first_day_uv_7d,
    COUNT(DISTINCT n.did) AS next_day_app_uv_7d,
    ROUND(COUNT(DISTINCT n.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS app_next_day_retain_rate,
    COUNT(DISTINCT nc.did) AS next_day_channel_uv_7d,
    ROUND(COUNT(DISTINCT nc.did) * 100.0 / COUNT(DISTINCT f.did), 2) AS channel_next_day_retain_rate
FROM first_day_channel_users f
LEFT JOIN next_day_app_open n
    ON f.first_date = n.first_date AND f.did = n.did
LEFT JOIN next_day_channel_users nc
    ON f.first_date = nc.first_date AND f.did = nc.did AND f.feed_channel = nc.feed_channel
GROUP BY f.feed_channel
HAVING COUNT(DISTINCT f.did) >= 100000
ORDER BY channel_next_day_retain_rate DESC;
