# 信息流双端概念说明

> **信息流双端** = **浏览器信息流（BF）** + **内容中心（CC）** 两条业务线的信息流子域合并视角。
> 用于跨端对比、双端合计、自建 vs 火山在双端的统一口径评估。

---

## 一、为什么需要"双端"概念

浏览器信息流（BF）和内容中心（CC）各自有独立的信息流消费场景，但业务上常需要：

1. **双端合计**：看"信息流整体"有效用户 / 时长 / VV，两端各自按本端口径算出后**直接加总**（不去重）。
2. **跨端对比**：同一指标在 BF 与 CC 的表现差异，定位哪端在波动。
3. **自建 vs 火山（仅 BF 端）**：BF 端有都江堰实验（自建组 / 火山组），CC 端无此拆分；双端对比时 BF 可细分到自建/火山，CC 只给整体。

---

## 二、双端有效用户口径

"有效用户"在双端的定义**不一致**，必须分别按各端口径判定，不能跨端直接相加标识：

| 端 | 数据源 | 有效用户判定 |
|----|--------|-------------|
| **BF 浏览器信息流** | `iceberg_zjyprc_hadoop.browser.dwm_djy_dau_user_consum_index_di_copy`（都江堰专用宽表，含预计算 `exp_group`） | `date < 20260306`：`expose_cnt>0 OR consum_cnt_v2>0`；`date >= 20260306`：`is_vliad_user_new='是'`（滑动埋点全量后切新口径） |
| **CC 内容中心** | `iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di` | 有列表页曝光（`item_position>=4 OR ad_position>4` 的 `ad_expose_cnt+expos_cnt`）或消费（`consum_cnt>0`） |

> ⚠️ **双端合计 = 两端分别算后直接加总（不去重）**：BF 与 CC 的 did 命名空间可能重叠，本口径不做去重，直接把两端的 DAU / VV / 时长相加。如需精确去重，需 UNION 两端 did 后再 COUNT DISTINCT（性能开销大，通常按业务接受不去重）。

---

## 三、双端指标对照

> **双端合计规则**：DAU / VV / 时长均**两端各自按本端口径算出，然后直接加总**（不去重）。人均有效时长 = 双端总有效时长加总 / 双端有效 DAU 加总。

| 指标 | BF 端 | CC 端 | 双端合计 |
|------|-------|-------|---------|
| 有效用户 DAU | 自建组 DAU / 火山组 DAU | 有效用户 UV | BF DAU + CC DAU（直接加总，不去重） |
| 有效用户 VV | `consum_cnt_v2` 直接求和（无需内联） | `sum(consum_cnt)` 限有效用户 | BF VV + CC VV（直接加总） |
| 有效用户时长 | 列表页时长 + 处理后消费时长 | **信息流时长 `feed_dura`（不含消费时长）** | BF 时长 + CC 时长（直接加总；注意 BF 含消费时长、CC 不含） |
| 人均有效时长 | 有效时长 / 有效 DAU | 有效时长 / 有效 DAU | 双端总有效时长加总 / 双端有效 DAU 加总（不直接除两端人均） |

---

## 四、自建 vs 火山（仅 BF 端）

BF 端的都江堰实验通过 `exp_group` 字段预分为：

- `36%自建组`（exp_id 含 `1566672`）
- `36%火山组`（exp_id 含 `1566673`）
- `自建反转组`（exp_id 含 `1960891`）
- `火山反转组`（exp_id 含 `1960892`）

双端对比时，BF 端可细分到自建/火山，CC 端只给整体。常见对比指标：

- 自建信息流有效人均时长（分钟）= 自建有效时长 / 自建有效 DAU
- 自建信息流有效时长达火山 = 自建有效时长 / 火山有效时长

---

## 五、参考文件

| 文件 | 内容 |
|------|------|
| `reference/feed-dual-end/concept.md` | 本文件，信息流双端概念说明 |
| `reference/feed-dual-end/valid-user-metrics-reference.md` | 双端有效用户 DAU / VV / 时长 SQL 口径 |
| `reference/browser-feed/dujiangyan-metrics-reference.md` | BF 端都江堰全量指标（基于 Label 宽表 `dwm_browser_event_aggregation_label_di`） |
| `reference/content-center/raw-core-metrics-reference.md` | CC 端底表全量核心指标 |

> **BF 端两张表的选择**：
> - `dwm_djy_dau_user_consum_index_di_copy`：都江堰专用宽表，含预计算 `exp_group`，**自建/火山对比、有效用户（is_vliad_user_new 口径）优先用此表**。
> - `dwm_browser_event_aggregation_label_di`：Label 宽表，维度更全（含 push/profile 等），**非自建/火山对比、或需更多维度时用此表**。
