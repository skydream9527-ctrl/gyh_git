#  日报模式（独立跑数 + 飞书推送）

> **2026-05-11 起：飞书卡片简化为「长图版」** — 只推 HTML 整页长图 + 报告链接 + 脚注，取消旧的 7 张图拼装 + 4 段式 Markdown。所有图表细节从 HTML 截图里直接可见（点击图片可放大）。

## ⚠️ 当前抑制清单（2026-04-28 起）

以下异常**先不纳入日报卡片**，等服务端刷数恢复后由用户明确解除：

- **规则 20（三元 ID 映射不唯一）**：结果被 `xm_author_id` 空值污染，数字虚高（dihui 25.9 万、guoying 48 万、beike 9.2 万、meilaoban 1.9 千条被标），等服务端历史数据补齐 `xm_author_id` 后再放开

规则 11 (`xm_author_id` 非空) 本身继续纳入日报。

## 目录
- [与其他模式的隔离原则](#与其他模式的隔离原则)
- [执行流程](#执行流程)
- [飞书卡片结构（长图版）](#飞书卡片结构长图版)
- [旧版 7 图拼装方案（已弃用，保留回退）](#旧版-7-图拼装方案已弃用保留回退)

## 与其他模式的隔离原则

**日报 ≠ 临时查询**。用户需求"日报独立跑数，和其他查询场景隔离开"，具体含义：

| 场景 | 触发 | 数据范围 | 输出 |
|---|---|---|---|
| **daily_report**（本模式） | 用户**明确**说"推日报到群"/"推送到飞书群"/"发群里"/"日报发飞书"/调度定时任务显式调用 | 必须覆盖**全部 4 家 CP**、**全部规则**、**全量存量**口径 | 飞书 post + 必要时导 CSV |
| report（见主 SKILL） | 用户说"盘点一下"/"当前状态如何" | 按用户指定范围（可单家 CP / 单规则） | Markdown 4 段式 |
| detail | 用户要 CSV 明细 | 特定 CP + 特定规则 | `$DJY_OUTPUT_ROOT/dirty/*.csv` |
| adhoc | 临时假设验证 | 单规则 | 命中率 + 样本 |

**关键区别**：日报不能被临时查询污染（比如用户刚问完"beike publish_time 怎么样"，不能认为日报只跑那个字段）。日报**永远是完整盘点**，即使用户只关心部分字段。

## 执行流程

### Step 1 · 确认 webhook 配置

**默认从 skill 根目录 `.env` 自动加载**（权限 600）：
```
# /Users/mi/.claude/skills/djy-pool-analysis/.env
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/{id}
FEISHU_SECRET={secret}
```

`feishu_post.py` 会在运行时自动读取（缺失任一 key 时报错退出）。命令行 env var 可覆盖 `.env` 值，便于临时测试。

**换群**：编辑 `.env` 换 URL + secret，`chmod 600 .env` 保持权限。

### Step 1.5 · 跑消费数据

消费数据概览放在日报图表 HTML **最顶部**（内容池图表之前），含 CP 维度环比表格 + Top5 内容。

**HTML 样式**：日报产出的 HTML 报告必须遵循 [html_report_style.md](html_report_style.md) 定义的样式规范（素净浅灰底、CP 专属配色徽章、涨跌幅度渐变色、Top5 并排固定行高对齐、14px 圆角卡片等）。参考实现：`~/Desktop/ai_djy_pool_analysis/reports/content_pool_validate_20260507.html`。

```bash
cd ~/.claude/skills/djy-pool-analysis/scripts/consumption
python3 consumption_daily_card.py
# stdout 输出 JSON 路径（如 ~/Desktop/ai_djy_pool_analysis/tmp/consumption_20260505.json）
# 可选参数：--date YYYYMMDD（默认昨天）
```

生成的 JSON 传给 [Step 2.5](#step-25--生成-html-报告) 的 `chart_gen_html.py` 作为第 5 个参数，即可合并到图表 HTML 中统一截图。

### Step 2 · 跑四家 CP 全量数据

按 skill 禁用缓存铁律，**必须**真实执行 SQL。统一走 `run_validate_sql.py`（自动注入 exemptions.json 的豁免 + 去注释 + 合并换行）：

```bash
cd ~/.claude/skills/djy-pool-analysis

# 1. Template A（全字段扫描）
python3 scripts/run_validate_sql.py template_a_stock.sql

# 2. Rule 20（作者映射）
python3 scripts/run_validate_sql.py rule20_author_mapping.sql

# 3. （建议）按 create_time 维度的 7 天趋势，自己手写 SQL 通过 stdin 跑：
#    注意：date 是分区键，不是入库时间；必须用 create_time 做趋势聚合
echo "SELECT a_cp, from_unixtime(cast(create_time as bigint)/1000, 'yyyy-MM-dd') AS create_date,
  COUNT(*) AS total,
  SUM(CASE WHEN author_image IS NULL OR author_image = '' THEN 1 ELSE 0 END) AS author_image_n,
  SUM(CASE WHEN xm_author_id IS NULL OR xm_author_id = '' THEN 1 ELSE 0 END) AS xm_author_id_n
  FROM paimon_zjyprc_hadoop.browser.business_content_pool_realtime
  WHERE a_cp IN ('cn-dihui-djy','cn-beike-djy','cn-guoying-djy','cn-meilaoban-djy')
    {{EXEMPT_FILTER}}
    AND from_unixtime(cast(create_time as bigint)/1000, 'yyyy-MM-dd') >= '<7 days ago>'
  GROUP BY a_cp, from_unixtime(cast(create_time as bigint)/1000, 'yyyy-MM-dd')
  ORDER BY a_cp, create_date" | python3 scripts/run_validate_sql.py -

# 4. 若规则 12/13 命中 > 0，对命中 CP 跑豁免验证（exemption_check.sql 不含 item 级豁免占位符，按原流程跑）
arch -arm64 /usr/bin/python3 ~/.claude/skills/data-sql/scripts/sql_query_tool.py \
  "$(sed 's/--.*$//' scripts/exemption_check.sql | sed 's/{{CP}}/cn-beike-djy/g' | tr '\n' ' ')"
```

### Step 2.5 · 生成 HTML 报告

用 `chart_gen_html.py` 把 stock/daily 趋势 CSV + 消费 JSON 合成一份 HTML（顶部消费概览 + 内容池趋势 + 每家 CP 字段明细）：

```bash
python3 $SKILL/scripts/shared/chart_gen_html.py \
    "$STOCK_CSV" "$DAILY_CSV" "$YESTERDAY" "$HTML_PATH" "$CONSUM_JSON"
# 产出 HTML_PATH=$ROOT/reports/content_pool_validate_${YESTERDAY}.html
```

样式规范见 [html_report_style.md](html_report_style.md)。T-1 锚定约定：文件名 = 数据日期（`YYYYMMDD`=T-1），跑数日 `TODAY` 不出现在文件名中。

### Step 2.6 · HTML 截长图

使用 Playwright（通过 `channel=chrome` 调用系统 Chrome，无需额外下载浏览器）截整页长图：

```bash
mkdir -p "$ROOT/charts"
LONGPNG="$ROOT/charts/daily_${YESTERDAY}_$(date +%H%M%S).png"  # 用时间戳避开 Read 工具图片缓存
/usr/bin/python3 $SKILL/scripts/shared/chart_html_to_longpng.py "$HTML_PATH" "$LONGPNG"
# 产出 1500×3000+ px、2x HiDPI PNG，约 2-3 MB
```

**为什么不用旧的 `chart_html_to_png.py`**：旧脚本把 HTML 拆成 7 张独立 card 图分别截（依赖 Chrome headless `--screenshot`），在飞书卡片里堆成 4 段+图列表，结构复杂、维护成本高。长图方案：HTML 整页一张图，点击可在飞书里放大查看所有图表细节。

### Step 3 · 上传飞书图床 + 组装「长图版」卡片 JSON

```bash
IMG_KEY=$(arch -arm64 /usr/bin/python3 $SKILL/scripts/shared/feishu_upload_image.py "$LONGPNG")

arch -arm64 /usr/bin/python3 $SKILL/scripts/shared/build_longpng_card.py \
    --image-key "$IMG_KEY" \
    --date "$YESTERDAY" \
    --report-url "$REPORT_URL" \
    > "$REPORT_PATH"
```

**卡片结构**（由 `build_longpng_card.py` 生成，2026-05-11 精简版）：

| 位置 | 元素 | 内容 |
|---|---|---|
| header | `title` | `📊 djy 内容池校验 · 日报 · YYYY-MM-DD` |
| header | `subtitle` | `数据截至 YYYY-MM-DD · 口径=全量存量 · 点击图片可放大` |
| header | `template` | `blue`（当前版本未做整体严重度着色，都是蓝；未来可按异常数着色） |
| elements[0] | `img` | HTML 整页长图 · `mode=fit_horizontal` + `preview=true` |
| elements[1] | `div (lark_md)` | `📎 [查看完整 HTML 报告（含交互图表）](pages_url)` |
| elements[2] | `hr` | 分隔线 |
| elements[3] | `note` | 数据源 + 豁免说明 + 跑数时间 |

### Step 4 · 推送到飞书

```bash
REPORT_PATH="$REPORTS/${TODAY}.json"
arch -arm64 /usr/bin/python3 $SKILL/scripts/shared/feishu_post.py "$REPORT_PATH"
```

返回 `{"code": 0, "msg": "success"}` 即推送成功。配置通过根目录 `.env` 自动加载 `FEISHU_WEBHOOK` / `FEISHU_SECRET` / `FEISHU_APP_ID` / `FEISHU_APP_SECRET`。

## 飞书卡片结构（长图版）

### 飞书 img 元素关键参数

| 参数 | 值 | 说明 |
|---|---|---|
| `tag` | `img` | 固定 |
| `img_key` | `img_v3_...` | 来自 `feishu_upload_image.py` 上传返回 |
| `mode` | `fit_horizontal` | 适配卡片宽度，长图自动按比例缩放。备选：`crop_center`（裁剪）、`stretch_width`（拉伸铺满）、`custom_width`（配合 `custom_width` 参数） |
| `preview` | `true` | 允许点击放大、缩放、保存 — 长图必备，否则用户看不清细节 |
| `alt` | `{"tag":"plain_text","content":"..."}` | 无障碍文案，也用于截图预览占位 |

### feishu_post.py 已处理的踩坑

| 限制 | 处理方式 |
|---|---|
| 空段落 → `code 19002 params error` | 脚本自动过滤空字符串行 |
| text tag 加 `style: ["bold"]` → `19002` | 不使用 style，用 emoji / 分隔符代替 |
| plain_text 不支持 markdown | 标题/脚注只用普通文字；格式化只在 lark_md 元素里用 |
| lark_md 不支持原生 markdown 列表/标题 | 用 `·` 代替 bullet，用 `**粗体**` 代替标题 |

## 旧版 7 图拼装方案（已弃用，保留回退）

2026-05-11 之前用的复杂方案：

- **截图**：`chart_html_to_png.py` 把 HTML 拆 7 张 card 图（c0 消费 + c1~c6 内容池）
- **组装**：`build_chart_card.py` 拼成 4 段式（Top 3 / CP 总览 / CP 明细 / 趋势图 / 脚注），飞书卡片 elements 多达 15+
- **脚本保留**：`chart_html_to_png.py` + `build_chart_card.py` 暂不删除，万一长图方案有问题可以回退（但 prompt 和 skill 文档不再指向它们）

**弃用原因**：
- 维护成本高（修改一次 HTML 模板要同步改 4 段式卡片代码）
- 6 张独立图视觉上碎片化，用户要上下滑多次才能看全
- 长图方案一张图全覆盖，点击放大看细节体验更好

## 历史趋势对比

长图版不再生成"Top 3 趋势"独立文字段 — HTML 报告里的 7 天折线图已经直观展示每日变化，点击长图放大即可查看具体数值。

若需要文字版"相比上次日报"对比：HTML `chart_stock_trend.sql` 的 7 天 cutoff 趋势可直接读出，但目前卡片不渲染。

### 2026-05-25 stock 累计口径切换

`chart_stock_trend.sql`（图二 bad_any + 图三~六 每字段存量趋势）从 paimon 分区键 `date <= cutoff` 切到 `from_unixtime(create_time) <= cutoff`：
- **原因**：paimon upsert 表的 `date` 字段会随 CP 重推内容更新到最新推送日；CP 5/22-5/25 持续重推 4/29 老内容且把 `author_image` 字段置空时，`date <= cutoff` 累计计数虚涨（beike image_empty 5/21→5/25 +597），但按 create_time 口径看新内容 0 异常。
- **影响**：5/25 之前的 stock 曲线与之后**不可比**；切换后曲线反映"实际入库时间累计的异常",与图一（c1 daily 增量）口径对齐。
- **CP 重推老内容并置空字段**这类场景仍需要监控，但应通过 ad-hoc 查询（按 `date` 分区拉清单）而非日报趋势图。

### 2026-05-26 在线池口径切换 + 三元 ID 趋势

接续 5/25 的 create_time 切换，进一步把 **c2~c6 + 健康卡 + template_a 主校验** 切到**在线池**口径（`online='1' AND delete_reason 空`），并在 c3~c6 加两条三元 ID 一致性曲线：

**改动**：
| 区域 | 改动前 | 改动后 |
|---|---|---|
| 健康卡"当前异常字段总条数" | 全量含下线（244,059）| 在线池（199,826）|
| c2 累计趋势 | 全量 | 在线池 |
| c3~c6 每 CP 趋势 | 14 个字段 全量 | 14 个字段 + 2 个三元 ID 字段，全部在线池 |
| c1 每日入库量 | 全量 | **不变**（仍全量，看 CP 推送节奏）|
| template_a 4 段式校验 | 全量 | 在线池 |

**新增字段**：
- `cp_author 多 xm`（multi_xm_authors_n）：旗下 ≥2 个 xm_author_id 的 cp_author 数
- `lead 多 cp_author`（multi_cp_leads_n）：旗下 ≥2 个 cp_author_id 的 lead 数

**新增 SQL**：[chart_id_consistency_trend.sql](../../scripts/validate/chart_id_consistency_trend.sql) · 7 cutoff × 4 CP × 在线池，~100s pyhive

**与历史不可比**：5/26 前后健康卡 + c2~c6 数字均断裂；后续推 CP 群清单 / template_a 主校验数字一致，可直接对照。

## 补发机制（缺失日回溯）

crontab 每日 09:45 触发，电脑关机/休眠会错过。恢复日跑时需要整合缺失日数据，做法见 `djy-daily-prompt.txt` Step 0：

- 判定：扫近 7 天（受 `.daily_since` 起点限制），缺失 = 当日 JSON 不存在
- 回溯：缺失日的数据**只能**用 `create_time` 切片查询（业务池是 upsert 表，字段会被覆盖，无法重建"历史时点当时全库状态"）
- 输出：长图版下，补发说明需要渲染到 **HTML 顶部**（在消费概览之前），这样截长图时自然带上。目前 `chart_gen_html.py` 暂不支持补发 section，需要手动改 HTML 或扩展脚本（TODO）。手动补跑单日日报时，按 `YESTERDAY` 重跑即可（见 [daily_report 单日补跑](#补发机制缺失日回溯) 流程）。

这套机制不需要存 snapshot/csv，纯 SQL 实时跑。
