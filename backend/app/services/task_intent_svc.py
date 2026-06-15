"""Lightweight task intent parsing and routing hints.

This module intentionally stays deterministic. It is not trying to replace the
LLM; it catches common business shorthand before the agent spends tool calls on
the wrong interpretation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import agents_svc


_AD_KEYWORDS = (
    "广告",
    "广告位",
    "曝光",
    "实时曝光",
    "收入",
    "财收",
    "ecpm",
    "eCPM",
    "填充",
    "ad_request",
    "ad_response",
    "tagid",
    "tag_id",
    "下钻",
    "环比",
)

_TAG_DATE_RE = re.compile(
    r"(?P<tag>\d+(?:\.\d+)*\.[A-Za-z]\.\d+)(?P<year>\d{2,4})年(?P<month>\d{1,2})(?:月|\.)?(?P<day>\d{1,2})?"
)


@dataclass(frozen=True)
class ParsedIntent:
    domain: str | None = None
    tag_id: str | None = None
    date_text: str | None = None
    route_agent_id: str | None = None
    route_reason: str | None = None
    prompt_hint: str | None = None

    def as_dict(self) -> dict:
        return {
            "domain": self.domain,
            "tag_id": self.tag_id,
            "date_text": self.date_text,
            "route_agent_id": self.route_agent_id,
            "route_reason": self.route_reason,
            "prompt_hint": self.prompt_hint,
        }


def _is_ad_data_text(text: str) -> bool:
    lowered = text.lower()
    return any(k.lower() in lowered for k in _AD_KEYWORDS)


def parse_message_intent(text: str, *, task_name: str | None = None) -> ParsedIntent:
    """Parse a single user message plus optional task name into routing hints."""
    combined = f"{task_name or ''}\n{text or ''}".strip()
    is_ad = _is_ad_data_text(combined)
    match = _TAG_DATE_RE.search(text or "")

    tag_id = None
    date_text = None
    prompt_hint = None
    if match:
        tag_id = match.group("tag")
        year = match.group("year")
        month = match.group("month")
        day = match.group("day")
        date_text = f"{year}年{month}月{day}日" if day else f"{year}年{month}月"
        prompt_hint = (
            "【后端预解析提示】用户输入里出现了紧贴日期的业务标识。"
            f"优先按广告位 tag_id=`{tag_id}`、日期=`{date_text}` 理解，"
            "不要把完整连写片段误判成实验 ID 或版本号。"
        )
        if is_ad:
            prompt_hint += (
                "这是广告/财收数据诊断任务；先复述该断句并直接按此口径分析。"
                "只有在表或口径缺失时才提出一个定向澄清问题。"
            )
            if "实时" in (text or ""):
                prompt_hint += (
                    "用户明确要实时数据；如果当前只找到 T+1/离线表，必须先说明能力边界，"
                    "再用离线数据做代理验证或询问实时数据源。"
                )

    route_agent_id = None
    route_reason = None
    if is_ad and agents_svc.get_agent("data-analysis"):
        route_agent_id = "data-analysis"
        route_reason = "ad_data_diagnosis"

    return ParsedIntent(
        domain="ad_data" if is_ad else None,
        tag_id=tag_id,
        date_text=date_text,
        route_agent_id=route_agent_id,
        route_reason=route_reason,
        prompt_hint=prompt_hint,
    )


def choose_agent_for_task(
    *,
    requested_agent_id: str | None,
    name: str,
    description: str | None = None,
    initial_prompt: str | None = None,
) -> tuple[str | None, ParsedIntent]:
    """Return an agent id after applying conservative auto-routing.

    We only override when the user selected no agent or the generic entry agent.
    A deliberate specialized agent selection is preserved.
    """
    text = "\n".join(p for p in (description, initial_prompt) if p)
    intent = parse_message_intent(text, task_name=name)
    requested = (requested_agent_id or "").strip() or None
    if requested not in (None, "general"):
        return requested, intent
    if intent.route_agent_id:
        return intent.route_agent_id, intent
    return requested, intent


def build_runtime_hint(text: str, *, task_name: str | None = None) -> str:
    intent = parse_message_intent(text, task_name=task_name)
    return intent.prompt_hint or ""
