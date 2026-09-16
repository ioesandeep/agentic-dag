"""The lifecycle state the remote platform reports for a pull request."""

from __future__ import annotations

from enum import Enum


class PullRequestState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
