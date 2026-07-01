# 序贯检验（Sequential Testing）：让"偷看"变得安全

> [偷看陷阱](../pitfalls/peeking.md) 一文讲了为什么"看到显著就停"会让 5% 的错误率膨胀到 30%。**序贯检验**是工业级解法——它让你**任意时刻看 p 值都安全**，代价是损失约 20% 的功效。本文讲清三种主流方案及实操落地。

---

## 一、为什么需要序贯检验

固定样本量（fixed-horizon）实验有两个工业痛点：

1. **效果好的不能早停**：实验设计要 14 天，第 5 天就明显大涨——但你按规矩还要等 9 天，业务损失。
2. **效果差的也不能早停**：实验已经明显在伤害指标，但样本量不够"显著"，只能眼睁睁看着烧钱。

序贯检验的承诺：

> **任意时刻、任意频率看 p 值，I 类错误率仍受控**。可以早停、可以无限延长、可以每天看。

代价：

- **大约 20% 的功效损失**（达到同样功效要多约 25% 样本量）
- **统计量计算更复杂**（不是简单 p 值）

业界判断：这个交易在大多数场景下**值得**——尤其是在线 AB 测试的"任何时候都可能要决策"的环境。

---

## 二、核心思想：confidence sequence 替代 p 值

传统假设检验给的是**单一时刻的**置信区间和 p 值——只在"事先固定的样本量"下才有 5% 错误率保证。

序贯检验给的是 **confidence sequence**：

```
传统：     在 n = N 时，CI 包含真值的概率 ≥ 95%
序贯：     在 n = 1, 2, 3, ... 任意时刻，CI 同时包含真值的概率 ≥ 95%
```

直觉上 confidence sequence "更宽"：要承担"一辈子"的覆盖率，不能像 fixed-horizon 那样窄。但这恰恰解决了偷看问题——任何时刻停下都安全。

---

## 三、三种主流序贯方法

### 1. Group Sequential（α 拆分）

**思路**：预先约定看 K 次，把 α 切成 K 份，每次用更严的阈值。

最经典的两个边界：

| 边界 | 特点 | 适用 |
|---|---|---|
| **O'Brien-Fleming** | 早期严、后期宽 | 不希望"早期假阳性早停"，谨慎场景 |
| **Pocock** | 各次同等阈值 | 希望尽早早停，aggressive 场景 |

举例（K=5 次，α=0.05，O'Brien-Fleming）：

```
第 1 次：α₁ = 0.000005
第 2 次：α₂ = 0.0013
第 3 次：α₃ = 0.0085
第 4 次：α₄ = 0.0228
第 5 次：α₅ = 0.0417
```

**优势**：数学严谨、医药临床试验金标准
**劣势**：必须**预先**指定看几次，临时改动作不到

```python
# Python 实现（statsmodels）
from statsmodels.stats.gof import GroupSequential
boundaries = GroupSequential(alpha=0.05, alternative='two-sided',
                              spending_function='obrien-fleming',
                              n_analyses=5).boundaries
```

### 2. mSPRT（Mixture Sequential Probability Ratio Test）

**Optimizely 在 2015 年的论文**（Johari et al., *Peeking at A/B Tests*）让序贯检验进入工业实验平台。

**思路**：不算 p 值，算"似然比"——这是不依赖采样停止规则的统计量。

```
传统：α 是基于样本量的"末位检验"
mSPRT：α 是基于样本路径的"任意时刻检验"

数学上：
  设似然比 Λ_n = L(x_1..n | H₁) / L(x_1..n | H₀)
  停止规则：Λ_n > 1/α  →  拒绝 H₀
  
关键性质：P(任何时刻 Λ_n > 1/α | H₀) ≤ α    ← 这就是任意时刻保证
```

为什么叫 "**m**SPRT"：mixture 是因为对效应量取了一个先验，避免你需要事先指定具体的 H₁。

### 3. Confidence Sequence（Howard 等, 2021）

最现代的非参数方法。基于 martingale 不等式直接构造 always-valid CI：

```
对均值 μ 的 confidence sequence：

   ̂μ_n - C_n  ≤  μ  ≤  ̂μ_n + C_n         对所有 n 同时成立

其中 C_n ≈ √(σ² · log(1/α) / n) · 修正项
```

