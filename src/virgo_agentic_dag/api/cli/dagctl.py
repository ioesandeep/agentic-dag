"""The dagctl command-line entry point for inspecting and advancing a run."""

from __future__ import annotations

import argparse
import asyncio
import io
import logging
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from virgo_agentic_dag.domain.command.exit_code import ExitCode
from virgo_agentic_dag.domain.command.serve_command import DEFAULT_HOST, DEFAULT_PORT
from virgo_agentic_dag.domain.exceptions.host.web_extra_missing import WebExtraMissing
from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError
from virgo_agentic_dag.domain.exceptions.manifest.config_error import ConfigError
from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.exceptions.platform.observation_error import (
    ObservationError,
)
from virgo_agentic_dag.domain.exceptions.platform.publish_error import PublishError
from virgo_agentic_dag.domain.exceptions.run.run_busy import RunBusy
from virgo_agentic_dag.domain.node.recovery_cause_enum import RecoveryCauseEnum
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.dag_utils import (
    get_dag_db_path,
    get_dag_home,
)

ENV_FILE_NAME = ".env.local"

_FAILURES = (
    ConfigError,
    SpecError,
    ObservationError,
    PublishError,
    WebExtraMissing,
    WorktreeError,
    sqlite3.OperationalError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested command, reporting a known failure without a traceback."""
    args = _build_parser().parse_args(argv)
    _open_reporting()
    _load_environment(args)

    try:
        return _dispatch(args)
    except RunBusy as busy:
        sys.stderr.write(f"{busy}\n")

        return int(ExitCode.RUN_BUSY)
    except _FAILURES as error:
        sys.stderr.write(f"{error}\n")

        return 1


def _dispatch(args: argparse.Namespace) -> int:
    if args.command == "validate":
        return _run_validate(args)

    if args.command == "preview":
        return _run_preview(args)

    if args.command == "tick":
        return _run_tick(args)

    if args.command == "start":
        return _run_start(args)

    if args.command == "abort":
        return _run_abort(args)

    if args.command == "watch":
        return _run_watch(args)

    if args.command == "status":
        return _run_status(args)

    if args.command == "adopt":
        return _run_adopt(args)

    if args.command == "retry":
        return _run_retry(args)

    if args.command == "skip":
        return _run_skip(args)

    if args.command == "stop":
        return _run_stop(args)

    if args.command == "examine":
        return _run_examine(args)

    if args.command == "recover":
        return _run_recover(args)

    if args.command == "serve":
        return _run_serve(args)

    return _run_log(args)


def _run_validate(args: argparse.Namespace) -> int:
    """Validate the graph file named by --dag and return the handler's exit code."""
    from virgo_agentic_dag.api.cli.handlers.validate_command_handler import (
        ValidateCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.validate_command import ValidateCommand

    command = ValidateCommand(dag_path=args.dag)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(ValidateCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_preview(args: argparse.Namespace) -> int:
    """Render the graph file named by --dag and return the handler's exit code."""
    from virgo_agentic_dag.api.cli.handlers.preview_command_handler import (
        PreviewCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.preview_command import PreviewCommand

    command = PreviewCommand(dag_path=args.dag)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(PreviewCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_tick(args: argparse.Namespace) -> int:
    """Advance a run by one control pass."""
    from virgo_agentic_dag.api.cli.handlers.tick_command_handler import (
        TickCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.tick_command import TickCommand

    command = TickCommand(dag_path=args.dag)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(TickCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_start(args: argparse.Namespace) -> int:
    """Run one pass, then register the host job that re-runs `start` until the run completes."""
    from virgo_agentic_dag.api.cli.handlers.start_command_handler import (
        StartCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.start_command import StartCommand

    command = StartCommand(dag_path=args.dag)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(StartCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_abort(args: argparse.Namespace) -> int:
    """Stop the run named on the command line and return the handler's exit code."""
    from virgo_agentic_dag.api.cli.handlers.abort_command_handler import (
        AbortCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.abort_command import AbortCommand

    command = AbortCommand(dag_name=args.name)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(AbortCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_adopt(args: argparse.Namespace) -> int:
    """Add a node for an existing pull request to a run that is already going."""
    from virgo_agentic_dag.api.cli.handlers.adopt_command_handler import (
        AdoptCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.adopt_command import AdoptCommand

    command = AdoptCommand(
        dag_path=args.dag,
        pr=args.pr,
        node_id=args.id,
        session=args.session,
        executor=ExecutorAgent(args.executor) if args.executor else None,
        project_root=args.project_root,
        workspace_path=args.workspace,
    )

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(AdoptCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_retry(args: argparse.Namespace) -> int:
    """Send a stopped node of the graph named by --dag back to work."""
    from virgo_agentic_dag.api.cli.handlers.retry_command_handler import (
        RetryCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.retry_command import RetryCommand

    command = RetryCommand(dag_path=args.dag, node_id=args.node, reset=args.reset)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(RetryCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_skip(args: argparse.Namespace) -> int:
    """Skip a node of the graph named by --dag and return the handler's exit code."""
    from virgo_agentic_dag.api.cli.handlers.skip_command_handler import (
        SkipCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.skip_command import SkipCommand

    command = SkipCommand(dag_path=args.dag, node_id=args.node)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(SkipCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_stop(args: argparse.Namespace) -> int:
    """Stop the specified node's running session."""
    from virgo_agentic_dag.api.cli.handlers.stop_command_handler import (
        StopCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.stop_command import StopCommand

    command = StopCommand(dag_path=args.dag, node_id=args.node)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(StopCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_examine(args: argparse.Namespace) -> int:
    """Print the current row of a node of the graph named by --dag."""
    from virgo_agentic_dag.api.cli.handlers.examine_command_handler import (
        ExamineCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.examine_command import ExamineCommand

    command = ExamineCommand(dag_path=args.dag, node_id=args.node)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(ExamineCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_recover(args: argparse.Namespace) -> int:
    """Act on a stopped node of the graph named by --dag and record the recovery."""
    from virgo_agentic_dag.api.cli.handlers.recover_command_handler import (
        RecoverCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.recover_command import RecoverCommand

    command = RecoverCommand(
        dag_path=args.dag,
        node_id=args.node,
        cause=RecoveryCauseEnum(args.cause),
        action=args.action,
        recoverable=not args.unrecoverable,
        recover_at=args.recover_at,
        restore_marks=args.restore_marks,
        wake_message=args.wake,
    )

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(RecoverCommandHandler).handle(command))

    return asyncio.run(_run())


def _parse_utc_timestamp(text: str) -> datetime:
    """Return the ISO 8601 timestamp as a UTC datetime, taking a bare one as UTC already."""
    timestamp = datetime.fromisoformat(text)
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)

    return timestamp.astimezone(UTC)


def _run_watch(args: argparse.Namespace) -> int:
    """Fire a pass whenever the named run's pull requests change."""
    from virgo_agentic_dag.api.cli.handlers.watch_command_handler import (
        WatchCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.watch_command import WatchCommand

    command = WatchCommand(dag_name=args.name, sse_url=args.sse)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(WatchCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_status(args: argparse.Namespace) -> int:
    """Print the named run's recorded state, or fail when no run has that name."""
    from virgo_agentic_dag.api.cli.handlers.status_command_handler import (
        StatusCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.status_command import StatusCommand
    from virgo_agentic_dag.utils.format_label import format_label

    if not (get_dag_db_path(args.name)).exists():
        raise ConfigError(format_label(LABELS["dagUnknown"], {"dag": args.name}))

    command = StatusCommand(dag_name=args.name)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(StatusCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_serve(args: argparse.Namespace) -> int:
    """Serve the read-only web api until the process is stopped."""
    from virgo_agentic_dag.api.cli.handlers.serve_command_handler import (
        ServeCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.serve_command import ServeCommand

    command = ServeCommand(host=args.host, port=args.port)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(ServeCommandHandler).handle(command))

    return asyncio.run(_run())


def _run_log(args: argparse.Namespace) -> int:
    """Print the named run's audit trail, or fail when no run has that name."""
    from virgo_agentic_dag.api.cli.handlers.log_command_handler import (
        LogCommandHandler,
    )
    from virgo_agentic_dag.bootstrap.context_initializer import initialize_context
    from virgo_agentic_dag.domain.command.log_command import LogCommand
    from virgo_agentic_dag.utils.format_label import format_label

    if not (get_dag_db_path(args.name)).exists():
        raise ConfigError(format_label(LABELS["dagUnknown"], {"dag": args.name}))

    command = LogCommand(dag_name=args.name)

    async def _run() -> int:
        async with initialize_context(command, sys.stdout) as context:
            return int(await context.get(LogCommandHandler).handle(command))

    return asyncio.run(_run())


def _load_environment(args: argparse.Namespace) -> None:
    """Load the run's own `.env.local`, since a scheduled process reads no profile."""
    home = _get_run_home(args)
    if home is None:
        return

    load_dotenv(home / ENV_FILE_NAME)


def _get_run_home(args: argparse.Namespace) -> Path | None:
    """Return the directory this command's run keeps its files in, if it names one."""
    if args.command in ("abort", "watch", "status", "log"):
        return get_dag_home(args.name)

    dag = getattr(args, "dag", None)
    if dag is None:
        return None

    return Path(dag).parent


def _open_reporting() -> None:
    """Stream progress unbuffered, so a long-running command is not left silent."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dagctl")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help=LABELS["validateHelp"])
    validate.add_argument("--dag", type=Path, required=True)

    preview = commands.add_parser("preview", help=LABELS["previewHelp"])
    preview.add_argument("--dag", type=Path, required=True)

    tick = commands.add_parser("tick", help=LABELS["tickHelp"])
    tick.add_argument("--dag", type=Path, required=True)

    start = commands.add_parser("start", help=LABELS["startHelp"])
    start.add_argument("--dag", type=Path, required=True)

    abort = commands.add_parser("abort", help=LABELS["abortHelp"])
    abort.add_argument("name")

    watch = commands.add_parser("watch", help=LABELS["watchHelp"])
    watch.add_argument("name")
    watch.add_argument("--sse", default="")

    adopt = commands.add_parser("adopt", help=LABELS["adoptHelp"])
    adopt.add_argument(
        "--pr", required=True, help="the url of the pull request to take over"
    )
    adopt.add_argument(
        "--dag", type=Path, required=True, help="the graph file of the run adopting it"
    )
    adopt.add_argument(
        "--executor",
        default=None,
        help="executor for the adopted node; defaults to the dag executor",
        choices=[agent.value for agent in ExecutorAgent],
    )
    adopt.add_argument("--id", default="", help="node id; coined from the pr if unset")
    adopt.add_argument(
        "--session", default="", help="an agent session to resume on the first wake"
    )
    adopt.add_argument(
        "--project-root",
        type=Path,
        help="the checkout the pull request lives in, when not the dag's own",
    )
    adopt.add_argument(
        "--workspace",
        type=Path,
        help="where the node's worktree is cut, when not the dag's own",
    )

    retry = commands.add_parser("retry", help=LABELS["retryHelp"])
    retry.add_argument("node", help="the id of the stopped node to send back to work")
    retry.add_argument(
        "--dag", type=Path, required=True, help="the graph file of the run holding it"
    )
    retry.add_argument(
        "--reset",
        action="store_true",
        help="start a new conversation instead of resuming the recorded one",
    )

    skip = commands.add_parser("skip", help=LABELS["skipHelp"])
    skip.add_argument("node", help="the id of the node to skip")
    skip.add_argument(
        "--dag", type=Path, required=True, help="the graph file of the run holding it"
    )

    stop = commands.add_parser("stop", help=LABELS["stopHelp"])
    stop.add_argument("node", help="the id of the node to stop")
    stop.add_argument(
        "--dag", type=Path, required=True, help="the graph file for the run"
    )

    examine = commands.add_parser("examine", help=LABELS["examineHelp"])
    examine.add_argument("node", help="the id of the node to print")
    examine.add_argument(
        "--dag", type=Path, required=True, help="the graph file of the run holding it"
    )

    recover = commands.add_parser("recover", help=LABELS["recoverHelp"])
    recover.add_argument("node", help="the id of the failed node to act on")
    recover.add_argument(
        "--dag", type=Path, required=True, help="the graph file of the run holding it"
    )
    recover.add_argument(
        "--cause",
        required=True,
        choices=[cause.value for cause in RecoveryCauseEnum],
        help="the classification of the failure",
    )
    recover.add_argument(
        "--action", required=True, help="what the recovery agent did about it"
    )
    recover.add_argument(
        "--recover-at",
        type=_parse_utc_timestamp,
        help="when the node is eligible again, as an ISO 8601 timestamp; now when unset",
    )
    recover.add_argument(
        "--restore-marks",
        action="store_true",
        help="put the worktree's watermarks back to before the latest session",
    )
    verdict = recover.add_mutually_exclusive_group()
    verdict.add_argument(
        "--wake", default="", help="resume the node's conversation with this message"
    )
    verdict.add_argument(
        "--unrecoverable",
        action="store_true",
        help="record that no recovery is possible and leave the node to a human",
    )

    status = commands.add_parser("status", help=LABELS["statusHelp"])
    status.add_argument("name")

    log = commands.add_parser("log", help=LABELS["logHelp"])
    log.add_argument("name")

    serve = commands.add_parser("serve", help=LABELS["serveHelp"])
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    return parser
