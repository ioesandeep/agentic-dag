"""The possible states of a learning extraction lock file."""

from __future__ import annotations

from enum import Enum


class ExtractionLockStateEnum(Enum):
    FREE = "free"  # no lock file, or the process id of a process that has exited
    HELD = "held"  # the process id of a running process
    UNREADABLE = "unreadable"  # an empty file, or contents that are not a process id
