"""A DagLoader that reads an approved graph from a TOML file."""

from __future__ import annotations

import tomllib
from pathlib import Path

from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.notifications.notification_dispatcher_type import (
    NotificationDispatcherType,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import (
    AttemptBudget,
)
from virgo_agentic_dag.services.loading.parsers.node_parser import NodeParser
from virgo_agentic_dag.services.loading.toml.toml_reader import TomlReader
from virgo_agentic_dag.utils.attempt_budget import (
    get_default_recovery_attempts_allowed,
)


class TomlDagLoader(DagLoader):
    """Reads and parses an approved graph from TOML, rejecting malformed input."""

    def __init__(self) -> None:
        self._reader = TomlReader(SpecError)
        self._nodes = NodeParser(self._reader)

    def load(self, path: Path) -> DagSpec:
        try:
            data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise SpecError(f"dag: {Path(path).name} is not valid TOML: {error}")

        return self.parse(data)

    def parse(self, data: dict[str, object]) -> DagSpec:
        """Build a DagSpec from parsed TOML, rejecting malformed input with a reason."""
        name = self._reader.require_str(data, "name", "dag")
        raw_nodes = self._reader.get_list(data, "nodes", "dag")
        if not raw_nodes:
            raise SpecError("dag: 'nodes' must be a non-empty list")

        nodes = tuple(
            self._nodes.parse(raw, index) for index, raw in enumerate(raw_nodes)
        )

        dag_executor_agent = self._nodes.get_executor_agent(data, f"dag {name!r}")

        return DagSpec(
            name=name,
            nodes=nodes,
            project_root=self._get_path(data, "project_root"),
            workspace_path=self._get_path(data, "workspace_path"),
            executor_agent=dag_executor_agent or ExecutorAgent.CLAUDE,
            base_branch=str(data.get("base_branch", "")),
            db_path=self._get_path(data, "db_path"),
            max_workers=self._reader.get_positive_int(data, "max_workers", 2, "dag"),
            tick_interval_seconds=self._reader.get_positive_int(
                data, "tick_interval_seconds", 300, "dag"
            ),
            caps=self._get_caps(data),
            slack_channel=str(data.get("slack_channel", "")),
            repo_slug=str(data.get("repo_slug", "")),
            notification_dispatcher=self._get_notification_dispatcher(data),
            sse_url=str(data.get("sse_url", "")),
            agent_account=str(data.get("agent_account", "")),
        )

    def _get_path(self, data: dict[str, object], key: str) -> Path | None:
        raw = str(data.get(key, ""))
        if not raw:
            return None

        return Path(raw).expanduser()

    def _get_notification_dispatcher(
        self, data: dict[str, object]
    ) -> NotificationDispatcherType:
        raw = str(
            data.get("notification_dispatcher", NotificationDispatcherType.BOT.value)
        )

        try:
            return NotificationDispatcherType(raw)
        except ValueError as error:
            raise SpecError(
                f"dag: notification_dispatcher must be bot or mcp, not {raw}"
            ) from error

    def _get_caps(self, data: dict[str, object]) -> AttemptBudget:
        table = data.get("caps")
        if table is None:
            return AttemptBudget()

        caps = self._reader.require_table(table, "dag.caps")

        return AttemptBudget(
            node_wakes=self._reader.get_positive_int(
                caps, "node_wakes", AttemptBudget().node_wakes, "dag.caps"
            ),
            node_recoveries=self._reader.get_positive_int(
                caps,
                "node_recoveries",
                get_default_recovery_attempts_allowed(),
                "dag.caps",
            ),
            session_timeout_seconds=self._reader.get_positive_int(
                caps,
                "session_timeout_seconds",
                AttemptBudget().session_timeout_seconds,
                "dag.caps",
            ),
            session_turns=self._reader.get_positive_int(
                caps,
                "session_turns",
                AttemptBudget().session_turns,
                "dag.caps",
            ),
        )
