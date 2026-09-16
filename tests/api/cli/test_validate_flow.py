from collections.abc import Callable
from pathlib import Path

import pytest
from virgo_agentic_dag.api.cli.dagctl import main

pytestmark = pytest.mark.e2e

_VALID = """name = "live"
executor_agent = "claude"

[[nodes]]
id = "A"
brief = "Do the first thing."

[[nodes]]
id = "B"
depends_on = ["A"]
brief = "Do the second thing."
"""

_INVALID = """name = "live"

[[nodes]]
id = "A"
executor_agent = "claude"
depends_on = ["ghost"]
brief = "Do the thing."

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "Do it again."
"""

_MALFORMED_PR = """name = "live"
executor_agent = "claude"

[[nodes]]
id = "A"
pr = "412"
brief = "Take over the pull request."
"""

_UNPARSEABLE = 'name = "broken'


@pytest.fixture
def write_dag(tmp_path: Path) -> Callable[[str], Path]:
    def _write(body: str) -> Path:
        dag = tmp_path / "live-dag.toml"
        header = f'db_path = "{tmp_path / "db.sqlite3"}"\n'
        dag.write_text(header + body, encoding="utf-8")

        return dag

    return _write


@pytest.fixture
def run_validate(
    write_dag: Callable[[str], Path], capsys: pytest.CaptureFixture[str]
) -> Callable[[str], tuple[int, str, str]]:
    def _run(body: str) -> tuple[int, str, str]:
        code = main(["validate", "--dag", str(write_dag(body))])
        captured = capsys.readouterr()

        return code, captured.out, captured.err

    return _run


def test_a_valid_graph_is_reported_valid_and_exits_zero(
    run_validate: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_validate(_VALID)

    assert code == 0
    assert out == "valid\n"


def test_an_invalid_graph_prints_one_reason_per_line_and_exits_one(
    run_validate: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_validate(_INVALID)

    assert code == 1
    assert out.splitlines() == [
        "duplicate-node: A is declared more than once",
        "unknown-dependency: A depends on ghost, which is not in the graph",
    ]


def test_a_node_whose_pull_request_is_not_a_url_is_refused(
    run_validate: Callable[[str], tuple[int, str, str]],
) -> None:
    code, out, _ = run_validate(_MALFORMED_PR)

    assert code == 1
    assert out.splitlines() == [
        "pr-not-url: A names pr 412, which is not a pull request url"
    ]


def test_the_validate_command_creates_no_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    dag = tmp_path / "homed-dag.toml"
    dag.write_text(_VALID, encoding="utf-8")
    run_home = tmp_path / "live"

    code = main(["validate", "--dag", str(dag)])

    assert code == 0
    assert not run_home.exists()


def test_a_file_that_fails_to_parse_prints_the_reason_and_exits_one(
    run_validate: Callable[[str], tuple[int, str, str]],
) -> None:
    code, _, err = run_validate(_UNPARSEABLE)

    assert code == 1
    assert "not valid TOML" in err
