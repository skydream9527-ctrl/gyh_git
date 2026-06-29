# 作者扶持数据口径规范

> 目的：统一"作者扶持"相关分析的数据口径，用于周度效果评估和日度消费监控。
> 适用范围：都江堰信息流—自建分发链路下的作者扶持体系。
> 版本：v1.0（2026-04-27 定稿）

---

## 1. 业务背景

作者扶持分三类，作者之间**互斥**（一个作者同一时刻只属于一类）。归类优先级：**常态化 > 一阶冷启 > 二阶冷启**。

| 类型 | 定义 | 数据侧判定 |
|---|---|---|
| **常态化扶持** | 长期重点扶持的作者（一般是 MCN 头部、行业作者） | 出现在 `dwm_djy_author_boost_df` 当日分区中 |
| **一阶冷启扶持** | 新作者首次入池后的 7 天判定期，验证作者内容是否值得继续扶持 | `flag='assist'` + 不在 boost_df + `first_date` 与当日有重叠（窗口 [first_date, first_date+6]） |
| **二阶冷启扶持** | 一阶**成功**后继续追加 1 周的流量扶持 | `flag='assist'` + 不在 boost_df + `first_date` 在当日之前 ≥7 天（一阶窗口已结束但仍在 assist 名单） |

### 1.1 一阶冷启的 7 天判定

作者首次入池日记为 `first_date`（永不回写）。一阶窗口 = `[first_date, first_date + 6]`，共 7 天。期间每日做判定：

- **成功**：7 天内任一天被判"优质"（曝光≥60 且时长回报率≥0.95，或曝光≥1000）
- **失败**：连续 3 天被判"低质"（曝光≥60 且时长回报率<0.95）
- **扶持中**：入池未满 7 天
- **其他-内容不足**：跑满 7 天，7 日新增内容量 <3（作者自身不活跃）
- **其他-欠曝光**：跑满 7 天，7 日新增内容量 ≥3 但未获得足够曝光（系统分发不足）

### 1.2 flag 字段含义

`djy_browser_cold_assist_author_infos_di` 表的 `flag` 字段只有两个值：

- `flag='assist'`：冷启扶持通道（一阶 + 二阶追加都走这里）
- `flag='great'`：常态化补充通道（100% 与 `dwm_djy_author_boost_df` 重合，归入常态化）

**区分一阶 / 二阶的唯一依据不是 flag，而是 `first_date` 与当日的距离。**

---

## 2. 数据源

### 2.1 扶持名单表 ── `iceberg_zjyprc_hadoop.browser.djy_browser_cold_assist_author_infos_di`

- **Owner**：算法侧（每日产出）
- **分区**：`date + flag`，类型均为 `VARCHAR`（date 格式 `'YYYYMMDD'`，如 `'20260426'`）
- **关键字段**：
  - `xm_author_id`：小米作者 ID
  - `author_type`：业务侧已做分类映射（不是原始 cp_name）
  - `flag`：'assist' / 'great'
  - `assist_date` / `assist_days`(=7)

### 2.2 冷启状态快照表 ── `iceberg_zjyprc_hadoop.newhome.dws_author_cold_start_status_di`

- **Owner**：产品/运营侧
- **分区**：`date`（`BIGINT`，格式 `20260426`）
- **含义**：每日作者扶持状态快照，最新分区 = 最新终态
- **关键字段**：
  - `xm_author_id`
  - `author_type`
  - `first_date`（`BIGINT`，`YYYYMMDD` 格式，永不回写）
  - `author_status`（'成功' / '失败' / '扶持中' / '其他-内容不足' / '其他-欠曝光'）

### 2.3 常态化扶持作者表 ── `iceberg_zjyprc_hadoop.newhome.dwm_djy_author_boost_df`

- **Owner**：产品/运营侧（人工配置，上游 `dim_djy_cold_author_boost_cms_df`）
- **分区**：`date`（`BIGINT`）
- **语义**：**全表都是常态化扶持作者**，**无 flag / priority 等二级过滤字段**
- **关键字段**：`xm_author_id` / `author_name` / `author_type` / `comment` / `priority` / `expose_page` / `first_date`

