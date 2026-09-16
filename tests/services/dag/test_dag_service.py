from pathlib import Path

import pytest
from virgo_agentic_dag.services.dag.dag_service import DagService
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.unit


def build_service(dag_home: Path, monkeypatch: pytest.MonkeyPatch) -> DagService:
    monkeypatch.setattr(
        "virgo_agentic_dag.services.dag.dag_service.get_dag_root", lambda: dag_home
    )
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: dag_home
    )

    return DagService(TomlDagLoader())


def write_graph(home: Path, name: str, nodes: int = 1) -> None:
    home.mkdir(parents=True, exist_ok=True)
    blocks = "".join(f"[[nodes]]\nid = 'n{index}'\n" for index in range(nodes))
    home.joinpath("dag.toml").write_text(f"name = '{name}'\n{blocks}", encoding="utf-8")


def test_loads_every_dag_under_the_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_graph(tmp_path / "alpha", "alpha", nodes=2)
    write_graph(tmp_path / "beta", "beta")
    (tmp_path / "worktrees").mkdir()

    dag_specs = build_service(tmp_path, monkeypatch).get_dag_list()

    assert [(dag_spec.name, len(dag_spec.nodes)) for dag_spec in dag_specs] == [
        ("alpha", 2),
        ("beta", 1),
    ]


def test_skips_a_dag_when_its_graph_file_will_not_load(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_graph(tmp_path / "alpha", "alpha")
    (tmp_path / "legacy").mkdir()
    (tmp_path / "legacy" / "dag.toml").write_text("name = 'legacy'\n", encoding="utf-8")

    dag_specs = build_service(tmp_path, monkeypatch).get_dag_list()

    assert [dag_spec.name for dag_spec in dag_specs] == ["alpha"]


def test_returns_nothing_when_the_home_holds_no_dag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert build_service(tmp_path, monkeypatch).get_dag_list() == []
    assert build_service(tmp_path / "never-created", monkeypatch).get_dag_list() == []
