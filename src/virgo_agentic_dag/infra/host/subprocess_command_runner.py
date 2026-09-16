"""The production CommandRunner, running external commands through the host shell-free."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner


class SubprocessCommandRunner(CommandRunner):
    """Runs a command as a direct argv subprocess, never through a shell."""

    def __init__(
        self, timeout_seconds: int = 30, env: Mapping[str, str] | None = None
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._env = None if env is None else dict(env)

    def run(self, argv: Sequence[str], cwd: Path | None = None) -> RunResult:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self._timeout_seconds,
            check=False,
            env=self._env,
        )

        return RunResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
