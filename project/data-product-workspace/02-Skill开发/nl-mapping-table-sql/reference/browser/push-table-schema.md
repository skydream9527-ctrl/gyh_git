# Browser Push - 底表表结构 & 维度 & 关联模式

> **业务域**：浏览器 Push（推送）
> **数据层级**：底表/宽表（dwd/dwm/回调日志层），非预聚合中间表
> **核心底表**：`hive_zjyprc_hadoop.browser.push_callback_log`（每行一次 Push 回调事件）
> **时间分区字段**：`date`（INT，格式 YYYYMMDD）
> **用户ID字段**：`deviceid`（回调日志中；关联用户画像/分层表时对应 `did` / `userid`）

> [!IMPORTANT]
> **日期写法（强制）**：分区字段 `date` 为 INT，**必须用不带引号的整型**（`date = 20260628` / `date BETWEEN 20260601 AND 20260628`）。
> 带引号的 `'20260628'` 会导致分区裁剪失效、全表历史扫描、查询超时。

---

## 一、源表速查

| 表 | 全名 | 用途 |
|----|------|------|
| Push回调日志表 | `hive_zjyprc_hadoop.browser.push_callback_log` | 核心底表，送达(EXPOSE)/点击(CLICK)回调 |
| 审出池表 | `hive_zjyprc_hadoop.browser.dwd_push_content_pool_daily_df` | 物料属性/分类/时效性（增量快照表） |
| Push引入物料池 | `hive_zjyprc_hadoop.browser.dwd_push_content_pool_di` | 物料候选池（漏斗第一层、含 title/summary/url/category） |
| 推送物料画像表 | `hive_zjyprc_hadoop.browser.dwd_push_item_profile` | 物料标题/分类/质量分/历史统计 |
| 真实送达表 | `iceberg_zjyprc_hadoop.browser.dwd_push_real_expose_dt` | 真实曝光（屏幕真实展示，约80%设备覆盖） |
| 支持真实送达设备表 | `iceberg_zjyprc_hadoop.push.dwd_xmpush_expose_device_di` | 筛出支持真实送达打点的设备 |
| 推送点击行为表 | `hive_zjyprc_hadoop.browser.browser_push_click_info` | 点击行为明细 |
| 推送任务日志表 | `hive_zjyprc_hadoop.browser.m_push_common_log_di` | 任务级日志（下发数 sendNum / 物料列表 / 扩量任务） |
| 物料体裁表 | `paimon_zjyprc_hadoop.browser.dm_push_ai_common_feature_item_df` | 体裁 c_type：VIDEO/NEWS/MINIVIDEO |
| Push会话消费统计表 | `iceberg_zjyprc_hadoop.browser.dwm_browser_push_open_session_consum_di` | 会话时长（单位**分钟**） |
| 流内行为宽表(都江堰Label) | `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di` | Push点击后流内消费时长（单位**毫秒**） |
| 通知开关表 | `hive_zjyprc_hadoop.push.dwd_browser_notify_switch_df` | 通知栏开关状态（静态/动态关闭率） |
| Push用户分层表 | `hive_zjyprc_hadoop.browser.dwd_push_user_level_browser_df` | 重度/中度/轻度分层 |
| Push用户画像特征表 | `iceberg_zjyprc_hadoop.browser.dm_push_ai_user_profile_feature_did_df_v1` | 年龄/性别/城市/机型/兴趣/自建火山分组（T-2） |

> **app_id 约定**：浏览器 Push 在真实送达表 / 通知开关表中 `app_id = 1000274`。

---

## 二、核心底表：push_callback_log

**Database**: `hive_zjyprc_hadoop.browser`
**粒度**: 每行一次 Push 回调事件

