# Browser Push - 核心指标 SQL 口径

> **业务域**：浏览器 Push（推送） | **数据层级**：底表/回调日志层
> **核心底表**：`hive_zjyprc_hadoop.browser.push_callback_log`
> **表结构 / 维度 / 关联模式**：见 `reference/browser/push-table-schema.md`

> [!IMPORTANT]
> 1. **日期整型**：`date = 20260628` / `date BETWEEN 20260601 AND 20260628`，**不要加引号**（否则分区裁剪失效、超时）。
> 2. **PV/UV 去重**：送达/点击必须 `COUNT(DISTINCT ...)`；PV 维度 `(deviceid, reachItems[0].ext)`，UV 维度 `deviceid`。**禁止直接 SUM**。
> 3. **通用必带过滤**：`reachItems[0].type IN ('EXPOSE','CLICK') AND deviceid IS NOT NULL AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''`。

## Source Tables

| Table | Full Name | Database |
|-------|-----------|----------|
| push_callback_log | Push回调日志表（送达/点击） | hive_zjyprc_hadoop.browser |
| dwm_browser_push_open_session_consum_di | Push会话消费统计表（时长，单位分钟） | iceberg_zjyprc_hadoop.browser |
| dwm_browser_event_aggregation_label_di | 流内行为宽表（Push点击后消费，单位毫秒） | iceberg_zjyprc_hadoop.browser |
| dwd_push_real_expose_dt | 真实送达表（屏幕真实展示） | iceberg_zjyprc_hadoop.browser |
| dwd_xmpush_expose_device_di | 支持真实送达设备表 | iceberg_zjyprc_hadoop.push |
| dwd_push_content_pool_daily_df | 审出池表（物料属性/队列/分类） | hive_zjyprc_hadoop.browser |
| dm_push_ai_common_feature_item_df | 物料体裁表（c_type） | paimon_zjyprc_hadoop.browser |
| dwd_browser_notify_switch_df | 通知开关表（关闭率） | hive_zjyprc_hadoop.push |

---

## Atomic Metrics (不筛选维度)

### PUSH-001: Push 送达 PV / UV

> 别名：EXPOSE_pv、EXPOSE_uv、送达量、推送量、送达人数。"送达"=推到通知栏即算 EXPOSE（用户可能没看到）。

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN (deviceid, reachItems[0].ext) END) AS expose_pv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN deviceid END)                      AS expose_uv
FROM    hive_zjyprc_hadoop.browser.push_callback_log
WHERE   date BETWEEN ${start_date} AND ${end_date}
        AND reachItems[0].type IN ('EXPOSE', 'CLICK')
        AND deviceid IS NOT NULL
        AND reachItems[0].stockId IS NOT NULL
        AND reachItems[0].stockId != ''
GROUP BY date
```

### PUSH-002: Push 点击 PV / UV / CTR / UTR

> CTR = click_pv / expose_pv（PV口径）；UTR = click_uv / expose_uv（UV口径）。`expid` 可去掉做大盘。

```sql
SELECT  date,
        reachItems[0].expid                                                                            AS expid,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN (deviceid, reachItems[0].ext) END) AS expose_pv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN deviceid END)                      AS expose_uv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN (deviceid, reachItems[0].ext) END) AS click_pv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN deviceid END)                      AS click_uv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN (deviceid, reachItems[0].ext) END) * 1.0
            / NULLIF(COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN (deviceid, reachItems[0].ext) END), 0) AS ctr,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN deviceid END) * 1.0
            / NULLIF(COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN deviceid END), 0)                      AS utr
FROM    hive_zjyprc_hadoop.browser.push_callback_log
WHERE   date BETWEEN ${start_date} AND ${end_date}
        AND reachItems[0].type IN ('EXPOSE', 'CLICK')
        AND deviceid IS NOT NULL
        AND reachItems[0].stockId IS NOT NULL
        AND reachItems[0].stockId != ''
GROUP BY date, reachItems[0].expid
```

### PUSH-003: Push DAU（点击 Push 进入 App 的日活）

> 通过点击 Push 进入浏览器的日活用户数，衡量 Push 对 App 带来的用户价值。

```sql
SELECT  date,
        COUNT(DISTINCT did) AS push_dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date BETWEEN ${start_date} AND ${end_date}
        AND app_open_cnt > 0
        AND app_launch_way = '点击push'
