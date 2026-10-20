from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.pull_request_details import PullRequestDetails
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_agent_repo import (
    SqliteNodeAgentRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.services.run.adopted_node_importer import AdoptedNodeImporter

pytestmark = pytest.mark.integration


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[SqliteDatabase]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'run.sqlite3'}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()

    try:
        yield database
    finally:
        await database.dispose()


@pytest.mark.parametrize("reset", [False, True])
async def test_import_node_reuses_the_agent_row_when_the_node_is_imported_again(
    mocker: MockerFixture, database: SqliteDatabase, reset: bool
) -> None:
    current_time = datetime(2026, 10, 19, tzinfo=UTC)

    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    pr_details = PullRequestDetails(
        number=16,
        repository="acme/virgo",
        url="https://github.com/acme/virgo/pull/16",
        head_branch="fix/login",
    )

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=current_time
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.side_effect = lambda graph_node, instructions, agent: (
        AgentSession(
            agent_id=agent.id, started_at=current_time, triggered_by="launch", pid=4242
        )
    )

    node_agent_repo = SqliteNodeAgentRepo(database)

    node_repo = SqliteNodeRepo(database)

    audit_entry_repo = SqliteAuditEntryRepo(database)

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    importer = AdoptedNodeImporter(
        workspace=workspace,
        node_repo=node_repo,
        node_agent_repo=node_agent_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        agent_launchers={ExecutorAgent.CLAUDE: agent_launcher},
    )

    await importer.import_node(graph_node, pr_details)

    recorded_agent = await node_agent_repo.get_by_node_id("A")

    assert recorded_agent is not None

    recorded_resume_token = recorded_agent.resume_token
    recorded_session_id = recorded_agent.sessions[0].id

    if reset:
        recorded_agent.resume_token = ""
        await node_agent_repo.save(recorded_agent)

    agent_launcher.wake.return_value = AgentSession(
        agent_id=recorded_agent.id,
        started_at=current_time,
        triggered_by="wake",
        pid=4243,
    )

    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/retried-A", created_at=current_time
    )

    await importer.import_node(graph_node, pr_details)

    async with database.open_session() as session:
        statement = select(NodeAgent.id).where(NodeAgent.node_id == "A")
        agent_ids = await session.scalars(statement)

        assert agent_ids.all() == [recorded_agent.id]

    retried_agent = await node_agent_repo.get_by_node_id("A")

    assert retried_agent is not None

    assert len(retried_agent.sessions) == 2
    assert retried_agent.sessions[0].id == recorded_session_id

    assert retried_agent.worktree is not None
    assert retried_agent.worktree.absolute_path == "/ws/retried-A"

    if reset:
        assert retried_agent.resume_token
        assert retried_agent.resume_token != recorded_resume_token

        assert agent_launcher.launch.await_count == 2
        agent_launcher.wake.assert_not_awaited()
    else:
        assert retried_agent.resume_token == recorded_resume_token

        agent_launcher.wake.assert_awaited_once()
        agent_launcher.launch.assert_awaited_once()
