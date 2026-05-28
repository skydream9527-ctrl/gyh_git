# 偷看的代价（Peeking Problem）

> "实验跑了 3 天看了一眼，p < 0.05，停了上线"——这个看似无害的操作，实际上把 5% 的 I 类错误率推高到 20-30%。这是 AB 测试最普遍、最隐蔽、危害最大的陷阱。

---

## 一、什么叫"偷看"

**偷看（Peeking）** 是指：在实验**未跑完预设样本量**之前，反复观察 p 值，并基于"看到了显著"就停止实验做决策。

形式上："**Optional Stopping Based on Significance**"——以显著性为条件的提前停止。

不是偷看的：
- 跑完预设样本量后查看
- 持续监控 SRM、漏斗异常等**质量指标**
- 提前停止是因为业务紧急 / 灾难性下跌 / SRM 报警（与显著性无关）

是偷看的：
- 每天看一次报表，看到 p < 0.05 就上线
- 看到 p = 0.06 决定"再跑两天看看"
- 多次小幅延长样本量直到出现显著

---

## 二、为什么偷看会导致错误率爆炸

### 直觉

p 值在 H₀ 为真时是均匀分布在 [0, 1] 上的随机变量。每次观察，它都有 5% 概率小于 0.05。

如果你只看一次，I 类错误率就是 5%。但每天看一次连看 30 天：

```
30 天每天独立观察一次的 I 类错误率（粗略上限）：
   1 - (1 - 0.05)^30 ≈ 79%
```

实际上每天的 p 值不独立（时间序列相关），实测**偷看 10 次的 I 类错误约 22-28%**。

### 模拟（说服力 > 公式）

```python
import numpy as np

def simulate_peeking(n_total=10000, n_peeks=20, n_simulations=10000):
    """
    H0 真：两组同分布。看 n_peeks 次 p 值，只要任一次 p < 0.05 就当成"发现差异"。
    返回：错误拒绝 H0 的比例。
    """
    false_positive = 0
    peek_points = np.linspace(n_total // n_peeks, n_total, n_peeks).astype(int)

    for _ in range(n_simulations):
        a = np.random.normal(0, 1, n_total)
        b = np.random.normal(0, 1, n_total)  # H0 真
        for k in peek_points:
            from scipy.stats import ttest_ind
            _, p = ttest_ind(a[:k], b[:k])
            if p < 0.05:
                false_positive += 1
                break
    return false_positive / n_simulations

# 试试
print(simulate_peeking(n_peeks=1))    # ≈ 0.05  正确
print(simulate_peeking(n_peeks=5))    # ≈ 0.14
print(simulate_peeking(n_peeks=20))   # ≈ 0.28  偷看 20 次错误率近 30%
```

> 任何工程师跑一遍这段代码，就再也忘不了 peeking 的危害。

---

## 三、为什么这件事在产品组反复发生

不是因为人们故意作弊。是因为**这种行为模式天然契合产品工作节奏**：

1. **看板每天更新**：你打开看实验报告，p 值就在屏幕上
2. **决策有时间压力**：早一天上线，早一天上线收益
3. **直觉的偏置**：看到"显著"就停 = 见好就收，看到"不显著"就继续 = 不甘心
4. **没有人讲明白后果**：组内只学了"p < 0.05 就显著"，没人讲偷看会让 5% 变 30%

这种文化要靠**制度**纠正，光靠"提醒"不行。

---

## 四、五种正确做法

### 方法 1：固定样本量后跑完，不偷看

最简单也最容易被忽视。事前算样本量，事中只看 SRM 和质量监控，**事后**才看 p。

| 优势 | 劣势 |
|---|---|
| 无 peeking，统计干净 | 不能提前停止，浪费流量 / 错过快速决策 |
| 实施零成本 | 等不及的团队会偷偷看 |

### 方法 2：Bonferroni 校正

把 α 除以观察次数：

```
看 K 次 → 每次用 α' = α/K 当阈值
```

例：实验跑 14 天每天看 → 阈值 0.05/14 ≈ 0.0036。

| 优势 | 劣势 |
|---|---|
| 实施超简单 | 过度保守，损失大量功效 |
| 能容忍偷看 | 实际**根本没人在用**——太严了 |

### 方法 3：Group Sequential（α 拆分）

提前预设要看几次，把 α 拆给每次看（O'Brien-Fleming、Pocock 边界）：

```
看 5 次，预先分配 α 边界：
   第 1 次：α₁ = 0.000005
   第 2 次：α₂ = 0.0013
   第 3 次：α₃ = 0.0085
   第 4 次：α₄ = 0.0228
   第 5 次：α₅ = 0.0417
（早期严，后期松——这样早期不会因为噪声误停）
```

| 优势 | 劣势 |
|---|---|
| 在医药临床试验是金标准 | 必须**预先**指定看几次，不能临时决定 |
| 数学严谨 | 工业 AB 实验里"看几次"是动态的，难落地 |

