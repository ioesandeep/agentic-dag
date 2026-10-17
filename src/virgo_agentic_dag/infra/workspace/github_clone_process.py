import asyncio
import os
from pathlib import Path

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)
from virgo_agentic_dag.domain.catalog.ports.github_clone_handle import GithubCloneHandle
from virgo_agentic_dag.domain.catalog.ports.github_clone_process import (
    GithubCloneProcess as GithubCloneProcessPort,
)
from virgo_agentic_dag.infra.workspace.subprocess_clone_handle import (
    SubprocessCloneHandle,
)


class GithubCloneProcess(GithubCloneProcessPort):
    """Start GitHub clones with independent process ownership."""

    async def start(
        self, reference: str, staging_path: Path, lock_descriptor: int
    ) -> GithubCloneHandle:
        """Start the requested repository clone without credential prompts."""
        creation = self._create_handle(reference, staging_path, lock_descriptor)
        creation_task = asyncio.create_task(creation)
        is_cancelled = False
        is_complete = creation_task.done()
        while not is_complete:
            completion = asyncio.shield(creation_task)
            try:
                await completion
            except asyncio.CancelledError:
                is_cancelled = True

            is_complete = creation_task.done()

        clone_handle = creation_task.result()
        if is_cancelled:
            await clone_handle.terminate()

            raise asyncio.CancelledError

        return clone_handle

    async def _create_handle(
        self, reference: str, staging_path: Path, lock_descriptor: int
    ) -> GithubCloneHandle:
        environment = self._get_environment()
        directory = str(staging_path)
        arguments = ["gh", "repo", "clone", "--no-upstream", reference, directory]
        try:
            process = await asyncio.create_subprocess_exec(
                *arguments,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=environment,
                start_new_session=True,
                pass_fds=(lock_descriptor,),
            )
        except OSError as error:
            raise CatalogError(
                code=CatalogErrorCodeEnum.IMPORT_FAILED,
                detail="The GitHub clone process cannot start.",
            ) from error

        return SubprocessCloneHandle(process)

    @staticmethod
    def _get_environment() -> dict[str, str]:
        return os.environ | {
            "GH_PROMPT_DISABLED": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
            "GIT_SSH_COMMAND": "ssh -oBatchMode=yes",
            "GCM_INTERACTIVE": "never",
        }
