# Feed-Release-AB-SQL使用指南

> 来源: https://mi.feishu.cn/wiki/RF3owKzNvih8zBkZwT4c1AZpn5d

# Feed-Release-AB-SQL 使用指南

## 1、简介

### 什么是 Feed-Release-AB-SQL？

Feed-Release-AB-SQL 是一个**版本灰度 AB 分析 SQL 生成器**技能，帮助用户根据版本信息自动生成版本灰度分析所需的全部 SQL 查询文件，无需手写复杂 SQL。

### 核心能力

| 能力 | 说明 |
|-|-|
| 🎯 版本对比分析 | 自动生成实验组与对照组的对比分析 SQL |
| 📊 8 大指标模块 | 大盘、信息流日活率、消费、留存、广告等 8 个模块 |
| 🔬 统计检验支持 | 自动生成置信度计算 SQL（t 检验、Z 检验） |
| ✅ 语法校验 | Spark SQL 语法自动校验与修复 |
| 📁 一键生成 | 16 个 SQL 文件自动生成并保存 |

---

## 2、安装前置依赖

### 2.1 安装 Mi Code CLI

MacOS / Linux / WSL / Matrix 实例，在终端运行：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"
```

### 2.2 安装依赖 Skill

```Bash
micode skills add user_gongyunhe/feed-release-ab-sql -i  # 版本灰度AB分析SQL生成
micode skills add ai-team/feishu -i                     # 写飞书文档（可选）
```

### 2.3 获取数据工坊 Token

1. 登录数据工厂：https://data.mioffice.cn/workspace/?wid=11329#/workspace/11329/config
2. 生成新 Token，复制保存
3. 配置环境变量：

```Bash
export DATAWORKS_TOKEN_ID="your_token_here"
```

### 2.4 申请表权限

常用数据表（需提前申请权限）：

- `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_miui_di`
- `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
- `hive_zjyprc_hadoop.dwm.dwm_app_detail_history_did_df`

---

## 3、使用方法

### 3.1 启动 Mi Code

```Bash
mkdir -p ~/micode && cd ~/micode
micode
```

### 3.2 执行 Skill

在 Mi Code 对话框中输入：

```Plain Text
执行 feed-release-ab-sql
```

或直接描述需求：

```Plain Text
帮我生成 v28.0.0 版本的灰度分析 SQL
```

### 3.3 交互流程

**Step 1：提供版本名称**

```Plain Text
您好！我是互联网数据分析专家，将帮助您生成版本灰度分析的 SQL 查询。

首先，请提供需要分析的 APP 版本名称（如：v28.0.0）：
```

**Step 2：提供版本号**

```Plain Text
收到版本名称：v28.0.0

接下来请提供：
1. 实验组版本号（新版本/灰度版本）：如 28.0.0
2. 对照组版本号（旧版本/线上版本）：如 27.9.0
```

**Step 3：提供时间周期**

```Plain Text
收到版本信息：
- 实验组版本：28.0.0
- 对照组版本：27.9.0

最后请提供分析时间周期：
- 开始日期（格式：YYYY-MM-DD）
- 结束日期（格式：YYYY-MM-DD）
```

**Step 4：确认信息**

```Plain Text
📋 信息确认：
┌─────────────────────────────────────┐
│ 版本名称：v28.0.0                    │
│ 实验组版本：28.0.0                   │
│ 对照组版本：27.9.0                   │
│ 分析时间：2024-01-01 至 2024-01-07   │
│ 时间跨度：7 天                       │
└─────────────────────────────────────┘

确认无误后，我将开始生成 SQL 文件。请回复"确认"继续：
```

**Step 5：自动生成**

系统自动执行：

- 读取 8 个 SQL 模板文件
- 替换模板中的占位符
- 生成 8 个指标查询 SQL
- 生成 8 个置信度计算 SQL
- Spark SQL 语法校验
- 保存到桌面文件夹

---

## 4、使用示例

### 示例：生成 v28.0.0 版本灰度分析 SQL

