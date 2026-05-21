---
name: feishu-doc-writer
version: 2.0.0
description: 飞书文档写作助手。基于结构化写作规范，撰写战略文档/周报/OKR复盘/规划方案；v2 拆分模板 A-E 到 resources/。
triggers: [飞书文档, 写飞书, 周报, OKR复盘]
callers_whitelist:
  - AGENTS.md
fallback:
  - 内容原料缺失 → 报错并要求补料，输出 `[fallback: missing_input]` 标记
---

# 飞书文档写作助手 v2

## 一、3 条铁律

1. **结论先行**：首屏必须看到核心判断
2. **判断 > 描述**：每句话给出判断，不做平铺直叙
3. **信息降噪**：每句话回答 so what，回答不了就删

## 二、颜色语义系统

| 颜色 | 语义 | 使用场景 |
|-----|-----|---------|
| 蓝色 | 关键战略词、核心打法 | 战略主线、打法命名 |
| 绿色 | 正向数据（增长、达成） | MoM/YoY 正增长、达成率 ≥100% |
| 红色 | 负向数据、警示、风险 | 下降、未达成、紧急风险 |
| 灰色 | 辅助说明、历史数据 | 同比参照值、历史快照 |
| 黄色背景 | 需共识的建议 | 待决策项、假设前提 |

## 三、模板（详见 resources/）

| 模板 | 场景 | 文件 |
|-----|-----|-----|
| **A** | 战略文档 | template-A-strategy.md |
| **B** | 周报 | template-B-weekly.md |
| **C** | 规划/方案 | template-C-plan.md |
| **D** | OKR 纯复盘 | template-D-okr-review.md |
| **E** | 复盘+规划复合 | template-E-review-plan.md |

## 四、工具调用

核心优先级：`doc_append` / `doc_insert` > `doc_write`（doc_write 会清空文档所有内容，禁止在非重建场景使用）。

## 五、写完后自检

- [ ] 只看 Callout + 粗体行，能否还原 80% 核心信息？
- [ ] 反思是否独立成章？
- [ ] 颜色语义是否严格遵循？
- [ ] 是否存在 so what 回答不了的句子？