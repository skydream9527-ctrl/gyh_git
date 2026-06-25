# 分布式训练与并行策略

> 大模型训练不是"把单卡脚本改成多卡"那么简单——它是把一个装不进单卡的问题，拆成"算得动、通信得起、收敛得了"三件事的工程艺术。一个 70B 模型从 8 卡跑到 1024 卡，线性加速比能做到 0.7-0.8 已经是世界级水平。本文从"为什么要并行"讲起，到三大并行范式、ZeRO、3D 并行实战配置，再到选型决策表。

---

## 一、为什么单卡训不动大模型

先算一笔账，训练一个 70B 模型（Adam 优化器、BF16、激活不重计算）：

```
模型参数：       70B × 2 bytes (BF16)        = 140 GB
梯度：           70B × 2 bytes (BF16)        = 140 GB
优化器状态：     70B × 8 bytes (FP32 m,v)    = 560 GB
                                  ─────────────────
权重相关显存合计                            ≈ 840 GB

激活（seq=2048, batch=1, 80层）             ≈ 80-160 GB
                                  ─────────────────
单步所需显存                                ≈ 1 TB
```

单张 H100 80GB / A100 80GB **根本装不下**。这就是分布式训练要解决的第一个问题：**装不下 → 切开**。

但切开只是开始，真正的难点是切完之后：

| 问题 | 含义 | 衡量指标 |
|---|---|---|
| 装得下 | 把张量/层/数据分散到多卡 | 单卡显存占用 |
| 算得动 | 切开后计算量不浪费、不空等 | MFU（Model FLOPs Utilization） |
| 通信得起 | 卡间同步开销不吞掉计算收益 | 通信占比 < 30% |
| 收敛得了 | 并行不破坏梯度/数值正确性 | loss 曲线、grad norm |

**记一条铁律**：并行策略的本质是"用通信换显存"——你省下的每一 GB 显存，都要用一次 AllReduce/AllGather/ReduceScatter 来还。好的策略是"还得起"的策略。

---

## 二、三大并行范式

### 1. 数据并行（Data Parallelism, DP）

最朴素：每张卡拿一份完整模型 + 一份不同数据，各算各的梯度，再 AllReduce 平均。

```
GPU0: 完整模型 + batch[0:4]  ─┐
GPU1: 完整模型 + batch[4:8]  ─┼─→ 各自前向+反向 → AllReduce 梯度 → 同步更新
GPU2: 完整模型 + batch[8:12] ─┤
GPU3: 完整模型 + batch[12:16]┘
```

- **优点**：实现简单，几乎不改模型代码
- **致命缺点**：每张卡都存完整模型+优化器状态 → 70B 模型单卡仍要 840GB，**装不下就是装不下**
- **通信**：每步一次 AllReduce，通信量 ∝ 参数量，与 batch 无关

**结论**：纯 DP 只适合"模型装得下单卡"的场景。大模型必须把模型本身也切开 → 模型并行。

### 2. 模型并行（Model Parallelism, MP）

把模型本身切开。有两种切法，方向完全不同。

#### 2a. 张量并行（Tensor Parallelism, TP）

**切法**：把每一层的权重矩阵按列/行切到多卡，每卡算一部分，再用通信拼起来。

以线性层 `Y = XW` 为例，把 `W` 按列切到 N 卡：

```
W = [W_1 | W_2 | ... | W_N]   (列切)

GPU_i 计算: Y_i = X · W_i      (各卡独立算一部分)
然后 AllGather:  Y = [Y_1 | Y_2 | ... | Y_N]
```

- **粒度**：层内切，每层都要通信（前向 AllGather / 反向 ReduceScatter）
- **通信频率**：极高，每层 2 次集合通信
- **关键约束**：通信太频繁，**只在机内（NVLink/NVSwitch 域内）做 TP**，跨机做 TP 会被网络拖死
- **典型规模**：TP=2/4/8（对应单机 2/4/8 卡）

#### 2b. 流水线并行（Pipeline Parallelism, PP）

**切法**：把模型按层切成 N 段，每段放一张卡，数据像流水线一样流过去。

```
GPU0: Layer[0:20]   →  GPU1: Layer[20:40]   →  GPU2: Layer[40:60]   →  GPU3: Layer[60:80]
       (stage 0)            (stage 1)              (stage 2)              (stage 3)
```

- **粒度**：层间切，只在 stage 边界通信（传激活）
- **通信频率**：低，每个 micro-batch 边界一次点对点通信
- **致命问题：气泡（bubble）**。朴素流水线下，stage 0 算完才能给 stage 1，stage 1 算时 stage 0 空闲：

