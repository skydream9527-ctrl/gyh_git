-- 规模体验指标查询 SQL（优化版）
-- 用于分析版本灰度期间的用户规模和体验相关指标
-- 优化说明：合并对 dwm_browser_event_aggregation_miui_di 表的多次查询

with base_data as (
    select 
        did,
        app_ver,
        is_new_miui_imei_2024,
        sum(app_open_cnt) as app_open_cnt,
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv,
        sum(search_security_cnt) as search_cnt
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date=20260331 
        and app_open_cnt > 0 
        and coalesce(did,'') != ''
    group by 
        did,
        app_ver,
        is_new_miui_imei_2024
),
base as ( 
    SELECT 
        did, 
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        search_cnt 
    from 
        base_data
), 
base_all as ( 
    select 
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        search_cnt 
    from 
        base 
    union all 
    select 
        * 
    from 
        base 
), 
base1 as ( 
    select 
        did, 
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        sum(if (app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv 
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date=20260330 
        and app_open_cnt > 0 
        and coalesce(did,'') != '' 
    group by 
        did, 
        app_ver, 
        is_new_miui_imei_2024 
), 
base1_all as ( 
    select 
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        zhuqi_pv 
    from 
        base1 
    union all 
    select 
        * 
    from 
        base1 
), 
result1 as ( 
    select 
        user_type, 
        app_ver, 
        sum(if (t.did is not null, 1, 0))/count(base1_all.did) as open_rate, 
        sum(if (t.did is not null and zhuqi_pv>0, 1, 0))/sum(if (base1_all.did is not null and zhuqi_pv>0, 1, 0)) as zhuqi_rate 
    from 
        base1_all 
        left join ( 
            select 
                distinct did 
            from 
                base_all 
        ) t on base1_all.did=t.did 
    group by 
        user_type, 
        app_ver 
), 
result2 as ( 
    select 
        user_type, 
        app_ver, 
        sum(if (search_cnt>0, 1, 0))/count(did) as sousuo_rate, 
        avg(search_cnt) as avg_search 
    from 
        base_all 
    group by 
        user_type, 
        app_ver 
) 

INSERT OVERWRITE table iceberg_zjyprc_hadoop.browser.browser_feeds_guimotiyan partition (date=20260331) 
select 
    if (a.user_type is not null, a.user_type, b.user_type) as user_type, 
    if (a.app_ver is not null, a.app_ver, b.app_ver) as app_ver, 
    open_rate, 
    zhuqi_rate, 
    sousuo_rate, 
    avg_search 
from 
    result1 a 
    full join result2 b on a.user_type=b.user_type 
    and a.app_ver=b.app_ver 
order by 
    user_type, 
    app_ver