# 内容产品的核心事件

> 本文聚焦内容产品（短视频 / 信息流 / 阅读 / 直播 / 播客）**最核心、最容易埋错、对推荐 / 推荐反馈 / AB 实验影响最大**的事件：曝光、播放、互动、推荐反馈。给出每类事件的标准 schema、可见性判定、心跳设计、信号极性等关键工程细节。

---

## 一、为什么这一篇是"核心"

内容产品的埋点海量（动辄 500+），但**真正决定决策质量的就那几类**：

| 事件类 | 影响范围 |
|---|---|
| **曝光（Impression）** | DAU、CTR、推荐池入口 |
| **播放（Playback）** | 时长、完播、推荐主信号 |
| **互动（Interaction）** | 留存、推荐反馈、社交关系 |
| **推荐反馈（Feedback）** | 模型训练数据，整个推荐效果天花板 |

埋错任意一个，都会影响整个产品的"反馈神经系统"。本文按这四类逐一讲清。

---

## 二、曝光（Impression）：被严重低估的事件

### 2.1 "曝光"为什么难

最简单也最容易错的埋点。"曝光"看似一目了然，但实操有 5 种不同含义：

```
1. DOM 渲染（render）         元素被生成到 DOM 树
2. 进入视口（in_viewport）    元素在屏幕可视区域
3. 部分可见（visible）        元素 ≥ X% 可见
4. 持续可见（dwell）          元素持续可见 ≥ T 秒
5. 用户感知（perceived）      用户实际"看到了"
```

**5 种粒度对应不同业务含义**：

- 推荐曝光池：通常用 (3) 部分可见 + 阈值 50%
- CTR 计算：通常用 (4) 持续可见 ≥ 1 秒
- 广告计费：业内标准 50% 可见 ≥ 1 秒（IAB Viewable）
- 内容反馈池：通常用 (4) + dwell 时长

> **没有明确"曝光"的口径，所有上层指标都是浮沙**。

### 2.2 推荐的标准曝光口径

```
有效曝光（valid_impression）：
  - 元素至少 50% 在视口内（visibility_ratio ≥ 0.5）
  - 持续 ≥ 1000ms
  - 用户没有快速滑过（不是连续滑动中扫过）

埋点：
  feed_card_impression
  参数：
    visibility_ratio_max     最大可见比例
    dwell_time_ms            停留毫秒
    is_valid_impression      是否满足有效曝光阈值
```

### 2.3 标准事件设计

```yaml
- event: feed_card_impression
  trigger: 卡片满足曝光条件时
  required_params:
    - card_id
    - content_id
    - content_type
    - position                 # 列表中位置
    - visibility_ratio_max     # 最大可见比例 0-1
    - dwell_time_ms            # 在视口内停留毫秒
    - is_valid_impression      # 是否满足有效曝光阈值
    - source                   # recommend / follow / hot / search
    - recommend_request_id     # 与推荐请求关联
    - strategy_id              # 推荐策略
    - page                     # 当前页
  optional_params:
    - exposure_session_id      # 同一连续曝光的 session
```

### 2.4 高频踩坑

#### 1. 不区分 render 和 impression
```
❌ 卡片刚渲染就上报 impression
→ 用户没看到也算曝光
→ CTR 被稀释
```

#### 2. 没有去重
```
❌ 用户上下滑动，同一卡片反复进入视口，每次都报
→ 一次会话同一卡片报了 5 次曝光
✅ 同一会话内同一卡片只报一次有效曝光
```

#### 3. 没有 dwell 时长
```
❌ 只判断"可见过"
→ 一秒内滑过 50 个卡片全是"曝光"
→ 推荐反馈被噪音淹没
```

#### 4. 客户端时间戳不可信
```
❌ 用 client_time 做曝光时序
→ 客户端时间不准会乱
✅ 服务端按 server_time 排序
```

#### 5. 列表位置 (position) 错
```
❌ 删除卡片后未更新 position
→ 同一物理位置上多个卡片用同一个 position
✅ position 是渲染时的当前位置
```

---

## 三、点击（Click / Tap）

### 3.1 标准事件

