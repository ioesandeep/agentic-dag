"""The parsed serve request, naming the address the web api binds to."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.command.command import Command

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8788


@dataclass(frozen=True)
class ServeCommand(Command):
    """A request to serve the read-only web api over this host's runs."""

    # loopback by default, because widening it exposes every run on this host
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    def requires_run_lock(self) -> bool:
        """The server changes no run, so it needs no run lock."""
        return False

    def requires_database(self) -> bool:
        """The server names no run, so it opens no database of its own."""
        return False