**用户输入**：

```Plain Text
执行 feed-release-ab-sql
→ 版本名称：v28.0.0
→ 实验组版本：28.0.0
→ 对照组版本：27.9.0
→ 分析时间：2024-01-01 至 2024-01-07
→ 确认
```

**生成结果**：

```Plain Text
🎉 SQL 文件生成完成！

📁 文件夹路径：~/Desktop/v28.0.0_20240107_143025

✅ Spark SQL 语法校验：16/16 个文件通过校验
✅ 文件完整性检查：16 个文件全部生成成功

文件列表：
├── dashboard_metrics.sql              # 大盘指标查询
├── dashboard_metrics_confidence.sql   # 大盘指标置信度计算
├── feed_dau_rate_metrics.sql          # 信息流日活率查询
├── feed_dau_rate_metrics_confidence.sql
├── feed_consumption_metrics.sql       # 信息流消费查询
├── feed_consumption_metrics_confidence.sql
├── tracking_monitoring_metrics.sql    # 埋点监控查询
├── tracking_monitoring_metrics_confidence.sql
├── feed_retention_metrics.sql         # 信息流留存查询
├── feed_retention_metrics_confidence.sql
├── scale_experience_metrics.sql       # 规模体验查询
├── scale_experience_metrics_confidence.sql
├── ot_advertising_metrics.sql         # OT广告指标查询
├── ot_advertising_metrics_confidence.sql
├── commercial_platform_metrics.sql    # 商业中台查询
└── commercial_platform_metrics_confidence.sql
```

---

## 5、支持的指标范围

### 5.1 大盘指标 (dashboard_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 下载量 | download_num | mean | 各版本新增下载用户数 |
| 日活率 | dau_rate | ratio | DAU / 下载量 |
| 人均使用时长(min) | avg_dur | mean | 人均APP使用时长 |

### 5.2 信息流日活率指标 (feed_dau_rate_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 信息流渗透率 | rate | ratio | 信息流DAU / 浏览器DAU |
| 广告请求UV | ad_request_uv | mean | 有广告请求的用户数 |
| 广告曝光率 | ad_expose_rate | ratio | 广告曝光UV / 广告请求UV |
| 人均广告请求 | ad_request_avg | mean | 广告请求PV / 广告请求UV |

### 5.3 信息流消费指标 (feed_consumption_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 有效率 | valid_rate | ratio | 有效用户占比 |
| 人均曝光 | avg_expose | mean | 人均非置顶曝光数 |
| 人均VV | avg_vv | mean | 人均视频播放数 |
| 人均信息流时长(min) | avg_dur | mean | 人均信息流停留时长 |
| 人均消费时长(min) | avg_xiaofei_dur | mean | 人均内容消费时长 |
| CTR | ctr | ratio | 点击率(VV/曝光) |
| UTR | utr | ratio | 用户点击率(有VV用户/DAU) |

### 5.4 埋点监控指标 (tracking_monitoring_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 视频完播率 | paly_rate | ratio | 完播数 / 播放数 |
| 小视频人均消费时长(min) | mini_avg_dur | mean | 小视频详情页人均时长 |
| 短视频人均消费时长(min) | short_avg_dur | mean | 短视频人均时长 |
| 内容人均消费时长(min) | avg_xiaofei_dur | mean | 综合内容人均消费时长 |

### 5.5 信息流留存指标 (feed_retention_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 曝光到曝光留存 | e2e_ret | ratio | 前日有曝光且次日有曝光的用户占比 |
| 曝光到有效留存 | e2v_ret | ratio | 前日有曝光且次日为有效用户的占比 |
| 有效到有效留存 | v2v_ret | ratio | 前日有效且次日有效的用户占比 |

### 5.6 规模体验指标 (scale_experience_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 次日打开率 | open_rate | ratio | 次日回访率 |
| 主启率 | zhuqi_rate | ratio | 通过icon/书签主动启动的用户占比 |
| 搜索率 | sousuo_rate | ratio | 有搜索行为用户占比 |
| 人均搜索次数 | avg_search | mean | 人均搜索PV |

