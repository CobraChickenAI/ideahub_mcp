"""Shared annotated types for tool input models.

The ``StrList`` alias bakes the ``coerce_str_list`` defensive coercion into
the type system itself, so a developer who adds a new list-typed tool
parameter cannot forget the ``field_validator(mode="before")`` plumbing —
the type does it. The lint guard in tests/test_lint.py enforces that no
tool input model declares a bare ``list[str]``; ``StrList`` is the only
allowed shape.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator

from ideahub_mcp.util.coerce import coerce_str_list

StrList = Annotated[list[str], BeforeValidator(coerce_str_list)]
