# 【教程】Handoff Preview 与 Figma 本地同步使用教程

<callout emoji="💡">
**一句话目标**
- 在本地 Handoff Preview 里选定当前页面和状态。
- 把当前页面推到 Figma，变成可编辑的原生 Frame、Text、Shape 和本地变量。
- Figma 写回只进入 Preview 待确认区，确认后再保存到本地 Handoff。
</callout>

## 适用范围

这份教程只覆盖本地编辑链路：

| 项目 | 支持情况 |
|-|-|
| 本地 `handoff/current` 预览 | 支持 |
| 个人 Figma 账号安装开发插件 | 支持 |
| 文案、常见样式、当前页引用 token | 支持 |
| 线上 GitLab / KBS Preview 写回 | 暂不支持 |
| Figma 自由画布重组后自动改 Handoff 结构 | 暂不支持 |

Handoff 仍是事实源。Figma 只是本地视觉编辑面，所有写回都要回到 Preview 工作台人工确认。

## 同步流程

<whiteboard token="HZF5wwGjnhhW9ebj4oqcUcw2nXb"></whiteboard>

## 准备工作

### 本地 Preview 服务

在 `handoff-mcp` 仓库里启动本地 Preview renderer。下面命令使用当前仓库的 minimal fixture，真实项目时替换 `HANDOFF_ROOT` 和 `AI_ROOT`：

```Bash
cd /Users/lxj/Desktop/handoff-mcp
PORT=5180 HOST=127.0.0.1 \
HANDOFF_ROOT=/Users/lxj/Desktop/handoff-mcp/fixtures/minimal-project/handoff/current \
AI_ROOT=/Users/lxj/Desktop/handoff-mcp/fixtures/minimal-project \
node assets/preview/renderer/serve-dist.mjs
```

打开本地需求页：

```Plain Text
http://127.0.0.1:5180/preview/handoff?sourceMode=local&localHandoffRoot=%2FUsers%2Flxj%2FDesktop%2Fhandoff-mcp%2Ffixtures%2Fminimal-project%2Fhandoff%2Fcurrent&requirement_id=minimal-token-preview
```

页面进入后切到「工作台模式」。右侧属性面板里会出现「Figma 同步」区域。

### Figma 开发插件

插件源码在：

```Plain Text
/Users/lxj/Desktop/handoff-mcp/assets/preview/figma-plugin
```

安装方式：

- 打开 Figma，新建或打开一个设计文件。
- 进入插件开发入口，选择导入本地 manifest。
- 选择这个文件：

```Plain Text
/Users/lxj/Desktop/handoff-mcp/assets/preview/figma-plugin/manifest.json
```

- 运行插件，插件面板会显示 `Sync URL` 输入框，以及 `Import`、`Write Back` 两个按钮。

## 从 Preview 推到 Figma

在 Preview 工作台操作：

- 确认当前页面、类型和状态正确，例如 `pages/home · ready`。
- 在右侧「Figma 同步」区域点击「复制地址」。
- 复制到的是当前页面状态的导出接口，形如：

```Plain Text
http://127.0.0.1:5180/api/figma-sync/export?type=pages&page=home&state=ready
```

在 Figma 插件操作：

- 把同步地址粘贴到 `Sync URL`。
- 点击 `Import`。
- 插件会创建一个 Handoff Frame，并生成可编辑图层。
- 插件会创建或复用 Figma 本地变量集合 `Handoff Local Tokens`。

导入时只会推当前页实际引用的 token。未引用 token 不会进入 Figma。

## 在 Figma 里编辑

第一版建议只做小步视觉调整：

| 可编辑内容 | 写回行为 |
|-|-|
| Text 文案 | 生成 Handoff 文案 patch |
| Text 颜色、字号 | 生成样式 patch |
| Frame 背景色 | 生成样式 patch |
| Frame 圆角 | 生成样式 patch |
| `Handoff Local Tokens` 变量值 | 生成 token patch |

注意事项：

