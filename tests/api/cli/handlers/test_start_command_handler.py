import io
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.start_command_handler import StartCommandHandler
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.command_handler import CommandHandler
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.start_command import StartCommand
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.infra.notification.bot_notification_dispatcher import (
    BotNotificationDispatcher,
)
from virgo_agentic_dag.infra.notification.slack_notification_composer import (
    SlackNotificationComposer,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)
from virgo_agentic_dag.services.watching.watcher_service import WatcherService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 8, 2, tzinfo=UTC)
SSE_URL = "http://stream/events"


@pytest.fixture
def job() -> ScheduledJob:
    return ScheduledJob(
        dag_name="demo",
        label=ScheduledJob.get_label("demo"),
        argv=json.dumps(["/venv/bin/dagctl", "start"]),
        interval_seconds=300,
        working_directory="/runs/demo",
        log_path="/runs/demo/start.log",
        environment="{}",
        created_at=NOW,
    )


@pytest.fixture
def watcher() -> Watcher:
    return Watcher(dag_name="demo", pid=4242, started_at=NOW)


@pytest.fixture
def build_node() -> Callable[[str, str, datetime], Node]:
    return lambda node_id, state, created_at: Node(
        id=node_id, state=state, created_at=created_at, updated_at=created_at
    )


async def test_leaves_the_host_waking_the_run_when_a_first_pass_succeeds(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=mocker.MagicMock(spec=WatcherService),
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.SUCCESS
    scheduler.register.assert_awaited_once_with(job)
    scheduled_job_repo.save.assert_awaited_once_with(job)
    assert out.getvalue().endswith("\n")


async def test_registers_nothing_when_the_host_already_wakes_the_run(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = True
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=mocker.MagicMock(spec=WatcherService),
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=notification_publisher,
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    scheduler.register.assert_not_awaited()
    scheduled_job_repo.save.assert_not_awaited()
    notification_publisher.publish.assert_not_called()


async def test_schedules_nothing_when_the_first_pass_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.FAILURE

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=mocker.MagicMock(spec=ScheduledJobBuilder),
        watcher_service=mocker.MagicMock(spec=WatcherService),
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.FAILURE
    scheduler.register.assert_not_awaited()
    scheduled_job_repo.save.assert_not_awaited()


async def test_stops_waking_the_run_when_it_has_settled(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.RUN_COMPLETE
    scheduler.retire.assert_awaited_once_with(job)
    scheduled_job_repo.delete.assert_awaited_once_with(job)


async def test_settles_quietly_when_no_host_was_waking_the_run(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.RUN_COMPLETE
    scheduler.retire.assert_not_awaited()


async def test_starts_the_watcher_when_a_stream_is_configured(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    watcher_service = mocker.MagicMock(spec=WatcherService)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=mocker.MagicMock(spec=ScheduledJobRepo),
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=(), sse_url=SSE_URL),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    watcher_service.watch.assert_awaited_once_with("demo")


async def test_starts_no_watcher_when_no_stream_is_configured(
    mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    watcher_service = mocker.MagicMock(spec=WatcherService)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=mocker.MagicMock(spec=ScheduledJobRepo),
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=(), sse_url=""),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    watcher_service.watch.assert_not_awaited()


async def test_stops_the_watcher_when_the_run_completes(
    mocker: MockerFixture, watcher: Watcher, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = watcher

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=mocker.MagicMock(spec=SchedulerFactory),
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=(), sse_url=SSE_URL),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    watcher_service.forget.assert_awaited_once_with("demo")
    watcher_service.kill.assert_called_once_with(watcher)
    watcher_service.watch.assert_not_awaited()


async def test_concludes_in_the_order_that_survives_self_fatal_kills(
    mocker: MockerFixture, job: ScheduledJob, watcher: Watcher, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = watcher

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    call_order = mocker.MagicMock()
    call_order.attach_mock(notification_publisher.publish, "publish")
    call_order.attach_mock(notification_publisher.drain, "drain")
    call_order.attach_mock(watcher_service.forget, "forget_watcher")
    call_order.attach_mock(scheduled_job_repo.delete, "delete_job")
    call_order.attach_mock(scheduler.retire, "retire_job")
    call_order.attach_mock(watcher_service.kill, "kill_watcher")

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=scheduled_job_repo,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=notification_publisher,
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    assert [name for name, _, _ in call_order.mock_calls] == [
        "publish",
        "drain",
        "forget_watcher",
        "delete_job",
        "retire_job",
        "kill_watcher",
    ]


async def test_posts_the_dag_started_message_when_the_host_job_is_registered(
    mocker: MockerFixture,
    job: ScheduledJob,
    build_node: Callable[[str, str, datetime], Node],
    tmp_path: Path,
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [
        build_node("A", NodeState.IN_PROGRESS.value, NOW),
        build_node("B", NodeState.PENDING.value, NOW),
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        scheduled_job_repo=mocker.MagicMock(spec=ScheduledJobRepo),
        node_repo=node_repo,
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=mocker.MagicMock(spec=WatcherService),
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=notification_publisher,
    )

    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    mocker.patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-token"})
    dispatcher = BotNotificationDispatcher(
        poster=poster,
        slack_notification_repo=mocker.AsyncMock(spec=SlackNotificationRepo),
        channel="#dag",
        composer=SlackNotificationComposer(),
        dag_name="demo",
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    dag_started_event = notification_publisher.publish.call_args.args[0]
    await dispatcher.dispatch(dag_started_event)

    posted_text = poster.post.call_args.args[1]["text"]
    assert posted_text == "*demo* started — 2 nodes, 1 in progress"


async def test_posts_the_dag_completed_message_when_the_run_completes(
    mocker: MockerFixture,
    build_node: Callable[[str, str, datetime], Node],
    tmp_path: Path,
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    clock = mocker.patch(
        "virgo_agentic_dag.api.cli.handlers.start_command_handler.datetime"
    )
    clock.now.return_value = NOW

    started_at = NOW.replace(tzinfo=None) - timedelta(hours=2)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [
        build_node("A", NodeState.MERGED.value, started_at),
        build_node("B", NodeState.MERGED.value, started_at + timedelta(hours=1)),
        build_node("C", NodeState.SKIPPED.value, started_at + timedelta(hours=1)),
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=mocker.MagicMock(spec=SchedulerFactory),
        scheduled_job_repo=scheduled_job_repo,
        node_repo=node_repo,
        scheduled_job_builder=scheduled_job_builder,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=notification_publisher,
    )

    poster = mocker.MagicMock(spec=JsonPoster)
    poster.post.return_value = {"ok": True, "ts": "1700.1"}
    mocker.patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-token"})
    dispatcher = BotNotificationDispatcher(
        poster=poster,
        slack_notification_repo=mocker.AsyncMock(spec=SlackNotificationRepo),
        channel="#dag",
        composer=SlackNotificationComposer(),
        dag_name="demo",
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")
    context = ApplicationContext(command, out)
    token = bind_context(context)
    try:
        await handler.handle(command)
    finally:
        unbind_context(token)

    dag_completed_event = notification_publisher.publish.call_args.args[0]
    await dispatcher.dispatch(dag_completed_event)

    payload = poster.post.call_args.args[1]
    assert payload["text"] == "*demo* complete in 2h 0m — 2 merged, 1 skipped"
    assert "thread_ts" not in payload
