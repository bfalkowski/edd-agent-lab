#!/usr/bin/env python3
"""Thin wrapper — prefer `edd-lab generate-variants` (later milestone)."""

import sys

print("Use: edd-lab generate-variants --scenario <id> --strategies ...", file=sys.stderr)
sys.exit(2)