- 写回前选中导入的 Handoff Frame，或选中它下面的任意子节点。
- 不要删除图层上的插件元数据。
- 新画出来的陌生节点不会自动变成 Handoff 结构。
- 大幅重排、复杂组件重组、无法语义化的 raw pixel 变化会降级为 warning。

## 从 Figma 写回 Preview

在 Figma 插件操作：

- 选中导入的 Handoff Frame 或子节点。
- 点击 `Write Back`。
- 插件会把变化发到：

```Plain Text
POST /api/figma-sync/writeback
```

- 插件状态显示 `Writeback queued: X patches, Y token patches.` 时，说明变化已经进入 Preview inbox。

这里不会直接写磁盘，也不会改线上 KBS。

## 在 Preview 确认保存

回到 Preview 工作台：

- 点击「拉取变更」。
- Preview 会读取：

```Plain Text
GET /api/figma-sync/inbox
```

- Handoff 节点变化进入现有 pending patch 面板。
- Token 变化显示在「保存 Token (N)」按钮旁。
- 逐条检查 pending patch。
- 文案和样式 patch 按工作台原有保存流程保存。
- Token patch 点击「保存 Token (N)」，确认后调用本地 `/api/save-token-patches`。

保存完成后，Preview 会清理已拉取的 inbox 项：

```Plain Text
POST /api/figma-sync/inbox/clear
```

## 推荐操作节奏

| 场景 | 做法 |
|-|-|
| 调一页视觉 | 只同步当前 `type/page/state` |
| 改多个状态 | 每个状态单独 Import 和 Write Back |
| 改 token | 优先改 Figma 本地变量，再回 Preview 保存 Token |
| 出现 warning | 回 Preview 看 warning，不自动保存 |
| Handoff 文件已变化 | 重新 Import，避免 base hash 过期 |

## 常见问题

### 浏览器显示 `127.0.0.1 拒绝建立连接`

本地 Preview 服务没有在对应端口监听。检查端口和启动命令是否一致：

```Bash
lsof -nP -iTCP:5180 -sTCP:LISTEN
curl -sI http://127.0.0.1:5180/preview/handoff
```

### 页面白屏

优先确认静态资源能访问：

```Bash
curl -sI http://127.0.0.1:5180/preview/assets/index-CQ1Kpl8J.js
```

如果资源 404，使用当前仓库的 `serve-dist.mjs`，它已经处理 `/preview/assets/*` 路由。

### `Import` 失败

常见原因：

| 表现 | 处理 |
|-|-|
| `Sync URL is required` | 插件里没有粘贴同步地址 |
| HTTP 404 | 同步地址里的 `page` 或 `state` 不存在 |
| 连接失败 | Preview 服务端口不对，或服务已退出 |
| payload schema 不支持 | 插件和本地服务版本不一致，重启服务并重新导入插件 |

### `Write Back` 提示选择 Frame

选中导入生成的 Handoff Frame，或它下面的任意节点，再点击 `Write Back`。

### 写回后 Preview 显示 0 条 patch

可能原因：

| 原因 | 处理 |
|-|-|
| 没有实际变化 | 在 Figma 改一个文本或颜色后重试 |
| 改的是暂不支持字段 | 换成文案、颜色、字号、圆角或 token 变量 |
| base hash 过期 | 重新从 Preview Import |
| 图层元数据丢失 | 重新 Import，不要复制成脱离原 Frame 的节点 |

## 验证清单

完成一次同步后，至少确认这些结果：

- Preview 工作台能打开当前本地需求。
- Figma 插件 `Import` 后生成 Handoff Frame。
- Figma 改字后 `Write Back` 显示 queued patches。
- Preview 点击「拉取变更」后 pending patch 可见。
- Token 变量变化进入「保存 Token (N)」。
- 保存后本地 Handoff 文件变化符合预期。

## 边界原则

- 本地 Preview 可以读写本地 Handoff。
- 线上 GitLab / KBS Preview 保持只读。
- Figma 不作为事实源。
- 任何无法映射到 Handoff 语义的变化只产生 warning。
- 保存前必须人工确认 patch。