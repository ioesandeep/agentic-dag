"""The macOS SleepInhibitor, keeping the host awake with caffeinate."""

from __future__ import annotations

import os
import subprocess

from virgo_agentic_dag.domain.infra.host.sleep_inhibitor import SleepInhibitor


class CaffeinateSleepInhibitor(SleepInhibitor):
    """Keeps a Mac awake with caffeinate until this process exits."""

    def __init__(self) -> None:
        self._caffeinate_process: subprocess.Popen[bytes] | None = None

    def keep_awake(self) -> None:
        pid = os.getpid()
        caffeinate_argv = ["/usr/bin/caffeinate", "-i", "-m", "-s", "-w", str(pid)]
        self._caffeinate_process = subprocess.Popen(
            caffeinate_argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
