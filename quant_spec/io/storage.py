"""Filesystem storage and canonical hashing utilities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

RUNTIME_HASH_EXCLUDE_FIELDS = frozenset(
    {
        "decided_at",
        "executed_at",
        "hostname",
        "latency_ms",
        "log_file",
        "output_path",
        "gates_hash",
        "report_hash",
        "result_hash",
    }
)


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, Path):
        return obj.as_posix()
    return obj


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize an object using the project canonical JSON format."""

    return json.dumps(
        _to_jsonable(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(obj: Any) -> str:
    """Return a sha256 digest over canonical JSON."""

    return f"sha256:{hashlib.sha256(canonical_json_bytes(obj)).hexdigest()}"


def stable_projection(obj: Any) -> Any:
    """Drop runtime-only fields before hashing an artifact."""

    jsonable = _to_jsonable(obj)
    if isinstance(jsonable, Mapping):
        return {
            key: stable_projection(value)
            for key, value in jsonable.items()
            if key not in RUNTIME_HASH_EXCLUDE_FIELDS
        }
    if isinstance(jsonable, list):
        return [stable_projection(value) for value in jsonable]
    return jsonable


class ArtifactStorage:
    """Path helper and serializer for hypothesis artifacts."""

    def __init__(self, root: Path | str = ".") -> None:
        self.root = Path(root)
        self.hypotheses_dir = self.root / "hypotheses"

    def hypothesis_dir(self, hypothesis_id: str) -> Path:
        return self.hypotheses_dir / hypothesis_id

    def raw_dir(self, hypothesis_id: str) -> Path:
        return self.hypothesis_dir(hypothesis_id) / "_raw"

    def logs_dir(self, hypothesis_id: str) -> Path:
        return self.hypothesis_dir(hypothesis_id) / "_logs"

    def ensure_layout(self, hypothesis_id: str) -> Path:
        hypothesis_dir = self.hypothesis_dir(hypothesis_id)
        hypothesis_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir(hypothesis_id).mkdir(exist_ok=True)
        self.logs_dir(hypothesis_id).mkdir(exist_ok=True)
        return hypothesis_dir

    def artifact_path(self, hypothesis_id: str, artifact_name: str) -> Path:
        return self.hypothesis_dir(hypothesis_id) / artifact_name

    def write_json(self, hypothesis_id: str, artifact_name: str, payload: Any) -> Path:
        self.ensure_layout(hypothesis_id)
        path = self.artifact_path(hypothesis_id, artifact_name)
        path.write_bytes(canonical_json_bytes(payload) + b"\n")
        return path

    def read_json(self, hypothesis_id: str, artifact_name: str) -> dict[str, Any]:
        path = self.artifact_path(hypothesis_id, artifact_name)
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, hypothesis_id: str, artifact_name: str, content: str) -> Path:
        self.ensure_layout(hypothesis_id)
        path = self.artifact_path(hypothesis_id, artifact_name)
        path.write_text(content, encoding="utf-8", newline="\n")
        return path

    def read_text(self, hypothesis_id: str, artifact_name: str) -> str:
        return self.artifact_path(hypothesis_id, artifact_name).read_text(
            encoding="utf-8"
        )

    def write_raw_json(
        self,
        hypothesis_id: str,
        artifact_name: str,
        payload: Any,
    ) -> Path:
        self.ensure_layout(hypothesis_id)
        path = self.raw_dir(hypothesis_id) / artifact_name
        path.write_bytes(canonical_json_bytes(payload) + b"\n")
        return path

    def hash_file(self, path: Path | str) -> str:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return f"sha256:{digest}"

    def hash_artifact(self, payload: Any) -> str:
        return canonical_sha256(stable_projection(payload))
