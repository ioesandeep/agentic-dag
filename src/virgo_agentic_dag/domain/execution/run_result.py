"""The exit code and captured output of one external command."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def get_output(self) -> str:
        """Return both streams together, for logs and failure evidence."""
        return f"{self.stdout}{self.stderr}"
