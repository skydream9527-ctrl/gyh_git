# 创作者签约审核 · audit_status 字段字典

来源：业务侧 2026-05-11 提供。字段位于 `iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg.audit_status`。

## 全部 13 个状态值

| audit_status | 中文含义 | 状态分类 | 是否终态 |
|---|---|---|---|
| `pending_initial_review` | 待初审 | 初审阶段 | 否 |
| `initial_review_rejected` | 初审驳回 | **已驳回** | 是 |
| `pending_re_review` | 待复审 | 复审阶段 | 否 |
| `re_review_rejected` | 复审驳回 | **已驳回** | 是 |
| `approved` | 审核通过 | **通过** | 是（进入二期考核） |
| `pending_second_assess` | 二期考核中 | 二期考核 | 否 |
| `pending_second_rectify` | 二期考核整改中 | 二期考核 | 否 |
| `second_assess_approved` | 二期考核通过 | **通过** | 是（进入三期考核） |
| `second_assess_rejected` | 二期考核未达标 | **考核失败** | 是 |
| `pending_third_assess` | 三期考核中 | 三期考核 | 否 |
| `pending_third_rectify` | 三期考核整改中 | 三期考核 | 否 |
| `third_assess_rejected` | 三期考核未达标 | **考核失败** | 是 |
| `assess_approved` | 三期考核通过 | **最终通过** | 是 |

## 状态流转（示意）

```
pending_initial_review  待初审
    ├─→ initial_review_rejected  初审驳回 ❌
    └─→ pending_re_review  待复审
            ├─→ re_review_rejected  复审驳回 ❌
            └─→ approved  审核通过 ✅
                    └─→ pending_second_assess  二期考核中
                            ├─→ pending_second_rectify  二期考核整改中
                            ├─→ second_assess_rejected  二期考核未达标 ❌
                            └─→ second_assess_approved  二期考核通过 ✅
                                    └─→ pending_third_assess  三期考核中
                                            ├─→ pending_third_rectify  三期考核整改中
                                            ├─→ third_assess_rejected  三期考核未达标 ❌
                                            └─→ assess_approved  三期考核通过 🏆
```

## 按校验口径分组

### 「合格作者」状态（通过类）

参与合规性校验、入库校验的主体。

```sql
audit_status IN (
  'approved',
  'second_assess_approved',
  'assess_approved',
  'pending_second_assess',
  'pending_second_rectify',
  'pending_third_assess',
  'pending_third_rectify'
)
```

### 「未完成审核」状态（中间态，暂不判合格）

```sql
audit_status IN (
  'pending_initial_review',
  'pending_re_review'
)
```

### 「已驳回 / 失败」状态（应豁免，不参与合规校验）

```sql
audit_status IN (
  'initial_review_rejected',
  're_review_rejected',
  'second_assess_rejected',
  'third_assess_rejected'
)
```

> 参考 [exemptions.md](exemptions.md) 的豁免规则章节；后续若业务明确要求"已驳回状态不计入合规校验基数"，统一从 step1 / step2 的 SQL WHERE 中加 `NOT IN (...)` 过滤。