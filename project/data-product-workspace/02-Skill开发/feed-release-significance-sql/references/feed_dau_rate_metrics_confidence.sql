-- 信息流日活率指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：ad_request_uv, ad_request_avg → 提取用户级明细
-- ratio 类指标（Z 检验）：rate, ad_expose_rate → 提取成功次数和总次数

with base_data as (
    select
        did,
        app_ver,
        is_new_feed_2024,
        is_new_miui_imei_2024,
        sum(if(is_top=0, expos_cnt, 0)) as nt_expose,
        sum(if(is_top=0, click_cnt, 0)) as nt_click,
        sum(if(is_top=0, view_cnt, 0)) as nt_view,
        sum(if(is_top=0, video_play_cnt, 0)) as nt_play,
        sum(ad_content_expose_cnt) as ad_expose_tally,
        sum(ad_content_request_client_cnt) as ad_request_tally,
        sum(app_open_cnt) as app_open_cnt
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    where
        date=20260331
        and feed_status in ('true', 'false')
        and coalesce(did,'') != ''
    group by
        did,
        app_ver,
        is_new_feed_2024,
        is_new_miui_imei_2024
)

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 广告请求UV ad_request_uv (mean → t 检验)
-- 每个有广告请求的用户一行，metric_value=广告请求次数
SELECT
    date,
    app_ver,
    if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
    did as user_id,
    ad_request_tally as metric_value
FROM
    base_data
WHERE
    ad_request_tally > 0
UNION ALL
SELECT
    date,
    app_ver,
    '大盘用户' as user_type,
    did as user_id,
    ad_request_tally as metric_value
FROM
    base_data
WHERE
    ad_request_tally > 0;

-- 1.2 人均广告请求 ad_request_avg (mean → t 检验)
-- 与 ad_request_uv 共享同一份用户级数据，metric_value=广告请求次数
-- （ad_request_avg = sum(ad_request_tally)/count(ad_request_uv)，t 检验只需用户级明细）
SELECT
    date,
    app_ver,
    if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
    did as user_id,
    ad_request_tally as metric_value
FROM
    base_data
WHERE
    ad_request_tally > 0
UNION ALL
SELECT
    date,
    app_ver,
    '大盘用户' as user_type,
    did as user_id,
    ad_request_tally as metric_value
FROM
    base_data
WHERE
    ad_request_tally > 0;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 信息流渗透率 rate (ratio → Z 检验)
-- 成功次数 = 信息流 DAU，总次数 = 浏览器 DAU
SELECT
    date,
    if(t1.user_type is not null, t1.user_type, t2.user_type) as user_type,
    if(t1.app_ver is not null, t1.app_ver, t2.app_ver) as app_ver,
    t2.number as total_users,
    coalesce(t1.number, 0) as success_count
FROM
    (
        SELECT
            if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
            app_ver,
            count(1) as number
        FROM
            base_data
        WHERE
            nt_expose + nt_click + nt_view + nt_play > 0
        GROUP BY
            app_ver,
            if(is_new_feed_2024=1, '新用户', '老用户')
        UNION ALL
        SELECT
            '大盘用户' as user_type,
            app_ver,
            count(1) as number
        FROM
            base_data
        WHERE
            nt_expose + nt_click + nt_view + nt_play > 0
        GROUP BY
            app_ver
    ) t1
    full join (
        SELECT
            if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
            app_ver,
            count(distinct did) as number
        FROM
            base_data
        WHERE
            app_open_cnt > 0
        GROUP BY
            app_ver,
            if(is_new_miui_imei_2024=1, '新用户', '老用户')
        UNION ALL
        SELECT
            '大盘用户' as user_type,
            app_ver,
            count(distinct did) as number
        FROM
            base_data
        WHERE
            app_open_cnt > 0
        GROUP BY
            app_ver
    ) t2 on t1.user_type=t2.user_type
    and t1.app_ver=t2.app_ver;

-- 2.2 广告曝光率 ad_expose_rate (ratio → Z 检验)
-- 成功次数 = 有广告曝光的用户数，总次数 = 有广告请求的用户数
SELECT
    date,
    app_ver,
    if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
    sum(if(ad_request_tally>0, 1, 0)) as total_users,
    sum(if(ad_expose_tally>0, 1, 0)) as success_count
FROM
    base_data
WHERE
    ad_request_tally > 0 or ad_expose_tally > 0
GROUP BY
    date,
    app_ver,
    if(is_new_feed_2024=1, '新用户', '老用户')
UNION ALL
SELECT
    date,
    app_ver,
    '大盘用户' as user_type,
    sum(if(ad_request_tally>0, 1, 0)) as total_users,
    sum(if(ad_expose_tally>0, 1, 0)) as success_count
FROM
    base_data
WHERE
    ad_request_tally > 0 or ad_expose_tally > 0
GROUP BY
    date,
    app_ver;
