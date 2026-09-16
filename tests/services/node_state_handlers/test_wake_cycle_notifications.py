import os
from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.infra.notification.bot_notification_dispatcher import (
    BotNotificationDispatcher,
)
from virgo_agentic_dag.infra.notification.slack_notification_composer import (
    SlackNotificationComposer,
)
from virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler import (
    InProgressNodeHandler,
)
from virgo_agentic_dag.services.node_state_handlers.resting_node_handler import (
    RestingNodeHandler,
)
from virgo_agentic_dag.services.signals.approval_signal import ApprovalSignal
from virgo_agentic_dag.services.signals.check_signal import CheckSignal
from virgo_agentic_dag.services.signals.comment_signal import CommentSignal
from virgo_agentic_dag.services.signals.conflict_signal import ConflictSignal

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)


@pytest.mark.parametrize(
    ("worktree_head_sha", "expected_phrases"),
    [
        (None, ["merge conflicts"]),
        ("1a2b3c4d5e6f", ["merge conflicts", "pushed 3 commits"]),
    ],
    ids=["pushed-nothing", "pushed"],
)
async def test_posts_only_the_pull_request_change_when_a_session_resumes_and_settles(
    worktree_head_sha: str | None,
    expected_phrases: list[str],
    mocker: MockerFixture,
) -> None:
    graph_node = GraphNode(id="A", executor_agent=ExecutorAgent.CLAUDE, name="Vesta")
    graph = Graph(name="demo", nodes=[graph_node])
    worktree = WorkTree(
        id=1,
        name="A",
        absolute_path="/ws/A",
        branch="virgo/a",
        pr_number=12,
        head_sha=worktree_head_sha,
        marks="{}",
        created_at=NOW,
    )
    session = AgentSession(
        id=1, agent_id="agent-1", started_at=NOW, triggered_by="launch", pid=1
    )

    node_agent_repo = mocker.MagicMock(spec=NodeAgentRepo)
    node_agent_repo.get_by_node_id.return_value = NodeAgent(
        id="agent-1",
        name="claude",
        resume_token="token",
        node_id="A",
        worktree=worktree,
        sessions=[session],
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.get_pull_request.return_value = PullRequestSnapshot(
        state=PullRequestState.OPEN,
        head_sha="8bddf07abcdef",
        base_branch="develop",
        is_mergeable=False,
    )
    code_repo.get_review_artifacts.return_value = []
    code_repo.find_pull_request.return_value = 12
    code_repo.count_commits_between.return_value = 3

    agent_launcher = mocker.MagicMock(spec=AgentLauncher)
    agent_launcher.wake.return_value = AgentSession(
        agent_id="agent-1", started_at=NOW, triggered_by="wake", pid=777
    )
    agent_launcher.supervise.return_value = SessionStatus.FINISHED

    workspace = mocker.MagicMock(spec=Workspace)
    workspace.get_branch.return_value = "virgo/a"

    audit_entry_repo = mocker.MagicMock(spec=AuditEntryRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)
    agent_launchers = {ExecutorAgent.CLAUDE: agent_launcher}

    work_tree_repo = mocker.MagicMock(spec=WorkTreeRepo)
    resting_handler = RestingNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=work_tree_repo,
        agent_launchers=agent_launchers,
        dag_spec=DagSpec(name="demo", nodes=(), caps=AttemptBudget(node_wakes=12)),
        code_repo=code_repo,
        pr_signals=[
            CommentSignal(agent_account="virgo-bot"),
            CheckSignal(),
            ConflictSignal(),
            ApprovalSignal(),
        ],
    )
    in_progress_handler = InProgressNodeHandler(
        node_repo=mocker.MagicMock(spec=NodeRepo),
        audit_entry_repo=audit_entry_repo,
        notification_publisher=notification_publisher,
        node_agent_repo=node_agent_repo,
        agent_session_repo=mocker.MagicMock(spec=AgentSessionRepo),
        work_tree_repo=mocker.MagicMock(spec=WorkTreeRepo),
        workspace=workspace,
        agent_launchers=agent_launchers,
        code_repo=code_repo,
    )

    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    slack_notification_repo = mocker.AsyncMock(spec=SlackNotificationRepo)
    slack_notification_repo.get_by_node_id.return_value = None

    mocker.patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-token"})
    dispatcher = BotNotificationDispatcher(
        poster=poster,
        slack_notification_repo=slack_notification_repo,
        channel="#dag",
        composer=SlackNotificationComposer(),
        dag_name="demo",
    )

    await resting_handler.handle(graph, [graph_node], NOW)
    await in_progress_handler.handle(graph, [graph_node], NOW)
    published_events = [
        publication.args[0]
        for publication in notification_publisher.publish.call_args_list
    ]
    for published_event in published_events:
        await dispatcher.dispatch(published_event)

    assert audit_entry_repo.save.await_count == 2

    woken_worktree = work_tree_repo.save.await_args.args[0]
    marked_worktree = work_tree_repo.advance_marks.await_args.args[0]
    assert (woken_worktree.id, woken_worktree.head_sha) == (1, "8bddf07abcdef")
    assert woken_worktree.marks == marked_worktree.marks

    posted_texts = [post.args[1]["text"] for post in poster.post.call_args_list]
    assert len(posted_texts) == len(expected_phrases)
    assert all(
        phrase in text
        for phrase, text in zip(expected_phrases, posted_texts, strict=True)
    )
