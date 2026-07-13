-- 信息流消费指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：avg_expose, avg_vv, avg_dur, avg_xiaofei_dur → 提取用户级明细
-- ratio 类指标（Z 检验）：valid_rate, ctr, utr → 提取成功次数和总次数

with base as (
    select
        did as distinct_id,
        app_ver,
        if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
        sum(if(is_top=0, expos_cnt, 0)) as nt_expose,
        sum(if(is_top=0, click_cnt, 0)) as nt_click,
        sum(if(is_top=0, view_cnt, 0)) as nt_view,
        sum(if(is_top=0, video_play_cnt, 0)) as nt_play,
        sum(if(is_top=0 and feed_channel != 'push' and feed_status='true', expose_enter_cnt, 0)) as ntp_expose_enter,
        sum(if(is_top=0 and feed_channel != 'push' and feed_status='true', click_enter_cnt, 0)) as ntp_click_enter,
        sum(if(is_top=0 and feed_channel != 'push', expos_cnt, 0)) as ntp_expose,
        sum(if(is_top=0 and feed_channel != 'push', click_cnt, 0)) as ntp_click,
        sum(if(is_top=0 and lower(item_type)='news', expos_cnt, 0)) as news_exp,
        sum(if(is_top=0 and lower(item_type)='inline_video', expos_cnt, 0)) as short_exp,
        sum(if(is_top=0 and lower(item_type) in ('vertical_video', 'mini_video'), expos_cnt, 0)) as mini_exp,
        sum(if(is_top=0 and lower(item_type)='news', click_cnt, 0)) as news_v,
        sum(if(is_top=0 and lower(item_type)='inline_video', video_play_cnt, 0)) as short_v,
        sum(if(is_top=0 and lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_v,
        sum(if(feed_status='true', feed_dura, 0)) as feed_dura,
        sum(consum_dura) as xiaofei_duration
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    where
        date=20260331
        and feed_status in ('true','false')
    group by
        did,
        app_ver,
        is_new_feed_2024
),
base_all as (
    select
        distinct_id,
        app_ver,
        '大盘用户' as user_type,
        nt_expose,
        nt_click,
        nt_view,
        nt_play,
        ntp_expose_enter,
        ntp_click_enter,
        if(ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag1,
        ntp_expose,
        ntp_click,
        if(ntp_expose>=6 or ntp_click>=1, 1, 0) as valid_flag2,
        news_exp,
        short_exp,
        mini_exp,
        news_v,
        short_v,
        mini_v,
        feed_dura,
        xiaofei_duration
    from
        base
    where
        nt_expose>0 or nt_click>0 or nt_view>0 or nt_play>0
    union all
    select
        distinct_id,
        app_ver,
        user_type,
        nt_expose,
        nt_click,
        nt_view,
        nt_play,
        ntp_expose_enter,
        ntp_click_enter,
        if(ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag1,
        ntp_expose,
        ntp_click,
        if(ntp_expose>=6 or ntp_click>=1, 1, 0) as valid_flag2,
        news_exp,
        short_exp,
        mini_exp,
        news_v,
        short_v,
        mini_v,
        feed_dura,
        xiaofei_duration
    from
        base
    where
        nt_expose>0 or nt_click>0 or nt_view>0 or nt_play>0
)

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 人均曝光 avg_expose (mean → t 检验)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    nt_expose as metric_value
FROM
    base_all;

-- 1.2 人均VV avg_vv (mean → t 检验)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    (news_v + short_v + mini_v) as metric_value
FROM
    base_all;

-- 1.3 人均信息流时长 avg_dur (mean → t 检验)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    feed_dura/60000 as metric_value
FROM
    base_all;

-- 1.4 人均消费时长 avg_xiaofei_dur (mean → t 检验)
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    xiaofei_duration/60000 as metric_value
FROM
    base_all;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 有效率 valid_rate (ratio → Z 检验)
-- 成功次数 = 有效用户数，总次数 = DAU
SELECT
    date,
    app_ver,
    user_type,
    count(1) as total_users,
    sum(valid_flag1) as success_count
FROM
    base_all
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.2 CTR (ratio → Z 检验)
-- 成功次数 = 总 VV 数，总次数 = 总曝光数
-- 注意：CTR 是事件级别比率，用聚合值提取
SELECT
    date,
    app_ver,
    user_type,
    sum(nt_expose) as total_users,
    sum(news_v + short_v + mini_v) as success_count
FROM
    base_all
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.3 UTR (ratio → Z 检验)
-- 成功次数 = 有 VV 的用户数，总次数 = DAU
SELECT
    date,
    app_ver,
    user_type,
    count(1) as total_users,
    sum(if(news_v + short_v + mini_v > 0, 1, 0)) as success_count
FROM
    base_all
GROUP BY
    date,
    app_ver,
    user_type;
