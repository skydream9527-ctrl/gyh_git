-- 规模体验指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：avg_search → 提取用户级明细
-- ratio 类指标（Z 检验）：open_rate, zhuqi_rate, sousuo_rate → 提取成功次数和总次数

with base_data as (
    select
        did,
        app_ver,
        is_new_miui_imei_2024,
        sum(app_open_cnt) as app_open_cnt,
        sum(if(app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv,
        sum(search_security_cnt) as search_cnt
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    where
        date=20260331
        and app_open_cnt > 0
        and coalesce(did,'') != ''
    group by
        did,
        app_ver,
        is_new_miui_imei_2024
),
base as (
    SELECT
        did,
        if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
        app_ver,
        search_cnt
    FROM
        base_data
),
base_all as (
    select
        did,
        '大盘用户' as user_type,
        app_ver,
        search_cnt
    from
        base
    union all
    select
        *
    from
        base
),
base1 as (
    select
        did,
        if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
        app_ver,
        sum(if(app_launch_way in ('点击icon', '点击桌面书签'), app_open_cnt, 0)) as zhuqi_pv
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    where
        date=20260330
        and app_open_cnt > 0
        and coalesce(did,'') != ''
    group by
        did,
        app_ver,
        is_new_miui_imei_2024
),
base1_all as (
    select
        did,
        '大盘用户' as user_type,
        app_ver,
        zhuqi_pv
    from
        base1
    union all
    select
        *
    from
        base1
)

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 人均搜索次数 avg_search (mean → t 检验)
-- 提取每个 DAU 用户的搜索次数
SELECT
    date,
    app_ver,
    user_type,
    did as user_id,
    search_cnt as metric_value
FROM
    base_all;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 次日打开率 open_rate (ratio → Z 检验)
-- 成功次数 = 前日 DAU 中次日仍活跃的用户数
-- 总次数 = 前日 DAU 用户数
SELECT
    date,
    app_ver,
    user_type,
    count(base1_all.did) as total_users,
    sum(if(t.did is not null, 1, 0)) as success_count
FROM
    base1_all
    left join (
        select
            distinct did
        from
            base_all
    ) t on base1_all.did=t.did
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.2 主启率 zhuqi_rate (ratio → Z 检验)
-- 成功次数 = 有主动启动行为的用户数
-- 总次数 = 前日 DAU 中有主启记录的用户数
SELECT
    date,
    app_ver,
    user_type,
    sum(if(base1_all.did is not null and zhuqi_pv>0, 1, 0)) as total_users,
    sum(if(t.did is not null and zhuqi_pv>0, 1, 0)) as success_count
FROM
    base1_all
    left join (
        select
            distinct did
        from
            base_all
    ) t on base1_all.did=t.did
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.3 搜索率 sousuo_rate (ratio → Z 检验)
-- 成功次数 = 有搜索行为的用户数
-- 总次数 = DAU 用户数
SELECT
    date,
    app_ver,
    user_type,
    count(did) as total_users,
    sum(if(search_cnt>0, 1, 0)) as success_count
FROM
    base_all
GROUP BY
    date,
    app_ver,
    user_type;
