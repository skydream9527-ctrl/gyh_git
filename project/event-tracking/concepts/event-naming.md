# 事件命名规范

> 命名是埋点设计里**最便宜也最容易做错**的事。一个事件名一旦上线就很难改——所有下游 SQL、报表、模型、文档都依赖它。本文给出一套可工程化的命名规范，并解释为什么这套规范在内容产品里特别重要。

---

## 一、为什么命名值得专门写一篇

埋点命名失败的代价是**复利的**：

```
Day 1：     一个事件叫错名字，没人察觉
Month 3：   下游加了 5 个 SQL 看板，都引用了这个名字
Month 6：   推荐团队、增长团队各引用了它
Year 1：    想改名 → 影响范围大到不敢改
Year 2：    每个新人入职都要被告知"这个名字是历史包袱"
```

**修复成本随时间指数上升**——这就是为什么命名是埋点设计的"零号问题"。

---

## 二、核心规范（**最小可执行版**）

### 规范 1：snake_case，全小写
```
✅ video_play_complete
✅ feed_card_impression
❌ VideoPlayComplete       (PascalCase 容易在 SQL 里出错)
❌ video-play-complete     (kebab 在很多 SQL 引擎是减号)
❌ videoPlayComplete       (camel 不一致)
```

**理由**：snake_case 在 SQL、Python、JSON 里都不需要转义，是最低摩擦的命名方式。**全公司统一一种风格**比"哪种风格"重要。

### 规范 2：`object_action` 或 `action_object` 模式（**任选其一，全公司统一**）

两种主流：

| 模式 | 例子 | 优势 |
|---|---|---|
| `object_action` | `video_play`, `comment_publish`, `feed_impression` | 同对象事件聚集排序 |
| `action_object` | `play_video`, `publish_comment`, `view_feed` | 动词在前，自然语言 |

**业界主流是 `object_action`**——因为按字母排序时，同一对象的事件会连在一起，便于查找：

```
按 object_action 排序：
   comment_delete
   comment_like           ← 评论相关连在一起
   comment_publish
   comment_reply
   feed_card_click
   feed_card_impression   ← feed 相关连在一起
   feed_refresh
   video_pause
   video_play
   video_play_complete    ← 视频相关连在一起
```

**选定后全公司一致**——最忌混用。

### 规范 3：动词词典（**必须有**）

固定 10-20 个动词，**严格用这些**，不要发明新词：

```
通用动作：
   click, tap, view, impression, scroll, hover

播放：
   play, pause, resume, complete, seek, speed_change

互动：
   like, unlike, favorite, unfavorite, share, comment, follow, unfollow

生产：
   create, publish, edit, delete, save_draft

生命周期：
   load, render, error, expose, dismiss

转化：
   submit, purchase, subscribe, cancel
```

> **为什么这件事重要**：没有词典 → 一个团队用 `click`，另一个用 `tap`，第三个用 `press`，第四个用 `select`。三个月后查询"用户点击"要 `WHERE action IN ('click', 'tap', 'press', 'select', 'touch', 'choose', 'hit')`。

### 规范 4：避免有歧义的前缀 / 后缀

```
❌ video_play_v2          (版本号写进事件名 → 升级时尴尬)
❌ video_play_new         (什么时候不"new" 了？)
❌ ios_video_play         (端别应该是参数不是名字)
❌ test_video_play        (测试事件 → 上线后忘删)
```

正确做法：**版本和端别都进参数**。

### 规范 5：**长度有上限**

经验值：**60 字符以内**，超长的多半是事件粒度太大。

```
❌ user_clicked_subscribe_button_in_video_recommendation_panel_after_watching_3_videos
   (这是 10 个字段拆开)
```

应该拆成：

```
✅ subscribe_button_click  +  参数 location, source, watch_count, ...
```

---

## 三、不要做的几件事

### ❌ 1. 把界面位置写进事件名
```
❌ home_feed_video_card_click
❌ profile_page_follow_click
❌ search_result_video_click

→ 同一个动作（视频卡片点击）在三个地方有三个名字
→ 想统计"所有视频点击" 要枚举所有地方
```

正确做法：

```
✅ video_card_click  +  参数 page="home_feed" / "profile" / "search_result"
```

### ❌ 2. 把业务状态写进事件名
```
❌ video_play_for_paid_user
❌ video_play_for_new_user

→ "新用户" / "付费用户" 是属性，不是事件
```

正确做法：

```
✅ video_play  +  参数 is_paid_user, days_since_install, ...
```

### ❌ 3. 一个事件名表达多个含义
```
❌ engagement (究竟是点赞还是评论还是分享？)
❌ user_action  (太泛，等于没埋)
```

每个事件名要**对应一个明确动作**。

### ❌ 4. 用缩写
```
❌ vid_p_c          (video_play_complete?  vid_play_count? )
❌ usr_lgn          (user_login)
```

**几年后只有原作者知道是什么意思**。

### ❌ 5. 用拼音
```
❌ shipin_bofang     (视频_播放)
❌ guanzhu_anniu     (关注_按钮)
```

**国际化和工具支持都会出问题**。即使纯中文产品也用英文事件名（业界共识）。

---

## 四、命名规范文档应该长什么样

把规范写进一份"埋点命名规范"文档，至少包含：

