# 模块4 配套练习：SQL 进阶 —— 多表 JOIN 与 CTE

> 面向：产品 / 爱钻研的运营（🔷进阶）。销售/运营可只看参考答案理解思路，复杂查询交给 AI。
> 说明：本练习练"多表关联 + CTE 拆步骤 + 避坑"。每题附**参考答案 SQL**。

---

## 练习1：PUSH 启动用户 vs 非 PUSH 用户的信息流消费对比（核心）
需求：查 2026-06-25 ~ 2026-07-01，PUSH 启动用户 vs 非 PUSH 启动用户的：用户数、人均 APP 时长（分钟）、人均信息流时长（分钟）、信息流渗透率（有消费的用户占比）、CTR。
要求：用 WITH 拆步骤、LEFT JOIN 关联、NULL 转 0。

**参考答案：**
```sql
WITH
-- 步骤1：每日 APP 用户，标记是否 PUSH 启动
app_user AS (
    SELECT
        date, did, app_dura,
        MAX(CASE WHEN app_launch_way IN ('点击push','subscribe_push') THEN 1 ELSE 0 END) AS is_push_launch
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date BETWEEN 20260625 AND 20260701
      AND is_app_dau_2024 = 1 AND COALESCE(did,'') != ''
    GROUP BY date, did, app_dura
),
-- 步骤2：信息流消费
feed_consume AS (
    SELECT date, did, expos_cnt, click_cnt, feed_dura,
           news_vv_cnt + short_vv_cnt + mini_vv_cnt AS vv
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
    WHERE date BETWEEN 20260625 AND 20260701
      AND is_dau_feed_dapan_2024 = 1 AND COALESCE(did,'') != '' AND is_top = 0
),
-- 步骤3：LEFT JOIN 关联（NULL 转 0）
user_full AS (
    SELECT a.date, a.did, a.is_push_launch, a.app_dura,
           COALESCE(b.expos_cnt,0) AS expos_cnt,
           COALESCE(b.click_cnt,0) AS click_cnt,
           COALESCE(b.feed_dura,0) AS feed_dura,
           COALESCE(b.vv,0) AS vv
    FROM app_user a
    LEFT JOIN feed_consume b ON a.date = b.date AND a.did = b.did
)
-- 步骤4：分组聚合
SELECT
    date,
    CASE WHEN is_push_launch = 1 THEN 'PUSH启动' ELSE '非PUSH启动' END AS user_group,
    COUNT(DISTINCT did) AS user_cnt,
    ROUND(SUM(app_dura)/COUNT(DISTINCT did)/60000, 2) AS avg_app_dur_min,
    ROUND(SUM(feed_dura)/COUNT(DISTINCT did)/60000, 2) AS avg_feed_dur_min,
    ROUND(SUM(CASE WHEN vv > 0 THEN 1 ELSE 0 END)*1.0/COUNT(DISTINCT did), 4) AS vv_penetration,
    ROUND(CASE WHEN SUM(expos_cnt) > 0 THEN SUM(click_cnt)*1.0/SUM(expos_cnt) ELSE 0 END, 4) AS ctr
FROM user_full
GROUP BY date, CASE WHEN is_push_launch = 1 THEN 'PUSH启动' ELSE '非PUSH启动' END
ORDER BY date, user_group
```
> 关键点：① 先在子查询里过滤再 JOIN（性能）② LEFT JOIN 后 `COALESCE` 补 0 ③ CTR 用 `SUM/SUM` 防止分母为 0。

---

## 练习2：新老用户在不同启动方式下的分布
需求：查 2026-06-28，新 / 老用户在 5 大类启动方式下的 DAU 及各自占比。

**参考答案：**
```sql
WITH user_launch AS (
    SELECT
        did,
        CASE WHEN is_new_2024 = 1 THEN '新用户' ELSE '老用户' END AS user_type,
        CASE
            WHEN app_launch_way IN ('点击icon','点击桌面书签') THEN '1-主启'
            WHEN app_launch_way = '第三方调起' THEN '2-三方调起'
            WHEN app_launch_way IN ('点击push','subscribe_push') THEN '3-Push启动'
            WHEN app_launch_way LIKE '%搜索%' THEN '4-搜索入口'
            ELSE '5-其他入口'
        END AS launch_type
    FROM iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di
    WHERE date = 20260628 AND is_app_dau_2024 = 1 AND COALESCE(did,'') != ''
),
user_total AS (
    SELECT user_type, COUNT(DISTINCT did) AS total_dau FROM user_launch GROUP BY user_type
)
SELECT
    a.user_type, a.launch_type,
    COUNT(DISTINCT a.did) AS launch_dau,
    b.total_dau,
    ROUND(COUNT(DISTINCT a.did)*1.0/b.total_dau, 4) AS ratio
FROM user_launch a
JOIN user_total b ON a.user_type = b.user_type
GROUP BY a.user_type, a.launch_type, b.total_dau
ORDER BY a.user_type, launch_dau DESC
```

---

## 练习3：AI 辅助复杂 SQL（拆步骤喂 AI）
需求："查 2026 年 6 月，点击过 PUSH 的用户，7 天留存率（点击 PUSH 当天 D0，D7 仍活跃占比），对比全体用户 7 天留存。"

**示范解（拆步骤，不必手写完整 SQL，重在会拆）：**
1. 步骤1：取 6 月每日活跃用户，标记当天是否点击 PUSH 启动 → 得到 D0 用户标签表
2. 步骤2：取 6 月~7 月中旬的全量活跃用户 → 作为"留存活跃表"
3. 步骤3：D0 用户关联"D0 日期 +7 天"的活跃表，判断是否还在 → 算 D7 留存
4. 步骤4：按 D0 日期 + 用户组（PUSH / 全体）聚合算留存率

> 💡 把这 4 步喂给 AI（每步说清用什么表、输出什么字段），比直接丢"算个留存"准确率高得多。生成后按下面 Checklist 校验。

---

## 练习4：挑错——下面 SQL 错在哪？
```sql
SELECT a.did, SUM(b.feed_dura)
FROM miui_di a
JOIN label_di b ON a.did = b.did      -- ①
WHERE a.date = 20260628
```
**参考答案（至少 3 个问题）：**
1. **JOIN 只关联了 did，漏了 date** → 一个人多天的数据会交叉相乘，数据爆炸膨胀。应 `ON a.date=b.date AND a.did=b.did`。
2. **label_di 没加 date 分区过滤** → 右表扫全表，极慢。子查询里两张表都要加 date。
3. **SELECT 了 did 又 SUM，但没 GROUP BY** → 语法/逻辑错，要 `GROUP BY a.did`。
4. 附加：没过滤有效活跃、没 COALESCE 处理 NULL、时长没 /60000。

---

## SQL 排查 Checklist（跑错/结果不对时按序检查）
1. 加了 date 分区吗？ 2. 加了有效用户过滤吗？ 3. JOIN 写 ON 了吗、关联 key 对吗（多天要 date+did）？ 4. 算人数用 DISTINCT 吗？ 5. 除法 *1.0 吗？ 6. NULL 用 COALESCE 吗？ 7. 时长 /60000 吗？ 8. 自然流量 is_top=0 吗？ 9. 关联后记录数有没有异常膨胀？ 10. 口径对吗（CTR 分母、留存定义）？

---

## 完成标准
- [ ] 能看懂/写出用 WITH 拆步骤的多表 LEFT JOIN 查询
- [ ] 牢记 JOIN 必写 ON、多天关联要 date+did、先过滤再 JOIN
- [ ] 会把复杂需求拆成步骤喂给 AI，并用 Checklist 校验
