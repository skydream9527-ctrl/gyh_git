# `delete_reason` 码值表

`paimon_zjyprc_hadoop.browser.business_content_pool_realtime.delete_reason` 的合法值域。

**来源**：业务方（用户）2026-04-27 提供的 `DeleteReasonEnum`（Java 枚举）

**性质**：仅说明，**不是规则库内的必填校验**。但在排查具体下线原因、判断豁免属性时会用到。

## A. 来自 CP 的下线原因（code 1-14）

`isCpOffline: true` —— CP 侧触发的下线。

| code | 枚举常量 | 中文 | recoverable（可恢复） |
|---|---|---|---|
| `1` | `OTHER` | 其他 | ❌ |
| `2` | `AUTHOR_REMOVE` | 作者自下架 | ❌ |
| `3` | `TORT` | 侵权 | ❌ |
| `4` | `ABUSE` | 违反相关法律 | ❌ |
| `5` | `ANACHRONISTIC` | 不合时宜 | ❌ |
| `6` | `UNCOMFORTABLE` | 令人不适 | ❌ |
| `7` | `ADVERTISING_INDUCEMENTS` | 广告诱导 | ❌ |
| `8` | `UNFACTUAL` | 非真实性 | ❌ |
| `9` | `TIME_OUT` | 超时效性 | ❌ |
| `10` | `LINK_EXPIRED` | 链接失效 | ❌ |
| `11` | `DUPLIATION` | 重复 | ✅ |
| `12` | `CP_OFFLINE` | CP 下线（原因未知） | ❌ |
| `13` | `DEFAULT_OFFLINE` | 入库默认下线 | ✅ |
| `14` | `INSITE_CP_OFFLINE` | 站内 CP 下线 | ✅ |

## B. 自定义下线原因（code 1001-1006）

`isCpOffline: false` —— 小米侧触发的下线。

| code | 枚举常量 | 中文 | recoverable（可恢复） |
|---|---|---|---|
| `1001` | `REVIEW_NO_PASS` | 审核未通过 | ✅ |
| `1002` | `MANUAL_DELETE` | 人工删除 | ✅ |
| `1003` | `SENSITIVE_OFFLINE` | 命中敏感词下线 | ✅ |
| `1004` | `COMMAND_DELETE` | 指令下线 | ❌ |
| `1005` | `AUTHOR_OFFLINE` | 作者拉黑 | ❌ |
| `1006` | `BLUR_IMAGE_OFFLINE` | 封面图模糊 | ✅ |

## 查询样例

```sql
-- 看各 CP 的下线原因分布
SELECT a_cp, delete_reason, COUNT(*) AS cnt
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE online = '0' AND delete_reason IS NOT NULL AND delete_reason != ''
GROUP BY a_cp, delete_reason
ORDER BY a_cp, cnt DESC;

-- 找某个码对应的具体内容样本
SELECT a_item_id, author_name, item_title, delete_reason
FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
WHERE delete_reason = '1002' AND a_cp = 'cn-beike-djy'
LIMIT 10;
```

## 豁免注释用法

在 `exemptions.json` 里登记豁免条目时，`reason` 字段可以直接引用码值解释：

```json
{
  "reason": "已下线（delete_reason=1002 人工删除）"
}
```
