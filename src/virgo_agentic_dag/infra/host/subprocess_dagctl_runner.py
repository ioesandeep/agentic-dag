"""The subprocess implementation of DagctlRunner."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from virgo_agentic_dag.config.constants import DAGCTL_ENVIRONMENT_VARIABLE_NAMES
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.dagctl_runner import DagctlRunner


class SubprocessDagctlRunner(DagctlRunner):
    """Runs dagctl in a child process with only the system variables from the current process."""

    async def run(self, arguments: list[str], dag_home: Path) -> RunResult:
        environment = self._get_environment()
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "virgo_agentic_dag.api.cli.dagctl",
            *arguments,
            cwd=dag_home,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )

        stdout_bytes, stderr_bytes = await process.communicate()
        exit_code = await process.wait()
        stdout = stdout_bytes.decode()
        stderr = stderr_bytes.decode()

        return RunResult(returncode=exit_code, stdout=stdout, stderr=stderr)

    def _get_environment(self) -> dict[str, str]:
        """Return the dagctl environment variables from this process, or an empty dictionary when none exist."""
        return {
            name: os.environ[name]
            for name in DAGCTL_ENVIRONMENT_VARIABLE_NAMES
            if name in os.environ
        }