```
朴素流水线（4 stage, 4 micro-batch）:
GPU0: [M0][M1][M2][M3]............[M0'][M1'][M2'][M3']   ← 中间一大段空闲 = 气泡
GPU1: ....[M0][M1][M2][M3]............[M0'][M1'][M2'][M3']
GPU2: ........[M0][M1][M2][M3]............[M0'][M1'][M2'][M3']
GPU3: ............[M0][M1][M2][M3]............[M0'][M1'][M2'][M3']
```

气泡占比 ≈ `(stage-1) / (stage-1 + micro_batch)`。**解法是 micro-batch 流水线调度**：

| 调度方式 | 代表 | 气泡 | 说明 |
|---|---|---|---|
| 朴素（GPipe） | - | 大 | 前向全做完再反向 |
| 1F1B | Megatron | 中 | 前向反向交错，省激活内存 |
| Interleaved 1F1B | Megatron-LM | 小 | 每个 stage 切多个虚拟 stage，气泡更小 |

**结论**：PP 适合跨机（通信少），但必须配合 micro-batch 调度压气泡，且 stage 数要和 micro-batch 数匹配（一般 micro-batch ≥ 4×stage）。

### 3. 三种并行对比

| 维度 | 数据并行 DP | 张量并行 TP | 流水线并行 PP |
|---|---|---|---|
| 切什么 | 数据 | 层内权重 | 层间分组 |
| 通信频率 | 每步 1 次 | 每层 2 次 | 每 micro-batch 边界 |
| 通信量 | ∝ 参数量 | ∝ 激活×batch | ∝ 激活×batch |
| 适合网络 | 跨机 IB | 机内 NVLink | 跨机 IB |
| 典型规模 | 几十~几千卡 | 2/4/8 | 4~16 stage |
| 改模型代码 | 几乎不用 | 要 | 要 |

---

## 三、ZeRO：让数据并行也能装下大模型

ZeRO（Zero Redundancy Optimizer）的核心洞察：**纯 DP 里每张卡都存了完整的优化器状态+梯度+参数，这是巨大的冗余**。把这些也切到不同卡上，需要时再通信拼回来。

ZeRO 三个阶段，逐级切更多东西：

```
                优化器状态    梯度        参数
                (FP32 m,v)   (BF16)     (BF16)
─────────────────────────────────────────────────
原始 DP         每卡全量      每卡全量    每卡全量     ← 70B 单卡 840GB
ZeRO-1         切分 N 份     每卡全量    每卡全量     ← 省优化器，约 1/N
ZeRO-2         切分 N 份     切分 N 份   每卡全量     ← 再省梯度
ZeRO-3         切分 N 份     切分 N 份   切分 N 份    ← 全切，单卡显存 ≈ 1/N
```

**显存收益**（70B，N=64 卡）：

| 方案 | 单卡显存（权重相关） | 代价 |
|---|---|---|
| 原始 DP | 840 GB（装不下） | - |
| ZeRO-1 | ~9 GB + 参数140GB ≈ 149GB | 多一次优化器 AllReduce |
| ZeRO-2 | ~9 GB + 参数140GB ≈ 149GB | 梯度 ReduceScatter |
| ZeRO-3 | ~13 GB（全切） | 前向/反向都要 AllGather 参数，**通信量大增** |

**关键权衡**：

- ZeRO-1/2：通信开销和 DP 差不多，**几乎免费**，应默认开启
- ZeRO-3：省显存但通信暴涨，**用通信换显存**。适合"卡多但单卡小"的场景
- ZeRO-3 的通信量与 TP 类似，但 TP 是机内低延迟，ZeRO-3 常跨机 → **同规模下 TP 通常比 ZeRO-3 快**

> **实战经验**：ZeRO-3 不是"更好的 DP"，而是"装不下时的兜底"。如果你能 TP+PP 装下，优先 TP+PP，性能更好。ZeRO-3 适合中等模型 + 多机小卡的场景（如 7B/13B 在 4090 集群上）。

### ZeRO-Offload / ZeRO-Infinity

进一步把优化器状态甚至参数 offload 到 CPU 内存 / NVMe：

- **ZeRO-Offload**：优化器状态放 CPU，CPU 算优化器更新（用 CPU 大内存换 GPU 显存）
- **ZeRO-Infinity**：参数也能在 GPU/CPU/NVMe 三级间按需换页

代价：CPU 算力远弱于 GPU，PCIe 带宽远低于 NVLink → **训练速度大幅下降**。只在"显存实在不够又买不起卡"时用，生产训练基本不用。

