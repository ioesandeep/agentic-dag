import json
from pathlib import Path
from unittest.mock import ANY, call

import pytest
from pytest_mock import MockerFixture
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.infra.code.github_code_repo import GitHubCodeRepo

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path("/projects/spacy")
PR_URL = "https://github.com/acme/virgo/pull/412"


async def test_asks_from_the_project_root_when_finding_a_pull_request(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(
        returncode=0, stdout=json.dumps([{"number": 12}])
    )

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    await code_repo.find_pull_request(graph_node, "virgo/a")

    argv, cwd = command_runner.run.call_args.args
    assert cwd == PROJECT_ROOT
    assert "--repo" not in argv


async def test_lets_gh_resolve_the_repository_when_reading_review_artifacts(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout="[]")

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    await code_repo.get_review_artifacts(graph_node, 61)

    runner_calls = command_runner.run.call_args_list
    assert all(
        runner_call.args[0][-1].startswith("repos/{owner}/{repo}/")
        for runner_call in runner_calls
    )
    assert {runner_call.args[1] for runner_call in runner_calls} == {PROJECT_ROOT}


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [(json.dumps([{"number": 7}, {"number": 12}]), 12), ("[]", 0)],
    ids=["newest-of-several", "none-open"],
)
async def test_returns_the_newest_pull_request_when_the_branch_has_any(
    stdout: str, expected: int, mocker: MockerFixture
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout=stdout)

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    assert await code_repo.find_pull_request(graph_node, "virgo/a") == expected


async def test_returns_the_commit_count_when_the_head_sha_is_ahead_of_the_base_sha(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(
        returncode=0, stdout=json.dumps({"total_commits": 3})
    )

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    commit_count = await code_repo.count_commits_between(
        graph_node, "1a2b3c4d", "8bddf07a"
    )

    assert commit_count == 3
    argv = command_runner.run.call_args.args[0]
    assert argv[-1] == "repos/{owner}/{repo}/compare/1a2b3c4d...8bddf07a"


async def test_raises_when_gh_cannot_be_run(mocker: MockerFixture) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=1)

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    with pytest.raises(ObservationError, match="virgo/a"):
        await code_repo.find_pull_request(graph_node, "virgo/a")


async def test_raises_when_gh_returns_unreadable_json(mocker: MockerFixture) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout="not json")

    code_repo = GitHubCodeRepo(command_runner=command_runner)
    graph_node = GraphNode(id="A", project_root=PROJECT_ROOT)

    with pytest.raises(ObservationError, match="unreadable"):
        await code_repo.find_pull_request(graph_node, "virgo/a")


async def test_reads_pull_request_details_from_the_url_alone(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(
        returncode=0,
        stdout=json.dumps(
            {
                "number": 412,
                "url": PR_URL,
                "headRefName": "human/half-done",
                "headRepository": {"name": "virgo"},
                "headRepositoryOwner": {"login": "acme"},
                "title": "feat(auth): add the login page",
            }
        ),
    )

    code_repo = GitHubCodeRepo(command_runner=command_runner)

    details = await code_repo.get_pr_details_from_url(PR_URL)

    assert details.number == 412
    assert details.repository == "acme/virgo"
    assert details.head_branch == "human/half-done"
    assert details.title == "feat(auth): add the login page"
    assert command_runner.run.call_args == call(
        ("gh", "pr", "view", PR_URL, "--json", ANY)
    )


async def test_raises_when_the_pull_request_details_are_unusable(
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(
        returncode=0, stdout=json.dumps({"number": 412, "url": PR_URL})
    )

    code_repo = GitHubCodeRepo(command_runner=command_runner)

    with pytest.raises(ObservationError, match="no usable details"):
        await code_repo.get_pr_details_from_url(PR_URL)
