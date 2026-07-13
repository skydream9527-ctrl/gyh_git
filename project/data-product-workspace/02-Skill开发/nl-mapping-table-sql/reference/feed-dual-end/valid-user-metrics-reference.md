# 信息流双端 - 有效用户 DAU / VV / 时长 SQL 口径

> **业务域**：信息流双端 = 浏览器信息流（BF）+ 内容中心（CC）
> **数据层级**：底表/宽表（dwm/dwd 层）
> **适用场景**：双端信息流有效用户的 DAU、VV、时长，含 BF 端自建 vs 火山对比。
> **概念基础**：先读 [`concept.md`](concept.md) 了解双端定义与口径差异。

> [!IMPORTANT]
> 1. **日期整型**：`date = 20260628` / `date BETWEEN 20260601 AND 20260628`，不要加引号（避免分区裁剪失效）。
> 2. **双端有效用户口径不一致**：BF 用 `is_vliad_user_new` / 旧版曝光消费判定，CC 用 `item_position>=4 OR ad_position>4` 的曝光消费判定；双端合计 = 两端各自按本端口径算出后直接加总（不去重，见 concept.md）。
> 3. **时长单位**：BF 端 `dura` / `consum_dura` 单位视底表而定（djy 宽表为秒级，无需除 60000）；CC 端 `feed_dura` / `consum_dura` 单位为毫秒，输出分钟需 `/60000`。
> 4. **小说/短故事消费时长内联处理**：BF 端消费**时长**必须按 `read_source` / `last_read_source` 内联处理，不可直接用 `consum_dura`；消费 **VV 直接用 `consum_cnt_v2` 字段，无需内联**。

---

## 一、BF 端（浏览器信息流）有效用户指标

> **数据源**：`iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di_copy`（都江堰专用宽表，含预计算 `exp_group`）
> **实验分组**：`exp_group IN ('36%自建组','36%火山组')`（如需反转组再加 `'自建反转组','火山反转组'`）

### 公共 CTE（BF 端所有有效用户指标共用）

```sql
-- t_base：按 user × 行为维度聚合原始字段
WITH t_base AS (
    SELECT
        date,
        did,
        exp_group,
        page,
        feed_channel,
        is_vliad_user_new,
        item_type,
        read_source,
        last_read_source,
        SUM(expose_pv)      AS expose_cnt,
        SUM(consum_cnt_v2)  AS consum_cnt_v2,
        SUM(dura)           AS dura,         -- 列表页时长
        SUM(consum_dura)    AS consum_dura   -- 消费时长
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di_copy
    WHERE date = ${date}
      AND exp_group IN ('36%自建组','36%火山组')
    GROUP BY 1,2,3,4,5,6,7,8,9
),
-- t_zijian_base：判定有效用户 + 计算列表页时长 + 处理后消费时长
t_zijian_base AS (
    SELECT
        date,
        exp_group,
        did,
        CASE
            WHEN date < 20260306 AND (expose_cnt > 0 OR consum_cnt_v2 > 0) THEN 1   -- 旧口径：有曝光或消费
            WHEN date >= 20260306 AND is_vliad_user_new = '是' THEN 1               -- 新口径：滑动埋点全量后用标识字段
            ELSE 0
        END AS is_feed_active_new,
        -- 列表页时长：双频道（热点/推荐）+ 列表页
        SUM(CASE WHEN feed_channel IN ('热点','推荐') AND page = '列表页' THEN dura ELSE 0 END) AS list_dura,
        -- 处理后消费时长：小说/短故事按 read_source 内联（首访 + 续读），其余直接计
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('小说','短故事')
            OR (item_type = '小说' AND (read_source IN ('rec','topnews')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
            OR (item_type = '短故事' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
            , consum_dura, 0)) AS consum_dura,
        -- 消费 VV：直接用 consum_cnt_v2 字段，无需内联处理
        SUM(consum_cnt_v2) AS consum_cnt_v2
    FROM t_base
    GROUP BY 1,2,3,4
    HAVING is_feed_active_new = 1   -- 仅保留有效用户
)
```

> 下文各指标 SQL 均以上述 `t_base` + `t_zijian_base` 为前缀，省略重复，仅给出最终 SELECT。

### BF-001: 有效用户 DAU（自建 vs 火山）

> 有效用户在自建组 / 火山组的去重 did 数。

```sql
-- 接 t_base, t_zijian_base
SELECT
    date,
    COUNT(DISTINCT IF(exp_group = '36%自建组', did, NULL)) AS zj_feed_valid_dau,   -- 自建信息流有效DAU
    COUNT(DISTINCT IF(exp_group = '36%火山组', did, NULL)) AS hs_feed_valid_dau    -- 火山信息流有效DAU
FROM t_zijian_base
GROUP BY date
;
```

