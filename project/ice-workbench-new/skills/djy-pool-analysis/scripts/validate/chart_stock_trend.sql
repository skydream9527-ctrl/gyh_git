-- 在线池"异常存量"趋势 · 近 7 天 cutoff × 4 CP × 字段维度
-- 口径：在线池累计「create_time ≤ cutoff」（online='1' AND delete_reason 空 + 入库时间）
-- 演进史：
--   · 历史曾用 paimon 分区键 `date <= 'YYYYMMDD'`，但 paimon upsert 表 `date` 字段会
--     随 CP 重推被更新到最新推送日，重推老内容时计数虚涨 → 2026-05-25 切到 create_time
--   · 历史无 online 过滤，下线内容里的旧异常（如 dihui 860 个 multi_xm 残留）拉高
--     卡片合计 244K → 2026-05-26 切到在线池，与日常推 CP 群的清单口径一致
-- 切换前后曲线均不可比；详见 references/validate/faq.md。
-- 覆盖图二（bad_any 趋势）+ 图三-⑥（每字段存量趋势）
-- 时序敏感：UNION ALL 7 cutoff 在数据空间早高峰会触发 250s 客户端超时，
--   故 cron 排在 10:30（错峰，集群空闲，能跑通），不要回退到 09:45。

SELECT
  cutoff AS snap_date,
  a_cp,
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
  SUM(CASE WHEN item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null') THEN 1 ELSE 0 END) AS body_null_n,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null') THEN 1 ELSE 0 END) AS word_cnt_null_n,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null') THEN 1 ELSE 0 END) AS image_cnt_null_n,
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
    OR (item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null'))
    OR (item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null'))
  THEN 1 ELSE 0 END) AS bad_any
FROM (
  SELECT *, '{{CUTOFF_6}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_6}}'
  UNION ALL SELECT *, '{{CUTOFF_5}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_5}}'
  UNION ALL SELECT *, '{{CUTOFF_4}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_4}}'
  UNION ALL SELECT *, '{{CUTOFF_3}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_3}}'
  UNION ALL SELECT *, '{{CUTOFF_2}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_2}}'
  UNION ALL SELECT *, '{{CUTOFF_1}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_1}}'
  UNION ALL SELECT *, '{{CUTOFF_0}}' AS cutoff FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy') AND online = '1' AND (delete_reason IS NULL OR delete_reason = '') AND create_time IS NOT NULL AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_0}}'
) t
WHERE 1=1
  {{EXEMPT_FILTER}}
GROUP BY cutoff, a_cp
ORDER BY a_cp, cutoff