```yaml
- event: feed_card_click
  trigger: 用户点击卡片
  required_params:
    - card_id, content_id, content_type
    - position
    - source
    - click_zone               # title / cover / author / share_btn
    - dwell_before_click_ms    # 从曝光到点击的时长
  optional_params:
    - tap_count                # 单击 / 双击
    - tap_position             # 点击的具体坐标（热区分析）
    - is_long_press
```

### 3.2 设计要点

#### 1. 点击区分热区
不是所有"点击卡片"都一样：
```
点击封面 → 进入详情页
点击作者 → 进入作者页
点击点赞 → 互动
点击分享 → 分享面板

→ click_zone 参数让一个事件覆盖多种点击意图
→ 同时可以做"哪个区域被点击最多"的热区分析
```

#### 2. 双击 / 长按
内容产品里"双击点赞"是高频操作：
```
✅ 单独事件 video_double_tap_like
✅ 或者 video_card_click + tap_count=2
（看你产品的语义）
```

#### 3. 点击与曝光的关联
**关键**：每次点击都要能 join 回它对应的曝光：
```
通过 (user_id, card_id, source, recommend_request_id) 联合 join
或者：曝光时生成 impression_id，点击时回传
```

---

## 四、播放（Playback）：内容产品的灵魂

### 4.1 播放事件家族（**最少 8 个**）

```yaml
video_play              起播
video_play_progress     进度心跳（每 N 秒）
video_play_pause        暂停
video_play_resume       恢复
video_play_seek         拖动
video_speed_change      倍速
video_play_complete     完播（≥ 95%）
video_play_error        播放失败
```

每个事件**职责单一**——不要"一个 video_play_event 用 type 字段区分"，那样查询难写、推荐反馈侧难处理。

### 4.2 起播事件（video_play）

```yaml
- event: video_play
  trigger: 视频实际开始播放（首帧渲染）
  required_params:
    - video_id, video_duration_seconds
    - source, page
    - play_strategy            # auto / manual / continuous
    - is_first_play            # 本次会话首次播放该视频
    - quality                  # 360p / 720p / 1080p
    - network_type
    - load_time_ms             # 从点击到首帧的耗时
    - recommend_request_id, strategy_id
```

#### 关键区分
```
"用户点击播放按钮"    ≠   "视频实际开始播放"
"页面进入"           ≠   "auto-play 触发"

→ video_play 应该是**实际开始播放首帧**的时刻
→ 点击事件单独埋（如果不是 auto play）
```

### 4.3 进度心跳（video_play_progress）

```yaml
- event: video_play_progress
  trigger: 每 N 秒上报一次（典型 N=5 或 10）
  required_params:
    - video_id
    - play_position_ms         # 当前播放位置
    - play_duration_ms         # 累计播放时长（不含暂停）
    - quality, speed
```

#### 心跳频率权衡
```
N=1 秒：    数据精细但量巨大（直播 / 长视频崩）
N=10 秒：   数据稀疏但接近内容产品标配
N=15-30：  仅用于离线分析

→ 业内典型：5-10 秒
→ 关键：暂停 / 拖动时不计入心跳
```

#### 心跳本身和事件本身要分清
心跳是**汇报一种状态**，不是新动作。**离线分析时**通常需要：
- 用 `video_play` 标记起播
- 用心跳累加得到"播放总时长"
- 用 `video_play_complete` 标记完播

### 4.4 完播（video_play_complete）

```yaml
- event: video_play_complete
  trigger: 播放进度达 95% 以上（或按业务自定义）
  required_params:
    - video_id, video_duration_seconds
    - total_play_duration_ms   # 不含暂停的总播放时长
    - completion_ratio         # 实际完成度（0-1）
    - replay_count             # 是否回放过
    - source, strategy_id, recommend_request_id
```

#### "完播"的几种定义
```
A. 进度 ≥ 95%：             业内最通用
B. 进度 ≥ 90% AND 时长 ≥ 60 秒：  对长视频更宽松
C. 看完到结尾（包括拖到结尾）：    可以但有争议
D. 用户主动点完成：          少见
```

**业务有自己的定义，但必须文档化**——否则 BI、推荐、增长用三套定义。

### 4.5 拖动（video_play_seek）

```yaml
- event: video_play_seek
  required_params:
    - video_id
    - from_position_ms
    - to_position_ms
    - seek_direction           # forward / backward
    - trigger                  # progress_bar / button / gesture
```

