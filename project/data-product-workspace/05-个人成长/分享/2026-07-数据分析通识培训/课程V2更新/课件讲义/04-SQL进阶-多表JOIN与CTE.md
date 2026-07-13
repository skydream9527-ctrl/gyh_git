# 模块4：SQL 进阶 —— 多表 JOIN、CTE 与执行调优

> 课时：1.5小时 | 层级：🔷 进阶
> 目标：会用 JOIN 关联多张表、用 CTE 拆解复杂查询、避开常见坑；并**理解 SQL 在 Spark/Hive 上的执行原理（MapReduce、Shuffle、数据倾斜），会做语法调优**。
> 前置：模块3（SQL 基础，含"执行原理入门"第七节）。
> 👉 **销售 / 运营**：JOIN/CTE **了解即可**，复杂查询交给 AI；执行原理与调优（五~十节）作为拓展，跟着案例看懂"什么慢、为什么慢"即可。产品/数据方向建议掌握。

---

## 一、开场：单表不够用的时候

有些问题一张表答不了，要跨表看：
- APP 启动行为（miui_di） + 信息流消费（label_di）
- PUSH 点击用户 + 他后续的消费
- 用户标签 + 行为数据

**JOIN = 用共同的"钥匙"（如 `date + did`）把多张表拼起来。**

---

## 二、JOIN：最常用两种（覆盖 99% 场景）

| 类型 | 逻辑 | 场景 | 比喻 |
|------|------|------|------|
| **INNER JOIN** | 只保留两表都匹配上的 | 既启动 APP 又看信息流的用户 | 数学语文都考了的学生 |
| **LEFT JOIN** | 左表全保留，右表没匹配填 NULL | 所有启动用户，看他有没有消费信息流 | 所有考数学的，语文缺考记 NULL |

> ⚠️ LEFT JOIN 后右表没匹配上是 **NULL**，要用 `COALESCE(feed_dura, 0)` 补 0，否则 SUM/AVG 异常。

**案例：PUSH 启动用户的信息流消费（先过滤再关联）**
```sql
SELECT COUNT(DISTINCT a.did) AS push_user,
  ROUND(SUM(COALESCE(b.feed_dura,0))/COUNT(DISTINCT a.did)/60000, 2) AS avg_min
FROM ( SELECT date,did FROM …miui_di
       WHERE date=20260628 AND is_app_dau_2024=1
         AND app_launch_way IN('点击push','subscribe_push') ) a
LEFT JOIN ( SELECT date,did,feed_dura FROM …label_di
       WHERE date=20260628 AND is_dau_feed_dapan_2024=1 AND is_top=0 ) b
  ON a.date=b.date AND a.did=b.did;
```

**JOIN 避坑**：① 一定写 `ON`（漏写 = 笛卡尔积，百万×百万搞挂集群）② 关联字段类型一致 ③ 注意多对多导致数据膨胀 ④ 小表放左边、先过滤再 JOIN。

---

## 三、CTE（WITH 语句）：像搭积木一样写 SQL

```sql
WITH
临时表1 AS ( SELECT … FROM … WHERE … ),
临时表2 AS ( SELECT … FROM 临时表1 JOIN … )
SELECT … FROM 临时表2;
```
> 复杂需求拆成多步，每步逻辑清晰、不易错，而且**让 AI 生成拆分后的 SQL 准确率更高**。典型：PUSH 用户 vs 全体用户对比，拆成「全体 / PUSH / 信息流 / 关联打标 / 聚合对比」5 步。

---

## 四、常见 SQL 错误

| 坑点 | 后果 | 避免 |
|------|------|------|
| 忘加分区 date | 扫全表跑几小时 | 先写 WHERE date |
| JOIN 漏 ON | 笛卡尔积爆炸 | 写完 JOIN 立刻写 ON |
| 多表关联直接 SUM | 数据重复、指标翻倍 | 先验证关联后记录数 |
| 直接 AVG 算人均 | 排除 NULL 用户，偏高 | `SUM(x)/COUNT(DISTINCT did)` |
| 没处理 NULL | 结果变 NULL | `COALESCE(x, 0)` |

