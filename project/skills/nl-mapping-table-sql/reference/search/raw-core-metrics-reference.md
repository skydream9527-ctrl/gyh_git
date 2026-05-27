# Search - 核心指标参考

> **数据源（口径权威）**：[`reference/search/data_tables.yaml`](data_tables.yaml)
> **配套表结构**：[`reference/search/table-schema.md`](table-schema.md)
> **数据层级**：搜索业务同时具备中间表（dm/ads）和底表/宽表（dwd），优先使用中间表。

## 概述

本文档基于搜索业务数据团队维护的 `data_tables.yaml`（v1.0），列出当前已对齐真实表的核心指标 SQL 模板。

> **范围约束**：仅列出 YAML 中 `status: aligned` 的指标。`pending_alignment` 的占位表（`search_result` / `user_profile` / `user_active`）暂不生成 SQL。

---

## 指标说明

### 1. 主动搜索 PV（active_search_pv）

**指标定义**: 全量主动搜索 PV
**首选数据源**: `iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di`（已内置渠道归属和版本覆盖率，**无需手动除以 0.9**）
**口径要求**: 必须加 `search_engine = 'ALL'` 才能拿到全量汇总

```sql
SELECT
    date,
    active_search_pv,
    bro_active_search_pv,
    qs_active_search_pv,
    nh_active_search_pv
FROM
    iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di
WHERE
    date = ${date-1}
    AND search_engine = 'ALL'
;
```

**回退方案（中间表故障时）**：直接查 `search_event_global`（dwd 418）

```sql
SELECT
    date,
    COUNT(1) AS active_search_pv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000418
WHERE
    date = ${date-1}
    AND event_name = 'search'
GROUP BY 1
;
```

---

### 2. 主动搜索 UV（active_search_uv）

**指标定义**: 全量主动搜索 UV
**数据源**: `iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di`

```sql
SELECT
    date,
    active_search_uv,
    bro_active_search_uv,
    qs_active_search_uv,
    nh_active_search_uv
FROM
    iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di
WHERE
    date = ${date-1}
    AND search_engine = 'ALL'
;
```

---

### 3. AI 搜索 UV（ai_search_uv）

**指标定义**: AI 搜索 UV（全量 / 浏览器 / 全搜分维度）
**数据源**: `iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di`

```sql
SELECT
    date,
    ai_search_uv,
    bro_ai_search_uv,
    qs_ai_search_uv,
    ai_avg_search_uv,
    bro_ai_avg_search_uv,
    qs_ai_avg_search_uv
FROM
    iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di
WHERE
    date = ${date-1}
    AND search_engine = 'ALL'
;
```

---

### 4. 搜索渗透率（search_penetration）

**指标定义**: 搜索 UV / 浏览器 DAU
**数据源**: `dm_search_pv_uv_di`（搜索 UV）+ `dwm_browser_event_aggregation_label_di`（浏览器 DAU）

```sql
SELECT
    s.date,
    s.bro_active_search_uv AS search_uv,
    d.browser_dau,
    s.bro_active_search_uv * 1.0 / d.browser_dau AS search_penetration
FROM (
    SELECT date, bro_active_search_uv
    FROM iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di
    WHERE date = ${date-1} AND search_engine = 'ALL'
) s
JOIN (
    SELECT date, COUNT(DISTINCT did) AS browser_dau
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date = ${date-1} AND is_app_dau_2024 = 1
    GROUP BY 1
) d ON s.date = d.date
;
```

---

### 5. 人均搜索次数（avg_search_per_user）

**指标定义**: 主动搜索 PV / 主动搜索 UV
**数据源**: `iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di`

```sql
SELECT
    date,
    bro_active_search_pv,
    bro_active_search_uv,
    bro_active_search_pv * 1.0 / bro_active_search_uv AS avg_search_per_user
FROM
    iceberg_zjyprc_hadoop.browser.dm_search_pv_uv_di
WHERE
    date = ${date-1}
    AND search_engine = 'ALL'
;
```

---

### 6. 周报搜索留存（weekly_report_search_retention）

**指标定义**: 搜索用户次留 / 7 留 / 30 留（含新用户口径）
**数据源**: `iceberg_zjyprc_hadoop.browser.dm_browser_search_core_indicators_2022_1d`
**口径**: 周报口径 = 过去 7 天日均留存，**不包含昨日**

