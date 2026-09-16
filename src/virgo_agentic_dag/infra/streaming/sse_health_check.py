"""A StreamHealthCheck that reads the sse server's health route over HTTP with urllib."""

from __future__ import annotations

import asyncio
import logging
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus

from virgo_agentic_dag.domain.infra.streaming.stream_health import StreamHealth
from virgo_agentic_dag.domain.infra.streaming.stream_health_check import (
    StreamHealthCheck,
)

logger = logging.getLogger(__name__)

HEALTH_PATH = "/healthz"
DEFAULT_TIMEOUT_SECONDS = 2.0


class SseHealthCheck(StreamHealthCheck):
    """Reads the sse server's health route, counting any failure to answer as not alive."""

    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds

    async def check(self, sse_url: str) -> StreamHealth:
        """Return whether the server behind ``sse_url`` answered, and the url asked."""
        url = self._get_health_url(sse_url)
        is_alive = await asyncio.to_thread(self._is_healthy, url)

        return StreamHealth(url=url, is_alive=is_alive)

    def _get_health_url(self, sse_url: str) -> str:
        parsed = urllib.parse.urlsplit(sse_url)

        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, HEALTH_PATH, "", "")
        )

    def _is_healthy(self, url: str) -> bool:
        try:
            with urllib.request.urlopen(url, timeout=self._timeout_seconds) as response:
                return HTTPStatus(response.status).is_success
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            logger.debug("health check of %s failed: %s", url, error)

            return False
