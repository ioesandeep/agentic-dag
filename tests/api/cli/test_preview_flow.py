from collections.abc import Callable
from pathlib import Path

import pytest
from virgo_agentic_dag.api.cli.dagctl import main

pytestmark = pytest.mark.e2e

_TWO_NODES = """name = "live"
executor_agent = "claude"

[[nodes]]
id = "A"
brief = "Do the first thing."

[[nodes]]
id = "B"
depends_on = ["A"]
brief = "Do the second thing."
"""

_ADOPTED = """name = "live"
executor_agent = "claude"

[[nodes]]
id = "A"
pr = "https://github.com/acme/widgets/pull/412"
brief = "Take over the pull request."
"""

_UNPARSEABLE = 'name = "broken'


@pytest.fixture
def write_dag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], Path]:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    def _write(body: str) -> Path:
        dag = tmp_path / "live-dag.toml"
        dag.write_text(body, encoding="utf-8")

        return dag

    return _write


@pytest.fixture
def run_preview(
    write_dag: Callable[[str], Path], capsys: pytest.CaptureFixture[str]
) -> Callable[[str], tuple[int, str, str]]:
    def _run(body: str) -> tuple[int, str, str]:
        code = main(["preview", "--dag", str(write_dag(body))])
        captured = capsys.readouterr()

        return code, captured.out, captured.err

    return _run


def test_the_diagram_draws_every_node_with_its_dependency_edges(
    run_preview: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_preview(_TWO_NODES)

    assert code == 0
    assert out.splitlines()[:4] == [
        "flowchart TD",
        "    A[A]",
        "    B[B]",
        "    A --> B",
    ]


def test_the_count_reports_how_many_agents_the_run_would_start(
    run_preview: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_preview(_TWO_NODES)

    assert code == 0
    assert out.endswith("agents: 2\n")


def test_a_node_taking_over_a_pull_request_is_marked_adopted(
    run_preview: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_preview(_ADOPTED)

    assert code == 0
    assert '    A["A (adopted)"]' in out.splitlines()


def test_a_preview_writes_nothing_to_the_host(
    run_preview: Callable[[str], tuple[int, str, str]], tmp_path: Path
) -> None:
    code, _, _ = run_preview(_TWO_NODES)

    assert code == 0
    assert not (tmp_path / "live").exists()


def test_preview_reports_why_a_graph_file_will_not_parse(
    run_preview: Callable[[str], tuple[int, str, str]],
) -> None:
    code, _, err = run_preview(_UNPARSEABLE)

    assert code == 1
    assert "not valid TOML" in err
