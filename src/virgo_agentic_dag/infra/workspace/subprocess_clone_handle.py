import asyncio
import os
import re
import signal

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.ports.github_clone_handle import GithubCloneHandle
from virgo_agentic_dag.domain.execution.run_result import RunResult


class SubprocessCloneHandle(GithubCloneHandle):
    """Supervise a clone and bound its diagnostic output."""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        self._process = process
        completion = self._collect_output()
        self._completion_task = asyncio.create_task(completion)
        self._termination_task: asyncio.Task[None] | None = None

    def poll(self) -> int | None:
        """Return the clone's observed exit code."""
        return self._process.returncode

    async def terminate(self) -> None:
        """Stop the owned process group and reap the clone."""
        if self._termination_task is None:
            termination = self._terminate_group()
            self._termination_task = asyncio.create_task(termination)

        is_cancelled = False
        is_complete = self._termination_task.done()
        while not is_complete:
            completion = asyncio.shield(self._termination_task)
            try:
                await completion
            except asyncio.CancelledError:
                is_cancelled = True

            is_complete = self._termination_task.done()

        self._termination_task.result()
        if is_cancelled:
            raise asyncio.CancelledError

    async def _terminate_group(self) -> None:
        self._signal_group(signal.SIGTERM)
        completion = asyncio.shield(self._completion_task)
        try:
            await asyncio.wait_for(completion, timeout=5)
        except TimeoutError:
            pass
        finally:
            self._signal_group(signal.SIGKILL)

        await self._completion_task

    async def wait(self, timeout_seconds: float = 1800) -> RunResult:
        """Return sanitized clone output after process completion."""
        completion = asyncio.shield(self._completion_task)
        try:
            return await asyncio.wait_for(completion, timeout_seconds)
        except TimeoutError as error:
            await self.terminate()

            raise CatalogError(
                code=CatalogErrorCodeEnum.IMPORT_TIMEOUT,
                detail="The GitHub clone exceeds its timeout.",
            ) from error
        except asyncio.CancelledError:
            await self.terminate()

            raise

    def _signal_group(self, signal_number: int) -> None:
        try:
            os.killpg(self._process.pid, signal_number)
        except ProcessLookupError:
            pass

    async def _collect_output(self) -> RunResult:
        output = bytearray()
        assert self._process.stdout is not None
        while True:
            chunk = await self._process.stdout.read(4096)
            if not chunk:
                break

            remaining_bytes = 4096 - len(output)
            output.extend(chunk[:remaining_bytes])

        returncode = await self._process.wait()
        decoded_output = output.decode("utf-8", errors="replace")
        plain_output = re.sub(
            r"\x1b\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0b-\x1f\x7f]", "", decoded_output
        )
        sanitized_output = re.sub(
            r"(?i)(?:https?://|ssh://|git@)\S+|(?:gh[pousr]_|github_pat_)\w+"
            r"|(?:authorization|token|password|secret)[^\n]*",
            "[redacted]",
            plain_output,
        )

        return RunResult(returncode=returncode, stderr=sanitized_output[:4096])
