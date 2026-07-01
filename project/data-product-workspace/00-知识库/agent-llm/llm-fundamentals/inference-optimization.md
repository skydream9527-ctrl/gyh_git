# LLM 推理优化

> 推理（inference）是 LLM 产品 90% 的成本来源。一个能把单 token 成本砍 5-10 倍的工程师，比"能调出更好 prompt"的工程师对业务的杠杆更大。本文系统梳理推理优化的核心机制。

---

## 一、为什么这是 LLM 工程的最大杠杆

每天有几百万用户的 LLM 应用：

- 单次请求 5K 输入 + 1K 输出 token
- 默认 GPT-4 ≈ $0.045 / 请求
- 1 亿次请求 / 月 ≈ $4.5M
- 全栈优化（量化、cache、批处理、小模型路由）后 ≈ $0.5M

**砍 90% 是常规操作**。这一节讲清都是哪些杠杆。

---

## 二、先搞清"瓶颈在哪"

LLM 推理在 GPU 上的两阶段——理解这点决定了一切优化方向（详见 [transformer.md](transformer.md)）：

```
Prefill（处理输入 prompt）
  特性：算力密集（compute-bound）
  时间：随 prompt 长度近似线性
  决定：首字延迟（TTFT, Time To First Token）

Decode（生成 token，每次一个）
  特性：内存带宽密集（memory-bound）
  时间：随 GPU 显存带宽
  决定：吞吐量、单条延迟、TPS（Tokens Per Second）
```

**关键**：decode 是内存瓶颈不是算力瓶颈——这意味着**减少要搬的数据**（量化、KV Cache 压缩）比"加快计算"更重要。

---

## 三、核心优化技术

### 1. KV Cache（基础）

详见 [transformer.md](transformer.md) 第七节。

**为什么它是基础**：每个 decode step 不必重算前面所有 token 的 K/V，只算新生成 token 的——decode 复杂度从 O(n²) 变 O(n)。

**代价**：内存。KV Cache 占用 ≈ 2 × 层数 × 头数 × head_dim × seq_len × batch × 字节数。
- 一个 70B 模型，序列 8K，batch 16 → 几十 GB 显存
- 这就是为什么并发数受 KV Cache 内存限制

### 2. PagedAttention / vLLM

KV Cache 朴素管理是连续分配 → **碎片化严重**（大并发下浪费 60-80% 显存）。

PagedAttention 借鉴操作系统虚拟内存：把 KV Cache 切成"页"管理 → 浪费降到 5%。

**实测吞吐提升 2-4 倍**。这是为什么**vLLM 是 2023 年起开源推理引擎事实标准**。

### 3. Flash Attention

把 attention 计算用 GPU SRAM tiling 重写，避免反复读写 HBM。

- 计算等价，但内存读写量降一个数量级
- 训练 / 推理 prefill 阶段提速 2-4 倍
- 现代框架（PyTorch 2.x、HF Transformers、vLLM、TGI）默认开启

### 4. Quantization（量化）

把 FP16 / BF16 权重压成 INT8 / INT4 / FP8 等更小的精度：

| 精度 | 显存 | 速度 | 质量损失 |
|---|---|---|---|
| FP16 / BF16 | 100% | 100% | 0 |
| FP8 | 50% | 130-150% | 极小 |
| INT8 | 50% | 130-180% | 小（微调可恢复） |
| INT4 | 25% | 200-300% | 中（GPTQ / AWQ 较好） |
| INT2 | 12.5% | 400%+ | 大（开始不可用） |

**主流方案**：

- **GPTQ**：训练后量化，保精度
- **AWQ**：激活感知量化，常用 INT4
- **GGUF**（llama.cpp）：CPU / 边缘端事实标准
- **FP8**（H100+）：硬件级支持，前沿主流

**经验**：INT8 几乎免费午餐；INT4 能跑 70B 在单张 24G 卡上，但小模型 INT4 容易掉点。

### 5. 投机解码（Speculative Decoding）

一个 token-by-token 的麻烦：每生成一个 token，整个大模型都要走一遍。

**投机思路**：

```
Step 1：用一个小模型（draft model）一次性预测 4-8 个 token
Step 2：用大模型一次性"验证"这 4-8 个 token（一次 forward 就够）
Step 3：从最早分歧点起接受验证通过的 token，剩下的丢弃
```

平均加速 1.5-3 倍，**质量与原模型严格一致**（不是近似）。

变体：
- **Vanilla Speculative Decoding**（Leviathan et al., 2022）
- **Medusa**：把多个"head"加到大模型上，自己生成 draft
- **EAGLE**：基于特征空间的更精确 draft

### 6. 批处理（Batching）

GPU 在大 batch 下利用率高得多。但 LLM 推理 batch 有难点：每条请求长度不同、生成速度不同。

**Continuous Batching**（vLLM 引入）：
- 不等"整批结束"才换批
- 一条结束马上替换为新的请求
- 实测吞吐 5-10 倍提升

**这一点对在线服务尤为关键**——延迟和吞吐能同时优化。

### 7. 推测：MoE 路由

DeepSeek-V3 / GPT-4 / Mixtral 等 MoE 模型有大量"未激活参数"。
- 总参 671B，每 token 激活 37B
- 推理成本接近 37B dense，但能力≈ 671B
- 这是从架构层降低成本的路径

---

## 四、Prompt Caching（**API 用户必懂**）

OpenAI、Anthropic 都已支持的功能：

