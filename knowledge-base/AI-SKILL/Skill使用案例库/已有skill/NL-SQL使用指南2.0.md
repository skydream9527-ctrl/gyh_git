# NL-SQL使用指南2.0

> 来源: https://mi.feishu.cn/wiki/Nb6iwoyaZisMXmkbYzYcCi2Qnqd

# NL-SQL 使用指南（2.0）

## 1、简介

### 什么是 NL-SQL？

NL-SQL 是一个**自然语言转 SQL** 的技能，帮助用户通过自然语言描述快速生成标准 SQL 查询语句，无需手写复杂 SQL。

### 核心能力

| 能力 | 说明 |
|-|-|
| 🎯 自然语言输入 | 用日常语言描述需求，自动转换为 SQL |
| 📊 多业务线支持 | 浏览器主端、浏览器信息流、内容中心、搜索、小说、竞对 |
| 📈 核心指标查询 | DAU、消费UV、VV、时长、留存等聚合指标 |
| 📝 埋点数据查询 | 事件级数据查询，支持 UV/PV 统计 |
| ✅ 指标校验 | 自动校验指标/事件是否在支持范围内 |

---

## 2、安装前置依赖

### 2.1 安装 Mi Code CLI

MacOS / Linux / WSL / Matrix 实例，在终端运行：

```Bash
bash -c "$(curl -fsSL https://cnbj1-fds.api.xiaomi.net/mi-code-public/install.sh)"
```

### 2.2 安装依赖 Skill

```Bash
micode skills add user_gongyunhe/nl-sql -i # 自然语言生成SQL
micode skills add ai-team/feishu -i         # 写飞书文档（可选）
micode skills add ai-team/data-sql -i       # 查数据工坊（可选）
```

### 2.3 获取数据工坊 Token

1. 登录数据工厂：https://data.mioffice.cn/workspace/?wid=11329#/workspace/11329/config
2. 生成新 Token，复制保存
3. 配置环境变量：

```Bash
export DATAWORKS_TOKEN_ID="your_token_here"
```

### 2.4 申请表权限

常用数据表（需提前申请权限）：

- `iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di`
- `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442`
- `iceberg_zjyprc_hadoop.newhome.dwm_newhome_event_aggregation_label_di`
- `iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000297`

---

## 3、使用方法

### 3.1 启动 Mi Code

```Bash
mkdir -p ~/micode && cd ~/micode
micode
```

### 3.2 执行 NL-SQL Skill

在 Mi Code 对话框中输入：

```Plain Text
执行 nl-sql
```

或直接描述需求：

```Plain Text
帮我查一下浏览器主端近7天的DAU
```

### 3.3 交互流程

**Step 1：选择业务线**

```Plain Text
请选择您要查询的业务：
1. 浏览器主端
2. 浏览器信息流
3. 内容中心
4. 搜索
5. 小说
6. 竞对
```

**Step 2：选择数据类型**

```Plain Text
请选择查询的数据类型：
1. 核心指标（Core Metrics）
2. 埋点数据（Event Tracking）
```

**Step 3：描述需求**

核心指标示例：

```Plain Text
我要查近7天的浏览器主启DAU，按天分组
```

埋点数据示例：

```Plain Text
事件：homepage_setting_expose
时间：近一个月
指标：UV、PV
```

**Step 4：确认并生成**

系统会展示映射结果，确认后生成 SQL。

---

## 4、使用示例

### 示例 1：查询核心指标

**用户输入**：

```Plain Text
执行 nl-sql
→ 选择：1. 浏览器主端
→ 选择：1. 核心指标
→ 输入：近7天的浏览器分启动方式DAU
```

**生成 SQL**：

```Scala
SELECT
    date,
    app_launch_way,
    COUNT(DISTINCT did) AS uv
FROM
    iceberg_zjyprc_hadoop.browser.dwm_browser_event_aggregation_label_di
WHERE
    date >= '20260324'
    AND date <= '20260330'
    AND is_app_dau_2024 = 1
GROUP BY
    date,
    app_launch_way
ORDER BY
    date,
    uv DESC
;
```

### 示例 2：查询埋点数据

**用户输入**：

```Plain Text
执行 nl-sql
→ 选择：1. 浏览器主端
→ 选择：2. 埋点数据
→ 输入：事件 homepage_setting_expose，近一个月的 UV、PV
```

**生成 SQL**：

```Scala
SELECT
    date,
    COUNT(DISTINCT distinct_id) AS uv,
    COUNT(*) AS pv
FROM
    iceberg_zjyprc_hadoop.dw.dwd_ot_event_di_31000000442
WHERE
    date >= '20260228'
    AND date <= '20260330'
    AND event_name = 'homepage_setting_expose'
GROUP BY
    date
ORDER BY
    date
;
```

