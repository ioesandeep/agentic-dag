"""Reads this host's dags."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from virgo_agentic_dag.api.web.api_responses.conversation_message_response import (
    ConversationMessageResponse,
)
from virgo_agentic_dag.api.web.api_responses.conversation_page_response import (
    ConversationPageResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_detail_response import (
    DagDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_summary_response import (
    DagSummaryResponse,
)
from virgo_agentic_dag.api.web.api_responses.memory_response import MemoryResponse
from virgo_agentic_dag.api.web.api_responses.node_detail_response import (
    NodeDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.api_responses.pagination_response import (
    PaginationResponse,
)
from virgo_agentic_dag.api.web.api_responses.recovery_session_response import (
    RecoverySessionResponse,
)
from virgo_agentic_dag.api.web.mappers import (
    codex_transcript_mapper,
    dag_mapper,
    recovery_session_mapper,
    transcript_mapper,
)
from virgo_agentic_dag.domain.agent.transcript_line import TranscriptLine
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.infra.agent.transcript_reader import TranscriptReader
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
from virgo_agentic_dag.utils.dag_utils import get_learnings_file_path

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
        transcript_reader: TranscriptReader,
    ) -> None:
        self._dag_service = dag_service
        self._database_registry = database_registry
        self._code_repo = code_repo
        self._transcript_locators = transcript_locators
        self._transcript_reader = transcript_reader
        self._repo_urls: dict[Path, str] = {}

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

        repo_url = await self._get_repo_url(dag_spec)
        audit_tail = self._find_audit_tail(audit_entries)

        return dag_mapper.to_detail_response(
            dag_spec, rows, scheduled_job, watcher, audit_tail, repo_url
        )

    def _find_audit_tail(self, audit_entries: list[AuditEntry]) -> list[AuditEntry]:
        """Return the latest audit entries, newest first."""
        newest_first = sorted(
            audit_entries, key=lambda entry: (entry.created_at, entry.id), reverse=True
        )

        return newest_first[:AUDIT_TAIL_SIZE]

    async def get_memory_by_name(self, name: str) -> MemoryResponse | None:
        """Return the memory file of a dag, or None when the dag is unknown."""
        dag_spec = self._find_dag_spec(name)
        if dag_spec is None:
            return None

        memory_path = get_learnings_file_path(dag_spec.name)

        return await asyncio.to_thread(self._load_memory, memory_path)

    def _load_memory(self, memory_path: Path) -> MemoryResponse:
        """Load the memory file, empty when the file does not exist."""
        is_memory_file_present = memory_path.is_file()
        if not is_memory_file_present:
            return MemoryResponse(content="", updated_at=None)

        content = memory_path.read_text(encoding="utf-8")
        modified_time = memory_path.stat().st_mtime
        updated_at = datetime.fromtimestamp(modified_time, UTC)

        return MemoryResponse(content=content, updated_at=updated_at)

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

    async def get_conversation_page(
        self, dag_name: str, node_id: str, before: int | None, limit: int
    ) -> ConversationPageResponse | None:
        """Return a page of a node's agent transcript, or None when the dag or node is unknown."""
        dag_spec = self._find_dag_spec(dag_name)
        if dag_spec is None:
            return None

        gateway = self._database_registry.open(dag_spec.name)
        node: Node | None = None
        if gateway is not None:
            node = await gateway.node_repo.read(node_id)

        node_spec = dag_spec.find_node(node_id)
        if node is None and node_spec is None:
            return None

        node_agent = node.agent if node is not None else None
        if node_agent is None:
            return self._get_empty_conversation_page(limit)

        return await asyncio.to_thread(
            self._load_conversation_page, node_agent, before, limit
        )

    def _get_empty_conversation_page(self, limit: int) -> ConversationPageResponse:
        """Return a conversation page with no messages."""
        pagination = PaginationResponse(next_cursor=None, per_page=limit)

        return ConversationPageResponse(
            session_id="", messages=[], pagination=pagination
        )

    def _load_conversation_page(
        self, node_agent: NodeAgent, before: int | None, limit: int
    ) -> ConversationPageResponse:
        """Return a page of an agent's transcript, or an empty page when no transcript file exists."""
        transcript_path = self._get_transcript_path(node_agent)
        if transcript_path is None:
            return self._get_empty_conversation_page(limit)

        look_ahead_lines = self._list_look_ahead_lines(transcript_path, before, limit)
        page_lines: list[TranscriptLine] = []
        conversation_messages: list[ConversationMessageResponse] = []
        while len(conversation_messages) < limit:
            block_end = page_lines[0].offset if page_lines else before
            block_lines = self._transcript_reader.list_lines_before(
                transcript_path, block_end
            )
            if not block_lines:
                break

            page_lines = block_lines + page_lines
            conversation_messages = self._to_page_messages(
                node_agent, page_lines, look_ahead_lines
            )

        pagination = self._get_pagination(page_lines, conversation_messages, limit)

        return ConversationPageResponse(
            session_id=node_agent.resume_token,
            messages=conversation_messages,
            pagination=pagination,
        )

    def _get_pagination(
        self,
        page_lines: list[TranscriptLine],
        conversation_messages: list[ConversationMessageResponse],
        limit: int,
    ) -> PaginationResponse:
        """Return pagination with no next cursor when the page reaches the transcript start."""
        oldest_offset = page_lines[0].offset if page_lines else 0
        is_start_reached = len(conversation_messages) < limit or oldest_offset == 0
        next_cursor = None if is_start_reached else oldest_offset

        return PaginationResponse(next_cursor=next_cursor, per_page=limit)

    def _list_look_ahead_lines(
        self, transcript_path: Path, before: int | None, limit: int
    ) -> list[TranscriptLine]:
        """Return transcript lines from the page boundary, or an empty list when `before` is None."""
        if before is None:
            return []

        return self._transcript_reader.list_lines_from(transcript_path, before, limit)

    def _get_transcript_path(self, node_agent: NodeAgent) -> Path | None:
        """Return the agent's transcript file path, or None when no transcript file exists."""
        transcript_locator = self._transcript_locators[ExecutorAgent(node_agent.name)]
        transcript_path = transcript_locator.get_transcript_path(node_agent)
        if transcript_path is None:
            return None

        has_transcript_file = transcript_path.is_file()

        return transcript_path if has_transcript_file else None

    def _to_page_messages(
        self,
        node_agent: NodeAgent,
        page_lines: list[TranscriptLine],
        look_ahead_lines: list[TranscriptLine],
    ) -> list[ConversationMessageResponse]:
        """Return conversation messages for the page lines, or an empty list when no page line maps to a message."""
        if node_agent.name == ExecutorAgent.CODEX.value:
            return codex_transcript_mapper.to_conversation_page_messages(
                page_lines, look_ahead_lines
            )

        return transcript_mapper.to_conversation_page_messages(
            page_lines, look_ahead_lines
        )

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

    async def get_recovery_sessions_by_dag_name(
        self, name: str
    ) -> list[RecoverySessionResponse] | None:
        """Return the named dag's recovery sessions, or None when no dag has the name."""
        dag_spec = self._find_dag_spec(name)
        if dag_spec is None:
            return None

        gateway = self._database_registry.open(dag_spec.name)
        if gateway is None:
            return []

        recovery_sessions = await gateway.recovery_session_repo.get_all()

        return recovery_session_mapper.to_recovery_session_list_response(
            recovery_sessions
        )

    async def _get_repo_url(self, dag_spec: DagSpec) -> str:
        """Return the web url of a dag's repository, or empty where unreadable."""
        project_root = dag_spec.project_root
        if project_root is None:
            return ""

        cached = self._repo_urls.get(project_root)
        if cached is not None:
            return cached

        try:
            repo_url = await self._code_repo.get_repo_url(project_root)
        except (ObservationError, OSError) as error:
            logger.warning("%s names no repository: %s", dag_spec.name, error)

            return ""

        self._repo_urls[project_root] = repo_url

        return repo_url
