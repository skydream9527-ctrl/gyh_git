-- 步骤 0 明细：签约名单里未推送到审核表的作者
-- 占位符 __CONTRACTS_VALUES__：由 gen_contract_values.py --mode batch1/batch2 生成

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
SELECT c.cp AS cp_api, c.author_name
FROM contracts c
LEFT JOIN audit a
  ON c.cp = a.cp_api AND c.author_name = a.lead_author_name
WHERE a.cp_api IS NULL
ORDER BY c.cp, c.author_name;
