from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ideahub_mcp.domain.actors import ActorUnresolvedError, resolve_actor
from ideahub_mcp.storage.connection import open_connection
from ideahub_mcp.storage.migrations import apply_pending_migrations

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "ideahub_mcp" / "storage" / "migrations"
)


def _fresh(tmp_path: Path) -> sqlite3.Connection:
    cm = open_connection(tmp_path / "t.db")
    conn = cm.__enter__()
    apply_pending_migrations(conn, MIGRATIONS_DIR)
    return conn


def test_explicit_actor_arg_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("IDEAHUB_ACTOR", "human:env")
    conn = _fresh(tmp_path)
    result = resolve_actor(conn, explicit="agent:cli", client_info_name="claude-code")
    assert result.id == "agent:cli"
    assert result.created is True


def test_client_info_name_used_if_no_explicit(tmp_path: Path) -> None:
    conn = _fresh(tmp_path)
    result = resolve_actor(conn, explicit=None, client_info_name="claude-code")
    assert result.id == "agent:claude-code"


def test_env_var_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IDEAHUB_ACTOR", "human:michael")
    conn = _fresh(tmp_path)
    result = resolve_actor(conn, explicit=None, client_info_name=None)
    assert result.id == "human:michael"


def test_unresolved_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("IDEAHUB_ACTOR", raising=False)
    conn = _fresh(tmp_path)
    with pytest.raises(ActorUnresolvedError):
        resolve_actor(conn, explicit=None, client_info_name=None)
