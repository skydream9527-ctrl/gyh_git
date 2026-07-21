# 训练显存与通信优化

> 分布式训练的并行策略解决"怎么切"，本文解决"切完之后怎么榨干每一 GB 显存、每一点带宽"。混合精度、激活重计算、算子融合、集合通信拓扑——这些是 MFU（Model FLOPs Utilization）从 30% 提到 55% 的真正杠杆。一个细节没做好，千卡集群的有效算力可能只有标称的 35%。

---

## 一、显存都花在哪了：精确拆解

训练一步的显存 = 权重 + 梯度 + 优化器状态 + 激活 + 临时 buffer。以 70B、BF16、Adam、seq=2048、batch=1 为例：

| 组成 | 大小 | 占比 | 能不能省 |
|---|---|---|---|
| 权重（BF16） | 140 GB | 14% | ZeRO-3 / TP 切分 |
| 梯度（BF16） | 140 GB | 14% | ZeRO-2 / TP 切分 |
| 优化器状态（FP32 m,v） | 560 GB | 56% | ZeRO-1 切分（最大头） |
| 激活 | 80-160 GB | 16% | 重计算 / TP 切分 |
| 临时 buffer | 10-20 GB | - | 算子融合减少 |

**关键洞察**：优化器状态是最大的显存杀手（占一半以上），这就是 ZeRO-1 收益最大的原因。激活是第二大，靠重计算和 TP 切。

---

## 二、混合精度训练

### 1. 为什么不直接用 FP32

FP32 每个参数 4 bytes，70B 模型光权重就 280GB。BF16/FP16 只要 2 bytes，**显存减半、计算速度翻倍**（GPU 的 Tensor Core 对低精度有专门加速）。

### 2. 三种主流精度策略

| 精度 | 权重 | 梯度 | 优化器状态 | 说明 |
|---|---|---|---|---|
| FP32 | FP32 | FP32 | FP32 | 基准，慢且费显存 |
| FP16 + loss scaling | FP16 | FP16 | FP32 | 老方案，需动态 loss scale 防下溢 |
| BF16（推荐） | BF16 | BF16 | FP32 | 动态范围大，**无需 loss scaling**，现代 GPU 首选 |
| FP8（H100+） | FP8 | FP8/BF16 | FP32 | 最新，速度再提 1.5-2×，精度管理复杂 |

### 3. 混合精度的"混合"在哪

不是全程低精度，而是**计算用低精度、累积用高精度**：

```
前向/反向计算：BF16（快、省显存）
梯度累积 / 优化器更新：FP32（保数值精度）
主权重 master weight：FP32（始终维护一份高精度副本）
```

**为什么 BF16 比 FP16 安全**：BF16 有 8 位指数（和 FP32 一样），动态范围大，不会像 FP16 那样在反向传播时梯度下溢。**A100/H100 时代默认 BF16**，FP16 基本退出训练场景。

### 4. FP8 训练（前沿）

H100 引入 FP8（E4M3 / E5M2 两种格式），显存再省一半、算力再翻倍。但：

- 精度管理复杂：不同算子用不同格式（前向 E4M3、反向 E5M2）
- 需要 per-tensor 或 per-row scaling factor 防精度损失
- 目前主要在 Transformer Engine、MS-AMP 等框架支持
- **生产训练仍以 BF16 为主，FP8 是 2024-2025 的前沿方向**

---

## 三、激活重计算（Activation Checkpointing / Gradient Checkpointing）

### 1. 问题：激活吃显存

前向传播时每层的中间激活都要存着给反向用。70B、seq=2048、batch=1 的激活约 80-160GB，**比权重还大**。

### 2. 思路：用计算换显存

前向时不存中间激活，反向时重新算一遍：

```
朴素：前向存所有激活 → 反向直接用         （省计算，费显存）
重计算：前向不存 → 反向时重算前向         （省显存，费计算，多约 33% 前向算力）
```

### 3. 三种重计算策略

| 策略 | 显存节省 | 额外计算 | 说明 |
|---|---|---|---|
| Full（每层都重算） | 最大 | +33% | 最省显存，最慢 |
| Selective（只重算 attention） | 中 | +10-15% | **推荐**，attention 激活大但 FLOPs 小，性价比最高 |
| Uniform（每 N 层切一段） | 可调 | 可调 | 折中 |

**实战经验**：Selective recompute（只重算 attention 的 QKV softmax 中间量，保留 FFN 激活）是性价比最高的——激活显存砍 60-70%，额外计算只增 10%。Megatron-LM 默认就是这个。

---

## 四、算子融合（Operator Fusion）

### 1. 核心思想

GPU 算得快，但"把中间结果写回 HBM 再读出来"很慢。把多个算子融合成一个 kernel，中间结果留在 SRAM/寄存器，**省的是内存带宽**。

### 2. 典型融合

| 融合 | 朴素 | 融合后 | 收益 |
|---|---|---|---|
| Scale + Mask + Softmax | 3 次 HBM 读写 | 1 个 fused kernel | attention 提速 2-4× |
| Bias + Dropout + Residual + LayerNorm | 4 个 kernel | 1 个 fused kernel | 省带宽 |
| Linear + Bias + GELU | 3 个 kernel | 1 个 fused kernel | FFN 提速 |
| 反向 + 梯度计算 | 分步 | fused backward | 反向提速 |

**FlashAttention 就是极致的算子融合**：把整个 attention（QK^T → mask → softmax → ×V）融合成一个不写中间矩阵的 kernel。详见 [04-inference-optimization.md](04-inference-optimization.md)。

