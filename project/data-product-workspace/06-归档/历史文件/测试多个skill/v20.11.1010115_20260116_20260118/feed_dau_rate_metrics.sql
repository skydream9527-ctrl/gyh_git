-- 信息流日活率指标查询 SQL
-- 用于分析版本灰度期间的信息流日活率和广告相关指标
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
),
ad_table as ( 
    select 
        date,
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_uv, 
        sum(if (ad_expose_tally>0, 1, 0))/sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate, 
        sum(ad_request_tally)/sum(if (ad_request_tally>0, 1, 0)) as ad_request_avg 
    from 
        base_data
    where ad_request_tally > 0 or ad_expose_tally > 0
    group by 
        date,
        app_ver,
        if (is_new_feed_2024 = 1, '新用户', '老用户')
    union all 
    select 
        date,
        '大盘用户' as user_type, 
        app_ver, 
        sum(if (ad_request_tally>0, 1, 0)) as ad_request_uv, 
        sum(if (ad_expose_tally>0, 1, 0))/sum(if (ad_request_tally>0, 1, 0)) as ad_expose_rate, 
        sum(ad_request_tally)/sum(if (ad_request_tally>0, 1, 0)) as ad_request_avg 
    from 
        base_data
    where ad_request_tally > 0 or ad_expose_tally > 0
    group by 
        date,
        app_ver 
), 
browser_feeds as ( 
    select 
        date,
        if (is_new_feed_2024 = 1, '新用户', '老用户') as user_type, 
        app_ver, 
        count(1) as number 
    from 
        base_data
    where nt_expose + nt_click + nt_view + nt_play > 0
    group by 
        date,
        app_ver,
        if (is_new_feed_2024 = 1, '新用户', '老用户')
    union all
    select 
        date,
        '大盘用户' as user_type, 
        app_ver, 
        count(1) as number 
    from 
        base_data
    where nt_expose + nt_click + nt_view + nt_play > 0
    group by 
        date,
        app_ver
), 
browser_rate as ( 
    select 
        t2.date,
        t2.user_type as user_type, 
        t2.app_ver as app_ver, 
        if (t1.number is null, 0, t1.number)/t2.number as rate 
    from 
        browser_feeds t1
        right join ( 
            select 
                date,
                if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
                app_ver, 
                count(distinct did) as number 
            from 
                base_data
            where app_open_cnt > 0
            group by 
                date,
                app_ver,
                if (is_new_miui_imei_2024 = 1, '新用户', '老用户')
            union all 
            select 
                date,
                '大盘用户' as user_type, 
                app_ver, 
                count(distinct did) as number 
            from 
                base_data
            where app_open_cnt > 0
            group by 
                date,
                app_ver 
        ) t2 on t1.user_type=t2.user_type 
        and t1.app_ver=t2.app_ver 
        and t1.date=t2.date
)

select 
    coalesce(ad_table.date, browser_rate.date) as date,
    if (ad_table.user_type is not null, ad_table.user_type, browser_rate.user_type) as user_type, 
    if (ad_table.app_ver is not null, ad_table.app_ver, browser_rate.app_ver) as app_ver, 
    if (rate>1, 1, rate) as rate, 
    ad_request_uv, 
    ad_expose_rate, 
    ad_request_avg 
from 
    ad_table 
    full join browser_rate on ad_table.user_type=browser_rate.user_type 
    and ad_table.app_ver=browser_rate.app_ver
    and ad_table.date=browser_rate.date
