# matplotlib 图表生成规范（默认画图方案）

## 一、基础配置模板

每个图表生成脚本开头必须包含以下配置：

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')  # Windows 中文输出

import matplotlib
matplotlib.use('Agg')  # 无头模式，不弹窗
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# 中文字体链（按优先级尝试）
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False  # 负号显示

# 白色背景（飞书适配）
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["savefig.facecolor"] = "white"

# 可选：seaborn 美化
# import seaborn as sns
# sns.set_theme(style="whitegrid", font="SimHei")
```

## 二、生成流程

1. **先完成分析文本** → 确认需要哪些图表
2. 本地创建 `dar-charts/` 目录：`os.makedirs("dar-charts", exist_ok=True)`
3. 通过 Bash 执行 Python 脚本，一次性生成所有图表
4. 文件命名：`chart_1.png`, `chart_2.png`...（按章节和观点顺序编号）
5. 保存参数：`plt.savefig("dar-charts/chart_N.png", dpi=150, bbox_inches='tight')`
6. 每个图表生成后 `plt.close()` 释放内存
7. 全部生成后执行 `ls -lh dar-charts/` 校验所有 PNG 存在且 > 0 字节

## 三、标注系统（核心优势，必须善用）

matplotlib 最大优势在于自由标注，以下标注方式应积极使用：

### 极值标注（annotate + 箭头）

```python
# 标注最高点
ax.annotate(f'峰值: {max_val}',
    xy=(max_x, max_val),               # 箭头指向
    xytext=(max_x, max_val * 1.1),     # 文字位置
    arrowprops=dict(arrowstyle='->', color='red'),
    fontsize=9, color='red', ha='center')
```

### 均值线 / 目标线

```python
ax.axhline(y=mean_val, color='gray', linestyle='--', linewidth=0.8, label=f'均值: {mean_val:.1f}')
```

### 时段区间标注（寒暑假、活动期等）

```python
# 半透明色块标注暑假区间
ax.axvspan('2025-07-01', '2025-08-31', alpha=0.15, color='orange', label='暑假')
ax.axvspan('2025-01-15', '2025-02-25', alpha=0.15, color='skyblue', label='寒假')
```

### 事件标注（节假日、版本发布等）

```python
ax.axvline(x='2025-10-01', color='red', linestyle=':', linewidth=0.8)
ax.text('2025-10-01', y_pos, '国庆', rotation=90, va='bottom', fontsize=8, color='red')
```

### 自由标注（圆角文本框 + 弧形箭头）

```python
ax.annotate('关键转折点\n用户量首次突破百万',
    xy=(x, y),
    xytext=(x + offset, y + offset),
    bbox=dict(boxstyle='round,pad=0.3', facecolor='lightyellow', edgecolor='orange'),
    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color='orange'),
    fontsize=9)
```

### 四象限分割线 + 象限标签

```python
ax.axhline(y=y_threshold, color='gray', linestyle='--', linewidth=0.8)
ax.axvline(x=x_threshold, color='gray', linestyle='--', linewidth=0.8)
ax.text(x_max*0.75, y_max*0.85, '高价值高活跃', fontsize=10, ha='center', color='green', weight='bold')
ax.text(x_max*0.25, y_max*0.85, '高价值低活跃', fontsize=10, ha='center', color='orange', weight='bold')
ax.text(x_max*0.75, y_max*0.15, '低价值高活跃', fontsize=10, ha='center', color='blue', weight='bold')
ax.text(x_max*0.25, y_max*0.15, '低价值低活跃', fontsize=10, ha='center', color='gray', weight='bold')
```

## 四、常用图表实现参考

### 折线图（趋势分析）

```python
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(dates, values, marker='o', markersize=3, linewidth=1.5, label='DAU')
ax.axhline(y=np.mean(values), color='gray', linestyle='--', linewidth=0.8, label=f'均值: {np.mean(values):.0f}')
# 标注极值
ax.annotate(f'最高: {max(values)}', xy=(dates[np.argmax(values)], max(values)),
    xytext=(0, 10), textcoords='offset points', arrowprops=dict(arrowstyle='->'), fontsize=8)
ax.set_xlabel('日期')
ax.set_ylabel('DAU')
ax.legend()
ax.tick_params(axis='x', rotation=45)
plt.tight_layout()
```

### 分组柱状图（对比分析）

```python
x = np.arange(len(categories))
width = 0.35
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(x - width/2, group_a, width, label='A 组')
ax.bar(x + width/2, group_b, width, label='B 组')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()
# 柱顶数值标注
for i, v in enumerate(group_a):
    ax.text(i - width/2, v + 0.5, str(v), ha='center', fontsize=8)
```

### 热力图（时段分析 / 交叉分析）

```python
import seaborn as sns
fig, ax = plt.subplots(figsize=(14, 6))
sns.heatmap(matrix, annot=True, fmt='.0f', cmap='YlOrRd', ax=ax,
            xticklabels=hours, yticklabels=weekdays)
