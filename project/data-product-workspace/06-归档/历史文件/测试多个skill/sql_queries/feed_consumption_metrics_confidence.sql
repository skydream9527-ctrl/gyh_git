-- 信息流消费指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验：提取用户级数据用于统计检验
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
        news_v, 
        short_v, 
        mini_v, 
        feed_dura, 
        xiaofei_duration 
    from 
        base 
)

-- 人均曝光（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_expose' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    nt_expose as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0

union all

-- 人均VV（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_vv' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    (news_v + short_v + mini_v) as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0

union all

-- 人均信息流时长（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_dur' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    feed_dura/60000 as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0

union all

-- 人均消费时长（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_xiaofei_dur' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    xiaofei_duration/60000 as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0

union all

-- 有效率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'valid_rate' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    valid_flag1 as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0

union all

-- CTR（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'ctr' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when (news_v + short_v + mini_v) > 0 then 1 else 0 end as metric_value
from base_all
where nt_expose > 0

union all

-- UTR（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'utr' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when (news_v + short_v + mini_v) > 0 then 1 else 0 end as metric_value
from base_all
where nt_expose > 0 or nt_click > 0 or nt_view > 0 or nt_play > 0
