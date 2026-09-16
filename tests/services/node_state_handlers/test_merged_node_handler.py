from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.services.node_state_handlers.merged_node_handler import (
    MergedNodeHandler,
)

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)

BuildAgent = Callable[[WorkTree], NodeAgent]


@pytest.fixture
def build_agent() -> BuildAgent:
    return lambda worktree: NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="token",
        node_id="A",
        worktree=worktree,
    )


async def test_reclaims_the_worktree_when_the_node_has_merged(
    mocker: MockerFixture, build_agent: BuildAgent
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", pr_number=12, created_at=NOW
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree)

    node_repo = mocker.MagicMock(spec=NodeRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    workspace = mocker.MagicMock(spec=Workspace)

    handler = MergedNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        work_tree_repo=work_tree_repo,
        workspace=workspace,
    )

    await handler.handle(graph, [graph_node], NOW)

    workspace.remove.assert_awaited_once_with(worktree)
    work_tree_repo.mark_reclaimed.assert_awaited_once()
    assert work_tree_repo.mark_reclaimed.await_args.args[0].id == 1
    node_repo.update_state.assert_not_awaited()
    audit_entry_repo.save.assert_not_awaited()
    notification_publisher.publish.assert_not_called()


async def test_reclaims_nothing_when_the_worktree_is_already_gone(
    mocker: MockerFixture, build_agent: BuildAgent
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        pr_number=12,
        created_at=NOW,
        reclaimed_at=NOW,
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree)

    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    workspace = mocker.MagicMock(spec=Workspace)

    handler = MergedNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        work_tree_repo=work_tree_repo,
        workspace=workspace,
    )

    await handler.handle(graph, [graph_node], NOW)

    workspace.remove.assert_not_awaited()
    work_tree_repo.mark_reclaimed.assert_not_awaited()


async def test_reclaims_nothing_when_the_node_has_no_worktree(
    mocker: MockerFixture,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None

    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    workspace = mocker.MagicMock(spec=Workspace)

    handler = MergedNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        work_tree_repo=work_tree_repo,
        workspace=workspace,
    )

    await handler.handle(graph, [graph_node], NOW)

    workspace.remove.assert_not_awaited()
    work_tree_repo.mark_reclaimed.assert_not_awaited()


async def test_keeps_the_worktree_when_removal_fails(
    mocker: MockerFixture, build_agent: BuildAgent
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1, name="A", absolute_path="/ws/A", pr_number=12, created_at=NOW
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = build_agent(worktree)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.remove.side_effect = WorktreeError("could not remove A")

    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)

    handler = MergedNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=mocker.MagicMock(spec=AuditEntryRepo),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
        node_agent_repo=node_agent_repo,
        work_tree_repo=work_tree_repo,
        workspace=workspace,
    )

    await handler.handle(graph, [graph_node], NOW)

    work_tree_repo.mark_reclaimed.assert_not_awaited()