### 方法 4：mSPRT / Always Valid Inference

Optimizely 在 2015 年的论文 *Peeking at A/B Tests*（Johari et al.）解决了这个问题。

核心：用**序贯似然比**而不是 p 值。这种统计量**任何时候停下都不会膨胀错误率**。

```python
# 业界做法的简化思路（伪代码）
def msprt(data_a, data_b, alpha=0.05):
    """
    Always-valid sequential test.
    返回 always-valid p 值（任何时刻偷看都安全）。
    """
    # 维护一个 likelihood ratio
    # 累积 log-LR 超过 log(1/alpha) 时拒绝 H0
    ...
```

| 优势 | 劣势 |
|---|---|
| **完全允许任意频率偷看** | 实现复杂，需要数学背景 |
| 工业级（Optimizely、Microsoft 都用） | 损失约 20% 的功效（统计学版"无免费午餐"） |
| 是现代实验平台的标配 | 不是开箱即用，要自研或用商用平台 |

### 方法 5：贝叶斯方法

用后验概率代替 p 值，没有"次数膨胀"问题：

```
P(B 比 A 好 | data) > 95%  →  上线 B
```

| 优势 | 劣势 |
|---|---|
| 没有偷看问题（贝叶斯不依赖采样停止规则） | 先验选择争议（用什么先验？） |
| 决策语言更自然 | 团队学习成本高 |
| Lift 估计直接给后验分布 | 多重比较 / 兜底处理仍需思考 |

---

## 五、业界主流方案的实际选择

| 公司 | 方案 |
|---|---|
| Microsoft ExP | mSPRT / Group Sequential 混用 |
| Netflix | Always Valid Inference + Bayesian |
| 字节 DataTester | 混合（有 mSPRT 选项） |
| Airbnb | 主要固定样本量 + 早停规则 |
| Optimizely | mSPRT（专利级实现） |
| 多数中小公司 | 固定样本量 + 严格制度（最常见） |

> 没有银弹。**最关键的是制度**——技术再好，团队不遵守一样翻车。

---

## 六、制度落地的几个关键点

如果你在搭实验文化，建议把这些写进规范：

```
1. 实验申请单必须填"样本量、跑多少天、停止规则"
   - 不填不开实验

2. 报告页面"提前显著"时，要求填写"原计划 vs 实际停"差异理由
   - 留痕，季度复盘

3. 默认禁止"看到显著就上线"
   - 要么跑满，要么用平台的 always-valid 模式

4. 每周复盘"短跑实验"占比
   - 高于 30% 说明组内偷看严重

5. 培训 + 持续提醒
   - 让 PM、工程师都懂 5% → 30% 的故事
```

---

## 七、容易混淆的几件事

### 1. "持续监控质量指标"算偷看吗？
- 不算。监控的是 SRM、漏斗、错误率，不是 p 值。它们决定**该不该终止实验**，不是**该不该下结论**。

### 2. "实验跑了 14 天，第 14 天看了 p"算偷看吗？
- 不算。看一次就停 = 标准的 fixed-horizon 检验，无 peeking。

### 3. "我每天只看一次效应量、不看 p"算偷看吗？
- 灰色地带。如果你"基于效应量大就停"，本质和 p 值停止类似（效应量和 p 单调相关）。建议事先定好规则。

### 4. "我看的是置信区间，不是 p 值"
- 一样有问题。CI 不包含 0 ↔ p < α，二者等价。

### 5. "实验 7 天 p=0.06，我多跑 3 天到 0.04 了，能上吗？"
- ⚠️ 高度可疑。这是 peeking 的典型症状。
- 正确做法：要么事先就规划 10 天，要么用 always-valid 方法。

---

## 八、Checklist

```
□ 1. 实验有事先约定好的样本量 / 时长吗？
□ 2. 中途看 p 值是否会触发"提前上线" 决策？
□ 3. 实验平台是否支持 always-valid 推断？
□ 4. 团队规范里有没有写清"什么是合规的提前停止"？
□ 5. 复盘时有没有看"提前停止 vs 跑满"实验的占比？
□ 6. 报告页面对"未达样本量"的实验有警告吗？
```

---

## 九、扩展阅读

- 本目录：[../concepts/hypothesis-testing.md](../concepts/hypothesis-testing.md)、[../concepts/power-and-sample-size.md](../concepts/power-and-sample-size.md)
- Evan Miller — *How Not To Run an A/B Test*（经典短文，必读）
- Johari, Pekelis, Walsh — *Peeking at A/B Tests* (KDD 2015，mSPRT 论文)
- Howard, Ramdas, McAuliffe, Sekhon — *Time-uniform, nonparametric, nonasymptotic confidence sequences*（confidence sequence 理论基础）
- Lindon & Malek — *Always Valid Inference for Generalized Linear Models* (Netflix 论文)
- Kohavi et al., *Trustworthy Online Controlled Experiments*, Ch.18 "The Statistics behind Online Controlled Experiments"
