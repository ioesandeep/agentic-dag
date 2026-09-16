"""Reads this host's dags."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from virgo_agentic_dag.api.web.api_responses.conversation_message_response import (
    ConversationMessageResponse,
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
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.mappers import (
    codex_transcript_mapper,
    dag_mapper,
    transcript_mapper,
)
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.persistence.entities.audit_entry import AuditEntry
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_gateway import (
    DagDatabaseGateway,
)
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.services.dag.dag_service import DagService

logger = logging.getLogger(__name__)

AUDIT_TAIL_SIZE = 50


class DagWebService:
    """Reads this host's dags."""

    def __init__(
        self,
        dag_service: DagService,
        database_registry: DagDatabaseRegistry,
        code_repo: CodeRepo,
        transcript_locators: Mapping[ExecutorAgent, TranscriptLocator],
    ) -> None:
        self._dag_service = dag_service
        self._database_registry = database_registry
        self._code_repo = code_repo
        self._transcript_locators = transcript_locators
        self._repo_slugs: dict[Path, str] = {}

    async def list_dags(self) -> list[DagSummaryResponse]:
        """Return one entry per dag on this host."""
        dag_specs = self._dag_service.get_dag_list()

        return [await self._get_dag_summary(dag_spec) for dag_spec in dag_specs]

    async def _get_dag_summary(self, dag_spec: DagSpec) -> DagSummaryResponse:
        """Return one dag's entry for the listing."""
        gateway = self._database_registry.open(dag_spec.name)
        if gateway is None:
            return dag_mapper.to_unreadable_response(dag_spec)

        try:
            rows = await gateway.node_repo.get_all()
            scheduled_job = await gateway.scheduled_job_repo.get_by_dag_name(
                dag_spec.name
            )
            watcher = await gateway.watcher_repo.get_by_dag_name(dag_spec.name)
        except SQLAlchemyError as error:
            logger.warning("%s will not read: %s", dag_spec.name, error)

            return dag_mapper.to_unreadable_response(dag_spec)

        return dag_mapper.to_response(dag_spec, rows, scheduled_job, watcher)

    async def get_dag(self, name: str) -> DagDetailResponse | None:
        """Return one dag's detail, or None where no dag on this host has the name."""
        dag_spec = self._find_dag_spec(name)
        if dag_spec is None:
            return None

        return await self._get_dag_detail(dag_spec)

    def _find_dag_spec(self, name: str) -> DagSpec | None:
        """Return the spec of the dag with this name, or None where there is none."""
        dag_specs = self._dag_service.get_dag_list()

        return next((dag_spec for dag_spec in dag_specs if dag_spec.name == name), None)

    async def _get_dag_detail(self, dag_spec: DagSpec) -> DagDetailResponse:
        """Return one dag's detail."""
        gateway = self._database_registry.open(dag_spec.name)
        if gateway is None:
            return dag_mapper.to_unreadable_detail_response(dag_spec)

        try:
            rows = await gateway.node_repo.get_all()
            scheduled_job = await gateway.scheduled_job_repo.get_by_dag_name(
                dag_spec.name
            )
            watcher = await gateway.watcher_repo.get_by_dag_name(dag_spec.name)
            audit_entries = await gateway.audit_entry_repo.get_all()
        except SQLAlchemyError as error:
            logger.warning("%s will not read: %s", dag_spec.name, error)

            return dag_mapper.to_unreadable_detail_response(dag_spec)

        repo_slug = await self._get_repo_slug(dag_spec)
        audit_tail = self._find_audit_tail(audit_entries)

        return dag_mapper.to_detail_response(
            dag_spec, rows, scheduled_job, watcher, audit_tail, repo_slug
        )

    def _find_audit_tail(self, audit_entries: list[AuditEntry]) -> list[AuditEntry]:
        """Return the latest audit entries, newest first."""
        newest_first = sorted(
            audit_entries, key=lambda entry: (entry.created_at, entry.id), reverse=True
        )

        return newest_first[:AUDIT_TAIL_SIZE]

    async def get_node_by_name(
        self, dag_name: str, node_id: str
    ) -> NodeResponse | None:
        """Return a node of a dag, or None where the dag or the node is unknown."""
        dag_spec = self._find_dag_spec(dag_name)
        if dag_spec is None:
            return None

        dag_detail = await self._get_dag_detail(dag_spec)
        node_detail = self._find_node_detail(dag_detail, node_id)
        if node_detail is None:
            return None

        return await self._get_node_response(dag_spec, dag_detail, node_detail)

    def _find_node_detail(
        self, dag_detail: DagDetailResponse, node_id: str
    ) -> NodeDetailResponse | None:
        """Return the node with this id, or None where the dag has none."""
        return next(
            (detail for detail in dag_detail.nodes if detail.id == node_id), None
        )

    async def _get_node_response(
        self,
        dag_spec: DagSpec,
        dag_detail: DagDetailResponse,
        node_detail: NodeDetailResponse,
    ) -> NodeResponse:
        """Return a single node's response."""
        node_spec = dag_spec.find_node(node_detail.id)
        gateway = self._database_registry.open(dag_spec.name)
        if gateway is None:
            return dag_mapper.to_node_response(
                node_detail=node_detail,
                node_details=dag_detail.nodes,
                node_spec=node_spec,
                node=None,
                audit_entries=[],
                slack_notifications=[],
                conversation_messages=[],
                node_recovery=None,
            )

        node = await gateway.node_repo.read(node_detail.id)
        audit_entries = await gateway.audit_entry_repo.get_all()
        slack_notifications = await self._get_slack_notifications(
            gateway, node_detail.id
        )
        node_audit_entries = self._find_node_audit_entries(
            audit_entries, node_detail.id
        )
        conversation_messages = await self._get_conversation_messages(node)
        node_recovery = await gateway.node_recovery_repo.get_newest_recovery_by_node_id(
            node_detail.id
        )

        return dag_mapper.to_node_response(
            node_detail=node_detail,
            node_details=dag_detail.nodes,
            node_spec=node_spec,
            node=node,
            audit_entries=node_audit_entries,
            slack_notifications=slack_notifications,
            conversation_messages=conversation_messages,
            node_recovery=node_recovery,
        )

    async def _get_conversation_messages(
        self, node: Node | None
    ) -> list[ConversationMessageResponse]:
        """Return the messages of a node's agent transcript, empty where it has none."""
        node_agent = node.agent if node is not None else None
        if node_agent is None:
            return []

        try:
            return await asyncio.to_thread(self._load_conversation_messages, node_agent)
        except OSError as error:
            logger.warning("%s will not read: %s", node_agent.id, error)

            return []

    def _load_conversation_messages(
        self, node_agent: NodeAgent
    ) -> list[ConversationMessageResponse]:
        """Load the messages of an agent's session file."""
        transcript_locator = self._transcript_locators[ExecutorAgent(node_agent.name)]
        transcript_path = transcript_locator.get_transcript_path(node_agent)
        transcript_lines = node_agent.get_transcript_lines(transcript_path)
        if node_agent.name == ExecutorAgent.CODEX.value:
            return codex_transcript_mapper.to_conversation_message_responses(
                transcript_lines
            )

        return transcript_mapper.to_conversation_message_responses(transcript_lines)

    async def _get_slack_notifications(
        self, gateway: DagDatabaseGateway, node_id: str
    ) -> list[SlackNotification]:
        """Return the Slack notification threads opened for a node."""
        slack_notification = await gateway.slack_notification_repo.get_by_node_id(
            node_id
        )
        if slack_notification is None:
            return []

        return [slack_notification]

    def _find_node_audit_entries(
        self, audit_entries: list[AuditEntry], node_id: str
    ) -> list[AuditEntry]:
        """Return the latest audit entries of a single node, newest first."""
        node_audit_entries = [
            audit_entry
            for audit_entry in audit_entries
            if audit_entry.node_id == node_id
        ]

        return self._find_audit_tail(node_audit_entries)

    async def _get_repo_slug(self, dag_spec: DagSpec) -> str:
        """Return the owner/repo of a dag's repository, or empty where unreadable."""
        project_root = dag_spec.project_root
        if project_root is None:
            return ""

        cached = self._repo_slugs.get(project_root)
        if cached is not None:
            return cached

        try:
            repo_slug = await self._code_repo.get_repo_slug(project_root)
        except (ObservationError, OSError) as error:
            logger.warning("%s names no repository: %s", dag_spec.name, error)

            return ""

        self._repo_slugs[project_root] = repo_slug

        return repo_slug
