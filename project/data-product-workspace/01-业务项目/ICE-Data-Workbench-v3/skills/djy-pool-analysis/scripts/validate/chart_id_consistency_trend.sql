-- 三元 ID 一致性趋势 · 近 7 天 cutoff × 4 CP × 在线池
-- 输出：(snap_date, a_cp, multi_xm_authors_n, multi_cp_leads_n)
--   · multi_xm_authors_n  · 该 cutoff 在线池里、旗下 ≥2 个 xm_author_id 的 cp_author_id 数量
--   · multi_cp_leads_n    · 该 cutoff 在线池里、旗下 ≥2 个 cp_author_id 的 lead_author_id 数量
-- 阈值口径：clean = total 严格 1:1:1，任何 ≥2 都算异常
-- 时序敏感：UNION ALL 7 cutoff，加 online 过滤后数据量比 chart_stock_trend 更小
--   故 cron 排在 chart_stock_trend 之后（同一 10:30 窗口跑得完）

WITH base AS (
  SELECT '{{CUTOFF_6}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_6}}'
  UNION ALL SELECT '{{CUTOFF_5}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_5}}'
  UNION ALL SELECT '{{CUTOFF_4}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_4}}'
  UNION ALL SELECT '{{CUTOFF_3}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_3}}'
  UNION ALL SELECT '{{CUTOFF_2}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_2}}'
  UNION ALL SELECT '{{CUTOFF_1}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_1}}'
  UNION ALL SELECT '{{CUTOFF_0}}' AS cutoff, a_cp, lead_author_id, author_id, xm_author_id, a_item_id, create_time
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND online = '1' AND (delete_reason IS NULL OR delete_reason = '')
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_0}}'
),
filtered AS (
  SELECT * FROM base WHERE 1=1 {{EXEMPT_FILTER}}
),
xm_violations AS (
  SELECT cutoff, a_cp, COUNT(*) AS multi_xm_authors_n
  FROM (
    SELECT cutoff, a_cp, author_id
    FROM filtered
    WHERE author_id IS NOT NULL AND author_id <> ''
      AND xm_author_id IS NOT NULL AND xm_author_id <> ''
    GROUP BY cutoff, a_cp, author_id
    HAVING COUNT(DISTINCT xm_author_id) >= 2
  ) t
  GROUP BY cutoff, a_cp
),
lead_violations AS (
  SELECT cutoff, a_cp, COUNT(*) AS multi_cp_leads_n
  FROM (
    SELECT cutoff, a_cp, lead_author_id
    FROM filtered
    WHERE lead_author_id IS NOT NULL AND lead_author_id <> ''
      AND author_id IS NOT NULL AND author_id <> ''
    GROUP BY cutoff, a_cp, lead_author_id
    HAVING COUNT(DISTINCT author_id) >= 2
  ) t
  GROUP BY cutoff, a_cp
),
all_keys AS (
  SELECT DISTINCT cutoff, a_cp FROM filtered
)
SELECT
  k.cutoff AS snap_date,
  k.a_cp,
  COALESCE(x.multi_xm_authors_n, 0) AS multi_xm_authors_n,
  COALESCE(l.multi_cp_leads_n, 0) AS multi_cp_leads_n
FROM all_keys k
LEFT JOIN xm_violations x ON k.cutoff = x.cutoff AND k.a_cp = x.a_cp
LEFT JOIN lead_violations l ON k.cutoff = l.cutoff AND k.a_cp = l.a_cp
ORDER BY k.a_cp, k.cutoff
