"""The liveness check for a process the framework started."""

from __future__ import annotations

import os


def is_process_alive(pid: int) -> bool:
    """Report whether the process with this id is still running."""
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True