### 3. 实践

- 用 Megatron-LM / DeepSpeed / PyTorch 2.x 的 fused kernel，不要手写
- PyTorch 2.x 的 `torch.compile` 能自动做图级融合
- 自定义算子用 Triton 写（比 CUDA 易维护）

---

## 五、集合通信：分布式训练的"血管"

### 1. 五大集合通信原语

| 原语 | 语义 | 典型用途 | 通信量 |
|---|---|---|---|
| Broadcast | 一卡 → 所有卡 | 参数同步 | ∝ 参数 |
| Reduce | 所有卡 → 一卡（求和等） | 梯度汇总到主卡 | ∝ 参数 |
| AllReduce | 所有卡 → 所有卡（都拿到结果） | **DP 梯度同步** | ∝ 参数 |
| AllGather | 各卡拼一份 → 每卡都拿全量 | TP 前向拼结果、ZeRO-3 取参数 | ∝ 参数 |
| ReduceScatter | 求和后切分 → 每卡拿一段 | ZeRO-2/3 梯度切分、TP 反向 | ∝ 参数/N |

### 2. AllReduce 的两种实现

AllReduce 是 DP 的核心，有两种底层实现：

```
Ring AllReduce（环形）:
  GPU0 → GPU1 → GPU2 → GPU3 → GPU0   (环形传递)
  阶段1: scatter-reduce（每卡汇聚一段）
  阶段2: allgather（每卡拿到完整结果）
  通信量 = 2 × (N-1)/N × 参数量，与 N 几乎无关 ← 适合大集群

Tree AllReduce（树形）:
  层层归约再广播，延迟低但带宽利用率不如 Ring
  适合小集群 / 低延迟场景
```

**NCCL**（NVIDIA）和 **RCCL**（AMD ROCm）默认用 Ring，大集群下带宽利用率最优。

### 3. 通信拓扑：机内 vs 跨机

| 互联 | 带宽 | 延迟 | 用途 |
|---|---|---|---|
| NVLink / NVSwitch | 300-900 GB/s | 低 | 机内 TP、ZeRO-3 |
| PCIe Gen4/5 | 64-128 GB/s | 中 | 机内备用 |
| InfiniBand（IB） | 200-400 Gb/s | 中 | 跨机 DP/PP |
| RoCE（以太网） | 100-400 Gb/s | 中高 | 跨机，成本低于 IB |

**铁律**：高频通信（TP、ZeRO-3 取参数）放机内 NVLink，低频通信（DP 梯度、PP 激活）放跨机 IB。配错了 → 通信占比从 15% 飙到 60%。

### 4. 通信与计算 overlap

好的训练框架会把通信藏到计算后面：

- DP：反向算完一层就异步 AllReduce 该层梯度，和下一层反向计算重叠
- PP：stage 间传激活和下一 micro-batch 计算重叠
- ZeRO-3：prefetch 下一层参数，和当前层计算重叠

**没 overlap 的框架，通信时间是纯空等**。这是 Megatron-LM 比"手写多卡脚本"快几倍的关键。

---

## 六、MFU：衡量训练效率的硬指标

### 1. 定义

```
MFU = 实际训练吞吐 (tokens/s) × 6 × 参数量 / GPU峰值FLOPS / GPU数
```

其中 `6 × 参数量 × tokens` 是训练一个 token 的理论 FLOPs（前向 2 + 反向 4）。

### 2. 基准

| 模型规模 | 硬件 | 优秀 MFU | 及格 MFU |
|---|---|---|---|
| 7B | A100 8卡 | 45-52% | 30% |
| 70B | H100 千卡 | 50-55% | 35% |
| 175B | H100 千卡 | 55%+ | 40% |

**MFU 低于 35% 一定有问题**：通信没 overlap、batch 太小、算子没融合、TP 跨机、数据加载瓶颈……逐项排查。

### 2. 常见 MFU 杀手

| 现象 | 原因 | 解法 |
|---|---|---|
| MFU 随卡数增加而下降 | 通信占比上升 | 增大 batch、减少跨机通信 |
| MFU 远低于理论 | 数据加载瓶颈 | 增加 dataloader worker、预取 |
| 单机内 MFU 低 | 算子没融合 | 用 fused kernel / torch.compile |
| 反向比前向慢很多 | 重计算策略不当 | selective recompute 替代 full |

---

## 七、常见踩坑

1. **BF16 忘了开**：默认 FP32 训练，显存翻倍、速度减半。检查 `torch.autocast(dtype=torch.bfloat16)`。
2. **重计算开成 full**：显存省了但 MFU 掉 20%。改 selective，只重算 attention。
3. **AllReduce 没开异步**：同步 AllReduce 会阻塞，整个反向算完才开始通信。用 `reduce_async` / 框架的 overlap。
4. **TP 跨机**：见 [01-distributed-training.md](01-distributed-training.md)，最常见也最致命。
5. **batch 太小**：micro-batch=1 时 kernel launch 开销占比高，MFU 上不去。在显存允许下尽量增大 micro-batch。
6. **梯度累积当并行**：gradient accumulation 不省通信（累积完还是要 AllReduce），别指望它替代 DP。

---

## 八、延伸阅读

- 并行策略选型（DP/TP/PP/ZeRO 怎么组合）：[01-distributed-training.md](01-distributed-training.md)
- 推理侧的显存与算子优化（KV Cache、FlashAttention、量化）：[04-inference-optimization.md](04-inference-optimization.md)
- 训练效率如何转化为上线效率（监控、成本治理）：[05-mlops-platform.md](05-mlops-platform.md)
