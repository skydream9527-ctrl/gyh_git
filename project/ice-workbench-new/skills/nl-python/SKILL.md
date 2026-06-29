---
name: nl-python
description: 在 ICE Workbench 数据分析任务里生成沙箱可执行的 Python 代码，做 SQL 之外的统计 / 预测 / 可视化。仅当任务范式标记 [Python] 或 SQL 算不出（时序预测、留存曲线拟合、变点检测、STL 分解、bootstrap 置信区间、SHAP 归因等）时使用。触发：用户提"预测 / Prophet / ARIMA / 拟合 / 变点 / STL / cohort 拟合 / KS test"，或 data-analysis agent 进入 Phase 4e。
---

# NL-Python: 自然语言转沙箱 Python

把已落到任务工作区的 CSV 当输入，跑 SQL 算不出的统计 / 预测 / 可视化，把结果落回工作区供 Phase 5 报告引用。

---

## 沙箱契约（不读不背就出错）

| 项 | 约束 |
|---|---|
| **执行入口** | `execute_python(code, description?, timeout_sec?)` 内置工具 |
| **运行进程** | `backend/.venv-sandbox/bin/python -I -S` 沙箱子进程，**无状态**（每次新进程，无变量复用）|
| **cwd** | `<task_workspace>/files/output/`（相对路径写在这里）|
| **超时** | wall-clock + RLIMIT_CPU 默认 60s；超出 SIGKILL，状态 `TIMEOUT` 或 `KILLED` |
| **内存** | RLIMIT_AS 默认 1 GiB（Linux）；越线 SIGKILL → `KILLED` |
| **输出大小** | RLIMIT_FSIZE 默认 50 MiB / 文件；超出 OSError |
| **网络** | **完全断开**：socket(AF_INET/AF_INET6) 与 getaddrinfo 都 raise `OSError("network disabled")`。**禁止** `requests / urllib3 / httpx / aiohttp / urlopen` —— 它们会立即抛错 |
| **stdout/stderr 上限** | 各 8 KiB；超出截断（仍算成功）|
| **可用包** | `numpy / pandas / scipy / scikit-learn / statsmodels / prophet / ruptures / matplotlib / seaborn / pyarrow` 加 Python stdlib。其它包不可用，import 即 ImportError |
| **写入约束** | 只信相对路径；绝对路径越界写虽然有 best-effort 跳板（cwd 锁定）但**强制规范**所有产物落到 `data/` / `charts/` / `models/` 三个子目录 |

### 不能做的事

- ❌ `import requests` / `urllib.request.urlopen` / 任何网络 IO
- ❌ `subprocess.*` / `os.system` / `os.exec*`（理论可执行，但只在沙箱进程里跑，无价值且增加风险）
- ❌ 直连 kyuubi / mysql / 任何数据源（只读 SQL 已落地的 CSV）
- ❌ 修改 `STATE.md` / `agent.json` / 系统文件
- ❌ 写绝对路径到 task workspace 之外
- ❌ 用 `time.sleep(60)` 之类的 busy wait 浪费 timeout 预算
- ❌ 安装新包 (`pip install`) — 网络已断且无效
- ❌ 在 stdout 打印整张 DataFrame（截断到 8KB；要存全量请落 CSV）

### 必须做的事

- ✅ `matplotlib.use('Agg')` 在 `import matplotlib.pyplot` 之前（沙箱已 export `MPLBACKEND=Agg`，但显式更稳）
- ✅ `import numpy as np; import pandas as pd` 走标准别名
- ✅ 所有产物写到 `data/` / `charts/` / `models/`，文件名带任务编号前缀 `T{n}_*`
- ✅ 关键数字 print 到 stdout 让用户和 LLM 能看到
- ✅ 异常用 try/except 包好关键步骤，print 友好错误信息

---

## IO 协议（Phase 4 下游只认这个）

### 输入

```
<task_workspace>/files/output/data/T{n}_*.csv      # 已 SQL 落地的明细 / 聚合
```

`pd.read_csv('data/T1_dau.csv')` —— 相对路径即可，cwd 已就位。

### 输出（强制三类目录）

```
data/T{n}_*.csv          # 处理后的数据（如外推后的 forecast / 拟合后的留存预测）
charts/T{n}_*.png        # 图（matplotlib Agg 出 PNG，PNG > 1KB 才算有效）
models/T{n}_*.pkl        # 拟合好的模型（可选，用于审计 / 复跑）
```

