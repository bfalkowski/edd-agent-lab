#!/usr/bin/env bash
# Smoke test: lab publish-run -> platform /v1/integrations/runs/publish -> ExperimentRun.
#
# Prerequisites:
#   Platform API running with run ingest (eval-driven-design-platform on :8000).
#
# Usage:
#   ./scripts/test_platform_publish.sh
#   EDD_API_BASE_URL=http://127.0.0.1:8001 ./scripts/test_platform_publish.sh
#   EDD_API_KEY=<jwt> ./scripts/test_platform_publish.sh   # when platform auth is enabled
#   EDD_TOKEN_FILE=/tmp/edd-api.token ./scripts/test_platform_publish.sh
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

resolve_bearer_token_explicit() {
  if [[ -n "${EDD_API_KEY:-}" ]]; then
    printf '%s' "${EDD_API_KEY}"
    return 0
  fi
  local token_file="${EDD_TOKEN_FILE:-${TMPDIR:-/tmp}/edd-api.token}"
  if [[ -f "${token_file}" ]]; then
    tr -d '[:space:]' <"${token_file}"
    return 0
  fi
}

mint_demo_bearer_token() {
  local platform_root="${EDD_PLATFORM_ROOT:-${LAB_ROOT}/../eval-driven-design-platform}"
  if [[ -f "${platform_root}/api/pyproject.toml" ]]; then
    (
      cd "${platform_root}/api"
      uv run python ../scripts/create_demo_jwt.py --tenant-id "${TENANT_ID}" --subject lab-smoke 2>/dev/null
    )
  fi
}

resolve_bearer_token() {
  resolve_bearer_token_explicit || mint_demo_bearer_token || true
}

BEARER_TOKEN="$(resolve_bearer_token_explicit || true)"
AUTH_MODE="none"

step "Check platform health at ${API_BASE}"
health_code="$(curl -s -o /dev/null -w '%{http_code}' "${API_BASE}/v1/health")"
[[ "${health_code}" == "200" ]] || fail "Platform not reachable (HTTP ${health_code}). Start API first."
pass "Platform health OK"

step "Preflight: generic run ingest endpoint is registered"
AUTH_REQUIRED="false"
preflight_code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/v1/integrations/runs/publish" \
  -H 'Content-Type: application/json' \
  -d '{}')"
if [[ "${preflight_code}" == "404" ]]; then
  fail "POST /v1/integrations/runs/publish returned 404 — restart platform API with current code."
fi
if [[ "${preflight_code}" == "401" ]]; then
  AUTH_REQUIRED="true"
  if [[ -z "${BEARER_TOKEN}" ]]; then
    BEARER_TOKEN="$(resolve_bearer_token || true)"
  fi
  if [[ -z "${BEARER_TOKEN}" ]]; then
    fail "Platform requires auth. Set EDD_API_KEY or EDD_TOKEN_FILE (e.g. from ./scripts/local_e2e.sh)."
  fi
  AUTH_MODE="bearer"
  preflight_code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/v1/integrations/runs/publish" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${BEARER_TOKEN}" \
    -d '{}')"
  if [[ "${preflight_code}" == "401" ]]; then
    BEARER_TOKEN="$(resolve_bearer_token || true)"
    [[ -n "${BEARER_TOKEN}" ]] || fail "Bearer token rejected (expired?). Regenerate with platform create_demo_jwt.py"
    preflight_code="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${API_BASE}/v1/integrations/runs/publish" \
      -H 'Content-Type: application/json' \
      -H "Authorization: Bearer ${BEARER_TOKEN}" \
      -d '{}')"
  fi
fi
# When auth is disabled, ignore stray bearer tokens so tenant_id query/body params are sent.
if [[ "${AUTH_REQUIRED}" != "true" ]]; then
  BEARER_TOKEN=""
  AUTH_MODE="none"
fi
[[ "${preflight_code}" == "400" || "${preflight_code}" == "422" ]] \
  || fail "Unexpected preflight status for empty publish body: ${preflight_code}"
pass "Run ingest endpoint reachable (HTTP ${preflight_code}, auth=${AUTH_MODE})"

