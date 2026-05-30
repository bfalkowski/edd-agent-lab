#!/usr/bin/env bash
# End-to-end reference demo: mock triage, eval v0/v1, optional platform publish.
#
# Usage:
#   ./scripts/demo_customer_escalation_triage.sh
#   EDD_DEMO_PUBLISH=1 EDD_API_BASE_URL=http://127.0.0.1:8000 ./scripts/demo_customer_escalation_triage.sh

set -euo pipefail

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${LAB_ROOT}"

pass() { printf '\033[32m✓ %s\033[0m\n' "$*"; }
step() { printf '\n→ %s\n' "$*"; }

step "Ensure lab package is importable"
uv sync --extra dev --extra ui --quiet
pass "Dependencies ready"

step "Run reference demo path (triage + eval both versions)"
EDD_DEMO_PUBLISH="${EDD_DEMO_PUBLISH:-}" uv run python -m edd_agent_lab.ui.demo_path
pass "Reference demo path complete"

printf '\n\033[32mCustomer Escalation Triage demo finished.\033[0m\n'
printf 'Open the lab workbench: http://localhost:8502 (edd-lab console)\n'
printf 'Open the platform console: http://localhost:8501\n'
