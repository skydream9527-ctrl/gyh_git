-- OT 口径广告指标查询 SQL
-- 用于分析版本灰度期间的广告相关指标（OT口径）
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with base_data as (
    select 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024,
        sum(ad_content_expose_cnt) as ad_expose,
        sum(ad_content_request_sever_cnt) as ad_require,
        sum(ad_content_click_cnt) as ad_click,
        sum(ad_content_return_sever_cnt) as ad_return
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and coalesce(did,'') != ''
        and tag_id not in ( 
            '1.13.c.4', 
            '1.13.f.14', 
            '1.13.f.17', 
            '1.13.f.18', 
            '1.13.f.20', 
            '1.13.r.2', 
            '1.13.r.3' 
        )
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did,
        app_ver,
        is_new_miui_imei_2024
),
q1 as ( 
    select 
        a.date,
        a.did as did, 
        if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type, 
        a.app_ver as app_ver, 
        ad_expose, 
        ad_click, 
        ad_require, 
        ad_return 
    from 
        ( 
            select 
                date,
                did, 
                app_ver, 
                if (is_new_miui_imei_2024 = 1, '新用户', '老用户') as user_type 
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
                if (is_new_miui_imei_2024 = 1, '新用户', '老用户') 
        ) a 
        left join base_data b on a.did=b.did 
        and a.app_ver=b.app_ver
        AND a.date=b.date
), 
q2 as ( 
    select 
        date,
        did, 
        '大盘用户' as user_type, 
        app_ver, 
        ad_expose, 
        ad_click, 
        ad_require, 
        ad_return 
    from 
        q1 
    union all 
    select 
        date,
        did, 
        user_type, 
        app_ver, 
        ad_expose, 
        ad_click, 
        ad_require, 
        ad_return 
    from 
        q1 
) 

select 
    date,
    user_type, 
    app_ver, 
    sum(ad_expose)/count(distinct did) as ipu, 
    sum(ad_require) as ad_require, 
    sum(ad_require)/count(distinct did) as avg_require, 
    sum(ad_click) as ad_click, 
    sum(ad_click)/count(distinct did) as avg_click, 
    sum(ad_return)/sum(ad_require) as tianchong_rate, 
    sum(ad_expose) as ad_expose, 
    sum(ad_click)/sum(ad_expose) as ctr 
from 
    q2 
group by 
    date,
    user_type, 
    app_ver
