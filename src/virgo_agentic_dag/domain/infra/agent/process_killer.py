from abc import ABC, abstractmethod


class ProcessKiller(ABC):
    """Stops an agent process and its child processes."""

    @abstractmethod
    def kill(self, pid: int) -> None:
        """End the agent's execution."""
