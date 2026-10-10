"""The model settings for every Codex session in a DAG."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CodexSpec:
    """Select the model and reasoning effort for new and resumed Codex sessions."""

    model: str = "gpt-6-sol"
    reasoning_effort: str = "xhigh"
