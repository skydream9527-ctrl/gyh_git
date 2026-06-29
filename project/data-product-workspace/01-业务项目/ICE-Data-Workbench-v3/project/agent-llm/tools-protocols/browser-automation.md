# 浏览器自动化：Playwright vs Computer Use

> Agent 接触互联网的两种主流方式：**Playwright** 是工具（你写代码控制它），**Computer Use** 是 Agent（LLM 直接看屏幕、控制鼠标键盘）。它们解决不同问题，工程上要分层使用。本文还覆盖 Browser-Use / Skyvern 等相关方案。

---

## 一、把两者放在同一坐标系

很多人混淆这两个。**完全不是同类产品**。

```
Playwright              Computer Use
─────────────────       ─────────────────
浏览器自动化框架         多模态 Agent 能力
你写代码控制它           LLM 直接看屏幕、控制鼠标键盘
DOM 级操作              像素级操作（视觉）
确定性                  概率性（LLM 决策）
快                      慢
便宜                    贵
封装好的 API            没有 API，靠"看"
```

**Playwright 是工具，Computer Use 是 Agent**。

---

## 二、Playwright 的工作方式

```python
await page.goto("https://example.com")
await page.click("button.submit")    # 用 CSS selector 定位
await page.fill("#email", "...")     # 用 ID 定位
text = await page.locator("h1").text_content()
```

需要你**精确知道页面的 DOM 结构**：
- 这个按钮的 selector 是什么
- 这个输入框的 ID 是什么
- 这个表的第几行第几列

**优势**：快、稳、便宜（不需要 LLM 决策）。

**劣势**：
- ❌ 改版即崩：网站改个 class name，你的脚本就废了
- ❌ 视觉信息抓不到：图表里的数据、Canvas 渲染的东西
- ❌ 难处理"看起来明显但 DOM 难找"的元素
- ❌ 不会"理解"页面：登录后页面跳转流程、动态弹窗

---

## 三、Computer Use 的工作方式

```python
# 不需要写脚本，给一个目标
task = "去 Bloomberg 查 Apple 最近一年股价图，截图保存"

# Claude 自己看截图、自己决定鼠标键盘操作
agent = ComputerUseAgent(model="claude-sonnet-4-6")
result = await agent.run(task)
```

它内部循环：
```
1. Screenshot (截图当前桌面)
   ↓
2. Claude 看截图 → 决定下一步操作
   ↓
3. 输出工具调用：
   - mouse_click(x=347, y=128)
   - type_text("apple inc")
   - key_press("Enter")
   - scroll(direction="down", amount=500)
   ↓
4. 系统执行操作
   ↓
5. 再次截图 → 回到步骤 2
```

**核心**：Claude 像人类一样**看屏幕**做决定，不依赖 DOM。

---

## 四、五个 Playwright 完全做不到的场景

### 场景 1：跨应用工作流

任务："从 Excel 读数据 → 在 Bloomberg 查证 → 在 Notion 写报告"

```
Playwright:    ❌ 只能控制浏览器
Computer Use:  ✅ 操作整个桌面（Excel app + 浏览器 + Notion app）
```

这是 Computer Use **最大的差异化**——不局限于浏览器。

### 场景 2：处理"看起来对但 DOM 没有"的元素

```
Canvas 渲染的图表（金融工具大量用）
PDF 嵌入的文档
WebGL 3D 应用
IFrame 跨域
```

Playwright 看 DOM = 啥都没有。Computer Use 看像素 = 跟人一样能"看到"。

### 场景 3：动态变化的网站

vendor 网站经常改 class name、改 selector。
- Playwright 脚本改完两周后大概率挂掉
- Computer Use 不依赖 selector，**它每次都是"看一眼现在长什么样"**

### 场景 4：登录流程的复杂分支

