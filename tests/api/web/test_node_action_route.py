import os
import subprocess
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
from virgo_agentic_dag.api.web.controllers.health_controller import HealthController
from virgo_agentic_dag.api.web.controllers.node_action_controller import (
    NodeActionController,
)
from virgo_agentic_dag.api.web.routes.conversation_route import ConversationRoute
from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
from virgo_agentic_dag.api.web.routes.node_action_route import NodeActionRoute
from virgo_agentic_dag.api.web.routes.recovery_session_route import (
    RecoverySessionRoute,
)
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.api.web.service.node_action_service import NodeActionService
from virgo_agentic_dag.api.web.web_application_factory import WebApplicationFactory
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.persistence.entities.agent_session import AgentSession
from virgo_agentic_dag.domain.persistence.entities.node_agent import NodeAgent
from virgo_agentic_dag.domain.persistence.entities.work_tree import WorkTree
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.agent.claude_transcript_locator import (
    ClaudeTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.host.subprocess_dagctl_runner import (
    SubprocessDagctlRunner,
)
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_agent_repo import (
    SqliteNodeAgentRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.e2e

STARTED_AT = datetime(2026, 8, 15, 9, 0, tzinfo=UTC)
ENDED_AT = datetime(2026, 8, 15, 9, 58, tzinfo=UTC)
RETRY_PATH = "/api/dags/alpha/seed/retry"
WAKE_PATH = "/api/dags/alpha/seed/wake"
STOP_PATH = "/api/dags/alpha/seed/stop"


@pytest.fixture
def dag_home(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root",
        return_value=tmp_path,
    )
    mocker.patch(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", return_value=tmp_path
    )

    return tmp_path


@pytest.fixture
async def database(dag_home: Path) -> AsyncGenerator[SqliteDatabase]:
    run_home = dag_home / "alpha"
    run_home.mkdir()
    db_path = run_home / "db.sqlite3"
    run_home.joinpath("dag.toml").write_text(
        f"name = 'alpha'\nrepo_slug = 'acme/virgo'\ndb_path = '{db_path}'\n"
        "[[nodes]]\nid = 'seed'\n",
        encoding="utf-8",
    )
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    database = SqliteDatabase(engine)
    await database.upgrade_to_head()
    await SqliteNodeRepo(database).ensure_rows([GraphNode(id="seed")], STARTED_AT)

    yield database

    await database.dispose()


@pytest.fixture
def client(mocker: MockerFixture, dag_home: Path) -> TestClient:
    dag_web_service = DagWebService(
        DagService(TomlDagLoader()),
        DagDatabaseRegistry(),
        mocker.MagicMock(spec=CodeRepo),
        {ExecutorAgent.CLAUDE: ClaudeTranscriptLocator()},
        TranscriptPageReader(),
    )
    dag_controller = DagController(dag_web_service)
    node_action_service = NodeActionService(
        dag_web_service=dag_web_service,
        dagctl_runner=SubprocessDagctlRunner(),
        timeout=1,
    )
    application = WebApplicationFactory(
        dag_route=DagRoute(dag_controller),
        health_route=HealthRoute(HealthController()),
        memory_route=MemoryRoute(dag_controller),
        conversation_route=ConversationRoute(dag_controller),
        node_action_route=NodeActionRoute(NodeActionController(node_action_service)),
        recovery_session_route=RecoverySessionRoute(dag_controller),
    ).build()

    return TestClient(application)


@pytest.fixture
def sleeping_process() -> Generator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(["sleep", "60"], start_new_session=True)

    yield process

    process.kill()
    process.wait()


@pytest.mark.parametrize(
    ("reset", "session_id"),
    [(False, "token-seed"), (True, "")],
    ids=["resume", "reset"],
)
async def test_retry_responds_with_a_pending_node_and_retains_or_clears_the_session_id_when_the_node_needs_a_human(
    client: TestClient, database: SqliteDatabase, reset: bool, session_id: str
) -> None:
    await SqliteNodeRepo(database).update_state("seed", NodeState.NEEDS_HUMAN, ENDED_AT)
    node_agent = NodeAgent(
        id="agent-seed", name="claude", resume_token="token-seed", node_id="seed"
    )
    await SqliteNodeAgentRepo(database).save(node_agent)

    response = client.post(RETRY_PATH, json={"reset": reset})

    assert response.status_code == 200
    assert (response.json()["state"], response.json()["sessionId"]) == (
        "pending",
        session_id,
    )


async def test_retry_responds_409_with_dagctl_refusal_when_the_node_is_resting(
    client: TestClient, database: SqliteDatabase
) -> None:
    await SqliteNodeRepo(database).update_state("seed", NodeState.RESTING, ENDED_AT)

    response = client.post(RETRY_PATH, json={"reset": False})

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "seed is resting; retry takes only a node that errored or is waiting "
            "on a human"
        )
    }


async def test_retry_responds_404_when_the_dag_has_no_node_with_the_id(
    client: TestClient, database: SqliteDatabase
) -> None:
    response = client.post("/api/dags/alpha/ghost/retry", json={"reset": False})

    assert response.status_code == 404
    assert response.json() == {
        "detail": "no node named ghost is in dag alpha on this host"
    }


