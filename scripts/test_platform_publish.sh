#!/usr/bin/env bash
# Smoke test: lab publish-run -> platform /v1/integrations/runs/publish -> ExperimentRun.
#
# Prerequisites:
#   Platform API running with run ingest (eval-driven-design-platform on :8000).
#
# Usage:
#   ./scripts/test_platform_publish.sh
#   EDD_API_BASE_URL=http://127.0.0.1:8001 ./scripts/test_platform_publish.sh
#   LAB_RUN_RECORD=/path/to/run-record.json ./scripts/test_platform_publish.sh
#   SMOKE_SKIP_LEGACY=1 ./scripts/test_platform_publish.sh

set -euo pipefail

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${LAB_ROOT}"

API_BASE="${EDD_API_BASE_URL:-http://127.0.0.1:8000}"
TENANT_ID="${EDD_TENANT_ID:-tenant-a}"
AGENT="${LAB_TEST_AGENT:-customer-solution}"
VERSION="${LAB_TEST_VERSION:-v1-discovery-graph}"
RUN_RECORD="${LAB_RUN_RECORD:-${LAB_ROOT}/lab-runs/customer_solution_agent/v1-discovery-graph/run-record.json}"

pass() { printf '\033[32m✓ %s\033[0m\n' "$*"; }
fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
step() { printf '\n→ %s\n' "$*"; }

json_field() {
  local json="$1"
  local field="$2"
  python3 -c "import json,sys; print(json.load(sys.stdin)['${field}'])" <<<"${json}"
}

step "Check platform health at ${API_BASE}"
health_code="$(curl -s -o /dev/null -w '%{http_code}' "${API_BASE}/v1/health")"
[[ "${health_code}" == "200" ]] || fail "Platform not reachable (HTTP ${health_code}). Start API first."
pass "Platform health OK"

step "Preflight: generic run ingest endpoint is registered"
preflight_code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/v1/integrations/runs/publish" \
  -H 'Content-Type: application/json' \
  -d '{}')"
if [[ "${preflight_code}" == "404" ]]; then
  fail "POST /v1/integrations/runs/publish returned 404 — restart platform API with current code."
fi
[[ "${preflight_code}" == "400" || "${preflight_code}" == "422" ]] \
  || fail "Unexpected preflight status for empty publish body: ${preflight_code}"
pass "Run ingest endpoint reachable (HTTP ${preflight_code})"

step "Ensure lab CLI is installed (Python 3.12, non-editable uv sync)"
if ! .venv/bin/python -c "import edd_agent_lab" 2>/dev/null; then
  uv venv --python 3.12
  uv sync --extra dev --extra platform --no-editable
fi
.venv/bin/python -c "import edd_agent_lab" || fail "edd_agent_lab not importable — run: uv sync --extra dev --extra platform --no-editable"
pass "Lab package import OK"

[[ -f "${RUN_RECORD}" ]] || fail "Missing run record: ${RUN_RECORD}"

step "Create platform EvalSpec for tenant ${TENANT_ID}"
spec_json="$(curl -s -X POST "${API_BASE}/v1/eval-specs" \
  -H 'Content-Type: application/json' \
  -d "{\"tenant_id\":\"${TENANT_ID}\",\"name\":\"Lab publish smoke\",\"rubric\":\"Discovery quality\",\"pass_threshold\":70}")"
spec_id="$(json_field "${spec_json}" eval_spec_id)"
pass "EvalSpec created: ${spec_id}"

step "Publish lab run-record via edd-lab (${AGENT} ${VERSION})"
publish_output="$(
  EDD_CLIENT_MODE=http \
  EDD_API_BASE_URL="${API_BASE}" \
  EDD_TENANT_ID="${TENANT_ID}" \
  EDD_EVAL_SPEC_ID="${spec_id}" \
  .venv/bin/edd-lab publish-run --agent "${AGENT}" --version "${VERSION}" 2>&1
)"
echo "${publish_output}"
echo "${publish_output}" | grep -q "published_http" || fail "Expected published_http status"
echo "${publish_output}" | grep -q "Gate status:" || fail "Expected gate status in CLI output"
platform_run_id="$(echo "${publish_output}" | awk '/Platform run id:/ {print $NF}')"
[[ -n "${platform_run_id}" ]] || fail "Could not parse platform_run_id from publish output"
pass "Published run: ${platform_run_id}"

