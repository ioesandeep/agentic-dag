from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.events.event import Event
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.infra.messaging.notification_subscriber import (
    NotificationSubscriber,
)
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 7, 31, tzinfo=UTC)


@dataclass(frozen=True)
class OtherEvent(Event):
    """The second event type the publisher routes by, which the package declares nowhere else."""

    label: str


@pytest.fixture
def event() -> NodeEvent:
    return WorkStartedEvent(
        node_id="A",
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title="Summarise a text",
        agent_name="Iris",
    )


async def test_delivers_to_every_subscriber_when_the_event_is_their_type(
    mocker: MockerFixture, event: NodeEvent
) -> None:
    first = mocker.MagicMock(spec=NotificationSubscriber)
    first.get_event_type.return_value = NodeEvent

    second = mocker.MagicMock(spec=NotificationSubscriber)
    second.get_event_type.return_value = NodeEvent

    publisher = NotificationPublisher(notification_subscribers=[first, second])

    publisher.publish(event)
    await publisher.drain()

    first.handle.assert_awaited_once_with(event)
    second.handle.assert_awaited_once_with(event)


async def test_skips_a_subscriber_when_the_event_is_not_its_type(
    mocker: MockerFixture, event: NodeEvent
) -> None:
    node_subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    node_subscriber.get_event_type.return_value = NodeEvent

    other_subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    other_subscriber.get_event_type.return_value = OtherEvent

    publisher = NotificationPublisher(
        notification_subscribers=[node_subscriber, other_subscriber]
    )

    publisher.publish(event)
    await publisher.drain()

    node_subscriber.handle.assert_awaited_once_with(event)
    other_subscriber.handle.assert_not_awaited()


async def test_returns_before_delivery_when_publishing(
    mocker: MockerFixture, event: NodeEvent
) -> None:
    subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    subscriber.get_event_type.return_value = NodeEvent

    publisher = NotificationPublisher(notification_subscribers=[subscriber])

    publisher.publish(event)

    subscriber.handle.assert_not_awaited()

    await publisher.drain()

    subscriber.handle.assert_awaited_once_with(event)


async def test_still_delivers_to_the_others_when_one_channel_fails(
    mocker: MockerFixture, event: NodeEvent
) -> None:
    exploding = mocker.MagicMock(spec=NotificationSubscriber)
    exploding.get_event_type.return_value = NodeEvent
    exploding.handle.side_effect = ValueError("channel down")

    surviving = mocker.MagicMock(spec=NotificationSubscriber)
    surviving.get_event_type.return_value = NodeEvent

    publisher = NotificationPublisher(notification_subscribers=[exploding, surviving])

    publisher.publish(event)
    await publisher.drain()

    surviving.handle.assert_awaited_once_with(event)


async def test_returns_at_once_when_draining_with_nothing_in_flight(
    mocker: MockerFixture,
) -> None:
    subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    subscriber.get_event_type.return_value = NodeEvent

    publisher = NotificationPublisher(notification_subscribers=[subscriber])

    await publisher.drain()

    subscriber.handle.assert_not_awaited()