### 2.4 消费宽表 ── `iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di`

- **分区**：`date`（`BIGINT`）+ `shiyan_group`（VARCHAR，值域：'自建组' / '火山组'）
- **粒度**：`did × item × page`
- **关键字段**：
  - `item_author_id`：内容发布者的 xm_author_id（与扶持表的 xm_author_id 同域可直接 JOIN）
  - `expose_pv`：曝光 PV
  - `consum_pv`：VV（播放次数）
  - `consum_dura`：消费时长，**单位 = 秒**（⚠️ 不是毫秒，与 label 表不同），转分钟 `/60`

---

## 3. 过滤规则（必遵守）

1. **排除 vivo**：`author_type NOT LIKE '%vivo%' AND author_type NOT LIKE '%VIVO%'`
2. **类型合并**：`MCN-贝壳 → MCN-beike`（同一实体历史命名差异）
3. **扶持名单只取一阶通道**：`flag = 'assist'`
4. **常态化优先级最高**：若作者同时在 boost_df 和 assist 名单，归常态化（LEFT JOIN boost + WHERE boost IS NULL 排除）
5. **跨月 first_date 判定必须用日期函数**：`date_parse(CAST(first_date AS VARCHAR), '%Y%m%d') BETWEEN DATE 'YYYY-MM-DD' AND DATE 'YYYY-MM-DD'`（整数 BETWEEN 会错匹如 20260332 等非法值）

---

## 4. 场景一：周度扶持效果分析

### 4.1 时间口径

- **扶持参与期**：上上周四 ~ 上周三（7 天）
- **最终观测日**：扶持结束后第 7 天（即本周三）
- **对比基线**：上一周批次（同口径）做周环比

### 4.2 作者归类（在本批次 `[S, E]` 下）

| 子表 | 定义 | first_date 判定 |
|---|---|---|
| **表A 一阶新增** | 本批次首次入池 | `first_date ∈ [S, E]` |
| **表B 一阶顺延** | 上一批次尚未结束一阶窗口的作者 | `first_date ∈ [S-6, S-1]` |
| **表C 一阶全部** | A + B | A ∪ B |

> ⚠️ `first_date < S-6` 的作者属"二阶追加"，**必须排除**，否则会污染一阶口径（常见误区）。

### 4.3 指标定义

| 指标 | 公式 |
|---|---|
| total_cnt | 参与扶持的去重作者数 |
| valid_cnt（有效扶持量） | `author_status IN ('成功','失败')` 的去重作者数（跑到终态的才算有效验证） |
| success_cnt | `author_status = '成功'` |
| fail_cnt | `author_status = '失败'` |
| success_rate | `success_cnt / (success_cnt + fail_cnt)` |
| content_short | `author_status = '其他-内容不足'` |
| expose_short | `author_status = '其他-欠曝光'` |
| 周环比(pp) | 本周 success_rate − 上周 success_rate，单位百分点 |

### 4.4 维度

按 `author_type` 拆，固定 8 类顺序：

```
供应商-站外高互动
供应商-站外高粉
供应商-站外垂类优质
供应商-火山高曝
作者体系优质新作者
MCN-dihui
MCN-guoying
MCN-beike  (含 MCN-贝壳)
```

每表附一行"总计"。

### 4.5 SQL 模板（参数化）

