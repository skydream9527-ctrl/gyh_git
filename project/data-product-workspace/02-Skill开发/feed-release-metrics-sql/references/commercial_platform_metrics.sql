-- 商业中台指标查询 SQL（优化版）
-- 用于分析版本灰度期间的商业化广告效果指标
-- 优化说明：合并对同一表的多次查询，减少表扫描次数

with dau_base as (
    select 
        did,
        max(app_ver) as app_ver,
        if(min(is_new_miui_imei_2024) = 1, '新用户', '老用户') as user_type
    from 
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di 
    where 
        date=20260331 
        and app_open_cnt > 0 
        and coalesce(did,'') != '' 
    group by 
        did
),
ad_data_all as (
    select 
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
        date=20260331
    group by 
        did,
        coalesce(ad_position_media_type,'')
),
q1 as ( 
    select 
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
            group by did
        ) b on a.did = b.did 
), 
q11 as ( 
    select 
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
            group by did
        ) b on a.did = b.did 
), 
q2 as ( 
    select 
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
        * 
    from 
        q1 
), 
q22 as ( 
    select 
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
        * 
    from 
        q11 
) 

INSERT OVERWRITE table iceberg_zjyprc_hadoop.browser.browser_adtable_zhiibiao partition (date=20260331) 
select 
    user_type, 
    '浏览器全广告位' as tag, 
    app_ver, 
    sum(fee) as fee, 
    sum(fee)/count(distinct distinct_id) as arpu, 
    sum(eview)/count(distinct distinct_id) as ipu, 
    sum(fee)/sum(eview)*1000 as ecpm, 
    sum(equery) as equery, 
    sum(equery)/count(distinct distinct_id) as avg_equery, 
    sum(eclick) as eclick, 
    sum(eclick)/count(distinct distinct_id) as avg_eclick, 
    sum(eadreturn)/sum(equery) as tianchong_rate, 
    sum(erawview) as erawview, 
    sum(eview) as eview, 
    sum(eview)/sum(erawview) as loudou, 
    sum(fee)/sum(eclick) as cpc, 
    sum(eclick)/sum(eview) as ctr, 
    sum(estardownload)/sum(eclick) as cvr, 
    sum(erawview)/sum(eadreturn) as eview_sucess_rate 
from 
    q2 
group by 
    user_type, 
    app_ver 
UNION all 
select 
    user_type, 
    '信息流全广告位' as tag, 
    app_ver, 
    sum(fee) as fee, 
    sum(fee)/count(distinct distinct_id) as arpu, 
    sum(eview)/count(distinct distinct_id) as ipu, 
    sum(fee)/sum(eview)*1000 as ecpm, 
    sum(equery) as equery, 
    sum(equery)/count(distinct distinct_id) as avg_equery, 
    sum(eclick) as eclick, 
    sum(eclick)/count(distinct distinct_id) as avg_eclick, 
    sum(eadreturn)/sum(equery) as tianchong_rate, 
    sum(erawview) as erawview, 
    sum(eview) as eview, 
    sum(eview)/sum(erawview) as loudou, 
    sum(fee)/sum(eclick) as cpc, 
    sum(eclick)/sum(eview) as ctr, 
    sum(estardownload)/sum(eclick) as cvr, 
    sum(erawview)/sum(eadreturn) as eview_sucess_rate 
from 
    q22 
group by 
    user_type, 
    app_ver