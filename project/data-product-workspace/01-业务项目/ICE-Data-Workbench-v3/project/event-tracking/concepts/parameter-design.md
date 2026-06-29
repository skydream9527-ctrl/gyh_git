# 参数设计

> 事件回答"发生了什么"，**参数回答"在什么情境下、对什么对象、由谁、怎么发生的"**。一个事件好不好用 90% 取决于参数设计。本文给出参数分层模型、命名规范、类型系统、和内容产品里的关键参数清单。

---

## 一、为什么参数设计比事件设计更难

事件名设计错了，至少容易**发现**——事件名一目了然。

参数设计错了，**几个月后才暴露**：
- 想做用户路径分析时发现"少了 source"
- 想算"老用户活跃"时发现"没存 days_since_install"
- 想做归因时发现"没传 channel"
- 想看推荐质量时发现"没传 strategy_id"

**埋点价值的 90% 来自参数，不是事件**。

行业里有句话：

> "事件是骨架，参数是肉。一个产品的可分析性由参数密度决定。"

---

## 二、最小心智模型：三层参数

不要把所有参数平铺。**任何成熟埋点系统都有三层参数**：

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   1. Super Properties（超级 / 公共参数）                     │
│      每个事件都自动带 — SDK 层注入                          │
│      例：user_id, device_id, session_id, app_version        │
│                                                             │
│   2. Event Common Properties（事件公共参数）                 │
│      属于某类事件的共享参数 — 业务层规范                    │
│      例：feed_id, position, page_name, source              │
│                                                             │
│   3. Event-Specific Properties（事件特有参数）              │
│      只此事件有的字段 — 单事件设计                          │
│      例：video_play 的 play_duration、quality              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**职责分离**：

- 第 1 层由 SDK 自动维护（产品同学不需要管）
- 第 2 层是埋点规范的核心（产品 + 数据 + 工程共建）
- 第 3 层每个事件自己定义

---

## 三、Super Properties 标准清单（**必有**）

每个事件都要带的参数。SDK 层自动注入：

### 1. 用户身份
```
user_id           （登录用户 ID）
anonymous_id      （未登录的设备级 ID）
device_id         （设备唯一标识）
distinct_id       （Mixpanel/Amplitude 风格的统一 ID）
```

### 2. 会话
```
session_id        （会话 ID，30 分钟无活动重置）
session_start_at  （会话开始时间）
```

### 3. 时间
```
event_time        （事件发生的客户端时间，毫秒）
server_time       （服务端接收时间，由服务端写入）
timezone          （客户端时区）
```

### 4. 应用 / 端
```
app_id            （多 app 时区分）
app_version       （客户端版本）
build_number      
platform          （ios / android / web / desktop / tv）
sdk_version       
```

### 5. 设备
```
device_brand      
device_model      
os_name           
os_version        
screen_width      
screen_height     
language          
country           
```

### 6. 网络
```
network_type      （wifi / 4g / 5g / unknown）
carrier           
ip                （服务端记录，注意隐私）
```

### 7. 投放归因（首次触达类）
```
install_channel   （安装渠道，仅首次安装时记录）
install_campaign  
referrer          
utm_source / utm_medium / utm_campaign  （Web 时）
```

> **总数控制在 20-30 个**。再多就过度——每个事件都要带这一坨开销可观（数据量、传输、存储）。

---

## 四、Event Common Properties（事件公共参数）

属于某**类**事件的共享参数。规划时按业务对象分组：

### 内容相关（任何内容类事件都该带）
```
content_id        （视频 / 文章 / 商品 / 直播间的唯一 ID）
content_type      （video / article / live / podcast）
content_author    
content_publish_at  
content_duration  （视频 / 音频时长，秒）
content_tag       （标签数组）
```

### 位置 / 上下文
```
page              （当前页面：home / profile / search / detail）
section           （子区域：feed / sidebar / recommend）
position          （在列表中的位置：0-based index）
column            （多列布局时的列号）
```