```sql
-- 参数：S=批次起, E=批次终, S6=S-6, S1=S-1, OBS=观测日
-- 本周示例: S='2026-04-09', E='2026-04-15', S6='2026-04-03', S1='2026-04-08', OBS=20260421
WITH assist AS (
    SELECT DISTINCT xm_author_id
    FROM iceberg_zjyprc_hadoop.browser.djy_browser_cold_assist_author_infos_di
    WHERE date BETWEEN '20260409' AND '20260415'
      AND flag = 'assist'
),
boost AS (
    SELECT DISTINCT xm_author_id
    FROM iceberg_zjyprc_hadoop.newhome.dwm_djy_author_boost_df
    WHERE date = 20260421
),
status AS (
    SELECT xm_author_id, author_type, first_date, author_status
    FROM iceberg_zjyprc_hadoop.newhome.dws_author_cold_start_status_di
    WHERE date = 20260421
),
base AS (
    SELECT
        s.xm_author_id,
        CASE WHEN s.author_type = 'MCN-贝壳' THEN 'MCN-beike' ELSE s.author_type END AS author_type,
        CASE
            WHEN date_parse(CAST(s.first_date AS VARCHAR), '%Y%m%d')
                 BETWEEN DATE '2026-04-09' AND DATE '2026-04-15' THEN 'new'
            WHEN date_parse(CAST(s.first_date AS VARCHAR), '%Y%m%d')
                 BETWEEN DATE '2026-04-03' AND DATE '2026-04-08' THEN 'rollover'
        END AS batch_type,
        s.author_status
    FROM assist a
    JOIN status s ON s.xm_author_id = a.xm_author_id
    LEFT JOIN boost b ON b.xm_author_id = a.xm_author_id
    WHERE b.xm_author_id IS NULL
      AND s.author_type NOT LIKE '%vivo%'
      AND s.author_type NOT LIKE '%VIVO%'
)
SELECT
    batch_type,
    author_type,
    COUNT(DISTINCT xm_author_id)                                                                    AS total_cnt,
    COUNT(DISTINCT IF(author_status IN ('成功','失败'), xm_author_id, NULL))                        AS valid_cnt,
    COUNT(DISTINCT IF(author_status = '成功', xm_author_id, NULL))                                  AS success_cnt,
    COUNT(DISTINCT IF(author_status = '失败', xm_author_id, NULL))                                  AS fail_cnt,
    ROUND(COUNT(DISTINCT IF(author_status = '成功', xm_author_id, NULL)) * 1.0 /
          NULLIF(COUNT(DISTINCT IF(author_status IN ('成功','失败'), xm_author_id, NULL)), 0), 4)   AS success_rate,
    COUNT(DISTINCT IF(author_status = '其他-内容不足', xm_author_id, NULL))                         AS content_short,
    COUNT(DISTINCT IF(author_status = '其他-欠曝光',   xm_author_id, NULL))                         AS expose_short
FROM (
    SELECT batch_type, author_type, author_status, xm_author_id FROM base WHERE batch_type IS NOT NULL
    UNION ALL
    SELECT 'all' AS batch_type, author_type, author_status, xm_author_id FROM base WHERE batch_type IS NOT NULL
)
GROUP BY batch_type, author_type
ORDER BY batch_type, total_cnt DESC;
```

`batch_type` 输出值：`'new'` = 表A / `'rollover'` = 表B / `'all'` = 表C。

---

## 5. 场景二：日度消费监控

### 5.1 时间口径

单日快照，取昨天分区（或最近可用分区）。

### 5.2 作者归类（在当日 OBS 下）

| 类型 | 归类条件 |
|---|---|
| 常态化扶持 | `dwm_djy_author_boost_df` date=OBS 的全部作者 |
| 一阶冷启 | `infos_di` date=OBS & flag='assist' & 不在 boost_df & 不含 vivo & `first_date ∈ [OBS-6, OBS]` |
| 二阶冷启 | `infos_di` date=OBS & flag='assist' & 不在 boost_df & 不含 vivo & `first_date < OBS-6` |

优先级：常态化 > 一阶 > 二阶（互斥归类）。

### 5.3 指标

| 指标 | 说明 |
|---|---|
| author_cnt | 该类作者总数 |
| active_author_cnt | 当日有曝光的作者数 |
| active_rate | active_author_cnt / author_cnt |
| expose_pv | 曝光 PV 合计 |
| vv | 播放次数合计 |
| consum_dura_min | 消费时长（分钟）= `SUM(consum_dura) / 60`（秒→分） |
| expose_pv_per_active | 活跃作者人均曝光 |
| vv_per_active | 活跃作者人均 VV |
| dura_min_per_active | 活跃作者人均消费时长（分钟） |

