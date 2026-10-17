from abc import ABC, abstractmethod


class CatalogDatabase(ABC):
    """Define the catalog storage lifecycle for services."""

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare catalog storage for use."""

    @abstractmethod
    async def dispose(self) -> None:
        """Release catalog database connections."""
