# 置信度检验方法参考

## 一、检验方法选择规则

| 指标类型 | metric_type | 检验方法 | 所需数据 |
|---------|-------------|---------|---------|
| 均值类 | mean | t 检验 | 样本均值、样本标准差、样本量 |
| 比率类 | ratio | Z 检验 | 成功次数、总次数 |

## 二、t 检验数据提取规则（均值类指标）

### 2.1 SQL 结构模板

```sql
-- {指标模块名称} - 置信度计算数据提取
-- 用于 t 检验：提取每个用户的指标值，用于计算样本均值、标准差、样本量

SELECT 
    date,
    app_ver,
    user_type,
    did as user_id,
    {指标字段} as metric_value
FROM {基础数据表}
WHERE date BETWEEN {开始日期} AND {结束日期}
  AND app_ver IN ('{实验组版本号}', '{对照组版本号}')
  AND {指标相关条件}
```

### 2.2 提取要求

- 必须提取到**用户级（did 级别）**的明细数据
- 每行代表一个用户的一条指标值
- 输出字段必须包含：`date`, `app_ver`, `user_type`, `user_id`, `metric_value`
- `metric_value` 必须为数值类型
- 不允许在 SQL 内做聚合（AVG/SUM/COUNT 等），聚合由下游统计工具完成

## 三、Z 检验数据提取规则（比率类指标）

### 3.1 SQL 结构模板

```sql
-- {指标模块名称} - 置信度计算数据提取
-- 用于 Z 检验：提取成功次数和总次数

SELECT 
    date,
    app_ver,
    user_type,
    COUNT(DISTINCT did) as total_users,
    SUM({成功条件}) as success_count
FROM {基础数据表}
WHERE date BETWEEN {开始日期} AND {结束日期}
  AND app_ver IN ('{实验组版本号}', '{对照组版本号}')
GROUP BY date, app_ver, user_type
```

### 3.2 提取要求

- 必须提取**成功次数**和**总次数**两个聚合值
- 输出字段必须包含：`date`, `app_ver`, `user_type`, `total_users`, `success_count`
- `success_count` 为满足条件的用户数
- `total_users` 为分母用户总数
- GROUP BY 必须包含 `date`, `app_ver`, `user_type`

## 四、各模块指标检验方法分配

| 模块 | 文件名 | mean 类指标 | ratio 类指标 |
|------|--------|------------|-------------|
| 大盘指标 | dashboard_metrics | download_num, avg_dur | dau_rate |
| 信息流日活率 | feed_dau_rate_metrics | ad_request_uv, ad_request_avg | rate, ad_expose_rate |
| 信息流消费 | feed_consumption_metrics | avg_expose, avg_vv, avg_dur, avg_xiaofei_dur | valid_rate, ctr, utr |
| 埋点监控 | tracking_monitoring_metrics | mini_avg_dur, short_avg_dur, avg_xiaofei_dur | paly_rate |
| 信息流留存 | feed_retention_metrics | — | e2e_ret, e2v_ret, v2v_ret |
| 规模体验 | scale_experience_metrics | avg_search | open_rate, zhuqi_rate, sousuo_rate |
| OT广告 | ot_advertising_metrics | ipu, avg_require, avg_click | tianchong_rate, ctr |
| 商业中台 | commercial_platform_metrics | arpu, ipu, ecpm, cpc | tianchong_rate, loudou, ctr, cvr, eview_sucess_rate |

## 五、置信度 SQL 文件命名规范

文件命名格式：`{原指标模块文件名}_confidence.sql`

| 序号 | 文件名 | 对应指标模块 |
|------|--------|-------------|
| 1 | dashboard_metrics_confidence.sql | 大盘指标 |
| 2 | feed_dau_rate_metrics_confidence.sql | 信息流日活率 |
| 3 | feed_consumption_metrics_confidence.sql | 信息流消费 |
| 4 | tracking_monitoring_metrics_confidence.sql | 埋点监控 |
| 5 | feed_retention_metrics_confidence.sql | 信息流留存 |
| 6 | scale_experience_metrics_confidence.sql | 规模体验 |
| 7 | ot_advertising_metrics_confidence.sql | OT广告 |
| 8 | commercial_platform_metrics_confidence.sql | 商业中台 |

## 六、置信度 SQL 与指标取数 SQL 的关系

置信度 SQL 的数据来源与指标取数 SQL 使用**相同的基础数据表**，但提取粒度不同：

| 维度 | 指标取数 SQL | 置信度取数 SQL |
|------|-------------|---------------|
| 聚合粒度 | 按版本+用户类型聚合 | mean: 用户级明细；ratio: 按版本+用户类型聚合 |
| 输出目的 | 直接查看指标值 | 提供统计检验的原始数据 |
| GROUP BY | date, app_ver, user_type | mean: 无 GROUP BY；ratio: date, app_ver, user_type |
| 聚合函数 | AVG, SUM, COUNT 等 | mean: 不聚合；ratio: COUNT(DISTINCT), SUM |

## 七、各模块置信度 SQL 示例文件

以下文件提供了每个模块的置信度取数 SQL 示例，可直接参考改写：

| 序号 | 文件名 | 指标模块 | mean 类指标（t 检验） | ratio 类指标（Z 检验） |
|------|--------|---------|----------------------|----------------------|
| 1 | `dashboard_metrics_confidence.sql` | 大盘指标 | download_num, avg_dur | dau_rate |
| 2 | `feed_dau_rate_metrics_confidence.sql` | 信息流日活率 | ad_request_uv, ad_request_avg | rate, ad_expose_rate |
| 3 | `feed_consumption_metrics_confidence.sql` | 信息流消费 | avg_expose, avg_vv, avg_dur, avg_xiaofei_dur | valid_rate, ctr, utr |
| 4 | `tracking_monitoring_metrics_confidence.sql` | 埋点监控 | mini_avg_dur, short_avg_dur, avg_xiaofei_dur | paly_rate |
| 5 | `feed_retention_metrics_confidence.sql` | 信息流留存 | — | e2e_ret, e2v_ret, v2v_ret |
| 6 | `scale_experience_metrics_confidence.sql` | 规模体验 | avg_search | open_rate, zhuqi_rate, sousuo_rate |
| 7 | `ot_advertising_metrics_confidence.sql` | OT广告 | ipu, avg_require, avg_click | tianchong_rate, ctr |
| 8 | `commercial_platform_metrics_confidence.sql` | 商业中台 | arpu, ipu, ecpm, cpc | tianchong_rate, loudou, ctr, cvr, eview_sucess_rate |
