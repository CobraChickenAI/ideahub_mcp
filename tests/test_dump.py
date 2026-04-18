import sqlite3

from ideahub_mcp.domain.actors import resolve_actor
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.dump import DUMP_HINT, DumpInput, dump_ideas


def _seed(conn: sqlite3.Connection) -> None:
    resolve_actor(conn, explicit="human:m", client_info_name=None)


def test_dump_empty_has_hint(conn: sqlite3.Connection) -> None:
    out = dump_ideas(conn, DumpInput())
    assert out.count == 0
    assert out.blob == ""
    assert out.hint == DUMP_HINT
    assert out.scope_resolved == "global"


def test_dump_echoes_resolved_scope(conn: sqlite3.Connection) -> None:
    out = dump_ideas(conn, DumpInput(scope="repo:demo"))
    assert out.scope_resolved == "repo:demo"


def test_dump_newest_first(conn: sqlite3.Connection) -> None:
    _seed(conn)
    a = capture_idea(conn, CaptureInput(content="first", actor="human:m", scope="global"))
    b = capture_idea(conn, CaptureInput(content="second", actor="human:m", scope="global"))
    out = dump_ideas(conn, DumpInput())
    assert out.blob.index(b.id) < out.blob.index(a.id)


def test_dump_excludes_archived(conn: sqlite3.Connection) -> None:
    _seed(conn)
    cap = capture_idea(conn, CaptureInput(content="x", actor="human:m", scope="global"))
    conn.execute(
        "UPDATE idea SET archived_at=? WHERE id=?", ("2026-01-01T00:00:00Z", cap.id)
    )
    out = dump_ideas(conn, DumpInput())
    assert out.count == 0
    out_all = dump_ideas(conn, DumpInput(include_archived=True))
    assert out_all.count == 1


def test_dump_token_budget_truncates(conn: sqlite3.Connection) -> None:
    _seed(conn)
    for i in range(50):
        capture_idea(
            conn,
            CaptureInput(
                content=f"idea number {i} " * 20, actor="human:m", scope="global"
            ),
        )
    out = dump_ideas(conn, DumpInput(limit_tokens=100))
    assert out.truncated is True
    assert out.count < 50


def test_dump_scope_filter(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(conn, CaptureInput(content="a", actor="human:m", scope="global"))
    capture_idea(conn, CaptureInput(content="b", actor="human:m", scope="repo:x"))
    out = dump_ideas(conn, DumpInput(scope="repo:x"))
    assert out.count == 1
    assert "\nb\n" in out.blob
    assert "\na\n" not in out.blob


def test_dump_default_excludes_checkpoints(conn: sqlite3.Connection) -> None:
    _seed(conn)
    actor_id = resolve_actor(conn, explicit="human:m", client_info_name=None).id
    conn.execute(
        "INSERT INTO idea (id, content, scope, actor_id, tags, created_at, kind) VALUES "
        "('i1','writeback phase','s1',?, '[]', datetime('now'), 'idea'),"
        "('c1','writeback phase','s1',?, '[]', datetime('now'), 'checkpoint')",
        (actor_id, actor_id),
    )
    out = dump_ideas(conn, DumpInput(scope="s1"))
    assert "i1" in out.blob
    assert "c1" not in out.blob

    out2 = dump_ideas(conn, DumpInput(scope="s1", include_checkpoints=True))
    assert "i1" in out2.blob
    assert "c1" in out2.blob
