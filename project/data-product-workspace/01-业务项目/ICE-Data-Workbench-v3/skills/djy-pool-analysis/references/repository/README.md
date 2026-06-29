# ai_djy_pool_analysis

都江堰内容池日报系统。一个仓库**同时管两件事**：

1. **每日日报产物**：HTML 报告 / 飞书卡片 JSON 归档 / 脏数据 CSV
2. **日报 skill 代码**：每天 10:30 由 cron 触发的 10 步流水线代码（`djy-skill/`）

GitLab Pages 在线查看：`http://ai-djy-pool-analysis-4bbd9e.pages.n.xiaomi.com/content_pool_validate_<YYYYMMDD>.html`

---

## 仓库结构

```
.
├── README.md              # 本文件
├── .gitignore             # 屏蔽 .env / 凭证 / charts/ / tmp/ 等
├── .gitlab-ci.yml         # GitLab Pages 配置（仅 publish reports/）
│
├── djy-skill/             # ✨ skill 代码（macOS/Ubuntu 共用）
│   ├── SKILL.md
│   ├── bin/               # cron 包装脚本（4 个 djy-daily-*.sh）
│   ├── scripts/           # consumption / validate / creator_audit / shared
│   ├── references/
│   ├── exemptions.json
│   └── README.md          # skill 说明（部署 / 用法 / 环境变量）
│
├── reports/               # 📄 每日日报 HTML（GitLab Pages 发布源）
├── daily_reports/         # 飞书卡片 JSON 归档
├── dirty/                 # detail 模式脏数据 CSV
│
├── scripts/               # 仓库自身的 git hooks（不是 skill 代码）
│   ├── install-hooks.sh
│   └── pre-commit-secrets-check.sh
│
├── charts/                # ⚠️ gitignore（长图 PNG）
├── tmp/                   # ⚠️ gitignore（中间 SQL 结果）
└── logs/                  # 本机日志（不入 git）
```

`djy-skill/` 跟 `scripts/` 区分开：
- `djy-skill/scripts/` 是日报跑数代码（Python / SQL）
- 仓库根 `scripts/` 是 git hooks（防止凭证误提交）

---

## 当前部署

| 角色 | 主机 | skill 路径 | 项目目录 |
|---|---|---|---|
| 开发 + 备用 | macOS（mi 本机） | `~/.claude/skills/djy-pool-analysis` → symlink → `~/Desktop/ai_djy_pool_analysis/djy-skill` | `~/Desktop/ai_djy_pool_analysis` |
| 生产 cron | Ubuntu（mi@10.192.45.120） | `~/.claude/skills/djy-pool-analysis` → symlink → `~/ai_djy_pool_analysis/djy-skill` | `~/ai_djy_pool_analysis` |

cron 每天 10:30 在 Ubuntu 触发，跑 `djy-skill/bin/djy-daily-report.sh`。

---

## 日常工作流

### 改 skill 代码

```bash
# 1. 在 macOS 上改文件（路径走 symlink 或直接走 Desktop）
vi ~/.claude/skills/djy-pool-analysis/scripts/validate/template_a_stock.sql

# 2. 提交并推送
cd ~/Desktop/ai_djy_pool_analysis
git add djy-skill/
git commit -m "改了某 SQL 校验规则"
git push origin main

# 3. Ubuntu 上拉取（任何时候，下次 cron 跑生效）
ssh mi@10.192.45.120 'cd ~/ai_djy_pool_analysis && git pull'
```

### 手动跑日报（测试 / 补跑）

```bash
# 完整流程（推飞书 + push HTML 到 Pages）
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-report.sh

# 只跑不推（验证用）
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-run.sh --skip-push

# 补历史某天
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-run.sh --yesterday 20260517
```

### 看日志

```bash
# Ubuntu（生产）
ssh mi@10.192.45.120 'tail -100 ~/logs/djy-daily/$(date +%Y-%m-%d).log'

# macOS（手动跑时）
tail -100 ~/logs/djy-daily/$(date +%Y-%m-%d).log
```

---

## 首次部署到新主机

详见 [`djy-skill/README.md`](djy-skill/README.md)。简短版：

```bash
# 1. clone
git clone git@git.n.xiaomi.com:v-zhujiaqing3/ai_djy_pool_analysis.git ~/ai_djy_pool_analysis

# 2. 让 Claude Code 能找到 skill
ln -s ~/ai_djy_pool_analysis/djy-skill ~/.claude/skills/djy-pool-analysis

# 3. 配 .env（飞书 4 项 + DataWorks token）
cp ~/ai_djy_pool_analysis/djy-skill/.env.example ~/ai_djy_pool_analysis/djy-skill/.env
# 编辑 .env 填实际凭证
chmod 600 ~/ai_djy_pool_analysis/djy-skill/.env

# 4. 装系统 + Python 依赖
# 见 djy-skill/README.md

# 5. cron
(crontab -l 2>/dev/null; \
 echo "30 10 * * * DJY_OUTPUT_ROOT=$HOME/ai_djy_pool_analysis /bin/bash $HOME/.claude/skills/djy-pool-analysis/bin/djy-daily-report.sh") \
 | crontab -
```

---

## 重要约束

- **`.env` 绝不进 git**：含 DataWorks token / 飞书 APP_SECRET。已在 `.gitignore` 屏蔽。每台主机自己维护一份本地 `.env`。
- **`reports/` 是 Pages 发布源**：动这里要意识到所有人能看到。其他目录改动不会暴露成网页。
- **`charts/` `tmp/` 不入 git**：体积大，每次重生成。日报跑出的长图通过飞书图床走，不走 Pages。
- **跨平台路径**：项目目录通过环境变量 `DJY_OUTPUT_ROOT` 适配（macOS 默认 `~/Desktop/ai_djy_pool_analysis`，Ubuntu 默认 `~/ai_djy_pool_analysis`）。`bin/*.sh` 用 `$HOME` / `BASH_SOURCE` 推导路径，不能写硬编码。

---

## 相关 memory

私人 memory 中相关条目（仅本人 Claude Code 可见）：

- `project_djy_daily_report_cron` — cron 调度规则、三类失败模式 + 兜底
- `feedback_daily_report_push_rule` — 何时触发推飞书（必须显式说"推/发+飞书/群"）
- `feedback_daily_report_longpng_only` — 卡片只推 HTML 长图
- `reference_djy_tables` — 召回/粗排/精排/内容池/审核高频表名速查
