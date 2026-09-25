import asyncio
import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.infra.host.subprocess_dagctl_runner import (
    SubprocessDagctlRunner,
)

pytestmark = pytest.mark.unit


async def test_run_sets_only_the_dagctl_environment_variables_when_the_process_environment_includes_a_token(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    mocker.patch.dict(
        os.environ,
        {"PATH": "/usr/bin", "HOME": "/Users/sandeep", "SLACK_BOT_TOKEN": "xoxb-1"},
        clear=True,
    )

    process = mocker.MagicMock(spec=asyncio.subprocess.Process)
    process.communicate.return_value = (b"", b"")
    process.wait.return_value = 0
    create_subprocess_exec = mocker.patch(
        "asyncio.create_subprocess_exec", return_value=process
    )

    await SubprocessDagctlRunner().run(["stop", "seed"], tmp_path)

    assert create_subprocess_exec.call_args.kwargs["env"] == {
        "PATH": "/usr/bin",
        "HOME": "/Users/sandeep",
    }
