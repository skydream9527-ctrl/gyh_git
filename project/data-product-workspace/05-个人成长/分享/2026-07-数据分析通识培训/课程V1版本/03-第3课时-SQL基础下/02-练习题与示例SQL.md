# 第3课时练习题与示例SQL

---

## 课堂练习（复杂查询场景）

---

### 练习1：PUSH启动用户的信息流消费对比
需求：查询2026-06-25到2026-07-01，PUSH启动用户 vs 非PUSH启动用户的：
- 用户数
- 人均APP时长（分钟）
- 人均信息流时长（分钟）
- 信息流VV渗透率（有信息流消费的用户占比）
- CTR（点击/曝光，注意只统计有曝光的用户）
要求用WITH语句拆分步骤，LEFT JOIN关联，NULL值转0

**参考答案：**
```sql
WITH 
-- 步骤1：每日APP用户，标记是否PUSH启动
app_user AS (
    SELECT
        date,
        did,
        app_dura,
        MAX(CASE WHEN app_launch_way IN ('点击push', 'subscribe_push') THEN 1 ELSE 0 END) AS is_push_launch
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260625 AND 20260701
      AND is_app_dau_2024 = 1
      AND COALESCE(did, '') != ''
    GROUP BY date, did, app_dura
),
-- 步骤2：信息流消费数据
feed_consume AS (
    SELECT
        date,
        did,
        expos_cnt,
        click_cnt,
        feed_dura,
        news_vv_cnt + short_vv_cnt + mini_vv_cnt AS vv
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260625 AND 20260701
      AND is_dau_feed_dapan_2024 = 1
      AND COALESCE(did, '') != ''
      AND is_top = 0
),
-- 步骤3：关联数据
user_full AS (
    SELECT
        a.date,
        a.did,
        a.is_push_launch,
        a.app_dura,
        COALESCE(b.expos_cnt, 0) AS expos_cnt,
        COALESCE(b.click_cnt, 0) AS click_cnt,
        COALESCE(b.feed_dura, 0) AS feed_dura,
        COALESCE(b.vv, 0) AS vv
    FROM app_user a
    LEFT JOIN feed_consume b
    ON a.date = b.date AND a.did = b.did
)
-- 步骤4：分组聚合
SELECT
    date,
    CASE WHEN is_push_launch = 1 THEN 'PUSH启动用户' ELSE '非PUSH启动用户' END AS user_group,
    COUNT(DISTINCT did) AS user_cnt,
    ROUND(SUM(app_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_app_dur_min,
    ROUND(SUM(feed_dura) / COUNT(DISTINCT did) / 60000, 2) AS avg_feed_dur_min,
    ROUND(SUM(CASE WHEN vv > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT did), 4) AS vv_penetration,
    ROUND(CASE WHEN SUM(expos_cnt) > 0 THEN SUM(click_cnt) * 1.0 / SUM(expos_cnt) ELSE 0 END, 4) AS ctr
FROM user_full
GROUP BY date, CASE WHEN is_push_launch = 1 THEN 'PUSH启动用户' ELSE '非PUSH启动用户' END
ORDER BY date, user_group
```

---

### 练习2：新老用户在不同启动方式下的差异
需求：查询2026-06-28，新用户（is_new_2024=1）和老用户，在5大类启动方式下的DAU占比，输出每个用户群的启动方式分布。

**参考答案：**
```sql
WITH user_launch AS (
    SELECT
        did,
        CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END AS user_type,
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
),
user_total AS (
    SELECT user_type, COUNT(DISTINCT did) AS total_dau
    FROM user_launch
    GROUP BY user_type
)
SELECT
    a.user_type,
    a.launch_type,
    COUNT(DISTINCT a.did) AS launch_dau,
    b.total_dau,
    ROUND(COUNT(DISTINCT a.did) * 1.0 / b.total_dau, 4) AS ratio
FROM user_launch a
JOIN user_total b ON a.user_type = b.user_type
GROUP BY a.user_type, a.launch_type, b.total_dau
ORDER BY a.user_type, launch_dau DESC
```

---

### 练习3：用AI辅助写复杂SQL练习
需求："查2026年6月，点击过PUSH的用户中，7天留存率是多少（即点击PUSH当天是D0，D7仍活跃的用户占比），对比全体用户的7天留存率"
提示：
1. 先把这个需求拆成步骤，用WITH结构
2. 思考怎么定义点击PUSH用户、怎么算留存
3. 自己先尝试写，再让AI生成，对比差异，校验逻辑是否正确

---

## SQL排查问题Checklist
SQL跑错/结果不对的时候，按这个顺序检查：
1. ✅ 有没有加date分区过滤？
2. ✅ 有没有加is_app_dau_2024=1有效用户过滤？
3. ✅ JOIN有没有写ON条件？关联key对不对？（多天查询要关联date+did）
4. ✅ 计算人数有没有用COUNT(DISTINCT did)？
5. ✅ 除法有没有乘1.0避免整数除法？
6. ✅ NULL值有没有用COALESCE转0？
7. ✅ 时长单位有没有转换（毫秒转分钟除以60000）？
8. ✅ 信息流自然流量有没有过滤is_top=0？
9. ✅ 多表关联后有没有数据重复？（可以先查COUNT看记录数对不对）
10. ✅ 指标口径是否正确？（CTR是点击/曝光还是点击/到达？留存怎么定义？）
