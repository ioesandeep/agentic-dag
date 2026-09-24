"""Every bean the application uses, declared in one place and nowhere else."""

# mypy: disable-error-code="type-abstract"

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import create_async_engine
from virgo_agentic_dag.api.cli.handlers.abort_command_handler import (
    AbortCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.adopt_command_handler import (
    AdoptCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.examine_command_handler import (
    ExamineCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.log_command_handler import (
    LogCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.preview_command_handler import (
    PreviewCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.recover_command_handler import (
    RecoverCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.retry_command_handler import (
    RetryCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.serve_command_handler import (
    ServeCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.skip_command_handler import (
    SkipCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.start_command_handler import (
    StartCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.status_command_handler import (
    StatusCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.stop_command_handler import (
    StopCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.tick_command_handler import TickCommandHandler
from virgo_agentic_dag.api.cli.handlers.validate_command_handler import (
    ValidateCommandHandler,
)
from virgo_agentic_dag.api.cli.handlers.watch_command_handler import (
    WatchCommandHandler,
)
from virgo_agentic_dag.domain.command.dag_command import DagCommand
from virgo_agentic_dag.domain.command.serve_command import ServeCommand
from virgo_agentic_dag.domain.exceptions.host.web_extra_missing import WebExtraMissing
from virgo_agentic_dag.domain.infra.agent.agent_launcher import AgentLauncher
from virgo_agentic_dag.domain.infra.agent.session_killer import SessionKiller
from virgo_agentic_dag.domain.infra.agent.transcript_locator import TranscriptLocator
from virgo_agentic_dag.domain.infra.code.code_repo import CodeRepo
from virgo_agentic_dag.domain.infra.locking.run_lock import RunLock
from virgo_agentic_dag.domain.infra.messaging.notification_subscriber import (
    NotificationSubscriber,
)
from virgo_agentic_dag.domain.infra.streaming.stream_health_check import (
    StreamHealthCheck,
)
from virgo_agentic_dag.domain.infra.web.web_server import WebServer
from virgo_agentic_dag.domain.infra.workspace.workspace import Workspace
from virgo_agentic_dag.domain.notifications.notification_composer import (
    NotificationComposer,
)
from virgo_agentic_dag.domain.persistence.repos.agent_session_repo import (
    AgentSessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.audit_entry_repo import AuditEntryRepo
from virgo_agentic_dag.domain.persistence.repos.node_agent_repo import NodeAgentRepo
from virgo_agentic_dag.domain.persistence.repos.node_recovery_repo import (
    NodeRecoveryRepo,
)
from virgo_agentic_dag.domain.persistence.repos.node_repo import NodeRepo
from virgo_agentic_dag.domain.persistence.repos.recovery_session_repo import (
    RecoverySessionRepo,
)
from virgo_agentic_dag.domain.persistence.repos.scheduled_job_repo import (
    ScheduledJobRepo,
)
from virgo_agentic_dag.domain.persistence.repos.slack_notification_repo import (
    SlackNotificationRepo,
)
from virgo_agentic_dag.domain.persistence.repos.watcher_repo import WatcherRepo
from virgo_agentic_dag.domain.persistence.repos.work_tree_repo import WorkTreeRepo
from virgo_agentic_dag.domain.preview.renderer import Renderer
from virgo_agentic_dag.domain.service.graph_builder import GraphBuilder
from virgo_agentic_dag.domain.service.graph_validation_service import (
    GraphValidationService,
)
from virgo_agentic_dag.domain.service.notification_publisher import (
    NotificationPublisher,
)
from virgo_agentic_dag.domain.service.validators.cycle_validator import CycleValidator
from virgo_agentic_dag.domain.service.validators.duplicate_node_validator import (
    DuplicateNodeValidator,
)
from virgo_agentic_dag.domain.service.validators.malformed_pull_request_validator import (
    MalformedPullRequestValidator,
)
from virgo_agentic_dag.domain.service.validators.missing_dependency_validator import (
    MissingDependencyValidator,
)
from virgo_agentic_dag.domain.service.validators.missing_executor_validator import (
    MissingExecutorValidator,
)
from virgo_agentic_dag.domain.specs.dag_spec import DagSpec
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.infra.agent.agent_session_killer import AgentSessionKiller
from virgo_agentic_dag.infra.agent.claude_agent_launcher import ClaudeAgentLauncher
from virgo_agentic_dag.infra.agent.claude_transcript_locator import (
    ClaudeTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.codex_agent_launcher import CodexAgentLauncher
from virgo_agentic_dag.infra.agent.codex_transcript_locator import (
    CodexTranscriptLocator,
)
from virgo_agentic_dag.infra.agent.transcript_page_reader import TranscriptPageReader
from virgo_agentic_dag.infra.code.github_code_repo import GitHubCodeRepo
from virgo_agentic_dag.infra.host.subprocess_command_runner import (
    SubprocessCommandRunner,
)
from virgo_agentic_dag.infra.host.system_sleeper import SystemSleeper
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock
from virgo_agentic_dag.infra.notification.bot_notification_dispatcher import (
    BotNotificationDispatcher,
)
from virgo_agentic_dag.infra.notification.slack_notification_composer import (
    SlackNotificationComposer,
)
from virgo_agentic_dag.infra.notification.slack_notification_dispatcher_factory import (
    SlackNotificationDispatcherFactory,
)
from virgo_agentic_dag.infra.notification.slack_notification_subscriber import (
    SlackNotificationSubscriber,
)
from virgo_agentic_dag.infra.notification.urllib_json_poster import UrllibJsonPoster
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_agent_session_repo import (
    SqliteAgentSessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_audit_entry_repo import (
    SqliteAuditEntryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_database import SqliteDatabase
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_agent_repo import (
    SqliteNodeAgentRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_recovery_repo import (
    SqliteNodeRecoveryRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_node_repo import SqliteNodeRepo
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_recovery_session_repo import (
    SqliteRecoverySessionRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_scheduled_job_repo import (
    SqliteScheduledJobRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_slack_notification_repo import (
    SqliteSlackNotificationRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_watcher_repo import (
    SqliteWatcherRepo,
)
from virgo_agentic_dag.infra.persistence.sqlite.sqlite_work_tree_repo import (
    SqliteWorkTreeRepo,
)
from virgo_agentic_dag.infra.scheduling.scheduler_factory import SchedulerFactory
from virgo_agentic_dag.infra.streaming.sse_health_check import SseHealthCheck
from virgo_agentic_dag.infra.workspace.git_workspace import GitWorkspace
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.learning.extraction_lock import ExtractionLock
from virgo_agentic_dag.services.learning.learning_dispatch_service import (
    LearningDispatchService,
)
from virgo_agentic_dag.services.learning.learning_prompt_composer import (
    LearningPromptComposer,
)
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader
from virgo_agentic_dag.services.node_state_handlers.in_progress_node_handler import (
    InProgressNodeHandler,
)
from virgo_agentic_dag.services.node_state_handlers.merged_node_handler import (
    MergedNodeHandler,
)
from virgo_agentic_dag.services.node_state_handlers.node_state_handling_facade import (
    NodeStateHandlingFacade,
)
from virgo_agentic_dag.services.node_state_handlers.pending_node_handler import (
    PendingNodeHandler,
)
from virgo_agentic_dag.services.node_state_handlers.resting_node_handler import (
    RestingNodeHandler,
)
from virgo_agentic_dag.services.preview.mermaid_renderer import MermaidRenderer
from virgo_agentic_dag.services.recovery.node_examination_service import (
    NodeExaminationService,
)
from virgo_agentic_dag.services.recovery.node_recovery_service import (
    NodeRecoveryService,
)
from virgo_agentic_dag.services.recovery.recovery_dispatch_service import (
    RECOVERY_AGENT_NAME,
    RecoveryDispatchService,
)
from virgo_agentic_dag.services.recovery.recovery_prompt_composer import (
    RecoveryPromptComposer,
)
from virgo_agentic_dag.services.recovery.recovery_scan_service import (
    RecoveryScanService,
)
from virgo_agentic_dag.services.run.adopt_service import AdoptService
from virgo_agentic_dag.services.run.adopted_node_importer import AdoptedNodeImporter
from virgo_agentic_dag.services.run.node_importer import NodeImporter
from virgo_agentic_dag.services.run.node_skip_service import NodeSkipService
from virgo_agentic_dag.services.scheduling.scheduled_job_builder import (
    ScheduledJobBuilder,
)
from virgo_agentic_dag.services.signals.approval_signal import ApprovalSignal
from virgo_agentic_dag.services.signals.check_signal import CheckSignal
from virgo_agentic_dag.services.signals.comment_signal import CommentSignal
from virgo_agentic_dag.services.signals.conflict_signal import ConflictSignal
from virgo_agentic_dag.services.signals.pr_signal import PrSignal
from virgo_agentic_dag.services.stop.node_stop_service import NodeStopService
from virgo_agentic_dag.services.watching.run_watcher import RunWatcher
from virgo_agentic_dag.services.watching.subscription_factory import SubscriptionFactory
from virgo_agentic_dag.services.watching.watch_plan_reader import WatchPlanReader
from virgo_agentic_dag.services.watching.watcher_service import WatcherService
from virgo_agentic_dag.utils.dag_utils import get_learnings_file_path
from virgo_agentic_dag.utils.format_label import format_label

if TYPE_CHECKING:
    from virgo_agentic_dag.bootstrap.application_context import ApplicationContext


def register_beans(context: ApplicationContext) -> None:
    """Declare how every collaborator is built, so booting the context is one call."""
    context.register(TomlDagLoader, lambda _context: TomlDagLoader())
    context.register(DagSpec, _build_dag_spec)
    context.register(RunLock, lambda _context: DagRunLock(_context.get_db_path()))
    context.register(SqliteDatabase, _build_database)
    context.register(
        NodeRepo, lambda _context: SqliteNodeRepo(_context.get(SqliteDatabase))
    )
    context.register(
        AuditEntryRepo,
        lambda _context: SqliteAuditEntryRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        NodeAgentRepo,
        lambda _context: SqliteNodeAgentRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        AgentSessionRepo,
        lambda _context: SqliteAgentSessionRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        WorkTreeRepo,
        lambda _context: SqliteWorkTreeRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        SlackNotificationRepo,
        lambda _context: SqliteSlackNotificationRepo(_context.get(SqliteDatabase)),
    )
    context.register(BotNotificationDispatcher, _build_bot_notification_dispatcher)
    context.register(
        SlackNotificationDispatcherFactory,
        lambda _context: SlackNotificationDispatcherFactory(
            dag_spec=_context.get(DagSpec),
            bot_dispatcher=_context.get(BotNotificationDispatcher),
        ),
    )
    context.register(NotificationPublisher, _build_notification_publisher)
    context.register(
        NotificationComposer,
        lambda _context: SlackNotificationComposer(),
    )
    context.register(Workspace, _build_workspace)
    context.register(CodeRepo, _build_code_repo)
    context.register(SessionKiller, _build_session_killer)
    context.register(
        SchedulerFactory, lambda _context: SchedulerFactory(SubprocessCommandRunner())
    )
    context.register(
        ScheduledJobRepo,
        lambda _context: SqliteScheduledJobRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        WatcherRepo,
        lambda _context: SqliteWatcherRepo(context.get(SqliteDatabase)),
    )
    context.register(StreamHealthCheck, lambda _context: SseHealthCheck())
    context.register(WatcherService, _build_watcher_service)
    context.register(WatchCommandHandler, _build_watch_command_handler)
    context.register(
        GraphBuilder, lambda _context: GraphBuilder(context.get(TomlDagLoader))
    )
    context.register(
        GraphValidationService,
        lambda _context: GraphValidationService(
            [
                CycleValidator(),
                DuplicateNodeValidator(),
                MissingDependencyValidator(),
                MissingExecutorValidator(),
                MalformedPullRequestValidator(),
            ]
        ),
    )
    context.register(PendingNodeHandler, _build_pending_node_handler)
    context.register(InProgressNodeHandler, _build_in_progress_node_handler)
    context.register(RestingNodeHandler, _build_resting_node_handler)
    context.register(MergedNodeHandler, _build_merged_node_handler)
    context.register(NodeStateHandlingFacade, _build_node_state_handling_facade)
    context.register(TickCommandHandler, _build_tick_command_handler)
    context.register(ValidateCommandHandler, _build_validate_command_handler)
    context.register(Renderer, lambda _context: MermaidRenderer())
    context.register(PreviewCommandHandler, _build_preview_command_handler)
    context.register(ScheduledJobBuilder, _build_scheduled_job_builder)
    context.register(StartCommandHandler, _build_start_command_handler)
    context.register(AbortCommandHandler, _build_abort_command_handler)
    context.register(NodeImporter, _build_node_importer)
    context.register(AdoptService, _build_adopt_service)
    context.register(AdoptCommandHandler, _build_adopt_command_handler)
    context.register(RetryCommandHandler, _build_retry_command_handler)
    context.register(NodeSkipService, _build_node_skip_service)
    context.register(SkipCommandHandler, _build_skip_command_handler)
    context.register(NodeStopService, _build_node_stop_service)
    context.register(StopCommandHandler, _build_stop_command_handler)
    context.register(StatusCommandHandler, _build_status_command_handler)
    context.register(LogCommandHandler, _build_log_command_handler)
    context.register(DagService, _build_dag_service)
    context.register(
        NodeRecoveryRepo,
        lambda _context: SqliteNodeRecoveryRepo(_context.get(SqliteDatabase)),
    )
    context.register(
        RecoverySessionRepo,
        lambda _context: SqliteRecoverySessionRepo(_context.get(SqliteDatabase)),
    )
    context.register(RecoveryScanService, _build_recovery_scan_service)
    context.register(RecoveryDispatchService, _build_recovery_dispatch_service)
    context.register(LearningDispatchService, _build_learning_dispatch_service)
    context.register(NodeExaminationService, _build_node_examination_service)
    context.register(NodeRecoveryService, _build_node_recovery_service)
    context.register(ExamineCommandHandler, _build_examine_command_handler)
    context.register(RecoverCommandHandler, _build_recover_command_handler)

    if isinstance(context.command, ServeCommand):
        _register_web_beans(context)


def _register_web_beans(context: ApplicationContext) -> None:
    """Declare the beans only `serve` uses, which need the web extra installed."""
    try:
        from virgo_agentic_dag.api.web.controllers.dag_controller import DagController
        from virgo_agentic_dag.api.web.controllers.health_controller import (
            HealthController,
        )
        from virgo_agentic_dag.api.web.routes.conversation_route import (
            ConversationRoute,
        )
        from virgo_agentic_dag.api.web.routes.dag_route import DagRoute
        from virgo_agentic_dag.api.web.routes.health_route import HealthRoute
        from virgo_agentic_dag.api.web.routes.memory_route import MemoryRoute
        from virgo_agentic_dag.api.web.routes.recovery_session_route import (
            RecoverySessionRoute,
        )
        from virgo_agentic_dag.api.web.service.dag_web_service import DagWebService
        from virgo_agentic_dag.api.web.web_application_factory import (
            WebApplicationFactory,
        )
        from virgo_agentic_dag.infra.web.uvicorn_web_server import UvicornWebServer
    except ImportError as missing:
        raise WebExtraMissing(LABELS["webExtraMissing"]) from missing

    context.register(DagDatabaseRegistry, lambda _context: DagDatabaseRegistry())
    context.register(HealthController, lambda _context: HealthController())
    context.register(
        DagWebService,
        lambda _context: DagWebService(
            dag_service=_context.get(DagService),
            database_registry=_context.get(DagDatabaseRegistry),
            code_repo=_context.get(CodeRepo),
            transcript_locators=_build_transcript_locators(),
            transcript_reader=TranscriptPageReader(),
        ),
    )
    context.register(
        DagController, lambda _context: DagController(_context.get(DagWebService))
    )
    context.register(
        HealthRoute, lambda _context: HealthRoute(_context.get(HealthController))
    )
    context.register(DagRoute, lambda _context: DagRoute(_context.get(DagController)))
    context.register(
        MemoryRoute, lambda _context: MemoryRoute(_context.get(DagController))
    )
    context.register(
        ConversationRoute,
        lambda _context: ConversationRoute(_context.get(DagController)),
    )
    context.register(
        RecoverySessionRoute,
        lambda _context: RecoverySessionRoute(_context.get(DagController)),
    )
    context.register(
        WebApplicationFactory,
        lambda _context: WebApplicationFactory(
            dag_route=_context.get(DagRoute),
            health_route=_context.get(HealthRoute),
            memory_route=_context.get(MemoryRoute),
            conversation_route=_context.get(ConversationRoute),
            recovery_session_route=_context.get(RecoverySessionRoute),
        ),
    )
    context.register(
        WebServer,
        lambda _context: UvicornWebServer(
            application_factory=_context.get(WebApplicationFactory)
        ),
    )
    context.register(
        ServeCommandHandler,
        lambda _context: ServeCommandHandler(
            web_server=_context.get(WebServer),
            database_registry=_context.get(DagDatabaseRegistry),
        ),
    )


def _build_scheduled_job_builder(context: ApplicationContext) -> ScheduledJobBuilder:
    return ScheduledJobBuilder(context.get(DagSpec), Path(sys.argv[0]).resolve())


def _build_start_command_handler(context: ApplicationContext) -> StartCommandHandler:
    return StartCommandHandler(
        context.get(TickCommandHandler),
        context.get(SchedulerFactory),
        context.get(ScheduledJobRepo),
        context.get(NodeRepo),
        context.get(ScheduledJobBuilder),
        context.get(WatcherService),
        context.get(DagSpec),
        context.get(NotificationPublisher),
    )


def _build_watcher_service(context: ApplicationContext) -> WatcherService:
    return WatcherService(
        context.get(WatcherRepo),
        Path(sys.argv[0]).resolve(),
    )


def _build_watch_command_handler(context: ApplicationContext) -> WatchCommandHandler:
    plan_reader = WatchPlanReader(
        context.get(ScheduledJobRepo),
        context.get(WorkTreeRepo),
        context.get(CodeRepo),
        context.get(TomlDagLoader),
    )
    run_watcher = RunWatcher(
        plan_reader,
        SubscriptionFactory(),
        SubprocessCommandRunner(),
        SystemSleeper(),
    )

    return WatchCommandHandler(run_watcher)


def _build_dag_spec(context: ApplicationContext) -> DagSpec:
    """Load the DagSpec from the graph file the running command names."""
    return context.get(TomlDagLoader).load(_get_dag_path(context))


def _get_dag_path(context: ApplicationContext) -> Path:
    """Return the graph file the running command names, failing for a command that names none."""
    command = context.command
    if not isinstance(command, DagCommand):
        raise LookupError(
            format_label(
                LABELS["commandCarriesNoGraph"],
                {"command": type(command).__name__},
            )
        )

    return command.dag_path


def _build_workspace(_context: ApplicationContext) -> GitWorkspace:
    return GitWorkspace(SubprocessCommandRunner())


def _build_database(context: ApplicationContext) -> SqliteDatabase:
    db_path = context.get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    return SqliteDatabase(engine)


def _build_notification_publisher(
    _context: ApplicationContext,
) -> NotificationPublisher:
    subscribers: list[NotificationSubscriber[Any]] = [SlackNotificationSubscriber()]

    return NotificationPublisher(subscribers)


def _build_bot_notification_dispatcher(
    context: ApplicationContext,
) -> BotNotificationDispatcher:
    dag_spec = context.get(DagSpec)
    poster = UrllibJsonPoster()

    return BotNotificationDispatcher(
        poster=poster,
        slack_notification_repo=context.get(SlackNotificationRepo),
        channel=dag_spec.slack_channel,
        composer=context.get(NotificationComposer),
        dag_name=dag_spec.name,
    )


def _build_code_repo(_context: ApplicationContext) -> GitHubCodeRepo:
    return GitHubCodeRepo(SubprocessCommandRunner())


def _build_session_killer(context: ApplicationContext) -> AgentSessionKiller:
    return AgentSessionKiller(
        context.get(AgentSessionRepo),
        context.get(NodeRepo),
        context.get(AuditEntryRepo),
    )


def _build_abort_command_handler(context: ApplicationContext) -> AbortCommandHandler:
    return AbortCommandHandler(
        context.get(RunLock),
        context.get(WatcherService),
        context.get(SessionKiller),
        context.get(AgentSessionRepo),
        context.get(SchedulerFactory),
        context.get(ScheduledJobRepo),
    )


def _build_adopt_command_handler(context: ApplicationContext) -> AdoptCommandHandler:
    return AdoptCommandHandler(context.get(RunLock), context.get(AdoptService))


def _build_adopt_service(context: ApplicationContext) -> AdoptService:
    return AdoptService(
        dag_loader=context.get(TomlDagLoader),
        code_repo=context.get(CodeRepo),
        node_repo=context.get(NodeRepo),
        node_importer=context.get(NodeImporter),
    )


def _build_node_importer(context: ApplicationContext) -> AdoptedNodeImporter:
    return AdoptedNodeImporter(
        workspace=context.get(Workspace),
        node_repo=context.get(NodeRepo),
        node_agent_repo=context.get(NodeAgentRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        agent_launchers=_build_agent_launchers(context.get(DagSpec)),
    )


def _build_retry_command_handler(context: ApplicationContext) -> RetryCommandHandler:
    return RetryCommandHandler(
        context.get(RunLock),
        context.get(NodeRepo),
        context.get(AuditEntryRepo),
        context.get(NotificationPublisher),
        context.get(NodeAgentRepo),
    )


def _build_node_skip_service(context: ApplicationContext) -> NodeSkipService:
    return NodeSkipService(
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        graph_builder=context.get(GraphBuilder),
    )


def _build_skip_command_handler(context: ApplicationContext) -> SkipCommandHandler:
    return SkipCommandHandler(context.get(RunLock), context.get(NodeSkipService))


def _build_node_stop_service(context: ApplicationContext) -> NodeStopService:
    return NodeStopService(
        node_repo=context.get(NodeRepo),
        agent_session_repo=context.get(AgentSessionRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        graph_builder=context.get(GraphBuilder),
        agent_launchers=_build_agent_launchers(context.get(DagSpec)),
    )


def _build_stop_command_handler(context: ApplicationContext) -> StopCommandHandler:
    return StopCommandHandler(context.get(RunLock), context.get(NodeStopService))


def _build_status_command_handler(context: ApplicationContext) -> StatusCommandHandler:
    return StatusCommandHandler(
        context.get(NodeRepo),
        context.get(AgentSessionRepo),
        context.get(WatcherRepo),
        context.get(ScheduledJobRepo),
        context.get(TomlDagLoader),
        context.get(StreamHealthCheck),
    )


def _build_log_command_handler(context: ApplicationContext) -> LogCommandHandler:
    return LogCommandHandler(context.get(AuditEntryRepo))


def _build_dag_service(context: ApplicationContext) -> DagService:
    return DagService(context.get(TomlDagLoader))


def _build_transcript_locators() -> dict[ExecutorAgent, TranscriptLocator]:
    return {
        ExecutorAgent.CLAUDE: ClaudeTranscriptLocator(),
        ExecutorAgent.CODEX: CodexTranscriptLocator(),
    }


def _build_agent_launchers(
    dag_spec: DagSpec,
) -> dict[ExecutorAgent, AgentLauncher]:
    learnings_path = get_learnings_file_path(dag_spec.name)

    return {
        ExecutorAgent.CLAUDE: ClaudeAgentLauncher(
            dag_spec.caps.session_timeout_seconds,
            dag_spec.caps.session_turns,
            learnings_path,
        ),
        ExecutorAgent.CODEX: CodexAgentLauncher(
            dag_spec.caps.session_timeout_seconds,
            learnings_path,
            CodexTranscriptLocator(),
        ),
    }


def _build_pending_node_handler(context: ApplicationContext) -> PendingNodeHandler:
    dag_spec = context.get(DagSpec)
    agent_launchers = _build_agent_launchers(dag_spec)

    return PendingNodeHandler(
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        workspace=context.get(Workspace),
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        node_agent_repo=context.get(NodeAgentRepo),
        code_repo=context.get(CodeRepo),
        node_importer=context.get(NodeImporter),
    )


def _build_in_progress_node_handler(
    context: ApplicationContext,
) -> InProgressNodeHandler:
    dag_spec = context.get(DagSpec)
    agent_launchers = _build_agent_launchers(dag_spec)

    return InProgressNodeHandler(
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        node_agent_repo=context.get(NodeAgentRepo),
        agent_session_repo=context.get(AgentSessionRepo),
        work_tree_repo=context.get(WorkTreeRepo),
        workspace=context.get(Workspace),
        agent_launchers=agent_launchers,
        code_repo=context.get(CodeRepo),
    )


def _build_resting_node_handler(context: ApplicationContext) -> RestingNodeHandler:
    dag_spec = context.get(DagSpec)
    agent_launchers = _build_agent_launchers(dag_spec)
    pr_signals = _build_pr_signals(dag_spec)

    return RestingNodeHandler(
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        node_agent_repo=context.get(NodeAgentRepo),
        agent_session_repo=context.get(AgentSessionRepo),
        work_tree_repo=context.get(WorkTreeRepo),
        agent_launchers=agent_launchers,
        dag_spec=dag_spec,
        code_repo=context.get(CodeRepo),
        pr_signals=pr_signals,
    )


def _build_merged_node_handler(context: ApplicationContext) -> MergedNodeHandler:
    return MergedNodeHandler(
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        notification_publisher=context.get(NotificationPublisher),
        node_agent_repo=context.get(NodeAgentRepo),
        work_tree_repo=context.get(WorkTreeRepo),
        workspace=context.get(Workspace),
    )


def _build_pr_signals(dag_spec: DagSpec) -> list[PrSignal]:
    return [
        CommentSignal(agent_account=dag_spec.agent_account),
        CheckSignal(),
        ConflictSignal(),
        ApprovalSignal(),
    ]


def _build_node_state_handling_facade(
    context: ApplicationContext,
) -> NodeStateHandlingFacade:
    return NodeStateHandlingFacade(
        node_repo=context.get(NodeRepo),
        in_progress_handler=context.get(InProgressNodeHandler),
        resting_handler=context.get(RestingNodeHandler),
        pending_handler=context.get(PendingNodeHandler),
        merged_handler=context.get(MergedNodeHandler),
    )


def _build_tick_command_handler(context: ApplicationContext) -> TickCommandHandler:
    return TickCommandHandler(
        graph_builder=context.get(GraphBuilder),
        validation_service=context.get(GraphValidationService),
        node_repo=context.get(NodeRepo),
        node_state_handling_facade=context.get(NodeStateHandlingFacade),
        recovery_scan_service=context.get(RecoveryScanService),
        recovery_dispatch_service=context.get(RecoveryDispatchService),
        learning_dispatch_service=context.get(LearningDispatchService),
        out=context.output_writer,
    )


def _build_validate_command_handler(
    context: ApplicationContext,
) -> ValidateCommandHandler:
    return ValidateCommandHandler(
        graph_builder=context.get(GraphBuilder),
        validation_service=context.get(GraphValidationService),
        out=context.output_writer,
    )


def _build_preview_command_handler(
    context: ApplicationContext,
) -> PreviewCommandHandler:
    return PreviewCommandHandler(
        dag_spec=context.get(DagSpec),
        renderer=context.get(Renderer),
    )


def _build_recovery_scan_service(context: ApplicationContext) -> RecoveryScanService:
    return RecoveryScanService(
        node_repo=context.get(NodeRepo),
        node_recovery_repo=context.get(NodeRecoveryRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
    )


def _build_recovery_dispatch_service(
    context: ApplicationContext,
) -> RecoveryDispatchService:
    dag_spec = context.get(DagSpec)
    agent_launchers = _build_agent_launchers(dag_spec)
    executor_agent = dag_spec.executor_agent
    recovery_home = context.get_db_path().parent / RECOVERY_AGENT_NAME
    recovery_home.mkdir(parents=True, exist_ok=True)

    prompt_composer = RecoveryPromptComposer(
        node_recovery_repo=context.get(NodeRecoveryRepo),
        dag_path=_get_dag_path(context).resolve(),
        dagctl_path=Path(sys.argv[0]).resolve(),
        transcript_locators=_build_transcript_locators(),
    )

    return RecoveryDispatchService(
        recovery_session_repo=context.get(RecoverySessionRepo),
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        agent_launcher=agent_launchers[executor_agent],
        executor_agent=executor_agent,
        prompt_composer=prompt_composer,
        recovery_home=recovery_home,
    )


def _build_learning_dispatch_service(
    context: ApplicationContext,
) -> LearningDispatchService:
    dag_spec = context.get(DagSpec)
    agent_launchers = _build_agent_launchers(dag_spec)
    run_home = context.get_db_path().parent
    executor_agent = dag_spec.executor_agent

    extraction_lock = ExtractionLock(run_home / "learning_extraction.lock")
    prompt_composer = LearningPromptComposer(
        learnings_path=get_learnings_file_path(dag_spec.name),
        repo_slug=context.repo_slug,
    )

    return LearningDispatchService(
        extraction_lock=extraction_lock,
        prompt_composer=prompt_composer,
        node_repo=context.get(NodeRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        agent_launcher=agent_launchers[executor_agent],
        executor_agent=executor_agent,
        run_home=run_home,
    )


def _build_node_examination_service(
    context: ApplicationContext,
) -> NodeExaminationService:
    return NodeExaminationService(
        node_repo=context.get(NodeRepo),
        node_recovery_repo=context.get(NodeRecoveryRepo),
        transcript_locators=_build_transcript_locators(),
    )


def _build_node_recovery_service(context: ApplicationContext) -> NodeRecoveryService:
    return NodeRecoveryService(
        node_repo=context.get(NodeRepo),
        node_recovery_repo=context.get(NodeRecoveryRepo),
        agent_session_repo=context.get(AgentSessionRepo),
        audit_entry_repo=context.get(AuditEntryRepo),
        work_tree_repo=context.get(WorkTreeRepo),
        notification_publisher=context.get(NotificationPublisher),
        graph_builder=context.get(GraphBuilder),
        agent_launchers=_build_agent_launchers(context.get(DagSpec)),
    )


def _build_examine_command_handler(
    context: ApplicationContext,
) -> ExamineCommandHandler:
    return ExamineCommandHandler(context.get(NodeExaminationService))


def _build_recover_command_handler(
    context: ApplicationContext,
) -> RecoverCommandHandler:
    return RecoverCommandHandler(
        run_lock=context.get(RunLock),
        node_recovery_service=context.get(NodeRecoveryService),
    )
