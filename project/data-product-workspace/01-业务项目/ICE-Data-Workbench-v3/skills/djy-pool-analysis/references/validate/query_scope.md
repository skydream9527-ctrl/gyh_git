# 查询口径 + 表特性 + 缓存规则

## 表特性（关键背景）

- **表名**：`paimon_zjyprc_hadoop.browser.business_content_pool_realtime`
- **`date` 字段**：格式 `YYYYMMDD`（如 `'20260423'`），**分区键**。**业务不用它做任何趋势**（用户 2026-04-27 确认）。趋势聚合必须用 `create_time`
- **`create_time` 字段**：毫秒级 Unix 时间戳，是**真正的入库时间**（用户 2026-04-25 确认）。做 7 天 / 日 / 周趋势统一用它
- **`publish_time` 字段**：端侧展示的发布时间，严格版校验（`create_time` 有值不豁免），见规则 3
- **upsert 型实时表，非追加型**：同一 `a_item_id` 会被 CP 后续推送覆盖更新（字段值会变）

### upsert 特性的直接影响

- 同一 SQL 前后两次跑**结果可能不同**（字段从空 → 有值属正常更新）
- 报告必须标注「数据采集时点」，告警用"当前快照"表达
- 抽样 `a_item_id` 做静态核查 **不可靠**（可能已被修复覆盖）
- 推 CP 时**不要**附 item_id 固定清单，附"当前快照 CSV"并说明"以 CP 推送状态为准"

### 实证（2026-04-23 上午）

dihui `lead_author_name_n` 上午 11:00 报 4 条，12:00 核查变 0 条，`total` 完全不变 —— 同 item_id 的字段在 CP 侧被补值。

## 查询口径本质：都是 WHERE 条件组合

所有"口径"都跑同一张表 `business_content_pool_realtime`、同一种字段空/异常校验 SQL，**差别只在 WHERE 条件**。不涉及快照、不需要存档、每次实时跑。

### 三组互相独立的过滤条件

| 条件维度 | 可选值 | 意义 |
|---|---|---|
| **时间过滤** | 1. 不加 → 全量入库数据 <br> 2. `create_time` 限今日 → 当日新入库 <br> 3. `create_time BETWEEN a AND b` → 某段入库 | 决定**看哪批 item** |
| **在线过滤** | 1. 不加 → 含下线内容 <br> 2. `online='1' AND (delete_reason IS NULL OR delete_reason='')` → 仅端上可见 | 决定**是否剔除已删内容** |
| **CP 过滤** | `a_cp IN (...)` | 固定这套 4 家白名单 |

### 常见口径（上面三组的组合）

| 业务称呼 | 组合 | 用途 |
|---|---|---|
| **全量存量**（日报主口径） | 时间不加 · 在线不加 | 主报告，看**当前池子整体字段质量**（历史 + 新入库的当前字段值） |
| **当日新增（增量）** | `create_time` 限今日 · 在线不加 | 监控 CP 当日推送 bug |
| **在线池** | 时间不加 · `online='1'` | 对齐 CP 侧口径，看**端上可见的字段质量** |
| **缺失日切片**（日报补发用） | `create_time` 限那几天 · 在线不加 | 恢复日分析电脑关机错过的日期 |

⚠️ **`date` 字段不要用作时间过滤**。`date` 是分区键（入库日），不是入库时间；也不是"当日更新日"。曾经用过 `date = '今日'` 误报 dihui `author_image` 504 条、而真实在线池 51,406 条，100 倍差异。入库时间过滤**只能用 `create_time`**。

### 在线池 vs 全量存量

CP 侧日报通常口径更细：**在线池**（`online = '1'` 且 `delete_reason` 为空），只看**当前推荐可见**的内容。

```sql
WHERE a_cp = '{{CP}}'
  AND online = '1'
  AND (delete_reason IS NULL OR delete_reason = '')
```

差异示例（2026-04-23 实测 dihui）：