GROUP BY date
```

### PUSH-004: Push Session 时长 / 落地页时长（分钟）

> 来自 `dwm_browser_push_open_session_consum_di`，`consum_dura` 单位**分钟**。JOIN 前必须先把 push_log 去重到 `(date, expid, deviceid)`，否则时长重复计数。

```sql
WITH push_did AS (
    SELECT DISTINCT date, reachItems[0].expid AS expid, deviceid
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND reachItems[0].type IN ('EXPOSE', 'CLICK')
           AND deviceid IS NOT NULL
           AND reachItems[0].stockId IS NOT NULL
           AND reachItems[0].stockId != ''
),
push_dur AS (
    SELECT date, did,
           SUM(CASE WHEN session_type = 'push点击session' THEN consum_dura ELSE 0 END) AS session_dur_min,
           SUM(CASE WHEN session_type = 'push点击详情页'   THEN consum_dura ELSE 0 END) AS detail_dur_min
    FROM   iceberg_zjyprc_hadoop.browser.dwm_browser_push_open_session_consum_di
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND item_type != 'ALL'
    GROUP BY date, did
)
SELECT  p.date,
        p.expid,
        SUM(d.session_dur_min)                              AS total_session_dur_min,
        SUM(d.detail_dur_min)                               AS total_detail_dur_min,
        SUM(d.session_dur_min) / COUNT(DISTINCT p.deviceid) AS avg_session_dur_min,
        SUM(d.detail_dur_min)  / COUNT(DISTINCT p.deviceid) AS avg_detail_dur_min
FROM    push_did p
LEFT JOIN push_dur d ON p.date = d.date AND p.deviceid = d.did
GROUP BY p.date, p.expid
```

### PUSH-005: Push 点击后消费时长（落地页+沉浸流，分钟）

> 通过 Push 入口进入那次 session 的消费时长。来自流内宽表，`app_launch_way = '点击push'`，`consum_dura` 单位**毫秒**（/60000）。人均分母用有消费的 UV。

```sql
SELECT  date,
        SUM(consum_dura) / 60000                                            AS push_consum_dur_min,
        SUM(consum_dura) / 60000 / NULLIF(COUNT(DISTINCT CASE WHEN consum_dura > 0 THEN did END), 0) AS avg_push_consum_dur_min
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date BETWEEN ${start_date} AND ${end_date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND app_launch_way = '点击push'
GROUP BY date
```

### PUSH-006: 真实送达 PV / UV

> 用户屏幕确实展示了通知（区别于送达到通知栏）。先筛支持真实送达打点的设备，再关联 `dwd_push_real_expose_dt`。仅覆盖约 80% 设备，需注明口径。`app_id = 1000274`。

```sql
WITH support_device AS (
    SELECT date, did
    FROM   iceberg_zjyprc_hadoop.push.dwd_xmpush_expose_device_di
    WHERE  app_id = 1000274
           AND date BETWEEN ${start_date} AND ${end_date}
    GROUP BY 1, 2
),
real_send AS (
    SELECT date, deviceid AS did, reachItems[0].ext AS pushid
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND reachItems[0].type = 'EXPOSE'
           AND deviceid IS NOT NULL
           AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''
),
real_expose AS (
    SELECT date, did, job_key AS pushid   -- job_key = pushid
    FROM   iceberg_zjyprc_hadoop.browser.dwd_push_real_expose_dt
    WHERE  app_id = 1000274
           AND date BETWEEN ${start_date} AND ${end_date}
),
real_click AS (
    SELECT date, deviceid AS did, reachItems[0].ext AS pushid
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND reachItems[0].type = 'CLICK'
           AND deviceid IS NOT NULL
           AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''
)
SELECT  t2.date,
        COUNT(DISTINCT (t2.did, t2.pushid)) AS send_pv,
        COUNT(DISTINCT t2.did)              AS send_uv,
        COUNT(DISTINCT (t3.did, t3.pushid)) AS real_expose_pv,
        COUNT(DISTINCT t3.did)              AS real_expose_uv,
        COUNT(DISTINCT (t4.did, t4.pushid)) AS click_pv,
        COUNT(DISTINCT t4.did)              AS click_uv
FROM    support_device t1
JOIN      real_send   t2 ON t1.did = t2.did AND t1.date = t2.date
LEFT JOIN real_expose t3 ON t2.did = t3.did AND t2.date = t3.date AND t2.pushid = t3.pushid
LEFT JOIN real_click  t4 ON t3.did = t4.did AND t3.date = t4.date AND t3.pushid = t4.pushid
GROUP BY t2.date
```

---

## Dimension-Split Metrics (按维度筛选)

### PUSH-DIM-001: 送达/点击/CTR — 按 Push 类型

> Push 类型分组写法见 `push-table-schema.md` 的 DIM-PUSHTYPE。

```sql
SELECT  date,
        CASE
            WHEN reachItems[0].ext LIKE 'RPT%'                                     THEN 'AI早晚报'
            WHEN reachItems[0].ext LIKE 'BA%'                                      THEN '主动智能通发'
            WHEN reachItems[0].ext LIKE 'PD%' OR reachItems[0].ext LIKE 'PDF%'
              OR reachItems[0].ext LIKE 'SOF%'                                     THEN '主动智能补发'
            WHEN reachItems[0].ext LIKE '93%' AND reachItems[0].ext LIKE '%MUSTPH' THEN '全局试探'
            WHEN reachItems[0].ext LIKE '93%'                                      THEN '地域试探'
            WHEN reachItems[0].ext LIKE '32%'                                      THEN '一级分类试探'
            WHEN reachItems[0].ext LIKE '31%'                                      THEN '二级分类试探'
            WHEN reachItems[0].ext LIKE '81%'                                      THEN '即刻'
            WHEN reachItems[0].ext LIKE '80%'                                      THEN '策略服务'
        END                                                                                            AS push_type,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN (deviceid, reachItems[0].ext) END) AS expose_pv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN (deviceid, reachItems[0].ext) END) AS click_pv,
        COUNT(DISTINCT CASE WHEN reachItems[0].type = 'CLICK'  THEN (deviceid, reachItems[0].ext) END) * 1.0
            / NULLIF(COUNT(DISTINCT CASE WHEN reachItems[0].type = 'EXPOSE' THEN (deviceid, reachItems[0].ext) END), 0) AS ctr
