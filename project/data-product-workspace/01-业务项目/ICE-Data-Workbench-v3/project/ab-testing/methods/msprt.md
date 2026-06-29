# mSPRT — 工业级"任意时刻可看"的实验方案

> **mSPRT**（Mixture Sequential Probability Ratio Test）是 Optimizely 在 2015 年 KDD 论文 *Peeking at A/B Tests* 中引入工业实验的方案——它让"任意时刻看 p 值都安全"成为可工程化部署的方法。本文从机制讲到落地，给出可工程化的伪代码、参数选择经验、和上线注意事项。

> 上下文：
> - [pitfalls/peeking.md](../pitfalls/peeking.md) — 偷看为什么把 5% 错误率推到 30%
> - [methods/sequential-testing.md](sequential-testing.md) — 序贯检验家族总览（含 Group Sequential / Confidence Sequence / 贝叶斯）

---

## 一、它解决的工业痛点

固定样本量（fixed-horizon）实验有两个工业级痛点：

1. **效果好的不能早停**：实验设计要 14 天，第 5 天就明显大涨——按规矩还要等 9 天，业务损失。
2. **效果差的也不能早停**：明显在伤害指标，但样本量不够"显著"，只能眼睁睁看着烧钱。

Group Sequential（α-spending）能早停，但要求**事先预定**几次中期分析——不灵活。

mSPRT 给的承诺：

> **任意时刻、任意频率看，I 类错误率仍 ≤ α。** 不需要预定看几次。

代价：

- ~20% 的功效损失（达到同样功效要多约 25% 样本量）
- 实现复杂度上升（需要选 prior、做数值积分）
- 团队需要懂 likelihood ratio 概念

---

## 二、核心：从 SPRT 到 mSPRT

### 2.1 SPRT（Sequential Probability Ratio Test, Wald 1945）

二战年代 Abraham Wald 给的方法：

```
H₀: μ = 0           （无效应）
H₁: μ = δ           （有效应，δ 已知）

定义似然比：
   Λ_n = ∏_{i=1}^n  f(x_i | H₁) / f(x_i | H₀)

停止规则（A、B 是两个边界，A < 1 < B）：
   Λ_n ≥ B  →  拒绝 H₀（"有效应"）
   Λ_n ≤ A  →  接受 H₀（"无效应"）
   A < Λ_n < B  →  继续观察
```

**关键性质**：在 H₀ 真实下，`Λ_n` 是个 martingale，由 **Doob's optional stopping**：

```
P(任何时刻 Λ_n ≥ 1/α | H₀) ≤ α
```

→ 任意时刻看，错误率仍 ≤ α。

**SPRT 的工业局限**：

- 必须事先指定具体的 H₁（即 δ 的具体值）
- 在线实验里"我猜效应是 1%"——猜错了功效大幅下降

---

### 2.2 mSPRT：用 mixture 替代单点 H₁

Robbins (1970) 的扩展：**对 δ 取一个 prior 分布**，而不是固定一个 δ。

```
mixture 似然比：
   Λ_n = ∫ ∏ f(x_i | δ) / f(x_i | 0)  · π(δ)  dδ

   π(δ) 是对效应量的先验（典型用 Normal(0, τ²)）
```

直觉：
- SPRT 押注一个具体 δ
- mSPRT 押注一**簇** δ，先验加权积分
- 任何效应量 δ_true 都"被 mixture 覆盖"，不需要事先猜对

**关键定理**（Robbins）：

```
对任何停止时刻 N（哪怕基于 Λ_n 自己选）：
   P(任何时刻 Λ_n ≥ 1/α | H₀) ≤ α
```

→ **always-valid p-value**：

```
p̃_n = min(1, 1/Λ_n)
```

任意时刻看 `p̃_n`，把它当 p 值用，I 类错误率仍 ≤ α。

---

## 三、工业最常用的形式（Normal-Normal 情形）

### 3.1 假设

- 单观测 X_i ~ N(μ, σ²)，σ² 已知或可估
- H₀: μ = 0
- H₁: μ ≠ 0
- Prior: μ ~ N(0, τ²)

### 3.2 闭式解

```
        ̂μ_n = (1/n) Σ x_i              样本均值
        S_n  = ̂μ_n · n                  累积和

似然比：
   Λ_n = √(σ² / (σ² + n·τ²)) · exp(  S_n² / (2 · (σ²/n + τ²) · n²)  )
```

简化为 always-valid p 值：

```
p̃_n = min(1, 1/Λ_n)
```

### 3.3 对应到双样本（A/B）

```
处理组 - 对照组的均值差：
   D_i = X_B,i - X_A,i

视为单样本，按上面公式套用即可（σ² → 2σ²）。
```

---

## 四、Python 教学版实现

