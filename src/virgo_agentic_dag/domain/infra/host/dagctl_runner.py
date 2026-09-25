"""The interface for running dagctl and returning its result."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from virgo_agentic_dag.domain.execution.run_result import RunResult


class DagctlRunner(ABC):
    """Runs a dagctl command in a child process and returns its exit code and output."""

    @abstractmethod
    async def run(self, arguments: list[str], dag_home: Path) -> RunResult:
        """Run dagctl with the arguments in the dag home and return once the process exits."""
