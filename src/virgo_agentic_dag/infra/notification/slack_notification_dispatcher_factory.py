"""Choosing how a run reaches Slack, so the channel itself never names a route."""

from __future__ import annotations

from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.messaging.notification_dispatcher import (
    NotificationDispatcher,
)
from virgo_agentic_dag.domain.notifications.notification_dispatcher_type import (
    NotificationDispatcherType,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec


class SlackNotificationDispatcherFactory:
    """Hands back the delivery route this run's configuration asks for."""

    def __init__(
        self, dag_spec: DagSpec, bot_dispatcher: NotificationDispatcher
    ) -> None:
        self._dag_spec = dag_spec
        self._bot_dispatcher = bot_dispatcher

    def get_dispatcher(self) -> NotificationDispatcher:
        """Return the dispatcher this run is configured for, raising ConfigError when unbuilt."""
        target = self._dag_spec.notification_dispatcher
        if target is NotificationDispatcherType.BOT:
            return self._bot_dispatcher

        raise ConfigError(
            f"config: notification_dispatcher {target.value} is not built yet"
        )
