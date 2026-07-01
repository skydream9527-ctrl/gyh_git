# Kyuubi-Presto 取数踩坑记录

> 沉淀时间：2026-07-01
> 来源案例：信息流有效 DAU 与时长 4-6 月分天取数（`数据需求/0701信息流有效DAU时长4-6月/`）
> 配套方法：[../methods/Kyuubi-Presto大数据量取数优化方法.md](../methods/Kyuubi-Presto大数据量取数优化方法.md)

---

## 坑1：presto OOM（exceeded distributed user memory limit of 240GB）

**现象**：`Query exceeded distributed user memory limit of 240GB`，errorCode 131073，errorName=EXCEEDED_GLOBAL_MEMORY_LIMIT。

**根因**：`count(distinct did)` 在大 `(date,did)` 分组下维护 distinct 哈希表，内存爆炸。本次 91 天 × 1740 万 did = 15.8 亿分组。

**解决**：
1. 子查询已按 `(date,did)` 去重时，外层 `count(distinct did)` → `count(*)`（等价，内存 O(分组数)）
2. 仍 OOM 则按月分批（每批 30 天）

> trino 报错会建议"使用 spark 引擎"——但 spark 太慢，优先用 presto + count(*) + 分批。

---

## 坑2：presto HAVING 不能引用 SELECT 别名的布尔组合

**现象**：`'((consum_cnt_v2 > 0) OR ((is_slide > 0) AND (expose_cnt > 0)))' must be an aggregate expression or appear in GROUP BY clause`

**根因**：把外层 WHERE 过滤下推到子查询 HAVING 时，`HAVING consum_cnt_v2 > 0 OR (is_slide > 0 AND expose_cnt > 0)` 引用了多个 SELECT 别名的布尔组合，presto 拒绝。

**注意**：简单聚合别名（如 `HAVING total_cnt > 0`，total_cnt 是 `sum(...)+sum(...)`）presto 接受；多别名布尔组合不行。

**解决**：保留文档原结构——过滤放外层 WHERE（引用子查询输出列，合法），不要下推到子查询 HAVING。

---

## 坑3：presto worker fetch 临时错误

**现象**：`Error fetching http://10.x.x.x:18500/v1/task/.../results/.../0: Expected response...`

**根因**：presto worker 短暂不可用 / 网络抖动，非 SQL 错误。常发于多查询并发时。

**解决**：直接重跑该批次即可恢复。降低并发（同时≤2-3 个大查询）可减少发生。

---

## 坑4：spark 引擎太慢

**现象**：单日 spark 查询 5 分钟未完成。

**根因**：spark 对 ad-hoc 小查询启动 + 调度开销大，不如 presto 轻。

**解决**：iceberg/hive 表 ad-hoc 查询默认用 presto。spark 仅作 presto 反复 OOM 的兜底（接受慢但不 OOM）。

---

## 坑5：workspace 校验失败

**现象**：`Workspace validation failed. Config workspace: '10192'. Token belongs to: '11329' (桌面内容中心_产品)`

**根因**：token 实际所属 workspace 与命令指定不一致。config 里 chnbj 配了 10192 和 11329 两个 workspace，token 属于 11329。

**解决**：用 token 实际所属的 workspace（11329）。报错信息会明确告知 token 属于哪个 workspace，按提示切换即可。

---

## 坑6：rlike 在 presto 不支持

**现象**：`rlike` 语法在 presto 报错。

**根因**：rlike 是 spark/hive 方言，presto 用 `regexp_like`。

**解决**：`a rlike 'p1|p2'` → `regexp_like(a, 'p1|p2')`。改写后用单日探针校验数值一致。

> 详见方法文档「优化1：方言等价改写」。

---

## 坑7：SQL 含中文/单引号的 shell 传递

**现象**：SQL 含中文或单引号（如 `'热点'`），命令行直接传参报错或被 shell 截断。

**解决**：SQL 写到文件，用 `"$(cat file.sql)"` 传递。双引号内 `$(cat)` 展开后，SQL 内的单引号/中文原样保留（前提：SQL 内无 `$` 和反引号）。

---

## 坑8：Presto/Trino 中文别名必须加双引号

**现象**：SQL中中文列别名未加引号，报错 `mismatched input '点'` / `mismatched input '推'` 等。

**根因**：Presto/Trino 对未加引号的标识符要求是纯ASCII，中文别名必须用双引号包裹。

**错误写法**：`AS uv_点击icon`

**正确写法**：`AS "uv_点击icon"`

**注意**：
- 双引号是标识符引用，单引号是字符串常量，不可混用
- `SELECT '热点' AS channel` → 字符串常量，不需要双引号
- `SELECT uv AS "热点频道UV"` → 别名含中文，必须双引号
- Hive/Spark 通常容忍无引号中文别名，但 Presto/Trino 严格要求

**排查方法**：报错信息指向中文位置时，第一反应检查中文别名是否加了双引号。

---

## 坑9：网络中断导致查询结果未返回（Connection aborted）

**现象**：查询已提交但执行时间较长时，出现 `Connection aborted. RemoteDisconnected('Remote end closed connection without response')`。

**根因**：kyuubi-cli 与服务端的HTTP长连接因网络抖动/超时断开，非SQL本身错误。

**解决**：用重试脚本单独重跑失败的查询，不需要修改SQL。大查询建议降低并发（同时≤2-3个）。

---

## 坑10：feishu docx update --mode overwrite 需要交互确认

**现象**：执行 `feishu docx update --mode overwrite --force` 时命令卡住，提示 `overwrite will permanently destroy all images and whiteboards in the document. Continue? [y/N]:`

**解决**：用 `echo "y" | feishu docx update ...` 管道输入确认，避免交互式阻塞。