文件名规范：`T{n}_{语义}.{ext}`，例：
- `data/T3_forecast_dau_t30.csv`
- `charts/T3_forecast_dau.png`
- `models/T3_prophet.pkl`

### 沙箱返回结构（execute_python 工具响应）

```json
{
  "status": "ok | error | timeout | killed | setup_error",
  "stdout": "...",
  "stderr": "...",
  "files_created": [
    {"relpath": "data/T3_forecast.csv", "size_bytes": 1234, "kind": "csv"},
    {"relpath": "charts/T3_forecast.png", "size_bytes": 56789, "kind": "png"}
  ],
  "registered_files": [...],   // 已自动注册到 frontend file panel
  "duration_ms": 3210,
  "exit_code": 0,
  "truncated": false
}
```

`registered_files[*].file_id` 拿到后，Phase 5 报告里通过 `feishu docx upload-image` 嵌入图片即可。

---

## 代码模板：分场景 reference 文件

每个分析方法的可运行模板见 `reference/`：

| 文件 | 覆盖范式 / 子模式 |
|---|---|
| `reference/forecasting.md` | 预测 8d (Prophet / SARIMA / STL+ARIMA) |
| `reference/cohort-curve.md` | 预测 8e (留存曲线幂律 / 指数拟合 + LT 积分) |
| `reference/changepoint.md` | 预测 8f (ruptures PELT / BinSeg) |
| `reference/decomposition.md` | 波动 3 / 趋势 6 (STL 周期剥离) |
| `reference/comparative-stats.md` | 对比 1 (bootstrap CI / permutation test / KS test) |
| `reference/distribution.md` | 分布 5 (curve_fit / 双峰检测 / 集中度) |
| `reference/retention.md` | 留存 7 (cohort heatmap + cluster) |
| `reference/io-contract.md` | CSV / PNG schema + 命名规范（本文档外的扩展）|

> 用 `read_skill nl-python <reference/X.md>` 拉对应模板。

---

## 通用代码骨架（每段 Python 都从这里起）

```python
"""T{n}: 一句描述本段做什么"""
import os
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. 读输入（相对路径）
df = pd.read_csv('data/T1_dau.csv', parse_dates=['date'])

# 2. 检查输入（防御式）
assert len(df) >= 14, f"need at least 14 days, got {len(df)}"
assert df['date'].is_monotonic_increasing, "input must be sorted by date"

# 3. 核心分析 ...

# 4. 落产物
df_out.to_csv('data/T2_processed.csv', index=False)
fig.savefig('charts/T2_chart.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# 5. 关键数字打 stdout（≤ 8KB）
print(f"rows in: {len(df)}, rows out: {len(df_out)}")
print(f"summary stat: {df_out['value'].mean():.3f}")
```

---

## 错误恢复路径

| 沙箱状态 | 含义 | 恢复 |
|---|---|---|
| `error` + traceback 含 ImportError | 用了不在白名单的包 | 改用白名单包；告知用户 |
| `error` + 用户代码 raise | 数据 schema 不符 / 边界条件 / 数值异常 | 加 assert 校验 + 修代码重跑 |
| `timeout` / `killed` (signal=9) | 超时或 OOM | 先 SQL 聚合到更小，或 sample；分块跑 |
| `killed` (signal=11/segfault) | C 扩展出错（罕见）| 减小数据量 / 改算法 |
| `setup_error` | venv 没装好 | 提示用户 `make install-sandbox` |

---

## 反模式（看到就要修）

- ❌ 不 assert 输入 schema 就直接 indexing → 沙箱 traceback 只能告诉你"KeyError: 'foo'"
- ❌ `df.head()` 只 print 不存 → 用户拿不到完整结果
- ❌ matplotlib 用默认 backend → 沙箱里 import 就 raise（已 export MPLBACKEND=Agg，但代码里不写一句 `matplotlib.use('Agg')` 是不规范）
- ❌ `df.to_pickle('data/x.pkl')` 把 DataFrame 当模型存 → kind 会被识别成 model；DataFrame 该用 CSV/Parquet
- ❌ 嵌套 try 包整段 → 错误信息丢失。每个外部依赖（read_csv / fit / savefig）单独 try
- ❌ 用 `os.path.join` 拼绝对路径 → 直接相对就行
- ❌ 一段代码做 5 件事 → 拆成多次 execute_python 调用，方便用户校对中间产物
