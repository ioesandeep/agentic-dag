"""An API route for a node's agent transcript."""

from __future__ import annotations

from fastapi import APIRouter, status
from virgo_agentic_dag.api.web.api_responses.conversation_page_response import (
    ConversationPageResponse,
)
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController


class ConversationRoute:
    """A builder for a node's agent transcript route."""

    def __init__(self, controller: DagController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return a router containing the conversation route."""
        router = APIRouter(prefix="/api", tags=["conversations"])
        router.add_api_route(
            "/dags/{dag_name}/{node_id}/conversation",
            self._controller.get_conversation_page,
            methods=["GET"],
            response_model=ConversationPageResponse,
            summary="Return a page of a node's agent transcript.",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "A 404 response when the dag or node is unknown or the cursor is past the end of the transcript."
                }
            },
        )

        return router
