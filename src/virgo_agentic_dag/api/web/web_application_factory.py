"""Builds the web api application."""

from __future__ import annotations

from fastapi import FastAPI
from virgo_agentic_dag.api.web.routes.conversation_route import ConversationRoute
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute

TITLE = "virgo-agentic-dag"
DESCRIPTION = (
    "A read-only api over the dags this host records. "
    "No route starts, advances, or stops a dag."
)


class WebApplicationFactory:
    """Builds the web api application."""

    def __init__(
        self,
        dag_route: DagRoute,
        health_route: HealthRoute,
        memory_route: MemoryRoute,
        conversation_route: ConversationRoute,
    ) -> None:
        self._dag_route = dag_route
        self._health_route = health_route
        self._memory_route = memory_route
        self._conversation_route = conversation_route

    def build(self) -> FastAPI:
        """Return the web api application."""
        application = FastAPI(title=TITLE, description=DESCRIPTION)
        application.include_router(self._health_route.build())
        application.include_router(self._memory_route.build())
        application.include_router(self._conversation_route.build())
        application.include_router(self._dag_route.build())

        return application
