from pathlib import Path

from typer.testing import CliRunner

from quant_spec.cli import app

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[2]


def test_cli_run_pass_demo(tmp_path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            app,
            [
                "run",
                str(REPO_ROOT / "examples/HYP-002-intraday-pass-demo.yaml"),
                "--llm-mode",
                "fixture",
            ],
        )

        assert result.exit_code == 0
        assert "CANDIDATE_FOR_REVIEW" in result.output
        assert Path("hypotheses/HYP-002-intraday-pass-demo/decision.md").exists()


def test_cli_run_fail_demo_returns_gate_exit_code(tmp_path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            app,
            [
                "run",
                str(REPO_ROOT / "examples/HYP-001-intraday-fail-demo.yaml"),
                "--llm-mode",
                "fixture",
            ],
        )

        assert result.exit_code == 2
        assert "CLOSED_BY_GATE" in result.output
        assert Path("hypotheses/HYP-001-intraday-fail-demo/decision.md").exists()
