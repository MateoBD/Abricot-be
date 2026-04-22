"""Time-ordered UUID v7 generation for primary keys (see .mcp/abricot_checklist.md §1)."""

from __future__ import annotations

from uuid import UUID

from uuid6 import uuid7


def new_uuid7() -> UUID:
    """Return a new UUID version 7 (RFC draft / uuid6 package)."""
    return uuid7()
