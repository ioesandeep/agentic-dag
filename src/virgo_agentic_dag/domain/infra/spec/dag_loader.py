"""The port that reads an approved graph file into a validated DagSpec."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.specs.dag_spec import DagSpec


class DagLoader(ABC):
    """Loads an approved graph from persistent form into its domain model."""

    @abstractmethod
    def load(self, path: Path) -> DagSpec:
        """Read the graph at ``path`` and return its validated model."""
