# 常见问题 + 已知问题

## Q：数字对不上 CP 侧日报（差 100 倍），怎么办？

十有八九是**查询口径**不同。按这个顺序排查：

1. **口径**：CP 侧看「在线池」（`online='1'` 且 `delete_reason` 为空），你可能跑了「全量存量」或「当日新增」。三者数字可能差 1-100 倍。见 [query_scope.md](query_scope.md)
2. **时间字段用错**：时间切片**只能**用 `create_time`（入库时间，毫秒 Unix）；`date` 是分区键不是入库时间，加 `date='20260429'` 类过滤会漏数或错数。日报主口径**不加任何时间过滤**（= 查全量）
3. **豁免**：CP 侧可能排除了 AIGC / PGC 账号，见 [exemptions.md](exemptions.md)

## Q：两次跑同一条 SQL 数字变了，哪个对？

都对。表是 upsert 型实时表，同一 `a_item_id` 被 CP 后续推送覆盖 —— 字段值会变，但 `total` 一般不变。以**当前快照**为准，报告必须标时间戳。

## Q：两个异常数字碰巧相同（例 dihui lead_author_name 空 4 条 + Rule 20 命中 4 条），是同一批数据吗？

**不一定**，碰巧同数字不代表同组数据。要核实必须反查具体 `a_item_id` 是否重叠：

```sql
SELECT a_item_id FROM ... WHERE lead_author_name IS NULL INTERSECT
SELECT a_item_id FROM ... WHERE lead_author_id IN (SELECT lead_author_id FROM bad_leads)
```

## Q：报告里要写"作者头像缺失"还是 `author_image` 字段为空？

**字段名直出**，业务含义放括号里。格式：`` `author_image`（作者头像）· 字段为空 ``。理由：报告要给 CP 对接人看，对接人要直接对齐 schema，业务释义作主干他们要反查。

## Q：`publish_time` 空但 `create_time` 有值算不算异常？

算。规则 3 严格版，`publish_time` 必填，`create_time` 不豁免。

**业务依据**（用户 2026-04-27 确认）：`publish_time` 是**端侧展示**的内容发布时间，用户直接看到。`create_time` 是入库时间（后台记录），不是用户感知字段。两者不能互相替代。

## Q：`date` 字段能用来做趋势分析吗？

**不能**。`date` 是分区键，业务上**不承载入库时间语义**，不用它做任何趋势（用户 2026-04-27 确认）。

日期维度聚合统一用 `create_time`（毫秒级时间戳，入库时间）：

```sql
-- 正确
GROUP BY from_unixtime(cast(create_time as bigint) / 1000, 'yyyy-MM-dd')

-- 错误（曾经用过，2026-04-25 被用户纠正）
GROUP BY date
```

## Q：日报某天数字突然降低 ~18%，是新规则太宽松了吗？

**不是新规则**，是 **2026-05-26 起 stock 趋势 + 健康卡 + 主校验切到了在线池口径**。

切换前后对比：

| 卡片/曲线 | 5/25 全量含下线 | 5/26 在线池 |
|---|---|---|
| 健康卡总条数 | 244,059 | 199,826 |
| beike author_image_n（最新 cutoff） | 44,718 | 42,336 |
| guoying（同上） | 121,354 | 119,090 |

差额来自下线池里的旧异常（如 dihui 5 月初的历史 860 个 multi_xm 都在下线池）。**改后数字与日常推 CP 群的"在线 item 清单"完全一致**。

如果要看含下线的历史趋势数字，跑 ad-hoc：
```sql
SELECT a_cp, COUNT(*) FROM ... WHERE a_cp = '...' [无 online 过滤]
```
但日报本身不再展示。

## Q：日报里 c3~c6 趋势新增的"cp_author 多 xm"和"lead 多 cp_author"是什么？

**2026-05-26 新加的两条三元 ID 一致性曲线**，来自 [chart_id_consistency_trend.sql](../../scripts/validate/chart_id_consistency_trend.sql)：

| 字段 | 含义 |
|---|---|
| `cp_author 多 xm` | 当前在线池里、旗下 ≥2 个 `xm_author_id` 的 `author_id` 数（双小米 ID 残留） |
| `lead 多 cp_author` | 当前在线池里、旗下 ≥2 个 `author_id` 的 `lead_author_id` 数（人格分裂） |