### 4.1 案例演示：四个坑的"翻车现场"（带真实数字）

**① JOIN 漏 ON → 笛卡尔积爆炸**
> miui_di 6/28 有 100 万行、label_di 6/28 有 80 万行。
> - ❌ 漏写 ON：每一行都去匹配对面**所有**行 → 100万 × 80万 = **8000 亿行**，集群直接跑挂 / OOM。
> - ✅ 写对 `ON a.date=b.date AND a.did=b.did`：约 80 万行。
>
> 一个 ON 的差别，结果差了 **一百万倍**。

**② 多表关联后直接 SUM → 指标翻倍**
> 用户 d_1001 当天 APP 时长 30 分钟；他在 label_di 里有 3 条记录（图文 / 短视频 / 小视频频道各一条）。LEFT JOIN 后，30 分钟被复制成 3 行：
> ```
> d_1001 | 图文   | app_dura=30
> d_1001 | 短视频 | app_dura=30
> d_1001 | 小视频 | app_dura=30
> ```
> `SUM(app_dura)` = **90** 分钟 → 凭空多了两倍！
> ✅ 正确：关联前先各自聚合到 did 粒度，或对 app_dura 这种"左表指标"去重后再算。

**③ 忘加 date → 扫全表**
> 表保留了 400 天的分区。查 6/28 一天：
> - ✅ 加 `WHERE date=20260628`：只读 **1** 个分区
> - ❌ 忘加 date：读 **400** 个分区 → 数据量、耗时 **翻 400 倍**（从几秒变几小时）

**④ AVG 算人均 → 偏高**
> 10 个活跃用户，其中 5 人有信息流消费（共 100 分钟），5 人没消费（LEFT JOIN 后 feed_dura 是 NULL）：
> - ❌ `AVG(feed_dura)` = 100 / **5** = 20 分钟（AVG 自动跳过 NULL，只算了有消费的人）
> - ✅ `SUM(feed_dura)/COUNT(DISTINCT did)` = 100 / **10** = 10 分钟
>
> 差了整整一倍——这就是为什么"人均"要用 `SUM/人数`，而不是 `AVG`。

---

## 五、SQL 在引擎里到底怎么执行的：MapReduce 模型

模块3 说过"SQL 被引擎拆成分布式任务跑"。这些任务的核心模型叫 **MapReduce**，三个阶段：

| 阶段 | 干什么 | 对应 SQL |
|------|--------|----------|
| **Map（分）** | 把大数据切成很多块，每台机器各处理一块：读数据、过滤、按 key 打标 | `FROM`、`WHERE`、`SELECT` 列 |
| **Shuffle（洗牌/搬运）** | 把 Map 结果**按 key 重新分发**，让"同一个 key 的数据"汇到同一台机器 | `GROUP BY`/`JOIN` 的 key |
| **Reduce（合）** | 每台机器对分到自己这儿的同 key 数据做聚合/关联 | `COUNT/SUM`、`JOIN` |

**一个类比：全国人口普查**
```
Map：    每个村各自统计本村人数        （成千上万个村并行，快）
Shuffle：把同一个省的数据汇总到该省中心  （跨地区搬运，最费时费力）
Reduce： 每个省中心算出本省总人口        （各省并行，快）
```

### 5.1 案例演示：一条 GROUP BY 怎么走完三阶段

需求：`SELECT app_launch_way, COUNT(DISTINCT did) FROM …miui_di WHERE date=20260628 GROUP BY app_launch_way`（按启动方式统计人数）。假设当天数据分在 3 台机器上：

