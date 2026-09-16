"""The liveness route."""

from __future__ import annotations

from fastapi import APIRouter
from virgo_agentic_dag.api.web.api_responses.health_response import HealthResponse
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController

TAG = "health"


class HealthRoute:
    """Names the liveness route."""

    def __init__(self, controller: HealthController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return the router that carries the liveness route."""
        router = APIRouter(tags=[TAG])
        router.add_api_route(
            "/healthz",
            self._controller.get_health,
            methods=["GET"],
            response_model=HealthResponse,
            summary="Read the liveness status of this server",
        )

        return router
