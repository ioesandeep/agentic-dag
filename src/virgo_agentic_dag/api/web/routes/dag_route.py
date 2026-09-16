"""The read-only routes over this host's dags."""

from __future__ import annotations

from fastapi import APIRouter, status
from virgo_agentic_dag.api.web.api_responses.dag_detail_response import (
    DagDetailResponse,
)
from virgo_agentic_dag.api.web.api_responses.dag_summary_response import (
    DagSummaryResponse,
)
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController

PREFIX = "/api"
TAG = "dags"


class DagRoute:
    """Names the dag routes."""

    def __init__(self, controller: DagController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return the router that carries the dag routes."""
        router = APIRouter(prefix=PREFIX, tags=[TAG])
        router.add_api_route(
            "/dags",
            self._controller.list_dags,
            methods=["GET"],
            response_model=list[DagSummaryResponse],
            summary="List every dag on this host",
        )
        router.add_api_route(
            "/dags/{name}",
            self._controller.get_dag,
            methods=["GET"],
            response_model=DagDetailResponse,
            summary="Read one dag with its nodes and audit tail",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "No dag on this host has the name."
                }
            },
        )
        router.add_api_route(
            "/dags/{dag_name}/{node_id}",
            self._controller.get_node_by_name,
            methods=["GET"],
            response_model=NodeResponse,
            summary="Get a single node of a dag",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "The dag or the node is unknown on this host."
                }
            },
        )

        return router
