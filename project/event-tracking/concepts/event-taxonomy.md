# 事件分类法（Event Taxonomy）

> 命名规范解决"一个事件叫什么"，**分类法解决"几百个事件怎么组织在一起"**。一个产品成熟到 100+ 事件后，没有分类法就会陷入"找不到、记不住、互相重叠"的混乱。本文给出一套实战可用的分类体系。

---

## 一、为什么需要分类法

100 个事件还能靠记忆。500 个事件就完全失控：

```
没有分类法的常见症状：

   - 新人入职第一周问："我想看用户播放视频的数据，有哪些事件？"
     → 全员翻文档 30 分钟
   - 加新事件前不知道"是否已经有了"
     → 重复埋点
   - 数据查询时 WHERE event_name IN (...) 列十几个名字
     → 总有漏的
   - 团队 A 加的"分享"和团队 B 加的"分享"语义不同
     → 数据打架

→ 这不是"记不住"的问题，是"没有结构"的问题
```

分类法的本质是**给事件赋予结构**——让"找事件"从遍历变成定位。

---

## 二、最小分类模型：三层

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Domain                                                    │
│   领域      → "这事属于哪个业务模块"                          │
│   例：内容、用户、商业化、社交、增长                         │
│                                                             │
│       ↓                                                     │
│                                                             │
│   Object                                                    │
│   对象      → "对什么东西操作"                                │
│   例：video, feed, comment, user, payment                   │
│                                                             │
│       ↓                                                     │
│                                                             │
│   Action                                                    │
│   动作      → "做了什么"                                      │
│   例：click, play, complete, like, share                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

事件名 = `object_action`（详见 [event-naming.md](event-naming.md)），但事件**所属**的域 / 对象 / 动作维度全部要在元数据里登记。

---

## 三、Domain 维度：内容产品的典型划分

按业务模块划分，4-7 个为宜：

```
1. content       内容相关（视频、文章、直播、播客）
2. interaction   互动（点赞、评论、分享、关注）
3. user          用户（注册、登录、画像、设置）
4. social        社交（私信、群组、好友）
5. growth        增长（推送、邀请、签到、任务）
6. commercial    商业化（广告、付费、订阅）
7. infrastructure  基础（错误、性能、网络）
```

> **不要超过 8 个 domain**——再多说明业务还没分清。

---

## 四、Object 维度：内容产品标准对象

```
content 域：
   video, article, audio, live, podcast, image, gallery

interaction 域：
   like, comment, favorite, share, follow, reply

user 域：
   user, profile, account, setting, notification

social 域：
   message, group, friend, mention

growth 域：
   push, sms, email, invitation, task, sign_in

commercial 域：
   ad, payment, subscription, order, coupon

infrastructure 域：
   error, performance, network, crash
```

---

## 五、Action 维度：动作分类法（**重要**）

按"动作生命周期"再分组：

### 1. Discovery（发现）
- `impression`, `view`, `expose`, `render`
- "用户看到 / 接触到内容"

### 2. Engagement（参与）
- `click`, `tap`, `play`, `pause`, `seek`, `complete`
- "用户主动消费内容"

### 3. Interaction（互动）
- `like`, `unlike`, `favorite`, `comment`, `share`, `follow`
- "用户对内容产生关系"

### 4. Lifecycle（生命周期）
- `create`, `publish`, `edit`, `delete`, `archive`
- "内容 / 对象本身的状态变化"

### 5. Conversion（转化）
- `purchase`, `subscribe`, `submit`, `register`, `install`
- "高价值业务动作"

### 6. Negative（负向）
- `dismiss`, `not_interested`, `report`, `block`, `hide`
- "用户表达负面态度"

> **Negative 是内容产品独有且关键的一类**——电商 / SaaS 用得少，但内容产品里负反馈是推荐系统的"血液"。

---

## 六、放在一起：事件元数据

每个事件登记时带上完整三维分类：

```yaml
- name: video_play_complete
  domain: content
  object: video
  action: complete
  action_category: engagement
  description: 视频播放至结束（≥95% 进度）
  required_params: [video_id, play_duration_ms, source]
  applies_to_platforms: [ios, android, web]
  is_recommend_signal: true        # 推荐反馈相关
  signal_polarity: positive        # 正反馈
  added_at: 2023-04-01
  owner: video-team
```

这种结构化登记的好处：

```
1. 数据团队建数仓时按 domain 分主题表
2. 推荐团队按 is_recommend_signal=true 一键提取所有反馈事件
3. 新人查事件时按 object 过滤
4. 命名审查时按 action 词典验证
```

---

## 七、内容产品的"事件矩阵"

把 Object × Action 画成矩阵，能直观看出**哪些事件该有但还没有**：

```
                   impression   click   play   complete   like   share   negative
video                 ✓          ✓      ✓       ✓         ✓      ✓        ✓
article               ✓          ✓      —       ✓         ✓      ✓        ✓
live                  ✓          ✓      ✓       —         ✓      ✓        ✓
audio                 ✓          ✓      ✓       ✓         ✓      ✓        ✓
feed                  ✓          ✓      —       —         —      —        ✓
comment               ✓          ✓      —       —         ✓      —        ✓
profile               ✓          ✓      —       —         —      ✓        —
```

