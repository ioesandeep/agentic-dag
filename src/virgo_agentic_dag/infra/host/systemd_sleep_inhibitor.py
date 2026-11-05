"""The Linux SleepInhibitor, keeping the host awake with a systemd inhibitor lock."""

from __future__ import annotations

import os
import subprocess

from virgo_agentic_dag.domain.infra.host.sleep_inhibitor import SleepInhibitor
from virgo_agentic_dag.labels.en import LABELS


class SystemdSleepInhibitor(SleepInhibitor):
    """Keeps a Linux host awake with a systemd inhibitor lock until this process exits."""

    def __init__(self) -> None:
        self._systemd_inhibit_process: subprocess.Popen[bytes] | None = None

    def keep_awake(self) -> None:
        pid = os.getpid()
        reason = LABELS["sleepInhibitorReason"]
        systemd_inhibit_argv = [
            "systemd-inhibit",
            "--what=sleep:idle",
            "--who=virgo-agentic-dag",
            f"--why={reason}",
            "--mode=block",
            "tail",
            f"--pid={pid}",
            "-f",
            "/dev/null",
        ]

        self._systemd_inhibit_process = subprocess.Popen(
            systemd_inhibit_argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
