# 创作者签约审核校验 · 概览

## 背景

业务方（运营）会分批整理 CP 的签约作者名单（飞书表格），按流程推送给"创作者签约审核系统"审核通过后，作者才能正式在内容池中分发内容。校验目的：定期盘点**签约名单 → 审核表 → 内容池**这条链路的一致性。

## 涉及数据源

| 数据源 | 类型 | 用途 |
|---|---|---|
| `iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg` | Iceberg 表 | 创作者签约审核推送记录 |
| `paimon_zjyprc_hadoop.browser.business_content_pool_realtime` | Paimon 表 | 内容池，判断作者是否历史入库 |
| 签约名单（第一批） | 飞书表格 CSV | 匹配键仅有 CP + 作者名 |
| 签约名单（第二批） | 飞书表格 CSV | 有 CP + xm_author_id + 作者名 |

## CP 范围

| CP | 参与校验 | 说明 |
|---|---|---|
| `cn-beike-djy` | ✅ | |
| `cn-dihui-djy` | ✅ | |
| `cn-meilaoban-djy` | ❌ 豁免 | 业务确认整家 CP 未推送属正常状态，校验时剔除 |
| `cn-guoying-djy` | — | 当前不在签约审核范围 |

## 关键字段

### 审核表 `creator_audit_info_iceberg`

| 字段 | 类型 | 说明 |
|---|---|---|
| `cp_api` | varchar | CP 标识（如 cn-beike-djy） |
| `lead_author_id` | varchar | 主站作者 ID（**最稳定的匹配键**） |
| `lead_author_name` | varchar | 创作者名称（**会变更，不作稳定键**） |
| `xm_author_id` | varchar | 小米作者 ID（可能为空，尚未刷库） |
| `audit_status` | varchar | 审核状态（13 个枚举值，详见 [audit_status.md](audit_status.md)） |
| `audit_time` | bigint | 提审时间（毫秒时间戳） |
| `update_time` | bigint | 状态更新时间（毫秒时间戳，有审核动作时 >> audit_time） |
| `reject_reason` | varchar | 驳回原因（枚举，详见 [field_dict.md](field_dict.md#驳回原因-rejectreason-枚举)） |

> 完整字段字典（35 个字段，含业务含义、驳回原因枚举、常用查询）详见 [field_dict.md](field_dict.md)。

### 内容池 `business_content_pool_realtime`

| 字段 | 说明 |
|---|---|
| `a_cp` | CP 标识（对应审核表的 cp_api） |
| `lead_author_id` | 主站作者 ID（与审核表同语义） |
| `lead_author_name` | 作者名（一条 `lead_author_id` 可能对应多个历史名） |
| `create_time` | 内容入库时间（毫秒时间戳，**判断历史入库用此字段**） |
| `date` | 分区字段（**不是入库时间**，不要按它过滤"历史"） |

## 校验范围（排除项）

> 详见 [exemptions.md](exemptions.md)

1. **媒老板整家 CP**：整家未推送属正常，剔除
2. **审核表"测试账号N"**：名字 `LIKE '测试账号%'` 为已驳回的错误推送，剔除
3. **dihui 的 xm_author_id 为空**：尚未刷库属正常，不参与 xm_author_id 匹配
4. **审核表作者名**：不作为稳定匹配键（会变更）

## 快速链路

```
签约名单（第一批 + 第二批）
    │ ① CP + 作者名
    ▼
审核表 creator_audit_info_iceberg （已剔除测试账号）
    │ ② CP + lead_author_id + create_time 判断入库
    ▼
内容池 business_content_pool_realtime （历史入过库）
    │ ③ lead_author_id 下所有历史作者名 vs 签约清单（emoji 容错）
    ▼
签约清单合规作者
```

详见 [match_logic.md](match_logic.md)。
