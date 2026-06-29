# Mify Model Gateway Skill — Changelog

## 2026-05-21 — default-desktop-proxy-http-loopback

- Claude Desktop 本地 proxy 默认改为 `http://localhost:<port>` loopback，避免 Electron provider health check 对自签 localhost CA 报 `ERR_CERT_AUTHORITY_INVALID`。
- `manage_claude_desktop_proxy.py` 新增/固化 `--scheme http|https`，state 记录 scheme，并能从 LaunchAgent 参数识别当前协议，避免旧 state 残留 `https` 时误报。
- 更新 Desktop proxy 文档与验证命令：HTTP 为默认推荐，HTTPS 仅在用户明确需要时使用 `--scheme https`。

## 2026-05-21 — fix-desktop-proxy-localhost-tls

- 修复 Claude Desktop 本地 proxy TLS 证书生成：改用明确的 OpenSSL config 生成 CA/server 证书，避免重复/异常扩展导致系统 TLS 校验报 `ERR_CERT_AUTHORITY_INVALID`。
- `manage_claude_desktop_proxy.py install --apply` 会校验现有 CA/server 证书；若发现不可验证，会自动重签 localhost 证书再安装。
- 已知现象：模型对话可能仍能成功，但 Claude Desktop 顶部 provider health check 会因为 Chromium/System TLS 不信任 localhost 证书而提示 `Can't reach localhost:41414`。

## 2026-05-20 — generalize-desktop-proxy-routing-and-port

- 放宽 Claude Desktop 本地 proxy 的模型改写触发条件：任何 `/v1/*` JSON POST 只要 top-level `model` 命中映射表或带 `[1M]` / `[1m]` 标签，就先 normalize/改写再转发，不再把改写绑死到 `/v1/messages`。
- 保留 route path 分流只用于特殊 endpoint：`/v1/models` 本地返回模型列表，`*/count_tokens` 本地返回估算 token，其他 `/v1/*` 透明转发。
- `manage_claude_desktop_proxy.py install --apply` 默认优先 41414；若端口占用，自动选择 41415-41514 的空闲端口，也支持 `--port` 显式指定，避免对外分享时固定端口冲突。
- 更新 SKILL / reference / eval，明确 `xisheng` provider 名保留，排障时不要把 provider 名误判为根因。

## 2026-05-20 — fix-desktop-proxy-beta-routing

- 修复 Claude Desktop 本地 proxy 的核心路由逻辑：按 query 前的 route path 识别 `/v1/messages?beta=true`，避免 `xisheng/claude-*` 原样打到 Mify 后触发 `Not supported model`。
- 新增 `/v1/messages/count_tokens?beta=true` 本地 token 估算响应、`[1M]` / `[1m]` 模型标签剥离、`claude-haiku-4-5-20251001` fallback 映射。
- 更新 Desktop proxy 文档与验证命令，明确 PPIO 直通、xisheng→MiMo 映射、Claude Code 配置三者边界。
- 默认 7 个 Desktop picker 模型全部标记 `supports1m: true`；healthz 改成 loopback liveness 检查，避免旧本地 CA 被 Python 证书策略误报。

## 2026-05-19 — claude-desktop-local-proxy

- 新增 Claude Desktop 非 Claude 模型本地 proxy 工作流：先明确官方 Desktop 只支持 Claude/Anthropic routes，再询问用户是否接受本机 proxy 绕过模型名校验。
- 新增 `scripts/claude_desktop_proxy.py` 与 `scripts/manage_claude_desktop_proxy.py`，支持 `install/status/start/restart/stop/uninstall`，默认提供 PPIO Claude 直通 + `xisheng/claude-*` 映射到 MiMo 的矩阵。
- 明确 Claude Desktop proxy 与 Claude Code 配置完全分离：Claude Code 继续用 `set_cc_model.py` 直接配置真实 Mify 模型，不需要伪装。
- 已知风险：本地 proxy 是工程绕法，不是 Anthropic 官方承诺；未来 Claude Desktop 若加强校验，可能需要更新 proxy。

## 2026-05-16 — fix-description-length

修 Codex 启动时报错 `invalid description: exceeds maximum length of 1024 characters`（实测 1126 字符）。

- 重写 description 1126 → ~501 字符
- 按 superpowers:writing-skills CSO 原则改为 `Use when ...` 触发式
- 剥离原描述里 7 条编号工作流（"(1) 查 Mify... (7) 把 Mify 挂到 Claude Desktop..."），这类细节本来就该在 SKILL.md 正文，不该塞进 frontmatter，否则 Claude/Codex 会把 description 当工作流引导而跳过读全文
- frontmatter 总字节 1898 → 582
- 同期 agent-sync-doctor / icloud-materialization-doctor 也做了类似修复

## 2026-05-11

### Pricing portal investigation note

新增 `references/pricing_portal_research.md`，记录 `gatewayPrice` 调研结论：

