"""Advances a node waiting on its pull request."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime

from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.checks_completed_event import ChecksCompletedEvent
from virgo_agentic_dag.domain.events.comments_added_event import CommentsAddedEvent
from virgo_agentic_dag.domain.events.mergeability_changed_event import (
    MergeabilityChangedEvent,
)
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.node_event_fields import NodeEventFields
from virgo_agentic_dag.domain.events.pull_request_approved_event import (
    PullRequestApprovedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_merged_event import (
    PullRequestMergedEvent,
)
from virgo_agentic_dag.domain.events.work_resumed_event import WorkResumedEvent
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.node.node_state_handler import NodeStateHandler
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
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
from virgo_agentic_dag.domain.signals.signal_change import SignalChange
from virgo_agentic_dag.domain.signals.signal_mark_index import SignalMarkIndex
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.tick.tick_response import TickResponse
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.signals.pr_signal import PrSignal
from virgo_agentic_dag.utils.format_label import format_label

logger = logging.getLogger(__name__)


class RestingNodeHandler(NodeStateHandler):
    """Reads each resting node's pull request fresh and acts on its current state."""

    def __init__(
        self,
        node_repo: NodeRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        node_agent_repo: NodeAgentRepo,
        agent_session_repo: AgentSessionRepo,
        work_tree_repo: WorkTreeRepo,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
        dag_spec: DagSpec,
        code_repo: CodeRepo,
        pr_signals: list[PrSignal],
    ) -> None:
        super().__init__(node_repo, audit_entry_repo, notification_publisher)
        self._node_agent_repo = node_agent_repo
        self._agent_session_repo = agent_session_repo
        self._work_tree_repo = work_tree_repo
        self._agent_launchers = agent_launchers
        self._dag_spec = dag_spec
        self._code_repo = code_repo
        self._pr_signals = pr_signals

    async def handle(
        self,
        graph: Graph,
        resting_graph_nodes: list[GraphNode],
        _: datetime,
    ) -> TickResponse:
        tick_response = TickResponse()
        for graph_node in resting_graph_nodes:
            node_response = await self._advance(graph_node)
            tick_response = tick_response.increment_with(node_response)

        return tick_response

    async def _advance(self, graph_node: GraphNode) -> TickResponse:
        agent = await self._node_agent_repo.get_by_node_id(graph_node.id)
        if agent is None or agent.worktree is None:
            node_event = self._get_stopped_event(
                graph_node, NotificationType.AGENT_FAILED, LABELS["sessionNeverStarted"]
            )
            await self.record(
                node_event, NodeState.ERRORED, LABELS["sessionNeverStarted"]
            )

            return TickResponse(events_applied=1)

        worktree = agent.worktree
        if worktree.pr_number == 0:
            logger.warning(
                "%s rests without a pull request on record, leaving it alone",
                graph_node.id,
            )

            return TickResponse()

        executor_agent = graph_node.executor_agent
        launcher = self._agent_launchers.get(executor_agent) if executor_agent else None

        if launcher is None:
            logger.warning(
                "%s cannot be woken, executor %s left the configuration",
                graph_node.id,
                executor_agent,
            )

            return TickResponse()

        try:
            return await self._observe(graph_node, agent, worktree, launcher)
        except (ObservationError, OSError) as error:
            logger.warning(
                "%s stays resting, its pull request reads again next tick: %s",
                graph_node.id,
                error,
            )

            return TickResponse()

    async def _observe(
        self,
        graph_node: GraphNode,
        agent: NodeAgent,
        worktree: WorkTree,
        launcher: AgentLauncher,
    ) -> TickResponse:
        snapshot = await self._code_repo.get_pull_request(
            graph_node, worktree.pr_number
        )
        if not snapshot.is_complete:
            return TickResponse()

        if snapshot.state is PullRequestState.MERGED:
            await self._record_settled(graph_node)

            return await self._record_merged(graph_node, worktree, snapshot)

        if snapshot.state is PullRequestState.CLOSED:
            await self._record_settled(graph_node)
            closed_pr_details = snapshot.to_pr_details(worktree.pr_number)
            node_event = self._get_stopped_event(
                graph_node,
                NotificationType.NEEDS_HUMAN,
                LABELS["closedUnmerged"],
                closed_pr_details,
            )
            await self.record(
                node_event, NodeState.NEEDS_HUMAN, LABELS["closedUnmerged"]
            )

            return TickResponse(events_applied=1)

        pr_details = await self._get_fully(graph_node, worktree, snapshot)
        marks = self._get_marks(worktree)

        changes: list[SignalChange] = []
        for pr_signal in self._pr_signals:
            change = pr_signal.detect(pr_details, marks.read(pr_signal.name))
            if change is not None:
                changes.append(change)

        if not changes:
            return TickResponse()

        advanced_marks = marks.advanced(changes)
        marked_worktree = WorkTree(
            id=worktree.id,
            agent_id=worktree.agent_id,
            name=worktree.name,
            absolute_path=worktree.absolute_path,
            branch=worktree.branch,
            pr_number=worktree.pr_number,
            head_sha=worktree.head_sha,
            marks=json.dumps(dict(advanced_marks.values)),
            created_at=worktree.created_at,
            reclaimed_at=worktree.reclaimed_at,
        )
        await self._work_tree_repo.advance_marks(marked_worktree)
        self._publish_news(graph_node, changes, pr_details)

        waking_changes = [change for change in changes if change.wakes_node]
        if not waking_changes:
            return TickResponse(events_applied=1)

        return await self._wake(
            graph_node, agent, marked_worktree, launcher, waking_changes, pr_details
        )

    async def _get_fully(
        self, graph_node: GraphNode, worktree: WorkTree, snapshot: PullRequestSnapshot
    ) -> PrDetails:
        artifacts = await self._code_repo.get_review_artifacts(
            graph_node, worktree.pr_number
        )

        pr_details = snapshot.to_pr_details(worktree.pr_number)

        return replace(pr_details, artifacts=tuple(artifacts))

    def _get_marks(self, worktree: WorkTree) -> SignalMarkIndex:
        marks_values = json.loads(worktree.marks or "{}")

        return SignalMarkIndex(marks_values)

    def _publish_news(
        self,
        graph_node: GraphNode,
        changes: list[SignalChange],
        pr_details: PrDetails,
    ) -> None:
        for change in changes:
            node_event = self._get_signal_event(graph_node, change, pr_details)
            if node_event is None:
                continue

            self._notification_publisher.publish(node_event)

    def _get_signal_event(
        self,
        graph_node: GraphNode,
        change: SignalChange,
        pr_details: PrDetails,
    ) -> NodeEvent | None:
        """Return an optional node event for a signal change."""
        if change.notification is None:
            return None

        current_time = datetime.now(UTC)
        fields = NodeEventFields(
            node_id=graph_node.id,
            type=change.notification,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
        )

        match change.notification:
            case NotificationType.FEEDBACK_RECEIVED:
                return CommentsAddedEvent(
                    **fields, pr_details=pr_details, comment_count=change.count
                )
            case NotificationType.CI_FAILED:
                return ChecksCompletedEvent(**fields, pr_details=pr_details)
            case NotificationType.CONFLICTS_FOUND:
                return MergeabilityChangedEvent(**fields, pr_details=pr_details)
            case NotificationType.APPROVED:
                return PullRequestApprovedEvent(**fields, pr_details=pr_details)
            case _:
                return None

    async def _record_settled(self, graph_node: GraphNode) -> None:
        node = await self._node_repo.read(graph_node.id)
        if node is None:
            logger.warning(
                "%s settled its pull request without a node row to record it on",
                graph_node.id,
            )

            return

        if not node.has_pull_request_settled():
            await self._node_repo.record_pull_request_settled(node, datetime.now(UTC))

    async def _record_merged(
        self,
        graph_node: GraphNode,
        worktree: WorkTree,
        snapshot: PullRequestSnapshot,
    ) -> TickResponse:
        kind = (
            NotificationType.APPROVED_AND_MERGED
            if snapshot.is_approved
            else NotificationType.MERGED
        )
        note = LABELS["pullRequestMerged"]
        if snapshot.merged_by:
            note = format_label(
                LABELS["pullRequestMergedBy"], {"merged_by": snapshot.merged_by}
            )

        current_time = datetime.now(UTC)
        node_event = PullRequestMergedEvent(
            node_id=graph_node.id,
            type=kind,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
            pr_details=snapshot.to_pr_details(worktree.pr_number),
        )
        await self.record(node_event, NodeState.MERGED, note)

        return TickResponse(events_applied=1)

    async def _wake(
        self,
        graph_node: GraphNode,
        agent: NodeAgent,
        worktree: WorkTree,
        launcher: AgentLauncher,
        waking_changes: list[SignalChange],
        pr_details: PrDetails,
    ) -> TickResponse:
        wakes = sum(1 for session in agent.sessions if session.triggered_by == "wake")
        if wakes >= self._dag_spec.caps.node_wakes:
            stopped_event = self._get_stopped_event(
                graph_node,
                NotificationType.NEEDS_HUMAN,
                LABELS["outOfWakes"],
                pr_details,
            )
            await self.record(
                stopped_event, NodeState.NEEDS_HUMAN, LABELS["outOfWakes"]
            )

            return TickResponse(events_applied=1)

        news = "\n\n".join(change.render() for change in waking_changes)

        # TODO: if the agent product has deleted this session on its own, recovering
        # from that belongs in its launcher. This handler resumes without checking.
        launched = await launcher.wake(graph_node, news, agent)
        await self._agent_session_repo.add(launched)
        await self._record_head_sha(worktree, pr_details)

        note = format_label(
            LABELS["workResumed"], {"agent_name": graph_node.get_agent_name()}
        )
        current_time = datetime.now(UTC)
        node_event = WorkResumedEvent(
            node_id=graph_node.id,
            type=NotificationType.WORK_RESUMED,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
        )
        await self.record(node_event, NodeState.IN_PROGRESS, note)

        return TickResponse(events_applied=1, sessions_started=1)

    async def _record_head_sha(self, worktree: WorkTree, pr_details: PrDetails) -> None:
        """Record the pull request head SHA as the woken session's starting commit."""
        woken_worktree = WorkTree(
            id=worktree.id,
            agent_id=worktree.agent_id,
            name=worktree.name,
            absolute_path=worktree.absolute_path,
            branch=worktree.branch,
            pr_number=worktree.pr_number,
            head_sha=pr_details.head_sha,
            marks=worktree.marks,
            created_at=worktree.created_at,
            reclaimed_at=worktree.reclaimed_at,
        )
        await self._work_tree_repo.save(woken_worktree)

    def _get_stopped_event(
        self,
        graph_node: GraphNode,
        notification_type: NotificationType,
        reason: str,
        pr_details: PrDetails | None = None,
    ) -> AgentStoppedEvent:
        """Create an event for an agent stop on the resting graph node."""
        current_time = datetime.now(UTC)

        return AgentStoppedEvent(
            node_id=graph_node.id,
            type=notification_type,
            created_at=current_time,
            updated_at=current_time,
            title=graph_node.title,
            agent_name=graph_node.get_agent_name(),
            reason=reason,
            pr_details=pr_details,
        )
