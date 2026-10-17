from enum import StrEnum


class CheckoutKindEnum(StrEnum):
    """Distinguish managed checkouts from external checkouts."""

    MANAGED = "managed"
    EXTERNAL = "external"
