from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError


class WorktreeConflictError(WorktreeError):
    """Indicates that a workspace path belongs to an unregistered directory."""