### 推荐 / 分发
```
source            （exposure 来源：recommend / follow / hot / search）
recommend_strategy_id    （推荐策略 ID）
recommend_request_id     （召回请求 ID，用于推荐反馈）
recommend_score          （推荐分）
recommend_reason         （推荐理由：友邻在看 / 类似内容 / ...）
```

### 实验 / AB
```
experiment_id     （进入哪个实验）
variant_id        （是哪个变体：control / treatment）
```

> **公共参数应该有专门的"参数字典"维护**——和事件命名规范同等重要。

---

## 五、命名规范

参数名命名规范和事件命名一脉相承（详见 [event-naming.md](event-naming.md)）：

### 1. snake_case
```
✅ video_play_duration
✅ recommend_strategy_id
❌ videoPlayDuration
❌ video-play-duration
```

### 2. 命名要"全栈可识别"
```
❌ id              （什么的 id？）
✅ user_id        
✅ video_id       
✅ comment_id     

❌ name           （谁的名字？）
✅ user_name      
✅ video_title    
```

### 3. 单位写进名字（**关键**）
```
❌ duration              （秒？毫秒？分钟？）
✅ duration_ms          
✅ duration_seconds     
✅ size_kb              
✅ price_cents          
```

**这是 1 分钟的工作能省 1 年的混乱**。你将来 query 时能看到名字就知道单位。

### 4. 布尔类用 `is_` 或 `has_`
```
✅ is_paid_user
✅ is_first_visit
✅ has_subscribed
❌ paid          （0/1 还是 'yes'/'no'？）
```

### 5. 时间用 `_at` 后缀
```
✅ created_at
✅ published_at
✅ install_at
❌ time         
❌ date         
```

---

## 六、参数类型系统

每个参数明确类型，**绝不混用**：

| 类型 | 示例 | 注意 |
|---|---|---|
| `string` | `user_id`, `country` | 长度限制（避免无限长） |
| `int` | `position`, `duration_ms` | 注意 32-bit vs 64-bit |
| `float` | `score`, `latitude` | 精度问题 |
| `boolean` | `is_paid_user` | 严格 `true/false`，不要 `1/0` |
| `enum` | `platform`, `network_type` | 必须有 enum 值清单 |
| `array` | `tags`, `permissions` | 元素类型一致 |
| `object` | `metadata` | 嵌套结构，慎用 |
| `timestamp` | `event_time` | 用毫秒整数，不用字符串 |

**类型混乱的代价**：

```
某团队 user_id 一会儿是字符串 "123"，一会儿是整数 123
→ JOIN 时类型不匹配，要不断 CAST
→ 最终发现 5% 的数据 JOIN 不上，那 5% 永远不进分析
```

---

## 七、Enum 参数特别处理

任何"只能取几个值"的字段都用 enum + **明确的取值清单**：

```python
PLATFORM_ENUM = {'ios', 'android', 'web', 'desktop', 'tv', 'wechat_mp', 'h5'}
NETWORK_ENUM = {'wifi', '4g', '5g', '3g', '2g', 'ethernet', 'unknown'}
SOURCE_ENUM = {'recommend', 'follow', 'hot', 'search', 'related', 'push',
               'deeplink', 'share_link', 'profile', 'history'}
```

**严格执行**：

- 校验上报时是 enum 内的值
- 新增 enum 值需要走 review
- 旧值 deprecate 要走流程

> **没有 enum 约束的"枚举"很快变成 100 种自由文本**——查询时再也分不清。

---

## 八、内容产品的关键参数（分场景）

### 视频播放类
```
video_id, video_duration_seconds
play_strategy        （auto_play / manual / continuous）
play_duration_ms     （本次播放时长）
play_progress        （0.0-1.0，最终进度）
play_speed           （0.5 / 1.0 / 1.5 / 2.0）
quality              （360p / 720p / 1080p / 4k）
buffer_count         （缓冲次数）
buffer_total_ms      （缓冲总时长）
network_type         
is_completed         
```

### 信息流卡片
```
feed_id, position
content_type, content_id, content_author
strategy_id, recommend_score, recommend_reason
exposure_duration_ms     （在屏幕上停留多久）
visibility_ratio         （最大可见比例 0-1）
```

