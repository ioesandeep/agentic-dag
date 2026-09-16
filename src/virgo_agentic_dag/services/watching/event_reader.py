"""A background thread that reads an event stream into a queue."""

from __future__ import annotations

import logging
import queue
import threading

from virgo_agentic_dag.domain.exceptions.platform.stream_error import StreamError
from virgo_agentic_dag.domain.infra.streaming.event_stream import EventStream

logger = logging.getLogger(__name__)


class EventReader:
    """Reads a stream on a thread, so its consumer can wait on events with a timeout."""

    def __init__(self, stream: EventStream, reconnect_seconds: float = 5.0) -> None:
        self._stream = stream
        self._reconnect_seconds = reconnect_seconds
        self._events: queue.Queue[str] = queue.Queue()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._read, daemon=True)

    def start(self) -> None:
        """Begin reading the stream in the background."""
        self._thread.start()

    def stop(self) -> None:
        """Stop the reader from reconnecting and end the read it is parked on."""
        self._stopped.set()
        self._stream.close()

    def is_running(self) -> bool:
        """Return whether the reader's thread is still alive."""
        return self._thread.is_alive()

    def get_event(self, timeout_seconds: float) -> str | None:
        """Return the next payload, or None when the wait runs out."""
        try:
            return self._events.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def _read(self) -> None:
        while not self._stopped.is_set():
            try:
                for payload in self._stream.subscribe():
                    self._events.put(payload)
            except StreamError as error:
                logger.info("stream lost, reconnecting: %s", error)

            self._stopped.wait(self._reconnect_seconds)