```python
import numpy as np

def msprt_log_lr(cum_diff, n, sigma_sq, tau_sq):
    """
    mSPRT log likelihood ratio (Normal-Normal)
    
    Args:
        cum_diff: 累积差值 = sum(B - A)
        n: 累积样本量（每组）
        sigma_sq: 单观测方差
        tau_sq: 效应量先验方差（核心调参）
    
    Returns:
        log Λ_n
    """
    # 后验方差
    post_var = 2 * sigma_sq / n + tau_sq
    log_lr = (
        0.5 * np.log(2 * sigma_sq / (2 * sigma_sq + n * tau_sq))
        + (cum_diff ** 2) / (2 * post_var * n ** 2) * tau_sq
    )
    return log_lr


def msprt_p_value(cum_diff, n, sigma_sq, tau_sq):
    """always-valid p value"""
    log_lr = msprt_log_lr(cum_diff, n, sigma_sq, tau_sq)
    return np.minimum(1.0, np.exp(-log_lr))


# 模拟使用
np.random.seed(42)
true_lift = 0.02     # 真实效应 2%
sigma = 1.0
n_total = 100_000

x_a = np.random.normal(0, sigma, n_total)
x_b = np.random.normal(true_lift, sigma, n_total)
diff = x_b - x_a
cum = np.cumsum(diff)

# 选择先验：τ² 一般设成"业务期望的最小可检测效应量"
tau = 0.01           # 1%
p_seq = np.array([
    msprt_p_value(cum[n-1], n, sigma**2, tau**2) 
    for n in range(100, n_total, 100)
])

# 第一次显著的样本量
first_sig = np.argmax(p_seq < 0.05) * 100 + 100
print(f"mSPRT 在 n = {first_sig} 时首次显著")
```

→ 任意时刻看 `p_seq[i]`，p < α 就停。

---

## 五、最关键的工程决策：prior 方差 τ² 怎么选

mSPRT 的功效高度依赖 τ² 的选择：

```
τ² 太大（远超真实效应）：
   先验太散，似然比累积慢 → 早停困难

τ² 太小（远小于真实效应）：
   先验过度集中在 0 → 真效应来时也"看不见"

τ² 刚好等于真实效应量：
   功效接近 SPRT（理论最优）
```

但你不知道真实效应——这就是 mSPRT 用 mixture 的原因。

### 经验设法

**经验值**：把 τ² 设成"业务关心的最小可检测效应（MDE）"的平方。

```
你说"如果转化率涨 1% 我就上线"
→ MDE = 0.01
→ τ² = 0.01² = 0.0001
```

含义：
- 真实效应在 ±MDE 量级 → 早停效率最高
- 真实效应远大于 MDE → 仍能早停（只是相对偏慢）
- 真实效应远小于 MDE → 你本来就不该期待早停

### 多元 prior（高级）

也可以用 mixture of Normals，覆盖多个量级的效应：

```
π(δ) = 0.5 · N(0, τ₁²) + 0.5 · N(0, τ₂²)
       (大效应)         (小效应)
```

复杂度上升但鲁棒性更好。Optimizely / Netflix 内部都用类似变体。

---

## 六、和其他"always-valid"方法的对比

| 方法 | 优势 | 劣势 |
|---|---|---|
| **mSPRT** | 工业最早落地、有大量实战经验 | 需要选 prior |
| **Confidence Sequence**（Howard et al. 2021） | 不需要 prior、非参数 | CI 较宽（约 1.5-2× SPRT） |
| **Group Sequential** | 经典、易解释 | 必须**预先**指定看几次 |
| **Bayesian** | 完全绕开偷看问题 | 团队学习成本 |
| **e-process / e-value**（最新） | 数学上最干净 | 工业实践仍少 |

→ 详见 [sequential-testing.md](sequential-testing.md) 第 5 节的横向对比。

工业落地的现实选择：

- 中小公司：直接用商用平台（Optimizely / VWO）的 always-valid 模式
- 大公司：自研 mSPRT 或 Confidence Sequence
- 数据团队偏数学派：Confidence Sequence（更"干净"）
- 数据团队偏经验派：mSPRT（资源最丰富）

---

## 七、上线注意事项

### 7.1 仅做"代替 p 值"，不改实验流程

mSPRT 不替代：
- 样本量计算（[power-and-sample-size.md](../concepts/power-and-sample-size.md)）
- SRM 检测
- CUPED 等方差缩减（[cuped.md](cuped.md)）
- 多重比较校正

它**只**改"能不能任意时刻看 p"。其他实验质量保证仍要做。

### 7.2 阈值 α 的解读

```
传统 fixed-horizon p：    H₀ 真实下，n=N 时 p < α 概率 ≤ α
always-valid p：         H₀ 真实下，∀n p_n < α 概率 ≤ α
```

