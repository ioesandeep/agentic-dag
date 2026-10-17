from abc import ABC, abstractmethod

from virgo_agentic_dag.domain.execution.run_result import RunResult


class GithubCloneHandle(ABC):
    """Control an owned clone until its process terminates."""

    @abstractmethod
    def poll(self) -> int | None:
        """Return the exit code when the clone terminates."""

    @abstractmethod
    async def terminate(self) -> None:
        """Stop the clone process group before releasing its resources."""

    @abstractmethod
    async def wait(self, timeout_seconds: float = 1800) -> RunResult:
        """Wait for clone completion within the worker's timeout."""
