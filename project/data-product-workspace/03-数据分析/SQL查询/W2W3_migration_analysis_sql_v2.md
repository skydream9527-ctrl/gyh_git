# W2→W3 L2/L3/L4/L5 用户迁移行为分析 SQL

> 分层标准：周总消费时长（week_dura_min）
> 层级定义：L1_浅消费(<1min) / L2_轻消费(<3min) / L3_中消费(<10min) / L4_深消费(<30min) / L5_重度(<80min) / L6_极重度(<200min) / L7_超重度(≥200min)
> 5月自然周：W1(0504-0510) / W2(0511-0517) / W3(0518-0524) / W4(0525-0531)

---

## 1a. 用户分群（5月4周分层分布）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260504 AND 20260510 THEN 'W1'
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
      WHEN date BETWEEN 20260525 AND 20260531 THEN 'W4'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260504 AND 20260531
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260504 AND 20260510 THEN 'W1'
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
      WHEN date BETWEEN 20260525 AND 20260531 THEN 'W4'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
)

SELECT
  shiyan_group,
  week_label,
  layer,
  COUNT(*) AS user_cnt
FROM user_layer
GROUP BY shiyan_group, week_label, layer
ORDER BY shiyan_group, week_label, layer;
```

---

## 1b. 用户周间层级流向（5月4周相邻周流转矩阵）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260504 AND 20260510 THEN 'W1'
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
      WHEN date BETWEEN 20260525 AND 20260531 THEN 'W4'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260504 AND 20260531
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260504 AND 20260510 THEN 'W1'
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
      WHEN date BETWEEN 20260525 AND 20260531 THEN 'W4'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
),

w1 AS (
  SELECT did, shiyan_group, layer AS from_layer
  FROM user_layer WHERE week_label = 'W1'
),

w2 AS (
  SELECT did, shiyan_group, layer AS from_layer
  FROM user_layer WHERE week_label = 'W2'
),

w3 AS (
  SELECT did, shiyan_group, layer AS from_layer
  FROM user_layer WHERE week_label = 'W3'
),

w4 AS (
  SELECT did, shiyan_group, layer AS from_layer
  FROM user_layer WHERE week_label = 'W4'
),

flow_w1_w2 AS (
  SELECT
    'W1→W2' AS flow_period,
    w1.shiyan_group,
    w1.from_layer,
    w2.from_layer AS to_layer,
    COUNT(*) AS user_cnt
  FROM w1
  JOIN w2 ON w1.did = w2.did AND w1.shiyan_group = w2.shiyan_group
  GROUP BY w1.shiyan_group, w1.from_layer, w2.from_layer
),

flow_w2_w3 AS (
  SELECT
    'W2→W3' AS flow_period,
    w2.shiyan_group,
    w2.from_layer,
    w3.from_layer AS to_layer,
    COUNT(*) AS user_cnt
  FROM w2
  JOIN w3 ON w2.did = w3.did AND w2.shiyan_group = w3.shiyan_group
  GROUP BY w2.shiyan_group, w2.from_layer, w3.from_layer
),

flow_w3_w4 AS (
  SELECT
    'W3→W4' AS flow_period,
    w3.shiyan_group,
    w3.from_layer,
    w4.from_layer AS to_layer,
    COUNT(*) AS user_cnt
  FROM w3
  JOIN w4 ON w3.did = w4.did AND w3.shiyan_group = w4.shiyan_group
  GROUP BY w3.shiyan_group, w3.from_layer, w4.from_layer
)

SELECT * FROM flow_w1_w2
UNION ALL
SELECT * FROM flow_w2_w3
UNION ALL
SELECT * FROM flow_w3_w4
ORDER BY flow_period, shiyan_group, from_layer, to_layer;
```

---

## 2a. 品类TOP3（W2→W3，L2/L3/L4/L5迁移用户，W3消费按消费次数）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260511 AND 20260524
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
),

w2 AS (
  SELECT did, shiyan_group, layer AS w2_layer
  FROM user_layer WHERE week_label = 'W2'
),

w3 AS (
  SELECT did, shiyan_group, layer AS w3_layer
  FROM user_layer WHERE week_label = 'W3'
),

migration AS (
  SELECT
    w2.did,
    w2.shiyan_group,
    w2.w2_layer,
    CASE
      WHEN w2.w2_layer < w3.w3_layer THEN '上迁'
      WHEN w2.w2_layer = w3.w3_layer THEN '平级'
      ELSE '下迁'
    END AS migration_type
  FROM w2
  JOIN w3 ON w2.did = w3.did AND w2.shiyan_group = w3.shiyan_group
  WHERE w2.w2_layer IN ('L2_轻消费','L3_中消费','L4_深消费','L5_重度')
),