```
Bloomberg 登录可能遇到：
- 正常登录 → 主页
- 触发 2FA → 输验证码 → 主页  
- 触发 captcha → 等用户解 → 主页
- session 过期 → 强制改密码 → 主页
- 提示订阅过期 → 续费页面
```

Playwright 写所有分支 = 写到吐。Computer Use 看到啥处理啥。

### 场景 5：第一次接触的 UI

任务："去这个我没见过的 SaaS 工具上导出数据"

Playwright：你得先打开浏览器调研一遍 DOM 结构再写脚本。
Computer Use：直接给目标，它自己摸索。

---

## 五、Computer Use 的真实代价

### 代价 1：慢

```
Playwright:    单次操作 50-200ms
Computer Use:  单次操作 3-15 秒
                （要截图 + 上传 + LLM 看 + LLM 决策 + 执行）
```

完成"登录 + 搜索 + 截图"这种 5 步任务，Playwright 几秒，Computer Use 一分钟+。

### 代价 2：贵

每一步都要：
- 截图 → 转 base64 → 喂 LLM（图像 token 很多，~1500 token/张）
- LLM 决策 → 输出工具调用

**单步成本 ~$0.01-0.05**。一次任务 50 步 = $0.5-2.5。

对比 Playwright：电费而已。

### 代价 3：不稳定

Computer Use 是**概率性**的，会犯人类不会犯的错：
- 点错按钮（坐标算错）
- 误读数字（视觉模型误识）
- 卡在循环里（一直点同一个按钮）

需要 retry 机制 + 上限保护 + 人工兜底。

### 代价 4：调试地狱

Playwright 出错：看 selector 错在哪，立刻知道。
Computer Use 出错：看 trace（一堆截图）→ 猜是什么导致 LLM 误判 → 改 prompt → 再试。

---

## 六、真实的能力边界（Anthropic 自己披露）

Anthropic 在 Computer Use 发布时**罕见地**坦诚了局限：

> "Computer use is still experimental—at times cumbersome and error-prone."

他们公开的 OSWorld benchmark 数据：
- Claude 4.5 Sonnet: 50.0%
- Claude 4 Opus: 38.1%
- 人类基线: 72.4%

意思是：在 OSWorld 这个"通用桌面任务"评测上，**Claude 完成度大约是人类的 70%**。

实际跑你会发现：
- 简单任务（登录 + 找东西）：~80% 成功
- 复杂任务（跨应用 + 多步推理）：~30% 成功
- 长任务（30 步以上）：累积错误率高

---

## 七、实战决策框架

### 用 Playwright 的场景

```
✅ 任务确定且重复（每天抓同一个网站）
✅ 性能/成本敏感（高频、大量）
✅ 网站结构稳定
✅ 只需要 DOM 信息
✅ 不需要登录或登录已自动化
```

99% 的"研究 Agent 抓网页"是这种场景。**首选 Playwright**。

### 用 Computer Use 的场景

```
✅ 跨应用任务（不只是浏览器）
✅ 网站频繁变化或不可控
✅ 需要"看图表/截图"（视觉信息）
✅ 一次性任务（不值得写 Playwright 脚本）
✅ 用户授权操作（"帮我订机票"这种）
```

### 混合策略（最优）

```
┌──────────────────────────────────────────┐
│  第一层：Playwright (80% 任务)            │
│  - 标准网页抓取                           │
│  - 已知站点的标准流程                     │
└──────────────────────────────────────────┘
              │ 失败时降级
              ▼
┌──────────────────────────────────────────┐
│  第二层：Computer Use (20% 任务)          │
│  - 跨应用                                 │
│  - 视觉理解                               │
│  - 处理 Playwright 失败的情况              │
└──────────────────────────────────────────┘
```

实战代码骨架：

