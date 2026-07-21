# 人群包圈选 — SQL 模板

> 来源：2026 H1 共 16 份人群包/圈选交付文档归纳。这类需求高度同质，差异只在参数（APP、时长、版本、实验 ID）。
> 状态：⚠️ 骨架为归纳版，具体表名/字段需用真实 badcase 校准后标 ✅。

## 共性套路

- **输入**：标签的交并集 + 排除条件 + 时长/版本阈值 + 随机抽样控量
- **数据源**：`dwm_${biz}_event_aggregation_label_di`（行为标签宽表）join `dwm_app_usage_did_di`（第三方 APP 安装/使用）
- **产出**：oaid 人群包，三种交付形态 —— 万象人群包 ID / HDFS 文件 / 仅量级
- **人工投入**：主要在需求澄清（口径、量级反复调），SQL 执行可参数化

## 通用模板骨架

```sql
/* 人群包圈选通用模板
 * 参数：${dt} 日期分区 | ${biz} 业务线(browser/content_center)
 *       ${app_list} 第三方APP包名 | ${ver_min} 最低版本 | ${dur_min} 时长阈值 | ${sample} 抽样比例
 * 交付：万象人群包ID / HDFS文件 / 仅量级
 * 字段以 data-analysis/sql/浏览器核心表字段字典.md 为准
 */
WITH label AS (                         -- 1) 标签圈人：交并集 + 阈值
    SELECT did
    FROM dwm_${biz}_event_aggregation_label_di
    WHERE dt = '${dt}'
      AND app_use_duration >= ${dur_min}                     -- 时长阈值（注意单位口径）
      AND split(app_version, '.')[0] >= '${ver_min}'         -- 版本号 split 判断（按实际字段校准）
      -- AND <命中某功能/内容/实验的标签条件>
),
app_cross AS (                          -- 2) 第三方 APP 交集（如已安装闲鱼/淘宝/京东）
    SELECT DISTINCT did
    FROM dwm_app_usage_did_di
    WHERE dt = '${dt}' AND package_name IN (${app_list})
),
excl AS (                               -- 3) 排除：已售卖人群/高端机/黑名单
    SELECT did FROM <排除源表> WHERE <排除条件>
)
SELECT m.oaid                           -- 4) did → oaid 映射后输出
FROM label l
JOIN app_cross a ON l.did = a.did
LEFT JOIN excl e ON l.did = e.did
JOIN <did_oaid_映射表> m ON l.did = m.did
WHERE e.did IS NULL
  AND rand() <= ${sample};              -- 控量抽样
```

## 参数说明

| 参数 | 含义 | 示例 | 备注 |
|------|------|------|------|
| `${dt}` | 数据日期分区 | `20260630` | 通常取 T-1 |
| `${biz}` | 业务线 | `browser` | 决定标签宽表 |
| `${app_list}` | 第三方 APP 包名 | `'com.taobao...','com.jd...'` | 交集/差集用 |
| `${ver_min}` | 最低版本号 | `20` | split 取主版本号判断 |
| `${dur_min}` | 时长阈值 | `0` | 注意秒/分钟口径 |
| `${sample}` | 抽样比例 | `0.5` | 控量到目标量级 |

## 典型场景（差异仅在参数）

| 场景 | 出现次数 | 关键参数差异 | 交付 |
|------|---------|-------------|------|
| 短剧 push 人群包 | 4 | 命中短剧标签 + 分男女/分端 | 万象 ID |
| 浮层售卖测算 | 3 | 第三方 APP 交集（淘宝/京东/闲鱼）+ 仅量级 | 量级数值 |
| 版本圈选（未升级/指定版本） | 2 | `${ver_min}` 版本号判断 | HDFS 文件 |
| 激励任务人群 | 多 | 活跃/无活跃时间窗 + 只增不减 | 万象 ID + 每日调度 |

## 交付 checklist

- [ ] 口径与需求方确认（时长单位、版本判断、排除项）
- [ ] 量级是否在目标范围（>1KW 需拆分）
- [ ] oaid 涉及隐私，按规范私发不入公开文档
- [ ] 交付后到 [../人群包资产登记/人群包登记表.md](../人群包资产登记/人群包登记表.md) 登记一行

## 待校准项（用真实 badcase 补全）

- `dwm_*_event_aggregation_label_di` 的实际全名与标签字段枚举
- did→oaid 映射表名
- 版本号字段的实际格式与 split 规则
- 时长字段单位（秒/分钟）与 0-24h 限制口径
