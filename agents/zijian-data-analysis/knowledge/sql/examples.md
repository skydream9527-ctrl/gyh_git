# 标准 SQL 示例

> 三条经过验证的示例，覆盖最常见的取数模式。所有示例都先把 `model.sql` 整段塞进 `WITH djy_model AS (...)`，外层只做 GROUP BY + 聚合。

---

## 示例 1 · 按实验组统计消费时长

**用户原话**：「查看都江堰不同实验组的消费时长」

**取数思路**：
- 维度：`exp_group_6`（流量分组，6 个组合并）
- 指标：`consum_dura`（aggregator=sum）

```sql
WITH djy_model AS (
    -- 此处粘贴 sql/model.sql 完整 SELECT 字段列表
    SELECT
        date,
        djy_rec_expid,
        exp_group,
        observation_group,
        case
            when exp_group in ('36%自建组') then '36%自建组'
            when exp_group in ('36%火山组') then '36%火山组'
            when observation_group in ('2%自建反转组') then '自建反转组'
            when observation_group in ('2%火山反转组') then '火山反转组'
            when observation_group in ('2%自建纯净组') then '自建纯净组'
            when observation_group in ('2%火山纯净组') then '火山纯净组'
        end as exp_group_6,
        -- ... model.sql 其余字段
        if (
            feed_channel in ('热点', '推荐', 'profile_djy','profile','push')
            or (item_type in('短故事') and (read_source in ('rec', 'topnews','feed_main_info','unknown') or (
                read_source in ('feed_continue_view_card', 'browser_history')
                and last_read_source in ('rec', 'topnews','feed_main_info','unknown'))))
            or (item_type in('小说') and (read_source in ('rec', 'topnews') or read_source in ('feed_continue_view_card', 'browser_history')
                and last_read_source in ('rec', 'topnews')))
            ,consum_dura,0.0
        ) as consum_dura
        -- ... 其余字段省略，实际拼时必须粘完整
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date BETWEEN 20260101 AND 20260107
)
SELECT
    exp_group_6,
    SUM(consum_dura) AS total_consum_dura
FROM djy_model
WHERE exp_group_6 IS NOT NULL    -- 排除非 6 组用户
GROUP BY exp_group_6
ORDER BY total_consum_dura DESC
```

**关键点**：
- `exp_group_6` 在 model.sql 中定义，外层直接 GROUP BY
- `WHERE exp_group_6 IS NOT NULL` 排除既不在 36% 组也不在反转/纯净组的用户

---

## 示例 2 · 按内容分类统计曝光与消费

**用户原话**：「分析都江堰不同内容分类的曝光和消费情况」

**取数思路**：
- 维度：`item_category`（内容一级分类）
- 指标：`expose_pv`（aggregator=sum）+ `consum_pv`（aggregator=sum）+ `完播完读率`（fieldType=4 派生）

```sql
WITH djy_model AS (
    -- 此处粘贴 sql/model.sql 完整 SELECT 字段列表
    SELECT
        date,
        item_category,
        case when feed_channel in ('热点', '推荐', 'profile_djy','profile','push') then expose_pv end as expose_pv,
        if (
            feed_channel in ('热点', '推荐', 'profile_djy','profile','push')
            or (item_type in('短故事') and ...)
            or (item_type in('小说') and ...)
            ,consum_pv,0.0
        ) as consum_pv,
        all_consum_pv,    -- 完播完读 PV
        -- ... 其余字段省略
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date BETWEEN 20260101 AND 20260107
)
SELECT
    item_category,
    SUM(expose_pv)        AS total_expose_pv,
    SUM(consum_pv)        AS total_consum_pv,
    SUM(all_consum_pv) * 1.0 / NULLIF(SUM(consum_pv), 0) AS finish_read_rate   -- 完播完读率（派生）
FROM djy_model
WHERE item_category IS NOT NULL
GROUP BY item_category
ORDER BY total_consum_pv DESC
LIMIT 30
```

**关键点**：
- `完播完读率` 是 fieldType=4 派生指标，外层用 `SUM(all_consum_pv) / SUM(consum_pv)` 计算
- 派生分母套 `NULLIF(..., 0)` 防止除零
- `LIMIT 30` 防止小流量长尾内容污染

---

## 示例 3 · 信息流 DAU（distinct-count 指标）

**用户原话**：「查询都江堰最近一周每天的信息流 DAU」

**取数思路**：
- 维度：`date`（按天）
- 指标：`信息流DAU`（indexes.csv 中 name = `case when expose_pv>0 or consum_pv>0 then did end`，aggregator=distinct-count）

```sql
WITH djy_model AS (
    -- 此处粘贴 sql/model.sql 完整 SELECT 字段列表
    SELECT
        date,
        did,
        case when feed_channel in ('热点', '推荐', 'profile_djy','profile','push') then expose_pv end as expose_pv,
        if (
            feed_channel in ('热点', '推荐', 'profile_djy','profile','push')
            or (item_type in('短故事') and ...)
            or (item_type in('小说') and ...)
            ,consum_pv,0.0
        ) as consum_pv
        -- ... 其余字段省略
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date BETWEEN 20260113 AND 20260119   -- 「最近一周」需要根据 today 替换为具体日期
)
SELECT
    date,
    COUNT(DISTINCT CASE WHEN expose_pv > 0 OR consum_pv > 0 THEN did END) AS dau,
    COUNT(DISTINCT CASE WHEN consum_pv > 0 THEN did END)                  AS 消费UV
FROM djy_model
GROUP BY date
ORDER BY date
```

**关键点**：
- 「最近一周」「过去 N 天」等相对时间，**必须**根据当前日期算出具体 `YYYYMMDD` 数字再传进 WHERE，不能让 SQL 引擎自己算
- `信息流DAU` 是 distinct-count 指标，外层 `COUNT(DISTINCT CASE WHEN ... THEN did END)`
- 同一查询里加几个 distinct-count 指标几乎免费（一次扫表多算几列），用户问 DAU 顺手附上消费 UV / 完读 UV

---

## 复合示例 · 实验组 × 体裁交叉对比

**用户原话**：「自建组 vs 火山组，看不同体裁的消费时长差异」

**取数思路**：P1 对比框架，双维度 GROUP BY + 同时输出基础和派生指标。

```sql
WITH djy_model AS (
    -- model.sql 完整正文
    SELECT ... FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date BETWEEN 20260101 AND 20260107
)
SELECT
    exp_group_6,
    item_type,
    COUNT(DISTINCT CASE WHEN expose_pv>0 OR consum_pv>0 THEN did END) AS dau,
    SUM(consum_dura)                                                  AS total_consum_dura,
    SUM(consum_dura) * 1.0
      / NULLIF(COUNT(DISTINCT CASE WHEN consum_pv>0 THEN did END), 0) AS 人均消费时长,
    SUM(all_consum_pv) * 1.0 / NULLIF(SUM(consum_pv), 0)              AS 完播完读率
FROM djy_model
WHERE exp_group_6 IN ('36%自建组','36%火山组')   -- 只对比 36% 大组
  AND item_type IS NOT NULL
GROUP BY exp_group_6, item_type
ORDER BY exp_group_6, total_consum_dura DESC
```

**关键点**：
- 两个对比组的流量盘子相同（都是 36%），可以直接对比绝对值；如果对比 36% vs 2% 反转，必须用人均指标或占比
- 同一行同时给 sum / distinct-count / 派生比率，省一次查询
- `WHERE exp_group_6 IN (...)` 用 fieldType=1 的简单字段过滤，不会踩 fieldType=5 的还原陷阱
