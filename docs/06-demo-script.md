# Demo Script

## Milestone 1 (current)

```bash
cd edd-agent-lab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
edd-lab --help
edd-lab list-scenarios --agent customer-solution
edd-lab list-evals --agent customer-solution
pytest
```

## Milestone 2+

```bash
edd-lab run-agent --agent customer-solution --scenario healthcare_documentation
edd-lab run-evals --agent customer-solution --suite discovery_quality
```