**① Map —— 3 台机器各读一批，各自按启动方式打标**
```
机器1 读到：d1→icon,  d2→push
机器2 读到：d3→icon,  d4→icon
机器3 读到：d5→push,  d6→icon
```
**② Shuffle —— 按 app_launch_way（就是 GROUP BY 的 key）重新分发**
```
icon 的全汇到 机器A：d1, d3, d4, d6
push 的全汇到 机器B：d2, d5
```
**③ Reduce —— 每台机器对分到的同 key 算 COUNT(DISTINCT did)**
```
机器A：icon → 4 人
机器B：push → 2 人
```
> 💡 看清楚了：**GROUP BY 的字段就是 shuffle 的 key**——同一个 key 的数据必须先"搬"到一起才能算。这个"搬"就是 shuffle，也是整条链路最慢的一步。JOIN 同理，只是 key 换成了关联字段 `did`。

> 🎯 关键结论：`SELECT / WHERE / 列映射` 主要在 **Map 阶段** → 天然并行、快；`GROUP BY / JOIN / DISTINCT / ORDER BY` 会触发 **Shuffle** → 慢，是性能瓶颈。**调优的本质，多半就是"和 Shuffle 作斗争"。**

---

## 六、Shuffle：性能瓶颈的根源

**Shuffle = 把数据跨机器"按 key 重新分发"的过程**，涉及**网络传输 + 磁盘读写 + 排序**，是整条链路里最贵的操作。几百 GB 数据在上千台机器间搬来搬去，慢就慢在这。

**哪些操作会触发 Shuffle：**

| 操作 | 为什么要 shuffle |
|------|------------------|
| `GROUP BY` | 要把同一分组的数据凑到一起才能聚合 |
| `JOIN` | 要把两表相同 key 的行凑到一起才能关联 |
| `DISTINCT` | 本质是按值分组去重 |
| `ORDER BY`（全局排序） | 要把所有数据汇总排序 |
| 窗口函数 `OVER(PARTITION BY …)` | 按分区重新分发 |

**减少 Shuffle 代价的思路**（越往前越有效）：先过滤（WHERE）、只带需要的列、先聚合再 JOIN、能不排就不排、避免没必要的 DISTINCT。

### 6.1 案例演示："先聚合再 JOIN"能省多少

需求：算 PUSH 用户的人均信息流时长（miui_di JOIN label_di）。label_di 是明细，当天 5000 万行。

| 写法 | 进 Shuffle 的数据量 | 结果 |
|------|--------------------|------|
| ❌ 直接拿 5000 万行明细去 JOIN | **5000 万行**全进 shuffle | 搬得慢，还容易倾斜 |
| ✅ 先按 did 聚合成 800 万行，再 JOIN | 只有 **800 万行**进 shuffle | shuffle 数据量降 ~6 倍，快很多 |

**对应 SQL 差别：**
```sql
-- ✅ 好：子查询里先 GROUP BY did 聚合，把明细压小，再关联
LEFT JOIN ( SELECT date, did, SUM(feed_dura) AS feed_dura
            FROM …label_di WHERE date=20260628 AND is_top=0
            GROUP BY date, did ) b
  ON a.date=b.date AND a.did=b.did
```
> 💡 一句话：**能少 shuffle 就少 shuffle，非 shuffle 不可时就让它少搬点数据**（先过滤、先聚合、只带需要的列，都是这个道理）。

---

## 七、数据倾斜（Data Skew）：99% 跑完，卡在最后 1%

**现象**：任务大部分 task 很快跑完，个别 task 卡住很久，甚至内存溢出（OOM）失败，进度条常年卡在 99%。

**原因**：某个 key 的数据量特别大。Shuffle 后这个 key 的数据**全汇到一台机器**，它一个人干了别人几百倍的活。

### 7.1 案例演示：一个空 did 怎么拖垮整个任务

两表按 `did` JOIN。数据里有 **3000 万行 did 为空**（埋点丢失 / 未登录的脏数据），正常 did 每个只有几行。

