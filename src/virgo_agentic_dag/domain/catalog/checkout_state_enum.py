from enum import StrEnum


class CheckoutStateEnum(StrEnum):
    """Describe a checkout's observed local condition."""

    PENDING = "pending"
    READY = "ready"
    MISSING = "missing"
    INVALID = "invalid"
