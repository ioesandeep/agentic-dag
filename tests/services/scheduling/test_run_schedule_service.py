from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.exceptions.host.scheduling_error import SchedulingError
from virgo_agentic_dag.domain.infra.scheduling.scheduled_job import ScheduledJob
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import (  # noqa: F401
    SqliteDatabase,
)
from virgo_agentic_dag.services.scheduling.run_schedule_service import (
    RunScheduleService,
)
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)

pytestmark = pytest.mark.unit
NOW = datetime(2026, 8, 2, tzinfo=UTC)


@pytest.fixture
def create_job() -> Callable[..., ScheduledJob]:
    return lambda **changes: ScheduledJob(
        **{
            "dag_name": "demo",
            "label": "fyi.virgo.dag.demo",
            "argv": '["/venv/bin/dagctl", "start", "--dag", "/runs/demo/dag.toml"]',
            "environment": '{"PATH": "/usr/bin"}',
            "interval_seconds": 300,
            "working_directory": "/runs/demo",
            "log_path": "/runs/demo/start.log",
            "created_at": NOW,
            **changes,
        }
    )


@pytest.mark.parametrize("method", ["ensure_registered", "reconcile"])
@pytest.mark.parametrize(
    ("is_registered", "has_row"),
    [(False, False), (False, True), (True, False), (True, True)],
    ids=["missing-both", "missing-host-job", "missing-row", "unchanged"],
)
async def test_schedule_registers_only_when_required(
    method: str,
    is_registered: bool,
    has_row: bool,
    create_job: Callable[..., ScheduledJob],
    mocker: MockerFixture,
) -> None:
    scheduled_job = create_job()
    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.build.return_value = scheduled_job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = is_registered

    created_at = NOW - timedelta(days=1)
    stored_job = create_job(created_at=created_at) if has_row else None

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = stored_job

    run_schedule_service = RunScheduleService(
        scheduler=scheduler,
        scheduled_job_repo=scheduled_job_repo,
        scheduled_job_builder_factory=lambda: scheduled_job_builder,
    )

    register = getattr(run_schedule_service, method)
    dag_path = Path("/runs/demo/dag.toml")

    registered_job = await register(dag_path)

    should_register = not is_registered or (method == "reconcile" and not has_row)
    if should_register:
        assert registered_job is scheduled_job
        scheduler.register.assert_awaited_once_with(scheduled_job)
    else:
        assert registered_job is None
        scheduler.register.assert_not_awaited()

    if should_register or not has_row:
        scheduled_job_repo.save.assert_awaited_once_with(scheduled_job)
    else:
        scheduled_job_repo.save.assert_not_awaited()


@pytest.mark.parametrize(
    ("method", "attribute", "value"),
    [
        ("reconcile", "argv", '["/old/bin/dagctl", "start"]'),
        ("reconcile", "environment", '{"PATH": "/old/bin"}'),
        ("reconcile", "interval_seconds", 600),
        ("reconcile", "working_directory", "/old/demo"),
        ("reconcile", "log_path", "/old/demo/start.log"),
        ("ensure_registered", "environment", '{"PATH": "/old/bin"}'),
    ],
)
async def test_schedule_replaces_changed_jobs_only_when_reconciling(
    method: str,
    attribute: str,
    value: str | int,
    create_job: Callable[..., ScheduledJob],
    mocker: MockerFixture,
) -> None:
    scheduled_job = create_job()
    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.build.return_value = scheduled_job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = True

    stored_job = create_job(**{attribute: value})
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = stored_job

    run_schedule_service = RunScheduleService(
        scheduler=scheduler,
        scheduled_job_repo=scheduled_job_repo,
        scheduled_job_builder_factory=lambda: scheduled_job_builder,
    )

    register = getattr(run_schedule_service, method)
    dag_path = Path("/runs/demo/dag.toml")

    registered_job = await register(dag_path)

    if method == "reconcile":
        assert registered_job is scheduled_job
        scheduler.register.assert_awaited_once_with(scheduled_job)
        scheduled_job_repo.save.assert_awaited_once_with(scheduled_job)
    else:
        assert registered_job is None
        scheduler.register.assert_not_awaited()
        scheduled_job_repo.save.assert_not_awaited()


@pytest.mark.parametrize("method", ["ensure_registered", "reconcile"])
async def test_schedule_saves_nothing_when_host_registration_fails(
    method: str, create_job: Callable[..., ScheduledJob], mocker: MockerFixture
) -> None:
    scheduled_job = create_job()
    scheduled_job_builder = mocker.MagicMock(spec=ScheduledJobBuilder)
    scheduled_job_builder.build.return_value = scheduled_job

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = False
    scheduler.register.side_effect = SchedulingError("user manager unavailable")

    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)

    run_schedule_service = RunScheduleService(
        scheduler=scheduler,
        scheduled_job_repo=scheduled_job_repo,
        scheduled_job_builder_factory=lambda: scheduled_job_builder,
    )

    register = getattr(run_schedule_service, method)
    dag_path = Path("/runs/demo/dag.toml")

    with pytest.raises(SchedulingError, match="user manager unavailable"):
        await register(dag_path)

    scheduled_job_repo.save.assert_not_awaited()


@pytest.mark.parametrize("is_registered", [False, True])
async def test_retire_removes_the_host_job_when_the_row_is_missing(
    is_registered: bool, mocker: MockerFixture
) -> None:
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.return_value = None

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = is_registered

    run_schedule_service = RunScheduleService(
        scheduler=scheduler,
        scheduled_job_repo=scheduled_job_repo,
        scheduled_job_builder_factory=mocker.MagicMock(),
    )

    await run_schedule_service.retire("demo")

    scheduled_job_repo.delete.assert_not_awaited()
    if is_registered:
        retired_job = scheduler.retire.await_args.args[0]

        assert retired_job.label == "fyi.virgo.dag.demo"
    else:
        scheduler.retire.assert_not_awaited()


async def test_retire_retries_the_host_after_a_previous_retirement_fails(
    create_job: Callable[..., ScheduledJob], mocker: MockerFixture
) -> None:
    scheduled_job = create_job()
    scheduled_job_repo = mocker.MagicMock(spec=ScheduledJobRepo)
    scheduled_job_repo.get_by_dag_name.side_effect = [scheduled_job, None]

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.return_value = True
    scheduler.retire.side_effect = [SchedulingError("user manager unavailable"), None]

    call_order = mocker.MagicMock()
    call_order.attach_mock(scheduled_job_repo.delete, "delete_job")
    call_order.attach_mock(scheduler.retire, "retire_job")

    run_schedule_service = RunScheduleService(
        scheduler=scheduler,
        scheduled_job_repo=scheduled_job_repo,
        scheduled_job_builder_factory=mocker.MagicMock(),
    )

    with pytest.raises(SchedulingError, match="user manager unavailable"):
        await run_schedule_service.retire("demo")

    await run_schedule_service.retire("demo")

    retired_labels = [call.args[0].label for call in scheduler.retire.await_args_list]

    assert retired_labels == ["fyi.virgo.dag.demo", "fyi.virgo.dag.demo"]
    assert [name for name, _, _ in call_order.mock_calls] == [
        "delete_job",
        "retire_job",
        "retire_job",
    ]
