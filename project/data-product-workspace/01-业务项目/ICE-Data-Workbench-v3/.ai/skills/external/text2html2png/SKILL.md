# Text2Html2Png — HTML 可视化图表生成

> ⚠️ 完整功能需要 `npm install`。当前为骨架版。

## 使用方式

1. 在 `.ai/skills/external/text2html2png/` 目录下执行 `npm install`
2. AI 根据需求生成 HTML → CLI 截图 → 输出 PNG

## 可用模板

- architecture：架构图
- comparison：对比表格
- dashboard：数据仪表盘
- flowchart：流程图
- funnel：漏斗图
- gantt：甘特图
- org-chart：组织结构图
- timeline：时间线
- weekly-summary：周报摘要

## 可用风格

- paper：纸张质感
- editorial：编辑风格
- minimal：极简
- dark：暗色
- warm：暖色
- glass：毛玻璃
- neon：霓虹

## CLI 截图命令

```bash
npx tsx scripts/screenshot.ts --html {HTML路径} --out {输出PNG路径} --bg "#f5f4f0" --width 1200 --padding 20
```

完整模板和脚本请从源工作区同步（联系管理员获取地址）。