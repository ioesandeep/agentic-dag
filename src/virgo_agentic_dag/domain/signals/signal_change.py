"""One signal's rendered description of a change on a pull request."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.domain.notifications.notification_type import NotificationType


@dataclass(frozen=True)
class SignalChange:
    """One signal's detected change, its rendered text, and the watermark that retires it."""

    signal: str
    mark: str
    heading: str
    body: str
    wakes_node: bool = True
    notification: NotificationType | None = None
    count: int = 0

    def render(self) -> str:
        """Return this change as a section of the node's brief."""
        return f"### {self.heading}\n\n{self.body}"
