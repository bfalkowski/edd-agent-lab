from pathlib import Path

import yaml

from edd_agent_lab.agents.registry import normalize_agent_dir
from edd_agent_lab.evals.schemas import Scenario
from edd_agent_lab.paths import SCENARIOS_DIR


def _agent_scenario_dir(agent_key: str) -> Path:
    return SCENARIOS_DIR / normalize_agent_dir(agent_key)


def list_scenario_paths(agent_key: str) -> list[Path]:
    directory = _agent_scenario_dir(agent_key)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.yml"))


def list_scenario_ids(agent_key: str) -> list[str]:
    return [path.stem for path in list_scenario_paths(agent_key)]


def list_scenarios(agent_key: str) -> list[Scenario]:
    return [load_scenario(agent_key, scenario_id) for scenario_id in list_scenario_ids(agent_key)]


def load_scenario(agent_key: str, scenario_id: str) -> Scenario:
    path = _agent_scenario_dir(agent_key) / f"{scenario_id}.yml"
    if not path.is_file():
        raise FileNotFoundError(f"Scenario not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(data)


def load_scenario_by_id(scenario_id: str, agent_key: str = "customer-solution") -> Scenario:
    return load_scenario(agent_key, scenario_id)
