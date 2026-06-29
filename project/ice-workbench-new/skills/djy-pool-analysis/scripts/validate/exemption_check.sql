-- CP 豁免白名单自动验证
-- 当规则 12/13（lead_author_id/name 空）命中数 > 0 时，必须先跑这条
-- 用途：识别命中的作者分布，辅助判定异常来源
-- 参数：{{CP}} 替换成目标 CP
--
-- 注意：template_a_stock.sql 里规则 12/13 已经排除了 aigc01IncisiveInsightHub（锐析）
-- 所以本 SQL 列出的都是**真实异常作者**（aigc 已豁免）。item_type 保留在 GROUP BY 里，方便追溯问题集中在哪种类型。
-- 2026-04-28 升级：规则 12/13 扩展为全类型必填（原非 NEWS），本 SQL 同步去掉 item_type != 'NEWS' 条件

SELECT author_name, author_id, item_type, COUNT(*) AS cnt
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp = '{{CP}}'
  AND author_id != 'aigc01IncisiveInsightHub'
  AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null')
GROUP BY author_name, author_id, item_type
ORDER BY cnt DESC

-- 判定：
-- 所有命中都已是真实异常（aigc 已在 SQL 里排除）
-- 告警文案：`命中 X 条（均为真实异常，aigc 锐析已自动豁免）` + 按 author 分布推 CP
