# Browser Feed 都江堰 - 信息流核心指标 SQL 口径（Label 宽表）

> **业务域**：浏览器信息流 / 都江堰（自建信息流算法场景）
> **数据层级**：底表/宽表（dwm/dwd 层）
> **核心宽表**：`iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`（Label 宽表，user-day 粒度）
> **适用场景**：信息流有效用户 / 有效时长 / 消费 / 多体裁（小说·短故事）等"都江堰口径"指标，中间表 `dm_*` 不支持时使用。

> [!IMPORTANT]
> 1. **日期整型**：`date = 20260628` / `date BETWEEN 20260601 AND 20260628`，不要加引号（避免分区裁剪失效）。
> 2. **时长单位**：`feed_dura` / `consum_dura` 单位为**毫秒**，输出分钟需 `/60000`。
> 3. **有效用户为硬性标识**：基于用户整体行为判定，不能通过灵活维度筛选排除某类用户。

---

## 一、标准限制（所有都江堰口径默认带）

```sql
WHERE date = ${date}
  AND is_app_dau_2024 = 1                       -- 浏览器活跃用户
  AND is_top = 0                                -- 非置顶内容
  AND (feed_channel IN ('热点','推荐','profile','profile_djy','push')   -- 双频道+作者列表(自建/火山)+push
       OR item_type IN ('novel','shortstory'))  -- 小说/短故事无频道信息，单独兼容
```

**自建 / 火山实验分组（exp_id）**：

```sql
CASE
    WHEN exp_id LIKE '%1566672%' THEN '36%自建组'
    WHEN exp_id LIKE '%1566673%' THEN '36%火山组'
    WHEN exp_id LIKE '%1960891%' THEN '自建反转组'
    WHEN exp_id LIKE '%1960892%' THEN '火山反转组'
    ELSE '其他'
END AS exp_group
-- 限制 36%+4% 流量：AND (exp_id RLIKE '1566672' OR exp_id RLIKE '1566673' OR exp_id RLIKE '1960891' OR exp_id RLIKE '1960892')
```

> [!WARNING]
> **"处理后的消费VV / 消费时长"（强制内联处理）**
> Label 表 `consum_cnt_v2` / `consum_dura` 为**原始字段**。计算消费、有效用户、信息流DAU时，**小说/短故事必须按 read_source 内联处理**，不可直接用 `consum_cnt_v2 > 0`。处理表达式（下文记为 `<处理后消费VV>` / `<处理后消费时长>`）：

```sql
-- <处理后消费VV>：把 consum_dura 换成 consum_cnt_v2 即为 <处理后消费时长>
SUM(IF(
    coalesce(item_type,'') NOT IN ('novel','shortstory')                                                    -- 非小说短故事
    OR (item_type = 'novel'      AND (read_source IN ('rec','topnews')
        OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))                            -- 小说：首访+续读
    OR (item_type = 'shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
        OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown')))) -- 短故事：首访+续读
    , consum_cnt_v2, 0))
```

---

## 二、核心指标（Core Metrics）

### DJY-001: 有效用户DAU（新口径·滑动埋点）

> 在热点/推荐列表页有滑动行为(`is_feed_sliding='true'`)，或有内容消费的用户数。`content_duration` 滑动埋点于 20.12+ 版本全量。

```sql
SELECT  date,
        COUNT(DISTINCT IF(
            (feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND is_feed_sliding = 'true')  -- 列表页有滑动
            OR consum_cnt_v2 > 0                                                                                              -- 有消费
        , did, NULL)) AS valid_user_dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

> **不含 PUSH**：把消费条件替换为 `(CASE WHEN coalesce(feed_channel,'') != 'push' THEN consum_cnt_v2 END) > 0`。
> **有效用户DAU = 仅滑动(无消费)UV + 消费UV**；人均有效时长 = 总有效时长 / 有效用户DAU。

### DJY-002: 总有效时长（分钟）

> 有效用户的双频道列表页信息流时长 + 整体消费时长。先判定有效用户再计列表页时长（无下滑的消费用户列表页时长也计入）。

```sql
SELECT  date,
        SUM(CASE WHEN feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') THEN feed_dura END) / 60000  -- 列表页信息流时长
        + SUM(consum_dura) / 60000                                                                                                    -- 消费时长
            AS total_valid_dur_min
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

> **不含 PUSH**：消费时长部分替换为 `SUM(CASE WHEN coalesce(feed_channel,'') != 'push' THEN consum_dura END)/60000`。

### DJY-003: 消费UV

> 在信息流中有图文浏览、短视频/小视频播放、小说/短故事阅读、短剧/直播观看等行为的用户数。

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN consum_cnt_v2 > 0 THEN did END) AS consum_uv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

