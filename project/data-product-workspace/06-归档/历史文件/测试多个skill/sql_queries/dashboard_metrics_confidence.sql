-- 大盘指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验：提取用户级数据用于统计检验
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

-- 下载量（均值类指标 - t检验）
with download_data as (
    select 
        date,
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
        AND app_version IN ('20.11.1010115', '20.11.10115')
),

-- 人均使用时长（均值类指标 - t检验）
duration_data as (
    select 
        date,
        app_ver,
        if (is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
        did as user_id,
        sum(app_dura)/60000 as metric_value
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        app_ver,
        is_new_miui_imei_2024,
        did
),

-- 日活率（比率类指标 - Z检验）
dau_data as (
    select 
        date,
        app_ver,
        '大盘用户' as user_type,
        did as user_id,
        1 as is_dau
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt + app_duration_cnt > 0 
        and coalesce(did,'') != '' 
        and is_app_dau_2024 = 1
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        app_ver,
        did
)

select 
    date,
    app_ver,
    user_type,
    'download_num' as metric_name,
    'mean' as metric_type,
    user_id,
    metric_value
from download_data

union all

select 
    date,
    app_ver,
    user_type,
    'avg_dur' as metric_name,
    'mean' as metric_type,
    user_id,
    metric_value
from duration_data

union all

select 
    date,
    app_ver,
    user_type,
    'dau_rate' as metric_name,
    'ratio' as metric_type,
    user_id,
    is_dau as metric_value
from dau_data
