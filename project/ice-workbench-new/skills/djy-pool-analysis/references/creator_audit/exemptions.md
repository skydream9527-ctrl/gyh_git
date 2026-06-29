# 创作者签约审核校验 · 豁免规则

校验前必须应用以下排除逻辑，否则会产生大量误报。

## 1. 媒老板（cn-meilaoban-djy）整家 CP 未推送

**豁免范围**：全部校验步骤

**原因**：业务侧确认媒老板整家 CP 目前未接入审核推送链路，属正常状态。

**应用方式**：
- 步骤 0（签约名单）：剔除签约名单里所有 `cp = 'cn-meilaoban-djy'` 的记录
- 步骤 1/2：审核表本身就没有媒老板数据，不额外过滤

**影响量级**：第一批 224 + 第二批 375 = 599 位媒老板签约作者全部剔除。

## 2. 审核表"测试账号N"为驳回错误数据

**豁免范围**：步骤 1 / 步骤 2

**原因**：之前因推送 `lead_author_id` 错误，这批作者的 `lead_author_name` 被更新成"测试账号1/测试账号2/..."，业务侧已驳回，后续无需关注。

**识别规则**：
```sql
lead_author_name LIKE '测试账号%'
```

**应用方式**：
```sql
SELECT DISTINCT cp_api, lead_author_id
FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
WHERE cp_api <> '' AND lead_author_id <> ''
  AND (lead_author_name IS NULL OR lead_author_name NOT LIKE '测试账号%')
```

**影响量级**：约 61 条（当前全部在 cn-dihui-djy 下，数量会变化）。

## 3. dihui 审核表 xm_author_id 为空

**豁免范围**：任何以 xm_author_id 为匹配键的场景

**原因**：审核表上游尚未把 dihui 的 xm_author_id 刷库，全部为空。业务侧确认为正常待刷库状态。

**应用方式**：
- 匹配签约名单时统一改用 `CP + 作者名`，不要试图用 xm_author_id 辅助匹配
- 第二批签约名单虽然自带 xm_author_id，也不作为主键

## 4. 审核表 lead_author_name 不作稳定匹配键

**原因**：审核表推送的作者名会被后续流程（如作者改名、MCN 维护）更新，不同时间点值可能不同。

**应用方式**：
- 跨表匹配（审核 → 内容池）时只用 `lead_author_id`
- 步骤 2 的签约清单匹配，要拉取内容池中该 `lead_author_id` 对应的**所有历史 `lead_author_name`** 作为候选名字集

## 外部可能新增的豁免

如果业务方说明某批数据属于正常场景，按"现象 → 规则 → 范围"的结构更新本文件：

```markdown
## N. <简短标题>

**豁免范围**：<哪些步骤>
**原因**：<业务侧说明>
**识别规则**：<SQL / Python 表达式>
**应用方式**：<如何在脚本中实现>
**影响量级**：<大致数量>
```
