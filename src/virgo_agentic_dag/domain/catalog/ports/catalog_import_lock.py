from abc import ABC, abstractmethod
from contextlib import AbstractContextManager


class CatalogImportLock(ABC):
    """Prevent concurrent imports of the same repository."""

    @abstractmethod
    def acquire(self, repository_id: str) -> AbstractContextManager[int]:
        """Provide an owned descriptor until the import and clone terminate."""
