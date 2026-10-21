import pytest

from virgo_agentic_dag.infra.code.check_failure_mapper import CheckFailureMapper

pytestmark = pytest.mark.unit


def test_passing_checks_are_not_failures():
    checks = [{"name": "build", "conclusion": "SUCCESS"}]

    assert CheckFailureMapper().get_failures(checks) == ()


def test_a_failure_keeps_its_name_and_conclusion():
    checks = [{"name": "tests", "conclusion": "FAILURE"}]

    failures = CheckFailureMapper().get_failures(checks)

    assert failures[0].name == "tests"
    assert failures[0].conclusion == "FAILURE"


def test_the_run_id_is_taken_from_the_details_link():
    checks = [
        {
            "name": "tests",
            "conclusion": "FAILURE",
            "detailsUrl": "https://github.com/o/r/actions/runs/98765/job/12",
        }
    ]

    assert CheckFailureMapper().get_failures(checks)[0].run_id == "98765"


def test_a_check_without_a_run_link_has_no_run_id():
    checks = [{"name": "tests", "conclusion": "FAILURE", "detailsUrl": "https://x/y"}]

    assert CheckFailureMapper().get_failures(checks)[0].run_id == ""


def test_a_check_still_running_leaves_the_verdict_unsettled() -> None:
    rollup = [
        {"name": "test", "conclusion": "SUCCESS"},
        {"name": "lint", "status": "IN_PROGRESS", "conclusion": ""},
    ]

    assert CheckFailureMapper().get_settled(rollup) is False


def test_every_check_finished_settles_the_verdict() -> None:
    rollup = [{"name": "test", "conclusion": "SUCCESS"}]

    assert CheckFailureMapper().get_settled(rollup) is True


def test_a_pull_request_with_no_checks_is_settled() -> None:
    assert CheckFailureMapper().get_settled([]) is True


@pytest.mark.parametrize(
    ("state", "target_url", "run_id"),
    [
        ("FAILURE", "https://github.com/o/r/actions/runs/98765/job/12", "98765"),
        ("ERROR", "https://ci.example.com/build/12", ""),
    ],
)
def test_get_failures_returns_commit_status_failures(
    state: str, target_url: str, run_id: str
) -> None:
    checks = [{"context": "jenkins", "state": state, "targetUrl": target_url}]
    mapper = CheckFailureMapper()

    failures = mapper.get_failures(checks)

    assert len(failures) == 1

    assert failures[0].name == "jenkins"
    assert failures[0].conclusion == state
    assert failures[0].run_id == run_id


@pytest.mark.parametrize(
    ("state", "settled"),
    [
        ("FAILURE", True),
        ("ERROR", True),
        ("SUCCESS", True),
        ("PENDING", False),
        ("EXPECTED", False),
    ],
)
def test_get_settled_returns_whether_commit_statuses_have_finished(
    state: str, settled: bool
) -> None:
    checks = [{"context": "jenkins", "state": state}]
    mapper = CheckFailureMapper()

    checks_settled = mapper.get_settled(checks)

    assert checks_settled is settled


def test_get_failures_returns_failures_from_check_runs_and_commit_statuses() -> None:
    checks = [
        {"name": "tests", "conclusion": "FAILURE"},
        {"context": "jenkins", "state": "ERROR"},
        {"name": "lint", "conclusion": "SUCCESS"},
        {"context": "circleci", "state": "SUCCESS"},
        {"context": "buildkite", "state": "PENDING"},
    ]

    mapper = CheckFailureMapper()

    failures = mapper.get_failures(checks)

    assert [failure.name for failure in failures] == ["tests", "jenkins"]


@pytest.mark.parametrize(
    ("conclusion", "state", "settled"),
    [
        ("", "SUCCESS", False),
        ("SUCCESS", "PENDING", False),
        ("SUCCESS", "FAILURE", True),
    ],
)
def test_get_settled_returns_whether_check_runs_and_commit_statuses_have_finished(
    conclusion: str, state: str, settled: bool
) -> None:
    checks = [
        {"name": "tests", "conclusion": conclusion},
        {"context": "jenkins", "state": state},
    ]

    mapper = CheckFailureMapper()

    checks_settled = mapper.get_settled(checks)

    assert checks_settled is settled
