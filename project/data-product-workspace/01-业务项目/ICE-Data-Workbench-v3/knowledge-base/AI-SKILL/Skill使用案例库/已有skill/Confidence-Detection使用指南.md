# Confidence Detection使用指南

> 来源: https://mi.feishu.cn/wiki/QxYmwfXUEiud6Hk23RVc10bin3c

# Confidence Detection 使用指南

## 1、简介

### 什么是 Confidence Detection？

Confidence Detection 是一个**AB测试置信度检测与统计分析**的技能，帮助用户进行AB实验的统计假设检验、计算p值与置信区间、判断实验显著性，对比实验组与对照组指标差异。

### 核心能力

| 能力 | 说明 |
|-|-|
| 🧪 实验设计诊断 | 识别指标类型、判断检验方向、评估样本量充足性 |
| 📊 统计计算 | Welch's t 检验（均值类）、双样本比率 Z 检验（比率类） |
| 📈 8大指标模块 | 大盘、信息流日活率、消费、留存、规模体验、广告等 |
| 🔍 分天计算 | 按天分别计算每个指标的显著性，不做跨天聚合 |
| 📝 完整报告 | 生成包含SQL、数据、显著性结果的完整分析报告 |
| 📤 飞书输出 | 自动创建飞书在线文档，方便分享与协作 |

---

## 2、安装前置依赖 

### 2.1 安装 Mi Code CLI

MacOS / Linux / WSL / Matrix 实例，在终端运行：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"


```

### 2.2 安装依赖 Skill

```Bash
micode skills add user_gongyunhe/confidence-detection -i  # AB测试置信度检测
micode skills add ai-team/sql -i                          # 数据查询
micode skills add ai-team/feishu -i                       # 写飞书文档


```

### 2.3 获取数据工坊 Token

1. 登录数据工厂：https://data.mioffice.cn/workspace/?wid=11329#/workspace/11329/config
2. 生成新 Token，复制保存
3. 配置环境变量：

```Bash
export DATAWORKS_TOKEN_ID="your_token_here"


```

---

## 3、使用方法

### 3.1 启动 Mi Code

```Bash
mkdir -p ~/micode && cd ~/micode
micode


```

### 3.2 执行 Confidence Detection Skill

在 Mi Code 对话框中输入：

```Plain Text
执行 confidence-detection


```

或直接描述需求：

```Plain Text
帮我做一下 28.0.0 版本的 AB 测试置信度分析


```

### 3.3 交互流程

**Step 1：收集信息**

```Plain Text
请提供以下信息：
1. 实验组（新版本）的版本号
2. 对照组（旧版本）的版本号
3. 分析时间周期（开始日期和结束日期）
4. 事件描述（用于文件夹命名，如"灰度分析"）


```

**Step 2：生成 SQL 并查询数据**

- 阅读 reference 目录下的 8 个 SQL 模板
- 根据用户参数生成查询 SQL
- 逐个调用 sql Skill 执行查询
- 将结果保存为 CSV 文件

**Step 3：分天计算显著性**

- 读取 8 个 CSV 数据文件
- 按指标类型选择检验方法
- 分天计算每个指标的显著性

**Step 4：生成完整报告**

- 整合 SQL + 数据 + 显著性结果
- 生成 `confidence_analysis_report.md`

**Step 5：创建飞书文档**

- 调用 feishu 技能创建在线文档
- 返回文档链接

---

## 4、使用示例

### 示例：版本灰度分析

**用户输入**：

```Plain Text
执行 confidence-detection
→ 实验组版本：28.0.0
→ 对照组版本：27.9.0
→ 时间范围：2024-04-01 至 2024-04-07
→ 事件描述：灰度分析


```

**执行过程**：

```Plain Text
收到，确认实验分析参数如下：
- 实验组：28.0.0
- 对照组：27.9.0
- 时间范围：2024-04-01 至 2024-04-07（7天）
- 工作目录：~/Desktop/20240408_灰度分析_28.0.0/

正在执行分析流程...
【第一步完成】工作文件夹已创建
【第二步】生成 8 个模块的 SQL，逐个查询...
  → dashboard_metrics.sql ✅ → dashboard_metrics.csv ✅
  → feed_dau_rate_metrics.sql ✅ → feed_dau_rate_metrics.csv ✅
  → feed_consumption_metrics.sql ✅ → feed_consumption_metrics.csv ✅
  → tracking_monitoring_metrics.sql ✅ → tracking_monitoring_metrics.csv ✅
  → feed_retention_metrics.sql ✅ → feed_retention_metrics.csv ✅
  → scale_experience_metrics.sql ✅ → scale_experience_metrics.csv ✅
  → ot_advertising_metrics.sql ✅ → ot_advertising_metrics.csv ✅
  → commercial_platform_metrics.sql ✅ → commercial_platform_metrics.csv ✅
