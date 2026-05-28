#!/usr/bin/env python3
"""Thin wrapper — prefer `edd-lab run-agent` (Milestone 2+)."""

import sys

print("Use: edd-lab run-agent --agent customer-solution --scenario <id>", file=sys.stderr)
sys.exit(2)
