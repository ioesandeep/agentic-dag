import subprocess
from collections.abc import AsyncGenerator, Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.domain.command.stop_command import StopCommand
from virgo_agentic_dag.domain.exceptions.run.stop_refused import StopRefused
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_agent_session_repo import (
    SqliteAgentSessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.services.recovery.recovery_scan_service import (
    RecoveryScanService,
)
from virgo_agentic_dag.services.stop.node_stop_service import NodeStopService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 9, 23, tzinfo=UTC)
COMMAND = StopCommand(dag_path=Path("dag.toml"), node_id="A")

BuildNode = Callable[[NodeState, int], Node]


@pytest.fixture
def running_process() -> Iterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(["sleep", "60"])

    yield process

    process.kill()
    process.wait()


@pytest.fixture
def dead_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()

    return process.pid


@pytest.fixture
async def database(tmp_path: Path) -> AsyncGenerator[SqliteDatabase]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'db.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    yield database

    await database.dispose()


@pytest.fixture
def build_node(tmp_path: Path) -> BuildNode:
    return lambda state, pid: Node(
        id="A",
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
        recovery_attempts_allowed=2,
        agent=NodeAgent(
            id="agent-A",
            name="claude",
            node_id="A",
            worktree=WorkTree(
                agent_id="agent-A",
                name="A",
                absolute_path=str(tmp_path / "A"),
                created_at=NOW,
            ),
            sessions=[
                AgentSession(
                    agent_id="agent-A", started_at=NOW, triggered_by="launch", pid=pid
                )
            ],
        ),
    )


@pytest.fixture
def graph() -> Graph:
    return Graph(
        name="demo", nodes=[GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)]
    )


async def test_stop_moves_the_node_to_needs_human_when_its_session_is_running(
    mocker: MockerFixture,
    database: SqliteDatabase,
    build_node: BuildNode,
    graph: Graph,
    running_process: subprocess.Popen[bytes],
) -> None:
    node = build_node(NodeState.IN_PROGRESS, running_process.pid)
    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    audit_entry_repo = SqliteAuditEntryRepo(database)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = graph
    service = NodeStopService(
        node_repo=node_repo,
        agent_session_repo=SqliteAgentSessionRepo(database),
        audit_entry_repo=audit_entry_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=graph_builder,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )

    await service.stop(COMMAND, NOW)

    stopped_node = await node_repo.read("A")
    audit_entries = await audit_entry_repo.get_all()
    assert stopped_node is not None
    stopped_session = stopped_node.get_latest_session()
    assert stopped_session is not None
    assert agent_launcher.stop.await_args.args[0].pid == running_process.pid
    assert (stopped_session.end_state, stopped_session.exit_code) == ("stopped", None)
    assert stopped_node.state == NodeState.NEEDS_HUMAN.value
    assert audit_entries[0].note == "the stop command stops the session"


async def test_get_recoverable_nodes_returns_no_nodes_when_stop_command_stops_the_latest_session(
    mocker: MockerFixture,
    database: SqliteDatabase,
    build_node: BuildNode,
    graph: Graph,
    running_process: subprocess.Popen[bytes],
) -> None:
    node = build_node(NodeState.IN_PROGRESS, running_process.pid)
    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    node_repo = SqliteNodeRepo(database)
    audit_entry_repo = SqliteAuditEntryRepo(database)
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.stop.side_effect = lambda session: running_process.kill()
    graph_builder = mocker.MagicMock(spec=GraphBuilder)
    graph_builder.build_from_path.return_value = graph
    node_stop_service = NodeStopService(
        node_repo=node_repo,
        agent_session_repo=SqliteAgentSessionRepo(database),
        audit_entry_repo=audit_entry_repo,
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=graph_builder,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )
    recovery_scan_service = RecoveryScanService(
        node_repo=node_repo,
        node_recovery_repo=SqliteNodeRecoveryRepo(database),
        audit_entry_repo=audit_entry_repo,
    )
    await node_stop_service.stop(COMMAND, NOW)
    running_process.wait()

    recoverable_nodes = await recovery_scan_service.get_recoverable_nodes(NOW)

    assert recoverable_nodes == []


async def test_stop_raises_stop_refused_when_no_node_has_the_command_id(
    mocker: MockerFixture, database: SqliteDatabase
) -> None:
    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = NodeStopService(
        node_repo=SqliteNodeRepo(database),
        agent_session_repo=SqliteAgentSessionRepo(database),
        audit_entry_repo=SqliteAuditEntryRepo(database),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )

    with pytest.raises(StopRefused, match="A is not a node of this run"):
        await service.stop(COMMAND, NOW)

    agent_launcher.stop.assert_not_awaited()


async def test_stop_raises_stop_refused_when_the_node_is_not_in_progress(
    mocker: MockerFixture,
    database: SqliteDatabase,
    build_node: BuildNode,
    running_process: subprocess.Popen[bytes],
) -> None:
    node = build_node(NodeState.RESTING, running_process.pid)
    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = NodeStopService(
        node_repo=SqliteNodeRepo(database),
        agent_session_repo=SqliteAgentSessionRepo(database),
        audit_entry_repo=SqliteAuditEntryRepo(database),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )

    with pytest.raises(
        StopRefused, match="stop fails for A because its state is resting"
    ):
        await service.stop(COMMAND, NOW)

    agent_launcher.stop.assert_not_awaited()


async def test_stop_raises_stop_refused_when_the_session_is_not_running(
    mocker: MockerFixture,
    database: SqliteDatabase,
    build_node: BuildNode,
    dead_pid: int,
) -> None:
    node = build_node(NodeState.IN_PROGRESS, dead_pid)
    async with database.open_session() as db_session:
        db_session.add(node)
        await db_session.commit()

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    service = NodeStopService(
        node_repo=SqliteNodeRepo(database),
        agent_session_repo=SqliteAgentSessionRepo(database),
        audit_entry_repo=SqliteAuditEntryRepo(database),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        graph_builder=mocker.MagicMock(spec=GraphBuilder),
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )

    with pytest.raises(
        StopRefused, match="A has no running session; the next tick settles it"
    ):
        await service.stop(COMMAND, NOW)

    agent_launcher.stop.assert_not_awaited()
