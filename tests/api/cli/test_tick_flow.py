import os
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest
from virgo_agentic_dag.api.cli.dagctl import main
from virgo_agentic_dag.infra.agent.claude_agent_launcher import ClaudeAgentLauncher
from virgo_agentic_dag.infra.locking.dag_run_lock import DagRunLock

pytestmark = pytest.mark.e2e

DAG_TOML = """
name = "e2e"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "build the first slice"

[[nodes]]
id = "B"
executor_agent = "claude"
brief = "build on top of A"
depends_on = ["A"]
"""

BROKEN_DAG_TOML = """
name = "e2e"

[[nodes]]
id = "A"
executor_agent = "claude"
brief = "depends on a ghost"
depends_on = ["ghost"]
"""


def build_run_dir(
    tmp_path: Path, dag_toml: str, db_in_dag: bool = True
) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "develop"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    dag = tmp_path / "dag.toml"
    workspace = tmp_path / "ws"
    db = tmp_path / "db.sqlite3" if db_in_dag else tmp_path / "e2e" / "db.sqlite3"
    db_line = f'db_path = "{db}"\n' if db_in_dag else ""
    header = (
        f'project_root = "{repo}"\n'
        f'workspace_path = "{workspace}"\n'
        f"{db_line}"
        'base_branch = "develop"\n'
    )
    dag.write_text(header + dag_toml, encoding="utf-8")

    return {
        "dag": dag,
        "repo": repo,
        "workspace": workspace,
        "db": db,
    }