【第三步】分天计算每个指标的显著性...
【第四步】生成 confidence_analysis_report.md ✅
【第五步】创建飞书在线文档 → 文档链接：https://xxx.feishu.cn/docx/xxx


```

**输出结果**：

- 工作文件夹：`~/Desktop/20240408_灰度分析_28.0.0/`
- 包含 8 个 SQL 文件 + 8 个 CSV 数据文件 + 1 个分析报告
- 飞书在线文档链接

---

## 5、支持的指标模块

### 5.1 八大指标模块

| 模块 | SQL 文件 | 主要指标 |
|-|-|-|
| 大盘指标 | dashboard_metrics.sql | 下载量、日活率、人均使用时长 |
| 信息流日活率 | feed_dau_rate_metrics.sql | 渗透率、广告请求UV、曝光率 |
| 信息流消费 | feed_consumption_metrics.sql | 有效率、人均曝光、人均VV、CTR |
| 埋点监控 | tracking_monitoring_metrics.sql | 视频完播率、人均消费时长 |
| 信息流留存 | feed_retention_metrics.sql | 曝光留存、有效留存 |
| 规模体验 | scale_experience_metrics.sql | 次日打开率、主启率、搜索率 |
| OT广告 | ot_advertising_metrics.sql | IPU、人均广告请求、填充率 |
| 商业中台 | commercial_platform_metrics.sql | ARPU、ECPM、CPC、CVR |

### 5.2 指标类型与检验方法

| 指标类型 | 检验方法 | 示例指标 |
|-|-|-|
| 均值类（mean） | Welch's t 检验 | 人均时长、ARPU、IPU |
| 比率类（ratio） | 双样本比率 Z 检验 | 转化率、留存率、CTR |

---

## 6、统计决策规则

### 6.1 显著性判断标准

| 场景 | p 值 | 置信区间 | 结论 |
|-|-|-|-|
| 强显著正向 | p < 0.01 | CI 下限 > 0 | ✅ 强烈建议采纳 |
| 显著正向 | 0.01 ≤ p < 0.05 | CI 下限 > 0 | ✅ 建议采纳 |
| 边缘显著 | 0.05 ≤ p < 0.10 | CI 含 0 | ⚠️ 需更多数据 |
| 不显著 | p ≥ 0.10 | CI 含 0 | ➡️ 无法拒绝 H₀ |
| 显著负向 | p < 0.05 | CI 上限 < 0 | ❌ 建议终止 |

### 6.2 效应量参考标准

| 效应量 | Cohen's d（均值类） | Odds Ratio（比率类） |
|-|-|-|
| 小 | 0.2 | 1.5 |
| 中 | 0.5 | 2.5 |
| 大 | 0.8 | 4.3 |

---

## 7、输出报告结构

### 7.1 报告内容

生成的报告包含以下部分：

**一、实验概览**

- 实验组版本、对照组版本、分析时间范围、显著性水平

**二、模块一：大盘用户指标分析**

- 按日期展示所有指标的分析结果

**三、模块二：老用户指标分析**

- 按日期展示所有指标的分析结果

**四、模块三：新用户指标分析**

- 按日期展示所有指标的分析结果

**五、分模块详细分析**

- 8 个模块的 SQL 查询代码
- 原始数据表格
- 显著性计算结果（含公式推导）

**六、综合建议**

- 根据统计结果给出发布建议

### 7.2 工作文件夹结构

```Plain Text
~/Desktop/{日期}_{事件}_{实验组版本号}/
├── dashboard_metrics.sql
├── dashboard_metrics.csv
├── feed_dau_rate_metrics.sql
├── feed_dau_rate_metrics.csv
├── ...（其他 6 个模块的 SQL 和 CSV）
└── confidence_analysis_report.md

```

---

## 8、常见问题

### Q1：时间范围建议设置多少天？

**建议**：7 天以内。超过 7 天可能稀释版本差异效果。

### Q2：样本量不足怎么办？

**解决方案**：

- 当任一组样本量 < 30 时，系统会提醒结果可能不稳定
- 建议延长实验时间或扩大灰度范围

### Q3：如何理解 p 值和置信区间？

**解释**：

- **p 值**：在零假设为真时，观察到当前或更极端结果的概率
- **置信区间**：真实差异有 95% 的概率落在此区间内

### Q4：多重比较问题如何处理？

**建议**：当同时检验 > 3 个指标时，注意多重比较问题。可使用 Bonferroni 校正（α' = α/n）。

### Q5：SQL 查询失败怎么办？

**常见原因**：

1. **权限不足**：申请对应表的访问权限
2. **Token 过期**：重新生成数据工坊 Token
3. **版本号错误**：确认版本号格式正确

---

## 9、参考链接

- [Mi Code CLI 使用说明书](https://micode.mioffice.cn)
- [Mi Code Hub（AI 工具链平台）](https://micode.mioffice.cn/#/skills)
- [数据工坊平台](https://data.mioffice.cn)

---

## 10、联系开发者

如有问题或需求，请联系：**gongyunhe**