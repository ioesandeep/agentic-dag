"""The retry ceilings that stop a node and escalate it to a human."""

from __future__ import annotations

from dataclasses import dataclass

from virgo_agentic_dag.utils.attempt_budget import (
    get_default_recovery_attempts_allowed,
)


@dataclass(frozen=True)
class AttemptBudget:
    node_wakes: int = 12
    node_recoveries: int = get_default_recovery_attempts_allowed()
    session_timeout_seconds: int = 1800
    session_turns: int = 120
