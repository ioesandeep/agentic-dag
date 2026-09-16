import io
import os
import signal
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.services.watching.watcher_service import WatcherService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 2, tzinfo=UTC)


@contextmanager
def bound_out() -> Iterator[io.StringIO]:
    out = io.StringIO()
    token = bind_context(ApplicationContext(AbortCommand(dag_name="demo"), out))
    try:
        yield out
    finally:
        unbind_context(token)


def is_dead(pid: int) -> bool:
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True

    return False


def wait_until_dead(pid: int) -> bool:
    deadline = time.monotonic() + 5
    while not is_dead(pid) and time.monotonic() < deadline:
        time.sleep(0.05)

    return is_dead(pid)


async def test_spawns_and_records_a_watcher_when_none_is_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        await watcher_service.watch("demo")

    watcher_repo.save.assert_awaited_once()
    assert watcher_repo.save.await_args.args[0].pid > 0
    assert (tmp_path / "demo" / "watch.log").exists()


async def test_spawns_nothing_when_the_recorded_watcher_still_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = Watcher(
        dag_name="demo", pid=os.getpid(), started_at=NOW
    )
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        await watcher_service.watch("demo")

    watcher_repo.save.assert_not_awaited()


async def test_respawns_when_the_recorded_watcher_is_dead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    finished = subprocess.Popen(["sleep", "0"], start_new_session=True)
    finished.wait(timeout=5)
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = Watcher(
        dag_name="demo", pid=finished.pid, started_at=NOW
    )
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        await watcher_service.watch("demo")

    watcher_repo.save.assert_awaited_once()


async def test_kills_and_forgets_the_watcher_when_stopped(
    mocker: MockerFixture,
) -> None:
    running = subprocess.Popen(["sleep", "30"], start_new_session=True)
    recorded = Watcher(dag_name="demo", pid=running.pid, started_at=NOW)
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = recorded
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        await watcher_service.stop("demo")

    assert wait_until_dead(running.pid)
    watcher_repo.delete.assert_awaited_once_with(recorded)


async def test_stays_quiet_when_no_watcher_was_recorded(mocker: MockerFixture) -> None:
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        await watcher_service.stop("demo")

    watcher_repo.delete.assert_not_awaited()


async def test_forget_removes_the_record_and_leaves_the_process_running(
    mocker: MockerFixture,
) -> None:
    running = subprocess.Popen(["sleep", "30"], start_new_session=True)
    recorded = Watcher(dag_name="demo", pid=running.pid, started_at=NOW)
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = recorded
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    with bound_out():
        watcher = await watcher_service.forget("demo")

    assert watcher is recorded
    watcher_repo.delete.assert_awaited_once_with(recorded)
    assert not is_dead(running.pid)
    os.killpg(running.pid, signal.SIGKILL)


async def test_kill_ends_the_process_without_needing_a_record(
    mocker: MockerFixture,
) -> None:
    running = subprocess.Popen(["sleep", "30"], start_new_session=True)
    watcher_repo = mocker.AsyncMock(spec=WatcherRepo)
    watcher_service = WatcherService(watcher_repo, Path("/bin/echo"))

    watcher_service.kill(Watcher(dag_name="demo", pid=running.pid, started_at=NOW))

    assert wait_until_dead(running.pid)
