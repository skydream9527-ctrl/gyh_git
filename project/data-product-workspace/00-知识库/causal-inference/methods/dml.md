# Double / Debiased Machine Learning（DML）

> DML（Chernozhukov et al., 2018）是过去 10 年因果推断领域最大的红利之一——它**让"用任意 ML 模型做因果估计"在统计上变得严谨**。如果你已经在用 XGBoost / 神经网络做预测，DML 让你免费拿到一套估因果效应的工具。

---

## 一、它在解决什么

倾向得分（[propensity-score.md](propensity-score.md)）有个软肋：**当 X 高维或非线性时，PS 模型容易偏**。线性 logit 拟不动复杂关系，但用 ML 又面临"过拟合 → 偏差不收敛"的问题。

DML 同时解决两件事：

1. **可以放心用 ML**：随便用 XGBoost / 神经网络估 PS 和结果模型
2. **统计性质好**：估出来的因果效应仍然是**√n-consistent**（标准误差按 1/√n 收敛），可以做置信区间

它的两个关键技巧：

- **Neyman 正交（Orthogonalization）**：把 ML 模型的小偏差消掉
- **交叉拟合（Cross-fitting）**：把训练集和估计集分开，避免过拟合污染

---

## 二、DML 的标准设定

### 部分线性模型（PLM, Partial Linear Model）

最常用的设定：

```
Y = θ · T + g(X) + ε       结果方程（θ 是因果效应）
T = m(X) + η                处理方程（X 决定处理倾向）
```

直觉：把处理 T 和结果 Y 都对 X "残差化"，剩下的关系就是 T 对 Y 的纯因果效应。

### 三步流程（核心）

```
Step 1：用 ML 估两个 nuisance 模型
        m̂(X) = E[T | X]            ← 倾向得分（连续或离散）
        ĝ(X) = E[Y | X]            ← 结果模型

Step 2：算残差
        T_resid = T - m̂(X)
        Y_resid = Y - ĝ(X)

Step 3：用残差回归得到 θ
        θ̂ = (T_resid · Y_resid).sum() / (T_resid²).sum()
```

这个 θ̂ 就是因果效应估计——**而且无论 m̂、ĝ 是不是线性的，都成立**。

---

## 三、Neyman 正交：为什么这样做有效

朴素做法的问题：

```
Y = θT + g(X) + ε
直接对所有变量回归 Y ~ T + X：
   ML 模型估 g(X) 时会"误吸收一部分" T 的效应 → θ 估计有偏
```

DML 的关键是**残差化**：

```
T_resid = T - E[T|X]   ← 只剩下"X 不能解释的 T 变化"
Y_resid = Y - E[Y|X]   ← 只剩下"X 不能解释的 Y 变化"

两者的关系就是 θ 的纯效应。
```

数学上这叫 **Neyman 正交条件**：score 函数对 nuisance 参数的偏导在真实值处为 0——意味着 nuisance 估计的小偏差**不会**传染给 θ。

---

## 四、交叉拟合：避免过拟合污染

如果你用同一份数据训练 nuisance 模型 + 估 θ，ML 模型的过拟合会让残差里包含"假的可预测性"，θ 估计有偏。

**解法**：K-fold 交叉拟合。

```
1. 把数据切成 K 份（典型 K=2 或 5）
2. 用第 i 份外的数据训练 m̂、ĝ
3. 在第 i 份上算残差
4. 把所有 fold 的残差拼起来再算 θ
```

```python
from sklearn.model_selection import KFold

def cross_fit_dml(X, T, Y, m_model, g_model, K=5):
    kf = KFold(n_splits=K, shuffle=True)
    T_resid = np.zeros_like(T, dtype=float)
    Y_resid = np.zeros_like(Y, dtype=float)
    
    for train, test in kf.split(X):
        m_model.fit(X[train], T[train])
        g_model.fit(X[train], Y[train])
        T_resid[test] = T[test] - m_model.predict(X[test])
        Y_resid[test] = Y[test] - g_model.predict(X[test])
    
    # OLS 估 θ
    theta = (T_resid * Y_resid).sum() / (T_resid ** 2).sum()
    # 标准误（简化版）
    n = len(Y)
    psi = T_resid * (Y_resid - theta * T_resid)
    var_theta = (psi ** 2).mean() / (T_resid ** 2).mean() ** 2 / n
    return theta, np.sqrt(var_theta)
```

---

## 五、用 EconML（推荐）

实操中用 Microsoft 的 `econml`，几行代码搞定：

