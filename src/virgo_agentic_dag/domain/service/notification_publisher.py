"""Fans each event out to the channels subscribed to it, letting none of them stop the caller."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from virgo_agentic_dag.domain.events.event import Event
from virgo_agentic_dag.domain.infra.messaging.notification_subscriber import (
    NotificationSubscriber,
)

logger = logging.getLogger(__name__)


class NotificationPublisher:
    """Fans an event out to its subscribed channels without blocking the caller, isolating each channel's failures."""

    def __init__(
        self, notification_subscribers: list[NotificationSubscriber[Any]]
    ) -> None:
        self._notification_subscribers = notification_subscribers
        self._deliveries: set[asyncio.Task[None]] = set()

    def publish(self, event: Event) -> None:
        """Schedule this event for every channel subscribed to its type, without waiting."""
        logger.debug("publishing %s", type(event).__name__)

        for subscriber in self._notification_subscribers:
            if not isinstance(event, subscriber.get_event_type()):
                continue

            delivery = self._deliver(subscriber, event)
            delivery_task = asyncio.create_task(delivery)

            self._deliveries.add(delivery_task)
            delivery_task.add_done_callback(self._deliveries.discard)

    async def drain(self) -> None:
        """Wait for every scheduled delivery, so none is lost at shutdown."""
        while self._deliveries:
            in_flight = list(self._deliveries)
            await asyncio.gather(*in_flight)

            self._deliveries.difference_update(in_flight)

    async def _deliver(
        self, subscriber: NotificationSubscriber[Any], event: Event
    ) -> None:
        try:
            await subscriber.handle(event)
        except Exception:
            logger.warning(
                "notification subscriber %s failed on %s",
                type(subscriber).__name__,
                type(event).__name__,
                exc_info=True,
            )
