-- 步骤 2：内容池作者 → 签约清单匹配（严格精确匹配版本）
-- 输出该 lead_author_id 在内容池所有历史 (CP, 作者名) 组合
-- 精确匹配失败的候选，交给 run_audit_check.py 做 emoji 容错二次匹配
--
-- 占位符 __CONTRACTS_VALUES__：由 gen_contract_values.py --mode merged 生成
-- （两批合并去重后的 (cp, name) 列表）

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
)
SELECT
  a.cp_api,
  COUNT(*) AS in_pool_total,
  SUM(CASE WHEN h.lead_author_id IS NOT NULL THEN 1 ELSE 0 END) AS in_contract_strict,
  COUNT(*) - SUM(CASE WHEN h.lead_author_id IS NOT NULL THEN 1 ELSE 0 END) AS not_in_contract_strict
FROM in_pool a
LEFT JOIN hit h ON a.cp_api = h.cp_api AND a.lead_author_id = h.lead_author_id
GROUP BY a.cp_api
ORDER BY a.cp_api;