```
Shuffle 按 did 分发：
  空 did（"")   → 全部 3000 万行 全汇到同一台机器！
  正常 did       → 均匀分到上千台机器，每台几万行
```
结果：
- 其他上千个 task：每个 **~30 秒**完成
- 那 1 个处理空 did 的 task：要啃 3000 万行 → 跑 **40 分钟**，甚至 OOM 挂掉
- 现象就是进度条卡在 **99%** 半天不动

**修复**：加一行 `WHERE COALESCE(did,'') != ''` 先过滤掉空 did → **40 分钟变 40 秒**。

> 🔴 常见"大 key"：**did 为空/默认值/测试 id**（最高频）、某个爆款内容 id、某个超热门频道、"其他"兜底分类。遇到卡 99%，**第一反应先查有没有空值/默认值 key**。

**其他解法**（按场景）：

| 方法 | 说明 |
|------|------|
| **过滤脏 key** | 先 `WHERE COALESCE(did,'')!=''` —— 能解决 80% 的倾斜 |
| **小表广播（map join）** | 大表 JOIN 小表时，把小表广播到每台机器，**不用 shuffle**（见第八/九节） |
| **加盐打散** | 给倾斜 key 加随机前缀分散到多台机器，聚合后再合并（进阶，一般交给数据同学） |
| **提前聚合** | 先把明细压成汇总，降低进入 shuffle 的数据量 |

---

## 八、语法与执行调优（写 SQL 时就能做的）

| 调优手段 | 做什么 | 收益 |
|----------|--------|------|
| **分区裁剪** | `WHERE` 带上分区字段 `date` | 只扫需要的分区，**最有效** |
| **列裁剪** | 只 `SELECT` 需要的列，别 `*` | 少读少传 |
| **谓词下推** | 过滤条件尽量早（写进子查询里、靠近表） | 尽早把数据变少 |
| **先聚合再 JOIN** | 明细先 `GROUP BY` 压小再关联 | 大幅减少 shuffle 数据（见 6.1） |
| **小表广播 broadcast/map join** | 小表（一般 <几十 MB）广播到各机器 | 免 shuffle，提速明显 |
| **避免笛卡尔积** | JOIN 必写 `ON`、关联键正确 | 防数据爆炸（见 4.1） |
| **控制 ORDER BY** | 只要 Top N 就 `ORDER BY … LIMIT`，别全局排 | 减少 shuffle |
| **大跨度分步跑** | 查 3 个月以上按月拆开 | 单次任务更稳、更快 |
| **优先 DWM 聚合表** | 别动不动查明细层 | 数据量小几个量级 |
| **小文件治理**（了解级） | 别产出海量小文件 | 减少调度开销 |

**几个"了解级"参数**（日常用默认即可，需要时问数据同学）：

| 参数 | 作用 |
|------|------|
| `spark.sql.shuffle.partitions` | shuffle 后的分区数，默认 200；数据大可调大 |
| `spark.sql.autoBroadcastJoinThreshold` | 小于该大小的表自动走 broadcast join |
| `spark.sql.adaptive.enabled`（**AQE**） | 自适应查询执行，能**自动**优化 shuffle 分区、处理部分倾斜、转 broadcast——现在多默认开启 |

> 💡 现代 Spark 有 AQE 兜底，很多优化引擎会自动做；但**加 date 分区、先过滤、先聚合、避免笛卡尔积**这些"写 SQL 的习惯"，仍然是你自己最该做好的。

---

## 九、Hive vs Spark：我们到底在用哪个

| 维度 | Hive（基于 MapReduce） | Spark SQL |
|------|------------------------|-----------|
| 计算方式 | 每一步中间结果都**落磁盘** | **内存计算 + DAG**（多步串成一张图，省掉中间落盘） |
| 速度 | 慢、但稳 | **快**，主流 |
| 适合 | 超大批处理、稳定性优先 | 交互式分析、日常取数 |
| 我们 | 部分老调度任务 | **Kyuubi 连的就是 Spark SQL，日常主要用它** |

