"""The web server the serve verb runs, built on uvicorn."""

from __future__ import annotations


import uvicorn

from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.infra.web.web_server import WebServer


class UvicornWebServer(WebServer):
    """Serves an application under uvicorn, which calls the factory to build it."""

    def __init__(self, application_factory: WebApplicationFactory) -> None:
        self._application_factory = application_factory

    async def serve(self, host: str, port: int) -> None:
        """Serve on this host and port until the process is interrupted."""
        config = uvicorn.Config(
            self._application_factory.build, host=host, port=port, factory=True
        )

        await uvicorn.Server(config).serve()
