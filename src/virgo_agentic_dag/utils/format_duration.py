"""Format a duration as hours and minutes for a user-facing message."""

from __future__ import annotations

from datetime import timedelta


def format_duration(duration: timedelta) -> str:
    """Return the duration as `8h 20m`, or as `20m` when it is under an hour."""
    hours, remaining_time = divmod(duration, timedelta(hours=1))
    minutes = remaining_time // timedelta(minutes=1)
    if not hours:
        return f"{minutes}m"

    return f"{hours}h {minutes}m"
