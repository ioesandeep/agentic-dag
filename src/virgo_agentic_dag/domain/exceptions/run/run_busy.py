"""The error raised when another pass is already working this run."""

from __future__ import annotations


class RunBusy(RuntimeError):
    """Raised when a run is already held by another pass, so this one should retry later."""
