-- 埋点监控指标查询 SQL
-- 用于分析版本灰度期间的视频播放和消费时长等监控指标
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with base_data as (
    select 
        date,
        did,
        app_ver,
        is_new_feed_2024,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_video_play_tally,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video'), video_over_cnt, 0)) as mini_video_over_tally,
        sum(if (lower(item_type) in ('vertical_video', 'mini_video') and duration_type ='detail_page', feed_dura, 0)) as mini_detail_dur,
        sum(if (lower(item_type)='inline_video', video_play_cnt, 0)) as short_video_play_tally,
        sum(if (lower(item_type)='inline_video', video_over_cnt, 0)) as short_video_over_tally,
        sum(if (lower(item_type)='inline_video', video_over_event_dura, 0)) as short_feed_dur,
        sum(if (lower(item_type)='news', view_quit_cnt, 0)) as news_view_tally,
        sum(if (lower(item_type)='news', view_event_dura, 0)) as news_detail_dur
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and feed_status in ('true', 'false')
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_feed_2024
),
base as ( 
    SELECT 
        date,
        did as distinct_id, 
        app_ver, 
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        mini_video_play_tally, 
        mini_video_over_tally, 
        mini_detail_dur, 
        short_video_play_tally, 
        short_video_over_tally, 
        short_feed_dur, 
        news_detail_dur, 
        news_view_tally 
    from 
        base_data
), 
base_all as ( 
    select 
        date,
        distinct_id, 
        app_ver, 
        '大盘用户' as user_type, 
        mini_video_play_tally, 
        mini_video_over_tally, 
        mini_detail_dur, 
        short_video_play_tally, 
        short_video_over_tally, 
        short_feed_dur, 
        news_detail_dur, 
        news_view_tally 
    from 
        base 
    union all 
    select 
        date,
        * 
    from 
        base 
) 

SELECT 
    date,
    user_type, 
    app_ver, 
    if (paly_rate>1, 1, paly_rate) as paly_rate, 
    mini_avg_dur, 
    short_avg_dur, 
    avg_xiaofei_dur 
from 
    ( 
        select 
            date,
            user_type, 
            app_ver, 
            (sum(mini_video_over_tally)+sum(short_video_over_tally))/(sum(mini_video_play_tally)+sum(short_video_play_tally)) as paly_rate, 
            sum(mini_detail_dur)/(sum(mini_video_over_tally)*60000) as mini_avg_dur, 
            sum(short_feed_dur)/(sum(short_video_over_tally)*60000) as short_avg_dur, 
            (sum(news_detail_dur)+sum(mini_detail_dur)+sum(short_feed_dur))/((sum(news_view_tally)+sum(mini_video_over_tally)+sum(short_video_over_tally))*60000) as avg_xiaofei_dur 
        from 
            base_all 
        group by 
            date,
            user_type, 
            app_ver 
    ) tmp
