import re
from dataclasses import dataclass

from virgo_agentic_dag.domain.catalog.catalog_error import CatalogError
from virgo_agentic_dag.domain.catalog.catalog_error_code_enum import (
    CatalogErrorCodeEnum,
)


@dataclass(frozen=True)
class GitHubRepositoryReference:
    """Identify the GitHub repository requested by a caller."""

    full_name: str

    def __post_init__(self) -> None:
        normalized_reference = self.full_name.strip().lower()
        normalized_reference = normalized_reference.removesuffix("/").removesuffix(
            ".git"
        )
        repository_match = re.fullmatch(
            r"(?:(?:https://github\.com/|git@github\.com:|ssh://git@github\.com(?::22)?/))?"
            r"([a-z0-9][a-z0-9-]*/(?!\.{1,2}$)[a-z0-9_.-]+)",
            normalized_reference,
        )
        if repository_match is None:
            raise CatalogError(
                code=CatalogErrorCodeEnum.UNSUPPORTED_REMOTE,
                detail="A supported GitHub repository reference is required.",
                field="reference",
            )

        full_name = repository_match.group(1)
        object.__setattr__(self, "full_name", full_name)

    @property
    def web_url(self) -> str:
        """Locate the repository on GitHub."""
        return f"https://github.com/{self.full_name}"
