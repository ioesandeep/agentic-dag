"""The immutable specification of a run, holding its graph and host settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from virgo_agentic_dag.domain.notifications.notification_dispatcher_type import (
    NotificationDispatcherType,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.utils.dag_utils import get_dag_db_path

DEFAULT_BASE_BRANCH = "main"

WORKSPACE_HOME = Path.home() / "tmp" / "agentic-dag"


@dataclass(frozen=True)
class DagSpec:
    # name of the task this graph carries out
    name: str
    nodes: tuple[NodeSpec, ...]
    # what every node inherits unless it names its own
    project_root: Path | None = None
    workspace_path: Path | None = None
    executor_agent: ExecutorAgent = ExecutorAgent.CLAUDE
    base_branch: str = ""
    # where this run keeps its database; the run's own home when unnamed
    db_path: Path | None = None
    max_workers: int = 2
    # how long the host waits between passes once a run is started
    tick_interval_seconds: int = 300
    caps: AttemptBudget = AttemptBudget()
    slack_channel: str = ""
    repo_slug: str = ""
    notification_dispatcher: NotificationDispatcherType = NotificationDispatcherType.BOT
    sse_url: str = ""
    # to be inferred from the account the agent's credentials act as
    agent_account: str = ""

    def get_db_path(self) -> Path:
        """Return where this dag's run keeps its database, its choice or the run's home."""
        return self.db_path or get_dag_db_path(self.name)

    def get_project_root(self, node: NodeSpec) -> Path:
        """Return the checkout this node works in, defaulting to this dag's own."""
        return node.project_root or self.project_root or Path.cwd()

    def get_workspace_path(self, node: NodeSpec) -> Path:
        """Return where this node's worktrees are cut, defaulting to this dag's scratch home."""
        return node.workspace_path or self.workspace_path or WORKSPACE_HOME / self.name

    def get_executor_agent(self, node: NodeSpec) -> ExecutorAgent:
        """Returns the node's executor agent or the DAG's default executor agent."""
        return node.executor_agent or self.executor_agent

    def get_base_branch(self, node: NodeSpec) -> str:
        """Return the branch this node's worktree is cut from."""
        return node.base_branch or self.base_branch or DEFAULT_BASE_BRANCH

    def find_node(self, node_id: str) -> NodeSpec | None:
        return next((n for n in self.nodes if n.id == node_id), None)
