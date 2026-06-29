# Feed-Release-AB-Analysis使用指南

> 来源: https://mi.feishu.cn/wiki/E0Tvwptx3iRQvakT7CUc79d6nBb

# Feed-Release-AB-Analysis 使用指南

## 1、简介

### 什么是 Feed-Release-AB-Analysis？

Feed-Release-AB-Analysis 是一个**版本灰度 AB 分析报告生成器**技能，帮助用户根据版本灰度数据自动生成完整的分析报告，包含核心指标对比、统计显著性检验和发布建议。

### 核心能力

| 能力 | 说明 |
|-|-|
| 📊 数据解析 | 自动解析 8 大模块的核心指标数据 |
| 🔬 统计检验 | 分天计算各指标的统计显著性（t 检验、Z 检验） |
| 📈 可视化报告 | 生成包含图表、热力图的 HTML 格式报告 |
| 🎯 发布建议 | 基于数据分析给出发布建议和风险提示 |
| 📁 一键生成 | 自动整合数据并生成完整分析报告 |

---

## 2、安装前置依赖

### 2.1 安装 Mi Code CLI

MacOS / Linux / WSL / Matrix 实例，在终端运行：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"
```

### 2.2 安装依赖 Skill

```Bash
micode skills add user_gongyunhe/feed-release-ab-analysis -i  # 版本灰度AB分析报告生成
micode skills add ai-team/feishu -i                          # 写飞书文档（可选）
```

### 2.3 准备数据文件

需要准备 **16 份数据文件**，分为两类：

**第一类：核心指标数据（8 份）**

| 文件名 | 指标模块 |
|-|-|
| `dashboard_metrics.csv` | 大盘指标 |
| `feed_dau_rate_metrics.csv` | 信息流日活率指标 |
| `feed_consumption_metrics.csv` | 信息流消费指标 |
| `tracking_monitoring_metrics.csv` | 埋点监控指标 |
| `feed_retention_metrics.csv` | 信息流留存指标 |
| `scale_experience_metrics.csv` | 规模体验指标 |
| `ot_advertising_metrics.csv` | OT 口径广告指标 |
| `commercial_platform_metrics.csv` | 商业中台指标 |

**第二类：显著性检验原始数据（8 份）**

| 文件名 | 指标模块 |
|-|-|
| `dashboard_metrics_significance.csv` | 大盘指标（显著性） |
| `feed_dau_rate_metrics_significance.csv` | 信息流日活率指标（显著性） |
| `feed_consumption_metrics_significance.csv` | 信息流消费指标（显著性） |
| `tracking_monitoring_metrics_significance.csv` | 埋点监控指标（显著性） |
| `feed_retention_metrics_significance.csv` | 信息流留存指标（显著性） |
| `scale_experience_metrics_significance.csv` | 规模体验指标（显著性） |
| `ot_advertising_metrics_significance.csv` | OT 口径广告指标（显著性） |
| `commercial_platform_metrics_significance.csv` | 商业中台指标（显著性） |

> 💡 提示：这些数据文件可通过 `feed-release-ab-sql` skill 生成 SQL 并执行后获得

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
执行 feed-release-ab-analysis
```

或直接描述需求：

```Plain Text
帮我分析 v28.0.0 版本的灰度数据
```

### 3.3 交互流程

**Step 1：提供数据目录**

```Plain Text
请提供版本灰度数据所在的文件夹路径，我将读取其中的数据文件进行分析。
```

**Step 2：自动解析数据**

系统自动执行：

- 读取目录中的 16 个数据文件
- 验证数据完整性
- 解析核心指标数据
- 计算统计显著性

**Step 3：生成分析报告**

系统自动生成：

- 实验概览
- 整体结论（核心发现、发布建议、风险提示）
- 全局指标对比图表
- 各模块详细分析
- 显著性计算过程

---

## 4、使用示例

### 示例：分析 v28.0.0 版本灰度数据

**用户输入**：

```Plain Text
执行 feed-release-ab-analysis
→ 数据目录：~/Desktop/v28.0.0_20240107_143025
```

**生成结果**：

```Plain Text
✅ 数据完整性检查：16/16 个文件全部存在
✅ 核心指标数据解析完成
✅ 显著性计算完成
✅ 分析报告生成完成

📁 报告文件：~/Desktop/v28.0.0_20240107_143025/version_ab_analysis_report.md

📊 分析概览：
- 实验组版本：28.0.0
- 对照组版本：27.9.0
- 分析时间：2024-01-01 至 2024-01-07（共7天）
- 显著正向指标：12 个
- 显著负向指标：3 个
- 不显著指标：25 个

📢 发布建议：✅ 建议全量发布
```

  
---  
  
\## 5、支持的指标范围  
  
\### 5.1 大盘指标 (dashboard_metrics)  

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 下载量 | download_num | mean | 各版本新增下载用户数 |
| 日活率 | dau_rate | ratio | DAU / 下载量 |
| 人均使用时长(min) | avg_dur | mean | 人均APP使用时长 |

  
\### 5.2 信息流日活率指标 (feed_dau_rate_metrics)  

