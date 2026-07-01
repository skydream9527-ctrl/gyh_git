# Kyuubi-Presto 大数据量取数优化方法

> 沉淀时间：2026-07-01
> 来源案例：信息流有效 DAU 与时长 4-6 月分天取数（`数据需求/0701信息流有效DAU时长4-6月/`）
> 适用场景：通过 kyuubi-cli 对 iceberg/hive 大表做长时间范围（月级+）、高基数（千万级 did）聚合取数
> 配套踩坑：[../pitfalls/Kyuubi-Presto取数踩坑.md](../pitfalls/Kyuubi-Presto取数踩坑.md)

---

## 核心判断：先 presto，不行再分批，最后才 spark

| 引擎 | 速度 | 内存机制 | 方言 | 适用 |
|---|---|---|---|---|
| presto | 快（单日千万级 did 约 30-90 秒） | 内存聚合，超 240GB 用户上限直接 OOM | 标准 SQL（不支持 rlike） | 首选 |
| spark | 慢（单日常 5 分钟+） | 磁盘溢写，不 OOM 但很慢 | spark/hive 方言（rlike 等） | presto 反复 OOM 时的兜底 |

> 经验：91 天 × 千万级 did 全量查询 presto 会 OOM。优先 presto + count(*) 优化 + 按月分批，不要直接上 spark。

---

## 优化 1：方言等价改写（spark → presto）

文档/历史 SQL 常用 spark 方言，presto 需等价改写：

| spark 方言 | presto 等价 | 说明 |
|---|---|---|
| `a rlike 'p1\|p2'` | `regexp_like(a, 'p1\|p2')` | 部分匹配，语义一致 |
| `if(cond, x, y)` | `if(cond, x, y)` | presto 原生支持，无需改 |
| `coalesce` / `sum` / `max` / `count(distinct)` | 同名 | 无需改 |
| `group by 1,2`（序号） | 同名 | presto 支持 ordinal |

> 改写后必须用单日校验值对照，确认数值无损（见「校验驱动」）。

---

## 优化 2：count(distinct did) → count(*) 等价优化

**前提**：子查询已按 `(date, did)` 分组去重（每个 `(date, did)` 组合唯一）。

此时外层 `group by date` 后：
- `count(distinct did)` = 该 date 下不同 did 数
- `count(*)` = 该 date 下行数 = 不同 did 数（因每行 did 唯一）

两者**完全等价**，但 `count(*)` 不维护 distinct 哈希表，内存从 O(行数) 降到 O(分组数)，可避免 OOM。

```sql
-- 优化前（OOM 风险）
SELECT date, count(distinct did)
FROM (select date, did, ... group by 1, 2) a
GROUP BY 1

-- 优化后（等价，低内存）
SELECT date, count(*)
FROM (select date, did, ... group by 1, 2) a
GROUP BY 1
```

> ⚠️ 仅当子查询按 `(date, did)` 去重时成立。若子查询保留多维度（一行多个 did 维度），不可替换。

---

## 优化 3：按时间分批执行

当单查询仍 OOM（数据量超 presto 240GB 上限），按时间维度分批：

| 数据量 | 分批策略 | 示例 |
|---|---|---|
| 单月（30 天）千万级 did | 通常可单查 | `date between 20260401 and 20260430` |
| 季度（90 天）千万级 did | 按月分批（3 次） | 4 月 / 5 月 / 6 月 各一次 |
| 半年+ 千万级 did | 按周或半月分批 | 每 7-15 天一次 |

分批后用 python/jq 合并 JSON 结果、排序、校验完整性（行数 = 预期天数，无缺天）。

> 并发控制：分批查询可 `run_in_background` 并行，但同时≤2-3 个避免 presto worker fetch 错误。

---

## 校验驱动：单日探针 + 文档校验值对照

跑分天大查询前，**必须先用单日探针验证口径**：

1. 取文档校验日的 SQL 原样跑（如 `date = 20260401`）
2. 对比文档校验图/表中的数值
3. 完全一致 → 口径正确，扩展到分天
4. 不一致 → 排查字段 / 过滤 / 方言差异

> 本次案例：20260401 单日探针 browser_dau=7,449,022 / newhome_dau=17,407,582，与文档校验图 6 项指标全部一致后才扩展到 91 天。

---

## 执行参数模板

```bash
kyuubi sql query "$(cat query.sql)" \
  --catalog iceberg_zjyprc_hadoop \
  --engine presto \
  --region chnbj \
  --workspace 11329 \
  --format json
```

- `--workspace 11329` = 桌面内容中心_产品（token 实际所属，见踩坑坑5）
- 大查询前调大 timeout：`kyuubi config set session.query.timeout 1800`
- SQL 含中文/单引号时用 `"$(cat file.sql)"` 传递，避免 shell 转义问题

---

## 复用 Checklist

跑大数据量取数时按顺序检查：

- [ ] 单日探针验证口径（对照文档校验值）
- [ ] 方言改写（rlike → regexp_like）
- [ ] count(distinct did) → count(*)（若子查询已去重）
- [ ] 仍 OOM 则按月/周分批
- [ ] 分批结果合并 + 行数校验（无缺天）
- [ ] 归档到 `数据需求/MMDD主题/`，经验沉淀回 `00-知识库/data-analysis/`