**为什么重要**：
- 用户向前拖 = 内容前段无聊（推荐负反馈）
- 用户回看 = 内容值得看（推荐正反馈）
- 频繁拖 = 用户找特定内容

### 4.6 错误（video_play_error）

```yaml
- event: video_play_error
  required_params:
    - video_id
    - error_code               # enum
    - error_message            # 字符串简述
    - position_when_error_ms   # 出错时位置
    - retry_count              # 已重试次数
    - network_type
    - cdn_node                 # CDN 节点
    - quality
```

**错误事件不要嫌烦**——它是质量监控的核心。直播尤其依赖。

---

## 五、互动（Interaction）

### 5.1 互动事件分类（按信号强度）

```
弱信号    →    强信号

view  →  dwell  →  like  →  comment  →  share  →  follow  →  subscribe
 (低成本)                                                    (高成本)
```

成本越高 = 信号越强 = 推荐价值越大。**永远不要把所有互动事件混为一谈**。

### 5.2 标准事件

```yaml
- event: video_like
  required_params:
    - video_id, video_author_id
    - source, page
    - is_double_tap            # 双击点赞还是按钮点赞
    - dwell_before_like_ms     # 从曝光到点赞的时长（信号强度）
    - recommend_request_id, strategy_id

- event: video_unlike
  trigger: 取消点赞
  required_params:
    - video_id
    - dwell_before_unlike_ms

- event: video_share
  required_params:
    - video_id, video_author_id
    - share_to                 # wechat / weibo / link / save / qq
    - source, page

- event: video_comment
  required_params:
    - video_id, video_author_id
    - comment_text_length      # 字数（不存内容，隐私）
    - is_reply                 # 是否回复别人
    - reply_to_comment_id

- event: user_follow
  required_params:
    - target_user_id
    - source                   # video_detail / profile / recommend
    - follow_reason            # 推荐理由（可选）
```

### 5.3 设计要点

#### 1. 配套"取消"事件
```
video_like ↔ video_unlike
user_follow ↔ user_unfollow
video_favorite ↔ video_unfavorite

→ 真实互动是动态的，要能算"净增点赞"等
```

#### 2. 互动来源 (source)
```
同一个 like 在 feed 里和 detail 页里发生，意义不同
→ source 必带
```

#### 3. dwell_before_xxx
```
这是隐式信号强度的关键参数：
   dwell 1 秒后点赞    = 直觉性正反馈
   dwell 30 秒后点赞   = 深度认同
   dwell 0.1 秒后点赞  = 误触
   
→ 推荐模型可以用这个区分质量
```

---

## 六、推荐反馈信号（**内容产品独有，最关键**）

### 6.1 为什么要单独讲

电商 / SaaS 没有"推荐反馈" 的概念。内容产品的推荐系统**完全依赖埋点反馈训练**——埋错就模型崩。

### 6.2 反馈信号的极性

```
正反馈：用户喜欢，多推类似的
   - video_play_complete
   - video_like, video_share, video_comment, user_follow
   - long_dwell (停留长)
   - video_replay

负反馈：用户不喜欢，少推类似的
   - quick_swipe (快速滑走)
   - video_play_error / abort
   - feed_card_not_interested
   - feed_card_block_user
   - feed_card_report

中性：信息量小
   - 短停留 (但不是 quick_swipe)
   - 滑动浏览
```

**每个反馈事件都应明确标注极性**——通过元数据：

```yaml
- event: feed_card_quick_swipe
  is_recommend_signal: true
  signal_polarity: negative
  signal_strength: medium

- event: feed_card_not_interested
  is_recommend_signal: true
  signal_polarity: negative
  signal_strength: strong       # 显式负反馈，最强
```

### 6.3 关键反馈事件（**必埋**）

```yaml
# 隐式正反馈
- video_play_complete
- video_like
- video_share
- user_follow
- feed_card_long_dwell        # 停留 > X 秒，未点击但深度浏览

# 隐式负反馈
- feed_card_quick_swipe       # 快速滑过（< 1 秒）
- video_play_abort            # < 3 秒就关
- video_play_skip             # 未完播就切下一个

# 显式负反馈（强信号）
- feed_card_not_interested    # 不感兴趣按钮
- feed_card_block_user        # 屏蔽作者
- feed_card_report            # 举报
- feed_card_dismiss           # 主动关闭
```