| Column | Type | 说明 |
|--------|------|------|
| deviceid | varchar | 设备ID（去重维度，对应画像表的 did/userid） |
| reachitems | array(row(...)) | 回调明细数组，**取首元素 `reachItems[0]`** |
| source | smallint | 来源 |
| extra | varchar | 扩展字段（JSON），如 `get_json_object(extra,'$.errorCode')` |
| servertime | bigint | 服务端时间戳（毫秒），分时段分析用 |
| date | integer | 分区字段（YYYYMMDD） |

**`reachItems[0]` 结构体字段**：

| 字段 | 说明 |
|------|------|
| `reachItems[0].type` | 事件类型：`EXPOSE`(送达) / `CLICK`(点击) |
| `reachItems[0].ext` | 即 pushId，类型前缀区分 Push 类型（见维度章节） |
| `reachItems[0].stockId` | 物料ID（关联审出池/体裁表的 key） |
| `reachItems[0].reachtime` | 触达时间戳 |
| `reachItems[0].position` | 通知栏位置索引（从0开始） |
| `reachItems[0].pushtype` | 推送策略类型 |
| `reachItems[0].expid` | 实验ID |
| `reachItems[0].itemtype` / `itemcategory` | 物料体裁 / 分类（结构体内自带，部分场景可用） |
| `reachItems[0].duration` | 时长 |

> [!WARNING]
> **PV/UV 去重口径（强制）**：送达/点击**不能直接 SUM**，必须用 `COUNT(DISTINCT ...)`：
> - **PV** 去重维度 = `(deviceid, reachItems[0].ext)` → `COUNT(DISTINCT CASE WHEN ... THEN (deviceid, reachItems[0].ext) END)`
> - **UV** 去重维度 = `deviceid` → `COUNT(DISTINCT CASE WHEN ... THEN deviceid END)`
>
> **通用必带过滤**：`reachItems[0].type IN ('EXPOSE','CLICK') AND deviceid IS NOT NULL AND reachItems[0].stockId IS NOT NULL AND reachItems[0].stockId != ''`

**通用可选过滤片段**（按分析需要启用）：

```sql
-- 剔除早晚报
AND reachItems[0].ext NOT LIKE 'RPT%'
-- 剔除试探
AND reachItems[0].ext NOT LIKE '93%' AND reachItems[0].ext NOT LIKE '32%' AND reachItems[0].ext NOT LIKE '31%'
```

---

## 三、维度（dimension）

### DIM-EXPID：实验分组

- **字段**：`reachItems[0].expid`（varchar，直接来自回调日志，无需解析）
- **过滤**：`WHERE reachItems[0].expid IN ('1304128','1304129')`
- **注意**：多实验并存时按 expid 过滤，不同实验流量不叠加分析。

### DIM-PUSHTYPE：Push 类型（pushId 前缀）

- **字段**：`reachItems[0].ext`（即 pushId）
- **分组写法**：

```sql
CASE
    WHEN reachItems[0].ext LIKE 'RPT%'                                          THEN 'AI早晚报'
    WHEN reachItems[0].ext LIKE 'BA%'                                           THEN '主动智能通发'
    WHEN reachItems[0].ext LIKE 'PD%' OR reachItems[0].ext LIKE 'PDF%'
      OR reachItems[0].ext LIKE 'SOF%'                                          THEN '主动智能补发'
    WHEN reachItems[0].ext LIKE '93%' AND reachItems[0].ext LIKE '%MUSTPH'      THEN '全局试探'
    WHEN reachItems[0].ext LIKE '93%'                                           THEN '地域试探'
    WHEN reachItems[0].ext LIKE '32%'                                           THEN '一级分类试探'
    WHEN reachItems[0].ext LIKE '31%'                                           THEN '二级分类试探'
    WHEN reachItems[0].ext LIKE '81%'                                           THEN '即刻'
    WHEN reachItems[0].ext LIKE '80%'                                           THEN '策略服务'
END AS push_type
```