### 5.4 SQL 模板（参数化）

```sql
-- 参数：OBS=观测日（YYYYMMDD 整数），S6=OBS-6
-- 示例：OBS=20260426, S6=20260420
WITH
boost AS (
    SELECT DISTINCT xm_author_id
    FROM iceberg_zjyprc_hadoop.newhome.dwm_djy_author_boost_df
    WHERE date = 20260426
),
assist_candidates AS (
    SELECT DISTINCT a.xm_author_id
    FROM iceberg_zjyprc_hadoop.browser.djy_browser_cold_assist_author_infos_di a
    LEFT JOIN boost b ON a.xm_author_id = b.xm_author_id
    WHERE a.date = '20260426'
      AND a.flag = 'assist'
      AND a.author_type != 'UGC-vivo'
      AND b.xm_author_id IS NULL
),
status AS (
    SELECT xm_author_id, first_date
    FROM iceberg_zjyprc_hadoop.newhome.dws_author_cold_start_status_di
    WHERE date = 20260426
),
author_groups AS (
    SELECT xm_author_id, '1_常态化扶持' AS author_group FROM boost
    UNION ALL
    SELECT a.xm_author_id, '2_一阶冷启'
    FROM assist_candidates a JOIN status s ON a.xm_author_id = s.xm_author_id
    WHERE s.first_date BETWEEN 20260420 AND 20260426
    UNION ALL
    SELECT a.xm_author_id, '3_二阶冷启'
    FROM assist_candidates a JOIN status s ON a.xm_author_id = s.xm_author_id
    WHERE s.first_date < 20260420
),
author_consum AS (
    SELECT
        item_author_id,
        SUM(expose_pv)   AS expose_pv,
        SUM(consum_pv)   AS vv,
        SUM(consum_dura) AS consum_dura_sec
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date = 20260426
      AND item_author_id IS NOT NULL
      AND item_author_id != ''
    GROUP BY item_author_id
)
SELECT
    g.author_group,
    COUNT(DISTINCT g.xm_author_id)                                                              AS author_cnt,
    COUNT(DISTINCT CASE WHEN c.item_author_id IS NOT NULL THEN g.xm_author_id END)              AS active_author_cnt,
    ROUND(COUNT(DISTINCT CASE WHEN c.item_author_id IS NOT NULL THEN g.xm_author_id END) * 1.0
          / COUNT(DISTINCT g.xm_author_id), 4)                                                  AS active_rate,
    COALESCE(SUM(c.expose_pv), 0)                                                               AS expose_pv,
    COALESCE(SUM(c.vv), 0)                                                                      AS vv,
    ROUND(COALESCE(SUM(c.consum_dura_sec), 0) / 60.0, 2)                                        AS consum_dura_min,
    ROUND(COALESCE(SUM(c.expose_pv), 0) * 1.0
          / NULLIF(COUNT(DISTINCT CASE WHEN c.item_author_id IS NOT NULL THEN g.xm_author_id END), 0), 2) AS expose_pv_per_active,
    ROUND(COALESCE(SUM(c.vv), 0) * 1.0
          / NULLIF(COUNT(DISTINCT CASE WHEN c.item_author_id IS NOT NULL THEN g.xm_author_id END), 0), 2) AS vv_per_active,
    ROUND(COALESCE(SUM(c.consum_dura_sec), 0) / 60.0
          / NULLIF(COUNT(DISTINCT CASE WHEN c.item_author_id IS NOT NULL THEN g.xm_author_id END), 0), 2) AS dura_min_per_active
FROM author_groups g
LEFT JOIN author_consum c ON g.xm_author_id = c.item_author_id
GROUP BY g.author_group
ORDER BY g.author_group;
```

---

## 6. 关键坑位与陷阱