### 5.7 OT口径广告指标 (ot_advertising_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| IPU | ipu | mean | 人均广告曝光数 |
| 人均广告请求 | avg_require | mean | 人均广告请求数 |
| 人均广告点击 | avg_click | mean | 人均广告点击数 |
| 填充率 | tianchong_rate | ratio | 广告返回 / 广告请求 |
| CTR | ctr | ratio | 广告点击 / 广告曝光 |

### 5.8 商业中台指标 (commercial_platform_metrics)

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| ARPU | arpu | mean | 人均广告收入 |
| IPU | ipu | mean | 人均有效曝光 |
| ECPM | ecpm | mean | 千次曝光收入 |
| 填充率 | tianchong_rate | ratio | 广告填充率 |
| 漏斗率 | loudou | ratio | 有效曝光 / 原始曝光 |
| CPC | cpc | mean | 单次点击成本 |
| CTR | ctr | ratio | 点击率 |
| CVR | cvr | ratio | 转化率 |
| 曝光成功率 | eview_sucess_rate | ratio | 原始曝光 / 广告返回 |

---

## 6、SQL 文件说明

### 6.1 指标查询 SQL（8个）

用于查询各模块的核心指标数据，按日期和版本分组统计。

**文件命名**：`{模块名}_metrics.sql`

**输出字段**：

- `date`：日期
- `app_ver`：版本号
- `user_type`：用户类型（大盘用户、新用户、老用户）
- 各模块指标字段

### 6.2 置信度计算 SQL（8个）

用于提取统计检验所需的原始数据，支持 t 检验和 Z 检验。

**文件命名**：`{模块名}_metrics_confidence.sql`

**检验方法**：

- **mean（均值类指标）**：使用 t 检验

  - 所需数据：样本均值、样本标准差、样本量
- **ratio（比率类指标）**：使用 Z 检验

  - 所需数据：成功次数、总次数

---

## 7、执行 SQL

生成 SQL 后，可通过以下方式执行：

### 方式 1：数据工坊

🔗 https://data.mioffice.cn/workspace/?wid=11329#/workspace/11329/adHoc

将 SQL 复制到数据工坊执行。

### 方式 2：命令行（需配置 Token）

```Bash
DATAWORKS_TOKEN_ID=your_token python3 scripts/sql_query_tool.py --file dashboard_metrics.sql
```

### 方式 3：Spark SQL

```Bash
spark-sql -f dashboard_metrics.sql
```

---

## 8、常见问题

### Q1：提示"时间周期超过 7 天"怎么办？

**原因**：较长的时间周期可能会稀释版本差异的影响。

**解决方案**：

1. 建议将分析时间周期压缩到 7 天范围内
2. 如需分析更长周期，可确认后继续

### Q2：SQL 语法校验失败怎么办？

**原因**：SQL 语法错误或字段冲突。

**解决方案**：

1. 系统会自动尝试修复（最多重试 3 次）
2. 如仍失败，查看错误信息手动修复
3. 常见错误：字段名冲突、GROUP BY 缺失字段

### Q3：如何查看指标定义？

索引文件位置：

- 指标定义：`reference/metrics_definition.md`
- 指标名称映射：`reference/metric_name_mapping.md`

### Q4：生成的 SQL 如何使用？

**解决方案**：

1. 指标查询 SQL：直接执行，获取各版本指标数据
2. 置信度计算 SQL：执行后提取原始数据，用于统计检验
3. 可使用 confidence-detection skill 进行置信度计算

---

## 9、参考链接

- [Mi Code CLI 使用说明书](https://micode.mioffice.cn)
- [Mi Code Hub（AI 工具链平台）](https://micode.mioffice.cn/#/skills)
- [数据工坊平台](https://data.mioffice.cn)
- [Spark SQL 官方文档](https://spark.apache.org/sql/)

---

## 10、联系开发者

如有问题或需求，请联系：**gongyunhe**