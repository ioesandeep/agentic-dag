"""The error raised when this host's job system refuses to register or retire a job."""

from __future__ import annotations


class SchedulingError(RuntimeError):
    """Raised when a job cannot be registered with, or retired from, the host."""
