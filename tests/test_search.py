import sqlite3

from ideahub_mcp.domain.actors import resolve_actor
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.search import SearchInput, search_ideas


def _seed(conn: sqlite3.Connection) -> None:
    resolve_actor(conn, explicit="human:m", client_info_name=None)


def test_search_finds_matches(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(conn, CaptureInput(content="coherence layer", actor="human:m", scope="global"))
    capture_idea(conn, CaptureInput(content="unrelated", actor="human:m", scope="global"))
    out = search_ideas(conn, SearchInput(query="coherence"))
    assert out.count == 1
    assert "coherence" in out.hits[0].snippet.lower() or "[coherence]" in out.hits[0].snippet


def test_search_empty_result(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(conn, CaptureInput(content="apples", actor="human:m", scope="global"))
    out = search_ideas(conn, SearchInput(query="zebras"))
    assert out.count == 0


def test_search_excludes_archived_by_default(conn: sqlite3.Connection) -> None:
    _seed(conn)
    cap = capture_idea(
        conn, CaptureInput(content="findme", actor="human:m", scope="global")
    )
    conn.execute("UPDATE idea SET archived_at = ? WHERE id = ?", ("2026-01-01T00:00:00Z", cap.id))
    out = search_ideas(conn, SearchInput(query="findme"))
    assert out.count == 0
    out_all = search_ideas(conn, SearchInput(query="findme", include_archived=True))
    assert out_all.count == 1


def test_search_case_insensitive(conn: sqlite3.Connection) -> None:
    _seed(conn)
    capture_idea(conn, CaptureInput(content="Capitalized", actor="human:m", scope="global"))
    out = search_ideas(conn, SearchInput(query="capitalized"))
    assert out.count == 1


def test_search_default_excludes_checkpoints(conn: sqlite3.Connection) -> None:
    _seed(conn)
    actor_id = resolve_actor(conn, explicit="human:m", client_info_name=None).id
    conn.execute(
        "INSERT INTO idea (id, content, scope, actor_id, tags, created_at, kind) VALUES "
        "('i1','writeback phase','s1',?, '[]', datetime('now'), 'idea'),"
        "('c1','writeback phase','s1',?, '[]', datetime('now'), 'checkpoint')",
        (actor_id, actor_id),
    )
    out = search_ideas(conn, SearchInput(query="writeback", scope="s1"))
    ids = {h.id for h in out.hits}
    assert "i1" in ids
    assert "c1" not in ids

    out2 = search_ideas(
        conn, SearchInput(query="writeback", scope="s1", include_checkpoints=True)
    )
    ids2 = {h.id for h in out2.hits}
    assert {"i1", "c1"}.issubset(ids2)
