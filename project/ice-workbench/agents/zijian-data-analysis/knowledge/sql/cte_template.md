# CTE 拼接模式（强制规则）

> 都江堰自建信息流的所有 SQL 都必须按这个模式拼。这不是建议，是约束。

---

## 为什么必须用 CTE

`model.sql`（同目录 `sql/model.sql`，约 220 行）已经把所有复杂的业务逻辑封装好了：

- 实验组归并（`exp_group_6` 把 36% / 自建反转 / 自建纯净 / 火山反转 / 火山纯净 / 火山组 6 个分组合并）
- 消费时长口径（`consum_dura` 已经按"自建发的短故事/小说阅读"逻辑过滤过）
- 曝光/点击的频道限定（已限定在 热点 / 推荐 / profile_djy / profile / push）
- 视频时长分桶（`video_length_level` / `video_length_level_v2`）
- 有效用户判定（`is_feed_active_new` / `is_feed_active_new_no_push`，跨 20260306 切口径）
- 图文字数分桶（`图文字数区间` 维度）
- 短故事/小说的自建口径专用字段（`shortstory_read_cnt_v2` / `novel_read_cnt_v2`）

**好处**：
- 外层只做"维度分组 + 指标聚合"，简单到不会出错
- model.sql 升级时（业务逻辑改变），所有外层查询零改动
- 跨任务/跨同事的 SQL 口径自动一致

**禁止**：在外层重写 model.sql 已有的业务逻辑（CASE WHEN / IF）。要新增逻辑就改 model.sql。

---

## 模板（固定结构）

```sql
WITH djy_model AS (
    -- 把 sql/model.sql 整段（SELECT … FROM … WHERE date BETWEEN <start> AND <end>）原样粘贴到这里
    SELECT
        date, djy_rec_expid, exp_group, observation_group,
        case when exp_group in ('36%自建组') then '36%自建组' ... end as exp_group_6,
        ...   -- model.sql 完整字段列表
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
    WHERE date BETWEEN <开始日期> AND <结束日期>   -- 必须显式时间分区
)
SELECT
    <维度字段>,        -- 来自 metrics/dimensions.csv，直接引用 model 中已定义的字段名
    <聚合指标>         -- 来自 metrics/indexes.csv，按 aggregator 列定义聚合方式
FROM djy_model
GROUP BY <维度字段>
ORDER BY <可选>
```

---

## 关键规则

### 1. 时间分区必传

`date` 是分区列，格式 `YYYYMMDD` **整数**（不是字符串）。

| 写法 | 说明 |
|---|---|
| `WHERE date BETWEEN 20260101 AND 20260107` | 区间，闭区间 |
| `WHERE date = 20260107` | 单日 |
| `WHERE date >= 20260101 AND date < 20260108` | 半开区间 |

**禁止**：跑全表（无 WHERE 或 date 条件），kyuubi 会被 reject。

### 2. 维度直接引用，不要在外层 CASE WHEN

dimensions.csv 中：
- `fieldType=1` 的维度 → model.sql 已经原样 SELECT 出来，外层直接 `GROUP BY <name>`
- `fieldType=5` 的维度 → 模型中已经 CASE WHEN 计算好（如 `exp_group_6`、`图文字数区间`），外层也是 `GROUP BY <alias>`

如果要新增维度（model.sql 里没有的），**改 model.sql** 加一段 CASE WHEN，**不要在外层加**。

### 3. fieldType=5 维度做过滤的陷阱

把 fieldType=5 维度（如「实验大组=自建组」）当作 WHERE 条件时，**必须从 dimensions.csv 复制完整 CASE WHEN 表达式**还原所有命中值。

```sql
-- 正确：完整还原 dimensions.csv 中"实验大组=自建组"的 CASE WHEN
WHERE exp_group IN ('自建组', '36%自建组')
   OR observation_group IN ('自建组', '4%自建反转组', '2%自建反转组', '2%自建纯净组')

-- 错误：只取部分值
WHERE exp_group IN ('36%自建组')
   OR observation_group IN ('2%自建反转组', '2%自建纯净组')
```

### 4. 派生指标（fieldType=4）外层运算

indexes.csv 中 `aggregator` 列为空、`fieldType=4` 的指标都是派生指标，本身没法直接聚合，必须用基础指标在外层做除法/加法/拼接：

```sql
-- 完播完读率
SUM(all_consum_pv) * 1.0 / NULLIF(SUM(consum_pv), 0) AS 完播完读率

-- 人均消费时长
SUM(consum_dura) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN consum_pv>0 THEN did END), 0) AS 人均消费时长

-- 总有效时长（加法派生）
SUM(IF(is_feed_active_new=1 AND page='列表页' AND feed_channel IN('热点','推荐'), dura, 0))
  + SUM(IF(is_feed_active_new=1, consum_dura, 0)) AS 总有效时长
```

**避免除零**：分母处都套 `NULLIF(..., 0)`，否则 presto 会抛 division by zero。

### 5. 聚合方式必须对齐 indexes.csv

| `aggregator` | 外层写法 | 例 |
|---|---|---|
| `sum` | `SUM(<name>)` | `SUM(consum_dura)` |
| `distinct-count` | `COUNT(DISTINCT <name 表达式>)` | `COUNT(DISTINCT CASE WHEN consum_pv>0 THEN did END)` |
| `avg` | `AVG(<name>)` | `AVG(avg_video_play_percent)` |
| `max` | `MAX(<name>)` | `MAX(comment_cnt)` |
| 空（fieldType=4） | 派生公式 | 见上一节 |

`distinct-count` 类指标的 `name` 字段在 indexes.csv 里就是完整的 CASE WHEN 表达式，**外层直接用 COUNT(DISTINCT ...) 包起来即可**：

```sql
-- 信息流 DAU （indexes.csv 中 name = "case when expose_pv>0 or consum_pv>0 then did end"，aggregator=distinct-count）
COUNT(DISTINCT CASE WHEN expose_pv > 0 OR consum_pv > 0 THEN did END) AS dau
```

---

## 常见错误模式

| 错误 | 说明 | 修复 |
|---|---|---|
| 外层重复 `case when feed_channel in ('热点','推荐') then ...` | model.sql 已经处理过，重复 | 删掉外层 CASE WHEN，直接 SUM model 中已定义字段 |
| `WHERE date >= '20260101'`（带引号） | date 是 int，字符串比较结果不可预期 | 写成 `date >= 20260101` |
| 派生指标当成基础指标 SUM 了 | 比如 `SUM(完播完读率)` | 用基础指标重写：`SUM(all_consum_pv)/SUM(consum_pv)` |
| 自建/火山曝光直接对比 | 流量盘子不同 | 改用占比：`djy_expose_pv/total_djy_expose_pv` |
| 缺时间分区 | 全表扫 | 加 `WHERE date BETWEEN ... AND ...` |
| `consum_dura` 期望直接是消费时长 | model.sql 里它是有限定的（限定在自建口径下） | 知道这点就好，不需要改写；要看大盘消费时长用 `dura` |
