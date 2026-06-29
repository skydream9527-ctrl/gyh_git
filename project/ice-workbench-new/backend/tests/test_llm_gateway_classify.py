"""Tests for normalize_tool_outcome classification enrichment.

structured-tool-error-handling Task 2: the feedback layer. When
``normalize_tool_outcome`` recognises a tool-level ``error_code`` it must
enrich the normalized ``error`` object with the classifier's three structured
fields (``error_type`` / ``recoverable`` / ``suggested_action``) while
preserving ``code`` (the original error_code) and ``message``.

Covers:
* Property 7 (property-based): normalization preserves original fields and
  appends classification.
* Task 2.3 (example-based): success results are returned unchanged, and a
  ``KYUUBI_EMPTY`` empty-result marker is *not* an error_code so it does not
  trigger a failure path.

Property tests use ``hypothesis`` and run a minimum of 100 iterations via the
conftest ``ice`` profile (max_examples=100).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.services import error_classifier as ec
from app.services.llm.error_classifier import EXACT_MAP, SUFFIX_RULES
from app.services.llm.llm_gateway import normalize_tool_outcome

VALID_ERROR_TYPES = {
    "configuration",
    "transient",
    "input",
    "permission",
    "business",
    "empty",
    "unknown",
}
VALID_SUGGESTED_ACTIONS = {
    "retry_once",
    "fix_params",
    "fix_sql",
    "report_user",
    "switch_tool",
    "abort",
}

_SUFFIXES = tuple(suffix for suffix, _ in SUFFIX_RULES)

# Broad code generator: exact-map codes, suffix-bearing codes, and arbitrary
# noise so the enrichment is exercised across the whole input space.
error_codes = st.one_of(
    st.sampled_from(sorted(EXACT_MAP.keys())),
    st.builds(lambda p, s: p + s, st.text(max_size=20), st.sampled_from(_SUFFIXES)),
    st.text(min_size=1, max_size=30),
)


# --- Property 7 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 7: 归一化保留原始字段并附加分类
@given(error_code=error_codes, message=st.text(min_size=1, max_size=80))
def test_property7_normalize_preserves_and_appends(error_code, message):
    """For any result carrying an error_code, the normalized error object
    contains code/message/error_type/recoverable/suggested_action, and code
    equals the original error_code.

    Note: ``message`` is generated non-empty because the gateway intentionally
    substitutes ``str(result)[:300]`` when the tool supplies no (or an empty)
    message — see design.md normalize_tool_outcome (``message ... or str(...)``).

    Feature: structured-tool-error-handling, Property 7: 归一化保留原始字段并附加分类
    Validates: Requirements 3.1, 3.2
    """
    result = {"error_code": error_code, "message": message}
    outcome = {"success": True, "status": "done", "result": result}

    normalized = normalize_tool_outcome(outcome)

    assert normalized["success"] is False
    assert normalized["status"] == "error"
    err = normalized["error"]
    # Original fields preserved.
    assert err["code"] == error_code
    assert err["message"] == message
    # Classification appended and consistent with the classifier.
    expected = ec.classify(error_code)
    assert err["error_type"] == expected["error_type"]
    assert err["recoverable"] == expected["recoverable"]
    assert err["suggested_action"] == expected["suggested_action"]
    # Appended values stay within the legal enum domain.
    assert err["error_type"] in VALID_ERROR_TYPES
    assert err["suggested_action"] in VALID_SUGGESTED_ACTIONS
    assert isinstance(err["recoverable"], bool)


# --- Task 2.3: example-based unit tests -------------------------------------

def test_success_result_returned_unchanged():
    """A genuine success result (no error_code) passes through untouched."""
    outcome = {
        "success": True,
        "status": "done",
        "result": {"rows": [[1]], "row_count": 1},
    }
    out = normalize_tool_outcome(outcome)
    assert out is outcome
    assert out["success"] is True
    assert "error" not in out


def test_kyuubi_empty_marker_does_not_trigger_failure():
    """An empty-result query carries the KYUUBI_EMPTY marker via ``empty`` /
    ``empty_code`` — never as an ``error_code`` — so it stays a success."""
    outcome = {
        "success": True,
        "status": "done",
        "result": {
            "rows": [],
            "row_count": 0,
            "empty": True,
            "empty_code": "KYUUBI_EMPTY",
        },
    }
    out = normalize_tool_outcome(outcome)
    # Empty result is a successful query, not a failure.
    assert out is outcome
    assert out["success"] is True
    assert "error" not in out


def test_failure_payload_is_enriched_with_classification():
    """A tool-level error_code is converted to a failure with classifier fields."""
    out = normalize_tool_outcome(
        {
            "success": True,
            "status": "done",
            "result": {
                "error_code": "KYUUBI_CONNECTION_ERROR",
                "message": "connection refused",
            },
        }
    )
    assert out["success"] is False
    assert out["status"] == "error"
    err = out["error"]
    assert err["code"] == "KYUUBI_CONNECTION_ERROR"
    assert err["message"] == "connection refused"
    assert err["error_type"] == "transient"
    assert err["recoverable"] is True
    assert err["suggested_action"] == "retry_once"


def test_already_failed_outcome_passes_through():
    """An outcome that is already a failure (success=False) is returned as-is."""
    outcome = {
        "success": False,
        "status": "error",
        "error": {"code": "TOOL_ERROR", "message": "boom"},
    }
    out = normalize_tool_outcome(outcome)
    assert out is outcome
