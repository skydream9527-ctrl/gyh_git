# 第2课时练习题与示例SQL

---

## 课堂练习（5个基础查询）
使用学过的两张核心表完成以下查询，先尝试自己写，再用AI辅助生成，最后对比差异：

---

### 练习1：APP整体核心指标
需求：查询2026-06-20到2026-06-30每天的：
- APP DAU
- 总启动次数
- 人均启动次数（总启动次数/DAU，保留2位小数）
- 人均APP使用时长（分钟，保留2位小数）
按日期升序排列

**参考答案：**
```sql
SELECT
    date,
    COUNT(DISTINCT did) AS app_dau,
    SUM(app_open_cnt) AS total_open_cnt,
    ROUND(SUM(app_open_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_open_cnt,
    ROUND(SUM(app_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_app_duration_min
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date BETWEEN 20260620 AND 20260630
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
GROUP BY date
ORDER BY date
```

---

### 练习2：信息流核心指标
需求：查询2026-06-28当天的：
- 信息流DAU
- 总曝光、总点击
- CTR（点击率，保留4位小数）
- 人均曝光次数、人均点击次数
- 人均信息流消费时长（分钟，保留2位小数）
- 总VV（图文+短视频+小视频）
要求：只统计自然推荐流量（过滤置顶内容）

**参考答案：**
```sql
SELECT
    date,
    COUNT(DISTINCT did) AS feed_dau,
    SUM(expos_cnt) AS total_expose,
    SUM(click_cnt) AS total_click,
    ROUND(SUM(click_cnt) * 1.0 / SUM(expos_cnt), 4) AS ctr,
    ROUND(SUM(expos_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_expose_per_user,
    ROUND(SUM(click_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_click_per_user,
    ROUND(SUM(feed_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_feed_duration_min,
    SUM(news_vv_cnt + short_vv_cnt + mini_vv_cnt) AS total_vv
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE date = 20260628
  AND is_dau_feed_dapan_2024 = 1
  AND COALESCE(did, '') != ''
  AND is_top = 0
GROUP BY date
```

---

### 练习3：新老用户分群指标
需求：查询2026-06-28当天，新用户和老用户分别的：
- DAU
- 人均APP时长
- 人均启动次数
提示：用is_new_2024字段，=1是新用户，=0是老用户

**参考答案：**
```sql
SELECT
    CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END AS user_type,
    COUNT(DISTINCT did) AS dau,
    ROUND(SUM(app_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_duration_min,
    ROUND(SUM(app_open_cnt) * 1.0 / COUNT(DISTINCT did), 2) AS avg_open_cnt
FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
WHERE date = 20260628
  AND is_app_dau_2024 = 1
  AND COALESCE(did, '') != ''
GROUP BY CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END
```

---

### 练习4：启动方式拆分
需求：查询2026-06-28当天，5大类启动方式的DAU和占比：
- 主启（点击icon、点击桌面书签）
- 三方调起（第三方调起）
- Push启动（点击push、subscribe_push）
- 搜索入口（所有带"搜索"的启动方式）
- 其他入口
按DAU从大到小排序

**参考答案：**
```sql
WITH base AS (
    SELECT
        did,
        CASE
            WHEN app_launch_way IN ('点击icon', '点击桌面书签') THEN '1-主启'
            WHEN app_launch_way = '第三方调起' THEN '2-三方调起'
            WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN '3-Push启动'
            WHEN app_launch_way LIKE '%搜索%' THEN '4-搜索入口'
            ELSE '5-其他入口'
        END AS launch_type
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date = 20260628
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
)
SELECT
    launch_type,
    COUNT(DISTINCT did) AS dau,
    ROUND(COUNT(DISTINCT did) * 1.0 / SUM(COUNT(DISTINCT did)) OVER(), 4) AS dau_ratio
FROM base
GROUP BY launch_type
ORDER BY dau DESC
```

---

### 练习5：用AI辅助写SQL练习
找一个你日常工作中经常需要查的指标，按照「正面提示词模板」写清楚需求，让AI生成SQL，然后按照4步校验法检查：
1. 字段是否都存在？
2. 过滤条件有没有加全？
3. 逻辑和公式对不对？
4. 结果数值在合理区间吗？

---

## AI写SQL提示词模板（可直接复制修改）
```
请帮我写Hive SQL，使用以下表：
表名：iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
字段说明：
- date: 日期，格式yyyyMMdd，分区字段
- did: 设备ID，用户唯一标识
- is_app_dau_2024: =1表示有效活跃用户
- app_open_cnt: APP打开次数
- app_dura: APP使用时长，单位毫秒
- is_new_2024: =1是新用户，=0是老用户
- app_launch_way: 启动方式，枚举值：点击icon/第三方调起/点击push/...

表名：iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
字段说明：
- date: 日期，格式yyyyMMdd，分区字段
- did: 设备ID
- is_dau_feed_dapan_2024: =1表示信息流活跃用户
- is_top: 0=自然推荐，1=置顶内容
- expos_cnt: 曝光次数
- click_cnt: 点击次数
- news_vv_cnt: 图文VV
- short_vv_cnt: 短视频VV
- mini_vv_cnt: 小视频VV
- feed_dura: 信息流消费时长，单位毫秒

我的查询需求：
【在这里写清楚你要查的指标、时间范围、过滤条件、分组维度】

要求：
1. 所有查询必须加date分区过滤，必须加is_app_dau_2024=1（或is_dau_feed_dapan_2024=1）过滤有效用户，必须过滤空did
2. 计算用户数必须用COUNT(DISTINCT did)
3. 除法计算记得乘1.0避免整数除法，保留合适的小数位
4. 时长是毫秒，转分钟需要除以60000
5. 代码加必要注释
```
