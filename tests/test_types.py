"""Tests for util/types.py — the StrList annotated type."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from ideahub_mcp.util.types import StrList


class _M(BaseModel):
    tags: StrList = Field(default_factory=list)


def test_strlist_accepts_native_list() -> None:
    assert _M(tags=["a", "b"]).tags == ["a", "b"]


def test_strlist_accepts_json_string() -> None:
    # Some MCP host bridges JSON-stringify list params before forwarding.
    m = _M.model_validate({"tags": '["a", "b"]'})
    assert m.tags == ["a", "b"]


def test_strlist_accepts_plain_string_as_single_tag() -> None:
    m = _M.model_validate({"tags": "solo"})
    assert m.tags == ["solo"]


def test_strlist_accepts_none_as_empty() -> None:
    m = _M.model_validate({"tags": None})
    assert m.tags == []


def test_strlist_default_is_empty() -> None:
    assert _M().tags == []


def test_strlist_rejects_non_list_json_object() -> None:
    with pytest.raises(ValidationError):
        _M.model_validate({"tags": '{"k": "v"}'})
