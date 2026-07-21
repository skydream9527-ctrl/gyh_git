# 高频取数 — SQL 模板

> 来源：2026 H1 共 24+ 份取数交付文档归纳，SQL 骨架集中在三大簇，均为 presto（`iceberg_zjyprc_hadoop`）上的单/双表聚合，`count(distinct did) + group by` 为主，复杂度中低。
> 状态：⚠️ 骨架为归纳版，具体表名/字段/口径需用真实 badcase 校准后标 ✅。

## 三大高频簇

| 簇 | 典型需求 | 输出 | 复用度 |
|----|---------|------|--------|
| 小说 SDK 系列 | 阅读 UV / 时长 / 留存 / 结算 | sheet 明细 | 高 |
| Top-N 系列 | top 机型 / top 网址 / top 账号 | sheet 明细 | 高 |
| 实验对比留存系列 | 实验组 vs 对照组 消费/留存/收入 | sheet 对比 | 高 |

---

## 簇 1：小说 SDK 系列

```sql
/* 小说SDK阅读 UV/时长（分渠道/分体裁）
 * 参数：${start}~${end} 日期 | ${sdk} SDK来源(火山/头条) | ${genre} 体裁
 */
SELECT dt,
       ${genre_dim}                       AS genre,
       COUNT(DISTINCT did)                AS read_uv,
       SUM(read_duration)                 AS total_duration,
       SUM(read_duration)/COUNT(DISTINCT did) AS avg_duration_per_uv
FROM <小说SDK阅读事实表>
WHERE dt BETWEEN '${start}' AND '${end}'
  AND sdk_source = '${sdk}'
GROUP BY dt, ${genre_dim}
ORDER BY dt;
```

要点：滚调/结算口径需与业务确认（复访口径、真实值 vs 上报值）；NH 火山复访涉及回传字段对齐。

---

## 簇 2：Top-N 系列

```sql
/* Top-N 明细（如浏览器访问网页 top10000 / top 机型 / top 账号）
 * 参数：${dt} 日期 | ${dim} 维度(网址/机型/账号) | ${N} 取前N | ${period} 统计周期
 */
SELECT ${dim}                       AS item,
       COUNT(DISTINCT did)          AS uv,
       COUNT(*)                     AS pv
FROM <行为事实表>
WHERE dt BETWEEN date_add('${dt}', -${period}) AND '${dt}'
GROUP BY ${dim}
ORDER BY uv DESC
LIMIT ${N};
```

要点：大数据量 top10000 明细注意 presto OOM，参考 `data-analysis/pitfalls/Kyuubi-Presto取数踩坑.md`；机型 top 用于小说 SDK 扩量测算。

---

## 簇 3：实验对比留存系列

```sql
/* 实验组 vs 对照组 对比（消费/留存/收入）
 * 参数：${exp_id} 实验ID | ${start}~${end} 日期
 */
SELECT exp_group,                                   -- 实验组/对照组
       COUNT(DISTINCT did)                       AS uv,
       SUM(revenue)                              AS revenue,
       SUM(duration)/COUNT(DISTINCT did)         AS avg_duration,
       -- 次日留存 = 次日仍活跃设备 / 当日设备
       COUNT(DISTINCT CASE WHEN is_next_day_active=1 THEN did END)*1.0
         / COUNT(DISTINCT did)                   AS day2_retention
FROM <实验事实表>
WHERE dt BETWEEN '${start}' AND '${end}'
  AND exp_id = '${exp_id}'
GROUP BY exp_group;
```

要点：exp_id 分组口径与实验平台对齐；收入回收有延迟，留意数据回溯。

---

## 通用注意事项

- 引擎选择、`rlike→regexp_like` 改写、`count(distinct)→count(*)` 等价优化、按月分批：见 [../../data-analysis/methods/Kyuubi-Presto大数据量取数优化方法.md](../../data-analysis/methods/)
- 表结构与字段枚举：见 [../../data-analysis/sql/浏览器核心表字段字典.md](../../data-analysis/sql/浏览器核心表字段字典.md)
- 交付以飞书 sheet 明细为主，人工投入在口径澄清 + 结果回填，非写 SQL —— 正是 `nl-sql` 提效重点

## 待校准项

- 三簇各自的实际事实表全名与关键字段
- 小说 SDK 滚调/结算口径、复访口径
- 实验事实表的 exp_id / exp_group 字段与留存计算口径