| 指标名称 | 字段名 | 指标类型 | 说明 |
|-|-|-|-|
| 信息流渗透率 | rate | ratio | 信息流DAU / 浏览器DAU |
| 广告请求UV | ad_request_uv | mean | 有广告请求的用户数 |
| 广告曝光率 | ad_expose_rate | ratio | 广告曝光UV / 广告请求UV |
| 人均广告请求 | ad_request_avg | mean | 广告请求PV / 广告请求UV |

  
\### 5.3 信息流消费指标 (feed_consumption_metrics)  

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

## 6、统计检验方法

### 6.1 均值类指标（mean）— Welch's t 检验

适用于：人均时长、人均曝光、人均VV 等均值类指标

**检验公式**：

```Plain Text
SE = √(s₀²/n₀ + s₁²/n₁)
t = (x̄₁ - x̄₀) / SE
df = (s₀²/n₀ + s₁²/n₁)² / [(s₀²/n₀)²/(n₀-1) + (s₁²/n₁)²/(n₁-1)]
p = 2 × P(T > |t|)  (双侧检验)
95% CI = [Δ - t_{α/2,df} × SE, Δ + t_{α/2,df} × SE]
Cohen's d = Δ / s_pooled
```

**所需数据**：

- `{metric}_n`：样本量
- `{metric}_mean`：均值
- `{metric}_std`：标准差

### 6.2 比率类指标（ratio）— 双样本比率 Z 检验

适用于：日活率、CTR、留存率 等比率类指标

**检验公式**：

```Plain Text
p̂₀ = x₀/n₀,  p̂₁ = x₁/n₁
p̂ = (x₀ + x₁) / (n₀ + n₁)
SE = √[p̂(1-p̂)(1/n₀ + 1/n₁)]
Z = (p̂₁ - p̂₀) / SE
p = 2 × Φ(-|Z|)  (双侧检验)
95% CI = [(p̂₁-p̂₀) - Z_{α/2} × SE_unpooled, (p̂₁-p̂₀) + Z_{α/2} × SE_unpooled]
Odds Ratio = [p̂₁/(1-p̂₁)] / [p̂₀/(1-p̂₀)]
```

**所需数据**：

- `{metric}_numerator`：分子（满足条件的数量）
- `{metric}_denominator`：分母（总数量）
- `{metric}_value`：比率值

---

## 7、报告内容说明

### 7.1 实验概览

包含：

- 实验组版本号
- 对照组版本号
- 分析时间范围
- 显著性水平（α = 0.05）
- 检验方法说明

### 7.2 整体结论

**核心发现摘要**：

- 显著正向指标数量及列表
- 显著负向指标数量及列表
- 不显著指标数量及列表

**发布建议**：

- ✅ 建议全量发布
- ⚠️ 建议延长观察
- ❌ 建议终止实验

**风险提示**：

- 显著负向指标的具体风险
- 样本量不足的指标
- 异常波动天的情况

### 7.3 全局指标对比图表

- 各模块指标变化热力图
- 显著性分布统计图
- 逐日趋势对比图

### 7.4 各模块详细分析

按用户类型分模块展示：

- 模块一：大盘用户
- 模块二：老用户
- 模块三：新用户

每个模块包含：

- 核心指标原始数据
- 完整的显著性计算过程（含公式和数值代入）
- 最终结论

---

## 8、常见问题

### Q1：提示"数据文件缺失"怎么办？

**原因**：目录中缺少部分数据文件。

**解决方案**：

1. 检查目录下是否有 16 个必需的数据文件
2. 使用 `feed-release-ab-sql` skill 生成缺失的 SQL 并执行
3. 将执行结果保存为 CSV 文件

### Q2：如何准备显著性检验数据？

**解决方案**：

1. 使用 `feed-release-ab-sql` skill 生成置信度计算 SQL
2. 执行 SQL 获取原始数据
3. 将结果保存为 `{模块名}_significance.csv`

### Q3：报告中的指标名称如何理解？

**解决方案**：

- 指标定义：`reference/metrics_definition.md`
- 指标名称映射：`reference/metric_name_mapping.md`

### Q4：如何解读显著性检验结果？

**解决方案**：

- **p < 0.05**：差异显著，拒绝原假设
- **p ≥ 0.05**：差异不显著，无法拒绝原假设
- **效应量**：衡量差异的实际意义大小

---

## 9、参考链接

- [Mi Code CLI 使用说明书](https://micode.mioffice.cn)
- [Mi Code Hub（AI 工具链平台）](https://micode.mioffice.cn/#/skills)
- [数据工坊平台](https://data.mioffice.cn)
- [Welch's t 检验](https://en.wikipedia.org/wiki/Welch%27s_t-test)
- [双样本比率 Z 检验](https://en.wikipedia.org/wiki/Two-proportion_z-test)

---

## 10、联系开发者

如有问题或需求，请联系：**gongyunhe**