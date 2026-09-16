import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.messaging.notification_dispatcher import (
    NotificationDispatcher,
)
from virgo_agentic_dag.domain.notifications.notification_dispatcher_type import (
    NotificationDispatcherType,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.notification.slack_notification_dispatcher_factory import (
    SlackNotificationDispatcherFactory,
)

pytestmark = pytest.mark.unit


def build_spec(target: NotificationDispatcherType) -> DagSpec:
    return DagSpec(name="demo", nodes=(), notification_dispatcher=target)


def test_returns_the_bot_route_when_the_run_is_configured_for_a_bot(
    mocker: MockerFixture,
) -> None:
    bot_dispatcher = mocker.MagicMock(spec=NotificationDispatcher)
    factory = SlackNotificationDispatcherFactory(
        build_spec(NotificationDispatcherType.BOT), bot_dispatcher
    )

    assert factory.get_dispatcher() is bot_dispatcher


def test_raises_when_the_configured_route_is_not_built_yet(
    mocker: MockerFixture,
) -> None:
    bot_dispatcher = mocker.MagicMock(spec=NotificationDispatcher)
    factory = SlackNotificationDispatcherFactory(
        build_spec(NotificationDispatcherType.MCP), bot_dispatcher
    )

    with pytest.raises(ConfigError, match="mcp"):
        factory.get_dispatcher()
