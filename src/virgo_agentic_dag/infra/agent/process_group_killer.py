import os
import signal

from virgo_agentic_dag.domain.infra.agent.process_killer import ProcessKiller


class ProcessGroupKiller(ProcessKiller):
    """Terminates agent processes and their child processes."""

    def kill(self, pid: int) -> None:
        """End the agent's execution."""
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return
