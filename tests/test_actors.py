from __future__ import annotations

import sqlite3

import pytest

from ideahub_mcp.domain.actors import ActorUnresolvedError, resolve_actor


def test_explicit_actor_arg_wins(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IDEAHUB_ACTOR", "human:env")
    result = resolve_actor(conn, explicit="agent:cli", client_info_name="claude-code")
    assert result.id == "agent:cli"
    assert result.created is True


def test_client_info_name_used_if_no_explicit(conn: sqlite3.Connection) -> None:
    result = resolve_actor(conn, explicit=None, client_info_name="claude-code")
    assert result.id == "agent:claude-code"


def test_env_var_fallback(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IDEAHUB_ACTOR", "human:michael")
    result = resolve_actor(conn, explicit=None, client_info_name=None)
    assert result.id == "human:michael"


def test_unresolved_raises(
    conn: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("IDEAHUB_ACTOR", raising=False)
    with pytest.raises(ActorUnresolvedError):
        resolve_actor(conn, explicit=None, client_info_name=None)
