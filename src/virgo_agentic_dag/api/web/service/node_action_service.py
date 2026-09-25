"""The service for retrying, waking, and stopping a node."""

from __future__ import annotations

import logging

from virgo_agentic_dag.api.web.api_requests.retry_request import RetryRequest
from virgo_agentic_dag.api.web.api_requests.wake_request import WakeRequest
from virgo_agentic_dag.api.web.api_responses.node_response import NodeResponse
from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.exceptions.run.node_action_failed import NodeActionFailed
from virgo_agentic_dag.domain.exceptions.run.node_action_refused import (
    NodeActionRefused,
)
from virgo_agentic_dag.domain.execution.run_result import RunResult
from virgo_agentic_dag.domain.infra.host.dagctl_runner import DagctlRunner
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.dag_utils import get_dag_graph_path
from virgo_agentic_dag.utils.format_label import format_label

logger = logging.getLogger(__name__)


class NodeActionService:
    """Retries, wakes, and stops a node."""

    def __init__(
        self,
        dag_web_service: DagWebService,
        dagctl_runner: DagctlRunner,
        timeout: float,
    ) -> None:
        self._dag_web_service = dag_web_service
        self._dagctl_runner = dagctl_runner
        self._timeout = timeout

    async def retry_node(
        self, dag_name: str, node_id: str, retry_request: RetryRequest
    ) -> NodeResponse | None:
        """Return the node after retrying it, or None when the dag or node is unknown."""
        node_response = await self._dag_web_service.get_node_by_name(dag_name, node_id)
        if node_response is None:
            return None

        reset_arguments = ["--reset"] if retry_request.reset else []
        retry_arguments = ["retry", node_id, *reset_arguments]
        await self._run_dagctl(dag_name, node_id, retry_arguments)

        return await self._dag_web_service.get_node_by_name(dag_name, node_id)

    async def wake_node(
        self, dag_name: str, node_id: str, wake_request: WakeRequest
    ) -> NodeResponse | None:
        """Return the node after waking it, or None when the dag or node is unknown."""
        node_response = await self._dag_web_service.get_node_by_name(dag_name, node_id)
        if node_response is None:
            return None

        is_resting = node_response.state == NodeState.RESTING.value
        if not is_resting:
            values = {"dag": dag_name, "node": node_id, "state": node_response.state}

            raise NodeActionRefused(format_label(LABELS["nodeNotResting"], values))

        recover_arguments = [
            "recover",
            node_id,
            f"--cause={wake_request.cause.value}",
            f"--action={wake_request.action}",
            f"--wake={wake_request.message}",
        ]
        await self._run_dagctl(dag_name, node_id, recover_arguments)

        return await self._dag_web_service.get_node_by_name(dag_name, node_id)

    async def stop_node(self, dag_name: str, node_id: str) -> NodeResponse | None:
        """Return the node after stopping its session, or None when the dag or node is unknown."""
        node_response = await self._dag_web_service.get_node_by_name(dag_name, node_id)
        if node_response is None:
            return None

        stop_arguments = ["stop", node_id]
        await self._run_dagctl(dag_name, node_id, stop_arguments)

        return await self._dag_web_service.get_node_by_name(dag_name, node_id)

    async def _run_dagctl(
        self, dag_name: str, node_id: str, arguments: list[str]
    ) -> None:
        """Run a dagctl command on the graph file of a dag and wait for it to exit."""
        dag_path = get_dag_graph_path(dag_name)
        dagctl_arguments = [
            *arguments,
            "--dag",
            str(dag_path),
            "--timeout",
            str(self._timeout),
        ]
        run_result = await self._dagctl_runner.run(dagctl_arguments, dag_path.parent)

        self._assert_success(run_result, dag_name, node_id)

    def _assert_success(
        self, run_result: RunResult, dag_name: str, node_id: str
    ) -> None:
        """Raise NodeActionRefused or NodeActionFailed when dagctl does not succeed."""
        exit_code = run_result.returncode
        refusal_text = run_result.stdout.strip()
        values = {
            "dag": dag_name,
            "node": node_id,
            "exit_code": exit_code,
            "timeout": self._timeout,
        }
        if exit_code == ExitCode.RUN_BUSY:
            raise NodeActionRefused(format_label(LABELS["runBusy"], values))

        if exit_code == ExitCode.FAILURE and refusal_text:
            raise NodeActionRefused(refusal_text)

        if exit_code != ExitCode.SUCCESS:
            logger.error(
                "dagctl exits with code %s for node %s in dag %s with output %s",
                exit_code,
                node_id,
                dag_name,
                run_result.get_output(),
            )

            raise NodeActionFailed(format_label(LABELS["nodeActionFailed"], values))