step "Verify ingest metadata, filters, legacy alias, pass gate, tenant isolation"
SMOKE_PLATFORM_RUN_ID="${platform_run_id}" \
SMOKE_RUN_RECORD="${RUN_RECORD}" \
SMOKE_SKIP_LEGACY="${SMOKE_SKIP_LEGACY:-}" \
EDD_API_BASE_URL="${API_BASE}" \
EDD_TENANT_ID="${TENANT_ID}" \
EDD_EVAL_SPEC_ID="${spec_id}" \
.venv/bin/python - <<'PY'
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx

from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION, build_publish_envelope

api = os.environ["EDD_API_BASE_URL"].rstrip("/")
tenant_id = os.environ["EDD_TENANT_ID"]
spec_id = os.environ["EDD_EVAL_SPEC_ID"]
platform_run_id = os.environ["SMOKE_PLATFORM_RUN_ID"]
run_record_path = Path(os.environ["SMOKE_RUN_RECORD"])
skip_legacy = os.environ.get("SMOKE_SKIP_LEGACY", "").strip().lower() in {"1", "true", "yes"}


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def get_run(run_id: str, *, tenant: str | None = None) -> dict:
    response = httpx.get(
        f"{api}/v1/experiment-runs/{run_id}",
        params={"tenant_id": tenant or tenant_id},
        timeout=10.0,
    )
    if response.status_code != 200:
        fail(f"GET experiment run failed: {response.status_code} {response.text}")
    return response.json()


# --- persisted ingest on GET ---
run = get_run(platform_run_id)
ingest = run.get("ingest")
if not ingest:
    fail("experiment run missing ingest metadata")
for field in ("source", "external_run_id", "subject_id", "suite_id", "gate_status"):
    if not ingest.get(field):
        fail(f"ingest.{field} missing on GET experiment run")
if ingest["source"] != "edd-agent-lab":
    fail(f"unexpected ingest.source: {ingest['source']!r}")
if run.get("candidate_version") != "v1-discovery-graph":
    fail(f"unexpected candidate_version: {run.get('candidate_version')!r}")
print(f"ingest.source={ingest['source']} external_run_id={ingest['external_run_id']}")
print(f"ingest.gate_status={ingest['gate_status']}")

# --- ingest_source list filter ---
listed = httpx.get(
    f"{api}/v1/experiment-runs",
    params={"tenant_id": tenant_id, "ingest_source": "edd-agent-lab", "limit": 50},
    timeout=10.0,
)
if listed.status_code != 200:
    fail(f"list experiment runs failed: {listed.status_code} {listed.text}")
run_ids = {item["experiment_run_id"] for item in listed.json().get("experiment_runs", [])}
if platform_run_id not in run_ids:
    fail("published run not returned by ingest_source=edd-agent-lab filter")
print(f"ingest_source filter includes platform run ({len(run_ids)} lab run(s))")

# --- fixture envelope round-trip (failure gate expected) ---
record = json.loads(run_record_path.read_text())
envelope = build_publish_envelope(record)
envelope["tenant_id"] = tenant_id
envelope["eval_spec_id"] = spec_id
if envelope.get("eval_spec_id") != spec_id:
    fail("eval_spec_id missing from built envelope")

response = httpx.post(f"{api}/v1/integrations/runs/publish", json=envelope, timeout=10.0)
if response.status_code != 201:
    fail(f"publish failed: {response.status_code} {response.text}")
body = response.json()
gate_status = body.get("gate_status")
if gate_status not in {"pass", "fail", "insufficient_evidence"}:
    fail(f"unexpected gate_status: {gate_status!r}")
if body.get("external_run_id") != envelope["run_id"]:
    fail("external_run_id mismatch in publish response")
print(f"fixture gate_status={gate_status}")

