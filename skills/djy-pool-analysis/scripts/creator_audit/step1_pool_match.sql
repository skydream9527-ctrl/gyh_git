-- 步骤 1：审核表 → 内容池历史入库匹配
-- 匹配键：CP + lead_author_id
-- 判断入库：create_time IS NOT NULL（非 date 分区过滤）
-- 已剔除：lead_author_name LIKE '测试账号%' 的驳回数据
-- 输出：CP × (审核表作者数, 历史入过库, 从未入库, 入库率)

WITH audit_ids AS (
  SELECT DISTINCT cp_api, lead_author_id
  FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
  WHERE cp_api IS NOT NULL AND cp_api <> ''
    AND lead_author_id IS NOT NULL AND lead_author_id <> ''
    AND (lead_author_name IS NULL OR lead_author_name NOT LIKE '测试账号%')
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
  COUNT(*) AS audit_total,
  SUM(CASE WHEN p.lead_author_id IS NOT NULL THEN 1 ELSE 0 END) AS ever_in_pool,
  COUNT(*) - SUM(CASE WHEN p.lead_author_id IS NOT NULL THEN 1 ELSE 0 END) AS never_in_pool
FROM audit_ids a
LEFT JOIN pool_ids p
  ON a.cp_api = p.cp AND a.lead_author_id = p.lead_author_id
GROUP BY a.cp_api
ORDER BY a.cp_api;