from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.command.skip_command import SkipCommand
from virgo_agentic_dag.domain.exceptions.run.skip_refused import SkipRefused
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.run.dependent_release_service import (
    DependentReleaseService,
)
from virgo_agentic_dag.services.run.node_skip_service import NodeSkipService
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 9, 7, tzinfo=UTC)
COMMAND = SkipCommand(dag_path=Path("dag.toml"), node_id="A")

BuildNode = Callable[..., Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id, state, agent=None: Node(
        id=node_id,
        title="",
        name="",
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
        agent=agent,
    )


@pytest.mark.parametrize(
    "state",
    [
        NodeState.PENDING,
        NodeState.RESTING,
        NodeState.ERRORED,
        NodeState.NEEDS_HUMAN,
    ],
)
async def test_skip_marks_the_node_skipped_when_it_is_waiting_or_stopped(
    state: NodeState, mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", state)
    node_repo.get_nodes_by_ids.return_value = []

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.ensure_registered.return_value = None
    dependent_release_service = mocker.MagicMock(spec=DependentReleaseService)
    dependent_release_service.release.return_value = []

    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        dependent_release_service=dependent_release_service,
        run_schedule_service=run_schedule_service,
    )

    pending_node_ids = await service.skip(COMMAND, NOW)

    audit_entry = audit_entry_repo.save.await_args.args[0]
    node_event = notification_publisher.publish.call_args.args[0]

    assert pending_node_ids == []
    node_repo.update_state.assert_awaited_once_with("A", NodeState.SKIPPED, NOW)

    assert audit_entry.state == NodeState.SKIPPED.value
    assert audit_entry.note == "a human skipped it"
    assert node_event.type is NotificationType.SKIPPED


@pytest.mark.parametrize("is_registered", [False, True])
@pytest.mark.parametrize(
    "state", [NodeState.ERRORED, NodeState.SKIPPED, NodeState.NEEDS_HUMAN]
)
async def test_skip_returns_the_descendant_to_pending_when_it_stopped_without_an_agent(
    is_registered: bool, state: NodeState, mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph = Graph(
        name="demo",
        nodes=[
            GraphNode(id="A"),
            GraphNode(id="B", depends_on=("A",)),
            GraphNode(id="D", depends_on=("B",)),
            GraphNode(id="F", depends_on=("B",)),
            GraphNode(id="E"),
            GraphNode(id="G", depends_on=("A",)),
        ],
    )

    started_agent = NodeAgent(id="agent-D", name="claude", node_id="D")
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", state)
    node_repo.get_nodes_by_ids.return_value = [
        build_node("B", NodeState.NEEDS_HUMAN),
        build_node("D", NodeState.NEEDS_HUMAN, agent=started_agent),
        build_node("F", NodeState.PENDING),
        build_node("G", NodeState.NEEDS_HUMAN),
    ]

    audit_entry = AuditEntry(
        node_id="B",
        state=NodeState.NEEDS_HUMAN.value,
        note="upstream node A stopped, so this one can never start",
        created_at=NOW,
    )

    independent_failure = AuditEntry(
        node_id="G",
        state=NodeState.NEEDS_HUMAN.value,
        note="executor missing is not registered",
        created_at=NOW,
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [audit_entry, independent_failure]
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    dependent_release_service = DependentReleaseService(
        graph=graph,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
    )

    scheduled_job = ScheduledJob(label="fyi.virgo.dag.demo")
    registered_job = None if is_registered else scheduled_job
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.ensure_registered.return_value = registered_job

    emit = mocker.patch("virgo_agentic_dag.services.run.node_skip_service.emit")

    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        dependent_release_service=dependent_release_service,
        run_schedule_service=run_schedule_service,
    )

    pending_node_ids = await service.skip(COMMAND, NOW)

    assert pending_node_ids == ["B"]
    node_repo.get_nodes_by_ids.assert_awaited_once_with(["B", "D", "F", "G"])

    node_repo.update_state.assert_any_await("B", NodeState.PENDING, NOW)
    assert node_repo.update_state.await_count == 2

    run_schedule_service.ensure_registered.assert_awaited_once_with(COMMAND.dag_path)
    if is_registered:
        emit.assert_not_called()
    else:
        emit.assert_called_once_with(
            "this host will run fyi.virgo.dag.demo until the run settles\n\n"
        )


async def test_skip_refuses_the_node_when_the_run_does_not_have_it(
    mocker: MockerFixture,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = None

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
        run_schedule_service=run_schedule_service,
    )

    with pytest.raises(SkipRefused, match="A is not a node of this run"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()


async def test_skip_refuses_the_node_when_it_is_in_progress(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.IN_PROGRESS)

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
        run_schedule_service=run_schedule_service,
    )

    with pytest.raises(SkipRefused, match="A is in progress and cannot be skipped"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()


async def test_skip_refuses_the_node_when_it_has_merged(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.MERGED)

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
        run_schedule_service=run_schedule_service,
    )

    with pytest.raises(SkipRefused, match="A has merged and cannot be skipped"):
        await service.skip(COMMAND, NOW)

    node_repo.update_state.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()


async def test_skip_registers_no_host_job_when_no_node_changes_state(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node("A", NodeState.SKIPPED)
    node_repo.get_nodes_by_ids.return_value = []

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    dependent_release_service = mocker.MagicMock(spec=DependentReleaseService)
    dependent_release_service.release.return_value = []
    service = NodeSkipService(
        node_repo=node_repo,
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        dependent_release_service=dependent_release_service,
        run_schedule_service=run_schedule_service,
    )

    pending_node_ids = await service.skip(COMMAND, NOW)

    assert pending_node_ids == []
    run_schedule_service.ensure_registered.assert_not_awaited()
