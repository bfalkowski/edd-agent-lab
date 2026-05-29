"""Agent generation mode and model access."""

from __future__ import annotations

import os
from typing import Literal

GenerationModeSetting = Literal["mock", "live", "auto"]
ResolvedGenerationMode = Literal["mock", "live"]

DEFAULT_AGENT_MODEL = "gpt-4o-mini"


def resolve_generation_mode(
    explicit: GenerationModeSetting | None = None,
) -> ResolvedGenerationMode:
    """Resolve mock vs live generation.

    - mock: deterministic template graph (CI default)
    - live: OpenAI-backed generation (requires OPENAI_API_KEY)
    - auto: live when OPENAI_API_KEY is set, otherwise mock
    """
    raw = (explicit or os.environ.get("AGENT_GENERATION_MODE", "auto")).strip().lower()
    if raw not in {"mock", "live", "auto"}:
        raise ValueError(
            f"Unsupported AGENT_GENERATION_MODE={raw!r}. Use mock, live, or auto."
        )
    if raw == "mock":
        return "mock"
    if raw == "live":
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "AGENT_GENERATION_MODE=live requires OPENAI_API_KEY. "
                "Set the key or use AGENT_GENERATION_MODE=auto."
            )
        return "live"
    return "live" if os.environ.get("OPENAI_API_KEY") else "mock"


def agent_model_name() -> str:
    return os.environ.get("AGENT_MODEL", DEFAULT_AGENT_MODEL)


def get_chat_model(*, temperature: float = 0.2):
    """Return a LangChain chat model or raise if dependencies/key are missing."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for live agent generation.")

    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Live generation requires langchain-openai. Install with: pip install -e '.[agent]'"
        ) from exc

    return ChatOpenAI(
        model=agent_model_name(),
        api_key=api_key,
        temperature=temperature,
    )
