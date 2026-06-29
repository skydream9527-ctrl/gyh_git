"""失败复盘：错误结构化分类（材料一/原型 approvals 失败复盘）。

把原始错误/error_code 映射为 {error_type, recoverable, suggested}，
供看板"报错"卡与 Approvals"失败复盘"展示，指导下一步（重试/缩小范围/换 Agent）。
"""
from __future__ import annotations

# error_code / 关键词 → 分类规则
_RULES: list[tuple[tuple[str, ...], dict]] = [
    (("timeout", "timed out", "超时"),
     {"error_type": "timeout", "recoverable": True, "suggested": "缩小时间窗或数据范围后重试"}),
    (("KYUUBI_NOT_CONFIGURED", "kyuubi"),
     {"error_type": "integration_unavailable", "recoverable": False, "suggested": "配置 Kyuubi 连接后重试"}),
    (("LLM_KEY_MISSING", "llm", "anthropic", "mify"),
     {"error_type": "llm_unavailable", "recoverable": False, "suggested": "配置 LLM 网关密钥后重试"}),
    (("FEISHU_NOT_CONFIGURED", "feishu"),
     {"error_type": "integration_unavailable", "recoverable": False, "suggested": "配置飞书集成后重试"}),
    (("APPROVAL_REQUIRED", "approval"),
     {"error_type": "needs_approval", "recoverable": True, "suggested": "在待确认队列中批准该动作"}),
    (("FORBIDDEN", "CROSS_SPACE_DENIED", "权限", "越权"),
     {"error_type": "permission_denied", "recoverable": False, "suggested": "申请相应空间成员资格或权限等级"}),
    (("rate", "429", "too many"),
     {"error_type": "rate_limited", "recoverable": True, "suggested": "稍后重试或降低并发"}),
    (("connection", "network", "unreachable", "连接"),
     {"error_type": "network", "recoverable": True, "suggested": "检查网络/服务可用性后重试"}),
]

_DEFAULT = {"error_type": "unknown", "recoverable": True, "suggested": "查看日志定位原因后重试"}


def classify(message: str = "", *, error_code: str = "") -> dict:
    """分类错误。返回 {error_type, recoverable, suggested, raw}。"""
    haystack = f"{error_code} {message}".lower()
    for keywords, result in _RULES:
        if any(kw.lower() in haystack for kw in keywords):
            return {**result, "raw": message or error_code}
    return {**_DEFAULT, "raw": message or error_code}