async def test_wake_responds_with_an_in_progress_node_and_its_recovery_when_the_node_is_resting(
    mocker: MockerFixture,
    tmp_path: Path,
    client: TestClient,
    database: SqliteDatabase,
) -> None:
    """Put a stub `claude` executable ahead of the real executable on `PATH` because waking the node starts `claude`."""
    await SqliteNodeRepo(database).update_state("seed", NodeState.RESTING, ENDED_AT)
    worktree_path = tmp_path / "ws" / "seed"
    worktree_path.mkdir(parents=True)
    worktree = WorkTree(
        name="alpha-seed",
        absolute_path=str(worktree_path),
        branch="feat/seed",
        created_at=STARTED_AT,
    )
    agent_session = AgentSession(
        started_at=STARTED_AT,
        ended_at=ENDED_AT,
        end_state="finished",
        triggered_by="launch",
        exit_code=0,
    )
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        worktree=worktree,
        sessions=[agent_session],
    )
    await SqliteNodeAgentRepo(database).save(node_agent)

    stub_directory = tmp_path / "bin"
    stub_directory.mkdir()
    claude_stub = stub_directory / "claude"
    claude_stub.write_text("#!/bin/sh\necho stub=claude\n", encoding="utf-8")
    claude_stub.chmod(0o755)
    mocker.patch.dict(
        os.environ, {"PATH": f"{stub_directory}{os.pathsep}{os.environ['PATH']}"}
    )

    response = client.post(
        WAKE_PATH,
        json={
            "cause": "usage_limit",
            "action": "woke the node after the usage limit reset",
            "message": "continue the task",
        },
    )

    assert response.status_code == 200
    node_response = response.json()
    assert node_response["state"] == "in_progress"
    assert (
        node_response["nodeRecovery"]["cause"],
        node_response["nodeRecovery"]["action"],
    ) == ("usage_limit", "woke the node after the usage limit reset")


async def test_wake_responds_409_without_running_dagctl_when_the_node_is_errored(
    mocker: MockerFixture, client: TestClient, database: SqliteDatabase
) -> None:
    await SqliteNodeRepo(database).update_state("seed", NodeState.ERRORED, ENDED_AT)

    dagctl_run = mocker.spy(SubprocessDagctlRunner, "run")

    response = client.post(
        WAKE_PATH,
        json={
            "cause": "usage_limit",
            "action": "woke the node after the usage limit reset",
            "message": "continue the task",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "wake requires node seed in dag alpha to be resting, not errored"
    }
    dagctl_run.assert_not_called()


async def test_stop_responds_with_the_node_in_needs_human_state_when_its_session_is_running(
    tmp_path: Path,
    client: TestClient,
    database: SqliteDatabase,
    sleeping_process: subprocess.Popen[bytes],
) -> None:
    await SqliteNodeRepo(database).update_state(
        "seed", NodeState.IN_PROGRESS, STARTED_AT
    )
    worktree = WorkTree(
        name="alpha-seed",
        absolute_path=str(tmp_path / "ws" / "seed"),
        branch="feat/seed",
        created_at=STARTED_AT,
    )
    agent_session = AgentSession(
        started_at=STARTED_AT, triggered_by="launch", pid=sleeping_process.pid
    )
    node_agent = NodeAgent(
        id="agent-seed",
        name="claude",
        resume_token="token-seed",
        node_id="seed",
        worktree=worktree,
        sessions=[agent_session],
    )
    await SqliteNodeAgentRepo(database).save(node_agent)

    response = client.post(STOP_PATH)

    assert response.status_code == 200
    assert response.json()["state"] == "needs_human"


async def test_retry_responds_409_when_another_command_has_the_run_lock_throughout_the_wait(
    dag_home: Path, client: TestClient, database: SqliteDatabase
) -> None:
    await SqliteNodeRepo(database).update_state("seed", NodeState.NEEDS_HUMAN, ENDED_AT)
    run_lock = DagRunLock(dag_home / "alpha" / "db.sqlite3")
    run_lock.acquire()

    response = client.post(RETRY_PATH, json={"reset": False})

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "dagctl cannot acquire the run lock for dag alpha before the 1-second "
            "timeout because another dagctl command, such as tick, retry, recover, "
            "or stop, retains the lock"
        )
    }
    run_lock.release()


@pytest.mark.parametrize(
    "run_result",
    [
        RunResult(returncode=2, stderr="dagctl: error: unrecognized arguments"),
        RunResult(returncode=1, stderr="the graph file will not load"),
    ],
    ids=["usage-error", "failure-without-refusal"],
)
async def test_stop_responds_500_when_dagctl_exits_with_code_2_or_code_1_without_stdout(
    mocker: MockerFixture,
    client: TestClient,
    database: SqliteDatabase,
    run_result: RunResult,
) -> None:
    await SqliteNodeRepo(database).update_state(
        "seed", NodeState.IN_PROGRESS, STARTED_AT
    )

    mocker.patch.object(SubprocessDagctlRunner, "run", return_value=run_result)

    response = client.post(STOP_PATH)

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            f"dagctl exits with code {run_result.returncode} for node seed in dag alpha"
        )
    }
