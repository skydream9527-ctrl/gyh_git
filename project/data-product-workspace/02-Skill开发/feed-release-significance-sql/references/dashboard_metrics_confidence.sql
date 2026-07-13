-- 大盘指标 - 置信度计算数据提取
-- mean 类指标（t 检验）：download_num, avg_dur → 提取用户级明细
-- ratio 类指标（Z 检验）：dau_rate → 提取成功次数和总次数

-- ============================================================
-- Part 1: mean 类指标 - t 检验数据提取（用户级明细，无聚合）
-- ============================================================

-- 1.1 下载量 download_num (mean → t 检验)
-- 每个下载用户一行，metric_value=1
SELECT
    date,
    app_version as app_ver,
    '大盘用户' as user_type,
    did as user_id,
    1 as metric_value
FROM
    hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
WHERE
    date=20260331
    and cat_lvl1_id=1
    and cat_lvl2_id=195
    and user_id=0
    and final_country='中国'
    and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date
    and package_name='com.android.browser';

-- 1.2 人均使用时长 avg_dur (mean → t 检验)
-- 提取每个 DAU 用户的 app_dur 值
SELECT
    date,
    app_ver,
    if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
    did as user_id,
    app_dur/60000 as metric_value
FROM
    (
        SELECT
            did,
            app_ver,
            is_new_miui_imei_2024,
            sum(app_dura) as app_dur
        FROM
            iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
        WHERE
            date=20260331
            and app_open_cnt + app_duration_cnt > 0
            and coalesce(did,'') != ''
            and is_app_dau_2024 = 1
        GROUP BY
            did,
            app_ver,
            is_new_miui_imei_2024
    ) t
UNION ALL
SELECT
    date,
    app_ver,
    '大盘用户' as user_type,
    did as user_id,
    app_dur/60000 as metric_value
FROM
    (
        SELECT
            did,
            app_ver,
            sum(app_dura) as app_dur
        FROM
            iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
        WHERE
            date=20260331
            and app_open_cnt + app_duration_cnt > 0
            and coalesce(did,'') != ''
            and is_app_dau_2024 = 1
        GROUP BY
            did,
            app_ver
    ) t;

-- ============================================================
-- Part 2: ratio 类指标 - Z 检验数据提取（成功次数 + 总次数）
-- ============================================================

-- 2.1 日活率 dau_rate (ratio → Z 检验)
-- 成功次数 = DAU 用户数，总次数 = 下载用户数
SELECT
    date,
    if(dau.user_type is not null, dau.user_type, '大盘用户') as user_type,
    if(download.app_ver is not null, download.app_ver, dau.app_ver) as app_ver,
    download.number as total_users,
    coalesce(dau.number, 0) as success_count
FROM
    (
        SELECT
            '大盘用户' as user_type,
            app_version as app_ver,
            count(distinct did) as number
        FROM
            hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df
        WHERE
            date=20260331
            and cat_lvl1_id=1
            and cat_lvl2_id=195
            and user_id=0
            and final_country='中国'
            and from_unixtime(cast(last_report_time/1000 AS bigint), 'yyyyMMdd')=date
            and package_name='com.android.browser'
        GROUP BY
            app_version
    ) download
    full join (
        SELECT
            if(is_new_miui_imei_2024=1, '新用户', '老用户') as user_type,
            app_ver,
            count(distinct did) as number
        FROM
            iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
        WHERE
            date=20260331
            and app_open_cnt + app_duration_cnt > 0
            and coalesce(did,'') != ''
            and is_app_dau_2024 = 1
        GROUP BY
            app_ver,
            if(is_new_miui_imei_2024=1, '新用户', '老用户')
        UNION ALL
        SELECT
            '大盘用户' as user_type,
            app_ver,
            count(distinct did) as number
        FROM
            iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
        WHERE
            date=20260331
            and app_open_cnt + app_duration_cnt > 0
            and coalesce(did,'') != ''
            and is_app_dau_2024 = 1
        GROUP BY
            app_ver
    ) dau on download.app_ver=dau.app_ver
    and download.user_type=dau.user_type;
