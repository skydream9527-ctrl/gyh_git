-- 商业中台指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验：提取用户级数据用于统计检验
-- 实验组版本: 20.11.1010115
-- 对照组版本: 20.11.10115
-- 分析时间: 20260116-20260118

with dau_base as (
    select 
        date,
        did,
        max(app_ver) as app_ver,
        if(min(is_new_miui_imei_2024) = 1, '新用户', '老用户') as user_type
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date BETWEEN 20260116 AND 20260118
        and app_open_cnt > 0 
        and coalesce(did,'') != ''
        AND app_ver IN ('20.11.1010115', '20.11.10115')
    group by 
        date,
        did
),
ad_data_all as (
    select 
        date,
        did,
        sum(ad_return_cnt) as eadreturn,
        sum(query_cnt) as equery,
        sum(fee_amt)/100000 as fee,
        sum(vaild_view_cnt) as eview,
        sum(vaild_click_cnt) as eclick,
        sum(raw_view_cnt) as erawview,
        sum(start_download_cnt) as estardownload,
        coalesce(ad_position_media_type,'') as ad_position_media_type
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_ad_event_aggregation_di 
    where 
        date BETWEEN 20260116 AND 20260118
    group by 
        date,
        did,
        coalesce(ad_position_media_type,'')
),
q1 as ( 
    select 
        a.date,
        a.did as distinct_id, 
        user_type, 
        app_ver, 
        fee, 
        eview, 
        eclick, 
        erawview, 
        estardownload, 
        eadreturn, 
        equery 
    from 
        dau_base a
        left join (
            select 
                date,
                did,
                sum(eadreturn) as eadreturn,
                sum(equery) as equery,
                sum(fee) as fee,
                sum(eview) as eview,
                sum(eclick) as eclick,
                sum(erawview) as erawview,
                sum(estardownload) as estardownload
            from ad_data_all
            where ad_position_media_type != '小说'
            group by date, did
        ) b on a.did = b.did AND a.date=b.date
), 
q2 as ( 
    select 
        date,
        distinct_id, 
        '大盘用户' as user_type, 
        app_ver, 
        fee, 
        eview, 
        eclick, 
        erawview, 
        estardownload, 
        eadreturn, 
        equery 
    from 
        q1 
    union all 
    select 
        date,
        * 
    from 
        q1 
)

-- ARPU（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'arpu' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    coalesce(fee, 0) as metric_value
from q2

union all

-- IPU（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'ipu' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    coalesce(eview, 0) as metric_value
from q2

union all

-- ECPM（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'ecpm' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    case when eview > 0 then coalesce(fee, 0)/eview*1000 else 0 end as metric_value
from q2
where eview > 0

union all

-- CPC（均值类指标 - t检验）
select 
    date,
    app_ver,
    user_type,
    'cpc' as metric_name,
    'mean' as metric_type,
    distinct_id as user_id,
    case when eclick > 0 then coalesce(fee, 0)/eclick else 0 end as metric_value
from q2
where eclick > 0

union all

-- 填充率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'tianchong_rate' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when equery > 0 and eadreturn > 0 then 1 else 0 end as metric_value
from q2
where equery > 0

union all

-- 漏斗率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'loudou' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when erawview > 0 and eview > 0 then 1 else 0 end as metric_value
from q2
where erawview > 0

union all

-- CTR（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'ctr' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when eview > 0 and eclick > 0 then 1 else 0 end as metric_value
from q2
where eview > 0

union all

-- CVR（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'cvr' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when eclick > 0 and estardownload > 0 then 1 else 0 end as metric_value
from q2
where eclick > 0

union all

-- 曝光成功率（比率类指标 - Z检验）
select 
    date,
    app_ver,
    user_type,
    'eview_sucess_rate' as metric_name,
    'ratio' as metric_type,
    distinct_id as user_id,
    case when eadreturn > 0 and erawview > 0 then 1 else 0 end as metric_value
from q2
where eadreturn > 0