| 口径 | total | `author_image` 空 | `image` 空 | `url` 非 http | `firstImg` 缺失 |
|---|---|---|---|---|---|
| 全量存量 | 255,284 | 51,862 | 25 | 3 | 18 |
| 已标记删除 | 22,484 | 3,670 | 25 | 3 | 18 |
| **在线池** | **232,924** | **48,171** | **0** | **0** | **0** |

→ `image` / `url` / `firstImg` 三项在已删内容里有残留，但**在线池已清零**。对齐 CP 侧日报必须走在线池口径。

### 日期过滤的误用历史

曾默认按 `date='今日'` 查，导致 dihui `author_image` 只报 504 条，而用户在线池数字是 51,406 条，差异 100 倍。**根因**：`date` 是分区键，不是入库时间；字段值后续被 CP 覆盖也不反映到 `date`。做时间切片**只能**用 `create_time`，日报主口径**不加时间过滤**（查全量）。

### 2026-05-25：stock 累计趋势从 `date` 切到 `create_time`

`chart_stock_trend.sql`（图二 + 图三~六）原本用 `WHERE date <= cutoff` 实现 7 天累计，但 paimon upsert 表的 `date` 字段会随 CP 重推被更新到最新推送日。CP 5/22-5/25 持续重推 4/29 老内容并把 `author_image` 字段置空，导致 stock 累计 +597（5/21→5/25）；同期按 `create_time` 看真新内容 0 异常。

**切换后**：`AND from_unixtime(CAST(create_time AS BIGINT) / 1000, 'yyyy-MM-dd') <= '{{CUTOFF_ISO_N}}'`，与图一 daily 增量曲线口径对齐。详见 [daily_report.md](daily_report.md#2026-05-25-stock-累计口径切换) 与 [faq.md](faq.md)。

### 2026-05-26：c2~c6 + 健康卡 + template_a 切到在线池口径

继 5/25 的 create_time 切换之后，**日报异常面板的口径再降一档**：

| SQL / 区域 | 改动 |
|---|---|
| `template_a_stock.sql`（4 段式主校验） | WHERE 加 `online='1' AND (delete_reason IS NULL OR delete_reason = '')` |
| `chart_stock_trend.sql`（c2 + c3~c6） | 7 个 UNION 分支同上 |
| 内容池健康度卡（"当前异常字段总条数"）| 自动跟着 chart_stock_trend.sql 切到在线池数字 |
| `chart_daily_trend.sql`（c1 入库量） | **不动**，全量入库才能反映 CP 推送节奏 |
| `chart_id_consistency_trend.sql`（新增）| 三元 ID 一致性，原生在线池口径 |

**为什么改**：之前全量含下线时，下线池里历史残留异常（如 dihui 历史 860 个 multi_xm 残留）会拉高卡片合计 244K，与日常推 CP 群"在线 item 清单"口径不一致，给业务方造成困扰。改后所有数字（健康卡 + c2~c6 + 主校验 + 推 CP 清单）口径统一。

**与历史不可比**：5/26 前后曲线/数字断裂，约下降 18%（244K → 200K）。

## 量级参考（2026-04-23 实测）

| CP | 全量存量 | 当日新增 |
|---|---|---|
| dihui | ~25 万 | ~4 千 |
| beike | ~17.7 万 | ~1 千 |
| guoying | ~70 万 | ~1 万 |
| meilaoban | ~6.7 万 | 个位数 |

## 🚫 禁用缓存铁律

**每次调用必须真实跑 SQL**，不允许凭会话上下文/历史结果合成报表。

理由：
- `business_content_pool_realtime` 是实时表，同一天不同时间点数据会变
- 结论要有可追溯的执行记录，用户随时可以复核
- 缓存复用容易遗漏新异常或错误复用旧数据

**例外**：规则库文档、字段映射、CP 白名单 —— 这些是配置，不是数据。

**对应的报告表述**：同一会话多次刷新时，用 `X（11:00 快照）→ Y（14:00 快照）` 的对比格式，不用"今日"模糊表达。
