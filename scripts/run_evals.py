#!/usr/bin/env python3
"""Thin wrapper — prefer `edd-lab run-evals` (Milestone 3+)."""

import sys

print("Use: edd-lab run-evals --agent customer-solution --suite <suite>", file=sys.stderr)
sys.exit(2)
