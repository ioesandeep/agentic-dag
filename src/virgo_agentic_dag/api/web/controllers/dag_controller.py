"""Handles the dag routes."""

from __future__ import annotations

from fastapi import HTTPException, status
from virgo_agentic_dag.api.web.api_responses.dag_detail_response import (
    DagDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_summary_response import (
    DagSummaryResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


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
