"""The timeout configuration for run lock acquisition."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunLockConfig:
    """The wait limit for acquiring a run lock."""

    # the maximum run lock wait in seconds, or None for an unlimited wait
    timeout: float | None
