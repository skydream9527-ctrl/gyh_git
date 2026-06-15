-- 按入库时间 × 最新分区快照 · 看"入库日异常 vs 截至今日仍异常（未恢复）"
-- 口径：取 date='20260429' 最新分区（即今天的最新状态）
--       按 create_time 入库日分组
--       输出每日入库总数 + 当前仍异常数（未恢复）
-- 对比 chart_daily_trend（入库时异常数）可算出"已恢复 = 入库时异常 - 当前仍异常"

SELECT a_cp,
  from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') AS create_date,
  COUNT(*) AS total,
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
    OR (item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-29' AND (
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
  THEN 1 ELSE 0 END) AS bad_now
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
  AND date = '20260429'
  AND create_time IS NOT NULL
  AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-23'
  AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '2026-04-29'
  {{EXEMPT_FILTER}}
GROUP BY a_cp, from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd')
ORDER BY a_cp, create_date
