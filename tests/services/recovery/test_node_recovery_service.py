import io
import os
import subprocess
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.recover_command import RecoverCommand
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.recovery.node_recovery_service import (
    NodeRecoveryService,
)
from virgo_agentic_dag.services.run.dependent_release_service import (
    DependentReleaseService,
)
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)

pytestmark = pytest.mark.behavior

BuildNode = Callable[[NodeState, int, str, str | None], Node]
BuildCommand = Callable[..., RecoverCommand]

WAKE_MESSAGE = "push the branch and open the pull request"


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 9, 5, tzinfo=UTC)


@pytest.fixture
def dead_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()

    return process.pid


@pytest.fixture
def build_command() -> BuildCommand:
    return lambda cause=RecoveryCauseEnum.TURN_CAP_REACHED, **overrides: RecoverCommand(
        dag_path=Path("dag.toml"),
        node_id="A",
        cause=cause,
        action="woke it where the transcript stopped",
        **overrides,
    )


@pytest.fixture
def out(build_command: BuildCommand) -> Iterator[io.StringIO]:
    out = io.StringIO()
    token = bind_context(ApplicationContext(build_command(), out))

    yield out

    unbind_context(token)


@pytest.fixture
def build_node(now: datetime) -> BuildNode:
    return lambda state, pid, resume_token, marks_before: Node(
        id="A",
        state=state.value,
        created_at=now,
        updated_at=now,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            resume_token=resume_token,
            node_id="A",
            worktree=WorkTree(
                id=3,
                agent_id="agent-A",
                name="A",
                absolute_path="/ws/A",
                marks='{"comment": 9}',
                created_at=now,
            ),
            sessions=[
                AgentSession(
                    id=7,
                    agent_id="agent-A",
                    started_at=now,
                    ended_at=now,
                    triggered_by="wake",
                    pid=pid,
                    marks_before=marks_before,
                )
            ],
        ),
    )


@pytest.fixture
def graph() -> Graph:
    return Graph(
        name="demo", nodes=[GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)]
    )


@pytest.mark.parametrize("has_parked_dependent", [False, True])
@pytest.mark.parametrize("is_registered", [False, True])
async def test_recover_resumes_the_conversation_and_writes_the_row_when_a_message_is_given(
    has_parked_dependent: bool,
    is_registered: bool,
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    graph: Graph,
    dead_pid: int,
    now: datetime,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.NEEDS_HUMAN, dead_pid, "token-A", None
    )

    graph_nodes = [*graph.nodes, GraphNode(id="B", depends_on=("A",))]
    release_graph = Graph(name="demo", nodes=graph_nodes)

    dependent = Node(id="B", state=NodeState.NEEDS_HUMAN.value)
    node_repo.get_nodes_by_ids.return_value = (
        [dependent] if has_parked_dependent else []
    )

    audit_entry = AuditEntry(
        node_id="B",
        state=NodeState.NEEDS_HUMAN.value,
        note="upstream node A stopped, so this one can never start",
        created_at=now,
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    audit_entry_repo.get_all.return_value = [audit_entry]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    dependent_release_service = DependentReleaseService(
        graph=release_graph,
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
    )

    woken_session = AgentSession(
        agent_id="agent-A", started_at=now, triggered_by="wake", pid=4242
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = woken_session

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)

    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = release_graph

    scheduled_job = ScheduledJob(label="fyi.virgo.dag.demo")
    registered_job = None if is_registered else scheduled_job

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.ensure_registered.return_value = registered_job

    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=agent_session_repo,
        audit_entry_repo=audit_entry_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=notification_publisher,
        graph_builder=graph_builder,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=dependent_release_service,
    )

    command = build_command(wake_message=WAKE_MESSAGE)

    exit_code = await service.recover(command)

    node_recovery = node_recovery_repo.add.await_args.args[0]

    agent_session_repo.add.assert_awaited_once_with(woken_session)
    assert exit_code is ExitCode.SUCCESS
    assert agent_launcher.wake.await_args.args[1] == WAKE_MESSAGE

    state_changes = [call.args[:2] for call in node_repo.update_state.await_args_list]
    expected_changes = [("A", NodeState.IN_PROGRESS)]
    if has_parked_dependent:
        expected_changes.append(("B", NodeState.PENDING))

    assert state_changes == expected_changes

    assert (node_recovery.session_id, node_recovery.cause) == (7, "turn_cap_reached")
    node_repo.spend_recovery_attempt.assert_awaited_once_with("A")

    run_schedule_service.ensure_registered.assert_awaited_once_with(command.dag_path)

    output = out.getvalue()
    has_schedule_message = "this host will run fyi.virgo.dag.demo" in output

    assert has_schedule_message is (not is_registered)


