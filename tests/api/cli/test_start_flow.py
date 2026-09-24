import contextlib
import io
import json
import os
import sqlite3
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.api.cli.handlers.start_command_handler import StartCommandHandler
from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.start_command import StartCommand
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.scheduling.scheduler import Scheduler
from virgo_agentic_dag.domain.observation.pull_request_snapshot import (
    PullRequestSnapshot,
)
from virgo_agentic_dag.domain.observation.pull_request_state import PullRequestState
from virgo_agentic_dag.domain.review.review_artifact import ReviewArtifact
from virgo_agentic_dag.domain.review.review_artifact_type import ReviewArtifactType
from virgo_agentic_dag.infra.agent.claude_agent_launcher import ClaudeAgentLauncher
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory

pytestmark = [pytest.mark.e2e, pytest.mark.slow]

CHANNEL_VARIABLE = "SLACK_E2E_CHANNEL"
TOKEN_VARIABLE = "SLACK_BOT_TOKEN"
SLACK_API_URL = "https://slack.com/api"
PULL_REQUEST_URL = "https://git.example.com/SK-Giri-Corp/virgo/pull"
PASS_COUNT = 8
READ_TIMEOUT_SECONDS = 30
READ_INTERVAL_SECONDS = 0.5

DAG_TOML = """
name = "{name}"
db_path = "{db}"
project_root = "{project_root}"
workspace_path = "{workspace}"
base_branch = "develop"
repo_slug = "SK-Giri-Corp/virgo"
slack_channel = "{channel}"

[[nodes]]
id = "A"
name = "Vesta"
title = "Change the greeting"
executor_agent = "claude"
brief = "change the greeting"

[[nodes]]
id = "B"
name = "Juno"
title = "Translate the greeting"
executor_agent = "claude"
brief = "translate the greeting"
depends_on = ["A"]
"""

AGENT_SCRIPT = '#!/bin/sh\ngit checkout -q -B "work-$(basename "$PWD")"\n'

A_LINK = f"<{PULL_REQUEST_URL}/42|pr#42>"
B_LINK = f"<{PULL_REQUEST_URL}/43|pr#43>"
A_THREAD = [
    f"Agent *Vesta* started working on `Change the greeting`\n<{PULL_REQUEST_URL}/42>",
    f"1 comment was added to {A_LINK}. Addressing them now",
    f"*skgiricorp* merged {A_LINK}. Agent *Vesta* will wind down. Thank you!",
]
B_THREAD = [
    f"Agent *Juno* started working on `Translate the greeting`\n<{PULL_REQUEST_URL}/43>",
    f"1 comment was added to {B_LINK}. Addressing them now",
    f"Agent *Juno* pushed 2 commits to {B_LINK}",
    f"*skgiricorp* merged {B_LINK}. Agent *Juno* will wind down. Thank you!",
]
EXPECTED_THREADS = {"A": A_THREAD, "B": B_THREAD}
AUDIT_NOTES_WITHOUT_A_MESSAGE = {"Vesta resumed work", "its session finished on #42"}


def list_slack_message_texts(
    method: str, query: dict[str, str], token: str, expected_texts: list[str]
) -> list[str]:
    """Returns Slack message texts when all expected texts are present or the
    deadline passes."""
    url = f"{SLACK_API_URL}/{method}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    deadline = time.monotonic() + READ_TIMEOUT_SECONDS
    while True:
        with urllib.request.urlopen(request) as response:
            payload = json.loads(response.read())

        texts = [
            message["blocks"][0]["text"]["text"] for message in payload["messages"]
        ]
        is_complete = all(text in texts for text in expected_texts)
        if is_complete or time.monotonic() > deadline:
            return texts

        time.sleep(READ_INTERVAL_SECONDS)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    repository = tmp_path / "repo"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repository, check=True)
    (repository / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repository, check=True)

    return repository


@pytest.fixture
def build_snapshot() -> Callable[
    [PullRequestState, str, str, str], PullRequestSnapshot
]:
    return lambda state, head_sha, title, url: PullRequestSnapshot(
        state=state,
        head_sha=head_sha,
        base_branch="develop",
        merged_by="skgiricorp",
        title=title,
        url=url,
    )