---

## 5、支持的指标范围

### 5.1 核心指标

| 业务线 | 支持指标示例 |
|-|-|
| 浏览器主端 | 主启DAU、有效DAU、三方调起DAU、分启动方式DAU |
| 浏览器信息流 | 消费UV、消费VV、人均消费时长、深度消费UV |
| 内容中心 | 内容消费UV、内容曝光VV、人均消费篇数 |
| 搜索 | 搜索UV、搜索PV、点击率 |
| 小说 | 阅读UV、阅读时长、完读率 |
| 竞对 | 竞品对比指标、市场份额 |

### 5.2 埋点事件

| 业务线 | 支持事件数量 |
|-|-|
| 浏览器主端 | 802 个事件 |
| 浏览器信息流 | 802 个事件 |
| 内容中心 | 191 个事件 |

> 💡 可通过索引文件查看完整指标/事件列表

---

## 6、三要素组合模型

NL-SQL 采用**业务线 + 指标 + 维度**三要素灵活组合的模式。

### 6.1 三要素定义

| 要素 | 作用 | 决定内容 | 灵活性 |
|-|-|-|-|
| **业务线** | 数据来源 | 使用哪个表 | 固定 |
| **指标** | 核心逻辑 | 过滤条件 + 聚合方式 | 固定 |
| **维度** | 分组视角 | GROUP BY 字段 | **灵活组合** |

### 6.2 组合示例

| 用户需求 | 业务线 | 指标 | 维度 | 生成逻辑 |
|-|-|-|-|-|
| 浏览器DAU | 浏览器主端 | DAU | date | 基础查询 |
| 浏览器分新老用户DAU | 浏览器主端 | DAU | date + is_new_2024 | 增加维度分组 |
| 浏览器MAU | 浏览器主端 | MAU | 无 | 月活聚合 |
| 浏览器分新老用户MAU | 浏览器主端 | MAU | is_new_2024 | **灵活组合** |
| 浏览器分启动方式DAU | 浏览器主端 | DAU | date + app_launch_way | 增加维度分组 |

### 6.3 常用维度字段

| 维度 | 字段名 | 取值示例 | 说明 |
|-|-|-|-|
| 新老用户 | `is_new_2024` | 1/0 | 1=新用户，0=老用户 |
| 启动方式 | `app_launch_way` | 点击icon/第三方调起/push | APP启动来源 |
| 日期 | `date` | 20260330 | 分区字段 |
| 机型 | `model` | Redmi K50 | 设备型号 |
| 版本 | `app_ver` | 15.5.0 | APP版本 |
| 省份 | `province` | 北京/上海/广东 | 地理位置 |
| 渠道 | `feed_channel` | 推荐/热点 | 信息流频道 |

---

## 7、执行 SQL

生成 SQL 后，可通过以下方式执行：

### 方式 1：数据工坊

🔗 https://data.mioffice.cn/workspace/?wid=11329#/workspace/11329/adHoc

将 SQL 复制到数据工坊执行。

### 方式 2：命令行（需配置 Token）

```Bash
DATAWORKS_TOKEN_ID=your_token python3 scripts/sql_query_tool.py --file query.sql
```

---

## 8、常见问题

### Q1：提示"指标不支持"怎么办？

**原因**：请求的指标不在当前索引范围内。

**解决方案**：

1. 查看系统推荐的相似指标
2. 联系开发者 **gongyunhe** 添加指标支持

### Q2：如何查看支持的指标列表？

索引文件位置：

- 指标名称：`reference/browser-main/metric-name-index.md`
- 事件名称：`reference/browser-main/event-name-index.md`

### Q3：SQL 执行报错怎么办？

常见原因：

1. **权限不足**：申请对应表的访问权限
2. **Token 过期**：重新生成数据工坊 Token
3. **日期格式错误**：确保使用 `YYYYMMDD` 格式

### Q4：如何灵活组合维度？

**解决方案**：

- 指标核心逻辑固定，不可随意修改
- 维度可以灵活组合，根据需求调整 GROUP BY
- 例如：DAU + 新老用户维度 = 按新老用户分组的 DAU

---

## 9、参考链接

- [Mi Code CLI 使用说明书](https://micode.mioffice.cn)
- [Mi Code Hub（AI 工具链平台）](https://micode.mioffice.cn/#/skills)
- [数据工坊平台](https://data.mioffice.cn)

---

## 10、联系开发者

如有问题或需求，请联系：**gongyunhe**