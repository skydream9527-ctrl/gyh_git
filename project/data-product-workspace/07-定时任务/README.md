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
| 每日工作回顾 | `scripts/daily_work_review.py` | 每天23:00 | 扫描当日文件变更+Git提交，生成工作总结草稿，三处备份 |
| 每周工作总结 | `scripts/weekly_work_review.py` | 每周日22:00 | 汇总一周每日回顾，生成周总结草稿，自动统计完成任务/文件数 |

## 使用说明

### 1. 配置任务
复制 `config/config.example.json` 到 `config/config.json`，修改配置：
- `feishu.webhook_url`: 飞书群机器人webhook地址
- `metrics`: 添加需要监控的指标和对应SQL
- `alert_threshold`: 配置异常告警阈值（下跌幅度）

### 2. 添加定时调度
使用系统crontab添加定时任务：
```bash
crontab -e
```
添加以下内容（每天9点、每天23点、每周日22点执行）：
```
0 9 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_daily_report.sh
0 23 * * * /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_daily_review.sh
0 22 * * 0 /Users/mi/Desktop/trae-cn/data-product/07-定时任务/scripts/run_weekly_review.sh
```

### 3. 手动测试运行
```bash
cd /Users/mi/Desktop/trae-cn/data-product/07-定时任务
python3 scripts/daily_metrics_report.py
```

## 飞书机器人配置
1. 在飞书群中添加「自定义机器人」
2. 获取webhook地址，填入配置文件
3. 如有签名校验，同时配置secret
