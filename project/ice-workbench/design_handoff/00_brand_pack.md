# 00 · Brand Pack（所有页面共用）

> 上传到 Claude Design 时，把这份文件先粘到项目说明里再粘当前页简报。

## 产品

- 名称：**ICE Data Workbench**
- 定位：AI 数据工作流工作台（NotebookLM 风格 / 数据分析向）
- 用户：业务侧的数据分析师 + 增长 / 实验同学
- 形态：Web，桌面 + 移动端双端必须适配

## 主题

双主题，均需出方案：

| Token | Dark（默认） | Light |
| --- | --- | --- |
| Background | `#1f1f1f` | `#faf9f6` |
| Surface | `#262626` | `#ffffff` |
| Surface 2 | `#2e2e2e` | `#f7f5f0` |
| Border | `#3c3c3c` | `#e6e2dc` |
| Divider | `#2e2e2e` | `#ece8e1` |
| Text | `#e8eaed` | `#1f1f1f` |
| Text Dim | `#9aa0a6` | `#5f6368` |
| Text Muted | `#6c7075` | `#80868b` |

## 主色（Primary / Accent）

| Token | Dark | Light |
| --- | --- | --- |
| Primary | `#8ab4f8` | `#1a73e8` |
| Primary Hover | `#aecbfa` | `#1557b0` |
| Primary On | `#1f1f1f` | `#ffffff` |
| Primary Soft (chip bg) | `rgba(138,180,248,0.16)` | `#e8f0fe` |
| Agent (二级品牌) | `#c58af9` | `#5f4b8b` |

## 范式色（5 类业务标签 chip）

业务里所有任务都打这 5 类标签之一，UI 里大量出现。请保持「克制、可识别、不饱和过度」：

| Chip | 含义 | Dark | Light |
| --- | --- | --- | --- |
| AB | AB 实验 | `#8ab4f8` | `#1967d2` |
| BIZ | 业务分析 | `#fdd663` | `#b06000` |
| GRAY | 灰度分析 | `#c58af9` | `#5f4b8b` |
| DATA | 数据探查 | `#81c995` | `#137333` |
| WAVE | 波动归因 | `#f28b82` | `#b3261e` |

每个 chip 同时有 `-dim`（hover 背景）和 `-soft`（chip 主体背景）两个透明度变体。

## 反馈色

| Token | Dark | Light |
| --- | --- | --- |
| Success | `#81c995` | `#137333` |
| Warning | `#fdd663` | `#b06000` |
| Error | `#f28b82` | `#b3261e` |
| Info | `#8ab4f8` | `#1a73e8` |

## 字体

```
heading / body : "Inter", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif
mono           : "JetBrains Mono", ui-monospace, monospace
```

中文回退到 PingFang SC（macOS）/ Microsoft YaHei（Windows）。**不需要上传字体文件**，全部使用系统/web 默认。

## 几何

- Radius：`14px`（card / 主要） · `10px`（sm） · `8px`（xs） · `999px`（pill）
- Shadow 三档（dark）：
  - `shadow-1`: `0 1px 2px rgba(0,0,0,0.4)`
  - `shadow-2`: `0 4px 16px rgba(0,0,0,0.45)`
  - `shadow-3`: `0 12px 32px rgba(0,0,0,0.55)`
- Shadow 三档（light）：
  - `shadow-1`: `0 1px 2px rgba(60,64,67,0.06)`
  - `shadow-2`: `0 1px 3px rgba(60,64,67,0.10), 0 4px 8px rgba(60,64,67,0.04)`
  - `shadow-3`: `0 4px 24px rgba(60,64,67,0.10)`

## 移动端规格

- 底部导航条：`60px`
- FAB（浮动操作按钮）：`56px`
- 安全区：iOS 需考虑 `env(safe-area-inset-bottom)`

## 设计参考

- NotebookLM（信息密度 + 工具感）
- Linear / Anthropic Claude.ai（克制的产品级视觉）
- **不要**参考：管理后台模板（Ant Design Pro / TDesign Admin / Dashboard Kit）— 我们当前已经有「太后台/Dev」的问题

## 不变量

- 颜色不能溢出上面的 token 表 — 新颜色必须能用现有 token 组合表达
- 圆角不能用 `4px` / `6px` — 与现有 8/10/14 体系冲突
- 不引入第三方 UI 库（Ant Design / MUI / Chakra）— 全部 CSS Modules + tokens
