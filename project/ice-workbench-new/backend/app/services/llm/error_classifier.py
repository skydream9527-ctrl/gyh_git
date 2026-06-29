"""Error_Classifier — deterministic, side-effect-free tool-error classifier.

This module turns a flat ``error_code`` into the three structured fields
``error_type`` / ``recoverable`` / ``suggested_action`` so that the LLM agent
runtime can decide a recovery strategy without parsing developer-facing text.

Design contract (see design.md "Components and Interfaces"):

* Pure functions, no I/O, no side effects: identical input → identical output.
* :func:`classify` never raises. Any string (including ``None``, empty string,
  unusual casing) is accepted; unrecognised codes fall back to
  ``(unknown, False, report_user)``.
* :func:`enrich` only *adds* fields — it never renames, mutates, or deletes any
  existing key, preserving backward compatibility (G7).

Resolution priority:
    1. Exact match (:data:`EXACT_MAP`).
    2. Suffix-pattern match (:data:`SUFFIX_RULES`).
    3. Fallback ``(unknown, False, report_user)``.

Exact matches take precedence over suffix matches so that, e.g.,
``KYUUBI_PERMISSION_ERROR`` is not misclassified by a ``*_ERROR``-style suffix.
"""

from __future__ import annotations

from typing import Literal, TypedDict

ErrorType = Literal[
    "configuration",
    "transient",
    "input",
    "permission",
    "business",
    "empty",
    "unknown",
]

SuggestedAction = Literal[
    "retry_once",
    "fix_params",
    "fix_sql",
    "report_user",
    "switch_tool",
    "abort",
]


class ErrorClassification(TypedDict):
    """Structured classification of a tool ``error_code``."""

    error_type: ErrorType
    recoverable: bool
    suggested_action: SuggestedAction


# --- Deterministic mapping tables ------------------------------------------

# Exact ``error_code`` → classification. Checked before suffix rules.
EXACT_MAP: dict[str, ErrorClassification] = {
    "VALIDATION_ERROR": {
        "error_type": "input",
        "recoverable": False,
        "suggested_action": "fix_params",
    },
    "SQL_BLOCKED": {
        "error_type": "permission",
        "recoverable": False,
        "suggested_action": "fix_sql",
    },
    "KYUUBI_SYNTAX_ERROR": {
        "error_type": "business",
        "recoverable": False,
        "suggested_action": "fix_sql",
    },
    "KYUUBI_CONNECTION_ERROR": {
        "error_type": "transient",
        "recoverable": True,
        "suggested_action": "retry_once",
    },
    "KYUUBI_PERMISSION_ERROR": {
        "error_type": "permission",
        "recoverable": False,
        "suggested_action": "report_user",
    },
    "KYUUBI_EMPTY": {
        "error_type": "empty",
        "recoverable": False,
        "suggested_action": "report_user",
    },
}

# Suffix pattern → classification. Mutually exclusive: a code matches at most
# one suffix rule. Checked only after the exact map misses.
SUFFIX_RULES: tuple[tuple[str, ErrorClassification], ...] = (
    (
        "_NOT_CONFIGURED",
        {
            "error_type": "configuration",
            "recoverable": False,
            "suggested_action": "report_user",
        },
    ),
    (
        "_NOT_INSTALLED",
        {
            "error_type": "configuration",
            "recoverable": False,
            "suggested_action": "report_user",
        },
    ),
    (
        "_TIMEOUT",
        {
            "error_type": "transient",
            "recoverable": True,
            "suggested_action": "retry_once",
        },
    ),
)

# Fallback for codes that match neither the exact map nor any suffix rule.
_FALLBACK: ErrorClassification = {
    "error_type": "unknown",
    "recoverable": False,
    "suggested_action": "report_user",
}


def classify(error_code: str | None) -> ErrorClassification:
    """Resolve ``error_code`` to a structured classification.

    Deterministic and total: never raises. ``None`` is normalised to the empty
    string. Resolution order is exact match → suffix match → fallback.

    Returns a fresh dict each call so callers cannot mutate the shared tables.
    """
    code = error_code or ""

    exact = EXACT_MAP.get(code)
    if exact is not None:
        return dict(exact)  # type: ignore[return-value]

    for suffix, classification in SUFFIX_RULES:
        if code.endswith(suffix):
            return dict(classification)  # type: ignore[return-value]

    return dict(_FALLBACK)  # type: ignore[return-value]


def enrich(envelope: dict) -> dict:
    """Augment a tool return ``envelope`` with structured error fields.

    If ``envelope`` contains an ``error_code``, add ``error_type`` /
    ``recoverable`` / ``suggested_action`` in place and return it. Otherwise the
    envelope is returned unchanged. Existing keys (``error_code`` / ``message``
    and any others) are never modified or removed — only the three classifier
    fields are added.
    """
    if not isinstance(envelope, dict):
        return envelope

    code = envelope.get("error_code")
    if not code:
        return envelope

    classification = classify(code)
    envelope["error_type"] = classification["error_type"]
    envelope["recoverable"] = classification["recoverable"]
    envelope["suggested_action"] = classification["suggested_action"]
    return envelope