consum AS (
  SELECT
    m.shiyan_group,
    m.w2_layer,
    m.migration_type,
    dc.item_category,
    SUM(dc.consum_dura) AS dura_min,
    SUM(dc.consum_pv)   AS consum_pv
  FROM migration m
  JOIN iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di dc
    ON m.did = dc.did AND m.shiyan_group = dc.shiyan_group
  WHERE dc.date BETWEEN 20260518 AND 20260524
    AND dc.page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND dc.feed_channel IN ('推荐','热点')
  GROUP BY m.shiyan_group, m.w2_layer, m.migration_type, dc.item_category
),

ranked AS (
  SELECT
    shiyan_group,
    w2_layer,
    migration_type,
    item_category,
    consum_pv,
    dura_min,
    ROW_NUMBER() OVER (PARTITION BY shiyan_group, w2_layer, migration_type ORDER BY consum_pv DESC) AS rnk
  FROM consum
)

SELECT shiyan_group, w2_layer, migration_type, item_category, consum_pv, dura_min, rnk
FROM ranked
WHERE rnk <= 3
ORDER BY shiyan_group, w2_layer, migration_type, rnk;
```

---

## 2b. 内容类型分布（W2→W3，L2/L3/L4/L5迁移用户，W3消费）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260511 AND 20260524
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
),

w2 AS (
  SELECT did, shiyan_group, layer AS w2_layer
  FROM user_layer WHERE week_label = 'W2'
),

w3 AS (
  SELECT did, shiyan_group, layer AS w3_layer
  FROM user_layer WHERE week_label = 'W3'
),

migration AS (
  SELECT
    w2.did,
    w2.shiyan_group,
    w2.w2_layer,
    CASE
      WHEN w2.w2_layer < w3.w3_layer THEN '上迁'
      WHEN w2.w2_layer = w3.w3_layer THEN '平级'
      ELSE '下迁'
    END AS migration_type
  FROM w2
  JOIN w3 ON w2.did = w3.did AND w2.shiyan_group = w3.shiyan_group
  WHERE w2.w2_layer IN ('L2_轻消费','L3_中消费','L4_深消费','L5_重度')
),

consum AS (
  SELECT
    m.shiyan_group,
    m.w2_layer,
    m.migration_type,
    dc.item_type,
    SUM(dc.consum_dura) AS dura_min,
    SUM(dc.consum_pv)   AS consum_pv
  FROM migration m
  JOIN iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di dc
    ON m.did = dc.did AND m.shiyan_group = dc.shiyan_group
  WHERE dc.date BETWEEN 20260518 AND 20260524
    AND dc.page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND dc.feed_channel IN ('推荐','热点')
  GROUP BY m.shiyan_group, m.w2_layer, m.migration_type, dc.item_type
)

SELECT
  shiyan_group,
  w2_layer,
  migration_type,
  item_type,
  consum_pv,
  dura_min,
  consum_pv * 100.0 / SUM(consum_pv) OVER (PARTITION BY shiyan_group, w2_layer, migration_type) AS pct_consum_pv
FROM consum
ORDER BY shiyan_group, w2_layer, migration_type, consum_pv DESC;
```

---

## 2c. 人均品类数（W2→W3，L2/L3/L4/L5迁移用户，W3消费）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260511 AND 20260524
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
),

w2 AS (
  SELECT did, shiyan_group, layer AS w2_layer
  FROM user_layer WHERE week_label = 'W2'
),

w3 AS (
  SELECT did, shiyan_group, layer AS w3_layer
  FROM user_layer WHERE week_label = 'W3'
),

migration AS (
  SELECT
    w2.did,
    w2.shiyan_group,
    w2.w2_layer,
    CASE
      WHEN w2.w2_layer < w3.w3_layer THEN '上迁'
      WHEN w2.w2_layer = w3.w3_layer THEN '平级'
      ELSE '下迁'
    END AS migration_type
  FROM w2
  JOIN w3 ON w2.did = w3.did AND w2.shiyan_group = w3.shiyan_group
  WHERE w2.w2_layer IN ('L2_轻消费','L3_中消费','L4_深消费','L5_重度')
),

