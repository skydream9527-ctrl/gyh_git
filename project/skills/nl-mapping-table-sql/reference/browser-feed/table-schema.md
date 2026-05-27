# Browser Feed - Mapping Table Schema

## Table Overview

浏览器信息流**没有独立的dm表**，复用浏览器整体的dm表，通过 `is_dau_feed_dapan_2024 = 1` 筛选信息流大盘DAU用户。

| # | Table Name | Full Name | Description |
|---|-----------|-----------|-------------|
| 1 | dm_browser_multi_dimension_indicators_di | 多维指标聚合表 | 浏览器核心指标多维度聚合日表 |
| 2 | dm_browser_multi_dimension_retain_indicators_di | 留存计算用did粒度指标表 | 留存计算用did粒度指标表，通过自关联计算留存 |
| 3 | ads_browser_user_type_core_indicators_di | 用户类型核心指标表 | 用户日活主题大数打平表 |
| 4 | ads_browser_item_type_core_indicators_di | 内容转化主题核心指标表 | 体裁维度内容转化大数打平表 |
| 5 | ads_browser_page_indicators_di | 小场景指标表 | 页面级指标聚合表 |
| 6 | ads_browser_finance_core_indicators_di | 财收核心指标表 | 广告收入相关指标聚合表 |

---

## Key Filter for Browser Feed

```sql
-- 信息流大盘DAU用户筛选条件
is_dau_feed_dapan_2024 = 1
```

---

## Table Schemas

### 1. dm_browser_multi_dimension_indicators_di（多维指标聚合表）

**Database**: `iceberg_zjyprc_hadoop.browser`
**粒度**: date + did + 各维度

```sql
CREATE TABLE iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_indicators_di (
  date INT COMMENT '日期',
  did STRING COMMENT '设备id',
  is_app_dau_2024 INT COMMENT '是否浏览器DAU用户，1：是，0：否',
  is_new_2024 INT COMMENT '是否是浏览器新用户，1：是，0：否',
  is_dau_feed_dapan_2024 INT COMMENT '是否浏览器信息流大盘DAU用户，1：是，0：否',
  is_valid_dapan_2024 INT COMMENT '是否大盘有效用户，1：是，0：否',
  is_feed_consume_2025 INT COMMENT '是否是信息流消费用户，1：是，0：否',
  app_dura_1d BIGINT COMMENT '1天app总时长（毫秒）',
  is_valid_browser_2025 INT COMMENT '是否是浏览器有效用户，1：是，0：否',
  app_launch_way STRING COMMENT '启动方式',
  item_type STRING COMMENT '体裁',
  app_version STRING COMMENT 'app版本',
  os_version STRING COMMENT '系统版本',
  phone_model STRING COMMENT '机型',
  feed_channel STRING COMMENT '频道',
  da_pv BIGINT COMMENT '日活pv',
  dau BIGINT COMMENT 'dau',
  app_duration_s BIGINT COMMENT '应用使用总时长（秒）',
  feed_duration_s BIGINT COMMENT '信息流使用时长（秒）',
  consum_duration_s BIGINT COMMENT '信息流消费时长（秒）',
  expose_pv BIGINT COMMENT '曝光量',
  expose_uv BIGINT COMMENT '曝光用户数',
  click_pv BIGINT COMMENT '点击量',
  click_uv BIGINT COMMENT '点击用户数',
  view_pv BIGINT COMMENT '浏览量',
  view_uv BIGINT COMMENT '浏览用户数',
  view_duration_s BIGINT COMMENT '浏览时长（秒）',
  play_pv BIGINT COMMENT '开始播放量',
  play_uv BIGINT COMMENT '开始播放用户数',
  play_duration_s BIGINT COMMENT '播放时长（秒）',
  finish_play_pv BIGINT COMMENT '完成播放量',
  like_pv BIGINT COMMENT '点赞量',
  share_pv BIGINT COMMENT '分享量',
  collect_pv BIGINT COMMENT '收藏量',
  comment_pv BIGINT COMMENT '评论量'
)
USING iceberg
PARTITIONED BY (date)
```

---

### 2. dm_browser_multi_dimension_retain_indicators_di（留存计算用did粒度指标表）

**Database**: `iceberg_zjyprc_hadoop.browser`
**粒度**: date + did 唯一
**说明**: 与多维指标聚合表结构类似，但仅保留 app_launch_way、item_type 两个维度，用于通过自关联计算留存