# --- passing gate with synthetic envelope ---
pass_run_id = f"smoke-pass-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
pass_envelope = {
    "schema_version": PUBLISH_SCHEMA_VERSION,
    "source": "edd-agent-lab",
    "run_id": pass_run_id,
    "agent": "customer_solution_agent",
    "agent_version": "v1-discovery-graph",
    "suite": "smoke-pass",
    "tenant_id": tenant_id,
    "eval_spec_id": spec_id,
    "scenario_ids": ["healthcare_documentation"],
    "eval_summary": {"overall_score": 0.95},
    "failure_packet": None,
    "outputs": {},
    "artifact_paths": {},
}
pass_response = httpx.post(f"{api}/v1/integrations/runs/publish", json=pass_envelope, timeout=10.0)
if pass_response.status_code != 201:
    fail(f"pass-gate publish failed: {pass_response.status_code} {pass_response.text}")
pass_body = pass_response.json()
if pass_body.get("gate_status") != "pass":
    fail(f"expected pass gate, got {pass_body.get('gate_status')!r}")
pass_run = get_run(str(pass_body["platform_run_id"]))
if pass_run.get("status") != "completed":
    fail(f"expected completed status for pass gate run, got {pass_run.get('status')!r}")
print(f"pass gate run={pass_body['platform_run_id']}")

# --- unified gate API ---
fail_gate = httpx.get(
    f"{api}/v1/experiment-runs/{platform_run_id}/gate",
    params={"tenant_id": tenant_id},
    timeout=10.0,
)
if fail_gate.status_code != 200:
    fail(f"gate GET failed for fixture run: {fail_gate.status_code} {fail_gate.text}")
fail_gate_body = fail_gate.json()
if fail_gate_body.get("evaluation_source") != "ingest":
    fail(f"expected evaluation_source=ingest, got {fail_gate_body.get('evaluation_source')!r}")
if fail_gate_body.get("gate_status") != "fail":
    fail(f"expected fail gate for fixture run, got {fail_gate_body.get('gate_status')!r}")

pass_gate = httpx.get(
    f"{api}/v1/experiment-runs/{pass_body['platform_run_id']}/gate",
    params={"tenant_id": tenant_id},
    timeout=10.0,
)
if pass_gate.status_code != 200:
    fail(f"gate GET failed for pass run: {pass_gate.status_code} {pass_gate.text}")
pass_gate_body = pass_gate.json()
if pass_gate_body.get("gate_status") != "pass":
    fail(f"expected pass gate API, got {pass_gate_body.get('gate_status')!r}")
print("gate API ok for fail + pass runs")

# --- legacy alias ---
if not skip_legacy:
    legacy_run_id = f"smoke-legacy-{uuid.uuid4().hex[:8]}"
    legacy_envelope = dict(pass_envelope)
    legacy_envelope["run_id"] = legacy_run_id
    legacy_envelope["suite"] = "smoke-legacy"
    legacy_response = httpx.post(
        f"{api}/v1/integrations/lab/publish",
        json=legacy_envelope,
        timeout=10.0,
    )
    if legacy_response.status_code != 201:
        fail(f"legacy publish failed: {legacy_response.status_code} {legacy_response.text}")
    legacy_body = legacy_response.json()
    if legacy_body.get("lab_run_id") != legacy_run_id:
        fail("legacy lab_run_id mismatch")
    if legacy_body.get("external_run_id") != legacy_run_id:
        fail("legacy external_run_id mismatch")
    print(f"legacy alias ok run_id={legacy_run_id}")

# --- tenant isolation ---
cross_tenant = httpx.get(
    f"{api}/v1/experiment-runs/{platform_run_id}",
    params={"tenant_id": "tenant-b"},
    timeout=10.0,
)
if cross_tenant.status_code != 404:
    fail(f"expected 404 for cross-tenant GET, got {cross_tenant.status_code}")
print("tenant isolation ok")
PY
pass "Ingest metadata, filters, pass gate, legacy alias, tenant isolation OK"

printf '\n\033[32mAll platform publish smoke checks passed.\033[0m\n'
