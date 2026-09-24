import asyncio
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
from virgo_agentic_dag.domain.command.abort_command import AbortCommand
from virgo_agentic_dag.domain.command.serve_command import ServeCommand
from virgo_agentic_dag.domain.command.tick_command import TickCommand
from virgo_agentic_dag.domain.events.node_event import NodeEvent
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.domain.infra.messaging.notification_subscriber import (
    NotificationSubscriber,
)
from virgo_agentic_dag.domain.notifications.notification_type import NotificationType
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.infra.code.github_code_repo import GitHubCodeRepo

pytestmark = pytest.mark.behavior

NOW = datetime(2026, 7, 31, tzinfo=UTC)
DELIVERY_SECONDS = 0.05

DAG_TOML = """
name = "demo"
db_path = "{db}"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "hold the run"
"""

HOMED_DAG_TOML = """
name = "demo"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "hold the run"
"""

CHECKED_OUT_DAG_TOML = """
name = "demo"
db_path = "{db}"
project_root = "{project_root}"
repo_slug = "{repo_slug}"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "hold the run"
"""


@pytest.fixture
def command(tmp_path: Path) -> TickCommand:
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(DAG_TOML.format(db=tmp_path / "db.sqlite3"), encoding="utf-8")

    return TickCommand(dag_path=dag_path)


@pytest.fixture
def event() -> NodeEvent:
    return WorkStartedEvent(
        node_id="A",
        type=NotificationType.WORK_STARTED,
        created_at=NOW,
        updated_at=NOW,
        title="Summarise a text",
        agent_name="Iris",
    )


async def test_delivers_scheduled_notifications_when_the_context_exits(
    mocker: MockerFixture, command: TickCommand, event: NodeEvent
) -> None:
    delivered = mocker.MagicMock()

    async def deliver_slowly(published: NodeEvent) -> None:
        """Outlast the shutdown path, so only a real drain sees the delivery through."""
        await asyncio.sleep(DELIVERY_SECONDS)

        delivered(published)

    subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    subscriber.get_event_type.return_value = NodeEvent
    subscriber.handle.side_effect = deliver_slowly

    async with initialize_context(command, io.StringIO()) as context:
        context.register(
            NotificationPublisher,
            lambda _: NotificationPublisher(notification_subscribers=[subscriber]),
        )
        context.get(NotificationPublisher).publish(event)

    delivered.assert_called_once_with(event)


async def test_delivers_scheduled_notifications_when_the_command_raises(
    mocker: MockerFixture, command: TickCommand, event: NodeEvent
) -> None:
    delivered = mocker.MagicMock()

    async def deliver_slowly(published: NodeEvent) -> None:
        """Outlast the shutdown path, so only a real drain sees the delivery through."""
        await asyncio.sleep(DELIVERY_SECONDS)

        delivered(published)

    subscriber = mocker.MagicMock(spec=NotificationSubscriber)
    subscriber.get_event_type.return_value = NodeEvent
    subscriber.handle.side_effect = deliver_slowly

    with pytest.raises(RuntimeError, match="boom"):
        async with initialize_context(command, io.StringIO()) as context:
            context.register(
                NotificationPublisher,
                lambda _: NotificationPublisher(notification_subscribers=[subscriber]),
            )
            context.get(NotificationPublisher).publish(event)

            raise RuntimeError("boom")

    delivered.assert_called_once_with(event)


async def test_refuses_a_second_pass_while_one_is_working_the_run(
    command: TickCommand,
) -> None:
    async with initialize_context(command, io.StringIO()):
        with pytest.raises(RunBusy, match="another pass"):
            async with initialize_context(command, io.StringIO()):
                pass


async def test_admits_an_abort_while_a_pass_is_working_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(HOMED_DAG_TOML, encoding="utf-8")
    tick = TickCommand(dag_path=dag_path)
    abort = AbortCommand(dag_name="demo")

    async with initialize_context(tick, io.StringIO()):
        async with initialize_context(abort, io.StringIO()) as context:
            assert context.command is abort


async def test_the_serve_command_opens_no_database_and_takes_no_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    async with initialize_context(ServeCommand(), io.StringIO()):
        pass

    assert list(tmp_path.iterdir()) == []


async def test_admits_a_pass_while_the_server_is_serving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(HOMED_DAG_TOML, encoding="utf-8")

    async with initialize_context(ServeCommand(), io.StringIO()):
        async with initialize_context(TickCommand(dag_path=dag_path), io.StringIO()):
            pass


async def test_frees_the_run_for_the_next_pass_when_the_context_exits(
    command: TickCommand,
) -> None:
    async with initialize_context(command, io.StringIO()):
        pass

    async with initialize_context(command, io.StringIO()) as context:
        assert context.command is command


async def test_initialize_context_sets_the_repository_slug_to_the_value_returned_by_github_code_repo_get_repo_slug_when_the_dag_specifies_an_empty_repository_slug(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(GitHubCodeRepo, "get_repo_slug", return_value="acme/virgo")
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(
        CHECKED_OUT_DAG_TOML.format(
            db=tmp_path / "db.sqlite3", project_root=tmp_path, repo_slug=""
        ),
        encoding="utf-8",
    )

    async with initialize_context(
        TickCommand(dag_path=dag_path), io.StringIO()
    ) as context:
        repo_slug = context.repo_slug

    assert repo_slug == "acme/virgo"


async def test_initialize_context_sets_the_repository_slug_from_the_dag_when_the_dag_specifies_a_repository_slug(
    tmp_path: Path,
) -> None:
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(
        CHECKED_OUT_DAG_TOML.format(
            db=tmp_path / "db.sqlite3", project_root=tmp_path, repo_slug="acme/fork"
        ),
        encoding="utf-8",
    )

    async with initialize_context(
        TickCommand(dag_path=dag_path), io.StringIO()
    ) as context:
        repo_slug = context.repo_slug

    assert repo_slug == "acme/fork"


async def test_initialize_context_keeps_the_repository_slug_empty_when_github_code_repo_get_repo_slug_raises_an_observation_error(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    mocker.patch.object(
        GitHubCodeRepo,
        "get_repo_slug",
        side_effect=ObservationError("gh repo view failed"),
    )
    dag_path = tmp_path / "dag.toml"
    dag_path.write_text(
        CHECKED_OUT_DAG_TOML.format(
            db=tmp_path / "db.sqlite3", project_root=tmp_path, repo_slug=""
        ),
        encoding="utf-8",
    )

    async with initialize_context(
        TickCommand(dag_path=dag_path), io.StringIO()
    ) as context:
        repo_slug = context.repo_slug

    assert repo_slug == ""
