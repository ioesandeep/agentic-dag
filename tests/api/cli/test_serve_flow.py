import sys
from pathlib import Path

import pytest
from virgo_agentic_dag.api.cli.dagctl import main

pytestmark = pytest.mark.e2e

WEB_MODULE_PREFIXES = ("virgo_agentic_dag.api.web", "virgo_agentic_dag.infra.web")
WEB_EXTRA_PACKAGES = ("fastapi", "pydantic", "uvicorn")

_VALID_DAG = """name = "live"
executor_agent = "claude"

[[nodes]]
id = "A"
brief = "Do the first thing."
"""


def uninstall_web_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make fastapi, pydantic, and uvicorn unimportable for the rest of this test."""
    for name in list(sys.modules):
        if name.startswith(WEB_MODULE_PREFIXES):
            monkeypatch.delitem(sys.modules, name)

    for name in WEB_EXTRA_PACKAGES:
        monkeypatch.setitem(sys.modules, name, None)


def test_refuses_to_serve_when_the_web_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    uninstall_web_extra(monkeypatch)

    exit_code = main(["serve"])

    assert exit_code == 1
    assert capsys.readouterr().err == (
        "serve needs the web extra: uv sync --package virgo-agentic-dag --extra web\n"
    )


def test_validates_a_graph_when_the_web_extra_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    uninstall_web_extra(monkeypatch)
    dag = tmp_path / "live-dag.toml"
    dag.write_text(_VALID_DAG, encoding="utf-8")

    exit_code = main(["validate", "--dag", str(dag)])

    assert exit_code == 0
    assert capsys.readouterr().out == "valid\n"