### DJY-004: 消费时长 / 消费VV（含多体裁内联处理）

> 消费时长（分钟）与消费次数。小说/短故事按 read_source 内联处理（见标准限制中的"处理后消费"）。

```sql
SELECT  date,
        SUM(IF(
            coalesce(item_type,'') NOT IN ('novel','shortstory')
            OR (item_type = 'novel'      AND (read_source IN ('rec','topnews')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
            OR (item_type = 'shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
            , consum_dura, 0)) / 60000 AS consum_dur_min,
        SUM(IF(
            coalesce(item_type,'') NOT IN ('novel','shortstory')
            OR (item_type = 'novel'      AND (read_source IN ('rec','topnews')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews'))))
            OR (item_type = 'shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
                OR (read_source IN ('feed_continue_view_card','browser_history') AND last_read_source IN ('rec','topnews','feed_main_info','unknown'))))
            , consum_cnt_v2, 0)) AS consum_vv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

### DJY-005: 信息流DAU

> 信息流可触达用户数，近似内容曝光UV。考虑曝光打点缺失（主要是 push 频道），取有曝光或有消费的用户数。

```sql
SELECT  date,
        COUNT(DISTINCT CASE WHEN expos_cnt > 0 OR consum_cnt_v2 > 0 THEN did END) AS feed_dau
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

### DJY-006: 总时长（分钟）

> 信息流可触达用户的信息流总使用时长（含页面停留），= 一级页时长 + 二级页时长。

