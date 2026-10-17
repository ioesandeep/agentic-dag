from enum import StrEnum


class ImportStatusEnum(StrEnum):
    """Describe an import attempt's execution state."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"
