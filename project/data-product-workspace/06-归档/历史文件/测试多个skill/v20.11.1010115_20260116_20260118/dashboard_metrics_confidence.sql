-- 大盘指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

-- 下载量（均值类指标 - t检验）
with download_data as (
    select 
        date,
        '大盘用户' as user_type,
        app_version as app_ver,
        did as user_id,
        1 as metric_value
    from 
        hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df 
    where 
        date BETWEEN 20260116 AND 20260118
        and cat_lvl1_id=1 
        and cat_lvl2_id=195 
        and user_id=0 
        and final_country='中国'
        and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date 
        and package_name='com.android.browser' 
        and app_version IN ('20.11.1010115', '20.11.10115')
)

SELECT 
    date,
    user_type,
    app_ver,
    'download_num' as metric_name,
    'mean' as metric_type,
    count(distinct user_id) as sample_size,
    sum(metric_value) as total_value,
    avg(metric_value) as mean_value,
    stddev(metric_value) as std_value
FROM download_data
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均使用时长（均值类指标 - t检验）
SELECT 
    date,
    if (is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
    app_ver,
    'avg_dur' as metric_name,
    'mean' as metric_type,
    count(distinct did) as sample_size,
    sum(app_dur) as total_value,
    avg(app_dur/60000) as mean_value,
    stddev(app_dur/60000) as std_value
FROM (
    select 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024,
        sum(app_dura) as app_dur
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1 
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024
) t
GROUP BY date, if (is_new_miui_imei_2024=1, '新用户', '老用户'), app_ver

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'avg_dur' as metric_name,
    'mean' as metric_type,
    count(distinct did) as sample_size,
    sum(app_dur) as total_value,
    avg(app_dur/60000) as mean_value,
    stddev(app_dur/60000) as std_value
FROM (
    select 
        date,
        did,
        app_ver,
        sum(app_dura) as app_dur
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1 
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver
) t
GROUP BY date, app_ver

UNION ALL

-- 日活率（比率类指标 - Z检验）
SELECT 
    date,
    if (is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
    app_ver,
    'dau_rate' as metric_name,
    'ratio' as metric_type,
    count(distinct did) as success_count,
    download_num as total_count
FROM (
    select 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1 
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024
) dau
LEFT JOIN (
    select 
        date,
        app_version as app_ver,
        count(distinct did) as download_num
    from 
        hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df 
    where 
        date BETWEEN 20260116 AND 20260118
        and cat_lvl1_id=1 
        and cat_lvl2_id=195 
        and user_id=0 
        and final_country='中国'
        and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date 
        and package_name='com.android.browser' 
        and app_version IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        app_version
) dl ON dau.app_ver=dl.app_ver AND dau.date=dl.date
GROUP BY date, if (is_new_miui_imei_2024=1, '新用户', '老用户'), app_ver, download_num

UNION ALL

SELECT 
    date,
    '大盘用户' as user_type,
    app_ver,
    'dau_rate' as metric_name,
    'ratio' as metric_type,
    count(distinct did) as success_count,
    download_num as total_count
FROM (
    select 
        date,
        did,
        app_ver
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1 
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver
) dau
LEFT JOIN (
    select 
        date,
        app_version as app_ver,
        count(distinct did) as download_num
    from 
        hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df 
    where 
        date BETWEEN 20260116 AND 20260118
        and cat_lvl1_id=1 
        and cat_lvl2_id=195 
        and user_id=0 
        and final_country='中国'
        and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date 
        and package_name='com.android.browser' 
        and app_version IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        app_version
) dl ON dau.app_ver=dl.app_ver AND dau.date=dl.date
GROUP BY date, app_ver, download_num
