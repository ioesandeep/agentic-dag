"""The counts one control pass produced, for reporting and tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TickResponse:
    events_applied: int = 0
    sessions_started: int = 0
    is_complete: bool = False

    def increment_with(self, other: TickResponse) -> TickResponse:
        """Return the sum of these two responses' counts."""
        return TickResponse(
            self.events_applied + other.events_applied,
            self.sessions_started + other.sessions_started,
            self.is_complete or other.is_complete,
        )
