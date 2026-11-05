import os
import subprocess

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.infra.host.systemd_sleep_inhibitor import SystemdSleepInhibitor

pytestmark = pytest.mark.unit


def test_keep_awake_starts_systemd_inhibit_for_the_current_process(
    mocker: MockerFixture,
) -> None:
    pid = os.getpid()
    systemd_inhibit_argv = [
        "systemd-inhibit",
        "--what=sleep:idle",
        "--who=virgo-agentic-dag",
        "--why=dagctl watches a live dag run for pull request events",
        "--mode=block",
        "tail",
        f"--pid={pid}",
        "-f",
        "/dev/null",
    ]

    popen = mocker.patch.object(subprocess, "Popen")
    sleep_inhibitor = SystemdSleepInhibitor()

    sleep_inhibitor.keep_awake()

    popen.assert_called_once_with(
        systemd_inhibit_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
