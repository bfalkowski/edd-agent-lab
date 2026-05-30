import os

# Keep CI and local pytest deterministic unless a test overrides this.
# See AGENTS.md: CI has no AI provider keys; live LLM is opt-in only.
os.environ.setdefault("AGENT_GENERATION_MODE", "mock")