```python
from econml.dml import LinearDML, NonParamDML
from sklearn.ensemble import GradientBoostingRegressor

# 二元处理 T
est = LinearDML(
    model_y=GradientBoostingRegressor(),
    model_t=GradientBoostingRegressor(),  # 二元用 Classifier
    discrete_treatment=True,
    cv=5
)
est.fit(Y, T, X=X)
print(est.effect(X))             # 每个样本的 CATE
print(est.const_marginal_effect_inference(X).summary_frame())  # 含 CI
```

---

## 六、DML 的三个变体

### 1. Linear DML
- θ 是单个数（常数效应）
- 计算最简单，工业最常用

### 2. NonParametric DML
- θ 随 X 变化（CATE）
- 输出每个样本的因果效应估计

### 3. Causal Forest（属于 DML 家族）
- 用随机森林分裂找异质效应
- 适合做个体化因果决策（与 [uplift-modeling.md](uplift-modeling.md) 强相关）

---

## 七、什么时候用 DML

**强烈推荐**：

- 协变量高维（几十到几百个）
- 关系非线性（XGBoost 比线性回归在预测 Y 上明显好）
- 有兴趣估 CATE（异质效应）
- 团队里已经有 ML 工程能力

**用 PSM/IPW 反而更合适**：

- 协变量少 + 线性关系成立
- 团队对统计推断更熟悉，不太用 ML
- 解释性优先（PS 直观一些）

**根本不该用任何观察方法**（直接做实验）：

- 能做 AB
- 关键决策有政治 / 合规风险

---

## 八、五个使用细节

### 1. nuisance 模型不需要"拟合到完美"
- DML 的统计性质要求 m̂ 和 ĝ 各自的 MSE 收敛速度乘积 ≥ 1/n
- 业务上：每个模型 MSE 收敛到 n^(-1/4) 就够（比 1/√n 慢）
- 含义：用 XGBoost 默认参数通常够用，不用过度调参

### 2. 处理 T 是连续的也行
- 连续处理（如广告花费）→ m̂ 是回归（不是分类）
- 业界做剂量响应（dose-response）经常这么用

### 3. 多重处理（A/B/C 多变体）
- EconML 支持，但理论保证不如二元处理强
- 实际操作：每对处理之间分别 DML

### 4. 异质效应的注意事项
- CATE 估计比 ATE 估计**方差大很多**
- 不要在每个用户上看 CATE 数字，要看分位数 / 子群均值
- 与 Uplift Modeling 紧密相关（→ [uplift-modeling.md](uplift-modeling.md)）

### 5. 假设的"小字"
- DML 不放松 Ignorability：协变量足够、Positivity 成立、SUTVA 成立——这些假设没了 DML 一样翻车
- 它放松的是**模型形式假设**（不必线性），不是**因果识别假设**

---

## 九、和其他方法的关系

```
PSM / IPW       →  线性 PS 估计，二元 T 友好
回归调整         →  线性结果模型
DR (Doubly Robust) →  PS + 回归两个一起，至少一个对就稳
DML              →  在 DR 基础上加 ML + 交叉拟合 + Neyman 正交
                    （从某种意义上 DML = ML 版的 DR）
Causal Forest    →  DML 的非参数树版
```

---

## 十、Checklist

```
□ 1. 协变量足够吗？（DML 不解决"漏掉混淆"问题）
□ 2. Y 模型和 T 模型分别用什么算法？是否做了 K-fold 交叉拟合？
□ 3. 检查 m̂(X) 是否极端（< 0.05 或 > 0.95）？
□ 4. 估 ATE 还是 CATE？
□ 5. 是否做了 sanity check（如 placebo 检验 / 随机置换 T 后 θ̂ 应接近 0）？
□ 6. 报告里给了 95% CI 吗？（DML 的优势就是有渐近正态性）
□ 7. 和 PSM / 简单回归的结果是否大方向一致？（不一致的话查问题）
```

---

## 十一、扩展阅读

- 本目录：[propensity-score.md](propensity-score.md)、[uplift-modeling.md](uplift-modeling.md)
- Chernozhukov et al. (2018) — *Double/Debiased Machine Learning for Treatment and Structural Parameters* — **奠基论文**
- Athey & Wager (2019) — *Estimating Treatment Effects with Causal Forests*
- EconML 官方文档：https://econml.azurewebsites.net/
- Microsoft Research — *EconML: Powerful Machine Learning Methods for Heterogeneous Treatment Effects*
- 综述：Knaus, Lechner, Strittmatter (2021) — *Machine learning estimation of heterogeneous causal effects*
