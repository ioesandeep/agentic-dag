"""Builds the dag responses."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from virgo_agentic_dag.api.web.api_responses.agent_session_response import (
    AgentSessionResponse,
)
from virgo_agentic_dag.api.web.api_responses.audit_line_response import (
    AuditLineResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_detail_response import (
    DagDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_summary_response import (
    DagSummaryResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_detail_response import (
    NodeDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_preview_response import (
    NodePreviewResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_recovery_response import (
    NodeRecoveryResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.api_responses.slack_notification_response import (
    SlackNotificationResponse,
)
from virgo_agentic_dag.api.web.api_responses.worktree_response import (
    WorktreeResponse,
)
from virgo_agentic_dag.api.web.utils.to_utc import to_utc
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.node_recovery import NodeRecovery
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec

WAKE_TRIGGER = "wake"


def to_response(
    dag_spec: DagSpec,
    rows: list[Node],
    scheduled_job: ScheduledJob | None,
    watcher: Watcher | None,
) -> DagSummaryResponse:
    """Convert a dag to its API response."""
    nodes = to_node_responses(dag_spec, rows)

    return DagSummaryResponse(
        name=dag_spec.name,
        base_branch=dag_spec.base_branch,
        tick_interval_seconds=dag_spec.tick_interval_seconds,
        node_count=len(nodes),
        nodes=nodes,
        last_activity_at=_find_last_activity(nodes),
        is_scheduled=scheduled_job is not None,
        is_watching=watcher is not None,
    )


def to_unreadable_response(dag_spec: DagSpec) -> DagSummaryResponse:
    """Convert a dag that cannot be read to its API response."""
    return DagSummaryResponse(
        name=dag_spec.name,
        base_branch=dag_spec.base_branch,
        tick_interval_seconds=dag_spec.tick_interval_seconds,
        is_readable=False,
    )


def to_node_responses(dag_spec: DagSpec, rows: list[Node]) -> list[NodePreviewResponse]:
    """Convert every node of a dag to its API response."""
    rows_by_id = {row.id: row for row in rows}
    declared = [
        _to_declared_node_response(node_spec, rows_by_id.get(node_spec.id))
        for node_spec in dag_spec.nodes
    ]
    adopted = [
        _to_adopted_node_response(row)
        for row in rows
        if dag_spec.find_node(row.id) is None
    ]

    return declared + adopted


def to_detail_response(
    dag_spec: DagSpec,
    rows: list[Node],
    scheduled_job: ScheduledJob | None,
    watcher: Watcher | None,
    audit_entries: list[AuditEntry],
    repo_url: str,
) -> DagDetailResponse:
    """Convert a dag to its detail API response."""
    previews = to_node_responses(dag_spec, rows)
    nodes = _to_node_detail_responses(dag_spec, rows, previews, repo_url)
    audit = [_to_audit_response(audit_entry) for audit_entry in audit_entries]

    return DagDetailResponse(
        name=dag_spec.name,
        base_branch=dag_spec.base_branch,
        tick_interval_seconds=dag_spec.tick_interval_seconds,
        node_count=len(nodes),
        nodes=nodes,
        last_activity_at=_find_last_activity(previews),
        is_scheduled=scheduled_job is not None,
        is_watching=watcher is not None,
        audit=audit,
    )


def to_unreadable_detail_response(dag_spec: DagSpec) -> DagDetailResponse:
    """Convert a dag that cannot be read to its detail API response."""
    return DagDetailResponse(
        name=dag_spec.name,
        base_branch=dag_spec.base_branch,
        tick_interval_seconds=dag_spec.tick_interval_seconds,
        is_readable=False,
    )


def to_node_response(
    node_detail: NodeDetailResponse,
    node_details: list[NodeDetailResponse],
    node_spec: NodeSpec | None,
    node: Node | None,
    audit_entries: list[AuditEntry],
    slack_notifications: list[SlackNotification],
    node_recovery: NodeRecovery | None,
) -> NodeResponse:
    """Convert a single node to its API response."""
    node_agent = node.agent if node is not None else None
    worktree = node_agent.worktree if node_agent is not None else None
    agent_sessions = node_agent.sessions if node_agent is not None else []
    newest_session = agent_sessions[-1] if agent_sessions else None

    dependent_node_ids = _find_dependent_node_ids(node_detail, node_details)
    agent_session_responses = [
        _to_agent_session_response(agent_session) for agent_session in agent_sessions
    ]
    audit_line_responses = [
        _to_audit_response(audit_entry) for audit_entry in audit_entries
    ]
    slack_notification_responses = [
        _to_slack_notification_response(slack_notification)
        for slack_notification in slack_notifications
    ]

    return NodeResponse(
        **node_detail.model_dump(),
        instructions=node_spec.instructions if node_spec is not None else "",
        blocks=dependent_node_ids,
        worktree=_to_worktree_response(worktree) if worktree is not None else None,
        sessions=agent_session_responses,
        audits=audit_line_responses,
        slack_notifications=slack_notification_responses,
        exit_code=newest_session.exit_code if newest_session is not None else None,
        log_tail=newest_session.log_tail if newest_session is not None else None,
        node_recovery=(
            _to_node_recovery_response(node_recovery)
            if node_recovery is not None
            else None
        ),
    )


def _to_declared_node_response(
    node_spec: NodeSpec, row: Node | None
) -> NodePreviewResponse:
    """Convert a declared node to its API response."""
    return NodePreviewResponse(
        id=node_spec.id,
        title=node_spec.title,
        agent_name=node_spec.get_agent_name(),
        state=row.state if row is not None else NodeState.PENDING.value,
        depends_on=list(node_spec.depends_on),
        updated_at=_get_updated_at(row),
    )


def _to_adopted_node_response(row: Node) -> NodePreviewResponse:
    """Convert an adopted node to its API response."""
    return NodePreviewResponse(
        id=row.id,
        title=row.title,
        agent_name=row.get_agent_name(),
        state=row.state,
        updated_at=_get_updated_at(row),
    )


def _to_node_detail_responses(
    dag_spec: DagSpec,
    rows: list[Node],
    previews: list[NodePreviewResponse],
    repo_url: str,
) -> list[NodeDetailResponse]:
    """Convert every node of a dag to its detail API response."""
    rows_by_id = {row.id: row for row in rows}

    return [
        _to_node_detail_response(
            preview,
            rows_by_id.get(preview.id),
            dag_spec.find_node(preview.id),
            repo_url,
        )
        for preview in previews
    ]


def _to_node_detail_response(
    preview: NodePreviewResponse,
    row: Node | None,
    node_spec: NodeSpec | None,
    repo_url: str,
) -> NodeDetailResponse:
    """Convert one node to its detail API response."""
    agent = row.agent if row is not None else None
    worktree = agent.worktree if agent is not None else None

    return NodeDetailResponse(
        id=preview.id,
        title=preview.title,
        agent_name=preview.agent_name,
        state=preview.state,
        depends_on=preview.depends_on,
        updated_at=preview.updated_at,
        wakes=_count_wakes(agent),
        session_id=agent.resume_token if agent is not None else "",
        pr_url=_get_pr_url(node_spec, worktree, repo_url),
        pr_number=_get_pr_number(node_spec, worktree),
        worktree_name=worktree.name if worktree is not None else "",
        branch=worktree.branch if worktree is not None else "",
    )


def _to_audit_response(audit_entry: AuditEntry) -> AuditLineResponse:
    """Convert one audit entry to its API response."""
    return AuditLineResponse(
        created_at=audit_entry.created_at.replace(tzinfo=UTC),
        node_id=audit_entry.node_id,
        state=audit_entry.state,
        note=audit_entry.note,
    )


def _find_dependent_node_ids(
    node_detail: NodeDetailResponse, node_details: list[NodeDetailResponse]
) -> list[str]:
    """Return the ids of the nodes that depend on this node."""
    return [detail.id for detail in node_details if node_detail.id in detail.depends_on]


def _to_worktree_response(worktree: WorkTree) -> WorktreeResponse:
    """Convert a worktree to its API response."""
    return WorktreeResponse(
        name=worktree.name,
        absolute_path=worktree.absolute_path,
        branch=worktree.branch,
        pr_number=worktree.pr_number,
        created_at=worktree.created_at.replace(tzinfo=UTC),
        reclaimed_at=to_utc(worktree.reclaimed_at),
        signal_marks=_get_signal_marks(worktree),
    )


def _to_agent_session_response(agent_session: AgentSession) -> AgentSessionResponse:
    """Convert a single agent session to its API response."""
    return AgentSessionResponse(
        id=agent_session.id,
        started_at=agent_session.started_at.replace(tzinfo=UTC),
        ended_at=to_utc(agent_session.ended_at),
        end_state=agent_session.end_state,
        triggered_by=agent_session.triggered_by,
    )


def _to_slack_notification_response(
    slack_notification: SlackNotification,
) -> SlackNotificationResponse:
    """Convert a single Slack notification thread to its API response."""
    return SlackNotificationResponse(
        id=slack_notification.id,
        channel=slack_notification.channel,
        thread_id=slack_notification.thread_id,
        created_at=slack_notification.created_at.replace(tzinfo=UTC),
    )


def _to_node_recovery_response(node_recovery: NodeRecovery) -> NodeRecoveryResponse:
    """Convert a single recorded failure of a node to its API response."""
    return NodeRecoveryResponse(
        id=node_recovery.id,
        session_id=node_recovery.session_id,
        detected_at=node_recovery.detected_at.replace(tzinfo=UTC),
        cause=node_recovery.cause,
        recoverable=node_recovery.recoverable,
        recover_at=node_recovery.recover_at.replace(tzinfo=UTC),
        action=node_recovery.action,
    )


def _get_signal_marks(worktree: WorkTree) -> dict[str, str]:
    """Return the signal marks of a worktree, keyed by signal name."""
    signal_marks: dict[str, str] = json.loads(worktree.marks or "{}")

    return signal_marks


def _count_wakes(agent: NodeAgent | None) -> int:
    """Return the number of wakes of a node's agent."""
    if agent is None:
        return 0

    return sum(1 for session in agent.sessions if session.triggered_by == WAKE_TRIGGER)


