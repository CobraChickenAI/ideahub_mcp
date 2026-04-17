from pathlib import Path

from ideahub_mcp.storage.backup import snapshot_store


def test_snapshot_creates_timestamped_copy(tmp_path: Path) -> None:
    src = tmp_path / "store.db"
    src.write_bytes(b"fake-db-bytes")
    backups = tmp_path / "backups"
    result = snapshot_store(src, backups)
    assert result.exists()
    assert result.parent == backups
    assert result.read_bytes() == b"fake-db-bytes"


def test_snapshot_prunes_beyond_retention(tmp_path: Path) -> None:
    src = tmp_path / "store.db"
    src.write_bytes(b"x")
    backups = tmp_path / "backups"
    for i in range(20):
        snapshot_store(
            src, backups, retention_days=3, now_override=f"2026-01-{i + 1:02d}T00:00:00"
        )
    assert len(list(backups.glob("*.db"))) <= 3
