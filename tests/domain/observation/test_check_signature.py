import pytest
from virgo_agentic_dag.domain.observation.check_failure import CheckFailure
from virgo_agentic_dag.domain.observation.check_signature import CheckSignature

pytestmark = pytest.mark.unit


def test_the_same_commit_and_checks_are_the_same_failure():
    failures = (CheckFailure(name="unit", conclusion="FAILURE"),)

    assert CheckSignature.of("abc", failures) == CheckSignature.of("abc", failures)


def test_a_new_commit_is_a_different_failure():
    failures = (CheckFailure(name="unit", conclusion="FAILURE"),)

    assert CheckSignature.of("abc", failures) != CheckSignature.of("def", failures)


def test_a_different_failing_check_is_a_different_failure():
    unit = (CheckFailure(name="unit", conclusion="FAILURE"),)
    lint = (CheckFailure(name="lint", conclusion="FAILURE"),)

    assert CheckSignature.of("abc", unit) != CheckSignature.of("abc", lint)


def test_check_order_does_not_change_the_failure():
    unit = CheckFailure(name="unit", conclusion="FAILURE")
    lint = CheckFailure(name="lint", conclusion="FAILURE")

    assert CheckSignature.of("abc", (unit, lint)) == CheckSignature.of(
        "abc", (lint, unit)
    )


def test_no_failures_is_the_empty_signature():
    assert CheckSignature.of("abc", ()) == CheckSignature()
