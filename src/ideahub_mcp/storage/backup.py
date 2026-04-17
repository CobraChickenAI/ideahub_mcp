from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_stamp(stem: str) -> datetime | None:
    """Parse 'store-2026-01-02T00-00-00' back into a datetime."""
    raw = stem.removeprefix("store-")
    # Rebuild ISO: first 10 chars are date with hyphens; then 'T'; then time with hyphens.
    try:
        date_part, time_part = raw.split("T", 1)
        time_iso = time_part.replace("-", ":")
        return datetime.fromisoformat(f"{date_part}T{time_iso}")
    except (ValueError, IndexError):
        return None


def snapshot_store(
    store_path: Path,
    backups_dir: Path,
    retention_days: int = 14,
    now_override: str | None = None,
) -> Path:
    """Copy store_path into backups_dir with an ISO timestamp. Prune older than retention."""
    backups_dir.mkdir(parents=True, exist_ok=True)
    now_iso = now_override or datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        timespec="seconds"
    )
    safe = now_iso.replace(":", "-")
    dest = backups_dir / f"store-{safe}.db"
    shutil.copy2(store_path, dest)

    now_dt = datetime.fromisoformat(now_iso)
    cutoff = now_dt - timedelta(days=retention_days)
    for p in backups_dir.glob("store-*.db"):
        ts = _parse_stamp(p.stem)
        if ts is None:
            continue
        if ts <= cutoff:
            p.unlink()
    return dest
