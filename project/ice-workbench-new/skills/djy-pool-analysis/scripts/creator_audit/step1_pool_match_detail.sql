-- 步骤 1 明细：审核表中"从未入库"作者列表 + 审核推送时间
-- 用于定位问题批次（例如 2026-04-17 批量推送但停滞在 pending_initial_review）

WITH audit_full AS (
  SELECT
    cp_api,
    lead_author_id,
    ARBITRARY(lead_author_name) AS audit_name,
    MAX(audit_time) AS audit_time_ms,
    MAX(update_time) AS update_time_ms,
    ARBITRARY(audit_status) AS audit_status
  FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
  WHERE cp_api IS NOT NULL AND cp_api <> ''
    AND lead_author_id IS NOT NULL AND lead_author_id <> ''
    AND (lead_author_name IS NULL OR lead_author_name NOT LIKE '测试账号%')
  GROUP BY cp_api, lead_author_id
),
pool_ids AS (
  SELECT DISTINCT a_cp AS cp, lead_author_id
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-beike-djy', 'cn-dihui-djy')
    AND lead_author_id IS NOT NULL AND lead_author_id <> ''
    AND create_time IS NOT NULL
)
SELECT
  a.cp_api,
  a.audit_name,
  a.lead_author_id,
  FROM_UNIXTIME(a.audit_time_ms / 1000) AS audit_time_str,
  FROM_UNIXTIME(a.update_time_ms / 1000) AS update_time_str,
  a.audit_status
FROM audit_full a
LEFT JOIN pool_ids p
  ON a.cp_api = p.cp AND a.lead_author_id = p.lead_author_id
WHERE p.lead_author_id IS NULL
ORDER BY a.cp_api, a.audit_time_ms;