**优势**：
- 不需要假设分布
- 不需要先验
- 可任意时刻停

**劣势**：
- CI 比传统宽（约 1.5-2 倍）
- 数学背景重

**这是 Netflix 在 *Always Valid Inference for Generalized Linear Models* 等系列论文里推的方向**。

---

## 四、贝叶斯方法（另一条路线）

完全绕开"采样停止"问题——贝叶斯推断**根本不依赖**采样规则。

```
后验：P(B 比 A 好 | data) > 95%  →  上线 B
```

```python
import numpy as np
from scipy.stats import beta

# 转化率实验：A 组 1000 人 50 转化；B 组 1000 人 70 转化
# 用 Beta-Binomial 共轭先验
posterior_A = beta(1 + 50, 1 + 950)
posterior_B = beta(1 + 70, 1 + 930)

# Monte Carlo 估算 P(B > A)
samples_A = posterior_A.rvs(100_000)
samples_B = posterior_B.rvs(100_000)
prob_B_better = (samples_B > samples_A).mean()
print(f"P(B > A) = {prob_B_better:.3f}")
```

| 优势 | 劣势 |
|---|---|
| 没有偷看问题 | 先验选择有争议（不同先验给不同结论） |
| 决策语言更自然 | 团队学习成本 |
| 直接给"B 比 A 好的概率" | 多重比较 / 兜底逻辑仍需思考 |

**实操**：业界主要在贝叶斯实验平台（如 VWO、Convert）里用。自建平台也可以——但需要对贝叶斯推断有共识。

---

## 五、对比：什么时候用哪个

| 方案 | 必须事先约定看几次？ | 早停效率 | 实现复杂度 | 主要缺点 |
|---|---|---|---|---|
| Fixed-horizon（不偷看） | 否（看一次） | 0 | 极低 | 死板，浪费流量 |
| Bonferroni 校正 | 是 | 低 | 极低 | 严过头 |
| Group Sequential | **是** | 中 | 中 | 不灵活 |
| mSPRT | 否 | 高 | 高 | 数学难 |
| Confidence Sequence | 否 | 高 | 高 | CI 较宽 |
| 贝叶斯 | 否 | 高 | 中 | 先验争议 |

**业界落地**：

- 一线大厂（Microsoft / Netflix / 字节 / Optimizely）：**mSPRT 或 confidence sequence**
- 中型公司：**Group Sequential 或贝叶斯**
- 小公司 / 早期：**fixed-horizon + 严格制度**

---

## 六、最小落地代码（mSPRT 简化版）

```python
import numpy as np
from scipy.stats import norm

def msprt_p_value(deltas, sigma, theta_prior=0.05):
    """
    简化的 mSPRT always-valid p 值
    
    Args:
        deltas: 累积观察的 (B - A) 差值数组
        sigma: 标准差估计
        theta_prior: 效应量先验（控制功效与早停的取舍）
    
    Returns:
        always-valid p 值序列
    """
    n = len(deltas)
    cum_sum = np.cumsum(deltas)
    cum_n = np.arange(1, n + 1)
    
    # mSPRT 似然比（Gaussian mixture 近似）
    sd = sigma * np.sqrt(cum_n)
    log_lr = (cum_sum ** 2) / (2 * sd ** 2) * \
             (theta_prior ** 2) / (theta_prior ** 2 + sigma ** 2 / cum_n) - \
             0.5 * np.log(1 + cum_n * theta_prior ** 2 / sigma ** 2)
    
    p_value = np.minimum(1, np.exp(-log_lr))
    return p_value

# 使用
deltas = np.random.normal(0.02, 1, 5000)  # 真实差异 0.02
p_seq = msprt_p_value(deltas, sigma=1)
# 任意时刻 p_seq[i] < 0.05 都可以停
first_significant = np.argmax(p_seq < 0.05)
print(f"第 {first_significant} 步首次显著")
```

> 这只是教学版。生产用需要更严谨的实现：参考 Microsoft `confseq` 库、Netflix `confseq` 库或 Optimizely 公开的伪代码。

---

## 七、实施细节

