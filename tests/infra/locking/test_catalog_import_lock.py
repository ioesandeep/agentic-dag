import os
import signal
import subprocess
import sys
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

import pytest

from virgo_agentic_dag.config.catalog_settings import CatalogSettings
from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.infra.locking.catalog_import_lock import CatalogImportLock

pytestmark = pytest.mark.integration


@pytest.fixture
def create_lock_command() -> Callable[[Path, str, str], list[str]]:
    script = (
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from virgo_agentic_dag.config.catalog_settings import CatalogSettings\n"
        "from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError\n"
        "from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import CatalogErrorCodeEnum\n"
        "from virgo_agentic_dag.infra.locking.catalog_import_lock import CatalogImportLock\n"
        "catalog_root = Path(sys.argv[1])\n"
        "catalog_settings = CatalogSettings(root=catalog_root)\n"
        "catalog_import_lock = CatalogImportLock(catalog_settings=catalog_settings)\n"
    )

    return lambda root, repository_id, action: [
        sys.executable,
        "-c",
        script + action,
        str(root),
        repository_id,
    ]


@pytest.mark.parametrize(
    ("repository_id", "exit_code"),
    [
        ("B83C1E50-637D-4BC7-9F35-330088EE2783", 7),
        ("040abf2c-f9b6-467c-afdd-cb3d49d1f1b0", 0),
    ],
    ids=["same-repository", "different-repository"],
)
def test_import_lock_excludes_only_the_same_repository(
    tmp_path: Path,
    create_lock_command: Callable[[Path, str, str], list[str]],
    repository_id: str,
    exit_code: int,
) -> None:
    catalog_settings = CatalogSettings(root=tmp_path)
    catalog_import_lock = CatalogImportLock(catalog_settings=catalog_settings)
    command = create_lock_command(
        tmp_path,
        repository_id,
        "try:\n"
        "    with catalog_import_lock.acquire(sys.argv[2]):\n"
        "        pass\n"
        "except CatalogError as error:\n"
        "    assert error.code is CatalogErrorCodeEnum.IMPORT_ACTIVE\n"
        "    sys.exit(7)\n",
    )

    with catalog_import_lock.acquire("b83c1e50-637d-4bc7-9f35-330088ee2783"):
        completed_process = subprocess.run(command, capture_output=True, timeout=5)

    assert completed_process.returncode == exit_code


@pytest.mark.parametrize("worker_exit", ["os._exit(0)", "pass"])
def test_clone_retains_import_lock_when_worker_exits(
    tmp_path: Path,
    create_lock_command: Callable[[Path, str, str], list[str]],
    worker_exit: str,
) -> None:
    repository_id = "b83c1e50-637d-4bc7-9f35-330088ee2783"
    catalog_settings = CatalogSettings(root=tmp_path)
    catalog_import_lock = CatalogImportLock(catalog_settings=catalog_settings)
    worker_command = create_lock_command(
        tmp_path,
        repository_id,
        "with catalog_import_lock.acquire(sys.argv[2]) as lock_descriptor:\n"
        "    clone_code = 'import sys\\nsys.stdin.buffer.read(1)'\n"
        "    clone_command = [sys.executable, '-c', clone_code]\n"
        "    subprocess.Popen(clone_command, stdin=sys.stdin, pass_fds=(lock_descriptor,))\n"
        f"    {worker_exit}\n",
    )
    contender_command = create_lock_command(
        tmp_path,
        repository_id,
        "with catalog_import_lock.acquire(sys.argv[2]):\n    pass\n",
    )

    worker = subprocess.Popen(
        worker_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        worker_exit_code = worker.wait(timeout=5)
        assert worker_exit_code == 0
        with pytest.raises(CatalogError, match="already owns") as catalog_error:
            with catalog_import_lock.acquire(repository_id):
                pytest.fail("The clone must prevent a competing import.")

        assert catalog_error.value.code is CatalogErrorCodeEnum.IMPORT_ACTIVE
        assert catalog_error.value.existing_repository_id == repository_id
    finally:
        try:
            worker.communicate(input=b"exit", timeout=5)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                os.killpg(worker.pid, signal.SIGKILL)

            worker.communicate(timeout=5)

            raise

    completed_process = subprocess.run(
        contender_command, capture_output=True, timeout=5
    )

    assert completed_process.returncode == 0, completed_process.stderr


def test_import_lock_preserves_the_lock_file_after_context_failure(
    tmp_path: Path,
) -> None:
    repository_id = "b83c1e50-637d-4bc7-9f35-330088ee2783"
    catalog_settings = CatalogSettings(root=tmp_path)
    catalog_import_lock = CatalogImportLock(catalog_settings=catalog_settings)
    lock_path = catalog_settings.locks_path / f"{repository_id}.lock"
    with catalog_import_lock.acquire(repository_id):
        lock_inode = lock_path.stat().st_ino

    with pytest.raises(RuntimeError, match="import fails"):
        with catalog_import_lock.acquire(repository_id):
            raise RuntimeError("import fails")

    with catalog_import_lock.acquire(repository_id):
        assert lock_path.stat().st_ino == lock_inode


@pytest.mark.parametrize("failure", ["invalid-id", "catalog-file"])
def test_import_lock_reports_catalog_errors_before_creating_lock_files(
    tmp_path: Path, failure: str
) -> None:
    catalog_root = tmp_path / "catalog"
    repository_id = "../outside"
    expected_code = CatalogErrorCodeEnum.INVALID_INPUT
    if failure == "catalog-file":
        catalog_root.touch()
        repository_id = "b83c1e50-637d-4bc7-9f35-330088ee2783"
        expected_code = CatalogErrorCodeEnum.IMPORT_FAILED

    catalog_settings = CatalogSettings(root=catalog_root)
    catalog_import_lock = CatalogImportLock(catalog_settings=catalog_settings)

    with pytest.raises(CatalogError, match="UUIDs|cannot be acquired") as catalog_error:
        with catalog_import_lock.acquire(repository_id):
            pytest.fail("Invalid catalog storage must prevent acquisition.")

    lock_path_iterator = tmp_path.glob("**/*.lock")
    lock_paths = list(lock_path_iterator)

    assert catalog_error.value.code is expected_code
    assert lock_paths == []
