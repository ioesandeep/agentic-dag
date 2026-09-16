"""The specification of one node, holding its dependencies and agent instructions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent


@dataclass(frozen=True)
class NodeSpec:
    id: str
    depends_on: tuple[str, ...] = ()
    title: str = ""
    name: str = ""
    instructions: str = ""
    # each of these falls back to the dag's own when this node names none
    project_root: Path | None = None
    workspace_path: Path | None = None
    executor_agent: ExecutorAgent | None = None
    base_branch: str = ""
    # the url of a pull request this node takes over instead of opening its own
    pr: str = ""
    session: str = ""

    def is_adopted(self) -> bool:
        """Report whether this node takes over a pull request that already exists."""
        return bool(self.pr)

    def get_agent_name(self) -> str:
        """Return the display name of the agent assigned to this node."""
        return self.name or self.title or self.id
