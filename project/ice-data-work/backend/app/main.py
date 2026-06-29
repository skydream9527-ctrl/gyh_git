from __future__ import annotations

import contextlib
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import APIError, ErrorCode
from app.seed import runner as seed_runner


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # G3：确保四层空间顶层目录存在 + 种子
    seed_runner.bootstrap()
    yield


app = FastAPI(title="ICE-DATA-WORK", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 统一错误信封 ----
@app.exception_handler(APIError)
async def _api_error(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.envelope())


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": str(exc.detail),
            "error_code": ErrorCode.NOT_FOUND.value
            if exc.status_code == 404
            else ErrorCode.BAD_REQUEST.value,
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": str(exc) or "internal error",
            "error_code": ErrorCode.INTERNAL.value,
            "data": None,
        },
    )


app.include_router(api_router)


# ---- 生产：单端口伺服前端 SPA（dist 存在时）----
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")
