# 模块3 配套练习：SQL 基础 + AI 辅助取数

> 面向：产品（必做）/ 销售 / 运营（做 1、2、5，其余了解）
> 说明：先自己写，再用 AI 生成对照，最后按 4 步校验。每题附**参考答案 SQL**。
> 用表：`iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di`（APP）、`...label_di`（信息流）。

---

## 练习1：APP 整体核心指标（必做）
需求：查 2026-06-20 ~ 2026-06-30 每天的 APP DAU、总启动次数、人均启动次数（2 位小数）、人均 APP 时长（分钟，2 位小数），按日期升序。

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

## 练习2：信息流核心指标（必做）
需求：查 2026-06-28 当天信息流 DAU、总曝光、总点击、CTR（4 位小数）、人均曝光、人均点击、人均消费时长（分钟）、总 VV（图文+短视频+小视频）。只统计自然推荐流量。

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
> 三个高频坑：除法 `*1.0`、时长 `/60000`、大盘 CTR 用 `SUM/SUM` 不用 `AVG`。

---

## 练习3：新老用户分群
需求：查 2026-06-28，新用户 / 老用户分别的 DAU、人均 APP 时长（分钟）、人均启动次数。提示：`is_new_2024`，=1 新、=0 老。

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

## 练习4：启动方式拆分 + 占比
需求：查 2026-06-28，5 大类启动方式（主启 / 三方调起 / Push / 搜索 / 其他）的 DAU 和占比，按 DAU 降序。

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
> 💡 这里已经用到一点 CTE（WITH）和窗口函数 `SUM(...) OVER()` 算占比，模块4 会细讲 CTE。

---

## 练习5：AI 辅助 + 4 步校验（人人必做）
挑一个你日常要看的指标，按提示词 5 要素（表 / 字段 / 需求 / 过滤 / 注意）写清楚让 AI 生成 SQL，然后按 4 步校验：

**示范：提示词写法**
> 【表】label_di（did+date 粒度）【字段】expos_cnt 曝光、click_cnt 点击、is_top 置顶、is_dau_feed_dapan_2024 信息流活跃【需求】6/28 各信息流频道的 CTR【过滤】自然流量 is_top=0、有效活跃=1【注意】加 date 分区、CTR=SUM(click)/SUM(expos) 且 *1.0】

**4 步校验清单（对照 AI 结果打勾）：**
- [ ] ① 字段校验：AI 有没有编不存在的字段？（对照数据地图/速查手册）
- [ ] ② 分区校验：WHERE 加了 `date` 吗？
- [ ] ③ 逻辑校验：算人数 `COUNT(DISTINCT did)`？除法 `*1.0`？时长 `/60000`？
- [ ] ④ 结果校验：数量级合理吗？（DAU 百万级、CTR 百分之几）

---

## 完成标准
- [ ] 练习 1~4 能独立写出（或看懂参考答案每一行在干嘛）
- [ ] 记得四个必加：date 分区、is_app_dau/is_dau_feed 过滤、COUNT(DISTINCT did)、除法 *1.0
- [ ] 会用 5 要素提示词让 AI 写 SQL，并用 4 步校验把关

> 💡 销售/运营重点是练习 5（让 AI 写 + 校验）；练习 1、2 至少要能"看懂改日期就能用"。
