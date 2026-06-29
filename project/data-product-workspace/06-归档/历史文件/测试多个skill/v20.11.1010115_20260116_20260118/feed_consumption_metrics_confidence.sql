-- 信息流消费指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

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
        and app_ver IN ('20.11.1010115', '20.11.10115')
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

-- 有效率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'valid_rate' as metric_name,
    'ratio' as metric_type,
    sum(valid_flag1) as success_count,
    count(1) as total_count
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均曝光（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_expose' as metric_name,
    'mean' as metric_type,
    count(1) as sample_size,
    sum(nt_expose) as total_value,
    avg(nt_expose) as mean_value,
    stddev(nt_expose) as std_value
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均VV（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_vv' as metric_name,
    'mean' as metric_type,
    count(1) as sample_size,
    sum(news_v+short_v+mini_v) as total_value,
    avg(news_v+short_v+mini_v) as mean_value,
    stddev(news_v+short_v+mini_v) as std_value
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均信息流时长（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_dur' as metric_name,
    'mean' as metric_type,
    count(1) as sample_size,
    sum(feed_dura) as total_value,
    avg(feed_dura/60000) as mean_value,
    stddev(feed_dura/60000) as std_value
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均消费时长（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_xiaofei_dur' as metric_name,
    'mean' as metric_type,
    count(1) as sample_size,
    sum(xiaofei_duration) as total_value,
    avg(xiaofei_duration/60000) as mean_value,
    stddev(xiaofei_duration/60000) as std_value
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- CTR（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'ctr' as metric_name,
    'ratio' as metric_type,
    sum(news_v+short_v+mini_v) as success_count,
    sum(nt_expose) as total_count
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver

UNION ALL

-- UTR（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'utr' as metric_name,
    'ratio' as metric_type,
    sum(if (news_v+short_v+mini_v>0, 1, 0)) as success_count,
    count(1) as total_count
FROM base_all
WHERE nt_expose>0 OR nt_click>0 OR nt_view>0 OR nt_play>0
GROUP BY date, user_type, app_ver
