"""What a health check learned about the server behind an event stream url."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StreamHealth:
    """Carries the liveness answer together with the url it was asked of."""

    # the health route the check asked, derived from the stream url
    url: str
    is_alive: bool
