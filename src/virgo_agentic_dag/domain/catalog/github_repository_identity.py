from dataclasses import dataclass

from virgo_agentic_dag.domain.catalog.repository_provider_enum import (
    RepositoryProviderEnum,
)


@dataclass(frozen=True)
class GitHubRepositoryIdentity:
    """Describe a repository independently of its current owner and name."""

    provider_repository_id: str
    full_name: str
    web_url: str
    ssh_url: str
    default_branch: str | None
    provider: RepositoryProviderEnum = RepositoryProviderEnum.GITHUB
    host: str = "github.com"
