-- OT 口径广告指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：ipu, avg_require, avg_click → 提取用户级明细
-- ratio 类指标（Z 检验）：tianchong_rate, ctr → 提取成功次数和总次数

with base_data as (
    select
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
        date=20260331
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
    group by
        did,
        app_ver,
        is_new_miui_imei_2024
),
q1 as (
    select
        a.did as did,
        if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
        a.app_ver as app_ver,
        coalesce(ad_expose, 0) as ad_expose,
        coalesce(ad_click, 0) as ad_click,
        coalesce(ad_require, 0) as ad_require,
        coalesce(ad_return, 0) as ad_return
    from
        (
            select
                did,
                app_ver,
                if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type
            from
                iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
            where
                date=20260331
                and app_open_cnt > 0
                and coalesce(did,'') != ''
            group by
                did,
                app_ver,
                if(is_new_miui_imei_2024=1, '新用户', '老用户')
        ) a
        left join base_data b on a.did=b.did
        and a.app_ver=b.app_ver
),
q2 as (
    select
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

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 IPU 人均广告曝光数 (mean → t 检验)
-- 提取每个 DAU 用户的广告曝光数
SELECT
    date,
    app_ver,
    user_type,
    did as user_id,
    ad_expose as metric_value
FROM
    q2;

-- 1.2 人均广告请求 avg_require (mean → t 检验)
-- 提取每个 DAU 用户的广告请求数
SELECT
    date,
    app_ver,
    user_type,
    did as user_id,
    ad_require as metric_value
FROM
    q2;

-- 1.3 人均广告点击 avg_click (mean → t 检验)
-- 提取每个 DAU 用户的广告点击数
SELECT
    date,
    app_ver,
    user_type,
    did as user_id,
    ad_click as metric_value
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
    sum(ad_require) as total_users,
    sum(ad_return) as success_count
FROM
    q2
WHERE
    ad_require > 0 or ad_return > 0
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.2 CTR 广告点击率 (ratio → Z 检验)
-- 成功次数 = 广告点击数，总次数 = 广告曝光数
SELECT
    date,
    app_ver,
    user_type,
    sum(ad_expose) as total_users,
    sum(ad_click) as success_count
FROM
    q2
WHERE
    ad_expose > 0 or ad_click > 0
GROUP BY
    date,
    app_ver,
    user_type;