阈值是"clean = total"严格 1:1:1，任何 ≥2 都算异常。豁免按 item_id 注入。

**典型异常清单**（5/26 实测）：
- beike: 8 个 cp_author（武备科普、主持人郝韵 等历史批次）
- dihui: 0（狐友星闻社 d6797b3a item 已豁免）
- guoying: 5 个 lead（廖乙又、即录、羊丢丢、董子涵、jen妮——每家都是 1 条 1 cp 旁支）
- meilaoban: 0

## Q：日报 stock 累计趋势某天突然上涨几十/几百条，是新内容质量出问题了吗？

**多半不是**。先用 `create_time` 按入库时间维度复核：

```sql
-- 真新内容异常（按 create_time 分日）
SELECT date_format(from_unixtime(CAST(create_time AS BIGINT)/1000), '%Y-%m-%d') AS d,
       SUM(CASE WHEN author_image IS NULL OR author_image = '' OR LOWER(author_image) = 'null' THEN 1 ELSE 0 END) AS image_empty
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE a_cp = 'cn-beike-djy' AND online = '1' AND ...
GROUP BY 1 ORDER BY 1 DESC
```

如果 create_time 维度上的当日异常 ≈ 0，但 stock 日报曲线仍上涨，那是 **CP 重推老内容并把字段置空**：upsert 表 `date` 分区会被更新到最新推送日，让历史 item 在 stock 累计里"重新出现"。

2026-05-25 起 `chart_stock_trend.sql` 已切到 `from_unixtime(create_time) <= cutoff` 口径，这种污染已规避；如果在更老的日报截图里看到此现象，属于切换前历史数据，不要按"新异常"对待。具体定位重推内容用按 `date` 分区拉清单的 ad-hoc SQL（不是日报趋势图）。

## Q：detail 模式跑完但 `$DJY_OUTPUT_ROOT/dirty/` 没文件？

大概率漏做 Python 转换步骤。`data-sql` 对多列 SELECT **不会自动保存 CSV**，只对 GROUP BY 聚合保存。两步走：

1. SQL 用 `CONCAT_WS(CHR(1), col1, col2, ...)` 合成单列 → `run_validate_sql.py` 会让 data-sql 把 CSV 落到 `$DJY_OUTPUT_ROOT/tmp/`（默认 `~/Desktop/ai_djy_pool_analysis/tmp/`）
2. 用 `scripts/export_to_csv.py` 把 `tmp/data_*.csv` 转为标准多列 CSV，dst 传文件名会自动落到 `$DJY_OUTPUT_ROOT/dirty/`

## Q：adhoc 模式发现新字段有问题，怎么入规则库？

1. 跑 adhoc 确认命中率和量级
2. 更新 [rules.md](rules.md) 加新规则条目
3. 更新 [`scripts/template_a_stock.sql`](../scripts/template_a_stock.sql) 加对应 `SUM(CASE WHEN ...)`
4. 更新 [rules.md](rules.md) 的字段映射表新加一行

## 已知 CP 侧业务问题（持续跟踪）

### dihui：`video_duration` 数值合理性（**已升级规则 15**）

- 2026-04-22 adhoc 发现：dihui 视频类 50-60%（约 6,073 条）`video_duration = 0` 或负数
- 属 dihui 侧推送 bug
- **决定**（2026-04-28 用户改判，覆盖 04-27 的"暂不升级"决定）：规则 15 升级为"非空 AND > 0"，值=0 或负数也告警
- 实测：dihui 当前 3,106 条 `video_duration = '0'`（升级后纳入日报告警）

### dihui：`author_image` 长期未清零（2026-04-13 ~ 至今）

- 全量存量 5 万条左右，每日上下波动（最低 504，最高 24,045）
- 一周内多次暴涨：04-17 达 24,045 条、04-22 达 16,870 条
- 曾经推动 CP 修复过 `url` / `image` / `firstImg`（几小时内从千级降到个位数），但 `author_image` 是硬骨头
- 根因未定位，建议专项追问

### beike：`author_image` 长期高位（22%）

- 全量存量 38,827 条空，占 beike 总量 22%
- 持续一周以上，beike 对接人未响应

### beike：`publish_time` 偶发大规模爆炸

- 04-17 单日 `publish_time` 空率曾达 51.7%（1,066 条），其他日期稳态 <1%
- 建议排查 beike 推送管道是否偶发字段丢失
