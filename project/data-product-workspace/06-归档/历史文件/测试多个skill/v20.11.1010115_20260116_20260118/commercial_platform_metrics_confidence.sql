-- 商业中台指标 - 置信度计算数据提取
-- 用于 t 检验和 Z 检验
-- 实验组版本：20.11.1010115
-- 对照组版本：20.11.10115
-- 分析时间：20260116-20260118

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
        and app_ver IN ('20.11.1010115', '20.11.10115')
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
        LEFT JOIN (
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
        ) b ON a.did = b.did AND a.date=b.date
), 
q11 as ( 
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
        LEFT JOIN (
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
            where ad_position_media_type = '信息流'
            group by date, did
        ) b ON a.did = b.did AND a.date=b.date
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
), 
q22 as ( 
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
        q11 
    union all 
    select 
        date,
        * 
    from 
        q11 
)

-- ARPU（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'arpu' as metric_name,
    'mean' as metric_type,
    count(distinct distinct_id) as sample_size,
    sum(fee) as total_value,
    avg(fee) as mean_value,
    stddev(fee) as std_value
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- IPU（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'ipu' as metric_name,
    'mean' as metric_type,
    count(distinct distinct_id) as sample_size,
    sum(eview) as total_value,
    avg(eview) as mean_value,
    stddev(eview) as std_value
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- ECPM（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'ecpm' as metric_name,
    'mean' as metric_type,
    count(distinct distinct_id) as sample_size,
    sum(fee) as total_value,
    avg(fee/eview*1000) as mean_value,
    stddev(fee/eview*1000) as std_value
FROM q2
WHERE eview > 0
GROUP BY date, user_type, app_ver

UNION ALL

-- 填充率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'tianchong_rate' as metric_name,
    'ratio' as metric_type,
    sum(eadreturn) as success_count,
    sum(equery) as total_count
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- 漏斗率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'loudou' as metric_name,
    'ratio' as metric_type,
    sum(eview) as success_count,
    sum(erawview) as total_count
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- CPC（均值类指标 - t检验）
SELECT 
    date,
    user_type,
    app_ver,
    'cpc' as metric_name,
    'mean' as metric_type,
    count(distinct distinct_id) as sample_size,
    sum(fee) as total_value,
    avg(fee/eclick) as mean_value,
    stddev(fee/eclick) as std_value
FROM q2
WHERE eclick > 0
GROUP BY date, user_type, app_ver

UNION ALL

-- CTR（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'ctr' as metric_name,
    'ratio' as metric_type,
    sum(eclick) as success_count,
    sum(eview) as total_count
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- CVR（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'cvr' as metric_name,
    'ratio' as metric_type,
    sum(estardownload) as success_count,
    sum(eclick) as total_count
FROM q2
GROUP BY date, user_type, app_ver

UNION ALL

-- 曝光成功率（比率类指标 - Z检验）
SELECT 
    date,
    user_type,
    app_ver,
    'eview_sucess_rate' as metric_name,
    'ratio' as metric_type,
    sum(erawview) as success_count,
    sum(eadreturn) as total_count
FROM q2
GROUP BY date, user_type, app_ver
