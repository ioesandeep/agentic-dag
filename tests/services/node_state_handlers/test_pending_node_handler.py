from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.services.node_state_handlers.pending_node_handler import (
    PendingNodeHandler,
)
from virgo_agentic_dag.services.run.adopted_node_importer import AdoptedNodeImporter

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)
PR_NUMBER = 16
PR_URL = f"https://github.com/acme/virgo/pull/{PR_NUMBER}"
HEAD_BRANCH = "human/half-done"

BuildNode = Callable[..., Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id, state, name="", title="": Node(
        id=node_id,
        title=title,
        name=name,
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def pr_details() -> PullRequestDetails:
    return PullRequestDetails(
        number=PR_NUMBER,
        repository="acme/virgo",
        url=PR_URL,
        head_branch=HEAD_BRANCH,
    )


async def test_starts_the_node_when_its_dependencies_have_merged(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph_node = GraphNode(
        id="A", executor_agent=ExecutorAgent.CLAUDE, instructions="do it", name="Vesta"
    )
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING, name="Vesta")

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, NOW)
    agent_launcher.launch.assert_awaited_once()
    assert agent_launcher.launch.await_args.args[0].id == "A"
    agent = node_agent_repo.save.await_args.args[0]
    assert agent.worktree is not None
    assert len(agent.sessions) == 1
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.WORK_STARTED


async def test_resumes_the_recorded_agent_when_the_node_has_run_before(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph_node = GraphNode(
        id="A", executor_agent=ExecutorAgent.CLAUDE, instructions="do it"
    )
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    recorded_worktree = WorkTree(
        id=7, agent_id="agent-1", name="A", absolute_path="/ws/A", created_at=NOW
    )
    ended_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, ended_at=NOW, end_state="finished"
    )
    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="first-token",
        node_id="A",
        sessions=[ended_session],
        worktree=recorded_worktree,
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=4242
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    agent_launcher.wake.assert_awaited_once()
    agent_launcher.launch.assert_not_awaited()
    agent = node_agent_repo.save.await_args.args[0]
    assert agent.id == "agent-1"
    assert agent.resume_token == "first-token"
    assert agent.worktree is not None and agent.worktree.id == 7
    assert len(agent.sessions) == 2


async def test_starts_a_new_conversation_when_the_recorded_agent_has_no_resume_token(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph_node = GraphNode(
        id="A", executor_agent=ExecutorAgent.CLAUDE, instructions="do it"
    )
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    recorded_worktree = WorkTree(
        id=7, agent_id="agent-1", name="A", absolute_path="/ws/A", created_at=NOW
    )
    ended_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, ended_at=NOW, end_state="finished"
    )
    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="",
        node_id="A",
        sessions=[ended_session],
        worktree=recorded_worktree,
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    agent_launcher.launch.assert_awaited_once()
    agent_launcher.wake.assert_not_awaited()
    agent = node_agent_repo.save.await_args.args[0]
    assert agent.id == "agent-1"
    assert agent.resume_token
    assert agent.worktree is not None and agent.worktree.id == 7
    assert len(agent.sessions) == 2


async def test_leaves_the_node_pending_when_a_dependency_has_not_merged(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",)
    )
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.RESTING)]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    workspace = mocker.MagicMock(spec=Workspace)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    agent_launcher.launch.assert_not_awaited()


async def test_starts_the_node_when_its_ancestor_was_skipped(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    ancestor = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",)
    )
    graph = Graph(name="demo", nodes=[ancestor, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.side_effect = [
        [build_node("A", NodeState.SKIPPED)],
        [],
    ]
    node_repo.read.return_value = build_node("B", NodeState.PENDING)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="B", absolute_path="/ws/B", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("B", NodeState.IN_PROGRESS, NOW)
    agent_launcher.launch.assert_awaited_once()


async def test_leaves_the_node_pending_when_the_skipped_ancestor_has_an_unmerged_ancestor(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    root_ancestor = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    skipped_ancestor = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",)
    )
    graph_node = GraphNode(
        id="D", executor_agent=ExecutorAgent.CLAUDE, depends_on=("B",)
    )
    graph = Graph(name="demo", nodes=[root_ancestor, skipped_ancestor, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_state.return_value = [build_node("B", NodeState.SKIPPED)]
    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.RESTING)]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    workspace = mocker.MagicMock(spec=Workspace)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.get_nodes_by_ids.assert_awaited_once_with(["A"])
    node_repo.update_state.assert_not_awaited()
    agent_launcher.launch.assert_not_awaited()


async def test_needs_a_human_when_an_upstream_node_has_stopped(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",)
    )
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.ERRORED)]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    workspace = mocker.MagicMock(spec=Workspace)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("B", NodeState.NEEDS_HUMAN, NOW)
    agent_launcher.launch.assert_not_awaited()
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.NEEDS_HUMAN
    assert event.reason == "upstream node A stopped, so this one can never start"


