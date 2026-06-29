-- 埋点监控指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

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
        and app_ver IN ('20.11.1010115', '20.11.10115')
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

-- 视频完播率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'paly_rate' as metric_name,
    'ratio' as metric_type,
    sum(mini_video_over_tally + short_video_over_tally) as success_count,
    sum(mini_video_play_tally + short_video_play_tally) as total_count
FROM base_all
GROUP BY date, user_type, app_ver

UNION ALL

-- 小视频人均消费时长（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'mini_avg_dur' as metric_name,
    'mean' as metric_type,
    count(distinct_id) as sample_size,
    sum(mini_detail_dur) as total_value,
    avg(mini_detail_dur/60000) as mean_value,
    stddev(mini_detail_dur/60000) as std_value
FROM base_all
WHERE mini_video_over_tally > 0
GROUP BY date, user_type, app_ver

UNION ALL

-- 短视频人均消费时长（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'short_avg_dur' as metric_name,
    'mean' as metric_type,
    count(distinct_id) as sample_size,
    sum(short_feed_dur) as total_value,
    avg(short_feed_dur/60000) as mean_value,
    stddev(short_feed_dur/60000) as std_value
FROM base_all
WHERE short_video_over_tally > 0
GROUP BY date, user_type, app_ver

UNION ALL

-- 内容人均消费时长（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_xiaofei_dur' as metric_name,
    'mean' as metric_type,
    count(distinct_id) as sample_size,
    sum(news_detail_dur + mini_detail_dur + short_feed_dur) as total_value,
    avg((news_detail_dur + mini_detail_dur + short_feed_dur)/60000) as mean_value,
    stddev((news_detail_dur + mini_detail_dur + short_feed_dur)/60000) as std_value
FROM base_all
WHERE (news_view_tally + mini_video_over_tally + short_video_over_tally) > 0
GROUP BY date, user_type, app_ver
