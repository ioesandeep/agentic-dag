import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

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


def test_runs_the_same_dagctl_that_started_it_when_building_the_job(
    tmp_path: Path,
) -> None:
    builder = build_builder()
    dag_path = tmp_path / "dag.toml"

    job = builder.build(dag_path, NOW)

    assert job.get_argv() == [
        str(EXECUTABLE),
        "start",
        "--dag",
        str(tmp_path / "dag.toml"),
    ]


def test_works_where_the_graph_lives_when_building_the_job(
    tmp_path: Path,
) -> None:
    builder = build_builder()
    dag_path = tmp_path / "dag.toml"

    job = builder.build(dag_path, NOW)

    assert job.get_working_directory() == tmp_path
    assert job.get_log_path() == tmp_path / "start.log"


def test_waits_as_long_as_the_configuration_asks_between_passes(tmp_path: Path) -> None:
    builder = build_builder(tick_interval_seconds=600)
    dag_path = tmp_path / "dag.toml"

    job = builder.build(dag_path, NOW)

    assert job.interval_seconds == 600
    assert job.label == "fyi.virgo.dag.demo"


@pytest.mark.parametrize(
    ("platform", "config_home"),
    [("darwin", "/custom"), ("linux", "/custom"), ("linux", "relative")],
)
def test_job_preserves_the_environment_for_the_host_scheduler(
    platform: str, config_home: str, tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(sys, "platform", platform)
    mocker.patch.dict(
        os.environ,
        {
            "HOME": str(tmp_path),
            "XDG_CONFIG_HOME": config_home,
            "PATH": "/usr/bin",
            "GH_TOKEN": "credential",
        },
    )

    builder = build_builder()
    dag_path = tmp_path / "dag.toml"

    job = builder.build(dag_path, NOW)

    expected_environment = {"PATH": "/usr/bin"}
    if platform == "linux":
        effective_config_home = (
            "/custom" if config_home == "/custom" else str(tmp_path / ".config")
        )

        expected_environment.update(
            HOME=str(tmp_path), XDG_CONFIG_HOME=effective_config_home
        )

    assert json.loads(job.environment) == expected_environment