async def test_start_posts_messages_to_the_channel_when_the_pull_requests_for_two_nodes_change_from_open_to_merged(
    tmp_path: Path,
    project_root: Path,
    build_snapshot: Callable[[PullRequestState, str, str, str], PullRequestSnapshot],
    mocker: MockerFixture,
) -> None:
    channel = os.environ[CHANNEL_VARIABLE]
    token = os.environ[TOKEN_VARIABLE]
    dag_name = f"slack-e2e-{uuid.uuid4().hex[:8]}"
    dag_messages = [
        f"*{dag_name}* started — 2 nodes, 1 in progress",
        f"*{dag_name}* complete in 0m — 2 merged",
    ]
    dag_path = tmp_path / "dag.toml"
    db_path = tmp_path / "db.sqlite3"
    dag_path.write_text(
        DAG_TOML.format(
            name=dag_name,
            db=db_path,
            project_root=project_root,
            workspace=tmp_path / "ws",
            channel=channel,
        ),
        encoding="utf-8",
    )
    start_command = StartCommand(dag_path=dag_path)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    agent_stub = bin_dir / ClaudeAgentLauncher._BINARY
    agent_stub.write_text(AGENT_SCRIPT, encoding="utf-8")
    agent_stub.chmod(0o755)
    mocker.patch.dict(
        os.environ, {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    )

    a_url = f"{PULL_REQUEST_URL}/42"
    b_url = f"{PULL_REQUEST_URL}/43"
    open_a = build_snapshot(PullRequestState.OPEN, "a1", "Change the greeting", a_url)
    merged_a = build_snapshot(
        PullRequestState.MERGED, "a1", "Change the greeting", a_url
    )
    open_b = build_snapshot(
        PullRequestState.OPEN, "b1", "Translate the greeting", b_url
    )
    pushed_b = build_snapshot(
        PullRequestState.OPEN, "b2", "Translate the greeting", b_url
    )
    merged_b = build_snapshot(
        PullRequestState.MERGED, "b2", "Translate the greeting", b_url
    )
    # TODO: drop the extra open reading between each settle and the observation after it, and the per-node review artifact iterators, once NotificationPublisher delivers a node's events in publish order.
    pull_request_snapshots = {
        "A": iter([open_a, open_a, open_a, open_a, merged_a]),
        "B": iter([open_b, open_b, open_b, pushed_b, pushed_b, merged_b]),
    }
    pull_request_numbers = {"A": 42, "B": 43}
    review_comment = ReviewArtifact(
        kind=ReviewArtifactType.ISSUE_COMMENT,
        artifact_id=1,
        author="skgiricorp",
        body="Please rename the variable",
        created_at="2026-09-14T10:00:00Z",
    )

    code_repo = mocker.MagicMock(spec=CodeRepo)
    code_repo.find_pull_request.side_effect = lambda graph_node, branch: (
        pull_request_numbers[graph_node.id]
    )
    code_repo.get_pull_request.side_effect = lambda graph_node, number: next(
        pull_request_snapshots[graph_node.id]
    )
    review_artifacts = {
        "A": iter([[], [review_comment]]),
        "B": iter([[], [review_comment], [review_comment]]),
    }
    code_repo.get_review_artifacts.side_effect = lambda graph_node, number: next(
        review_artifacts[graph_node.id]
    )
    code_repo.count_commits_between.return_value = 2

    scheduler = mocker.MagicMock(spec=Scheduler)
    scheduler.is_registered.side_effect = lambda job: scheduler.register.called
    scheduler_factory = mocker.MagicMock(spec=SchedulerFactory)
    scheduler_factory.get_scheduler.return_value = scheduler

    exit_codes: list[ExitCode] = []
    for _ in range(PASS_COUNT):
        async with initialize_context(start_command, io.StringIO()) as context:
            context.register(CodeRepo, lambda _context: code_repo)
            context.register(SchedulerFactory, lambda _context: scheduler_factory)
            exit_code = await context.get(StartCommandHandler).handle(start_command)

        exit_codes.append(exit_code)
        with contextlib.suppress(ChildProcessError):
            while True:
                os.wait()

    assert exit_codes == [*[ExitCode.SUCCESS] * (PASS_COUNT - 1), ExitCode.RUN_COMPLETE]

    with sqlite3.connect(db_path) as connection:
        thread_ids = dict(
            connection.execute("select node_id, thread_id from slack_notifications")
        )
        audit_notes = [
            note
            for (note,) in connection.execute(
                "select note from audit_entries where node_id = 'A'"
            )
        ]

    history_texts = list_slack_message_texts(
        "conversations.history",
        {"channel": channel, "limit": "50"},
        token,
        dag_messages,
    )
    dag_texts = [
        text for text in reversed(history_texts) if text.startswith(f"*{dag_name}*")
    ]
    assert dag_texts == dag_messages

    threads = {
        node_id: list_slack_message_texts(
            "conversations.replies",
            {"channel": channel, "ts": thread_id},
            token,
            EXPECTED_THREADS[node_id],
        )
        for node_id, thread_id in thread_ids.items()
    }
    assert threads == EXPECTED_THREADS

    assert AUDIT_NOTES_WITHOUT_A_MESSAGE <= set(audit_notes)