def _get_pr_url(
    node_spec: NodeSpec | None, worktree: WorkTree | None, repo_url: str
) -> str:
    """Return the url of a node's pull request, or empty where it has none."""
    if node_spec is not None and node_spec.pr:
        return node_spec.pr

    if worktree is None:
        return ""

    if worktree.pr_url:
        return worktree.pr_url

    if worktree.pr_number == 0 or not repo_url:
        return ""

    # TODO: return an empty url here once no worktree row predates the pr_url column.
    return f"{repo_url}/pull/{worktree.pr_number}"


def _get_pr_number(node_spec: NodeSpec | None, worktree: WorkTree | None) -> int:
    """Return the number of a node's pull request, or 0 where it has none."""
    if worktree is not None and worktree.pr_number != 0:
        return worktree.pr_number

    declared_pr_url = node_spec.pr if node_spec is not None else ""
    last_path_segment = declared_pr_url.rsplit("/", 1)[-1]
    is_pr_number = last_path_segment.isdecimal()

    return int(last_path_segment) if is_pr_number else 0


def _get_updated_at(row: Node | None) -> datetime | None:
    """Return the time of the last write to a node's state, in UTC."""
    if row is None:
        return None

    return row.updated_at.replace(tzinfo=UTC)


def _find_last_activity(nodes: list[NodePreviewResponse]) -> datetime | None:
    """Return the newest state write across these nodes."""
    written_at = [node.updated_at for node in nodes if node.updated_at is not None]
    if not written_at:
        return None

    return max(written_at)