step "Ensure lab CLI is installed (Python 3.12, non-editable uv sync)"
if ! .venv/bin/python -c "import edd_agent_lab" 2>/dev/null; then
  uv venv --python 3.12
  uv sync --extra dev --extra platform --no-editable
fi
.venv/bin/python -c "import edd_agent_lab" || fail "edd_agent_lab not importable — run: uv sync --extra dev --extra platform --no-editable"
pass "Lab package import OK"

[[ -f "${RUN_RECORD}" ]] || fail "Missing run record: ${RUN_RECORD}"

step "Create platform EvalSpec for tenant ${TENANT_ID}"
spec_payload="{\"tenant_id\":\"${TENANT_ID}\",\"name\":\"Lab publish smoke\",\"rubric\":\"Discovery quality\",\"pass_threshold\":70}"
if [[ -n "${BEARER_TOKEN}" ]]; then
  spec_json="$(curl -s -X POST "${API_BASE}/v1/eval-specs" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer ${BEARER_TOKEN}" \
    -d "${spec_payload}")"
else
  spec_json="$(curl -s -X POST "${API_BASE}/v1/eval-specs" \
    -H 'Content-Type: application/json' \
    -d "${spec_payload}")"
fi
if ! spec_id="$(json_field "${spec_json}" eval_spec_id 2>/dev/null)"; then
  fail "EvalSpec create failed: ${spec_json}"
fi
pass "EvalSpec created: ${spec_id}"

step "Publish lab run-record via edd-lab (${AGENT} ${VERSION})"
publish_output="$(
  EDD_CLIENT_MODE=http \
  EDD_API_BASE_URL="${API_BASE}" \
  EDD_TENANT_ID="${TENANT_ID}" \
  EDD_EVAL_SPEC_ID="${spec_id}" \
  EDD_API_KEY="${BEARER_TOKEN}" \
  .venv/bin/edd-lab publish-run --agent "${AGENT}" --version "${VERSION}" 2>&1
)"
echo "${publish_output}"
echo "${publish_output}" | grep -q "published_http" || fail "Expected published_http status"
echo "${publish_output}" | grep -q "Gate status:" || fail "Expected gate status in CLI output"
platform_run_id="$(echo "${publish_output}" | awk '/Platform run id:/ {print $NF}')"
[[ -n "${platform_run_id}" ]] || fail "Could not parse platform_run_id from publish output"
pass "Published run: ${platform_run_id}"

if [[ -n "${BEARER_TOKEN}" ]]; then
  PLATFORM_ROOT="${EDD_PLATFORM_ROOT:-${LAB_ROOT}/../eval-driven-design-platform}"
  TENANT_B_TOKEN="$(
    cd "${PLATFORM_ROOT}/api" && uv run python ../scripts/create_demo_jwt.py --tenant-id tenant-b --subject lab-smoke-b 2>/dev/null
  )"
else
  TENANT_B_TOKEN=""
fi

step "Verify ingest metadata, filters, legacy alias, pass gate, tenant isolation"
SMOKE_PLATFORM_RUN_ID="${platform_run_id}" \
SMOKE_RUN_RECORD="${RUN_RECORD}" \
SMOKE_LAB_ROOT="${LAB_ROOT}" \
SMOKE_SKIP_LEGACY="${SMOKE_SKIP_LEGACY:-}" \
SMOKE_BEARER_TOKEN="${BEARER_TOKEN}" \
SMOKE_TENANT_B_TOKEN="${TENANT_B_TOKEN}" \
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
bearer_token = os.environ.get("SMOKE_BEARER_TOKEN", "").strip()
tenant_b_token = os.environ.get("SMOKE_TENANT_B_TOKEN", "").strip()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def auth_headers() -> dict[str, str]:
    if bearer_token:
        return {"Authorization": f"Bearer {bearer_token}"}
    return {}


def tenant_params(*, tenant: str | None = None) -> dict[str, str]:
    if bearer_token:
        return {}
    return {"tenant_id": tenant or tenant_id}