```python
async def fetch_with_fallback(url: str, task_description: str) -> dict:
    # 尝试 Playwright
    try:
        result = await playwright_fetch(url)
        if result["text"] and len(result["text"]) > 500:
            return {"via": "playwright", "data": result}
    except Exception as e:
        log.warning(f"Playwright failed: {e}")
    
    # 降级到 Computer Use
    log.info("Falling back to Computer Use")
    result = await computer_use_agent.run(
        f"Open {url} and extract: {task_description}"
    )
    return {"via": "computer_use", "data": result}
```

---

## 八、Computer Use vs Browser Use vs Skyvern

容易混。三者关系：

| | Anthropic Computer Use | Browser Use | Skyvern |
|---|---|---|---|
| 范围 | 整个桌面 | 仅浏览器 | 仅浏览器 |
| 模型 | Claude 4 系列 | 任意 LLM | 任意 LLM |
| 视觉 | 全屏截图 | 浏览器截图 | 浏览器截图 |
| API | Anthropic 官方 | 开源库 | 商业服务 |
| 强项 | 跨应用 | 易上手 | 企业级 |
| 适合 | 通用桌面 | 浏览器自动化 | RPA 替代 |

**Browser Use** 是社区开源的"轻量版 Computer Use"，只针对浏览器。如果你只需要**浏览器交互**，它通常比 Computer Use 更划算（速度快、成本低）。

**Skyvern** 是商业产品，专门做"用 Agent 替代传统 RPA"。

---

## 九、Playwright 服务化（推荐生产架构）

跑一个常驻的 Playwright 服务，subagent 通过 API 调：

```
[Playwright Service (常驻)]
  ↑    ↑    ↑
  │    │    │
researcher-1   researcher-2   researcher-3
```

```python
# browser_service.py
from playwright.async_api import async_playwright
from fastapi import FastAPI
from pydantic import BaseModel

class FetchRequest(BaseModel):
    url: str
    wait_for: str | None = None  # CSS selector
    actions: list[dict] = []     # [{type: "click", selector: "..."}]
    auth_profile: str | None = None  # 用哪个用户的 cookie

class FetchResult(BaseModel):
    url: str
    final_url: str  # redirects
    html: str
    text: str       # extracted readable text
    screenshot_b64: str | None = None
    
app = FastAPI()
playwright_ctx = None
browser_pool = {}

@app.on_event("startup")
async def startup():
    global playwright_ctx
    playwright_ctx = await async_playwright().start()
    browser_pool["default"] = await playwright_ctx.chromium.launch(headless=True)

@app.post("/fetch", response_model=FetchResult)
async def fetch(req: FetchRequest):
    browser = browser_pool["default"]
    
    # 选择 context（不同 auth_profile 用不同 cookie）
    if req.auth_profile and req.auth_profile != "default":
        ctx = await browser.new_context(
            storage_state=f"./auth_profiles/{req.auth_profile}.json"
        )
    else:
        ctx = await browser.new_context()
    
    page = await ctx.new_page()
    try:
        await page.goto(req.url, wait_until="networkidle", timeout=30000)
        
        if req.wait_for:
            await page.wait_for_selector(req.wait_for, timeout=10000)
        
        for action in req.actions:
            if action["type"] == "click":
                await page.click(action["selector"])
            elif action["type"] == "scroll":
                await page.evaluate("window.scrollBy(0, 1000)")
            elif action["type"] == "fill":
                await page.fill(action["selector"], action["value"])
            await page.wait_for_load_state("networkidle", timeout=5000)
        
        html = await page.content()
        text = await page.evaluate("() => document.body.innerText")
        screenshot = None
        if req.actions:
            screenshot_bytes = await page.screenshot()
            import base64
            screenshot = base64.b64encode(screenshot_bytes).decode()
        
        return FetchResult(
            url=req.url,
            final_url=page.url,
            html=html[:200000],
            text=text[:50000],
            screenshot_b64=screenshot,
        )
    finally:
        await ctx.close()
```

启动：
```bash
uvicorn browser_service:app --port 8801 --workers 1
```

---

## 十、集成到 LangGraph 研究 Agent