```sql
CREATE TABLE iceberg_zjyprc_hadoop.browser.dm_browser_multi_dimension_retain_indicators_di (
  date INT COMMENT '日期',
  did STRING COMMENT '设备id',
  is_app_dau_2024 INT COMMENT '是否浏览器DAU用户，1：是，0：否',
  is_new_2024 INT COMMENT '是否是浏览器新用户，1：是，0：否',
  is_dau_feed_dapan_2024 INT COMMENT '是否浏览器信息流大盘DAU用户，1：是，0：否',
  is_valid_dapan_2024 INT COMMENT '是否大盘有效用户，1：是，0：否',
  is_feed_consume_2025 INT COMMENT '是否是信息流消费用户，1：是，0：否',
  app_dura_1d BIGINT COMMENT '1天app总时长（毫秒）',
  is_valid_browser_2025 INT COMMENT '是否是浏览器有效用户，1：是，0：否',
  app_launch_way STRING COMMENT '启动方式',
  item_type STRING COMMENT '体裁',
  da_pv BIGINT COMMENT '日活pv',
  app_duration_s BIGINT COMMENT '应用使用总时长（秒）',
  feed_duration_s BIGINT COMMENT '信息流使用时长（秒）',
  consum_duration_s BIGINT COMMENT '信息流消费时长（秒）',
  expose_pv BIGINT COMMENT '曝光量',
  click_pv BIGINT COMMENT '点击量',
  view_pv BIGINT COMMENT '浏览量',
  view_duration_s BIGINT COMMENT '浏览时长（秒）',
  play_pv BIGINT COMMENT '开始播放量',
  play_duration_s BIGINT COMMENT '播放时长（秒）',
  finish_play_pv BIGINT COMMENT '完成播放量',
  like_pv BIGINT COMMENT '点赞量',
  share_pv BIGINT COMMENT '分享量',
  collect_pv BIGINT COMMENT '收藏量',
  comment_pv BIGINT COMMENT '评论量'
)
USING iceberg
PARTITIONED BY (date)
```

---

### 3. ads_browser_user_type_core_indicators_di（用户类型核心指标表）

**Database**: `iceberg_zjyprc_hadoop.browser`

```sql
CREATE TABLE iceberg_zjyprc_hadoop.browser.ads_browser_user_type_core_indicators_di (
  date INT COMMENT '日期',
  user_type STRING COMMENT '用户类型',
  dau BIGINT COMMENT 'dau',
  mau BIGINT COMMENT '月活人数',
  app_duration_s BIGINT COMMENT '应用使用总时长（秒）',
  feed_duration_s BIGINT COMMENT '信息流使用时长（秒）',
  consum_duration_s BIGINT COMMENT '信息流消费时长（秒）'
)
USING iceberg
PARTITIONED BY (date)
```

---

### 4. ads_browser_item_type_core_indicators_di（内容转化主题核心指标表）

**Database**: `iceberg_zjyprc_hadoop.browser`

```sql
CREATE TABLE iceberg_zjyprc_hadoop.browser.ads_browser_item_type_core_indicators_di (
  date INT COMMENT '日期',
  item_type STRING COMMENT '体裁',
  expose_pv BIGINT COMMENT '曝光量',
  expose_uv BIGINT COMMENT '曝光用户数',
  click_pv BIGINT COMMENT '点击量',
  click_uv BIGINT COMMENT '点击用户数',
  view_pv BIGINT COMMENT '浏览量',
  view_uv BIGINT COMMENT '浏览用户数',
  view_duration_s BIGINT COMMENT '浏览时长（秒）',
  play_pv BIGINT COMMENT '开始播放量',
  play_uv BIGINT COMMENT '开始播放用户数',
  play_duration_s BIGINT COMMENT '播放时长（秒）',
  finish_play_pv BIGINT COMMENT '完成播放量',
  like_pv BIGINT COMMENT '点赞量',
  share_pv BIGINT COMMENT '分享量',
  collect_pv BIGINT COMMENT '收藏量',
  comment_pv BIGINT COMMENT '评论量'
)
USING iceberg
PARTITIONED BY (date)
```

---

### 5. ads_browser_page_indicators_di（小场景指标表）

**Database**: `iceberg_zjyprc_hadoop.browser`

```sql
CREATE TABLE iceberg_zjyprc_hadoop.browser.ads_browser_page_indicators_di (
  date INT COMMENT '日期',
  page STRING COMMENT '页面',
  expose_pv BIGINT COMMENT '曝光量',
  expose_uv BIGINT COMMENT '曝光用户数',
  click_pv BIGINT COMMENT '点击量',
  click_uv BIGINT COMMENT '点击用户数',
  view_pv BIGINT COMMENT '浏览量',
  view_uv BIGINT COMMENT '浏览用户数',
  view_duration_s DOUBLE COMMENT '浏览时长（秒）',
  play_pv BIGINT COMMENT '开始播放量',
  play_uv BIGINT COMMENT '开始播放用户数',
  play_duration_s DOUBLE COMMENT '播放时长（秒）',
  finish_play_pv BIGINT COMMENT '完成播放量',
  like_pv BIGINT COMMENT '点赞量',
  share_pv BIGINT COMMENT '分享量',
  collect_pv BIGINT COMMENT '收藏量',
  comment_pv BIGINT COMMENT '评论量'
)
USING iceberg
PARTITIONED BY (date)
```

---

### 6. ads_browser_finance_core_indicators_di（财收核心指标表）

**Database**: `doris_c3prc_xiaomi.browser`

```sql
CREATE TABLE doris_c3prc_xiaomi.browser.ads_browser_finance_core_indicators_di (
  date INT COMMENT '日期',
  ad_position_scene STRING COMMENT '广告位场景：图文详情页、视频详情页、小视频详情页、短视频频道',
  tag_id STRING COMMENT '广告位',
  gmv DOUBLE COMMENT '流水',
  revenue DOUBLE COMMENT '财收',
  ad_request_cnt BIGINT COMMENT '广告请求次数',
  ad_response_cnt BIGINT COMMENT '广告填充次数',
  expose_cnt BIGINT COMMENT '计费曝光',
  click_cnt BIGINT COMMENT '计费点击',
  download_cnt BIGINT COMMENT '广告下载量'
)
USING iceberg
PARTITIONED BY (date)
```
