"""A cause of node session recovery."""

from __future__ import annotations

from enum import Enum


class RecoveryCauseEnum(Enum):
    TURN_CAP_REACHED = "turn_cap_reached"
    BACKGROUND_WAIT_TERMINATED = "background_wait_terminated"
    USAGE_LIMIT = "usage_limit"
    PROVIDER_FAILURE = "provider_failure"
    PROCESS_KILLED = "process_killed"
    NO_PULL_REQUEST = "no_pull_request"
    OVERDUE = "overdue"
    WORKSPACE_INCONSISTENT = "workspace_inconsistent"