- `api.llm.mioffice.cn/v1/models` 仍只返回可用性 catalog，`?include=pricing` 不增加价格字段。
- `api.llm.mioffice.cn` 下常见 pricing 路径仍为 400/404。
- `llm.mioffice.cn/gatewayPrice` 和候选 `/api/*` 路径未登录均被 CAS 302 拦截。
- Chrome 已登录页面可打开到“大模型 API 开放平台”，但本次 Codex Chrome plugin native bridge 不可用，Computer Use 读取 Chrome 超时；AppleScript 可读 URL/title，但页面 JS 需要用户启用 `View > Developer > Allow JavaScript from Apple Events` 才能继续捕获 XHR。
- 推荐后续优先走“捕获已登录页面 XHR 响应并缓存”，避免直接读取/保存 CAS cookie；Chrome extension 技术上可读 HttpOnly cookie，但无法由 skill 静默安装，只能 Web Store / 企业策略 / 用户开发者模式安装。

## 2026-05-08

### Claude Desktop 1.6259.x 适配

Claude Desktop Cowork 3P 本地用户配置主路径更新为：

```text
~/Library/Application Support/Claude-3p/configLibrary/_meta.json
~/Library/Application Support/Claude-3p/configLibrary/<active-id>.json
```

`_meta.json.appliedId` 指向 active config。clean profile / 新机器没有 active id 时，skill 会自动生成 UUID 并创建对应 JSON。

### 模型列表限制更新

生产默认 `inferenceModels` 收敛到 4 个已验证 Claude routes：

- `ppio/pa/claude-opus-4-7`
- `ppio/pa/claude-opus-4-6`
- `ppio/pa/claude-sonnet-4-6`
- `ppio/pa/claude-haiku-4-5`

MiMo / Kimi / Qwen / DeepSeek / GPT 等非 Claude Mify 模型继续支持 Claude Code，但不要写入 Claude Desktop 生产 `inferenceModels`。

### 新增操作模式

| 命令 | 用途 |
|---|---|
| `install_cowork_config.py` | first-time / clean profile dry-run |
| `install_cowork_config.py --apply` | 写入完整 3P configLibrary 配置 |
| `install_cowork_config.py --fix-models` | 已有 profile 只预览模型列表修复 |
| `install_cowork_config.py --fix-models --apply` | 已有 profile 只替换 `inferenceModels` |
| `install_cowork_config.py --include-mimo-test` | 显式追加 MiMo 做 test-only 失败验证 |
| `install_cowork_config.py --live-models` | 探索 Mify 实时 Claude routes，opt-in，不作为默认生产路径 |

### 证据与评测

证据整理：`https://feishu.cn/wiki/NXNNwA1mfiT1zNkfP79crnqdnzf`

新增 4 条 Claude Desktop 1.6259.x 兼容性 eval：

- 已有 profile 只修模型，不能覆盖用户其他配置
- clean profile active id 自举
- MiMo 显式 test-only 失败验证
- live catalog opt-in

## 2026-04-28

历史记录：以下是 4/28 当时的修复背景。Claude Desktop 1.6259.x 之后，请以 2026-05-08 的 `configLibrary` 主路径为准。

### 对话历史安全继承

从 GUI 配置迁移到 skill 自动配置时，已有的 Claude Desktop 对话记录自动继承，不丢失、不需要手动操作。后续修改模型列表也不影响历史对话。

> 历史技术要点：4/28 当时采用 `enterpriseConfig` 驱动模型列表和网关配置，并把 `configLibrary` draft UUID 作为身份锚。5/8 之后，skill 直接写 `configLibrary` active config，不再把它只当身份锚。

### Cowork 联网能力放开

默认写入 `coworkEgressAllowedHosts: ["*"]`，Cowork 沙箱内 Web Fetch（访问外部 URL 获取内容）开箱即用，不再被沙箱拦截。

> 注：Web Search 需要 Anthropic 官方订阅，3P 模式下暂不可用。

### 配置安全性增强

- **不覆盖用户设置**：配置落盘采用 read-modify-write 模式，不会重置你在 Claude Desktop 里手动调过的 UI 偏好（sidebar 模式、快捷键等）
- **回滚更安全**：`--revert` 只清空 enterpriseConfig 字段，保留 preferences 等其他内容，不删整个文件
- **去除多余字段**：不再写入 `deploymentOrganizationUuid`，由 app 自行管理身份，减少配置冲突风险

### 白屏修复（重大）

4/28 当时的白屏修复是从 `defaults write` plist 迁移到 `~/Library/Application Support/Claude-3p/claude_desktop_config.json`。5/8 之后，Claude Desktop 1.6259.x 的当前主路径已更新为 `~/Library/Application Support/Claude-3p/configLibrary/`。旧 plist 路径继续废弃，`claude_desktop_config.json` 只作为旧兼容/偏好载体。

---

### 改动文件清单

| 文件 | 改动 |
|---|---|
| `scripts/install_cowork_config.py` | 4/28 版本：write_json_config() read-modify-write；cmd_revert() 清空而非删文件；build_target() 去掉 deploymentOrganizationUuid、加 coworkEgressAllowedHosts；ENTERPRISE_KEYS 同步 |
| `references/cowork_provisioning.md` | 4/28 版本记录了 configLibrary 身份锚结论；5/8 版本已更新为 configLibrary active config 主路径 |
| `SKILL.md` | 4/28 版本记录了 read-modify-write + 不碰 configLibrary；5/8 版本已更新为写 configLibrary active config |
