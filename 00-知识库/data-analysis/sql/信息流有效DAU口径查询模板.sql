-- =====================================================
-- 信息流有效 DAU 与时长口径查询模板（presto 版）
-- -----------------------------------------------------
-- 口径来源：信息流有效相关指标口径-20260509
--           https://mi.feishu.cn/wiki/C0J0w7MksizOJWkYQ3vcrWarn4g
-- 沉淀时间：2026-07-01
-- 来源案例：数据需求/0701信息流有效DAU时长4-6月/（4-6 月 91 天分天，含校验）
-- 配套文档：../methods/Kyuubi-Presto大数据量取数优化方法.md
--           ../pitfalls/Kyuubi-Presto取数踩坑.md
-- kyuubi 执行参数：--catalog iceberg_zjyprc_hadoop --engine presto --region chnbj --workspace 11329
-- =====================================================
-- 复用方法：
--   1. 改下方 BETWEEN 日期（按月分批，勿一次跑 90 天+，会 OOM）
--   2. 首次使用先用单日（date = 校验日）跑探针，对照文档校验值
--   3. count(*) 等价于 count(distinct did)——因子查询已按 (date,did) 去重
--   4. presto 不支持 rlike，已用 regexp_like 等价改写
-- =====================================================


-- ========== 查询1：浏览器信息流有效 DAU 与时长（分天） ==========
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


-- ========== 查询2：内容中心信息流有效 DAU 与时长（分天） ==========
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


-- ========== 口径校验参考（20260401 单日，对照文档校验图）==========
-- 浏览器：browser_feed_valid_dau = 7,449,022，browser_feed_valid_dura = 137,892,030.91（分钟）
-- 内容中心：newhome_feed_valid_dau = 17,407,582，newhome_feed_valid_dura = 230,603,639.36（分钟）
-- 双端合计：DAU = 24,856,604，时长 = 368,495,670.27（分钟）
