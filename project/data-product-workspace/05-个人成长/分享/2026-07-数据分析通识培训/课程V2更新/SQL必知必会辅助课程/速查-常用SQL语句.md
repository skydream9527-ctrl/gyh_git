# 常用 SQL 语句速查（一页纸）

> 提炼自《SQL 必知必会》附录 + 主课要点。落到公司平台用 Hive/Spark 语法（LIMIT / CONCAT / 分区 date）。

---

## 完整子句顺序
```
SELECT   列 / 聚集
FROM     表 [JOIN 表 ON 条件]
WHERE    行过滤（分组前）
GROUP BY 分组维度
HAVING   分组过滤（分组后）
ORDER BY 排序 [DESC]
LIMIT    n
```

## 检索 · 过滤 · 排序
```sql
SELECT DISTINCT col1, col2 FROM t WHERE date=20260628 LIMIT 10;
WHERE a = 1 AND (b = 2 OR c = 3)        -- 混用 AND/OR 加括号
WHERE x BETWEEN 5 AND 10
WHERE x IN ('a','b')      WHERE x NOT IN ('a')
WHERE x IS NULL           -- NULL 用 IS NULL，不能 = NULL
WHERE name LIKE 'Fish%'   -- % 多字符, _ 单字符
ORDER BY price DESC, name ASC
```

## 计算 · 函数
```sql
SELECT CONCAT(a,' - ',b) AS title           -- 拼接（Hive/Spark）
SELECT qty * price AS subtotal              -- 算术，记得起别名 AS
UPPER(x) LOWER(x) TRIM(x) SUBSTR(x,1,3) LENGTH(x)   -- 文本
YEAR(d) ROUND(x,2) ABS(x)                   -- 日期/数值
```

## 聚集 · 分组
```sql
COUNT(*)  COUNT(col)  COUNT(DISTINCT col)   -- *含NULL；col不含NULL；DISTINCT算“多少种”
SUM(x)  AVG(x)  MAX(x)  MIN(x)              -- AVG 跳过 NULL
SELECT k, COUNT(*) FROM t GROUP BY k HAVING COUNT(*) >= 2;
-- 人均别用 AVG：用 SUM(x)/COUNT(DISTINCT 用户)
```

## 联结 · 子查询 · 组合
```sql
-- 内联结（只留都匹配的）
FROM A JOIN B ON A.id = B.id
-- 左联结（A 全留，B 缺失为 NULL）
FROM A LEFT JOIN B ON A.id = B.id
-- 多表串联（沿外键）
FROM Customers c
JOIN Orders o     ON c.cust_id=o.cust_id
JOIN OrderItems i ON o.order_num=i.order_num
-- 子查询过滤
WHERE id IN (SELECT id FROM t2 WHERE ...)
-- 组合（上下拼行）
SELECT ... UNION [ALL] SELECT ...          -- ALL 不去重
```

## 写操作（了解级，务必带 WHERE）
```sql
INSERT INTO t(col1,col2) VALUES(v1,v2);
UPDATE t SET col=val WHERE ...;   -- 🔴 无 WHERE = 改全表
DELETE FROM t WHERE ...;          -- 🔴 无 WHERE = 删全表
```

---

## 高频铁律（踩坑清单）
| # | 铁律 |
|---|------|
| 1 | 查询必加分区 `WHERE date=…`（Hive/Spark 分区裁剪） |
| 2 | 算人数用 `COUNT(DISTINCT did)`，别漏 DISTINCT |
| 3 | 算率除法 `*1.0`，时长毫秒 `/60000` |
| 4 | JOIN 必写 `ON`，否则笛卡尔积爆炸 |
| 5 | LEFT JOIN 后右表 NULL 用 `COALESCE(x,0)` |
| 6 | 人均用 `SUM/COUNT(DISTINCT)`，别用 `AVG` |
| 7 | AND 比 OR 优先，混用加括号 |
| 8 | UPDATE/DELETE 先用 SELECT 验证 WHERE |

> 更深入的执行原理与调优（MapReduce / Shuffle / 数据倾斜）见主课模块4。
