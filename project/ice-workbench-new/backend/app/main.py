"""FastAPI application entry."""
from __future__ import annotations

import logging
import os
import secrets
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .api.v1 import api_router
from .core.cli_path import widen_path_in_place
from .core.config import get_settings
from .core.deps import client_ip, require_admin
from .core.errors import APIError, ErrorCode
from .core.logging import access_log, setup_logging
from .core.middleware import get_rate_limit_info
from .seed.runner import bootstrap
from .services import event_log

setup_logging()
log = logging.getLogger("ice")


# Documented public defaults — refuse to boot with these in any deployment
# scenario where credentials matter. Catches the "shipped the .env.example"
# class of mistake before it lands in prod.
_KNOWN_DEFAULT_SECRETS = {
    "dev-secret-please-change-me-32bytes",
    "change-me-please-32-bytes-min",
    "change-me-on-deploy-32-bytes-minimum-please",
    "change-me",
    "secret",
}


def _validate_security_settings(s) -> None:
    """Hard guard on launch. Refuse weak/default secrets when the deployment
    is anything other than a single-user local dev (Aegis-only, no Bearer)."""
    secret = s.ICE_SECRET_KEY or ""
    if secret in _KNOWN_DEFAULT_SECRETS or len(secret) < 32:
        log.error(
            "ICE_SECRET_KEY 不安全：默认值或长度 < 32 字节。"
            "请生成一个 >= 32 字节的随机密钥并写入 .env。"
            "参考：python -c 'import secrets;print(secrets.token_urlsafe(48))'"
        )
        raise RuntimeError(
            "ICE_SECRET_KEY must be set to a >= 32-byte random value (refusing to boot)"
        )

    origins = s.cors_origins_list
    if "*" in origins:
        log.warning(
            "ICE_CORS_ORIGINS 包含 '*'：CORS 通配符与 allow_credentials=True 不兼容，"
            "已自动将 allow_credentials 关闭。建议改成具体来源（逗号分隔）。"
        )

    if s.AEGIS_DEV_BYPASS_EMAIL:
        log.warning(
            "AEGIS_DEV_BYPASS_EMAIL 已启用 (%s)：任何携带 X-Dev-Bypass: 1 的请求都会被认作该用户。"
            "**仅可在本机开发环境使用，部署到 staging/prod 之前必须清空。**",
            s.AEGIS_DEV_BYPASS_EMAIL,
        )


