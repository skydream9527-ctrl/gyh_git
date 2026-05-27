# Browser - 底表/宽表核心指标参考

> **数据层级**：底表/宽表（dwm/dwd 层）
> **与中间表的区别**：中间表（dm/ads/dim）是预聚合表，查询效率高但维度有限；底表/宽表是原始聚合表，支持更灵活的维度筛选，但查询性能较低
> **适用场景**：当中间表不支持所需维度或指标时，可使用底表/宽表查询

## 概述
本文档包含浏览器业务的核心指标SQL查询代码，基于dwm/dwd层底表，用于浏览器业务的分析和运营监控。

## 指标说明

### 1. 浏览器主启DAU
**指标定义**: 通过点击图标启动浏览器的日活跃用户数
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**启动方式**: 点击icon
**过滤条件**: `app_launch_way='点击icon'` 且 `app_open_cnt+app_duration_cnt>0`

```sql
SELECT
    date,
    did
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and app_launch_way='点击icon'
    and app_open_cnt+app_duration_cnt>0
GROUP BY
    1,
    2
;
```

### 2. 浏览器有效DAU
**指标定义**: 浏览器的有效日活跃用户数
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**过滤条件**: `is_app_dau_2024=1` 且 `app_launch_way<>'第三方调起'` 且 `app_open_cnt>0`

```sql
SELECT
    date,
    did
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and is_app_dau_2024=1
    and app_launch_way<>'第三方调起'
    and app_open_cnt>0
GROUP BY
    1,
    2
;
```

### 3. 浏览器消费UV
**指标定义**: 在浏览器中产生消费行为的用户数
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**过滤条件**: `consum_cnt_v2>0`

```sql
SELECT
    date,
    did
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and consum_cnt_v2>0
GROUP BY
    1,
    2
;
```

### 4. 浏览器一级页（列表页）vv
**指标定义**: 浏览器一级页面的浏览量
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**页面类型**: 一级页面（信息流、推荐等）
**计算逻辑**: 统计非置顶内容的曝光次数

```sql
SELECT
    date,
    sum(if (is_top=0, expos_cnt, 0)) vv
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and is_app_dau_2024=1
    and page in ('feed_info_topnews', 'feed_info_rec')
GROUP BY
    1
;
```

### 5. 浏览器短会话uv
**指标定义**: 浏览器短会话的用户数
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**会话类型**: 短会话（有浏览或视频播放行为）
**页面类型**: 详情页、短视频等

```sql
SELECT
    date,
    did
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and is_app_dau_2024=1
    and page in (
        'feed_content_detail',
        'feed_minivideo_continuously_root',
        'feed_minivideo_continuously',
        'feed_shortvideo_immerse_root',
        'feed_shortvideo_immerse'
    ) and (view_cnt>0 or video_play_cnt>0)
GROUP BY
    1,
    2
;
```

### 6. 图文详情页浏览量vv/时长
**指标定义**: 图文详情页的浏览量和停留时长
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**页面类型**: 图文详情页
**内容类型**: 新闻

```sql
SELECT
    date,
    count(
        distinct case
            when view_cnt>0 then did
            else null
        end
    ) uv,
    sum(if (is_top=0, consum_cnt_v2, 0)) vv,
    sum(feed_dura)/60000 dura
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and is_app_dau_2024=1
    and page='feed_content_detail'
    and item_type='news'
GROUP BY
    1
;
```

### 7. 视频详情页浏览量vv/时长
**指标定义**: 视频详情页的浏览量和停留时长
**数据源**: `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
**页面类型**: 视频详情页
**内容类型**: 内联视频

```sql
SELECT
    date,
    count(
        distinct case
            when video_play_cnt>0 then did
            else null
        end
    ) uv,
    sum(if (is_top=0, consum_cnt_v2, 0)) vv,
    sum(feed_dura)/60000 dura
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date=${date-1}
    and is_app_dau_2024=1
    and page='feed_content_detail'
    and item_type='inline_video'
GROUP BY
    1
;
```

## 使用说明
1. 所有查询中的 `${date-1}` 表示前一天的日期
2. 时长相关指标需要除以60000转换为分钟
3. 用户去重使用 `did` 字段
4. 浏览器相关指标主要使用聚合表 `dwm_browser_event_aggregation_label_di`

## 注意事项
- 查询结果需要按日期分组
- 注意数据过滤条件，确保数据准确性
- 一级页面包含多个频道，需要完整列出
- 短会话和长会话需要分别统计
- 图文和视频详情页需要按内容类型分别统计
- 时长计算需要考虑边界值
- DAU指标需要区分启动方式和有效性
