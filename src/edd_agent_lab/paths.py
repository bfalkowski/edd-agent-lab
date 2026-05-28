import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent


def _has_lab_data(root: Path) -> bool:
    return (root / "scenarios").is_dir() and (root / "evals").is_dir()


def _find_repo_root() -> Path:
    override = os.environ.get("EDD_AGENT_LAB_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if _has_lab_data(root):
            return root
        raise FileNotFoundError(
            f"EDD_AGENT_LAB_ROOT does not contain scenarios/ and evals/: {root}"
        )

    for start in (Path.cwd(), PACKAGE_ROOT):
        for candidate in (start, *start.parents):
            if _has_lab_data(candidate):
                return candidate

    # src-layout fallback when running tests against source tree
    src_fallback = PACKAGE_ROOT.parent.parent
    if _has_lab_data(src_fallback):
        return src_fallback

    return src_fallback


REPO_ROOT = _find_repo_root()
SCENARIOS_DIR = REPO_ROOT / "scenarios"
EVALS_DIR = REPO_ROOT / "evals"
LAB_RUNS_DIR = REPO_ROOT / "lab-runs"
