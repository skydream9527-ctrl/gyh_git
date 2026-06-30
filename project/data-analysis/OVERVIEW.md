# 数据分析方法库

> 数据产品经理/分析师常用分析方法手册，包含适用场景、实现步骤、常见坑、实战案例。

## 核心心智模型

数据分析的本质是**用数据回答业务问题**，不是炫技：
```
业务问题 → 拆解问题 → 选择方法 → 取数计算 → 业务解读 → 决策建议
```
不要拿着锤子找钉子，方法是工具，不是目的。

## 分析方法分类

### 1. 用户行为分析类
| 方法 | 适用场景 | 文件 |
|------|----------|------|
| 漏斗分析 | 转化流程优化、关键路径流失诊断 | [funnel-analysis.md](methods/funnel-analysis.md) |
| 路径分析 | 用户行为轨迹挖掘、导航优化、异常路径发现 | [path-analysis.md](methods/path-analysis.md) |
| 留存分析 | 用户粘性评估、产品价值验证、召回策略 | [retention-analysis.md](methods/retention-analysis.md) |
| 同期群分析(Cohort) | 新用户质量评估、版本迭代效果、生命周期分层 | [cohort-analysis.md](methods/cohort-analysis.md) |
| 会话分析(Session) | 单次访问行为模式、时长/深度评估 | [session-analysis.md](methods/session-analysis.md) |

### 2. 用户价值分析类
| 方法 | 适用场景 | 文件 |
|------|----------|------|
| RFM分析 | 用户价值分层、精准营销、会员体系设计 | [rfm-analysis.md](methods/rfm-analysis.md) |
| 用户分群 | 差异化运营、个性化推荐、精准触达 | [user-segmentation.md](methods/user-segmentation.md) |
| 用户生命周期分析 | 新手/成长/成熟/流失/召回全链路运营 | [lifecycle-analysis.md](methods/lifecycle-analysis.md) |
| CLV/LTV | 用户终身价值计算、获客成本评估、ROI测算 | [ltv-calculation.md](methods/ltv-calculation.md) |

### 3. 对比归因类
| 方法 | 适用场景 | 文件 |
|------|----------|------|
| 对比分析 | 指标异动诊断、版本效果评估、A/B结果解读 | [comparative-analysis.md](methods/comparative-analysis.md) |
| 同比/环比分析 | 趋势判断、季节性识别、周期性波动 | [yoy-mom-analysis.md](methods/yoy-mom-analysis.md) |
| 维度下钻 | 异常原因定位、细粒度问题发现 | [drill-down.md](methods/drill-down.md) |
| 归因分析 | 转化贡献拆分、渠道效果评估、多触点归因 | [attribution-analysis.md](methods/attribution-analysis.md) |

### 4. 指标监控类
| 方法 | 适用场景 | 文件 |
|------|----------|------|
| 指标异动分析 | 核心指标突然涨跌、问题根因定位 | [metric-anomaly-analysis.md](methods/metric-anomaly-analysis.md) |
| 趋势分析 | 长期走势判断、拐点识别、预测预警 | [trend-analysis.md](methods/trend-analysis.md) |
| 健康度评估 | 业务整体状况诊断、北极星指标拆解 | [health-score.md](methods/health-score.md) |

### 5. 业务专项类
| 方法 | 适用场景 | 文件 |
|------|----------|------|
| 营销活动分析 | 活动效果评估、ROI计算、经验沉淀 | [campaign-analysis.md](methods/campaign-analysis.md) |
| 商品/内容分析 | 选品/内容策略、爆款识别、推荐优化 | [content-analysis.md](methods/content-analysis.md) |
| 渠道分析 | 获客质量评估、渠道投放优化、反作弊 | [channel-analysis.md](methods/channel-analysis.md) |
| 付费转化分析 | 付费链路优化、定价策略、客单价提升 | [monetization-analysis.md](methods/monetization-analysis.md) |
| 流失分析 | 流失用户画像、流失原因定位、召回策略 | [churn-analysis.md](methods/churn-analysis.md) |

## 通用分析流程

### 标准数据分析七步
```
1. 明确问题：到底要回答什么业务问题？决策对象是谁？
2. 拆解指标：把大问题拆成可量化的指标，明确口径
3. 数据准备：取数、清洗、校验、确认数据准确性
4. 探索分析：用合适的方法做探索，发现异常/规律
5. 验证结论：交叉验证，排除辛普森悖论、幸存者偏差等
6. 业务解读：把数据结论翻译成业务语言，讲清楚"所以呢"
7. 落地建议：给出可执行的决策建议，明确预期效果
```

## 常见分析陷阱

| 陷阱 | 表现 | 规避方法 |
|------|------|----------|
| 相关当因果 | 两个指标一起涨就认为A导致B | 混淆变量排查、因果推断方法、AB验证 |
| 幸存者偏差 | 只看成功用户/留存用户的特征 | 全量用户对比、流失样本分析 |
| 辛普森悖论 | 总体和分组结论相反 | 必须分层下钻看 |
| 口径不一致 | 不同人同一个指标算出来不一样 | 指标字典统一、口径文档化、数据校验 |
| 忽略基数 | 只看转化率不看流量规模，结论误导 | 绝对数+相对数一起看 |
| 过度拟合 | 过度解读小样本的波动规律 | 统计显著性校验、样本量足够再下结论 |
| 为了解释而解释 | 强行给波动找原因，实则是正常波动 | 先判断波动是否在正常区间 |

## 心法

1. **业务第一，数据第二**：不懂业务的分析师只是取数工具
2. **结论先行**：先说"是什么、为什么、怎么办"，再放过程
3. **好分析能落地**：不能指导决策的分析是自嗨
4. **质疑数据**：拿到数据先校验，错数据比没数据更可怕
5. **保持简单**：能用简单方法说清楚的，不要搞复杂模型
6. **讲好故事**：数据是论据，逻辑是骨架，业务价值是结论
