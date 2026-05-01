import pytest
from hypothesis import given
from hypothesis import strategies as st

from ideahub_mcp.util.coerce import coerce_str_list, normalize_task_ref


def test_list_passthrough() -> None:
    assert coerce_str_list(["a", "b"]) == ["a", "b"]


def test_none_becomes_empty() -> None:
    assert coerce_str_list(None) == []


def test_json_encoded_list_is_parsed() -> None:
    assert coerce_str_list('["mcp", "claude-desktop"]') == ["mcp", "claude-desktop"]


def test_plain_string_becomes_single_tag() -> None:
    assert coerce_str_list("lonely") == ["lonely"]


def test_empty_string_becomes_empty() -> None:
    assert coerce_str_list("") == []


def test_non_list_json_raises() -> None:
    with pytest.raises(ValueError):
        coerce_str_list('{"a": 1}')


def test_normalize_task_ref_none_passthrough() -> None:
    assert normalize_task_ref(None) is None


def test_normalize_task_ref_empty_to_none() -> None:
    assert normalize_task_ref("") is None
    assert normalize_task_ref("   ") is None
    assert normalize_task_ref("---") is None


def test_normalize_task_ref_collapses_separators() -> None:
    assert normalize_task_ref("Writeback Phase 1") == "writeback-phase-1"
    assert normalize_task_ref("writeback_phase_1") == "writeback-phase-1"
    assert normalize_task_ref("writeback-phase-1") == "writeback-phase-1"
    assert normalize_task_ref("  Writeback   Phase   1  ") == "writeback-phase-1"


def test_normalize_task_ref_strips_leading_trailing_hyphens() -> None:
    assert normalize_task_ref("--foo--") == "foo"
    assert normalize_task_ref("!!foo!!") == "foo"


def test_normalize_task_ref_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        normalize_task_ref(42)
    with pytest.raises(ValueError):
        normalize_task_ref(["foo"])


@given(s=st.text(min_size=0, max_size=80))
def test_normalize_task_ref_idempotent(s: str) -> None:
    once = normalize_task_ref(s)
    twice = normalize_task_ref(once)
    assert once == twice
