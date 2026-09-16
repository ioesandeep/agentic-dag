"""Reads the graph files this host keeps, one dag to a directory under the dag home."""

from __future__ import annotations

import logging
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.utils.dag_utils import get_dag_graph_path, get_dag_root

logger = logging.getLogger(__name__)


class DagService:
    """Answers what this host has planned, from graph files and nothing else."""

    def __init__(self, dag_loader: DagLoader) -> None:
        self._dag_loader = dag_loader

    def get_dag_list(self) -> list[DagSpec]:
        """Return the spec of every dag on this host, skipping any graph that will not load."""
        loaded = [self._load_dag_spec(path) for path in self._find_graph_files()]

        return [dag_spec for dag_spec in loaded if dag_spec is not None]

    def _find_graph_files(self) -> list[Path]:
        """Return the graph file of every dag that keeps one under the dag home."""
        dag_root: Path = get_dag_root()
        if not dag_root.is_dir():
            return []

        graph_files = [
            get_dag_graph_path(entry.name)
            for entry in dag_root.iterdir()
            if entry.is_dir() and get_dag_graph_path(entry.name).is_file()
        ]

        return sorted(graph_files)

    def _load_dag_spec(self, path: Path) -> DagSpec | None:
        """Return this graph file's spec, or nothing when it will not load.

        A listing spans every dag on the host, including ones written by an older
        version, so one graph the loader rejects must not sink the whole answer.
        """
        try:
            return self._dag_loader.load(path)
        except (SpecError, OSError) as error:
            logger.warning("%s will not load: %s", path, error)

            return None
