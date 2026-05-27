# NL → Python（沙箱里跑分析）

在 ICE Workbench 数据分析任务里生成沙箱可执行的 Python 代码，做 SQL 之外的统计 / 预测 / 可视化。

**触发场景**：用户提"预测 / Prophet / ARIMA / 拟合 / 变点 / STL / cohort 拟合 / 留存外推 / KS test"；或 data-analysis agent 进入 Phase 4e（范式 tag = `[波动/分布/趋势/预测/8d/8e/8f]`）。
**主要功能**：按范式生成模板代码 → `execute_python` 沙箱执行 → 落 `data/T{n}_*.csv` + `charts/T{n}_*.png` + `models/T{n}_*.pkl`。
**沙箱契约**：白名单包（pandas / numpy / scipy / sklearn / statsmodels / prophet / ruptures / matplotlib / seaborn）；网络全断；CPU 60s + 内存 1G；不直连数据源（永远是 SQL 的下游消费者）。
