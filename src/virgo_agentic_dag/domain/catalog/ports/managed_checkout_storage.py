from abc import ABC, abstractmethod
from pathlib import Path


class ManagedCheckoutStorage(ABC):
    """Provide attempt staging and preserve published checkouts."""

    @abstractmethod
    async def create_staging(self, import_id: str) -> Path:
        """Create a directory owned by a new import attempt."""

    @abstractmethod
    async def publish_staging(self, repository_id: str, import_id: str) -> Path:
        """Publish caller-validated staging under the caller's repository lock."""

    @abstractmethod
    async def get_final_path(self, repository_id: str) -> Path | None:
        """Locate an existing final directory for recovery validation."""

    @abstractmethod
    async def delete_staging(self, import_id: str) -> None:
        """Delete attempt staging after the caller confirms process termination."""
