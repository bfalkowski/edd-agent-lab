"""Load structured evidence artifacts for platform publish envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

EVIDENCE_FIELDS = ("failure_packet", "fix_plan", "comparison", "gate_result")


def load_evidence_document(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON evidence artifact."""
    file_path = Path(path)
    raw = file_path.read_text(encoding="utf-8")
    if file_path.suffix in {".yaml", ".yml"}:
        loaded = yaml.safe_load(raw)
    else:
        loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        msg = f"Evidence artifact must be a mapping: {file_path}"
        raise ValueError(msg)
    return loaded


def extract_evidence_block(document: dict[str, Any], field: str) -> dict[str, Any] | None:
    if field in document and isinstance(document[field], dict):
        return dict(document[field])
    return document if field == "failure_packet" and "id" in document else None


def resolve_evidence_from_run_record(run_record: dict[str, Any]) -> dict[str, Any]:
    """Collect publish-ready evidence blobs from inline fields and artifact paths."""
    resolved: dict[str, Any] = {}
    artifact_paths = run_record.get("artifact_paths") or {}

    for field in EVIDENCE_FIELDS:
        inline = run_record.get(field)
        if isinstance(inline, dict):
            resolved[field] = inline
            continue

        artifact_ref = artifact_paths.get(field)
        if not artifact_ref:
            continue

        document = load_evidence_document(artifact_ref)
        block = extract_evidence_block(document, field)
        if block is not None:
            resolved[field] = block

    return resolved


def attach_evidence_to_envelope(
    envelope: dict[str, Any],
    run_record: dict[str, Any],
) -> dict[str, Any]:
    """Attach structured evidence sections to a publish envelope."""
    for field, value in resolve_evidence_from_run_record(run_record).items():
        envelope[field] = value
    return envelope
