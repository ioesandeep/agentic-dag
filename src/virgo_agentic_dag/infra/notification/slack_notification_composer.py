"""Composes the notifications about a dag and its nodes in the markup Slack renders."""

from __future__ import annotations

from collections.abc import Mapping

from virgo_agentic_dag.domain.events.agent_stopped_event import AgentStoppedEvent
from virgo_agentic_dag.domain.events.checks_completed_event import ChecksCompletedEvent
from virgo_agentic_dag.domain.events.comments_added_event import CommentsAddedEvent
from virgo_agentic_dag.domain.events.comments_addressed_event import (
    CommentsAddressedEvent,
)
from virgo_agentic_dag.domain.events.commit_pushed_event import CommitPushedEvent
from virgo_agentic_dag.domain.events.dag_completed_event import DagCompletedEvent
from virgo_agentic_dag.domain.events.dag_started_event import DagStartedEvent
from virgo_agentic_dag.domain.events.mergeability_changed_event import (
    MergeabilityChangedEvent,
)
from virgo_agentic_dag.domain.events.node_retried_event import NodeRetriedEvent
from virgo_agentic_dag.domain.events.node_skipped_event import NodeSkippedEvent
from virgo_agentic_dag.domain.events.pull_request_adopted_event import (
    PullRequestAdoptedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_approved_event import (
    PullRequestApprovedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_merged_event import (
    PullRequestMergedEvent,
)
from virgo_agentic_dag.domain.events.pull_request_opened_event import (
    PullRequestOpenedEvent,
)
from virgo_agentic_dag.domain.events.work_started_event import WorkStartedEvent
from virgo_agentic_dag.domain.node.node_state import NodeState
from virgo_agentic_dag.domain.notifications.notification_composer import (
    NotificationComposer,
)
from virgo_agentic_dag.domain.run.pr_details import PrDetails
from virgo_agentic_dag.utils.format_duration import format_duration


class SlackNotificationComposer(NotificationComposer):
    """Composes every notification with Slack's link and bold markup."""

    def work_started(self, event: WorkStartedEvent) -> str:
        return self._render_started(event.agent_name, event.title or event.node_id)

    def pull_request_adopted(self, event: PullRequestAdoptedEvent) -> str:
        return (
            f"Agent *{event.agent_name}* was handed "
            f"{self._render_link(event.pr_details)}. "
            "It will respond to whatever happens there next — new comments, "
            "merge conflicts, failing checks, or the pull request becoming ready."
        )

    def pull_request_opened(self, event: PullRequestOpenedEvent) -> str:
        started = self._render_started(event.agent_name, event.title or event.node_id)
        url = self._render_url(event.pr_details)

        return f"{started}\n{url}"

    def commit_pushed(self, event: CommitPushedEvent) -> str:
        if not event.commit_count:
            return ""

        commits = "commit" if event.commit_count == 1 else "commits"

        return (
            f"Agent *{event.agent_name}* pushed {event.commit_count} {commits} to "
            f"{self._render_link(event.pr_details)}"
        )

    def comments_added(self, event: CommentsAddedEvent) -> str:
        comments = "comment was" if event.comment_count == 1 else "comments were"

        return (
            f"{event.comment_count} {comments} added to "
            f"{self._render_link(event.pr_details)}. Addressing them now"
        )

    def comments_addressed(self, event: CommentsAddressedEvent) -> str:
        comments = "comment" if event.comment_count == 1 else "comments"
        head_sha = event.pr_details.head_sha
        where = f" in `{head_sha[:8]}`" if head_sha else ""

        return (
            f"Addressed {event.comment_count} {comments} on "
            f"{self._render_link(event.pr_details)}{where}"
        )

    def checks_completed(self, event: ChecksCompletedEvent) -> str:
        link = self._render_link(event.pr_details)
        if not event.pr_details.failures:
            return f"The checks on {link} are green again"

        named = ", ".join(f"`{failure.name}`" for failure in event.pr_details.failures)

        return f"{link} has failing checks: {named}. Looking into it"

    def mergeability_changed(self, event: MergeabilityChangedEvent) -> str:
        link = self._render_link(event.pr_details)
        if not event.pr_details.is_conflicted:
            return f"{link} merges cleanly again"

        return (
            f"{link} has merge conflicts with the base branch. I will try to resolve "
            "them, and ask for help if I cannot"
        )

    def pull_request_approved(self, event: PullRequestApprovedEvent) -> str:
        approver = event.pr_details.get_approver_name()
        who = f"*{approver}*" if approver else "A reviewer"

        return (
            f"{who} approved {self._render_link(event.pr_details)}. "
            "Waiting for it to be merged"
        )

    def pull_request_merged(self, event: PullRequestMergedEvent) -> str:
        who = f"*{event.pr_details.merged_by}*" if event.pr_details.merged_by else "It"

        return (
            f"{who} merged {self._render_link(event.pr_details)}. "
            f"Agent *{event.agent_name}* will wind down. Thank you!"
        )

    def agent_stopped(self, event: AgentStoppedEvent) -> str:
        where = ""
        if event.pr_details is not None:
            where = f" on {self._render_link(event.pr_details)}"

        stopped = f"`{event.node_id}` stopped{where} — {event.reason}"
        log_line = self._get_log_line(event.log_tail)
        if not log_line:
            return stopped

        return f"{stopped}\n```\n{log_line}\n```"

    def node_retried(self, event: NodeRetriedEvent) -> str:
        return (
            f"A human sent `{event.title or event.node_id}` back to work. "
            f"Agent *{event.agent_name}* starts again on the next pass"
        )

    def node_skipped(self, event: NodeSkippedEvent) -> str:
        return f"`{event.title or event.node_id}` was skipped"

    def dag_started(self, event: DagStartedEvent) -> str:
        nodes = "node" if event.node_count == 1 else "nodes"

        return (
            f"*{event.dag_name}* started — {event.node_count} {nodes}, "
            f"{event.in_progress_node_count} in progress"
        )

    def dag_completed(self, event: DagCompletedEvent) -> str:
        elapsed_time = format_duration(event.elapsed_time)
        state_counts = self._render_state_counts(event.node_counts_by_state)

        return f"*{event.dag_name}* complete in {elapsed_time} — {state_counts}"

    def _render_state_counts(
        self, node_counts_by_state: Mapping[NodeState, int]
    ) -> str:
        state_counts = [
            f"{count} {state.value.replace('_', ' ')}"
            for state, count in node_counts_by_state.items()
        ]

        return ", ".join(state_counts)

    def _get_log_line(self, log_tail: str) -> str:
        """Return the final non-empty log line escaped for Slack."""
        lines = [line.strip() for line in log_tail.splitlines() if line.strip()]
        if not lines:
            return ""

        last_line = lines[-1][:200]

        return (
            last_line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("`", "")
        )

    def _render_started(self, agent_name: str, title: str) -> str:
        return f"Agent *{agent_name}* started working on `{title}`"

    def _render_url(self, pr_details: PrDetails) -> str:
        if not pr_details.url:
            return f"pr#{pr_details.number}"

        return f"<{pr_details.url}>"

    def _render_link(self, pr_details: PrDetails) -> str:
        if not pr_details.url:
            return f"pr#{pr_details.number}"

        return f"<{pr_details.url}|pr#{pr_details.number}>"
