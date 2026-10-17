import asyncio
import json
from subprocess import TimeoutExpired
from typing import cast

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.github_repository_identity import (
    GitHubRepositoryIdentity,
)
from virgo_agentic_dag.domain.catalog.github_repository_reference import (
    GitHubRepositoryReference,
)
from virgo_agentic_dag.domain.catalog.ports.github_repository_catalog_client import (
    GitHubRepositoryCatalogClient as GitHubRepositoryCatalogClientPort,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner


class GitHubRepositoryCatalogClient(GitHubRepositoryCatalogClientPort):
    """Resolve identities for explicitly requested GitHub repositories."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def get_repository_identity(
        self, github_repository_reference: GitHubRepositoryReference
    ) -> GitHubRepositoryIdentity:
        """Resolve the repository explicitly requested by the caller."""
        argv = [
            "env",
            "GH_PROMPT_DISABLED=1",
            "gh",
            "repo",
            "view",
            github_repository_reference.web_url,
            "--json",
            "id,nameWithOwner,url,defaultBranchRef,sshUrl",
        ]
        try:
            run_result = await asyncio.to_thread(self._command_runner.run, argv)
        except FileNotFoundError as error:
            raise self._get_error(CatalogErrorCodeEnum.GITHUB_CLI_MISSING) from error
        except (OSError, TimeoutExpired) as error:
            raise self._get_error(CatalogErrorCodeEnum.GITHUB_UNAVAILABLE) from error

        if run_result.returncode != 0:
            error_code = self._get_error_code(run_result)

            raise self._get_error(error_code)

        return self._parse_identity(run_result.stdout)

    def _parse_identity(self, stdout: str) -> GitHubRepositoryIdentity:
        try:
            payload = json.loads(stdout)
            provider_repository_id = self._get_string(payload, "id")
            full_name = self._get_string(payload, "nameWithOwner")
            web_url = self._get_string(payload, "url")
            ssh_url = self._get_string(payload, "sshUrl")
            default_branch_ref = payload["defaultBranchRef"]
            default_branch = None
            if default_branch_ref is not None:
                default_branch = self._get_string(default_branch_ref, "name")

        except (ValueError, KeyError, TypeError) as error:
            raise self._get_error(CatalogErrorCodeEnum.GITHUB_UNAVAILABLE) from error

        return GitHubRepositoryIdentity(
            provider_repository_id=provider_repository_id,
            full_name=full_name,
            web_url=web_url,
            ssh_url=ssh_url,
            default_branch=default_branch,
        )

    @staticmethod
    def _get_string(payload: object, key: str) -> str:
        is_object = isinstance(payload, dict)
        if not is_object:
            raise ValueError

        payload_object = cast(dict[str, object], payload)
        value = payload_object[key]
        is_string = isinstance(value, str)
        if not is_string or not value:
            raise ValueError

        return cast(str, value)

    @staticmethod
    def _get_error_code(run_result: RunResult) -> CatalogErrorCodeEnum:
        stderr = run_result.stderr.lower()
        if run_result.returncode == 127:
            return CatalogErrorCodeEnum.GITHUB_CLI_MISSING

        if (
            run_result.returncode == 4
            or "gh auth login" in stderr
            or "http 401" in stderr
        ):
            return CatalogErrorCodeEnum.GITHUB_AUTH_REQUIRED

        if "could not resolve to a repository" in stderr or "http 404" in stderr:
            return CatalogErrorCodeEnum.GITHUB_NOT_FOUND

        return CatalogErrorCodeEnum.GITHUB_UNAVAILABLE

    @staticmethod
    def _get_error(code: CatalogErrorCodeEnum) -> CatalogError:
        return CatalogError(code=code, detail="GitHub repository lookup failed.")