### Tool 包装

```python
# tools/browser.py
import httpx
from langchain_core.tools import tool

BROWSER_SERVICE_URL = "http://localhost:8801"

@tool
async def browser_fetch(
    url: str, 
    wait_for: str | None = None,
    auth_profile: str | None = None,
) -> dict:
    """Fetch a URL using a real browser. 
    Use when:
    - Site is JavaScript-heavy (SPA)
    - Site requires login (specify auth_profile)
    - Site has dynamic content
    
    For static HTML pages, prefer simple_fetch (faster).
    """
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{BROWSER_SERVICE_URL}/fetch",
            json={"url": url, "wait_for": wait_for, "auth_profile": auth_profile}
        )
        return resp.json()


@tool  
async def browser_interact(
    url: str,
    actions: list[dict],
    extract_after: str | None = None,
) -> dict:
    """Fetch and interact with a page (click, scroll, fill).
    Use when you need to:
    - Click 'Load More' to see all content
    - Fill a search box
    - Navigate multi-step flows
    """
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{BROWSER_SERVICE_URL}/fetch",
            json={
                "url": url, 
                "actions": actions,
                "wait_for": extract_after,
            }
        )
        return resp.json()
```

### 在 researcher subgraph 里使用

修改 `fetch_pages_node`：

```python
async def fetch_pages_node(state: ResearcherState) -> dict:
    fetched = []
    seen_urls = set()
    
    for r in state["search_results"][:15]:
        if r["url"] in seen_urls:
            continue
        seen_urls.add(r["url"])
        
        # 决定用哪种 fetch
        fetcher = pick_fetcher(r["url"])
        
        try:
            if fetcher == "browser":
                content = await browser_fetch.ainvoke({
                    "url": r["url"],
                    "auth_profile": _auth_profile_for(r["url"]),
                })
                fetched.append({
                    "url": r["url"], 
                    "content": content["text"][:8000],
                    "via": "browser",
                })
            else:
                content = await simple_fetch.ainvoke({"url": r["url"]})
                fetched.append({
                    "url": r["url"],
                    "content": content[:8000],
                    "via": "simple",
                })
        except Exception as e:
            log_error(r["url"], e)
            continue
    
    return {"fetched_pages": fetched}


def pick_fetcher(url: str) -> str:
    """Routing: 哪些站用 browser，哪些用 simple_fetch"""
    BROWSER_REQUIRED_DOMAINS = {
        "bloomberg.com", "ft.com", "wsj.com",
        "twitter.com", "x.com",
        "linkedin.com",
        "scholar.google.com",
    }
    SPA_HINT_DOMAINS = {
        "notion.so", "airtable.com",
    }
    
    domain = extract_domain(url)
    if domain in BROWSER_REQUIRED_DOMAINS or domain in SPA_HINT_DOMAINS:
        return "browser"
    return "simple"


def _auth_profile_for(url: str) -> str | None:
    domain = extract_domain(url)
    if "bloomberg.com" in domain:
        return "bloomberg"
    if "wsj.com" in domain:
        return "wsj"
    return None
```

---

## 十一、鉴权（Auth Profile）的工程化

最大的实战难点：**怎么管理多个站点的 cookie**。

### 一次性登录，永久使用

```python
# auth_setup.py — 手动跑一次
import asyncio
from playwright.async_api import async_playwright

async def setup_bloomberg():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示窗口让你登录
        ctx = await browser.new_context()
        page = await ctx.new_page()
        await page.goto("https://www.bloomberg.com/account/signin")
        
        print("请在浏览器登录，登录完成按 Enter...")
        input()
        
        # 保存 cookie + storage
        await ctx.storage_state(path="./auth_profiles/bloomberg.json")
        await browser.close()
        print("✅ 已保存到 auth_profiles/bloomberg.json")

asyncio.run(setup_bloomberg())
```