def install_agent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    script: str,
    binary: str = ClaudeAgentLauncher._BINARY,
) -> None:
    """Put a stub named like the launcher's binary ahead of the real one on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / binary
    stub.write_text(script, encoding="utf-8")
    stub.chmod(0o755)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")


@pytest.fixture(autouse=True)
def exiting_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_agent(tmp_path, monkeypatch, "#!/bin/sh\necho stub=claude\n")
    install_agent(
        tmp_path,
        monkeypatch,
        "#!/bin/sh\necho stub=codex\n"
        'echo \'{"type":"thread.started","thread_id":"codex-thread"}\'\n',
        binary="codex",
    )


def sleeping_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_agent(tmp_path, monkeypatch, "#!/bin/sh\nsleep 60\n")


def run_tick(paths: dict[str, Path]) -> int:
    return int(main(["tick", "--dag", str(paths["dag"])]))


def run_retry(paths: dict[str, Path], node_id: str, reset: bool = False) -> int:
    flags = ["--reset"] if reset else []

    return int(main(["retry", node_id, "--dag", str(paths["dag"]), *flags]))


def settle_agent(paths: dict[str, Path]) -> int:
    newest_pid = get_newest_pid(paths["db"])
    assert wait_until_dead(newest_pid)

    return run_tick(paths)


def get_states(db: Path) -> dict[str, str]:
    with sqlite3.connect(db) as connection:
        return dict(connection.execute("select id, state from nodes"))


def get_newest_pid(db: Path) -> int:
    with sqlite3.connect(db) as connection:
        row = connection.execute(
            "select pid from agent_sessions order by id desc limit 1"
        ).fetchone()

    return int(row[0])


def get_resume_token(db: Path) -> str:
    with sqlite3.connect(db) as connection:
        row = connection.execute("select resume_token from node_agents").fetchone()

    return str(row[0])


def is_dead(pid: int) -> bool:
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True

    return False


def wait_until_dead(pid: int) -> bool:
    deadline = time.monotonic() + 5
    while not is_dead(pid) and time.monotonic() < deadline:
        time.sleep(0.05)

    return is_dead(pid)


@pytest.mark.parametrize("executor", ["claude", "codex"])
def test_starts_the_ready_node_when_the_run_first_ticks(
    tmp_path: Path,
    executor: str,
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML.replace('"claude"', f'"{executor}"'))

    assert run_tick(paths) == 0

    assert get_states(paths["db"]) == {"A": "in_progress", "B": "pending"}
    with sqlite3.connect(paths["db"]) as connection:
        agents = list(
            connection.execute("select node_id, name, resume_token from node_agents")
        )
        sessions = connection.execute("select count(*) from agent_sessions").fetchone()[
            0
        ]
        worktrees = list(connection.execute("select name from work_trees"))
        audits = list(connection.execute("select node_id, state from audit_entries"))

    assert len(agents) == 1 and agents[0][0] == "A" and agents[0][1] == executor
    assert agents[0][2]
    assert sessions == 1
    assert worktrees == [("A",)]
    assert audits == [("A", "in_progress")]
    assert (paths["workspace"] / "A").is_dir()


@pytest.mark.parametrize(
    "executor,override", [("codex", "claude"), ("claude", "codex")]
)
def test_runs_the_recovery_and_learning_agents_with_the_dag_executor_when_a_node_specifies_a_different_executor(
    tmp_path: Path,
    executor: str,
    override: str,
) -> None:
    paths = build_run_dir(
        tmp_path,
        f'name = "mixed"\nexecutor_agent = "{executor}"\n'
        '[[nodes]]\nid = "A"\nbrief = "first slice"\n'
        f'[[nodes]]\nid = "B"\nexecutor_agent = "{override}"\nbrief = "second slice"\n',
    )
    assert run_tick(paths) == 0
    with sqlite3.connect(paths["db"]) as connection:
        agents = dict(connection.execute("select node_id, name from node_agents"))
        pids = list(connection.execute("select pid from agent_sessions"))

    for (pid,) in pids:
        assert wait_until_dead(pid)

    assert agents == {"A": executor, "B": override}
    assert f"stub={executor}" in (paths["workspace"] / "A.log").read_text()
    assert f"stub={override}" in (paths["workspace"] / "B.log").read_text()
    assert run_tick(paths) == 3
    with sqlite3.connect(paths["db"]) as connection:
        recovery_pid = connection.execute(
            "select pid from recovery_session"
        ).fetchone()[0]
        connection.execute(
            "update nodes set state = 'merged', pull_request_settled_at = '2026-09-12 00:00:00'"
        )

    assert wait_until_dead(recovery_pid)
    assert f"stub={executor}" in (tmp_path / "recovery.log").read_text()
    assert run_tick(paths) == 3
    learning_pid = int((tmp_path / "learning_extraction.lock").read_text())
    assert wait_until_dead(learning_pid)
    assert f"stub={executor}" in (tmp_path / "learning.log").read_text()


def test_changes_nothing_when_the_agent_is_still_working(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    sleeping_agent(tmp_path, monkeypatch)
    assert run_tick(paths) == 0

    assert run_tick(paths) == 0

    assert get_states(paths["db"]) == {"A": "in_progress", "B": "pending"}
    with sqlite3.connect(paths["db"]) as connection:
        sessions = connection.execute("select count(*) from agent_sessions").fetchone()[
            0
        ]

    assert sessions == 1


def test_settles_the_run_when_the_agent_published_nothing(
    tmp_path: Path,
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    assert run_tick(paths) == 0
    with sqlite3.connect(paths["db"]) as connection:
        pid = connection.execute("select pid from agent_sessions").fetchone()[0]

    assert wait_until_dead(pid)

    assert run_tick(paths) == 3

    assert get_states(paths["db"]) == {"A": "needs_human", "B": "needs_human"}
    with sqlite3.connect(paths["db"]) as connection:
        sessions = list(
            connection.execute("select end_state, ended_at from agent_sessions")
        )
        audits = list(
            connection.execute(
                "select node_id, state, note from audit_entries order by rowid"
            )
        )

    assert len(sessions) == 1
    assert sessions[0][0] == "finished" and sessions[0][1] is not None
    assert audits == [
        ("A", "in_progress", "A started work"),
        ("A", "needs_human", "its session finished without opening a pull request"),
        ("B", "needs_human", "upstream node A stopped, so this one can never start"),
        ("A", "needs_human", "a recovery agent session started to examine it"),
        ("B", "needs_human", "a recovery agent session started to examine it"),
    ]
    assert (paths["workspace"] / "A").is_dir()


def test_retry_resumes_the_recorded_agent_in_its_worktree(tmp_path: Path) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    assert run_tick(paths) == 0
    first_token = get_resume_token(paths["db"])
    assert settle_agent(paths) == 3

    assert run_retry(paths, "A") == 0
    assert run_tick(paths) == 0
    assert settle_agent(paths) == 3
    assert get_states(paths["db"])["A"] == "needs_human"

    assert run_retry(paths, "A") == 0
    assert run_tick(paths) == 0
    assert settle_agent(paths) == 3

    with sqlite3.connect(paths["db"]) as connection:
        tokens = list(connection.execute("select resume_token from node_agents"))
        triggers = list(
            connection.execute("select triggered_by from agent_sessions order by id")
        )
        worktree_names = list(connection.execute("select name from work_trees"))

    directory_names = [
        path.name for path in paths["workspace"].iterdir() if path.is_dir()
    ]
    assert tokens == [(first_token,)]
    assert triggers == [("launch",), ("wake",), ("wake",)]
    assert worktree_names == [("A",)]
    assert directory_names == ["A"]


@pytest.mark.parametrize("executor", ["claude", "codex"])
def test_retry_starts_a_new_conversation_when_the_command_includes_the_reset_option(
    tmp_path: Path, executor: str
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    assert run_tick(paths) == 0
    first_token = get_resume_token(paths["db"])
    assert settle_agent(paths) == 3

    paths["dag"].write_text(
        paths["dag"].read_text().replace('"claude"', f'"{executor}"')
    )
    assert run_retry(paths, "A", reset=True) == 0
    assert run_tick(paths) == 0
    assert settle_agent(paths) == 3

    with sqlite3.connect(paths["db"]) as connection:
        tokens = list(connection.execute("select resume_token from node_agents"))
        agents = list(connection.execute("select name from node_agents"))
        triggers = list(
            connection.execute("select triggered_by from agent_sessions order by id")
        )

    assert len(tokens) == 1
    assert tokens[0][0] != first_token
    assert agents == [(executor,)]
    assert triggers == [("launch",), ("launch",)]


@pytest.mark.parametrize("executor", ["claude", "codex"])
def test_recover_resumes_the_existing_agent_when_the_command_includes_a_wake_message(
    tmp_path: Path, executor: str
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML.replace('"claude"', f'"{executor}"'))
    assert run_tick(paths) == 0
    assert settle_agent(paths) == 3

    exit_code = main(
        [
            "recover",
            "A",
            "--dag",
            str(paths["dag"]),
            "--cause",
            "no_pull_request",
            "--action",
            "told it to open the pull request",
            "--wake",
            "open the pull request",
        ]
    )

    with sqlite3.connect(paths["db"]) as connection:
        triggers = list(
            connection.execute("select triggered_by from agent_sessions order by id")
        )
        notes = list(
            connection.execute(
                "select note from audit_entries where state = 'in_progress' order by rowid"
            )
        )
        rows = list(connection.execute("select cause from node_recovery"))

    assert int(exit_code) == 0
    assert get_states(paths["db"])["A"] == "in_progress"
    assert triggers == [("launch",), ("wake",)]
    assert notes[-1] == ("the recovery agent resumed it: open the pull request",)
    assert rows == [("no_pull_request",)]


def test_recover_leaves_the_node_to_a_human_when_it_is_unrecoverable(
    tmp_path: Path,
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    assert run_tick(paths) == 0
    assert settle_agent(paths) == 3

    exit_code = main(
        [
            "recover",
            "A",
            "--dag",
            str(paths["dag"]),
            "--cause",
            "no_pull_request",
            "--action",
            "the task names no repository to open the pull request in",
            "--unrecoverable",
        ]
    )

    with sqlite3.connect(paths["db"]) as connection:
        rows = list(
            connection.execute(
                "select cause, recoverable, action from node_recovery order by id"
            )
        )

    assert int(exit_code) == 0
    assert get_states(paths["db"])["A"] == "needs_human"
    assert rows == [
        (
            "no_pull_request",
            0,
            "the task names no repository to open the pull request in",
        )
    ]


def test_abort_kills_the_running_agent_and_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "virgo_agentic_dag.utils.dag_utils.get_dag_root", lambda: tmp_path
    )
    paths = build_run_dir(tmp_path, DAG_TOML, db_in_dag=False)
    sleeping_agent(tmp_path, monkeypatch)
    assert run_tick(paths) == 0
    with sqlite3.connect(paths["db"]) as connection:
        pid = connection.execute("select pid from agent_sessions").fetchone()[0]

    assert not is_dead(pid)

    assert int(main(["abort", "e2e"])) == 0

    assert wait_until_dead(pid)
    assert get_states(paths["db"]) == {"A": "needs_human", "B": "pending"}
    with sqlite3.connect(paths["db"]) as connection:
        sessions = list(
            connection.execute("select end_state, ended_at from agent_sessions")
        )
        audits = list(
            connection.execute(
                "select node_id, state from audit_entries order by rowid"
            )
        )

    assert len(sessions) == 1
    assert sessions[0][0] == "aborted" and sessions[0][1] is not None
    assert audits == [("A", "in_progress"), ("A", "needs_human")]


def test_exits_busy_when_another_pass_already_holds_the_run(tmp_path: Path) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    holder = DagRunLock(paths["db"])
    holder.acquire()

    assert run_tick(paths) == 75

    holder.release()
    assert run_tick(paths) == 0


def test_writes_nothing_when_the_graph_is_invalid(tmp_path: Path) -> None:
    paths = build_run_dir(tmp_path, BROKEN_DAG_TOML)

    assert run_tick(paths) == 1

    assert get_states(paths["db"]) == {}


def test_exits_with_the_complete_code_when_every_node_has_settled(
    tmp_path: Path,
) -> None:
    paths = build_run_dir(tmp_path, DAG_TOML)
    assert run_tick(paths) == 0

    with sqlite3.connect(paths["db"]) as connection:
        connection.execute("update nodes set state = 'merged'")

    assert run_tick(paths) == 3

    assert get_states(paths["db"]) == {"A": "merged", "B": "merged"}
    assert not (paths["workspace"] / "A").is_dir()
    with sqlite3.connect(paths["db"]) as connection:
        reclaimed = list(connection.execute("select reclaimed_at from work_trees"))

    assert len(reclaimed) == 1 and reclaimed[0][0] is not None
