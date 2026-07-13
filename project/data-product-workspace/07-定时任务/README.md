# 定时任务目录

用于存放自动化数据查询、定时报表推送飞书等任务。

## 目录结构
```
07-定时任务/
├── scripts/      # 执行脚本
├── config/       # 配置文件
├── logs/         # 运行日志
├── reports/      # 生成的报表文件
└── templates/    # 消息/报表模板
```

## 现有任务
| 任务名称 | 脚本 | 调度时间 | 说明 |
|----------|------|----------|------|
| 每日核心指标监控 | `scripts/daily_metrics_report.py` | 每天9:00 | 查询核心指标，对比昨日/上周，推送飞书 |
| 每日工作回顾 | `scripts/daily_work_review.py` | 每天23:00 | 扫描当日文件变更+Git提交，生成工作总结草稿，自动抽取计划更新建议、绩效素材、决策记录，三处备份。**自动生成 WORK-PLAN.md 更新草稿**到 `99-临时文件/work-plan-updates/` |
| 每周工作总结 | `scripts/weekly_work_review.py` | 每周日22:00 | 汇总一周每日回顾，生成周总结草稿，自动统计完成任务/文件数 |
| 决策回填闭环 | `scripts/decision_review.py` | 每天09:00 | 扫描 DECISIONS.md 到期决策，搜集每日记录/MEMORY/WORK-PLAN 证据，生成回填简报，推送飞书提醒 |
| 需求→资产回流 | `scripts/asset_recall.py` | 手动触发 | 扫描已完成分析任务，提取 SQL/指标/人群包/方法论资产，生成回填建议报告 |
| 每日早间简报 | `scripts/morning_briefing.py` | 每天08:30 | 读取 WORK-PLAN P0/P1 + 昨日未完成 + 到期决策 → 更新 DAILY-TODO + CURRENT.md + 飞书提醒 |
| 知识库活跃度体检 | `scripts/kb_health_check.py` | 手动/每月 | 扫描 00-知识库/ 各域文件数/活跃度/引用，评级🟢/🟡/🔴，生成体检报告 |

## 使用说明

### 1. 配置任务
复制 `config/config.example.json` 到 `config/config.json`，修改配置：
- `feishu.webhook_url`: 飞书群机器人webhook地址
- `metrics`: 添加需要监控的指标和对应SQL
- `alert_threshold`: 配置异常告警阈值（下跌幅度）

### 2. 添加定时调度

推荐使用统一配置文件 `config/crontab.conf`，一键安装：
```bash
bash 07-定时任务/scripts/install_cron.sh
```

或手动添加（`crontab -e`）：
```
30 8 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_morning_briefing.sh
0 9 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_daily_report.sh
0 9 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_decision_review.sh
0 23 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_daily_review.sh
0 22 * * 0 /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_weekly_review.sh
```

### 3. 手动测试运行
```bash
cd /Users/mi/Desktop/trae-cn/data-product/07-定时任务
python3 scripts/daily_metrics_report.py
```

每日工作回顾可手动运行：
```bash
cd /Users/mi/Desktop/trae-cn/data-product
python3 07-定时任务/scripts/daily_work_review.py
```

生成的日报会自动填充三类待确认内容：
- `WORK-PLAN.md` 更新建议：根据文件路径、提交信息、待办/阻塞/P0/P1 等关键词抽取
- 绩效素材：按项目产出、数据分析、知识库、自动化脚本、Agent/Skill 建设分类抽取
- `DECISIONS.md` 决策记录：根据关键决策、取舍、风险、明确不做、回看等关键词抽取

## 飞书机器人配置
1. 在飞书群中添加「自定义机器人」
2. 获取webhook地址，填入配置文件
3. 如有签名校验，同时配置secret
