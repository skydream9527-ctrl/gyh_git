# 日报推送 SOP

## 启动检查

1. 先读取 `djy-pool-analysis` skill，确认用户需求属于以下哪类：
   - `daily_report`：完整日报，可能包含飞书推送。
   - `report`：巡检报告，不一定推送。
   - `detail`：脏数据明细导出。
   - `adhoc`：临时规则验证。
   - `consumption`：消费指标分析。
   - `creator_audit`：创作者审核链路校验。
   - `uploaded_sql_daily`：用户上传 SQL 后自动查数并生成 AI 日报。
2. 用户未明确模式时，最多问 3 个澄清问题：日期/周期、SQL 是否已上传或可粘贴、是否需要定时推送。
3. 用户只说“日报推送/自动日报”但没有提供 SQL 时，第一句话先索要 SQL 文件或 SQL 代码；不要先问 Webhook。
4. 只要涉及飞书推送，最终必须提供飞书自定义机器人 Webhook 地址，格式示例：`https://open.feishu.cn/open-apis/bot/v2/hook/57dccdeb-8a90-4710-b186-9c1d4bdf6702`。签名校验密钥选填，格式示例：`UTUraFvQfj5CerVC9YsXeh`。Webhook/签名只在日报内容确认和定时时间确认之后再问；不要把签名密钥写入最终回复、文件标题或日志摘要。

## 强制执行顺序 · SQL 到定时推送

所有“上传 SQL 自动日报 / 自动查数并定时推送 / 日报 agent”类需求必须按下面顺序推进，不得跳步：

1. **索要 SQL**
   - 优先让用户上传 `.sql` 文件；也接受直接粘贴 SQL 代码。
   - 多条 SQL 必须询问业务名称和展示顺序，或按文件名/用户给定顺序处理。
   - 未拿到 SQL 前，不问 Webhook、不创建定时任务、不承诺能推送。

2. **审查并执行 SQL**
   - 只执行只读 `SELECT` / `WITH ... SELECT`。
   - 发现写入/DDL/权限语句立即拒绝，并要求用户改成只读查询。
   - 对日期占位符、目标日期、日报周期、limit/聚合范围先确认，再调用 `kyuubi_query`。
   - 默认每个可查指标都要补齐三组日期：目标日 `D`、前一日 `D-1`、上周同日 `D-7`。优先将日期条件改写为 `IN (D, D-1, D-7)` 并按日期聚合；无法安全改写时分别执行三次同口径 SQL。
   - 默认计算并展示每个指标的日环比和周同比：`日环比 = (D - D-1) / D-1`，`周同比 = (D - D-7) / D-7`。分母为 0、缺失或不可查时标记 `N/A`，并在异常说明里写明原因。
   - 查询后保存：最终 SQL、原始结果、聚合后的日报数据摘要。

3. **组合日报**
   - 将多条 SQL 查询结果合并成统一日报数据模型：指标卡、明细表、趋势/分布、异常、建议动作、数据口径。
   - 每个指标数据结构默认包含：`metric_name`、`category`、`current_value`、`prev_day_value`、`last_week_value`、`unit`、`day_over_day_pct`、`week_over_week_pct`、`status`、`compare_note`。公式指标需分别计算 D/D-1/D-7 三个值后再算环比/同比，不得只用 D 的公式结果推导对比。
   - 样式必须参照 `update_file/ai_djy_pool_analysis-main.zip` 中的 `djy-skill/references/validate/html_report_style.md`、`report_format.md`、`card_template.json` 和 `reports/content_pool_validate_*.html`：
     - 商务简约、高信息密度、浅灰背景、白色卡片、14-18px 圆角、弱阴影。
     - 顶部标题 + 数据截至/口径；核心指标卡；Top/明细表；趋势图；异常/建议动作；页脚口径说明。
     - CP/业务维度用彩色徽章或左边线；涨跌用红绿文字/透明底，不用刺眼渐变；每个指标行默认展示“当前值 / 日环比 / 周同比”三列，核心指标卡也要露出两项变化率。
   - 用 `write_file` / `execute_python` 保存至少两份产物：`daily_report_preview.html` 和 `daily_report_preview.png`。
   - 飞书群推送统一使用“HTML 截图 + HTML 链接”格式：PNG 展示日报主视觉，正文只保留标题、数据日期、异常摘要和 HTML 报告链接；不得再把整份日报 Markdown 表格直接推到群里。

