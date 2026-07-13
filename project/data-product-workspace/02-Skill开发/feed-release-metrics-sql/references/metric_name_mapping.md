# 指标名称映射表

本文档定义了所有指标英文字段名到中文显示名称的映射关系。

---

## 一、大盘指标 (dashboard_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| download_num | 下载量 | mean |
| dau_rate | 日活率 | ratio |
| avg_dur | 人均使用时长 | mean |

---

## 二、信息流日活率指标 (feed_dau_rate_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| rate | 信息流渗透率 | ratio |
| ad_request_uv | 广告请求UV | mean |
| ad_expose_rate | 广告曝光率 | ratio |
| ad_request_avg | 人均广告请求 | mean |

---

## 三、信息流消费指标 (feed_consumption_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| valid_rate | 有效率 | ratio |
| avg_expose | 人均曝光 | mean |
| avg_vv | 人均VV | mean |
| avg_dur | 人均信息流时长 | mean |
| avg_xiaofei_dur | 人均消费时长 | mean |
| ctr | CTR | ratio |
| utr | UTR | ratio |

---

## 四、埋点监控指标 (tracking_monitoring_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| paly_rate | 视频完播率 | ratio |
| mini_avg_dur | 小视频人均消费时长 | mean |
| short_avg_dur | 短视频人均消费时长 | mean |
| avg_xiaofei_dur | 内容人均消费时长 | mean |

---

## 五、信息流留存指标 (feed_retention_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| e2e_ret | 曝光到曝光留存 | ratio |
| e2v_ret | 曝光到有效留存 | ratio |
| v2v_ret | 有效到有效留存 | ratio |

---

## 六、规模体验指标 (scale_experience_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| open_rate | 次日打开率 | ratio |
| zhuqi_rate | 主启率 | ratio |
| sousuo_rate | 搜索率 | ratio |
| avg_search | 人均搜索次数 | mean |

---

## 七、OT口径广告指标 (ot_advertising_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| ipu | IPU | mean |
| avg_require | 人均广告请求 | mean |
| avg_click | 人均广告点击 | mean |
| tianchong_rate | 填充率 | ratio |
| ctr | CTR | ratio |

---

## 八、商业中台指标 (commercial_platform_metrics)

| 英文字段名 | 中文名称 | metric_type |
|-----------|---------|-------------|
| arpu | ARPU | mean |
| ipu | IPU | mean |
| ecpm | ECPM | mean |
| tianchong_rate | 填充率 | ratio |
| loudou | 漏斗率 | ratio |
| cpc | CPC | mean |
| ctr | CTR | ratio |
| cvr | CVR | ratio |
| eview_sucess_rate | 曝光成功率 | ratio |

---

## 用户类型映射

| user_type 值 | 中文显示名称 | 模块顺序 |
|-------------|-------------|---------|
| 大盘用户 | 大盘用户 | 1 |
| 老用户 | 老用户 | 2 |
| 新用户 | 新用户 | 3 |

---

## 使用说明

1. 在生成报告时，所有指标名称应使用中文名称
2. 通过英文字段名在本表中查找对应的中文名称
3. 用户类型按模块顺序展示：大盘用户 → 老用户 → 新用户
