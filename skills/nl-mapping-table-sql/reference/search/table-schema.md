# Search - 表结构

> **数据源（口径权威）**：[`reference/search/data_tables.yaml`](data_tables.yaml)（搜索业务数据团队维护的唯一权威表清单）。
> 表名/字段如有冲突，**以 YAML 为准**，本文件为可读视图。

---

## 1. 表总览

| Key | 真实表名 | 层级 | 粒度 | 状态 |
|-----|---------|------|------|------|
| `dm_search_pv_uv` | `iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di` | dm（聚合表） | 日 + 搜索引擎 | aligned |
| `ads_search_intent` | `iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_hot_search_word_dod_metrics_di` | ads（聚合表） | 日 + query + 意图分类 | aligned |
| `ads_search_intent_level1` | `iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di` | ads（聚合表） | 日 + 一级意图 + 结果意图 | aligned |
| `dm_browser_search_core` | `iceberg_zjyprc_hadoop.browser.dm_browser_search_core_indicators_2022_1d` | dm（聚合表） | 日 | aligned |
| `search_event` | `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442` | dwd（埋点宽表） | 单次事件 | partial_aligned |
| `search_event_global` | `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418` | dwd（埋点宽表） | 单次事件 | aligned |
| `search_result` | `ods_search_result_di` | ods（占位，待对齐） | 单次曝光/点击 | pending_alignment |
| `user_profile` | `dim_user_profile` | dim（占位，待对齐） | 用户级 | pending_alignment |
| `user_active` | `ods_user_active_di` | ods（占位，待对齐） | 用户日级 | pending_alignment |

> 所有表的分区字段都是 `date`，已对齐表均为 `INT YYYYMMDD`。

---

## 2. 中间表（dm / ads）— 优先使用

### 2.1 `dm_search_pv_uv` — 主动搜索 PV/UV 聚合表

- 真实表：`iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di`
- 粒度：按日 + 搜索引擎聚合（`search_engine='ALL'` 表示全量汇总）
- 来源：基于 dwd 442（search_security）+ 418（search）加工，已内置渠道归属和版本覆盖率逻辑，**查询时无需手动除以 0.9**

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 YYYYMMDD |
| `search_engine` | string | 搜索引擎维度，`'ALL'` = 全量汇总 |
| `active_search_pv` | double | 全量主动搜索 PV |
| `bro_active_search_pv` | double | 浏览器主动搜索 PV |
| `qs_active_search_pv` | double | 全搜主动搜索 PV（端内+端外） |
| `nh_active_search_pv` | double | NH 媒体（内容中心）主动搜索 PV |
| `active_search_uv` | double | 全量主动搜索 UV |
| `bro_active_search_uv` | double | 浏览器主动搜索 UV |
| `qs_active_search_uv` | double | 全搜主动搜索 UV |
| `nh_active_search_uv` | double | NH 媒体主动搜索 UV |
| `ai_search_uv` | double | AI 搜索 UV |
| `bro_ai_search_uv` | double | 浏览器 AI 搜索 UV |
| `qs_ai_search_uv` | double | 全搜 AI 搜索 UV |
| `ai_avg_search_uv` | double | AI 人均搜次 UV |
| `bro_ai_avg_search_uv` | double | 浏览器 AI 人均搜次 UV |
| `qs_ai_avg_search_uv` | double | 全搜 AI 人均搜次 UV |

**承载指标**：`active_search_pv`、`search_penetration`、`avg_search_per_user`

### 2.2 `ads_search_intent` — 搜索 query 意图分类表

- 真实表：`iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_hot_search_word_dod_metrics_di`
- 粒度：日 + query + 意图分类
- 适用：热门搜索词排行、按 query 维度的意图分布

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 |
| `query` | string | 搜索 query 文本 |
| `intention_name_result` | string | 意图分类结果 |
| `intention_name_level_1` | string | 一级意图（医疗健康/科技/影音娱乐/文化/出行/ACGN-游戏/人物/色情等），特殊值 `'未匹配内容意图'` |
| `intention_name_level_2` | string | 二级意图（子类） |
| `query_pv` | bigint | query 搜索 PV |
| `query_uv` | bigint | query 搜索 UV |
| `query_pv_ratio` | double | query PV 占比 |
| `query_pv_dod` | double | query PV 日环比 |
| `query_pv_wow` | double | query PV 周环比 |
| `query_pv_mom` | double | query PV 月环比 |
| `query_pv_7` | bigint | 最近 7 天 query PV |
| `query_pv_30` | bigint | 最近 30 天 query PV |

**注意**：查询时过滤掉 `intention_name_level_1` 中的 `'未匹配内容意图'` 和 `'未匹配领域意图'`。

### 2.3 `ads_search_intent_level1` — 一级领域意图聚合表

