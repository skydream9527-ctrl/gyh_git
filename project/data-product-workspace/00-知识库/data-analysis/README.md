# 数据分析 — 方法、工具与案例

> 浏览器/信息流/内容中心/搜索/小说业务的数据分析方法论、SQL/Python最佳实践和实战案例沉淀。

## 目录导航

| 目录 | 内容 |
|------|------|
| [concepts/](./concepts/) | 核心概念：指标定义、统计基础、常见分析思维 |
| [methods/](./methods/) | 分析方法论：MECE/漏斗/对比/归因/留存/分群/异动排查 |
| [sql/](./sql/) | SQL最佳实践：编写规范、性能优化、常用查询模板、Kyuubi使用技巧、表字段字典 |
| [python/](./python/) | Python分析：Pandas技巧、数据可视化、自动化脚本、常用分析库 |
| [pitfalls/](./pitfalls/) | 分析踩坑记录：辛普森悖论、幸存者偏差、常见统计陷阱 |
| [cases/](./cases/) | 实战案例：业务分析报告、问题排查、专项分析沉淀 |
| [templates/](./templates/) | 分析模板：数据分析报告模板、指标字典模板、复盘模板、AI分析Prompt |
| OVERVIEW.md | 开篇导读，建立数据分析心智模型 |

### 核心文件
| 文件 | 内容 |
|------|------|
| [methods/数据分析方法论.md](./methods/数据分析方法论.md) | MECE/漏斗/对比/归因分析框架、指标体系设计、数据质量检查清单、异动排查SOP |
| [sql/浏览器核心表字段字典.md](./sql/浏览器核心表字段字典.md) | ✅ 浏览器业务常用表结构、字段枚举、启动方式分类、三方渠道清单、查询模板（2026-06-29探查更新） |
| [templates/数据分析Prompt模板.md](./templates/数据分析Prompt模板.md) | AI辅助数据分析的标准Prompt模板，从问题定义到报告生成全流程 |
| [cases/2026-06-29-浏览器核心分析报告综合总结.md](./cases/2026-06-29-浏览器核心分析报告综合总结.md) | 7份飞书报告综合提炼：用户画像/行为分层/内容规律/竞品影响/节假日运营/决策建议矩阵 |
| [methods/Kyuubi-Presto大数据量取数优化方法.md](./methods/Kyuubi-Presto大数据量取数优化方法.md) | ✅ presto引擎选择/rlike→regexp_like改写/count(distinct)→count(*)等价优化/按月分批/校验驱动（2026-07-01） |
| [pitfalls/Kyuubi-Presto取数踩坑.md](./pitfalls/Kyuubi-Presto取数踩坑.md) | ✅ presto OOM 240GB/HAVING别名布尔组合/worker fetch临时错误/spark慢/workspace校验/rlike不支持（2026-07-01） |
| [sql/信息流有效DAU口径查询模板.sql](./sql/信息流有效DAU口径查询模板.sql) | ✅ 浏览器+内容中心信息流有效DAU/时长 presto查询模板，含口径校验参考值（2026-07-01） |

## 业务覆盖
- **浏览器主端**：DAU、留存、使用时长、功能渗透率
- **信息流**：点击率、停留时长、互动率、内容消费指标
- **内容中心**：内容供给、分发效率、创作者生态
- **搜索**：搜索量、点击率、满意度、零结果率
- **小说**：阅读时长、留存、付费转化

## 核心能力
- 指标异动排查方法论
- AB实验结果解读
- 用户行为路径分析
- 业务问题根因定位
- 自动化分析脚本开发
- AI辅助分析提效

## 与本工作区的关联
- AB实验结果分析 → [../ab-testing/](../ab-testing/)
- 观察数据因果推断 → [../causal-inference/](../causal-inference/)
- AI数据分析Agent → [../agent-llm/](../agent-llm/)
- 产品指标体系设计 → [../product/](../product/)
- 日常临时分析工作区 → [../../03-数据分析/](../../03-数据分析/)