跑一次，cookie 保存到文件。后续 Playwright service 从文件加载，**自动以登录状态访问**。

### Cookie 失效检测

```python
@app.post("/fetch")
async def fetch(req: FetchRequest):
    # ... 
    
    # 检查是否被踢回登录页
    if "signin" in page.url.lower() or "login" in page.url.lower():
        raise HTTPException(status_code=401, 
                           detail=f"Auth profile '{req.auth_profile}' expired")
```

返回 401 后 Lead Researcher 知道这个数据源没了，可以走备选。

---

## 十二、浏览器对成本的影响

| | simple_fetch | Playwright fetch |
|---|---|---|
| 单次延迟 | ~1 秒 | ~3-10 秒 |
| 单次成本 | 几乎为零 | 服务器 CPU + 内存 |
| 单服务并发 | 无限（HTTP client） | ~5-10（chromium 限制） |
| 失败率 | 高（被 block） | 低 |

**实战**：80% 的 URL 用 simple_fetch 就行，**只对 routing 命中的高价值站点用 browser**。

---

## 十三、一个常被忽略的坑：浏览器指纹

很多站会检测"是不是 headless chromium"然后 block。Playwright 默认就会被检测到。

修复：用 `playwright-stealth`：

```python
from playwright_stealth import stealth_async

page = await ctx.new_page()
await stealth_async(page)  # 注入反检测脚本
await page.goto(url)
```

**意义**：能把成功率从 60% 提到 95%+。

---

## 十四、接到我们研究 Agent 的实战方案

回到我们的研究 Agent，**不需要全面上 Computer Use**，分层就好：

```python
# tools/web.py
async def smart_fetch(url: str, hint: str = None) -> dict:
    """智能抓取，三层 fallback"""
    
    # Layer 1: simple_fetch (80% 用例)
    try:
        result = await simple_fetch(url)
        if _quality_ok(result):
            return result
    except Exception:
        pass
    
    # Layer 2: Playwright (15% 用例：JS 渲染、登录)
    try:
        result = await playwright_fetch(url, auth_profile=_pick_profile(url))
        if _quality_ok(result):
            return result
    except Exception:
        pass
    
    # Layer 3: Computer Use 或 Browser Use (5% 用例：极端情况)
    if hint:  # 只有有明确目标时才用
        return await browser_use_fetch(url, task=hint)
    
    raise FetchError(f"Could not fetch {url}")


def _quality_ok(result) -> bool:
    """检测抓取质量"""
    text = result.get("text", "")
    return (
        len(text) > 500 and
        "captcha" not in text.lower() and
        "please enable javascript" not in text.lower() and
        "access denied" not in text.lower()
    )
```

**实战经验**：
- 第一层覆盖 80% URL，几乎免费
- 第二层覆盖 95%（含登录站点）
- 第三层只有特殊任务才触发

---

## 十五、Computer Use 的未来（推测）

当前 Computer Use 是 **2025 年 Anthropic 押注的方向**。趋势是：

- **更便宜**（图像 token 优化、专用模型）
- **更快**（screenshot diff 而非全图、动作 batch）
- **更准**（专门 RL 训练的"桌面操作 model"）

如果按 OpenAI Deep Research 那种特化模型的路径，**未来 1-2 年 Computer Use 的能力会接近人类水平**——这意味着：很多今天必须写 Playwright 脚本的任务，未来可以直接交给 Computer Use。

但**今天不要押宝**。今天的最优解是分层组合。

---

## 十六、扩展阅读

- [../agents/research-agent-architecture.md](../agents/research-agent-architecture.md) —— 研究 Agent 中的 web fetch 集成
- [../production/langgraph-research-agent-impl.md](../production/langgraph-research-agent-impl.md) —— LangGraph 中的浏览器工具调用
- [function-calling.md](function-calling.md) —— 工具调用基础
- [mcp.md](mcp.md) —— MCP 协议（可以把浏览器服务包成 MCP server）
