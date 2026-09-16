"""The port that asks whether the server behind an event stream is still alive."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.infra.streaming.stream_health import StreamHealth


class StreamHealthCheck(ABC):
    """Answers whether the server serving a stream url is up, without opening a stream."""

    @abstractmethod
    async def check(self, sse_url: str) -> StreamHealth:
        """Return whether the server behind ``sse_url`` answered, and the url asked."""
