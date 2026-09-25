import threading
import time
from pathlib import Path

import pytest
from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.domain.infra.locking.run_lock_config import RunLockConfig
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock

pytestmark = pytest.mark.unit


def build_lock(tmp_path: Path) -> DagRunLock:
    return DagRunLock(tmp_path / "demo" / "db.sqlite3")


def test_refuses_a_second_pass_while_the_first_holds_the_run(tmp_path: Path) -> None:
    first = build_lock(tmp_path)
    first.acquire()

    with pytest.raises(RunBusy, match="another pass"):
        build_lock(tmp_path).acquire()

    first.release()


def test_admits_the_next_pass_when_the_run_is_released(tmp_path: Path) -> None:
    first = build_lock(tmp_path)
    first.acquire()
    first.release()

    second = build_lock(tmp_path)
    second.acquire()

    second.release()


def test_locks_a_sidecar_beside_the_database_it_guards(tmp_path: Path) -> None:
    lock = build_lock(tmp_path)

    lock.acquire()

    assert (tmp_path / "demo" / "db.sqlite3.lock").exists()
    lock.release()


def test_makes_the_run_home_when_it_is_the_first_arrival(tmp_path: Path) -> None:
    lock = DagRunLock(tmp_path / "fresh" / "db.sqlite3")

    lock.acquire()

    assert (tmp_path / "fresh").is_dir()
    lock.release()


def test_stays_quiet_when_released_without_being_held(tmp_path: Path) -> None:
    build_lock(tmp_path).release()


def test_never_blocks_a_pass_working_a_different_dag(tmp_path: Path) -> None:
    first = DagRunLock(tmp_path / "one" / "db.sqlite3")
    second = DagRunLock(tmp_path / "two" / "db.sqlite3")
    first.acquire()

    second.acquire()

    first.release()
    second.release()


def test_claims_the_run_without_waiting_when_it_is_free(tmp_path: Path) -> None:
    lock = build_lock(tmp_path)

    lock.acquire_waiting()

    with pytest.raises(RunBusy, match="another pass"):
        build_lock(tmp_path).acquire()

    lock.release()


def test_waits_out_the_holder_and_then_claims_the_run(tmp_path: Path) -> None:
    holder = build_lock(tmp_path)
    holder.acquire()
    release_delay = threading.Timer(0.2, holder.release)
    release_delay.start()
    started = time.monotonic()

    waiter = build_lock(tmp_path)
    waiter.acquire_waiting()

    assert time.monotonic() - started >= 0.15
    waiter.release()


@pytest.mark.parametrize("timeout", [None, 5], ids=["no_timeout", "within_the_timeout"])
def test_acquires_the_run_lock_when_the_current_holder_releases_it(
    tmp_path: Path, timeout: float | None
) -> None:
    holder = build_lock(tmp_path)
    holder.acquire()
    release_delay = threading.Timer(0.2, holder.release)
    release_delay.start()
    run_lock_config = RunLockConfig(timeout=timeout)

    waiter = build_lock(tmp_path)
    waiter.acquire_lock(run_lock_config)

    with pytest.raises(RunBusy, match="another pass"):
        build_lock(tmp_path).acquire()

    waiter.release()
