"""The delivery route a run dispatches its notifications through."""

from __future__ import annotations

from enum import Enum


class NotificationDispatcherType(Enum):
    BOT = "bot"
    MCP = "mcp"
