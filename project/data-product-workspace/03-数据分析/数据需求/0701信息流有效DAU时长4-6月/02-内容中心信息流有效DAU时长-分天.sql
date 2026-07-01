-- =====================================================
-- 0701 信息流有效 DAU 与时长 - Part02: 内容中心信息流有效（分天）
-- 时间范围：2026-04-01 ~ 2026-06-30（按月分批执行，改下方 BETWEEN 日期）
-- 口径来源：信息流有效相关指标口径-20260509
--           https://mi.feishu.cn/wiki/C0J0w7MksizOJWkYQ3vcrWarn4g
-- kyuubi 执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================
-- 口径要点：
--   1. 有效用户判定：total_cnt > 0
--      total_cnt = sum(consum_cnt) + sum(if(item_position>=4 or ad_position>4, ad_expose_cnt + expos_cnt, 0))
--   2. 前置过滤：is_dau_2024=1 AND is_top=0
--      AND coalesce(ad_expose_cnt,0)+coalesce(expos_cnt,0)+coalesce(consum_cnt,0)+coalesce(feed_dura,0)+coalesce(consum_dura,0) > 0
--   3. 时长 = (sum(feed_dura) + sum(consum_dura)) / 60000（毫秒→分钟）
--
-- 引擎与优化说明：
--   - 子查询已按 (date, did) 去重，外层 count(*) 等价于 count(distinct did)，大幅降低内存
--   - 91 天全量会超出 presto 240GB 用户内存上限，需按月分批执行：
--       4月: date between 20260401 and 20260430
--       5月: date between 20260501 and 20260531
--       6月: date between 20260601 and 20260630
-- =====================================================

SELECT
    date,
    -- 内容中心信息流有效用户时长（分钟）
    sum(total_dura) AS newhome_feed_valid_dura,
    -- 内容中心信息流有效 DAU
    count(*) AS newhome_feed_valid_dau
FROM (
    SELECT
        date, did,
        -- total_cnt：有效交互计数（消费 + 第4位及以后的曝光）
        sum(consum_cnt)
          + sum(if(item_position >= 4 OR ad_position > 4, ad_expose_cnt + expos_cnt, 0)) AS total_cnt,
        -- 内容中心信息流时长（分钟）
        (sum(feed_dura) + sum(consum_dura)) / 60000 AS total_dura
    FROM iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
    WHERE date BETWEEN 20260401 AND 20260430   -- 按月分批，改此处的起止日期
      AND is_dau_2024 = 1
      AND is_top = 0
      AND coalesce(ad_expose_cnt, 0) + coalesce(expos_cnt, 0) + coalesce(consum_cnt, 0) + coalesce(feed_dura, 0) + coalesce(consum_dura, 0) > 0
    GROUP BY 1, 2
    HAVING total_cnt > 0
) a
GROUP BY 1
ORDER BY date;
