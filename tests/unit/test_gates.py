from quant_spec.validation.gates import evaluate_gates
from tests.unit.helpers import result_for_fixture


def test_fail_fixture_fails_sharpe_oos_and_skips_remaining_gates() -> None:
    report = evaluate_gates(result_for_fixture("HYP-001-intraday-fail-demo"))

    assert report.summary == "FAIL"
    assert report.first_failed == "G2_sharpe_oos"
    assert [gate.status for gate in report.gates] == [
        "PASS",
        "FAIL",
        "SKIPPED",
        "SKIPPED",
        "SKIPPED",
    ]


def test_pass_fixture_passes_all_gates() -> None:
    report = evaluate_gates(result_for_fixture("HYP-002-intraday-pass-demo"))

    assert report.summary == "PASS"
    assert report.first_failed is None
    assert {gate.status for gate in report.gates} == {"PASS"}


def test_nan_metric_fails_corresponding_gate() -> None:
    result = result_for_fixture("HYP-002-intraday-pass-demo")
    result.metrics.outsample.sharpe = float("nan")

    report = evaluate_gates(result)

    assert report.summary == "FAIL"
    assert report.first_failed == "G2_sharpe_oos"
    assert report.gates[1].metric is None


def test_inf_metric_fails_corresponding_gate() -> None:
    result = result_for_fixture("HYP-002-intraday-pass-demo")
    result.metrics.outsample.sharpe = float("inf")

    report = evaluate_gates(result)

    assert report.summary == "FAIL"
    assert report.first_failed == "G2_sharpe_oos"
    assert report.gates[1].metric is None
    assert [gate.status for gate in report.gates[2:]] == [
        "SKIPPED",
        "SKIPPED",
        "SKIPPED",
    ]


def test_missing_early_metric_fails_corresponding_gate() -> None:
    result = result_for_fixture("HYP-002-intraday-pass-demo")
    delattr(result.metrics.outsample, "sharpe")

    report = evaluate_gates(result)

    assert report.summary == "FAIL"
    assert report.first_failed == "G2_sharpe_oos"
    assert report.gates[1].metric is None
    assert [gate.status for gate in report.gates] == [
        "PASS",
        "FAIL",
        "SKIPPED",
        "SKIPPED",
        "SKIPPED",
    ]


def test_missing_later_metric_fails_corresponding_gate() -> None:
    result = result_for_fixture("HYP-002-intraday-pass-demo")
    delattr(result.metrics.outsample, "win_rate")

    report = evaluate_gates(result)

    assert report.summary == "FAIL"
    assert report.first_failed == "G3_winrate_oos"
    assert report.gates[2].metric is None
    assert [gate.status for gate in report.gates] == [
        "PASS",
        "PASS",
        "FAIL",
        "SKIPPED",
        "SKIPPED",
    ]


def test_gate_hash_is_deterministic() -> None:
    result = result_for_fixture("HYP-002-intraday-pass-demo")

    assert evaluate_gates(result).gates_hash == evaluate_gates(result).gates_hash