### 1. SRM 监控仍然要做
序贯检验解决"提前停"问题，**不解决"分流坏了"问题**。SRM 检查独立运行，跟序贯无关。

### 2. 检查间隔不能太密
理论上"每条数据进来都看 p"是允许的，但工程上：
- 每秒看一次 → 数据库压力大
- 业界通常每天 1-3 次 / 小时 1 次

### 3. 序贯检验的"功效成本"
- 同样要达到 80% 功效，序贯比 fixed-horizon 多约 25% 样本量
- 含义：**只在你预期"会偷看"时上序贯**——如果你能严格守纪律 fixed-horizon，反而省样本

### 4. 不同指标用不同方法
- 转化率 → 贝叶斯 Beta-Binomial 最自然
- 连续指标 → mSPRT / confidence sequence
- 比率指标 → 与 [Delta Method](../concepts/hypothesis-testing.md#5-比率指标delta-method) 组合

### 5. 报告时讲清"序贯 stopped early"
"实验在第 7 天达到序贯显著并停止"和"实验跑满 14 天 p < 0.05"是两件事——文档化以便后续复盘。

---

## 八、几个反直觉的事实

### 1. 序贯检验有时**比** fixed-horizon **早**就能停
- 真实效应大时，序贯第 3-5 天就能拒绝 H₀，远早于 fixed-horizon 的 14 天
- 这就是工业级实验平台采用它的根本原因——不是为了合规，是为了**业务节奏更快**

### 2. 序贯不是"灵丹妙药"
- 它换的是"采样规则灵活性 vs 功效"，不是免费午餐
- 如果你的实验从一开始就能严守规则，传统方法功效更高

### 3. "贝叶斯 vs 序贯"是两套世界观
- 序贯仍是 frequentist：控制 I 类错误率
- 贝叶斯：控制后验概率
- **多数工业平台两者都支持**，让用户选

### 4. "总样本不够"序贯也救不了你
- 如果你要的 MDE 现实流量根本支持不了，序贯换方法只是换种死法
- 序贯不替代样本量计算，只放松"必须按计划停"的约束

### 5. mSPRT 的"先验"看起来像贝叶斯但是 frequentist
- mSPRT 的 mixture 先验只是为了让似然比"对各种效应量都有信号"
- 它的错误率保证仍是 frequentist 的（任何 H₀ 真实下错误率 ≤ α）

---

## 九、Checklist

```
□ 1. 我真的需要"任意时刻可看"，还是 fixed-horizon 就够？
□ 2. 用了哪种方法（Group Seq / mSPRT / Confidence Seq / 贝叶斯）？为什么？
□ 3. 检查间隔是多少？数据库压力 OK？
□ 4. 文档化了"序贯 stopped early"的历史，方便后续复盘？
□ 5. 团队（PM、工程师、数据科学）都知道**这是序贯结果不是 fixed-horizon 结果**？
□ 6. SRM 监控独立运行了吗？
□ 7. 多重比较情况下，序贯 + Bonferroni / FDR 怎么组合？
□ 8. 是否计算了"序贯造成的功效损失"，确认实验仍能检出 MDE？
```

---

## 十、扩展阅读

- 本目录：[../pitfalls/peeking.md](../pitfalls/peeking.md)、[../concepts/hypothesis-testing.md](../concepts/hypothesis-testing.md)、[../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md)、[cuped.md](cuped.md)
- Johari, Pekelis, Walsh (2015) — *Peeking at A/B Tests*（mSPRT 工业版本，KDD'15）
- Howard, Ramdas, McAuliffe, Sekhon (2021) — *Time-uniform, nonparametric, nonasymptotic confidence sequences*（confidence sequence 理论基础）
- Lindon & Malek (2022) — *Always Valid Inference for Generalized Linear Models*（Netflix 论文）
- Lan & DeMets (1983) — *Discrete Sequential Boundaries for Clinical Trials*（α-spending 论文）
- Kohavi et al., *Trustworthy Online Controlled Experiments*, Ch.18
- Wald (1945) — *Sequential Tests of Statistical Hypotheses*（SPRT 原始论文，二战军工背景）
- 工具：Microsoft `confseq`、Netflix `confseq` 开源库
