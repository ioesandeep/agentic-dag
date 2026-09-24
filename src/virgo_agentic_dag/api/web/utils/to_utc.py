"""Set the timezone of a timestamp to UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def to_utc(timestamp: datetime | None) -> datetime | None:
    """Return the timestamp with UTC as its timezone, or None when the timestamp is None."""
    if timestamp is None:
        return None

    return timestamp.replace(tzinfo=UTC)
