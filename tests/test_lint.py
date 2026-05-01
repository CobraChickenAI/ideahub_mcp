"""Build-time architectural guards.

These tests fail the build when a structural contract is bypassed.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "ideahub_mcp"


def _is_list_str_annotation(node: ast.expr) -> bool:
    """Match a bare ``list[str]`` annotation node, however parenthesized."""
    if not isinstance(node, ast.Subscript):
        return False
    value = node.value
    if not (isinstance(value, ast.Name) and value.id == "list"):
        return False
    slice_node = node.slice
    return isinstance(slice_node, ast.Name) and slice_node.id == "str"


def test_no_bare_list_str_in_input_models() -> None:
    """Input models must use ``StrList`` (not bare ``list[str]``).

    ``StrList`` (util/types.py) carries the ``coerce_str_list`` BeforeValidator
    so MCP host bridges that JSON-stringify list params don't silently fail
    Pydantic validation. The bare annotation re-introduces that fragility,
    which is why a developer adding a new list-typed input parameter must
    not be able to forget it.

    A class is treated as an "input model" when its name ends in ``Input``.
    """
    offenders: list[str] = []
    for p in SRC.rglob("*.py"):
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError:
            continue
        for cls in ast.walk(tree):
            if not (isinstance(cls, ast.ClassDef) and cls.name.endswith("Input")):
                continue
            for stmt in cls.body:
                if not isinstance(stmt, ast.AnnAssign):
                    continue
                if _is_list_str_annotation(stmt.annotation):
                    target = stmt.target
                    field = target.id if isinstance(target, ast.Name) else "<expr>"
                    offenders.append(
                        f"{p.relative_to(SRC)}::{cls.name}.{field}"
                    )
    assert offenders == [], (
        "Bare list[str] in input model fields — use StrList from "
        f"util/types.py: {offenders}"
    )
