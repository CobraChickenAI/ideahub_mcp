"""Shared pytest fixtures."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from ideahub_mcp.storage.migrations import apply_pending_migrations

MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "ideahub_mcp" / "storage" / "migrations"
)


@pytest.fixture
def tmp_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Isolated IDEAHUB_MCP_HOME per test."""
    monkeypatch.setenv("IDEAHUB_MCP_HOME", str(tmp_path))
    yield tmp_path


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """Fresh migrated SQLite connection per test."""
    c = sqlite3.connect(tmp_path / "t.db", isolation_level=None)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    apply_pending_migrations(c, MIGRATIONS_DIR)
    try:
        yield c
    finally:
        c.close()
