"""Adds an existing pull request to a run as a resting node."""

from __future__ import annotations

from pathlib import Path

from virgo_agentic_dag.bootstrap.application_context import emit
from virgo_agentic_dag.domain.command.adopt_command import AdoptCommand
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.graph.graph_node import GraphNode
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.code.pull_request_details import (
    PullRequestDetails,
)
from virgo_agentic_dag.domain.infra.spec.dag_loader import DagLoader
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.specs.dag_spec import WORKSPACE_HOME, DagSpec
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.run.node_importer import NodeImporter
from virgo_agentic_dag.utils.format_label import format_label


class AdoptService:
    """Resolves what the adopt command line named and hands the node to the importer."""

    def __init__(
        self,
        dag_loader: DagLoader,
        code_repo: CodeRepo,
        node_repo: NodeRepo,
        node_importer: NodeImporter,
    ) -> None:
        self._dag_loader = dag_loader
        self._code_repo = code_repo
        self._node_repo = node_repo
        self._node_importer = node_importer

    async def adopt(self, command: AdoptCommand) -> ExitCode:
        """Seed the adopted node, refusing a run that is not going or an id it already uses."""
        dag_spec = self._dag_loader.load(command.dag_path)
        if not dag_spec.get_db_path().exists():
            emit(format_label(LABELS["runMissing"], {"dag": dag_spec.name}))

            return ExitCode.FAILURE

        if not command.pr.startswith(("http://", "https://")):
            raise SpecError(format_label(LABELS["prNotUrl"], {"pr": command.pr}))

        pr_details = await self._code_repo.get_pr_details_from_url(command.pr)
        node_id = command.node_id or f"PR-{pr_details.number}"
        if await self._node_repo.read(node_id) is not None:
            emit(
                format_label(
                    LABELS["nodeAlreadyInRun"],
                    {"node_id": node_id, "dag_name": dag_spec.name},
                )
            )

            return ExitCode.FAILURE

        workspace_path = (
            command.workspace_path
            or dag_spec.workspace_path
            or WORKSPACE_HOME / dag_spec.name
        )
        project_root = await self._resolve_project_root(
            command, dag_spec, pr_details, workspace_path
        )
        graph_node = GraphNode(
            id=node_id,
            title=pr_details.title,
            executor_agent=command.executor or dag_spec.executor_agent,
            instructions=self._render_takeover_brief(pr_details),
            project_root=project_root,
            workspace_path=workspace_path,
            pr=pr_details.url,
        )
        await self._node_importer.import_node(graph_node, pr_details, command.session)

        emit(
            format_label(
                LABELS["nodeAdopted"],
                {
                    "node_id": node_id,
                    "dag_name": dag_spec.name,
                    "pr_number": pr_details.number,
                    "branch": pr_details.head_branch,
                },
            )
        )

        return ExitCode.SUCCESS

    def _render_takeover_brief(self, pr_details: PullRequestDetails) -> str:
        """Return the brief for a node the command line adopts, since it declares none itself."""
        return format_label(
            LABELS["takeoverBrief"],
            {
                "pr_number": pr_details.number,
                "repository": pr_details.repository,
                "branch": pr_details.head_branch,
                "pr_url": pr_details.url,
            },
        )

    async def _resolve_project_root(
        self,
        command: AdoptCommand,
        dag_spec: DagSpec,
        pr_details: PullRequestDetails,
        workspace_path: Path,
    ) -> Path:
        """Return the checkout holding the pull request's repository, cloning it when none does."""
        if command.project_root is not None:
            if not await self._is_repo_in_project_root(
                command.project_root, pr_details.repository
            ):
                message = format_label(
                    LABELS["prOutsideCheckout"],
                    {
                        "pr": pr_details.url,
                        "repository": pr_details.repository,
                        "project_root": command.project_root,
                    },
                )

                raise ConfigError(message)

            return command.project_root

        dag_project_root = dag_spec.project_root
        if dag_project_root is not None and await self._is_repo_in_project_root(
            dag_project_root, pr_details.repository
        ):
            return dag_project_root

        clone_root = workspace_path / pr_details.repository.split("/")[-1]
        if not clone_root.is_dir():
            clone_root.parent.mkdir(parents=True, exist_ok=True)
            await self._code_repo.clone_repository(pr_details.repository, clone_root)

        return clone_root

    async def _is_repo_in_project_root(
        self, project_root: Path, repository: str
    ) -> bool:
        """Report whether this project root is a checkout of the pull request's repository."""
        if not project_root.is_dir():
            return False

        try:
            project_repository = await self._code_repo.get_repo_slug(project_root)

            return project_repository == repository
        except ObservationError:
            return False
