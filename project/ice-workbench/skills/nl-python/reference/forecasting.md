# 预测 · Forecasting (Prophet / SARIMA / STL+ARIMA)

适用范式 8d（时序预测）。SQL 不能算这个；Python 必走。

## 选型决策树

```
有节假日 / 多周期 (年+周)? ──→ Prophet
       │
       否 ─→ 单周期、强自相关? ──→ SARIMA
                  │
                  否 ─→ 想剥周期再 ARIMA? ─→ STL + ARIMA
```

| 条件 | 选 |
|---|---|
| 数据 ≥ 28 天，单/多周期，要置信区间 | **Prophet**（默认）|
| 数据 ≥ 90 天，季节性强，要严格统计性质 | **SARIMA** (`statsmodels.tsa.statespace.SARIMAX`) |
| 周期复杂、要先剥周期 | **STL + ARIMA**（`statsmodels.tsa.seasonal.STL` 残差 + ARIMA）|
| 数据 < 14 天 | **拒绝**：返回 "数据量不足" 给用户 |

---

## 通用契约

- 训练数据 ≥ 28 天（< 28 天直接拒绝）
- 必留 holdout：最后 7 天作 validation，算 MAPE / RMSE
- 输出 CSV schema：`date | yhat | yhat_lower | yhat_upper`（80% 区间）
- 必落 PNG：历史实线 + 预测虚线 + 置信带

---

## 模板 A · Prophet（默认推荐）

```python
"""T{n}: Prophet 预测 [指标名] 未来 30 天"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pickle
from prophet import Prophet

# 1. 输入：date + value（Prophet 要求列名 ds, y）
df = pd.read_csv('data/T1_dau.csv', parse_dates=['date'])
assert len(df) >= 28, f"Prophet 需要 ≥28 天历史，当前 {len(df)} 天"
df = df.rename(columns={'date': 'ds', 'dau': 'y'}).sort_values('ds').reset_index(drop=True)

# 2. 留 holdout 算 MAPE
holdout_n = 7
train = df.iloc[:-holdout_n].copy()
holdout = df.iloc[-holdout_n:].copy()

# 3. 拟合
m = Prophet(
    interval_width=0.80,                # 80% 置信区间
    daily_seasonality=False,            # 日级数据通常没"日内"季节性
    weekly_seasonality=True,
    yearly_seasonality=len(df) >= 365,  # 数据够才开年季节性
    changepoint_prior_scale=0.05,       # 默认；调高更敏感
)
m.fit(train)

# 4. 在 holdout 上算误差
fc_holdout = m.predict(holdout[['ds']])
mape = float(np.mean(np.abs((holdout['y'].values - fc_holdout['yhat'].values)
                             / holdout['y'].values)))
rmse = float(np.sqrt(np.mean((holdout['y'].values - fc_holdout['yhat'].values) ** 2)))
print(f"holdout MAPE = {mape:.3%}, RMSE = {rmse:.2f}")

# 5. 用全量 fit + 预测未来
m_full = Prophet(
    interval_width=0.80,
    weekly_seasonality=True,
    yearly_seasonality=len(df) >= 365,
)
m_full.fit(df)
future = m_full.make_future_dataframe(periods=30, freq='D', include_history=False)
fc = m_full.predict(future)

out = fc[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(columns={'ds': 'date'})
out.to_csv('data/T{n}_forecast_30d.csv', index=False)

# 6. 图
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(df['ds'], df['y'], 'k-', label='历史', linewidth=1.5)
ax.plot(out['date'], out['yhat'], 'b--', label='预测 (yhat)', linewidth=1.5)
ax.fill_between(out['date'], out['yhat_lower'], out['yhat_upper'],
                alpha=0.2, label='80% 区间')
ax.set_title(f"DAU 预测（MAPE={mape:.1%}）")
ax.set_xlabel('date'); ax.set_ylabel('DAU'); ax.legend()
fig.savefig('charts/T{n}_forecast.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# 7. 持久化模型（审计 / 复跑）
with open('models/T{n}_prophet.pkl', 'wb') as fh:
    pickle.dump(m_full, fh)

# 8. 关键点
key_points = out[out['date'].isin([
    out['date'].iloc[0],
    out['date'].iloc[6],
    out['date'].iloc[-1],
])].assign(label=['T+1', 'T+7', 'T+30'])
print("关键预测点：")
print(key_points[['label', 'date', 'yhat', 'yhat_lower', 'yhat_upper']].to_string(index=False))
```

---

## 模板 B · SARIMA（数据量大、季节性强）