4. **和用户对话调整**
   - 展示日报摘要、关键截图/HTML 文件名、卡片正文预览，询问用户是否需要调整指标、标题、排序、口径、样式、告警阈值或话术。
   - 用户提出调整时，继续修改并覆盖/另存预览产物；直到用户明确确认“内容和样式可以”。
   - 未获得用户确认前，不询问 Webhook、不创建定时任务。

5. **询问定时执行和定时发送时间**
   - 内容确认后，询问是否需要定时执行；若需要，询问执行频率、执行时间、数据日期口径、是否执行后立即发送。
   - 默认建议：每天 09:00 执行昨日数据并生成/发送；cron 为 `0 9 * * *`。
   - 如用户要求“定时执行”和“定时发送”分开，必须在定时任务 prompt 中写明两个时间及动作边界；平台只支持单 cron 时，说明会在一次任务里按用户确认的发送时间逻辑执行或提示限制。

6. **最后收集飞书机器人配置**
   - 在定时时间确认后，才询问飞书机器人 Webhook 地址（必填）和签名校验密钥（选填）。
   - 用户未提供 Webhook 时，不得创建定时任务；只保留已确认的日报预览。
   - 用户提供签名密钥时，仅写入工具调用/定时任务 prompt 必要字段，不在自然语言回复中明文复述。

7. **新增平台定时任务**
   - 以上信息齐全后，必须调用 `create_scheduled_task` 新增平台定时任务。
   - 定时任务 `prompt` 必须完整写入：SQL 来源/最终 SQL 文件名或 SQL 内容摘要、日期口径、查询顺序、数据组合规则、HTML/截图样式要求、用户确认过的日报结构、执行时间、发送时间、Webhook、是否传 `sign_secret`、失败处理、以及“必须先生成 `daily_report_preview.html`，再截图为 `daily_report_preview.png`，最后用 `feishu_send_message(webhook_url=..., sign_secret=..., image_path=..., html_url=...)` 推送 HTML 截图 + HTML 链接；不得推整份 Markdown，不得用 `feishu_publish` 或 `receive_id`”。
   - 创建成功后返回定时任务名称、cron、下次执行时间、Webhook 尾号、产物文件清单和后续修改入口。

## uploaded_sql_daily · 上传 SQL 自动日报

当用户上传 `.sql` 文件，或说“按我上传的 SQL 跑日报 / 自动查数 / 生成 AI 日报”时，按下面流程执行：

1. **发现 SQL 文件**
   - 调 `list_files(scope="uploaded")` 找到用户上传文件。
   - 只读取 `.sql` / `.txt` 中明确为 SQL 的文件；多个 SQL 文件按文件名排序，并给用户列出清单。
   - 调 `read_file(name="<文件名>")` 读取 SQL 原文。

2. **SQL 安全与口径审查**
   - 只允许 `SELECT` / `WITH ... SELECT` 查询。
   - 发现 `INSERT`、`OVERWRITE`、`CREATE`、`DROP`、`ALTER`、`DELETE`、`UPDATE`、`TRUNCATE`、`MERGE`、`CALL`、`GRANT`、`REVOKE` 等写入或权限语句时，立即拒绝执行，并说明要改成只读 SELECT。
   - 检查是否有明确日期分区或时间范围；没有时先问用户目标日期/日报周期。
   - 检查是否缺少 `LIMIT` 或结果可能过大；必要时先加采样/聚合/limit 预跑，不能盲目拉全量明细。
   - 检查 SQL 中日期占位符：`${date}`、`${yesterday}`、`{{date}}`、`<YYYYMMDD>` 等；替换前必须向用户确认日期。

3. **执行查询**
   - 用 `kyuubi_query(sql=<审查后的 SQL>)` 执行。
   - 每个 SQL 都保存两份产物：
     - `sql/<序号>_<业务名>.sql`：最终执行 SQL。
     - `data/<序号>_<业务名>.csv` 或 JSON 摘要：查询结果。
   - 行数为 0、关键字段缺失、分母为 0 或查询失败时，不继续生成日报；先解释问题并给修改建议。

