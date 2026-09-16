import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from virgo_agentic_dag.domain.command.start_command import StartCommand
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.node_spec import NodeSpec
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 2, tzinfo=UTC)
EXECUTABLE = Path("/venv/bin/dagctl")


def build_builder(tick_interval_seconds: int = 300) -> ScheduledJobBuilder:
    spec = DagSpec(
        name="demo",
        nodes=(NodeSpec(id="A"),),
        tick_interval_seconds=tick_interval_seconds,
    )

    return ScheduledJobBuilder(spec, EXECUTABLE)


def build_command(tmp_path: Path) -> StartCommand:
    return StartCommand(dag_path=tmp_path / "dag.toml")


def test_runs_the_same_dagctl_that_started_it_when_building_the_job(
    tmp_path: Path,
) -> None:
    job = build_builder().build(build_command(tmp_path), NOW)

    assert job.get_argv() == [
        str(EXECUTABLE),
        "start",
        "--dag",
        str(tmp_path / "dag.toml"),
    ]


def test_works_where_the_graph_lives_when_building_the_job(
    tmp_path: Path,
) -> None:
    job = build_builder().build(build_command(tmp_path), NOW)

    assert job.get_working_directory() == tmp_path
    assert job.get_log_path() == tmp_path / "start.log"


def test_waits_as_long_as_the_configuration_asks_between_passes(tmp_path: Path) -> None:
    job = build_builder(tick_interval_seconds=600).build(build_command(tmp_path), NOW)

    assert job.interval_seconds == 600
    assert job.label == "fyi.virgo.dag.demo"


def test_carries_the_path_it_was_started_with_when_building_the_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "/opt/homebrew/bin:/usr/bin")

    job = build_builder().build(build_command(tmp_path), NOW)

    assert json.loads(job.environment) == {"PATH": "/opt/homebrew/bin:/usr/bin"}
