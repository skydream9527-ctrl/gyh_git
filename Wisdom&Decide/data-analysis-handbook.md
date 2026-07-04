
# 📊 数据分析方法手册 · 速查入口

> 数据分析的本质是**用数据回答业务问题**，不是炫技。不要拿着锤子找钉子。
> 完整方法库见 [project/data-analysis/OVERVIEW.md](../project/data-analysis/OVERVIEW.md)。

## 核心心智模型

```
业务问题 → 拆解问题 → 选择方法 → 取数计算 → 业务解读 → 决策建议
   ↑                                                          ↓
   └──────────────── 验证效果，持续迭代 ←───────────────────────┘
```

### 好分析的三个标准
1. **能落地**：结论直接指导决策，给出具体行动建议
2. **有逻辑**：推理清晰，结论有数据支撑
3. **讲人话**：把数据翻译成业务语言

### 六句心法
1. 业务第一，数据第二
2. 结论先行：先说"是什么、为什么、怎么办"
3. 质疑数据：拿到先校验，错数据比没数据更可怕
4. 保持简单：能简单说清楚就别搞复杂模型
5. 对比才有结论：单独一个数字没有意义
6. 相关 ≠ 因果：一起涨不代表因果，要验证

## 通用分析七步

1. **明确问题**：回答什么业务问题？谁看？做什么决策？
2. **拆解指标**：拆成可量化指标，明确口径
3. **数据准备**：取数、清洗、**校验**（铁律：数据不对分析全废）
4. **探索分析**：选合适方法，可视化发现规律
5. **交叉验证**：多角度验证，排除辛普森 / 幸存者偏差
6. **业务解读**：翻译成业务语言，找到根因
7. **落地建议**：具体可执行，含预期效果和优先级

## 方法分类速查

| 类别 | 方法 |
|------|------|
| 用户行为 | 漏斗 / 路径 / 留存 / 同期群 |
| 用户价值 | RFM / 用户分群 / 生命周期 / LTV |
| 对比归因 | 对比 / 同比环比 / 下钻 / 归因 / 异动诊断 |
| 指标监控 | 异动告警 / 趋势 |

完整方法索引与文件链接见 [OVERVIEW.md](../project/data-analysis/OVERVIEW.md)。

## 实战速查

| 场景 | 去哪 |
|------|------|
| 指标下跌排查 | [checklists/metric-drop.md](../project/data-analysis/checklists/metric-drop.md) |
| 新功能上线评估 | [checklists/new-feature.md](../project/data-analysis/checklists/new-feature.md) |
| 渠道质量评估 | [checklists/channel-quality.md](../project/data-analysis/checklists/channel-quality.md) |
| 报告怎么写 | [writing/report-guide.md](../project/data-analysis/writing/report-guide.md) |
| 常见陷阱避坑 | [pitfalls.md](../project/data-analysis/pitfalls.md) |

## 最后

> 所有的模型都是错的，但有些是有用的。不用追求完美分析，在信息足够时快速决策，然后迭代验证。