ax.set_xlabel('小时')
ax.set_ylabel('星期')
ax.set_title('用户活跃时段热力图')
```

### 漏斗图（转化分析）

```python
fig, ax = plt.subplots(figsize=(8, 6))
steps = ['曝光', '点击', '下载', '激活', '注册']
values = [10000, 6500, 3200, 1800, 1200]
# 居中水平条形模拟漏斗
max_val = max(values)
for i, (step, val) in enumerate(zip(steps, values)):
    width = val / max_val
    left = (1 - width) / 2
    color = plt.cm.Blues(0.3 + 0.7 * (len(steps) - i) / len(steps))
    ax.barh(i, width, left=left, height=0.6, color=color, edgecolor='white')
    ax.text(0.5, i, f'{step}\n{val:,} ({val/values[0]*100:.1f}%)', ha='center', va='center', fontsize=10, weight='bold')
    if i > 0:
        conv_rate = val / values[i-1] * 100
        ax.text(0.95, i - 0.5, f'转化率: {conv_rate:.1f}%', ha='right', va='center', fontsize=8, color='gray')
ax.invert_yaxis()
ax.axis('off')
ax.set_title('转化漏斗', fontsize=14, weight='bold')
```

### 瀑布图（异常归因 / 缺口分析）

```python
fig, ax = plt.subplots(figsize=(10, 5))
categories = ['基准值', '渠道A↑', '渠道B↓', '渠道C↑', '自然量↓', '最终值']
values = [1000, 200, -350, 150, -100, 900]
cumulative = [0]
for v in values[:-1]:
    cumulative.append(cumulative[-1] + v)
# 起点（基准值和最终值用不同颜色）
for i, (cat, val) in enumerate(zip(categories, values)):
    if i == 0 or i == len(categories) - 1:
        ax.bar(i, abs(val), bottom=0 if i == 0 else 0, color='steelblue')
    elif val >= 0:
        ax.bar(i, val, bottom=cumulative[i], color='green', alpha=0.7)
    else:
        ax.bar(i, abs(val), bottom=cumulative[i] + val, color='red', alpha=0.7)
    ax.text(i, cumulative[i] + val/2 if i > 0 and i < len(categories)-1 else val/2,
            f'{val:+d}' if i > 0 and i < len(categories)-1 else str(abs(val)),
            ha='center', va='center', fontsize=9, weight='bold')
ax.set_xticks(range(len(categories)))
ax.set_xticklabels(categories)
```

### 饼图（结构分析，≤6 类）

```python
fig, ax = plt.subplots(figsize=(8, 8))
wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
    startangle=90, colors=plt.cm.Set3.colors[:len(labels)])
ax.set_title('用户来源结构')
```

### Cohort 留存热力图

```python
fig, ax = plt.subplots(figsize=(12, 8))
sns.heatmap(cohort_df, annot=True, fmt='.1%', cmap='YlGnBu', ax=ax,
            vmin=0, vmax=1)
ax.set_xlabel('留存周期')
ax.set_ylabel('注册批次')
ax.set_title('用户留存 Cohort 分析')
```

### 帕累托图（二八分析）

```python
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(range(len(sorted_items)), sorted_values, color='steelblue')
ax2 = ax1.twinx()
ax2.plot(range(len(sorted_items)), cumulative_pct, color='red', marker='o', markersize=3)
ax2.axhline(y=0.8, color='red', linestyle='--', linewidth=0.8)
ax2.set_ylabel('累计占比')
ax2.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
```

## 五、桑基图降级策略

matplotlib 不支持原生桑基图。当分析方法需要桑基图时：

1. **默认替代**：使用矩阵热力图 `sns.heatmap()` 展示流向关系（行=来源，列=目标，色深=流量）
2. **强需求桑基图**：引导用户在阶段七 Step 4 选择生成 ECharts HTML 报告（ECharts 有原生桑基图支持）

涉及桑基图的方法：#5 渠道归因、#12 用户路径分析、#19 跨渠道迁移

## 六、常见问题

### Windows 中文乱码

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### 字体缺失警告

检查可用字体：
```python
import matplotlib.font_manager as fm
[f.name for f in fm.fontManager.ttflist if 'Hei' in f.name or 'Ya' in f.name]
```

### X 轴标签重叠

```python
ax.tick_params(axis='x', rotation=45)
# 或只显示部分标签
ax.xaxis.set_major_locator(ticker.MaxNLocator(nbins=10))
```

### 图表尺寸不合适

- 折线图/趋势图：`figsize=(12, 5)`
- 热力图：`figsize=(14, 6)` 或更大
- 饼图：`figsize=(8, 8)`
- 漏斗图：`figsize=(8, 6)`

### 保存后图表被裁切

始终使用 `bbox_inches='tight'`：
```python
plt.savefig("dar-charts/chart_1.png", dpi=150, bbox_inches='tight')
```
