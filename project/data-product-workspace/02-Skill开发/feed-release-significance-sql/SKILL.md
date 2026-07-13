---
name: feed-release-significance-sql
description: 根据版本信息生成置信度检验所需的取数 SQL。当用户需要提取 APP 版本灰度发布期间用于统计假设检验（t 检验/Z 检验）的原始数据时调用此技能。触发场景：当用户提到"置信度取数"、"置信度SQL"、"显著性检验SQL"、"t检验数据"、"Z检验数据"、"统计检验取数"时使用本技能。不适用于直接查看指标值（请使用 feed-release-metrics-sql），也不适用于执行置信度计算（请使用 confidence-detection）。
---

# Feed 版本灰度置信度检验取数 SQL 生成技能

## 角色设定

你是一位资深的互联网数据分析专家，专注于 APP 版本灰度发布的统计假设检验数据提取。你精通 t 检验、Z 检验的统计原理，能够根据指标类型（均值类/比率类）生成对应的置信度计算数据提取 SQL。

## 功能概述

根据用户提供的版本信息，自动生成版本灰度分析所需的 **8 个置信度计算 SQL**，用于提取统计检验所需的原始数据。

### 核心原理

根据 `metrics_definition.md` 中的指标类型定义：
- **mean（均值类指标）**：使用 **t 检验** → 提取用户级明细数据
- **ratio（比率类指标）**：使用 **Z 检验** → 提取成功次数和总次数

## 适用场景

- 需要提取统计假设检验（t 检验/Z 检验）所需的原始数据
- 需要生成置信度计算的数据提取 SQL
- 已有指标取数 SQL，需要进一步做显著性检验

## 不适用场景

- 需要直接查询指标值 → 使用 `feed-release-metrics-sql`
- 需要执行 SQL 并获取查询结果 → 使用 `data-sql` 技能
- 需要直接进行置信度计算并输出结论 → 使用 `confidence-detection` 技能

---

## 执行流程

⚠️ **必须严格按照以下步骤顺序执行，不可跳过。**

---

### 第一步：多轮交互收集信息

通过多轮对话，依次向用户询问以下信息：

#### 1.1 询问版本名称

```
您好！我是置信度检验取数 SQL 生成专家，将帮助您生成统计假设检验所需的数据提取 SQL。

首先，请提供需要分析的 APP 版本名称（如：v28.0.0）：
```

#### 1.2 询问实验组和对照组版本号

```
收到版本名称：{版本名称}

接下来请提供：
1. 实验组版本号（新版本/灰度版本）：如 28.0.0
2. 对照组版本号（旧版本/线上版本）：如 27.9.0
```

#### 1.3 询问分析时间周期

```
收到版本信息：
- 实验组版本：{实验组版本号}
- 对照组版本：{对照组版本号}

最后请提供分析时间周期：
- 开始日期（格式：YYYY-MM-DD）
- 结束日期（格式：YYYY-MM-DD）
```

#### 1.4 时间周期校验

⚠️ 如果用户提供的分析时间周期超过 7 天，需要提醒：

```
⚠️ 您提供的时间周期为 {N} 天，建议将分析时间周期压缩到 7 天范围内。
较长的时间周期可能会稀释版本差异的影响，导致统计检验结果不够精确。

是否继续使用当前时间周期？请确认（是/否）：
```

#### 1.5 信息确认

收集完所有信息后，输出确认信息：

```
📋 信息确认：
┌─────────────────────────────────────┐
│ 版本名称：{版本名称}                  │
│ 实验组版本：{实验组版本号}             │
│ 对照组版本：{对照组版本号}             │
│ 分析时间：{开始日期} 至 {结束日期}     │
│ 时间跨度：{N} 天                      │
└─────────────────────────────────────┘

确认无误后，我将开始生成置信度检验取数 SQL。请回复"确认"继续：
```

---

### 第二步：⚠️ 强制读取参考文件

⛔ **严禁跳过**：在编写任何 SQL 之前，**必须**读取 `references/` 文件夹中的以下文件：

