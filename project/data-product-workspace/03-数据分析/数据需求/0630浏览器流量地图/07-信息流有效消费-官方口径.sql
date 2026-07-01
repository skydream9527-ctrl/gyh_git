-- =====================================================
-- 0630 浏览器流量地图 - Part07: 信息流有效消费（官方口径）
-- 时间范围：2026-06-22 ~ 2026-06-28（7天）
-- 口径来源：信息流有效相关指标口径-20260509
--           https://mi.feishu.cn/wiki/C0J0w7MksizOJWkYQ3vcrWarn4g
-- 注意：只取浏览器部分，不含内容中心(newhome)
-- kyuubi执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================

-- 有效用户判定条件（满足任一即为有效）：
--   条件A：consum_cnt_v2 > 0（有内容消费）
--   条件B：is_slide > 0 AND expose_cnt > 0（列表页滑动且有曝光）
--
-- 前置过滤条件：
--   1. is_app_dau_2024 = 1（DAU）
--   2. is_top = 0（排除顶焦用户）
--   3. feed_channel in ('热点','推荐','profile','profile_djy','push') OR item_type in ('novel','shortstory')
--
-- 时长口径：feed_dura（列表页时长，仅热点/推荐×feed_info_topnews/feed_info_rec）
--          + consum_dura（详情页消费时长，有item_type过滤）


-- ========== 查询1：按天输出信息流有效DAU和时长 ==========
SELECT
    date,
    -- 浏览器信息流有效用户时长（分钟）
    CAST(SUM(feed_dura + consum_dura) AS BIGINT) / 60000 AS browser_feed_valid_dura_min,
    -- 浏览器信息流有效DAU
    COUNT(DISTINCT did) AS browser_feed_valid_dau
FROM (
    SELECT
        date,
        did,
        -- 是否列表页滑动（热点/推荐频道 + feed_info_topnews/feed_info_rec页面 + 滑动标记）
        MAX(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true', 1, 0)) AS is_slide,
        -- consum_cnt_v2：有效消费次数（排除非novel/shortstory，novel/shortstory需在特定实验组且特定read_source）
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('novel','shortstory')
            OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_cnt_v2, 0
        )) AS consum_cnt_v2,
        -- 列表页时长：仅热点/推荐频道 × feed_info_topnews/feed_info_rec页面
        SUM(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec'), feed_dura, 0)) AS feed_dura,
        -- 详情页消费时长：有item_type过滤
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('novel','shortstory')
            OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_dura, 0
        )) AS consum_dura,
        -- 曝光数：符合频道/item_type条件
        SUM(IF(
            feed_channel IN ('热点','推荐','profile','profile_djy','push')
            OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566672|1960891|2316339|2316341|1643918') AND item_docid RLIKE 'djy')
            OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566673|1960892|2316340|1960893|1643917') AND item_docid RLIKE 'toutiao'),
            expos_cnt, 0
        )) AS expose_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND is_app_dau_2024 = 1
      AND is_top = 0
      AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
    GROUP BY 1, 2
) a
-- 有效用户过滤：有消费 OR (有滑动 AND 有曝光)
WHERE consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)
GROUP BY 1
ORDER BY 1;


-- ========== 查询2：7天汇总 ==========
SELECT
    CAST(SUM(feed_dura + consum_dura) AS BIGINT) / 60000 AS browser_feed_valid_dura_min_7d,
    COUNT(DISTINCT did) AS browser_feed_valid_dau_7d,
    -- 日均
    ROUND(CAST(SUM(feed_dura + consum_dura) AS BIGINT) / 60000.0 / 7, 2) AS dura_min_daily_avg,
    ROUND(COUNT(DISTINCT did) / 7.0, 0) AS dau_daily_avg,
    -- 人均时长
    ROUND(CAST(SUM(feed_dura + consum_dura) AS BIGINT) / 60000.0 / COUNT(DISTINCT did), 2) AS dura_per_user_min
FROM (
    SELECT
        date,
        did,
        MAX(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true', 1, 0)) AS is_slide,
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('novel','shortstory')
            OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_cnt_v2, 0
        )) AS consum_cnt_v2,
        SUM(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec'), feed_dura, 0)) AS feed_dura,
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('novel','shortstory')
            OR ((exp_id RLIKE '1566672|1960891|2316339|2316341|1643918')
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_dura, 0
        )) AS consum_dura,
        SUM(IF(
            feed_channel IN ('热点','推荐','profile','profile_djy','push')
            OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566672|1960891|2316339|2316341|1643918') AND item_docid RLIKE 'djy')
            OR (item_type IN ('novel','shortstory') AND (exp_id RLIKE '1566673|1960892|2316340|1960893|1643917') AND item_docid RLIKE 'toutiao'),
            expos_cnt, 0
        )) AS expose_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260622 AND 20260628
      AND is_app_dau_2024 = 1
      AND is_top = 0
      AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
    GROUP BY 1, 2
) a
WHERE consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0);
