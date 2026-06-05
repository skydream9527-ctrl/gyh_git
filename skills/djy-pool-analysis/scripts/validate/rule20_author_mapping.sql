-- 规则 20 · 作者三元 ID 一致性检测（author_id ↔ lead_author_id ↔ xm_author_id）
--
-- 违反条件：同一 CP 下三元两两不一对一
-- 适用：所有 item_type（含 NEWS，2026-04-28 用户确认）
-- 豁免：aigc01IncisiveInsightHub（锐析洞察局）
--   - 它的 lead_author_id 全空，所以不会出现在 lead_author_id 方向的分组里（自动豁免）
--   - author_id 方向：同一 aigc 下 (lead_author_id=null, xm_author_id=X) 若唯一则合规
--   - xm_author_id 方向：同一 xm 下 (author_id=aigc, lead_author_id=null) 若唯一则合规
--
-- 输出三个方向：
--   a) author_id  → distinct (lead_author_id, xm_author_id) 组合必须 1
--   b) lead_author_id (非空) → distinct (author_id, xm_author_id) 组合必须 1
--   c) xm_author_id → distinct (author_id, lead_author_id) 组合必须 1
-- 每方向报告：bad_keys（异常 key 数量）+ bad_items（涉及条数）

SELECT a_cp, 'author_id->N(lead,xm)' AS direction,
       COUNT(DISTINCT author_id) AS bad_keys,
       SUM(item_cnt) AS bad_items
FROM (
  SELECT a_cp, author_id, COUNT(*) AS item_cnt
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND author_id IS NOT NULL AND author_id != ''
    {{EXEMPT_FILTER}}
  GROUP BY a_cp, author_id
  HAVING COUNT(DISTINCT CONCAT(COALESCE(lead_author_id,'NULL'), '|', COALESCE(xm_author_id,'NULL'))) > 1
) t
GROUP BY a_cp

UNION ALL

SELECT a_cp, 'lead_author_id->N(author,xm)' AS direction,
       COUNT(DISTINCT lead_author_id) AS bad_keys,
       SUM(item_cnt) AS bad_items
FROM (
  SELECT a_cp, lead_author_id, COUNT(*) AS item_cnt
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND lead_author_id IS NOT NULL AND lead_author_id != ''
    {{EXEMPT_FILTER}}
  GROUP BY a_cp, lead_author_id
  HAVING COUNT(DISTINCT CONCAT(COALESCE(author_id,'NULL'), '|', COALESCE(xm_author_id,'NULL'))) > 1
) t
GROUP BY a_cp

UNION ALL

SELECT a_cp, 'xm_author_id->N(author,lead)' AS direction,
       COUNT(DISTINCT xm_author_id) AS bad_keys,
       SUM(item_cnt) AS bad_items
FROM (
  SELECT a_cp, xm_author_id, COUNT(*) AS item_cnt
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND xm_author_id IS NOT NULL AND xm_author_id != ''
    {{EXEMPT_FILTER}}
  GROUP BY a_cp, xm_author_id
  HAVING COUNT(DISTINCT CONCAT(COALESCE(author_id,'NULL'), '|', COALESCE(lead_author_id,'NULL'))) > 1
) t
GROUP BY a_cp

ORDER BY a_cp, direction