### BF-002: 有效用户 VV（自建 vs 火山）

> 有效用户的消费 VV，直接用 `consum_cnt_v2` 字段（无需小说/短故事内联处理）。

```sql
-- 接 t_base, t_zijian_base
SELECT
    date,
    SUM(IF(exp_group = '36%自建组', consum_cnt_v2, 0)) AS zj_feed_valid_vv,   -- 自建信息流有效VV
    SUM(IF(exp_group = '36%火山组', consum_cnt_v2, 0)) AS hs_feed_valid_vv    -- 火山信息流有效VV
FROM t_zijian_base
GROUP BY date
;
```

### BF-003: 有效用户时长（自建 vs 火山）

> 有效用户的列表页时长 + 处理后消费时长。

```sql
-- 接 t_base, t_zijian_base
SELECT
    date,
    SUM(IF(exp_group = '36%自建组', list_dura + consum_dura, 0)) AS zj_feed_valid_dura,   -- 自建信息流有效时长
    SUM(IF(exp_group = '36%火山组', list_dura + consum_dura, 0)) AS hs_feed_valid_dura    -- 火山信息流有效时长
FROM t_zijian_base
GROUP BY date
;
```

### BF-004: 有效用户人均时长 + 时长达火山比（组合指标）

> 一次查询拿到自建人均有效时长、自建有效时长达火山比。

```sql
-- 接 t_base, t_zijian_base
SELECT
    date,
    -- 自建信息流有效人均时长（分钟）
    zj_feed_valid_dura / zj_feed_valid_dau AS per_feed_valid_dura,
    -- 自建信息流有效时长达火山
    zj_feed_valid_dura / hs_feed_valid_dura AS dhs_feed_valid_dura
FROM (
    SELECT
        date,
        SUM(IF(exp_group = '36%自建组', list_dura + consum_dura, 0)) AS zj_feed_valid_dura,
        COUNT(DISTINCT IF(exp_group = '36%自建组', did, NULL))        AS zj_feed_valid_dau,
        SUM(IF(exp_group = '36%火山组', list_dura + consum_dura, 0)) AS hs_feed_valid_dura
    FROM t_zijian_base
    GROUP BY 1
) a
;
```

> **多日查询**：把 `WHERE date = ${date}` 改为 `WHERE date BETWEEN ${start} AND ${end}`，外层 `GROUP BY date` 即可按日返回；如需多日合计，外层去掉 `date` 分组。

---

## 二、CC 端（内容中心）有效用户指标

> **数据源**：`iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di`
> **有效用户判定**：有列表页曝光（`item_position>=4 OR ad_position>4` 的 `ad_expose_cnt+expos_cnt`）或消费（`consum_cnt>0`）
> **时长单位**：`feed_dura` / `consum_dura` 为毫秒，输出分钟需 `/60000`

### CC-001: 有效用户 DAU

> 有列表页曝光或消费行为的用户数。

```sql
WITH a AS (
    SELECT
        date,
        did,
        SUM(CASE WHEN (item_position >= 4 OR ad_position > 4) THEN ad_expose_cnt + expos_cnt END) AS expos_cnt,
        SUM(consum_cnt) AS consum_cnt_v2
    FROM iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
    WHERE date BETWEEN ${start} AND ${end}
      AND is_dau_2024 = 1
      AND is_top = 0
    GROUP BY date, did
)
SELECT
    a.date,
    COUNT(DISTINCT a.did) AS uv    -- 内容中心信息流有效用户DAU
FROM a
WHERE a.consum_cnt_v2 > 0 OR a.expos_cnt > 0
GROUP BY a.date
;
```

### CC-002: 有效用户 VV

> 有效用户的总消费次数（`consum_cnt`）。

```sql
WITH s1 AS (
    SELECT
        date,
        did,
        SUM(consum_cnt) AS vv,
        SUM(CASE WHEN (item_position >= 4 OR ad_position > 4) THEN ad_expose_cnt + expos_cnt END) AS expos_cnt,
        SUM(feed_dura) / 60000   AS feed_dura_min,  -- 信息流时长（分钟）
        SUM(consum_dura) / 60000 AS consum_dura     -- 消费时长（分钟）
    FROM iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
    WHERE date BETWEEN ${start} AND ${end}
      AND is_dau_2024 = 1
      AND is_top = 0
      AND COALESCE(ad_expose_cnt, 0) + COALESCE(expos_cnt, 0) + COALESCE(consum_cnt, 0)
        + COALESCE(feed_dura, 0) + COALESCE(consum_dura, 0) + COALESCE(click_cnt, 0) > 0
    GROUP BY date, did
)
SELECT
    date,
    SUM(IF(vv + expos_cnt > 0, vv, 0)) AS valid_feed_vv   -- 内容中心信息流有效用户VV
FROM s1
GROUP BY date
;
```

