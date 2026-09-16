import io
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.dagctl import main
from virgo_agentic_dag.api.cli.handlers.status_command_handler import (
    StatusCommandHandler,
)
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.status_command import StatusCommand
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.infra.streaming.stream_health import StreamHealth
from virgo_agentic_dag.domain.infra.streaming.stream_health_check import (
    StreamHealthCheck,
)
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 4, tzinfo=UTC)
DAG_PATH = "/runs/demo/dag.toml"
DAGCTL_ARGV = ["/venv/bin/dagctl", "start"]
SSE_URL = "http://127.0.0.1:8787/events"
HEALTH_URL = "http://127.0.0.1:8787/healthz"
JOB_LINE = "job\tfyi.virgo.dag.demo\tevery 300s\n"


@pytest.fixture
def build_node() -> Callable[[str, str], Node]:
    return lambda node_id, state: Node(
        id=node_id, state=state, created_at=NOW, updated_at=NOW
    )


@pytest.fixture
def build_open_session() -> Callable[[int], AgentSession]:
    return lambda pid: AgentSession(
        agent_id=f"agent-{pid}", started_at=NOW, triggered_by="launch", pid=pid
    )


@pytest.fixture
def build_job() -> Callable[..., ScheduledJob]:
    return lambda dag_path=None: ScheduledJob(
        dag_name="demo",
        label=ScheduledJob.get_label("demo"),
        argv=json.dumps(DAGCTL_ARGV + (["--dag", dag_path] if dag_path else [])),
        interval_seconds=300,
        working_directory="/runs/demo",
        log_path="/runs/demo/start.log",
        environment="{}",
        created_at=NOW,
    )


async def test_prints_every_record_when_the_run_is_live(
    mocker: MockerFixture,
    build_node: Callable[[str, str], Node],
    build_open_session: Callable[[int], AgentSession],
    build_job: Callable[..., ScheduledJob],
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [
        build_node("A", "in_progress"),
        build_node("B", "pending"),
    ]

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = [build_open_session(41)]

    watcher_repo = mocker.MagicMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = Watcher(
        dag_name="demo", pid=7, started_at=NOW
    )

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job()

    handler = StatusCommandHandler(
        node_repo=node_repo,
        agent_session_repo=agent_session_repo,
        watcher_repo=watcher_repo,
        scheduled_job_repo=scheduled_job_repo,
        dag_loader=mocker.MagicMock(spec=DagLoader),
        stream_health_check=mocker.MagicMock(spec=StreamHealthCheck),
    )

    out = io.StringIO()
    command = StatusCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == (
        "node\tA\tin_progress\n"
        "node\tB\tpending\n"
        "session\tagent-41\tpid 41\ttrigger launch\n"
        "watcher\tpid 7\n"
        "job\tfyi.virgo.dag.demo\tevery 300s\n"
    )


async def test_status_reports_the_bridge_answered_when_it_is_reachable(
    mocker: MockerFixture, build_job: Callable[..., ScheduledJob]
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = []

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = []

    watcher_repo = mocker.MagicMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(DAG_PATH)

    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(name="demo", nodes=(), sse_url=SSE_URL)

    stream_health_check = mocker.MagicMock(spec=StreamHealthCheck)
    stream_health_check.check.return_value = StreamHealth(url=HEALTH_URL, is_alive=True)

    handler = StatusCommandHandler(
        node_repo=node_repo,
        agent_session_repo=agent_session_repo,
        watcher_repo=watcher_repo,
        scheduled_job_repo=scheduled_job_repo,
        dag_loader=dag_loader,
        stream_health_check=stream_health_check,
    )

    out = io.StringIO()
    command = StatusCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == JOB_LINE + f"bridge\t{HEALTH_URL}\tanswered\n"
    stream_health_check.check.assert_awaited_once_with(SSE_URL)


async def test_status_reports_the_url_it_tried_when_the_bridge_refuses(
    mocker: MockerFixture, build_job: Callable[..., ScheduledJob]
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = []

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = []

    watcher_repo = mocker.MagicMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(DAG_PATH)

    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(name="demo", nodes=(), sse_url=SSE_URL)

    stream_health_check = mocker.MagicMock(spec=StreamHealthCheck)
    stream_health_check.check.return_value = StreamHealth(
        url=HEALTH_URL, is_alive=False
    )

    handler = StatusCommandHandler(
        node_repo=node_repo,
        agent_session_repo=agent_session_repo,
        watcher_repo=watcher_repo,
        scheduled_job_repo=scheduled_job_repo,
        dag_loader=dag_loader,
        stream_health_check=stream_health_check,
    )

    out = io.StringIO()
    command = StatusCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == JOB_LINE + f"bridge\t{HEALTH_URL}\tno answer\n"


async def test_status_says_nothing_about_the_bridge_when_no_sse_url_is_named(
    mocker: MockerFixture, build_job: Callable[..., ScheduledJob]
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = []

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = []

    watcher_repo = mocker.MagicMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = build_job(DAG_PATH)

    dag_loader = mocker.MagicMock(spec=DagLoader)
    dag_loader.load.return_value = DagSpec(name="demo", nodes=(), sse_url="")

    stream_health_check = mocker.MagicMock(spec=StreamHealthCheck)

    handler = StatusCommandHandler(
        node_repo=node_repo,
        agent_session_repo=agent_session_repo,
        watcher_repo=watcher_repo,
        scheduled_job_repo=scheduled_job_repo,
        dag_loader=dag_loader,
        stream_health_check=stream_health_check,
    )

    out = io.StringIO()
    command = StatusCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == JOB_LINE
    stream_health_check.check.assert_not_awaited()


async def test_says_nothing_is_recorded_when_the_run_is_empty(
    mocker: MockerFixture,
) -> None:
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = []

    agent_session_repo = mocker.MagicMock(spec=AgentSessionRepo)
    agent_session_repo.get_open_sessions.return_value = []

    watcher_repo = mocker.MagicMock(spec=WatcherRepo)
    watcher_repo.get_by_dag_name.return_value = None

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    handler = StatusCommandHandler(
        node_repo=node_repo,
        agent_session_repo=agent_session_repo,
        watcher_repo=watcher_repo,
        scheduled_job_repo=scheduled_job_repo,
        dag_loader=mocker.MagicMock(spec=DagLoader),
        stream_health_check=mocker.MagicMock(spec=StreamHealthCheck),
    )

    out = io.StringIO()
    command = StatusCommand(dag_name="demo")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    assert out.getvalue() == "demo has nothing recorded yet\n"


def test_refuses_when_no_run_lives_under_the_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    exit_code = main(["status", "ghost"])

    assert exit_code == 1
    assert "no dag named ghost lives on this host" in capsys.readouterr().err
    assert not (tmp_path / "ghost").exists()
