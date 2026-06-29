# djy-pool-analysis

都江堰内容池分析 skill。包含三大模块：

- **校验（validate）**：4 家 CP × 20+ 条规则，检查内容池字段准确性
- **消费（consumption）**：DAU 级流量指标分析
- **创作者审核（creator_audit）**：签约 → 审核 → 入库 → 合规链路校验

完整说明见 [SKILL.md](SKILL.md)。

## 目录结构

```
.
├── SKILL.md              # skill 完整说明书
├── exemptions.json       # 各 CP 豁免规则配置
├── .env.example          # 环境变量模板（实际 .env 不入 git）
├── bin/                  # 日报 cron 包装脚本
│   ├── djy-daily-report.sh   # cron 入口（带 watchdog）
│   ├── djy-daily-run.sh      # 10 步流水线主体
│   ├── djy-daily-charts.sh
│   └── djy-daily-alert.sh    # 失败飞书告警
├── references/           # 各模块参考文档
└── scripts/
    ├── consumption/      # 消费模块
    ├── creator_audit/    # 创作者审核模块
    ├── shared/           # 共享工具（HTML 生成、长图截屏、飞书推送、git push）
    └── validate/         # 校验模块（SQL 模板）
```

## 部署 / 使用

### 首次部署

```bash
git clone git@git.n.xiaomi.com:v-zhujiaqing3/djy-pool-analysis.git \
  ~/.claude/skills/djy-pool-analysis

# 配 .env（飞书 4 项 + DataWorks Token）
cp ~/.claude/skills/djy-pool-analysis/.env.example \
   ~/.claude/skills/djy-pool-analysis/.env
# 编辑 .env 填实际凭证
chmod 600 ~/.claude/skills/djy-pool-analysis/.env
```

### 日报 cron

```cron
30 10 * * * /bin/bash $HOME/.claude/skills/djy-pool-analysis/bin/djy-daily-report.sh
```

`bash` 路径在 macOS / Ubuntu 都是 `/bin/bash`，可直接复用。

### 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DJY_OUTPUT_ROOT` | `$HOME/ai_djy_pool_analysis` | 日报产出目录（reports/charts/daily_reports 父级）。macOS 上一般 `export DJY_OUTPUT_ROOT=$HOME/Desktop/ai_djy_pool_analysis` |

### 手动跑

```bash
# 推飞书的完整流程
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-report.sh

# 只跑不推（验证用）
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-run.sh --skip-push

# 补历史某天
bash ~/.claude/skills/djy-pool-analysis/bin/djy-daily-run.sh --yesterday 20260517
```

### 日志

- macOS / Ubuntu 统一：`~/logs/djy-daily/<日期>.log`

## 跨平台说明

脚本用 `$HOME` / `BASH_SOURCE` / `DJY_OUTPUT_ROOT` 等变量推导路径，macOS / Ubuntu 共用同一份代码。`python3` 直接走 PATH，不写绝对路径或 `arch -arm64`。

## 相关仓库

- 日报产出（HTML / JSON 归档）：`git@git.n.xiaomi.com:v-zhujiaqing3/ai_djy_pool_analysis.git`
- GitLab Pages（在线日报查看）：`http://ai-djy-pool-analysis-4bbd9e.pages.n.xiaomi.com/content_pool_validate_<YYYYMMDD>.html`
