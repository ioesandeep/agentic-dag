"""The subscriber interface each notification channel implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.events.event import Event


class NotificationSubscriber[EventT: Event](ABC):
    """Receives the one event type it subscribes to and renders it for its own medium."""

    @abstractmethod
    def get_event_type(self) -> type[EventT]:
        """Return the event type this channel subscribes to."""

    @abstractmethod
    async def handle(self, event: EventT) -> None:
        """Render and deliver this event in this channel's own format."""
