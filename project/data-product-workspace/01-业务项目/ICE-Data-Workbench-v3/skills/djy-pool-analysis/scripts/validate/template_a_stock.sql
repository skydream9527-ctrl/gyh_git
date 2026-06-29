-- Template A · 在线池字段扫描（主报告基线）
-- 口径：在线池（online='1' AND delete_reason 空），按 a_cp 聚合
-- 2026-05-26 切到在线池：与日报 c2~c6 + 健康卡 + 推 CP 清单口径一致
-- 可选 item_type 拆分：把 GROUP BY a_cp 改为 GROUP BY a_cp, item_type
-- 可选当日增量：加 AND date = '{{DATE}}'（作为辅报告）

SELECT
  a_cp,
  COUNT(*) AS total,
  -- 规则 1 全类型必填
  SUM(CASE WHEN a_item_id IS NULL OR a_item_id = '' OR LOWER(a_item_id) = 'null' THEN 1 ELSE 0 END) AS a_item_id_n,
  -- 规则 3
  SUM(CASE WHEN publish_time IS NULL OR publish_time = '' OR LOWER(publish_time) = 'null' THEN 1 ELSE 0 END) AS publish_time_n,
  -- 规则 7（非空 + 值域 ∈ {'0','1'}，1=在线 / 0=下线）
  SUM(CASE WHEN online IS NULL OR online = '' OR LOWER(online) = 'null' OR online NOT IN ('0','1') THEN 1 ELSE 0 END) AS online_n,
  -- 规则 4/5
  SUM(CASE WHEN author_id IS NULL OR author_id = '' OR LOWER(author_id) = 'null' THEN 1 ELSE 0 END) AS author_id_n,
  SUM(CASE WHEN author_name IS NULL OR author_name = '' OR LOWER(author_name) = 'null' THEN 1 ELSE 0 END) AS author_name_n,
  -- 规则 10
  SUM(CASE WHEN author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null' THEN 1 ELSE 0 END) AS author_image_n,
  -- 规则 11
  SUM(CASE WHEN xm_author_id IS NULL OR xm_author_id = '' OR LOWER(xm_author_id) = 'null' THEN 1 ELSE 0 END) AS xm_author_id_n,
  -- 规则 12/13 全类型必填（2026-04-28 改动，含 NEWS），唯一 author-level 豁免：aigc01IncisiveInsightHub
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (lead_author_id IS NULL OR lead_author_id = '' OR LOWER(lead_author_id) = 'null') THEN 1 ELSE 0 END) AS lead_author_id_null,
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (lead_author_name IS NULL OR lead_author_name = '' OR LOWER(lead_author_name) = 'null') THEN 1 ELSE 0 END) AS lead_author_name_null,
  -- 规则 8
  SUM(CASE WHEN url IS NULL OR url = '' OR LOWER(url) = 'null' OR (url NOT LIKE 'http://%' AND url NOT LIKE 'https://%') THEN 1 ELSE 0 END) AS url_bad,
  -- 规则 9
  SUM(CASE WHEN image IS NULL OR image = '' OR LOWER(image) = 'null' THEN 1 ELSE 0 END) AS image_n,
  -- 规则 14/15/16 非 NEWS 必填
  -- 规则 14 全类型必填（2026-04-28 扩展，原非 NEWS），豁免 aigc01IncisiveInsightHub
  SUM(CASE WHEN author_id != 'aigc01IncisiveInsightHub' AND (category IS NULL OR category = '' OR LOWER(category) = 'null') THEN 1 ELSE 0 END) AS category_null,
  -- 规则 15 非 NEWS 必填 + 值 > 0（2026-04-28 升级，原只查空）
  SUM(CASE WHEN item_type != 'NEWS' AND (
        video_duration IS NULL OR video_duration = '' OR LOWER(video_duration) = 'null'
     OR video_duration = '0' OR video_duration LIKE '0.%' OR video_duration LIKE '-%'
  ) THEN 1 ELSE 0 END) AS video_duration_bad_nn,
  SUM(CASE WHEN item_type != 'NEWS' AND (video_detail_list IS NULL OR video_detail_list = '' OR LOWER(video_detail_list) = 'null') THEN 1 ELSE 0 END) AS video_detail_list_empty_nn,
  -- 规则 16.1 video_detail_list 内 7 个必填字段非空（2026-04-28 确认）
  -- 必填（告警）：videoUrl / firstImg / bitrate / codecType / videoResolution / videoWidth / videoHeight
  -- 可选（缺失/空不告警）：videoUrlBackup1（允许为空）/ urlExpiredTime / size / videoType / frameRate（非全 CP 都有）
  -- 违规：任一必填字段缺失 OR 值为空串 OR 值为 null（数字 0 暂不算，一致规则 15）
  SUM(CASE WHEN item_type != 'NEWS' AND video_detail_list IS NOT NULL AND video_detail_list != '' AND (
        video_detail_list NOT LIKE '%"videoUrl":"http%'
     OR video_detail_list NOT LIKE '%"firstImg":"http%'
     OR video_detail_list NOT LIKE '%"bitrate":%'       OR video_detail_list LIKE '%"bitrate":""%'       OR video_detail_list LIKE '%"bitrate":null%'
     OR video_detail_list NOT LIKE '%"codecType":%'     OR video_detail_list LIKE '%"codecType":""%'     OR video_detail_list LIKE '%"codecType":null%'
     OR video_detail_list NOT LIKE '%"videoResolution":%' OR video_detail_list LIKE '%"videoResolution":""%' OR video_detail_list LIKE '%"videoResolution":null%'
     OR video_detail_list NOT LIKE '%"videoWidth":%'    OR video_detail_list LIKE '%"videoWidth":""%'    OR video_detail_list LIKE '%"videoWidth":null%'
     OR video_detail_list NOT LIKE '%"videoHeight":%'   OR video_detail_list LIKE '%"videoHeight":""%'   OR video_detail_list LIKE '%"videoHeight":null%'
  ) THEN 1 ELSE 0 END) AS video_detail_incomplete_nn,
  -- 规则 16.2 · fileMd5 条件必填（2026-04-28 定稿）
  -- 生效范围：create_time >= 2026-04-29 的内容（4.29 正式生效，历史全部豁免）
  -- 违规：该范围内 fileMd5 缺失 OR 空串 OR null
  SUM(CASE WHEN item_type != 'NEWS'
    AND video_detail_list IS NOT NULL AND video_detail_list != ''
    AND create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-04-29'
    AND (
         video_detail_list NOT LIKE '%"fileMd5":%'
      OR video_detail_list LIKE '%"fileMd5":""%'
      OR video_detail_list LIKE '%"fileMd5":null%'
    )
    THEN 1 ELSE 0 END) AS filemd5_missing_nn,
  -- 规则 17/18/19 NEWS 必填
  SUM(CASE WHEN item_type = 'NEWS' AND (body IS NULL OR body = '' OR LOWER(body) = 'null') THEN 1 ELSE 0 END) AS body_null_news,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_body_word_cnt IS NULL OR e_xm_body_word_cnt = '' OR LOWER(e_xm_body_word_cnt) = 'null') THEN 1 ELSE 0 END) AS e_xm_body_word_cnt_null_news,
  SUM(CASE WHEN item_type = 'NEWS' AND (e_xm_image_cnt IS NULL OR e_xm_image_cnt = '' OR LOWER(e_xm_image_cnt) = 'null') THEN 1 ELSE 0 END) AS e_xm_image_cnt_null_news,
  -- 规则 22 · ai_article 条件必填 + 值域（2026-04-28 新增，生效日 2026-05-22）
  -- 生效范围：create_time >= 2026-05-22
  -- 值域：NEWS ∈ {'0','1'} · VIDEO/MINIVIDEO ∈ {'0','1','2','3','4','5'}
  -- 违规：在生效范围内空 OR 值超出允许集
  SUM(CASE WHEN create_time IS NOT NULL
    AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') >= '2026-05-22'
    AND (
         ai_article IS NULL OR ai_article = '' OR LOWER(ai_article) = 'null'
      OR (item_type = 'NEWS' AND ai_article NOT IN ('0','1'))
      OR (item_type != 'NEWS' AND ai_article NOT IN ('0','1','2','3','4','5'))
    )
    THEN 1 ELSE 0 END) AS ai_article_bad,
  -- 规则 23 · author_ip 全类型必填（2026-04-28 新增，无生效日期，全量告警）
  -- CP 级豁免：beike（cn-beike-djy）确认部分作者无法获取 IP 属地，空值属业务正常态，不计异常
  SUM(CASE WHEN a_cp != 'cn-beike-djy' AND (author_ip IS NULL OR author_ip = '' OR LOWER(author_ip) = 'null') THEN 1 ELSE 0 END) AS author_ip_null
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
  AND online = '1'
  AND (delete_reason IS NULL OR delete_reason = '')
  {{EXEMPT_FILTER}}
GROUP BY a_cp
ORDER BY total DESC