### CC-003: 有效用户时长（总 / 人均 / 活跃 UV）

> 有效用户的信息流时长（`feed_dura`），一次查询拿到人均有效时长、活跃 UV、总有效时长。**注意：CC 端有效时长 = 信息流时长 `feed_dura`，不含消费时长**（与 BF 端口径不同，BF 端含列表页+消费时长）。

```sql
WITH s1 AS (
    SELECT
        date,
        did,
        SUM(consum_cnt) AS vv,
        SUM(CASE WHEN (item_position >= 4 OR ad_position > 4) THEN ad_expose_cnt + expos_cnt END) AS expos_cnt,
        SUM(feed_dura) / 60000   AS feed_dura_min,  -- 信息流时长（分钟）
        SUM(consum_dura) / 60000 AS consum_dura     -- 消费时长（分钟，本指标不使用，保留供其他指标复用 CTE）
    FROM iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
    WHERE date BETWEEN ${start} AND ${end}
      AND is_dau_2024 = 1
      AND is_top = 0
      AND COALESCE(ad_expose_cnt, 0) + COALESCE(expos_cnt, 0) + COALESCE(consum_cnt, 0)
        + COALESCE(feed_dura, 0) + COALESCE(consum_dura, 0) + COALESCE(click_cnt, 0) > 0
    GROUP BY date, did
)
SELECT
    date,
    SUM(IF(vv + expos_cnt > 0, feed_dura_min, 0)) / COUNT(DISTINCT IF(vv + expos_cnt > 0, did, NULL)) AS per_valid_feed_dura,  -- 人均有效时长（分钟）
    COUNT(DISTINCT IF(vv + expos_cnt > 0, did, NULL)) AS active_uv,                                                              -- 活跃UV（=有效用户DAU）
    SUM(IF(vv + expos_cnt > 0, feed_dura_min, 0)) AS valid_feed_dura                                                              -- 总有效时长（分钟）
FROM s1
GROUP BY date
;
```

> **CC-001 与 CC-003 的 active_uv 一致**：两者有效用户判定口径相同（`consum_cnt_v2>0 OR expos_cnt>0` 等价于 `vv+expos_cnt>0`），可互相印证。

---

## 三、双端合计（DAU / VV / 时长，两端分别算后直接加总）

> **合计规则**：DAU / VV / 时长均**两端各自按本端口径算出，然后直接加总**（不去重）。人均有效时长 = 双端总有效时长加总 / 双端有效 DAU 加总。
> ⚠️ **加总为不去重口径**（BF did 与 CC did 可能重叠）。如需去重合计，需同时取两表 did 做 UNION 后再 COUNT DISTINCT，性能开销大，通常按业务接受不去重。

