from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from unittest.mock import ANY

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.exceptions.host.base_branch_missing_error import (
    BaseBranchMissingError,
)
from virgo_agentic_dag.domain.exceptions.host.worktree_conflict_error import (
    WorktreeConflictError,
)
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import (
    AgentLauncher,
    AgentWakeTriggerEnum,
)
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
from virgo_agentic_dag.infra.persistence.memory.inmemory_audit_entry_repo import (
    InMemoryAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.memory.inmemory_node_repo import (
    InMemoryNodeRepo,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.node_state_handlers.pending_node_handler import (
    PendingNodeHandler,
)
from virgo_agentic_dag.services.run.adopted_node_importer import AdoptedNodeImporter
from virgo_agentic_dag.services.run.node_importer import NodeImporter

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)
PAST_RESUME_AT = NOW - timedelta(seconds=1)
PR_NUMBER = 16
PR_URL = f"https://github.com/acme/virgo/pull/{PR_NUMBER}"
HEAD_BRANCH = "human/half-done"

BuildNode = Callable[..., Node]


@pytest.fixture
def build_node() -> BuildNode:
    return lambda node_id, state, name="", title="", resume_at=None: Node(
        id=node_id,
        title=title,
        name=name,
        state=state.value,
        created_at=NOW,
        updated_at=NOW,
        resume_at=resume_at,
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


@pytest.mark.parametrize("cooldown_seconds", [0, 7200])
async def test_leaves_the_node_pending_without_audit_updates_before_its_resume_time(
    mocker: MockerFixture, build_node: BuildNode, cooldown_seconds: int
) -> None:
    dependency = GraphNode(id="A")
    graph_node = GraphNode(
        id="B",
        executor_agent=ExecutorAgent.CLAUDE,
        depends_on=("A",),
        cooldown_seconds=cooldown_seconds,
    )

    graph = Graph(name="demo", nodes=[dependency, graph_node])

    resume_at = NOW + timedelta(hours=1)
    next_tick_time = NOW + timedelta(minutes=30)

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.read.return_value = build_node(
        "B", NodeState.PENDING, resume_at=resume_at
    )

    node_repo.get_nodes_by_ids.return_value = [build_node("A", NodeState.MERGED)]
    node_repo.get_nodes_by_state.return_value = []

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}

    dag_spec = DagSpec(name="demo", nodes=(), max_workers=2)
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=mocker.MagicMock(spec=Workspace),
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        node_agent_repo=mocker.MagicMock(spec=NodeAgentRepo),
        code_repo=mocker.MagicMock(spec=CodeRepo),
        node_importer=mocker.MagicMock(spec=NodeImporter),
    )

    await handler.handle(graph, [graph_node], NOW)
    await handler.handle(graph, [graph_node], next_tick_time)

    node_repo.update_state.assert_not_awaited()
    audit_entry_repo.save.assert_not_awaited()

    notification_publisher.publish.assert_not_called()

    agent_launcher.launch.assert_not_awaited()
    agent_launcher.wake.assert_not_awaited()


