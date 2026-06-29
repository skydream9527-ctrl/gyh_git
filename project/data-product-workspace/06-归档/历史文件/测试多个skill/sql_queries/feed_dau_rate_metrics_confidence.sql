-- 信息流日活率指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验：提取用户级数据用于统计检验
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with base_data as (
    select 
        date,
        did,
        app_ver,
        is_new_feed_2024,
        is_new_miui_imei_2024,
        sum(if (is_top=0, expos_cnt, 0)) as nt_expose,
        sum(if (is_top=0, click_cnt, 0)) as nt_click,
        sum(if (is_top=0, view_cnt, 0)) as nt_view,
        sum(if (is_top=0, video_play_cnt, 0)) as nt_play,
        sum(ad_content_expose_cnt) as ad_expose_tally,
        sum(ad_content_request_client_cnt) as ad_request_tally,
        sum(app_open_cnt) as app_open_cnt
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di  
    where 
        date BETWEEN 20260116 AND 20260118
        and feed_status in ('true', 'false')
        and coalesce(did,'') != ''
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_feed_2024,
        is_new_miui_imei_2024
),

-- 广告请求UV（均值类指标 - t检验）
ad_request_data as (
    select 
        date,
        app_ver,
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
        did as user_id,
        ad_request_tally as metric_value
    from base_data
    where ad_request_tally > 0
),

-- 人均广告请求（均值类指标 - t检验）
ad_request_avg_data as (
    select 
        date,
        app_ver,
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
        did as user_id,
        ad_request_tally as metric_value
    from base_data
    where ad_request_tally > 0
),

-- 信息流渗透率（比率类指标 - Z检验）
feed_penetration_data as (
    select 
        date,
        app_ver,
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type,
        did as user_id,
        case when nt_expose + nt_click + nt_view + nt_play > 0 then 1 else 0 end as metric_value
    from base_data
    where app_open_cnt > 0
),

-- 广告曝光率（比率类指标 - Z检验）
ad_expose_rate_data as (
    select 
        date,
        app_ver,
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
        did as user_id,
        case when ad_expose_tally > 0 then 1 else 0 end as metric_value
    from base_data
    where ad_request_tally > 0
)

select 
    date,
    app_ver,
    user_type,
    'ad_request_uv' as metric_name,
    'mean' as metric_type,
    user_id,
    metric_value
from ad_request_data

union all

select 
    date,
    app_ver,
    user_type,
    'ad_request_avg' as metric_name,
    'mean' as metric_type,
    user_id,
    metric_value
from ad_request_avg_data

union all

select 
    date,
    app_ver,
    user_type,
    'rate' as metric_name,
    'ratio' as metric_type,
    user_id,
    metric_value
from feed_penetration_data

union all

select 
    date,
    app_ver,
    user_type,
    'ad_expose_rate' as metric_name,
    'ratio' as metric_type,
    user_id,
    metric_value
from ad_expose_rate_data
