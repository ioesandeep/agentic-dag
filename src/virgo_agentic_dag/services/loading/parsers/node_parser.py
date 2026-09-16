"""Parses one node table from an approved graph into a NodeSpec."""

from __future__ import annotations

from pathlib import Path

from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec
from virgo_agentic_dag.services.loading.toml.toml_reader import TomlReader


class NodeParser:
    """Builds a NodeSpec from a TOML node table, ignoring any key the spec no longer carries."""

    def __init__(self, reader: TomlReader) -> None:
        self._reader = reader

    def parse(self, raw: object, index: int) -> NodeSpec:
        where = f"dag.nodes[{index}]"
        table = self._reader.require_table(raw, where)
        node_id = self._reader.require_str(table, "id", where)

        return NodeSpec(
            id=node_id,
            depends_on=self._reader.get_str_tuple(
                table, "depends_on", f"node {node_id!r}"
            ),
            title=str(table.get("title", "")),
            name=str(table.get("name", "")),
            executor_agent=self.get_executor_agent(table, f"node {node_id!r}"),
            instructions=str(table.get("instructions", table.get("brief", ""))),
            pr=str(table.get("pr", "")),
            session=str(table.get("session", "")),
            project_root=self._get_path(table, "project_root"),
            workspace_path=self._get_path(table, "workspace_path"),
            base_branch=str(table.get("base_branch", "")),
        )

    def _get_path(self, table: dict[str, object], key: str) -> Path | None:
        raw = str(table.get(key, ""))
        if not raw:
            return None

        return Path(raw).expanduser()

    def get_executor_agent(
        self, table: dict[str, object], where: str
    ) -> ExecutorAgent | None:
        """Return the agent named here, whether that is a node table or the dag itself."""
        raw = str(table.get("executor_agent", table.get("executor", "")))
        if not raw:
            return None

        try:
            return ExecutorAgent(raw)
        except ValueError:
            raise SpecError(
                f"{where}: no launcher for executor agent {raw!r}"
            ) from None
