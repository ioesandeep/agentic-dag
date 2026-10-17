import asyncio
import signal
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.infra.locking.catalog_import_lock import CatalogImportLock
from virgo_agentic_dag.infra.workspace.github_clone_process import GithubCloneProcess

pytestmark = pytest.mark.integration


async def test_clone_uses_the_explicit_fork_without_interactive_prompts(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    create_process = asyncio.create_subprocess_exec
    start_process = mocker.patch(
        "asyncio.create_subprocess_exec", new_callable=mocker.MagicMock
    )
    start_process.side_effect = lambda *arguments, **config: create_process(
        sys.executable, "-c", "pass", **config
    )
    staging_path = tmp_path / "staging"
    clone_process = GithubCloneProcess()
    lock_path = tmp_path / "import.lock"

    with lock_path.open("a+b") as lock_file:
        lock_descriptor = lock_file.fileno()
        clone_handle = await clone_process.start(
            "sandeep/fork", staging_path, lock_descriptor
        )
        run_result = await clone_handle.wait()

    arguments, config = start_process.call_args
    assert arguments[:5] == ("gh", "repo", "clone", "--no-upstream", "sandeep/fork")
    assert arguments[5] == str(staging_path)
    assert config["pass_fds"] == (lock_descriptor,)
    assert config["start_new_session"] is True
    assert config["env"]["GH_PROMPT_DISABLED"] == "1"
    assert config["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert config["stdin"] == asyncio.subprocess.DEVNULL
    assert run_result.returncode == clone_handle.poll() == 0


@pytest.mark.parametrize(
    "stop_method", ["terminate", "timeout", "cancel", "cancel-wait"]
)
async def test_clone_stops_descendants_before_releasing_the_import_lock(
    tmp_path: Path, mocker: MockerFixture, stop_method: str
) -> None:
    repository_id = "b83c1e50-637d-4bc7-9f35-330088ee2783"
    catalog_settings = CatalogSettings(root=tmp_path)
    import_lock = CatalogImportLock(catalog_settings=catalog_settings)
    lock_path = catalog_settings.locks_path / f"{repository_id}.lock"
    staging_path = tmp_path / "staging"
    clone_process = GithubCloneProcess()
    create_process = asyncio.create_subprocess_exec
    with import_lock.acquire(repository_id) as lock_descriptor:
        script = (
            "import os, signal, time\n"
            "if os.fork() == 0:\n"
            "    signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            f"    os.write({lock_descriptor}, b'ready')\n"
            "time.sleep(60)\n"
        )
        start_process = mocker.patch(
            "asyncio.create_subprocess_exec", new_callable=mocker.MagicMock
        )
        start_process.side_effect = lambda *arguments, **config: create_process(
            sys.executable, "-c", script, **config
        )
        clone_handle = await clone_process.start(
            "sandeep/fork", staging_path, lock_descriptor
        )

    try:
        async with asyncio.timeout(5):
            content = lock_path.read_bytes()
            while not content:
                await asyncio.sleep(0.01)
                content = lock_path.read_bytes()

        with pytest.raises(CatalogError, match="already owns"):
            with import_lock.acquire(repository_id):
                pytest.fail("The clone must retain its inherited import lock.")

        if stop_method == "timeout":
            with pytest.raises(CatalogError, match="timeout") as catalog_error:
                await clone_handle.wait(timeout_seconds=0.01)

            assert catalog_error.value.code is CatalogErrorCodeEnum.IMPORT_TIMEOUT
        elif stop_method == "terminate":
            await clone_handle.terminate()
        else:
            if stop_method == "cancel-wait":
                operation = clone_handle.wait()
            else:
                operation = clone_handle.terminate()

            operation_task = asyncio.create_task(operation)
            await asyncio.sleep(0)
            operation_task.cancel()
            if stop_method == "cancel-wait":
                await asyncio.sleep(0)
                operation_task.cancel()

            with pytest.raises(asyncio.CancelledError, match="^$"):
                await operation_task

        with import_lock.acquire(repository_id):
            assert clone_handle.poll() == -signal.SIGTERM
    finally:
        await clone_handle.terminate()


async def test_clone_bounds_and_sanitizes_failure_output(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    create_process = asyncio.create_subprocess_exec
    script = (
        "import sys\n"
        "print('denied https://sandeep:credential@github.com/sandeep/fork')\n"
        "print('ghp_privatecredential Authorization: Bearer privatecredential')\n"
        "print('\\x1b[31m' + 'x' * 100000)\n"
        "sys.exit(3)\n"
    )
    start_process = mocker.patch(
        "asyncio.create_subprocess_exec", new_callable=mocker.MagicMock
    )
    start_process.side_effect = lambda *arguments, **config: create_process(
        sys.executable, "-c", script, **config
    )
    clone_process = GithubCloneProcess()
    lock_path = tmp_path / "import.lock"
    staging_path = tmp_path / "staging"

    with lock_path.open("a+b") as lock_file:
        lock_descriptor = lock_file.fileno()
        clone_handle = await clone_process.start(
            "sandeep/fork", staging_path, lock_descriptor
        )
        run_result = await clone_handle.wait()

    assert run_result.returncode == 3
    assert len(run_result.stderr) <= 4096
    assert "denied" in run_result.stderr
    assert "credential" not in run_result.stderr
    assert "\x1b" not in run_result.stderr


async def test_clone_reaps_the_process_when_start_is_cancelled(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    creation = asyncio.Future()
    process = mocker.MagicMock(spec=asyncio.subprocess.Process, pid=123456)
    process.stdout = mocker.MagicMock(spec=asyncio.StreamReader)
    process.stdout.read.return_value = b""
    process.wait.return_value = -signal.SIGTERM
    start_process = mocker.patch(
        "asyncio.create_subprocess_exec", new_callable=mocker.MagicMock
    )
    start_process.return_value = creation
    mocker.patch("os.killpg")
    clone_process = GithubCloneProcess()

    operation = clone_process.start("sandeep/fork", tmp_path, 7)
    operation_task = asyncio.create_task(operation)
    await asyncio.sleep(0)
    operation_task.cancel()
    creation.set_result(process)
    with pytest.raises(asyncio.CancelledError, match="^$"):
        await operation_task

    process.wait.assert_awaited_once()
