"""The error raised when a command needs the web extra and it is not installed."""

from __future__ import annotations


class WebExtraMissing(RuntimeError):
    """Raised when serve runs on a host without fastapi and uvicorn."""
