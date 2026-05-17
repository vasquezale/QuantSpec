from quant_spec.validation.gates import evaluate_gates
from tests.unit.helpers import result_for_fixture


def test_canonical_fixture_outcomes_are_pass_and_fail() -> None:
    fail_report = evaluate_gates(result_for_fixture("HYP-001-intraday-fail-demo"))
    pass_report = evaluate_gates(result_for_fixture("HYP-002-intraday-pass-demo"))

    assert fail_report.summary == "FAIL"
    assert pass_report.summary == "PASS"
