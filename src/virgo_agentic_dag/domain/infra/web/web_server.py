"""The web server the framework runs its application on."""

from __future__ import annotations

from abc import ABC, abstractmethod


class WebServer(ABC):
    """Serves an application on one address until it is stopped."""

    @abstractmethod
    async def serve(self, host: str, port: int) -> None:
        """Serve on this host and port, returning once the server has stopped."""
