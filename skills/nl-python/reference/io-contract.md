# nl-python IO 契约（命名 + schema）

## 目录布局

```
<task_workspace>/files/output/   ← cwd
├── data/                        ← CSV 输入 / 输出
│   ├── T1_dau.csv               (kyuubi 落地)
│   ├── T2_forecast_30d.csv      (Python 处理)
│   └── T2_forecast_components.csv
├── charts/                      ← PNG 图（matplotlib Agg）
│   ├── T2_forecast.png
│   └── T2_residuals.png
└── models/                      ← 模型 pickle
    └── T2_prophet.pkl
```

## 命名规范

```
<dir>/T{n}_{语义}.{ext}
```

- `T{n}` 跟 Phase 2 任务编号一致（T1 / T2 / ...）
- 语义部分：`forecast / decomposition / changepoint / cohort_lt / comparison / distribution / retention_heatmap`
- 不允许：空格、中文、特殊字符
- 多产物用后缀区分：`T2_forecast_30d.csv` / `T2_forecast_components.csv`

## CSV 通用约定

- 第一列是日期 / 主键时，列名固定 `date / id / cohort` 等英文
- 日期格式 `YYYY-MM-DD`
- 浮点保留至少 6 位有效数字（`pandas.to_csv` 默认即可）
- 不写 index：`df.to_csv('...', index=False)` —— 除非 index 本身是关键（cohort 矩阵）

## PNG 通用约定

```python
fig.savefig('charts/T{n}_x.png', dpi=120, bbox_inches='tight')
plt.close(fig)
```

- DPI 120（不是默认 100，太糊；也不是 300，太大）
- `bbox_inches='tight'` 防 label 被裁
- 必 `plt.close(fig)`，沙箱内存紧
- 图必有 title + 轴标签（用户从图里能看懂）
- 多图分多文件（`T2_forecast.png` / `T2_residuals.png`），不堆同一个

## 各范式产物 schema 对照表

| 范式 / 子模式 | 主 CSV | 主 PNG | 关键字段 |
|---|---|---|---|
| 1 对比 | `T{n}_comparison.csv` | `T{n}_comparison.png` | `bootstrap_ci_low/high, permutation_p, ks_p` |
| 2 拆解 | `T{n}_decomposition.csv` | `T{n}_waterfall.png` | `分项, 当期, 对标, 贡献_bp` (Σ 应等于 ΔY) |
| 3 波动 | `T{n}_anomalies.csv` | `T{n}_stl.png` | `date, observed, resid, resid_in_sigma` |
| 4 漏斗 | `T{n}_funnel.csv` | `T{n}_funnel.png` | `step, uv, step_conv_rate, cumulative_conv_rate` |
| 5 分布 | `T{n}_distribution.csv` | `T{n}_distribution.png` | `mean, median, p10/50/90/99, gini, top1pct_share, shape` |
| 6 趋势 | `T{n}_trend.csv` + `T{n}_segments.csv` | `T{n}_trend.png` + `T{n}_changepoints.png` | `slope, r2, breakpoint_date, jump_in_sigma` |
| 7 留存 | `T{n}_cohort_clusters.csv` + `T{n}_retention_keypoints.csv` | `T{n}_retention_heatmap.png` | cohort × day_n 矩阵 + cluster |
| 8d 预测 | `T{n}_forecast_30d.csv` | `T{n}_forecast.png` | `date, yhat, yhat_lower, yhat_upper` |
| 8e 留存外推 | `T{n}_cohort_lt.csv` | `T{n}_cohort_curve_fit.png` | `cohort, model, r2, d30_pred, d60_pred, d90_pred, lt_to_d90` |
| 8f 变点 | `T{n}_breakpoints.csv` + `T{n}_segments.csv` | `T{n}_changepoints.png` | `breakpoint_date, jump, jump_in_sigma` |

## stdout 协议

每段代码必须打到 stdout 的**最少**关键数字（让 LLM 和用户看到结果，不用打开 CSV）：

- 输入行数 / 形状
- 关键统计（mean, std, R², p-value, MAPE 等）
- 输出文件路径（隐含：`data/T{n}_*.csv`、`charts/T{n}_*.png`）
- 一句结论（"显著" / "不显著"、"高置信" / "低置信"）

stdout 上限 8KB，**不要**打整张 DataFrame；超过 30 行的表落 CSV，stdout 只打 head + tail + summary。

## 不要做

- ❌ 写绝对路径（`/Users/...`、`/tmp/...`）
- ❌ 写到 task workspace 之外
- ❌ 把图存成 SVG（PNG 给 feishu docx 嵌入更稳）
- ❌ DataFrame 用 pickle 存（用 CSV / Parquet）
- ❌ 同一段 Python 写 5+ 个产物 → 拆多次 execute_python
