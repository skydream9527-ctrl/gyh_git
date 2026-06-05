-- Template B · 7 天趋势对比（按 date 分区维度，增量视角辅报告）
-- 取 {{DATE_D_MINUS_7}} 到 {{DATE}} 共 8 天数据，后处理计算 D-1 日环比 / D-7 周同比 / MA7 偏离度
-- 触发条件说明：每个 (CP, 规则) 走绝对量 0 异常原则分级（紧急≥1000 / 高100-999 / 低1-99 / 正常 0）
--
-- ⚠️ 时间维度说明：本视图用 `date`（分区键）做趋势，和业务"入库时间"语义不同。
-- 业务口径的 create_time 维度 7 天趋势请走 references/daily_report.md 里的内联 SQL（日报自动化使用）
-- 本文件用于 date 分区维度的兜底查询（手动跑 / 非日报场景）
--
-- 2026-04-28 全量升级：
--   · 规则 12/13 扩展为全类型（豁免 aigc01IncisiveInsightHub）
--   · 规则 14 扩展为全类型（豁免 aigc01IncisiveInsightHub）
--   · 规则 15 升级（非空 AND > 0）
--   · 规则 16.1 扩展为 7 必填字段（原只查 firstImg）
--   · 新增规则 16.2 fileMd5 条件必填（create_time >= 2026-04-29）
--   · 新增规则 22 ai_article 条件必填 + 值域（create_time >= 2026-05-22）
--   · 新增规则 23 author_ip 全类型必填

SELECT
  date, a_cp,
  COUNT(*) AS total,
  -- 规则 3
  SUM(CASE WHEN publish_time IS NULL OR publish_time = '' OR LOWER(publish_time) = 'null' THEN 1 ELSE 0 END) AS publish_time_n,
  -- 规则 10
  SUM(CASE WHEN author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null' THEN 1 ELSE 0 END) AS author_image_n,
  -- 规则 11
  SUM(CASE WHEN xm_author_id IS NULL OR xm_author_id = '' OR LOWER(xm_author_id) = 'null' THEN 1 ELSE 0 END) AS xm_author_id_n,
  -- 规则 8
  SUM(CASE WHEN url IS NULL OR url = '' OR LOWER(url) = 'null' OR (url NOT LIKE 'http://%' AND url NOT LIKE 'https://%') THEN 1 ELSE 0 END) AS url_bad,
  -- 规则 9
  SUM(CASE WHEN image IS NULL OR image = '' OR LOWER(image) = 'null' THEN 1 ELSE 0 END) AS image_n,
  -- 规则 12/13 全类型（2026-04-28），豁免 aigc01IncisiveInsightHub
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null') THEN 1 ELSE 0 END) AS lead_author_id_null,
  -- 规则 14 全类型（2026-04-28），豁免 aigc01IncisiveInsightHub
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (category IS NULL OR category = '' OR LOWER(category) = 'null') THEN 1 ELSE 0 END) AS category_null,
  -- 规则 15 升级（非空 AND > 0）
  SUM(CASE WHEN item_type != 'NEWS' AND (
       video_duration IS NULL OR video_duration = '' OR LOWER(video_duration) = 'null'
    OR video_duration = '0' OR video_duration LIKE '0.%' OR video_duration LIKE '-%'
  ) THEN 1 ELSE 0 END) AS video_duration_bad,
  -- 规则 16
  SUM(CASE WHEN item_type != 'NEWS' AND (video_detail_list IS NULL OR video_detail_list = '' OR LOWER(video_detail_list) = 'null') THEN 1 ELSE 0 END) AS video_detail_list_empty,
  -- 规则 16.1 7 个必填字段（2026-04-28，替代旧的 firstimg_missing）
  SUM(CASE WHEN item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND (
        video_detail_list NOT LIKE '%"videoUrl":"http%'
     OR video_detail_list NOT LIKE '%"firstImg":"http%'
     OR video_detail_list NOT LIKE '%"bitrate":%'       OR video_detail_list LIKE '%"bitrate":""%'       OR video_detail_list LIKE '%"bitrate":null%'
     OR video_detail_list NOT LIKE '%"codecType":%'     OR video_detail_list LIKE '%"codecType":""%'     OR video_detail_list LIKE '%"codecType":null%'
     OR video_detail_list NOT LIKE '%"videoResolution":%' OR video_detail_list LIKE '%"videoResolution":""%' OR video_detail_list LIKE '%"videoResolution":null%'
     OR video_detail_list NOT LIKE '%"videoWidth":%'    OR video_detail_list LIKE '%"videoWidth":""%'    OR video_detail_list LIKE '%"videoWidth":null%'
     OR video_detail_list NOT LIKE '%"videoHeight":%'   OR video_detail_list LIKE '%"videoHeight":""%'   OR video_detail_list LIKE '%"videoHeight":null%'
  ) THEN 1 ELSE 0 END) AS video_detail_incomplete,
  -- 规则 16.2 fileMd5 条件必填（2026-04-28 新增，create_time >= 2026-04-29 生效）
  SUM(CASE WHEN item_type != 'NEWS'
    AND video_detail_list IS NOT NULL AND video_detail_list != ''
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-29'
    AND (
         video_detail_list NOT LIKE '%"fileMd5":%'
      OR video_detail_list LIKE '%"fileMd5":""%'
      OR video_detail_list LIKE '%"fileMd5":null%'
    )
    THEN 1 ELSE 0 END) AS filemd5_missing,
  -- 规则 17
  SUM(CASE WHEN item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null') THEN 1 ELSE 0 END) AS body_null_news,
  -- 规则 22 ai_article 条件必填 + 值域（2026-04-28 新增，create_time >= 2026-05-22 生效）
  SUM(CASE WHEN create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-05-22'
    AND (
         ai_article IS NULL OR ai_article = '' OR LOWER(ai_article) = 'null'
      OR (item_type = 'NEWS' AND ai_article NOT IN ('0','1'))
      OR (item_type != 'NEWS' AND ai_article NOT IN ('0','1','2','3','4','5'))
    )
    THEN 1 ELSE 0 END) AS ai_article_bad,
  -- 规则 23 author_ip 全类型必填（2026-04-28 新增，无生效日期）
  SUM(CASE WHEN a_cp != 'cn-beike-djy' AND (author_ip IS NULL OR author_ip = '' OR LOWER(author_ip) = 'null') THEN 1 ELSE 0 END) AS author_ip_null
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
  AND date BETWEEN '{{DATE_D_MINUS_7}}' AND '{{DATE}}'
  {{EXEMPT_FILTER}}
GROUP BY date, a_cp
ORDER BY a_cp, date