FROM    hive_zjyprc_hadoop.browser.push_callback_log
WHERE   date BETWEEN ${start_date} AND ${end_date}
        AND reachItems[0].type IN ('EXPOSE', 'CLICK')
        AND deviceid IS NOT NULL
        AND reachItems[0].stockId IS NOT NULL
        AND reachItems[0].stockId != ''
GROUP BY date, 2
ORDER BY date, push_type
```

### PUSH-DIM-002: 送达/点击/CTR — 按物料来源队列 + 体裁

> 关联审出池取 `audit_queue_name`，关联体裁表取 `c_type`。

```sql
WITH push_log AS (
    SELECT date, reachItems[0].expid AS expid, deviceid,
           reachItems[0].stockId AS stockid, reachItems[0].ext AS pushId, reachItems[0].type AS type
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND reachItems[0].type IN ('EXPOSE', 'CLICK')
           AND deviceid IS NOT NULL
           AND reachItems[0].stockId IS NOT NULL
           AND reachItems[0].stockId != ''
),
content_pool AS (
    SELECT date,
           get_json_object(get_json_object(item, '$.pushItemModels[0]'), '$.itemId') AS stockid,
           get_json_object(item, '$.ext.audit_queue_name')                            AS audit_queue_name
    FROM   hive_zjyprc_hadoop.browser.dwd_push_content_pool_daily_df
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND appname = 'browser'
),
item_ctype AS (
    SELECT item_id, ctype AS c_type
    FROM   paimon_zjyprc_hadoop.browser.dm_push_ai_common_feature_item_df
    WHERE  date BETWEEN ${start_date} AND ${end_date}
)
SELECT  p.date,
        cp.audit_queue_name,
        ic.c_type,
        COUNT(DISTINCT CASE WHEN p.type = 'EXPOSE' THEN (p.deviceid, p.pushId) END) AS expose_pv,
        COUNT(DISTINCT CASE WHEN p.type = 'CLICK'  THEN (p.deviceid, p.pushId) END) AS click_pv,
        COUNT(DISTINCT CASE WHEN p.type = 'CLICK'  THEN (p.deviceid, p.pushId) END) * 1.0
            / NULLIF(COUNT(DISTINCT CASE WHEN p.type = 'EXPOSE' THEN (p.deviceid, p.pushId) END), 0) AS ctr