| # | 坑位 | 正确做法 |
|---|---|---|
| 1 | `infos_di.date` 是 VARCHAR，`dws/boost.date` 是 BIGINT | WHERE 分别用 `'20260426'` 和 `20260426`，别写错引号 |
| 2 | `consum_dura` 单位是**秒**，不是毫秒 | 转分钟用 `/60`（label 表才是 `/60000`） |
| 3 | 跨月 first_date 范围用整数 BETWEEN 会错匹非法日期 | 必须 `date_parse + BETWEEN DATE 'YYYY-MM-DD'` |
| 4 | 一阶"顺延"若误写成 `first_date < S`，会把二阶追加作者算进来 | 严格 `first_date ∈ [S-6, S-1]`，只保留一阶窗口与本批次有重叠的 |
| 5 | `flag='great'` 与 `boost_df` 100% 重合 | 归常态化，不是独立"二阶通道"；二阶只走 flag='assist' |
| 6 | `author_type` 字段已是业务分类，不是原始 cp_name | 直接用，不要再 JOIN item→cp 映射 |
| 7 | 消费宽表按 `did×item×page` 聚合，作者维度需 SUM 到 `item_author_id` | JOIN 作者用 `item_author_id = xm_author_id` |
| 8 | `shiyan_group` 值域只有 '自建组'/'火山组'，不加过滤=两组都算 | 想看单一分发链路加 WHERE；看全量则不加 |
| 9 | **池表 `djy_cold_start_content_pool_selected` 必须按 date 对齐 JOIN**——若 `pool_dedup GROUP BY item_id`（丢 date）+ `JOIN ON item_id`（不匹配日期），会把 item 所有日期的消费都算作"冷启消费"，cold_pv 被放大 2-3 倍 | `pool_dedup` 必须 `GROUP BY item_id, date`；JOIN 条件必须 `ON c.item_id = p.item_id AND c.date = p.date` |
| 10 | **Spark/Hive 的 `INSERT OVERWRITE` 必须放在 WITH 的所有 CTE 之后、最终 SELECT 之前**——写成 `INSERT ... WITH ...` 会报 `mismatched input 'WITH'` | 正确顺序：`WITH cte1 AS (...), cte2 AS (...)` → `INSERT OVERWRITE TABLE xxx PARTITION (...)` → `SELECT ... FROM ...` |
| 11 | **Presto vs Spark SQL 函数差异**——在 datum 临时查询里用 Presto 能跑，但数据工场作业默认 Spark 引擎，复制过去就报错 | `CAST(x AS VARCHAR)` → `CAST(x AS STRING)`；`date_parse(s,'%Y%m%d')` → `to_date(s,'yyyyMMdd')`；`date_add('day',-6,d)` → `date_sub(d, 6)`；`DATE(s,'yyyyMMdd')` → `to_date(s,'yyyyMMdd')` |

---

## 7. 对账要点

1. 三类作者数总和 = 当日 `boost_df` 并集 `infos_di(assist, 非vivo, 非boost)` 的作者数
2. 一阶新增 + 一阶顺延 = 一阶全部（first_date 一作者一值，无重复）
3. `flag='great'` 作者数 ≈ `boost_df` 作者数（两者来自同一上游逻辑）
4. 消费宽表全量聚合（不过滤作者）= 当日大盘 VV/曝光/时长（可用于自检口径是否跑全）

---

## 8. 版本与变更

- v1.0（2026-04-27）：首次定稿，对齐一阶窗口严格判定 + 三类作者互斥 + consum_dura 单位为秒
- v1.1（2026-05-06）：新增坑位 #9——池表 JOIN 必须按 (item_id, date) 双维度对齐，跨日单维度 dedup 会放大 cold_pv 2-3 倍（实际事故：14 天 SQL 跑出 13.8M PV vs 正确值 3.1M PV）
- v1.2（2026-05-06）：新增坑位 #10——Spark/Hive `INSERT OVERWRITE` 必须放在 WITH CTE 之后、SELECT 之前，否则报 `mismatched input 'WITH'`
