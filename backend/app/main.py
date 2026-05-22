"""FastAPI application entry."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .api.v1 import api_router
from .core.config import get_settings
from .core.errors import APIError, ErrorCode
from .seed.runner import bootstrap

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Conservative security headers for all responses.

    Avoid setting CSP here because the SPA mounts in-line script for fast
    initial paint; tightening CSP needs a separate audit. The headers below
    are universally safe for an internal data tool.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(self), camera=()")
        # Only emit HSTS over HTTPS (avoid the dev-localhost 6-month lock-in).
        if request.url.scheme == "https":
            h.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .services import scheduler_svc

    log.info("ICE backend starting up; running seed bootstrap…")
    await bootstrap()
    scheduler_svc.start_loop()
    log.info("ICE backend ready (scheduler loop active)")
    try:
        yield
    finally:
        scheduler_svc.stop_loop()


app = FastAPI(title="ICE Data Workbench v3 API", version="3.0.0", lifespan=lifespan)

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


@app.exception_handler(APIError)
async def _api_error_handler(_: Request, exc: APIError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())


@app.exception_handler(StarletteHTTPException)
async def _http_handler(_: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code * 100 + 1,
            "message": str(exc.detail),
            "error_code": ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else "HTTP_ERROR",
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def _fallback_handler(_: Request, exc: Exception):
    log.exception("unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "code": 50001,
            "message": str(exc),
            "error_code": ErrorCode.INTERNAL_ERROR,
            "data": None,
        },
    )


@app.get("/api/v1/health")
async def health():
    return {"code": 0, "message": "success", "data": {"status": "ok", "version": "3.0.0"}}


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

    @app.get("/", include_in_schema=False)
    async def _spa_root():
        return FileResponse(_index_path, headers=_NO_CACHE_HEADERS)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        # API 路由已在前面注册；这里只接未命中任何 API 的 GET。
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
