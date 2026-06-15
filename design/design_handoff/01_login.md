# 01 · 登录页（Login）

> **改造重点**：**去掉「后台/Dev」感，做更产品化的视觉**。当前页给人「内部工具」的感觉，希望改造后能传达「专业的数据工作台 / 可信任的企业产品」气质。

源码：[LoginPage.tsx](../frontend/src/pages/login/LoginPage.tsx) · [Login.css](../frontend/src/pages/login/Login.css)

参考截图：见 `screenshots/01_login-*.png`（4 个状态）

---

## 当前 IA

```
┌────────────────────────────────────────────────────────────┐
│  [bg grid]  [orb 1]  [orb 2]   ← 装饰层（被批评：太花/太 Dev）│
│                                                            │
│   ┌──────────────────────────────────────────────────┐    │
│   │  LEFT 品牌区             │  RIGHT 表单区          │    │
│   │  ─────────────           │  ─────────────         │    │
│   │  🔷 ICE Data Workbench   │  登录                  │    │
│   │  AI 数据工作流工作台      │  两种登录方式任选其一   │    │
│   │                          │                        │    │
│   │  [Tab: 米盾 | 账号密码]  │                        │    │
│   │  ↓                       │                        │    │
│   │  用户:上周新版本留存…    │  [当前 Tab 内容]        │    │
│   │     ↓                    │                        │    │
│   │  ⚡ Tool: SQL→Skill→图表 │                        │    │
│   │     ↓                    │                        │    │
│   │  📊 Agent: D7 留存+5.6pp │                        │    │
│   └──────────────────────────────────────────────────┘    │
│                                                            │
│  「→ 」     ↑ 卡片是 2 列 grid                             │
│  「↓ 」     ↑ 左列是 illustrative 区域，右列是表单         │
│  ←─── viewport（≥1024px 桌面 / ≤768px 移动堆叠）────→   │
└────────────────────────────────────────────────────────────┘
```

## 状态变体（共 4 种）

| 状态 | 触发条件 | 主要内容 |
| --- | --- | --- |
| **A. Aegis 米盾未识别** | 未通过米盾代理域名访问 / 本地无 dev_bypass | 一段说明 + `🔁 重新尝试` 按钮 |
| **B. 账号密码登录** | 米盾不可用 / 用户切到密码 Tab | 账号 + 密码 + 「登录」按钮 +（可选）「去注册」链接 |
| **C. 账号密码注册** | 后端 `open_register_enabled=true` 且用户切到注册 | 账号 + 姓名 + 密码 + 确认密码 + 「创建账号」按钮 |
| **D. 注册待审批** | 注册接口返回成功后停留 | 黄色提示 + 申请人信息 + 「回到登录页 / 再申请一个」 |

## 现有组件清单

- [LoginPage.tsx](../frontend/src/pages/login/LoginPage.tsx) — 单文件页面，4 状态全部内联
- [Login.css](../frontend/src/pages/login/Login.css) — 所有视觉
- 依赖的全局：[tokens.css](../frontend/src/styles/tokens.css)
- 业务调用：
  - `authApi.methods()` → `{ aegis_enabled, password_enabled, open_register_enabled }`
  - `authStore.bootstrapMe()` → 米盾自动识别
  - `authStore.login(email, pwd)` / `authStore.register(email, name, pwd)`
  - `sysApi.toggles()` → 全局开关（包括 `feishu_enabled`）

## 改造目标

**做**：

1. **更产品化的视觉气质**，参考 Linear / Anthropic claude.ai / NotebookLM 的克制感
2. 左列从「内部循环动画」改成**对外的产品价值表达** — 例如：
   - 一句话产品定位 + 一两个真实数据样例（脱敏）
   - 或一组可信背书（团队/技术栈/数据规模），不要 emoji 列表
3. **米盾 / 账号密码 Tab** 切换的视觉级别要降权 — 当前两个 Tab 视觉权重相当，但米盾才是主入口（企业内部 90% 用户走米盾），应该是「米盾大按钮 + 账号密码作为次级折叠选项」的关系
4. 注册待审批状态（D）改成**正向的等待态** — 现在是黄色 warning，看起来像出错；应该是 info / 中性 + 一点点正向暗示（「我们已通知管理员」之类）
5. 一定要给出 dark + light 双主题方案

**不做**：

- 不要参考 Ant Design / TDesign 后台模板
- 不要 emoji 占位（🛡 🔑 ⚡ 📊 这些应该用图标库或自定义 SVG）
- 不要装饰性的 grid bg / orb 渐变球（当前的 `login-bg-grid` + `login-orb` 是「Dev 感」主因之一）
- 不要把表单变得更花哨 — 表单本身越少越好

## 不变量（不能破坏的契约）

- 4 个状态的转换逻辑必须完全保留：A/B/C/D 切换、`?logout=1` query 行为、`submittedForApproval` 停留态
- 必须保留「米盾自动识别 → 自动跳 dashboard」的体验：用户访问页面后，如果 `bootstrapMe()` 成功，立刻跳转，不要 1 秒 splash
- 表单字段不能改名（`email` / `name` / `password` / `confirm`）
- 客户端密码强度规则保留：≥10 位 + 大小写/数字/符号 3 类 + ≤128 位
- 客户端登录失败软锁（5 分钟内 5 次）保留 — 提示不要冲淡其严肃性
- 所有错误反馈走 `pushToast()`，不要用 inline error 字段
- 移动端（≤768px）整张卡片堆叠成单列，左列内容降权或折叠
- a11y：`role="tablist"`、`aria-selected`、`autoComplete="username|current-password|new-password|name"` 全部保留

## 给 Claude Design 的 Prompt 模板

```
Project context: ICE Data Workbench — an AI data analysis workbench
inspired by NotebookLM. Designed for business analysts and growth teams.
The brand pack is in 00_brand_pack.md (already pasted above).

Task: Redesign the login page. Current page feels like an internal
"developer tool" — we want a more product-grade, enterprise-trustable
look. References: Linear, Anthropic claude.ai, NotebookLM.

The page must support 4 states:
  A. Aegis (corporate SSO) not recognized — show retry button
  B. Username/password login
  C. Open registration (only when backend allows)
  D. Registration pending approval (positive waiting state, not an error)

The Aegis path is the primary login (90% of users). The password
path is secondary — visually demote it (e.g. a small "use account
password instead" link below a big Aegis button).

Provide BOTH dark and light themes. Mobile (≤768px) stacks to single
column; the brand/illustration column should collapse or demote, not
disappear.

Things to avoid:
  - emoji icons (🛡 🔑 ⚡ 📊) — replace with a coherent icon set
  - decorative grid background + glowing orbs (current page has both,
    they're the main "dev tool" smell)
  - admin dashboard look (Ant Design Pro / TDesign Admin style)

Hard constraints:
  - Form fields keep their semantic names: email/username, name,
    password, confirm
  - Pending-approval state (D) is informational, not an error
  - Layout must work at 1024px+, 1280px (default), and ≤768px mobile

Deliverables: 4 state designs × 2 themes = 8 frames. Plus a mobile
variant for each state (4 frames). Total 12 frames.
```
