"""Handles the dag routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import HTTPException, Query, status
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
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.api_responses.recovery_session_response import (
    RecoverySessionResponse,
)
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.config.constants import (
    DEFAULT_CONVERSATION_PAGE_LIMIT,
    MAX_CONVERSATION_PAGE_LIMIT,
)
from virgo_agentic_dag.domain.exceptions.host.transcript_cursor_past_end import (
    TranscriptCursorPastEnd,
)
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label

BeforeQuery = Annotated[
    int | None,
    Query(
        ge=0,
        description="The byte offset before which the page ends, or null for the newest page.",
    ),
]
LimitQuery = Annotated[
    int,
    Query(
        ge=1,
        le=MAX_CONVERSATION_PAGE_LIMIT,
        description="The minimum number of messages on any page other than the last page.",
    ),
]


class DagController:
    """Handles the dag routes."""

    def __init__(self, dag_web_service: DagWebService) -> None:
        self._dag_web_service = dag_web_service

    async def list_dags(self) -> list[DagSummaryResponse]:
        """Return one entry per dag on this host."""
        return await self._dag_web_service.list_dags()

    async def get_dag(self, name: str) -> DagDetailResponse:
        """Return one dag with its nodes and audit tail.

        Raises:
            HTTPException: 404 where no dag on this host has the name.
        """
        dag = await self._dag_web_service.get_dag(name)
        if dag is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(LABELS["dagUnknown"], {"dag": name}),
            )

        return dag

    async def get_node_by_name(self, dag_name: str, node_id: str) -> NodeResponse:
        """Return a single node of a dag.

        Raises:
            HTTPException: 404 where the dag or the node is unknown.
        """
        node_response = await self._dag_web_service.get_node_by_name(dag_name, node_id)
        if node_response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(
                    LABELS["nodeUnknown"], {"dag": dag_name, "node": node_id}
                ),
            )

        return node_response

    async def get_memory_by_name(self, name: str) -> MemoryResponse:
        """Return the memory file of a dag."""
        memory_response = await self._dag_web_service.get_memory_by_name(name)
        if memory_response is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(LABELS["dagUnknown"], {"dag": name}),
            )

        return memory_response

    async def get_conversation_page(
        self,
        dag_name: str,
        node_id: str,
        before: BeforeQuery = None,
        limit: LimitQuery = DEFAULT_CONVERSATION_PAGE_LIMIT,
    ) -> ConversationPageResponse:
        """Return a page of a node's agent transcript."""
        try:
            conversation_page = await self._dag_web_service.get_conversation_page(
                dag_name, node_id, before, limit
            )
        except TranscriptCursorPastEnd as past_end:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(
                    LABELS["transcriptCursorPastEnd"],
                    {"cursor": before, "dag": dag_name, "node": node_id},
                ),
            ) from past_end

        if conversation_page is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(
                    LABELS["nodeUnknown"], {"dag": dag_name, "node": node_id}
                ),
            )

        return conversation_page

    async def get_recovery_sessions_by_dag_name(
        self, name: str
    ) -> list[RecoverySessionResponse]:
        """Return the dag's recovery sessions newest first."""
        recovery_session_responses = (
            await self._dag_web_service.get_recovery_sessions_by_dag_name(name)
        )
        if recovery_session_responses is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=format_label(LABELS["dagUnknown"], {"dag": name}),
            )

        return recovery_session_responses
