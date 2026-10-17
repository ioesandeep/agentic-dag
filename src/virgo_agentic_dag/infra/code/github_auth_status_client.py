import asyncio
import json
from subprocess import TimeoutExpired
from typing import Any

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.github_auth_status import GithubAuthStatus
from virgo_agentic_dag.domain.catalog.ports.github_auth_status_client import (
    GithubAuthStatusClient as GithubAuthStatusClientPort,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.command_runner import CommandRunner


class GithubAuthStatusClient(GithubAuthStatusClientPort):
    """Check the active GitHub CLI account for catalog operations."""

    def __init__(self, command_runner: CommandRunner) -> None:
        self._command_runner = command_runner

    async def status(self) -> GithubAuthStatus:
        """Check authentication for catalog operations."""
        run_result = await self._run()
        active_account = self._get_active_account(run_result.stdout)

        return self._get_status(active_account)

    async def _run(self) -> RunResult:
        argv = ["gh", "auth", "status", "--hostname", "github.com", "--json", "hosts"]
        try:
            run_result = await asyncio.to_thread(self._command_runner.run, argv)
        except FileNotFoundError as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_CLI_MISSING,
                detail="Install GitHub CLI and run gh auth login --hostname github.com.",
            ) from error
        except (OSError, TimeoutExpired) as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
                detail="GitHub authentication could not be checked. Retry later.",
            ) from error

        if run_result.returncode != 0:
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
                detail="Run gh auth status --hostname github.com to check GitHub CLI.",
            )

        return run_result

    def _get_active_account(self, stdout: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(stdout)
            accounts: list[dict[str, Any]] = payload["hosts"].get("github.com", [])
            for account in accounts:
                is_active = account["active"]
                if is_active is True:
                    return account

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
                detail="GitHub CLI returned invalid authentication status. Update GitHub CLI.",
            ) from error

        return None

    def _get_status(self, active_account: dict[str, Any] | None) -> GithubAuthStatus:
        state = active_account.get("state") if active_account is not None else None
        if active_account is None or state == "error":
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_AUTH_REQUIRED,
                detail="Run gh auth login --hostname github.com or gh auth switch --hostname github.com.",
            )

        login = active_account.get("login")
        has_login = isinstance(login, str) and bool(login)
        if state != "success" or not has_login:
            raise CatalogError(
                code=CatalogErrorCodeEnum.GITHUB_UNAVAILABLE,
                detail="GitHub authentication could not be checked. Retry later.",
            )

        return GithubAuthStatus(
            host="github.com", authenticated=True, login=login, guidance=None
        )