```sql
-- ============ BF 端 ============
WITH t_base AS (
    SELECT
        date, did, exp_group, page, feed_channel, is_vliad_user_new, item_type, read_source, last_read_source,
        SUM(expose_pv)     AS expose_cnt,
        SUM(consum_cnt_v2) AS consum_cnt_v2,
        SUM(dura)          AS dura,         -- 列表页时长
        SUM(consum_dura)   AS consum_dura   -- 消费时长
    FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di_copy
    WHERE date = ${date}
      AND exp_group IN ('36%自建组','36%火山组')
    GROUP BY 1,2,3,4,5,6,7,8,9
),
t_zijian_base AS (
    SELECT
        date, exp_group, did,
        CASE
            WHEN date < 20260306 AND (expose_cnt>0 OR consum_cnt_v2>0) THEN 1
            WHEN date >= 20260306 AND is_vliad_user_new='是' THEN 1
            ELSE 0
        END AS is_feed_active_new,
        -- 列表页时长（双频道+列表页）
        SUM(CASE WHEN feed_channel IN ('热点','推荐') AND page = '列表页' THEN dura ELSE 0 END) AS list_dura,
        -- 处理后消费时长（小说/短故事按 read_source 内联）
        SUM(IF(
            COALESCE(item_type,'') NOT IN ('小说','短故事')
            OR (item_type = '小说' AND (read_source IN ('rec','topnews')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
            OR (item_type = '短故事' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
            , consum_dura, 0)) AS consum_dura,
        -- 消费 VV：直接用 consum_cnt_v2 字段，无需内联处理
        SUM(consum_cnt_v2) AS consum_cnt_v2
    FROM t_base
    GROUP BY 1,2,3
    HAVING is_feed_active_new = 1   -- 仅保留有效用户
),
bf_metrics AS (
    SELECT
        date,
        COUNT(DISTINCT did)                          AS bf_valid_dau,     -- BF 有效用户 DAU
        SUM(consum_cnt_v2)                           AS bf_valid_vv,      -- BF 有效用户 VV
        SUM(list_dura + consum_dura)                 AS bf_valid_dura     -- BF 有效用户时长（列表页+处理后消费）
    FROM t_zijian_base
    GROUP BY date
),
-- ============ CC 端 ============
cc_s1 AS (
    SELECT
        date, did,
        SUM(consum_cnt) AS vv,
        SUM(CASE WHEN (item_position>=4 OR ad_position>4) THEN ad_expose_cnt + expos_cnt END) AS expos_cnt,
        SUM(feed_dura) / 60000   AS feed_dura_min,  -- 信息流时长（分钟；CC 有效时长 = 此项）
        SUM(consum_dura) / 60000 AS consum_dura     -- 消费时长（分钟，CC 有效时长不含）
    FROM iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di
    WHERE date = ${date}
      AND is_dau_2024 = 1
      AND is_top = 0
      AND COALESCE(ad_expose_cnt, 0) + COALESCE(expos_cnt, 0) + COALESCE(consum_cnt, 0)
        + COALESCE(feed_dura, 0) + COALESCE(consum_dura, 0) + COALESCE(click_cnt, 0) > 0
    GROUP BY date, did
),
cc_metrics AS (
    SELECT
        date,
        COUNT(DISTINCT IF(vv + expos_cnt > 0, did, NULL))                            AS cc_valid_dau,     -- CC 有效用户 DAU
        SUM(IF(vv + expos_cnt > 0, vv, 0))                                          AS cc_valid_vv,      -- CC 有效用户 VV
        SUM(IF(vv + expos_cnt > 0, feed_dura_min, 0))                               AS cc_valid_dura     -- CC 有效用户时长（信息流时长）
    FROM cc_s1
    GROUP BY date
)
-- ============ 双端合计（直接加总，不去重） ============
SELECT
    COALESCE(bf_metrics.date, cc_metrics.date) AS date,
    bf_metrics.bf_valid_dau,
    cc_metrics.cc_valid_dau,
    COALESCE(bf_metrics.bf_valid_dau, 0) + COALESCE(cc_metrics.cc_valid_dau, 0) AS dual_end_valid_dau_sum,   -- 双端有效DAU加总
    bf_metrics.bf_valid_vv,
    cc_metrics.cc_valid_vv,
    COALESCE(bf_metrics.bf_valid_vv, 0) + COALESCE(cc_metrics.cc_valid_vv, 0) AS dual_end_valid_vv_sum,       -- 双端有效VV加总
    bf_metrics.bf_valid_dura,
    cc_metrics.cc_valid_dura,
    COALESCE(bf_metrics.bf_valid_dura, 0) + COALESCE(cc_metrics.cc_valid_dura, 0) AS dual_end_valid_dura_sum, -- 双端有效时长加总
    -- 双端人均有效时长 = 双端总有效时长加总 / 双端有效 DAU 加总
    (COALESCE(bf_metrics.bf_valid_dura, 0) + COALESCE(cc_metrics.cc_valid_dura, 0))
        / NULLIF(COALESCE(bf_metrics.bf_valid_dau, 0) + COALESCE(cc_metrics.cc_valid_dau, 0), 0) AS dual_end_per_valid_dura
FROM bf_metrics
FULL OUTER JOIN cc_metrics ON bf_metrics.date = cc_metrics.date
ORDER BY date
;
```

> **多日查询**：把两表 `WHERE date = ${date}` 改为 `WHERE date BETWEEN ${start} AND ${end}`，外层按 `date` 分组即可按日返回双端加总结果。

---

## 四、参数说明

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `${date}` | 单日日期（整型，不带引号） | `20260628` |
| `${start}` / `${end}` | 时间窗起止（整型，不带引号） | `20260601` / `20260628` |

---

## 五、注意事项

1. **BF 端口径切换节点 `20260306`**：滑动埋点 `is_feed_sliding` / `is_vliad_user_new` 在该日期全量，跨节点对比需注意口径变更引起的正常波动。
2. **BF 端两张表的选择**：本文件用 `dwm_djy_dau_user_consum_index_di_copy`（含预计算 `exp_group`，自建/火山对比专用）；如不需自建/火山拆分或需更多维度（push/profile），改用 `dwm_browser_event_aggregation_label_di`，见 [`../browser-feed/dujiangyan-metrics-reference.md`](../browser-feed/dujiangyan-metrics-reference.md)。
3. **CC 端 `is_top=0`**：有效用户统计排除置顶内容，与 DAU 口径（`is_dau_2024=1`）叠加使用。
4. **小说/短故事消费内联（BF 端）**：消费 VV / 时长必须按 `read_source` / `last_read_source` 内联处理，直接用 `consum_cnt_v2` / `consum_dura` 会多算非推荐来源的阅读。
5. **双端合计 DAU 不去重**：BF 与 CC 的 did 命名空间可能重叠，加总值会偏高；如需精确去重需 UNION 两端 did。
