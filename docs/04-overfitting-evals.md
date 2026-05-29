# Overfitting Evals

The `overfitting` suite runs a base scenario plus domain-swap variants. Risk thresholds:

- **high**: base passes and variant pass rate &lt; 0.50
- **medium**: base passes and variant pass rate in [0.50, 0.80)
- **low**: base passes and variant pass rate ≥ 0.80

Implementation:

- Risk thresholds: `src/edd_agent_lab/evals/overfitting.py`
- Suite execution: `src/edd_agent_lab/evals/runner.py`
- Variant scoring uses scenario `expected_themes` via `score_discovery_invariant()` in `src/edd_agent_lab/evals/scoring.py`

Refresh committed lab artifacts:

```bash
python scripts/refresh_overfitting_lab_artifacts.py
```
