"""Defines the watcher configuration that remains fixed after startup."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WatchPlan:
    # the event stream url, without the topics query
    sse_url: str
    # the stored start command the watcher fires
    argv: tuple[str, ...]
    working_directory: Path
    # The watcher refreshes topics after this many seconds of stream inactivity.
    refresh_seconds: int
