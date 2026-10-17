from subprocess import TimeoutExpired

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.infra.code.github_auth_status_client import (
    GithubAuthStatusClient,
)

pytestmark = pytest.mark.unit


async def test_status_returns_the_active_account_for_github_com(
    mocker: MockerFixture,
) -> None:
    stdout = (
        '{"hosts":{"github.example.com":[{"active":true,"login":"enterprise"}],'
        '"github.com":[{"active":false,"state":"error","login":"inactive"},'
        '{"active":true,"state":"success","login":"sandeep"}]}}'
    )
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout=stdout)
    github_auth_status_client = GithubAuthStatusClient(command_runner=command_runner)

    github_auth_status = await github_auth_status_client.status()

    assert github_auth_status.host == "github.com"
    assert github_auth_status.login == "sandeep"
    assert github_auth_status.authenticated is True
    command_runner.run.assert_called_once_with(
        ["gh", "auth", "status", "--hostname", "github.com", "--json", "hosts"]
    )


@pytest.mark.parametrize(
    "stdout",
    [
        '{"hosts":{}}',
        '{"hosts":{"github.com":[{"active":false,"state":"success","login":"inactive"}]}}',
        '{"hosts":{"github.com":[{"active":false,"state":"success","login":"inactive"},'
        '{"active":true,"state":"error","login":"sandeep","error":"private diagnostic"}]}}',
    ],
)
async def test_status_requires_authentication_when_no_active_account_is_valid(
    mocker: MockerFixture, stdout: str
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=0, stdout=stdout)
    github_auth_status_client = GithubAuthStatusClient(command_runner=command_runner)

    with pytest.raises(CatalogError, match="gh auth login") as raised_error:
        await github_auth_status_client.status()

    assert raised_error.value.code is CatalogErrorCodeEnum.GITHUB_AUTH_REQUIRED
    assert "private diagnostic" not in raised_error.value.detail


@pytest.mark.parametrize(
    ("command_failure", "expected_code"),
    [
        (
            FileNotFoundError("private diagnostic"),
            CatalogErrorCodeEnum.GITHUB_CLI_MISSING,
        ),
        (TimeoutExpired("gh", 30), CatalogErrorCodeEnum.GITHUB_UNAVAILABLE),
    ],
)
async def test_status_reports_command_failures_without_external_diagnostics(
    mocker: MockerFixture,
    command_failure: Exception,
    expected_code: CatalogErrorCodeEnum,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = command_failure
    github_auth_status_client = GithubAuthStatusClient(command_runner=command_runner)

    with pytest.raises(CatalogError, match="GitHub") as raised_error:
        await github_auth_status_client.status()

    assert raised_error.value.code is expected_code
    assert "private diagnostic" not in raised_error.value.detail


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [
        (1, "private diagnostic"),
        (0, "invalid json"),
        (0, '{"hosts": null}'),
        (0, '{"hosts":{"github.com":[{"active":true,"state":"timeout"}]}}'),
    ],
)
async def test_status_reports_unavailable_when_authentication_cannot_be_checked(
    mocker: MockerFixture, returncode: int, stdout: str
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.return_value = RunResult(returncode=returncode, stdout=stdout)
    github_auth_status_client = GithubAuthStatusClient(command_runner=command_runner)

    with pytest.raises(CatalogError, match="GitHub") as raised_error:
        await github_auth_status_client.status()

    assert raised_error.value.code is CatalogErrorCodeEnum.GITHUB_UNAVAILABLE
    assert "private diagnostic" not in raised_error.value.detail
