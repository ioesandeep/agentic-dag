"""The status supervision reports for a launched agent session."""

from __future__ import annotations

from enum import Enum


class SessionStatus(Enum):
    ALIVE = "alive"
    FINISHED = "finished"
    OVERDUE = "overdue"
