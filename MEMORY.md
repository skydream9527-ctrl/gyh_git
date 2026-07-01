# MEMORY.md — 长期记忆索引

> 本文件由 AI 自动维护，用户无需手动编辑。每次对话开始时 AI 读取，对话结束时 AI 更新。

## 当前重点

- 建设 Wisdom&Decide 个人决策中心，系统化决策流程
- ICE Data Workbench v3 迭代与功能完善
- ice-data-work（新数据工作台）设计与开发
- AI Agent / Skill / MCP 能力边界探索与建设

## 关键决策

- 2026-06-30：项目定位为「思考与探索空间」，思考记录是主体，工程代码是参考副本 → THINKING.md
- 2026-06-30：工程副本去重，只保留 project/ice-workbench-new/ 一份参考；开发正本在 git.n.xiaomi.com/gongyunhe/ice-workbench，不在本仓库改代码
- 2026-06-29：创建 Wisdom&Decide 目录作为个人决策中心 → Wisdom&Decide/README.md
- 2026-06-29：整合 ICE-DATA-WORK、ice_workbench_new、data-product 三个目录到 project/ 下

## 我的偏好

- 先结论后细节
- 竞品分析、方案对比带对比表格，不要大段文字
- PRD 必须包含异常流程和边界条件
- 周报用结构化格式，先总后分
- 引用数据必须标注来源和时间，无数据标注「推断」
- AI 做执行，我专注于决策和判断

## 近期记忆

- 07-01：完整整合 ~/Desktop/trae-cn/data-product 目录到 project/data-product-workspace/，包含：00-知识库（7大知识域+归档/操作手册）、01-业务项目、02-Skill开发、03-数据分析、04-会议纪要、05-个人成长（每日/每周/季度复盘+绩效素材）、06-归档、07-定时任务、入口文件（AGENTS/CURRENT/DECISIONS/MEMORY/USER/WORK-PLAN/WORKFLOWS/TEMPLATES）
- 06-30：项目结构梳理与整理 → THINKING.md。新建思考空间总入口；工程去重删 ~6900 文件（保留 ice-workbench-new）；decisions→references、feishu-part→notes/、删空 memory/your-domain、reference→engineering-ref；重写 README/CLAUDE 为思考空间入口
- 06-29：创建 Wisdom&Decide 决策中心，梳理项目全景，输出决策SOP → Wisdom&Decide/
- 06-29：将三个桌面目录整合进 project/ 并同步到GitLab
- 06-26：更新 agent-llm 记忆系统文档和参考资料并同步Git
- 06-25：添加决策框架、LLM思维、AI基础设施知识等29个文件并同步Git