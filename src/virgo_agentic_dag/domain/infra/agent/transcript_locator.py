"""The interface for resolving which file records a node agent's transcript."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent


class TranscriptLocator(ABC):
    """Resolves a node agent's transcript file for the agent product that wrote it."""

    @abstractmethod
    def get_transcript_path(self, agent: NodeAgent) -> Path | None:
        """Returns the path to a node agent's transcript file."""
