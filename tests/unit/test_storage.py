import math
from pathlib import Path

import pytest

from quant_spec.io.storage import (
    ArtifactStorage,
    canonical_json_bytes,
    canonical_sha256,
    stable_projection,
)


def test_canonical_json_is_sorted_and_compact() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_canonical_json_rejects_non_finite_numbers(bad_value: float) -> None:
    with pytest.raises(ValueError, match="Out of range float values"):
        canonical_json_bytes({"metrics": {"sharpe": bad_value}})


def test_hash_is_stable_for_same_canonical_payload() -> None:
    left = {"b": [2, 1], "a": {"x": "demo"}}
    right = {"a": {"x": "demo"}, "b": [2, 1]}

    assert canonical_sha256(left) == canonical_sha256(right)


def test_artifact_hash_excludes_runtime_fields() -> None:
    storage = ArtifactStorage()
    first = {
        "hypothesis_id": "HYP-001-intraday-fail-demo",
        "executed_at": "2026-05-15T00:00:00Z",
        "metrics": {"sharpe": 1.0},
    }
    second = {
        "hypothesis_id": "HYP-001-intraday-fail-demo",
        "executed_at": "2026-05-16T00:00:00Z",
        "metrics": {"sharpe": 1.0},
    }

    assert storage.hash_artifact(first) == storage.hash_artifact(second)


def test_storage_writes_layout_and_json(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)

    path = storage.write_json(
        "HYP-001-intraday-fail-demo",
        "results.json",
        {"ok": True, "value": 1},
    )

    assert path.exists()
    assert storage.raw_dir("HYP-001-intraday-fail-demo").is_dir()
    assert storage.logs_dir("HYP-001-intraday-fail-demo").is_dir()
    assert storage.read_json("HYP-001-intraday-fail-demo", "results.json") == {
        "ok": True,
        "value": 1,
    }


def test_storage_rejects_non_finite_json_artifacts(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)

    with pytest.raises(ValueError, match="Out of range float values"):
        storage.write_json(
            "HYP-001-intraday-fail-demo",
            "results.json",
            {"metrics": {"sharpe": math.inf}},
        )

    assert not storage.artifact_path(
        "HYP-001-intraday-fail-demo",
        "results.json",
    ).exists()


def test_storage_writes_text_raw_json_and_hashes_files(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)

    text_path = storage.write_text("HYP-001-intraday-fail-demo", "notes.md", "hello\n")
    raw_path = storage.write_raw_json(
        "HYP-001-intraday-fail-demo",
        "response.json",
        {"b": 2, "a": 1},
    )

    assert storage.read_text("HYP-001-intraday-fail-demo", "notes.md") == "hello\n"
    assert raw_path.read_text(encoding="utf-8") == '{"a":1,"b":2}\n'
    assert storage.hash_file(text_path).startswith("sha256:")


def test_stable_projection_handles_paths_lists_and_self_hash_fields() -> None:
    payload = {
        "path": Path("/tmp/runtime-only"),
        "items": [{"result_hash": "sha256:" + "0" * 64, "value": 1}],
    }

    assert stable_projection(payload) == {"items": [{"value": 1}]}
