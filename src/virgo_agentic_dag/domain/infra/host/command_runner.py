"""The port through which the controller runs an external command and reads its result."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from virgo_agentic_dag.domain.execution.run_result import RunResult


class CommandRunner(ABC):
    """Runs one external command to completion and returns its exit code and output."""

    @abstractmethod
    def run(self, argv: Sequence[str], cwd: Path | None = None) -> RunResult:
        """Run the command to completion, optionally inside ``cwd``.

        Raises:
            OSError: when the command cannot be started at all.
        """
