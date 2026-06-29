-- 步骤 2 明细：严格精确匹配未命中的作者 + 其在内容池的所有历史作者名
-- 输出后由 run_audit_check.py 做 emoji 容错二次匹配
--
-- 占位符 __CONTRACTS_VALUES__：由 gen_contract_values.py --mode merged 生成

WITH contracts(cp, author_name) AS (
  VALUES
  __CONTRACTS_VALUES__
),
audit_ids AS (
  SELECT DISTINCT cp_api, lead_author_id
  FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
  WHERE cp_api IS NOT NULL AND cp_api <> ''
    AND lead_author_id IS NOT NULL AND lead_author_id <> ''
    AND (lead_author_name IS NULL OR lead_author_name NOT LIKE '测试账号%')
),
pool_history AS (
  SELECT DISTINCT a_cp AS cp, lead_author_id, lead_author_name
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-beike-djy', 'cn-dihui-djy')
    AND lead_author_id IS NOT NULL AND lead_author_id <> ''
    AND lead_author_name IS NOT NULL AND lead_author_name <> ''
    AND create_time IS NOT NULL
),
pool_authors AS (SELECT DISTINCT cp, lead_author_id FROM pool_history),
in_pool AS (
  SELECT a.cp_api, a.lead_author_id
  FROM audit_ids a
  INNER JOIN pool_authors p ON a.cp_api = p.cp AND a.lead_author_id = p.lead_author_id
),
hit AS (
  SELECT DISTINCT ip.cp_api, ip.lead_author_id
  FROM in_pool ip
  INNER JOIN pool_history p ON ip.cp_api = p.cp AND ip.lead_author_id = p.lead_author_id
  INNER JOIN contracts c ON p.cp = c.cp AND p.lead_author_name = c.author_name
),
miss AS (
  SELECT a.cp_api, a.lead_author_id
  FROM in_pool a
  LEFT JOIN hit h ON a.cp_api = h.cp_api AND a.lead_author_id = h.lead_author_id
  WHERE h.lead_author_id IS NULL
),
pool_all_names AS (
  SELECT cp, lead_author_id, ARRAY_JOIN(ARRAY_AGG(DISTINCT lead_author_name), ' | ') AS all_names
  FROM pool_history
  GROUP BY cp, lead_author_id
)
SELECT m.cp_api, pa.all_names, m.lead_author_id
FROM miss m
LEFT JOIN pool_all_names pa
  ON m.cp_api = pa.cp AND m.lead_author_id = pa.lead_author_id
ORDER BY m.cp_api, pa.all_names;