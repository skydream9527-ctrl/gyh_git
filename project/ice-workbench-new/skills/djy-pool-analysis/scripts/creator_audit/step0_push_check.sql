-- 步骤 0：签约名单 → 审核表推送校验
-- 匹配键：CP + 作者名
-- 占位符 __CONTRACTS_VALUES__：由 gen_contract_values.py --mode batch1/batch2 生成
--
-- 若要同时跑两批，请分别替换 VALUES 跑两次（保持基数统计独立）。
-- 输出：CP × (名单总数, 已推送, 未推送, 推送率)

WITH contracts(cp, author_name) AS (
  VALUES
  __CONTRACTS_VALUES__
),
audit AS (
  SELECT DISTINCT cp_api, lead_author_name
  FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
  WHERE cp_api IS NOT NULL AND cp_api <> ''
    AND lead_author_name IS NOT NULL AND lead_author_name <> ''
)
SELECT
  c.cp AS cp_api,
  COUNT(*) AS total,
  SUM(CASE WHEN a.cp_api IS NOT NULL THEN 1 ELSE 0 END) AS pushed,
  COUNT(*) - SUM(CASE WHEN a.cp_api IS NOT NULL THEN 1 ELSE 0 END) AS not_pushed
FROM contracts c
LEFT JOIN audit a
  ON c.cp = a.cp_api AND c.author_name = a.lead_author_name
GROUP BY c.cp
ORDER BY c.cp;
