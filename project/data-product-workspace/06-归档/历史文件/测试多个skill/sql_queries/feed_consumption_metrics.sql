-- 信息流消费指标查询 SQL
-- 用于分析版本灰度期间的信息流消费相关指标
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with base as ( 
    select 
        date,
        did as distinct_id, 
        app_ver, 
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        sum(if (is_top=0, expos_cnt, 0)) as nt_expose, 
        sum(if (is_top=0, click_cnt, 0)) as nt_click, 
        sum(if (is_top=0, view_cnt, 0)) as nt_view, 
        sum(if (is_top=0, video_play_cnt, 0)) as nt_play, 
        sum(if (is_top=0 and feed_channel != 'push' and feed_status = 'true', expose_enter_cnt, 0)) as ntp_expose_enter, 
        sum(if (is_top=0 and feed_channel != 'push' and feed_status = 'true', click_enter_cnt, 0)) as ntp_click_enter, 
        sum(if (is_top=0 and feed_channel != 'push', expos_cnt, 0)) as ntp_expose, 
        sum(if (is_top=0 and feed_channel != 'push', click_cnt, 0)) as ntp_click, 
        sum(if (is_top=0 and lower(item_type)='news', expos_cnt, 0)) as news_exp, 
        sum(if (is_top=0 and lower(item_type)='inline_video', expos_cnt, 0)) as short_exp, 
        sum(if (is_top=0 and lower(item_type) in ('vertical_video', 'mini_video'), expos_cnt, 0)) as mini_exp, 
        sum(if (is_top=0 and lower(item_type)='news', click_cnt, 0)) as news_v, 
        sum(if (is_top=0 and lower(item_type) = 'inline_video', video_play_cnt, 0)) as short_v, 
        sum(if (is_top=0 and lower(item_type) in ('vertical_video', 'mini_video'), video_play_cnt, 0)) as mini_v, 
        sum(if (feed_status='true', feed_dura, 0)) as feed_dura, 
        sum(consum_dura) as xiaofei_duration 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and feed_status in ('true','false')
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver, 
        is_new_feed_2024
), 
base_all as ( 
    select 
        date,
        distinct_id, 
        app_ver, 
        '大盘用户' as user_type, 
        nt_expose, 
        nt_click, 
        nt_view, 
        nt_play, 
        ntp_expose_enter, 
        ntp_click_enter, 
        if (ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag1, 
        ntp_expose, 
        ntp_click, 
        if (ntp_expose>=6 or ntp_click>=1, 1, 0) as valid_flag2, 
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
    union all 
    select 
        date,
        distinct_id, 
        app_ver, 
        user_type, 
        nt_expose, 
        nt_click, 
        nt_view, 
        nt_play, 
        ntp_expose_enter, 
        ntp_click_enter, 
        if (ntp_expose_enter>=6 or ntp_click_enter>=1, 1, 0) as valid_flag1, 
        ntp_expose, 
        ntp_click, 
        if (ntp_expose>=6 or ntp_click>=1, 1, 0) as valid_flag2, 
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
) 

SELECT 
    date,
    user_type, 
    app_ver, 
    count(1) as dau, 
    sum(valid_flag1)/count(1) as valid_rate, 
    avg(nt_expose) as avg_expose, 
    avg(news_v+short_v+mini_v) as avg_vv, 
    avg(feed_dura)/60000 as avg_dur, 
    avg(xiaofei_duration)/60000 as avg_xiaofei_dur, 
    sum(news_v+short_v+mini_v)/sum(nt_expose) as ctr, 
    sum(if (news_v+short_v+mini_v>0, 1, 0))/count(1) as utr 
from 
    base_all 
where 
    nt_expose>0 or nt_click>0 or nt_view>0 or nt_play>0
group by 
    date,
    user_type, 
    app_ver
