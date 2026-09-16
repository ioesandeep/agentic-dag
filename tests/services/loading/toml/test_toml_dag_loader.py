from pathlib import Path

import pytest
from virgo_agentic_dag.domain.exceptions.manifest.spec_error import SpecError
from virgo_agentic_dag.domain.notifications.notification_dispatcher_type import (
    NotificationDispatcherType,
)
from virgo_agentic_dag.domain.specs.executor_agent import ExecutorAgent
from virgo_agentic_dag.domain.states.attempt_budget import AttemptBudget
from virgo_agentic_dag.services.loading.toml.toml_dag_loader import TomlDagLoader

pytestmark = pytest.mark.unit

DAG_TOML = """
name = "demo"

[[nodes]]
id = "T1"
executor_agent = "claude"
brief = "b"

[[nodes]]
id = "T"
depends_on = ["T1"]
"""


def build_data() -> dict[str, object]:
    return {
        "name": "demo",
        "project_root": "/projects/virgo",
        "workspace_path": "/ws/virgo",
        "executor_agent": "claude",
        "base_branch": "develop",
        "nodes": [
            {"id": "T1", "brief": "b"},
            {
                "id": "T2",
                "project_root": "~/projects/spacy",
                "workspace_path": "/ws/spacy",
                "base_branch": "main",
            },
            {"id": "T", "depends_on": ["T1"]},
        ],
    }


def test_parse_dag_round_trips() -> None:
    data = build_data()

    spec = TomlDagLoader().parse(data)

    assert spec.name == "demo"
    assert spec.find_node("T").depends_on == ("T1",)


def test_reads_the_defaults_when_the_dag_names_them() -> None:
    data = build_data()

    spec = TomlDagLoader().parse(data)

    assert spec.project_root == Path("/projects/virgo")
    assert spec.workspace_path == Path("/ws/virgo")
    assert spec.executor_agent is ExecutorAgent.CLAUDE
    assert spec.base_branch == "develop"


def test_reads_the_overrides_when_a_node_names_them() -> None:
    data = build_data()

    node = TomlDagLoader().parse(data).find_node("T2")

    assert node.project_root == Path.home() / "projects" / "spacy"
    assert node.workspace_path == Path("/ws/spacy")
    assert node.base_branch == "main"


def test_leaves_the_overrides_empty_when_a_node_names_none() -> None:
    data = build_data()

    node = TomlDagLoader().parse(data).find_node("T1")

    assert node.project_root is None
    assert node.workspace_path is None
    assert node.executor_agent is None
    assert node.base_branch == ""


def test_load_dag_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "dag.toml"
    path.write_text(DAG_TOML, encoding="utf-8")

    spec = TomlDagLoader().load(path)

    assert spec.name == "demo"
    assert spec.find_node("T").depends_on == ("T1",)


def test_reads_the_run_behavior_when_the_dag_names_it() -> None:
    data = {
        **build_data(),
        "max_workers": 4,
        "tick_interval_seconds": 120,
        "slack_channel": "#dag",
        "sse_url": "http://stream/events",
        "agent_account": "bot",
        "caps": {
            "node_wakes": 5,
            "node_recoveries": 2,
            "session_timeout_seconds": 900,
            "session_turns": 40,
        },
    }

    spec = TomlDagLoader().parse(data)

    assert spec.max_workers == 4
    assert spec.tick_interval_seconds == 120
    assert spec.slack_channel == "#dag"
    assert spec.sse_url == "http://stream/events"
    assert spec.agent_account == "bot"
    assert spec.caps == AttemptBudget(
        node_wakes=5,
        node_recoveries=2,
        session_timeout_seconds=900,
        session_turns=40,
    )


def test_defaults_the_run_behavior_when_the_dag_says_nothing() -> None:
    spec = TomlDagLoader().parse(build_data())

    assert spec.max_workers == 2
    assert spec.tick_interval_seconds == 300
    assert spec.caps == AttemptBudget()
    assert spec.notification_dispatcher is NotificationDispatcherType.BOT
    assert spec.sse_url == ""


def test_defaults_the_session_turns_when_the_caps_table_omits_it() -> None:
    data = {**build_data(), "caps": {"node_wakes": 5}}

    spec = TomlDagLoader().parse(data)

    assert spec.caps.session_turns == AttemptBudget().session_turns


def test_rejects_a_session_turns_that_is_not_a_positive_integer() -> None:
    data = {**build_data(), "caps": {"session_turns": 0}}

    with pytest.raises(SpecError, match="session_turns"):
        TomlDagLoader().parse(data)


def test_rejects_a_notification_dispatcher_it_does_not_know() -> None:
    data = {**build_data(), "notification_dispatcher": "carrier-pigeon"}

    with pytest.raises(SpecError, match="bot or mcp"):
        TomlDagLoader().parse(data)


@pytest.mark.parametrize("dag_executor", ["claude", "codex"])
def test_uses_the_dag_executor_or_a_nodes_own_override_when_one_is_named(
    dag_executor: str,
) -> None:
    override = "codex" if dag_executor == "claude" else "claude"
    data = {
        "name": "mixed",
        "executor_agent": dag_executor,
        "nodes": [
            {"id": "A"},
            {"id": "B", "executor_agent": override},
        ],
    }

    spec = TomlDagLoader().parse(data)

    assert spec.executor_agent.value == dag_executor
    assert spec.get_executor_agent(spec.nodes[0]).value == dag_executor
    assert spec.get_executor_agent(spec.nodes[1]).value == override


def test_defaults_the_dag_executor_to_claude_when_the_data_omits_it() -> None:
    data = {"name": "bare", "nodes": [{"id": "A"}]}

    spec = TomlDagLoader().parse(data)

    assert spec.executor_agent is ExecutorAgent.CLAUDE
