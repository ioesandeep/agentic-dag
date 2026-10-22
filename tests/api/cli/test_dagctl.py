from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.api.cli.dagctl import main
from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory

pytestmark = pytest.mark.behavior


def test_start_exits_one_with_a_single_error_line_when_scheduling_fails(
    tmp_path: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(
        f'name = "demo"\ndb_path = "{tmp_path / "db.sqlite3"}"\n'
        'executor_agent = "claude"\n[[nodes]]\nid = "A"\nbrief = "Run a task."\n',
        encoding="utf-8",
    )

    scheduling_error = SchedulingError("user manager unavailable")
    mocker.patch.object(SchedulerFactory, "get_scheduler", side_effect=scheduling_error)
    dag_path_argument = str(dag_path)

    exit_code = main(["start", "--dag", dag_path_argument])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.err == "user manager unavailable\n"
