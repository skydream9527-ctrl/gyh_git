# 指标定义文件
# 定义每个 SQL 模板中包含的指标及其统计检验类型
# metric_type: mean（均值类 → t检验）| ratio（比率类 → Z检验）

## dashboard_metrics.sql — 大盘指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 下载量 | download_num | mean | 各版本新增下载用户数 |
| 日活率 | dau_rate | ratio | DAU / 下载量 |
| 人均使用时长(min) | avg_dur | mean | 人均APP使用时长 |

## feed_dau_rate_metrics.sql — 信息流日活率指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 信息流渗透率 | rate | ratio | 信息流DAU / 浏览器DAU |
| 广告请求UV | ad_request_uv | mean | 有广告请求的用户数 |
| 广告曝光率 | ad_expose_rate | ratio | 广告曝光UV / 广告请求UV |
| 人均广告请求 | ad_request_avg | mean | 广告请求PV / 广告请求UV |

## feed_consumption_metrics.sql — 信息流消费指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 有效率 | valid_rate | ratio | 有效用户占比 |
| 人均曝光 | avg_expose | mean | 人均非置顶曝光数 |
| 人均VV | avg_vv | mean | 人均视频播放数 |
| 人均信息流时长(min) | avg_dur | mean | 人均信息流停留时长 |
| 人均消费时长(min) | avg_xiaofei_dur | mean | 人均内容消费时长 |
| CTR | ctr | ratio | 点击率(VV/曝光) |
| UTR | utr | ratio | 用户点击率(有VV用户/DAU) |

## tracking_monitoring_metrics.sql — 埋点监控指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 视频完播率 | paly_rate | ratio | 完播数 / 播放数 |
| 小视频人均消费时长(min) | mini_avg_dur | mean | 小视频详情页人均时长 |
| 短视频人均消费时长(min) | short_avg_dur | mean | 短视频人均时长 |
| 内容人均消费时长(min) | avg_xiaofei_dur | mean | 综合内容人均消费时长 |

## feed_retention_metrics.sql — 信息流留存指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 曝光到曝光留存 | e2e_ret | ratio | 前日有曝光且次日有曝光的用户占比 |
| 曝光到有效留存 | e2v_ret | ratio | 前日有曝光且次日为有效用户的占比 |
| 有效到有效留存 | v2v_ret | ratio | 前日有效且次日有效的用户占比 |

## scale_experience_metrics.sql — 规模体验指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| 次日打开率 | open_rate | ratio | 次日回访率 |
| 主启率 | zhuqi_rate | ratio | 通过icon/书签主动启动的用户占比 |
| 搜索率 | sousuo_rate | ratio | 有搜索行为用户占比 |
| 人均搜索次数 | avg_search | mean | 人均搜索PV |

## ot_advertising_metrics.sql — OT口径广告指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| IPU | ipu | mean | 人均广告曝光数 |
| 人均广告请求 | avg_require | mean | 人均广告请求数 |
| 人均广告点击 | avg_click | mean | 人均广告点击数 |
| 填充率 | tianchong_rate | ratio | 广告返回 / 广告请求 |
| CTR | ctr | ratio | 广告点击 / 广告曝光 |

## commercial_platform_metrics.sql — 商业中台指标

| 指标名称 | 字段名 | metric_type | 说明 |
|---------|--------|-------------|------|
| ARPU | arpu | mean | 人均广告收入 |
| IPU | ipu | mean | 人均有效曝光 |
| ECPM | ecpm | mean | 千次曝光收入 |
| 填充率 | tianchong_rate | ratio | 广告填充率 |
| 漏斗率 | loudou | ratio | 有效曝光 / 原始曝光 |
| CPC | cpc | mean | 单次点击成本 |
| CTR | ctr | ratio | 点击率 |
| CVR | cvr | ratio | 转化率 |
| 曝光成功率 | eview_sucess_rate | ratio | 原始曝光 / 广告返回 |