- **常用过滤**：
  - 只看主动智能：`AND (reachItems[0].ext LIKE 'BA%' OR reachItems[0].ext LIKE 'PD%' OR reachItems[0].ext LIKE 'SO%')`
  - 只看试探：`AND (reachItems[0].ext LIKE '93%' OR reachItems[0].ext LIKE '32%' OR reachItems[0].ext LIKE '31%')`

### DIM-QUEUE：物料来源队列（audit_queue_name）

- **字段**：`get_json_object(item, '$.ext.audit_queue_name')`（派生，JOIN 审出池表 `dwd_push_content_pool_daily_df`）
- **核心取值**：`hot_report`(热门资讯/全局热榜) / `hot_report_vertical`(垂类热榜)
- **过滤**：`WHERE audit_queue_name = 'hot_report'`

### DIM-CTYPE：物料体裁（c_type）

- **字段**：`c_type`（来自 `paimon_zjyprc_hadoop.browser.dm_push_ai_common_feature_item_df`，通过 `item_id` 关联）
- **取值**：`VIDEO` / `NEWS` / `MINIVIDEO`
- **注意**：体裁表往前多取 2 天覆盖内容池延迟；**禁止**用 `iceberg_zjyprc_hadoop.browser.hot_content_pool_understand_result_iceberg` 取体裁。

### DIM-PUSHLEVEL：Push 用户分层（push_level）

- **来源**：`hive_zjyprc_hadoop.browser.dwd_push_user_level_browser_df`（key=`userid` 对应 `deviceid`，date 取行为 `start_date - 2`）
- **分组写法**：

```sql
CASE
    WHEN ul.push_click_days_in1week >= 2 OR ul.push_click_days_in1month >= 5  THEN '重度'
    WHEN ul.push_click_days_in1week = 0 AND ul.push_click_days_in1month <= 2  THEN '轻度'
    ELSE '中度'
END AS push_level
```

- **注意**：必须加 `ul.push_expose_pv_month > 0` 过滤，否则会关联到从未收到 Push 的用户。

### DIM-RFM：信息流 RFM 分层

- **推荐表**：`iceberg_zjyprc_hadoop.browser.dim_browser_content_flow_rfm_user_di`（数据小，分层直观）
- **字段**：`layer`（中文：0消费用户 / 流失预警 / 轻度消费 / 潜力成长 / 中度忠诚 / 重度忠诚）
- **关联**：`ON push_log.deviceid = rfm.did AND rfm.date = ${date} - 2`（T-2）
- **过滤**：流内重度 `WHERE layer IN ('潜力成长','中度忠诚','重度忠诚')`

### DIM-PROFILE：用户基础属性画像

- **表**：`iceberg_zjyprc_hadoop.browser.dm_push_ai_user_profile_feature_did_df_v1`（key=`did`，**T-2** 更新）
- **核心字段**：

| 字段 | 说明 | 常用取值 |
|------|------|---------|
| `user_age_6_level` | 年龄6分段 | 1=0-17、2=18-24、3=25-30、4=31-40、5=41-50、6=50+ |
| `user_sex` | 性别 | 1=男、2=女、null=未知 |
| `curr_city_type` | 城市等级 | 1=一线…5=五线、6=新一线 |
| `phone_brand` | 手机品牌 | 2=小米、1=红米、3=黑鲨 |
| `user_source_type` | 内容来源分组 | 1=自建、2=火山、0=未知 |
| `feeds_rfm_category` | 信息流RFM | 0=未访问…6=重度忠诚 |
| `user_level_tag` | 用户调性 | 1=高端、2=中层、3=低端 |

- 兴趣标签：`interest_finance_level` / `interest_ecom_level` / `interest_game_level` / `interest_video_level` / `interest_read_level` 等（level 类型）。

---

## 四、关联模式（join_pattern）

> 所有画像/分层/RFM 表均为 **T-2** 口径（date = 行为日期 - 2）。

### JOIN-1：push_callback_log × 审出物料池（打物料来源队列标签）

