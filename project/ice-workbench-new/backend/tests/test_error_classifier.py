"""Tests for Error_Classifier (structured-tool-error-handling, Task 1).

Covers property-based tests for Properties 1-6 plus example-based unit tests
that assert the mapping table item-by-item and guard the "exact precedes
suffix" regression (KYUUBI_PERMISSION_ERROR must not be caught by a ``*_ERROR``
suffix).

Property tests use the ``hypothesis`` library and run a minimum of 100
iterations via the conftest ``ice`` profile (max_examples=100).
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.services import error_classifier as ec
from app.services.llm.error_classifier import (
    EXACT_MAP,
    SUFFIX_RULES,
    classify,
    enrich,
)

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


def _is_unmatched(code: str) -> bool:
    """True when ``code`` hits neither the exact map nor any suffix rule."""
    if code in EXACT_MAP:
        return False
    return not any(code.endswith(suffix) for suffix in _SUFFIXES)


# Broad code generator: arbitrary text plus the empty string and None, so the
# "never raises on any string/None" contract is genuinely exercised.
any_code = st.one_of(
    st.none(),
    st.text(max_size=40),
    st.sampled_from(sorted(EXACT_MAP.keys())),
    st.sampled_from(_SUFFIXES),
)


# --- Property 1 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 1: 分类输出始终在合法枚举内
@given(error_code=any_code)
def test_property1_output_domain_is_legal(error_code):
    """classify never raises and always returns in-domain enum values.

    Feature: structured-tool-error-handling, Property 1: 分类输出始终在合法枚举内
    Validates: Requirements 1.2, 1.3, 1.4, 2.6, 7.3
    """
    result = classify(error_code)
    assert result["error_type"] in VALID_ERROR_TYPES
    assert result["suggested_action"] in VALID_SUGGESTED_ACTIONS
    assert isinstance(result["recoverable"], bool)


# --- Property 2 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 2: 分类是确定性的
@given(error_code=any_code)
def test_property2_classification_is_deterministic(error_code):
    """Repeated calls with the same code return identical results.

    Feature: structured-tool-error-handling, Property 2: 分类是确定性的
    Validates: Requirements 2.7
    """
    first = classify(error_code)
    second = classify(error_code)
    third = classify(error_code)
    assert first == second == third


# --- Property 3 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 3: 后缀模式映射正确
@given(prefix=st.text(max_size=30))
def test_property3_suffix_configuration_mapping(prefix):
    """``*_NOT_CONFIGURED`` / ``*_NOT_INSTALLED`` → (configuration, False, report_user).

    Feature: structured-tool-error-handling, Property 3: 后缀模式映射正确
    Validates: Requirements 2.2, 2.3
    """
    for suffix in ("_NOT_CONFIGURED", "_NOT_INSTALLED"):
        code = prefix + suffix
        if code in EXACT_MAP:
            continue
        result = classify(code)
        assert result == {
            "error_type": "configuration",
            "recoverable": False,
            "suggested_action": "report_user",
        }


# Feature: structured-tool-error-handling, Property 3: 后缀模式映射正确
@given(prefix=st.text(max_size=30))
def test_property3_suffix_timeout_mapping(prefix):
    """``*_TIMEOUT`` → (transient, True, retry_once).

    Feature: structured-tool-error-handling, Property 3: 后缀模式映射正确
    Validates: Requirements 2.2, 2.3
    """
    code = prefix + "_TIMEOUT"
    if code in EXACT_MAP:
        return
    result = classify(code)
    assert result == {
        "error_type": "transient",
        "recoverable": True,
        "suggested_action": "retry_once",
    }


# --- Property 4 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 4: 精确映射与 KYUUBI 细分映射正确
@given(error_code=st.sampled_from(sorted(EXACT_MAP.keys())))
def test_property4_exact_map_mapping(error_code):
    """Every exact-map code classifies to its tabulated three fields.

    Feature: structured-tool-error-handling, Property 4: 精确映射与 KYUUBI 细分映射正确
    Validates: Requirements 2.4, 2.5, 5.6, 5.7, 5.8, 5.9
    """
    assert classify(error_code) == EXACT_MAP[error_code]


# --- Property 5 -------------------------------------------------------------
# Feature: structured-tool-error-handling, Property 5: 未知错误码兜底
@given(error_code=st.text(max_size=40))
def test_property5_unknown_fallback(error_code):
    """Codes outside the exact map and all suffix rules fall back to unknown.

    Feature: structured-tool-error-handling, Property 5: 未知错误码兜底
    Validates: Requirements 2.1, 2.6
    """
    if not _is_unmatched(error_code):
        return
    assert classify(error_code) == {
        "error_type": "unknown",
        "recoverable": False,
        "suggested_action": "report_user",
    }


# --- Property 6 -------------------------------------------------------------
json_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(max_size=30),
    st.lists(st.integers(), max_size=4),
)
arbitrary_envelope = st.dictionaries(
    keys=st.text(min_size=1, max_size=15),
    values=json_values,
    max_size=6,
)


# Feature: structured-tool-error-handling, Property 6: enrich 的增量性（只增不改不删）
@given(envelope=arbitrary_envelope, error_code=st.text(min_size=1, max_size=20))
def test_property6_enrich_is_additive(envelope, error_code):
    """enrich only adds the three fields iff error_code present; never mutates
    or deletes existing keys.

    Feature: structured-tool-error-handling, Property 6: enrich 的增量性（只增不改不删）
    Validates: Requirements 1.1, 1.5, 1.6, 7.1
    """
    # Snapshot the original (excluding the three classifier keys, which we may
    # add). Avoid collisions by clearing any pre-seeded classifier keys.
    added_keys = {"error_type", "recoverable", "suggested_action"}
    base = {k: v for k, v in envelope.items() if k not in added_keys}

    # Case A: no error_code → unchanged.
    no_code = dict(base)
    no_code.pop("error_code", None)
    result_a = enrich(dict(no_code))
    assert result_a == no_code

    # Case B: with error_code → original keys preserved, three keys added.
    with_code = dict(base)
    with_code["error_code"] = error_code
    original = dict(with_code)
    result_b = enrich(with_code)

    # All original keys/values preserved unchanged.
    for k, v in original.items():
        assert result_b[k] == v
    # Exactly the three classifier keys added.
    assert set(result_b.keys()) - set(original.keys()) == added_keys
    expected = classify(error_code)
    assert result_b["error_type"] == expected["error_type"]
    assert result_b["recoverable"] == expected["recoverable"]
    assert result_b["suggested_action"] == expected["suggested_action"]


# --- Task 1.7: example-based unit tests ------------------------------------

EXPECTED_TABLE = {
    "VALIDATION_ERROR": ("input", False, "fix_params"),
    "SQL_BLOCKED": ("permission", False, "fix_sql"),
    "KYUUBI_SYNTAX_ERROR": ("business", False, "fix_sql"),
    "KYUUBI_CONNECTION_ERROR": ("transient", True, "retry_once"),
    "KYUUBI_PERMISSION_ERROR": ("permission", False, "report_user"),
    "KYUUBI_EMPTY": ("empty", False, "report_user"),
    "TOOL_NOT_CONFIGURED": ("configuration", False, "report_user"),
    "KYUUBI_NOT_INSTALLED": ("configuration", False, "report_user"),
    "KYUUBI_TIMEOUT": ("transient", True, "retry_once"),
}


def test_mapping_table_item_by_item():
    """Each known error_code resolves to its documented three fields."""
    for code, (etype, recoverable, action) in EXPECTED_TABLE.items():
        result = classify(code)
        assert result["error_type"] == etype, code
        assert result["recoverable"] is recoverable, code
        assert result["suggested_action"] == action, code


def test_permission_error_not_caught_by_error_suffix():
    """KYUUBI_PERMISSION_ERROR matches the exact map, not a ``*_ERROR`` suffix.

    Regression for "exact precedes suffix": despite ending in ``_ERROR``, it
    must classify as permission/report_user, not fall through to unknown.
    """
    result = classify("KYUUBI_PERMISSION_ERROR")
    assert result == {
        "error_type": "permission",
        "recoverable": False,
        "suggested_action": "report_user",
    }


def test_generic_error_suffix_falls_back_to_unknown():
    """A bare ``*_ERROR`` / ``*_CLI_ERROR`` code (no exact/suffix rule) is unknown."""
    for code in ("SOME_ERROR", "KYUUBI_CLI_ERROR", "RANDOM_FAILED"):
        assert classify(code) == {
            "error_type": "unknown",
            "recoverable": False,
            "suggested_action": "report_user",
        }


def test_classify_handles_none_and_empty():
    """classify(None) and classify('') return the unknown fallback, no raise."""
    for code in (None, ""):
        assert classify(code) == {
            "error_type": "unknown",
            "recoverable": False,
            "suggested_action": "report_user",
        }


def test_enrich_success_result_unchanged():
    """A success envelope without error_code is returned unchanged."""
    env = {"rows": [], "row_count": 0}
    out = enrich(dict(env))
    assert out == env


def test_enrich_preserves_error_code_and_message():
    """enrich keeps error_code/message and adds three fields."""
    env = {"error_code": "KYUUBI_CONNECTION_ERROR", "message": "connection refused"}
    out = enrich(dict(env))
    assert out["error_code"] == "KYUUBI_CONNECTION_ERROR"
    assert out["message"] == "connection refused"
    assert out["error_type"] == "transient"
    assert out["recoverable"] is True
    assert out["suggested_action"] == "retry_once"
