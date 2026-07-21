---
name: data-monitoring-reference
description: 数据监控百宝箱 — 内容生态核心指标 SQL 库（覆盖都江堰、信息流、深度用户、广告流水四大模块）。Agent 通过引用本文件查询全量指标，唯一可变参数为日期 `<date>`（YYYYMMDD 格式）。
source: https://mi.feishu.cn/wiki/TLnPwmRiyiVBLekqhR9caoUtnjh?sheet=dViMG9
sheet_token: BGJSspzbkhP3XPtY6Ijc1C2Kn8d
sheet_id: dViMG9
last_synced: 2026-06-02
---

# 数据监控百宝箱 — SQL Reference

## 使用说明

- **唯一变量**：所有 SQL 中的日期参数统一为 `<date>` 占位符，调用时替换为 `YYYYMMDD` 字符串（如 `20260601`）。
- **执行引擎**：通过 `kyuubi-cli` 执行（标签 paimon/iceberg/doris 表分别走对应引擎），返回单日聚合结果。
- **指标分组**：本目录共 33 条指标，分 4 大模块（都江堰、信息流、深度用户、广告流水）；其中 7 条暂无 SQL（标记为 `null`，Owner 待补）。
- **占位符替换示例**（Python）：
  ```python
  sql = TEMPLATE.replace("<date>", "20260601")
  ```

## 指标索引

| # | 模块 | 指标名称 | SQL 状态 |
|---|------|---------|----------|
| 1 | 都江堰 | 有效活跃用户人均时长（min） | ✅ |
| 2 | 都江堰 | 有效活跃用户 DAU（w） | ✅ |
| 3 | 都江堰 | ARPU 达火山（%） | ⚠️ 缺 SQL |
| 4 | 信息流 | 双端 DAU | ✅ |
| 5 | 信息流 | 浏览器 DAU（万） | ✅ |
| 6 | 信息流 | 浏览器主启动 DAU（万） | ✅ |
| 7 | 信息流 | 浏览器 PUSH 启动 DAU（万） | ✅ |
| 8 | 信息流 | 浏览器第三方调起 DAU | ✅ |
| 9 | 信息流 | 浏览器活跃用户次日留存率 | ✅ |
| 10 | 信息流 | 浏览器 DNU（万） | ✅ |
| 11 | 信息流 | 浏览器新用户次日留存率 | ✅ |
| 12 | 信息流 | 浏览器信息流 DAU（万） | ✅ |
| 13 | 信息流 | 浏览器信息流消费 UV（万） | ⚠️ 缺 SQL |
| 14 | 信息流 | 内容中心信息流 DAU（万） | ✅ |
| 15 | 信息流 | 内容中心信息流消费 UV | ✅ |
| 16 | 信息流 | 双端信息流有效用户 7 日留存 | ⚠️ 缺 SQL |
| 17 | 信息流 | 双端信息流有效用户总时长（min） | ⚠️ 缺 SQL |
| 18 | 信息流 | 自建信息流有效用户人均时长（min） | ⚠️ 缺 SQL |
| 19 | 信息流 | 浏览器人均时长（min） | ⚠️ 缺 SQL |
| 20 | 信息流 | 信息流人均时长（min） | ⚠️ 缺 SQL |
| 21 | 信息流 | 浏览器信息流人均时长（min） | ⚠️ 缺 SQL |
| 22 | 信息流 | 内容中心信息流人均时长（min） | ✅ |
| 23 | 信息流 | 浏览器信息流人均 VV | ⚠️ 缺 SQL |
| 24 | 信息流 | 浏览器信息流 IPU | ⚠️ 缺 SQL |
| 25 | 信息流 | 内容中心信息流人均 VV | ⚠️ 缺 SQL |
| 26 | 信息流 | 内容中心信息流 IPU | ⚠️ 缺 SQL |
| 27 | 深度用户 | 深度用户 DAU（浏览器+NH） | ✅ |
| 28 | 深度用户 | 浏览器深度用户 DAU | ✅ |
| 29 | 深度用户 | NH 深度用户 DAU | ✅ |
| 30 | 广告流水 | 浏览器 dARPU（元） | ✅ |
| 31 | 广告流水 | 浏览器广告总流水（万） | ✅ |
| 32 | 广告流水 | 内容中心 dARPU | ✅ |
| 33 | 广告流水 | 内容中心广告总流水（万） | ✅ |

---

## 一、都江堰

### M01 · 有效活跃用户人均时长（min）