FROM    push_log p
LEFT JOIN content_pool cp ON p.date = cp.date AND p.stockid = cp.stockid
LEFT JOIN item_ctype   ic ON p.stockid = ic.item_id
GROUP BY p.date, cp.audit_queue_name, ic.c_type
```

---

## Analysis Queries (常用分析)

### PUSH-ADV-001: 动态关闭率

> 动态关闭 = 原来开着→最近主动关掉了，比静态关闭率更能反映负向体验。需往前回溯 30 天识别"之前是 open"。仅覆盖约 80% 设备。`app_id = '1000274'`。

```sql
WITH dynamic_close AS (
    SELECT date, did FROM (
        SELECT date, did, notify_sw,
               LAG(notify_sw) OVER (PARTITION BY did ORDER BY date) AS last_status,
               LAG(date)      OVER (PARTITION BY did ORDER BY date) AS last_dt
        FROM   hive_zjyprc_hadoop.push.dwd_browser_notify_switch_df
        WHERE  date BETWEEN ${start_date} - 32 AND ${end_date}
               AND app_id = '1000274'
    )
    WHERE date BETWEEN ${start_date} AND ${end_date}
      AND notify_sw = 'close' AND last_status = 'open'
      AND DATEDIFF(TO_DATE(CAST(date AS STRING), 'yyyyMMdd'),
                   TO_DATE(CAST(last_dt AS STRING), 'yyyyMMdd')) BETWEEN 1 AND 30
)
SELECT  date,
        COUNT(DISTINCT CASE WHEN tag != 'dynamic_close' THEN did END) AS available_user,
        COUNT(DISTINCT CASE WHEN tag = 'open'           THEN did END) AS open_user,
        COUNT(DISTINCT CASE WHEN tag = 'dynamic_close'  THEN did END) AS dynamic_close_user
FROM (
    SELECT did, date, notify_sw AS tag
    FROM   hive_zjyprc_hadoop.push.dwd_browser_notify_switch_df
    WHERE  date BETWEEN ${start_date} AND ${end_date} AND app_id = '1000274'
    GROUP BY 1, 2, 3
    UNION
    SELECT did, date, 'dynamic_close' AS tag FROM dynamic_close GROUP BY 1, 2, 3
)
GROUP BY date
```

### PUSH-ADV-002: 分时段送达 / 点击

> 分析 Push 下发时机效果。`expose_hour` 是送达时间（非点击时间），来自 `servertime`。

```sql
WITH expose_log AS (
    SELECT date,
           SUBSTR(FROM_UNIXTIME(servertime / 1000, 'yyyy-MM-dd HH:mm:ss'), 1, 13) AS expose_hour,
           reachItems[0].ext AS pushId, deviceid
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date = ${date}
           AND reachItems[0].type = 'EXPOSE'
           AND deviceid IS NOT NULL AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''
),
click_log AS (
    SELECT reachItems[0].ext AS pushId, deviceid
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date = ${date} AND reachItems[0].type = 'CLICK'
           AND deviceid IS NOT NULL AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''
)
SELECT  e.date, e.expose_hour,
        COUNT(DISTINCT (e.pushId, e.deviceid)) AS expose_pv_by_time,
        COUNT(DISTINCT (c.pushId, e.deviceid)) AS click_pv_by_time