```sql
SELECT  date,
        SUM(feed_dura) / 60000 AS total_dur_min
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

### DJY-007: 双频道双列表页 CTR / UTR

> 衡量双频道双列表内容曝光转化效率。CTR/UTR 必须限制双频道双列表页才有意义（点击基本在列表页上报）。

```sql
SELECT  date,
        SUM(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec'), click_cnt, 0)) * 1.0
            / NULLIF(SUM(IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec'), expos_cnt, 0)), 0) AS ctr,
        COUNT(DISTINCT IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND click_cnt > 0, did, NULL)) * 1.0
            / NULLIF(COUNT(DISTINCT IF(feed_channel IN ('热点','推荐') AND page IN ('feed_info_topnews','feed_info_rec') AND expos_cnt > 0, did, NULL)), 0) AS utr
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
        AND (feed_channel IN ('热点','推荐','profile','profile_djy','push') OR item_type IN ('novel','shortstory'))
GROUP BY date
```

---

## 三、多体裁指标（小说 / 短故事）

> 小说/短故事阅读为阅读器上报，无 feed_channel；阅读来源用 `read_source`/`last_read_source` 判断。曝光/点击需限制 `item_docid rlike 'djy'`（自建）或 `'toutiao'`（火山）；阅读时长/VV 不需要限制 djy。

### DJY-NOVEL-001: 小说曝光PV / 点击PV（自建 vs 火山）

```sql
SELECT  date,
        SUM(IF(item_type = 'novel' AND item_docid RLIKE 'djy',     expos_cnt, 0)) AS novel_expose_pv_djy,
        SUM(IF(item_type = 'novel' AND item_docid RLIKE 'toutiao', expos_cnt, 0)) AS novel_expose_pv_volcano,
        SUM(IF(item_type = 'novel' AND item_docid RLIKE 'djy',     click_cnt, 0)) AS novel_click_pv_djy,
        SUM(IF(item_type = 'novel' AND item_docid RLIKE 'toutiao', click_cnt, 0)) AS novel_click_pv_volcano
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
GROUP BY date
```

### DJY-NOVEL-002: 小说阅读时长（分钟）/ 阅读VV

> 首访 `read_source in ('rec','topnews')` + 续读 `read_source in ('feed_continue_view_card','browser_history') and last_read_source in ('rec','topnews')`。

```sql
SELECT  date,
        SUM(IF(item_type = 'novel' AND (read_source IN ('rec','topnews')
            OR (last_read_source IN ('rec','topnews') AND read_source IN ('feed_continue_view_card','browser_history')))
            , consum_dura, 0)) / 60000 AS novel_read_dur_min,
        SUM(IF(item_type = 'novel' AND (read_source IN ('rec','topnews')
            OR (last_read_source IN ('rec','topnews') AND read_source IN ('feed_continue_view_card','browser_history')))
            , consum_cnt_v2, 0)) AS novel_read_vv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
GROUP BY date
```

### DJY-STORY-001: 短故事曝光PV / 点击PV（自建）

> 目前火山不分发短故事。

```sql
SELECT  date,
        SUM(IF(item_type = 'shortstory' AND item_docid RLIKE 'djy', expos_cnt, 0)) AS story_expose_pv_djy,
        SUM(IF(item_type = 'shortstory' AND item_docid RLIKE 'djy', click_cnt, 0)) AS story_click_pv_djy
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
GROUP BY date
```

### DJY-STORY-002: 短故事阅读时长（分钟）/ 阅读VV

> 首访 `read_source in ('rec','topnews','feed_main_info','unknown')` + 续读。20.12 以下版本 item_book_id 可能为 null（上报缺失），仍需统计。

```sql
SELECT  date,
        SUM(IF(item_type = 'shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
            OR (last_read_source IN ('rec','topnews','feed_main_info','unknown') AND read_source IN ('feed_continue_view_card','browser_history')))
            , consum_dura, 0)) / 60000 AS story_read_dur_min,
        SUM(IF(item_type = 'shortstory' AND (read_source IN ('rec','topnews','feed_main_info','unknown')
            OR (last_read_source IN ('rec','topnews','feed_main_info','unknown') AND read_source IN ('feed_continue_view_card','browser_history')))
            , consum_cnt_v2, 0)) AS story_read_vv
FROM    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE   date = ${date}
        AND is_app_dau_2024 = 1
        AND is_top = 0
GROUP BY date
```

---

## 四、计算指标（不需要开发）

| Metric | Formula | Description |
|--------|---------|-------------|
| 人均有效时长(分钟) | 总有效时长 / 有效用户DAU | avg_valid_dur_min |
| 人均消费时长(分钟) | 消费时长 / 消费UV | avg_consum_dur_min |
| 人均消费VV | 消费VV / 消费UV | avg_consum_vv |
| 人均时长(分钟) | 总时长 / 信息流DAU | avg_dur_min |
| 有效用户渗透率 | 有效用户DAU / 信息流DAU | valid_user_penetration |
| 信息流ARPU | 信息流收入 / 信息流活跃用户 | feed_arpu（收入来自 dwm_browser_ad_event_aggregation_di，最细粒度 did+tagid） |

---

## 五、关键注意事项

1. **滑动埋点口径切换**：2026/3/6 后用新口径（滑动埋点 `is_feed_sliding`），3/6 前用旧口径（曝光位置：热点 item_position>=4 / 推荐 >=7）。跨 3/6 对比需注意口径变更引起的正常波动。
2. **小说/短故事消费**：不能用频道一刀切；消费VV/时长必须按 read_source 内联处理。
3. **曝光/点击 vs 阅读**：小说/短故事曝光点击需限 `item_docid rlike 'djy'`（自建专项）；阅读时长/VV 不限 djy（自建前缀是数据侧拼接）。
4. **有效时长 GAP**：堰立方口径（有效用户的 滑动时长+列表停留+消费时长）与实验平台口径（滑动时长+消费时长）约差 20%。
5. **收入**：信息流收入无法区分来源频道（仅 did+tagid 粒度），ARPU 分母信息流活跃用户也不限都江堰频道。