async def test_recover_writes_the_row_and_wakes_nothing_when_no_message_is_given(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
    now: datetime,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.RESTING, dead_pid, "token-A", None
    )

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    reset_at = now + timedelta(hours=2)

    exit_code = await service.recover(
        build_command(cause=RecoveryCauseEnum.USAGE_LIMIT, recover_at=reset_at)
    )

    node_recovery = node_recovery_repo.add.await_args.args[0]

    agent_launcher.wake.assert_not_awaited()
    node_repo.update_state.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()

    assert exit_code is ExitCode.SUCCESS
    assert (node_recovery.cause, node_recovery.recover_at) == ("usage_limit", reset_at)
    node_repo.spend_recovery_attempt.assert_awaited_once_with("A")


async def test_recover_moves_the_node_to_needs_human_when_it_is_unrecoverable(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.ERRORED, dead_pid, "token-A", None
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=mocker.MagicMock(spec=NodeRecoveryRepo),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=audit_entry_repo,
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={},
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(
        build_command(cause=RecoveryCauseEnum.OVERDUE, recoverable=False)
    )

    audit_entry = audit_entry_repo.save.await_args.args[0]

    assert exit_code is ExitCode.SUCCESS
    node_repo.spend_recovery_attempt.assert_awaited_once_with("A")

    assert node_repo.update_state.await_args.args[:2] == ("A", NodeState.NEEDS_HUMAN)
    assert audit_entry.note.startswith(
        "the recovery agent marked it unrecoverable: overdue"
    )


async def test_recover_restores_the_marks_of_the_latest_session_when_asked(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.RESTING, dead_pid, "token-A", '{"comment": 4}'
    )

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=work_tree_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={},
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(build_command(restore_marks=True))

    restored_worktree = work_tree_repo.advance_marks.await_args.args[0]

    node_recovery_repo.add.assert_awaited_once()
    assert exit_code is ExitCode.SUCCESS
    assert (restored_worktree.id, restored_worktree.marks) == (3, '{"comment": 4}')


async def test_recover_writes_no_row_when_the_session_recorded_no_marks(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.RESTING, dead_pid, "token-A", None
    )

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=work_tree_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={},
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(build_command(restore_marks=True))

    work_tree_repo.advance_marks.assert_not_awaited()
    node_recovery_repo.add.assert_not_awaited()
    node_repo.spend_recovery_attempt.assert_not_awaited()

    assert exit_code is ExitCode.FAILURE
    assert "no watermarks recorded before its latest session" in out.getvalue()


async def test_recover_writes_no_row_when_the_process_of_the_node_is_alive(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.RESTING, os.getpid(), "token-A", None
    )

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(build_command(wake_message=WAKE_MESSAGE))

    agent_launcher.wake.assert_not_awaited()
    node_recovery_repo.add.assert_not_awaited()
    node_repo.spend_recovery_attempt.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()

    assert exit_code is ExitCode.FAILURE
    assert "nothing acts on a live process" in out.getvalue()


async def test_recover_writes_no_row_when_the_node_has_no_conversation_to_resume(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(NodeState.ERRORED, dead_pid, "", None)

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(build_command(wake_message=WAKE_MESSAGE))

    agent_launcher.wake.assert_not_awaited()
    node_recovery_repo.add.assert_not_awaited()
    node_repo.spend_recovery_attempt.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()

    assert exit_code is ExitCode.FAILURE
    assert "retry --reset" in out.getvalue()


@pytest.mark.parametrize("state", [NodeState.IN_PROGRESS, NodeState.MERGED])
async def test_recover_writes_no_row_when_the_node_has_not_stopped(
    state: NodeState,
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(state, dead_pid, "token-A", None)

    node_recovery_repo = mocker.MagicMock(spec=NodeRecoveryRepo)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=node_recovery_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    exit_code = await service.recover(build_command(wake_message=WAKE_MESSAGE))

    agent_launcher.wake.assert_not_awaited()
    node_recovery_repo.add.assert_not_awaited()
    node_repo.spend_recovery_attempt.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()

    assert exit_code is ExitCode.FAILURE
    assert state.value in out.getvalue()


async def test_recover_registers_nothing_when_the_agent_fails_to_wake(
    mocker: MockerFixture,
    out: io.StringIO,
    build_command: BuildCommand,
    build_node: BuildNode,
    graph: Graph,
    dead_pid: int,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        NodeState.NEEDS_HUMAN, dead_pid, "token-A", None
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.side_effect = OSError("agent process cannot start")

    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = graph

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    service = NodeRecoveryService(
        node_repo=node_repo,
        node_recovery_repo=mocker.MagicMock(spec=NodeRecoveryRepo),
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=graph_builder,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
        run_schedule_service=run_schedule_service,
        dependent_release_service=mocker.MagicMock(spec=DependentReleaseService),
    )

    command = build_command(wake_message=WAKE_MESSAGE)

    exit_code = await service.recover(command)

    assert exit_code is ExitCode.FAILURE
    node_repo.update_state.assert_not_awaited()
    run_schedule_service.ensure_registered.assert_not_awaited()
    assert "this host will run" not in out.getvalue()
