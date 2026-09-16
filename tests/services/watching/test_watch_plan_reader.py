import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader
from virgo_agentic_dag.services.watching.watch_plan_reader import WatchPlanReader

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 2, tzinfo=UTC)

DAG_TOML = """
name = "demo"
sse_url = "http://stream:8787/events"
project_root = "{project_root}"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "build the slice"
"""


def write_dag(tmp_path: Path) -> Path:
    dag_path = tmp_path / "dag.toml"
    dag_toml = DAG_TOML.format(project_root=tmp_path / "repo")
    dag_path.write_text(dag_toml, encoding="utf-8")

    return dag_path


def build_job(tmp_path: Path, dag_path: Path) -> ScheduledJob:
    return ScheduledJob(
        dag_name="demo",
        label=ScheduledJob.get_label("demo"),
        argv=json.dumps(["/venv/bin/dagctl", "start", "--dag", str(dag_path)]),
        interval_seconds=300,
        working_directory=str(tmp_path),
        log_path=str(tmp_path / "start.log"),
        environment="{}",
        created_at=NOW,
    )


def build_worktree(pr_number: int, name: str = "A") -> WorkTree:
    return WorkTree(
        id=pr_number,
        name=name,
        absolute_path=f"/ws/{name}",
        branch=name,
        pr_number=pr_number,
        created_at=NOW,
    )


def build_reader(
    scheduled_job_repo: AsyncMock, work_tree_repo: AsyncMock, code_repo: AsyncMock
) -> WatchPlanReader:
    return WatchPlanReader(
        scheduled_job_repo, work_tree_repo, code_repo, TomlDagLoader()
    )


async def test_resolves_the_plan_from_the_scheduled_job_and_the_dag_file(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dag_path = write_dag(tmp_path)
    scheduled_job_repo = mocker.AsyncMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(tmp_path, dag_path)
    work_tree_repo = mocker.AsyncMock(spec=WorkTreeRepo)
    code_repo = mocker.AsyncMock(spec=CodeRepo)
    code_repo.get_repo_slug.return_value = "acme/virgo"
    reader = build_reader(scheduled_job_repo, work_tree_repo, code_repo)

    plan = await reader.get_plan(WatchCommand(dag_name="demo"))

    assert plan.sse_url == "http://stream:8787/events"
    assert plan.argv[-2:] == ("--dag", str(dag_path))
    assert plan.working_directory == tmp_path
    assert plan.repo_slug == "acme/virgo"
    code_repo.get_repo_slug.assert_awaited_once_with(tmp_path / "repo")


async def test_prefers_the_stream_the_operator_named(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dag_path = write_dag(tmp_path)
    scheduled_job_repo = mocker.AsyncMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(tmp_path, dag_path)
    work_tree_repo = mocker.AsyncMock(spec=WorkTreeRepo)
    code_repo = mocker.AsyncMock(spec=CodeRepo)
    reader = build_reader(scheduled_job_repo, work_tree_repo, code_repo)

    plan = await reader.get_plan(
        WatchCommand(dag_name="demo", sse_url="http://elsewhere/events")
    )

    assert plan.sse_url == "http://elsewhere/events"


async def test_refuses_when_the_run_was_never_scheduled(mocker: MockerFixture) -> None:
    scheduled_job_repo = mocker.AsyncMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None
    work_tree_repo = mocker.AsyncMock(spec=WorkTreeRepo)
    code_repo = mocker.AsyncMock(spec=CodeRepo)
    reader = build_reader(scheduled_job_repo, work_tree_repo, code_repo)

    with pytest.raises(ConfigError, match="not scheduled"):
        await reader.get_plan(WatchCommand(dag_name="demo"))


async def test_refuses_when_no_stream_is_configured_anywhere(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dag_path = tmp_path / "dag.toml"
    dag_toml = DAG_TOML.format(project_root=tmp_path / "repo")
    dag_path.write_text(dag_toml.replace('sse_url = "http://stream:8787/events"\n', ""))
    scheduled_job_repo = mocker.AsyncMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(tmp_path, dag_path)
    work_tree_repo = mocker.AsyncMock(spec=WorkTreeRepo)
    code_repo = mocker.AsyncMock(spec=CodeRepo)
    reader = build_reader(scheduled_job_repo, work_tree_repo, code_repo)

    with pytest.raises(ConfigError, match="no event stream"):
        await reader.get_plan(WatchCommand(dag_name="demo"))


async def test_names_each_published_pull_request_once_in_order(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    dag_path = write_dag(tmp_path)
    scheduled_job_repo = mocker.AsyncMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(tmp_path, dag_path)
    work_tree_repo = mocker.AsyncMock(spec=WorkTreeRepo)
    work_tree_repo.get_published.return_value = [
        build_worktree(15),
        build_worktree(12),
        build_worktree(12, name="B"),
    ]
    code_repo = mocker.AsyncMock(spec=CodeRepo)
    code_repo.get_repo_slug.return_value = "acme/virgo"
    reader = build_reader(scheduled_job_repo, work_tree_repo, code_repo)
    plan = await reader.get_plan(WatchCommand(dag_name="demo"))

    topics = await reader.get_topics(plan)

    assert topics == ["acme/virgo#12", "acme/virgo#15"]
