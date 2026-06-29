# 创作者签约审核校验 · 产出格式

## 本地 CSV（由 `run_audit_check.py` 生成）

默认输出目录：`~/Desktop/VS Code/签约审核校验_<YYYYMMDD>/`

| 文件 | 内容 | 列 |
|---|---|---|
| `step0_batch1_not_pushed.csv` | 第一批签约未推送明细 | CP, author_name |
| `step0_batch2_not_pushed.csv` | 第二批签约未推送明细 | xm_author_id, CP, author_name |
| `step1_never_in_pool.csv` | 历史从未入库的审核作者 + 审核时间 | CP, audit_name, lead_author_id, audit_time, update_time, audit_status |
| `step2_not_in_contract_final.csv` | 真·不在签约清单（emoji 容错后） | CP, 作者名, lead_author_id, 备注 |
| `step2_emoji_matched.csv` | emoji 容错命中明细（上游数据质量问题） | CP, 内容池原名, 签约清单原名, 清洗后, lead_author_id |
| `summary.csv` | 所有汇总表合并 | 多级表头（按步骤分区） |

## 飞书电子表格结构

用户要求推送飞书时，建议创建 5 sheet：

| Sheet 名 | 内容来源 | 样式 |
|---|---|---|
| `Sheet1`（汇总） | 手动组装（需求一 + 步骤一/二 + 关键发现） | 标题行深蓝底白字 |
| `第一批未推送明细` | step0_batch1_not_pushed.csv | 表头深蓝 |
| `第二批未推送明细` | step0_batch2_not_pushed.csv | 表头深蓝 |
| `审核表不在内容池明细` | step1_never_in_pool.csv | 表头深蓝 |
| `审核表不在签约名单明细` | step2_not_in_contract_final.csv | 表头**红色**（强告警） |

**注意**：emoji 容错命中的 25 位属于数据质量问题，不是核心结论，不建议单独建 sheet（汇总页"关键发现"提一下即可）。

## 汇总页（Sheet1）模板

结构固定四段：

```
[标题栏] 数据日期 + 表名 + 排除项说明
[空行]
[需求一] 签约名单→审核表
  第一批 (CP, 名单总数, 已推送, 未推送, 推送率)
  第二批 (CP, 名单总数, 已推送, 未推送, 推送率)
[空行]
[步骤一] 审核表→内容池 (CP, 审核表作者数, 历史入过库, 从未入库, 入库率)
[空行]
[步骤二] 内容池作者→签约清单 (CP, 内容池可匹配作者, 在签约清单, 不在签约清单, 合规率)
[空行]
[关键发现] 4 条分项说明
```

详见主会话 `58c8130f` 的最终版。

## 飞书推送规则

**严格触发条件**：用户明确说"推/发/送 + 飞书/群"组合词时才推送。

- ✅ "推送到飞书"、"发群里"、"送到群"
- ❌ "跑一下校验"、"出个结果"（仅生成，不推送）

与 [validate/daily_report.md](../validate/daily_report.md) 同等规则。

## Rate Limit 处理

飞书 API（写入/清空/样式）有频控，建议：
- 两次写入之间插入 `sleep 5` 以上
- 触发限流后等 60~90 秒再重试
- 不要短循环重试

## 关键发现模板

产出时以下四条建议固定包含（数字按实际更新）：

```
① 签约→审核 推送率 XX% / YY%
  第一批 XX% / 第二批 YY%；合计 N 位名单上作者未推送，需推送侧补录

② 审核→内容池 入库率 ZZ%
  beike XX% / dihui YY%；从未入库的 M 位需定位推送批次

③ 内容池→签约清单 合规率 WW%
  仅 K 位真·不在清单：<列出>；需业务方确认是否历史存量/跨批次

④ 数据质量：签约清单 X 条作者名 emoji 被截断为 '�'
  上游链路存在不支持 4 字节 UTF-8 的环节，建议清单维护方修复
```