```sql
SELECT
    date,
    browser_search_retain_2,
    new_browser_search_retain_2,
    browser_search_retain_7,
    new_browser_search_retain_7,
    browser_search_retain_30,
    new_browser_search_retain_30
FROM
    iceberg_zjyprc_hadoop.browser.dm_browser_search_core_indicators_2022_1d
WHERE
    date >= ${date-8}
    AND date < ${date-1}
ORDER BY date
;
```

---

### 7. 热门搜索词（top_search_query）

**指标定义**: 按 query 维度排行 PV / UV
**数据源**: `iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_hot_search_word_dod_metrics_di`

```sql
SELECT
    query,
    SUM(query_pv) AS pv,
    SUM(query_uv) AS uv
FROM
    iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_hot_search_word_dod_metrics_di
WHERE
    date = ${date-1}
    AND intention_name_level_1 NOT IN ('未匹配内容意图', '未匹配领域意图')
GROUP BY 1
ORDER BY pv DESC
LIMIT 100
;
```

---

### 8. 搜索意图分布（query_intent_analysis）

**指标定义**: 一级领域意图的当日 PV / UV / 占比
**数据源**: `iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di`

```sql
SELECT
    date,
    intention_name_level_1,
    SUM(query_pv) AS query_pv,
    SUM(query_uv) AS query_uv,
    SUM(query_pv_ratio) AS query_pv_ratio
FROM
    iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di
WHERE
    date = ${date-1}
    AND intention_name_level_1 NOT IN ('未匹配内容意图', '未匹配领域意图')
GROUP BY 1, 2
ORDER BY query_pv DESC
;
```

---

### 9. 意图日环比（intent_trend）

**指标定义**: 意图分布的日 / 周 / 月环比
**数据源**: `ads_search_intent_dashboard_by_intent_level1_metrics_di`（无内置 dod/wow/mom，需手动跨日对比）

```sql
SELECT
    cur.intention_name_level_1,
    cur.query_pv AS pv_today,
    prev.query_pv AS pv_yesterday,
    (cur.query_pv - prev.query_pv) * 1.0 / prev.query_pv AS dod
FROM (
    SELECT intention_name_level_1, SUM(query_pv) AS query_pv
    FROM iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di
    WHERE date = ${date-1}
      AND intention_name_level_1 NOT IN ('未匹配内容意图', '未匹配领域意图')
    GROUP BY 1
) cur
JOIN (
    SELECT intention_name_level_1, SUM(query_pv) AS query_pv
    FROM iceberg_zjyprc_hadoop.browser.ads_search_intent_dashboard_by_intent_level1_metrics_di
    WHERE date = ${date-2}
      AND intention_name_level_1 NOT IN ('未匹配内容意图', '未匹配领域意图')
    GROUP BY 1
) prev USING (intention_name_level_1)
ORDER BY ABS(dod) DESC
;
```

---

## 指标—表映射索引

| 指标 | 首选表 | 兜底表 |
|------|-------|-------|
| active_search_pv / search_pv / total_search_pv | `dm_search_pv_uv_di` | `dwd_ot_event_di_31000000418` |
| active_search_uv | `dm_search_pv_uv_di` | `dwd_ot_event_di_31000000418` |
| ai_search_uv / ai_avg_search_uv | `dm_search_pv_uv_di` | — |
| search_penetration | `dm_search_pv_uv_di` + `dwm_browser_event_aggregation_label_di` | — |
| avg_search_per_user | `dm_search_pv_uv_di` | `dwd_ot_event_di_31000000442` |
| weekly_report_search_retention | `dm_browser_search_core_indicators_2022_1d` | — |
| top_search_query | `ads_search_intent_dashboard_hot_search_word_dod_metrics_di` | — |
| query_intent_analysis | `ads_search_intent_dashboard_by_intent_level1_metrics_di` | — |
| intent_trend | `ads_search_intent_dashboard_by_intent_level1_metrics_di` | — |
| ctr / click_uv | （`search_result` 占位待对齐） | — |
| search_post_retention | （`user_active` 占位待对齐） | `dwd_ot_event_di_31000000442` + `user_active` |

## 注意事项

1. **日期分区类型**：搜索业务所有已对齐表的 `date` 都是 `INT YYYYMMDD`，**不要写连字符**。
2. **聚合表汇总**：`dm_search_pv_uv_di` 必须加 `search_engine = 'ALL'`，否则只查到分引擎数据。
3. **意图特殊值过滤**：`ads_search_intent*` 系列查询时排除 `'未匹配内容意图'` 和 `'未匹配领域意图'`。
4. **占位表**：`search_result` / `user_profile` / `user_active` 在 YAML 中状态为 `pending_alignment`，请按 SKILL.md 的范围约束流程提示用户。
