import json
import os
from pathlib import Path

import pytest

from quant_spec.io.storage import ArtifactStorage
from quant_spec.pipeline.runner import (
    stage_backtest,
    stage_gates,
    stage_report,
    stage_spec,
    stage_validate_brief,
)
from quant_spec.settings import get_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_LIVE = os.getenv("RUN_LIVE_TESTS") == "1" and bool(get_settings().anthropic_api_key)

pytestmark = pytest.mark.skipif(
    not RUN_LIVE,
    reason="set RUN_LIVE_TESTS=1 and ANTHROPIC_API_KEY to run live Claude tests",
)


def test_live_claude_spec_and_report_persist_audit_payloads(tmp_path) -> None:
    get_settings.cache_clear()
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        REPO_ROOT / "examples/HYP-001-intraday-fail-demo.yaml",
        storage,
    )

    spec_path = stage_spec(brief, storage, "live")
    result = stage_backtest(brief, storage)
    stage_gates(result, storage)
    report_path = stage_report(brief, storage, "live")

    raw_dir = storage.raw_dir(brief.id)
    spec_payload = json.loads(
        raw_dir.joinpath("spec_response.json").read_text(encoding="utf-8")
    )
    report_payload = json.loads(
        raw_dir.joinpath("report_response.json").read_text(encoding="utf-8")
    )
    usage_payload = json.loads(
        raw_dir.joinpath("usage.json").read_text(encoding="utf-8")
    )

    assert spec_path.exists()
    assert report_path.exists()
    assert spec_payload["model"]
    assert spec_payload["usage"]
    assert spec_payload["latency_ms"] is not None
    assert spec_payload["raw_response"]
    assert report_payload["model"]
    assert report_payload["usage"]
    assert {record["stage"] for record in usage_payload["records"]} == {
        "spec",
        "report",
    }

    get_settings.cache_clear()
