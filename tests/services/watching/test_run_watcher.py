import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.application_context import (
    ApplicationContext,
    bind_context,
    unbind_context,
)
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.watch_command import WatchCommand
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.domain.infra.host.sleeper import Sleeper
from virgo_agentic_dag.services.watching.event_reader import EventReader
from virgo_agentic_dag.services.watching.run_watcher import RunWatcher
from virgo_agentic_dag.services.watching.subscription_factory import SubscriptionFactory
from virgo_agentic_dag.services.watching.watch_plan import WatchPlan
from virgo_agentic_dag.services.watching.watch_plan_reader import WatchPlanReader

pytestmark = pytest.mark.unit

PLAN = WatchPlan(
    sse_url="http://stream/events",
    argv=("dagctl", "start", "--dag", "/runs/demo/dag.toml"),
    working_directory=Path("/runs/demo"),
    repo_slug="acme/virgo",
    refresh_seconds=300,
)


def build_watcher(
    plan_reader: AsyncMock,
    subscription_factory: MagicMock,
    command_runner: MagicMock,
    sleeper: MagicMock,
) -> RunWatcher:
    return RunWatcher(
        plan_reader,
        subscription_factory,
        command_runner,
        sleeper,
        debounce_seconds=0.01,
    )


async def run_watch(watcher: RunWatcher) -> ExitCode:
    command = WatchCommand(dag_name="demo")
    token = bind_context(ApplicationContext(command, io.StringIO()))
    try:
        return await watcher.watch(command)
    finally:
        unbind_context(token)


async def test_fires_one_pass_when_a_burst_of_events_settles(
    mocker: MockerFixture,
) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.return_value = ["acme/virgo#12"]
    reader = mocker.MagicMock(spec=EventReader)
    reader.get_event.side_effect = ["pull_request", "pull_request", None]
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    subscription_factory.build.return_value = reader
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=int(ExitCode.RUN_COMPLETE))
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    exit_code = await run_watch(watcher)

    assert exit_code is ExitCode.RUN_COMPLETE
    command_runner.run.assert_called_once_with(PLAN.argv, PLAN.working_directory)
    subscription_factory.build.assert_called_once_with(PLAN.sse_url, ["acme/virgo#12"])
    reader.stop.assert_called_once_with()


async def test_never_fires_for_unsupported_events(mocker: MockerFixture) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.return_value = ["acme/virgo#12"]
    quiet = mocker.MagicMock(spec=EventReader)
    quiet.get_event.side_effect = ["star", None]
    active = mocker.MagicMock(spec=EventReader)
    active.get_event.side_effect = ["pull_request", None]
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    subscription_factory.build.side_effect = [quiet, active]
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=int(ExitCode.RUN_COMPLETE))
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    await run_watch(watcher)

    assert command_runner.run.call_count == 1
    assert subscription_factory.build.call_count == 2


async def test_waits_for_a_pull_request_when_the_run_has_none_yet(
    mocker: MockerFixture,
) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.side_effect = [[], ["acme/virgo#12"]]
    plan_reader.is_scheduled.return_value = True
    reader = mocker.MagicMock(spec=EventReader)
    reader.get_event.side_effect = ["pull_request", None]
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    subscription_factory.build.return_value = reader
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=int(ExitCode.RUN_COMPLETE))
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    await run_watch(watcher)

    sleeper.sleep.assert_called_once()
    subscription_factory.build.assert_called_once_with(PLAN.sse_url, ["acme/virgo#12"])


async def test_resubscribes_when_a_pass_leaves_the_run_running(
    mocker: MockerFixture,
) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.side_effect = [
        ["acme/virgo#12"],
        ["acme/virgo#12", "acme/virgo#13"],
    ]
    first = mocker.MagicMock(spec=EventReader)
    first.get_event.side_effect = ["pull_request", None]
    second = mocker.MagicMock(spec=EventReader)
    second.get_event.side_effect = ["pull_request", None]
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    subscription_factory.build.side_effect = [first, second]
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [
        RunResult(returncode=int(ExitCode.SUCCESS)),
        RunResult(returncode=int(ExitCode.RUN_COMPLETE)),
    ]
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    exit_code = await run_watch(watcher)

    assert exit_code is ExitCode.RUN_COMPLETE
    assert command_runner.run.call_count == 2
    assert subscription_factory.build.call_args_list[1].args[1] == [
        "acme/virgo#12",
        "acme/virgo#13",
    ]


async def test_refreshes_its_topics_when_the_stream_stays_quiet(
    mocker: MockerFixture,
) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.return_value = ["acme/virgo#12"]
    quiet = mocker.MagicMock(spec=EventReader)
    quiet.get_event.side_effect = [None]
    active = mocker.MagicMock(spec=EventReader)
    active.get_event.side_effect = ["pull_request", None]
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    subscription_factory.build.side_effect = [quiet, active]
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=int(ExitCode.RUN_COMPLETE))
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    await run_watch(watcher)

    assert subscription_factory.build.call_count == 2
    assert command_runner.run.call_count == 1


async def test_ends_the_watch_when_the_run_is_no_longer_scheduled(
    mocker: MockerFixture,
) -> None:
    plan_reader = mocker.AsyncMock(spec=WatchPlanReader)
    plan_reader.get_plan.return_value = PLAN
    plan_reader.get_topics.return_value = []
    plan_reader.is_scheduled.return_value = False
    subscription_factory = mocker.MagicMock(spec=SubscriptionFactory)
    command_runner = mocker.MagicMock(spec=CommandRunner)
    sleeper = mocker.MagicMock(spec=Sleeper)
    watcher = build_watcher(plan_reader, subscription_factory, command_runner, sleeper)

    exit_code = await run_watch(watcher)

    assert exit_code is ExitCode.RUN_COMPLETE
    subscription_factory.build.assert_not_called()
    sleeper.sleep.assert_not_called()
