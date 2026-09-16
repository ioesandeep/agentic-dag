"""The values a watcher resolves once at startup and never re-reads."""

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
    # the owner/repo part of every topic this run subscribes to
    repo_slug: str
    # seconds of stream silence before the watcher re-reads the run's pull requests
    refresh_seconds: int
