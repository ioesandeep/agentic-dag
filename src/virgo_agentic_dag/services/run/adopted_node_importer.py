"""Takes a node onto a pull request that already exists and starts its agent there."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from virgo_agentic_dag.domain.events.pull_request_adopted_event import (
    PullRequestAdoptedEvent,
)
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.run.node_importer import NodeImporter
from virgo_agentic_dag.utils.create_session_token import create_session_token
from virgo_agentic_dag.utils.format_label import format_label


class AdoptedNodeImporter(NodeImporter):
    """Launches the node's agent on the pull request it takes over, unless the caller
    hands over a session for it to rest on."""

    def __init__(
        self,
        workspace: Workspace,
        node_repo: NodeRepo,
        node_agent_repo: NodeAgentRepo,
        audit_entry_repo: AuditEntryRepo,
        notification_publisher: NotificationPublisher,
        agent_launchers: Mapping[ExecutorAgent, AgentLauncher],
    ) -> None:
        self._workspace = workspace
        self._node_repo = node_repo
        self._node_agent_repo = node_agent_repo
        self._audit_entry_repo = audit_entry_repo
        self._notification_publisher = notification_publisher
        self._agent_launchers = agent_launchers

    async def import_node(
        self,
        graph_node: GraphNode,
        pr_details: PullRequestDetails,
        session_token: str | None = None,
    ) -> None:
        adopted_node = replace(graph_node, base_branch=pr_details.head_branch)
        provisioned = await self._workspace.provision(adopted_node)
        worktree = WorkTree(
            name=provisioned.name,
            absolute_path=provisioned.absolute_path,
            branch=pr_details.head_branch,
            pr_number=pr_details.number,
            created_at=provisioned.created_at,
        )

        if session_token:
            handed_agent = self._build_agent(adopted_node, worktree, session_token)
            await self._record(
                adopted_node, pr_details, handed_agent, NodeState.RESTING
            )

            return

        agent = await self._launch(adopted_node, worktree)

        await self._record(adopted_node, pr_details, agent, NodeState.IN_PROGRESS)

    async def _launch(self, graph_node: GraphNode, worktree: WorkTree) -> NodeAgent:
        """Start the agent on the pull request under a session id this launch creates."""
        agent = self._build_agent(graph_node, worktree, create_session_token())
        session = await self._get_launcher(graph_node).launch(
            graph_node, graph_node.instructions, agent
        )
        agent.sessions.append(session)

        return agent

    async def _record(
        self,
        graph_node: GraphNode,
        pr_details: PullRequestDetails,
        agent: NodeAgent,
        state: NodeState,
    ) -> None:
        """Write the adopted node, its agent, and the state it reached wherever the run is read."""
        current_time = datetime.now(UTC)
        await self._node_repo.ensure_rows([graph_node], current_time)

        node = await self._node_repo.read(graph_node.id)
        if node is None:
            return

        await self._node_agent_repo.save(agent)
        await self._node_repo.update_state(graph_node.id, state, current_time)

        note = self._compose_note(pr_details, state)
        audit_entry = AuditEntry(
            node_id=graph_node.id,
            state=state.value,
            note=note,
            created_at=current_time,
        )
        await self._audit_entry_repo.save(audit_entry)

        reading = PrDetails(
            number=pr_details.number, head_sha="", title=pr_details.title
        )
        node_event = PullRequestAdoptedEvent(
            node_id=graph_node.id,
            type=NotificationType.PR_ADOPTED,
            created_at=current_time,
            updated_at=current_time,
            title=node.title,
            agent_name=node.get_agent_name(),
            pr_details=reading,
        )
        self._notification_publisher.publish(node_event)

    def _compose_note(self, pr_details: PullRequestDetails, state: NodeState) -> str:
        """Format a takeover note for the pull request."""
        label = (
            LABELS["takeoverResuming"]
            if state is NodeState.RESTING
            else LABELS["takeoverStarted"]
        )

        return format_label(
            label, {"pr_number": pr_details.number, "branch": pr_details.head_branch}
        )

    def _build_agent(
        self, graph_node: GraphNode, worktree: WorkTree, resume_token: str
    ) -> NodeAgent:
        """Build this node's agent, holding the worktree it works in and the session it resumes."""
        executor_agent = graph_node.executor_agent

        return NodeAgent(
            id=str(uuid.uuid4()),
            name=Path(executor_agent.value).name if executor_agent else "",
            resume_token=resume_token,
            node_id=graph_node.id,
            worktree=worktree,
        )

    def _get_launcher(self, graph_node: GraphNode) -> AgentLauncher:
        """Return the launcher that runs this node's agent product."""
        executor_agent = graph_node.executor_agent
        launcher = self._agent_launchers.get(executor_agent) if executor_agent else None
        if launcher is None:
            name = executor_agent.value if executor_agent else "none"
            message = format_label(LABELS["unknownExecutor"], {"executor": name})

            raise ConfigError(message)

        return launcher