async def test_leaves_the_node_pending_when_the_worker_budget_is_spent(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    """The handler loads the skipped nodes and then the working nodes, once for each pending node."""
    first_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    second_node = GraphNode(id="B", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[first_node, second_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.side_effect = [
        [],
        [],
        [],
        [build_node("A", NodeState.IN_PROGRESS)],
    ]
    node_repo.read.return_value = build_node("A", NodeState.PENDING)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=1),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [first_node, second_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, NOW)
    assert agent_launcher.launch.await_count == 1


async def test_needs_a_human_when_no_launcher_serves_its_agent(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph_node = GraphNode(id="A")
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    workspace = mocker.MagicMock(spec=Workspace)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("A", NodeState.NEEDS_HUMAN, NOW)
    agent_launcher.launch.assert_not_awaited()


async def test_leaves_the_node_pending_when_the_worktree_cannot_be_provisioned(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    failing_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    second_node = GraphNode(id="B", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[failing_node, second_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.side_effect = [
        build_node("A", NodeState.PENDING),
        build_node("B", NodeState.PENDING),
    ]

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.side_effect = [
        WorktreeError("no disk for A"),
        WorkTree(name="B", absolute_path="/ws/B", created_at=NOW),
    ]

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [failing_node, second_node], NOW)

    node_repo.update_state.assert_awaited_once_with("B", NodeState.IN_PROGRESS, NOW)
    agent_launcher.launch.assert_awaited_once()
    assert agent_launcher.launch.await_args.args[0].id == "B"


async def test_a_started_node_names_its_agent_and_its_task(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    graph_node = GraphNode(
        id="A",
        executor_agent=ExecutorAgent.CLAUDE,
        name="Aries",
        title="Rename the audit column",
    )
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node(
        "A", NodeState.PENDING, name="Aries", title="Rename the audit column"
    )

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    audit_entry_repo.save.assert_awaited_once()
    notification_publisher.publish.assert_called_once()
    entry = audit_entry_repo.save.await_args.args[0]
    event = notification_publisher.publish.call_args.args[0]
    assert (event.agent_name, event.title) == ("Aries", "Rename the audit column")
    assert entry.note == "Aries started work"


async def test_an_adopted_node_announces_the_pull_request_it_was_handed(
    mocker: MockerFixture,
    pr_details: PullRequestDetails,
    build_node: BuildNode,
) -> None:
    graph_node = GraphNode(
        id="A", executor_agent=ExecutorAgent.CLAUDE, name="Aries", pr=PR_URL
    )
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING, name="Aries")

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    audit_entry_repo.save.assert_awaited_once()
    notification_publisher.publish.assert_called_once()
    entry = audit_entry_repo.save.await_args.args[0]
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.PR_ADOPTED
    assert event.pr_details is not None and event.pr_details.number == PR_NUMBER
    assert entry.note.startswith(f"took over #{PR_NUMBER}")


async def test_launches_with_its_own_brief_when_it_declares_a_pull_request(
    mocker: MockerFixture,
    pr_details: PullRequestDetails,
    build_node: BuildNode,
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B",
        executor_agent=ExecutorAgent.CLAUDE,
        depends_on=("A",),
        instructions="finish what they started",
        pr=PR_URL,
    )
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.MERGED)]
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("B", NodeState.PENDING)

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="B", absolute_path="/ws/B", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = None
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_awaited_once_with("B", NodeState.IN_PROGRESS, ANY)
    agent = node_agent_repo.save.await_args.args[0]
    assert len(agent.sessions) == 1
    agent_launcher.launch.assert_awaited_once()
    launched_node, brief, launched_agent = agent_launcher.launch.await_args.args
    assert launched_node.id == "B"
    assert brief == "finish what they started"
    assert launched_agent.resume_token == agent.resume_token
    notification_publisher.publish.assert_called_once()
    event = notification_publisher.publish.call_args.args[0]
    assert event.type is NotificationType.PR_ADOPTED


async def test_cuts_the_worktree_from_the_declared_pull_request_head(
    mocker: MockerFixture,
    pr_details: PullRequestDetails,
    build_node: BuildNode,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE, pr=PR_URL)
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING)

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.launch.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    agent = node_agent_repo.save.await_args.args[0]
    assert agent.worktree is not None
    assert agent.worktree.pr_number == PR_NUMBER
    assert agent.worktree.branch == HEAD_BRANCH
    workspace.provision.assert_awaited_once()
    provisioned_node = workspace.provision.await_args.args[0]
    assert (provisioned_node.id, provisioned_node.base_branch) == ("A", HEAD_BRANCH)


async def test_skips_adoption_when_a_dependency_has_not_merged(
    mocker: MockerFixture, build_node: BuildNode
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",), pr=PR_URL
    )
    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.RESTING)]

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    workspace = mocker.MagicMock(spec=Workspace)

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {ExecutorAgent.CLAUDE: mocker.MagicMock(spec=AgentLauncher)}
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), max_workers=2),
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=AdoptedNodeImporter(
            workspace=workspace,
            node_repo=node_repo,
            node_agent_repo=node_agent_repo,
            audit_entry_repo=audit_entry_repo,
            notification_publisher=notification_publisher,
            agent_launchers=agent_launchers,
        ),
    )

    await handler.handle(graph, [graph_node], NOW)

    node_repo.update_state.assert_not_awaited()
    node_agent_repo.save.assert_not_awaited()
    workspace.provision.assert_not_awaited()
