-- 埋点监控指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：mini_avg_dur, short_avg_dur, avg_xiaofei_dur → 提取用户级明细
-- ratio 类指标（Z 检验）：paly_rate → 提取成功次数和总次数

with base_data as (
    select
        did,
        app_ver,
        is_new_feed_2024,
        sum(if(lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_video_play_tally,
        sum(if(lower(item_type) in ('vertical_video', 'mini_video'), video_over_cnt, 0)) as mini_video_over_tally,
        sum(if(lower(item_type) in ('vertical_video', 'mini_video') and duration_type='detail_page', feed_dura, 0)) as mini_detail_dur,
        sum(if(lower(item_type)='inline_video', video_play_cnt, 0)) as short_video_play_tally,
        sum(if(lower(item_type)='inline_video', video_over_cnt, 0)) as short_video_over_tally,
        sum(if(lower(item_type)='inline_video', video_over_event_dura, 0)) as short_feed_dur,
        sum(if(lower(item_type)='news', view_quit_cnt, 0)) as news_view_tally,
        sum(if(lower(item_type)='news', view_event_dura, 0)) as news_detail_dur
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
        if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
        mini_video_play_tally,
        mini_video_over_tally,
        mini_detail_dur,
        short_video_play_tally,
        short_video_over_tally,
        short_feed_dur,
        news_detail_dur,
        news_view_tally
    FROM
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

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 小视频人均消费时长 mini_avg_dur (mean → t 检验)
-- 仅取有完播记录的用户，metric_value = 小视频详情页时长(min)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    mini_detail_dur/60000 as metric_value
FROM
    base_all
WHERE
    mini_video_over_tally > 0;

-- 1.2 短视频人均消费时长 short_avg_dur (mean → t 检验)
-- 仅取有完播记录的用户，metric_value = 短视频时长(min)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    short_feed_dur/60000 as metric_value
FROM
    base_all
WHERE
    short_video_over_tally > 0;

-- 1.3 内容人均消费时长 avg_xiaofei_dur (mean → t 检验)
-- 仅取有播放/阅读记录的用户，metric_value = 综合消费时长(min)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    (news_detail_dur + mini_detail_dur + short_feed_dur)/60000 as metric_value
FROM
    base_all
WHERE
    (news_view_tally + mini_video_over_tally + short_video_over_tally) > 0;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 视频完播率 paly_rate (ratio → Z 检验)
-- 成功次数 = 完播数，总次数 = 播放数
SELECT
    date,
    app_ver,
    user_type,
    sum(mini_video_play_tally + short_video_play_tally) as total_users,
    sum(mini_video_over_tally + short_video_over_tally) as success_count
FROM
    base_all
WHERE
    (mini_video_play_tally + short_video_play_tally) > 0
GROUP BY
    date,
    app_ver,
    user_type;
