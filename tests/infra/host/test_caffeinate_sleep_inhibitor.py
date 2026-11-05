import os
import subprocess

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.infra.host.caffeinate_sleep_inhibitor import (
    CaffeinateSleepInhibitor,
)

pytestmark = pytest.mark.unit


def test_keep_awake_starts_caffeinate_for_the_current_process(
    mocker: MockerFixture,
) -> None:
    pid = os.getpid()
    caffeinate_argv = ["/usr/bin/caffeinate", "-i", "-m", "-s", "-w", str(pid)]

    popen = mocker.patch.object(subprocess, "Popen")
    sleep_inhibitor = CaffeinateSleepInhibitor()

    sleep_inhibitor.keep_awake()

    popen.assert_called_once_with(
        caffeinate_argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
