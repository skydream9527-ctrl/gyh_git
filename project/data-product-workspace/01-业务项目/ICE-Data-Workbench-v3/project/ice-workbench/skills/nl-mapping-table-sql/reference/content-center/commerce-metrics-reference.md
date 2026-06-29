# Content Center - Commerce Metrics Reference

## Source Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| ads_newhome_finance_core_indicators_di | 财收核心指标表 | doris_c3prc_xiaomi.newhome |

---

## Atomic Metrics (不筛选维度)

### CM-ADV-001: 财收(元)

```sql
SELECT  date,
        SUM(revenue) AS revenue
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-002: 流水(元)

```sql
SELECT  date,
        SUM(gmv) AS gmv
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-003: 计费曝光

```sql
SELECT  date,
        SUM(expose_cnt) AS expose_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-004: 计费点击

```sql
SELECT  date,
        SUM(click_cnt) AS click_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-005: 广告下载量

```sql
SELECT  date,
        SUM(download_cnt) AS download_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-006: 广告请求次数

```sql
SELECT  date,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

### CM-ADV-007: 广告填充次数

```sql
SELECT  date,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date
```

---

## Dimension-Filtered Metrics (按维度筛选)

### CM-ADV-DIM-001: 财收 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(revenue) AS revenue
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY revenue DESC
```

### CM-ADV-DIM-002: 财收 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(revenue) AS revenue
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY revenue DESC
LIMIT 50
```

### CM-ADV-DIM-003: 流水 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(gmv) AS gmv
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY gmv DESC
```

### CM-ADV-DIM-004: 流水 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(gmv) AS gmv
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY gmv DESC
LIMIT 50
```

### CM-ADV-DIM-005: 计费曝光 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(expose_cnt) AS expose_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY expose_cnt DESC
```

### CM-ADV-DIM-006: 计费曝光 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(expose_cnt) AS expose_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY expose_cnt DESC
LIMIT 50
```

### CM-ADV-DIM-007: 计费点击 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(click_cnt) AS click_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY click_cnt DESC
```

### CM-ADV-DIM-008: 计费点击 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(click_cnt) AS click_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY click_cnt DESC
LIMIT 50
```

### CM-ADV-DIM-009: 广告下载量 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(download_cnt) AS download_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY download_cnt DESC
```

### CM-ADV-DIM-010: 广告下载量 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(download_cnt) AS download_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY download_cnt DESC
LIMIT 50
```

### CM-ADV-DIM-011: 广告请求次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY ad_request_cnt DESC
```

### CM-ADV-DIM-012: 广告请求次数 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(ad_request_cnt) AS ad_request_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY ad_request_cnt DESC
LIMIT 50
```

### CM-ADV-DIM-013: 广告填充次数 — 按广告位场景

```sql
SELECT  date,
        ad_position_scene,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, ad_position_scene
ORDER BY ad_response_cnt DESC
```

### CM-ADV-DIM-014: 广告填充次数 — 按广告位

```sql
SELECT  date,
        tag_id,
        SUM(ad_response_cnt) AS ad_response_cnt
FROM    doris_c3prc_xiaomi.newhome.ads_newhome_finance_core_indicators_di
WHERE   date = '${DATE}'
GROUP BY date, tag_id
ORDER BY ad_response_cnt DESC
LIMIT 50
```

---

## Calculated Metrics (不需要开发)

| Metric | Formula | Description |
|--------|---------|-------------|
| eCPM | 财收/计费曝光*1000 | 每千次曝光收入 |
| CTR | 计费点击/计费曝光 | 广告点击率 |
| CVR | 广告下载/计费点击 | 广告转化率 |
| CPC | 财收/计费点击 | 每次点击成本 |
| 填充率 | 广告填充/广告请求 | 广告填充率 |
