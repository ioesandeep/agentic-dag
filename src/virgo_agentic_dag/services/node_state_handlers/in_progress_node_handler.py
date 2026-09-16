"""Advances a node whose agent session is still running."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime

from virgo_agentic_dag.domain.agent.session_status import SessionStatus
from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.commit_pushed_event import CommitPushedEvent
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.pull_request_opened_event import (
    PullRequestOpenedEvent,
)
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.node.node_state_handler import NodeStateHandler
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

logger = logging.getLogger(__name__)


class InProgressNodeHandler(NodeStateHandler):
    """Supervises each working session and settles the node when its session stops."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        node_agent_repo: NodeAgentRepo,
        agent_session_repo: AgentSessionRepo,
        work_tree_repo: WorkTreeRepo,
        workspace: Workspace,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
        code_repo: CodeRepo,
    ) -> None:
        super().__init__(node_repo, audit_entry_repo, notification_publisher)
        self._node_agent_repo = node_agent_repo
        self._agent_session_repo = agent_session_repo
        self._work_tree_repo = work_tree_repo
        self._workspace = workspace
        self._agent_launchers = agent_launchers
        self._code_repo = code_repo

    async def handle(
        self,
        graph: Graph,
        in_progress_graph_nodes: list[GraphNode],
        current_time: datetime,
    ) -> TickResponse:
        tick_response = TickResponse()
        for graph_node in in_progress_graph_nodes:
            node_response = await self._advance(graph_node)
            tick_response = tick_response.increment_with(node_response)

        return tick_response

    async def _advance(self, graph_node: GraphNode) -> TickResponse:
        agent = await self._node_agent_repo.get_by_node_id(graph_node.id)
        if agent is None or not agent.sessions or agent.worktree is None:
            node_event = self._get_stopped_event(
                graph_node,
                NotificationType.AGENT_FAILED,
                LABELS["sessionNeverStarted"],
            )
            await self.record(
                node_event, NodeState.ERRORED, LABELS["sessionNeverStarted"]
            )

            return TickResponse(events_applied=1)

        session = agent.sessions[-1]
        worktree = agent.worktree

        executor_agent = graph_node.executor_agent
        launcher = self._agent_launchers.get(executor_agent) if executor_agent else None

        if launcher is None:
            logger.warning(
                "%s cannot be supervised, executor %s left the configuration",
                graph_node.id,
                executor_agent,
            )

            return TickResponse()

        session_status = await launcher.supervise(session)
        if session_status is SessionStatus.ALIVE:
            return TickResponse()

        try:
            if session_status is SessionStatus.OVERDUE:
                await launcher.stop(session)

            return await self._settle(graph_node, session, worktree, session_status)
        except (WorktreeError, ObservationError, OSError) as error:
            logger.warning(
                "%s stays in progress, it will settle next tick: %s",
                graph_node.id,
                error,
            )

            return TickResponse()

    async def _settle(
        self,
        graph_node: GraphNode,
        session: AgentSession,
        worktree: WorkTree,
        session_status: SessionStatus,
    ) -> TickResponse:
        checked_out = await self._workspace.get_branch(worktree)
        branch = checked_out or worktree.branch

        found_pr_number = 0
        if branch:
            found_pr_number = await self._code_repo.find_pull_request(
                graph_node, branch
            )

        pr_number = found_pr_number or worktree.pr_number
        pr_details = await self._get_pr_details(graph_node, pr_number)
        closed_session = await self._close_session(session, worktree, session_status)

        if pr_details is None:
            return await self._record_stopped(
                graph_node, closed_session, session_status
            )

        commit_count = await self._count_pushed_commits(
            graph_node, worktree, pr_details
        )

        return await self._record_resting(
            graph_node, worktree, branch, pr_details, commit_count, session_status
        )

    async def _get_pr_details(
        self, graph_node: GraphNode, pr_number: int
    ) -> PrDetails | None:
        """Return optional pull request details for the graph node."""
        if pr_number == 0:
            return None

        snapshot = await self._code_repo.get_pull_request(graph_node, pr_number)

        return snapshot.to_pr_details(pr_number)

    async def _count_pushed_commits(
        self, graph_node: GraphNode, worktree: WorkTree, pr_details: PrDetails
    ) -> int:
        """Return the number of commits the settling session pushes."""
        started_sha = worktree.head_sha
        if not started_sha or started_sha == pr_details.head_sha:
            return 0

        return await self._code_repo.count_commits_between(
            graph_node, started_sha, pr_details.head_sha
        )

    async def _close_session(
        self,
        session: AgentSession,
        worktree: WorkTree,
        session_status: SessionStatus,
    ) -> AgentSession:
        """Return the session closed with its final state."""
        current_time = datetime.now(UTC)
        exit_code = worktree.find_exit_code()
        log_tail = worktree.find_log_tail()
        closed_session = AgentSession(
            id=session.id,
            agent_id=session.agent_id,
            started_at=session.started_at,
            ended_at=current_time,
            end_state=session_status.value,
            triggered_by=session.triggered_by,
            pid=session.pid,
            pid_start=session.pid_start,
            exit_code=exit_code,
            log_tail=log_tail,
        )
        await self._agent_session_repo.close(closed_session)

        return closed_session

    async def _record_stopped(
        self,
        graph_node: GraphNode,
        closed_session: AgentSession,
        session_status: SessionStatus,
    ) -> TickResponse:
        overdue = session_status is SessionStatus.OVERDUE
        state = NodeState.ERRORED if overdue else NodeState.NEEDS_HUMAN
        kind = (
            NotificationType.AGENT_FAILED if overdue else NotificationType.NEEDS_HUMAN
        )
        note = (
            LABELS["sessionOverdue"]
            if overdue
            else LABELS["finishedWithoutPullRequest"]
        )

        log_tail = closed_session.get_failure_log_tail()
        node_event = self._get_stopped_event(graph_node, kind, note, log_tail)
        await self.record(node_event, state, note)

        return TickResponse(events_applied=1)

    def _get_stopped_event(
        self,
        graph_node: GraphNode,
        notification_type: NotificationType,
        reason: str,
        log_tail: str = "",
    ) -> AgentStoppedEvent:
        """Create an event for the graph node's agent stop."""
        current_time = datetime.now(UTC)

        return AgentStoppedEvent(
            node_id=graph_node.id,
            type=notification_type,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
            reason=reason,
            log_tail=log_tail,
        )

    async def _record_resting(
        self,
        graph_node: GraphNode,
        worktree: WorkTree,
        branch: str,
        pr_details: PrDetails,
        commit_count: int,
        session_status: SessionStatus,
    ) -> TickResponse:
        pr_number = pr_details.number
        first_publication = worktree.pr_number == 0
        published_worktree = WorkTree(
            id=worktree.id,
            agent_id=worktree.agent_id,
            name=worktree.name,
            absolute_path=worktree.absolute_path,
            branch=branch,
            pr_number=pr_number,
            head_sha=pr_details.head_sha,
            marks=worktree.marks,
            created_at=worktree.created_at,
            reclaimed_at=worktree.reclaimed_at,
        )
        await self._work_tree_repo.record_publication(published_worktree)

        note = self._compose_resting_note(pr_number, session_status, first_publication)
        node_event = self._get_published_event(
            graph_node, pr_details, commit_count, first_publication
        )
        await self.record(node_event, NodeState.RESTING, note)

        return TickResponse(events_applied=1)

    def _get_published_event(
        self,
        graph_node: GraphNode,
        pr_details: PrDetails,
        commit_count: int,
        first_publication: bool,
    ) -> NodeEvent:
        """Create a node event for a pull request publication."""
        current_time = datetime.now(UTC)
        if first_publication:
            return PullRequestOpenedEvent(
                node_id=graph_node.id,
                type=NotificationType.PR_OPENED,
                created_at=current_time,
                updated_at=current_time,
                title=graph_node.title,
                agent_name=graph_node.get_agent_name(),
                pr_details=pr_details,
            )

        return CommitPushedEvent(
            node_id=graph_node.id,
            type=NotificationType.PR_UPDATED,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
            pr_details=pr_details,
            commit_count=commit_count,
        )

    def _compose_resting_note(
        self, pr_number: int, session_status: SessionStatus, first_publication: bool
    ) -> str:
        if session_status is SessionStatus.OVERDUE:
            return LABELS["sessionOverdue"]

        if first_publication:
            return format_label(LABELS["pullRequestOpened"], {"pr_number": pr_number})

        return format_label(
            LABELS["sessionFinishedOnPullRequest"], {"pr_number": pr_number}
        )