user_category AS (
  SELECT
    m.shiyan_group,
    m.w2_layer,
    m.migration_type,
    m.did,
    COUNT(DISTINCT dc.item_category) AS category_cnt
  FROM migration m
  JOIN iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di dc
    ON m.did = dc.did AND m.shiyan_group = dc.shiyan_group
  WHERE dc.date BETWEEN 20260518 AND 20260524
    AND dc.page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND dc.feed_channel IN ('推荐','热点')
  GROUP BY m.shiyan_group, m.w2_layer, m.migration_type, m.did
)

SELECT
  shiyan_group,
  w2_layer,
  migration_type,
  COUNT(*)            AS user_cnt,
  AVG(category_cnt)   AS avg_category_per_user,
  APPROX_PERCENTILE(category_cnt, 0.5) AS median_category
FROM user_category
GROUP BY shiyan_group, w2_layer, migration_type
ORDER BY shiyan_group, w2_layer, migration_type;
```

---

## 3. 单次消费时长分布（W2→W3，L2/L3/L4/L5迁移用户）

```sql
WITH user_week AS (
  SELECT
    did,
    shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END AS week_label,
    SUM(consum_dura) AS week_dura_min
  FROM iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di
  WHERE date BETWEEN 20260511 AND 20260524
    AND page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND feed_channel IN ('推荐','热点')
  GROUP BY did, shiyan_group,
    CASE
      WHEN date BETWEEN 20260511 AND 20260517 THEN 'W2'
      WHEN date BETWEEN 20260518 AND 20260524 THEN 'W3'
    END
),

user_layer AS (
  SELECT
    did,
    shiyan_group,
    week_label,
    CASE
      WHEN week_dura_min < 1   THEN 'L1_浅消费'
      WHEN week_dura_min < 3   THEN 'L2_轻消费'
      WHEN week_dura_min < 10  THEN 'L3_中消费'
      WHEN week_dura_min < 30  THEN 'L4_深消费'
      WHEN week_dura_min < 80  THEN 'L5_重度'
      WHEN week_dura_min < 200 THEN 'L6_极重度'
      ELSE 'L7_超重度'
    END AS layer
  FROM user_week
  WHERE week_dura_min > 0
),

w2 AS (
  SELECT did, shiyan_group, layer AS w2_layer
  FROM user_layer WHERE week_label = 'W2'
),

w3 AS (
  SELECT did, shiyan_group, layer AS w3_layer
  FROM user_layer WHERE week_label = 'W3'
),

migration AS (
  SELECT
    w2.did,
    w2.shiyan_group,
    w2.w2_layer,
    CASE
      WHEN w2.w2_layer < w3.w3_layer THEN '上迁'
      WHEN w2.w2_layer = w3.w3_layer THEN '平级'
      ELSE '下迁'
    END AS migration_type
  FROM w2
  JOIN w3 ON w2.did = w3.did AND w2.shiyan_group = w3.shiyan_group
  WHERE w2.w2_layer IN ('L2_轻消费','L3_中消费','L4_深消费','L5_重度')
),

user_dura AS (
  SELECT
    m.shiyan_group,
    m.w2_layer,
    m.migration_type,
    m.did,
    SUM(dc.consum_dura) AS total_dura_min,
    SUM(dc.consum_pv)   AS total_consum_pv
  FROM migration m
  JOIN iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di dc
    ON m.did = dc.did AND m.shiyan_group = dc.shiyan_group
  WHERE dc.date BETWEEN 20260518 AND 20260524
    AND dc.page IN ('图文详情页','短小融合沉浸页','小视频沉浸页','短剧流页面')
    AND dc.feed_channel IN ('推荐','热点')
  GROUP BY m.shiyan_group, m.w2_layer, m.migration_type, m.did
  HAVING total_consum_pv > 0
)

SELECT
  shiyan_group,
  w2_layer,
  migration_type,
  COUNT(*)                                         AS user_cnt,
  AVG(total_dura_min * 60.0 / total_consum_pv)     AS avg_dura_per_consum_sec,
  APPROX_PERCENTILE(total_dura_min * 60.0 / total_consum_pv, 0.25) AS p25_sec,
  APPROX_PERCENTILE(total_dura_min * 60.0 / total_consum_pv, 0.50) AS p50_sec,
  APPROX_PERCENTILE(total_dura_min * 60.0 / total_consum_pv, 0.75) AS p75_sec,
  APPROX_PERCENTILE(total_dura_min * 60.0 / total_consum_pv, 0.90) AS p90_sec
FROM user_dura
GROUP BY shiyan_group, w2_layer, migration_type
ORDER BY shiyan_group, w2_layer, migration_type;
```
