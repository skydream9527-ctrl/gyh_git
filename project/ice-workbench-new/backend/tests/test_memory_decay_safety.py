"""Tests for memory-timestamp-decay-safety tasks 1 & 2.

Covers the new ICE_MEMORY_* config defaults + sensitive-pattern compilation and
the minimal frontmatter parse/render helpers in context_svc.
"""
from __future__ import annotations

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.config import Settings
from app.services.task.context_svc import (
    _now,
    _parse_frontmatter,
    _render_frontmatter,
)


# ---------------------------------------------------------------------------
# Task 1.1 — config smoke + _now
# ---------------------------------------------------------------------------

def test_memory_config_defaults():
    """Defaults load as documented (R7.3/7.4): 30 / 90 / 0.5."""
    s = Settings()
    assert s.ICE_MEMORY_HALF_LIFE_DAYS == 30.0
    assert s.ICE_MEMORY_STALENESS_DAYS == 90.0
    assert s.ICE_MEMORY_LEGACY_DECAY == 0.5


def test_sensitive_patterns_compile_and_nonempty():
    """The default sensitive-pattern set is non-empty and fully compilable."""
    s = Settings()
    patterns = s.memory_sensitive_patterns
    assert patterns, "default sensitive pattern set must not be empty"
    categories = {cat for cat, _ in patterns}
    # Safe-default coverage promised by the spec.
    for expected in {"api_key", "token", "password", "secret", "private_key", "密钥"}:
        assert expected in categories
    for _, pat in patterns:
        # already compiled; sanity-check it can run a search
        pat.search("nothing-here")


def test_sensitive_patterns_skip_invalid_regex():
    """An invalid regex item is skipped; valid items still compile (no raise)."""
    s = Settings(ICE_MEMORY_SENSITIVE_PATTERNS="good:abc,bad:[unterminated,also_good:xyz")
    cats = {cat for cat, _ in s.memory_sensitive_patterns}
    assert cats == {"good", "also_good"}


def test_sensitive_patterns_skip_items_without_category():
    """Items lacking a `category:` prefix are skipped rather than raising."""
    s = Settings(ICE_MEMORY_SENSITIVE_PATTERNS="no_colon_here,real:abc")
    cats = {cat for cat, _ in s.memory_sensitive_patterns}
    assert cats == {"real"}


def test_now_is_iso_utc():
    """_now() produces an ISO 8601 string parseable to a UTC-aware datetime."""
    parsed = datetime.fromisoformat(_now())
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# Task 2.2 — frontmatter unit examples
# ---------------------------------------------------------------------------

def test_parse_no_frontmatter_returns_original():
    text = "just a plain body\nno fences here"
    fields, body = _parse_frontmatter(text)
    assert fields == {}
    assert body == text


def test_parse_legacy_memory_file_shape():
    """The shape produced by the existing _memory_file output parses cleanly."""
    text = (
        "---\n"
        "name: report-style\n"
        "description: 结论先行\n"
        "metadata:\n"
        "  type: feedback\n"
        "---\n\n"
        "用户偏好：先给结论。\n"
    )
    fields, body = _parse_frontmatter(text)
    assert fields["name"] == "report-style"
    assert fields["description"] == "结论先行"
    assert fields["metadata"] == {"type": "feedback"}
    assert body == "用户偏好：先给结论。"


def test_render_preserves_extra_fields_and_field_order():
    fields = {
        "name": "slug1",
        "description": "hook",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-02-01T00:00:00+00:00",
        "custom_extra": "keepme",
        "metadata": {"type": "project", "owner": "alice"},
    }
    rendered = _render_frontmatter(fields, "body text")
    # Known scalar fields come first in fixed order, before the unknown field.
    assert rendered.index("name:") < rendered.index("description:")
    assert rendered.index("description:") < rendered.index("created_at:")
    assert rendered.index("created_at:") < rendered.index("updated_at:")
    assert rendered.index("updated_at:") < rendered.index("custom_extra:")
    # metadata block renders last and stays nested.
    assert rendered.index("custom_extra:") < rendered.index("metadata:")
    assert "  type: project" in rendered
    assert "  owner: alice" in rendered
    # Round-trips the unknown field + body.
    fields2, body2 = _parse_frontmatter(rendered)
    assert fields2["custom_extra"] == "keepme"
    assert body2 == "body text"


def test_unparseable_lines_preserved_not_raised():
    text = (
        "---\n"
        "name: x\n"
        "a line without a colon\n"
        "---\n\n"
        "body\n"
    )
    fields, body = _parse_frontmatter(text)
    rendered = _render_frontmatter(fields, body)
    assert "a line without a colon" in rendered


# ---------------------------------------------------------------------------
# Task 2.1 — Property 9: Frontmatter round-trip preserves unknown fields
# ---------------------------------------------------------------------------

# Smart generators: frontmatter keys are identifier-like (no ':' so the split
# stays unambiguous), values are single-line with no leading/trailing spaces or
# newlines — matching the real frontmatter input space.
_key = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=1,
    max_size=20,
).filter(lambda k: ":" not in k and k.strip() == k and k not in {"metadata"})
_value = st.text(
    alphabet=st.characters(blacklist_characters="\n\r"),
    min_size=0,
    max_size=40,
).map(lambda v: v.strip())

_extra_fields = st.dictionaries(_key, _value, max_size=6)
_metadata = st.dictionaries(_key, _value, min_size=1, max_size=4)


@given(
    extra=_extra_fields,
    metadata=_metadata,
    body=st.text(
        alphabet=st.characters(blacklist_characters="\r"), max_size=80
    ).map(lambda b: b.strip("\n")),
)
@settings(max_examples=120)
# Feature: memory-timestamp-decay-safety, Property 9: Frontmatter 往返保留未知字段
def test_property_frontmatter_roundtrip_preserves_unknown_fields(extra, metadata, body):
    fields = dict(extra)
    fields["name"] = "the-slug"
    fields["description"] = "the hook"
    fields["metadata"] = dict(metadata)

    rendered = _render_frontmatter(fields, body)
    parsed_fields, parsed_body = _parse_frontmatter(rendered)

    # Every field (including arbitrary unknown ones) survives the round-trip.
    for key, val in fields.items():
        assert parsed_fields.get(key) == val
    # Re-render → re-parse is stable (idempotent), proving no drift.
    rendered2 = _render_frontmatter(parsed_fields, parsed_body)
    parsed_fields2, parsed_body2 = _parse_frontmatter(rendered2)
    assert parsed_fields2 == parsed_fields
    assert parsed_body2 == parsed_body
