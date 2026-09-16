"""An EventStream that reads server-sent events over HTTP with urllib."""

from __future__ import annotations

import logging
import socket
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator
from http.client import HTTPResponse

from virgo_agentic_dag.domain.exceptions.platform.stream_error import StreamError
from virgo_agentic_dag.domain.infra.streaming.event_stream import EventStream

logger = logging.getLogger(__name__)


class UrllibEventStream(EventStream):
    """Holds one HTTP connection open and yields each SSE data payload."""

    def __init__(self, url: str, read_timeout_seconds: float = 60.0) -> None:
        self._url = url
        self._read_timeout_seconds = read_timeout_seconds
        self._response: HTTPResponse | None = None
        self._is_closed = False

    def subscribe(self) -> Iterator[str]:
        """Yield each data payload from the stream until the connection closes.

        Raises:
            StreamError: when the connection cannot be opened or dies mid-read.
        """
        response = self._open()

        with response:
            try:
                yield from self._get_payloads(response)
            except (TimeoutError, OSError) as error:
                raise StreamError(f"connection to {self._url} lost: {error}") from error
            finally:
                self._release(response)

    def close(self) -> None:
        """End the connection so a read parked on it stops."""
        self._is_closed = True
        self._end_read(self._response)

    def _open(self) -> HTTPResponse:
        """Open the connection, ending it if close already ran on another thread."""
        if self._is_closed:
            raise StreamError(f"stream to {self._url} is closed")

        try:
            response: HTTPResponse = urllib.request.urlopen(
                self._url, timeout=self._read_timeout_seconds
            )
        except (urllib.error.URLError, OSError) as error:
            raise StreamError(f"cannot connect to {self._url}: {error}") from error

        self._response = response
        if self._is_closed:
            self._end_read(response)

        return response

    def _release(self, response: HTTPResponse) -> None:
        if self._response is response:
            self._response = None

    def _end_read(self, response: HTTPResponse | None) -> None:
        """Shut the socket down, which is what ends a read already parked on it."""
        if response is None:
            return

        try:
            connection = socket.socket(fileno=response.fileno())
        except (AttributeError, OSError, ValueError):
            return

        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            logger.debug("socket for %s was already down", self._url)
        finally:
            connection.detach()

    def _get_payloads(self, lines: Iterable[bytes]) -> Iterator[str]:
        pending: list[str] = []
        for raw in lines:
            line = raw.decode("utf-8").rstrip("\r\n")
            if not line and pending:
                yield "\n".join(pending)
                pending = []
            elif line.startswith("data:"):
                pending.append(line.removeprefix("data:").lstrip())
