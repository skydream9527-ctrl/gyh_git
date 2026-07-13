-- 埋点监控指标查询 SQL（优化版）
-- 用于分析版本灰度期间的视频播放和消费时长等监控指标
-- 优化说明：合并对 dwm_browser_event_aggregation_label_di 表的多次查询

with base_data as (
    select 
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
        date=20260331 
        and feed_status in ('true', 'false')
    group by 
        did,
        app_ver,
        is_new_feed_2024
),
base as ( 
    SELECT 
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
        * 
    from 
        base 
) 

INSERT OVERWRITE table iceberg_zjyprc_hadoop.browser.browser_feeds_jiankong partition (date=20260331) 
SELECT 
    user_type, 
    app_ver, 
    if (paly_rate>1, 1, paly_rate) as paly_rate, 
    mini_avg_dur, 
    short_avg_dur, 
    avg_xiaofei_dur 
from 
    ( 
        select 
            user_type, 
            app_ver, 
            (sum(mini_video_over_tally)+sum(short_video_over_tally))/(sum(mini_video_play_tally)+sum(short_video_play_tally)) as paly_rate, 
            sum(mini_detail_dur)/(sum(mini_video_over_tally)*60000) as mini_avg_dur, 
            sum(short_feed_dur)/(sum(short_video_over_tally)*60000) as short_avg_dur, 
            (sum(news_detail_dur)+sum(mini_detail_dur)+sum(short_feed_dur))/((sum(news_view_tally)+sum(mini_video_over_tally)+sum(short_video_over_tally))*60000) as avg_xiaofei_dur 
        from 
            base_all 
        group by 
            user_type, 
            app_ver 
    ) tmp