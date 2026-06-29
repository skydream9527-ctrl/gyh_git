-- 规模体验指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验：提取用户级数据用于统计检验
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

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
        AND app_ver IN ('20.11.1010115', '20.11.10115')
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
        search_cnt,
        zhuqi_pv
    from 
        base_data
), 
base_all as ( 
    select 
        date,
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        search_cnt,
        zhuqi_pv
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
        AND app_ver IN ('20.11.1010115', '20.11.10115')
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

-- 人均搜索次数（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_search' as metric_name,
    'mean' as metric_type,
    did as user_id,
    search_cnt as metric_value
from base_all

union all

-- 搜索率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'sousuo_rate' as metric_name,
    'ratio' as metric_type,
    did as user_id,
    case when search_cnt > 0 then 1 else 0 end as metric_value
from base_all

union all

-- 次日打开率（比率类指标 - Z检验）
select 
    a.date,
    a.app_ver,
    a.user_type,
    'open_rate' as metric_name,
    'ratio' as metric_type,
    a.did as user_id,
    case when t.did is not null then 1 else 0 end as metric_value
from 
    base1_all a
    left join ( 
        select 
            date,
            distinct did 
        from 
            base_all 
    ) t on a.did=t.did AND a.date=t.date

union all

-- 主启率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'zhuqi_rate' as metric_name,
    'ratio' as metric_type,
    did as user_id,
    case when zhuqi_pv > 0 then 1 else 0 end as metric_value
from base1_all
where did is not null
