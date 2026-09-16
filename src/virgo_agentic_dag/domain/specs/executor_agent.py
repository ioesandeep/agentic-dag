"""The agent product a node's work is dispatched to."""

from __future__ import annotations

from enum import Enum


class ExecutorAgent(Enum):
    CLAUDE = "claude"
    CODEX = "codex"