```sql
SELECT
    date AS date_level_day,
    (
      SUM(
        IF(
          page = '列表页'
          AND feed_channel IN ('热点', '推荐'),
          dura,
          0
        )
      ) + SUM(
        IF(
          COALESCE(item_type, '') NOT IN ('小说', '短故事')
          OR (item_type = '短故事' AND (read_source IN ('rec', 'topnews', 'feed_main_info', 'unknown')
            OR (read_source IN ('feed_continue_view_card', 'browser_history')
                       AND last_read_source IN ('rec', 'topnews', 'feed_main_info', 'unknown'))))
          OR (item_type = '小说'
              AND (read_source IN ('rec', 'topnews')
                   OR (read_source IN ('feed_continue_view_card', 'browser_history')
                       AND last_read_source IN ('rec', 'topnews')))),
          consum_dura,
          0.0
        )
      )
    ) / COUNT(DISTINCT did) AS valid_consume_dura_per_user
FROM paimon_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
WHERE date = <date>
    AND (exp_group IN ('36%火山组', '36%自建组'))
    AND (exp_group IN ('自建组', '36%自建组') OR observation_group IN ('自建组', '4%自建反转组', '2%自建反转组', '2%自建纯净组', '自建shuffle组', '自建其他组'))
    AND is_valid_user_new = '是'
GROUP BY date
```

### M02 · 有效活跃用户 DAU（w）

```sql
SELECT
    date AS date_level_day,
    COUNT(DISTINCT did) AS valid_action_scale_1d
FROM paimon_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
WHERE date = <date>
    AND (exp_group IN ('36%火山组', '36%自建组'))
    AND (exp_group IN ('自建组', '36%自建组') OR observation_group IN ('自建组', '4%自建反转组', '2%自建反转组', '2%自建纯净组', '自建shuffle组', '自建其他组'))
    AND is_valid_user_new = '是'
GROUP BY date
```

### M03 · ARPU 达火山（%）

> ⚠️ 暂无 SQL（待补）

---

## 二、信息流

### M04 · 双端 DAU

```sql
SELECT  date,
        sum(dau) AS dau
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor IN ('小米浏览器', '内容中心')
GROUP BY date
```

### M05 · 浏览器 DAU（万）

```sql
SELECT  date, sum(dau) dau
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor = '小米浏览器'
GROUP BY date
```

### M06 · 浏览器主启动 DAU（万）

```sql
SELECT  date,
        sum(icon_dau) icon_dau
FROM    doris_zjyprc_hadoop.browser.ads_browser_core_targets_d_ccq
WHERE   date = <date>
        AND user_type = '大盘用户'
GROUP BY date
```

### M07 · 浏览器 PUSH 启动 DAU（万）

```sql
SELECT  date,
        sum(push_dau) push_dau
FROM    doris_zjyprc_hadoop.browser.ads_browser_core_addtargets_d_doris
WHERE   date = <date>
        AND user_type = '大盘用户'
GROUP BY date
```

### M08 · 浏览器第三方调起 DAU

```sql
SELECT  date,
        sum(three_dau) three_dau
FROM    doris_zjyprc_hadoop.browser.ads_browser_core_addtargets_d_doris
WHERE   date = <date>
        AND user_type = '大盘用户'
GROUP BY date
```

### M09 · 浏览器活跃用户次日留存率

```sql
SELECT  date, sum(active_retain1) active_retain1
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor = '小米浏览器'
GROUP BY date
```

### M10 · 浏览器 DNU（万）

```sql
SELECT  date, sum(new_dau) new_dau
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor = '小米浏览器'
GROUP BY date
```

### M11 · 浏览器新用户次日留存率

```sql
SELECT  date, sum(new_retain1) new_retain1
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor = '小米浏览器'
GROUP BY date
```

### M12 · 浏览器信息流 DAU（万）

```sql
SELECT  date,
        count(distinct did) uv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = <date>
        AND is_dau_feed_dapan_2024 = 1
GROUP BY date
```

### M13 · 浏览器信息流消费 UV（万）

> ⚠️ 暂无 SQL（待补）

### M14 · 内容中心信息流 DAU（万）

```sql
SELECT  date, sum(dau) dau
FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
WHERE   date = <date>
        AND competitor = '内容中心'
GROUP BY date
```

### M15 · 内容中心信息流消费 UV

```sql
SELECT  date,
        count(distinct did) uv
FROM    iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
WHERE   date = <date>
        AND is_dau_2024 = 1
        AND consum_cnt > 0
GROUP BY date
```

### M16 · 双端信息流有效用户 7 日留存

> ⚠️ 暂无 SQL（待补）

### M17 · 双端信息流有效用户总时长（min）

> ⚠️ 暂无 SQL（待补）

### M18 · 自建信息流有效用户人均时长（min）

> ⚠️ 暂无 SQL（待补）

### M19 · 浏览器人均时长（min）

> ⚠️ 暂无 SQL（待补）

### M20 · 信息流人均时长（min）

> ⚠️ 暂无 SQL（待补）

### M21 · 浏览器信息流人均时长（min）

> ⚠️ 暂无 SQL（待补）

### M22 · 内容中心信息流人均时长（min）

```sql
SELECT  date,
        sum(metric_value) metric_value
FROM    iceberg_zjyprc_hadoop.browser.ads_mcid_financial_consume_metric_di
WHERE   date = <date>
        AND metric_name = '内容中心人均时长(分钟)'
GROUP BY date
```

