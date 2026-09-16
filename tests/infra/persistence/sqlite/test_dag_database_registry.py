from pathlib import Path

import pytest
from virgo_agentic_dag.infra.persistence.sqlite.dag_database_registry import (
    DagDatabaseRegistry,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def dag_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )

    return tmp_path


def test_registry_returns_no_gateway_when_the_dag_has_no_database(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()
    dag_home.joinpath("alpha").mkdir()

    assert registry.open("alpha") is None


def test_registry_returns_the_same_gateway_when_a_dag_opens_twice(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()
    dag_home.joinpath("alpha").mkdir()
    dag_home.joinpath("alpha", "db.sqlite3").touch()

    assert registry.open("alpha") is registry.open("alpha")


async def test_registry_opens_a_dag_again_when_it_has_been_disposed(
    dag_home: Path,
) -> None:
    registry = DagDatabaseRegistry()
    dag_home.joinpath("alpha").mkdir()
    dag_home.joinpath("alpha", "db.sqlite3").touch()
    first = registry.open("alpha")

    await registry.dispose()

    assert registry.open("alpha") is not first
