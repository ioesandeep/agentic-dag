"""The parsed adopt request, naming a pull request to add to a run as a node."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from virgo_agentic_dag.domain.command.dag_command import DagCommand
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent


@dataclass(frozen=True)
class AdoptCommand(DagCommand):
    """An existing pull request adopted into a run as a resting node."""

    # the url of the pull request to take over
    pr: str
    # coined from the pull request number when the caller names none
    node_id: str = ""
    # an agent session to resume on the first wake; a fresh one is minted when empty
    session: str = ""
    executor: ExecutorAgent | None = None
    # the checkout the pull request lives in, when not the dag's own
    project_root: Path | None = None
    # where the node's worktree is cut, when not the dag's own
    workspace_path: Path | None = None

    def requires_run_lock(self) -> bool:
        """Adopt claims the run itself, waiting out the pass that holds it instead of failing."""
        return False
