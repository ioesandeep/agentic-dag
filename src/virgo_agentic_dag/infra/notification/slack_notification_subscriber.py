"""The notification channel that delivers events to Slack."""

from __future__ import annotations

from virgo_agentic_dag.bootstrap.application_context import get_context
from virgo_agentic_dag.domain.events.event import Event
from virgo_agentic_dag.domain.infra.messaging.notification_subscriber import (
    NotificationSubscriber,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.notification.slack_notification_dispatcher_factory import (
    SlackNotificationDispatcherFactory,
)


class SlackNotificationSubscriber(NotificationSubscriber[Event]):
    """Passes each event to the Slack route this run is configured for."""

    def get_event_type(self) -> type[Event]:
        return Event

    async def handle(self, event: Event) -> None:
        context = get_context()
        dag_spec = context.get(DagSpec)
        if not dag_spec.slack_channel:
            return

        dispatcher = context.get(SlackNotificationDispatcherFactory).get_dispatcher()
        await dispatcher.dispatch(event)