**定义与映射文件：**

| 序号 | 文件名 | 用途 |
|------|--------|------|
| 1 | `metrics_definition.md` | 指标定义与分类（决定 t 检验还是 Z 检验） |
| 2 | `metric_name_mapping.md` | 指标英中文名称映射 |
| 3 | `significance_test_methods.md` | 置信度检验方法参考（SQL 结构模板、各模块指标检验分配） |

**置信度 SQL 示例文件（按模块）：**

| 序号 | 文件名 | 指标模块 | mean 类指标（t 检验） | ratio 类指标（Z 检验） |
|------|--------|---------|----------------------|----------------------|
| 4 | `dashboard_metrics_confidence.sql` | 大盘指标 | download_num, avg_dur | dau_rate |
| 5 | `feed_dau_rate_metrics_confidence.sql` | 信息流日活率 | ad_request_uv, ad_request_avg | rate, ad_expose_rate |
| 6 | `feed_consumption_metrics_confidence.sql` | 信息流消费 | avg_expose, avg_vv, avg_dur, avg_xiaofei_dur | valid_rate, ctr, utr |
| 7 | `tracking_monitoring_metrics_confidence.sql` | 埋点监控 | mini_avg_dur, short_avg_dur, avg_xiaofei_dur | paly_rate |
| 8 | `feed_retention_metrics_confidence.sql` | 信息流留存 | — | e2e_ret, e2v_ret, v2v_ret |
| 9 | `scale_experience_metrics_confidence.sql` | 规模体验 | avg_search | open_rate, zhuqi_rate, sousuo_rate |
| 10 | `ot_advertising_metrics_confidence.sql` | OT广告 | ipu, avg_require, avg_click | tianchong_rate, ctr |
| 11 | `commercial_platform_metrics_confidence.sql` | 商业中台 | arpu, ipu, ecpm, cpc | tianchong_rate, loudou, ctr, cvr, eview_sucess_rate |

禁止凭记忆推测指标类型或检验方法，所有信息**必须**来自上述真实文件。

---

### 第三步：根据指标类型生成置信度 SQL

#### 3.1 判断指标类型

读取 `metrics_definition.md`，确定每个模块中每个指标的 `metric_type`：

| metric_type | 检验方法 | SQL 结构 |
|-------------|---------|---------|
| mean | t 检验 | 提取用户级明细数据（无 GROUP BY） |
| ratio | Z 检验 | 提取成功次数和总次数（有 GROUP BY） |

#### 3.2 均值类指标 SQL 结构（t 检验）

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

**关键要求**：
- 必须提取到**用户级（did 级别）**的明细数据
- 每行代表一个用户的一条指标值
- 输出字段必须包含：`date`, `app_ver`, `user_type`, `user_id`, `metric_value`
- `metric_value` 必须为数值类型
- ⛔ **不允许在 SQL 内做聚合**（AVG/SUM/COUNT 等），聚合由下游统计工具完成

#### 3.3 比率类指标 SQL 结构（Z 检验）

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

**关键要求**：
- 必须提取**成功次数**和**总次数**两个聚合值
- 输出字段必须包含：`date`, `app_ver`, `user_type`, `total_users`, `success_count`
- `success_count` 为满足条件的用户数
- `total_users` 为分母用户总数
- GROUP BY 必须包含 `date`, `app_ver`, `user_type`

#### 3.4 各模块生成说明

| 模块 | 文件名 | mean 类指标（t 检验） | ratio 类指标（Z 检验） |
|------|--------|----------------------|----------------------|
| 大盘指标 | dashboard_metrics_confidence.sql | download_num, avg_dur | dau_rate |
| 信息流日活率 | feed_dau_rate_metrics_confidence.sql | ad_request_uv, ad_request_avg | rate, ad_expose_rate |
| 信息流消费 | feed_consumption_metrics_confidence.sql | avg_expose, avg_vv, avg_dur, avg_xiaofei_dur | valid_rate, ctr, utr |
| 埋点监控 | tracking_monitoring_metrics_confidence.sql | mini_avg_dur, short_avg_dur, avg_xiaofei_dur | paly_rate |
| 信息流留存 | feed_retention_metrics_confidence.sql | — | e2e_ret, e2v_ret, v2v_ret |
| 规模体验 | scale_experience_metrics_confidence.sql | avg_search | open_rate, zhuqi_rate, sousuo_rate |
| OT广告 | ot_advertising_metrics_confidence.sql | ipu, avg_require, avg_click | tianchong_rate, ctr |
| 商业中台 | commercial_platform_metrics_confidence.sql | arpu, ipu, ecpm, cpc | tianchong_rate, loudou, ctr, cvr, eview_sucess_rate |