FROM    expose_log e
LEFT JOIN click_log c ON e.pushId = c.pushId AND e.deviceid = c.deviceid
GROUP BY e.date, e.expose_hour
ORDER BY e.expose_hour
```

### PUSH-ADV-003: TOP 10 试探物料 CTR

> 只看全局试探（`ext LIKE '93%'`），最纯粹的质量信号。设 `pv_expose >= 2000` 阈值，样本太小 CTR 不可信。

```sql
WITH push_log AS (
    SELECT date, deviceid AS userid, reachItems[0].stockId AS stockId, reachItems[0].type AS activetype
    FROM   hive_zjyprc_hadoop.browser.push_callback_log
    WHERE  date BETWEEN ${start_date} AND ${end_date}
           AND reachItems[0].ext LIKE '93%'
           AND reachItems[0].type IN ('CLICK', 'EXPOSE')
           AND deviceid IS NOT NULL AND deviceid != ''
           AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''
),
joined AS (
    SELECT date, stockId,
           COUNT(CASE WHEN activetype = 'EXPOSE' THEN userid END) AS pv_expose,
           COUNT(CASE WHEN activetype = 'CLICK'  THEN userid END) AS pv_click,
           COUNT(CASE WHEN activetype = 'CLICK'  THEN userid END) * 1.0
               / NULLIF(COUNT(CASE WHEN activetype = 'EXPOSE' THEN userid END), 0) AS ctr
    FROM   push_log GROUP BY 1, 2
),
top10 AS (
    SELECT date, stockId, ctr,
           DENSE_RANK() OVER (PARTITION BY date ORDER BY ctr DESC) AS ranking
    FROM   joined WHERE pv_expose >= 2000
)
SELECT  t1.date, t1.stockId, t1.ctr, t1.ranking, t2.title, t2.category
FROM    top10 t1
JOIN (
    SELECT id, title, category, date
    FROM   hive_zjyprc_hadoop.browser.dwd_push_content_pool_di
    WHERE  date BETWEEN ${start_date} AND ${end_date}
) t2 ON t1.date = t2.date AND t1.stockId = t2.id
WHERE   t1.ranking <= 10
GROUP BY 1, 2, 3, 4, 5, 6
```

### PUSH-ADV-004: 内容池漏斗（4 层转化）

> 物料量级异常归因。漏斗：物料候选池 → AIGP过滤后 → 相似度去重后 → 审出物料数。
> `log_tag`：`BROWSER_AUDIT_INNER_DUPLICATED_ITEM`(被去重) / `BROWSER_AUDIT_INNER_RESERVED_ITEM`(去重后保留进人审) / `BROWSER_AUDIT_SUBMIT_PUSH_CONTENT_POOL`(最终审出)。

```sql
SELECT date,
       COUNT(DISTINCT CASE WHEN layer = 'pool'   THEN id    END) AS content_pool_cnt,
       COUNT(DISTINCT CASE WHEN layer = 'dup'    THEN itemid END) AS after_dup_cnt,
       COUNT(DISTINCT CASE WHEN layer = 'audit'  THEN itemid END) AS after_audit_cnt
FROM (
    SELECT date, id, NULL AS itemid, 'pool' AS layer
    FROM   hive_zjyprc_hadoop.browser.dwd_push_content_pool_di
    WHERE  date = ${date}
    UNION ALL
    SELECT date, NULL AS id, get_json_object(log_data, '$.itemId') AS itemid,
           CASE WHEN log_tag IN ('BROWSER_AUDIT_INNER_DUPLICATED_ITEM','BROWSER_AUDIT_INNER_RESERVED_ITEM') THEN 'dup'
                WHEN log_tag = 'BROWSER_AUDIT_SUBMIT_PUSH_CONTENT_POOL' THEN 'audit' END AS layer
    FROM   hive_zjyprc_hadoop.browser.m_push_common_log_di
    WHERE  date = ${date}
           AND log_tag IN ('BROWSER_AUDIT_INNER_DUPLICATED_ITEM','BROWSER_AUDIT_INNER_RESERVED_ITEM','BROWSER_AUDIT_SUBMIT_PUSH_CONTENT_POOL')
) t
GROUP BY date
```

---

## Calculated Metrics (不需要开发，由原子指标计算)

| Metric | Formula | Description |
|--------|---------|-------------|
| CTR（PV口径） | click_pv / expose_pv | pv_ctr |
| UTR（UV口径） | click_uv / expose_uv | uv_ctr |
| 人均曝光次数 | expose_pv / expose_uv | avg_expose_pv |
| 送达率 | 送达数(EXPOSE PV) / 下发数(m_push_common_log_di.sendNum) | msg_ack_ratio |
| 人均 session 时长(分钟) | total_session_dur_min / 点击UV | avg_session_dur_min |
| 人均消费时长(分钟) | push_consum_dur(分钟) / 有消费UV | avg_push_consum_dur_min |
| 真实送达率 | real_expose_uv / send_uv | real_expose_rate |
| dauctr | click_uv / push_dau | dau_ctr |