---

## 四、3D 并行：TP × PP × DP 的实战组合

真正训百亿/千亿模型，是三种并行叠加：

```
                    ┌─────────────────────────────────────┐
   数据并行 DP       │  DP group 0      DP group 1   ...   │   ← 跨机，IB 网络
   (外层，跨机)      │  ┌───────────┐  ┌───────────┐       │
                    │  │ PP stage0 │  │ PP stage0 │       │
                    │  │ PP stage1 │  │ PP stage1 │       │   ← 流水线，跨机
                    │  │ PP stage2 │  │ PP stage2 │       │
                    │  │ [TP=4]    │  │ [TP=4]    │       │   ← 张量并行，机内 NVLink
                    │  └───────────┘  └───────────┘       │
                    └─────────────────────────────────────┘
```

**配置原则**（Megatron-LM / DeepSpeed 经验）：

1. **TP 放机内**：TP=单机 GPU 数（如 8），吃 NVLink 带宽
2. **PP 放跨机**：PP=stage 数，吃 IB 带宽但通信稀疏
3. **DP 填满剩余**：DP = 总卡数 / (TP × PP)，最外层

**举例**：1024 卡训 175B，单机 8 卡：
- TP = 8（机内）
- PP = 16（跨 16 个机组的 stage）
- DP = 1024 / (8×16) = 8

**全局 batch** = DP × micro_batch × accumulation_steps，要调到收敛稳定且通信占比合理（一般 global batch 在 1K-4K token 级别）。

---

## 五、缓存命中率：训练效率的隐形杠杆

### 1. 什么是缓存命中率

**缓存命中率（Cache Hit Rate）= 命中缓存的访问次数 / 总访问次数**。

计算机体系结构的核心思想是"存储分层"：越快的层越小越贵。把热点数据放在快层，慢层只处理冷数据 → 整体平均访问延迟接近快层。

```
快 ←──────────────────────────────────────────────────→ 慢
GPU 寄存器 → SRAM(共享内存/L1) → L2 → HBM(显存) → NVLink → IB → DRAM → SSD
~1 cycle     ~20 cycle        ~200 cycle  ~500 cycle   ...
```

每次访问落在快层叫 **hit**，落到慢层叫 **miss**。命中率越高，平均延迟越低、带宽利用率越高。

**为什么分布式训练必须关心**：训练的有效算力（MFU）很大程度由缓存命中率决定。一个 kernel 如果反复从 HBM 读同一份数据、SRAM 命中率为 0 → 带宽成瓶颈 → 算力闲置。算子融合和 FlashAttention 的本质就是**把中间量留在 SRAM，把命中率从 ~0 拉到接近 100%**（详见 [02-training-optimization.md](02-training-optimization.md)）。

> 记一条：分布式训练里"并行策略"解决怎么切，"缓存命中率"解决切完之后每一层存储有没有被榨干。两者叠加才决定 MFU 是 35% 还是 55%。

### 2. 训练中影响命中率的关键缓存层

| 缓存层 | 存什么 | 命中高的收益 | 典型 miss 原因 |
|---|---|---|---|
| GPU SRAM / L1 | kernel tiling 块、融合中间量 | kernel 提速 2-4× | 算子没融合、tile 太大装不下 |
| GPU L2 | 跨 kernel 复用的权重/数据 | 多 kernel 间复用 | 访问模式不规律、被驱逐 |
| HBM（显存） | 权重、激活、优化器状态 | 避免重算 | 容量不够被换出 / 被 recompute |
| Host DRAM | dataloader 预取、tokenized data | 数据不阻塞 GPU | worker 太少、没 prefetch |
| Page cache | 训练数据 shard | 免读磁盘 | 数据量超内存、随机读 |
| 通信 buffer | 梯度 bucket、prefetch 参数 | 通信计算 overlap | 没开异步、buffer 太碎 |

### 3. 如何提高缓存命中率

#### a) Kernel 层：算子融合 + tiling

- **算子融合**：多个算子合成一个 kernel，中间量留在 SRAM 不写回 HBM → SRAM 命中率拉满（详见 [02-training-optimization.md](02-training-optimization.md) 第四节）
- **Tiling**：把大矩阵切成 SRAM 装得下的块，分块计算 → 每块在 SRAM 内被反复复用
- **FlashAttention**：极致的融合 + tiling，attention 中间矩阵 S 全程不写回 HBM，SRAM 命中率从 ~0 拉到接近 100%

#### b) 数据加载层：prefetch + 缓存预处理结果

