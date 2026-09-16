"""Fill a label's placeholders, so every user-facing string is written in one catalog."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def format_label(value: str, args: Mapping[str, Any] | None = None) -> str:
    """Return the label with each `{placeholder}` replaced by the argument named for it."""
    if not args:
        return value

    return value.format(**args)
