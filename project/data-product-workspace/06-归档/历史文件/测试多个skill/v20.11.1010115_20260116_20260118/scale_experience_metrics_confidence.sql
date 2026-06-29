-- 规模体验指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

with base_data as (
    select 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024,
        sum(app_open_cnt) as app_open_cnt,
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv,
        sum(search_security_cnt) as search_cnt
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt > 0 
        and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024
),
base as ( 
    SELECT 
        date,
        did, 
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        search_cnt 
    from 
        base_data
), 
base_all as ( 
    select 
        date,
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        search_cnt 
    from 
        base 
    union all 
    select 
        date,
        * 
    from 
        base 
), 
base1 as ( 
    select 
        date,
        did, 
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt > 0 
        and coalesce(did,'') != ''
        and app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did, 
        app_ver, 
        is_new_miui_imei_2024 
), 
base1_all as ( 
    select 
        date,
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        zhuqi_pv 
    from 
        base1 
    union all 
    select 
        date,
        * 
    from 
        base1 
)

-- 次日打开率（比率类指标 - Z检验）
SELECT 
    base1_all.date,
    user_type,
    app_ver,
    'open_rate' as metric_name,
    'ratio' as metric_type,
    sum(if (t.did is not null, 1, 0)) as success_count,
    count(base1_all.did) as total_count
FROM 
    base1_all 
    LEFT JOIN ( 
        SELECT DISTINCT date, did 
        FROM base_all
    ) t ON base1_all.did=t.did AND base1_all.date=t.date
GROUP BY base1_all.date, user_type, app_ver

UNION ALL

-- 主启率（比率类指标 - Z检验）
SELECT 
    base1_all.date,
    user_type,
    app_ver,
    'zhuqi_rate' as metric_name,
    'ratio' as metric_type,
    sum(if (t.did is not null and zhuqi_pv>0, 1, 0)) as success_count,
    sum(if (base1_all.did is not null and zhuqi_pv>0, 1, 0)) as total_count
FROM 
    base1_all 
    LEFT JOIN ( 
        SELECT DISTINCT date, did 
        FROM base_all
    ) t ON base1_all.did=t.did AND base1_all.date=t.date
GROUP BY base1_all.date, user_type, app_ver

UNION ALL

-- 搜索率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'sousuo_rate' as metric_name,
    'ratio' as metric_type,
    sum(if (search_cnt>0, 1, 0)) as success_count,
    count(did) as total_count
FROM base_all
GROUP BY date, user_type, app_ver

UNION ALL

-- 人均搜索次数（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'avg_search' as metric_name,
    'mean' as metric_type,
    count(did) as sample_size,
    sum(search_cnt) as total_value,
    avg(search_cnt) as mean_value,
    stddev(search_cnt) as std_value
FROM base_all
GROUP BY date, user_type, app_ver
