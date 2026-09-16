"""Builds the reader a watcher gets its run's events through."""

from __future__ import annotations

import urllib.parse
from collections.abc import Sequence

from virgo_agentic_dag.infra.streaming.urllib_event_stream import UrllibEventStream
from virgo_agentic_dag.services.watching.event_reader import EventReader


class SubscriptionFactory:
    """Builds an event reader whose stream url is scoped to the given topics."""

    def build(self, sse_url: str, topics: Sequence[str]) -> EventReader:
        """Return a reader for these topics only."""
        url = self.get_url(sse_url, topics)

        return EventReader(UrllibEventStream(url))

    def get_url(self, sse_url: str, topics: Sequence[str]) -> str:
        """Return the stream url with these topics as its query."""
        separator = "&" if "?" in sse_url else "?"
        encoded = urllib.parse.quote(",".join(topics), safe=",/")

        return f"{sse_url}{separator}topics={encoded}"