@pytest.mark.parametrize(
    ("resume_at", "pr", "label_name", "trigger"),
    [
        (None, "", "retryMessage", AgentWakeTriggerEnum.RETRY),
        (NOW, "", "resumeMessage", AgentWakeTriggerEnum.RECOVERY),
        (PAST_RESUME_AT, "", "resumeMessage", AgentWakeTriggerEnum.RECOVERY),
        (NOW, PR_URL, "resumeMessage", AgentWakeTriggerEnum.RECOVERY),
    ],
    ids=["human_retry", "wait_ends", "wait_ended", "wait_ends_with_pr"],
)
async def test_resumes_the_recorded_agent_when_the_node_has_run_before(
    mocker: MockerFixture,
    build_node: BuildNode,
    resume_at: datetime | None,
    pr: str,
    label_name: str,
    trigger: AgentWakeTriggerEnum,
) -> None:
    graph_node = GraphNode(
        id="A", executor_agent=ExecutorAgent.CLAUDE, instructions="do it", pr=pr
    )

    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node(
        "A", NodeState.PENDING, resume_at=resume_at
    )

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

    recorded_agent = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="first-token",
        node_id="A",
        sessions=[ended_session],
        worktree=recorded_worktree,
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = recorded_agent

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by=trigger.value, pid=4242
    )

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)
    node_importer = mocker.MagicMock(spec=NodeImporter)

    dag_spec = DagSpec(name="demo", nodes=(), max_workers=2)
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=node_importer,
    )

    await handler.handle(graph, [graph_node], NOW)

    agent_launcher.wake.assert_awaited_once_with(
        graph_node, LABELS[label_name], recorded_agent, trigger
    )

    agent_launcher.launch.assert_not_awaited()
    node_importer.import_node.assert_not_awaited()
    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, NOW)

    agent = node_agent_repo.save.await_args.args[0]

    assert agent.id == "agent-1"
    assert agent.resume_token == "first-token"
    assert agent.worktree is not None and agent.worktree.id == 7
    assert len(agent.sessions) == 2


@pytest.mark.parametrize(
    ("executor_agent", "resume_token"),
    [(ExecutorAgent.CLAUDE, ""), (ExecutorAgent.CODEX, "first-token")],
)
async def test_starts_a_new_conversation_when_the_recorded_agent_cannot_resume(
    mocker: MockerFixture,
    build_node: BuildNode,
    executor_agent: ExecutorAgent,
    resume_token: str,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=executor_agent, instructions="do it")

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
        name=executor_agent.value,
        resume_token=resume_token,
        node_id="A",
        sessions=[ended_session],
        worktree=recorded_worktree,
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    new_session = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=4242
    )

    if resume_token:
        agent_launcher.wake.return_value = new_session
    else:
        agent_launcher.launch.return_value = new_session

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    code_repo = mocker.MagicMock(spec=CodeRepo)

    agent_launchers = {executor_agent: agent_launcher}
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

    tick_response = await handler.handle(graph, [graph_node], NOW)

    if resume_token:
        agent_launcher.wake.assert_awaited_once()
        agent_launcher.launch.assert_not_awaited()
    else:
        agent_launcher.launch.assert_awaited_once()
        agent_launcher.wake.assert_not_awaited()

    assert tick_response.sessions_started == 1
    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, NOW)

    agent = node_agent_repo.save.await_args.args[0]

    assert agent.id == "agent-1"
    assert agent.resume_token
    assert agent.worktree is not None and agent.worktree.id == 7
    assert len(agent.sessions) == 2

    audit_entry = audit_entry_repo.save.await_args.args[0]

    if resume_token:
        assert audit_entry.note == (
            "A started a new conversation because the previous session recorded no thread ID"
        )
    else:
        assert audit_entry.note == "A started work"


@pytest.mark.parametrize("dependency_state", [NodeState.RESTING, NodeState.PENDING])
async def test_leaves_the_node_pending_when_a_dependency_has_not_merged(
    dependency_state: NodeState, mocker: MockerFixture, build_node: BuildNode
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B", executor_agent=ExecutorAgent.CLAUDE, depends_on=("A",)
    )

    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = [build_node("A", dependency_state)]

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


