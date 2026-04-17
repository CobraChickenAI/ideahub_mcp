import sqlite3

import pytest

from ideahub_mcp.domain.actors import resolve_actor
from ideahub_mcp.errors import IdeaHubError
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.get import GetInput, get_idea


def test_get_returns_full_detail(conn: sqlite3.Connection) -> None:
    resolve_actor(conn, explicit="human:m", client_info_name=None)
    cap = capture_idea(
        conn, CaptureInput(content="hello", actor="human:m", scope="global", tags=["t"])
    )
    got = get_idea(conn, GetInput(id=cap.id))
    assert got.id == cap.id
    assert got.content == "hello"
    assert got.tags == ["t"]
    assert got.notes == []
    assert got.links == []


def test_get_missing_raises(conn: sqlite3.Connection) -> None:
    with pytest.raises(IdeaHubError) as exc:
        get_idea(conn, GetInput(id="nope"))
    assert exc.value.code == "idea_not_found"
