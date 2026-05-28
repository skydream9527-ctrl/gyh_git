# 内容产品埋点 — 事件与参数设计

> 系统梳理内容产品（短视频 / 信息流 / 阅读 / 直播 / 社交 / 播客）的埋点事件与参数设计：从命名规范、分类体系、参数模型，到数据契约、治理、推荐系统反馈信号——让"埋点"从"产品同学事后补"的脏活，变成可设计、可演进、可信任的工程资产。

## 研究范围

### 1. 概念基础
- 事件命名规范：snake_case、verb_object、动词词典
- 事件分类法：action_object、impression / interaction / lifecycle
- 参数设计：公共参数 vs 事件特有参数
- 用户 / 会话 / 设备 / 内容的实体模型
- 数据契约（schema as contract）

### 2. 内容产品核心事件
- **曝光（Impression / View）**：可见性判定、有效曝光阈值、卡片/feed/详情页区分
- **点击（Click / Tap）**：归因、热区、双击 / 长按
- **播放（Playback）**：起播、心跳、完播、播放进度、暂停 / 拖动 / 倍速
- **互动（Interaction）**：点赞、收藏、关注、评论、分享——信号强度差异
- **生产（UGC）**：发布、草稿、修改
- **生命周期**：登录 / 退出 / 切换 / 后台 / 唤起
- **转化（Conversion）**：付费、订阅、表单提交
- **错误 / 异常**：加载失败、播放卡顿、网络异常

### 3. 推荐系统反馈信号（内容产品独有）
- 正反馈：完播、关注、二次访问、长停留
- 负反馈：快速滑走、不感兴趣、举报、屏蔽
- 隐式 vs 显式信号
- 信号在线学习的延迟与去重

### 4. 数据契约与治理
- Schema Registry：版本管理、向后兼容
- 命名约束：避免"同名不同义"、"同义不同名"
- 必填 / 选填 / 弃用流转
- SRM-like 数据质量监控
- 埋点失效的检测与告警

### 5. 实施与工程
- **客户端 vs 服务端埋点**：决策树、各自适用边界
- SDK 选型：自研 vs Mixpanel / Amplitude / 神策 / GrowingIO
- 上报策略：实时 / 批量 / 离线、压缩、丢失重传
- 沙箱环境与发布流程
- 埋点验证工具

### 6. 数据消费层接口
- 与数仓的对接：明细表、聚合表、维度表
- 与 AB 测试的关系：[../ab-testing/](../ab-testing/)
- 与因果分析的对接：[../causal-inference/](../causal-inference/)
- 与推荐 / 增长团队的协作模式

### 7. 业界标准与方法论
- Snowplow Tracker Protocol、Segment Spec
- Amplitude Taxonomy、Mixpanel Naming Convention
- Google Analytics 4 事件模型
- 字节 / 美团 / 快手等内部数据规范的公开实践

## 目录结构（建议）

```
event-tracking/
├── README.md                       ← 本文件
├── OVERVIEW.md                     ← 开篇导读
├── concepts/                       ← 概念基础
│   ├── event-naming.md
│   ├── event-taxonomy.md
│   ├── parameter-design.md
│   └── entity-model.md
├── content-events/                 ← 内容产品核心事件
│   ├── core-content-events.md
│   ├── impression-and-visibility.md
│   ├── playback-events.md
│   ├── interaction-events.md
│   └── recommendation-feedback.md
├── governance/                     ← 治理
│   ├── schema-and-contract.md
│   ├── data-quality.md
│   └── versioning.md
├── implementation/                 ← 实施
│   ├── client-vs-server.md
│   ├── sdk-selection.md
│   └── verification.md
└── industry/                       ← 业界规范对比
    ├── snowplow-and-segment.md
    └── amplitude-mixpanel.md
```

## 关键参考

### 行业标准 / 公开规范
- **Snowplow Tracker Protocol**：开源、最严格的事件 schema 标准
- **Segment Spec**：电商 / SaaS 行业事实标准
- **Amplitude Taxonomy Playbook**：实战性最强
- **Google Analytics 4 Events**：免费且广泛
- **Mixpanel Naming Convention**

### 实战书籍 / 文献
- *Data Driven*（DJ Patil）— 数据团队建设
- Snowplow 团队的多篇白皮书
- Amplitude 的 *Taxonomy Playbook*（免费下载）
- 字节内部分享文献（公开版本）

### 工具
- **采集**：Mixpanel、Amplitude、Snowplow、Segment、神策、GrowingIO、自研
- **验证**：Iteratively、Avo、Snowtype（schema-first 工具）
- **数仓**：BigQuery、Snowflake、ClickHouse、Doris、Hudi / Iceberg
- **可视化**：Looker、Tableau、Metabase、Superset、自研 BI

## 与本工作区其他模块的关联

- **AB 测试**（[../ab-testing/](../ab-testing/)）：实验离不开埋点；SRM 检测就是埋点质量监控
- **因果推断**（[../causal-inference/](../causal-inference/)）：观察性研究的协变量、处理变量、结果变量都来自埋点
- **Agent + LLM**（[../agent-llm/](../agent-llm/)）：Agent 应用的可观测性（[../agent-llm/production/observability.md](../agent-llm/production/observability.md)）和埋点是同根同源的工程实践
- **控制论**（[../cybernetics/](../cybernetics/)）：埋点是反馈环的"传感器"——传感器质量决定控制系统能力（Ashby 必要多样性）

## 一句话定位

**埋点不是"事后让数据团队补数据"，是产品决策的反馈神经系统。事件与参数设计的质量直接决定 AB 实验、推荐效果、增长策略、用户洞察的天花板。这个目录把它从'脏活'提升为'可设计、可演进、可信任的工程资产'。**
