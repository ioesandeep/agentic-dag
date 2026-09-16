"""The kind of lifecycle moment a human-facing notification marks."""

from __future__ import annotations

from enum import Enum


class NotificationType(Enum):
    WORK_STARTED = "work_started"
    WORK_RESUMED = "work_resumed"
    PR_ADOPTED = "pr_adopted"
    PR_OPENED = "pr_opened"
    PR_UPDATED = "pr_updated"
    FEEDBACK_RECEIVED = "feedback_received"
    FEEDBACK_ADDRESSED = "feedback_addressed"
    FEEDBACK_ANSWERED = "feedback_answered"
    CONFLICTS_FOUND = "conflicts_found"
    CONFLICTS_RESOLVED = "conflicts_resolved"
    CI_FAILED = "ci_failed"
    CI_FIXED = "ci_fixed"
    AGENT_FAILED = "agent_failed"
    BLOCKED = "blocked"
    NEEDS_HUMAN = "needs_human"
    RETRIED = "retried"
    SKIPPED = "skipped"
    APPROVED = "approved"
    MERGED = "merged"
    APPROVED_AND_MERGED = "approved_and_merged"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
