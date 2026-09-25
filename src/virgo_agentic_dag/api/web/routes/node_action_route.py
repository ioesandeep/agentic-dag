"""The api routes for retrying, waking, and stopping a node."""

from __future__ import annotations

from fastapi import APIRouter, status
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.controllers.node_action_controller import (
    NodeActionController,
)


class NodeActionRoute:
    """Builds the routes for retrying, waking, and stopping a node."""

    def __init__(self, controller: NodeActionController) -> None:
        self._controller = controller

    def build(self) -> APIRouter:
        """Return the router for retrying, waking, and stopping a node."""
        router = APIRouter(prefix="/api", tags=["node-actions"])
        router.add_api_route(
            "/dags/{dag_name}/{node_id}/retry",
            self._controller.retry_node,
            methods=["POST"],
            response_model=NodeResponse,
            summary="Retry a node of a dag",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "The dag or the node is unknown on this host."
                },
                status.HTTP_409_CONFLICT: {
                    "description": "Another command has the run lock, or dagctl retry refuses the node."
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "description": "dagctl retry exits with an unexpected code."
                },
            },
        )
        router.add_api_route(
            "/dags/{dag_name}/{node_id}/wake",
            self._controller.wake_node,
            methods=["POST"],
            response_model=NodeResponse,
            summary="Wake a resting node of a dag",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "The dag or the node is unknown on this host."
                },
                status.HTTP_409_CONFLICT: {
                    "description": "The node is not resting, another command has the run lock, or dagctl recover refuses to wake the node."
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "description": "dagctl recover exits with an unexpected code."
                },
            },
        )
        router.add_api_route(
            "/dags/{dag_name}/{node_id}/stop",
            self._controller.stop_node,
            methods=["POST"],
            response_model=NodeResponse,
            summary="Stop the running session of a node",
            responses={
                status.HTTP_404_NOT_FOUND: {
                    "description": "The dag or the node is unknown on this host."
                },
                status.HTTP_409_CONFLICT: {
                    "description": "Another command has the run lock, or dagctl stop refuses the node."
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "description": "dagctl stop exits with an unexpected code."
                },
            },
        )

        return router
