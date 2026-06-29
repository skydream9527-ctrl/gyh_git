-- 规则 21 · a_item_id 库内全局唯一性检测
-- 违反条件：同一 a_item_id 出现在多条记录中
-- 业务含义：a_item_id 是 CP 入库后拼前缀的内容主键，upsert 表理论上不会重复
-- 若命中：upsert 键配置异常 / 前缀冲突 / CP 误推等
-- 注意：先排除 item_id 级豁免白名单，再做 GROUP BY（避免豁免 id 进入统计）

SELECT
  COUNT(*) AS dup_ids,
  SUM(cnt) AS dup_items
FROM (
  SELECT a_item_id, COUNT(*) AS cnt
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    AND a_item_id IS NOT NULL AND a_item_id != ''
    {{EXEMPT_FILTER}}
  GROUP BY a_item_id
  HAVING COUNT(*) > 1
) t

-- 如需看具体重复 id 列表，去掉外层聚合：
-- SELECT a_item_id, COUNT(*) AS cnt FROM ... GROUP BY a_item_id HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT 100