```python
"""T{n}: SARIMA 预测"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pickle
from statsmodels.tsa.statespace.sarimax import SARIMAX

df = pd.read_csv('data/T1_dau.csv', parse_dates=['date']).sort_values('date')
assert len(df) >= 90, f"SARIMA 建议 ≥90 天历史，当前 {len(df)} 天"

y = df.set_index('date')['dau'].asfreq('D')
holdout_n = 7
train, holdout = y[:-holdout_n], y[-holdout_n:]

# (p, d, q) x (P, D, Q, s); s=7 周季节性
model = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7),
                enforce_stationarity=False, enforce_invertibility=False)
res = model.fit(disp=False)
fc_holdout = res.get_forecast(steps=holdout_n)
yhat_h = fc_holdout.predicted_mean
mape = float(np.mean(np.abs((holdout - yhat_h) / holdout)))
rmse = float(np.sqrt(np.mean((holdout - yhat_h) ** 2)))
print(f"holdout MAPE = {mape:.3%}, RMSE = {rmse:.2f}")

# 全量 fit + 30 天预测
model_full = SARIMAX(y, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7),
                     enforce_stationarity=False, enforce_invertibility=False)
res_full = model_full.fit(disp=False)
fc = res_full.get_forecast(steps=30)
ci = fc.conf_int(alpha=0.20)  # 80% interval
out = pd.DataFrame({
    'date': pd.date_range(y.index[-1] + pd.Timedelta(days=1), periods=30, freq='D'),
    'yhat': fc.predicted_mean.values,
    'yhat_lower': ci.iloc[:, 0].values,
    'yhat_upper': ci.iloc[:, 1].values,
})
out.to_csv('data/T{n}_forecast_30d.csv', index=False)

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(y.index, y.values, 'k-', label='历史')
ax.plot(out['date'], out['yhat'], 'b--', label='预测')
ax.fill_between(out['date'], out['yhat_lower'], out['yhat_upper'], alpha=0.2)
ax.set_title(f"SARIMA 预测（MAPE={mape:.1%}）"); ax.legend()
fig.savefig('charts/T{n}_forecast.png', dpi=120, bbox_inches='tight')
plt.close(fig)

with open('models/T{n}_sarima.pkl', 'wb') as fh:
    pickle.dump(res_full, fh)
print(f"forecast saved: T+1={out['yhat'].iloc[0]:.1f}, T+30={out['yhat'].iloc[-1]:.1f}")
```

---

## 模板 C · STL + ARIMA（需要先剥季节性）

```python
"""T{n}: STL 剥周期 + ARIMA 残差预测"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.arima.model import ARIMA

df = pd.read_csv('data/T1_dau.csv', parse_dates=['date']).sort_values('date')
assert len(df) >= 56, "STL 至少 8 周（56 天）"

y = df.set_index('date')['dau'].asfreq('D')
stl = STL(y, period=7, robust=True)
res = stl.fit()

trend, seasonal, resid = res.trend, res.seasonal, res.resid
# 在 trend + resid 上跑 ARIMA，季节性单独外推（用最近 1 个 period 平铺）
deseason = trend + resid
arima = ARIMA(deseason.dropna(), order=(1, 1, 1)).fit()
fc = arima.get_forecast(steps=30)
season_template = seasonal.iloc[-7:].values   # 最近一周的季节性 pattern
season_future = np.tile(season_template, int(np.ceil(30 / 7)))[:30]

future_dates = pd.date_range(y.index[-1] + pd.Timedelta(days=1), periods=30, freq='D')
yhat = fc.predicted_mean.values + season_future
ci = fc.conf_int(alpha=0.20)
yhat_lower = ci.iloc[:, 0].values + season_future
yhat_upper = ci.iloc[:, 1].values + season_future

out = pd.DataFrame({'date': future_dates, 'yhat': yhat,
                    'yhat_lower': yhat_lower, 'yhat_upper': yhat_upper})
out.to_csv('data/T{n}_forecast_30d.csv', index=False)

fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
axes[0].plot(y, label='原始'); axes[0].set_title('STL 分解')
axes[1].plot(trend, color='C1', label='trend')
axes[2].plot(seasonal, color='C2', label='seasonal (period=7)')
axes[3].plot(resid, color='C3', label='resid')
for ax in axes: ax.legend(loc='upper right')
fig.savefig('charts/T{n}_stl_decomposition.png', dpi=120, bbox_inches='tight')
plt.close(fig)

# 预测主图
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(y.index, y.values, 'k-', label='历史')
ax.plot(future_dates, yhat, 'b--', label='预测')
ax.fill_between(future_dates, yhat_lower, yhat_upper, alpha=0.2)
ax.set_title('STL+ARIMA 预测'); ax.legend()
fig.savefig('charts/T{n}_forecast.png', dpi=120, bbox_inches='tight')
plt.close(fig)
print(f"forecast: T+1={yhat[0]:.1f}, T+7={yhat[6]:.1f}, T+30={yhat[-1]:.1f}")
```

---

## 必须打到 stdout 的字段（Phase 5 报告引用）

```
holdout MAPE = X.XX%
holdout RMSE = X.XX
forecast: T+1=...  T+7=...  T+30=...
yhat_lower / yhat_upper at T+30 = ... / ...
model file: models/T{n}_*.pkl
```

## 必须显式声明的假设（Phase 5 必写）

- 假设近期斜率 / 周期延续
- 无重大事件（推全 / 政策 / 节假日特殊调整）
- 假设训练数据已过质量门（无大段 NULL / 0 / 异常跳变）
- holdout MAPE 视作历史误差，未来误差**预期不低于** holdout MAPE
