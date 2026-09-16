"""The named exit codes a command returns, so no caller reasons about bare numbers."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    RUN_COMPLETE = 3
    RUN_BUSY = 75
