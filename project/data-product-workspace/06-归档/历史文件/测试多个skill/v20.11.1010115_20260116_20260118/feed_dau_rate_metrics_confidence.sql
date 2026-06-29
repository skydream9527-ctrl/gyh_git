-- 信息流日活率指标 - 置信度计算数据提取
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
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_feed_2024,
        is_new_miui_imei_2024
)

-- 信息流渗透率（比率类指标 - Z检验）
SELECT 
    date,
    if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type,
    app_ver,
    'rate' as metric_name,
    'ratio' as metric_type,
    count(distinct case when nt_expose + nt_click + nt_view + nt_play > 0 then did end) as success_count,
    count(distinct case when app_open_cnt > 0 then did end) as total_count
FROM base_data
WHERE app_open_cnt > 0
GROUP BY date, if (is_new_miui_imei_2024 = 1, '新用户', '老用户'), app_ver

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'rate' as metric_name,
    'ratio' as metric_type,
    count(distinct case when nt_expose + nt_click + nt_view + nt_play > 0 then did end) as success_count,
    count(distinct case when app_open_cnt > 0 then did end) as total_count
FROM base_data
WHERE app_open_cnt > 0
GROUP BY date, app_ver

UNION ALL

-- 广告请求UV（均值类指标 - t检验）
SELECT 
    date,
    if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
    app_ver,
    'ad_request_uv' as metric_name,
    'mean' as metric_type,
    count(distinct did) as sample_size,
    sum(if (ad_request_tally>0, 1, 0)) as total_value,
    avg(if (ad_request_tally>0, 1, 0)) as mean_value,
    stddev(if (ad_request_tally>0, 1, 0)) as std_value
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, if (is_new_feed_2024 = 1, '新用户', '老用户'), app_ver

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'ad_request_uv' as metric_name,
    'mean' as metric_type,
    count(distinct did) as sample_size,
    sum(if (ad_request_tally>0, 1, 0)) as total_value,
    avg(if (ad_request_tally>0, 1, 0)) as mean_value,
    stddev(if (ad_request_tally>0, 1, 0)) as std_value
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, app_ver

UNION ALL

-- 广告曝光率（比率类指标 - Z检验）
SELECT 
    date,
    if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
    app_ver,
    'ad_expose_rate' as metric_name,
    'ratio' as metric_type,
    count(distinct case when ad_expose_tally>0 then did end) as success_count,
    count(distinct case when ad_request_tally>0 then did end) as total_count
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, if (is_new_feed_2024 = 1, '新用户', '老用户'), app_ver

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'ad_expose_rate' as metric_name,
    'ratio' as metric_type,
    count(distinct case when ad_expose_tally>0 then did end) as success_count,
    count(distinct case when ad_request_tally>0 then did end) as total_count
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, app_ver

UNION ALL

-- 人均广告请求（均值类指标 - t检验）
SELECT 
    date,
    if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type,
    app_ver,
    'ad_request_avg' as metric_name,
    'mean' as metric_type,
    count(distinct case when ad_request_tally>0 then did end) as sample_size,
    sum(ad_request_tally) as total_value,
    avg(ad_request_tally) as mean_value,
    stddev(ad_request_tally) as std_value
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, if (is_new_feed_2024 = 1, '新用户', '老用户'), app_ver

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'ad_request_avg' as metric_name,
    'mean' as metric_type,
    count(distinct case when ad_request_tally>0 then did end) as sample_size,
    sum(ad_request_tally) as total_value,
    avg(ad_request_tally) as mean_value,
    stddev(ad_request_tally) as std_value
FROM base_data
WHERE ad_request_tally > 0 OR ad_expose_tally > 0
GROUP BY date, app_ver
