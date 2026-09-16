"""Handles the liveness route."""

from __future__ import annotations

from virgo_agentic_dag.api.web.api_responses.health_response import HealthResponse


class HealthController:
    """Handles the liveness route."""

    async def get_health(self) -> HealthResponse:
        """Return the liveness status of this server."""
        return HealthResponse(status="ok")
