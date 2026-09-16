"""The interface for the text a notification channel posts about a dag and its nodes."""

from __future__ import annotations

from abc import ABC, abstractmethod

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


class NotificationComposer(ABC):
    """A composer for dag and node event notifications in a channel's markup."""

    @abstractmethod
    def work_started(self, event: WorkStartedEvent) -> str:
        """Return the text for an agent starting work on a node."""

    @abstractmethod
    def pull_request_adopted(self, event: PullRequestAdoptedEvent) -> str:
        """Return the text for an agent taking over a pull request that already exists."""

    @abstractmethod
    def pull_request_opened(self, event: PullRequestOpenedEvent) -> str:
        """Returns notification text for a pull request opened event."""

    @abstractmethod
    def commit_pushed(self, event: CommitPushedEvent) -> str:
        """Returns notification text for a commit push event."""

    @abstractmethod
    def comments_added(self, event: CommentsAddedEvent) -> str:
        """Return the text for new reviewer comments awaiting a response."""

    @abstractmethod
    def comments_addressed(self, event: CommentsAddressedEvent) -> str:
        """Return the text for reviewer comments the agent has responded to."""

    @abstractmethod
    def checks_completed(self, event: ChecksCompletedEvent) -> str:
        """Return the text for the checks on a pull request."""

    @abstractmethod
    def mergeability_changed(self, event: MergeabilityChangedEvent) -> str:
        """Return the text for whether a pull request merges cleanly."""

    @abstractmethod
    def pull_request_approved(self, event: PullRequestApprovedEvent) -> str:
        """Return the text for a pull request approval."""

    @abstractmethod
    def pull_request_merged(self, event: PullRequestMergedEvent) -> str:
        """Return the text for a merged pull request."""

    @abstractmethod
    def agent_stopped(self, event: AgentStoppedEvent) -> str:
        """Return the text for a node the agent cannot advance alone."""

    @abstractmethod
    def node_retried(self, event: NodeRetriedEvent) -> str:
        """Return text for a human returning a node to the run."""

    @abstractmethod
    def node_skipped(self, event: NodeSkippedEvent) -> str:
        """Return the text for a node that was skipped."""

    @abstractmethod
    def dag_started(self, event: DagStartedEvent) -> str:
        """Return the text for a dag starting."""

    @abstractmethod
    def dag_completed(self, event: DagCompletedEvent) -> str:
        """Return the text for a dag whose every node has settled."""
