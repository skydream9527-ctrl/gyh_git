-- dihui / beike 4/28→4/29 新增未修内容明细
-- 口径：截止 4/29 存量异常 - 截止 4/28 存量异常 = 新增未修的 item_id
-- 取这些 item 在 4/29 快照里的详情 + 各异常字段标志

WITH bad_29 AS (
  SELECT a_item_id, a_cp, item_type, author_id, item_title, create_time,
    publish_time, author_image, xm_author_id, author_ip, url, image,
    lead_author_id, category, video_duration, video_detail_list,
    body, e_xm_body_word_cnt, e_xm_image_cnt
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
),
bad_28 AS (
  SELECT a_item_id
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy')
    AND date <= '20260428'
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
)
SELECT
  b29.a_cp,
  b29.a_item_id,
  b29.item_type,
  SUBSTR(b29.item_title, 1, 40) AS title_40,
  from_unixtime(CAST(b29.create_time AS BIGINT) / 1000, 'MM-dd HH:mm') AS create_at,
  -- 异常标志（1=命中）
  CASE WHEN b29.publish_time IS NULL OR b29.publish_time = '' OR LOWER(b29.publish_time) = 'null' THEN 1 ELSE 0 END AS f_publish_time,
  CASE WHEN b29.author_image IS NULL OR b29.author_image = '' OR LOWER(b29.author_image) = 'null' THEN 1 ELSE 0 END AS f_author_image,
  CASE WHEN b29.xm_author_id IS NULL OR b29.xm_author_id = '' OR LOWER(b29.xm_author_id) = 'null' THEN 1 ELSE 0 END AS f_xm_author_id,
  CASE WHEN b29.a_cp != 'cn-beike-djy' AND (b29.author_ip IS NULL OR b29.author_ip = '' OR LOWER(b29.author_ip) = 'null') THEN 1 ELSE 0 END AS f_author_ip,
  CASE WHEN b29.url IS NULL OR b29.url = '' OR LOWER(b29.url) = 'null' OR (b29.url NOT LIKE 'http://%' AND b29.url NOT LIKE 'https://%') THEN 1 ELSE 0 END AS f_url,
  CASE WHEN b29.image IS NULL OR b29.image = '' OR LOWER(b29.image) = 'null' THEN 1 ELSE 0 END AS f_image,
  CASE WHEN b29.author_id != 'aigc01IncisiveInsightHub' AND (b29.lead_author_id IS NULL OR b29.lead_author_id = '' OR LOWER(b29.lead_author_id) = 'null') THEN 1 ELSE 0 END AS f_lead_author,
  CASE WHEN b29.author_id != 'aigc01IncisiveInsightHub' AND (b29.category IS NULL OR b29.category = '' OR LOWER(b29.category) = 'null') THEN 1 ELSE 0 END AS f_category,
  CASE WHEN b29.item_type != 'NEWS' AND (b29.video_duration IS NULL OR b29.video_duration = '' OR LOWER(b29.video_duration) = 'null' OR b29.video_duration = '0' OR b29.video_duration LIKE '0.%' OR b29.video_duration LIKE '-%') THEN 1 ELSE 0 END AS f_video_duration,
  CASE WHEN b29.item_type != 'NEWS' AND b29.video_detail_list IS NOT NULL AND b29.video_detail_list != '' AND (
        b29.video_detail_list NOT LIKE '%"videoUrl":"http%'
     OR b29.video_detail_list NOT LIKE '%"firstImg":"http%'
     OR b29.video_detail_list NOT LIKE '%"bitrate":%' OR b29.video_detail_list LIKE '%"bitrate":""%' OR b29.video_detail_list LIKE '%"bitrate":null%'
     OR b29.video_detail_list NOT LIKE '%"codecType":%' OR b29.video_detail_list LIKE '%"codecType":""%' OR b29.video_detail_list LIKE '%"codecType":null%'
     OR b29.video_detail_list NOT LIKE '%"videoResolution":%' OR b29.video_detail_list LIKE '%"videoResolution":""%' OR b29.video_detail_list LIKE '%"videoResolution":null%'
     OR b29.video_detail_list NOT LIKE '%"videoWidth":%' OR b29.video_detail_list LIKE '%"videoWidth":""%' OR b29.video_detail_list LIKE '%"videoWidth":null%'
     OR b29.video_detail_list NOT LIKE '%"videoHeight":%' OR b29.video_detail_list LIKE '%"videoHeight":""%' OR b29.video_detail_list LIKE '%"videoHeight":null%'
  ) THEN 1 ELSE 0 END AS f_video_detail_7,
  CASE WHEN b29.item_type = 'NEWS' AND (b29.body IS NULL OR b29.body = '' OR LOWER(b29.body) = 'null') THEN 1 ELSE 0 END AS f_body_news,
  CASE WHEN b29.item_type = 'NEWS' AND (b29.e_xm_body_word_cnt IS NULL OR b29.e_xm_body_word_cnt = '' OR LOWER(b29.e_xm_body_word_cnt) = 'null') THEN 1 ELSE 0 END AS f_word_cnt,
  CASE WHEN b29.item_type = 'NEWS' AND (b29.e_xm_image_cnt IS NULL OR b29.e_xm_image_cnt = '' OR LOWER(b29.e_xm_image_cnt) = 'null') THEN 1 ELSE 0 END AS f_image_cnt
FROM bad_29 b29
LEFT JOIN bad_28 b28 ON b29.a_item_id = b28.a_item_id
WHERE b28.a_item_id IS NULL
ORDER BY b29.a_cp, b29.create_time DESC
