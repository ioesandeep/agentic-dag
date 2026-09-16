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
