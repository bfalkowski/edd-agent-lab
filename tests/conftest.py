import os

# Keep CI and local pytest deterministic unless a test overrides this.
os.environ.setdefault("AGENT_GENERATION_MODE", "mock")
