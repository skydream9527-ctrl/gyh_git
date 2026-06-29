-- 大盘指标查询 SQL
-- 用于分析版本灰度期间的大盘用户数据
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

with download_user as ( 
    select 
        date,
        '大盘用户' as user_type, 
        app_version as app_ver, 
        count(distinct did) as number 
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
), 
dau_base as (
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
),
dau_user as ( 
    select 
        date,
        if (is_new_miui_imei_2024=1, '新用户', '老用户') as user_type, 
        app_ver, 
        count(distinct did) as number, 
        sum(app_dur) as app_dur 
    from 
        dau_base
    group by 
        date,
        app_ver, 
        if (is_new_miui_imei_2024=1, '新用户', '老用户')
    union all 
    select 
        date,
        '大盘用户' as user_type, 
        app_ver, 
        count(distinct did) as number, 
        sum(app_dur) as app_dur 
    from 
        dau_base
    group by 
        date,
        app_ver 
)

SELECT 
    coalesce(dau_user.date, download_user.date) as date,
    if (dau_user.user_type is not null, dau_user.user_type, '大盘用户') as user_type, 
    if (download_user.app_ver is not null, download_user.app_ver, dau_user.app_ver) as app_ver, 
    download_user.number as download_num, 
    if (dau_user.number/download_user.number>1, 1, dau_user.number/download_user.number) as dau_rate, 
    app_dur/(dau_user.number*60000) as avg_dur 
from 
    download_user 
    full join dau_user on download_user.app_ver=dau_user.app_ver 
    and download_user.date=dau_user.date