→ "—" 表示这个组合不存在（不适用）
→ 空白 = 该埋但还没埋（**埋点缺口**）

每季度对照这个矩阵 review 一遍，就能系统性发现埋点死角。

---

## 八、分类法的几个反模式

### ❌ 1. 按 UI 位置分类
```
❌ home_events, feed_events, profile_events, search_events
→ 同样的"视频点击"在每个分类里都有一份
→ 重复
```

正确：按业务对象分。位置变成参数。

### ❌ 2. 按团队分类
```
❌ team_a_events, team_b_events
→ 团队边界变了就要重组分类
→ 团队是组织视角，不是业务视角
```

### ❌ 3. 太深的层级
```
❌ content > video > recommendation > exposure > ...（5 层）
→ 没人记得住
```

3 层就够：domain / object / action。

### ❌ 4. 按版本分类
```
❌ v1_events, v2_events
→ 版本是参数（applies_to_app_version），不是分类
```

### ❌ 5. 没有"未分类" 兜底
```
→ 即使有完整的分类法，总有边界事件不好归类
→ 强行归类反而别扭
→ 接受 "uncategorized" 作为兜底分类（控制比例 < 5%）
```

---

## 九、如何"从无到有"建立分类法

如果你的产品已经有几百个无组织的事件，按这个步骤来：

### Step 1: 导出所有现有事件
```sql
SELECT event_name, COUNT(*) as event_count
FROM events
WHERE event_time >= NOW() - INTERVAL 30 DAY
GROUP BY event_name
ORDER BY event_count DESC;
```

### Step 2: 人工聚类
```
按你直觉对的分组，把 300 个事件归到 10-20 个 cluster。
```

### Step 3: 抽象出 domain / object / action
```
每个 cluster 的"共同点"提炼成 object。
观察哪些动作反复出现，提炼成 action 词典。
```

### Step 4: 建分类树
```
domain
  └─ object
      └─ action_category
          └─ action
              └─ event
```

### Step 5: 标注每个事件
```
为每个现存事件打上 (domain, object, action_category, action) 标签。
```

### Step 6: 制定"新事件准入流程"
```
新埋点必须先确定分类位置，才能进入命名 review。
未在分类法内的事件不允许上线。
```

### Step 7: 每月 review
```
观察"uncategorized" 事件比例。
比例上升 → 分类法不够覆盖，需要演进。
比例下降到 0 → 健康。
```

---

## 十、分类法工具化

不要靠人工维护一个 Word 文档。建议工具化：

### 选项 A：YAML / JSON 文件 + Lint
```yaml
# events_taxonomy.yaml
events:
  - name: video_play_complete
    domain: content
    object: video
    action: complete
    action_category: engagement
    ...
```

CI 检查：
- 新加事件必须填全字段
- 名字格式符合规范（详见 [event-naming.md](event-naming.md)）
- domain / object / action 在词典内

### 选项 B：用 schema-first 工具
- **Iteratively / Amplitude Data**
- **Avo**
- **Snowtype**
- 这些工具内置分类法 + 类型校验 + SDK 代码生成

### 选项 C：自建 Schema Registry
- 大公司自研
- 与 CI、SDK、数仓、BI 工具深度集成
- 实施成本高但 ROI 好

---

## 十一、分类法的演进

埋点分类法**会演进**。设计时考虑：

1. **新增 domain / object / action 的流程**（Review + 通知下游）
2. **deprecate 旧分类的流程**（先标记 deprecated，N 个月后删除）
3. **重命名 / 合并**（双轨过渡期 6-12 个月）
4. **跨大版本的兼容**（埋点 v1 vs v2 在数仓如何 union）

> 分类法是**活的**，不是石头碑文。**最坏的分类法是"一次定制后从此冻结"**。

---

## 十二、Checklist

```
□ 1. 有完整的 domain / object / action 三层分类？
□ 2. domain 数量 ≤ 8？
□ 3. action 词典在 [event-naming.md](event-naming.md) 中明确？
□ 4. 每个事件有元数据（domain / object / action / signal_polarity 等）？
□ 5. 推荐反馈类事件有专门标记（is_recommend_signal）？
□ 6. "事件矩阵"每季度 review，发现埋点缺口？
□ 7. 有"新事件准入流程"，不在分类内的事件不允许上线？
□ 8. uncategorized 事件比例 < 5%？
□ 9. 分类法的演进有版本管理？
□ 10. 分类法是工具化（YAML + Lint / schema-first 工具）的，不是 Word 文档？
```

---

## 十三、扩展阅读

- 本目录：[event-naming.md](event-naming.md)、[parameter-design.md](parameter-design.md)
- 内容事件：[../content-events/core-content-events.md](../content-events/core-content-events.md)
- **Amplitude — Taxonomy Playbook**（最实战，免费 PDF）
- **Snowplow Tracker Protocol**（最严格的 schema 模型）
- **Segment Specification**（电商 / SaaS 范式）
- Heap、Mixpanel、神策的"事件分类"设计文档
- 内部数据契约工具：Iteratively / Avo / Snowtype
