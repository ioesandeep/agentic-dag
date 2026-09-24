"""The GET route for a dag's recovery sessions."""

from __future__ import annotations

from fastapi import APIRouter, status
from virgo_agentic_dag.api.web.api_responses.recovery_session_response import (
    RecoverySessionResponse,
)
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController


class RecoverySessionRoute:
    """A router builder for a dag's recovery sessions."""

    def __init__(self, controller: DagController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return the API router for a dag's recovery sessions."""
        router = APIRouter(prefix="/api", tags=["recovery-sessions"])
        router.add_api_route(
            "/dags/{name}/recovery-sessions",
            self._controller.get_recovery_sessions_by_dag_name,
            methods=["GET"],
            response_model=list[RecoverySessionResponse],
            summary="Get the recovery sessions of a dag, newest first",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "No dag on this host has the name."
                }
            },
        )

        return router
