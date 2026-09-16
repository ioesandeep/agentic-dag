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
