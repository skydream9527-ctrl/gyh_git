-- =====================================================
-- 0701 信息流有效 DAU 与时长 - Part01: 浏览器信息流有效（分天）
-- 时间范围：2026-04-01 ~ 2026-06-30（按月分批执行，改下方 BETWEEN 日期）
-- 口径来源：信息流有效相关指标口径-20260509
--           https://mi.feishu.cn/wiki/C0J0w7MksizOJWkYQ3vcrWarn4g
-- 关联取数：数据需求/0630浏览器流量地图/07-信息流有效消费-官方口径.sql（同口径 7 天版，用 rlike/spark）
-- kyuubi 执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================
-- 口径要点：
--   1. 有效用户判定（满足任一）：consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)
--   2. 前置过滤：is_app_dau_2024=1 AND is_top=0
--      AND (feed_channel in ('热点','推荐','profile','profile_djy','push') OR item_type in ('novel','shortstory'))
--   3. 时长 = (feed_dura + consum_dura) / 60000（毫秒→分钟）
--      - feed_dura：列表页时长（仅 热点/推荐 × feed_info_topnews/feed_info_rec）
--      - consum_dura：详情页消费时长（有 item_type/实验组/read_source 过滤）
--
-- 引擎与优化说明：
--   - presto 不支持 rlike，已等价改写为 regexp_like()（与 spark rlike 语义一致，部分匹配）
--   - 子查询已按 (date, did) 去重，外层 count(*) 等价于 count(distinct did)，大幅降低内存
--   - 91 天全量会超出 presto 240GB 用户内存上限，需按月分批执行：
--       4月: date between 20260401 and 20260430
--       5月: date between 20260501 and 20260531
--       6月: date between 20260601 and 20260630
-- =====================================================

SELECT
    date,
    -- 浏览器信息流有效用户时长（分钟）
    sum(feed_dura + consum_dura) / 60000 AS browser_feed_valid_dura,
    -- 浏览器信息流有效 DAU
    count(*) AS browser_feed_valid_dau
FROM (
    SELECT
        date, did,
        -- 是否列表页滑动（热点/推荐 × feed_info_topnews/feed_info_rec × 滑动标记）
        max(if(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true', 1, 0)) AS is_slide,
        -- consum_cnt_v2：有效消费次数（排除非 novel/shortstory；novel/shortstory 需在特定实验组且特定 read_source）
        sum(if(
            coalesce(item_type,'') NOT IN ('novel','shortstory')
            OR ((regexp_like(exp_id, '1566672|1960891|2316339|2316341|1643918'))
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_cnt_v2, 0
        )) AS consum_cnt_v2,
        -- 列表页时长：仅 热点/推荐 × feed_info_topnews/feed_info_rec
        sum(if(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec'), feed_dura, 0)) AS feed_dura,
        -- 详情页消费时长：有 item_type/实验组/read_source 过滤
        sum(if(
            coalesce(item_type,'') NOT IN ('novel','shortstory')
            OR ((regexp_like(exp_id, '1566672|1960891|2316339|2316341|1643918'))
                AND (
                    (item_type='novel' AND (read_source IN ('rec','topnews') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
                    OR (item_type='shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown') OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
                )
            ),
            consum_dura, 0
        )) AS consum_dura,
        -- 曝光数：符合频道/item_type 条件
        sum(if(
            feed_channel IN ('热点','推荐','profile','profile_djy','push')
            OR (item_type IN ('novel','shortstory') AND regexp_like(exp_id, '1566672|1960891|2316339|2316341|1643918') AND regexp_like(item_docid, 'djy'))
            OR (item_type IN ('novel','shortstory') AND regexp_like(exp_id, '1566673|1960892|2316340|1960893|1643917') AND regexp_like(item_docid, 'toutiao')),
            expos_cnt, 0
        )) AS expose_cnt
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260401 AND 20260430   -- 按月分批，改此处的起止日期
      AND is_app_dau_2024 = 1
      AND is_top = 0
      AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
    GROUP BY 1, 2
) a
-- 有效用户过滤：有消费 OR (有滑动 AND 有曝光)
WHERE consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)
GROUP BY 1
ORDER BY date;
