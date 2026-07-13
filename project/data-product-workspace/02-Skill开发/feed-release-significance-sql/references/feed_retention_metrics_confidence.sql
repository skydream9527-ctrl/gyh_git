-- 信息流留存指标 - 置信度计算数据提取
-- 全部为 ratio 类指标（Z 检验）：e2e_ret, e2v_ret, v2v_ret → 提取成功次数和总次数

with date_2 as (
    select
        did as distinct_id,
        app_ver,
        if(is_new_feed_2024=1, '新用户', '老用户') as user_type,
        is_valid_dapan_2024 as valid_flag1,
        max(if(is_top=0 and expos_cnt>0, 1, 0)) as exp_flag
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    where
        date=20260330
        and feed_status in ('true','false')
    group by
        did,
        app_ver,
        is_new_feed_2024,
        is_valid_dapan_2024
),
date_2all as (
    select
        distinct_id,
        app_ver,
        '大盘用户' as user_type,
        valid_flag1,
        exp_flag
    from
        date_2
    union all
    select
        distinct_id,
        app_ver,
        user_type,
        valid_flag1,
        exp_flag
    from
        date_2
),
date_1all as (
    select
        did,
        is_valid_dapan_2024 as valid_flag1,
        max(if(is_top=0 and expos_cnt>0, 1, 0)) as exp_flag
    from
        iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    where
        date=20260331
        and feed_status in ('true','false')
    group by
        did,
        is_valid_dapan_2024
)

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 曝光到曝光留存 e2e_ret (ratio → Z 检验)
-- 成功次数 = 前日有曝光且次日也有曝光的用户数
-- 总次数 = 前日有曝光的用户数
SELECT
    date,
    app_ver,
    user_type,
    sum(if(a.exp_flag=1, 1, 0)) as total_users,
    sum(if(a.exp_flag=1 and b.exp_flag=1, 1, 0)) as success_count
FROM
    date_2all a
    left join date_1all b on a.distinct_id=b.did
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.2 曝光到有效留存 e2v_ret (ratio → Z 检验)
-- 成功次数 = 前日有曝光且次日为有效用户的用户数
-- 总次数 = 前日有曝光的用户数
SELECT
    date,
    app_ver,
    user_type,
    sum(if(a.exp_flag=1, 1, 0)) as total_users,
    sum(if(a.exp_flag=1 and b.valid_flag1=1, 1, 0)) as success_count
FROM
    date_2all a
    left join date_1all b on a.distinct_id=b.did
GROUP BY
    date,
    app_ver,
    user_type;

-- 2.3 有效到有效留存 v2v_ret (ratio → Z 检验)
-- 成功次数 = 前日有效且次日也有效的用户数
-- 总次数 = 前日有效用户数
SELECT
    date,
    app_ver,
    user_type,
    sum(a.valid_flag1) as total_users,
    sum(if(b.did is not null and b.valid_flag1=1 and a.valid_flag1=1, 1, 0)) as success_count
FROM
    date_2all a
    left join date_1all b on a.distinct_id=b.did
GROUP BY
    date,
    app_ver,
    user_type;
