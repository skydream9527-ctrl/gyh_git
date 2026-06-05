# 创作者签约审核表字段字典

**来源**：[【都江堰】创作者审核运营平台接口文档](https://mi.feishu.cn/wiki/VS3xwqwvViOWuakUL1tcQBsxnBc) 中的 `AuditCreatorInfo` 参数说明（2026-04-15 更新）。

**用途**：理解审核表 `iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg` 每个字段的业务含义。本 skill 只做 SELECT 读取，不调用运营后台接口。

## 命名约定

- **接口侧**：驼峰（`cpApi`、`leadAuthorId`）
- **数据表侧**：下划线（`cp_api`、`lead_author_id`）
- **毫秒时间戳**：所有 `*_time` 字段均为 `bigint` 毫秒戳，展示用 `FROM_UNIXTIME(ts/1000)`

## 字段全量对照（35 个）

### 主键 / 身份类

| 接口字段 | 数据表字段 | 类型 | 业务含义 |
|---|---|---|---|
| `cpApi` | `cp_api` | String | MCN 对应 cpApi（如 `cn-beike-djy`） |
| `leadAuthorId` | `lead_author_id` | String | **主站作者 ID / 创作者唯一标识**，最稳定匹配键 |
| `xmAuthorId` | `xm_author_id` | String | 小米作者 ID（审核表推送时可能为空） |
| `cpAuthorId` | `cp_author_id` | String | CP 作者 ID |
| `mainSite` | `main_site` | String | 创作者站点：抖音 / 快手 / 小红书 等 |
| `contactNumber` | `contact_number` | String | 联系号码 |
| `leadAuthorName` | `lead_author_name` | String | **创作者名称**（会变更，不作稳定匹配键） |
| `profile` | `creator_profile` | String | 创作者头像 URL |
| `mainPages` | `main_pages` | List\<String\> | 创作者主页地址（多站点） |

### 认证材料类

| 接口字段 | 数据表字段 | 业务含义 |
|---|---|---|
| `authenticationLabel` | `authentication_label` | 认证标签 |
| `authenticationIdCard` | `authentication_id_card` | 身份证照片链接 |
| `authenticationPhoto` | `authentication_photo` | 人脸照片链接 |
| `authenticationVideo` | `authentication_video` | 真实性视频链接 |
| `authenticationFileWithMCN` | `authentication_file_with_mcn` | 创作者&MCN 协议文件链接 |
| `authenticationImage` | `authentication_image` | 真实性图片链接 |
| — | `original_authentication_*` | 原始认证材料（5 个字段，保留首次上传备份） |

### 账号属性类

| 接口字段 | 数据表字段 | 业务含义 |
|---|---|---|
| `accountType` | `account_type` | 账号类型：`original` 原创 / `derivative` 二创 |
| `accountLevel` | `account_level` | 账号等级：`S` / `A` / `B` / `F`（免费） |
| `verticalField` | `vertical_field` | 垂直分类，格式 `xx-xx-xx` |
| `desc` | `creator_desc` | 简介 |
| `copyrightExpirationTime` | `copyright_expiration_time` | 版权到期时间 |

### 社交指标类

| 接口字段 | 数据表字段 | 业务含义 |
|---|---|---|
| `followCount` | `follow_count` | 粉丝量 |
| `upCount` | `up_count` | 点赞量 |
| `shareCount` | `share_count` | 分享数 |

### 审核流程类

| 接口字段 | 数据表字段 | 业务含义 |
|---|---|---|
| `auditStatus` | `audit_status` | 审核状态（13 个枚举，详见 [audit_status.md](audit_status.md)） |
| `auditTime` | `audit_time` | 提审时间（毫秒戳） |
| — | `update_time` | 状态更新时间（毫秒戳；数据表独有，有审核动作时 `update_time >> audit_time`） |
| `auditOperator` | `audit_operator` | 最近审核人 |
| `rejectReason` | `reject_reason` | 驳回原因（枚举见下文） |

### 考核期类

| 接口字段 | 数据表字段 | 业务含义 |
|---|---|---|
| `assessmentBeginTime` | `assessment_begin_time` | 考核开始时间（二/三期复用） |
| `assessmentEndTime` | `assessment_end_time` | 考核结束时间 |
| `rectifyBeginTime` | `rectify_begin_time` | 整改开始时间 |
| `rectifyEndTime` | `rectify_end_time` | 整改结束时间 |
| `videoView` | `video_view` | 播放量 |
| `videoViewBeginTime` | `video_view_begin_time` | 播放量考核开始时间 |
| `videoViewEndTime` | `video_view_end_time` | 播放量考核结束时间 |
| `monthlyUpdateFrequency` | `monthly_update_frequency` | 月更频率 |
| `monthlyUpdateFrequencyBeginTime` | `monthly_update_frequency_begin_time` | 月更考核开始时间 |
| `monthlyUpdateFrequencyEndTime` | `monthly_update_frequency_end_time` | 月更考核结束时间 |

## 驳回原因 `reject_reason` 枚举

| 值 | 含义 |
|---|---|
| `AUTHENTICATION_FAILED` | 身份认证材料不合格 |
| `BASIC_INFO_INCOMPLETE` | 基本资料不准确或不完整 |
| `CONTENT_STYLE_MISMATCH` | 内容画风不匹配 |
| `VIOLATION_OF_POLICY` | 内容或行为违反平台规范 |
| `OTHER` | 其他 |

> 二/三期考核阶段的驳回另有一套"考核未合格理由"枚举（`assessRejectReasons`），值由运营后台维护，分析中遇到未知值时可向业务方确认。

## 常见查询片段

```sql
-- 查某个作者的完整审核档案
SELECT
  cp_api, lead_author_id, lead_author_name, audit_status,
  FROM_UNIXTIME(audit_time/1000) AS audit_t,
  FROM_UNIXTIME(update_time/1000) AS update_t,
  reject_reason, audit_operator,
  account_type, account_level, vertical_field,
  follow_count, up_count, share_count
FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
WHERE cp_api = 'cn-dihui-djy' AND lead_author_id = '86812366381';

-- 按驳回原因聚合
SELECT cp_api, audit_status, reject_reason, COUNT(*) AS cnt
FROM iceberg_zjyprc_hadoop.browser.creator_audit_info_iceberg
WHERE audit_status IN ('initial_review_rejected', 're_review_rejected',
                       'second_assess_rejected', 'third_assess_rejected')
GROUP BY cp_api, audit_status, reject_reason
ORDER BY cp_api, cnt DESC;
```