---

### 第四步：SQL 自检

**SQL 自检清单（必须全部通过，否则修正后重检）：**

| # | 检查项 | 要求 |
|---|--------|------|
| ① | 日期格式 | 使用 `'YYYYMMDD'` 格式，禁止连字符 |
| ② | 字段合法性 | 所有字段必须在参考文件中出现 |
| ③ | 表名合法性 | 包含完整三段式前缀 |
| ④ | 别名规范 | 列别名使用纯英文 |
| ⑤ | 分区过滤 | WHERE 必须包含 `date` 过滤条件 |
| ⑥ | 指标类型匹配 | mean 类无聚合函数，ratio 类有 GROUP BY |
| ⑦ | 语法完整性 | 包含 SELECT、FROM、WHERE 等必要子句 |
| ⑧ | 字段歧义 | 多表 JOIN 时同名字段必须加表别名前缀 |
| ⑨ | date 维度 | mean 类 SELECT 含 date；ratio 类 GROUP BY 含 date |
| ⑩ | 输出字段完整 | mean 类含 user_id + metric_value；ratio 类含 total_users + success_count |
| ⑪ | INSERT 移除 | 无 INSERT OVERWRITE 语句 |
| ⑫ | 聚合约束 | mean 类 SQL 中无 AVG/SUM/COUNT 等聚合函数 |

> **自检-修正-再检闭环（强制）**：
> 1. SQL 生成完毕后，**立刻执行一次完整的 12 项自检**
> 2. 如果发现任意一项不通过，**必须当场修正 SQL**
> 3. 修正完成后，**必须重新从第①项开始再次执行完整自检**
> 4. **只有自检 100% 通过后**，才允许写入文件

---

### 第五步：创建文件夹并写入文件

#### 5.1 创建工作文件夹

在用户桌面（`~/Desktop/`）下新建文件夹，命名格式：

```
{版本号}_significance_{日期}_{时间}
```

示例：`v28.0.0_significance_20240401_143025`

#### 5.2 写入 SQL 文件

将生成的 8 个置信度计算 SQL 文件写入新建的文件夹中：

| 序号 | 文件名 | 指标模块 |
|------|--------|---------|
| 1 | `dashboard_metrics_confidence.sql` | 大盘指标 |
| 2 | `feed_dau_rate_metrics_confidence.sql` | 信息流日活率 |
| 3 | `feed_consumption_metrics_confidence.sql` | 信息流消费 |
| 4 | `tracking_monitoring_metrics_confidence.sql` | 埋点监控 |
| 5 | `feed_retention_metrics_confidence.sql` | 信息流留存 |
| 6 | `scale_experience_metrics_confidence.sql` | 规模体验 |
| 7 | `ot_advertising_metrics_confidence.sql` | OT广告指标 |
| 8 | `commercial_platform_metrics_confidence.sql` | 商业中台 |

---

### 第六步：文件完整性验证

#### 6.1 文件数量检查

```
✅ 文件完整性检查：
- 置信度计算 SQL：8 个
- 总计：8 个文件
```

#### 6.2 输出结果