def get_run(run_id: str, *, tenant: str | None = None) -> dict:
    response = httpx.get(
        f"{api}/v1/experiment-runs/{run_id}",
        params=tenant_params(tenant=tenant),
        headers=auth_headers(),
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
    params={"ingest_source": "edd-agent-lab", "limit": 50, **tenant_params()},
    headers=auth_headers(),
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

response = httpx.post(
    f"{api}/v1/integrations/runs/publish",
    json=envelope,
    headers=auth_headers(),
    timeout=10.0,
)
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
pass_response = httpx.post(
    f"{api}/v1/integrations/runs/publish",
    json=pass_envelope,
    headers=auth_headers(),
    timeout=10.0,
)
if pass_response.status_code != 201:
    fail(f"pass-gate publish failed: {pass_response.status_code} {pass_response.text}")
pass_body = pass_response.json()
if pass_body.get("gate_status") != "pass":
    fail(f"expected pass gate, got {pass_body.get('gate_status')!r}")
pass_run = get_run(str(pass_body["platform_run_id"]))
if pass_run.get("status") != "completed":
    fail(f"expected completed status for pass gate run, got {pass_run.get('status')!r}")
print(f"pass gate run={pass_body['platform_run_id']}")

# --- structured failure evidence (reference scenario) ---
platform_root = Path(os.environ.get("EDD_PLATFORM_ROOT", "")).expanduser()
failure_yaml = platform_root / "examples" / "customer_escalation_triage" / "failure-packet-v0.yaml"
if failure_yaml.is_file():
    import yaml

    failure_doc = yaml.safe_load(failure_yaml.read_text(encoding="utf-8"))
    evidence_run_id = f"smoke-evidence-fail-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    evidence_envelope = {
        "schema_version": PUBLISH_SCHEMA_VERSION,
        "source": "edd-agent-lab",
        "run_id": evidence_run_id,
        "tenant_id": tenant_id,
        "agent": "customer_escalation_triage",
        "agent_version": "v0-baseline",
        "suite": "escalation_triage",
        "eval_spec_id": spec_id,
        "scenario_ids": ["escalation-latency-quality-regression-001"],
        "eval_summary": {"overall_score": 0.95},
        "failure_packet": failure_doc["failure_packet"],
        "outputs": {},
        "artifact_paths": {},
    }
    evidence_publish = httpx.post(
        f"{api}/v1/integrations/runs/publish",
        json=evidence_envelope,
        headers=auth_headers(),
        timeout=10.0,
    )
    if evidence_publish.status_code != 201:
        fail(f"structured failure publish failed: {evidence_publish.status_code} {evidence_publish.text}")
    evidence_body = evidence_publish.json()
    if evidence_body.get("gate_status") != "fail":
        fail(f"expected fail gate for structured failure, got {evidence_body.get('gate_status')!r}")
    gate_explanation = str(evidence_body.get("gate_explanation") or "")
    if "separate_facts_from_hypotheses" not in gate_explanation:
        fail("gate_explanation missing failed behavior rule separate_facts_from_hypotheses")

    evidence_run_id_platform = str(evidence_body["platform_run_id"])
    evidence_get = httpx.get(
        f"{api}/v1/experiment-runs/{evidence_run_id_platform}/evidence",
        params=tenant_params(),
        headers=auth_headers(),
        timeout=10.0,
    )
    if evidence_get.status_code != 200:
        fail(f"GET evidence failed: {evidence_get.status_code} {evidence_get.text}")
    evidence_payload = evidence_get.json()
    failure_packet = evidence_payload.get("failure_packet") or {}
    if failure_packet.get("id") != "fp-v0-unsupported-root-cause":
        fail(f"unexpected failure_packet.id: {failure_packet.get('id')!r}")
    if failure_packet.get("failed_behavior_rule_id") != "separate_facts_from_hypotheses":
        fail(
            "unexpected failed_behavior_rule_id: "
            f"{failure_packet.get('failed_behavior_rule_id')!r}"
        )
    print(f"structured failure evidence ok run={evidence_run_id_platform}")
else:
    print(f"structured failure evidence skipped (missing {failure_yaml})")

# --- v2 escalation reference publish (fix plan + comparison + gate) ---
from edd_agent_lab.integrations.publish import PUBLISH_SCHEMA_VERSION_V2

