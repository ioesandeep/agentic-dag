from virgo_agentic_dag.domain.exceptions.host.worktree_error import WorktreeError


class BaseBranchMissingError(WorktreeError):
    """Indicates that a worktree base branch does not resolve to a commit."""