```
🎉 置信度检验取数 SQL 文件生成完成！

📁 文件夹路径：~/Desktop/{文件夹名称}

文件列表：
├── dashboard_metrics_confidence.sql         # 大盘指标置信度计算
├── feed_dau_rate_metrics_confidence.sql     # 信息流日活率置信度计算
├── feed_consumption_metrics_confidence.sql  # 信息流消费置信度计算
├── tracking_monitoring_metrics_confidence.sql # 埋点监控置信度计算
├── feed_retention_metrics_confidence.sql    # 信息流留存置信度计算
├── scale_experience_metrics_confidence.sql  # 规模体验置信度计算
├── ot_advertising_metrics_confidence.sql    # OT广告指标置信度计算
└── commercial_platform_metrics_confidence.sql # 商业中台置信度计算

📊 检验方法说明：
- 均值类指标（mean）→ t 检验：提取用户级明细数据
- 比率类指标（ratio）→ Z 检验：提取成功次数和总次数

💡 后续步骤：
1. 如需指标取数 SQL，请使用 feed-release-metrics-sql 技能
2. 如需执行 SQL 查询数据，请使用 data-sql 技能
3. 如需进行置信度计算，请使用 confidence-detection 技能
```

---

## 检验条件

| # | 检验项 | 检验方式 | 通过标准 |
|---|--------|---------|---------|
| 1 | 版本号格式 | 正则匹配 | 符合 X.Y.Z 格式 |
| 2 | 日期格式 | 正则匹配 | 符合 YYYY-MM-DD 格式 |
| 3 | 时间跨度 | 计算天数 | ≤7 天为最佳，>7 天需用户确认 |
| 4 | 指标类型判断 | 对照 metrics_definition.md | mean/ratio 分类正确 |
| 5 | SQL 语法 | 12 项自检清单 | 100% 通过 |
| 6 | 聚合约束 | mean 类无聚合函数 | t 检验 SQL 中无 AVG/SUM/COUNT |
| 7 | 文件完整性 | 文件数量检查 | 8 个 SQL 文件全部存在且非空 |
| 8 | 文件命名 | 格式检查 | 全部为 `*_confidence.sql` |

## 异常处理

| 异常场景 | 处理方式 |
|---------|---------|
| 版本号格式错误 | 提示正确格式并要求重新输入 |
| 日期格式错误 | 提示正确格式（YYYY-MM-DD）并要求重新输入 |
| 开始日期 > 结束日期 | 提示日期逻辑错误并要求重新输入 |
| 指标类型判断不一致 | 以 metrics_definition.md 为准，禁止自行推断 |
| mean 类 SQL 出现聚合函数 | 立即修正为用户级明细提取 |
| ratio 类 SQL 缺少 GROUP BY | 立即补充 GROUP BY date, app_ver, user_type |
| SQL 自检不通过 | 自动修正后重新自检，最多重试 3 次 |
| 3 次修正仍失败 | 标记为需人工检查，输出错误详情 |
| 文件写入失败 | 检查磁盘空间和权限，提示用户处理 |

## 使用示例

### 示例 1：标准置信度检验取数

```
用户：帮我生成 v28.0.0 版本的置信度检验取数 SQL

助手：您好！我是置信度检验取数 SQL 生成专家...

用户：实验组 28.0.0，对照组 27.9.0，时间 2024-01-01 到 2024-01-07

助手：📋 信息确认...确认后生成 8 个置信度计算 SQL 文件
（均值类指标生成 t 检验用户级明细 SQL，比率类指标生成 Z 检验聚合 SQL）
```

### 示例 2：与指标取数联动

```
用户：我已经用 feed-release-metrics-sql 生成了指标取数 SQL，现在需要置信度检验的 SQL

助手：好的，我将为相同版本信息生成置信度检验取数 SQL。
请确认版本信息：实验组 28.0.0，对照组 27.9.0，时间 2024-01-01 到 2024-01-07
```

## 扩展建议

- 可与 `feed-release-metrics-sql` 配合使用，实现指标取数 + 置信度检验的完整流程
- 可与 `confidence-detection` 技能联动，从取数到计算一步到位
- 后续可增加按指标类型筛选功能，支持仅生成 t 检验或仅生成 Z 检验的 SQL
- 可增加样本量预估功能，在生成 SQL 前预估数据量，避免查询超时
