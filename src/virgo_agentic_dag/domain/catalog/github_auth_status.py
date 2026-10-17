from dataclasses import dataclass


@dataclass(frozen=True)
class GithubAuthStatus:
    """Describe the GitHub account available for catalog operations."""

    host: str
    authenticated: bool
    login: str | None
    guidance: str | None
