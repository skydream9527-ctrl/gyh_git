# 数据报告 HTML 可视化模板

> 沉淀时间：2026-07-01
> 来源案例：浏览器信息流流量地图现状摸底分析
> 参考风格：http://ai.ice.miui.srv/files/v1-0-8c4f8b908f0c.html（黑白灰编辑风格 v1.0）

---

## 视觉设计规范

### 色彩体系（黑白灰编辑风）
```css
--ink: #151515;        /* 主色：标题、正文重点、柱状条 */
--text: #252525;       /* 正文色 */
--muted: #646464;      /* 次要文字 */
--quiet: #8a8a8a;      /* 辅助说明/标签 */
--line: #3a3a3a;       /* 重边框 */
--line-muted: #777;    /* 中边框 */
--line-soft: #deddd9;  /* 轻分隔线 */
--paper: #f7f6f2;      /* 页面背景（暖白纸色） */
--panel: #fffefa;      /* 卡片背景 */
--panel-soft: #f0efeb; /* 卡片浅底 */
--panel-deep: #e2e1dd; /* 卡片深底 */
--highlight: #fef3c7;  /* 高亮黄（用于关键数字标记） */
--shadow: 0 10px 24px rgba(0,0,0,0.045); /* 卡片阴影 */
```

### 字体组合
- **标题**：`"Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", serif`（宋体/衬线）
- **数据/数字/标签**：`"Avenir Next", sans-serif`（无衬线，数字等宽）
- **正文**：`"Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif`
- **code**：系统等宽字体

---

## 页面结构模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <!-- 色彩变量、字体、基础样式 -->
</head>
<body>
<div class="page">

  <!-- 头部 -->
  <header class="header">
    <div class="eyebrow">项目名 · Project Name<span class="ver">v1.0</span></div>
    <h1>报告主标题</h1>
    <div class="subtitle">副标题/一句话描述</div>
    <div class="meta-row">
      <span>数据日期</span>
      <span>数据源</span>
      <span>口径说明</span>
    </div>
  </header>

  <!-- 各Section -->
  <section>
    <div class="section-head">
      <span class="section-num">01</span>
      <h2>章节标题</h2>
      <span class="section-desc">英文副标题/说明</span>
    </div>
    <!-- 章节内容 -->
  </section>

</div>
</body>
</html>
```

---

## 组件库

### 1. 核心结论卡片（headline-card）
- 2列grid布局
- 左边框3px ink色
- 包含：标签（FINDING 01）、标题、描述（关键词用highlight黄底）

### 2. 四象限矩阵（quadrant-grid）
- 2×2 grid，4个象限
- 左上：ink反白（高价值象限）
- 包含：象限标签、标题、频道列表（名称+数据）、策略建议

### 3. 数据表格（data-table）
- 表头11px uppercase quiet色
- 数据行hover背景panel-soft
- 数值列右对齐，用Avenir Next字体
- 带柱状条列（col-bar）：6px高度bar-wrap + bar-fill
- 重点数字用cell-strong加粗
- 警告标记用cell-warn（highlight背景）

### 4. 双栏对比柱状条（retain-compare）
- 2列grid
- 每行：名称 + 横向柱状条 + 数值
- bar-fill颜色区分：重点用ink，一般用line-muted

### 5. 三栏TOP3卡片（triple-grid）
- 3列grid，每列一个维度
- 包含：列标题、排名+名称+数值

### 6. 行动建议（action-item）
- P0：ink左边框 + panel-deep背景（最高优先）
- P1：line左边框（中优先）
- P2：line-muted左边框（低优先）
- 包含：优先级标签、标题、描述

### 7. 附录说明（appendix-note）
- panel-soft背景 + 2px ink左边框
- 12-13px muted色文字

---

## 使用建议

1. **结论先行**：第一section放核心结论卡片（3-5条），一眼看到重点
2. **数据可视化**：表格中用柱状条代替纯数字，直观对比
3. **重点标记**：关键数字/异常值用highlight黄底或cell-strong加粗
4. **四象限分析**：留存×时长/UV等二维分析，用2×2矩阵比文字更清晰
5. **附录兜底**：详细数据表、口径说明放最后section，不干扰主线

---

## 输出流程

1. 飞书Markdown文档确认内容定稿
2. 按此模板手工编写HTML（飞书→HTML的自动转换效果差，需手工调整布局）
3. 保存到项目目录，浏览器打开预览
4. 需要时可用 `open xxx.html` 命令直接打开