- **DAG（有向无环图）**：Spark 把你 SQL 的多步操作先画成一张"执行流程图"，整体优化后再跑，能合并步骤、少落磁盘——这是它比 Hive 快的关键。
- 语法上两者 **90% 通用**（都是 SQL），少数函数/写法有差异；跑之前留意当前用的是哪个引擎。

---

## 十、看懂执行计划 & 慢查询排查

**用 `EXPLAIN` 看引擎打算怎么跑：**
```sql
EXPLAIN
SELECT … FROM … WHERE date = 20260628 …;
```
重点看三件事：
1. 有没有**全表扫描**（说明没走分区裁剪 → 检查 date 条件）
2. 有没有**大的 Shuffle / Exchange**（JOIN、GROUP BY 前有没有先过滤/聚合）
3. JOIN 是不是走了 **Broadcast**（小表广播，好事）

**跑得慢 / 跑不出来，按这个顺序排查：**
| # | 先看 | 对策 |
|---|------|------|
| 1 | 加 date 分区了吗 | 漏了就是全表扫描，先补上（见 4.1 ③） |
| 2 | JOIN 漏 ON 了吗 | 笛卡尔积，补 ON、检查关联键（见 4.1 ①） |
| 3 | Shuffle 是不是太大 | JOIN/GROUP BY 前先过滤、先聚合、只带需要的列（见 6.1） |
| 4 | 是不是数据倾斜 | 看个别 task 是否卡住 → 先查空值/默认值 key（见 7.1） |
| 5 | 时间跨度太长 | 按月分步跑 |

> 🎯 通用铁律：**先查 1 天验证逻辑，再放大时间范围**；别一直重试占集群资源。

---

## 十一、AI 辅助复杂 SQL（重点）
- **复杂需求拆成步骤喂给 AI**（用什么表、输出什么字段），别一次丢大需求。
- **AI 常见坑修复**：幻觉字段（对照数据地图）、关联漏 date、没处理 NULL、口径错（明确告诉公式）、大表直接关联（拆 WITH、让它先聚合）、人均用了 AVG（改 SUM/COUNT DISTINCT）。
- 还可以让 AI **解释执行计划**：把 `EXPLAIN` 结果贴给它，让它指出"哪里可能有大 shuffle、有没有走分区裁剪、能不能改 broadcast join"。
- 进阶提示词模板见公共资料《AI 写 SQL 提示词模板》。

---

## 本节课小结
1. JOIN 两种：INNER（都匹配）/ LEFT（左表全留），LEFT 后用 COALESCE 补 NULL；JOIN 必写 ON、先过滤再关联。
2. CTE（WITH）把复杂查询拆积木，也让 AI 更准。
3. **执行原理**：SQL → MapReduce（Map 分 / Shuffle 搬 / Reduce 合）；`GROUP BY/JOIN/DISTINCT/ORDER BY` 触发 Shuffle，是瓶颈（案例见 5.1）。
4. **数据倾斜**：某个大 key（多为空值/默认值）拖垮任务 → 先过滤脏 key、小表广播（案例见 7.1）。
5. **调优**：分区裁剪 + 列裁剪 + 谓词下推 + 先聚合再 JOIN + 小表广播 + 避免笛卡尔积；Spark（内存+DAG）比 Hive（MapReduce 落盘）快，日常用 Spark。
6. `EXPLAIN` 看执行计划，慢查询按"分区→ON→shuffle→倾斜→跨度"顺序排查。
7. 复杂 SQL 交给 AI 拆步骤生成 + 人校验。

## 下节课预告
- 模块5《数据分析方法》（🔷进阶）——从"取数"升级到"给结论"，排查问题、漏斗、分群。
