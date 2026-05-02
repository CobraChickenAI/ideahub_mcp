"""Build a deterministic ideahub_mcp store for evaluation runs.

Usage: ``uv run python evals/seed_corpus.py <target-path>``

Re-runnable: deletes the target file first, then rebuilds from scratch with
hand-picked ULIDs and frozen timestamps so every run produces a byte-identical
store. The corpus content is engineered to make the questions in
``ideahub_mcp_eval.xml`` answerable with stable, string-comparable answers.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from ulid import ULID

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ideahub_mcp.storage.connection import open_connection  # noqa: E402
from ideahub_mcp.storage.migrations import apply_pending_migrations  # noqa: E402
from ideahub_mcp.util.hashing import compute_content_hash  # noqa: E402

MIGRATIONS_DIR = REPO_ROOT / "src" / "ideahub_mcp" / "storage" / "migrations"


def uid(n: int) -> str:
    """Stable ULID from an integer. Lexically ordered, deterministic."""
    return str(ULID.from_int(n))


# Frozen timebase. Every row's created_at derives from this so reseeding never
# drifts.
BASE_DAY = "2026-01-{day:02d}T{hour:02d}:00:00"


def ts(day: int, hour: int = 12) -> str:
    return BASE_DAY.format(day=day, hour=hour)


# Actor allocations. IDs hand-picked, prefix-typed per ideahub_mcp's
# actor_resolver convention.
ACTORS = [
    ("human:alice", "human", "alice", ts(1, 0)),
    ("human:bob", "human", "bob", ts(1, 0)),
    ("agent:claude", "agent", "claude", ts(1, 0)),
    ("agent:codex", "agent", "codex", ts(1, 0)),
]


# Ideas. (uid_n, content, scope, actor, originator, tags, created_day,
# task_ref, kind, kind_label, archived_at).
# Content is engineered to make the eval questions verifiable.
IDEAS = [
    # repo:demo / coherence-tagged: 4 live + 1 archived (Q1 expects 4)
    (1, "Coherence requires deny-by-default at every boundary.",
     "repo:demo", "human:alice", None, ["coherence", "boundary"], 2, None,
     "idea", None, None),
    (2, "Fail-closed execution is non-negotiable for safety.",
     "repo:demo", "human:alice", None, ["coherence", "fail-closed"], 3, None,
     "idea", None, None),
    (3, "Single source of truth per capability prevents drift.",
     "repo:demo", "human:bob", None, ["coherence"], 4, None,
     "idea", None, None),
    (4, "Provenance integrity binds every claim to its origin.",
     "repo:demo", "agent:claude", "human:alice", ["coherence", "provenance"],
     5, None, "idea", None, None),
    # archived coherence idea — excluded from default counts
    (5, "Stale draft on TML positioning that should not appear in counts.",
     "repo:demo", "human:bob", None, ["coherence", "draft"], 6, None,
     "idea", None, ts(7, 9)),
    # supersession chain (Q2 — supersedes 'Initial draft of TML primitives')
    (6, "Initial draft of TML primitives covering only seven concepts.",
     "repo:demo", "human:alice", None, ["primitives", "draft"], 8, None,
     "idea", None, None),
    (7, "Eight invariants of TML: deny-by-default, fail-closed, "
        "single source of truth, scope anchoring, domain ownership, "
        "provenance required, provenance integrity, view direction.",
     "repo:demo", "human:alice", None, ["invariants", "primitives"], 9, None,
     "idea", None, None),
    # Q4 corpus: three ideas mentioning fail-closed execution
    (8, "Fail-closed execution applies even when policy lookup fails.",
     "repo:demo", "agent:claude", None, ["fail-closed"], 10, None,
     "idea", None, None),
    (9, "Audit found one regression: fail-closed execution skipped for "
        "cached capabilities.",
     "repo:demo", "human:bob", None, ["fail-closed", "audit"], 11, None,
     "idea", None, None),
    # Q5 — most-noted idea will be #7 (4 notes)
    (10, "Tag overlap heuristic for related ideas.",
     "repo:demo", "agent:codex", None, ["search", "ranking"], 12, None,
     "idea", None, None),
    (11, "Lateral relationship between TML and schema.org vocabularies.",
     "repo:demo", "human:alice", None, ["schema-org", "vocabulary"], 13, None,
     "idea", None, None),
    # repo:other — out-of-scope filler
    (12, "Cross-repo capture lives outside repo:demo.",
     "repo:other", "human:bob", None, ["misc"], 14, None,
     "idea", None, None),
    (13, "Another repo:other idea unrelated to coherence.",
     "repo:other", "human:alice", None, ["misc"], 15, None,
     "idea", None, None),
    # human:alice author count in repo:demo (Q8): alice authored ideas
    # 1, 2, 4 (originator), 6, 7, 11 in repo:demo. As actor_id: 1, 2, 6, 7, 11
    # = 5 ideas (excluding archived #5 which alice didn't author anyway).
    # Total live alice-authored ideas in repo:demo = 5.
    # Q6 — strongest tag overlap to idea #7 (tags: invariants, primitives).
    # Idea #6 shares 'primitives' = overlap 1. Make #14 share both =
    # overlap 2.
    (14, "Re-derivation of TML invariants from the primitives grid.",
     "repo:demo", "agent:claude", None, ["invariants", "primitives"], 16, None,
     "idea", None, None),
]


# Notes per idea_id. (note_uid_n, idea_uid_n, kind, content, actor, day).
NOTES = [
    # idea #7 gets 4 notes — most-noted idea (Q5).
    (101, 7, "confirmation", "Confirmed against the published manifesto.",
     "human:bob", 9),
    (102, 7, "observation", "Note: 'view direction' wasn't in early drafts.",
     "agent:claude", 10),
    (103, 7, "follow-up", "Cross-link to provenance-integrity essay.",
     "human:alice", 11),
    (104, 7, "correction", "Corrected wording on scope-anchoring clause.",
     "human:alice", 12),
    # idea #5 archive note (Q9) — content carries the archive reason.
    (105, 5, "archive", "Superseded by current TML positioning baseline.",
     "human:bob", 7),
    # a couple of misc notes for variety
    (106, 1, "observation", "Boundary semantics tested with mock connector.",
     "agent:codex", 4),
    (107, 4, "follow-up", "Wire provenance into the audit log.",
     "agent:claude", 6),
]


# Links. (source_uid_n, target_uid_n, kind, day).
# Link kind canonicalization: for 'related', store with smaller id as source
# (matches link_ideas behavior).
LINKS = [
    # Q2 — idea #7 supersedes idea #6
    (7, 6, "supersedes", 9),
    # Q3 — idea #1 related to idea #2 (canonical: 1 < 2 already)
    (1, 2, "related", 3),
    # Q10 — idea #7 has related-link to #14 (canonical: 7 < 14)
    (7, 14, "related", 16),
    # extra graph density
    (10, 11, "evolved_from", 13),
    (8, 9, "duplicate", 11),
]


# Checkpoints. Default-excluded from list/search/dump unless opt-in.
# (uid_n, content, scope, actor, tags, day, task_ref, kind_label).
# Q7 — task_ref 'writeback-phase-1' has 3 checkpoints.
CHECKPOINTS = [
    (201, "Decision: candidate envelope skips when candidates=0.",
     "repo:demo", "agent:claude", ["writeback"], 17,
     "writeback-phase-1", "decision"),
    (202, "Observation: dedup hash path merges tags into the original row.",
     "repo:demo", "agent:claude", ["writeback"], 18,
     "writeback-phase-1", "observation"),
    (203, "Next step: add candidate-utilization telemetry in P1 follow-up.",
     "repo:demo", "human:alice", ["writeback"], 19,
     "writeback-phase-1", "next_step"),
    # checkpoints under a different task_ref — must NOT be counted in Q7.
    (204, "Question: should promote also touch the FTS row?",
     "repo:demo", "human:alice", ["promote"], 20,
     "promote-design", "question"),
    (205, "Assumption: ULID lex order is good enough for recency tiebreak.",
     "repo:demo", "agent:codex", ["search"], 21,
     "search-tuning", "assumption"),
]


def build(target: Path) -> None:
    if target.exists():
        target.unlink()
    with open_connection(target) as conn:
        apply_pending_migrations(conn, MIGRATIONS_DIR)
        for actor_id, kind, display, first_seen in ACTORS:
            conn.execute(
                "INSERT INTO actor (id, kind, display_name, first_seen_at) "
                "VALUES (?, ?, ?, ?)",
                (actor_id, kind, display, first_seen),
            )
        for (n, content, scope, actor, originator, tags, day, task_ref,
             kind, kind_label, archived_at) in IDEAS:
            conn.execute(
                "INSERT INTO idea "
                "(id, content, scope, actor_id, originator_id, tags, "
                " created_at, archived_at, kind, task_ref, kind_label, "
                " content_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uid(n), content, scope, actor, originator,
                    json.dumps(tags), ts(day), archived_at, kind, task_ref,
                    kind_label, compute_content_hash(content),
                ),
            )
        for (n, content, scope, actor, tags, day, task_ref, kind_label) \
                in CHECKPOINTS:
            conn.execute(
                "INSERT INTO idea "
                "(id, content, scope, actor_id, originator_id, tags, "
                " created_at, kind, task_ref, kind_label, content_hash) "
                "VALUES (?, ?, ?, ?, NULL, ?, ?, 'checkpoint', ?, ?, ?)",
                (
                    uid(n), content, scope, actor, json.dumps(tags),
                    ts(day), task_ref, kind_label,
                    compute_content_hash(content),
                ),
            )
        for note_n, idea_n, kind, content, actor, day in NOTES:
            conn.execute(
                "INSERT INTO idea_note "
                "(id, idea_id, kind, content, actor_id, originator_id, "
                " created_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?)",
                (uid(note_n), uid(idea_n), kind, content, actor, ts(day)),
            )
        for src, tgt, kind, day in LINKS:
            conn.execute(
                "INSERT INTO idea_link "
                "(source_idea_id, target_idea_id, kind, created_at) "
                "VALUES (?, ?, ?, ?)",
                (uid(src), uid(tgt), kind, ts(day)),
            )


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: seed_corpus.py <target-store-path>", file=sys.stderr)
        sys.exit(2)
    target = Path(sys.argv[1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    build(target)
    counts = sqlite3.connect(target).execute(
        "SELECT "
        " (SELECT COUNT(*) FROM idea WHERE kind='idea'), "
        " (SELECT COUNT(*) FROM idea WHERE kind='checkpoint'), "
        " (SELECT COUNT(*) FROM idea_note), "
        " (SELECT COUNT(*) FROM idea_link), "
        " (SELECT COUNT(*) FROM actor)"
    ).fetchone()
    print(
        f"Seeded {target}: "
        f"{counts[0]} ideas, {counts[1]} checkpoints, {counts[2]} notes, "
        f"{counts[3]} links, {counts[4]} actors."
    )


if __name__ == "__main__":
    main()
