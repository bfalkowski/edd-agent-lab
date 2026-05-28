from pathlib import Path

import yaml

from edd_agent_lab.evals.schemas import EvalSuite, OverfittingEvalSuite
from edd_agent_lab.paths import EVALS_DIR


def _agent_eval_dir(agent_key: str) -> Path:
    """Map CLI agent key to on-disk eval directory name."""
    mapping = {
        "customer-solution": "customer_solution_agent",
        "customer_solution": "customer_solution_agent",
        "customer_solution_agent": "customer_solution_agent",
    }
    dirname = mapping.get(agent_key, agent_key.replace("-", "_"))
    return EVALS_DIR / dirname


def list_eval_suite_paths(agent_key: str) -> list[Path]:
    directory = _agent_eval_dir(agent_key)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.yml"))


def list_eval_suite_ids(agent_key: str) -> list[str]:
    return [path.stem for path in list_eval_suite_paths(agent_key)]


def list_eval_suites(agent_key: str) -> list[EvalSuite | OverfittingEvalSuite]:
    return [load_eval_suite(agent_key, suite_id) for suite_id in list_eval_suite_ids(agent_key)]


def load_eval_suite(agent_key: str, suite_id: str) -> EvalSuite | OverfittingEvalSuite:
    path = _agent_eval_dir(agent_key) / f"{suite_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(f"Eval suite not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if suite_id == "overfitting" or data.get("base_case") is not None:
        return OverfittingEvalSuite.model_validate(data)
    return EvalSuite.model_validate(data)


def load_eval_suite_by_id(
    suite_id: str, agent_key: str = "customer-solution"
) -> EvalSuite | OverfittingEvalSuite:
    return load_eval_suite(agent_key, suite_id)
