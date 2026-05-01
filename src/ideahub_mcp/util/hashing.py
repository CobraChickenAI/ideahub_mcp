"""Canonical content hashing for deduplication.

The hash is the *only* signal the dedup branch uses past the 5-second
idempotency window. The normalization rules here are load-bearing: changing
them would silently re-partition the corpus along a new dedup axis. Treat
this module as schema, not utility.
"""

from __future__ import annotations

import hashlib
import re

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_for_hash(content: str) -> str:
    """Normalize content prior to hashing.

    Strips leading/trailing whitespace, collapses internal whitespace runs to
    a single space, and lowercases. This collapses cosmetic variations
    (trailing newlines, double spaces, casing) onto the same hash so
    near-identical re-captures dedup.
    """
    return _WHITESPACE_RUN.sub(" ", content.strip()).lower()


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest of normalized content."""
    return hashlib.sha256(normalize_for_hash(content).encode("utf-8")).hexdigest()
