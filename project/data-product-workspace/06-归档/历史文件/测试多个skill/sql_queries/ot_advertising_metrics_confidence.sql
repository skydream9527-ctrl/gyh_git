-- OT口径广告指标 - 置信度计算数据提取
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

-- IPU（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'ipu' as metric_name,
    'mean' as metric_type,
    did as user_id,
    coalesce(ad_expose, 0) as metric_value
from q2

union all

-- 人均广告请求（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_require' as metric_name,
    'mean' as metric_type,
    did as user_id,
    coalesce(ad_require, 0) as metric_value
from q2

union all

-- 人均广告点击（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'avg_click' as metric_name,
    'mean' as metric_type,
    did as user_id,
    coalesce(ad_click, 0) as metric_value
from q2

union all

-- 填充率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'tianchong_rate' as metric_name,
    'ratio' as metric_type,
    did as user_id,
    case when ad_require > 0 and ad_return > 0 then 1 else 0 end as metric_value
from q2
where ad_require > 0

union all

-- CTR（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'ctr' as metric_name,
    'ratio' as metric_type,
    did as user_id,
    case when ad_expose > 0 and ad_click > 0 then 1 else 0 end as metric_value
from q2
where ad_expose > 0