### M23 · 浏览器信息流人均 VV

> ⚠️ 暂无 SQL（待补）

### M24 · 浏览器信息流 IPU

> ⚠️ 暂无 SQL（待补）

### M25 · 内容中心信息流人均 VV

> ⚠️ 暂无 SQL（待补）

### M26 · 内容中心信息流 IPU

> ⚠️ 暂无 SQL（待补）

---

## 三、深度用户

### M27 · 深度用户 DAU（浏览器 + NH）

```sql
SELECT  date,
        sum(dau_uv) dau_uv
FROM
    (
        SELECT  date,
                sum(dau_uv) dau_uv
        FROM    doris_c3prc_xiaomi.browser.ads_browser_deep_user_indicators
        WHERE   date = <date>
                AND user_type = '深度用户'
        GROUP BY date
        UNION ALL
        SELECT  date,
                sum(dau_uv) dau_uv
        FROM    doris_c3prc_xiaomi.newhome.ads_newhome_deep_user_indicators
        WHERE   date = <date>
                AND user_type = '深度用户'
        GROUP BY date
    ) t
GROUP BY date
```

### M28 · 浏览器深度用户 DAU

```sql
SELECT  date,
        sum(dau_uv) dau_uv
FROM    doris_c3prc_xiaomi.browser.ads_browser_deep_user_indicators
WHERE   date = <date>
        AND user_type = '深度用户'
GROUP BY date
```

### M29 · NH 深度用户 DAU

```sql
SELECT  date,
        sum(dau_uv) dau_uv
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_deep_user_indicators
WHERE   date = <date>
        AND user_type = '深度用户'
GROUP BY date
```

---

## 四、广告流水

### M30 · 浏览器 dARPU（元）

```sql
SELECT  t1.date,
        t1.metric_value / t2.dau dARPU
FROM
    (
        SELECT  date,
                sum(metric_value) metric_value
        FROM    iceberg_zjyprc_hadoop.browser.ads_micd_financial_daily_report_di
        WHERE   date = <date>
                AND metric_name = '浏览器(除小说)流水'
        GROUP BY date
    ) t1
    JOIN (
        SELECT  date,
                sum(dau) dau
        FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
        WHERE   date = <date>
                AND competitor = '小米浏览器'
        GROUP BY date
    ) t2 ON t1.date = t2.date
```

### M31 · 浏览器广告总流水（万）

```sql
SELECT  date,
        sum(metric_value) metric_value
FROM    iceberg_zjyprc_hadoop.browser.ads_micd_financial_daily_report_di
WHERE   date = <date>
        AND metric_name = '浏览器(除小说)流水'
GROUP BY date
```

### M32 · 内容中心 dARPU

```sql
SELECT  t1.date,
        t1.metric_value / t2.dau dARPU
FROM
    (
        SELECT  date,
                sum(metric_value) metric_value
        FROM    iceberg_zjyprc_hadoop.browser.ads_micd_financial_daily_report_di
        WHERE   date = <date>
                AND metric_name = '内容中心流水'
        GROUP BY date
    ) t1
    JOIN (
        SELECT  date,
                sum(dau) dau
        FROM    iceberg_zjyprc_hadoop.browser.ads_miui_app_competitor_di
        WHERE   date = <date>
                AND competitor = '内容中心'
        GROUP BY date
    ) t2 ON t1.date = t2.date
```

### M33 · 内容中心广告总流水（万）

```sql
SELECT  date,
        sum(metric_value) metric_value
FROM    iceberg_zjyprc_hadoop.browser.ads_micd_financial_daily_report_di
WHERE   date = <date>
        AND metric_name = '内容中心流水'
GROUP BY date
```

---

## Agent 调用约定

```yaml
input:
  date: "YYYYMMDD"        # 唯一参数，例如 "20260601"
  metric_ids: ["M01", "M27", "M30"]   # 可选，不传则跑全量已实现指标

procedure:
  1. 加载本 reference，按 metric_ids 取出对应 SQL（跳过 ⚠️ 标记）。
  2. 将每条 SQL 中的 <date> 全部替换为 input.date。
  3. 通过 kyuubi-cli 执行（按表前缀路由：paimon_*/iceberg_*/doris_*）。
  4. 汇总结果为统一表头：{ metric_id, metric_name, module, date, value }。
```

## 维护

- 数据源：飞书表格 [内容生态 SQL 指标白皮书 · 数据监控百宝箱](https://mi.feishu.cn/wiki/TLnPwmRiyiVBLekqhR9caoUtnjh?sheet=dViMG9)
- 同步命令：`feishu sheet read BGJSspzbkhP3XPtY6Ijc1C2Kn8d "dViMG9!A1:D200"`
- 7 条 ⚠️ 缺失 SQL 待飞书源表更新后回填。
