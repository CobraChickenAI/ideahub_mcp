import sqlite3

from ideahub_mcp.domain.actors import resolve_actor
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.list_ideas import ListInput, list_ideas


def _seed(conn: sqlite3.Connection) -> None:
    resolve_actor(conn, explicit="human:m", client_info_name=None)
    resolve_actor(conn, explicit="human:n", client_info_name=None)


def test_list_filters_by_scope(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(conn, CaptureInput(content="a", actor="human:m", scope="global"))
    capture_idea(conn, CaptureInput(content="b", actor="human:m", scope="repo:x"))
    out = list_ideas(conn, ListInput(scope="repo:x"))
    assert out.count == 1
    assert out.items[0].scope == "repo:x"


def test_list_filters_by_actor_and_tags_any(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(
        conn, CaptureInput(content="x", actor="human:m", scope="global", tags=["a"])
    )
    capture_idea(
        conn, CaptureInput(content="y", actor="human:n", scope="global", tags=["b"])
    )
    out = list_ideas(conn, ListInput(actor="human:m", tags_any=["a"]))
    assert out.count == 1


def test_list_tags_all(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(
        conn, CaptureInput(content="p", actor="human:m", scope="global", tags=["a", "b"])
    )
    capture_idea(
        conn, CaptureInput(content="q", actor="human:m", scope="global", tags=["a"])
    )
    out = list_ideas(conn, ListInput(tags_all=["a", "b"]))
    assert out.count == 1


def test_list_excludes_archived_by_default(conn: sqlite3.Connection) -> None:
    _seed(conn)
    cap = capture_idea(
        conn, CaptureInput(content="z", actor="human:m", scope="global")
    )
    conn.execute("UPDATE idea SET archived_at = ? WHERE id = ?", ("2026-01-01T00:00:00Z", cap.id))
    out = list_ideas(conn, ListInput())
    assert out.count == 0
    out_all = list_ideas(conn, ListInput(include_archived=True))
    assert out_all.count == 1


def test_list_preview_truncated_to_120(conn: sqlite3.Connection) -> None:
    _seed(conn)
    long = "x" * 200
    capture_idea(conn, CaptureInput(content=long, actor="human:m", scope="global"))
    out = list_ideas(conn, ListInput())
    assert len(out.items[0].preview) == 120
