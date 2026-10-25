import sqlite3

import pytest

from ideahub_mcp.errors import IdeaHubError
from ideahub_mcp.tools.capture import CaptureInput, capture_idea
from ideahub_mcp.tools.recognize import RecognizeInput, recognize_actor
from ideahub_mcp.tools.register import RegisterInput, register_actor


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_register_creates_actor(conn: sqlite3.Connection) -> None:
    out = register_actor(conn, RegisterInput(id="human:michael"))
    assert out.created is True
    assert out.actor.id == "human:michael"
    assert out.actor.kind == "human"
    assert out.actor.display_name == "michael"
    assert recognize_actor(conn, RecognizeInput(id="human:michael")).actors[0] == out.actor


def test_register_uses_display_name(conn: sqlite3.Connection) -> None:
    out = register_actor(
        conn, RegisterInput(id="human:michael", display_name="Michael Schartung")
    )
    assert out.actor.display_name == "Michael Schartung"


def test_register_is_idempotent(conn: sqlite3.Connection) -> None:
    first = register_actor(conn, RegisterInput(id="agent:ingester"))
    second = register_actor(
        conn, RegisterInput(id="agent:ingester", display_name="Renamed")
    )
    assert second.created is False
    assert second.actor == first.actor
    assert _count(conn, "actor") == 1


def test_register_rejects_unprefixed_id(conn: sqlite3.Connection) -> None:
    with pytest.raises(IdeaHubError) as exc:
        register_actor(conn, RegisterInput(id="michael"))
    assert exc.value.code == "invalid_actor_id"
    assert _count(conn, "actor") == 0


def test_register_writes_no_ideas_or_notes(conn: sqlite3.Connection) -> None:
    register_actor(conn, RegisterInput(id="human:michael"))
    assert _count(conn, "idea") == 0
    assert _count(conn, "idea_note") == 0
    assert _count(conn, "idea_link") == 0


def test_capture_with_registered_originator(conn: sqlite3.Connection) -> None:
    register_actor(conn, RegisterInput(id="agent:ingester"))
    with pytest.raises(sqlite3.IntegrityError):
        capture_idea(
            conn,
            CaptureInput(
                content="before", actor="agent:ingester", scope="global",
                originator="human:michael",
            ),
        )
    register_actor(conn, RegisterInput(id="human:michael"))
    out = capture_idea(
        conn,
        CaptureInput(
            content="after", actor="agent:ingester", scope="global",
            originator="human:michael",
        ),
    )
    assert out.originator == "human:michael"
    row = conn.execute(
        "SELECT actor_id, originator_id FROM idea WHERE id = ?", (out.id,)
    ).fetchone()
    assert row == ("agent:ingester", "human:michael")