- **`num_workers` 调大**：多进程并行预取，下一个 batch 在 GPU 算当前 batch 时就准备好
- **`prefetch_factor`**：每个 worker 预取多份，平滑 IO 抖动
- **`pin_memory=True`**：锁页内存，CPU→GPU 传输可异步，避免 dataloader 阻塞 GPU
- **缓存 tokenized data**：原始文本→token 反复做是浪费，tokenize 一次存到内存/SSD，后续直接读
- **数据本地性**：分布式训练时数据 shard 就近放（同机/同机架），避免跨网络读

#### c) 激活层：selective recompute 平衡

激活重计算的本质是**主动降低 HBM 激活缓存命中率**（不存、重算）来换显存。但全重算太费算力，selective recompute 只对"激活大、FLOPs 小"的 attention 部分重算，保留 FFN 激活在 HBM 命中 → 整体性价比最高。

#### d) 通信层：bucket + overlap

- **梯度 bucketing**：把多个小梯度合并成大 buffer 一次通信，提高网络带宽利用率（类似提高"通信缓存"命中率）
- **通信计算 overlap**：反向算完一层就异步通信，通信 buffer 持续命中 → 通信时间藏到计算后面
- **ZeRO prefetch**：ZeRO-3 在算当前层时 prefetch 下一层参数到 HBM，避免算到时再从远端取

#### e) 文件系统层

- **训练数据放内存盘 / SSD**：避免机械盘 IO 瓶颈
- **shard 大小合适**：太小频繁 open，太大 page cache 装不下
- **顺序读取**：顺序 IO 命中 page cache + 预读，比随机读快 10×

### 4. 怎么判断缓存是不是瓶颈

| 现象 | 可能是哪层缓存 miss |
|---|---|
| MFU 低、GPU 利用率低但算力够 | 数据加载层（dataloader 阻塞） |
| kernel 速度远低于理论带宽 | SRAM/L2 miss（没融合 / tiling 差） |
| 多机扩展性差 | 通信 buffer / 拓扑 miss |
| 长序列训练显存够但慢 | 激活反复重算（HBM miss 太多） |
| 首个 epoch 慢、后续快 | page cache 冷启动（正常现象） |

**排查工具**：NVIDIA Nsight Compute / Nsight Systems（kernel 级 cache 命中率）、PyTorch Profiler（dataloader / 通信占比）。

---

## 六、选型决策表

| 你的场景 | 推荐方案 | 理由 |
|---|---|---|
| 7B 模型，单机 8×A100 | ZeRO-2 或 TP=2 | 装得下，ZeRO-2 几乎免费 |
| 13B 模型，单机 8×A100 80G | ZeRO-3 或 TP=2+DP | 单卡勉强装不下权重+优化器 |
| 70B 模型，多机 A100/H100 | TP=8 × PP=4+ × DP | 必须 3D 并行 |
| 175B+ 模型，千卡集群 | TP=8 × PP=16+ × DP | 3D 并行 + Interleaved 1F1B |
| 模型装得下单卡，只想加速 | 纯 DP / ZeRO-1 | 通信最少，最简单 |
| 显存不够又买不起卡 | ZeRO-3 / ZeRO-Offload | 用通信/速度换显存 |

---

## 七、常见踩坑

1. **TP 跨机**：把 TP=8 设成跨两台机器 → AllReduce 走 IB，每层通信延迟翻几倍，MFU 直接腰斩。TP 永远只在 NVLink 域内。
2. **PP stage 数和 micro-batch 不匹配**：micro-batch < stage 数 → 气泡占比极高。经验值 micro-batch ≥ 4×stage。
3. **global batch 太小**：DP=2 时 global batch 太小，梯度噪声大、收敛慢。要么加 gradient accumulation，要么减少 PP/TP 增加 DP。
4. **忘了开 ZeRO-1/2**：很多框架默认不开，但 ZeRO-1/2 几乎零成本省显存，应默认开。
5. **通信和计算没 overlap**：好的实现会把通信和下一层的计算重叠（如 PP 的通信和计算流水）。没 overlap → 通信时间纯空等。

---

## 八、延伸阅读

- 推理侧的并行与显存管理：[03-inference-serving.md](03-inference-serving.md)
- 训练显存与通信细节（混合精度、激活重计算、集合通信）：[02-training-optimization.md](02-training-optimization.md)
- 训练完如何上线、监控、灰度：[05-mlops-platform.md](05-mlops-platform.md)
- 经典论文：Megatron-LM（TP+PP）、DeepSpeed ZeRO（3 阶段）、PipeDream（1F1B 调度）
