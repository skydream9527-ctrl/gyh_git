# 第1章：SQL 与数据检索基础

> 对应原书：第 1–2 课（了解 SQL、检索数据）
> 目标：知道 SQL 是什么，会用 SELECT 把数据"取出来"。

---

## 1.1 SQL 是什么

- **数据库**：保存有组织数据的容器；**表**：某种特定类型数据的结构化清单。
- 一张表 = **行（记录）+ 列（字段）**，每列有数据类型；**主键**唯一标识每一行（如 Products 表的 `prod_id`）。
- **SQL**（Structured Query Language）= 和数据库对话的语言，各家数据库大多支持，语法大同小异。

> 💡 呼应主课启动课：表就是二维表格，SQL 就是在表上"筛选 + 分组 + 计算"。

---

## 1.2 SELECT：检索列

**检索单列：**
```sql
SELECT prod_name
FROM Products;
```
**检索多列**（列名用逗号隔开）：
```sql
SELECT prod_id, prod_name, prod_price
FROM Products;
```
**检索所有列**（用 `*`，通配符）：
```sql
SELECT * FROM Products;
```
> ⚠️ 除非确实要所有列，否则**别用 `SELECT *`**——多取列既慢又浪费（主课"列裁剪"也强调过）。

---

## 1.3 DISTINCT：只要不同的值

```sql
SELECT DISTINCT vend_id
FROM Products;        -- 有哪些供应商（去掉重复）
```
> ⚠️ `DISTINCT` 作用于**所有**列，不只是紧跟它的那列。`SELECT DISTINCT vend_id, prod_price` 是"两列组合去重"，不是只对 vend_id 去重。

---

## 1.4 限制结果行数

探查数据时只想看几行。**这一点各数据库写法差别最大：**

| 环境 | 写法 |
|------|------|
| 书里(SQL Server) | `SELECT TOP 5 prod_name FROM Products` |
| 书里(DB2) | `FETCH FIRST 5 ROWS ONLY` |
| MySQL / **Hive / Spark（我们用）** | `SELECT prod_name FROM Products LIMIT 5` |

```sql
-- 我们的平台：
SELECT prod_name FROM Products LIMIT 5;
```

---

## 1.5 注释

```sql
SELECT prod_name    -- 行内注释：到行尾
-- 整行注释
FROM Products;
/* 多行注释
   可以写好几行 */
```

---

## 本章要点
1. `SELECT 列 FROM 表` 是一切的起点；要所有列才用 `*`，平时**只取需要的列**。
2. `DISTINCT` 去重，且作用于后面**所有**列。
3. 限制行数各库不同，**我们用 `LIMIT n`**。
4. 探查数据养成加 `LIMIT` 的习惯。

## 小练习（附参考答案）
1. 从 Products 表取出所有产品名。
2. 取出产品目录里出现过的所有不同价格。
3. 只看前 3 个产品的 id 和名字。

<details><summary>参考答案</summary>

```sql
-- 1
SELECT prod_name FROM Products;
-- 2
SELECT DISTINCT prod_price FROM Products;
-- 3
SELECT prod_id, prod_name FROM Products LIMIT 3;
```
</details>
