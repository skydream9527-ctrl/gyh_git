# skills/ — 本地 Skill 目录

本目录存放项目可发现的 agentic skills。后端启动时通过 `skills/*/SKILL.md`
自动识别，任务创建时会快照到 `tasks/{tid}/skills/`，运行中通过
`read_skill(skill_id=...)` 读取说明并按步骤执行。

## 当前清单

| Skill | 用途 |
|---|---|
| `daily-news-collector` | 每日科技新闻收集、筛选与分发 |
| `data.an` | 数据查询、分析报告、可视化和飞书交付 |
| `datum-cli` | datum CLI 使用说明 |
| `docx` | Word / docx 文档生成与处理 |
| `feishu` | 飞书文档 / 多维表格 / 图片等 CLI 能力 |
| `feishu-pyramid-writer` | 按金字塔原理撰写飞书文档 |
| `kyuubi` | Kyuubi SQL 查询 |
| `mify-knowledge-base` | Mify 知识库创建、上传、更新和搜索 |
| `mify-model-gateway` | 小米 Mify 大模型网关查询、测试和接入 |
| `nl-mapping-table-sql` | 自然语言生成映射表 SQL |
| `nl-python` | Python 数据分析和可视化 |
| `pdf` | PDF 读取、转换和生成 |
| `pptx` | PPTX 生成与处理 |
| `schedule-send` | 定时日报发送到飞书多维表格 |
| `sql` | 数据工场 DataWorks SQL 查询 |
| `text2html2png` | 文本生成 HTML 图表并截图为 PNG |

## 子目录约定

```text
skills/{skill_id}/
├── SKILL.md            # 必需：frontmatter + 使用说明
├── INTRO.zh.md         # 必需：中文展示简介
├── scripts/            # 可执行脚本（可选）
├── references/         # 参考资料（可选）
└── assets/             # 资源（可选）
```

## 调用方式

这些 skill 不是独立 function tool。Agent 需要先调用：

```text
read_skill(skill_id="<skill_id>")
```

如果 `SKILL.md` 指向同目录参考资料，再用：

```text
read_skill(skill_id="<skill_id>", path="references/example.md")
```

任务内只能读取该任务已绑定并快照的 skill；新建任务默认会注入当前目录下的
agentic skills，已有任务可在工作区右栏 Skills 面板添加。
