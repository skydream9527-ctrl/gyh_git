# 日报 HTML 样式规范

日报产出的 HTML 报告必须遵循本文件定义的样式和结构。参考实现：`~/Desktop/ai_djy_pool_analysis/reports/content_pool_validate_20260507.html`

## 整体风格

- **设计理念**：商务简约、素净舒适、信息密度高但不拥挤
- **背景**：纯净浅灰 `#f7f8fa`（不用渐变）
- **文字色**：主文字 `#2c3e50`，次级 `#7f8c9b`，弱化 `#a0aec0`
- **容器**：`max-width: 1440px; margin: 0 auto`
- **字体**：`-apple-system, "PingFang SC", "Microsoft YaHei", Arial, sans-serif`

## 页面结构（顺序固定）

1. **页面头部** — 标题 + 副标题 + 口径说明（居中）
2. **消费数据概览** — 昨日日环比表格（涨跌色按幅度渐变）
3. **昨日消费 Top5 内容** — 两张表并排（VV Top5 + 时长 Top5）
4. **入库趋势 + 异常存量趋势** — 两张折线图并排（Chart.js）
5. **异常校验结果** — 趋势 Top3 + CP 总览表 + 每家 CP 详细问题块
6. **各 CP 字段存量趋势** — 四张折线图 2x2 网格
7. **页脚** — 自动生成说明 + 口径 + 豁免声明

## 色彩系统

### CP 配色（徽章 + 图表折线）

| CP | 徽章背景 | 图表线色 |
|---|---|---|
| beike | `#5b8def` | `#5b8def` |
| dihui | `#e07070` | `#e07070` |
| guoying | `#4db89a` | `#4db89a` |
| meilaoban | `#d4903a` | `#d4903a` |

### 涨跌色（按幅度渐变）

涨跌不用固定底色，用 `rgba` 透明度映射变化幅度：

```
涨：rgba(34, 154, 96, opacity)  文字色 #1e7e4a
跌：rgba(220, 53, 69, opacity)  文字色 #c0392b
```

opacity 映射规则（|变化幅度|）：
- ≥100%: 0.28-0.30
- 50-100%: 0.22
- 30-50%: 0.16-0.20
- 10-30%: 0.10-0.14
- 1-10%: 0.03-0.07
- 无变化: transparent

### 功能色

| 场景 | 颜色 |
|---|---|
| 表头背景 | `#e8edf3`，文字 `#2c3e50`，底线 `#c9d4e0` |
| 区块标题背景 | `#edf2f7`，左边线 `#5b8def` |
| 严重-紧急左边线 | `#e25d5d` |
| 严重-高左边线 | `#e6a23c` |
| 严重-低左边线 | `#e6c84c` |
| 标签-紧急 | 底 `#fde8e8` 字 `#c0392b` |
| 标签-正常 | 底 `#e6f7ee` 字 `#1e7e4a` |
| 操作建议块 | 底 `#f7f8fa` 左线 `#5b8def` |
| 趋势提示块 | 底 `#fffbf0` 左线 `#e6a23c` |
| code 标签 | 底 `#edf2f7` 字 `#3a5ba0` |
| 链接 | `#5b8def` hover `#3a6ddb` |
| 数值强调 | `#3a5ba0`（深蓝） |

## 组件规范

### 卡片

```css
background: white;
border-radius: 14px;
padding: 22px;
box-shadow: 0 2px 12px rgba(0,0,0,0.04);
/* hover */
transform: translateY(-2px);
box-shadow: 0 4px 20px rgba(0,0,0,0.08);
```

### 表格

- 表头：`background: #e8edf3`，`border-bottom: 2px solid #c9d4e0`，`white-space: nowrap`
- 单元格：`padding: 10px 14px`，底线 `#edf2f7`
- hover 行：`background: #f7f8fa`

### Top5 并排表格

- 容器：`display: flex; gap: 22px; align-items: stretch`
- 每行固定 `height: 80px`，垂直居中
- ID 列：等宽字体 11px，`color: #7f8c9b`，`width: 150px`，允许换行（`word-break: break-all`）
- 标题列：可点击跳转视频源文件，链接用 `.top5-link` 样式
- 数值列：`width: 70px`，居中

### CP 徽章

```css
display: inline-block;
padding: 3px 10px;
border-radius: 20px;
color: white;
font-size: 12px;
font-weight: 600;
```

### 区块标题

```css
font-size: 17px; font-weight: 600;
padding: 10px 14px;
background: #edf2f7;
border-left: 4px solid #5b8def;
border-radius: 0 10px 10px 0;
```

### 异常问题块

```css
background: white;
border-radius: 14px;
padding: 20px 22px;
box-shadow: 0 2px 12px rgba(0,0,0,0.04);
border-left: 4px solid {severity-color};
```

## 图表（Chart.js）

- 折线：`borderWidth: 2.5`，`tension: 0.4`，`fill: true`（浅色填充 opacity 0x18）
- 点：默认隐藏（`pointRadius: 0`），hover 显示（`pointHoverRadius: 6`）
- 网格：Y 轴 `#f1f5f9`，X 轴隐藏
- Tooltip：深色背景 `rgba(30,41,59,0.9)`，圆角 8px
- DataLabels：仅最大值和最后一个值显示

## 反模式（禁止）

- 渐变色背景/表头（刺眼）
- 高饱和纯色大面积使用
- 左右表格不对齐（必须固定行高或合并为单表）
- 内容 ID 截断显示
- 数据列不居中