v2_fixture = Path(os.environ["SMOKE_LAB_ROOT"]) / "tests" / "fixtures" / "publish" / "evidence-run-record-v1-pass.json"
if v2_fixture.is_file():
    v2_record = json.loads(v2_fixture.read_text(encoding="utf-8"))
    try:
        from edd_agent_lab.integrations.reference_publish import load_reference_publish_artifacts

        v2_record["trace_links"] = load_reference_publish_artifacts()["trace_links_v1"]
    except FileNotFoundError:
        pass
    v2_record["run_id"] = f"smoke-evidence-v2-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    v2_envelope = build_publish_envelope(v2_record)
    v2_envelope["tenant_id"] = tenant_id
    v2_envelope["eval_spec_id"] = spec_id
    assert v2_envelope["schema_version"] == PUBLISH_SCHEMA_VERSION_V2
    v2_publish = httpx.post(
        f"{api}/v1/integrations/runs/publish",
        json=v2_envelope,
        headers=auth_headers(),
        timeout=10.0,
    )
    if v2_publish.status_code != 201:
        fail(f"v2 escalation publish failed: {v2_publish.status_code} {v2_publish.text}")
    v2_body = v2_publish.json()
    if v2_body.get("gate_status") != "pass":
        fail(f"expected pass gate for v2 escalation bundle, got {v2_body.get('gate_status')!r}")
    v2_run_id = str(v2_body["platform_run_id"])
    v2_evidence = httpx.get(
        f"{api}/v1/experiment-runs/{v2_run_id}/evidence",
        params=tenant_params(),
        headers=auth_headers(),
        timeout=10.0,
    )
    if v2_evidence.status_code != 200:
        fail(f"GET v2 evidence failed: {v2_evidence.status_code} {v2_evidence.text}")
    v2_payload = v2_evidence.json()
    if (v2_payload.get("fix_plan") or {}).get("id") != "fix-v1-evidence-first-triage":
        fail(f"unexpected fix_plan.id: {(v2_payload.get('fix_plan') or {}).get('id')!r}")
    if (v2_payload.get("comparison") or {}).get("id") != "compare-v0-v1-escalation-triage":
        fail(f"unexpected comparison.id: {(v2_payload.get('comparison') or {}).get('id')!r}")
    if (v2_payload.get("gate_result") or {}).get("overall_status") != "pass_for_demo_not_production":
        fail(
            "unexpected gate_result.overall_status: "
            f"{(v2_payload.get('gate_result') or {}).get('overall_status')!r}"
        )
    trace_links = v2_payload.get("trace_links") or []
    if not trace_links or trace_links[0].get("external_trace_id") != "trace_v1_def456":
        fail(f"unexpected trace_links on v2 evidence: {trace_links!r}")
    print(f"v2 escalation evidence ok run={v2_run_id}")
else:
    print(f"v2 escalation evidence skipped (missing {v2_fixture})")

# --- unified gate API ---
fail_gate = httpx.get(
    f"{api}/v1/experiment-runs/{platform_run_id}/gate",
    params=tenant_params(),
    headers=auth_headers(),
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
    params=tenant_params(),
    headers=auth_headers(),
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
        headers=auth_headers(),
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
if bearer_token and tenant_b_token:
    cross_tenant = httpx.get(
        f"{api}/v1/experiment-runs/{platform_run_id}",
        headers={"Authorization": f"Bearer {tenant_b_token}"},
        timeout=10.0,
    )
elif bearer_token:
    print("tenant isolation skipped (could not mint tenant-b token)")
    cross_tenant = None
else:
    cross_tenant = httpx.get(
        f"{api}/v1/experiment-runs/{platform_run_id}",
        params={"tenant_id": "tenant-b"},
        headers=auth_headers(),
        timeout=10.0,
    )
if cross_tenant is not None:
    if cross_tenant.status_code != 404:
        fail(f"expected 404 for cross-tenant GET, got {cross_tenant.status_code}")
    print("tenant isolation ok")
PY
pass "Ingest metadata, filters, pass gate, legacy alias, tenant isolation OK"

printf '\n\033[32mAll platform publish smoke checks passed.\033[0m\n'
