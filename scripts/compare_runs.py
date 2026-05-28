#!/usr/bin/env python3
"""Thin wrapper — prefer `edd-lab compare-runs` (Milestone 3+)."""

import sys

print("Use: edd-lab compare-runs --before <path> --after <path>", file=sys.stderr)
sys.exit(2)
