-- 日报图表底表 · 4 家 CP × 近 N 天 × 每个字段每日异常数 + 任一规则命中数
-- 时间窗口：{{CUTOFF_ISO_6}} ~ {{CUTOFF_ISO_0}}（近 7 天，运行时由 run_validate_sql.py 动态注入）
-- 时间维度：create_time（入库时间）
-- 豁免：占位符在 WHERE 段自动注入（item 级 28 条）+ author 级 aigc01IncisiveInsightHub 在规则里自带

SELECT a_cp,
  from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') AS create_date,
  COUNT(*) AS total,
  SUM(CASE WHEN publish_time IS NULL OR publish_time = '' OR LOWER(publish_time) = 'null' THEN 1 ELSE 0 END) AS publish_time_n,
  SUM(CASE WHEN author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null' THEN 1 ELSE 0 END) AS author_image_n,
  SUM(CASE WHEN xm_author_id IS NULL OR xm_author_id = '' OR LOWER(xm_author_id) = 'null' THEN 1 ELSE 0 END) AS xm_author_id_n,
  SUM(CASE WHEN a_cp != 'cn-beike-djy' AND (author_ip IS NULL OR author_ip = '' OR LOWER(author_ip) = 'null') THEN 1 ELSE 0 END) AS author_ip_n,
  SUM(CASE WHEN url IS NULL OR url = '' OR LOWER(url) = 'null' OR (url NOT LIKE 'http://%' AND url NOT LIKE 'https://%') THEN 1 ELSE 0 END) AS url_bad_n,
  SUM(CASE WHEN image IS NULL OR image = '' OR LOWER(image) = 'null' THEN 1 ELSE 0 END) AS image_n,
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null') THEN 1 ELSE 0 END) AS lead_author_id_n,
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (category IS NULL OR category = '' OR LOWER(category) = 'null') THEN 1 ELSE 0 END) AS category_n,
  SUM(CASE WHEN item_type != 'NEWS' AND (video_duration IS NULL OR video_duration = '' OR LOWER(video_duration) = 'null' OR video_duration = '0' OR video_duration LIKE '0.%' OR video_duration LIKE '-%') THEN 1 ELSE 0 END) AS video_duration_bad_n,
  SUM(CASE WHEN item_type != 'NEWS' AND (video_detail_list IS NULL OR video_detail_list = '' OR LOWER(video_detail_list) = 'null') THEN 1 ELSE 0 END) AS video_detail_empty_n,
  SUM(CASE WHEN item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND (
        video_detail_list NOT LIKE '%"videoUrl":"http%'
     OR video_detail_list NOT LIKE '%"firstImg":"http%'
     OR video_detail_list NOT LIKE '%"bitrate":%' OR video_detail_list LIKE '%"bitrate":""%' OR video_detail_list LIKE '%"bitrate":null%'
     OR video_detail_list NOT LIKE '%"codecType":%' OR video_detail_list LIKE '%"codecType":""%' OR video_detail_list LIKE '%"codecType":null%'
     OR video_detail_list NOT LIKE '%"videoResolution":%' OR video_detail_list LIKE '%"videoResolution":""%' OR video_detail_list LIKE '%"videoResolution":null%'
     OR video_detail_list NOT LIKE '%"videoWidth":%' OR video_detail_list LIKE '%"videoWidth":""%' OR video_detail_list LIKE '%"videoWidth":null%'
     OR video_detail_list NOT LIKE '%"videoHeight":%' OR video_detail_list LIKE '%"videoHeight":""%' OR video_detail_list LIKE '%"videoHeight":null%'
  ) THEN 1 ELSE 0 END) AS video_detail_incomplete_n,
  SUM(CASE WHEN item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-30' AND (
       video_detail_list NOT LIKE '%"fileMd5":%' OR video_detail_list LIKE '%"fileMd5":""%' OR video_detail_list LIKE '%"fileMd5":null%'
  ) THEN 1 ELSE 0 END) AS filemd5_missing_n,
  SUM(CASE WHEN item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null') THEN 1 ELSE 0 END) AS body_null_n,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null') THEN 1 ELSE 0 END) AS word_cnt_null_n,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null') THEN 1 ELSE 0 END) AS image_cnt_null_n,
  SUM(CASE WHEN from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-05-22' AND (
       ai_article IS NULL OR ai_article = '' OR LOWER(ai_article) = 'null'
    OR (item_type = 'NEWS' AND ai_article NOT IN ('0','1'))
    OR (item_type != 'NEWS' AND ai_article NOT IN ('0','1','2','3','4','5'))
  ) THEN 1 ELSE 0 END) AS ai_article_bad_n,
  SUM(CASE WHEN
       (publish_time IS NULL OR publish_time = '' OR LOWER(publish_time) = 'null')
    OR (author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null')
    OR (xm_author_id IS NULL OR xm_author_id = '' OR LOWER(xm_author_id) = 'null')
    OR (a_cp != 'cn-beike-djy' AND (author_ip IS NULL OR author_ip = '' OR LOWER(author_ip) = 'null'))
    OR (url IS NULL OR url = '' OR LOWER(url) = 'null' OR (url NOT LIKE 'http://%' AND url NOT LIKE 'https://%'))
    OR (image IS NULL OR image = '' OR LOWER(image) = 'null')
    OR (author_id != 'aigc01IncisiveInsightHub' AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null'))
    OR (author_id != 'aigc01IncisiveInsightHub' AND (category IS NULL OR category = '' OR LOWER(category) = 'null'))
    OR (item_type != 'NEWS' AND (video_duration IS NULL OR video_duration = '' OR LOWER(video_duration) = 'null' OR video_duration = '0' OR video_duration LIKE '0.%' OR video_duration LIKE '-%'))
    OR (item_type != 'NEWS' AND (video_detail_list IS NULL OR video_detail_list = '' OR LOWER(video_detail_list) = 'null'))
    OR (item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND (
         video_detail_list NOT LIKE '%"videoUrl":"http%'
      OR video_detail_list NOT LIKE '%"firstImg":"http%'
      OR video_detail_list NOT LIKE '%"bitrate":%' OR video_detail_list LIKE '%"bitrate":""%' OR video_detail_list LIKE '%"bitrate":null%'
      OR video_detail_list NOT LIKE '%"codecType":%' OR video_detail_list LIKE '%"codecType":""%' OR video_detail_list LIKE '%"codecType":null%'
      OR video_detail_list NOT LIKE '%"videoResolution":%' OR video_detail_list LIKE '%"videoResolution":""%' OR video_detail_list LIKE '%"videoResolution":null%'
      OR video_detail_list NOT LIKE '%"videoWidth":%' OR video_detail_list LIKE '%"videoWidth":""%' OR video_detail_list LIKE '%"videoWidth":null%'
      OR video_detail_list NOT LIKE '%"videoHeight":%' OR video_detail_list LIKE '%"videoHeight":""%' OR video_detail_list LIKE '%"videoHeight":null%'
    ))
    OR (item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-30' AND (
         video_detail_list NOT LIKE '%"fileMd5":%' OR video_detail_list LIKE '%"fileMd5":""%' OR video_detail_list LIKE '%"fileMd5":null%'
    ))
    OR (item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null'))
    OR (from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-05-22' AND (
         ai_article IS NULL OR ai_article = '' OR LOWER(ai_article) = 'null'
      OR (item_type = 'NEWS' AND ai_article NOT IN ('0','1'))
      OR (item_type != 'NEWS' AND ai_article NOT IN ('0','1','2','3','4','5'))
    ))
  THEN 1 ELSE 0 END) AS bad_any
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
  AND create_time IS NOT NULL
  AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '{{CUTOFF_ISO_6}}'  -- CHART_WINDOW_START（运行时注入）
  AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_0}}'  -- CHART_WINDOW_END（运行时注入）
  {{EXEMPT_FILTER}}
GROUP BY a_cp, from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd')
ORDER BY a_cp, create_date
