import json
from subprocess import TimeoutExpired

import pytest
from pytest_mock import MockerFixture

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.github_repository_reference import (
    GitHubRepositoryReference,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner
from virgo_agentic_dag.infra.code.github_repository_catalog_client import (
    GitHubRepositoryCatalogClient,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "reference",
    [
        " Acme/Fork ",
        "https://github.com/Acme/Fork.git/",
        "git@github.com:Acme/Fork.git",
        "ssh://git@github.com/Acme/Fork.git",
    ],
)
def test_reference_normalizes_supported_github_references(reference: str) -> None:
    github_repository_reference = GitHubRepositoryReference(reference)

    assert github_repository_reference.full_name == "acme/fork"
    assert github_repository_reference.web_url == "https://github.com/acme/fork"


@pytest.mark.parametrize(
    "reference",
    [
        "https://user:credential@github.com/acme/fork",
        "git@gitlab.com:acme/fork.git",
        "https://github.com/acme/fork/tree/main",
        "acme/",
        "/fork",
        "acme/..",
    ],
)
def test_reference_rejects_unsupported_references_without_exposing_input(
    reference: str,
) -> None:
    with pytest.raises(CatalogError, match="supported GitHub") as captured_error:
        GitHubRepositoryReference(reference)

    assert captured_error.value.code is CatalogErrorCodeEnum.UNSUPPORTED_REMOTE
    assert captured_error.value.field == "reference"
    assert reference not in str(captured_error.value)


@pytest.mark.parametrize(
    ("full_name", "default_branch"), [("Acme/Fork", "main"), ("NewOwner/Renamed", None)]
)
async def test_client_returns_explicit_fork_identity_and_current_metadata(
    full_name: str,
    default_branch: str | None,
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    payload = {
        "id": "R_fork",
        "nameWithOwner": full_name,
        "url": f"https://github.com/{full_name}",
        "sshUrl": f"git@github.com:{full_name}.git",
        "defaultBranchRef": {"name": default_branch} if default_branch else None,
    }
    stdout = json.dumps(payload)
    command_runner.run.return_value = RunResult(returncode=0, stdout=stdout)
    client = GitHubRepositoryCatalogClient(command_runner=command_runner)
    reference = GitHubRepositoryReference("acme/fork")

    expected_argv = [
        "env",
        "GH_PROMPT_DISABLED=1",
        "gh",
        "repo",
        "view",
        "https://github.com/acme/fork",
        "--json",
        "id,nameWithOwner,url,defaultBranchRef,sshUrl",
    ]

    identity = await client.get_repository_identity(reference)

    assert identity.provider_repository_id == "R_fork"
    assert identity.full_name == full_name
    assert identity.default_branch == default_branch
    command_runner.run.assert_called_once_with(expected_argv)


@pytest.mark.parametrize(
    ("command_response", "code"),
    [
        (FileNotFoundError("credential"), CatalogErrorCodeEnum.GITHUB_CLI_MISSING),
        (TimeoutExpired("credential", 30), CatalogErrorCodeEnum.GITHUB_UNAVAILABLE),
        (
            RunResult(returncode=4, stderr="GH_TOKEN=credential"),
            CatalogErrorCodeEnum.GITHUB_AUTH_REQUIRED,
        ),
        (
            RunResult(returncode=1, stderr="HTTP 404: credential"),
            CatalogErrorCodeEnum.GITHUB_NOT_FOUND,
        ),
        (
            RunResult(returncode=1, stderr="network: credential"),
            CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
        ),
        (
            RunResult(returncode=0, stdout="GH_TOKEN=credential"),
            CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
        ),
    ],
)
async def test_client_translates_external_failures_without_exposing_command_values(
    command_response: RunResult | Exception,
    code: CatalogErrorCodeEnum,
    mocker: MockerFixture,
) -> None:
    command_runner = mocker.MagicMock(spec=CommandRunner)
    command_runner.run.side_effect = [command_response]
    client = GitHubRepositoryCatalogClient(command_runner=command_runner)
    reference = GitHubRepositoryReference("acme/fork")

    with pytest.raises(CatalogError, match="lookup failed") as captured_error:
        await client.get_repository_identity(reference)

    assert captured_error.value.code is code
    assert "credential" not in repr(captured_error.value)
    assert "GH_TOKEN" not in repr(captured_error.value)