```markdown
# 埋点命名规范 v1.0

## 1. 通用规则
- snake_case，全小写
- object_action 模式
- 60 字符以内
- 用英文，不用拼音

## 2. 动词词典（不在词典里的词不允许使用）
- click, tap, view, impression
- play, pause, complete, seek
- like, favorite, share, comment, follow
- ...

## 3. 对象词典
- video, feed, comment, user, profile, ...

## 4. 不允许的命名
- 含 v1, v2, new, old, test
- 含界面位置（应该用参数）
- 含业务状态（应该用参数）

## 5. 命名审查流程
- 新埋点必须 PR review
- review 时 lint 工具自动检查
- 上线前埋点 owner + 数据 owner 双签
```

> **写下来 + 强制执行**比"嘴上说"重要 100 倍。规范没文档 = 没规范。

---

## 五、Lint 工具：自动化命名约束

不要靠人工 review。建一个简单的 Lint 工具检查所有新增事件：

```python
import re

VERB_DICTIONARY = {'click', 'tap', 'view', 'impression', 'play', 'pause',
                   'complete', 'seek', 'like', 'favorite', 'share', 'comment',
                   'follow', 'create', 'publish', 'edit', 'delete', ...}

OBJECT_DICTIONARY = {'video', 'feed', 'comment', 'user', 'profile', ...}

FORBIDDEN_TOKENS = {'v1', 'v2', 'new', 'old', 'test', 'tmp', 'wip'}

def lint_event_name(name: str) -> list[str]:
    errors = []
    
    # 全小写 + snake_case
    if name != name.lower():
        errors.append(f"应全小写: {name}")
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        errors.append(f"必须 snake_case: {name}")
    
    # 长度
    if len(name) > 60:
        errors.append(f"超过 60 字符: {name}")
    
    # 禁用词
    for token in FORBIDDEN_TOKENS:
        if token in name.split('_'):
            errors.append(f"含禁用词 '{token}': {name}")
    
    # object_action 模式
    parts = name.split('_')
    if len(parts) < 2:
        errors.append(f"应至少 object_action 两段: {name}")
    
    # 词典检查（最后一段是动词）
    if parts[-1] not in VERB_DICTIONARY:
        errors.append(f"动词 '{parts[-1]}' 不在词典: {name}")
    
    # 对象在前几段
    if not any(p in OBJECT_DICTIONARY for p in parts[:-1]):
        errors.append(f"未识别到合法对象词: {name}")
    
    return errors
```

接入 CI：每个 PR 改动埋点定义文件就跑这个 Lint。

---

## 六、内容产品的命名特殊考虑

### 1. 区分"曝光"和"可见曝光"
```
✅ feed_card_render          (DOM 渲染了)
✅ feed_card_impression      (满足可见性阈值的有效曝光)

→ 这两个含义不同，必须两个事件
→ 详见 [../content-events/core-content-events.md](../content-events/core-content-events.md)
```

### 2. 播放进度类事件多样
```
✅ video_play              (起播)
✅ video_play_progress     (进度心跳，每 N 秒一次)
✅ video_play_complete     (完播)
✅ video_play_pause        (暂停)
✅ video_play_resume       (恢复)
✅ video_play_seek         (拖动)
✅ video_speed_change      (倍速调整)
✅ video_play_error        (播放失败)

→ 内容产品的播放埋点天然 8-10 个事件
→ 这是为什么命名规范在内容产品上比电商重要 5 倍
```

### 3. 推荐反馈事件
```
✅ feed_card_dwell           (停留时长，作为隐式正反馈)
✅ feed_card_quick_swipe     (快速滑走，隐式负反馈)
✅ feed_card_not_interested  (显式负反馈)
✅ feed_card_block_user      (强负反馈)
✅ feed_card_report          (举报)

→ 推荐系统对这些事件极度敏感，命名必须精确无歧义
```

---

## 七、命名一旦上线，怎么改

很难改。但有几种相对干净的方式：

### 方法 1：双写过渡

```
v1.0：     发送 video_play
v1.5：     同时发送 video_play 和 video_play_v2
v2.0：     只发送 video_play_v2
v2.5：     drop video_play

下游 SQL 在过渡期同时支持两个名字
```

### 方法 2：上报层 alias

在数据接收服务做事件名映射：

```python
EVENT_ALIASES = {
    'video_play': 'video_play_v2',  # 旧名映射到新名
}
```

下游永远只看到新名，但旧客户端不需要更新。

### 方法 3：直接 break + 全员通知

适合还没大规模使用的场景。**绝不要在已被多个团队 / 报表使用后这么做**。

---

## 八、Checklist

```
□ 1. 全公司有统一的"命名规范文档"吗？
□ 2. 命名风格（snake_case + object_action）一致吗？
□ 3. 动词词典明确吗？是否在 review 时强制执行？
□ 4. 对象词典明确吗？
□ 5. 禁用前缀（v1/test/new 等）有 Lint 工具检查吗？
□ 6. 长度有上限（建议 ≤ 60）？
□ 7. 同一动作（如视频点击）只有一个事件名？
□ 8. 界面位置 / 业务状态都在参数里，不在事件名里？
□ 9. 有版本管理流程（旧名怎么 deprecate）？
□ 10. 新人能 30 分钟内学会规范吗？
```

---

## 九、扩展阅读

- 本目录：[event-taxonomy.md](event-taxonomy.md) — 在命名规范之上的分类体系
- 本目录：[parameter-design.md](parameter-design.md) — 参数怎么设计
- 内容事件：[../content-events/core-content-events.md](../content-events/core-content-events.md)
- **Amplitude — *Taxonomy Playbook***（免费 PDF，必读）
- **Snowplow — Tracker Protocol**（最严格的 schema 标准）
- **Segment — Specification**（电商 / SaaS 行业事实标准）
- Mixpanel Naming Convention 文档
- Iteratively / Avo / Snowtype（schema-first 工具）