### 6.4 关键参数：`recommend_request_id`

每次推荐召回的请求 ID。**所有反馈事件都要带回**，让推荐系统能 join 用户行为和具体策略：

```
推荐请求          推荐结果           用户行为
┌──────────┐    ┌──────────┐     ┌────────────┐
│ req_abc  │ →  │ 10 个卡片  │  →  │ 点了第 3 个 │
│ strategy │    │           │     │ 完播        │
│ model_v5 │    │           │     │ 点赞        │
└──────────┘    └──────────┘     └────────────┘
                       ↓                ↓
            通过 recommend_request_id 关联
```

没有这个参数 = 推荐反馈数据无法归因到策略 = 模型迭代瞎子。

### 6.5 反馈延迟

不同信号到达时间不同：

```
即时（秒级）：     click, like, share, follow, complete
中等（分钟级）：   re-engagement, re-share
长期（小时-天）：  retention, churn

推荐模型在线学习需要"即时"信号
长期效应需要离线 ETL 关联
```

埋点时不需要管延迟，但**数仓侧的反馈聚合**要分层处理。

---

## 七、推荐反馈完整 schema 示例

```yaml
- name: feed_card_quick_swipe
  domain: content
  object: feed_card
  action: quick_swipe
  action_category: negative
  is_recommend_signal: true
  signal_polarity: negative
  signal_strength: medium
  
  required_params:
    - card_id
    - content_id, content_type
    - position
    - source                 # recommend / follow / hot
    - dwell_time_ms          # 实际停留时间
    - swipe_velocity         # 滑动速度（区分"快速滑走" vs "正常浏览"）
    - recommend_request_id
    - strategy_id, model_id, model_version
  
  description: |
    用户在卡片可见后 < 1.5 秒内主动滑走。
    判定：dwell_time_ms < 1500 AND swipe_velocity > 阈值。
    用作推荐系统的隐式负反馈。
  
  notes: |
    阈值由推荐团队和数据团队共同 calibrate，每季度 review。
```

---

## 八、综合 Checklist

### 曝光
```
□ 1. "有效曝光"的判定（visibility + dwell）明确？
□ 2. 同一会话同一卡片的曝光去重了？
□ 3. position 与渲染位置同步更新？
□ 4. recommend_request_id 必带？
```

### 播放
```
□ 5. 播放事件家族 ≥ 8 个（起播 / 心跳 / 完播 / 暂停 / 拖动 / 倍速 / 错误等）？
□ 6. "起播"是首帧渲染，不是点击播放按钮？
□ 7. 心跳频率（N 秒）公司统一？
□ 8. "完播"定义全公司一致并文档化？
□ 9. 错误事件包含 error_code、network、cdn 等诊断字段？
```

### 互动
```
□ 10. 每个 like / favorite / follow 配套 unlike / unfavorite / unfollow？
□ 11. 互动事件带 dwell_before_xxx（信号强度）？
□ 12. share 区分 share_to（哪个渠道）？
```

### 推荐反馈
```
□ 13. 所有反馈事件标注 signal_polarity（pos / neg / neutral）？
□ 14. 强信号（report / block / not_interested）单独埋？
□ 15. recommend_request_id 在所有反馈事件里出现？
□ 16. 隐式负反馈（quick_swipe / play_abort）有阈值定义？
□ 17. 反馈事件 schema 由推荐团队 + 数据团队 + 产品共同 review？
```

---

## 九、扩展阅读

- 本目录其他文档（待补）：impression-and-visibility.md、playback-events.md、interaction-events.md、recommendation-feedback.md
- 概念基础：[../concepts/event-naming.md](../concepts/event-naming.md)、[../concepts/parameter-design.md](../concepts/parameter-design.md)、[../concepts/event-taxonomy.md](../concepts/event-taxonomy.md)
- IAB Viewable Impression Standard（广告业曝光标准）
- YouTube Engineering Blog 系列（视频埋点经验）
- Netflix Tech Blog（推荐反馈系统）
- 字节 / 快手 / 小红书等公开分享的内容反馈体系
- 与 AB 测试的对接：[../../ab-testing/concepts/hypothesis-testing.md](../../ab-testing/concepts/hypothesis-testing.md)
