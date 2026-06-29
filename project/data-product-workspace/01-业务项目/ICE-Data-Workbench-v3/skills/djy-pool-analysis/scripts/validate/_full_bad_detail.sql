-- beike + dihui 全量异常内容明细（当前内容池存量视角，不做快照差集）
-- 只要当前仍命中任一规则就输出；Paimon 查询层按 a_item_id 自动去重
-- 注：author_ip 规则全生效；fileMd5 / ai_article 按生效日起算（4/29 / 5/22）

SELECT
  a_cp,
  a_item_id,
  item_type,
  author_id,
  SUBSTR(item_title, 1, 40) AS title_40,
  from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd HH:mm') AS create_at,
  CASE WHEN publish_time IS NULL OR publish_time = '' OR LOWER(publish_time) = 'null' THEN 1 ELSE 0 END AS f_publish_time,
  CASE WHEN author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null' THEN 1 ELSE 0 END AS f_author_image,
  CASE WHEN xm_author_id IS NULL OR xm_author_id = '' OR LOWER(xm_author_id) = 'null' THEN 1 ELSE 0 END AS f_xm_author_id,
  CASE WHEN a_cp != 'cn-beike-djy' AND (author_ip IS NULL OR author_ip = '' OR LOWER(author_ip) = 'null') THEN 1 ELSE 0 END AS f_author_ip,
  CASE WHEN url IS NULL OR url = '' OR LOWER(url) = 'null' OR (url NOT LIKE 'http://%' AND url NOT LIKE 'https://%') THEN 1 ELSE 0 END AS f_url,
  CASE WHEN image IS NULL OR image = '' OR LOWER(image) = 'null' THEN 1 ELSE 0 END AS f_image,
  CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null') THEN 1 ELSE 0 END AS f_lead_author,
  CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (category IS NULL OR category = '' OR LOWER(category) = 'null') THEN 1 ELSE 0 END AS f_category,
  CASE WHEN item_type != 'NEWS' AND (video_duration IS NULL OR video_duration = '' OR LOWER(video_duration) = 'null' OR video_duration = '0' OR video_duration LIKE '0.%' OR video_duration LIKE '-%') THEN 1 ELSE 0 END AS f_video_duration,
  CASE WHEN item_type != 'NEWS' AND (video_detail_list IS NULL OR video_detail_list = '' OR LOWER(video_detail_list) = 'null') THEN 1 ELSE 0 END AS f_video_detail_empty,
  CASE WHEN item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND (
        video_detail_list NOT LIKE '%"videoUrl":"http%'
     OR video_detail_list NOT LIKE '%"firstImg":"http%'
     OR video_detail_list NOT LIKE '%"bitrate":%' OR video_detail_list LIKE '%"bitrate":""%' OR video_detail_list LIKE '%"bitrate":null%'
     OR video_detail_list NOT LIKE '%"codecType":%' OR video_detail_list LIKE '%"codecType":""%' OR video_detail_list LIKE '%"codecType":null%'
     OR video_detail_list NOT LIKE '%"videoResolution":%' OR video_detail_list LIKE '%"videoResolution":""%' OR video_detail_list LIKE '%"videoResolution":null%'
     OR video_detail_list NOT LIKE '%"videoWidth":%' OR video_detail_list LIKE '%"videoWidth":""%' OR video_detail_list LIKE '%"videoWidth":null%'
     OR video_detail_list NOT LIKE '%"videoHeight":%' OR video_detail_list LIKE '%"videoHeight":""%' OR video_detail_list LIKE '%"videoHeight":null%'
  ) THEN 1 ELSE 0 END AS f_video_detail_7,
  CASE WHEN item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null') THEN 1 ELSE 0 END AS f_body_news,
  CASE WHEN item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null') THEN 1 ELSE 0 END AS f_word_cnt,
  CASE WHEN item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null') THEN 1 ELSE 0 END AS f_image_cnt
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy')
  AND date <= '20260429'
  AND (
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
    OR (item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null'))
  )
  {{EXEMPT_FILTER}}
ORDER BY a_cp, create_time DESC
