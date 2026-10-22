import sys

import pytest

from virgo_agentic_dag.infra.host.subprocess_command_runner import (
    SubprocessCommandRunner,
)

pytestmark = pytest.mark.integration


def test_captures_stdout_and_zero_exit():
    result = SubprocessCommandRunner().run(["echo", "hello"])

    assert result.returncode == 0
    assert result.stdout.strip() == "hello"


def test_reports_a_non_zero_exit_without_raising():
    assert SubprocessCommandRunner().run(["false"]).returncode != 0


def test_missing_command_raises_oserror():
    with pytest.raises(OSError):
        SubprocessCommandRunner().run(["definitely-not-a-real-command-xyz"])


def test_returns_124_when_a_command_exceeds_its_timeout() -> None:
    command_runner = SubprocessCommandRunner(timeout_seconds=1)
    argv = [sys.executable, "-c", "import time; time.sleep(2)"]

    run_result = command_runner.run(argv)

    assert run_result.returncode == 124
    assert sys.executable in run_result.stderr
    assert "time.sleep(2)" in run_result.stderr
    assert "1-second timeout" in run_result.stderr
