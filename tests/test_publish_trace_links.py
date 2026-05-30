from __future__ import annotations

import json
from pathlib import Path

from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION, build_publish_envelope

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "publish"


def _load_run_record(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_build_publish_envelope_includes_trace_links_for_v0_failure() -> None:
    record = _load_run_record("evidence-run-record-v0-fail.json")
    envelope = build_publish_envelope(record)

    assert envelope["schema_version"] == PUBLISH_SCHEMA_VERSION
    assert len(envelope["trace_links"]) == 1
    assert envelope["trace_links"][0]["id"] == "trace-link-v0-001"
    assert envelope["trace_links"][0]["external_trace_id"] == "trace_v0_abc123"