- 真实表：`iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di`
- 粒度：日 + 一级意图 + 结果意图（按意图聚合，不按 query）
- 适用：意图分布趋势、日/周/月环比对比

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 |
| `intention_name_result` | string | 结果意图（如：黄页查询、找不合规资源） |
| `intention_name_level_1` | string | 一级领域意图（医疗健康/科技/影音娱乐/色情等） |
| `query_pv` | bigint | 该意图当日搜索 PV |
| `query_uv` | bigint | 该意图当日搜索 UV |
| `query_pv_ratio` | double | 该意图 PV 占比 |
| `query_pv_7` | bigint | 该意图近 7 天 PV |
| `query_pv_7_ratio` | double | 该意图近 7 天 PV 占比 |
| `query_pv_30` | bigint | 该意图近 30 天 PV |
| `query_pv_30_ratio` | double | 该意图近 30 天 PV 占比 |

**与 `ads_search_intent` 的区别**：
- 本表按意图聚合，无内置 dod/wow/mom，环比需手动跨日期对比
- `ads_search_intent` 按 query 聚合，内置 dod/wow/mom

### 2.4 `dm_browser_search_core` — 浏览器搜索核心指标日聚合表

- 真实表：`iceberg_zjyprc_hadoop.browser.dm_browser_search_core_indicators_2022_1d`
- 粒度：按日聚合
- 周报留存指标的来源；口径为「过去 7 天日均留存，不包含昨日」

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 |
| `browser_search_retain_2` | double | 搜索用户次留 |
| `new_browser_search_retain_2` | double | 搜索新用户次留 |
| `browser_search_retain_7` | double | 搜索用户 7 留 |
| `new_browser_search_retain_7` | double | 搜索新用户 7 留 |
| `browser_search_retain_30` | double | 搜索用户 30 留 |
| `new_browser_search_retain_30` | double | 搜索新用户 30 留 |

**承载指标**：`weekly_report_search_retention`

---

## 3. 底表 / 宽表（dwd 埋点）— 中间表覆盖不到时回退

### 3.1 `search_event` — 浏览器打点事件表

- 真实表：`iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
- 粒度：单次事件行为（每次搜索一行）
- 状态：`partial_aligned`（基于 events.yaml 和实测验证补全关键字段，2026-05-19）

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 YYYYMMDD |
| `distinct_id` | string | **设备唯一标识（顶层列），所有 UV 去重统一用此字段** |
| `event_name` | string | 事件名（`app_open` / `search_security` / `search_resultpage_module_click` 等） |
| `properties[searchengine_name]` | string | 搜索引擎名称（baidu / 360 / douyin） |
| `properties[search_source]` | string | 搜索来源（19 种值） |
| `properties[search_enter_way]` | string | 进入搜索方式（8 种值） |
| `properties[search_way]` | string | 搜索方式（9 种值） |
| `properties[from_page]` | string | 上级页面（browser / search_result） |
| `properties[page_type]` | string | 页面类型（novel / djy_content / game） |
| `properties[query]` | string | 搜索词 |
| `properties[searchid]` | string | 搜索唯一 ID |
| `properties[device_id]` | string | 设备 ID（properties 内）；**UV 去重请用顶层列 `distinct_id`** |

**UV 标准**：`distinct_id`（顶层列，访问方式 = column）。已在 `app_open` / `search_security` 上验证。

**承载指标**：`browser_dau`、`total_search_pv`、`search_pv`、`search_penetration`、`avg_search_per_user`、`ctr`、`click_uv`、`top_query_concentration`、`long_tail_query_ratio`、`search_post_retention`

### 3.2 `search_event_global` — 全搜端内打点事件表

- 真实表：`iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418`
- 粒度：单次事件行为
- **建议**：主动搜索类指标优先用 `dm_search_pv_uv` 聚合表，而非直查本表

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | int | 日期分区 YYYYMMDD |
| `distinct_id` | string | 设备唯一标识（顶层列） |
| `event_name` | string | 事件名（`search` 等） |
| `properties[search_source]` | string | 搜索来源（search_button / sug_word / search_keyboard / search_history / search_engine） |

**承载指标**：`active_search_pv`

---

## 4. 占位表（pending_alignment）— 暂不可用

以下三张表 YAML 中标记为占位名，未对齐真实表，**生成 SQL 前必须先与数据团队确认**：

| Key | 占位名 | 用途 |
|-----|-------|------|
| `search_result` | `ods_search_result_di` | 搜索结果曝光与点击表（CTR / click_uv） |
| `user_profile` | `dim_user_profile` | 用户画像维表（拆解 user_segment / device 维度） |
| `user_active` | `ods_user_active_di` | 用户日活跃表（留存计算依赖） |

如果用户请求的指标只能由这些占位表承载，按 SKILL.md 的范围约束流程：
1. 提示用户「搜索业务该指标当前未对齐真实表」
2. 引导联系开发者 **gongyunhe** 补充表对齐

---

## 5. 字段使用注意

1. **日期分区**：搜索业务所有已对齐表的 `date` 字段都是 `INT YYYYMMDD`，过滤写法 `date = 20260520` 或 `date >= 20260514 AND date < 20260521`。
2. **UV 去重**：`search_event` / `search_event_global` 使用 **顶层列 `distinct_id`**，**不要**用 `properties[device_id]`。
3. **聚合表汇总**：`dm_search_pv_uv` 必须加 `search_engine = 'ALL'` 才能拿到全量。
4. **意图过滤**：`ads_search_intent*` 系列表查询时过滤掉 `'未匹配内容意图'` / `'未匹配领域意图'` 这类特殊值。
