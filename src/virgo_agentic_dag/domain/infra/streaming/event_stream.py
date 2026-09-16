"""The port that yields webhook deliveries from the notification server."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class EventStream(ABC):
    """Yields raw event names from one server connection until it closes."""

    @abstractmethod
    def subscribe(self) -> Iterator[str]:
        """Yield each delivery's event name, returning when the connection closes.

        Raises:
            StreamError: when the connection cannot be opened or dies mid-read.
        """

    @abstractmethod
    def close(self) -> None:
        """End the connection so a read parked on it stops."""