# Built CSP. Audited against frontend/dist/index.html — the production SPA
# loads only its own /assets/*.{js,css} (same origin), Google Fonts CSS +
# fonts (third-party hosts), and connects to /api/* and /api/v1/ws/* (same
# origin). `'unsafe-inline'` for style-src is kept because React's inline
# `style=` attributes (used widely in the SPA) and `react-syntax-highlighter`
# need it; rendered markdown is sanitized by DOMPurify so XSS via inline style
# requires defeating that first. ws:/wss: explicit because CSP3's `'self'`
# does not cover ws-scheme URLs.
_CSP_PROD = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com data:; "
    "img-src 'self' data: blob:; "
    "media-src 'self' data: blob:; "
    "connect-src 'self' ws: wss:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """给每个 HTTP 请求分配 8 字符 request_id，写进 contextvar + 响应头。

    诊断时用户贴的 X-Request-Id 可以反查到这次请求触发的所有 events。
    若客户端已带 X-Request-Id 则尊重传入值，便于网关链路追踪。
    """

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or secrets.token_hex(4)
        token = event_log.request_id_var.set(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            event_log.request_id_var.reset(token)
        response.headers.setdefault("X-Request-Id", rid)
        # Access log: method, path, status, duration
        duration_ms = (time.perf_counter() - start) * 1000
        path = request.url.path
        # Skip noisy paths (health checks, static assets) from access log
        if not path.startswith("/assets") and path != "/api/v1/health":
            access_log.log_request(
                method=request.method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                client_ip=client_ip(request),
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers for all responses.

    The built SPA has no inline scripts, so a strict `script-src 'self'` is
    safe. Style stays `'unsafe-inline'` because React inline-style attributes
    are pervasive — DOMPurify protects rendered user markdown from script
    injection there.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(self), camera=()")
        h.setdefault("Content-Security-Policy", _CSP_PROD)
        # Only emit HSTS over HTTPS (avoid locking dev-localhost into HTTPS).
        # Behind a reverse proxy the X-Forwarded-Proto header reflects the
        # original scheme; trust it because the proxy is the one we want to
        # honor for HSTS decisions.
        scheme = (
            request.headers.get("x-forwarded-proto", "").lower()
            or request.url.scheme
        )
        if scheme == "https":
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """Defense-in-depth per-IP rate limit on /api/*.

    IMPORTANT — Per-worker limitation (no shared store):
      Counters live in each uvicorn worker's process memory. Under -w N the
      *effective* global cap is N × MAX_PER_WINDOW (worst case, perfect
      load balance). Example: 4 workers × 240/min = 960 req/min ceiling.
      There is NO cross-worker coordination — this is intentional to avoid
      external dependencies. For stricter global limiting, add a reverse-proxy
      rate limiter (nginx limit_req, Cloudflare, etc.) in front of uvicorn.

    Configuration:
      ICE_RATE_LIMIT_PER_MIN env var overrides MAX_PER_WINDOW (default 240).

    MAX_PER_WINDOW=240/60s gives 4 req/s sustained per worker — enough
    headroom for an SPA initial load (workspace mount fires ~15 requests,
    doubled by React StrictMode in dev), while still throttling a scraper
    that holds 4+ req/s for a full minute.

    Auth-specific limits in `rate_limit_svc` keep their own separate, much
    tighter counters and are not affected by this middleware.
    """

    WINDOW_SEC = 60.0
    MAX_PER_WINDOW = 240
    _MAX_KEYS = 4096
    _EVICT_TARGET = 3072

    def __init__(self, app):
        super().__init__(app)
        # OrderedDict so we can LRU-evict cheaply: every touched IP is moved
        # to the end; eviction pops from the front.
        self._by_ip: OrderedDict[str, deque[float]] = OrderedDict()

    def _evict_if_full(self) -> None:
        # 旧实现是 dict.clear()，在 unique-IP 洪水时会把所有合法计数也清零，
        # 等于把限速反向放大成"每 4096 次请求一次硬重置"。LRU 半量裁剪保住
        # 活跃 IP 的窗口，被裁掉的最坏情况是丢失部分历史样本。
        while len(self._by_ip) > self._EVICT_TARGET:
            self._by_ip.popitem(last=False)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Only gate JSON API. Static assets / SPA shell / WS upgrades are
        # not in scope. WS upgrades go through /api/v1/ws/* — exclude those
        # too because a long-lived stream shouldn't count against a per-min
        # request budget.
        if path.startswith("/api/") and not path.startswith("/api/v1/ws"):
            ip = client_ip(request)
            if ip:
                now = time.monotonic()
                cutoff = now - self.WINDOW_SEC
                dq = self._by_ip.get(ip)
                if dq is None:
                    dq = deque()
                    self._by_ip[ip] = dq
                else:
                    self._by_ip.move_to_end(ip)
                while dq and dq[0] < cutoff:
                    dq.popleft()
                if len(dq) >= self.MAX_PER_WINDOW:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "code": 42901,
                            "message": "请求过于频繁，请稍后再试",
                            "error_code": "RATE_LIMITED",
                            "data": None,
                        },
                        headers={"Retry-After": str(int(self.WINDOW_SEC))},
                    )
                dq.append(now)
                if len(self._by_ip) > self._MAX_KEYS:
                    self._evict_if_full()
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services import scheduler_svc

    log.info("ICE backend starting up; running seed bootstrap…")
    widen_path_in_place()
    await bootstrap()
    scheduler_svc.start_loop()
    log.info("ICE backend ready (scheduler loop active)")
    try:
        yield
    finally:
        scheduler_svc.stop_loop()


# OpenAPI / Swagger UI / ReDoc are admin-only. Anonymous probes hit 401
# instead of receiving a 150 KB schema dump that maps every endpoint and
# its parameters. We disable the default auto-mounted routes and re-add
# our own gated copies below.
app = FastAPI(
    title="ICE Data Workbench v3 API",
    version="3.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

settings = get_settings()
_validate_security_settings(settings)

# CORS: '*' with credentials is rejected by browsers anyway — degrade
# gracefully rather than 500-ing every preflight.
_origins = settings.cors_origins_list
_allow_credentials = "*" not in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GlobalRateLimitMiddleware)
# Outermost — runs first on request, last on response. 这样 request_id 在所有
# 处理链路（rate limit / CORS / 异常处理器）里都可见，并且响应一定带上头。
app.add_middleware(RequestIdMiddleware)


# ------------------------------------------------------------------
# OpenAPI — admin only. Custom routes since FastAPI's defaults are off.
# ------------------------------------------------------------------
@app.get("/openapi.json", include_in_schema=False)
async def _openapi(_: dict = Depends(require_admin)):
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


@app.get("/docs", include_in_schema=False)
async def _swagger_ui(_: dict = Depends(require_admin)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} — Swagger")


@app.get("/redoc", include_in_schema=False)
async def _redoc(_: dict = Depends(require_admin)):
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} — ReDoc")


def _extract_task_id(request: Request) -> str | None:
    """从路径参数 / 查询串里捞 task_id，给异常 emit 时定位归属。"""
    try:
        params = request.path_params or {}
        if "task_id" in params:
            return str(params["task_id"])
        if "tid" in params:
            return str(params["tid"])
    except Exception:
        pass
    try:
        return request.query_params.get("task_id")
    except Exception:
        return None


@app.exception_handler(APIError)
async def _api_error_handler(request: Request, exc: APIError):
    rid = event_log.request_id_var.get()
    envelope = exc.to_envelope()
    envelope["request_id"] = rid
    # 业务异常一般是已知错误码，仅 ≥500 才落 events 当作运维信号；
    # 4xx 太常见（VALIDATION / PERMISSION 等），不噪。
    if exc.status_code >= 500:
        event_log.emit(
            task_id=_extract_task_id(request),
            source="api",
            event_type="api_error",
            level="ERROR",
            request_id=rid,
            code=exc.error_code,
            message=f"{request.method} {request.url.path} → {exc.status_code} {exc.message}",
            payload={"status": exc.status_code, "biz_code": exc.biz_code},
        )
    return JSONResponse(status_code=exc.status_code, content=envelope)


@app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException):
    rid = event_log.request_id_var.get()
    if exc.status_code >= 500:
        event_log.emit(
            task_id=_extract_task_id(request),
            source="api",
            event_type="http_error",
            level="ERROR",
            request_id=rid,
            code="HTTP_ERROR",
            message=f"{request.method} {request.url.path} → {exc.status_code} {exc.detail}",
            payload={"status": exc.status_code},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code * 100 + 1,
            "message": str(exc.detail),
            "error_code": ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else "HTTP_ERROR",
            "data": None,
            "request_id": rid,
        },
    )


@app.exception_handler(Exception)
async def _fallback_handler(request: Request, exc: Exception):
    log.exception("unhandled exception")
    rid = event_log.request_id_var.get()
    event_log.emit(
        task_id=_extract_task_id(request),
        source="api",
        event_type="unhandled_exception",
        level="ERROR",
        request_id=rid,
        code="INTERNAL_ERROR",
        message=f"{request.method} {request.url.path}: {type(exc).__name__}: {str(exc)[:300]}",
    )
    return JSONResponse(
        status_code=500,
        content={
            "code": 50001,
            "message": str(exc),
            "error_code": ErrorCode.INTERNAL_ERROR,
            "data": None,
            "request_id": rid,
        },
    )


@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health():
    return {"code": 0, "message": "success", "data": {"status": "ok", "version": "3.0.0"}}


# robots.txt — explicit Disallow keeps the SPA shell out of search indexes.
# Otherwise the previous behavior was a SPA fallback returning the app shell,
# which Google would index under the title alone (information disclosure).
_ROBOTS_TXT = (
    "User-agent: *\n"
    "Disallow: /\n"
)


@app.api_route("/robots.txt", methods=["GET", "HEAD"], include_in_schema=False)
async def robots_txt():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(_ROBOTS_TXT, headers={"Cache-Control": "public, max-age=86400"})


app.include_router(api_router)


# ------------------------------------------------------------------
# 生产环境：同端口伺服前端 SPA dist
# ------------------------------------------------------------------
# 如果 frontend/dist/ 存在（`npm run build` 产出），挂载为静态文件并对
# 未命中的路由回落到 index.html（SPA history-mode 支持）。部署 Linux /
# 公网时只暴露后端端口（默认 8000），不用再单独跑 vite dev server，
# 也不再有前后端跨域。开发模式下这段不生效，照样用 vite :5173 + proxy。
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").exists():
    # /assets/... 等静态资源
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    _index_path = _FRONTEND_DIST / "index.html"
    # index.html 引用的是 hash 化的 /assets/*.js 和 *.css，所以浏览器缓存
    # index.html 是错的（拿到旧 hash 引用，永远拉不到新 build）。强制
    # 浏览器每次都校验 index.html 是否有更新；新 build 后自动失效旧缓存。
    _NO_CACHE_HEADERS = {"Cache-Control": "no-cache, must-revalidate"}

    # Accept HEAD too — health checks / CDN probes / link checkers commonly
    # use it. FastAPI's `@app.get` rejects HEAD with 405 by default, so
    # switch to `api_route` and list both methods.
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def _spa_root():
        return FileResponse(_index_path, headers=_NO_CACHE_HEADERS)

    @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # API 路由已在前面注册；这里只接未命中任何 API 的 GET/HEAD。
        # /api/* 未命中的路径返回 JSON 404（交给 exception_handler）。
        if full_path.startswith("api/"):
            raise StarletteHTTPException(status_code=404, detail="Not Found")
        # 真实静态文件（favicon、manifest 等）优先读 dist 下的对应文件
        candidate = _FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_index_path, headers=_NO_CACHE_HEADERS)

    log.info("Serving frontend SPA from %s", _FRONTEND_DIST)
else:
    log.info("frontend/dist/ not found — run `npm run build` for single-port deploy")
