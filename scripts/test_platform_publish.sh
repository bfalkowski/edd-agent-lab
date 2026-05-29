#!/usr/bin/env bash
# Smoke test: lab publish-run -> platform /v1/integrations/lab/publish -> ExperimentRun.
#
# Prerequisites:
#   Platform API running with lab ingest (eval-driven-design-platform on :8000).
#
# Usage:
#   ./scripts/test_platform_publish.sh
#   EDD_API_BASE_URL=http://127.0.0.1:8001 ./scripts/test_platform_publish.sh

set -euo pipefail

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${LAB_ROOT}"

API_BASE="${EDD_API_BASE_URL:-http://127.0.0.1:8000}"
TENANT_ID="${EDD_TENANT_ID:-tenant-a}"
AGENT="${LAB_TEST_AGENT:-customer-solution}"
VERSION="${LAB_TEST_VERSION:-v1-discovery-graph}"
RUN_RECORD="${LAB_ROOT}/lab-runs/customer_solution_agent/v1-discovery-graph/run-record.json"

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
platform_run_id="$(echo "${publish_output}" | awk '/Platform run id:/ {print $NF}')"
[[ -n "${platform_run_id}" ]] || fail "Could not parse platform_run_id from publish output"
pass "Published run: ${platform_run_id}"

step "Verify ExperimentRun on platform"
run_json="$(curl -s "${API_BASE}/v1/experiment-runs/${platform_run_id}?tenant_id=${TENANT_ID}")"
run_status="$(json_field "${run_json}" status)"
candidate="$(json_field "${run_json}" candidate_version)"
[[ "${candidate}" == "v1-discovery-graph" ]] || fail "Unexpected candidate_version: ${candidate}"
pass "ExperimentRun status=${run_status} candidate=${candidate}"

step "Verify publish envelope + gate fields (httpx round-trip)"
EDD_API_BASE_URL="${API_BASE}" \
EDD_TENANT_ID="${TENANT_ID}" \
EDD_EVAL_SPEC_ID="${spec_id}" \
.venv/bin/python - <<'PY'
import json
import os
import sys
from pathlib import Path

import httpx

from edd_agent_lab.integrations.publish import build_publish_envelope

run_record = Path("lab-runs/customer_solution_agent/v1-discovery-graph/run-record.json")
record = json.loads(run_record.read_text())
envelope = build_publish_envelope(record)
envelope["tenant_id"] = os.environ["EDD_TENANT_ID"]

if envelope.get("eval_spec_id") != os.environ["EDD_EVAL_SPEC_ID"]:
    sys.exit("eval_spec_id missing from built envelope")

api = os.environ["EDD_API_BASE_URL"].rstrip("/")
response = httpx.post(f"{api}/v1/integrations/lab/publish", json=envelope, timeout=10.0)
if response.status_code != 201:
    sys.exit(f"publish failed: {response.status_code} {response.text}")

body = response.json()
gate_status = body.get("gate_status")
if gate_status not in {"pass", "fail", "insufficient_evidence"}:
    sys.exit(f"unexpected gate_status: {gate_status!r}")

print(f"gate_status={gate_status}")
print(f"gate_explanation={body.get('gate_explanation')}")
PY
pass "Envelope + gate response OK"

printf '\n\033[32mAll platform publish smoke checks passed.\033[0m\n'
