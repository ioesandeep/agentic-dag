"""The delivery route interface a notification channel sends through."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.events.event import Event


class NotificationDispatcher(ABC):
    """Delivers one event over its route, holding whatever conversation state that route needs."""

    @abstractmethod
    async def dispatch(self, event: Event) -> None:
        """Deliver this event over this route."""
