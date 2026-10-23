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
from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.infra.messaging.json_poster import JsonPoster
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.node import Node
from virgo_agentic_dag.domain.persistence.entities.watcher import Watcher
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
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
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)
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


async def test_start_reconciles_the_host_job_after_a_successful_pass(
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

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.reconcile.return_value = job

    call_order = mocker.MagicMock()
    call_order.attach_mock(scheduler.is_registered, "lookup")
    call_order.attach_mock(tick_command_handler.handle, "tick")
    call_order.attach_mock(run_schedule_service.reconcile, "reconcile")

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
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
    assert call_order.mock_calls == [
        mocker.call.lookup(job),
        mocker.call.tick(command),
        mocker.call.reconcile(command.dag_path),
    ]

    assert out.getvalue().endswith("\n")


@pytest.mark.parametrize("failed_operation", ["is_registered", "reconcile"])
async def test_start_propagates_scheduling_errors(
    failed_operation: str, mocker: MockerFixture, job: ScheduledJob, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.SUCCESS

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.build.return_value = job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False

    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    failed_method = scheduler.is_registered
    if failed_operation == "reconcile":
        failed_method = run_schedule_service.reconcile

    failed_method.side_effect = SchedulingError("user manager unavailable")

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
        watcher_service=mocker.MagicMock(spec=WatcherService),
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    command = StartCommand(dag_path=tmp_path / "dag.toml")

    with pytest.raises(SchedulingError, match="user manager unavailable"):
        await handler.handle(command)

    if failed_operation == "is_registered":
        tick_command_handler.handle.assert_not_awaited()


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

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.reconcile.return_value = None

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
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
    notification_publisher.publish.assert_not_called()


async def test_schedules_nothing_when_the_first_pass_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.FAILURE

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=mocker.MagicMock(spec=ScheduledJobBuilder),
        run_schedule_service=run_schedule_service,
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
    run_schedule_service.reconcile.assert_not_awaited()
    scheduler.register.assert_not_awaited()


async def test_start_retires_the_schedule_when_the_run_completes(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
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
    run_schedule_service.retire.assert_awaited_once_with("demo")


async def test_start_retries_retirement_when_a_previous_conclusion_fails(
    mocker: MockerFixture, tmp_path: Path
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    run_schedule_service.retire.side_effect = [
        SchedulingError("user manager unavailable"),
        None,
    ]

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=mocker.MagicMock(spec=NotificationPublisher),
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")

    context = ApplicationContext(command, out)
    token = bind_context(context)

    try:
        with pytest.raises(SchedulingError, match="user manager unavailable"):
            await handler.handle(command)

        exit_code = await handler.handle(command)
    finally:
        unbind_context(token)

    assert exit_code is ExitCode.RUN_COMPLETE
    assert run_schedule_service.retire.await_args_list == [
        mocker.call("demo"),
        mocker.call("demo"),
    ]


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
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
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
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
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

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = watcher

    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = mocker.MagicMock(spec=Scheduler)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
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


@pytest.mark.parametrize(
    ("is_watcher_process_group", "shutdown_calls"),
    [
        (False, ["kill_watcher", "retire_job"]),
        (True, ["retire_job", "kill_watcher"]),
    ],
    ids=["launchd-pass", "watcher-pass"],
)
async def test_conclude_completes_cleanup_before_terminating_the_current_pass(
    is_watcher_process_group: bool,
    shutdown_calls: list[str],
    mocker: MockerFixture,
    watcher: Watcher,
    tmp_path: Path,
) -> None:
    current_process_group = watcher.pid if is_watcher_process_group else watcher.pid + 1
    mocker.patch("os.getpgrp", return_value=current_process_group)

    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = watcher

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    run_schedule_service = mocker.MagicMock(spec=RunScheduleService)
    if is_watcher_process_group:
        watcher_service.kill.side_effect = SystemExit("pass terminated")
    else:
        run_schedule_service.retire.side_effect = SystemExit("pass terminated")

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    call_order = mocker.MagicMock()
    call_order.attach_mock(notification_publisher.publish, "publish")
    call_order.attach_mock(notification_publisher.drain, "drain")

    call_order.attach_mock(watcher_service.forget, "forget_watcher")
    call_order.attach_mock(run_schedule_service.retire, "retire_job")
    call_order.attach_mock(watcher_service.kill, "kill_watcher")

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=mocker.MagicMock(spec=NodeRepo),
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=run_schedule_service,
        watcher_service=watcher_service,
        dag_spec=DagSpec(name="demo", nodes=()),
        notification_publisher=notification_publisher,
    )

    out = io.StringIO()
    command = StartCommand(dag_path=tmp_path / "dag.toml")

    context = ApplicationContext(command, out)
    token = bind_context(context)

    try:
        with pytest.raises(SystemExit, match="pass terminated"):
            await handler.handle(command)
    finally:
        unbind_context(token)

    assert [name for name, _, _ in call_order.mock_calls] == [
        "publish",
        "drain",
        "forget_watcher",
        *shutdown_calls,
    ]

    watcher_service.kill.assert_called_once_with(watcher)
    run_schedule_service.retire.assert_awaited_once_with("demo")


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
        node_repo=node_repo,
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
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


@pytest.mark.parametrize(
    ("states", "expected_message"),
    [
        (
            [NodeState.MERGED, NodeState.MERGED, NodeState.SKIPPED],
            "*demo* complete in 2h 0m — 2 merged, 1 skipped",
        ),
        (
            [NodeState.NEEDS_HUMAN, NodeState.ERRORED, NodeState.SKIPPED],
            "*demo* errored after 2h 0m — 1 needs human, 1 errored, 1 skipped",
        ),
        (
            [NodeState.SKIPPED] * 3,
            "*demo* complete in 2h 0m — 3 skipped",
        ),
    ],
    ids=["complete", "errored", "all-skipped"],
)
async def test_start_posts_the_run_status_when_the_run_finishes(
    states: list[NodeState],
    expected_message: str,
    mocker: MockerFixture,
    build_node: Callable[[str, str, datetime], Node],
    tmp_path: Path,
) -> None:
    tick_command_handler = mocker.MagicMock(spec=CommandHandler)
    tick_command_handler.handle.return_value = ExitCode.RUN_COMPLETE

    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.get_dag_name.return_value = "demo"

    watcher_service = mocker.MagicMock(spec=WatcherService)
    watcher_service.forget.return_value = None

    clock = mocker.patch(
        "virgo_agentic_dag.api.cli.handlers.start_command_handler.datetime"
    )

    clock.now.return_value = NOW

    started_at = NOW.replace(tzinfo=None) - timedelta(hours=2)
    node_repo = mocker.MagicMock(spec=NodeRepo)
    node_repo.get_all.return_value = [
        build_node("A", states[0].value, started_at),
        build_node("B", states[1].value, started_at + timedelta(hours=1)),
        build_node("C", states[2].value, started_at + timedelta(hours=1)),
    ]

    notification_publisher = mocker.MagicMock(spec=NotificationPublisher)

    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = mocker.MagicMock(spec=Scheduler)

    handler = StartCommandHandler(
        tick_command_handler=tick_command_handler,
        scheduler_factory=scheduler_factory,
        node_repo=node_repo,
        scheduled_job_builder=scheduled_job_builder,
        run_schedule_service=mocker.MagicMock(spec=RunScheduleService),
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

    assert payload["text"] == expected_message
    assert "thread_ts" not in payload