@pytest.mark.parametrize("error_type", [WorktreeError, ObservationError, OSError])
async def test_leaves_the_node_pending_when_the_worktree_cannot_be_provisioned(
    mocker: MockerFixture, build_node: BuildNode, error_type: type[Exception]
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
        error_type("no disk for A"),
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


@pytest.mark.parametrize("error_type", [BaseBranchMissingError, WorktreeConflictError])
async def test_pending_node_handler_moves_the_node_to_errored_when_provisioning_cannot_succeed(
    mocker: MockerFixture, build_node: BuildNode, error_type: type[WorktreeError]
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph = Graph(name="demo", nodes=[graph_node])

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_nodes_by_ids.return_value = []
    node_repo.get_nodes_by_state.return_value = []
    node_repo.read.return_value = build_node("A", NodeState.PENDING)

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.side_effect = error_type("Cannot provision A from missing-base")

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    dag_spec = DagSpec(name="demo", nodes=(), max_workers=2)
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        node_agent_repo=mocker.MagicMock(spec=NodeAgentRepo),
        code_repo=mocker.MagicMock(spec=CodeRepo),
        node_importer=mocker.MagicMock(spec=NodeImporter),
    )

    tick_response = await handler.handle(graph, [graph_node], NOW)

    assert tick_response.events_applied == 1
    assert tick_response.sessions_started == 0
    node_repo.update_state.assert_awaited_once_with("A", NodeState.ERRORED, NOW)
    agent_launcher.launch.assert_not_awaited()

    audit_entry_repo.save.assert_awaited_once()
    audit_entry = audit_entry_repo.save.await_args.args[0]

    assert audit_entry.state == NodeState.ERRORED.value
    assert audit_entry.note == "Cannot provision A from missing-base"

    notification_publisher.publish.assert_called_once()
    node_event = notification_publisher.publish.call_args.args[0]

    assert node_event.node_id == "A"
    assert node_event.type is NotificationType.AGENT_FAILED
    assert node_event.reason == audit_entry.note


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
    node_agent_repo.get_by_node_id.return_value = None

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


async def test_resumes_the_recorded_agent_when_an_adopted_node_is_retried(
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

    recorded_session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, ended_at=NOW, end_state="finished"
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="recorded-token",
        node_id="A",
        sessions=[recorded_session],
    )

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.provision.return_value = WorkTree(
        name="A", absolute_path="/ws/retried-A", created_at=NOW
    )

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=4242
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pr_details_from_url.return_value = pr_details

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}
    node_importer = AdoptedNodeImporter(
        workspace=workspace,
        node_repo=node_repo,
        node_agent_repo=node_agent_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        agent_launchers=agent_launchers,
    )

    dag_spec = DagSpec(name="demo", nodes=(), max_workers=2)
    handler = PendingNodeHandler(
        node_repo=node_repo,
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        workspace=workspace,
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        node_agent_repo=node_agent_repo,
        code_repo=code_repo,
        node_importer=node_importer,
    )

    tick_response = await handler.handle(graph, [graph_node], NOW)

    assert tick_response.events_applied == 1
    assert tick_response.sessions_started == 1

    agent_launcher.wake.assert_awaited_once()
    agent_launcher.launch.assert_not_awaited()

    agent = node_agent_repo.save.await_args.args[0]

    assert agent.id == "agent-1"
    assert agent.resume_token == "recorded-token"

    assert agent.sessions[0] is recorded_session
    assert len(agent.sessions) == 2

    assert agent.worktree.absolute_path == "/ws/retried-A"

    node_repo.update_state.assert_awaited_once_with("A", NodeState.IN_PROGRESS, ANY)


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
    node_agent_repo.get_by_node_id.return_value = None

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


async def test_records_a_single_pending_audit_entry_when_the_node_waits_for_its_cooldown(
    mocker: MockerFixture,
) -> None:
    dependency = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE)
    graph_node = GraphNode(
        id="B",
        executor_agent=ExecutorAgent.CLAUDE,
        depends_on=("A",),
        cooldown_seconds=3600,
    )

    graph = Graph(name="demo", nodes=[dependency, graph_node])

    node_repo = InMemoryNodeRepo()
    await node_repo.ensure_rows([dependency, graph_node], NOW)
    await node_repo.update_state("A", NodeState.MERGED, NOW)

    audit_entry_repo = InMemoryAuditEntryRepo()

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
    await handler.handle(graph, [graph_node], NOW + timedelta(minutes=30))
    await handler.handle(graph, [graph_node], NOW + timedelta(hours=2))

    audit_entries = await audit_entry_repo.get_all()
    assert [(audit_entry.state, audit_entry.note) for audit_entry in audit_entries] == [
        ("pending", f"it starts at {NOW + timedelta(hours=1)} when its cooldown ends"),
        ("in_progress", "B started work"),
    ]

    notification_publisher.publish.assert_called_once()
