"""统一错误信封：{code, message, error_code, data}。

服务端 raise APIError；main.py 的异常处理器把所有异常转成该结构。
不要直接返回 HTTPException。
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    OK = "OK"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL = "INTERNAL"
    # 集成降级
    FEISHU_NOT_CONFIGURED = "FEISHU_NOT_CONFIGURED"
    KYUUBI_NOT_CONFIGURED = "KYUUBI_NOT_CONFIGURED"
    LLM_KEY_MISSING = "LLM_KEY_MISSING"
    # 治理
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CROSS_SPACE_DENIED = "CROSS_SPACE_DENIED"


class APIError(Exception):
    def __init__(
        self,
        status: int,
        error_code: ErrorCode = ErrorCode.BAD_REQUEST,
        message: str = "",
        data: Any = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.message = message or error_code.value
        self.data = data

    def envelope(self) -> dict:
        return {
            "code": self.status,
            "message": self.message,
            "error_code": self.error_code.value,
            "data": self.data,
        }


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 200, "message": message, "error_code": ErrorCode.OK.value, "data": data}