### 互动行为
```
content_id, content_type
interaction_type     （like / favorite / share / comment / follow）
target_user_id       （关注 / 互动针对的用户）
share_to             （wechat / weibo / link / qq / save）
comment_text_length  （评论字数；不要存全文，隐私）
```

### 推荐反馈（**最重要**）
```
recommend_request_id    （和召回请求关联）
strategy_id, model_id, model_version
content_id
feedback_type           （positive_implicit / negative_implicit / 
                         positive_explicit / negative_explicit）
feedback_signal         （complete / dwell_long / quick_swipe / 
                         like / share / not_interested / report）
exposure_duration_ms    （细化反馈强度）
```

---

## 九、参数设计反模式（**别犯**）

### ❌ 1. 一个字段塞多种东西
```
❌ data = "video_id=123;duration=45;quality=720p"
✅ video_id=123, duration_seconds=45, quality="720p"
```

### ❌ 2. 把日志细节当参数
```
❌ stack_trace, log_lines
→ 这些进 logging 系统，不进埋点
```

### ❌ 3. 上传 PII（隐私）
```
❌ phone_number, id_card, email, password
→ 隐私违规，永远不要进埋点
```

### ❌ 4. 上传巨大对象
```
❌ full_user_profile = {...50 个字段...}
→ 数据量、传输、存储都会爆炸
→ 只传你**真正会查询**的字段
```

### ❌ 5. 实时计算的字段
```
❌ days_since_install     （客户端算，时区错就错）
→ 上传 install_at，让数仓侧算
```

### ❌ 6. 把状态机当字段
```
❌ user_state = "active_3_days_then_paid_then_churned"
→ 上传原始事件，让数仓重建状态
```

### ❌ 7. 不同事件同名参数语义不一致
```
事件 A: position 是列表索引（0-based int）
事件 B: position 是地理位置（"top" / "bottom" / "center"）
→ 同名不同义是噩梦
```

---

## 十、参数字典文档应该长什么样

每个参数维护一份字段表，至少包含：

```yaml
- name: video_play_duration_ms
  type: int
  unit: 毫秒
  description: 本次连续播放时长（不含暂停 / 缓冲）
  required: true
  applies_to: [video_play_complete, video_play_pause]
  added_at: 2024-01-15
  owner: video-team
  notes: |
    含拖动后的时长。如有疑问见 RFC-2024-15。
    超过 1h 的极端值在数仓侧 winsorize。

- name: source
  type: enum
  values: [recommend, follow, hot, search, related, push, ...]
  description: 流量来源
  required: true
  applies_to: [feed_card_impression, video_play, ...]
  added_at: 2023-08-01
  owner: data-team
```

**这是埋点资产的一部分，应该跟代码一起 review、一起迭代**。

---

## 十一、Checklist

```
□ 1. Super properties 由 SDK 自动注入，PM 不需要每次定义？
□ 2. 公共参数和事件参数严格分层？
□ 3. 命名遵循 snake_case + 单位后缀（_ms, _seconds, _kb）？
□ 4. 布尔参数用 is_ / has_ 前缀？
□ 5. 时间参数用 _at 后缀 + 毫秒整数？
□ 6. 所有 enum 参数有明确的取值清单？
□ 7. 同名参数在不同事件里语义一致？
□ 8. 推荐反馈类参数齐全（strategy_id, recommend_request_id, feedback_type）？
□ 9. 没有上传 PII（手机 / 身份证 / 邮箱）？
□ 10. 有没有维护"参数字典"文档？
```

---

## 十二、扩展阅读

- 本目录：[event-naming.md](event-naming.md) — 事件命名（参数命名的基础）
- 本目录：[event-taxonomy.md](event-taxonomy.md) — 分类法
- 内容事件：[../content-events/core-content-events.md](../content-events/core-content-events.md)
- **Snowplow Tracker Protocol** — 最严格的 schema 标准
- **Segment Spec** — Common, Identify, Track 的参数模型
- **Amplitude Taxonomy Playbook** — 实战参数设计
- 内部数据契约工具：Iteratively、Avo、Snowtype
- 隐私 / 合规：GDPR、个保法相关的 PII 字段处理