```
你的 prompt = [固定前缀 system 5K token] + [用户输入 200 token]

普通请求：每次都重算 5K token 的 K/V
prompt cache：第一次算完缓存住，之后请求只算新 token
```

**价格差异**：

- Anthropic：cache write ≈ 1.25× 原价；cache read ≈ 0.1× 原价
- OpenAI：cache hit 输入 token 50% 折扣

**实战收益**：

- Coding Agent、客服 Agent 等系统提示长 → cache 后输入费降 90%
- 文档问答把全文档 cache 住 → 多轮问询不重算

**触发条件**：

- 前缀必须**完全一致**到 token 级
- 长度有最低门槛（Anthropic 1024 token，OpenAI 1024 token）
- 缓存 TTL：Anthropic 5 分钟（默认），1 小时（可选）；OpenAI ~5-10 分钟

→ **设计 prompt 时把所有"稳定内容放最前"，"易变内容放最后"**。这一个设计习惯能省一个数量级费用。

---

## 五、自部署 vs API：决策维度

| 维度 | API | 自部署 |
|---|---|---|
| 单 token 成本 | 高 | 低（量上来后） |
| 启动成本 | 0 | 几人月 + GPU 投入 |
| 模型可选 | 有限（厂商提供的） | 任意开源 |
| 数据合规 | 厂商策略 | 完全自主 |
| Prompt cache | 厂商决定 | 自己实现 |
| 延迟 | 网络 + 厂商负载 | 本地可控 |
| 维护 | 0 | 持续 |

**实操建议**：

- 月调用 < 100 万次：API 几乎一定胜出
- 100 万 - 1 亿：分场景。低延迟 / 数据敏感场景考虑自部署
- > 1 亿次：**自部署 + API fallback** 是常见组合

---

## 六、自部署常用引擎

| 引擎 | 长处 | 适合场景 |
|---|---|---|
| **vLLM** | 综合最好，PagedAttention | 生产首选 |
| **TGI**（HF） | 与 HF 生态融合 | HF 工作流深度集成 |
| **SGLang** | 结构化输出强 | JSON / 多轮 / 工具调用密集 |
| **TensorRT-LLM**（NVIDIA） | 推理速度最快 | 极致性能优先 |
| **llama.cpp** | CPU / 边缘 / Mac | 本地推理、隐私敏感 |
| **MLC-LLM** | 跨平台编译（手机、Web） | 端侧部署 |

---

## 七、典型成本优化路径

按从易到难、收益从大到小：

```
1. 选对模型
   - 简单任务用小模型（Haiku、GPT-4o-mini、Qwen-Turbo）
   - 复杂任务才上大模型
   - 收益：5-20×

2. Prompt Cache
   - 把系统提示、长上下文 cache 住
   - 收益：3-10×

3. 路由 / 分级
   - 简单查询小模型回答 + 复杂的升级到大模型
   - 收益：2-5×

4. 量化部署
   - 自部署后 INT4 / FP8 量化
   - 收益：2-4×

5. Speculative Decoding
   - 自部署后开投机解码
   - 收益：1.5-3×

6. Batching 优化
   - vLLM 的 continuous batching
   - 收益：3-5×

7. 蒸馏 / SFT 小模型
   - 关键流量用 SFT 后的小模型
   - 收益：5-50×（视任务而定）
```

---

## 八、几个工程坑

### 1. 用很长的 system prompt 又不开 cache
不开 cache 的长 system 是钱包刺客。每次请求都在为同样的内容付费。

### 2. 不限 max_tokens
LLM 在不该结束时不会结束 → 单条请求耗 4K-8K token，成本飞涨。
**必设 max_tokens**，并配上"截断后总结"逻辑。

### 3. Streaming 但前端没用上
Streaming 用于改善 TTFT 体验，但有些客户端等全部生成完才显示——白白增加延迟。

### 4. KV Cache 内存爆炸没监控
线上 OOM 经常因为某条请求超长。Token 长度上限要硬截断。

### 5. 量化后没回测
INT4 量化在某些任务上掉 5-10 个点，必须做完整 eval 再上线。

---

## 九、Checklist

```
□ 1. 我用的模型是当前任务的"性价比最优"，还是默认 GPT-4？
□ 2. system / 长 context 是否启用了 prompt cache？
□ 3. 简单 vs 复杂请求是否做了路由分级？
□ 4. 是否设置了 max_tokens 上限？
□ 5. 自部署的话用什么引擎？开了 PagedAttention / Speculative Decoding 吗？
□ 6. 量化后做过完整 eval 吗？
□ 7. 监控里有 token 用量、p50/p99 延迟、cache 命中率吗？
□ 8. 一年后 token 量增长 10× 的话，方案够撑吗？
```

---

## 十、扩展阅读

- 本目录：[transformer.md](transformer.md)、[scaling-law.md](scaling-law.md)
- Kwon et al. (2023) — *Efficient Memory Management for Large Language Model Serving with PagedAttention*（vLLM 论文）
- Dao et al. (2022) — *FlashAttention: Fast and Memory-Efficient Exact Attention*
- Leviathan et al. (2022) — *Fast Inference from Transformers via Speculative Decoding*
- Frantar et al. (2022) — *GPTQ: Accurate Post-Training Quantization*
- Anthropic Prompt Caching docs
- OpenAI Prompt Caching docs
- Lilian Weng — *Large Transformer Model Inference Optimization*
