"""One node of the running graph, carrying everything the handlers need to know about it."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from virgo_agentic_dag.domain.specs.dag_spec import DEFAULT_BASE_BRANCH
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.utils.attempt_budget import (
    get_default_recovery_attempts_allowed,
)


@dataclass(frozen=True)
class GraphNode:
    id: str
    title: str = ""
    name: str = ""
    instructions: str = ""
    depends_on: tuple[str, ...] = ()
    executor_agent: ExecutorAgent | None = None
    # the checkout this node works in, which gh and git both resolve from
    project_root: Path = field(default_factory=Path.cwd)
    # where its worktree is cut, and the branch it is cut from
    workspace_path: Path = field(default_factory=Path.cwd)
    base_branch: str = DEFAULT_BASE_BRANCH
    # the url of a pull request this node takes over instead of opening its own
    pr: str = ""
    recovery_attempts_allowed: int = get_default_recovery_attempts_allowed()

    def get_agent_name(self) -> str:
        """Return the display name of this node's agent."""
        return self.name or self.title or self.id

    def is_adopted(self) -> bool:
        """Report whether this node takes over a pull request that already exists."""
        return bool(self.pr)
