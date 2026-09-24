"""The dag memory API route."""

from __future__ import annotations

from fastapi import APIRouter, status
from virgo_agentic_dag.api.web.api_responses.memory_response import MemoryResponse
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController

PREFIX = "/api"
TAG = "memory"


class MemoryRoute:
    """Builds the router for the memory file of a dag."""

    def __init__(self, controller: DagController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return the dag memory API router."""
        router = APIRouter(prefix=PREFIX, tags=[TAG])
        router.add_api_route(
            "/dags/{name}/memory",
            self._controller.get_memory_by_name,
            methods=["GET"],
            response_model=MemoryResponse,
            summary="Get the memory file of a dag",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "No dag on this host has the name."
                }
            },
        )

        return router