→ 给团队培训时务必讲清——always-valid p 的 0.05 含义和传统 p 的 0.05 不同（前者是"全程不超过"，后者是"单次不超过"），但**业务决策都按 < 0.05 行动是 OK 的**。

### 7.3 结合其他指标

mSPRT 给了"是否有效应"的判断。但工程上还要：

- **效应量 + CI**：always-valid CI（见 Howard et al.）报告"涨多少"
- **业务护栏指标**：关键护栏不能跌
- **SRM 监控**：分流坏了 mSPRT 也救不了

### 7.4 多变体（A/B/C/D）

- 朴素：A vs B、A vs C、A vs D 各跑 mSPRT，再做 Bonferroni 调 α
- 高级：用多元 mSPRT，直接联合似然比

业界实际做法：**预先指定主对比对**（A vs B），其他对比按 family-wise 校正。

### 7.5 不要"半路改 prior"

τ² 在实验启动前定下来，**实验跑过程中不能改**。否则 always-valid 性质破坏。

---

## 八、报告模板

mSPRT 实验结果报告应当包含：

```
✦ 实验名称、起止时间
✦ 主指标（OEC）+ 护栏指标
✦ 分流：50/50（或其他比例），SRM 检查通过
✦ 当前样本量 + 累积差值
✦ always-valid p 值
✦ Effect estimate + always-valid 95% CI
✦ 决策：上线 / 下线 / 继续观察
✦ 使用方法：mSPRT (Normal-Normal, τ² = 0.0001)
```

最后一行的"使用方法 + τ²"必须写清——这是后续审计 / 复现的关键。

---

## 九、常见坑

### 1. 团队把 always-valid p < 0.05 当作 fixed-horizon
- 数学上错误率仍 ≤ 5%，但**含义不同**——团队可能误以为可以"还看一眼" 之类
- 解法：培训 + 报告页面明示"always-valid"

### 2. 忽视样本量计算
- 觉得 mSPRT "随便看" 就不算样本量
- 真实情况：mSPRT **不缩短**期望样本量（甚至会拉长 ~25%）
- 它只让你**有机会**早停

### 3. SRM 出现也不停
- mSPRT 不防 SRM
- SRM 报警必须立刻终止——这和检验方法无关

### 4. 把 τ² 选成业务期望涨幅
- 例：业务希望涨 10%，τ² 设成 0.1²
- 实际效应可能只有 1%，τ² 严重过大 → 永远停不下来
- 经验：**τ² 设成 MDE 而不是"愿景"**

### 5. 多变体没校正 α
- A/B/C/D 四组对 A 比 → 三个对比，每个用 α=0.05 → family-wise 错误率 ~14%
- 解法：α/k 或显式预指定对比对

---

## 十、Checklist

```
□ 1. 我清楚 mSPRT vs Group Sequential vs Confidence Sequence 的差异吗？
□ 2. τ² 是基于业务 MDE 设的，不是基于"期望涨幅"？
□ 3. τ² 在实验启动前固定，过程不改？
□ 4. SRM、护栏指标、样本量计算都没省？
□ 5. 报告页明示"always-valid"，避免团队误读？
□ 6. 多变体 / 多指标做了校正？
□ 7. CI 用 always-valid 版本，不是 fixed-horizon 版本？
□ 8. 决策门槛 + 停止规则文档化（不只是"看到显著就停"）？
```

---

## 十一、扩展阅读

### 必读
- **Johari, Pekelis, Walsh (2015)** — *Peeking at A/B Tests*, KDD'15（**奠基论文**）
- Wald (1945) — *Sequential Tests of Statistical Hypotheses*（SPRT 原始）
- Robbins (1970) — *Statistical Methods Related to the Law of the Iterated Logarithm*（mixture 思想）

### 现代延伸
- **Howard, Ramdas, McAuliffe, Sekhon (2021)** — *Time-uniform, nonparametric, nonasymptotic confidence sequences*（confidence sequence 理论）
- Lindon & Malek (2022) — *Always Valid Inference for Generalized Linear Models*（Netflix）
- Maharaj, Sinha, Arbour (2023) — *Anytime-Valid Confidence Sequences for ATEs*

### 工程视角
- Optimizely Engineering Blog: *Stats Engine* 系列
- Microsoft *ExP Platform* 论文系列
- Netflix Tech Blog: *Quasi-Experimentation* / *Always Valid Inference*

### 工具
- Microsoft `confseq`（开源）
- Netflix `confseq`（开源）
- Python `statsmodels` 的部分序贯功能

### 本目录
- [sequential-testing.md](sequential-testing.md) — 序贯检验家族总览
- [pitfalls/peeking.md](../pitfalls/peeking.md) — 偷看代价
- [concepts/hypothesis-testing.md](../concepts/hypothesis-testing.md) — 假设检验基础
- [concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md) — 样本量
- [methods/cuped.md](cuped.md) — 配合 mSPRT 用的方差缩减
