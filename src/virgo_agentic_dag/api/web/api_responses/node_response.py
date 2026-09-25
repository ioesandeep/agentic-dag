"""The full detail of a single node."""

from __future__ import annotations

from pydantic import Field
from virgo_agentic_dag.api.web.api_responses.agent_session_response import (
    AgentSessionResponse,
)
from virgo_agentic_dag.api.web.api_responses.audit_line_response import (
    AuditLineResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_detail_response import (
    NodeDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_recovery_response import (
    NodeRecoveryResponse,
)
from virgo_agentic_dag.api.web.api_responses.slack_notification_response import (
    SlackNotificationResponse,
)
from virgo_agentic_dag.api.web.api_responses.worktree_response import (
    WorktreeResponse,
)


class NodeResponse(NodeDetailResponse):
    """The full detail of a single node of a dag."""

    instructions: str = Field(
        description="The instructions of this node, empty where the graph has none."
    )
    blocks: list[str] = Field(
        default_factory=list,
        description="The ids of the nodes that depend on this node.",
    )
    worktree: WorktreeResponse | None = Field(
        default=None,
        description="The worktree of this node's agent, null where none is created.",
    )
    sessions: list[AgentSessionResponse] = Field(
        default_factory=list,
        description="The sessions of this node's agent, oldest first.",
    )
    audits: list[AuditLineResponse] = Field(
        default_factory=list,
        description="The latest transitions of this node, newest first.",
    )
    slack_notifications: list[SlackNotificationResponse] = Field(
        default_factory=list,
        description="The Slack notification threads opened for this node.",
    )
    exit_code: int | None = Field(
        default=None,
        description=(
            "The exit code of the newest session of this node's agent, "
            "null where none is recorded."
        ),
    )
    log_tail: str | None = Field(
        default=None,
        description=(
            "The last log lines of the newest session of this node's agent, "
            "null where none is recorded."
        ),
    )
    node_recovery: NodeRecoveryResponse | None = Field(
        default=None,
        description="The newest recorded failure of this node, null where it has none.",
    )