```sql
LEFT JOIN hive_zjyprc_hadoop.browser.dwd_push_content_pool_daily_df cp
    ON push_log.date    = cp.date
    AND push_log.stockid = get_json_object(get_json_object(cp.item, '$.pushItemModels[0]'), '$.itemId')
    AND cp.appname       = 'browser'
```

> 审出池是**增量快照表**，`pool.date` = 审核入池日期 ≠ 下发日期；跨天关联用 `pool.date BETWEEN start_date-2 AND end_date` 覆盖延迟。

### JOIN-2：push_callback_log × 物料体裁表（打 c_type 标签）

```sql
LEFT JOIN paimon_zjyprc_hadoop.browser.dm_push_ai_common_feature_item_df ic
    ON push_log.stockid = ic.item_id
    AND ic.date BETWEEN ${start_date} - 2 AND ${end_date}   -- 往前多取2天覆盖延迟
```

### JOIN-3：push_log（去重后）× Push session 时长表

```sql
-- 必须先把 push_log 去重到 (date, expid, deviceid) 再 JOIN，否则 item_group 多行导致时长重复计数
LEFT JOIN iceberg_zjyprc_hadoop.browser.dwm_browser_push_open_session_consum_di dur
    ON push_did.deviceid = dur.did AND push_did.date = dur.date
```

> `consum_dura` 单位为**分钟**；`session_type` 区分 `push点击session` / `push点击详情页`。

### JOIN-4：push_log × 流内行为宽表（Push 点击后消费时长）

```sql
-- 方式A：仅 Push 入口消费（落地页+沉浸流）
LEFT JOIN iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di fd
    ON push_log.did = fd.did AND push_log.date = fd.date
    AND fd.feed_channel = 'push' AND fd.is_app_dau_2024 = 1 AND fd.is_top = 0
```

> 此表 `consum_dura` 单位为**毫秒**（/60000 转分钟），与 session 表（分钟）**不可混合求和**。流内消费/有效用户口径详见 `reference/browser-feed/dujiangyan-metrics-reference.md`。

### JOIN-5：push_callback_log × Push 用户分层

```sql
LEFT JOIN hive_zjyprc_hadoop.browser.dwd_push_user_level_browser_df ul
    ON push_log.deviceid = ul.userid
    AND ul.date = ${start_date} - 2 AND ul.appname = 'browser'
    AND ul.push_expose_pv_month > 0
```

### JOIN-6：push_callback_log × 用户画像特征表

```sql
LEFT JOIN iceberg_zjyprc_hadoop.browser.dm_push_ai_user_profile_feature_did_df_v1 up
    ON push_log.deviceid = up.did
    AND up.date = ${start_date} - 2   -- T-2
```

---

## 五、关键注意事项

1. **PV/UV 去重**：送达/点击必须 `COUNT(DISTINCT ...)`，PV 维度 `(deviceid, pushId)`，UV 维度 `deviceid`；不能直接 SUM。
2. **JSON 字段**：审出池 `item`、画像 `pushmodel`/`pushitemstat` 均为 STRING(JSON)，必须用 `get_json_object()` 解析，不能用点号。
3. **审出池增量表**：`pool.date` = 审核入池日期 ≠ 下发日期。
4. **T-2 规则**：关联用户分层/画像/RFM 表时 date 取行为日期 - 2。
5. **真实送达**：仅覆盖约 80% 设备，需先关联 `dwd_xmpush_expose_device_di` 筛出支持设备；送达→真实曝光差距约 20-30%。
6. **单位差异**：session 时长表 `consum_dura` = 分钟；流内 Label 表 `consum_dura` = 毫秒。
7. **"曝光"歧义**：推送侧"曝光"=送达(EXPOSE)；信息流侧=内容卡片展示；物料画像侧=历史累计送达量。
8. **日期整型**：分区 `date` 用不带引号的整型，避免分区裁剪失效。
