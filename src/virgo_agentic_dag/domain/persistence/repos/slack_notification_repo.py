"""Where the Slack thread bound to a node lives, whatever database holds it."""

from __future__ import annotations

from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.persistence.entities.slack_notification import (
    SlackNotification,
)


class SlackNotificationRepo(ABC):
    """Reads and writes the thread a node's Slack updates belong in."""

    @abstractmethod
    async def get_by_node_id(self, node_id: str) -> SlackNotification | None:
        """Return this node's thread, or None before its first message is posted."""

    @abstractmethod
    async def save(self, slack_notification: SlackNotification) -> None:
        """Persist this binding between a node and the thread it speaks in."""
