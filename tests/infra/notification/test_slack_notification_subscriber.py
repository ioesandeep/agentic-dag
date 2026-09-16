import io
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.notification.bot_notification_dispatcher import (
    BotNotificationDispatcher,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)

DAG_TOML = """
name = "demo"
db_path = "{db}"
slack_channel = "{channel}"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "hold the run"
"""


def build_command(tmp_path: Path, slack_channel: str) -> TickCommand:
    dag_path = tmp_path / "dag.toml"
    dag_toml = DAG_TOML.format(db=tmp_path / "db.sqlite3", channel=slack_channel)
    dag_path.write_text(dag_toml, encoding="utf-8")

    return TickCommand(dag_path=dag_path)


async def announce(
    tmp_path: Path, slack_channel: str, dispatcher: AsyncMock, event: NodeEvent
) -> None:
    command = build_command(tmp_path, slack_channel)

    async with initialize_context(command, io.StringIO()) as context:
        context.register(BotNotificationDispatcher, lambda context: dispatcher)

        context.get(NotificationPublisher).publish(event)


async def test_notifies_the_configured_route_when_a_node_speaks(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dispatcher = mocker.AsyncMock(spec=BotNotificationDispatcher)
    event = WorkStartedEvent(
        node_id="A",
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title="Summarise a text",
        agent_name="Iris",
    )

    await announce(tmp_path, "#dag", dispatcher, event)

    dispatcher.dispatch.assert_awaited_once_with(event)


async def test_stays_silent_when_no_slack_channel_is_configured(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dispatcher = mocker.AsyncMock(spec=BotNotificationDispatcher)
    event = WorkStartedEvent(
        node_id="A",
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title="Summarise a text",
        agent_name="Iris",
    )

    await announce(tmp_path, "", dispatcher, event)

    dispatcher.dispatch.assert_not_awaited()
