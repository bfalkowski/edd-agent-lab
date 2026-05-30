#!/usr/bin/env bash
set -euo pipefail

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM_ROOT="${EDD_PLATFORM_ROOT:-$(cd "${LAB_ROOT}/../eval-driven-design-platform" 2>/dev/null && pwd || true)}"
TARGET_DIR="${LAB_ROOT}/lab-runs/customer_escalation_triage/target"
SOURCE_DIR="${PLATFORM_ROOT}/examples/customer_escalation_triage"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Platform examples not found at ${SOURCE_DIR}" >&2
  echo "Set EDD_PLATFORM_ROOT to eval-driven-design-platform checkout." >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"
cp "${SOURCE_DIR}/graph-design-v0.yaml" "${TARGET_DIR}/graph-design-v0.yaml"
cp "${SOURCE_DIR}/graph-design-v1.yaml" "${TARGET_DIR}/graph-design.yaml"
echo "Exported graph design artifacts to ${TARGET_DIR}"
