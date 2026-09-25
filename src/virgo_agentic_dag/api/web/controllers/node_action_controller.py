"""The controller for retrying, waking, and stopping a node."""

from __future__ import annotations

from fastapi import HTTPException, status
from virgo_agentic_dag.api.web.api_requests.retry_request import RetryRequest
from virgo_agentic_dag.api.web.api_requests.wake_request import WakeRequest
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.service.node_action_service import NodeActionService
from virgo_agentic_dag.api.web.utils.get_node_unknown_exception import (
    get_node_unknown_exception,
)
from virgo_agentic_dag.domain.exceptions.run.node_action_failed import NodeActionFailed
from virgo_agentic_dag.domain.exceptions.run.node_action_refused import (
    NodeActionRefused,
)


class NodeActionController:
    """Translates node retry, wake, and stop results into HTTP responses."""

    def __init__(self, node_action_service: NodeActionService) -> None:
        self._node_action_service = node_action_service

    async def retry_node(
        self, dag_name: str, node_id: str, retry_request: RetryRequest
    ) -> NodeResponse:
        """Return a node of a dag after the retry command exits."""
        try:
            node_response = await self._node_action_service.retry_node(
                dag_name, node_id, retry_request
            )
        except NodeActionRefused as refused:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(refused)
            ) from refused
        except NodeActionFailed as failed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(failed)
            ) from failed

        if node_response is None:
            raise get_node_unknown_exception(dag_name, node_id)

        return node_response

    async def wake_node(
        self, dag_name: str, node_id: str, wake_request: WakeRequest
    ) -> NodeResponse:
        """Return a node of a dag after the recover command wakes it."""
        try:
            node_response = await self._node_action_service.wake_node(
                dag_name, node_id, wake_request
            )
        except NodeActionRefused as refused:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(refused)
            ) from refused
        except NodeActionFailed as failed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(failed)
            ) from failed

        if node_response is None:
            raise get_node_unknown_exception(dag_name, node_id)

        return node_response

    async def stop_node(self, dag_name: str, node_id: str) -> NodeResponse:
        """Return a node of a dag after the stop command exits."""
        try:
            node_response = await self._node_action_service.stop_node(dag_name, node_id)
        except NodeActionRefused as refused:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=str(refused)
            ) from refused
        except NodeActionFailed as failed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(failed)
            ) from failed

        if node_response is None:
            raise get_node_unknown_exception(dag_name, node_id)

        return node_response
