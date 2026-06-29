# 浏览器信息流 DAU 及留存率

> 口径：`iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
> 条件：`is_app_dau_2024 = 1 AND is_dau_feed_dapan_2024 = 1`
> 时间范围：20260401 ~ 20260610

---

## 1. 信息流 DAU（每日）

```sql
SELECT
    date,
    COUNT(DISTINCT did) AS feed_dau
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date BETWEEN 20260401 AND 20260610
  AND is_app_dau_2024 = 1
  AND is_dau_feed_dapan_2024 = 1
GROUP BY date
ORDER BY date;
```

---

## 2. 次日留存率

```sql
WITH dau AS (
    SELECT
        date,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260401 AND 20260610
      AND is_app_dau_2024 = 1
      AND is_dau_feed_dapan_2024 = 1
),

retained AS (
    SELECT
        a.date,
        COUNT(DISTINCT a.did) AS dau_cnt,
        COUNT(DISTINCT CASE
            WHEN datediff(
                from_unixtime(unix_timestamp(cast(b.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd'),
                from_unixtime(unix_timestamp(cast(a.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd')
            ) = 1 THEN b.did
        END) AS d1_retained_cnt
    FROM dau a
    LEFT JOIN dau b
      ON a.did = b.did
     AND b.date > a.date
    GROUP BY a.date
)

SELECT
    date,
    dau_cnt,
    d1_retained_cnt,
    ROUND(d1_retained_cnt * 100.0 / dau_cnt, 2) AS d1_retention_rate
FROM retained
WHERE date BETWEEN 20260401 AND 20260609
ORDER BY date;
```

---

## 3. 7 日留存率 & 30 日留存率

```sql
WITH dau AS (
    SELECT
        date,
        did
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260401 AND 20260710
      AND is_app_dau_2024 = 1
      AND is_dau_feed_dapan_2024 = 1
),

base AS (
    SELECT
        a.date,
        a.did,
        MAX(CASE WHEN datediff(
            from_unixtime(unix_timestamp(cast(b.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd'),
            from_unixtime(unix_timestamp(cast(a.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd')
        ) = 7 THEN 1 ELSE 0 END) AS is_d7,
        MAX(CASE WHEN datediff(
            from_unixtime(unix_timestamp(cast(b.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd'),
            from_unixtime(unix_timestamp(cast(a.date AS string), 'yyyyMMdd'), 'yyyy-MM-dd')
        ) = 30 THEN 1 ELSE 0 END) AS is_d30
    FROM dau a
    LEFT JOIN dau b
      ON a.did = b.did
     AND b.date > a.date
    GROUP BY a.date, a.did
)

SELECT
    date,
    COUNT(*) AS dau_cnt,
    SUM(is_d7)  AS d7_retained_cnt,
    SUM(is_d30) AS d30_retained_cnt,
    ROUND(SUM(is_d7)  * 100.0 / COUNT(*), 2) AS d7_retention_rate,
    ROUND(SUM(is_d30) * 100.0 / COUNT(*), 2) AS d30_retention_rate
FROM base
WHERE date BETWEEN 20260401 AND 20260610
GROUP BY date
ORDER BY date;
```