4. **AI 日报生成**
   - 汇总所有查询结果，生成日报结构：
     - 标题：`<业务名>日报 <YYYY-MM-DD>`
     - 一句话结论
     - 核心指标看板
     - 每个指标默认展示日环比和周同比，必要时再补充目标差异
     - 异常与告警
     - 原因假设
     - 建议动作
     - 数据口径与 SQL 产物链接/文件名
   - 若结果包含时间序列或维度分布，优先用 `execute_python` 生成 PNG 图表并写入 `charts/`。
   - 所有数字必须可追溯到某个 SQL 结果文件；报告中不要出现无法追溯的数值。

5. **预览调整与定时配置**
   - 必须进入“强制执行顺序 · SQL 到定时推送”的第 4-7 步：先让用户确认日报内容/样式，再问定时时间，最后问 Webhook/签名，并调用 `create_scheduled_task`。
   - 如果用户只想立即发送一次，也必须先确认日报预览，再收集 Webhook/签名，最后生成 HTML 截图并调用 `feishu_send_message(title, content, webhook_url, sign_secret?, image_path, html_url)`；不要推整份 Markdown，不要调用 `feishu_publish` 创建飞书文档，不要使用应用机器人私聊 `receive_id`。

## daily_report 标准流程

当用户明确要求“推送/发到飞书/发群”时：

1. 确认日期，默认昨日；若补跑历史，要求用户给 `YYYYMMDD`。
2. 如果用户还没提供 SQL 或未完成查数，先回到“强制执行顺序”第 1 步索要 SQL；不要先问 Webhook。
3. 读取 `djy-pool-analysis` 的日报流程说明，按其 10 步流水线执行或复述执行计划。
4. 优先使用 skill 内置脚本/SQL 的既有口径；如果当前工具无法直接执行 shell 脚本，则改用平台工具完成可复现的等价步骤：
   - `kyuubi_query` 执行校验/消费 SQL。
   - `execute_python` 生成图表、HTML、卡片 JSON 或长图。
   - `write_file` 保存 SQL、CSV、HTML、JSON 等文本产物；`execute_python` 生成并登记 PNG 截图等二进制产物。
   - `feishu_upload_image` 上传长图。
   - `feishu_send_message(webhook_url=..., sign_secret=..., image_path=..., html_url=...)` 发送“日报 HTML 截图 + HTML 链接”；未启用签名校验时不传 `sign_secret`。
5. 发布前自检：
   - 日期正确。
   - 4 家 CP 范围正确。
   - 规则命中数量和异常解释一致。
   - 消费指标单位正确，尤其 `consum_dura` 分钟转秒。
   - HTML/长图/飞书卡片可追溯；飞书群消息必须包含 HTML 截图和 HTML 链接。
   - 已取得用户确认的飞书机器人 Webhook；如启用签名校验，已取得密钥但不展示。
6. 推送后给用户返回：日期、推送目标 Webhook 尾号/群名、消息发送状态、异常摘要、产物文件列表。

## 巡检和明细

- `report`：先说明查询口径，再生成 4 段式巡检结论：总体结论、规则命中、CP 分布、处理建议。
- `detail`：必须说明导出字段、筛选条件、文件路径；大文件只给摘要和文件引用。
- `adhoc`：展示 SQL 与口径，获得确认后执行；结果必须说明是否可推广到日报规则。

## 消费分析

1. 明确时间范围、CP/频道/实验组等维度、指标集合。
2. 读取 skill 中 consumption 维度和指标说明。
3. SQL 必须带日期分区，优先输出 CSV 和可视化图。
4. 对环比/同比变化给出业务解释，不能只贴表。

## 创作者审核链路

1. 先要求用户提供第一批/第二批签约名单 CSV，或说明文件位置。
2. 按 skill 的三步逻辑：签约名单 → 审核表 → 内容池 → 签约清单回验。
3. 输出必须包含匹配键、豁免规则、未命中清单、建议处理动作。

## 派单规则

- 需要都江堰宽表下钻、实验组对比或消费归因时，可派给 `zijian-data-analysis`。
- 需要跨业务大盘对照时，可派给 `data-analysis`。
- 需要飞书知识归档、文档位置、权限或知识库沉淀时，可派给 `know`。

派单 prompt 必须自包含：日期、表名、SQL 口径、当前产物文件和需要对方返回的结论格式。
