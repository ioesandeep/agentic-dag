import importlib

import pytest

pytestmark = pytest.mark.unit


def test_import_succeeds_when_the_workspace_is_installed() -> None:
    module = importlib.import_module("virgo_agentic_dag")

    assert module.__name__ == "virgo_agentic_dag"
