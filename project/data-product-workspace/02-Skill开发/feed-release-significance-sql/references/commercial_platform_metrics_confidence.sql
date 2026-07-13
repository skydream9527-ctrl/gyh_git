-- 商业中台指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：arpu, ipu, ecpm, cpc → 提取用户级明细
-- ratio 类指标（Z 检验）：tianchong_rate, loudou, ctr, cvr, eview_sucess_rate → 提取成功次数和总次数

with dau_base as (
    select
        did,
        max(app_ver) as app_ver,
        if(min(is_new_miui_imei_2024)=1, '新用户', '老用户') as user_type
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
        coalesce(fee, 0) as fee,
        coalesce(eview, 0) as eview,
        coalesce(eclick, 0) as eclick,
        coalesce(erawview, 0) as erawview,
        coalesce(estardownload, 0) as estardownload,
        coalesce(eadreturn, 0) as eadreturn,
        coalesce(equery, 0) as equery
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
)

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 ARPU 人均广告收入 (mean → t 检验)
-- 提取每个 DAU 用户的广告收入
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    fee as metric_value
FROM
    q2;

-- 1.2 IPU 人均有效曝光 (mean → t 检验)
-- 提取每个 DAU 用户的有效曝光数
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    eview as metric_value
FROM
    q2;

-- 1.3 ECPM 千次曝光收入 (mean → t 检验)
-- 提取每个 DAU 用户的收入和曝光，用于计算 ecpm = fee/eview*1000
-- 注意：ecpm 是比率衍生指标，t 检验需提取用户级 fee 和 eview
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    case when eview > 0 then fee/eview*1000 else 0 end as metric_value
FROM
    q2;

-- 1.4 CPC 单次点击成本 (mean → t 检验)
-- 提取每个 DAU 用户的收入和点击，用于计算 cpc = fee/eclick
-- 注意：cpc 是比率衍生指标，t 检验需提取用户级 fee 和 eclick
SELECT
    date,
    app_ver,
    user_type,
    distinct_id as user_id,
    case when eclick > 0 then fee/eclick else 0 end as metric_value
FROM
    q2;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 填充率 tianchong_rate (ratio → Z 检验)
-- 成功次数 = 广告返回数，总次数 = 广告请求数
SELECT
    date,
    app_ver,
    user_type,
    sum(equery) as total_users,
    sum(eadreturn) as success_count
FROM
    q2
WHERE
    equery > 0 or eadreturn > 0
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.2 漏斗率 loudou (ratio → Z 检验)
-- 成功次数 = 有效曝光数，总次数 = 原始曝光数
SELECT
    date,
    app_ver,
    user_type,
    sum(erawview) as total_users,
    sum(eview) as success_count
FROM
    q2
WHERE
    erawview > 0 or eview > 0
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.3 CTR 点击率 (ratio → Z 检验)
-- 成功次数 = 有效点击数，总次数 = 有效曝光数
SELECT
    date,
    app_ver,
    user_type,
    sum(eview) as total_users,
    sum(eclick) as success_count
FROM
    q2
WHERE
    eview > 0 or eclick > 0
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.4 CVR 转化率 (ratio → Z 检验)
-- 成功次数 = 下载转化数，总次数 = 有效点击数
SELECT
    date,
    app_ver,
    user_type,
    sum(eclick) as total_users,
    sum(estardownload) as success_count
FROM
    q2
WHERE
    eclick > 0 or estardownload > 0
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.5 曝光成功率 eview_sucess_rate (ratio → Z 检验)
-- 成功次数 = 原始曝光数，总次数 = 广告返回数
SELECT
    date,
    app_ver,
    user_type,
    sum(eadreturn) as total_users,
    sum(erawview) as success_count
FROM
    q2
WHERE
    eadreturn > 0 or erawview > 0
GROUP BY
    date,
    app_ver,
    user_type;
