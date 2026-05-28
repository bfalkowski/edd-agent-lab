# Overfitting Evals

The `overfitting` suite runs a base scenario plus domain-swap variants. Risk thresholds:

- **high**: base passes and variant pass rate &lt; 0.50
- **medium**: base passes and variant pass rate in [0.50, 0.80)
- **low**: base passes and variant pass rate ≥ 0.80

Implementation: Milestone 5 (`src/edd_agent_lab/evals/overfitting.py`).
