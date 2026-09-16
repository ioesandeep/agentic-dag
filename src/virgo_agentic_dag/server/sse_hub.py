"""In-process routing of webhook arrivals to the SSE connections that asked for them."""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterable


class SseHub:
    """Delivers each published message to the connections subscribed to its topics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[queue.Queue[str], frozenset[str]] = {}

    def subscribe(self, topics: Iterable[str]) -> queue.Queue[str]:
        """Register a queue to receive messages published on these topics."""
        subscriber: queue.Queue[str] = queue.Queue()
        with self._lock:
            self._subscribers[subscriber] = frozenset(topics)

        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[str]) -> None:
        """Drop a connection queue so a closed client stops receiving messages."""
        with self._lock:
            self._subscribers.pop(subscriber, None)

    def publish(self, message: str, topics: Iterable[str]) -> None:
        """Deliver one message to every subscriber whose topics include one of these."""
        published = frozenset(topics)
        with self._lock:
            subscribers = tuple(self._subscribers.items())

        for subscriber, subscribed_topics in subscribers:
            if published & subscribed_topics:
                subscriber.put(message)

    def count_subscribers(self) -> int:
        """Return how many connections are currently subscribed."""
        with self._lock:
            return len(self._subscribers)
