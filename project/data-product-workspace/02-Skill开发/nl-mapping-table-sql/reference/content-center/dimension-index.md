# Content Center - Dimension Index

## Dimension Fields by Table

### dim_newhome_did_label_di（did标签表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段,格式YYYYMMDD | 必选筛选 |
| 内容中心DAU | is_app_dau_2024 | INT | 是否内容中心DAU用户 | 常用筛选(=1) |
| 新老用户 | is_new_2024 | INT | 是否新用户 | 常用筛选/分组 |
| 信息流大盘DAU | is_dau_feed_dapan_2024 | INT | 是否信息流大盘DAU用户 | 常用筛选(=1) |
| 大盘有效用户 | is_valid_dapan_2024 | INT | 是否大盘有效用户 | 常用筛选(=1) |
| 信息流消费用户 | is_feed_consume_2025 | INT | 是否信息流消费用户 | 常用筛选(=1) |
| app总时长 | app_dura_1d | BIGINT | 1天app总时长（毫秒） | 深度用户判断 |
| 浏览器有效用户 | is_valid_browser_2025 | INT | 是否浏览器有效用户 | 常用筛选(=1) |

---

### dm_newhome_multi_dimension_indicators_di（多维指标聚合表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 内容中心DAU | is_app_dau_2024 | INT | 是否内容中心DAU用户 | 常用筛选(=1) |
| 新老用户 | is_new_2024 | INT | 是否新用户 | 常用筛选/分组 |
| 信息流大盘DAU | is_dau_feed_dapan_2024 | INT | 是否信息流大盘DAU用户 | 常用筛选(=1) |
| 大盘有效用户 | is_valid_dapan_2024 | INT | 是否大盘有效用户 | 常用筛选(=1) |
| 信息流消费用户 | is_feed_consume_2025 | INT | 是否信息流消费用户 | 常用筛选(=1) |
| app总时长 | app_dura_1d | BIGINT | 1天app总时长（毫秒） | 深度用户判断 |
| 浏览器有效用户 | is_valid_browser_2025 | INT | 是否浏览器有效用户 | 常用筛选(=1) |
| 启动方式 | app_launch_way | STRING | 启动方式 | 枚举值查询 |
| 体裁 | item_type | STRING | 内容类型 | 枚举值查询 |
| App版本 | app_version | STRING | 客户端版本 | 枚举值查询(TOP50) |
| 系统版本 | os_version | STRING | 系统版本 | 枚举值查询(TOP50) |
| 机型 | phone_model | STRING | 设备机型 | 枚举值查询(TOP50) |
| 频道 | feed_channel | STRING | 信息流频道 | 枚举值查询 |

---

### dm_newhome_multi_dimension_retain_indicators_di（多维留存指标表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 应用端口 | app_port | STRING | 应用端口 | 枚举值查询 |
| 用户类型 | history_user_type | STRING | 整体/新用户/老用户 | 枚举值查询 |
| 活跃类型 | active_user_type | STRING | 整体/信息流活跃/非信息流活跃 | 枚举值查询 |
| 信息流有效类型 | feed_valid_user_type | STRING | 整体/信息流有效/非信息流有效 | 枚举值查询 |
| 消费类型 | consume_user_type | STRING | 整体/信息流消费/非信息流消费 | 枚举值查询 |
| 时长类型 | duration_user_type | STRING | 整体/深度用户/非深度用户 | 枚举值查询 |
| 浏览器有效类型 | browser_valid_user_type | STRING | 整体/浏览器有效/非浏览器有效 | 枚举值查询 |

---

### ads_newhome_user_type_core_indicators_di（用户类型核心指标表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 用户类型 | user_type | STRING | 用户分类 | 枚举值查询 |

---

### ads_newhome_item_type_core_indicators_di（内容转化主题核心指标表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 体裁 | item_type | STRING | 整体/图文/小视频/短视频/短剧/直播/小说/其他 | 枚举值查询 |

---

### ads_newhome_page_indicators_di（小场景指标表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 页面 | page | STRING | 页面标识 | 枚举值查询 |

---

### ads_newhome_finance_core_indicators_di（财收核心指标表）

| Dimension | Field | Type | Description | Query Type |
|-----------|-------|------|-------------|------------|
| 日期 | date | INT | 分区字段 | 必选筛选 |
| 广告位场景 | ad_position_scene | STRING | 广告位场景 | 枚举值查询 |
| 广告位 | tag_id | STRING | 广告位标识 | 枚举值查询 |

---

## Dimension Mapping Table

| User Query | Mapped Dimension | SQL Field |
|------------|------------------|-----------|
| "按启动方式" | 启动方式 | app_launch_way |
| "按体裁" | 体裁 | item_type |
| "按版本" | App版本 | app_version |
| "按系统版本" | 系统版本 | os_version |
| "按机型" | 机型 | phone_model |
| "按频道" | 频道 | feed_channel |
| "按用户类型" | 用户类型 | user_type / history_user_type |
| "按页面" | 页面 | page |
| "按广告位场景" | 广告位场景 | ad_position_scene |
| "按广告位" | 广告位 | tag_id |
| "按活跃类型" | 活跃类型 | active_user_type |
| "按消费类型" | 消费类型 | consume_user_type |
| "按时长类型" | 时长类型 | duration_user_type |
| "按浏览器有效类型" | 浏览器有效类型 | browser_valid_user_type |
| "按信息流有效类型" | 信息流有效类型 | feed_valid_user_type |

---

## Unsupported Dimensions (不在dm表中，需从dwm表查询)

以下维度在需求文档中出现，但不在当前dm映射表中，如需查询请联系开发者补充：

| Dimension | Field | Source Table | Description |
|-----------|-------|-------------|-------------|
| 实验组 | exp_id | dwm_newhome_event_aggregation_label_di | 实验分组 |
| 三方调起包名 | third_packagename | dwm_newhome_event_aggregation_label_di | 三方调起来源包名 |
| 是否冷启 | is_coldstart | dwm_newhome_event_aggregation_label_di | 冷启动标记 |
| 是否有上划行为 | is_feed_sliding | dwm_newhome_event_aggregation_label_di | 信息流上划行为标记 |
| 内容源 | source | dwm_newhome_event_aggregation_label_di | 内容来源 |
