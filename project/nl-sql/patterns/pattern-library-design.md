# 范式库设计原则

> 范式库是我们 nl-sql 准确率的核心引擎：将高频业务查询抽象为可复用的 (问题模板, SQL 模板) 对。

## 什么是范式

一个范式 = 一类业务查询的标准化表示：

```yaml
name: "渠道新用户次留"
question_template: "{时间范围}内{渠道}的新用户次日留存率"
sql_template: |
  WITH new_users AS (
    SELECT user_id, channel
    FROM user_events
    WHERE event = 'first_visit'
      AND dt BETWEEN '{start_date}' AND '{end_date}'
      AND channel = '{channel}'
  ),
  retained AS (
    SELECT a.user_id
    FROM new_users a
    JOIN user_events b ON a.user_id = b.user_id
    WHERE b.dt = date_add(a.dt, 1)
  )
  SELECT COUNT(DISTINCT retained.user_id) / COUNT(DISTINCT new_users.user_id) AS retention_rate
  FROM new_users LEFT JOIN retained ON new_users.user_id = retained.user_id
parameters:
  - name: start_date
    type: date
  - name: end_date
    type: date
  - name: channel
    type: enum
    values: [organic, paid, push, share]
tags: [留存, 渠道, 新用户]
difficulty: medium
```

## 设计原则

### 1. 从真实需求沉淀

不要凭空设计范式，从每一次真实取数需求中提取：
- 这个需求是否会反复出现？→ 值得做范式
- 只出现过一次的特殊查询 → 不做范式

### 2. 参数化而非硬编码

SQL 中的日期、渠道、指标等用参数占位，让一个范式覆盖一类查询。

### 3. 分层管理

| 层级 | 说明 | 数量 |
|---|---|---|
| 核心范式 | 每周都会用到的高频查询 | 20-30 个 |
| 常用范式 | 每月用到的查询 | 50-100 个 |
| 长尾范式 | 偶尔用到 | 按需积累 |

### 4. 持续迭代

每个 badcase 都可能催生一个新范式或修正一个已有范式。

## 与 data-product-workspace 的协作

- `00-知识库/数据资产/SQL模板库/` 存放具体的 SQL 模板（实操层）
- 本目录存放范式库的设计方法论和管理规范（理论层）
- 两者互相引用
